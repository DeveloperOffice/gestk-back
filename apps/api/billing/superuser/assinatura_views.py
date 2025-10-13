"""
Views para Assinaturas (SUPERUSER)
Endpoints exclusivos para administradores do sistema
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination

from apps.billing.models import Assinatura
from apps.api.shared.permissions import IsSuperUserOrContabilidadeOwner

from .assinatura_serializers import (
    AssinaturaListSerializer,
    AssinaturaDetailSerializer,
    AssinaturaCreateSerializer,
    AssinaturaUpdateSerializer
)
from .assinatura_services import AssinaturaService
from .assinatura_filters import AssinaturaFilter


class StandardPagination(PageNumberPagination):
    """Paginação padrão"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class AssinaturaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Assinaturas (SUPERUSER)
    
    Gerenciamento completo de assinaturas de planos.
    Acesso restrito a SUPERUSER.
    
    Endpoints disponíveis:
    - list: Listar todas as assinaturas (GET /api/billing/superuser/assinaturas/)
    - create: Criar nova assinatura (POST /api/billing/superuser/assinaturas/)
    - retrieve: Detalhar assinatura (GET /api/billing/superuser/assinaturas/{id}/)
    - update: Atualizar assinatura (PUT /api/billing/superuser/assinaturas/{id}/)
    - partial_update: Atualização parcial (PATCH /api/billing/superuser/assinaturas/{id}/)
    - destroy: Deletar assinatura (DELETE /api/billing/superuser/assinaturas/{id}/)
    - renovar: Renovar assinatura (POST /api/billing/superuser/assinaturas/{id}/renovar/)
    - suspender: Suspender assinatura (POST /api/billing/superuser/assinaturas/{id}/suspender/)
    - reativar: Reativar assinatura (POST /api/billing/superuser/assinaturas/{id}/reativar/)
    - cancelar: Cancelar assinatura (POST /api/billing/superuser/assinaturas/{id}/cancelar/)
    - gerar_fatura: Gerar fatura manualmente (POST /api/billing/superuser/assinaturas/{id}/gerar_fatura/)
    - estatisticas: Estatísticas da assinatura (GET /api/billing/superuser/assinaturas/{id}/estatisticas/)
    - resumo: Resumo geral (GET /api/billing/superuser/assinaturas/resumo/)
    """
    
    queryset = Assinatura.objects.select_related(
        'contabilidade', 'plano'
    ).prefetch_related('faturas').all()
    permission_classes = [IsAuthenticated, IsSuperUserOrContabilidadeOwner]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = AssinaturaFilter
    search_fields = ['contabilidade__razao_social', 'plano__nome', 'plano__codigo']
    ordering_fields = ['data_inicio', 'data_fim', 'valor_mensal', 'status', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Retorna serializer apropriado por ação"""
        if self.action == 'list':
            return AssinaturaListSerializer
        elif self.action == 'create':
            return AssinaturaCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AssinaturaUpdateSerializer
        return AssinaturaDetailSerializer
    
    def create(self, request, *args, **kwargs):
        """Criar nova assinatura"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Usar service para criar
        assinatura = AssinaturaService.criar(
            dados=serializer.validated_data,
            usuario=request.user
        )
        
        # Retornar com serializer de detalhe
        output_serializer = AssinaturaDetailSerializer(assinatura)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """Atualizar assinatura"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        
        # Usar service para atualizar
        assinatura = AssinaturaService.atualizar(
            instance=instance,
            dados=serializer.validated_data,
            usuario=request.user
        )
        
        # Retornar com serializer de detalhe
        output_serializer = AssinaturaDetailSerializer(assinatura)
        return Response(output_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Deletar assinatura"""
        instance = self.get_object()
        
        # Verificar se pode deletar
        if instance.status == 'ativa':
            return Response(
                {'detail': 'Não é possível deletar assinatura ativa. Cancele primeiro.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar se há faturas
        if instance.faturas.exists():
            return Response(
                {'detail': 'Não é possível deletar assinatura com faturas. Cancele a assinatura.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def renovar(self, request, pk=None):
        """
        Renovar assinatura
        
        Body:
        {
            "nova_data_fim": "2025-12-31",  // opcional
            "novo_valor": 1500.00  // opcional
        }
        """
        instance = self.get_object()
        
        nova_data_fim = request.data.get('nova_data_fim')
        novo_valor = request.data.get('novo_valor')
        
        try:
            AssinaturaService.renovar(
                instance=instance,
                usuario=request.user,
                nova_data_fim=nova_data_fim,
                novo_valor=novo_valor
            )
            
            serializer = AssinaturaDetailSerializer(instance)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def suspender(self, request, pk=None):
        """
        Suspender assinatura
        
        Body:
        {
            "motivo": "Inadimplência"
        }
        """
        instance = self.get_object()
        motivo = request.data.get('motivo')
        
        if not motivo:
            return Response(
                {'motivo': ['Este campo é obrigatório']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            AssinaturaService.suspender(
                instance=instance,
                motivo=motivo,
                usuario=request.user
            )
            
            serializer = AssinaturaDetailSerializer(instance)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def reativar(self, request, pk=None):
        """
        Reativar assinatura suspensa
        """
        instance = self.get_object()
        
        try:
            AssinaturaService.reativar(
                instance=instance,
                usuario=request.user
            )
            
            serializer = AssinaturaDetailSerializer(instance)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        Cancelar assinatura
        
        Body:
        {
            "motivo": "Solicitação do cliente"
        }
        """
        instance = self.get_object()
        motivo = request.data.get('motivo')
        
        if not motivo:
            return Response(
                {'motivo': ['Este campo é obrigatório']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            AssinaturaService.cancelar(
                instance=instance,
                motivo=motivo,
                usuario=request.user
            )
            
            serializer = AssinaturaDetailSerializer(instance)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def gerar_fatura(self, request, pk=None):
        """
        Gerar fatura manualmente
        
        Body:
        {
            "competencia": "2025-10"
        }
        """
        instance = self.get_object()
        competencia = request.data.get('competencia')
        
        if not competencia:
            return Response(
                {'competencia': ['Este campo é obrigatório']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            fatura = AssinaturaService.gerar_fatura(
                instance=instance,
                competencia=competencia,
                usuario=request.user
            )
            
            from .fatura_serializers import FaturaDetailSerializer
            serializer = FaturaDetailSerializer(fatura)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def estatisticas(self, request, pk=None):
        """
        Estatísticas detalhadas da assinatura
        """
        instance = self.get_object()
        estatisticas = AssinaturaService.calcular_estatisticas(instance)
        return Response(estatisticas)
    
    @action(detail=False, methods=['get'])
    def resumo(self, request):
        """
        Resumo geral das assinaturas
        
        Retorna:
        - Total de assinaturas
        - Distribuição por status
        - Alertas (próximas vencimento)
        - Valores (MRR, ARR)
        """
        # Aplicar filtros do queryset
        queryset = self.filter_queryset(self.get_queryset())
        
        resumo = AssinaturaService.calcular_resumo(queryset)
        return Response(resumo)
