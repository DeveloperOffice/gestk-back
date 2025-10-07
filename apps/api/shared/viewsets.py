"""
ViewSets Base para API REST

Classes base que implementam multitenancy e Regra de Ouro
Atualizado para suportar multi-tenant com UsuarioAcesso
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from .filters import ContabilidadeFilterBackend, DataEventoFilterBackend, MultitenantPermissionMixin
from .permissions import IsContabilidadeAccessible, IsScopeAccessible
import logging

logger = logging.getLogger(__name__)


class BaseViewSet(MultitenantPermissionMixin, viewsets.ModelViewSet):
    """
    ViewSet base que implementa multitenancy automático
    """
    
    permission_classes = [IsAuthenticated, IsContabilidadeAccessible]
    filter_backends = [ContabilidadeFilterBackend, DataEventoFilterBackend]
    
    def get_queryset(self):
        """
        Aplica filtros automáticos por contabilidade e escopo
        """
        queryset = super().get_queryset()
        
        if not self.request.user.is_authenticated:
            return queryset.none()
        
        # Superusuários têm acesso total
        if self.request.user.is_superuser:
            return queryset
        
        # Verificar se o modelo tem campo contabilidade
        if not hasattr(queryset.model, 'contabilidade'):
            return queryset
        
        # Obter contabilidade do contexto
        contabilidade = getattr(self.request, 'contabilidade', None)
        
        if not contabilidade:
            # Tentar usar a contabilidade padrão do usuário
            if hasattr(self.request.user, 'contabilidade') and self.request.user.contabilidade:
                contabilidade = self.request.user.contabilidade
            else:
                return queryset.none()
        
        # Aplicar filtro por contabilidade
        queryset = queryset.filter(contabilidade=contabilidade)
        
        # Aplicar filtros de escopo se necessário
        queryset = self.aplicar_filtros_escopo(queryset)
        
        return queryset
    
    def aplicar_filtros_escopo(self, queryset):
        """
        Aplica filtros de escopo baseados no UsuarioAcesso
        """
        try:
            from apps.core.models import UsuarioAcesso
            from django.utils import timezone
            
            # Buscar acessos do usuário para a contabilidade atual
            contabilidade = getattr(self.request, 'contabilidade', None)
            if not contabilidade:
                return queryset
            
            acessos = UsuarioAcesso.objects.filter(
                usuario=self.request.user,
                contabilidade=contabilidade,
                ativo=True,
                data_inicio__lte=timezone.now().date(),
                data_fim__isnull=True
            ) | UsuarioAcesso.objects.filter(
                usuario=self.request.user,
                contabilidade=contabilidade,
                ativo=True,
                data_inicio__lte=timezone.now().date(),
                data_fim__gte=timezone.now().date()
            )
            
            # Se não há acessos, retornar queryset vazio
            if not acessos.exists():
                return queryset.none()
            
            # Verificar se algum acesso permite acesso total (sem restrição de escopo)
            tem_acesso_total = any(not acesso.contrato and not acesso.empresa_cnpj for acesso in acessos)
            
            if tem_acesso_total:
                return queryset
            
            # Aplicar filtros de escopo
            filtros_escopo = Q()
            
            for acesso in acessos:
                if acesso.contrato and hasattr(queryset.model, 'contrato'):
                    filtros_escopo |= Q(contrato=acesso.contrato)
                
                if acesso.empresa_cnpj and hasattr(queryset.model, 'empresa_cnpj'):
                    filtros_escopo |= Q(empresa_cnpj=acesso.empresa_cnpj)
            
            if filtros_escopo:
                return queryset.filter(filtros_escopo)
            
            return queryset.none()
            
        except Exception as e:
            logger.error(f"Erro ao aplicar filtros de escopo: {e}")
            return queryset.none()
    
    def perform_create(self, serializer):
        """
        Define automaticamente a contabilidade ao criar objetos
        """
        contabilidade = getattr(self.request, 'contabilidade', self.request.user.contabilidade)
        serializer.save(contabilidade=contabilidade)
    
    def perform_update(self, serializer):
        """
        Valida contabilidade ao atualizar objetos
        """
        contabilidade = getattr(self.request, 'contabilidade', self.request.user.contabilidade)
        
        # Verificar se o objeto pertence à contabilidade
        if hasattr(serializer.instance, 'contabilidade'):
            if serializer.instance.contabilidade != contabilidade:
                raise PermissionDenied("Acesso negado: objeto não pertence à sua contabilidade")
        
        serializer.save()
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Endpoint para estatísticas básicas do modelo
        """
        try:
            queryset = self.get_queryset()
            
            stats = {
                'total': queryset.count(),
                'ativo': queryset.filter(ativo=True).count() if hasattr(queryset.model, 'ativo') else None,
                'inativo': queryset.filter(ativo=False).count() if hasattr(queryset.model, 'ativo') else None,
            }
            
            return Response(stats)
        except Exception as e:
            logger.error(f"Erro ao gerar estatísticas: {e}")
            return Response(
                {'error': 'Erro ao gerar estatísticas'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReadOnlyViewSet(MultitenantPermissionMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet somente leitura com multitenancy
    """
    
    permission_classes = [IsAuthenticated]
    filter_backends = [ContabilidadeFilterBackend, DataEventoFilterBackend]
    
    def get_queryset(self):
        """
        Aplica filtros automáticos por contabilidade
        """
        queryset = super().get_queryset()
        
        if not self.request.user.is_authenticated:
            return queryset.none()
        
        # Verificar se o modelo tem campo contabilidade
        if not hasattr(queryset.model, 'contabilidade'):
            return queryset
        
        # Aplicar filtro por contabilidade
        contabilidade = getattr(self.request, 'contabilidade', self.request.user.contabilidade)
        
        if not contabilidade:
            return queryset.none()
        
        return queryset.filter(contabilidade=contabilidade)


class DashboardViewSet(ReadOnlyViewSet):
    """
    ViewSet base para dashboards com agregações complexas
    """
    
    def get_queryset(self):
        """
        Aplica filtros específicos para dashboards
        """
        queryset = super().get_queryset()
        
        # Filtros específicos para dashboards
        data_inicio = self.request.query_params.get('data_inicio')
        data_fim = self.request.query_params.get('data_fim')
        
        if data_inicio and hasattr(queryset.model, 'data_criacao'):
            queryset = queryset.filter(data_criacao__gte=data_inicio)
        
        if data_fim and hasattr(queryset.model, 'data_criacao'):
            queryset = queryset.filter(data_criacao__lte=data_fim)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def resumo(self, request):
        """
        Endpoint para resumo executivo do dashboard
        """
        try:
            queryset = self.get_queryset()
            
            # Implementar agregações específicas do dashboard
            resumo = self.calcular_resumo(queryset)
            
            return Response(resumo)
        except Exception as e:
            logger.error(f"Erro ao gerar resumo: {e}")
            return Response(
                {'error': 'Erro ao gerar resumo'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def calcular_resumo(self, queryset):
        """
        Método para ser sobrescrito pelas classes filhas
        """
        return {
            'total': queryset.count(),
            'periodo': 'Últimos 30 dias'
        }
