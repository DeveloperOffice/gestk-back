import os
import django
from datetime import date, datetime
from django.db.models import Sum, Count
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from apps.core.models import Contabilidade
from apps.contabil.models import LancamentoContabil, Partida

def testar_etl_lancamentos_contabilidades():
    print("=== TESTE: ETL LANÇAMENTOS DAS CONTABILIDADES ===")
    
    # 1. Verificar contabilidades disponíveis
    print("\n--- CONTABILIDADES DISPONÍVEIS ---")
    contabilidades = Contabilidade.objects.all().order_by('razao_social')
    print(f"Total de contabilidades: {contabilidades.count()}")
    
    for contab in contabilidades:
        print(f"- {contab.razao_social} (CNPJ: {contab.cnpj})")
    
    # 2. Verificar lançamentos existentes antes da ETL
    print("\n--- LANÇAMENTOS EXISTENTES (ANTES DA ETL) ---")
    total_lancamentos_antes = LancamentoContabil.objects.count()
    print(f"Total de lançamentos no sistema: {total_lancamentos_antes}")
    
    # Lançamentos por contabilidade
    for contab in contabilidades:
        lancamentos_contab = LancamentoContabil.objects.filter(contabilidade=contab)
        if lancamentos_contab.exists():
            valor_total = lancamentos_contab.aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
            print(f"  {contab.razao_social}: {lancamentos_contab.count()} lançamentos - R$ {valor_total:,.2f}")
    
    # 3. Verificar lançamentos sem contrato (possivelmente das contabilidades)
    print("\n--- LANÇAMENTOS SEM CONTRATO (POSSIVELMENTE DAS CONTABILIDADES) ---")
    lancamentos_sem_contrato = LancamentoContabil.objects.filter(contrato__isnull=True)
    print(f"Lançamentos sem contrato: {lancamentos_sem_contrato.count()}")
    
    if lancamentos_sem_contrato.exists():
        for contab in contabilidades:
            sem_contrato = lancamentos_sem_contrato.filter(contabilidade=contab)
            if sem_contrato.exists():
                valor_sem_contrato = sem_contrato.aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
                print(f"  {contab.razao_social}: {sem_contrato.count()} lançamentos - R$ {valor_sem_contrato:,.2f}")
                
                # Amostra
                for lanc in sem_contrato[:3]:
                    print(f"    {lanc.numero_lancamento} - {lanc.historico[:50]}... - R$ {lanc.valor_total:,.2f}")
    
    # 4. Verificar partidas dos lançamentos sem contrato
    print("\n--- PARTIDAS DOS LANÇAMENTOS SEM CONTRATO ---")
    if lancamentos_sem_contrato.exists():
        for lanc in lancamentos_sem_contrato[:3]:
            partidas = lanc.partidas.all()
            print(f"  Lançamento {lanc.numero_lancamento} ({lanc.contabilidade.razao_social}):")
            for partida in partidas:
                print(f"    {partida.tipo_partida} - {partida.conta.codigo} ({partida.conta.nome}) - R$ {partida.valor:,.2f}")
    
    # 5. Resumo final
    print("\n--- RESUMO FINAL ---")
    print(f"Total de contabilidades: {contabilidades.count()}")
    print(f"Total de lançamentos: {LancamentoContabil.objects.count()}")
    print(f"Lançamentos sem contrato: {lancamentos_sem_contrato.count()}")
    print(f"Lançamentos com contrato: {LancamentoContabil.objects.filter(contrato__isnull=False).count()}")
    
    # 6. Instruções para executar a ETL
    print("\n--- INSTRUÇÕES PARA EXECUTAR A ETL ---")
    print("Para executar a ETL 06.1, use:")
    print("python manage.py etl_06_1_lancamentos_contabilidades --data-inicio=2019-01-01 --data-fim=2025-01-22")
    print("\nOu para uma contabilidade específica:")
    print("python manage.py etl_06_1_lancamentos_contabilidades --contabilidade-id=ID_DA_CONTABILIDADE")

if __name__ == '__main__':
    testar_etl_lancamentos_contabilidades()
