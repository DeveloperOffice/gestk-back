"""
Script para testar o fluxo completo: Login -> Token -> Carteira
Simula exatamente o que deve ser feito no Postman
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

import requests
from django.contrib.auth import get_user_model

Usuario = get_user_model()

print("=" * 80)
print("🔐 TESTE COMPLETO: LOGIN -> TOKEN -> CARTEIRA")
print("=" * 80)

# URL do servidor
BASE_URL = "http://127.0.0.1:8000"

# Testar login com wando
print("\n1️⃣ PASSO 1: FAZENDO LOGIN")
print("-" * 80)
print("POST http://127.0.0.1:8000/api/auth/token/")
print('Body: {"username": "wando", "password": "gestk2025"}')

login_data = {
    "username": "wando",
    "password": "gestk2025"
}

try:
    # Fazer requisição de login
    response = requests.post(f"{BASE_URL}/api/auth/token/", json=login_data)
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        access_token = data.get('access')
        refresh_token = data.get('refresh')
        
        print("✅ LOGIN BEM-SUCEDIDO!")
        print(f"\n📋 ACCESS TOKEN (primeiros 50 caracteres):")
        print(f"{access_token[:50]}...")
        
        # Agora testar o endpoint de carteira
        print("\n" + "=" * 80)
        print("2️⃣ PASSO 2: ACESSANDO ENDPOINT DE CARTEIRA")
        print("-" * 80)
        print("GET http://127.0.0.1:8000/api/gestao/carteira/clientes/")
        print(f'Headers: Authorization: Bearer {access_token[:30]}...')
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response_carteira = requests.get(f"{BASE_URL}/api/gestao/carteira/clientes/", headers=headers)
        
        print(f"\nStatus Code: {response_carteira.status_code}")
        
        if response_carteira.status_code == 200:
            data_carteira = response_carteira.json()
            print("\n✅ CARTEIRA OBTIDA COM SUCESSO!")
            print("\n📊 RESULTADO COMPLETO:")
            import json
            print(json.dumps(data_carteira, indent=2, ensure_ascii=False))
            
            summary = data_carteira.get('summary', {})
            print("\n" + "=" * 80)
            print("📈 RESUMO DOS DADOS:")
            print("=" * 80)
            print(f"   ├─ Total de Clientes: {summary.get('total_clientes')}")
            print(f"   ├─ Clientes Ativos: {summary.get('clientes_ativos')}")
            print(f"   ├─ Clientes Inativos: {summary.get('clientes_inativos')}")
            print(f"   ├─ Clientes Novos: {summary.get('clientes_novos')}")
            print(f"   └─ Percentual Ativo: {summary.get('percentual_ativo')}%")
            
            if summary.get('total_clientes', 0) > 0:
                print("\n✅ SUCESSO! A API está funcionando corretamente!")
            else:
                print("\n⚠️  ATENÇÃO: API retornou zeros. Verifique os logs do Django.")
        else:
            print(f"\n❌ ERRO AO BUSCAR CARTEIRA:")
            print(f"Status: {response_carteira.status_code}")
            print(f"Resposta: {response_carteira.text}")
    else:
        print(f"\n❌ ERRO NO LOGIN:")
        print(f"Status: {response.status_code}")
        print(f"Resposta: {response.text}")
        
        # Verificar se usuário existe no banco
        print("\n" + "=" * 80)
        print("🔍 VERIFICANDO USUÁRIO NO BANCO DE DADOS:")
        print("=" * 80)
        try:
            usuario = Usuario.objects.get(username='wando')
            print(f"✅ Usuário encontrado: {usuario.username}")
            print(f"   ├─ É Superuser? {'✅ SIM' if usuario.is_superuser else '❌ NÃO'}")
            print(f"   ├─ Está Ativo? {'✅ SIM' if usuario.is_active else '❌ NÃO'}")
            print(f"   └─ Contabilidade: {usuario.contabilidade.razao_social if usuario.contabilidade else '❌ SEM CONTABILIDADE'}")
            print("\n⚠️  A senha pode estar incorreta. Resetando senha para 'gestk2025'...")
            
            usuario.set_password('gestk2025')
            usuario.save()
            print("✅ Senha resetada! Execute o script novamente.")
            
        except Usuario.DoesNotExist:
            print("❌ Usuário 'wando' não existe no banco de dados")

except requests.exceptions.ConnectionError:
    print("\n" + "=" * 80)
    print("❌ ERRO: Não foi possível conectar ao servidor!")
    print("=" * 80)
    print("⚠️  Certifique-se que o servidor Django está rodando:")
    print("   python manage.py runserver")
    print("\nAbra outro terminal e execute o comando acima antes de rodar este script.")

except Exception as e:
    print(f"\n❌ ERRO INESPERADO: {str(e)}")
    import traceback
    traceback.print_exc()

# Instruções para o Postman
print("\n" + "=" * 80)
print("📝 COMO FAZER NO POSTMAN (PASSO A PASSO)")
print("=" * 80)

print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           PASSO 1: FAZER LOGIN                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

1. Abra o Postman
2. Crie uma nova requisição
3. Selecione o method: POST
4. Cole a URL: http://127.0.0.1:8000/api/auth/token/
5. Vá na aba "Body"
6. Selecione "raw" e "JSON"
7. Cole este JSON:
   
   {
       "username": "wando",
       "password": "gestk2025"
   }

8. Clique em "Send"
9. COPIE o valor do campo "access" da resposta

╔══════════════════════════════════════════════════════════════════════════════╗
║                     PASSO 2: ACESSAR ENDPOINT CARTEIRA                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

1. Crie uma NOVA requisição (ou mude a anterior)
2. Selecione o method: GET (não POST!)
3. Cole a URL: http://127.0.0.1:8000/api/gestao/carteira/clientes/
4. Vá na aba "Headers"
5. Adicione um novo header:
   Key: Authorization
   Value: Bearer SEU_TOKEN_AQUI
   
   ⚠️ IMPORTANTE: Tem que ter um ESPAÇO entre "Bearer" e o token!
   
6. Vá na aba "Body" e selecione "none"
7. Clique em "Send"

╔══════════════════════════════════════════════════════════════════════════════╗
║                         RESULTADO ESPERADO                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

{
    "summary": {
        "total_clientes": 2186,
        "clientes_ativos": 1550,
        "clientes_inativos": 636,
        "clientes_novos": 0,
        "clientes_sem_movimentacao": 0,
        "percentual_ativo": 70.91
    },
    "results": []
}

╔══════════════════════════════════════════════════════════════════════════════╗
║                     ❌ O QUE VOCÊ ESTAVA FAZENDO ERRADO                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

1. ❌ Usando POST em vez de GET no endpoint de carteira
2. ❌ Enviando username/password no body do endpoint de carteira
3. ❌ Não usando o token no header Authorization

╔══════════════════════════════════════════════════════════════════════════════╗
║                     ✅ FORMA CORRETA                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

Endpoint de LOGIN:
  - Method: POST
  - URL: /api/auth/token/
  - Body: username + password
  - Retorna: access token

Endpoint de CARTEIRA:
  - Method: GET
  - URL: /api/gestao/carteira/clientes/
  - Headers: Authorization: Bearer {token}
  - Body: none
  - Retorna: dados da carteira

""")

print("=" * 80)
