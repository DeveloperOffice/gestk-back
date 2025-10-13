"""
Serializers para gerenciamento de Clientes (Contratos) por ADMIN
"""
from rest_framework import serializers
from apps.pessoas.models import Contrato, PessoaJuridica, PessoaFisica
from apps.core.models import Contabilidade
from django.contrib.contenttypes.models import ContentType
from django.db import transaction


class ClienteInfoSerializer(serializers.Serializer):
    """Serializer para informações do cliente (PF ou PJ)"""
    id = serializers.UUIDField(read_only=True)
    tipo = serializers.SerializerMethodField()
    nome = serializers.SerializerMethodField()
    documento = serializers.SerializerMethodField()
    email = serializers.EmailField(read_only=True)
    telefone = serializers.CharField(read_only=True)
    
    def get_tipo(self, obj):
        return 'PJ' if isinstance(obj, PessoaJuridica) else 'PF'
    
    def get_nome(self, obj):
        if isinstance(obj, PessoaJuridica):
            return obj.razao_social
        return obj.nome_completo
    
    def get_documento(self, obj):
        if isinstance(obj, PessoaJuridica):
            return obj.cnpj
        return obj.cpf


class ContratoListSerializer(serializers.ModelSerializer):
    """Serializer para listagem de contratos (clientes)"""
    contabilidade_nome = serializers.CharField(source='contabilidade.razao_social', read_only=True)
    cliente_info = serializers.SerializerMethodField()
    esta_ativo = serializers.SerializerMethodField()
    dias_restantes = serializers.SerializerMethodField()
    
    class Meta:
        model = Contrato
        fields = [
            'id', 'contabilidade', 'contabilidade_nome',
            'cliente_info',
            'data_inicio', 'data_termino', 'dia_vencimento',
            'valor_honorario', 'plano_servico',
            'ativo', 'esta_ativo',
            'status_cobranca', 'dias_restantes',
            'limites_usuarios', 'limites_empresas'
        ]
        read_only_fields = ['id']
    
    def get_cliente_info(self, obj):
        """Retorna informações do cliente"""
        if obj.cliente:
            return ClienteInfoSerializer(obj.cliente).data
        return None
    
    def get_esta_ativo(self, obj):
        """Verifica se o contrato está realmente ativo"""
        from django.utils import timezone
        if not obj.ativo:
            return False
        if obj.data_termino and obj.data_termino < timezone.now().date():
            return False
        return True
    
    def get_dias_restantes(self, obj):
        """Calcula dias restantes do contrato"""
        from django.utils import timezone
        if not obj.data_termino:
            return None
        delta = obj.data_termino - timezone.now().date()
        return delta.days if delta.days >= 0 else 0


class ContratoDetailSerializer(serializers.ModelSerializer):
    """Serializer para detalhamento de contrato"""
    contabilidade_info = serializers.SerializerMethodField()
    cliente_info = serializers.SerializerMethodField()
    cliente_detalhes = serializers.SerializerMethodField()
    esta_ativo = serializers.SerializerMethodField()
    dias_restantes = serializers.SerializerMethodField()
    estatisticas = serializers.SerializerMethodField()
    
    class Meta:
        model = Contrato
        fields = [
            'id', 'id_legado',
            'contabilidade', 'contabilidade_info',
            'content_type', 'object_id',
            'cliente_info', 'cliente_detalhes',
            'data_inicio', 'data_termino', 'dia_vencimento',
            'valor_honorario', 'plano_servico',
            'modulos_contratados',
            'limites_usuarios', 'limites_empresas',
            'ativo', 'esta_ativo', 'status_cobranca',
            'dias_restantes', 'estatisticas'
        ]
        read_only_fields = ['id']
    
    def get_contabilidade_info(self, obj):
        """Retorna informações da contabilidade"""
        return {
            'id': str(obj.contabilidade.id),
            'razao_social': obj.contabilidade.razao_social,
            'cnpj': obj.contabilidade.cnpj
        }
    
    def get_cliente_info(self, obj):
        """Retorna informações básicas do cliente"""
        if obj.cliente:
            return ClienteInfoSerializer(obj.cliente).data
        return None
    
    def get_cliente_detalhes(self, obj):
        """Retorna detalhes completos do cliente"""
        if not obj.cliente:
            return None
        
        cliente = obj.cliente
        if isinstance(cliente, PessoaJuridica):
            return {
                'tipo': 'PJ',
                'razao_social': cliente.razao_social,
                'nome_fantasia': cliente.nome_fantasia,
                'cnpj': cliente.cnpj,
                'inscricao_estadual': cliente.inscricao_estadual,
                'inscricao_municipal': cliente.inscricao_municipal,
                'regime_tributario': cliente.regime_tributario,
                'simples_nacional': cliente.simples_nacional,
                'endereco': {
                    'logradouro': cliente.logradouro,
                    'numero': cliente.numero,
                    'complemento': cliente.complemento,
                    'bairro': cliente.bairro,
                    'cidade': cliente.cidade,
                    'uf': cliente.uf,
                    'cep': cliente.cep
                },
                'email': cliente.email,
                'telefone': cliente.telefone,
                'data_inicio_atividades': cliente.data_inicio_atividades
            }
        else:  # PessoaFisica
            return {
                'tipo': 'PF',
                'nome_completo': cliente.nome_completo,
                'cpf': cliente.cpf,
                'rg': cliente.rg if hasattr(cliente, 'rg') else None,
                'data_nascimento': cliente.data_nascimento if hasattr(cliente, 'data_nascimento') else None,
                'email': cliente.email,
                'telefone': cliente.telefone
            }
    
    def get_esta_ativo(self, obj):
        """Verifica se o contrato está realmente ativo"""
        from django.utils import timezone
        if not obj.ativo:
            return False
        if obj.data_termino and obj.data_termino < timezone.now().date():
            return False
        return True
    
    def get_dias_restantes(self, obj):
        """Calcula dias restantes do contrato"""
        from django.utils import timezone
        if not obj.data_termino:
            return None
        delta = obj.data_termino - timezone.now().date()
        return delta.days if delta.days >= 0 else 0
    
    def get_estatisticas(self, obj):
        """Retorna estatísticas do contrato"""
        from django.utils import timezone
        
        return {
            'dias_desde_inicio': (timezone.now().date() - obj.data_inicio).days if obj.data_inicio else None,
            'total_modulos': len(obj.modulos_contratados) if obj.modulos_contratados else 0,
            'dias_restantes': self.get_dias_restantes(obj)
        }


class ContratoUpdateSerializer(serializers.ModelSerializer):
    """Serializer para atualização de contrato"""
    
    class Meta:
        model = Contrato
        fields = [
            'data_inicio', 'data_termino', 'dia_vencimento',
            'valor_honorario', 'plano_servico',
            'modulos_contratados',
            'limites_usuarios', 'limites_empresas',
            'ativo', 'status_cobranca'
        ]
    
    def validate_data_termino(self, value):
        """Valida data de término"""
        if value and self.instance and self.instance.data_inicio:
            if value < self.instance.data_inicio:
                raise serializers.ValidationError(
                    "Data de término não pode ser anterior à data de início"
                )
        return value
    
    def validate_dia_vencimento(self, value):
        """Valida dia de vencimento"""
        if value and (value < 1 or value > 31):
            raise serializers.ValidationError(
                "Dia de vencimento deve estar entre 1 e 31"
            )
        return value
    
    def validate_valor_honorario(self, value):
        """Valida valor do honorário"""
        if value and value < 0:
            raise serializers.ValidationError(
                "Valor do honorário não pode ser negativo"
            )
        return value
    
    def validate_limites_usuarios(self, value):
        """Valida limite de usuários"""
        if value and value < 1:
            raise serializers.ValidationError(
                "Limite de usuários deve ser no mínimo 1"
            )
        return value
    
    def validate_limites_empresas(self, value):
        """Valida limite de empresas"""
        if value and value < 1:
            raise serializers.ValidationError(
                "Limite de empresas deve ser no mínimo 1"
            )
        return value
