"""
Script para verificar dados no banco de dados
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from apps.core.models import Contabilidade, Usuario
from apps.pessoas.models import PessoaJuridica, Contrato
from django.contrib.contenttypes.models import ContentType

print("\n" + "="*60)
print("VERIFICAÇÃO DO BANCO DE DADOS")
print("="*60 + "\n")

# 1. Verificar Contabilidades
total_contabilidades = Contabilidade.objects.count()
print(f"📊 CONTABILIDADES: {total_contabilidades}")
if total_contabilidades > 0:
    primeira_contabilidade = Contabilidade.objects.first()
    print(f"   - Primeira: {primeira_contabilidade.razao_social} (ID: {primeira_contabilidade.id})")
    print(f"   - CNPJ: {primeira_contabilidade.cnpj}")

# 2. Verificar Pessoas Jurídicas
total_pj = PessoaJuridica.objects.count()
print(f"\n📊 PESSOAS JURÍDICAS: {total_pj}")
if total_pj > 0:
    primeira_pj = PessoaJuridica.objects.first()
    print(f"   - Primeira: {primeira_pj.razao_social}")
    print(f"   - CNPJ: {primeira_pj.cnpj}")

# 3. Verificar Contratos
total_contratos = Contrato.objects.count()
print(f"\n📊 CONTRATOS: {total_contratos}")
if total_contratos > 0:
    primeiro_contrato = Contrato.objects.first()
    print(f"   - Primeiro Contrato ID: {primeiro_contrato.id}")
    print(f"   - Contabilidade: {primeiro_contrato.contabilidade.razao_social}")
    print(f"   - Ativo: {primeiro_contrato.ativo}")
    print(f"   - Data Início: {primeiro_contrato.data_inicio}")
    print(f"   - Status Cobrança: {primeiro_contrato.status_cobranca}")

# 4. Verificar Usuários
total_usuarios = Usuario.objects.count()
print(f"\n📊 USUÁRIOS: {total_usuarios}")
if total_usuarios > 0:
    primeiro_usuario = Usuario.objects.first()
    print(f"   - Primeiro: {primeiro_usuario.username}")
    if primeiro_usuario.contabilidade:
        print(f"   - Contabilidade: {primeiro_usuario.contabilidade.razao_social}")
    else:
        print(f"   - Contabilidade: NENHUMA")

# 5. Verificar contratos por contabilidade
if total_contabilidades > 0 and total_contratos > 0:
    print(f"\n📊 ANÁLISE POR CONTABILIDADE:")
    for contabilidade in Contabilidade.objects.all()[:3]:  # Primeiras 3
        contratos = Contrato.objects.filter(contabilidade=contabilidade)
        contratos_ativos = contratos.filter(ativo=True)
        print(f"\n   📁 {contabilidade.razao_social}")
        print(f"      - Total Contratos: {contratos.count()}")
        print(f"      - Contratos Ativos: {contratos_ativos.count()}")
        print(f"      - Contratos Inativos: {contratos.count() - contratos_ativos.count()}")

print("\n" + "="*60 + "\n")
