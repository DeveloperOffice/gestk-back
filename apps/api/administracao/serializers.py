"""
Serializers para API de Administração
"""

from rest_framework import serializers
from apps.administracao.models import ContratoGestk
from apps.core.models import Contabilidade, UsuarioAcesso


class ContratoGestkSerializer(serializers.ModelSerializer):
    """
    Serializer para Contratos GESTK
    """
    contabilidade_razao_social = serializers.CharField(source='contabilidade.razao_social', read_only=True)
    contabilidade_cnpj = serializers.CharField(source='contabilidade.cnpj', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    esta_vencido = serializers.BooleanField(read_only=True)
    esta_em_trial = serializers.BooleanField(read_only=True)
    dias_para_vencimento = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = ContratoGestk
        fields = [
            'id', 'contabilidade', 'contabilidade_razao_social', 'contabilidade_cnpj',
            'numero_contrato', 'data_inicio', 'data_termino', 'data_renovacao',
            'plano_servico', 'modulos_inclusos', 'limites_usuarios', 'limites_empresas',
            'limites_contratos_internos', 'valor_mensal', 'valor_anual', 'desconto_percentual',
            'dia_vencimento', 'status', 'motivo_suspensao', 'data_suspensao',
            'motivo_cancelamento', 'data_cancelamento', 'responsavel_financeiro_nome',
            'responsavel_financeiro_email', 'responsavel_financeiro_telefone',
            'endereco_cobranca', 'trial_ate', 'observacoes', 'created_at', 'updated_at',
            'created_by', 'created_by_username', 'esta_vencido', 'esta_em_trial', 'dias_para_vencimento'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    def validate_numero_contrato(self, value):
        """
        Valida se o número do contrato é único
        """
        if self.instance and self.instance.numero_contrato == value:
            return value
        
        if ContratoGestk.objects.filter(numero_contrato=value).exists():
            raise serializers.ValidationError("Já existe um contrato com este número.")
        
        return value
    
    def validate_data_termino(self, value):
        """
        Valida se a data de término é posterior à data de início
        """
        data_inicio = self.initial_data.get('data_inicio')
        if data_inicio and value and value <= data_inicio:
            raise serializers.ValidationError("Data de término deve ser posterior à data de início.")
        
        return value


class UsuarioAcessoSerializer(serializers.ModelSerializer):
    """
    Serializer para Acessos de Usuário
    """
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)
    usuario_email = serializers.CharField(source='usuario.email', read_only=True)
    usuario_nome_completo = serializers.CharField(source='usuario.get_full_name', read_only=True)
    contabilidade_razao_social = serializers.CharField(source='contabilidade.razao_social', read_only=True)
    contabilidade_cnpj = serializers.CharField(source='contabilidade.cnpj', read_only=True)
    contrato_id = serializers.CharField(source='contrato.id', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    esta_vencido = serializers.BooleanField(read_only=True)
    esta_ativo = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = UsuarioAcesso
        fields = [
            'id', 'usuario', 'usuario_username', 'usuario_email', 'usuario_nome_completo',
            'contabilidade', 'contabilidade_razao_social', 'contabilidade_cnpj',
            'contrato', 'contrato_id', 'empresa_cnpj', 'role', 'modulos_acesso',
            'data_inicio', 'data_fim', 'ativo', 'mfa_required', 'allowed_ip_ranges',
            'created_at', 'updated_at', 'created_by', 'created_by_username',
            'esta_vencido', 'esta_ativo'
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
    
    def validate(self, data):
        """
        Validação geral do acesso
        """
        # Verificar se pelo menos um escopo está definido (contrato ou empresa_cnpj)
        if not data.get('contrato') and not data.get('empresa_cnpj'):
            # Se não há escopo específico, permitir acesso total
            pass
        
        return data


class ContabilidadeAdministracaoSerializer(serializers.ModelSerializer):
    """
    Serializer para Contabilidades com informações de administração
    """
    contrato_gestk = serializers.SerializerMethodField()
    total_usuarios = serializers.SerializerMethodField()
    total_acessos = serializers.SerializerMethodField()
    acessos_ativos = serializers.SerializerMethodField()
    
    class Meta:
        model = Contabilidade
        fields = [
            'id', 'razao_social', 'nome_fantasia', 'cnpj', 'ativo',
            'responsavel_financeiro_nome', 'responsavel_financeiro_email',
            'responsavel_financeiro_telefone', 'suspensa_por_inadimplencia',
            'saldo_creditos', 'contrato_gestk', 'total_usuarios', 'total_acessos',
            'acessos_ativos', 'created_at', 'updated_at'
        ]
    
    def get_contrato_gestk(self, obj):
        """
        Retorna o contrato GESTK da contabilidade
        """
        contrato = obj.contrato_gestk.first() if hasattr(obj, 'contrato_gestk') else None
        if contrato:
            return ContratoGestkSerializer(contrato).data
        return None
    
    def get_total_usuarios(self, obj):
        """
        Retorna o total de usuários únicos com acesso à contabilidade
        """
        return obj.acessos_usuarios.values('usuario').distinct().count()
    
    def get_total_acessos(self, obj):
        """
        Retorna o total de acessos à contabilidade
        """
        return obj.acessos_usuarios.count()
    
    def get_acessos_ativos(self, obj):
        """
        Retorna o número de acessos ativos
        """
        return obj.acessos_usuarios.filter(ativo=True).count()