"""
Filtros para API de Billing
"""

import django_filters
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta

from apps.billing.models import Plano, Assinatura, Fatura, Pagamento


class PlanoFilter(django_filters.FilterSet):
    """
    Filtros para Planos
    """
    codigo = django_filters.CharFilter(lookup_expr='icontains')
    nome = django_filters.CharFilter(lookup_expr='icontains')
    ativo = django_filters.BooleanFilter()
    preco_min = django_filters.NumberFilter(field_name='preco_mensal', lookup_expr='gte')
    preco_max = django_filters.NumberFilter(field_name='preco_mensal', lookup_expr='lte')
    tem_desconto_anual = django_filters.BooleanFilter(
        method='filter_tem_desconto_anual'
    )
    
    class Meta:
        model = Plano
        fields = ['codigo', 'nome', 'ativo', 'preco_min', 'preco_max', 'tem_desconto_anual']
    
    def filter_tem_desconto_anual(self, queryset, name, value):
        """
        Filtra planos que têm desconto anual
        """
        if value:
            return queryset.filter(desconto_anual__gt=0)
        return queryset.filter(desconto_anual=0)


class AssinaturaFilter(django_filters.FilterSet):
    """
    Filtros para Assinaturas
    """
    contabilidade = django_filters.UUIDFilter(field_name='contabilidade__id')
    plano = django_filters.UUIDFilter(field_name='plano__id')
    plano_codigo = django_filters.CharFilter(field_name='plano__codigo')
    status = django_filters.ChoiceFilter(choices=Assinatura.STATUS_CHOICES)
    ciclo_cobranca = django_filters.ChoiceFilter(choices=Plano.CICLO_CHOICES)
    
    # Filtros de data
    data_inicio_apos = django_filters.DateFilter(field_name='data_inicio', lookup_expr='gte')
    data_inicio_antes = django_filters.DateFilter(field_name='data_inicio', lookup_expr='lte')
    data_fim_apos = django_filters.DateFilter(field_name='data_fim', lookup_expr='gte')
    data_fim_antes = django_filters.DateFilter(field_name='data_fim', lookup_expr='lte')
    
    # Filtros de valor
    valor_min = django_filters.NumberFilter(field_name='valor_mensal', lookup_expr='gte')
    valor_max = django_filters.NumberFilter(field_name='valor_mensal', lookup_expr='lte')
    
    # Filtros especiais
    ativa = django_filters.BooleanFilter(method='filter_ativa')
    em_trial = django_filters.BooleanFilter(method='filter_em_trial')
    vencida = django_filters.BooleanFilter(method='filter_vencida')
    vence_em_dias = django_filters.NumberFilter(method='filter_vence_em_dias')
    
    class Meta:
        model = Assinatura
        fields = [
            'contabilidade', 'plano', 'plano_codigo', 'status', 'ciclo_cobranca',
            'data_inicio_apos', 'data_inicio_antes', 'data_fim_apos', 'data_fim_antes',
            'valor_min', 'valor_max', 'ativa', 'em_trial', 'vencida', 'vence_em_dias'
        ]
    
    def filter_ativa(self, queryset, name, value):
        """
        Filtra assinaturas ativas
        """
        if value:
            return queryset.filter(
                Q(status='ativa') &
                Q(data_inicio__lte=timezone.now().date()) &
                (Q(data_fim__isnull=True) | Q(data_fim__gte=timezone.now().date()))
            )
        return queryset.exclude(
            Q(status='ativa') &
            Q(data_inicio__lte=timezone.now().date()) &
            (Q(data_fim__isnull=True) | Q(data_fim__gte=timezone.now().date()))
        )
    
    def filter_em_trial(self, queryset, name, value):
        """
        Filtra assinaturas em período de teste
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
    
    def filter_vencida(self, queryset, name, value):
        """
        Filtra assinaturas vencidas
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
    
    def filter_vence_em_dias(self, queryset, name, value):
        """
        Filtra assinaturas que vencem em X dias
        """
        if value is not None:
            data_limite = timezone.now().date() + timedelta(days=value)
            return queryset.filter(
                data_fim__isnull=False,
                data_fim__lte=data_limite,
                data_fim__gte=timezone.now().date()
            )
        return queryset


class FaturaFilter(django_filters.FilterSet):
    """
    Filtros para Faturas
    """
    assinatura = django_filters.UUIDFilter(field_name='assinatura__id')
    contabilidade = django_filters.UUIDFilter(field_name='assinatura__contabilidade__id')
    plano = django_filters.UUIDFilter(field_name='assinatura__plano__id')
    
    # Filtros de identificação
    numero_fatura = django_filters.CharFilter(lookup_expr='icontains')
    competencia = django_filters.CharFilter(lookup_expr='icontains')
    status = django_filters.ChoiceFilter(choices=Fatura.STATUS_CHOICES)
    
    # Filtros de data
    data_emissao_apos = django_filters.DateFilter(field_name='data_emissao', lookup_expr='gte')
    data_emissao_antes = django_filters.DateFilter(field_name='data_emissao', lookup_expr='lte')
    data_vencimento_apos = django_filters.DateFilter(field_name='data_vencimento', lookup_expr='gte')
    data_vencimento_antes = django_filters.DateFilter(field_name='data_vencimento', lookup_expr='lte')
    data_pagamento_apos = django_filters.DateFilter(field_name='data_pagamento', lookup_expr='gte')
    data_pagamento_antes = django_filters.DateFilter(field_name='data_pagamento', lookup_expr='lte')
    
    # Filtros de valor
    valor_min = django_filters.NumberFilter(field_name='valor_final', lookup_expr='gte')
    valor_max = django_filters.NumberFilter(field_name='valor_final', lookup_expr='lte')
    
    # Filtros especiais
    vencida = django_filters.BooleanFilter(method='filter_vencida')
    vence_em_dias = django_filters.NumberFilter(method='filter_vence_em_dias')
    em_atraso = django_filters.BooleanFilter(method='filter_em_atraso')
    
    class Meta:
        model = Fatura
        fields = [
            'assinatura', 'contabilidade', 'plano', 'numero_fatura', 'competencia', 'status',
            'data_emissao_apos', 'data_emissao_antes', 'data_vencimento_apos', 'data_vencimento_antes',
            'data_pagamento_apos', 'data_pagamento_antes', 'valor_min', 'valor_max',
            'vencida', 'vence_em_dias', 'em_atraso'
        ]
    
    def filter_vencida(self, queryset, name, value):
        """
        Filtra faturas vencidas
        """
        if value:
            return queryset.filter(
                data_vencimento__lt=timezone.now().date(),
                status='aberta'
            )
        return queryset.exclude(
            data_vencimento__lt=timezone.now().date(),
            status='aberta'
        )
    
    def filter_vence_em_dias(self, queryset, name, value):
        """
        Filtra faturas que vencem em X dias
        """
        if value is not None:
            data_limite = timezone.now().date() + timedelta(days=value)
            return queryset.filter(
                data_vencimento__lte=data_limite,
                data_vencimento__gte=timezone.now().date(),
                status='aberta'
            )
        return queryset
    
    def filter_em_atraso(self, queryset, name, value):
        """
        Filtra faturas em atraso (vencidas há mais de 30 dias)
        """
        if value:
            data_limite = timezone.now().date() - timedelta(days=30)
            return queryset.filter(
                data_vencimento__lt=data_limite,
                status='aberta'
            )
        return queryset.exclude(
            data_vencimento__lt=timezone.now().date() - timedelta(days=30),
            status='aberta'
        )


class PagamentoFilter(django_filters.FilterSet):
    """
    Filtros para Pagamentos
    """
    fatura = django_filters.UUIDFilter(field_name='fatura__id')
    assinatura = django_filters.UUIDFilter(field_name='fatura__assinatura__id')
    contabilidade = django_filters.UUIDFilter(field_name='fatura__assinatura__contabilidade__id')
    
    # Filtros de identificação
    transacao_id = django_filters.CharFilter(lookup_expr='icontains')
    referencia = django_filters.CharFilter(lookup_expr='icontains')
    status = django_filters.ChoiceFilter(choices=Pagamento.STATUS_CHOICES)
    metodo = django_filters.ChoiceFilter(choices=Pagamento.METODO_CHOICES)
    
    # Filtros de data
    data_pagamento_apos = django_filters.DateTimeFilter(field_name='data_pagamento', lookup_expr='gte')
    data_pagamento_antes = django_filters.DateTimeFilter(field_name='data_pagamento', lookup_expr='lte')
    data_confirmacao_apos = django_filters.DateTimeFilter(field_name='data_confirmacao', lookup_expr='gte')
    data_confirmacao_antes = django_filters.DateTimeFilter(field_name='data_confirmacao', lookup_expr='lte')
    created_apos = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_antes = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    # Filtros de valor
    valor_min = django_filters.NumberFilter(field_name='valor', lookup_expr='gte')
    valor_max = django_filters.NumberFilter(field_name='valor', lookup_expr='lte')
    
    # Filtros especiais
    confirmado = django_filters.BooleanFilter(method='filter_confirmado')
    pendente = django_filters.BooleanFilter(method='filter_pendente')
    
    class Meta:
        model = Pagamento
        fields = [
            'fatura', 'assinatura', 'contabilidade', 'transacao_id', 'referencia',
            'status', 'metodo', 'data_pagamento_apos', 'data_pagamento_antes',
            'data_confirmacao_apos', 'data_confirmacao_antes', 'created_apos', 'created_antes',
            'valor_min', 'valor_max', 'confirmado', 'pendente'
        ]
    
    def filter_confirmado(self, queryset, name, value):
        """
        Filtra pagamentos confirmados
        """
        if value:
            return queryset.filter(status='confirmado')
        return queryset.exclude(status='confirmado')
    
    def filter_pendente(self, queryset, name, value):
        """
        Filtra pagamentos pendentes
        """
        if value:
            return queryset.filter(status='pendente')
        return queryset.exclude(status='pendente')
