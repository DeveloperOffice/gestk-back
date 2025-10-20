"""
Testar autenticação dos usuários
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from django.contrib.auth import authenticate, get_user_model

User = get_user_model()

print('='*80)
print('TESTE DE AUTENTICAÇÃO')
print('='*80)

# Teste 1: Login com wando
print('\n1. Testando login: wando')
user1 = authenticate(username='wando', password='H33tsupa!')
if user1:
    print(f'   ✅ Login OK - {user1.username} ({user1.email})')
else:
    print(f'   ❌ Falha no login - Senha incorreta ou usuário inativo')

# Teste 2: Login com email juridico@office-ce.com.br
print('\n2. Testando login: juridico@office-ce.com.br')
user2 = authenticate(username='juridico@office-ce.com.br', password='H33tsupa!')
if user2:
    print(f'   ✅ Login OK - {user2.username} ({user2.email})')
else:
    print(f'   ❌ Falha no login - Username deve ser "wando", não o email')

# Teste 3: Verificar se pode resetar senha
print('\n3. Resetando senha do usuário wando para: gestk2025')
try:
    wando = User.objects.get(username='wando')
    wando.set_password('gestk2025')
    wando.save()
    print(f'   ✅ Senha alterada com sucesso!')
    
    # Testar nova senha
    user_test = authenticate(username='wando', password='gestk2025')
    if user_test:
        print(f'   ✅ Teste de login com nova senha: OK')
    else:
        print(f'   ❌ Teste de login com nova senha: FALHOU')
        
except Exception as e:
    print(f'   ❌ Erro ao resetar senha: {e}')

# Teste 4: Admin
print('\n4. Testando login: admin')
user4 = authenticate(username='admin', password='admin123')
if user4:
    print(f'   ✅ Login OK - {user4.username}')
else:
    print(f'   ❌ Falha no login')

print('\n' + '='*80)
print('RESUMO PARA LOGIN:')
print('='*80)
print('\n📱 ADMIN (Frontend Admin):')
print('   URL: http://localhost:3000/admin/login')
print('   Username: wando')
print('   Password: gestk2025 (nova senha)')
print()
print('📱 CLIENT (Frontend Cliente):')
print('   URL: http://localhost:3000/login')
print('   Username: operacional')
print('   Password: (use a senha original ou redefina)')
print()
print('🔧 Django Admin:')
print('   URL: http://127.0.0.1:8000/admin/')
print('   Username: wando ou admin')
print('   Password: gestk2025 ou admin123')
print('='*80)
