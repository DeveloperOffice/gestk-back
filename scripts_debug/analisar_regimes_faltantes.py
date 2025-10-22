"""
Script para analisar empresas sem regime tributário definido
Identifica onde estão as 290 empresas restantes (46% do total)
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from apps.pessoas.models import PessoaJuridica, Contrato
from apps.importacao.management.commands._base import BaseETLCommand
from django.contrib.contenttypes.models import ContentType

def analisar_regimes_faltantes():
    """Analisa empresas sem regime tributário"""
    
    print("=" * 80)
    print("ANÁLISE DE REGIMES TRIBUTÁRIOS FALTANTES")
    print("=" * 80)
    print()
    
    # 1. Obter mapa histórico
    print("1️⃣ Construindo mapa histórico...")
    etl_command = BaseETLCommand()
    historical_map = etl_command.build_historical_contabilidade_map()
    cnpjs_validos = set(historical_map.keys())
    
    # Filtrar apenas PJs válidas
    pjs_validas = PessoaJuridica.objects.filter(cnpj__in=cnpjs_validos)
    total_pjs = pjs_validas.count()
    print(f"   ✅ Total PJ com contratos válidos: {total_pjs}\n")
    
    # 2. Contar por regime_fiscal
    print("2️⃣ Distribuição por campo 'regime_fiscal':")
    simples = pjs_validas.filter(regime_fiscal='simples').count()
    presumido = pjs_validas.filter(regime_fiscal='presumido').count()
    real = pjs_validas.filter(regime_fiscal='real').count()
    sem_regime_fiscal = pjs_validas.filter(regime_fiscal__isnull=True).count()
    vazio = pjs_validas.filter(regime_fiscal='').count()
    
    print(f"   ✅ Simples Nacional: {simples} ({simples/total_pjs*100:.1f}%)")
    print(f"   ✅ Lucro Presumido: {presumido} ({presumido/total_pjs*100:.1f}%)")
    print(f"   ✅ Lucro Real: {real} ({real/total_pjs*100:.1f}%)")
    print(f"   ❌ NULL: {sem_regime_fiscal} ({sem_regime_fiscal/total_pjs*100:.1f}%)")
    print(f"   ⚠️  String vazia: {vazio} ({vazio/total_pjs*100:.1f}%)")
    print(f"   📊 TOTAL: {simples + presumido + real + sem_regime_fiscal + vazio}\n")
    
    # 3. Contar por regime_tributario
    print("3️⃣ Distribuição por campo 'regime_tributario':")
    com_regime_trib = pjs_validas.filter(regime_tributario__isnull=False).exclude(regime_tributario='').count()
    sem_regime_trib = pjs_validas.filter(regime_tributario__isnull=True).count()
    vazio_trib = pjs_validas.filter(regime_tributario='').count()
    
    print(f"   ✅ Com regime_tributario: {com_regime_trib} ({com_regime_trib/total_pjs*100:.1f}%)")
    print(f"   ❌ NULL: {sem_regime_trib} ({sem_regime_trib/total_pjs*100:.1f}%)")
    print(f"   ⚠️  String vazia: {vazio_trib} ({vazio_trib/total_pjs*100:.1f}%)\n")
    
    # 4. Cruzamento: regime_tributario vs regime_fiscal
    print("4️⃣ Empresas com regime_tributario mas SEM regime_fiscal:")
    tem_trib_sem_fiscal = pjs_validas.filter(
        regime_tributario__isnull=False
    ).exclude(
        regime_tributario=''
    ).filter(
        regime_fiscal__isnull=True
    ).count()
    print(f"   ⚠️  {tem_trib_sem_fiscal} empresas\n")
    
    # 5. Valores únicos em regime_tributario
    print("5️⃣ Valores encontrados no campo 'regime_tributario':")
    valores_unicos = pjs_validas.values_list('regime_tributario', flat=True).distinct()
    for valor in valores_unicos:
        if valor:
            count = pjs_validas.filter(regime_tributario=valor).count()
            print(f"   - '{valor}': {count} empresas")
    
    null_count = pjs_validas.filter(regime_tributario__isnull=True).count()
    print(f"   - NULL: {null_count} empresas")
    
    empty_count = pjs_validas.filter(regime_tributario='').count()
    if empty_count > 0:
        print(f"   - '' (vazio): {empty_count} empresas")
    print()
    
    # 6. Valores únicos em regime_fiscal
    print("6️⃣ Valores encontrados no campo 'regime_fiscal':")
    valores_fiscal = pjs_validas.values_list('regime_fiscal', flat=True).distinct()
    for valor in valores_fiscal:
        if valor:
            count = pjs_validas.filter(regime_fiscal=valor).count()
            print(f"   - '{valor}': {count} empresas")
    
    null_fiscal = pjs_validas.filter(regime_fiscal__isnull=True).count()
    print(f"   - NULL: {null_fiscal} empresas")
    
    empty_fiscal = pjs_validas.filter(regime_fiscal='').count()
    if empty_fiscal > 0:
        print(f"   - '' (vazio): {empty_fiscal} empresas")
    print()
    
    # 7. Empresas SEM nenhum regime definido
    print("7️⃣ Empresas SEM NENHUM regime definido:")
    sem_nenhum = pjs_validas.filter(
        regime_fiscal__isnull=True,
        regime_tributario__isnull=True
    ).count()
    print(f"   ❌ {sem_nenhum} empresas ({sem_nenhum/total_pjs*100:.1f}%)")
    
    # Mostrar exemplos
    if sem_nenhum > 0:
        print("\n   📋 Exemplos de empresas sem regime:")
        exemplos = pjs_validas.filter(
            regime_fiscal__isnull=True,
            regime_tributario__isnull=True
        )[:5]
        
        for pj in exemplos:
            print(f"      - {pj.razao_social[:40]:40} | CNPJ: {pj.cnpj}")
    print()
    
    # 8. Resumo final
    print("=" * 80)
    print("RESUMO FINAL")
    print("=" * 80)
    print(f"✅ Total PJ válidas: {total_pjs}")
    print(f"✅ Com regime_fiscal definido: {simples + presumido + real} ({(simples + presumido + real)/total_pjs*100:.1f}%)")
    print(f"✅ Com regime_tributario definido: {com_regime_trib} ({com_regime_trib/total_pjs*100:.1f}%)")
    print(f"❌ Sem regime_fiscal: {sem_regime_fiscal + vazio} ({(sem_regime_fiscal + vazio)/total_pjs*100:.1f}%)")
    print(f"❌ Sem nenhum regime: {sem_nenhum} ({sem_nenhum/total_pjs*100:.1f}%)")
    print()
    print("CONCLUSÃO:")
    print(f"As {total_pjs - (simples + presumido + real)} empresas restantes ({(total_pjs - (simples + presumido + real))/total_pjs*100:.1f}%) ")
    print(f"não possuem o campo 'regime_fiscal' preenchido no banco de dados.")
    print()
    print("=" * 80)

if __name__ == '__main__':
    analisar_regimes_faltantes()
