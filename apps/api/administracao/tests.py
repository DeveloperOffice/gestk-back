"""
Testes para API de Administração
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from apps.core.models import Contabilidade, UsuarioAcesso
from apps.administracao.models import ContratoGestk
from apps.pessoas.models import PessoaJuridica, PessoaFisica, Contrato
import json

User = get_user_model()


class ContratoGestkAPITestCase(APITestCase):
    """
    Testes para API de Contratos GESTK
    """
    
    def setUp(self):
        """
        Configuração inicial para os testes
        """
        # Criar usuário admin
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@gestk.com',
            password='admin123',
            tipo_usuario='admin',
            is_staff=True
        )
        
        # Criar contabilidade
        self.contabilidade = Contabilidade.objects.create(
            razao_social='Contabilidade Teste LTDA',
            nome_fantasia='Contabilidade Teste',
            cnpj='12345678000195',
            ativo=True
        )
        
        # Criar acesso do usuário à contabilidade
        self.acesso = UsuarioAcesso.objects.create(
            usuario=self.admin_user,
            contabilidade=self.contabilidade,
            role='admin',
            data_inicio='2024-01-01',
            ativo=True
        )
        
        # Token de autenticação
        refresh = RefreshToken.for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        self.client.force_authenticate(user=self.admin_user)
    
    def test_criar_contrato_gestk(self):
        """
        Testa criação de contrato GESTK
        """
        url = reverse('contratogestk-list')
        data = {
            'contabilidade': str(self.contabilidade.id),
            'numero_contrato': 'GESTK-2024-001',
            'data_inicio': '2024-01-01',
            'plano_servico': 'basic',
            'modulos_inclusos': ['contabil', 'fiscal'],
            'limites_usuarios': 5,
            'limites_empresas': 10,
            'valor_mensal': 299.90,
            'status': 'ativo'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ContratoGestk.objects.count(), 1)
        
        contrato = ContratoGestk.objects.first()
        self.assertEqual(contrato.numero_contrato, 'GESTK-2024-001')
        self.assertEqual(contrato.contabilidade, self.contabilidade)
    
    def test_listar_contratos_gestk(self):
        """
        Testa listagem de contratos GESTK
        """
        # Criar contrato
        ContratoGestk.objects.create(
            contabilidade=self.contabilidade,
            numero_contrato='GESTK-2024-001',
            data_inicio='2024-01-01',
            plano_servico='basic',
            valor_mensal=299.90
        )
        
        url = reverse('contratogestk-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_suspender_contrato_gestk(self):
        """
        Testa suspensão de contrato GESTK
        """
        contrato = ContratoGestk.objects.create(
            contabilidade=self.contabilidade,
            numero_contrato='GESTK-2024-001',
            data_inicio='2024-01-01',
            plano_servico='basic',
            valor_mensal=299.90,
            status='ativo'
        )
        
        url = reverse('contratogestk-suspender', kwargs={'pk': contrato.id})
        data = {'motivo': 'Inadimplência'}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        contrato.refresh_from_db()
        self.assertEqual(contrato.status, 'suspenso')
        self.assertEqual(contrato.motivo_suspensao, 'Inadimplência')
    
    def test_cancelar_contrato_gestk(self):
        """
        Testa cancelamento de contrato GESTK
        """
        contrato = ContratoGestk.objects.create(
            contabilidade=self.contabilidade,
            numero_contrato='GESTK-2024-001',
            data_inicio='2024-01-01',
            plano_servico='basic',
            valor_mensal=299.90,
            status='ativo'
        )
        
        url = reverse('contratogestk-cancelar', kwargs={'pk': contrato.id})
        data = {'motivo': 'Solicitação do cliente'}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        contrato.refresh_from_db()
        self.assertEqual(contrato.status, 'cancelado')
        self.assertEqual(contrato.motivo_cancelamento, 'Solicitação do cliente')


class UsuarioAcessoAPITestCase(APITestCase):
    """
    Testes para API de Acessos de Usuário
    """
    
    def setUp(self):
        """
        Configuração inicial para os testes
        """
        # Criar usuário admin
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@gestk.com',
            password='admin123',
            tipo_usuario='admin',
            is_staff=True
        )
        
        # Criar usuário comum
        self.user = User.objects.create_user(
            username='user',
            email='user@gestk.com',
            password='user123',
            tipo_usuario='operacional'
        )
        
        # Criar contabilidade
        self.contabilidade = Contabilidade.objects.create(
            razao_social='Contabilidade Teste LTDA',
            nome_fantasia='Contabilidade Teste',
            cnpj='12345678000195',
            ativo=True
        )
        
        # Token de autenticação
        refresh = RefreshToken.for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        self.client.force_authenticate(user=self.admin_user)
    
    def test_criar_acesso_usuario(self):
        """
        Testa criação de acesso de usuário
        """
        url = reverse('usuarioacesso-list')
        data = {
            'usuario': str(self.user.id),
            'contabilidade': str(self.contabilidade.id),
            'role': 'operacional',
            'modulos_acesso': ['contabil', 'fiscal'],
            'data_inicio': '2024-01-01',
            'ativo': True
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UsuarioAcesso.objects.count(), 1)
        
        acesso = UsuarioAcesso.objects.first()
        self.assertEqual(acesso.usuario, self.user)
        self.assertEqual(acesso.contabilidade, self.contabilidade)
    
    def test_listar_acessos_usuario(self):
        """
        Testa listagem de acessos de usuário
        """
        # Criar acesso
        UsuarioAcesso.objects.create(
            usuario=self.user,
            contabilidade=self.contabilidade,
            role='operacional',
            data_inicio='2024-01-01',
            ativo=True
        )
        
        url = reverse('usuarioacesso-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_desativar_acesso_usuario(self):
        """
        Testa desativação de acesso de usuário
        """
        acesso = UsuarioAcesso.objects.create(
            usuario=self.user,
            contabilidade=self.contabilidade,
            role='operacional',
            data_inicio='2024-01-01',
            ativo=True
        )
        
        url = reverse('usuarioacesso-desativar', kwargs={'pk': acesso.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        acesso.refresh_from_db()
        self.assertFalse(acesso.ativo)


class MultiTenantMiddlewareTestCase(TestCase):
    """
    Testes para Middleware Multi-Tenant
    """
    
    def setUp(self):
        """
        Configuração inicial para os testes
        """
        self.user = User.objects.create_user(
            username='user',
            email='user@gestk.com',
            password='user123',
            tipo_usuario='operacional'
        )
        
        self.contabilidade = Contabilidade.objects.create(
            razao_social='Contabilidade Teste LTDA',
            nome_fantasia='Contabilidade Teste',
            cnpj='12345678000195',
            ativo=True
        )
        
        self.acesso = UsuarioAcesso.objects.create(
            usuario=self.user,
            contabilidade=self.contabilidade,
            role='operacional',
            data_inicio='2024-01-01',
            ativo=True
        )
    
    def test_middleware_define_contabilidade_contexto(self):
        """
        Testa se o middleware define corretamente o contexto da contabilidade
        """
        from django.test import RequestFactory
        from apps.api.shared.middleware import MultiTenantContextMiddleware
        
        factory = RequestFactory()
        request = factory.get('/api/test/')
        request.user = self.user
        
        middleware = MultiTenantContextMiddleware(lambda req: None)
        middleware(request)
        
        # Verificar se a contabilidade foi definida no contexto
        self.assertEqual(request.contabilidade, self.contabilidade)
    
    def test_middleware_atualiza_ultima_contabilidade(self):
        """
        Testa se o middleware atualiza a última contabilidade acessada
        """
        from django.test import RequestFactory
        from apps.api.shared.middleware import MultiTenantContextMiddleware
        
        factory = RequestFactory()
        request = factory.get('/api/test/', HTTP_X_CONTABILIDADE_ID=str(self.contabilidade.id))
        request.user = self.user
        
        middleware = MultiTenantContextMiddleware(lambda req: None)
        middleware(request)
        
        # Verificar se a última contabilidade foi atualizada
        self.user.refresh_from_db()
        self.assertEqual(self.user.ultima_contabilidade, self.contabilidade)
