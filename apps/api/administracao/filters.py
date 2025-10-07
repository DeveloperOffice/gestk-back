"""
Filtros para API de Administração
"""

import django_filters
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta

from apps.administracao.models import ContratoGestk
from apps.core.models import UsuarioAcesso, Contabilidade


class ContratoGestkFilter(django_filters.FilterSet):
    """
    Filtros para Contratos GESTK
    """
    contabilidade = django_filters.UUIDFilter(field_name='contabilidade__id')
    numero_contrato = django_filters.CharFilter(lookup_expr='icontains')
    plano_servico = django_filters.CharFilter(lookup_expr='icontains')
    status = django_filters.ChoiceFilter(choices=ContratoGestk.STATUS_CHOICES)
    
    # Filtros de data
    data_inicio_apos = django_filters.DateFilter(field_name='data_inicio', lookup_expr='gte')
    data_inicio_antes = django_filters.DateFilter(field_name='data_inicio', lookup_expr='lte')
    data_termino_apos = django_filters.DateFilter(field_name='data_termino', lookup_expr='gte')
    data_termino_antes = django_filters.DateFilter(field_name='data_termino', lookup_expr='lte')
    
    # Filtros de valor
    valor_min = django_filters.NumberFilter(field_name='valor_mensal', lookup_expr='gte')
    valor_max = django_filters.NumberFilter(field_name='valor_mensal', lookup_expr='lte')
    
    # Filtros especiais
    ativo = django_filters.BooleanFilter(method='filter_ativo')
    vencido = django_filters.BooleanFilter(method='filter_vencido')
    em_trial = django_filters.BooleanFilter(method='filter_em_trial')
    vence_em_dias = django_filters.NumberFilter(method='filter_vence_em_dias')
    
    class Meta:
        model = ContratoGestk
        fields = [
            'contabilidade', 'numero_contrato', 'plano_servico', 'status',
            'data_inicio_apos', 'data_inicio_antes', 'data_termino_apos', 'data_termino_antes',
            'valor_min', 'valor_max', 'ativo', 'vencido', 'em_trial', 'vence_em_dias'
        ]
    
    def filter_ativo(self, queryset, name, value):
        """
        Filtra contratos ativos
        """
        if value:
            return queryset.filter(status='ativo')
        return queryset.exclude(status='ativo')
    
    def filter_vencido(self, queryset, name, value):
        """
        Filtra contratos vencidos
        """
        if value:
            return queryset.filter(
                data_termino__isnull=False,
                data_termino__lt=timezone.now().date()
            )
        return queryset.exclude(
            data_termino__isnull=False,
            data_termino__lt=timezone.now().date()
        )
    
    def filter_em_trial(self, queryset, name, value):
        """
        Filtra contratos em período de teste
        """
        if value:
            return queryset.filter(
                trial_ate__isnull=False,
                trial_ate__gte=timezone.now().date()
            )
        return queryset.exclude(
            trial_ate__isnull=False,
            trial_ate__gte=timezone.now().date()
        )
    
    def filter_vence_em_dias(self, queryset, name, value):
        """
        Filtra contratos que vencem em X dias
        """
        if value is not None:
            data_limite = timezone.now().date() + timedelta(days=value)
            return queryset.filter(
                data_termino__isnull=False,
                data_termino__lte=data_limite,
                data_termino__gte=timezone.now().date()
            )
        return queryset


class UsuarioAcessoFilter(django_filters.FilterSet):
    """
    Filtros para Acessos de Usuário
    """
    usuario = django_filters.UUIDFilter(field_name='usuario__id')
    contabilidade = django_filters.UUIDFilter(field_name='contabilidade__id')
    contrato = django_filters.UUIDFilter(field_name='contrato__id')
    role = django_filters.ChoiceFilter(choices=UsuarioAcesso.ROLE_CHOICES)
    
    # Filtros de data
    data_inicio_apos = django_filters.DateFilter(field_name='data_inicio', lookup_expr='gte')
    data_inicio_antes = django_filters.DateFilter(field_name='data_inicio', lookup_expr='lte')
    data_fim_apos = django_filters.DateFilter(field_name='data_fim', lookup_expr='gte')
    data_fim_antes = django_filters.DateFilter(field_name='data_fim', lookup_expr='lte')
    
    # Filtros especiais
    ativo = django_filters.BooleanFilter(field_name='ativo')
    vencido = django_filters.BooleanFilter(method='filter_vencido')
    mfa_required = django_filters.BooleanFilter(field_name='mfa_required')
    
    class Meta:
        model = UsuarioAcesso
        fields = [
            'usuario', 'contabilidade', 'contrato', 'role', 'ativo', 'mfa_required',
            'data_inicio_apos', 'data_inicio_antes', 'data_fim_apos', 'data_fim_antes',
            'vencido'
        ]
    
    def filter_vencido(self, queryset, name, value):
        """
        Filtra acessos vencidos
        """
        if value:
            return queryset.filter(
                data_fim__isnull=False,
                data_fim__lt=timezone.now().date()
            )
        return queryset.exclude(
            data_fim__isnull=False,
            data_fim__lt=timezone.now().date()
        )


class ContabilidadeAdministracaoFilter(django_filters.FilterSet):
    """
    Filtros para Contabilidades com informações de administração
    """
    razao_social = django_filters.CharFilter(lookup_expr='icontains')
    nome_fantasia = django_filters.CharFilter(lookup_expr='icontains')
    cnpj = django_filters.CharFilter(lookup_expr='icontains')
    ativo = django_filters.BooleanFilter()
    suspensa_por_inadimplencia = django_filters.BooleanFilter()
    
    # Filtros especiais
    com_contrato = django_filters.BooleanFilter(method='filter_com_contrato')
    sem_contrato = django_filters.BooleanFilter(method='filter_sem_contrato')
    com_usuarios = django_filters.BooleanFilter(method='filter_com_usuarios')
    sem_usuarios = django_filters.BooleanFilter(method='filter_sem_usuarios')
    
    class Meta:
        model = Contabilidade
        fields = [
            'razao_social', 'nome_fantasia', 'cnpj', 'ativo', 'suspensa_por_inadimplencia',
            'com_contrato', 'sem_contrato', 'com_usuarios', 'sem_usuarios'
        ]
    
    def filter_com_contrato(self, queryset, name, value):
        """
        Filtra contabilidades com contrato GESTK
        """
        if value:
            return queryset.filter(contrato_gestk__isnull=False).distinct()
        return queryset.filter(contrato_gestk__isnull=True)
    
    def filter_sem_contrato(self, queryset, name, value):
        """
        Filtra contabilidades sem contrato GESTK
        """
        if value:
            return queryset.filter(contrato_gestk__isnull=True)
        return queryset.filter(contrato_gestk__isnull=False).distinct()
    
    def filter_com_usuarios(self, queryset, name, value):
        """
        Filtra contabilidades com usuários
        """
        if value:
            return queryset.filter(acessos_usuarios__isnull=False).distinct()
        return queryset.filter(acessos_usuarios__isnull=True)
    
    def filter_sem_usuarios(self, queryset, name, value):
        """
        Filtra contabilidades sem usuários
        """
        if value:
            return queryset.filter(acessos_usuarios__isnull=True)
        return queryset.filter(acessos_usuarios__isnull=False).distinct()