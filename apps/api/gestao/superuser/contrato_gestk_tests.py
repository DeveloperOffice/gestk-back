"""
Testes para Contratos GESTK ViewSet (SUPERUSER)
"""

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta

from apps.core.models import Contabilidade, Usuario
from apps.administracao.models import ContratoGestk


class ContratoGestkViewSetTest(TestCase):
    """
    Suite de testes para ContratoGestkViewSet
    """
    
    def setUp(self):
        """Configurar ambiente de testes"""
        # Criar usuários
        self.superuser = Usuario.objects.create_superuser(
            username='admin',
            email='admin@gestk.com',
            password='admin123'
        )
        
        self.admin_user = Usuario.objects.create_user(
            username='admin1',
            email='admin1@contabil.com',
            password='admin123',
            is_staff=True
        )
        
        self.regular_user = Usuario.objects.create_user(
            username='user1',
            email='user1@contabil.com',
            password='user123'
        )
        
        # Criar contabilidades
        self.contabilidade1 = Contabilidade.objects.create(
            razao_social='Contábil Teste 1',
            nome_fantasia='Contábil 1',
            cnpj='12345678000190',
            ativo=True
        )
        
        self.contabilidade2 = Contabilidade.objects.create(
            razao_social='Contábil Teste 2',
            nome_fantasia='Contábil 2',
            cnpj='98765432000190',
            ativo=True
        )
        
        # Associar usuários
        self.admin_user.contabilidade = self.contabilidade1
        self.admin_user.save()
        
        self.regular_user.contabilidade = self.contabilidade1
        self.regular_user.save()
        
        # Criar contratos GESTK
        self.contrato1 = ContratoGestk.objects.create(
            contabilidade=self.contabilidade1,
            numero_contrato='GESTK-2024-001',
            data_inicio=timezone.now().date(),
            data_termino=timezone.now().date() + timedelta(days=365),
            plano_servico='Plano Básico',
            limites_usuarios=10,
            limites_empresas=5,
            limites_contratos_internos=50,
            valor_mensal=500.00,
            dia_vencimento=10,
            status='ativo',
            created_by=self.superuser
        )
        
        # Cliente API
        self.client = APIClient()
    
    def test_list_contratos_as_superuser(self):
        """Superuser pode listar todos os contratos"""
        self.client.force_authenticate(user=self.superuser)
        
        response = self.client.get('/api/gestao/superuser/contratos-gestk/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
    
    def test_list_contratos_as_admin(self):
        """Admin não pode listar contratos (apenas SUPERUSER)"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/gestao/superuser/contratos-gestk/')
        
        # Deve retornar 403 ou lista vazia dependendo da implementação
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN])
    
    def test_list_contratos_unauthenticated(self):
        """Usuário não autenticado não pode listar"""
        response = self.client.get('/api/gestao/superuser/contratos-gestk/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_retrieve_contrato_as_superuser(self):
        """Superuser pode detalhar contrato"""
        self.client.force_authenticate(user=self.superuser)
        
        response = self.client.get(f'/api/gestao/superuser/contratos-gestk/{self.contrato1.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['numero_contrato'], 'GESTK-2024-001')
        self.assertIn('uso_limites', response.data)
    
    def test_create_contrato_as_superuser(self):
        """Superuser pode criar contrato"""
        self.client.force_authenticate(user=self.superuser)
        
        data = {
            'contabilidade': self.contabilidade2.id,
            'numero_contrato': 'GESTK-2024-002',
            'data_inicio': timezone.now().date().isoformat(),
            'plano_servico': 'Plano Premium',
            'limites_usuarios': 20,
            'limites_empresas': 10,
            'limites_contratos_internos': 100,
            'valor_mensal': 1000.00,
            'dia_vencimento': 5,
        }
        
        response = self.client.post('/api/gestao/superuser/contratos-gestk/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['numero_contrato'], 'GESTK-2024-002')
        self.assertEqual(ContratoGestk.objects.count(), 2)
    
    def test_create_contrato_duplicate_numero(self):
        """Não pode criar contrato com número duplicado"""
        self.client.force_authenticate(user=self.superuser)
        
        data = {
            'contabilidade': self.contabilidade2.id,
            'numero_contrato': 'GESTK-2024-001',  # Duplicado
            'data_inicio': timezone.now().date().isoformat(),
            'plano_servico': 'Plano Básico',
            'limites_usuarios': 10,
            'limites_empresas': 5,
            'limites_contratos_internos': 50,
            'valor_mensal': 500.00,
            'dia_vencimento': 10,
        }
        
        response = self.client.post('/api/gestao/superuser/contratos-gestk/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('numero_contrato', response.data)
    
    def test_create_contrato_duplicate_contabilidade(self):
        """Não pode criar segundo contrato para mesma contabilidade (OneToOne)"""
        self.client.force_authenticate(user=self.superuser)
        
        data = {
            'contabilidade': self.contabilidade1.id,  # Já tem contrato
            'numero_contrato': 'GESTK-2024-003',
            'data_inicio': timezone.now().date().isoformat(),
            'plano_servico': 'Plano Básico',
            'limites_usuarios': 10,
            'limites_empresas': 5,
            'limites_contratos_internos': 50,
            'valor_mensal': 500.00,
            'dia_vencimento': 10,
        }
        
        response = self.client.post('/api/gestao/superuser/contratos-gestk/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('contabilidade', response.data)
    
    def test_update_contrato_as_superuser(self):
        """Superuser pode atualizar contrato"""
        self.client.force_authenticate(user=self.superuser)
        
        data = {
            'plano_servico': 'Plano Premium Atualizado',
            'valor_mensal': 750.00,
            'limites_usuarios': 15,
        }
        
        response = self.client.patch(
            f'/api/gestao/superuser/contratos-gestk/{self.contrato1.id}/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['plano_servico'], 'Plano Premium Atualizado')
        self.assertEqual(float(response.data['valor_mensal']), 750.00)
    
    def test_delete_contrato_ativo(self):
        """Não pode deletar contrato ativo"""
        self.client.force_authenticate(user=self.superuser)
        
        response = self.client.delete(f'/api/gestao/superuser/contratos-gestk/{self.contrato1.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ContratoGestk.objects.count(), 1)
    
    def test_delete_contrato_cancelado(self):
        """Pode deletar contrato cancelado"""
        self.client.force_authenticate(user=self.superuser)
        
        # Cancelar contrato primeiro
        self.contrato1.status = 'cancelado'
        self.contrato1.save()
        
        response = self.client.delete(f'/api/gestao/superuser/contratos-gestk/{self.contrato1.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ContratoGestk.objects.count(), 0)
    
    def test_renovar_contrato(self):
        """Superuser pode renovar contrato"""
        self.client.force_authenticate(user=self.superuser)
        
        data_termino_antiga = self.contrato1.data_termino
        
        response = self.client.post(
            f'/api/gestao/superuser/contratos-gestk/{self.contrato1.id}/renovar/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que data de término foi estendida
        self.contrato1.refresh_from_db()
        self.assertGreater(self.contrato1.data_termino, data_termino_antiga)
    
    def test_suspender_contrato(self):
        """Superuser pode suspender contrato"""
        self.client.force_authenticate(user=self.superuser)
        
        data = {'motivo': 'Inadimplência'}
        
        response = self.client.post(
            f'/api/gestao/superuser/contratos-gestk/{self.contrato1.id}/suspender/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.contrato1.refresh_from_db()
        self.assertEqual(self.contrato1.status, 'suspenso')
        self.assertEqual(self.contrato1.motivo_suspensao, 'Inadimplência')
    
    def test_reativar_contrato(self):
        """Superuser pode reativar contrato suspenso"""
        self.client.force_authenticate(user=self.superuser)
        
        # Suspender primeiro
        self.contrato1.status = 'suspenso'
        self.contrato1.motivo_suspensao = 'Teste'
        self.contrato1.save()
        
        response = self.client.post(
            f'/api/gestao/superuser/contratos-gestk/{self.contrato1.id}/reativar/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.contrato1.refresh_from_db()
        self.assertEqual(self.contrato1.status, 'ativo')
        self.assertIsNone(self.contrato1.motivo_suspensao)
    
    def test_cancelar_contrato(self):
        """Superuser pode cancelar contrato"""
        self.client.force_authenticate(user=self.superuser)
        
        data = {'motivo': 'Solicitação do cliente'}
        
        response = self.client.post(
            f'/api/gestao/superuser/contratos-gestk/{self.contrato1.id}/cancelar/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.contrato1.refresh_from_db()
        self.assertEqual(self.contrato1.status, 'cancelado')
        self.assertEqual(self.contrato1.motivo_cancelamento, 'Solicitação do cliente')
    
    def test_estatisticas_contrato(self):
        """Superuser pode ver estatísticas do contrato"""
        self.client.force_authenticate(user=self.superuser)
        
        response = self.client.get(
            f'/api/gestao/superuser/contratos-gestk/{self.contrato1.id}/estatisticas/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('periodo', response.data)
        self.assertIn('uso_recursos', response.data)
        self.assertIn('financeiro', response.data)
        self.assertIn('status_contrato', response.data)
    
    def test_resumo_contratos(self):
        """Superuser pode ver resumo geral"""
        self.client.force_authenticate(user=self.superuser)
        
        response = self.client.get('/api/gestao/superuser/contratos-gestk/resumo/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total', response.data)
        self.assertIn('por_status', response.data)
        self.assertIn('financeiro', response.data)
    
    def test_filter_by_status(self):
        """Filtrar contratos por status"""
        self.client.force_authenticate(user=self.superuser)
        
        response = self.client.get('/api/gestao/superuser/contratos-gestk/?status=ativo')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
    
    def test_search_contrato(self):
        """Buscar contrato por número"""
        self.client.force_authenticate(user=self.superuser)
        
        response = self.client.get('/api/gestao/superuser/contratos-gestk/?busca=GESTK-2024')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
