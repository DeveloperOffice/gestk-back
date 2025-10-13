"""
Testes para módulo Admin (Usuarios e Contratos)
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.core.models import Usuario, Contabilidade
from apps.pessoas.models import Contrato, PessoaJuridica, PessoaFisica
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
import uuid


class UsuarioViewSetTest(TestCase):
    """Testes para UsuarioViewSet"""
    
    def setUp(self):
        """Configuração inicial dos testes"""
        self.client = APIClient()
        
        # Criar contabilidade
        self.contabilidade = Contabilidade.objects.create(
            razao_social='Contabilidade Teste LTDA',
            nome_fantasia='Contabilidade Teste',
            cnpj='12345678000190',
            ativo=True
        )
        
        # Criar usuário ADMIN
        self.admin_user = Usuario.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='admin123',
            contabilidade=self.contabilidade,
            tipo_usuario='admin',
            pode_administrar_usuarios=True,
            ativo=True,
            is_active=True
        )
        
        # Criar usuário operacional
        self.operacional_user = Usuario.objects.create_user(
            username='operacional_test',
            email='operacional@test.com',
            password='oper123',
            contabilidade=self.contabilidade,
            tipo_usuario='operacional',
            modulos_acessiveis=['fiscal', 'contabil'],
            ativo=True,
            is_active=True
        )
        
        # URLs
        self.list_url = reverse('admin-usuarios-list')
        self.detail_url = lambda pk: reverse('admin-usuarios-detail', kwargs={'pk': pk})
    
    def test_list_usuarios_admin(self):
        """Testa listagem de usuários por ADMIN"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 2)
    
    def test_create_usuario_admin(self):
        """Testa criação de usuário por ADMIN"""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'username': 'novo_usuario',
            'email': 'novo@test.com',
            'password': 'senha123',
            'password_confirm': 'senha123',
            'first_name': 'Novo',
            'last_name': 'Usuario',
            'cpf': '12345678901',
            'contabilidade': str(self.contabilidade.id),
            'tipo_usuario': 'operacional',
            'modulos_acessiveis': ['fiscal'],
            'ativo': True,
            'is_active': True
        }
        
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], 'novo_usuario')
        self.assertEqual(response.data['email'], 'novo@test.com')
        
        # Verificar se foi criado no banco
        usuario = Usuario.objects.get(username='novo_usuario')
        self.assertTrue(usuario.check_password('senha123'))
    
    def test_create_usuario_senha_invalida(self):
        """Testa criação com senhas não coincidentes"""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'username': 'novo_usuario',
            'email': 'novo@test.com',
            'password': 'senha123',
            'password_confirm': 'senha456',
            'contabilidade': str(self.contabilidade.id),
            'tipo_usuario': 'operacional'
        }
        
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password_confirm', str(response.data))
    
    def test_create_usuario_admin_nao_pode_criar_superuser(self):
        """Testa que ADMIN não pode criar SUPERUSER"""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'username': 'novo_super',
            'email': 'super@test.com',
            'password': 'senha123',
            'password_confirm': 'senha123',
            'tipo_usuario': 'superuser'
        }
        
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_retrieve_usuario(self):
        """Testa detalhamento de usuário"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get(self.detail_url(self.operacional_user.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'operacional_test')
        self.assertIn('estatisticas', response.data)
    
    def test_update_usuario(self):
        """Testa atualização de usuário"""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'first_name': 'Nome Atualizado',
            'modulos_acessiveis': ['fiscal', 'contabil', 'rh']
        }
        
        response = self.client.patch(
            self.detail_url(self.operacional_user.id),
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Nome Atualizado')
        self.assertEqual(len(response.data['modulos_acessiveis']), 3)
        
        # Verificar no banco
        self.operacional_user.refresh_from_db()
        self.assertEqual(self.operacional_user.first_name, 'Nome Atualizado')
    
    def test_update_senha(self):
        """Testa atualização de senha"""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'password': 'nova_senha123',
            'password_confirm': 'nova_senha123'
        }
        
        response = self.client.patch(
            self.detail_url(self.operacional_user.id),
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar se a senha foi alterada
        self.operacional_user.refresh_from_db()
        self.assertTrue(self.operacional_user.check_password('nova_senha123'))
    
    def test_delete_usuario(self):
        """Testa deleção de usuário (soft delete)"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.delete(self.detail_url(self.operacional_user.id))
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verificar soft delete
        self.operacional_user.refresh_from_db()
        self.assertFalse(self.operacional_user.ativo)
        self.assertFalse(self.operacional_user.is_active)
        self.assertIn('_deleted_', self.operacional_user.username)
    
    def test_admin_nao_pode_deletar_a_si_mesmo(self):
        """Testa que ADMIN não pode deletar a si mesmo"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.delete(self.detail_url(self.admin_user.id))
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_ativar_usuario(self):
        """Testa ativação de usuário"""
        self.operacional_user.ativo = False
        self.operacional_user.is_active = False
        self.operacional_user.save()
        
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.post(
            reverse('admin-usuarios-ativar', kwargs={'pk': self.operacional_user.id})
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar no banco
        self.operacional_user.refresh_from_db()
        self.assertTrue(self.operacional_user.ativo)
        self.assertTrue(self.operacional_user.is_active)
    
    def test_desativar_usuario(self):
        """Testa desativação de usuário"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.post(
            reverse('admin-usuarios-desativar', kwargs={'pk': self.operacional_user.id})
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar no banco
        self.operacional_user.refresh_from_db()
        self.assertFalse(self.operacional_user.ativo)
        self.assertFalse(self.operacional_user.is_active)
    
    def test_resetar_senha(self):
        """Testa reset de senha"""
        self.client.force_authenticate(user=self.admin_user)
        
        token_version_anterior = self.operacional_user.token_version
        
        response = self.client.post(
            reverse('admin-usuarios-resetar-senha', kwargs={'pk': self.operacional_user.id}),
            {'nova_senha': 'senha_resetada123'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token_version', response.data)
        
        # Verificar no banco
        self.operacional_user.refresh_from_db()
        self.assertTrue(self.operacional_user.check_password('senha_resetada123'))
        self.assertEqual(self.operacional_user.token_version, token_version_anterior + 1)
    
    def test_atualizar_modulos(self):
        """Testa atualização de módulos"""
        self.client.force_authenticate(user=self.admin_user)
        
        novos_modulos = ['fiscal', 'contabil', 'rh', 'dashboards']
        
        response = self.client.post(
            reverse('admin-usuarios-atualizar-modulos', kwargs={'pk': self.operacional_user.id}),
            {'modulos': novos_modulos},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar no banco
        self.operacional_user.refresh_from_db()
        self.assertEqual(set(self.operacional_user.modulos_acessiveis), set(novos_modulos))
    
    def test_estatisticas(self):
        """Testa endpoint de estatísticas"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get(reverse('admin-usuarios-estatisticas'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total', response.data)
        self.assertIn('ativos', response.data)
        self.assertIn('inativos', response.data)
        self.assertIn('por_tipo', response.data)
        self.assertIn('por_modulo', response.data)
    
    def test_filtro_tipo_usuario(self):
        """Testa filtro por tipo de usuário"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get(self.list_url, {'tipo_usuario': 'operacional'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Todos os resultados devem ser operacionais
        for usuario in response.data['results']:
            self.assertEqual(usuario['tipo_usuario'], 'operacional')
    
    def test_filtro_busca(self):
        """Testa filtro de busca"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get(self.list_url, {'busca': 'operacional'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
    
    def test_usuario_sem_permissao_nao_acessa(self):
        """Testa que usuário sem permissão não acessa"""
        # Criar usuário sem permissão de administrar
        usuario_sem_permissao = Usuario.objects.create_user(
            username='sem_permissao',
            email='sem@test.com',
            password='senha123',
            contabilidade=self.contabilidade,
            tipo_usuario='operacional',
            pode_administrar_usuarios=False
        )
        
        self.client.force_authenticate(user=usuario_sem_permissao)
        
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# Importar testes de contratos
from .contrato_tests import ContratoViewSetTest
