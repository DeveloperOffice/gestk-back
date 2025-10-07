"""
Views para API de Administração
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta

from apps.api.shared.viewsets import BaseViewSet
from apps.api.shared.permissions import IsAdminOrContabilidadeOwner, IsMultiTenantUser
from apps.administracao.models import ContratoGestk
from apps.core.models import Contabilidade, UsuarioAcesso
from .serializers import (
    ContratoGestkSerializer, UsuarioAcessoSerializer,
    ContabilidadeAdministracaoSerializer
)
from .filters import (
    ContratoGestkFilter, UsuarioAcessoFilter, ContabilidadeAdministracaoFilter
)


class ContratoGestkViewSet(BaseViewSet):
    """
    ViewSet para gestão de Contratos GESTK
    """
    queryset = ContratoGestk.objects.all()
    serializer_class = ContratoGestkSerializer
    permission_classes = [IsAuthenticated, IsAdminOrContabilidadeOwner]
    filterset_class = ContratoGestkFilter
    search_fields = ['numero_contrato', 'contabilidade__razao_social', 'plano_servico']
    ordering_fields = ['numero_contrato', 'data_inicio', 'data_termino', 'status', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filtra contratos por contabilidade do contexto
        """
        queryset = ContratoGestk.objects.select_related(
            'contabilidade', 'created_by'
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
        Suspende um contrato GESTK
        """
        contrato = self.get_object()
        motivo = request.data.get('motivo', 'Suspensão manual')
        
        contrato.suspender(motivo)
        
        return Response({
            'message': 'Contrato suspenso com sucesso',
            'status': contrato.status,
            'motivo': contrato.motivo_suspensao,
            'data_suspensao': contrato.data_suspensao
        })
    
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        Cancela um contrato GESTK
        """
        contrato = self.get_object()
        motivo = request.data.get('motivo', 'Cancelamento manual')
        
        contrato.cancelar(motivo)
        
        return Response({
            'message': 'Contrato cancelado com sucesso',
            'status': contrato.status,
            'motivo': contrato.motivo_cancelamento,
            'data_cancelamento': contrato.data_cancelamento
        })
    
    @action(detail=True, methods=['post'])
    def ativar(self, request, pk=None):
        """
        Ativa um contrato GESTK
        """
        contrato = self.get_object()
        
        contrato.ativar()
        
        return Response({
            'message': 'Contrato ativado com sucesso',
            'status': contrato.status
        })
    
    @action(detail=False, methods=['get'])
    def resumo(self, request):
        """
        Resumo dos contratos GESTK
        """
        queryset = self.get_queryset()
        
        resumo = {
            'total': queryset.count(),
            'por_status': dict(queryset.values('status').annotate(count=Count('id')).values_list('status', 'count')),
            'por_plano': dict(queryset.values('plano_servico').annotate(count=Count('id')).values_list('plano_servico', 'count')),
            'ativos': queryset.filter(status='ativo').count(),
            'suspensos': queryset.filter(status='suspenso').count(),
            'cancelados': queryset.filter(status='cancelado').count(),
            'em_trial': queryset.filter(trial_ate__gte=timezone.now().date()).count(),
            'receita_mensal': sum(contrato.valor_mensal for contrato in queryset.filter(status='ativo')),
            'receita_anual': sum(contrato.valor_anual or 0 for contrato in queryset.filter(status='ativo'))
        }
        
        return Response(resumo)


class UsuarioAcessoViewSet(BaseViewSet):
    """
    ViewSet para gestão de Acessos de Usuário
    """
    queryset = UsuarioAcesso.objects.all()
    serializer_class = UsuarioAcessoSerializer
    permission_classes = [IsAuthenticated, IsAdminOrContabilidadeOwner]
    filterset_class = UsuarioAcessoFilter
    search_fields = ['usuario__username', 'usuario__email', 'contabilidade__razao_social']
    ordering_fields = ['data_inicio', 'data_fim', 'role', 'ativo', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filtra acessos por contabilidade do contexto
        """
        queryset = UsuarioAcesso.objects.select_related(
            'usuario', 'contabilidade', 'contrato', 'created_by'
        ).all()
        
        # Aplicar filtro de contabilidade se não for superusuário
        if not self.request.user.is_superuser:
            contabilidade = getattr(self.request, 'contabilidade', None)
            if contabilidade:
                queryset = queryset.filter(contabilidade=contabilidade)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def ativar(self, request, pk=None):
        """
        Ativa um acesso de usuário
        """
        acesso = self.get_object()
        
        acesso.ativar()
        
        return Response({
            'message': 'Acesso ativado com sucesso',
            'ativo': acesso.ativo
        })
    
    @action(detail=True, methods=['post'])
    def desativar(self, request, pk=None):
        """
        Desativa um acesso de usuário
        """
        acesso = self.get_object()
        
        acesso.desativar()
        
        return Response({
            'message': 'Acesso desativado com sucesso',
            'ativo': acesso.ativo
        })
    
    @action(detail=True, methods=['post'])
    def estender_vigencia(self, request, pk=None):
        """
        Estende a vigência de um acesso
        """
        acesso = self.get_object()
        nova_data_fim = request.data.get('data_fim')
        
        if not nova_data_fim:
            return Response(
                {'error': 'Data de fim é obrigatória'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            nova_data_fim = datetime.strptime(nova_data_fim, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Formato de data inválido. Use YYYY-MM-DD'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        acesso.estender_vigencia(nova_data_fim)
        
        return Response({
            'message': 'Vigência estendida com sucesso',
            'data_fim': acesso.data_fim
        })
    
    @action(detail=False, methods=['get'])
    def resumo(self, request):
        """
        Resumo dos acessos de usuário
        """
        queryset = self.get_queryset()
        
        resumo = {
            'total': queryset.count(),
            'por_role': dict(queryset.values('role').annotate(count=Count('id')).values_list('role', 'count')),
            'por_status': dict(queryset.values('ativo').annotate(count=Count('id')).values_list('ativo', 'count')),
            'ativos': queryset.filter(ativo=True).count(),
            'inativos': queryset.filter(ativo=False).count(),
            'vencidos': queryset.filter(data_fim__lt=timezone.now().date()).count(),
            'em_trial': queryset.filter(data_inicio__gte=timezone.now().date() - timedelta(days=30)).count()
        }
        
        return Response(resumo)


class ContabilidadeAdministracaoViewSet(BaseViewSet):
    """
    ViewSet para Contabilidades com informações de administração
    """
    queryset = Contabilidade.objects.all()
    serializer_class = ContabilidadeAdministracaoSerializer
    permission_classes = [IsAuthenticated, IsAdminOrContabilidadeOwner]
    filterset_class = ContabilidadeAdministracaoFilter
    search_fields = ['razao_social', 'nome_fantasia', 'cnpj']
    ordering_fields = ['razao_social', 'cnpj', 'created_at']
    ordering = ['razao_social']
    
    def get_queryset(self):
        """
        Filtra contabilidades (não aplica filtro de contabilidade)
        """
        return Contabilidade.objects.prefetch_related(
            'contrato_gestk', 'acessos_usuarios'
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
        Resumo das contabilidades com administração
        """
        queryset = self.get_queryset()
        
        resumo = {
            'total': queryset.count(),
            'com_contrato': queryset.filter(contrato_gestk__isnull=False).distinct().count(),
            'sem_contrato': queryset.filter(contrato_gestk__isnull=True).count(),
            'suspensas': queryset.filter(suspensa_por_inadimplencia=True).count(),
            'total_usuarios': queryset.aggregate(
                usuarios=Count('acessos_usuarios', distinct=True)
            )['usuarios'] or 0,
            'receita_total': sum(
                contrato.valor_mensal for contrato in 
                queryset.filter(contrato_gestk__status='ativo').values_list('contrato_gestk', flat=True)
            ) if queryset.filter(contrato_gestk__status='ativo').exists() else 0
        }
        
        return Response(resumo)