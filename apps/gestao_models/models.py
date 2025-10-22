"""
Modelos para Gestão de Carteira e Faturamento
"""

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from simple_history.models import HistoricalRecords


class FaturamentoEmpresa(models.Model):
    """
    Faturamento mensal das empresas clientes
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Multi-tenancy
    contabilidade = models.ForeignKey(
        'core.Contabilidade',
        on_delete=models.CASCADE,
        related_name='faturamentos_empresas',
        verbose_name=_('Contabilidade')
    )
    
    # Empresa (GenericForeignKey para PessoaJuridica ou PessoaFisica)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={'model__in': ['pessoajuridica', 'pessoafisica']}
    )
    object_id = models.UUIDField()
    empresa = GenericForeignKey('content_type', 'object_id')
    
    # Período
    ano = models.IntegerField(_('Ano'), db_index=True)
    mes = models.IntegerField(_('Mês'), db_index=True)
    
    # Valores de faturamento
    total_saidas = models.DecimalField(
        _('Total Saídas'),
        max_digits=15,
        decimal_places=2,
        default=0
    )
    total_servicos = models.DecimalField(
        _('Total Serviços'),
        max_digits=15,
        decimal_places=2,
        default=0
    )
    total_geral = models.DecimalField(
        _('Total Geral'),
        max_digits=15,
        decimal_places=2,
        default=0
    )
    
    # Metadados
    data_importacao = models.DateTimeField(
        _('Data de Importação'),
        auto_now_add=True
    )
    data_atualizacao = models.DateTimeField(
        _('Data de Atualização'),
        auto_now=True
    )
    
    # Auditoria
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = _('Faturamento da Empresa')
        verbose_name_plural = _('Faturamentos das Empresas')
        db_table = 'gestao_faturamento_empresas'
        unique_together = ['contabilidade', 'content_type', 'object_id', 'ano', 'mes']
        indexes = [
            models.Index(fields=['contabilidade', 'ano', 'mes']),
            models.Index(fields=['ano', 'mes']),
            models.Index(fields=['data_importacao']),
        ]
        ordering = ['-ano', '-mes', 'contabilidade__razao_social']
    
    def __str__(self):
        empresa_nome = self.empresa.razao_social if hasattr(self.empresa, 'razao_social') else self.empresa.nome_completo
        return f"{empresa_nome} - {self.ano}/{self.mes:02d} - R$ {self.total_geral:,.2f}"
    
    def save(self, *args, **kwargs):
        """Calcula total_geral automaticamente"""
        self.total_geral = self.total_saidas + self.total_servicos
        super().save(*args, **kwargs)
    
    @property
    def empresa_nome(self):
        """Retorna nome da empresa"""
        if hasattr(self.empresa, 'razao_social'):
            return self.empresa.razao_social
        elif hasattr(self.empresa, 'nome_completo'):
            return self.empresa.nome_completo
        return str(self.empresa)
    
    @property
    def empresa_cnpj_cpf(self):
        """Retorna CNPJ ou CPF da empresa"""
        if hasattr(self.empresa, 'cnpj'):
            return self.empresa.cnpj
        elif hasattr(self.empresa, 'cpf'):
            return self.empresa.cpf
        return None
