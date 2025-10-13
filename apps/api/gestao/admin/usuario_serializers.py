"""
Serializers para gerenciamento de Usuarios por ADMIN
"""
from rest_framework import serializers
from apps.core.models import Usuario, Contabilidade
from django.contrib.auth.hashers import make_password
from django.db import transaction


class UsuarioListSerializer(serializers.ModelSerializer):
    """Serializer para listagem de usuários"""
    contabilidade_nome = serializers.CharField(source='contabilidade.razao_social', read_only=True)
    tipo_usuario_display = serializers.CharField(source='get_tipo_usuario_display', read_only=True)
    esta_ativo = serializers.SerializerMethodField()
    total_modulos = serializers.SerializerMethodField()
    
    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'cpf', 'contabilidade', 'contabilidade_nome',
            'tipo_usuario', 'tipo_usuario_display',
            'ativo', 'esta_ativo', 'is_active',
            'modulos_acessiveis', 'total_modulos',
            'pode_executar_etl', 'pode_administrar_usuarios',
            'pode_ver_dados_sensiveis',
            'date_joined', 'last_login', 'data_ultima_atividade'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']
    
    def get_esta_ativo(self, obj):
        """Verifica se o usuário está realmente ativo"""
        return obj.ativo and obj.is_active
    
    def get_total_modulos(self, obj):
        """Retorna o total de módulos acessíveis"""
        return len(obj.modulos_acessiveis) if obj.modulos_acessiveis else 0


class UsuarioDetailSerializer(serializers.ModelSerializer):
    """Serializer para detalhamento de usuário"""
    contabilidade_info = serializers.SerializerMethodField()
    tipo_usuario_display = serializers.CharField(source='get_tipo_usuario_display', read_only=True)
    esta_ativo = serializers.SerializerMethodField()
    ultima_contabilidade_nome = serializers.CharField(
        source='ultima_contabilidade.razao_social', 
        read_only=True
    )
    estatisticas = serializers.SerializerMethodField()
    
    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'cpf', 'contabilidade', 'contabilidade_info',
            'ultima_contabilidade', 'ultima_contabilidade_nome',
            'tipo_usuario', 'tipo_usuario_display',
            'ativo', 'esta_ativo', 'is_active', 'is_staff',
            'modulos_acessiveis',
            'pode_executar_etl', 'pode_administrar_usuarios',
            'pode_ver_dados_sensiveis',
            'mfa_enabled', 'token_version',
            'data_ultima_atividade', 'ip_ultimo_acesso',
            'date_joined', 'last_login',
            'estatisticas'
        ]
        read_only_fields = [
            'id', 'date_joined', 'last_login', 
            'data_ultima_atividade', 'ip_ultimo_acesso'
        ]
    
    def get_contabilidade_info(self, obj):
        """Retorna informações da contabilidade"""
        if not obj.contabilidade:
            return None
        return {
            'id': str(obj.contabilidade.id),
            'razao_social': obj.contabilidade.razao_social,
            'cnpj': obj.contabilidade.cnpj,
            'ativo': obj.contabilidade.ativo
        }
    
    def get_esta_ativo(self, obj):
        """Verifica se o usuário está realmente ativo"""
        return obj.ativo and obj.is_active
    
    def get_estatisticas(self, obj):
        """Retorna estatísticas do usuário"""
        return {
            'total_modulos': len(obj.modulos_acessiveis) if obj.modulos_acessiveis else 0,
            'tem_mfa': obj.mfa_enabled,
            'versao_token': obj.token_version,
            'dias_desde_cadastro': (timezone.now() - obj.date_joined).days if obj.date_joined else 0,
            'dias_desde_ultimo_login': (timezone.now() - obj.last_login).days if obj.last_login else None,
        }


class UsuarioCreateSerializer(serializers.ModelSerializer):
    """Serializer para criação de usuário"""
    password = serializers.CharField(
        write_only=True, 
        required=True,
        style={'input_type': 'password'},
        help_text="Senha do usuário (será criptografada)"
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Confirmação da senha"
    )
    
    class Meta:
        model = Usuario
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'cpf',
            'contabilidade', 'tipo_usuario',
            'modulos_acessiveis',
            'pode_executar_etl', 'pode_administrar_usuarios',
            'pode_ver_dados_sensiveis',
            'ativo', 'is_active', 'is_staff'
        ]
    
    def validate_username(self, value):
        """Valida se o username já existe"""
        if Usuario.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username já está em uso.")
        return value
    
    def validate_email(self, value):
        """Valida se o email já existe"""
        if value and Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email já está em uso.")
        return value
    
    def validate_cpf(self, value):
        """Valida se o CPF já existe"""
        if value and Usuario.objects.filter(cpf=value).exists():
            raise serializers.ValidationError("CPF já está cadastrado.")
        return value
    
    def validate_contabilidade(self, value):
        """Valida se a contabilidade está ativa"""
        if value and not value.ativo:
            raise serializers.ValidationError("Contabilidade está inativa.")
        return value
    
    def validate_tipo_usuario(self, value):
        """Admin não pode criar superusuários"""
        if value == 'superuser':
            raise serializers.ValidationError(
                "Apenas SUPERUSER pode criar outros superusuários."
            )
        return value
    
    def validate(self, data):
        """Validações gerais"""
        # Validar senhas
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': 'As senhas não coincidem.'
            })
        
        # Validar módulos acessíveis
        modulos_validos = [escolha[0] for escolha in Usuario.MODULO_CHOICES]
        modulos = data.get('modulos_acessiveis', [])
        if modulos:
            for modulo in modulos:
                if modulo not in modulos_validos:
                    raise serializers.ValidationError({
                        'modulos_acessiveis': f'Módulo inválido: {modulo}'
                    })
        
        return data
    
    def create(self, validated_data):
        """Cria um novo usuário"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        # Criar usuário
        usuario = Usuario.objects.create(**validated_data)
        usuario.set_password(password)
        usuario.save()
        
        return usuario


class UsuarioUpdateSerializer(serializers.ModelSerializer):
    """Serializer para atualização de usuário"""
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={'input_type': 'password'},
        help_text="Nova senha (deixe em branco para não alterar)"
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={'input_type': 'password'},
        help_text="Confirmação da nova senha"
    )
    
    class Meta:
        model = Usuario
        fields = [
            'email', 'first_name', 'last_name', 'cpf',
            'password', 'password_confirm',
            'tipo_usuario', 'modulos_acessiveis',
            'pode_executar_etl', 'pode_administrar_usuarios',
            'pode_ver_dados_sensiveis',
            'ativo', 'is_active', 'is_staff'
        ]
    
    def validate_email(self, value):
        """Valida se o email já existe (exceto o próprio)"""
        if value:
            usuario = self.instance
            if Usuario.objects.filter(email=value).exclude(id=usuario.id).exists():
                raise serializers.ValidationError("Email já está em uso.")
        return value
    
    def validate_cpf(self, value):
        """Valida se o CPF já existe (exceto o próprio)"""
        if value:
            usuario = self.instance
            if Usuario.objects.filter(cpf=value).exclude(id=usuario.id).exists():
                raise serializers.ValidationError("CPF já está cadastrado.")
        return value
    
    def validate_tipo_usuario(self, value):
        """Admin não pode alterar para superuser"""
        if value == 'superuser' and self.instance.tipo_usuario != 'superuser':
            raise serializers.ValidationError(
                "Apenas SUPERUSER pode promover usuários a superusuário."
            )
        return value
    
    def validate(self, data):
        """Validações gerais"""
        # Validar senhas se fornecidas
        password = data.get('password', '').strip()
        password_confirm = data.get('password_confirm', '').strip()
        
        if password or password_confirm:
            if password != password_confirm:
                raise serializers.ValidationError({
                    'password_confirm': 'As senhas não coincidem.'
                })
        
        # Validar módulos acessíveis
        modulos_validos = [escolha[0] for escolha in Usuario.MODULO_CHOICES]
        modulos = data.get('modulos_acessiveis')
        if modulos is not None:
            for modulo in modulos:
                if modulo not in modulos_validos:
                    raise serializers.ValidationError({
                        'modulos_acessiveis': f'Módulo inválido: {modulo}'
                    })
        
        return data
    
    def update(self, instance, validated_data):
        """Atualiza o usuário"""
        password = validated_data.pop('password', '').strip()
        validated_data.pop('password_confirm', None)
        
        # Atualizar campos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Atualizar senha se fornecida
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


from django.utils import timezone
