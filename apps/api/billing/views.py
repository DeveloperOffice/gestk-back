"""
Views para API de Billing
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta

from apps.api.shared.viewsets import BaseViewSet
from apps.api.shared.permissions import IsAdminOrContabilidadeOwner, IsMultiTenantUser
from apps.billing.models import Plano, Assinatura, Fatura, Pagamento
from apps.core.models import Contabilidade
from .serializers import (
    PlanoSerializer, AssinaturaSerializer, FaturaSerializer,
    PagamentoSerializer, ContabilidadeBillingSerializer
)
from .filters import (
    PlanoFilter, AssinaturaFilter, FaturaFilter, PagamentoFilter
)


class PlanoViewSet(BaseViewSet):
    """
    ViewSet para gestão de Planos
    """
    queryset = Plano.objects.all()
    serializer_class = PlanoSerializer
    permission_classes = [IsAuthenticated, IsAdminOrContabilidadeOwner]
    filterset_class = PlanoFilter
    search_fields = ['codigo', 'nome', 'descricao']
    ordering_fields = ['nome', 'preco_mensal', 'ordem_exibicao', 'ativo']
    ordering = ['ordem_exibicao', 'nome']
    
    def get_queryset(self):
        """
        Filtra planos ativos por padrão
        """
        queryset = Plano.objects.all()
        
        # Se não for admin, mostrar apenas planos ativos
        if not self.request.user.is_superuser and not self.request.user.tipo_usuario in ['superuser', 'admin']:
            queryset = queryset.filter(ativo=True)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def ativos(self, request):
        """
        Lista apenas planos ativos
        """
        queryset = self.get_queryset().filter(ativo=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def resumo(self, request):
        """
        Resumo dos planos
        """
        queryset = self.get_queryset()
        
        resumo = {
            'total': queryset.count(),
            'ativos': queryset.filter(ativo=True).count(),
            'inativos': queryset.filter(ativo=False).count(),
            'preco_medio_mensal': queryset.filter(ativo=True).aggregate(
                preco_medio=Avg('preco_mensal')
            )['preco_medio'] or 0,
            'preco_medio_anual': queryset.filter(ativo=True).aggregate(
                preco_medio=Avg('preco_anual')
            )['preco_medio'] or 0
        }
        
        return Response(resumo)


class AssinaturaViewSet(BaseViewSet):
    """
    ViewSet para gestão de Assinaturas
    """
    queryset = Assinatura.objects.all()
    serializer_class = AssinaturaSerializer
    permission_classes = [IsAuthenticated, IsAdminOrContabilidadeOwner]
    filterset_class = AssinaturaFilter
    search_fields = ['contabilidade__razao_social', 'plano__nome', 'plano__codigo']
    ordering_fields = ['data_inicio', 'data_fim', 'status', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filtra assinaturas por contabilidade do contexto
        """
        queryset = Assinatura.objects.select_related(
            'contabilidade', 'plano', 'created_by'
        ).all()
        
        # Aplicar filtro de contabilidade se não for superusuário
        if not self.request.user.is_superuser:
            contabilidade = getattr(self.request, 'contabilidade', None)
            if contabilidade:
                queryset = queryset.filter(contabilidade=contabilidade)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def suspender(self, request, pk=None):
        """
        Suspende uma assinatura
        """
        assinatura = self.get_object()
        motivo = request.data.get('motivo', 'Suspensão manual')
        
        assinatura.suspender(motivo)
        
        return Response({
            'message': 'Assinatura suspensa com sucesso',
            'status': assinatura.status,
            'motivo': assinatura.motivo_suspensao,
            'data_suspensao': assinatura.data_suspensao
        })
    
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        Cancela uma assinatura
        """
        assinatura = self.get_object()
        motivo = request.data.get('motivo', 'Cancelamento manual')
        
        assinatura.cancelar(motivo)
        
        return Response({
            'message': 'Assinatura cancelada com sucesso',
            'status': assinatura.status,
            'motivo': assinatura.motivo_cancelamento,
            'data_cancelamento': assinatura.data_cancelamento
        })
    
    @action(detail=True, methods=['post'])
    def ativar(self, request, pk=None):
        """
        Ativa uma assinatura
        """
        assinatura = self.get_object()
        
        assinatura.ativar()
        
        return Response({
            'message': 'Assinatura ativada com sucesso',
            'status': assinatura.status
        })
    
    @action(detail=False, methods=['post'])
    def criar_assinatura(self, request):
        """
        Cria uma nova assinatura
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def resumo(self, request):
        """
        Resumo das assinaturas
        """
        queryset = self.get_queryset()
        
        resumo = {
            'total': queryset.count(),
            'por_status': dict(queryset.values('status').annotate(count=Count('id')).values_list('status', 'count')),
            'por_plano': dict(queryset.values('plano__nome').annotate(count=Count('id')).values_list('plano__nome', 'count')),
            'ativas': queryset.filter(status='ativa').count(),
            'suspensas': queryset.filter(status='suspensa').count(),
            'canceladas': queryset.filter(status='cancelada').count(),
            'em_trial': queryset.filter(trial_ate__gte=timezone.now().date()).count(),
            'receita_mensal': sum(ass.valor_mensal for ass in queryset.filter(status='ativa')),
            'receita_anual': sum(ass.valor_anual or 0 for ass in queryset.filter(status='ativa'))
        }
        
        return Response(resumo)


class FaturaViewSet(BaseViewSet):
    """
    ViewSet para gestão de Faturas
    """
    queryset = Fatura.objects.all()
    serializer_class = FaturaSerializer
    permission_classes = [IsAuthenticated, IsMultiTenantUser]
    filterset_class = FaturaFilter
    search_fields = ['numero_fatura', 'assinatura__contabilidade__razao_social']
    ordering_fields = ['numero_fatura', 'data_emissao', 'data_vencimento', 'status', 'valor_final']
    ordering = ['-data_emissao']
    
    def get_queryset(self):
        """
        Filtra faturas por contabilidade do contexto
        """
        queryset = Fatura.objects.select_related(
            'assinatura__contabilidade', 'assinatura__plano'
        ).all()
        
        # Aplicar filtro de contabilidade
        contabilidade = getattr(self.request, 'contabilidade', None)
        if contabilidade:
            queryset = queryset.filter(assinatura__contabilidade=contabilidade)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def marcar_como_paga(self, request, pk=None):
        """
        Marca uma fatura como paga
        """
        fatura = self.get_object()
        data_pagamento = request.data.get('data_pagamento')
        
        if data_pagamento:
            try:
                data_pagamento = datetime.strptime(data_pagamento, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Formato de data inválido. Use YYYY-MM-DD'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        fatura.marcar_como_paga(data_pagamento)
        
        return Response({
            'message': 'Fatura marcada como paga',
            'status': fatura.status,
            'data_pagamento': fatura.data_pagamento
        })
    
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        Cancela uma fatura
        """
        fatura = self.get_object()
        
        fatura.cancelar()
        
        return Response({
            'message': 'Fatura cancelada com sucesso',
            'status': fatura.status
        })
    
    @action(detail=False, methods=['post'])
    def gerar_faturas(self, request):
        """
        Gera faturas para assinaturas ativas
        """
        competencia = request.data.get('competencia')
        if not competencia:
            return Response(
                {'error': 'Competência é obrigatória (formato: YYYY-MM)'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Lógica para gerar faturas (implementar conforme necessário)
        # Por enquanto, retorna uma resposta de exemplo
        return Response({
            'message': f'Faturas geradas para competência {competencia}',
            'competencia': competencia,
            'faturas_geradas': 0  # Implementar lógica real
        })
    
    @action(detail=False, methods=['get'])
    def resumo(self, request):
        """
        Resumo das faturas
        """
        queryset = self.get_queryset()
        
        resumo = {
            'total': queryset.count(),
            'por_status': dict(queryset.values('status').annotate(count=Count('id')).values_list('status', 'count')),
            'abertas': queryset.filter(status='aberta').count(),
            'pagas': queryset.filter(status='paga').count(),
            'vencidas': queryset.filter(status='vencida').count(),
            'canceladas': queryset.filter(status='cancelada').count(),
            'valor_total_aberto': queryset.filter(status='aberta').aggregate(
                total=Sum('valor_final')
            )['total'] or 0,
            'valor_total_pago': queryset.filter(status='paga').aggregate(
                total=Sum('valor_final')
            )['total'] or 0,
            'receita_por_mes': dict(queryset.filter(status='paga').values('competencia').annotate(
                receita=Sum('valor_final')
            ).values_list('competencia', 'receita'))
        }
        
        return Response(resumo)


class PagamentoViewSet(BaseViewSet):
    """
    ViewSet para gestão de Pagamentos
    """
    queryset = Pagamento.objects.all()
    serializer_class = PagamentoSerializer
    permission_classes = [IsAuthenticated, IsMultiTenantUser]
    filterset_class = PagamentoFilter
    search_fields = ['fatura__numero_fatura', 'transacao_id', 'referencia']
    ordering_fields = ['data_pagamento', 'status', 'valor', 'metodo']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filtra pagamentos por contabilidade do contexto
        """
        queryset = Pagamento.objects.select_related(
            'fatura__assinatura__contabilidade'
        ).all()
        
        # Aplicar filtro de contabilidade
        contabilidade = getattr(self.request, 'contabilidade', None)
        if contabilidade:
            queryset = queryset.filter(fatura__assinatura__contabilidade=contabilidade)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def confirmar(self, request, pk=None):
        """
        Confirma um pagamento
        """
        pagamento = self.get_object()
        data_confirmacao = request.data.get('data_confirmacao')
        
        if data_confirmacao:
            try:
                data_confirmacao = datetime.strptime(data_confirmacao, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return Response(
                    {'error': 'Formato de data inválido. Use YYYY-MM-DD HH:MM:SS'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        pagamento.confirmar(data_confirmacao)
        
        return Response({
            'message': 'Pagamento confirmado com sucesso',
            'status': pagamento.status,
            'data_confirmacao': pagamento.data_confirmacao
        })
    
    @action(detail=True, methods=['post'])
    def estornar(self, request, pk=None):
        """
        Estorna um pagamento
        """
        pagamento = self.get_object()
        
        pagamento.estornar()
        
        return Response({
            'message': 'Pagamento estornado com sucesso',
            'status': pagamento.status
        })
    
    @action(detail=False, methods=['get'])
    def resumo(self, request):
        """
        Resumo dos pagamentos
        """
        queryset = self.get_queryset()
        
        resumo = {
            'total': queryset.count(),
            'por_status': dict(queryset.values('status').annotate(count=Count('id')).values_list('status', 'count')),
            'por_metodo': dict(queryset.values('metodo').annotate(count=Count('id')).values_list('metodo', 'count')),
            'pendentes': queryset.filter(status='pendente').count(),
            'confirmados': queryset.filter(status='confirmado').count(),
            'estornados': queryset.filter(status='estornado').count(),
            'valor_total_confirmado': queryset.filter(status='confirmado').aggregate(
                total=Sum('valor')
            )['total'] or 0,
            'valor_total_pendente': queryset.filter(status='pendente').aggregate(
                total=Sum('valor')
            )['total'] or 0
        }
        
        return Response(resumo)


class ContabilidadeBillingViewSet(BaseViewSet):
    """
    ViewSet para Contabilidades com informações de billing
    """
    queryset = Contabilidade.objects.all()
    serializer_class = ContabilidadeBillingSerializer
    permission_classes = [IsAuthenticated, IsAdminOrContabilidadeOwner]
    search_fields = ['razao_social', 'nome_fantasia', 'cnpj']
    ordering_fields = ['razao_social', 'cnpj', 'created_at']
    ordering = ['razao_social']
    
    def get_queryset(self):
        """
        Filtra contabilidades (não aplica filtro de contabilidade)
        """
        return Contabilidade.objects.prefetch_related(
            'assinaturas', 'assinaturas__faturas'
        ).all()
    
    @action(detail=True, methods=['post'])
    def suspender_por_inadimplencia(self, request, pk=None):
        """
        Suspende contabilidade por inadimplência
        """
        contabilidade = self.get_object()
        contabilidade.suspensa_por_inadimplencia = True
        contabilidade.save()
        
        return Response({
            'message': 'Contabilidade suspensa por inadimplência',
            'suspensa_por_inadimplencia': contabilidade.suspensa_por_inadimplencia
        })
    
    @action(detail=True, methods=['post'])
    def reativar(self, request, pk=None):
        """
        Reativa contabilidade
        """
        contabilidade = self.get_object()
        contabilidade.suspensa_por_inadimplencia = False
        contabilidade.save()
        
        return Response({
            'message': 'Contabilidade reativada',
            'suspensa_por_inadimplencia': contabilidade.suspensa_por_inadimplencia
        })
    
    @action(detail=False, methods=['get'])
    def resumo(self, request):
        """
        Resumo das contabilidades com billing
        """
        queryset = self.get_queryset()
        
        resumo = {
            'total': queryset.count(),
            'com_assinatura': queryset.filter(assinaturas__isnull=False).distinct().count(),
            'sem_assinatura': queryset.filter(assinaturas__isnull=True).count(),
            'suspensas': queryset.filter(suspensa_por_inadimplencia=True).count(),
            'receita_total': queryset.aggregate(
                receita=Sum('assinaturas__faturas__valor_final', 
                           filter=Q(assinaturas__faturas__status='paga'))
            )['receita'] or 0,
            'faturas_pendentes': queryset.aggregate(
                pendentes=Sum('assinaturas__faturas__valor_final',
                             filter=Q(assinaturas__faturas__status='aberta'))
            )['pendentes'] or 0
        }
        
        return Response(resumo)
