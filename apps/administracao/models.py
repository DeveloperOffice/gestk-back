"""
Modelos para o sistema de administração
ETLs 18, 19 e 20 - Usuários, Logs e Lançamentos
"""

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from apps.core.models import Contabilidade
from apps.pessoas.models import PessoaJuridica, PessoaFisica
import uuid


class BaseModeloMultitenant(models.Model):
    """
    Modelo base para todas as tabelas de administração
    
    Características:
    - contabilidade_id obrigatório para isolamento multitenant
    - Índices otimizados para performance
    - Validações de integridade
    - Auditoria automática
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contabilidade = models.ForeignKey(
        Contabilidade, 
        on_delete=models.CASCADE,
        db_index=True,
        help_text="Contabilidade responsável pelos dados"
    )
    data_criacao = models.DateTimeField(auto_now_add=True, db_index=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['contabilidade', 'data_criacao']),
        ]


class Usuario(models.Model):
    """
    ETL 18 - Usuários do sistema legado (ESTRUTURA CORRETA)
    
    Tabela acessória com idempotência:
    - 1 usuário por id_legado (global)
    - Sem contabilidade específica (usuário global)
    - Identificação por CNPJ na tabela UsuarioContabilidade
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_legado = models.CharField(
        max_length=50,
        unique=True,  # ← ÚNICO GLOBAL
        db_index=True,
        help_text="ID do usuário no sistema legado (i_usuario) - ÚNICO GLOBAL"
    )
    nome_usuario = models.CharField(
        max_length=100, 
        db_index=True,
        help_text="Nome do usuário no sistema legado"
    )
    ativo = models.BooleanField(
        default=True, 
        db_index=True,
        help_text="Se o usuário está ativo no sistema"
    )
    data_ultimo_acesso = models.DateTimeField(
        null=True, 
        blank=True, 
        db_index=True,
        help_text="Data do último acesso ao sistema"
    )
    tipo_usuario = models.CharField(
        max_length=20,
        default='NORMAL',
        db_index=True,
        help_text="Tipo do usuário (GERENTE, EXTERNO, NORMAL, etc.)"
    )
    data_criacao = models.DateTimeField(auto_now_add=True, db_index=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['ativo']),
            models.Index(fields=['nome_usuario']),
            models.Index(fields=['tipo_usuario']),
            models.Index(fields=['ativo', 'data_ultimo_acesso']),
        ]
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
    
    def __str__(self):
        return f"{self.nome_usuario} ({self.id_legado})"


class UsuarioContabilidade(BaseModeloMultitenant):
    """
    ETL 18 - Vínculos usuário-empresa-contabilidade (ESTRUTURA CORRETA)
    
    Identificação por CNPJ + Regra de Ouro:
    - Usuário global vinculado a contabilidades específicas
    - Múltiplos vínculos por usuário (diferentes empresas/contabilidades)
    - Datas de contrato incluídas
    """
    usuario = models.ForeignKey(
        Usuario, 
        on_delete=models.CASCADE, 
        db_index=True,
        help_text="Usuário que tem acesso à contabilidade"
    )
    empresa_cnpj = models.CharField(
        max_length=20,
        db_index=True,
        help_text="CNPJ da empresa que o usuário acessa"
    )
    empresa_nome = models.CharField(
        max_length=200,
        help_text="Nome da empresa que o usuário acessa"
    )
    data_inicio = models.DateField(
        db_index=True,
        help_text="Data de início do contrato"
    )
    data_fim = models.DateField(
        null=True, 
        blank=True, 
        db_index=True,
        help_text="Data de fim do contrato (NULL = ativo)"
    )
    ativo = models.BooleanField(
        default=True, 
        db_index=True,
        help_text="Se o vínculo está ativo"
    )
    modulos_acesso = models.JSONField(
        default=list,
        help_text="Lista de módulos que o usuário pode acessar"
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['contabilidade', 'usuario', 'data_inicio']),
            models.Index(fields=['contabilidade', 'ativo', 'data_inicio']),
            models.Index(fields=['usuario', 'ativo', 'data_inicio']),
            models.Index(fields=['empresa_cnpj', 'ativo']),
            models.Index(fields=['data_inicio', 'data_fim']),
        ]
        unique_together = ['contabilidade', 'usuario', 'empresa_cnpj']
        verbose_name = 'Vínculo Usuário-Contabilidade'
        verbose_name_plural = 'Vínculos Usuário-Contabilidade'
    
    def __str__(self):
        return f"{self.usuario.nome_usuario} → {self.contabilidade.razao_social} ({self.empresa_nome})"


class UsuarioModulo(BaseModeloMultitenant):
    """
    ETL 18 - Módulos acessíveis por usuário
    
    Mapeia quais módulos cada usuário pode acessar
    baseado no ROWGENERATOR e USCONFEMPRESAS
    """
    usuario = models.ForeignKey(
        Usuario, 
        on_delete=models.CASCADE, 
        db_index=True,
        help_text="Usuário que tem acesso ao módulo"
    )
    modulo_id = models.IntegerField(
        db_index=True,
        help_text="ID do módulo no sistema legado (ROW_NUM)"
    )
    modulo_nome = models.CharField(
        max_length=100,
        help_text="Nome do módulo"
    )
    ativo = models.BooleanField(
        default=True, 
        db_index=True,
        help_text="Se o módulo está ativo para o usuário"
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['contabilidade', 'usuario', 'modulo_id']),
            models.Index(fields=['contabilidade', 'modulo_id', 'ativo']),
            models.Index(fields=['usuario', 'ativo']),
        ]
        unique_together = ['contabilidade', 'usuario', 'modulo_id']
        verbose_name = 'Módulo do Usuário'
        verbose_name_plural = 'Módulos dos Usuários'
    
    def __str__(self):
        return f"{self.usuario.nome_usuario} - {self.modulo_nome}"


class LogAcesso(BaseModeloMultitenant):
    """
    ETL 19 - Logs de acesso dos usuários
    
    Registra acessos dos usuários ao sistema
    (dados sintéticos baseados nos vínculos)
    """
    usuario = models.ForeignKey(
        Usuario, 
        on_delete=models.CASCADE, 
        db_index=True,
        help_text="Usuário que fez o acesso"
    )
    data_acesso = models.DateTimeField(
        db_index=True,
        help_text="Data e hora do acesso"
    )
    tempo_sessao = models.DurationField(
        null=True, 
        blank=True,
        help_text="Tempo de duração da sessão"
    )
    ip_address = models.GenericIPAddressField(
        null=True, 
        blank=True,
        help_text="Endereço IP do usuário"
    )
    user_agent = models.TextField(
        null=True, 
        blank=True,
        help_text="User Agent do navegador"
    )
    modulo_acessado = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="Módulo que foi acessado"
    )
    acao_realizada = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Ação realizada pelo usuário"
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['contabilidade', 'usuario', 'data_acesso']),
            models.Index(fields=['contabilidade', 'data_acesso']),
            models.Index(fields=['usuario', 'data_acesso']),
            models.Index(fields=['data_acesso', 'modulo_acessado']),
        ]
        verbose_name = 'Log de Acesso'
        verbose_name_plural = 'Logs de Acesso'
    
    def __str__(self):
        return f"{self.usuario.nome_usuario} - {self.data_acesso}"


class LancamentoUsuario(BaseModeloMultitenant):
    """
    ETL 20 - Lançamentos realizados por usuário
    
    Registra lançamentos contábeis realizados por cada usuário
    com auditoria completa
    """
    usuario = models.ForeignKey(
        Usuario, 
        on_delete=models.CASCADE, 
        db_index=True,
        help_text="Usuário que realizou o lançamento"
    )
    data_lancamento = models.DateTimeField(
        db_index=True,
        help_text="Data e hora do lançamento"
    )
    tipo_operacao = models.CharField(
        max_length=50, 
        db_index=True,
        help_text="Tipo da operação realizada"
    )
    descricao = models.TextField(
        help_text="Descrição do lançamento"
    )
    valor = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Valor do lançamento (se aplicável)"
    )
    id_legado = models.CharField(
        max_length=100, 
        unique=True, 
        db_index=True,
        help_text="ID do lançamento no sistema legado"
    )
    modulo_origem = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="Módulo de origem do lançamento"
    )
    status = models.CharField(
        max_length=20,
        default='ATIVO',
        db_index=True,
        help_text="Status do lançamento"
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['contabilidade', 'usuario', 'data_lancamento']),
            models.Index(fields=['contabilidade', 'tipo_operacao', 'data_lancamento']),
            models.Index(fields=['usuario', 'data_lancamento']),
            models.Index(fields=['data_lancamento', 'status']),
            models.Index(fields=['modulo_origem', 'data_lancamento']),
        ]
        unique_together = ['contabilidade', 'id_legado']
        verbose_name = 'Lançamento do Usuário'
        verbose_name_plural = 'Lançamentos dos Usuários'
    
    def __str__(self):
        return f"{self.usuario.nome_usuario} - {self.tipo_operacao} - {self.data_lancamento}"


class AuditoriaSistema(BaseModeloMultitenant):
    """
    Tabela de auditoria para rastrear mudanças no sistema
    
    Registra todas as operações importantes para auditoria
    """
    usuario = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        db_index=True,
        help_text="Usuário que realizou a operação"
    )
    acao = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Tipo de ação realizada"
    )
    tabela_afetada = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Tabela que foi afetada"
    )
    registro_id = models.CharField(
        max_length=100,
        help_text="ID do registro afetado"
    )
    dados_anteriores = models.JSONField(
        null=True,
        blank=True,
        help_text="Dados antes da alteração"
    )
    dados_novos = models.JSONField(
        null=True,
        blank=True,
        help_text="Dados após a alteração"
    )
    ip_address = models.GenericIPAddressField(
        null=True, 
        blank=True,
        help_text="Endereço IP do usuário"
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['contabilidade', 'usuario', 'data_criacao']),
            models.Index(fields=['contabilidade', 'acao', 'data_criacao']),
            models.Index(fields=['tabela_afetada', 'data_criacao']),
            models.Index(fields=['data_criacao']),
        ]
        verbose_name = 'Auditoria do Sistema'
        verbose_name_plural = 'Auditorias do Sistema'
    
    def __str__(self):
        return f"{self.acao} - {self.tabela_afetada} - {self.data_criacao}"


class ContratoGestk(models.Model):
    """
    Contratos dos escritórios de contabilidade (clientes da GESTK)
    Diferente de pessoas.Contrato (clientes internos das contabilidades)
    """
    STATUS_CHOICES = [
        ('trial', 'Período de Teste'),
        ('ativo', 'Ativo'),
        ('suspenso', 'Suspenso'),
        ('cancelado', 'Cancelado'),
        ('vencido', 'Vencido')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Cliente da GESTK (escritório de contabilidade)
    contabilidade = models.OneToOneField(
        Contabilidade, 
        on_delete=models.CASCADE,
        related_name='contrato_gestk',
        help_text="Escritório de contabilidade cliente da GESTK"
    )
    
    # Dados do contrato
    numero_contrato = models.CharField(
        max_length=50, 
        unique=True, 
        db_index=True,
        help_text="Número único do contrato GESTK"
    )
    data_inicio = models.DateField(
        db_index=True,
        help_text="Data de início do contrato"
    )
    data_termino = models.DateField(
        null=True, 
        blank=True, 
        db_index=True,
        help_text="Data de término do contrato (NULL = sem prazo definido)"
    )
    data_renovacao = models.DateField(
        null=True, 
        blank=True,
        help_text="Data de renovação do contrato"
    )
    
    # Plano e serviços
    plano_servico = models.CharField(
        max_length=50, 
        db_index=True,
        help_text="Código do plano de serviço (basic, pro, enterprise)"
    )
    modulos_inclusos = models.JSONField(
        default=list,
        help_text="Lista de módulos inclusos no contrato"
    )
    limites_usuarios = models.IntegerField(
        default=5,
        help_text="Limite de usuários simultâneos"
    )
    limites_empresas = models.IntegerField(
        default=10,
        help_text="Limite de empresas que podem ser gerenciadas"
    )
    limites_contratos_internos = models.IntegerField(
        default=100,
        help_text="Limite de contratos internos (clientes da contabilidade)"
    )
    
    # Valores e cobrança
    valor_mensal = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Valor mensal do contrato"
    )
    valor_anual = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Valor anual do contrato (se houver desconto)"
    )
    desconto_percentual = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        help_text="Percentual de desconto aplicado"
    )
    dia_vencimento = models.IntegerField(
        default=10,
        help_text="Dia do mês para vencimento das faturas"
    )
    
    # Status e controle
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES,
        default='ativo',
        db_index=True,
        help_text="Status atual do contrato"
    )
    
    # Motivos de suspensão/cancelamento
    motivo_suspensao = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text="Motivo da suspensão do contrato"
    )
    data_suspensao = models.DateField(
        null=True, 
        blank=True,
        help_text="Data da suspensão do contrato"
    )
    motivo_cancelamento = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text="Motivo do cancelamento do contrato"
    )
    data_cancelamento = models.DateField(
        null=True, 
        blank=True,
        help_text="Data do cancelamento do contrato"
    )
    
    # Dados de cobrança
    responsavel_financeiro_nome = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Nome do responsável financeiro"
    )
    responsavel_financeiro_email = models.EmailField(
        blank=True, 
        null=True,
        help_text="E-mail do responsável financeiro"
    )
    responsavel_financeiro_telefone = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        help_text="Telefone do responsável financeiro"
    )
    
    # Endereço de cobrança
    endereco_cobranca = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Endereço para cobrança (JSON com logradouro, cidade, etc.)"
    )
    
    # Configurações especiais
    trial_ate = models.DateField(
        null=True, 
        blank=True,
        help_text="Data limite do período de teste"
    )
    observacoes = models.TextField(
        blank=True, 
        null=True,
        help_text="Observações adicionais sobre o contrato"
    )
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'core.Usuario', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='contratos_gestk_criados',
        help_text="Usuário que criou o contrato"
    )
    
    class Meta:
        verbose_name = 'Contrato GESTK'
        verbose_name_plural = 'Contratos GESTK'
        db_table = 'administracao_contratos_gestk'
        indexes = [
            models.Index(fields=['status', 'data_inicio']),
            models.Index(fields=['plano_servico', 'status']),
            models.Index(fields=['data_termino']),
            models.Index(fields=['trial_ate']),
            models.Index(fields=['numero_contrato']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Contrato {self.numero_contrato} - {self.contabilidade.razao_social}"
    
    @property
    def esta_vencido(self):
        """Verifica se o contrato está vencido"""
        if self.data_termino and self.data_termino < timezone.now().date():
            return True
        return False
    
    @property
    def esta_em_trial(self):
        """Verifica se o contrato está em período de teste"""
        if self.trial_ate and self.trial_ate >= timezone.now().date():
            return True
        return False
    
    @property
    def dias_para_vencimento(self):
        """Retorna quantos dias faltam para o vencimento"""
        if not self.data_termino:
            return None
        delta = self.data_termino - timezone.now().date()
        return delta.days
    
    def suspender(self, motivo, data_suspensao=None):
        """Suspende o contrato"""
        if data_suspensao is None:
            data_suspensao = timezone.now().date()
        
        self.status = 'suspenso'
        self.motivo_suspensao = motivo
        self.data_suspensao = data_suspensao
        self.save()
    
    def cancelar(self, motivo, data_cancelamento=None):
        """Cancela o contrato"""
        if data_cancelamento is None:
            data_cancelamento = timezone.now().date()
        
        self.status = 'cancelado'
        self.motivo_cancelamento = motivo
        self.data_cancelamento = data_cancelamento
        self.save()
    
    def ativar(self):
        """Ativa o contrato"""
        self.status = 'ativo'
        self.motivo_suspensao = None
        self.data_suspensao = None
        self.save()