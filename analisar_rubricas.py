import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from apps.funcionarios.models import Rescisao, RescisaoRubrica

print("=" * 80)
print("ANÁLISE DETALHADA - RUBRICAS SEM RESCISÃO")
print("=" * 80)

# 1. Ver rescisões salvas
print("\n1. AMOSTRA DE RESCISÕES NO BANCO:")
print("-" * 80)
rescisoes = Rescisao.objects.all()[:20]
for r in rescisoes:
    print(f"  id_legado: {r.id_legado:20s} | Contabilidade: {r.contabilidade.razao_social[:40]:40s}")

# 2. Construir mapa como a ETL faz
print("\n2. MAPA DE RESCISÕES (como a ETL constrói):")
print("-" * 80)
rescisoes_map = {r.id_legado: r for r in Rescisao.objects.all() if r.id_legado}
print(f"Total de chaves no mapa: {len(rescisoes_map)}")
print(f"Primeiras 10 chaves:")
for i, key in enumerate(list(rescisoes_map.keys())[:10]):
    print(f"  {key}")

# 3. Ver exemplos de id_legado que a query de rubricas está buscando
print("\n3. EXEMPLOS DE id_legado QUE A ETL DE RUBRICAS PROCURA:")
print("-" * 80)
print("(Simulando o que vem do Sybase)")
exemplos = [
    "81-153",
    "45-156", 
    "624-141",
    "700-6",
    "741-19"
]
for id_leg in exemplos:
    if id_leg in rescisoes_map:
        print(f"  ✅ {id_leg:15s} - ENCONTRADO")
    else:
        print(f"  ❌ {id_leg:15s} - NÃO ENCONTRADO")

# 4. Verificar se existem rubricas já salvas
print("\n4. RUBRICAS JÁ IMPORTADAS:")
print("-" * 80)
rubricas = RescisaoRubrica.objects.all()[:10]
print(f"Total rubricas: {RescisaoRubrica.objects.count()}")
if rubricas:
    print("Amostra:")
    for rr in rubricas:
        print(f"  Rescisão id_legado: {rr.rescisao.id_legado} | Rubrica: {rr.descricao[:40]} | Valor: {rr.valor}")

print("\n" + "=" * 80)
