"""
Filters para Assinaturas
"""

import django_filters
from django.db.models import Q
from django.utils import timezone

from apps.billing.models import Assinatura


class AssinaturaFilter(django_filters.FilterSet):
    """
    FilterSet para Assinaturas com filtros customizados
    """
    
    # Filtros básicos
    status = django_filters.MultipleChoiceFilter(
        choices=Assinatura.STATUS_CHOICES,
        help_text='Filtrar por status (ativa, suspensa, cancelada, expirada, trial)'
    )
    
    ciclo_cobranca = django_filters.MultipleChoiceFilter(
        choices=[
            ('mensal', 'Mensal'),
            ('anual', 'Anual'),
            ('trimestral', 'Trimestral'),
            ('semestral', 'Semestral'),
        ],
        help_text='Filtrar por ciclo de cobrança'
    )
    
    contabilidade = django_filters.NumberFilter(
        field_name='contabilidade__id',
        help_text='Filtrar por ID da contabilidade'
    )
    
    plano = django_filters.UUIDFilter(
        field_name='plano__id',
        help_text='Filtrar por ID do plano'
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
    
    data_fim_inicio = django_filters.DateFilter(
        field_name='data_fim',
        lookup_expr='gte',
        help_text='Data de fim >= (formato: YYYY-MM-DD)'
    )
    
    data_fim_fim = django_filters.DateFilter(
        field_name='data_fim',
        lookup_expr='lte',
        help_text='Data de fim <= (formato: YYYY-MM-DD)'
    )
    
    # Filtros especiais
    em_trial = django_filters.BooleanFilter(
        method='filter_em_trial',
        help_text='Filtrar assinaturas em período trial (true/false)'
    )
    
    proximas_vencimento = django_filters.NumberFilter(
        method='filter_proximas_vencimento',
        help_text='Assinaturas vencendo nos próximos X dias'
    )
    
    expirada = django_filters.BooleanFilter(
        method='filter_expirada',
        help_text='Filtrar assinaturas expiradas (true/false)'
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
        help_text='Buscar em razão social da contabilidade, nome do plano'
    )
    
    class Meta:
        model = Assinatura
        fields = []
    
    def filter_em_trial(self, queryset, name, value):
        """Filtrar assinaturas em período trial"""
        hoje = timezone.now().date()
        
        if value:
            # Assinaturas em trial (trial_ate >= hoje)
            return queryset.filter(trial_ate__gte=hoje)
        else:
            # Assinaturas fora de trial
            return queryset.filter(
                Q(trial_ate__lt=hoje) |
                Q(trial_ate__isnull=True)
            )
    
    def filter_proximas_vencimento(self, queryset, name, value):
        """Filtrar assinaturas próximas do vencimento"""
        if not value:
            return queryset
        
        hoje = timezone.now().date()
        data_limite = hoje + timezone.timedelta(days=value)
        
        return queryset.filter(
            data_fim__gte=hoje,
            data_fim__lte=data_limite,
            status='ativa'
        )
    
    def filter_expirada(self, queryset, name, value):
        """Filtrar assinaturas expiradas"""
        hoje = timezone.now().date()
        
        if value:
            # Assinaturas expiradas (data_fim < hoje)
            return queryset.filter(data_fim__lt=hoje)
        else:
            # Assinaturas não expiradas
            return queryset.filter(
                Q(data_fim__gte=hoje) |
                Q(data_fim__isnull=True)
            )
    
    def filter_busca(self, queryset, name, value):
        """Buscar em múltiplos campos"""
        if not value:
            return queryset
        
        return queryset.filter(
            Q(contabilidade__razao_social__icontains=value) |
            Q(plano__nome__icontains=value) |
            Q(plano__codigo__icontains=value)
        )
