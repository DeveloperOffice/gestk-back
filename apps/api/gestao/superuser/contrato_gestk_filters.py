"""
Filters para Contratos GESTK
"""

import django_filters
from django.db.models import Q
from django.utils import timezone

from apps.administracao.models import ContratoGestk


class ContratoGestkFilter(django_filters.FilterSet):
    """
    FilterSet para Contratos GESTK com filtros customizados
    """
    
    # Filtros básicos
    status = django_filters.MultipleChoiceFilter(
        choices=ContratoGestk.STATUS_CHOICES,
        help_text='Filtrar por status (trial, ativo, suspenso, cancelado, vencido)'
    )
    
    plano_servico = django_filters.CharFilter(
        lookup_expr='icontains',
        help_text='Filtrar por plano de serviço'
    )
    
    contabilidade = django_filters.NumberFilter(
        field_name='contabilidade__id',
        help_text='Filtrar por ID da contabilidade'
    )
    
    # Filtros de data
    data_inicio_inicio = django_filters.DateFilter(
        field_name='data_inicio',
        lookup_expr='gte',
        help_text='Data de início >= (formato: YYYY-MM-DD)'
    )
    
    data_inicio_fim = django_filters.DateFilter(
        field_name='data_inicio',
        lookup_expr='lte',
        help_text='Data de início <= (formato: YYYY-MM-DD)'
    )
    
    data_termino_inicio = django_filters.DateFilter(
        field_name='data_termino',
        lookup_expr='gte',
        help_text='Data de término >= (formato: YYYY-MM-DD)'
    )
    
    data_termino_fim = django_filters.DateFilter(
        field_name='data_termino',
        lookup_expr='lte',
        help_text='Data de término <= (formato: YYYY-MM-DD)'
    )
    
    # Filtros especiais
    em_trial = django_filters.BooleanFilter(
        method='filter_em_trial',
        help_text='Filtrar contratos em período trial (true/false)'
    )
    
    proximos_vencimento = django_filters.NumberFilter(
        method='filter_proximos_vencimento',
        help_text='Contratos vencendo nos próximos X dias'
    )
    
    vencido = django_filters.BooleanFilter(
        method='filter_vencido',
        help_text='Filtrar contratos vencidos (true/false)'
    )
    
    # Filtros de valores
    valor_mensal_min = django_filters.NumberFilter(
        field_name='valor_mensal',
        lookup_expr='gte',
        help_text='Valor mensal mínimo'
    )
    
    valor_mensal_max = django_filters.NumberFilter(
        field_name='valor_mensal',
        lookup_expr='lte',
        help_text='Valor mensal máximo'
    )
    
    # Busca textual
    busca = django_filters.CharFilter(
        method='filter_busca',
        help_text='Buscar em número de contrato, razão social da contabilidade'
    )
    
    class Meta:
        model = ContratoGestk
        fields = []
    
    def filter_em_trial(self, queryset, name, value):
        """Filtrar contratos em período trial"""
        hoje = timezone.now().date()
        
        if value:
            # Contratos em trial (trial_ate >= hoje)
            return queryset.filter(trial_ate__gte=hoje)
        else:
            # Contratos fora de trial (trial_ate < hoje ou sem trial)
            return queryset.filter(
                Q(trial_ate__lt=hoje) |
                Q(trial_ate__isnull=True)
            )
    
    def filter_proximos_vencimento(self, queryset, name, value):
        """Filtrar contratos próximos do vencimento"""
        if not value:
            return queryset
        
        hoje = timezone.now().date()
        data_limite = hoje + timezone.timedelta(days=value)
        
        return queryset.filter(
            data_termino__gte=hoje,
            data_termino__lte=data_limite,
            status='ativo'
        )
    
    def filter_vencido(self, queryset, name, value):
        """Filtrar contratos vencidos"""
        hoje = timezone.now().date()
        
        if value:
            # Contratos vencidos (data_termino < hoje)
            return queryset.filter(data_termino__lt=hoje)
        else:
            # Contratos não vencidos (data_termino >= hoje ou sem data)
            return queryset.filter(
                Q(data_termino__gte=hoje) |
                Q(data_termino__isnull=True)
            )
    
    def filter_busca(self, queryset, name, value):
        """Buscar em múltiplos campos"""
        if not value:
            return queryset
        
        return queryset.filter(
            Q(numero_contrato__icontains=value) |
            Q(contabilidade__razao_social__icontains=value) |
            Q(plano_servico__icontains=value)
        )
