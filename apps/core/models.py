import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

class Contabilidade(models.Model):
    """Modelo principal para multi-tenancy - representa escritórios de contabilidade"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    razao_social = models.TextField(_('Razão Social'))
    nome_fantasia = models.TextField(_('Nome Fantasia'), blank=True, null=True)
    cnpj = models.CharField(_('CNPJ'), max_length=14, unique=True)
    id_legado = models.IntegerField(_('ID Legado'), unique=True, null=True, blank=True, help_text="ID da empresa no sistema Sybase (BETHADBA.HRCONTRATO.CODI_EMP)")
    endereco = models.CharField(_('Endereço'), max_length=255, blank=True, null=True)
    telefone = models.CharField(_('Telefone'), max_length=20, blank=True, null=True)
    email = models.EmailField(_('E-mail'), blank=True, null=True)
    ativo = models.BooleanField(_('Ativo'), default=True)
    
    # Dados de cobrança
    responsavel_financeiro_nome = models.CharField(
        _('Responsável Financeiro - Nome'), 
        max_length=100, 
        blank=True, 
        null=True
    )
    responsavel_financeiro_email = models.EmailField(
        _('Responsável Financeiro - E-mail'), 
        blank=True, 
        null=True
    )
    responsavel_financeiro_telefone = models.CharField(
        _('Responsável Financeiro - Telefone'), 
        max_length=20, 
        blank=True, 
        null=True
    )
    inscricao_estadual = models.CharField(
        _('Inscrição Estadual'), 
        max_length=20, 
        blank=True, 
        null=True
    )
    endereco_cobranca = models.JSONField(
        _('Endereço de Cobrança'), 
        default=dict, 
        blank=True,
        help_text="Endereço para cobrança (JSON com logradouro, cidade, etc.)"
    )
    suspensa_por_inadimplencia = models.BooleanField(
        _('Suspensa por Inadimplência'), 
        default=False
    )
    saldo_creditos = models.DecimalField(
        _('Saldo de Créditos'), 
        max_digits=10, 
        decimal_places=2, 
        default=0
    )
    
    created_at = models.DateTimeField(_('Data de Criação'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Data de Atualização'), auto_now=True)
    
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = _('Contabilidade')
        verbose_name_plural = _('Contabilidades')
        db_table = 'core_contabilidades'
        ordering = ['razao_social']
        indexes = [
            models.Index(fields=['cnpj']),
            models.Index(fields=['ativo']),
            models.Index(fields=['id_legado']),
        ]
    
    def __str__(self):
        return f"{self.razao_social} ({self.cnpj})"

class Usuario(AbstractUser):
    """
    Usuário customizado do GESTK com referência obrigatória à contabilidade (tenant)
    """
    # Tipos de usuário
    TIPO_USUARIO_CHOICES = [
        ('superuser', 'Superusuário'),
        ('admin', 'Administrador'),
        ('operacional', 'Operacional'),
        ('etl', 'ETL'),
        ('readonly', 'Somente Leitura'),
    ]
    
    # Módulos do sistema
    MODULO_CHOICES = [
        ('gestao', 'Gestão'),
        ('dashboards', 'Dashboards'),
        ('fiscal', 'Fiscal'),
        ('contabil', 'Contábil'),
        ('rh', 'Recursos Humanos'),
        ('administracao', 'Administração'),
        ('etl', 'ETL'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relacionamento com contabilidade (obrigatório)
    contabilidade = models.ForeignKey(
        Contabilidade, 
        on_delete=models.CASCADE,
        related_name='usuarios',
        verbose_name=_('Contabilidade'),
        null=True, blank=True  # Temporário para superusuários
    )
    
    # Contabilidade mais recentemente acessada (para multi-tenant)
    ultima_contabilidade = models.ForeignKey(
        Contabilidade,
        on_delete=models.SET_NULL,
        related_name='usuarios_ultimo_acesso',
        verbose_name=_('Última Contabilidade'),
        null=True,
        blank=True,
        help_text="Contabilidade mais recentemente acessada pelo usuário"
    )
    
    # Dados pessoais
    cpf = models.CharField(_('CPF'), max_length=11, unique=True, null=True, blank=True)
    ativo = models.BooleanField(_('Ativo'), default=True)
    
    # Sistema de permissões customizado
    tipo_usuario = models.CharField(
        _('Tipo de Usuário'),
        max_length=20,
        choices=TIPO_USUARIO_CHOICES,
        default='operacional'
    )
    
    modulos_acessiveis = models.JSONField(
        _('Módulos Acessíveis'),
        default=list,
        help_text="Lista de módulos que o usuário pode acessar"
    )
    
    # Permissões específicas
    pode_executar_etl = models.BooleanField(
        _('Pode Executar ETL'),
        default=False,
        help_text="Pode executar comandos de ETL"
    )
    
    pode_administrar_usuarios = models.BooleanField(
        _('Pode Administrar Usuários'),
        default=False,
        help_text="Pode criar/editar usuários da contabilidade"
    )
    
    pode_ver_dados_sensiveis = models.BooleanField(
        _('Pode Ver Dados Sensíveis'),
        default=False,
        help_text="Pode visualizar dados sensíveis (salários, etc.)"
    )
    
    # Campos de segurança
    token_version = models.IntegerField(
        _('Versão do Token'),
        default=1,
        help_text="Versão do token para invalidação global"
    )
    
    mfa_enabled = models.BooleanField(
        _('MFA Habilitado'),
        default=False,
        help_text="Autenticação de dois fatores habilitada"
    )
    
    mfa_secret = models.CharField(
        _('Secret MFA'),
        max_length=32,
        blank=True,
        help_text="Chave secreta para MFA"
    )
    
    # Campos de auditoria
    data_ultima_atividade = models.DateTimeField(
        _('Última Atividade'),
        null=True, blank=True
    )
    
    ip_ultimo_acesso = models.GenericIPAddressField(
        _('IP do Último Acesso'),
        null=True, blank=True
    )
    
    # Fix para conflito de related_name
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('Groups'),
        blank=True,
        help_text=_('The groups this user belongs to.'),
        related_name='gestk_usuario_set',
        related_query_name='gestk_usuario',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('User permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='gestk_usuario_set',
        related_query_name='gestk_usuario',
    )
    
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = _('Usuário')
        verbose_name_plural = _('Usuários')
        db_table = 'core_usuarios'
        indexes = [
            models.Index(fields=['contabilidade', 'username']),
            models.Index(fields=['cpf']),
            models.Index(fields=['tipo_usuario']),
            models.Index(fields=['ativo']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_tipo_usuario_display()})"
    
    def tem_acesso_modulo(self, modulo):
        """Verifica se o usuário tem acesso a um módulo específico"""
        return modulo in self.modulos_acessiveis
    
    def pode_executar_comando_etl(self, comando):
        """Verifica se pode executar um comando ETL específico"""
        if not self.pode_executar_etl:
            return False
        
        # Lista de comandos ETL permitidos por tipo de usuário
        comandos_permitidos = {
            'superuser': ['*'],
            'admin': ['etl_*'],
            'etl': ['etl_*'],
        }
        
        return any(
            comando.startswith(permitido.replace('*', ''))
            for permitido in comandos_permitidos.get(self.tipo_usuario, [])
        )
    
    def is_superuser_gestk(self):
        """Verifica se é superusuário do GESTK (não apenas Django)"""
        return self.tipo_usuario == 'superuser'
    
    def is_admin_gestk(self):
        """Verifica se é administrador do GESTK"""
        return self.tipo_usuario == 'admin'
    
    def is_etl_user(self):
        """Verifica se é usuário de ETL"""
        return self.tipo_usuario == 'etl'


class UsuarioAcesso(models.Model):
    """
    Vínculos de usuários com contabilidades e escopos específicos
    Permite que um usuário PF tenha acesso a múltiplas contabilidades
    """
    ROLE_CHOICES = [
        ('superuser', 'Superusuário'),
        ('admin', 'Administrador'),
        ('operacional', 'Operacional'),
        ('etl', 'ETL'),
        ('readonly', 'Somente Leitura'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Usuário e contabilidade
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='acessos',
        db_index=True,
        help_text="Usuário que tem acesso"
    )
    contabilidade = models.ForeignKey(
        Contabilidade,
        on_delete=models.CASCADE,
        related_name='acessos_usuarios',
        db_index=True,
        help_text="Contabilidade acessível"
    )
    
    # Escopo do acesso (opcional - se não especificado, acesso total à contabilidade)
    contrato = models.ForeignKey(
        'pessoas.Contrato',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Contrato específico (se o acesso for restrito a um cliente)"
    )
    empresa_cnpj = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True,
        help_text="CNPJ da empresa específica (se o acesso for restrito)"
    )
    
    # Perfil e permissões
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='operacional',
        db_index=True,
        help_text="Papel do usuário nesta contabilidade"
    )
    modulos_acesso = models.JSONField(
        default=list,
        help_text="Módulos que o usuário pode acessar nesta contabilidade"
    )
    
    # Janela de validade
    data_inicio = models.DateField(
        db_index=True,
        help_text="Data de início do acesso"
    )
    data_fim = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Data de fim do acesso (NULL = sem prazo definido)"
    )
    ativo = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Se o acesso está ativo"
    )
    
    # Segurança
    mfa_required = models.BooleanField(
        default=False,
        help_text="MFA obrigatório para este acesso"
    )
    allowed_ip_ranges = models.JSONField(
        default=list,
        blank=True,
        help_text="Faixas de IP permitidas (CIDR)"
    )
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acessos_criados',
        help_text="Usuário que criou este acesso"
    )
    
    class Meta:
        verbose_name = 'Acesso de Usuário'
        verbose_name_plural = 'Acessos de Usuários'
        db_table = 'core_usuario_acessos'
        unique_together = [
            ('usuario', 'contabilidade', 'contrato'),
            ('usuario', 'contabilidade', 'empresa_cnpj'),
        ]
        indexes = [
            models.Index(fields=['usuario', 'ativo', 'data_inicio']),
            models.Index(fields=['contabilidade', 'ativo', 'data_inicio']),
            models.Index(fields=['role', 'ativo']),
            models.Index(fields=['data_inicio', 'data_fim']),
            models.Index(fields=['empresa_cnpj', 'ativo']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        escopo = ""
        if self.contrato:
            escopo = f" (Contrato: {self.contrato.id})"
        elif self.empresa_cnpj:
            escopo = f" (Empresa: {self.empresa_cnpj})"
        
        return f"{self.usuario.username} → {self.contabilidade.razao_social}{escopo}"
    
    @property
    def esta_vencido(self):
        """Verifica se o acesso está vencido"""
        if self.data_fim and self.data_fim < timezone.now().date():
            return True
        return False
    
    @property
    def esta_ativo(self):
        """Verifica se o acesso está ativo e dentro da validade"""
        if not self.ativo:
            return False
        if self.esta_vencido:
            return False
        if self.data_inicio > timezone.now().date():
            return False
        return True
    
    def tem_acesso_modulo(self, modulo):
        """Verifica se tem acesso a um módulo específico"""
        return modulo in self.modulos_acesso
    
    def tem_acesso_contrato(self, contrato_id):
        """Verifica se tem acesso a um contrato específico"""
        if not self.contrato:
            return True  # Acesso total à contabilidade
        return str(self.contrato.id) == str(contrato_id)
    
    def tem_acesso_empresa(self, cnpj):
        """Verifica se tem acesso a uma empresa específica"""
        if not self.empresa_cnpj:
            return True  # Acesso total à contabilidade
        return self.empresa_cnpj == cnpj
    
    def ativar(self):
        """Ativa o acesso"""
        self.ativo = True
        self.save()
    
    def desativar(self):
        """Desativa o acesso"""
        self.ativo = False
        self.save()
    
    def estender_vigencia(self, nova_data_fim):
        """Estende a vigência do acesso"""
        self.data_fim = nova_data_fim
        self.save()