"""
Script para verificar regra: 1 Empresa = 1 Contrato Ativo por Contabilidade
"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from apps.pessoas.models import Contrato, PessoaJuridica
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count

print("\n" + "="*70)
print("VALIDAÇÃO: REGRA DE 1 CONTRATO ATIVO POR EMPRESA/CONTABILIDADE")
print("="*70)

# Buscar content type de PessoaJuridica
pj_ct = ContentType.objects.get_for_model(PessoaJuridica)

# Buscar empresas com múltiplos contratos ativos na mesma contabilidade
duplicados = Contrato.objects.filter(
    content_type=pj_ct, 
    ativo=True
).values('object_id', 'contabilidade').annotate(
    total=Count('id')
).filter(total__gt=1)

print(f"\n📊 Total de contratos ativos: {Contrato.objects.filter(ativo=True).count()}")
print(f"📊 Total de contratos ativos (PJ): {Contrato.objects.filter(content_type=pj_ct, ativo=True).count()}")
print(f"\n⚠️  Empresas com múltiplos contratos ativos na mesma contabilidade: {len(duplicados)}")

if len(duplicados) > 0:
    print("\n❌ VIOLAÇÃO DA REGRA DETECTADA!")
    print("\nPrimeiros 10 casos:")
    for i, d in enumerate(list(duplicados)[:10], 1):
        pj = PessoaJuridica.objects.get(id=d['object_id'])
        print(f"\n  {i}. Empresa: {pj.razao_social} (CNPJ: {pj.cnpj})")
        print(f"     Contabilidade ID: {d['contabilidade']}")
        print(f"     Contratos ativos: {d['total']}")
        
        # Listar os contratos
        contratos = Contrato.objects.filter(
            content_type=pj_ct,
            object_id=d['object_id'],
            contabilidade_id=d['contabilidade'],
            ativo=True
        )
        for c in contratos:
            print(f"       - Contrato ID: {c.id}, Data início: {c.data_inicio}")
else:
    print("\n✅ REGRA VALIDADA: Cada empresa possui apenas 1 contrato ativo por contabilidade!")

print("\n" + "="*70)
