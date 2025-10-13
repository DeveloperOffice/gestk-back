"""
Views para Faturas (SUPERUSER)
Endpoints exclusivos para administradores do sistema
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination

from apps.billing.models import Fatura
from apps.api.shared.permissions import IsSuperUserOrContabilidadeOwner

from .fatura_serializers import (
    FaturaListSerializer,
    FaturaDetailSerializer,
    FaturaCreateSerializer,
    FaturaUpdateSerializer
)
from .fatura_services import FaturaService
from .fatura_filters import FaturaFilter


class StandardPagination(PageNumberPagination):
    """Paginação padrão"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class FaturaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Faturas (SUPERUSER)
    
    Gerenciamento completo de faturas.
    Acesso restrito a SUPERUSER.
    
    Endpoints disponíveis:
    - list: Listar todas as faturas (GET /api/billing/superuser/faturas/)
    - create: Criar nova fatura (POST /api/billing/superuser/faturas/)
    - retrieve: Detalhar fatura (GET /api/billing/superuser/faturas/{id}/)
    - update: Atualizar fatura (PUT /api/billing/superuser/faturas/{id}/)
    - partial_update: Atualização parcial (PATCH /api/billing/superuser/faturas/{id}/)
    - destroy: Deletar fatura (DELETE /api/billing/superuser/faturas/{id}/)
    - marcar_como_paga: Marcar fatura como paga (POST /api/billing/superuser/faturas/{id}/marcar_como_paga/)
    - cancelar: Cancelar fatura (POST /api/billing/superuser/faturas/{id}/cancelar/)
    - estornar: Estornar fatura paga (POST /api/billing/superuser/faturas/{id}/estornar/)
    - reabrir: Reabrir fatura cancelada (POST /api/billing/superuser/faturas/{id}/reabrir/)
    - processar_vencimentos: Processar faturas vencidas (POST /api/billing/superuser/faturas/processar_vencimentos/)
    - estatisticas: Estatísticas gerais (GET /api/billing/superuser/faturas/estatisticas/)
    """
    
    queryset = Fatura.objects.select_related(
        'assinatura__contabilidade',
        'assinatura__plano'
    ).all()
    permission_classes = [IsAuthenticated, IsSuperUserOrContabilidadeOwner]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = FaturaFilter
    search_fields = [
        'numero_fatura',
        'assinatura__contabilidade__razao_social',
        'competencia'
    ]
    ordering_fields = [
        'data_emissao',
        'data_vencimento',
        'data_pagamento',
        'valor_final',
        'status'
    ]
    ordering = ['-data_vencimento']
    
    def get_serializer_class(self):
        """Retorna serializer apropriado por ação"""
        if self.action == 'list':
            return FaturaListSerializer
        elif self.action == 'create':
            return FaturaCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return FaturaUpdateSerializer
        return FaturaDetailSerializer
    
    def create(self, request, *args, **kwargs):
        """Criar nova fatura"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Usar service para criar
        fatura = FaturaService.criar(dados=serializer.validated_data)
        
        # Retornar com serializer de detalhe
        output_serializer = FaturaDetailSerializer(fatura)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """Atualizar fatura"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        
        # Usar service para atualizar
        fatura = FaturaService.atualizar(
            instance=instance,
            dados=serializer.validated_data
        )
        
        # Retornar com serializer de detalhe
        output_serializer = FaturaDetailSerializer(fatura)
        return Response(output_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Deletar fatura"""
        instance = self.get_object()
        
        # Verificar se pode deletar
        if instance.status == 'paga':
            return Response(
                {'detail': 'Não é possível deletar fatura paga. Use estornar.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def marcar_como_paga(self, request, pk=None):
        """
        Marcar fatura como paga
        
        Body:
        {
            "data_pagamento": "2025-10-09",  // opcional
            "metadados_pagamento": {}  // opcional
        }
        """
        instance = self.get_object()
        
        data_pagamento = request.data.get('data_pagamento')
        metadados_pagamento = request.data.get('metadados_pagamento')
        
        try:
            FaturaService.marcar_como_paga(
                instance=instance,
                data_pagamento=data_pagamento,
                metadados_pagamento=metadados_pagamento
            )
            
            serializer = FaturaDetailSerializer(instance)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        Cancelar fatura
        
        Body:
        {
            "motivo": "Cancelamento da assinatura"
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
            FaturaService.cancelar(
                instance=instance,
                motivo=motivo
            )
            
            serializer = FaturaDetailSerializer(instance)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def estornar(self, request, pk=None):
        """
        Estornar fatura paga
        
        Body:
        {
            "motivo": "Pagamento indevido"
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
            FaturaService.estornar(
                instance=instance,
                motivo=motivo
            )
            
            serializer = FaturaDetailSerializer(instance)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def reabrir(self, request, pk=None):
        """
        Reabrir fatura cancelada ou estornada
        """
        instance = self.get_object()
        
        try:
            FaturaService.reabrir(instance=instance)
            
            serializer = FaturaDetailSerializer(instance)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def processar_vencimentos(self, request):
        """
        Processar faturas vencidas
        
        Atualiza status de faturas abertas que venceram
        e suspende assinaturas inadimplentes.
        """
        try:
            resultado = FaturaService.processar_vencimentos()
            return Response(resultado)
            
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def estatisticas(self, request):
        """
        Estatísticas gerais de faturas
        
        Retorna:
        - Total de faturas
        - Distribuição por status
        - Valores (total, pago, pendente)
        - Alertas (próximas vencimento, vencidas)
        """
        # Aplicar filtros do queryset
        queryset = self.filter_queryset(self.get_queryset())
        
        estatisticas = FaturaService.calcular_estatisticas(queryset)
        return Response(estatisticas)
