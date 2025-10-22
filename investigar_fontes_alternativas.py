#!/usr/bin/env python
"""
Investigar fontes alternativas de dados para o relatório
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
from django.db.models import Sum
from datetime import date, datetime

def investigar_fontes_alternativas():
    """Investiga fontes alternativas de dados"""
    print("=== INVESTIGAÇÃO: Fontes Alternativas de Dados ===")
    
    contabilidade = Contabilidade.objects.get(cnpj='10662155000147')
    print(f"Contabilidade: {contabilidade.razao_social} (CNPJ: {contabilidade.cnpj})")
    
    # Período: Jan-Set 2025
    data_inicio = date(2025, 1, 1)
    data_fim = date(2025, 9, 30)
    print(f"Período: {data_inicio} a {data_fim}")
    
    # 1. INVESTIGAR NOTAS FISCAIS - Diferentes filtros
    print("\n--- INVESTIGAÇÃO: Notas Fiscais (Diferentes Filtros) ---")
    
    # Notas por tipo
    tipos_nota = NotaFiscal.objects.filter(
        contabilidade=contabilidade,
        data_emissao__gte=data_inicio,
        data_emissao__lte=data_fim
    ).values('tipo_nota').annotate(
        total=models.Sum('valor_total'),
        count=models.Count('id')
    ).order_by('-total')
    
    print("Notas por tipo:")
    for tipo in tipos_nota:
        print(f"  {tipo['tipo_nota']}: R$ {tipo['total'] or 0:,.2f} ({tipo['count']} notas)")
    
    # Notas por emitente (id_legado_empresa)
    print("\nNotas por emitente (id_legado_empresa):")
    emitentes = NotaFiscal.objects.filter(
        contabilidade=contabilidade,
        data_emissao__gte=data_inicio,
        data_emissao__lte=data_fim
    ).values('id_legado_empresa').annotate(
        total=models.Sum('valor_total'),
        count=models.Count('id')
    ).order_by('-total')[:10]
    
    for emitente in emitentes:
        print(f"  Empresa {emitente['id_legado_empresa']}: R$ {emitente['total'] or 0:,.2f} ({emitente['count']} notas)")
    
    # 2. INVESTIGAR CONTRATOS - Diferentes campos
    print("\n--- INVESTIGAÇÃO: Contratos (Diferentes Campos) ---")
    
    contratos = Contrato.objects.filter(
        contabilidade=contabilidade,
        ativo=True
    )
    
    print(f"Total de contratos ativos: {contratos.count()}")
    
    # Verificar campos de valor
    campos_valor = ['valor_honorario', 'valor_mensal', 'valor_anual']
    for campo in campos_valor:
        if hasattr(contratos.first(), campo):
            valor = contratos.aggregate(total=models.Sum(campo))['total'] or 0
            print(f"  {campo}: R$ {valor:,.2f}")
    
    # 3. INVESTIGAR LANÇAMENTOS - Diferentes filtros
    print("\n--- INVESTIGAÇÃO: Lançamentos (Diferentes Filtros) ---")
    
    # Lançamentos por tipo
    lancamentos = LancamentoContabil.objects.filter(
        contabilidade=contabilidade,
        data_lancamento__gte=data_inicio,
        data_lancamento__lte=data_fim
    )
    
    print(f"Total de lançamentos: {lancamentos.count()}")
    
    # Verificar se há campo tipo_lancamento
    if hasattr(lancamentos.first(), 'tipo_lancamento'):
        tipos_lancamento = lancamentos.values('tipo_lancamento').annotate(
            total=models.Sum('valor_total'),
            count=models.Count('id')
        ).order_by('-total')
        
        print("Lançamentos por tipo:")
        for tipo in tipos_lancamento:
            print(f"  {tipo['tipo_lancamento']}: R$ {tipo['total'] or 0:,.2f} ({tipo['count']} lançamentos)")
    
    # 4. INVESTIGAR FUNCIONÁRIOS - Diferentes critérios
    print("\n--- INVESTIGAÇÃO: Funcionários (Diferentes Critérios) ---")
    
    # Funcionários por salário
    funcionarios = VinculoEmpregaticio.objects.filter(
        contabilidade=contabilidade,
        ativo=True
    )
    
    print(f"Total de funcionários: {funcionarios.count()}")
    
    # Funcionários por faixa salarial
    faixas = [
        (0, 1000, "Até R$ 1.000"),
        (1000, 3000, "R$ 1.000 - R$ 3.000"),
        (3000, 5000, "R$ 3.000 - R$ 5.000"),
        (5000, 10000, "R$ 5.000 - R$ 10.000"),
        (10000, 999999, "Acima de R$ 10.000")
    ]
    
    for min_sal, max_sal, desc in faixas:
        funcs = funcionarios.filter(
            salario_base__gte=min_sal,
            salario_base__lt=max_sal
        )
        total = funcs.aggregate(Sum('salario_base'))['salario_base__sum'] or 0
        print(f"  {desc}: {funcs.count()} funcionários, R$ {total:,.2f}")
    
    # 5. INVESTIGAR ESTATÍSTICAS - Diferentes períodos
    print("\n--- INVESTIGAÇÃO: Estatísticas (Diferentes Períodos) ---")
    
    # Estatísticas por mês
    stats_mensais = EstatisticaUsuario.objects.filter(
        contabilidade=contabilidade
    ).values('periodo_referencia').annotate(
        total_lancamentos=models.Sum('total_lancamentos'),
        total_tempo=models.Sum('tempo_total_minutos'),
        count=models.Count('id')
    ).order_by('periodo_referencia')
    
    print("Estatísticas por mês:")
    for stat in stats_mensais:
        print(f"  {stat['periodo_referencia']}: {stat['total_lancamentos'] or 0} lançamentos, {(stat['total_tempo'] or 0) / 60:.2f} horas")
    
    # 6. INVESTIGAR TABELAS ALTERNATIVAS
    print("\n--- INVESTIGAÇÃO: Tabelas Alternativas ---")
    
    # Verificar se há tabelas de faturamento específicas
    print("Possíveis tabelas de faturamento:")
    print("1. fiscal_notas_fiscais (já investigada)")
    print("2. pessoas_contratos (honorários)")
    print("3. contabil_lancamentos (lançamentos)")
    
    # Verificar se há tabelas de custos específicas
    print("\nPossíveis tabelas de custos:")
    print("1. funcionarios_vinculoempregaticio (já investigada)")
    print("2. contabil_lancamentos (despesas)")
    print("3. Outras tabelas de despesas")
    
    # 7. ANÁLISE FINAL
    print("\n--- ANÁLISE FINAL ---")
    print("Dados do relatório vs nossas fontes:")
    print(f"Faturamento real: R$ 80.796,31")
    print(f"  - Notas escritório: R$ 0,00")
    print(f"  - Contratos: R$ 455.957,14")
    print(f"  - Lançamentos: R$ 1.175.426.439,87")
    print(f"  - Notas clientes: R$ 9.087.898,03")
    
    print(f"\nCusto real: R$ 549.845,14")
    print(f"  - Funcionários escritório: R$ 0,00")
    print(f"  - Funcionários clientes: R$ 4.115.570,00")
    print(f"  - Lançamentos: R$ 1.175.426.439,87")
    
    print(f"\nLançamentos reais: 30")
    print(f"  - Lançamentos calculados: 121.396")
    
    print("\nCONCLUSÃO:")
    print("O relatório está usando fontes de dados diferentes ou filtros específicos")
    print("que não estamos aplicando. Preciso investigar mais profundamente.")

if __name__ == '__main__':
    investigar_fontes_alternativas()
