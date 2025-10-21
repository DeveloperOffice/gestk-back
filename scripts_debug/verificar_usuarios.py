"""
Script para verificar usuários do sistema
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

print('='*80)
print('USUÁRIOS CADASTRADOS NO SISTEMA')
print('='*80)

users = User.objects.all()
print(f'\nTotal de usuários: {users.count()}\n')

if users.count() == 0:
    print('⚠️  NENHUM USUÁRIO CADASTRADO!')
    print('\nCriando superusuário padrão...')
    
    # Criar superusuário
    admin = User.objects.create_superuser(
        username='admin',
        email='admin@gestk.com',
        password='admin123'
    )
    print(f'✅ Superusuário criado: admin / admin123')
    
    # Criar usuário cliente
    cliente = User.objects.create_user(
        username='cliente',
        email='cliente@gestk.com',
        password='cliente123',
        is_staff=False
    )
    print(f'✅ Usuário cliente criado: cliente / cliente123')
    
    print('\n' + '='*80)
    print('TESTE DE LOGIN:')
    print('  Admin: http://127.0.0.1:8000/admin/')
    print('    Username: admin')
    print('    Password: admin123')
    print()
    print('  API: http://127.0.0.1:8000/api/auth/login/')
    print('    Username: admin ou cliente')
    print('    Password: admin123 ou cliente123')
    print('='*80)

else:
    for user in users:
        print(f'Username: {user.username}')
        print(f'Email: {user.email}')
        print(f'Is Active: {user.is_active}')
        print(f'Is Staff: {user.is_staff}')
        print(f'Is Superuser: {user.is_superuser}')
        
        # Verificar campos customizados se existirem
        if hasattr(user, 'tipo_usuario'):
            print(f'Tipo: {user.tipo_usuario}')
        if hasattr(user, 'contabilidade'):
            print(f'Contabilidade: {user.contabilidade}')
        
        print('-'*80)
    
    print('\n✅ Para testar login:')
    print('  Admin Django: http://127.0.0.1:8000/admin/')
    print('  API: http://127.0.0.1:8000/api/auth/login/')
    print()
    print('⚠️  Se não conseguir logar, verifique:')
    print('  1. Senha correta')
    print('  2. Usuário ativo (is_active=True)')
    print('  3. Email correto para o username')
