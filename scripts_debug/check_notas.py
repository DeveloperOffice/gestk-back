import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from apps.fiscal.models import NotaFiscal, NotaFiscalItem
from django.db.models import Count, Min, Max

print('='*70)
print('ESTATÍSTICAS DE NOTAS FISCAIS NO BANCO')
print('='*70)

total = NotaFiscal.objects.count()
print(f'\n📊 Total de Notas: {total:,}')
print(f'📋 Total de Itens: {NotaFiscalItem.objects.count():,}')

print('\n📦 Por Tipo:')
for t in NotaFiscal.objects.values('tipo_nota').annotate(c=Count('id')).order_by('tipo_nota'):
    print(f'  {t["tipo_nota"]}: {t["c"]:,}')

datas = NotaFiscal.objects.aggregate(Min('data_emissao'), Max('data_emissao'))
print(f'\n📅 Período:')
print(f'  Primeira nota: {datas["data_emissao__min"]}')
print(f'  Última nota: {datas["data_emissao__max"]}')

print('\n🏢 Top 5 Contabilidades:')
for c in NotaFiscal.objects.values('contabilidade__nome').annotate(c=Count('id')).order_by('-c')[:5]:
    print(f'  {c["contabilidade__nome"]}: {c["c"]:,}')

print('='*70)
