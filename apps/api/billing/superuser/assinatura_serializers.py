"""
Serializers para Assinaturas (SUPERUSER)
"""

from rest_framework import serializers
from django.utils import timezone
from decimal import Decimal

from apps.billing.models import Assinatura, Plano
from apps.core.models import Contabilidade


class AssinaturaListSerializer(serializers.ModelSerializer):
    """
    Serializer para listagem de assinaturas
    """
    contabilidade_nome = serializers.CharField(
        source='contabilidade.razao_social',
        read_only=True
    )
    plano_nome = serializers.CharField(
        source='plano.nome',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    # Campos computados
    esta_ativa = serializers.BooleanField(read_only=True)
    esta_em_trial = serializers.BooleanField(read_only=True)
    dias_para_vencimento = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Assinatura
        fields = [
            'id', 'contabilidade', 'contabilidade_nome',
            'plano', 'plano_nome',
            'data_inicio', 'data_fim', 'data_renovacao',
            'status', 'status_display',
            'ciclo_cobranca', 'valor_mensal',
            'esta_ativa', 'esta_em_trial', 'dias_para_vencimento',
            'created_at', 'updated_at'
        ]


class AssinaturaDetailSerializer(serializers.ModelSerializer):
    """
    Serializer para detalhes da assinatura
    """
    contabilidade_dados = serializers.SerializerMethodField()
    plano_dados = serializers.SerializerMethodField()
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    # Campos computados
    esta_ativa = serializers.BooleanField(read_only=True)
    esta_em_trial = serializers.BooleanField(read_only=True)
    dias_para_vencimento = serializers.IntegerField(read_only=True)
    
    # Estatísticas de faturas
    total_faturas = serializers.SerializerMethodField()
    faturas_pagas = serializers.SerializerMethodField()
    faturas_pendentes = serializers.SerializerMethodField()
    valor_total_faturado = serializers.SerializerMethodField()
    
    class Meta:
        model = Assinatura
        fields = '__all__'
    
    def get_contabilidade_dados(self, obj):
        return {
            'id': obj.contabilidade.id,
            'razao_social': obj.contabilidade.razao_social,
            'cnpj': obj.contabilidade.cnpj,
            'ativo': obj.contabilidade.ativo,
        }
    
    def get_plano_dados(self, obj):
        return {
            'id': str(obj.plano.id),
            'codigo': obj.plano.codigo,
            'nome': obj.plano.nome,
            'preco_mensal': float(obj.plano.preco_mensal),
            'preco_anual': float(obj.plano.preco_anual) if obj.plano.preco_anual else None,
            'modulos_inclusos': obj.plano.modulos_inclusos,
            'limites': obj.plano.limites,
        }
    
    def get_total_faturas(self, obj):
        return obj.faturas.count()
    
    def get_faturas_pagas(self, obj):
        return obj.faturas.filter(status='paga').count()
    
    def get_faturas_pendentes(self, obj):
        return obj.faturas.filter(status__in=['aberta', 'vencida']).count()
    
    def get_valor_total_faturado(self, obj):
        from django.db.models import Sum
        total = obj.faturas.aggregate(Sum('valor_final'))['valor_final__sum']
        return float(total) if total else 0.0


class AssinaturaCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para criação de assinatura
    """
    class Meta:
        model = Assinatura
        fields = [
            'contabilidade', 'plano',
            'data_inicio', 'data_fim', 'data_renovacao',
            'status', 'ciclo_cobranca',
            'trial_ate',
            'valor_mensal', 'valor_anual',
            'dia_vencimento', 'desconto_percentual',
            'metadados'
        ]
    
    def validate_contabilidade(self, value):
        """Validar se contabilidade está ativa"""
        if not value.ativo:
            raise serializers.ValidationError(
                'Não é possível criar assinatura para contabilidade inativa'
            )
        return value
    
    def validate(self, attrs):
        """Validações gerais"""
        data_inicio = attrs.get('data_inicio')
        data_fim = attrs.get('data_fim')
        trial_ate = attrs.get('trial_ate')
        
        # Validar datas
        if data_fim and data_inicio and data_fim <= data_inicio:
            raise serializers.ValidationError({
                'data_fim': 'Data de fim deve ser posterior à data de início'
            })
        
        if trial_ate and trial_ate < data_inicio:
            raise serializers.ValidationError({
                'trial_ate': 'Data de trial deve ser posterior à data de início'
            })
        
        # Validar valores
        valor_mensal = attrs.get('valor_mensal')
        if valor_mensal and valor_mensal <= 0:
            raise serializers.ValidationError({
                'valor_mensal': 'Valor mensal deve ser maior que zero'
            })
        
        # Definir status automático baseado em trial
        if trial_ate and trial_ate >= timezone.now().date():
            attrs['status'] = 'trial'
        
        return attrs


class AssinaturaUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para atualização de assinatura
    """
    class Meta:
        model = Assinatura
        fields = [
            'plano',
            'data_fim', 'data_renovacao',
            'status', 'ciclo_cobranca',
            'trial_ate',
            'valor_mensal', 'valor_anual',
            'dia_vencimento', 'desconto_percentual',
            'metadados'
        ]
    
    def validate(self, attrs):
        """Validações para atualização"""
        instance = self.instance
        
        # Não permitir alterar status diretamente se houver faturas pendentes
        novo_status = attrs.get('status')
        if novo_status and novo_status != instance.status:
            if novo_status == 'cancelada':
                faturas_pendentes = instance.faturas.filter(
                    status__in=['aberta', 'vencida']
                ).count()
                if faturas_pendentes > 0:
                    raise serializers.ValidationError({
                        'status': f'Não é possível cancelar assinatura com {faturas_pendentes} faturas pendentes'
                    })
        
        # Validar datas
        data_fim = attrs.get('data_fim')
        if data_fim and data_fim <= instance.data_inicio:
            raise serializers.ValidationError({
                'data_fim': 'Data de fim deve ser posterior à data de início'
            })
        
        return attrs
