"""
Serializers para gestão de Contabilidades (SUPERUSER)
"""

from rest_framework import serializers
from django.db import transaction
from django.utils import timezone

from apps.core.models import Contabilidade


class ContabilidadeListSerializer(serializers.ModelSerializer):
    """
    Serializer para listagem de contabilidades (campos mínimos)
    """
    
    # Campos adicionais computados
    total_usuarios = serializers.SerializerMethodField()
    total_contratos = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Contabilidade
        fields = [
            'id',
            'razao_social',
            'nome_fantasia',
            'cnpj',
            'email',
            'telefone',
            'ativo',
            'status_display',
            'suspensa_por_inadimplencia',
            'saldo_creditos',
            'total_usuarios',
            'total_contratos',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_usuarios(self, obj):
        """Retorna total de usuários ativos"""
        return obj.usuarios.filter(ativo=True).count()
    
    def get_total_contratos(self, obj):
        """Retorna total de contratos ativos (clientes da contabilidade)"""
        return obj.contratos.filter(ativo=True).count()
    
    def get_status_display(self, obj):
        """Retorna status legível"""
        if obj.suspensa_por_inadimplencia:
            return 'Suspensa - Inadimplência'
        elif not obj.ativo:
            return 'Inativa'
        return 'Ativa'


class ContabilidadeDetailSerializer(serializers.ModelSerializer):
    """
    Serializer para detalhes completos de contabilidade
    """
    
    # Campos computados
    total_usuarios = serializers.SerializerMethodField()
    total_contratos = serializers.SerializerMethodField()
    total_clientes = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    estatisticas_usuarios = serializers.SerializerMethodField()
    
    class Meta:
        model = Contabilidade
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_usuarios(self, obj):
        return obj.usuarios.filter(ativo=True).count()
    
    def get_total_contratos(self, obj):
        """Retorna total de contratos ativos (clientes da contabilidade)"""
        return obj.contratos.filter(ativo=True).count()
    
    def get_total_clientes(self, obj):
        """Retorna total de clientes vinculados"""
        from apps.pessoas.models import Contrato
        return Contrato.objects.filter(
            contabilidade=obj,
            ativo=True
        ).count()
    
    def get_status_display(self, obj):
        if obj.suspensa_por_inadimplencia:
            return 'Suspensa - Inadimplência'
        elif not obj.ativo:
            return 'Inativa'
        return 'Ativa'
    
    def get_estatisticas_usuarios(self, obj):
        """Retorna estatísticas de usuários por tipo"""
        usuarios = obj.usuarios.filter(ativo=True)
        return {
            'total': usuarios.count(),
            'por_tipo': {
                'superuser': usuarios.filter(tipo_usuario='superuser').count(),
                'admin': usuarios.filter(tipo_usuario='admin').count(),
                'operacional': usuarios.filter(tipo_usuario='operacional').count(),
                'etl': usuarios.filter(tipo_usuario='etl').count(),
                'readonly': usuarios.filter(tipo_usuario='readonly').count(),
            }
        }


class ContabilidadeCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para criação de contabilidade
    """
    
    class Meta:
        model = Contabilidade
        fields = [
            'razao_social',
            'nome_fantasia',
            'cnpj',
            'email',
            'telefone',
            'endereco',
            'inscricao_estadual',
            'responsavel_financeiro_nome',
            'responsavel_financeiro_email',
            'responsavel_financeiro_telefone',
            'endereco_cobranca',
            'ativo',
        ]
    
    def validate_cnpj(self, value):
        """Validar CNPJ único"""
        # Remove caracteres especiais
        cnpj_limpo = ''.join(filter(str.isdigit, value))
        
        if len(cnpj_limpo) != 14:
            raise serializers.ValidationError(
                'CNPJ deve conter 14 dígitos'
            )
        
        if Contabilidade.objects.filter(cnpj=cnpj_limpo).exists():
            raise serializers.ValidationError(
                'Já existe uma contabilidade com este CNPJ'
            )
        
        return cnpj_limpo
    
    def validate_email(self, value):
        """Validar email único"""
        if value and Contabilidade.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                'Já existe uma contabilidade com este e-mail'
            )
        return value
    
    def validate(self, attrs):
        """Validações customizadas"""
        # Validar email do responsável financeiro se fornecido
        if attrs.get('responsavel_financeiro_email'):
            email = attrs['responsavel_financeiro_email']
            if not email or '@' not in email:
                raise serializers.ValidationError({
                    'responsavel_financeiro_email': 'E-mail inválido'
                })
        
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Criar contabilidade com transação
        """
        # Criar contabilidade
        contabilidade = Contabilidade.objects.create(**validated_data)
        
        return contabilidade


class ContabilidadeUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para atualização de contabilidade
    """
    
    class Meta:
        model = Contabilidade
        fields = [
            'razao_social',
            'nome_fantasia',
            'email',
            'telefone',
            'endereco',
            'inscricao_estadual',
            'responsavel_financeiro_nome',
            'responsavel_financeiro_email',
            'responsavel_financeiro_telefone',
            'endereco_cobranca',
            'ativo',
            'suspensa_por_inadimplencia',
            'saldo_creditos',
        ]
    
    def validate(self, attrs):
        """Validações de atualização"""
        instance = self.instance
        
        # Não permitir desativar se tiver contratos ativos (com clientes)
        if 'ativo' in attrs and not attrs['ativo']:
            contratos_ativos = instance.contratos.filter(ativo=True).count()
            if contratos_ativos > 0:
                raise serializers.ValidationError({
                    'ativo': f'Não é possível desativar. Existem {contratos_ativos} contratos ativos com clientes.'
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
