"""
Filters para gerenciamento de Contratos (Clientes) por ADMIN
"""
import django_filters
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from apps.pessoas.models import Contrato, PessoaJuridica, PessoaFisica


class ContratoFilter(django_filters.FilterSet):
    """Filtros para contratos"""
    
    # Filtros básicos
    ativo = django_filters.BooleanFilter(field_name='ativo')
    status_cobranca = django_filters.ChoiceFilter(
        field_name='status_cobranca',
        choices=[
            ('ativo', 'Ativo'),
            ('inativo', 'Inativo'),
            ('suspenso', 'Suspenso'),
            ('cancelado', 'Cancelado')
        ]
    )
    contabilidade = django_filters.UUIDFilter(field_name='contabilidade__id')
    plano_servico = django_filters.CharFilter(field_name='plano_servico', lookup_expr='icontains')
    
    # Filtros de datas
    data_inicio_apos = django_filters.DateFilter(
        field_name='data_inicio',
        lookup_expr='gte'
    )
    data_inicio_antes = django_filters.DateFilter(
        field_name='data_inicio',
        lookup_expr='lte'
    )
    data_termino_apos = django_filters.DateFilter(
        field_name='data_termino',
        lookup_expr='gte'
    )
    data_termino_antes = django_filters.DateFilter(
        field_name='data_termino',
        lookup_expr='lte'
    )
    
    # Filtros de valores
    valor_honorario_min = django_filters.NumberFilter(
        field_name='valor_honorario',
        lookup_expr='gte'
    )
    valor_honorario_max = django_filters.NumberFilter(
        field_name='valor_honorario',
        lookup_expr='lte'
    )
    
    # Filtros especiais
    vencendo = django_filters.BooleanFilter(method='filter_vencendo')
    vencido = django_filters.BooleanFilter(method='filter_vencido')
    sem_data_termino = django_filters.BooleanFilter(method='filter_sem_data_termino')
    
    # Filtro por tipo de cliente
    tipo_cliente = django_filters.ChoiceFilter(
        method='filter_tipo_cliente',
        choices=[
            ('PJ', 'Pessoa Jurídica'),
            ('PF', 'Pessoa Física')
        ]
    )
    
    # Filtro por módulo contratado
    modulo = django_filters.CharFilter(method='filter_modulo')
    
    # Busca textual (busca no nome/razão social do cliente)
    busca = django_filters.CharFilter(method='filter_busca')
    
    class Meta:
        model = Contrato
        fields = []
    
    def filter_vencendo(self, queryset, name, value):
        """Filtra contratos que vencem nos próximos 30 dias"""
        if value:
            from django.utils import timezone
            hoje = timezone.now().date()
            proximos_30_dias = hoje + timezone.timedelta(days=30)
            return queryset.filter(
                ativo=True,
                data_termino__isnull=False,
                data_termino__gte=hoje,
                data_termino__lte=proximos_30_dias
            )
        return queryset
    
    def filter_vencido(self, queryset, name, value):
        """Filtra contratos vencidos"""
        if value:
            from django.utils import timezone
            hoje = timezone.now().date()
            return queryset.filter(
                ativo=True,
                data_termino__isnull=False,
                data_termino__lt=hoje
            )
        return queryset
    
    def filter_sem_data_termino(self, queryset, name, value):
        """Filtra contratos sem data de término"""
        if value:
            return queryset.filter(data_termino__isnull=True)
        else:
            return queryset.filter(data_termino__isnull=False)
    
    def filter_tipo_cliente(self, queryset, name, value):
        """Filtra por tipo de cliente (PJ ou PF)"""
        if value == 'PJ':
            pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
            return queryset.filter(content_type=pj_content_type)
        elif value == 'PF':
            pf_content_type = ContentType.objects.get_for_model(PessoaFisica)
            return queryset.filter(content_type=pf_content_type)
        return queryset
    
    def filter_modulo(self, queryset, name, value):
        """Filtra contratos que têm um módulo específico"""
        return queryset.filter(
            modulos_contratados__contains=[value]
        )
    
    def filter_busca(self, queryset, name, value):
        """
        Busca textual em múltiplos campos
        Busca no nome/razão social do cliente através do GenericForeignKey
        """
        # Buscar em Pessoa Jurídica
        pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
        pj_ids = PessoaJuridica.objects.filter(
            Q(razao_social__icontains=value) |
            Q(nome_fantasia__icontains=value) |
            Q(cnpj__icontains=value)
        ).values_list('id', flat=True)
        
        # Buscar em Pessoa Física
        pf_content_type = ContentType.objects.get_for_model(PessoaFisica)
        pf_ids = PessoaFisica.objects.filter(
            Q(nome_completo__icontains=value) |
            Q(cpf__icontains=value)
        ).values_list('id', flat=True)
        
        # Filtrar contratos que correspondem aos clientes encontrados
        return queryset.filter(
            Q(content_type=pj_content_type, object_id__in=pj_ids) |
            Q(content_type=pf_content_type, object_id__in=pf_ids) |
            Q(plano_servico__icontains=value) |
            Q(id_legado__icontains=value)
        ).distinct()
