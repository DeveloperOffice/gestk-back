"""
Views para Contratos GESTK (SUPERUSER)
Endpoints exclusivos para administradores do sistema
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination

from apps.administracao.models import ContratoGestk
from apps.api.shared.permissions import IsSuperUserOrContabilidadeOwner

from .contrato_gestk_serializers import (
    ContratoGestkListSerializer,
    ContratoGestkDetailSerializer,
    ContratoGestkCreateSerializer,
    ContratoGestkUpdateSerializer
)
from .contrato_gestk_services import ContratoGestkService
from .contrato_gestk_filters import ContratoGestkFilter


class StandardPagination(PageNumberPagination):
    """Paginação padrão"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ContratoGestkViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Contratos GESTK (SUPERUSER)
    
    Gerenciamento completo de contratos entre GESTK e contabilidades clientes.
    Acesso restrito a SUPERUSER.
    
    Endpoints disponíveis:
    - list: Listar todos os contratos GESTK (GET /api/gestao/superuser/contratos-gestk/)
    - create: Criar novo contrato GESTK (POST /api/gestao/superuser/contratos-gestk/)
    - retrieve: Detalhar contrato específico (GET /api/gestao/superuser/contratos-gestk/{id}/)
    - update: Atualizar contrato (PUT /api/gestao/superuser/contratos-gestk/{id}/)
    - partial_update: Atualização parcial (PATCH /api/gestao/superuser/contratos-gestk/{id}/)
    - destroy: Deletar contrato (DELETE /api/gestao/superuser/contratos-gestk/{id}/)
    - renovar: Renovar contrato (POST /api/gestao/superuser/contratos-gestk/{id}/renovar/)
    - suspender: Suspender contrato (POST /api/gestao/superuser/contratos-gestk/{id}/suspender/)
    - reativar: Reativar contrato suspenso (POST /api/gestao/superuser/contratos-gestk/{id}/reativar/)
    - cancelar: Cancelar contrato (POST /api/gestao/superuser/contratos-gestk/{id}/cancelar/)
    - estatisticas: Estatísticas detalhadas do contrato (GET /api/gestao/superuser/contratos-gestk/{id}/estatisticas/)
    - resumo: Resumo geral dos contratos (GET /api/gestao/superuser/contratos-gestk/resumo/)
    """
    
    queryset = ContratoGestk.objects.select_related('contabilidade').all()
    permission_classes = [IsAuthenticated, IsSuperUserOrContabilidadeOwner]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ContratoGestkFilter
    search_fields = ['numero_contrato', 'contabilidade__razao_social', 'plano_servico']
    ordering_fields = ['data_inicio', 'data_termino', 'valor_mensal', 'status']
    ordering = ['-data_inicio']
    
    def get_serializer_class(self):
        """Retorna serializer apropriado por ação"""
        if self.action == 'list':
            return ContratoGestkListSerializer
        elif self.action == 'create':
            return ContratoGestkCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ContratoGestkUpdateSerializer
        return ContratoGestkDetailSerializer
    
    def create(self, request, *args, **kwargs):
        """Criar novo contrato GESTK"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Usar service para criar
        contrato = ContratoGestkService.criar(
            dados=serializer.validated_data,
            usuario=request.user
        )
        
        # Retornar com serializer de detalhe
        output_serializer = ContratoGestkDetailSerializer(contrato)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """Atualizar contrato existente"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        
        # Usar service para atualizar
        contrato = ContratoGestkService.atualizar(
            instance=instance,
            dados=serializer.validated_data,
            usuario=request.user
        )
        
        # Retornar com serializer de detalhe
        output_serializer = ContratoGestkDetailSerializer(contrato)
        return Response(output_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Deletar contrato"""
        instance = self.get_object()
        
        # Verificar se pode deletar
        if instance.status == 'ativo':
            return Response(
                {'detail': 'Não é possível deletar contrato ativo. Cancele primeiro.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def renovar(self, request, pk=None):
        """
        Renovar contrato
        
        Body:
        {
            "nova_data_termino": "2025-12-31",  // opcional
            "novo_valor": 1500.00  // opcional
        }
        """
        instance = self.get_object()
        
        nova_data_termino = request.data.get('nova_data_termino')
        novo_valor = request.data.get('novo_valor')
        
        try:
            ContratoGestkService.renovar(
                instance=instance,
                usuario=request.user,
                nova_data_termino=nova_data_termino,
                novo_valor=novo_valor
            )
            
            serializer = ContratoGestkDetailSerializer(instance)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def suspender(self, request, pk=None):
        """
        Suspender contrato
        
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
            ContratoGestkService.suspender(
                instance=instance,
                motivo=motivo,
                usuario=request.user
            )
            
            serializer = ContratoGestkDetailSerializer(instance)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def reativar(self, request, pk=None):
        """
        Reativar contrato suspenso
        """
        instance = self.get_object()
        
        try:
            ContratoGestkService.reativar(
                instance=instance,
                usuario=request.user
            )
            
            serializer = ContratoGestkDetailSerializer(instance)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        Cancelar contrato
        
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
            ContratoGestkService.cancelar(
                instance=instance,
                motivo=motivo,
                usuario=request.user
            )
            
            serializer = ContratoGestkDetailSerializer(instance)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def estatisticas(self, request, pk=None):
        """
        Estatísticas detalhadas do contrato
        
        Query params:
        - data_inicio: filtrar período (YYYY-MM-DD)
        - data_fim: filtrar período (YYYY-MM-DD)
        """
        instance = self.get_object()
        
        data_inicio = request.query_params.get('data_inicio')
        data_fim = request.query_params.get('data_fim')
        
        # Converter strings para date se fornecidas
        from datetime import datetime
        if data_inicio:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        if data_fim:
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        
        estatisticas = ContratoGestkService.calcular_estatisticas(
            instance=instance,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
        
        return Response(estatisticas)
    
    @action(detail=False, methods=['get'])
    def resumo(self, request):
        """
        Resumo geral dos contratos GESTK
        
        Retorna:
        - Total de contratos
        - Distribuição por status
        - Alertas (próximos vencimento)
        - Valores (MRR, ARR estimado)
        """
        # Aplicar filtros do queryset
        queryset = self.filter_queryset(self.get_queryset())
        
        resumo = ContratoGestkService.calcular_resumo(queryset)
        return Response(resumo)
