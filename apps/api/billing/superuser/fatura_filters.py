"""
Filters para Faturas
"""

import django_filters
from django.db.models import Q
from django.utils import timezone

from apps.billing.models import Fatura


class FaturaFilter(django_filters.FilterSet):
    """
    FilterSet para Faturas com filtros customizados
    """
    
    # Filtros básicos
    status = django_filters.MultipleChoiceFilter(
        choices=Fatura.STATUS_CHOICES,
        help_text='Filtrar por status (aberta, paga, vencida, cancelada, estornada)'
    )
    
    assinatura = django_filters.UUIDFilter(
        field_name='assinatura__id',
        help_text='Filtrar por ID da assinatura'
    )
    
    contabilidade = django_filters.NumberFilter(
        field_name='assinatura__contabilidade__id',
        help_text='Filtrar por ID da contabilidade'
    )
    
    competencia = django_filters.CharFilter(
        lookup_expr='exact',
        help_text='Filtrar por competência (YYYY-MM)'
    )
    
    ano = django_filters.NumberFilter(
        method='filter_ano',
        help_text='Filtrar por ano'
    )
    
    mes = django_filters.NumberFilter(
        method='filter_mes',
        help_text='Filtrar por mês (1-12)'
    )
    
    # Filtros de data
    data_emissao_inicio = django_filters.DateFilter(
        field_name='data_emissao',
        lookup_expr='gte',
        help_text='Data de emissão >= (formato: YYYY-MM-DD)'
    )
    
    data_emissao_fim = django_filters.DateFilter(
        field_name='data_emissao',
        lookup_expr='lte',
        help_text='Data de emissão <= (formato: YYYY-MM-DD)'
    )
    
    data_vencimento_inicio = django_filters.DateFilter(
        field_name='data_vencimento',
        lookup_expr='gte',
        help_text='Data de vencimento >= (formato: YYYY-MM-DD)'
    )
    
    data_vencimento_fim = django_filters.DateFilter(
        field_name='data_vencimento',
        lookup_expr='lte',
        help_text='Data de vencimento <= (formato: YYYY-MM-DD)'
    )
    
    data_pagamento_inicio = django_filters.DateFilter(
        field_name='data_pagamento',
        lookup_expr='gte',
        help_text='Data de pagamento >= (formato: YYYY-MM-DD)'
    )
    
    data_pagamento_fim = django_filters.DateFilter(
        field_name='data_pagamento',
        lookup_expr='lte',
        help_text='Data de pagamento <= (formato: YYYY-MM-DD)'
    )
    
    # Filtros especiais
    vencida = django_filters.BooleanFilter(
        method='filter_vencida',
        help_text='Filtrar faturas vencidas (true/false)'
    )
    
    proximas_vencimento = django_filters.NumberFilter(
        method='filter_proximas_vencimento',
        help_text='Faturas vencendo nos próximos X dias'
    )
    
    pendente = django_filters.BooleanFilter(
        method='filter_pendente',
        help_text='Filtrar faturas pendentes (aberta + vencida)'
    )
    
    # Filtros de valores
    valor_min = django_filters.NumberFilter(
        field_name='valor_final',
        lookup_expr='gte',
        help_text='Valor final mínimo'
    )
    
    valor_max = django_filters.NumberFilter(
        field_name='valor_final',
        lookup_expr='lte',
        help_text='Valor final máximo'
    )
    
    # Busca textual
    busca = django_filters.CharFilter(
        method='filter_busca',
        help_text='Buscar em número da fatura, razão social da contabilidade'
    )
    
    class Meta:
        model = Fatura
        fields = []
    
    def filter_ano(self, queryset, name, value):
        """Filtrar por ano"""
        if not value:
            return queryset
        
        return queryset.filter(competencia__startswith=str(value))
    
    def filter_mes(self, queryset, name, value):
        """Filtrar por mês"""
        if not value or value < 1 or value > 12:
            return queryset
        
        mes_str = str(value).zfill(2)
        return queryset.filter(competencia__endswith=mes_str)
    
    def filter_vencida(self, queryset, name, value):
        """Filtrar faturas vencidas"""
        hoje = timezone.now().date()
        
        if value:
            # Faturas vencidas (data_vencimento < hoje e status aberta/vencida)
            return queryset.filter(
                data_vencimento__lt=hoje,
                status__in=['aberta', 'vencida']
            )
        else:
            # Faturas não vencidas
            return queryset.filter(
                Q(data_vencimento__gte=hoje) |
                Q(status__in=['paga', 'cancelada', 'estornada'])
            )
    
    def filter_proximas_vencimento(self, queryset, name, value):
        """Filtrar faturas próximas do vencimento"""
        if not value:
            return queryset
        
        hoje = timezone.now().date()
        data_limite = hoje + timezone.timedelta(days=value)
        
        return queryset.filter(
            data_vencimento__gte=hoje,
            data_vencimento__lte=data_limite,
            status='aberta'
        )
    
    def filter_pendente(self, queryset, name, value):
        """Filtrar faturas pendentes"""
        if value:
            return queryset.filter(status__in=['aberta', 'vencida'])
        else:
            return queryset.exclude(status__in=['aberta', 'vencida'])
    
    def filter_busca(self, queryset, name, value):
        """Buscar em múltiplos campos"""
        if not value:
            return queryset
        
        return queryset.filter(
            Q(numero_fatura__icontains=value) |
            Q(assinatura__contabilidade__razao_social__icontains=value) |
            Q(competencia__icontains=value)
        )
