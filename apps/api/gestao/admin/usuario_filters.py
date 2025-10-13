"""
Filters para gerenciamento de Usuarios por ADMIN
"""
import django_filters
from django.db.models import Q
from apps.core.models import Usuario


class UsuarioFilter(django_filters.FilterSet):
    """Filtros para usuários"""
    
    # Filtros básicos
    ativo = django_filters.BooleanFilter(field_name='ativo')
    is_active = django_filters.BooleanFilter(field_name='is_active')
    tipo_usuario = django_filters.ChoiceFilter(
        field_name='tipo_usuario',
        choices=Usuario.TIPO_USUARIO_CHOICES
    )
    contabilidade = django_filters.UUIDFilter(field_name='contabilidade__id')
    
    # Filtros de permissões
    pode_executar_etl = django_filters.BooleanFilter(field_name='pode_executar_etl')
    pode_administrar_usuarios = django_filters.BooleanFilter(field_name='pode_administrar_usuarios')
    pode_ver_dados_sensiveis = django_filters.BooleanFilter(field_name='pode_ver_dados_sensiveis')
    mfa_enabled = django_filters.BooleanFilter(field_name='mfa_enabled')
    
    # Filtro por módulo acessível
    modulo = django_filters.CharFilter(method='filter_modulo')
    
    # Filtro de data de cadastro
    cadastrado_apos = django_filters.DateFilter(
        field_name='date_joined',
        lookup_expr='gte'
    )
    cadastrado_antes = django_filters.DateFilter(
        field_name='date_joined',
        lookup_expr='lte'
    )
    
    # Filtro de último login
    ultimo_login_apos = django_filters.DateFilter(
        field_name='last_login',
        lookup_expr='gte'
    )
    ultimo_login_antes = django_filters.DateFilter(
        field_name='last_login',
        lookup_expr='lte'
    )
    
    # Filtro por atividade
    sem_login = django_filters.BooleanFilter(method='filter_sem_login')
    
    # Busca textual
    busca = django_filters.CharFilter(method='filter_busca')
    
    class Meta:
        model = Usuario
        fields = []
    
    def filter_modulo(self, queryset, name, value):
        """Filtra usuários que têm acesso a um módulo específico"""
        return queryset.filter(
            modulos_acessiveis__contains=[value]
        )
    
    def filter_sem_login(self, queryset, name, value):
        """Filtra usuários que nunca fizeram login"""
        if value:
            return queryset.filter(last_login__isnull=True)
        else:
            return queryset.filter(last_login__isnull=False)
    
    def filter_busca(self, queryset, name, value):
        """
        Busca textual em múltiplos campos
        """
        return queryset.filter(
            Q(username__icontains=value) |
            Q(email__icontains=value) |
            Q(first_name__icontains=value) |
            Q(last_name__icontains=value) |
            Q(cpf__icontains=value) |
            Q(contabilidade__razao_social__icontains=value) |
            Q(contabilidade__cnpj__icontains=value)
        ).distinct()
