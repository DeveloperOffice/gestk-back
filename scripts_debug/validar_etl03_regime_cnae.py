"""
Script de Validação - ETL 03_1 (Regime Tributário e CNAE)

Este script valida se a importação de Pessoas Jurídicas está funcionando
corretamente, incluindo regime tributário e CNAE.

Uso:
    python scripts_debug/validar_etl03_regime_cnae.py
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from apps.pessoas.models import PessoaJuridica, Contrato
from apps.cadastros_gerais.models import CNAE
from django.db.models import Count, Q


def validar_regime_tributario():
    """Valida se os regimes tributários foram importados corretamente"""
    print("\n" + "="*70)
    print("VALIDAÇÃO: REGIME TRIBUTÁRIO")
    print("="*70)
    
    # Total de empresas
    total_empresas = PessoaJuridica.objects.count()
    print(f"\n📊 Total de Pessoas Jurídicas: {total_empresas}")
    
    # Empresas com regime tributário preenchido
    com_regime = PessoaJuridica.objects.filter(
        regime_tributario__isnull=False
    ).count()
    print(f"✅ Com regime tributário: {com_regime} ({(com_regime/total_empresas*100):.1f}%)")
    
    # Empresas sem regime tributário
    sem_regime = PessoaJuridica.objects.filter(
        regime_tributario__isnull=True
    ).count()
    print(f"⚠️  Sem regime tributário: {sem_regime} ({(sem_regime/total_empresas*100):.1f}%)")
    
    # Distribuição por regime
    print("\n📈 Distribuição por Regime Tributário:")
    regimes = PessoaJuridica.objects.values('regime_tributario').annotate(
        total=Count('id')
    ).order_by('regime_tributario')
    
    regime_map = {
        '1': 'Simples Nacional',
        '2': 'Lucro Presumido',
        '3': 'Lucro Real',
        '4': 'MEI'
    }
    
    for regime in regimes:
        codigo = regime['regime_tributario']
        total = regime['total']
        nome = regime_map.get(codigo, 'Não informado')
        percentual = (total / total_empresas * 100)
        print(f"  {codigo} - {nome}: {total} ({percentual:.1f}%)")
    
    # Validar consistência: simples_nacional deve ser True apenas para regime '1'
    print("\n🔍 Validação de Consistência:")
    inconsistencias = PessoaJuridica.objects.filter(
        Q(regime_tributario='1', simples_nacional=False) |
        Q(~Q(regime_tributario='1'), simples_nacional=True)
    ).count()
    
    if inconsistencias == 0:
        print("  ✅ Campo simples_nacional está consistente com regime_tributario")
    else:
        print(f"  ❌ Encontradas {inconsistencias} inconsistências entre simples_nacional e regime_tributario")
    
    # Validar regime_fiscal para dashboards
    print("\n📊 Distribuição por Regime Fiscal (para dashboards):")
    regimes_fiscais = PessoaJuridica.objects.values('regime_fiscal').annotate(
        total=Count('id')
    ).order_by('regime_fiscal')
    
    for regime in regimes_fiscais:
        codigo = regime['regime_fiscal']
        total = regime['total']
        percentual = (total / total_empresas * 100)
        print(f"  {codigo or 'NULL'}: {total} ({percentual:.1f}%)")


def validar_cnae():
    """Valida se os CNAEs foram importados corretamente"""
    print("\n" + "="*70)
    print("VALIDAÇÃO: CNAE PRINCIPAL")
    print("="*70)
    
    total_empresas = PessoaJuridica.objects.count()
    
    # Empresas com CNAE principal
    com_cnae = PessoaJuridica.objects.filter(
        cnae_principal__isnull=False
    ).count()
    print(f"\n✅ Empresas com CNAE principal: {com_cnae} ({(com_cnae/total_empresas*100):.1f}%)")
    
    # Empresas sem CNAE principal
    sem_cnae = PessoaJuridica.objects.filter(
        cnae_principal__isnull=True
    ).count()
    print(f"⚠️  Empresas sem CNAE principal: {sem_cnae} ({(sem_cnae/total_empresas*100):.1f}%)")
    
    # Total de CNAEs cadastrados
    total_cnaes = CNAE.objects.count()
    print(f"\n📋 Total de CNAEs cadastrados no sistema: {total_cnaes}")
    
    # CNAEs mais utilizados
    print("\n📊 Top 10 CNAEs mais utilizados:")
    top_cnaes = PessoaJuridica.objects.filter(
        cnae_principal__isnull=False
    ).values(
        'cnae_principal__codigo',
        'cnae_principal__descricao'
    ).annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    for i, cnae in enumerate(top_cnaes, 1):
        codigo = cnae['cnae_principal__codigo']
        descricao = cnae['cnae_principal__descricao']
        total = cnae['total']
        print(f"  {i}. {codigo} - {descricao[:50]}: {total} empresas")


def validar_ramo_atividade():
    """Valida se os ramos de atividade foram mapeados corretamente"""
    print("\n" + "="*70)
    print("VALIDAÇÃO: RAMO DE ATIVIDADE")
    print("="*70)
    
    total_empresas = PessoaJuridica.objects.count()
    
    # Distribuição por ramo
    print("\n📊 Distribuição por Ramo de Atividade:")
    ramos = PessoaJuridica.objects.values('ramo_atividade').annotate(
        total=Count('id')
    ).order_by('-total')
    
    for ramo in ramos:
        nome = ramo['ramo_atividade'] or 'Não informado'
        total = ramo['total']
        percentual = (total / total_empresas * 100)
        print(f"  {nome}: {total} ({percentual:.1f}%)")


def validar_contabilidade():
    """Valida se as empresas possuem contabilidade mapeada (Regra de Ouro)"""
    print("\n" + "="*70)
    print("VALIDAÇÃO: REGRA DE OURO - CONTABILIDADE")
    print("="*70)
    
    total_empresas = PessoaJuridica.objects.count()
    
    # Empresas com contratos ativos
    from django.contrib.contenttypes.models import ContentType
    pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
    
    empresas_com_contrato = PessoaJuridica.objects.filter(
        id__in=Contrato.objects.filter(
            content_type=pj_content_type
        ).values_list('object_id', flat=True)
    ).count()
    
    print(f"\n✅ Empresas com contrato: {empresas_com_contrato} ({(empresas_com_contrato/total_empresas*100):.1f}%)")
    
    # Empresas com contratos ativos
    empresas_com_contrato_ativo = PessoaJuridica.objects.filter(
        id__in=Contrato.objects.filter(
            content_type=pj_content_type,
            ativo=True
        ).values_list('object_id', flat=True)
    ).count()
    
    print(f"✅ Empresas com contrato ativo: {empresas_com_contrato_ativo} ({(empresas_com_contrato_ativo/total_empresas*100):.1f}%)")
    
    # Empresas sem contrato (não deveriam existir após ETL com Regra de Ouro)
    empresas_sem_contrato = total_empresas - empresas_com_contrato
    
    if empresas_sem_contrato == 0:
        print("\n✅ REGRA DE OURO VALIDADA: Todas as empresas possuem contrato!")
    else:
        print(f"\n⚠️  {empresas_sem_contrato} empresas sem contrato encontradas")
        print("    Isso pode indicar:")
        print("    1. Dados importados antes da implementação da Regra de Ouro")
        print("    2. Necessidade de re-executar a ETL 03_1")


def validar_amostras():
    """Mostra amostras de dados importados"""
    print("\n" + "="*70)
    print("AMOSTRAS DE DADOS IMPORTADOS")
    print("="*70)
    
    # 5 empresas com dados completos
    print("\n📋 5 Empresas com Dados Completos:")
    empresas = PessoaJuridica.objects.filter(
        regime_tributario__isnull=False,
        cnae_principal__isnull=False,
        ramo_atividade__isnull=False
    ).select_related('cnae_principal')[:5]
    
    for i, empresa in enumerate(empresas, 1):
        print(f"\n  {i}. {empresa.razao_social}")
        print(f"     CNPJ: {empresa.cnpj}")
        print(f"     Regime: {empresa.get_regime_tributario_display()} (Código: {empresa.regime_tributario})")
        print(f"     Regime Fiscal: {empresa.regime_fiscal}")
        print(f"     Simples Nacional: {empresa.simples_nacional}")
        print(f"     CNAE: {empresa.cnae_principal.codigo} - {empresa.cnae_principal.descricao[:50]}...")
        print(f"     Ramo: {empresa.ramo_atividade}")
        print(f"     Ativo: {empresa.ativo}")


def main():
    """Executa todas as validações"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  VALIDAÇÃO - ETL 03_1 (Regime Tributário e CNAE)".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")
    
    try:
        validar_regime_tributario()
        validar_cnae()
        validar_ramo_atividade()
        validar_contabilidade()
        validar_amostras()
        
        print("\n" + "="*70)
        print("✅ VALIDAÇÃO CONCLUÍDA")
        print("="*70)
        print("\nPróximos passos:")
        print("1. Revisar inconsistências encontradas (se houver)")
        print("2. Re-executar ETL se necessário: python manage.py etl_03_1_pessoas_juridicas")
        print("3. Testar endpoints da API: /api/gestao/carteira/categorias/")
        print("")
        
    except Exception as e:
        print(f"\n❌ ERRO durante validação: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
