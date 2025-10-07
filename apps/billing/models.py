"""
Modelos para Sistema de Billing e Cobrança
"""

import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class Plano(models.Model):
    """
    Planos de serviço disponíveis
    """
    CICLO_CHOICES = [
        ('mensal', 'Mensal'),
        ('anual', 'Anual'),
        ('trimestral', 'Trimestral'),
        ('semestral', 'Semestral'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(
        _('Código do Plano'), 
        max_length=50, 
        unique=True,
        help_text="Código único do plano (ex: basic, pro, enterprise)"
    )
    nome = models.CharField(
        _('Nome do Plano'), 
        max_length=100,
        help_text="Nome amigável do plano"
    )
    descricao = models.TextField(
        _('Descrição'), 
        blank=True, 
        null=True,
        help_text="Descrição detalhada do plano"
    )
    
    # Preços
    preco_mensal = models.DecimalField(
        _('Preço Mensal'), 
        max_digits=10, 
        decimal_places=2,
        help_text="Preço mensal do plano"
    )
    preco_anual = models.DecimalField(
        _('Preço Anual'), 
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Preço anual do plano (se houver desconto)"
    )
    desconto_anual = models.DecimalField(
        _('Desconto Anual (%)'), 
        max_digits=5, 
        decimal_places=2, 
        default=0,
        help_text="Percentual de desconto para pagamento anual"
    )
    
    # Limites e recursos
    modulos_inclusos = models.JSONField(
        _('Módulos Inclusos'), 
        default=list,
        help_text="Lista de módulos inclusos no plano"
    )
    limites = models.JSONField(
        _('Limites do Plano'), 
        default=dict,
        help_text="Limites do plano (usuários, empresas, contratos, etc.)"
    )
    
    # Configurações
    ativo = models.BooleanField(
        _('Ativo'), 
        default=True,
        help_text="Se o plano está disponível para contratação"
    )
    ordem_exibicao = models.IntegerField(
        _('Ordem de Exibição'), 
        default=0,
        help_text="Ordem para exibição na lista de planos"
    )
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = _('Plano')
        verbose_name_plural = _('Planos')
        db_table = 'billing_planos'
        ordering = ['ordem_exibicao', 'nome']
    
    def __str__(self):
        return f"{self.nome} ({self.codigo})"
    
    @property
    def preco_anual_calculado(self):
        """
        Calcula o preço anual com desconto
        """
        if self.preco_anual:
            return self.preco_anual
        
        if self.desconto_anual > 0:
            desconto = (self.preco_mensal * 12) * (self.desconto_anual / 100)
            return (self.preco_mensal * 12) - desconto
        
        return self.preco_mensal * 12


class Assinatura(models.Model):
    """
    Assinaturas de planos pelas contabilidades
    """
    STATUS_CHOICES = [
        ('ativa', 'Ativa'),
        ('suspensa', 'Suspensa'),
        ('cancelada', 'Cancelada'),
        ('expirada', 'Expirada'),
        ('trial', 'Período de Teste'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contabilidade = models.ForeignKey(
        'core.Contabilidade',
        on_delete=models.CASCADE,
        related_name='assinaturas',
        help_text="Contabilidade que possui a assinatura"
    )
    plano = models.ForeignKey(
        Plano,
        on_delete=models.PROTECT,
        related_name='assinaturas',
        help_text="Plano contratado"
    )
    
    # Período da assinatura
    data_inicio = models.DateField(
        _('Data de Início'),
        help_text="Data de início da assinatura"
    )
    data_fim = models.DateField(
        _('Data de Fim'),
        null=True,
        blank=True,
        help_text="Data de fim da assinatura (NULL = sem prazo definido)"
    )
    data_renovacao = models.DateField(
        _('Data de Renovação'),
        null=True,
        blank=True,
        help_text="Data da próxima renovação"
    )
    
    # Status e controle
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='ativa',
        db_index=True
    )
    ciclo_cobranca = models.CharField(
        _('Ciclo de Cobrança'),
        max_length=20,
        choices=Plano.CICLO_CHOICES,
        default='mensal'
    )
    
    # Período de teste
    trial_ate = models.DateField(
        _('Trial Até'),
        null=True,
        blank=True,
        help_text="Data limite do período de teste"
    )
    
    # Valores
    valor_mensal = models.DecimalField(
        _('Valor Mensal'),
        max_digits=10,
        decimal_places=2,
        help_text="Valor mensal da assinatura"
    )
    valor_anual = models.DecimalField(
        _('Valor Anual'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Valor anual da assinatura"
    )
    
    # Configurações de cobrança
    dia_vencimento = models.IntegerField(
        _('Dia do Vencimento'),
        default=10,
        help_text="Dia do mês para vencimento das faturas"
    )
    desconto_percentual = models.DecimalField(
        _('Desconto (%)'),
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Desconto adicional aplicado"
    )
    
    # Motivos de suspensão/cancelamento
    motivo_suspensao = models.CharField(
        _('Motivo da Suspensão'),
        max_length=255,
        blank=True,
        null=True
    )
    data_suspensao = models.DateField(
        _('Data da Suspensão'),
        null=True,
        blank=True
    )
    motivo_cancelamento = models.CharField(
        _('Motivo do Cancelamento'),
        max_length=255,
        blank=True,
        null=True
    )
    data_cancelamento = models.DateField(
        _('Data do Cancelamento'),
        null=True,
        blank=True
    )
    
    # Metadados
    metadados = models.JSONField(
        _('Metadados'),
        default=dict,
        blank=True,
        help_text="Dados adicionais da assinatura"
    )
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'core.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assinaturas_criadas'
    )
    
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = _('Assinatura')
        verbose_name_plural = _('Assinaturas')
        db_table = 'billing_assinaturas'
        indexes = [
            models.Index(fields=['contabilidade', 'status']),
            models.Index(fields=['status', 'data_inicio']),
            models.Index(fields=['data_renovacao']),
            models.Index(fields=['trial_ate']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.contabilidade.razao_social} - {self.plano.nome}"
    
    @property
    def esta_ativa(self):
        """
        Verifica se a assinatura está ativa
        """
        if self.status != 'ativa':
            return False
        
        if self.data_fim and self.data_fim < timezone.now().date():
            return False
        
        return True
    
    @property
    def esta_em_trial(self):
        """
        Verifica se está em período de teste
        """
        if self.trial_ate and self.trial_ate >= timezone.now().date():
            return True
        return False
    
    @property
    def dias_para_vencimento(self):
        """
        Retorna quantos dias faltam para o vencimento
        """
        if not self.data_fim:
            return None
        
        delta = self.data_fim - timezone.now().date()
        return delta.days
    
    def suspender(self, motivo, data_suspensao=None):
        """
        Suspende a assinatura
        """
        if data_suspensao is None:
            data_suspensao = timezone.now().date()
        
        self.status = 'suspensa'
        self.motivo_suspensao = motivo
        self.data_suspensao = data_suspensao
        self.save()
    
    def cancelar(self, motivo, data_cancelamento=None):
        """
        Cancela a assinatura
        """
        if data_cancelamento is None:
            data_cancelamento = timezone.now().date()
        
        self.status = 'cancelada'
        self.motivo_cancelamento = motivo
        self.data_cancelamento = data_cancelamento
        self.save()
    
    def ativar(self):
        """
        Ativa a assinatura
        """
        self.status = 'ativa'
        self.motivo_suspensao = None
        self.data_suspensao = None
        self.save()


class Fatura(models.Model):
    """
    Faturas geradas para as assinaturas
    """
    STATUS_CHOICES = [
        ('aberta', 'Aberta'),
        ('paga', 'Paga'),
        ('vencida', 'Vencida'),
        ('cancelada', 'Cancelada'),
        ('estornada', 'Estornada'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assinatura = models.ForeignKey(
        Assinatura,
        on_delete=models.CASCADE,
        related_name='faturas',
        help_text="Assinatura relacionada"
    )
    
    # Identificação da fatura
    numero_fatura = models.CharField(
        _('Número da Fatura'),
        max_length=50,
        unique=True,
        help_text="Número único da fatura"
    )
    competencia = models.CharField(
        _('Competência'),
        max_length=7,
        db_index=True,
        help_text="Competência da fatura (YYYY-MM)"
    )
    
    # Valores
    valor_original = models.DecimalField(
        _('Valor Original'),
        max_digits=12,
        decimal_places=2,
        help_text="Valor original da fatura"
    )
    desconto = models.DecimalField(
        _('Desconto'),
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Desconto aplicado"
    )
    valor_final = models.DecimalField(
        _('Valor Final'),
        max_digits=12,
        decimal_places=2,
        help_text="Valor final da fatura"
    )
    
    # Datas
    data_emissao = models.DateField(
        _('Data de Emissão'),
        default=timezone.now,
        help_text="Data de emissão da fatura"
    )
    data_vencimento = models.DateField(
        _('Data de Vencimento'),
        help_text="Data de vencimento da fatura"
    )
    data_pagamento = models.DateField(
        _('Data de Pagamento'),
        null=True,
        blank=True,
        help_text="Data do pagamento"
    )
    
    # Status
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='aberta',
        db_index=True
    )
    
    # Dados de cobrança
    link_boleto = models.URLField(
        _('Link do Boleto'),
        blank=True,
        null=True,
        help_text="Link para pagamento via boleto"
    )
    linha_digitavel = models.CharField(
        _('Linha Digitável'),
        max_length=200,
        blank=True,
        null=True,
        help_text="Linha digitável do boleto"
    )
    codigo_barras = models.CharField(
        _('Código de Barras'),
        max_length=200,
        blank=True,
        null=True,
        help_text="Código de barras do boleto"
    )
    
    # Metadados
    metadados = models.JSONField(
        _('Metadados'),
        default=dict,
        blank=True,
        help_text="Dados adicionais da fatura"
    )
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = _('Fatura')
        verbose_name_plural = _('Faturas')
        db_table = 'billing_faturas'
        indexes = [
            models.Index(fields=['assinatura', 'status']),
            models.Index(fields=['status', 'data_vencimento']),
            models.Index(fields=['competencia']),
            models.Index(fields=['data_vencimento']),
        ]
        ordering = ['-data_emissao']
    
    def __str__(self):
        return f"Fatura {self.numero_fatura} - {self.assinatura.contabilidade.razao_social}"
    
    @property
    def esta_vencida(self):
        """
        Verifica se a fatura está vencida
        """
        return self.data_vencimento < timezone.now().date() and self.status == 'aberta'
    
    @property
    def dias_para_vencimento(self):
        """
        Retorna quantos dias faltam para o vencimento
        """
        delta = self.data_vencimento - timezone.now().date()
        return delta.days
    
    def marcar_como_paga(self, data_pagamento=None):
        """
        Marca a fatura como paga
        """
        if data_pagamento is None:
            data_pagamento = timezone.now().date()
        
        self.status = 'paga'
        self.data_pagamento = data_pagamento
        self.save()
    
    def cancelar(self):
        """
        Cancela a fatura
        """
        self.status = 'cancelada'
        self.save()


class Pagamento(models.Model):
    """
    Pagamentos realizados
    """
    METODO_CHOICES = [
        ('boleto', 'Boleto Bancário'),
        ('pix', 'PIX'),
        ('cartao_credito', 'Cartão de Crédito'),
        ('cartao_debito', 'Cartão de Débito'),
        ('transferencia', 'Transferência Bancária'),
        ('dinheiro', 'Dinheiro'),
    ]
    
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('processando', 'Processando'),
        ('confirmado', 'Confirmado'),
        ('estornado', 'Estornado'),
        ('falhou', 'Falhou'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fatura = models.ForeignKey(
        Fatura,
        on_delete=models.CASCADE,
        related_name='pagamentos',
        help_text="Fatura relacionada"
    )
    
    # Valores
    valor = models.DecimalField(
        _('Valor'),
        max_digits=12,
        decimal_places=2,
        help_text="Valor do pagamento"
    )
    metodo = models.CharField(
        _('Método de Pagamento'),
        max_length=20,
        choices=METODO_CHOICES,
        help_text="Método utilizado para o pagamento"
    )
    
    # Identificação da transação
    transacao_id = models.CharField(
        _('ID da Transação'),
        max_length=100,
        db_index=True,
        blank=True,
        null=True,
        help_text="ID da transação no gateway de pagamento"
    )
    referencia = models.CharField(
        _('Referência'),
        max_length=100,
        blank=True,
        null=True,
        help_text="Referência do pagamento"
    )
    
    # Status e datas
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pendente',
        db_index=True
    )
    data_pagamento = models.DateTimeField(
        _('Data do Pagamento'),
        null=True,
        blank=True,
        help_text="Data e hora do pagamento"
    )
    data_confirmacao = models.DateTimeField(
        _('Data de Confirmação'),
        null=True,
        blank=True,
        help_text="Data e hora da confirmação"
    )
    
    # Metadados
    metadados = models.JSONField(
        _('Metadados'),
        default=dict,
        blank=True,
        help_text="Dados adicionais do pagamento"
    )
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = _('Pagamento')
        verbose_name_plural = _('Pagamentos')
        db_table = 'billing_pagamentos'
        indexes = [
            models.Index(fields=['fatura', 'status']),
            models.Index(fields=['status', 'data_pagamento']),
            models.Index(fields=['transacao_id']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Pagamento {self.id} - {self.fatura.numero_fatura}"
    
    def confirmar(self, data_confirmacao=None):
        """
        Confirma o pagamento
        """
        if data_confirmacao is None:
            data_confirmacao = timezone.now()
        
        self.status = 'confirmado'
        self.data_confirmacao = data_confirmacao
        self.save()
        
        # Marcar fatura como paga
        self.fatura.marcar_como_paga(data_confirmacao.date())
    
    def estornar(self):
        """
        Estorna o pagamento
        """
        self.status = 'estornado'
        self.save()
        
        # Reverter status da fatura
        self.fatura.status = 'aberta'
        self.fatura.data_pagamento = None
        self.fatura.save()
