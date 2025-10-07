"""
Serializers para API de Billing
"""

from rest_framework import serializers
from django.db import models
from apps.billing.models import Plano, Assinatura, Fatura, Pagamento
from apps.core.models import Contabilidade


class PlanoSerializer(serializers.ModelSerializer):
    """
    Serializer para Planos
    """
    preco_anual_calculado = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Plano
        fields = [
            'id', 'codigo', 'nome', 'descricao', 'preco_mensal', 'preco_anual',
            'desconto_anual', 'preco_anual_calculado', 'modulos_inclusos', 'limites',
            'ativo', 'ordem_exibicao', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_codigo(self, value):
        """
        Valida se o código do plano é único
        """
        if self.instance and self.instance.codigo == value:
            return value
        
        if Plano.objects.filter(codigo=value).exists():
            raise serializers.ValidationError("Já existe um plano com este código.")
        
        return value


class AssinaturaSerializer(serializers.ModelSerializer):
    """
    Serializer para Assinaturas
    """
    contabilidade_razao_social = serializers.CharField(source='contabilidade.razao_social', read_only=True)
    contabilidade_cnpj = serializers.CharField(source='contabilidade.cnpj', read_only=True)
    plano_nome = serializers.CharField(source='plano.nome', read_only=True)
    plano_codigo = serializers.CharField(source='plano.codigo', read_only=True)
    esta_ativa = serializers.BooleanField(read_only=True)
    esta_em_trial = serializers.BooleanField(read_only=True)
    dias_para_vencimento = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Assinatura
        fields = [
            'id', 'contabilidade', 'contabilidade_razao_social', 'contabilidade_cnpj',
            'plano', 'plano_nome', 'plano_codigo', 'data_inicio', 'data_fim', 'data_renovacao',
            'status', 'ciclo_cobranca', 'trial_ate', 'valor_mensal', 'valor_anual',
            'dia_vencimento', 'desconto_percentual', 'motivo_suspensao', 'data_suspensao',
            'motivo_cancelamento', 'data_cancelamento', 'metadados', 'created_at', 'updated_at',
            'created_by', 'esta_ativa', 'esta_em_trial', 'dias_para_vencimento'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    def validate_data_fim(self, value):
        """
        Valida se a data de fim é posterior à data de início
        """
        data_inicio = self.initial_data.get('data_inicio')
        if data_inicio and value and value <= data_inicio:
            raise serializers.ValidationError("Data de fim deve ser posterior à data de início.")
        
        return value


class FaturaSerializer(serializers.ModelSerializer):
    """
    Serializer para Faturas
    """
    assinatura_contabilidade = serializers.CharField(source='assinatura.contabilidade.razao_social', read_only=True)
    assinatura_plano = serializers.CharField(source='assinatura.plano.nome', read_only=True)
    esta_vencida = serializers.BooleanField(read_only=True)
    dias_para_vencimento = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Fatura
        fields = [
            'id', 'assinatura', 'assinatura_contabilidade', 'assinatura_plano',
            'numero_fatura', 'competencia', 'valor_original', 'desconto', 'valor_final',
            'data_emissao', 'data_vencimento', 'data_pagamento', 'status', 'link_boleto',
            'linha_digitavel', 'codigo_barras', 'metadados', 'created_at', 'updated_at',
            'esta_vencida', 'dias_para_vencimento'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_numero_fatura(self, value):
        """
        Valida se o número da fatura é único
        """
        if self.instance and self.instance.numero_fatura == value:
            return value
        
        if Fatura.objects.filter(numero_fatura=value).exists():
            raise serializers.ValidationError("Já existe uma fatura com este número.")
        
        return value


class PagamentoSerializer(serializers.ModelSerializer):
    """
    Serializer para Pagamentos
    """
    fatura_numero = serializers.CharField(source='fatura.numero_fatura', read_only=True)
    fatura_contabilidade = serializers.CharField(source='fatura.assinatura.contabilidade.razao_social', read_only=True)
    fatura_valor = serializers.DecimalField(source='fatura.valor_final', max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = Pagamento
        fields = [
            'id', 'fatura', 'fatura_numero', 'fatura_contabilidade', 'fatura_valor',
            'valor', 'metodo', 'transacao_id', 'referencia', 'status', 'data_pagamento',
            'data_confirmacao', 'metadados', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_valor(self, value):
        """
        Valida se o valor do pagamento não excede o valor da fatura
        """
        fatura = self.initial_data.get('fatura')
        if fatura:
            try:
                fatura_obj = Fatura.objects.get(id=fatura)
                if value > fatura_obj.valor_final:
                    raise serializers.ValidationError("Valor do pagamento não pode exceder o valor da fatura.")
            except Fatura.DoesNotExist:
                pass
        
        return value


class ContabilidadeBillingSerializer(serializers.ModelSerializer):
    """
    Serializer para Contabilidades com informações de billing
    """
    assinatura_atual = serializers.SerializerMethodField()
    total_faturas = serializers.SerializerMethodField()
    faturas_pendentes = serializers.SerializerMethodField()
    receita_total = serializers.SerializerMethodField()
    
    class Meta:
        model = Contabilidade
        fields = [
            'id', 'razao_social', 'nome_fantasia', 'cnpj', 'ativo',
            'responsavel_financeiro_nome', 'responsavel_financeiro_email',
            'suspensa_por_inadimplencia', 'saldo_creditos', 'assinatura_atual',
            'total_faturas', 'faturas_pendentes', 'receita_total'
        ]
    
    def get_assinatura_atual(self, obj):
        """
        Retorna a assinatura ativa da contabilidade
        """
        assinatura = obj.assinaturas.filter(status='ativa').first()
        if assinatura:
            return AssinaturaSerializer(assinatura).data
        return None
    
    def get_total_faturas(self, obj):
        """
        Retorna o total de faturas da contabilidade
        """
        return obj.assinaturas.aggregate(
            total=models.Count('faturas')
        )['total'] or 0
    
    def get_faturas_pendentes(self, obj):
        """
        Retorna o número de faturas pendentes
        """
        return obj.assinaturas.aggregate(
            pendentes=models.Count('faturas', filter=models.Q(faturas__status='aberta'))
        )['pendentes'] or 0
    
    def get_receita_total(self, obj):
        """
        Retorna a receita total da contabilidade
        """
        return obj.assinaturas.aggregate(
            receita=models.Sum('faturas__valor_final', filter=models.Q(faturas__status='paga'))
        )['receita'] or 0
