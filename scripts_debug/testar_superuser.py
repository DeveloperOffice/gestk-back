"""
Script para testar o comportamento da API com superuser
Verifica se superuser vê todos os contratos do banco de dados
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.pessoas.models import Contrato
from apps.core.models import Contabilidade

Usuario = get_user_model()

print("=" * 80)
print("TESTE DE SUPERUSER - VISUALIZAÇÃO DE TODOS OS CONTRATOS")
print("=" * 80)

# 1. Listar todos os usuários
print("\n📋 USUÁRIOS DISPONÍVEIS:\n")
usuarios = Usuario.objects.all()

for i, usuario in enumerate(usuarios, 1):
    contabilidade_info = f"{usuario.contabilidade.razao_social}" if usuario.contabilidade else "SEM CONTABILIDADE"
    superuser_badge = " 🔑 [SUPERUSER]" if usuario.is_superuser else ""
    
    # Contar contratos
    if usuario.is_superuser:
        total_contratos = Contrato.objects.all().count()
        ativos = Contrato.objects.filter(ativo=True).count()
    elif usuario.contabilidade:
        total_contratos = Contrato.objects.filter(contabilidade=usuario.contabilidade).count()
        ativos = Contrato.objects.filter(contabilidade=usuario.contabilidade, ativo=True).count()
    else:
        total_contratos = 0
        ativos = 0
    
    print(f"{i}. {usuario.username}{superuser_badge}")
    print(f"   └─ Contabilidade: {contabilidade_info}")
    print(f"   └─ Contratos visíveis: {total_contratos} ({ativos} ativos)")

# 2. Estatísticas gerais do banco de dados
print("\n" + "=" * 80)
print("📊 ESTATÍSTICAS GERAIS DO BANCO DE DADOS")
print("=" * 80)

total_contabilidades = Contabilidade.objects.count()
total_contratos_bd = Contrato.objects.count()
total_contratos_ativos_bd = Contrato.objects.filter(ativo=True).count()
total_contratos_inativos_bd = Contrato.objects.filter(ativo=False).count()

print(f"\n✅ Total de Contabilidades: {total_contabilidades}")
print(f"✅ Total de Contratos (BD): {total_contratos_bd}")
print(f"   ├─ Ativos: {total_contratos_ativos_bd}")
print(f"   └─ Inativos: {total_contratos_inativos_bd}")

# 3. Testar com o usuário wando (superuser)
print("\n" + "=" * 80)
print("🔑 TESTE COM SUPERUSER: wando")
print("=" * 80)

try:
    wando = Usuario.objects.get(username='wando')
    
    print(f"\n👤 Usuário: {wando.username}")
    print(f"   ├─ É Superuser? {'✅ SIM' if wando.is_superuser else '❌ NÃO'}")
    print(f"   └─ Contabilidade: {wando.contabilidade.razao_social if wando.contabilidade else 'SEM CONTABILIDADE'}")
    
    # Simular o que a API vai retornar
    if wando.is_superuser:
        todos_os_contratos = Contrato.objects.all()
    else:
        if wando.contabilidade:
            todos_os_contratos = Contrato.objects.filter(contabilidade=wando.contabilidade)
        else:
            todos_os_contratos = Contrato.objects.none()
    
    total = todos_os_contratos.count()
    ativos = todos_os_contratos.filter(ativo=True).count()
    inativos = total - ativos
    percentual = (ativos / total * 100) if total > 0 else 0
    
    print(f"\n📊 RESPOSTA ESPERADA DA API PARA 'wando':")
    print(f"   ├─ Total de clientes: {total}")
    print(f"   ├─ Clientes ativos: {ativos}")
    print(f"   ├─ Clientes inativos: {inativos}")
    print(f"   └─ Percentual ativo: {percentual:.2f}%")
    
    print(f"\n✅ JSON ESPERADO:")
    print(f'''{{
    "summary": {{
        "total_clientes": {total},
        "clientes_ativos": {ativos},
        "clientes_inativos": {inativos},
        "clientes_novos": 0,
        "clientes_sem_movimentacao": 0,
        "percentual_ativo": {percentual:.2f}
    }},
    "results": []
}}''')

except Usuario.DoesNotExist:
    print("\n❌ Usuário 'wando' não encontrado no banco de dados")

# 4. Comparar com usuário comum (teste_silpa)
print("\n" + "=" * 80)
print("👤 COMPARAÇÃO COM USUÁRIO COMUM: teste_silpa")
print("=" * 80)

try:
    teste_silpa = Usuario.objects.get(username='teste_silpa')
    
    print(f"\n👤 Usuário: {teste_silpa.username}")
    print(f"   ├─ É Superuser? {'✅ SIM' if teste_silpa.is_superuser else '❌ NÃO'}")
    print(f"   └─ Contabilidade: {teste_silpa.contabilidade.razao_social if teste_silpa.contabilidade else 'SEM CONTABILIDADE'}")
    
    # Simular o que a API vai retornar
    if teste_silpa.is_superuser:
        todos_os_contratos = Contrato.objects.all()
    else:
        if teste_silpa.contabilidade:
            todos_os_contratos = Contrato.objects.filter(contabilidade=teste_silpa.contabilidade)
        else:
            todos_os_contratos = Contrato.objects.none()
    
    total = todos_os_contratos.count()
    ativos = todos_os_contratos.filter(ativo=True).count()
    inativos = total - ativos
    percentual = (ativos / total * 100) if total > 0 else 0
    
    print(f"\n📊 RESPOSTA ESPERADA DA API PARA 'teste_silpa':")
    print(f"   ├─ Total de clientes: {total}")
    print(f"   ├─ Clientes ativos: {ativos}")
    print(f"   ├─ Clientes inativos: {inativos}")
    print(f"   └─ Percentual ativo: {percentual:.2f}%")

except Usuario.DoesNotExist:
    print("\n❌ Usuário 'teste_silpa' não encontrado no banco de dados")

# 5. Instruções para teste no Postman
print("\n" + "=" * 80)
print("🚀 INSTRUÇÕES PARA TESTAR NO POSTMAN")
print("=" * 80)

print("""
1️⃣ LOGIN COM SUPERUSER (wando):
   POST http://127.0.0.1:8000/api/auth/token/
   Body: {"username": "wando", "password": "SENHA_AQUI"}
   
2️⃣ USAR O TOKEN RETORNADO:
   Copie o 'access' token da resposta
   
3️⃣ TESTAR ENDPOINT CARTEIRA:
   GET http://127.0.0.1:8000/api/gestao/carteira/clientes/
   Headers: 
     - Authorization: Bearer {TOKEN_AQUI}
   
4️⃣ RESPOSTA ESPERADA:
   - Superuser (wando): Deve retornar TODOS os contratos do banco de dados
   - Usuário comum (teste_silpa): Deve retornar apenas contratos da sua contabilidade

✅ DIFERENÇA CHAVE:
   - Superuser vê: {total_contratos_bd} contratos
   - teste_silpa vê: Apenas contratos da sua contabilidade (906)
""")

print("\n" + "=" * 80)
