"""
Filters para Contabilidades
"""

import django_filters
from django.db.models import Q

from apps.core.models import Contabilidade


class ContabilidadeFilter(django_filters.FilterSet):
    """
    Filtros customizados para Contabilidade
    
    Uso:
    GET /api/gestao/superuser/contabilidades/?ativo=true&data_inicio=2024-01-01
    """
    
    # Filtros básicos
    ativo = django_filters.BooleanFilter(
        field_name='ativo'
    )
    
    suspensa_por_inadimplencia = django_filters.BooleanFilter(
        field_name='suspensa_por_inadimplencia'
    )
    
    # Filtros de data
    data_inicio = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='gte',
        label='Data Início (maior ou igual)'
    )
    
    data_fim = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='lte',
        label='Data Fim (menor ou igual)'
    )
    
    # Filtros de saldo
    saldo_creditos_min = django_filters.NumberFilter(
        field_name='saldo_creditos',
        lookup_expr='gte'
    )
    
    saldo_creditos_max = django_filters.NumberFilter(
        field_name='saldo_creditos',
        lookup_expr='lte'
    )
    
    # Busca textual
    busca = django_filters.CharFilter(
        method='filter_busca',
        label='Busca geral'
    )
    
    class Meta:
        model = Contabilidade
        fields = {
            'razao_social': ['exact', 'icontains', 'istartswith'],
            'nome_fantasia': ['icontains'],
            'cnpj': ['exact', 'icontains'],
            'email': ['exact', 'icontains'],
            'created_at': ['exact', 'gte', 'lte', 'year', 'month'],
        }
    
    def filter_busca(self, queryset, name, value):
        """
        Busca em múltiplos campos
        
        Busca por: razão social, nome fantasia, CNPJ, email
        """
        return queryset.filter(
            Q(razao_social__icontains=value) |
            Q(nome_fantasia__icontains=value) |
            Q(cnpj__icontains=value) |
            Q(email__icontains=value)
        )
