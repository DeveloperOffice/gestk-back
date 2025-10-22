"""
Serializers para endpoints de gestão
"""

from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from apps.core.models import Contabilidade, Usuario
from apps.pessoas.models import PessoaJuridica, PessoaFisica, Contrato
from apps.contabil.models import LancamentoContabil
from apps.fiscal.models import NotaFiscal
from apps.funcionarios.models import Funcionario


class ContabilidadeSerializer(serializers.ModelSerializer):
    """Serializer para contabilidades"""
    
    class Meta:
        model = Contabilidade
        fields = ['id', 'cnpj', 'razao_social', 'nome_fantasia']


class ClienteSerializer(serializers.Serializer):
    """Serializer para clientes (PJ/PF)"""
    
    id = serializers.UUIDField(read_only=True)
    tipo = serializers.CharField(read_only=True)
    cnpj_cpf = serializers.CharField(read_only=True)
    razao_social_nome = serializers.CharField(read_only=True)
    nome_fantasia = serializers.CharField(read_only=True, allow_null=True)
    email = serializers.EmailField(read_only=True, allow_null=True)
    telefone = serializers.CharField(read_only=True, allow_null=True)
    cidade = serializers.CharField(read_only=True, allow_null=True)
    uf = serializers.CharField(read_only=True, allow_null=True)
    ativo = serializers.BooleanField(read_only=True)
    data_inicio_contrato = serializers.DateField(read_only=True, allow_null=True)
    valor_honorario = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)


class ResponsavelSerializer(serializers.Serializer):
    """Serializer para responsável legal"""
    nome = serializers.CharField()
    email = serializers.EmailField(allow_null=True)
    telefone = serializers.CharField(allow_null=True)
    cpf = serializers.CharField(allow_null=True)


class ClienteListagemSerializer(serializers.Serializer):
    """Serializer para lista de clientes no dashboard"""
    id = serializers.UUIDField()
    razao_social = serializers.CharField()
    nome_fantasia = serializers.CharField(allow_null=True)
    cnpj = serializers.CharField()
    status = serializers.CharField()
    regime_fiscal = serializers.CharField(allow_null=True)
    ramo_atividade = serializers.CharField(allow_null=True)
    data_inicio = serializers.DateField(allow_null=True)
    data_fim = serializers.DateField(allow_null=True)
    valor_mensal = serializers.DecimalField(max_digits=15, decimal_places=2, allow_null=True)
    responsavel = ResponsavelSerializer(allow_null=True)


class CarteiraClientesSerializer(serializers.Serializer):
    """Serializer para análise de carteira de clientes"""
    
    contabilidade = ContabilidadeSerializer(read_only=True)
    total_clientes = serializers.IntegerField(read_only=True)
    clientes_ativos = serializers.IntegerField(read_only=True)
    clientes_inativos = serializers.IntegerField(read_only=True)
    clientes_novos = serializers.IntegerField(read_only=True)
    clientes_sem_movimentacao = serializers.IntegerField(read_only=True)
    percentual_ativo = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)


class CarteiraCategoriasSerializer(serializers.Serializer):
    """Serializer para categorias da carteira"""
    
    contabilidade = ContabilidadeSerializer(read_only=True)
    regime_fiscal = serializers.CharField(read_only=True)
    ramo_atividade = serializers.CharField(read_only=True)
    total_clientes = serializers.IntegerField(read_only=True)
    percentual = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)


class CarteiraEvolucaoSerializer(serializers.Serializer):
    """Serializer para evolução da carteira"""
    
    contabilidade = ContabilidadeSerializer(read_only=True)
    mes_ano = serializers.CharField(read_only=True)
    total_clientes = serializers.IntegerField(read_only=True)
    clientes_ativos = serializers.IntegerField(read_only=True)
    clientes_inativos = serializers.IntegerField(read_only=True)
    clientes_novos = serializers.IntegerField(read_only=True)
    clientes_cancelados = serializers.IntegerField(read_only=True)


class ClienteDetalhesSerializer(serializers.Serializer):
    """Serializer para detalhes do cliente"""
    
    cliente = ClienteSerializer(read_only=True)
    contabilidade = ContabilidadeSerializer(read_only=True)
    contrato_id = serializers.UUIDField(read_only=True)
    data_inicio_contrato = serializers.DateField(read_only=True, allow_null=True)
    data_termino_contrato = serializers.DateField(read_only=True, allow_null=True)
    valor_honorario = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    dia_vencimento = serializers.IntegerField(read_only=True, allow_null=True)
    total_lancamentos = serializers.IntegerField(read_only=True)
    total_notas_fiscais = serializers.IntegerField(read_only=True)
    total_funcionarios = serializers.IntegerField(read_only=True)
    ultimo_lancamento = serializers.DateField(read_only=True, allow_null=True)
    ultima_nota_fiscal = serializers.DateField(read_only=True, allow_null=True)


class ClienteListaSerializer(serializers.Serializer):
    """Serializer para lista de clientes por competência"""
    
    cliente = ClienteSerializer(read_only=True)
    contabilidade = ContabilidadeSerializer(read_only=True)
    competencia = serializers.CharField(read_only=True)
    total_lancamentos = serializers.IntegerField(read_only=True)
    total_notas_fiscais = serializers.IntegerField(read_only=True)
    valor_total_lancamentos = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    valor_total_notas = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    status = serializers.CharField(read_only=True)


class SocioMajoritarioSerializer(serializers.Serializer):
    """Serializer para sócio majoritário"""
    
    cliente = ClienteSerializer(read_only=True)
    contabilidade = ContabilidadeSerializer(read_only=True)
    socio_nome = serializers.CharField(read_only=True)
    socio_cpf = serializers.CharField(read_only=True)
    percentual_participacao = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    tipo_socio = serializers.CharField(read_only=True)


class UsuarioSerializer(serializers.ModelSerializer):
    """Serializer para usuários"""
    
    contabilidade_razao_social = serializers.CharField(
        source='contabilidade.razao_social',
        read_only=True
    )
    
    contabilidade_cnpj = serializers.CharField(
        source='contabilidade.cnpj',
        read_only=True
    )
    
    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'tipo_usuario', 'modulos_acessiveis', 'pode_executar_etl',
            'pode_administrar_usuarios', 'pode_ver_dados_sensiveis',
            'ativo', 'contabilidade_id', 'contabilidade_razao_social',
            'contabilidade_cnpj', 'data_ultima_atividade', 'mfa_enabled'
        ]
        read_only_fields = ['id', 'data_ultima_atividade']


class UsuarioAtividadesSerializer(serializers.Serializer):
    """Serializer para atividades do usuário"""
    
    usuario = UsuarioSerializer(read_only=True)
    data_atividade = serializers.DateField(read_only=True)
    total_atividades = serializers.IntegerField(read_only=True)
    atividades_etl = serializers.IntegerField(read_only=True)
    atividades_administracao = serializers.IntegerField(read_only=True)
    atividades_operacionais = serializers.IntegerField(read_only=True)
    tempo_total_horas = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)


class UsuarioProdutividadeSerializer(serializers.Serializer):
    """Serializer para produtividade do usuário"""
    
    usuario = UsuarioSerializer(read_only=True)
    periodo = serializers.CharField(read_only=True)
    total_atividades = serializers.IntegerField(read_only=True)
    tempo_total_horas = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    media_atividades_por_dia = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    media_tempo_por_atividade = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    eficiencia = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)


# Serializers para endpoint de usuários com dados reais
class UsuarioListagemDashboardSerializer(serializers.Serializer):
    """Serializer simplificado para lista de usuários no dashboard"""
    id = serializers.UUIDField()
    nome = serializers.CharField()
    status = serializers.CharField()


class ProdutividadeMensalRealSerializer(serializers.Serializer):
    """Produtividade mensal baseada em EstatisticaUsuario"""
    mes = serializers.CharField()
    tempo_total_horas = serializers.FloatField()
    total_importacoes = serializers.IntegerField()
    total_lancamentos = serializers.IntegerField()
    lancamentos_manuais = serializers.IntegerField()
    lancamentos_automaticos = serializers.IntegerField()
    total_atividades = serializers.IntegerField()


class RankingProdutividadeRealSerializer(serializers.Serializer):
    """Ranking com dados reais"""
    usuario_id = serializers.UUIDField()
    nome = serializers.CharField()
    tempo_sistema_horas = serializers.FloatField()
    total_lancamentos = serializers.IntegerField()
    lancamentos_manuais = serializers.IntegerField()
    total_importacoes = serializers.IntegerField()
    eficiencia = serializers.FloatField()


class ProdutividadePorEmpresaSerializer(serializers.Serializer):
    """Produtividade por empresa"""
    empresa_cnpj = serializers.CharField()
    empresa_nome = serializers.CharField()
    tempo_horas = serializers.FloatField()
    total_lancamentos = serializers.IntegerField()
    lancamentos_manuais = serializers.IntegerField()
    lancamentos_automaticos = serializers.IntegerField()
    total_importacoes = serializers.IntegerField()
    total_atividades = serializers.IntegerField()


# Serializers para análise do escritório de contabilidade
class ResumoFinanceiroSerializer(serializers.Serializer):
    """Resumo financeiro geral do escritório"""
    faturamento_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    faturamento_mensal = serializers.DecimalField(max_digits=15, decimal_places=2)
    custo_operacional_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    custo_operacional_mensal = serializers.DecimalField(max_digits=15, decimal_places=2)
    lucro_bruto = serializers.DecimalField(max_digits=15, decimal_places=2)
    margem_bruta_percentual = serializers.FloatField()
    lucro_liquido = serializers.DecimalField(max_digits=15, decimal_places=2)
    margem_liquida_percentual = serializers.FloatField()


class FaturamentoPorTipoSerializer(serializers.Serializer):
    """Faturamento por tipo de nota fiscal"""
    tipo = serializers.CharField()
    valor = serializers.DecimalField(max_digits=15, decimal_places=2)
    quantidade = serializers.IntegerField()


class EvolucaoMensalSerializer(serializers.Serializer):
    """Evolução mensal de faturamento"""
    mes = serializers.CharField()
    valor = serializers.DecimalField(max_digits=15, decimal_places=2)
    notas = serializers.IntegerField()


class TopClientesSerializer(serializers.Serializer):
    """Top clientes por faturamento"""
    cliente = serializers.CharField()
    cnpj = serializers.CharField()
    valor = serializers.DecimalField(max_digits=15, decimal_places=2)
    notas = serializers.IntegerField()


class FolhaPagamentoSerializer(serializers.Serializer):
    """Dados da folha de pagamento"""
    total_mensal = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_funcionarios = serializers.IntegerField()
    custo_medio_funcionario = serializers.DecimalField(max_digits=15, decimal_places=2)
    evolucao_mensal = EvolucaoMensalSerializer(many=True)


class DRESerializer(serializers.Serializer):
    """Demonstração do Resultado do Exercício"""
    receita_bruta = serializers.DecimalField(max_digits=15, decimal_places=2)
    impostos = serializers.DecimalField(max_digits=15, decimal_places=2)
    receita_liquida = serializers.DecimalField(max_digits=15, decimal_places=2)
    custos_variaveis = serializers.DecimalField(max_digits=15, decimal_places=2)
    lucro_bruto = serializers.DecimalField(max_digits=15, decimal_places=2)
    despesas_operacionais = serializers.DecimalField(max_digits=15, decimal_places=2)
    lucro_operacional = serializers.DecimalField(max_digits=15, decimal_places=2)
    lucro_liquido = serializers.DecimalField(max_digits=15, decimal_places=2)
