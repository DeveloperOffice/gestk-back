"""
Script para testar o endpoint de carteira diretamente
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from apps.core.models import Usuario
from apps.pessoas.models import Contrato
from django.utils import timezone
from datetime import timedelta

print("\n" + "="*60)
print("TESTE DO ENDPOINT DE CARTEIRA")
print("="*60 + "\n")

# 1. Listar usuários disponíveis
print("📋 USUÁRIOS DISPONÍVEIS:\n")
usuarios = Usuario.objects.all()
for i, usuario in enumerate(usuarios, 1):
    contabilidade_nome = usuario.contabilidade.razao_social if usuario.contabilidade else "SEM CONTABILIDADE"
    print(f"{i}. Username: {usuario.username}")
    print(f"   Email: {usuario.email}")
    print(f"   Contabilidade: {contabilidade_nome}")
    
    if usuario.contabilidade:
        contratos = Contrato.objects.filter(contabilidade=usuario.contabilidade)
        contratos_ativos = contratos.filter(ativo=True)
        print(f"   → Total Contratos: {contratos.count()}")
        print(f"   → Contratos Ativos: {contratos_ativos.count()}")
    print()

# 2. Simular o cálculo para um usuário específico
print("\n" + "="*60)
print("SIMULAÇÃO DO CÁLCULO PARA PRIMEIRO USUÁRIO COM CONTRATOS")
print("="*60 + "\n")

# Encontrar primeiro usuário com contabilidade que tem contratos
usuario_teste = None
for usuario in usuarios:
    if usuario.contabilidade:
        contratos = Contrato.objects.filter(contabilidade=usuario.contabilidade)
        if contratos.count() > 0:
            usuario_teste = usuario
            break

if usuario_teste:
    contabilidade = usuario_teste.contabilidade
    print(f"👤 Usuário: {usuario_teste.username}")
    print(f"🏢 Contabilidade: {contabilidade.razao_social}\n")
    
    # Buscar todos os contratos
    todos_os_contratos = Contrato.objects.filter(contabilidade=contabilidade)
    total_clientes = todos_os_contratos.count()
    
    # Calcular status
    clientes_ativos_qs = todos_os_contratos.filter(ativo=True)
    clientes_ativos = clientes_ativos_qs.count()
    clientes_inativos = total_clientes - clientes_ativos
    
    # Clientes novos (últimos 6 meses)
    data_limite_novos = timezone.now().date() - timedelta(days=180)
    clientes_novos = clientes_ativos_qs.filter(
        data_inicio__gte=data_limite_novos
    ).count()
    
    # Percentual
    percentual_ativo = (clientes_ativos / total_clientes * 100) if total_clientes > 0 else 0
    
    print("📊 RESULTADO ESPERADO:")
    print(f"   - Total de Clientes: {total_clientes}")
    print(f"   - Clientes Ativos: {clientes_ativos}")
    print(f"   - Clientes Inativos: {clientes_inativos}")
    print(f"   - Clientes Novos (últimos 6 meses): {clientes_novos}")
    print(f"   - Percentual Ativo: {percentual_ativo:.2f}%")
    
    print("\n📝 RESPOSTA JSON ESPERADA:")
    print(f"""{{
    "summary": {{
        "total_clientes": {total_clientes},
        "clientes_ativos": {clientes_ativos},
        "clientes_inativos": {clientes_inativos},
        "clientes_novos": {clientes_novos},
        "clientes_sem_movimentacao": 0,
        "percentual_ativo": {percentual_ativo:.2f}
    }},
    "results": []
}}""")
    
    print("\n💡 DICA PARA TESTAR NO POSTMAN:")
    print(f"   1. Faça login com: username='{usuario_teste.username}'")
    print(f"   2. Use o token retornado")
    print(f"   3. Acesse: GET http://127.0.0.1:8000/api/gestao/carteira/clientes/")
else:
    print("❌ Nenhum usuário encontrado com contabilidade que possui contratos!")

print("\n" + "="*60 + "\n")
