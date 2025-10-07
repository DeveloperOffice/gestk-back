"""
Permissões Customizadas para API REST

Implementa permissões baseadas em contabilidade e Regra de Ouro
Atualizado para suportar multi-tenant com UsuarioAcesso
"""

from rest_framework import permissions
from django.core.exceptions import PermissionDenied
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class IsContabilidadeOwner(permissions.BasePermission):
    """
    Permissão que verifica se o usuário pertence à contabilidade do objeto
    """
    
    def has_permission(self, request, view):
        """
        Verifica se o usuário tem permissão para acessar a view
        """
        if not request.user.is_authenticated:
            return False
        
        # Verificar se o usuário tem contabilidade
        if not hasattr(request.user, 'contabilidade') or not request.user.contabilidade:
            return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """
        Verifica se o usuário tem permissão para acessar o objeto
        """
        if not request.user.is_authenticated:
            return False
        
        # Verificar se o objeto tem campo contabilidade
        if not hasattr(obj, 'contabilidade'):
            return True
        
        # Verificar se a contabilidade do objeto é a mesma do usuário
        return obj.contabilidade == request.user.contabilidade


class IsContabilidadeOwnerOrReadOnly(permissions.BasePermission):
    """
    Permissão que permite leitura para todos e escrita apenas para donos da contabilidade
    """
    
    def has_permission(self, request, view):
        """
        Verifica se o usuário tem permissão para acessar a view
        """
        if not request.user.is_authenticated:
            return False
        
        # Verificar se o usuário tem contabilidade
        if not hasattr(request.user, 'contabilidade') or not request.user.contabilidade:
            return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """
        Verifica se o usuário tem permissão para acessar o objeto
        """
        if not request.user.is_authenticated:
            return False
        
        # Verificar se o objeto tem campo contabilidade
        if not hasattr(obj, 'contabilidade'):
            return True
        
        # Leitura sempre permitida
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Escrita apenas para donos da contabilidade
        return obj.contabilidade == request.user.contabilidade


class IsSuperUserOrContabilidadeOwner(permissions.BasePermission):
    """
    Permissão que permite acesso para superusuários ou donos da contabilidade
    """
    
    def has_permission(self, request, view):
        """
        Verifica se o usuário tem permissão para acessar a view
        """
        if not request.user.is_authenticated:
            return False
        
        # Superusuários têm acesso total
        if request.user.is_superuser:
            return True
        
        # Verificar se o usuário tem contabilidade
        if not hasattr(request.user, 'contabilidade') or not request.user.contabilidade:
            return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """
        Verifica se o usuário tem permissão para acessar o objeto
        """
        if not request.user.is_authenticated:
            return False
        
        # Superusuários têm acesso total
        if request.user.is_superuser:
            return True
        
        # Verificar se o objeto tem campo contabilidade
        if not hasattr(obj, 'contabilidade'):
            return True
        
        # Verificar se a contabilidade do objeto é a mesma do usuário
        return obj.contabilidade == request.user.contabilidade


class IsContabilidadeActive(permissions.BasePermission):
    """
    Permissão que verifica se a contabilidade está ativa
    """
    
    def has_permission(self, request, view):
        """
        Verifica se a contabilidade do usuário está ativa
        """
        if not request.user.is_authenticated:
            return False
        
        # Verificar se o usuário tem contabilidade
        if not hasattr(request.user, 'contabilidade') or not request.user.contabilidade:
            return False
        
        # Verificar se a contabilidade está ativa
        return request.user.contabilidade.ativo


class RegraOuroPermission(permissions.BasePermission):
    """
    Permissão que aplica a Regra de Ouro para validação de acesso
    """
    
    def has_permission(self, request, view):
        """
        Verifica se o usuário tem permissão baseada na Regra de Ouro
        """
        if not request.user.is_authenticated:
            return False
        
        # Verificar se o usuário tem contabilidade
        if not hasattr(request.user, 'contabilidade') or not request.user.contabilidade:
            return False
        
        # Aplicar Regra de Ouro se necessário
        if hasattr(request, 'contabilidade') and request.contabilidade:
            # Verificar se a contabilidade foi alterada pela Regra de Ouro
            if request.contabilidade != request.user.contabilidade:
                # Verificar se o usuário tem acesso à nova contabilidade
                return self.verificar_acesso_contabilidade(request.user, request.contabilidade)
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """
        Verifica se o usuário tem permissão para acessar o objeto baseado na Regra de Ouro
        """
        if not request.user.is_authenticated:
            return False
        
        # Verificar se o objeto tem campo contabilidade
        if not hasattr(obj, 'contabilidade'):
            return True
        
        # Aplicar Regra de Ouro
        contabilidade = getattr(request, 'contabilidade', request.user.contabilidade)
        
        if contabilidade != request.user.contabilidade:
            # Verificar se o usuário tem acesso à contabilidade da Regra de Ouro
            return self.verificar_acesso_contabilidade(request.user, contabilidade)
        
        return obj.contabilidade == contabilidade
    
    def verificar_acesso_contabilidade(self, user, contabilidade):
        """
        Verifica se o usuário tem acesso à contabilidade
        """
        try:
            # Verificar se o usuário tem vínculo com a contabilidade via UsuarioAcesso
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


class IsMultiTenantUser(permissions.BasePermission):
    """
    Permissão que verifica se o usuário tem acesso multi-tenant
    """
    
    def has_permission(self, request, view):
        """
        Verifica se o usuário tem permissão para acessar a view
        """
        if not request.user.is_authenticated:
            return False
        
        # Superusuários têm acesso total
        if request.user.is_superuser:
            return True
        
        # Verificar se o usuário tem pelo menos um acesso ativo
        from apps.core.models import UsuarioAcesso
        
        return UsuarioAcesso.objects.filter(
            usuario=request.user,
            ativo=True,
            data_inicio__lte=timezone.now().date(),
            data_fim__isnull=True
        ).exists() or UsuarioAcesso.objects.filter(
            usuario=request.user,
            ativo=True,
            data_inicio__lte=timezone.now().date(),
            data_fim__gte=timezone.now().date()
        ).exists()


class IsAdminOrContabilidadeOwner(permissions.BasePermission):
    """
    Permissão que permite acesso para administradores ou donos da contabilidade
    """
    
    def has_permission(self, request, view):
        """
        Verifica se o usuário tem permissão para acessar a view
        """
        if not request.user.is_authenticated:
            return False
        
        # Superusuários e administradores têm acesso total
        if request.user.is_superuser or request.user.tipo_usuario in ['superuser', 'admin']:
            return True
        
        # Verificar se o usuário tem contabilidade
        if not hasattr(request.user, 'contabilidade') or not request.user.contabilidade:
            return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """
        Verifica se o usuário tem permissão para acessar o objeto
        """
        if not request.user.is_authenticated:
            return False
        
        # Superusuários e administradores têm acesso total
        if request.user.is_superuser or request.user.tipo_usuario in ['superuser', 'admin']:
            return True
        
        # Verificar se o objeto tem campo contabilidade
        if not hasattr(obj, 'contabilidade'):
            return True
        
        # Verificar se a contabilidade do objeto é a mesma do usuário
        return obj.contabilidade == request.user.contabilidade


class IsContabilidadeAccessible(permissions.BasePermission):
    """
    Permissão que verifica se o usuário tem acesso à contabilidade específica
    """
    
    def has_permission(self, request, view):
        """
        Verifica se o usuário tem permissão para acessar a view
        """
        if not request.user.is_authenticated:
            return False
        
        # Superusuários têm acesso total
        if request.user.is_superuser:
            return True
        
        # Obter contabilidade do contexto (pode vir do header, parâmetro, etc.)
        contabilidade_id = self.get_contabilidade_from_request(request)
        if not contabilidade_id:
            return False
        
        # Verificar se o usuário tem acesso à contabilidade
        return self.verificar_acesso_contabilidade(request.user, contabilidade_id)
    
    def has_object_permission(self, request, view, obj):
        """
        Verifica se o usuário tem permissão para acessar o objeto
        """
        if not request.user.is_authenticated:
            return False
        
        # Superusuários têm acesso total
        if request.user.is_superuser:
            return True
        
        # Verificar se o objeto tem campo contabilidade
        if not hasattr(obj, 'contabilidade'):
            return True
        
        # Verificar se o usuário tem acesso à contabilidade do objeto
        return self.verificar_acesso_contabilidade(request.user, obj.contabilidade)
    
    def get_contabilidade_from_request(self, request):
        """
        Extrai o ID da contabilidade do request
        """
        # Tentar obter do header X-Contabilidade-ID
        contabilidade_id = request.META.get('HTTP_X_CONTABILIDADE_ID')
        if contabilidade_id:
            return contabilidade_id
        
        # Tentar obter do parâmetro de query
        contabilidade_id = request.query_params.get('contabilidade_id')
        if contabilidade_id:
            return contabilidade_id
        
        # Usar a contabilidade padrão do usuário
        if hasattr(request.user, 'contabilidade') and request.user.contabilidade:
            return request.user.contabilidade.id
        
        return None
    
    def verificar_acesso_contabilidade(self, user, contabilidade_id):
        """
        Verifica se o usuário tem acesso à contabilidade
        """
        try:
            from apps.core.models import UsuarioAcesso, Contabilidade
            
            # Se contabilidade_id é uma string UUID, converter
            if isinstance(contabilidade_id, str):
                contabilidade = Contabilidade.objects.get(id=contabilidade_id)
            else:
                contabilidade = contabilidade_id
            
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


class IsScopeAccessible(permissions.BasePermission):
    """
    Permissão que verifica se o usuário tem acesso ao escopo específico (contrato/empresa)
    """
    
    def has_permission(self, request, view):
        """
        Verifica se o usuário tem permissão para acessar a view
        """
        if not request.user.is_authenticated:
            return False
        
        # Superusuários têm acesso total
        if request.user.is_superuser:
            return True
        
        # Obter contabilidade e escopo do contexto
        contabilidade_id = self.get_contabilidade_from_request(request)
        contrato_id = self.get_contrato_from_request(request)
        empresa_cnpj = self.get_empresa_from_request(request)
        
        if not contabilidade_id:
            return False
        
        # Verificar se o usuário tem acesso ao escopo
        return self.verificar_acesso_escopo(request.user, contabilidade_id, contrato_id, empresa_cnpj)
    
    def has_object_permission(self, request, view, obj):
        """
        Verifica se o usuário tem permissão para acessar o objeto
        """
        if not request.user.is_authenticated:
            return False
        
        # Superusuários têm acesso total
        if request.user.is_superuser:
            return True
        
        # Verificar se o objeto tem campo contabilidade
        if not hasattr(obj, 'contabilidade'):
            return True
        
        # Obter escopo do objeto
        contrato_id = getattr(obj, 'contrato_id', None) if hasattr(obj, 'contrato_id') else None
        empresa_cnpj = getattr(obj, 'empresa_cnpj', None) if hasattr(obj, 'empresa_cnpj') else None
        
        # Verificar se o usuário tem acesso ao escopo
        return self.verificar_acesso_escopo(request.user, obj.contabilidade, contrato_id, empresa_cnpj)
    
    def get_contabilidade_from_request(self, request):
        """
        Extrai o ID da contabilidade do request
        """
        contabilidade_id = request.META.get('HTTP_X_CONTABILIDADE_ID')
        if contabilidade_id:
            return contabilidade_id
        
        contabilidade_id = request.query_params.get('contabilidade_id')
        if contabilidade_id:
            return contabilidade_id
        
        if hasattr(request.user, 'contabilidade') and request.user.contabilidade:
            return request.user.contabilidade.id
        
        return None
    
    def get_contrato_from_request(self, request):
        """
        Extrai o ID do contrato do request
        """
        return request.query_params.get('contrato_id')
    
    def get_empresa_from_request(self, request):
        """
        Extrai o CNPJ da empresa do request
        """
        return request.query_params.get('empresa_cnpj')
    
    def verificar_acesso_escopo(self, user, contabilidade_id, contrato_id=None, empresa_cnpj=None):
        """
        Verifica se o usuário tem acesso ao escopo específico
        """
        try:
            from apps.core.models import UsuarioAcesso, Contabilidade
            
            # Se contabilidade_id é uma string UUID, converter
            if isinstance(contabilidade_id, str):
                contabilidade = Contabilidade.objects.get(id=contabilidade_id)
            else:
                contabilidade = contabilidade_id
            
            # Buscar acessos do usuário para esta contabilidade
            acessos = UsuarioAcesso.objects.filter(
                usuario=user,
                contabilidade=contabilidade,
                ativo=True,
                data_inicio__lte=timezone.now().date(),
                data_fim__isnull=True
            ) | UsuarioAcesso.objects.filter(
                usuario=user,
                contabilidade=contabilidade,
                ativo=True,
                data_inicio__lte=timezone.now().date(),
                data_fim__gte=timezone.now().date()
            )
            
            # Se não há acessos, negar
            if not acessos.exists():
                return False
            
            # Verificar se algum acesso permite o escopo
            for acesso in acessos:
                # Se o acesso não tem restrição de escopo, permite tudo
                if not acesso.contrato and not acesso.empresa_cnpj:
                    return True
                
                # Verificar restrição por contrato
                if contrato_id and acesso.contrato:
                    if str(acesso.contrato.id) == str(contrato_id):
                        return True
                
                # Verificar restrição por empresa
                if empresa_cnpj and acesso.empresa_cnpj:
                    if acesso.empresa_cnpj == empresa_cnpj:
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao verificar acesso ao escopo: {e}")
            return False
