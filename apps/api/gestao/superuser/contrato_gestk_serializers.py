"""
Serializers para gestão de Contratos GESTK (SUPERUSER)
Contratos entre GESTK e suas contabilidades clientes (SaaS)
"""

from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from apps.administracao.models import ContratoGestk
from apps.core.models import Contabilidade


class ContratoGestkListSerializer(serializers.ModelSerializer):
    """
    Serializer para listagem de contratos GESTK (campos mínimos)
    """
    
    # Campos relacionados
    contabilidade_razao_social = serializers.CharField(
        source='contabilidade.razao_social',
        read_only=True
    )
    contabilidade_cnpj = serializers.CharField(
        source='contabilidade.cnpj',
        read_only=True
    )
    
    # Campos computados
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    dias_ate_vencimento = serializers.SerializerMethodField()
    esta_em_trial = serializers.SerializerMethodField()
    
    class Meta:
        model = ContratoGestk
        fields = [
            'id',
            'numero_contrato',
            'contabilidade',
            'contabilidade_razao_social',
            'contabilidade_cnpj',
            'plano_servico',
            'status',
            'status_display',
            'data_inicio',
            'data_termino',
            'data_renovacao',
            'valor_mensal',
            'dias_ate_vencimento',
            'esta_em_trial',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_dias_ate_vencimento(self, obj):
        """Calcula dias até vencimento"""
        if not obj.data_termino:
            return None
        delta = obj.data_termino - timezone.now().date()
        return delta.days
    
    def get_esta_em_trial(self, obj):
        """Verifica se está em período de teste"""
        if obj.trial_ate and obj.trial_ate >= timezone.now().date():
            return True
        return False


class ContratoGestkDetailSerializer(serializers.ModelSerializer):
    """
    Serializer para detalhes completos de contrato GESTK
    """
    
    # Campos relacionados
    contabilidade_razao_social = serializers.CharField(
        source='contabilidade.razao_social',
        read_only=True
    )
    contabilidade_cnpj = serializers.CharField(
        source='contabilidade.cnpj',
        read_only=True
    )
    contabilidade_email = serializers.CharField(
        source='contabilidade.email',
        read_only=True
    )
    
    # Campos computados
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    dias_ate_vencimento = serializers.SerializerMethodField()
    esta_em_trial = serializers.SerializerMethodField()
    esta_vencido = serializers.SerializerMethodField()
    uso_limites = serializers.SerializerMethodField()
    
    class Meta:
        model = ContratoGestk
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    def get_dias_ate_vencimento(self, obj):
        if not obj.data_termino:
            return None
        delta = obj.data_termino - timezone.now().date()
        return delta.days
    
    def get_esta_em_trial(self, obj):
        if obj.trial_ate and obj.trial_ate >= timezone.now().date():
            return True
        return False
    
    def get_esta_vencido(self, obj):
        return obj.esta_vencido
    
    def get_uso_limites(self, obj):
        """Retorna uso atual vs limites contratados"""
        usuarios_ativos = obj.contabilidade.usuarios.filter(ativo=True).count()
        contratos_internos = obj.contabilidade.contratos.filter(ativo=True).count()
        
        return {
            'usuarios': {
                'usado': usuarios_ativos,
                'limite': obj.limites_usuarios,
                'percentual': round((usuarios_ativos / obj.limites_usuarios * 100) if obj.limites_usuarios > 0 else 0, 2)
            },
            'contratos_internos': {
                'usado': contratos_internos,
                'limite': obj.limites_contratos_internos,
                'percentual': round((contratos_internos / obj.limites_contratos_internos * 100) if obj.limites_contratos_internos > 0 else 0, 2)
            }
        }


class ContratoGestkCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para criação de contrato GESTK
    """
    
    class Meta:
        model = ContratoGestk
        fields = [
            'contabilidade',
            'numero_contrato',
            'data_inicio',
            'data_termino',
            'data_renovacao',
            'plano_servico',
            'modulos_inclusos',
            'limites_usuarios',
            'limites_empresas',
            'limites_contratos_internos',
            'valor_mensal',
            'valor_anual',
            'desconto_percentual',
            'dia_vencimento',
            'responsavel_financeiro_nome',
            'responsavel_financeiro_email',
            'responsavel_financeiro_telefone',
            'endereco_cobranca',
            'trial_ate',
            'observacoes',
        ]
    
    def validate_numero_contrato(self, value):
        """Validar número de contrato único"""
        if ContratoGestk.objects.filter(numero_contrato=value).exists():
            raise serializers.ValidationError(
                'Já existe um contrato com este número'
            )
        return value
    
    def validate_contabilidade(self, value):
        """Validar se contabilidade já possui contrato"""
        if hasattr(value, 'contrato_gestk'):
            raise serializers.ValidationError(
                'Esta contabilidade já possui um contrato GESTK ativo'
            )
        return value
    
    def validate(self, attrs):
        """Validações customizadas"""
        # Validar datas
        if attrs.get('data_termino') and attrs['data_termino'] <= attrs['data_inicio']:
            raise serializers.ValidationError({
                'data_termino': 'Data de término deve ser maior que data de início'
            })
        
        if attrs.get('data_renovacao') and attrs['data_renovacao'] <= attrs['data_inicio']:
            raise serializers.ValidationError({
                'data_renovacao': 'Data de renovação deve ser maior que data de início'
            })
        
        # Validar limites
        if attrs.get('limites_usuarios', 0) < 1:
            raise serializers.ValidationError({
                'limites_usuarios': 'Limite de usuários deve ser maior que zero'
            })
        
        if attrs.get('limites_contratos_internos', 0) < 1:
            raise serializers.ValidationError({
                'limites_contratos_internos': 'Limite de contratos internos deve ser maior que zero'
            })
        
        # Validar valores
        if attrs.get('valor_mensal', 0) <= 0:
            raise serializers.ValidationError({
                'valor_mensal': 'Valor mensal deve ser maior que zero'
            })
        
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Criar contrato GESTK com transação
        """
        # Definir status inicial
        if validated_data.get('trial_ate') and validated_data['trial_ate'] >= timezone.now().date():
            validated_data['status'] = 'trial'
        else:
            validated_data['status'] = 'ativo'
        
        # Criar contrato
        contrato = ContratoGestk.objects.create(**validated_data)
        
        return contrato


class ContratoGestkUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para atualização de contrato GESTK
    """
    
    class Meta:
        model = ContratoGestk
        fields = [
            'data_termino',
            'data_renovacao',
            'plano_servico',
            'modulos_inclusos',
            'limites_usuarios',
            'limites_empresas',
            'limites_contratos_internos',
            'valor_mensal',
            'valor_anual',
            'desconto_percentual',
            'dia_vencimento',
            'responsavel_financeiro_nome',
            'responsavel_financeiro_email',
            'responsavel_financeiro_telefone',
            'endereco_cobranca',
            'observacoes',
        ]
    
    def validate(self, attrs):
        """Validações de atualização"""
        instance = self.instance
        
        # Não permitir alterar limites se ultrapassar uso atual
        if 'limites_usuarios' in attrs:
            usuarios_ativos = instance.contabilidade.usuarios.filter(ativo=True).count()
            if attrs['limites_usuarios'] < usuarios_ativos:
                raise serializers.ValidationError({
                    'limites_usuarios': f'Não é possível reduzir limite. Há {usuarios_ativos} usuários ativos.'
                })
        
        if 'limites_contratos_internos' in attrs:
            contratos_ativos = instance.contabilidade.contratos.filter(ativo=True).count()
            if attrs['limites_contratos_internos'] < contratos_ativos:
                raise serializers.ValidationError({
                    'limites_contratos_internos': f'Não é possível reduzir limite. Há {contratos_ativos} contratos ativos.'
                })
        
        # Validar datas se fornecidas
        if 'data_termino' in attrs and attrs['data_termino']:
            if attrs['data_termino'] <= instance.data_inicio:
                raise serializers.ValidationError({
                    'data_termino': 'Data de término deve ser maior que data de início'
                })
        
        return attrs
    
    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Atualizar com transação
        """
        # Atualizar campos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance
