#!/usr/bin/env python
"""
Investigar os dados reais do sistema para entender as fontes
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from apps.core.models import Contabilidade
from apps.fiscal.models import NotaFiscal
from apps.funcionarios.models import VinculoEmpregaticio
from apps.contabil.models import LancamentoContabil
from apps.pessoas.models import Contrato
from apps.administracao.models import EstatisticaUsuario
from django.db import models
from datetime import date, datetime

def investigar_dados_reais():
    """Investiga os dados reais do sistema"""
    print("=== INVESTIGAÇÃO: Dados Reais do Sistema ===")
    
    contabilidade = Contabilidade.objects.get(cnpj='10662155000147')
    print(f"Contabilidade: {contabilidade.razao_social} (CNPJ: {contabilidade.cnpj})")
    
    # Período: Jan-Set 2025
    data_inicio = date(2025, 1, 1)
    data_fim = date(2025, 9, 30)
    print(f"Período: {data_inicio} a {data_fim}")
    
    # 1. FATURAMENTO - Notas Fiscais
    print("\n--- FATURAMENTO (Notas Fiscais) ---")
    
    # Notas emitidas PELO ESCRITÓRIO
    notas_escritorio = NotaFiscal.objects.filter(
        parceiro_pj__cnpj=contabilidade.cnpj,
        data_emissao__gte=data_inicio,
        data_emissao__lte=data_fim,
        tipo_nota__in=['SAIDA', 'SERVICO']
    )
    
    faturamento_escritorio = notas_escritorio.aggregate(
        total=models.Sum('valor_total'),
        count=models.Count('id')
    )
    
    print(f"Notas emitidas PELO ESCRITÓRIO:")
    print(f"  Total: R$ {faturamento_escritorio['total'] or 0:,.2f}")
    print(f"  Quantidade: {faturamento_escritorio['count']}")
    
    # Notas dos CLIENTES (todas as notas da contabilidade)
    notas_clientes = NotaFiscal.objects.filter(
        contabilidade=contabilidade,
        data_emissao__gte=data_inicio,
        data_emissao__lte=data_fim,
        tipo_nota__in=['SAIDA', 'SERVICO']
    )
    
    faturamento_clientes = notas_clientes.aggregate(
        total=models.Sum('valor_total'),
        count=models.Count('id')
    )
    
    print(f"\nNotas dos CLIENTES (todas):")
    print(f"  Total: R$ {faturamento_clientes['total'] or 0:,.2f}")
    print(f"  Quantidade: {faturamento_clientes['count']}")
    
    # 2. CUSTOS - Funcionários
    print("\n--- CUSTOS (Funcionários) ---")
    
    # Funcionários DO ESCRITÓRIO
    from django.contrib.contenttypes.models import ContentType
    contabilidade_content_type = ContentType.objects.get_for_model(contabilidade.__class__)
    
    funcionarios_escritorio = VinculoEmpregaticio.objects.filter(
        contabilidade=contabilidade,
        ativo=True,
        content_type=contabilidade_content_type,
        object_id=contabilidade.id
    )
    
    custos_escritorio = funcionarios_escritorio.aggregate(
        total=models.Sum('salario_base'),
        count=models.Count('id')
    )
    
    print(f"Funcionários DO ESCRITÓRIO:")
    print(f"  Total: R$ {custos_escritorio['total'] or 0:,.2f}")
    print(f"  Quantidade: {custos_escritorio['count']}")
    
    # Funcionários DOS CLIENTES
    funcionarios_clientes = VinculoEmpregaticio.objects.filter(
        contabilidade=contabilidade,
        ativo=True
    ).exclude(
        content_type=contabilidade_content_type,
        object_id=contabilidade.id
    )
    
    custos_clientes = funcionarios_clientes.aggregate(
        total=models.Sum('salario_base'),
        count=models.Count('id')
    )
    
    print(f"\nFuncionários DOS CLIENTES:")
    print(f"  Total: R$ {custos_clientes['total'] or 0:,.2f}")
    print(f"  Quantidade: {custos_clientes['count']}")
    
    # 3. LANÇAMENTOS CONTÁBEIS
    print("\n--- LANÇAMENTOS CONTÁBEIS ---")
    
    lancamentos = LancamentoContabil.objects.filter(
        contabilidade=contabilidade,
        data_lancamento__gte=data_inicio,
        data_lancamento__lte=data_fim
    )
    
    lancamentos_data = lancamentos.aggregate(
        total=models.Sum('valor_total'),
        count=models.Count('id')
    )
    
    print(f"Lançamentos:")
    print(f"  Total: R$ {lancamentos_data['total'] or 0:,.2f}")
    print(f"  Quantidade: {lancamentos_data['count']}")
    
    # 4. CONTRATOS
    print("\n--- CONTRATOS ---")
    
    contratos = Contrato.objects.filter(
        contabilidade=contabilidade,
        ativo=True
    )
    
    contratos_data = contratos.aggregate(
        total=models.Sum('valor_honorario'),
        count=models.Count('id')
    )
    
    print(f"Contratos ativos:")
    print(f"  Total: R$ {contratos_data['total'] or 0:,.2f}")
    print(f"  Quantidade: {contratos_data['count']}")
    
    # 5. ESTATÍSTICAS DE USUÁRIOS
    print("\n--- ESTATÍSTICAS DE USUÁRIOS ---")
    
    estatisticas = EstatisticaUsuario.objects.filter(
        contabilidade=contabilidade,
        periodo_referencia__gte=data_inicio,
        periodo_referencia__lte=data_fim
    )
    
    stats_data = estatisticas.aggregate(
        total_lancamentos=models.Sum('total_lancamentos'),
        total_tempo=models.Sum('tempo_total_minutos'),
        count=models.Count('id')
    )
    
    print(f"Estatísticas de usuários:")
    print(f"  Total lançamentos: {stats_data['total_lancamentos'] or 0}")
    print(f"  Total tempo (min): {stats_data['total_tempo'] or 0}")
    print(f"  Total tempo (horas): {(stats_data['total_tempo'] or 0) / 60:.2f}")
    print(f"  Quantidade: {stats_data['count']}")
    
    # 6. ANÁLISE COMPARATIVA
    print("\n--- ANÁLISE COMPARATIVA ---")
    print("Dados do relatório vs nossos cálculos:")
    print(f"Faturamento real: R$ 80.796,31")
    print(f"Faturamento calculado: R$ {faturamento_escritorio['total'] or 0:,.2f}")
    print(f"Custo real: R$ 549.845,14")
    print(f"Custo calculado: R$ {custos_escritorio['total'] or 0:,.2f}")
    print(f"Lançamentos reais: 30")
    print(f"Lançamentos calculados: {lancamentos_data['count']}")
    
    # 7. INVESTIGAR FONTES ALTERNATIVAS
    print("\n--- INVESTIGAR FONTES ALTERNATIVAS ---")
    
    # Verificar se há outras tabelas de faturamento
    print("Possíveis fontes de faturamento:")
    print("1. Contratos (honorários): R$ {:.2f}".format(contratos_data['total'] or 0))
    print("2. Lançamentos contábeis: R$ {:.2f}".format(lancamentos_data['total'] or 0))
    print("3. Notas fiscais escritório: R$ {:.2f}".format(faturamento_escritorio['total'] or 0))
    print("4. Notas fiscais clientes: R$ {:.2f}".format(faturamento_clientes['total'] or 0))
    
    # Verificar se há outras tabelas de custos
    print("\nPossíveis fontes de custos:")
    print("1. Funcionários escritório: R$ {:.2f}".format(custos_escritorio['total'] or 0))
    print("2. Funcionários clientes: R$ {:.2f}".format(custos_clientes['total'] or 0))
    print("3. Lançamentos contábeis: R$ {:.2f}".format(lancamentos_data['total'] or 0))

if __name__ == '__main__':
    investigar_dados_reais()
