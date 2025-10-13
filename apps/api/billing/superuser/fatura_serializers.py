"""
Serializers para Faturas (SUPERUSER)
"""

from rest_framework import serializers
from django.utils import timezone

from apps.billing.models import Fatura, Assinatura


class FaturaListSerializer(serializers.ModelSerializer):
    """
    Serializer para listagem de faturas
    """
    contabilidade_nome = serializers.CharField(
        source='assinatura.contabilidade.razao_social',
        read_only=True
    )
    plano_nome = serializers.CharField(
        source='assinatura.plano.nome',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    # Campos computados
    esta_vencida = serializers.BooleanField(read_only=True)
    dias_para_vencimento = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Fatura
        fields = [
            'id', 'numero_fatura', 'competencia',
            'assinatura', 'contabilidade_nome', 'plano_nome',
            'valor_original', 'desconto', 'valor_final',
            'data_emissao', 'data_vencimento', 'data_pagamento',
            'status', 'status_display',
            'esta_vencida', 'dias_para_vencimento',
            'created_at', 'updated_at'
        ]


class FaturaDetailSerializer(serializers.ModelSerializer):
    """
    Serializer para detalhes da fatura
    """
    assinatura_dados = serializers.SerializerMethodField()
    contabilidade_dados = serializers.SerializerMethodField()
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    # Campos computados
    esta_vencida = serializers.BooleanField(read_only=True)
    dias_para_vencimento = serializers.IntegerField(read_only=True)
    dias_atraso = serializers.SerializerMethodField()
    
    class Meta:
        model = Fatura
        fields = '__all__'
    
    def get_assinatura_dados(self, obj):
        return {
            'id': str(obj.assinatura.id),
            'plano': obj.assinatura.plano.nome,
            'status': obj.assinatura.status,
            'ciclo_cobranca': obj.assinatura.ciclo_cobranca,
        }
    
    def get_contabilidade_dados(self, obj):
        return {
            'id': obj.assinatura.contabilidade.id,
            'razao_social': obj.assinatura.contabilidade.razao_social,
            'cnpj': obj.assinatura.contabilidade.cnpj,
            'ativo': obj.assinatura.contabilidade.ativo,
        }
    
    def get_dias_atraso(self, obj):
        """Retorna dias de atraso se vencida"""
        if obj.status in ['aberta', 'vencida'] and obj.data_vencimento < timezone.now().date():
            delta = timezone.now().date() - obj.data_vencimento
            return delta.days
        return 0


class FaturaCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para criação de fatura
    """
    class Meta:
        model = Fatura
        fields = [
            'assinatura', 'numero_fatura', 'competencia',
            'valor_original', 'desconto', 'valor_final',
            'data_emissao', 'data_vencimento',
            'status',
            'link_boleto', 'linha_digitavel', 'codigo_barras',
            'metadados'
        ]
    
    def validate_numero_fatura(self, value):
        """Validar número único"""
        if Fatura.objects.filter(numero_fatura=value).exists():
            raise serializers.ValidationError(
                'Já existe uma fatura com este número'
            )
        return value
    
    def validate_competencia(self, value):
        """Validar formato de competência (YYYY-MM)"""
        import re
        if not re.match(r'^\d{4}-\d{2}$', value):
            raise serializers.ValidationError(
                'Competência deve estar no formato YYYY-MM'
            )
        return value
    
    def validate(self, attrs):
        """Validações gerais"""
        valor_original = attrs.get('valor_original')
        desconto = attrs.get('desconto', 0)
        valor_final = attrs.get('valor_final')
        
        # Validar valores
        if valor_original <= 0:
            raise serializers.ValidationError({
                'valor_original': 'Valor original deve ser maior que zero'
            })
        
        if desconto < 0:
            raise serializers.ValidationError({
                'desconto': 'Desconto não pode ser negativo'
            })
        
        if desconto > valor_original:
            raise serializers.ValidationError({
                'desconto': 'Desconto não pode ser maior que o valor original'
            })
        
        # Calcular valor final
        esperado = valor_original - desconto
        if abs(valor_final - esperado) > 0.01:  # Tolerância de 1 centavo
            raise serializers.ValidationError({
                'valor_final': f'Valor final deve ser {esperado} (valor_original - desconto)'
            })
        
        # Validar datas
        data_emissao = attrs.get('data_emissao')
        data_vencimento = attrs.get('data_vencimento')
        
        if data_vencimento < data_emissao:
            raise serializers.ValidationError({
                'data_vencimento': 'Data de vencimento não pode ser anterior à data de emissão'
            })
        
        return attrs


class FaturaUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para atualização de fatura
    """
    class Meta:
        model = Fatura
        fields = [
            'valor_original', 'desconto', 'valor_final',
            'data_vencimento', 'data_pagamento',
            'status',
            'link_boleto', 'linha_digitavel', 'codigo_barras',
            'metadados'
        ]
    
    def validate(self, attrs):
        """Validações para atualização"""
        instance = self.instance
        
        # Não permitir alterar fatura já paga
        if instance.status == 'paga':
            novo_status = attrs.get('status')
            if novo_status and novo_status != 'paga':
                raise serializers.ValidationError({
                    'status': 'Não é possível alterar status de fatura já paga (use estornar)'
                })
        
        # Validar valores se alterados
        valor_original = attrs.get('valor_original', instance.valor_original)
        desconto = attrs.get('desconto', instance.desconto)
        valor_final = attrs.get('valor_final', instance.valor_final)
        
        esperado = valor_original - desconto
        if abs(valor_final - esperado) > 0.01:
            raise serializers.ValidationError({
                'valor_final': f'Valor final deve ser {esperado} (valor_original - desconto)'
            })
        
        return attrs
