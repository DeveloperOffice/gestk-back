"""
Filtros para Dashboard Demográfico
"""
import django_filters
from apps.funcionarios.models import VinculoEmpregaticio


class VinculoEmpregaticioFilterSet(django_filters.FilterSet):
    """Filtros para vínculos empregatícios"""
    
    # Filtros por data
    data_admissao_inicio = django_filters.DateFilter(
        field_name='data_admissao',
        lookup_expr='gte',
        label='Data de admissão (início)'
    )
    data_admissao_fim = django_filters.DateFilter(
        field_name='data_admissao',
        lookup_expr='lte',
        label='Data de admissão (fim)'
    )
    
    # Filtros por empresa
    empresa = django_filters.UUIDFilter(
        field_name='empresa_id',
        label='Empresa'
    )
    
    # Filtros por cargo/departamento
    cargo = django_filters.UUIDFilter(
        field_name='cargo_id',
        label='Cargo'
    )
    departamento = django_filters.UUIDFilter(
        field_name='departamento_id',
        label='Departamento'
    )
    
    # Filtro por status
    ativo = django_filters.BooleanFilter(
        field_name='ativo',
        label='Ativo'
    )
    
    class Meta:
        model = VinculoEmpregaticio
        fields = ['empresa', 'cargo', 'departamento', 'ativo']
