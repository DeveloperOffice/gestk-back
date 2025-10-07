"""
Middleware para gerenciamento de contexto multi-tenant
"""

from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import PermissionDenied
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class MultiTenantContextMiddleware(MiddlewareMixin):
    """
    Middleware que gerencia o contexto multi-tenant
    """
    
    def process_request(self, request):
        """
        Processa a requisição e define o contexto multi-tenant
        """
        if not request.user.is_authenticated:
            return
        
        # Obter contabilidade do contexto
        contabilidade = self.get_contabilidade_from_request(request)
        if contabilidade:
            # Verificar se o usuário tem acesso à contabilidade
            if self.verificar_acesso_contabilidade(request.user, contabilidade):
                request.contabilidade = contabilidade
                # Atualizar última contabilidade acessada
                self.atualizar_ultima_contabilidade(request.user, contabilidade)
            else:
                raise PermissionDenied("Usuário não tem acesso à contabilidade especificada")
        else:
            # Usar contabilidade padrão do usuário
            if hasattr(request.user, 'contabilidade') and request.user.contabilidade:
                request.contabilidade = request.user.contabilidade
            else:
                # Tentar obter a última contabilidade acessada
                if hasattr(request.user, 'ultima_contabilidade') and request.user.ultima_contabilidade:
                    if self.verificar_acesso_contabilidade(request.user, request.user.ultima_contabilidade):
                        request.contabilidade = request.user.ultima_contabilidade
                    else:
                        # Buscar primeira contabilidade acessível
                        contabilidade_acessivel = self.get_primeira_contabilidade_acessivel(request.user)
                        if contabilidade_acessivel:
                            request.contabilidade = contabilidade_acessivel
                        else:
                            raise PermissionDenied("Usuário não tem acesso a nenhuma contabilidade")
    
    def get_contabilidade_from_request(self, request):
        """
        Extrai a contabilidade do request
        """
        # Tentar obter do header X-Contabilidade-ID
        contabilidade_id = request.META.get('HTTP_X_CONTABILIDADE_ID')
        if contabilidade_id:
            try:
                from apps.core.models import Contabilidade
                return Contabilidade.objects.get(id=contabilidade_id)
            except Contabilidade.DoesNotExist:
                logger.warning(f"Contabilidade {contabilidade_id} não encontrada")
                return None
        
        # Tentar obter do parâmetro de query
        contabilidade_id = request.GET.get('contabilidade_id')
        if contabilidade_id:
            try:
                from apps.core.models import Contabilidade
                return Contabilidade.objects.get(id=contabilidade_id)
            except Contabilidade.DoesNotExist:
                logger.warning(f"Contabilidade {contabilidade_id} não encontrada")
                return None
        
        return None
    
    def verificar_acesso_contabilidade(self, user, contabilidade):
        """
        Verifica se o usuário tem acesso à contabilidade
        """
        try:
            from apps.core.models import UsuarioAcesso
            
            return UsuarioAcesso.objects.filter(
                usuario=user,
                contabilidade=contabilidade,
                ativo=True,
                data_inicio__lte=timezone.now().date(),
                data_fim__isnull=True
            ).exists() or UsuarioAcesso.objects.filter(
                usuario=user,
                contabilidade=contabilidade,
                ativo=True,
                data_inicio__lte=timezone.now().date(),
                data_fim__gte=timezone.now().date()
            ).exists()
            
        except Exception as e:
            logger.error(f"Erro ao verificar acesso à contabilidade: {e}")
            return False
    
    def atualizar_ultima_contabilidade(self, user, contabilidade):
        """
        Atualiza a última contabilidade acessada pelo usuário
        """
        try:
            if hasattr(user, 'ultima_contabilidade'):
                user.ultima_contabilidade = contabilidade
                user.save(update_fields=['ultima_contabilidade'])
        except Exception as e:
            logger.error(f"Erro ao atualizar última contabilidade: {e}")
    
    def get_primeira_contabilidade_acessivel(self, user):
        """
        Obtém a primeira contabilidade acessível pelo usuário
        """
        try:
            from apps.core.models import UsuarioAcesso
            
            acesso = UsuarioAcesso.objects.filter(
                usuario=user,
                ativo=True,
                data_inicio__lte=timezone.now().date(),
                data_fim__isnull=True
            ).first()
            
            if not acesso:
                acesso = UsuarioAcesso.objects.filter(
                    usuario=user,
                    ativo=True,
                    data_inicio__lte=timezone.now().date(),
                    data_fim__gte=timezone.now().date()
                ).first()
            
            return acesso.contabilidade if acesso else None
            
        except Exception as e:
            logger.error(f"Erro ao obter primeira contabilidade acessível: {e}")
            return None


class TenantAuditMiddleware(MiddlewareMixin):
    """
    Middleware para auditoria de trocas de tenant
    """
    
    def process_request(self, request):
        """
        Registra a troca de tenant para auditoria
        """
        if not request.user.is_authenticated:
            return
        
        # Verificar se houve troca de tenant
        if hasattr(request, 'contabilidade') and request.contabilidade:
            if hasattr(request.user, 'contabilidade') and request.user.contabilidade:
                if request.contabilidade != request.user.contabilidade:
                    self.registrar_troca_tenant(request.user, request.user.contabilidade, request.contabilidade)
    
    def registrar_troca_tenant(self, user, contabilidade_anterior, contabilidade_nova):
        """
        Registra a troca de tenant na auditoria
        """
        try:
            from apps.administracao.models import AuditoriaSistema
            
            AuditoriaSistema.objects.create(
                usuario=user,
                contabilidade=contabilidade_nova,
                acao='troca_tenant',
                tabela_afetada='core_usuarios',
                registro_id=str(user.id),
                dados_anteriores={
                    'contabilidade_id': str(contabilidade_anterior.id) if contabilidade_anterior else None,
                    'contabilidade_razao_social': contabilidade_anterior.razao_social if contabilidade_anterior else None
                },
                dados_novos={
                    'contabilidade_id': str(contabilidade_nova.id),
                    'contabilidade_razao_social': contabilidade_nova.razao_social
                },
                ip_address=self.get_client_ip(user)
            )
            
        except Exception as e:
            logger.error(f"Erro ao registrar troca de tenant: {e}")
    
    def get_client_ip(self, user):
        """
        Obtém o IP do cliente
        """
        # Implementar lógica para obter IP do request
        # Por enquanto, retornar None
        return None