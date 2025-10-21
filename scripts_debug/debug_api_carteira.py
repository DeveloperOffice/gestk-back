"""
Script para debugar o problema da API retornando zeros
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.pessoas.models import Contrato
from rest_framework_simplejwt.tokens import RefreshToken

Usuario = get_user_model()

print("=" * 80)
print("DEBUG: API CARTEIRA RETORNANDO ZEROS")
print("=" * 80)

# 1. Verificar todos os usuários e seus tokens
print("\n🔐 GERANDO TOKENS PARA TESTE:\n")

usuarios_para_testar = ['wando', 'teste_silpa', 'testuser', 'admin']

for username in usuarios_para_testar:
    try:
        usuario = Usuario.objects.get(username=username)
        refresh = RefreshToken.for_user(usuario)
        access_token = str(refresh.access_token)
        
        # Verificar contratos
        if usuario.is_superuser:
            total_contratos = Contrato.objects.all().count()
            ativos = Contrato.objects.filter(ativo=True).count()
        elif usuario.contabilidade:
            total_contratos = Contrato.objects.filter(contabilidade=usuario.contabilidade).count()
            ativos = Contrato.objects.filter(contabilidade=usuario.contabilidade, ativo=True).count()
        else:
            total_contratos = 0
            ativos = 0
        
        print(f"\n{'='*80}")
        print(f"👤 Usuário: {username}")
        print(f"{'='*80}")
        print(f"   ├─ É Superuser? {'✅ SIM' if usuario.is_superuser else '❌ NÃO'}")
        print(f"   ├─ Contabilidade: {usuario.contabilidade.razao_social if usuario.contabilidade else '❌ SEM CONTABILIDADE'}")
        print(f"   ├─ Total Contratos: {total_contratos}")
        print(f"   └─ Contratos Ativos: {ativos}")
        print(f"\n📋 TOKEN DE ACESSO:")
        print(f"   {access_token}")
        print(f"\n🚀 TESTE NO POSTMAN:")
        print(f"   GET http://127.0.0.1:8000/api/gestao/carteira/clientes/")
        print(f"   Headers:")
        print(f"     Authorization: Bearer {access_token}")
        
    except Usuario.DoesNotExist:
        print(f"\n❌ Usuário '{username}' não encontrado")

# 2. Verificar se o servidor está rodando
print("\n" + "="*80)
print("⚠️  IMPORTANTE:")
print("="*80)
print("""
1. Certifique-se que o servidor Django está rodando:
   python manage.py runserver

2. Use um dos tokens acima no Postman

3. Se ainda retornar zeros, verifique:
   - O token está sendo enviado corretamente?
   - O header Authorization está correto?
   - Há algum erro no console do servidor Django?
""")

# 3. Testar a lógica diretamente
print("\n" + "="*80)
print("🧪 TESTANDO A LÓGICA DIRETAMENTE:")
print("="*80)

for username in usuarios_para_testar:
    try:
        usuario = Usuario.objects.get(username=username)
        
        print(f"\n{'='*60}")
        print(f"Testando: {username}")
        print(f"{'='*60}")
        
        # Simular a lógica da API
        if not usuario.is_authenticated:
            print("❌ Usuário não autenticado")
            continue
        
        if usuario.is_superuser:
            print("✅ É SUPERUSER - Buscando TODOS os contratos")
            todos_os_contratos = Contrato.objects.all()
        else:
            if not hasattr(usuario, 'contabilidade') or not usuario.contabilidade:
                print("❌ Usuário não possui contabilidade associada")
                continue
            
            print(f"✅ Usuário COMUM - Buscando contratos de: {usuario.contabilidade.razao_social}")
            todos_os_contratos = Contrato.objects.filter(contabilidade=usuario.contabilidade)
        
        total_clientes = todos_os_contratos.count()
        clientes_ativos_qs = todos_os_contratos.filter(ativo=True)
        clientes_ativos = clientes_ativos_qs.count()
        clientes_inativos = total_clientes - clientes_ativos
        percentual_ativo = (clientes_ativos / total_clientes * 100) if total_clientes > 0 else 0
        
        print(f"\n📊 RESULTADO:")
        print(f"   ├─ Total: {total_clientes}")
        print(f"   ├─ Ativos: {clientes_ativos}")
        print(f"   ├─ Inativos: {clientes_inativos}")
        print(f"   └─ Percentual: {percentual_ativo:.2f}%")
        
        if total_clientes == 0:
            print("\n⚠️  PROBLEMA IDENTIFICADO: Total de clientes = 0")
            if not usuario.is_superuser:
                print(f"   Verificar se a contabilidade '{usuario.contabilidade.razao_social}' tem contratos")
            
    except Usuario.DoesNotExist:
        print(f"❌ Usuário '{username}' não encontrado")
    except Exception as e:
        print(f"❌ Erro ao testar '{username}': {str(e)}")

print("\n" + "="*80)
