"""
Testes para Assinaturas e Faturas ViewSet (SUPERUSER)
"""

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta
from decimal import Decimal

from apps.core.models import Contabilidade, Usuario
from apps.billing.models import Plano, Assinatura, Fatura


class AssinaturaViewSetTest(TestCase):
    """
    Suite de testes para AssinaturaViewSet
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
        
        # Criar contabilidade
        self.contabilidade = Contabilidade.objects.create(
            razao_social='Contábil Teste',
            nome_fantasia='Contábil',
            cnpj='12345678000190',
            ativo=True
        )
        
        self.admin_user.contabilidade = self.contabilidade
        self.admin_user.save()
        
        # Criar plano
        self.plano = Plano.objects.create(
            codigo='basic',
            nome='Plano Básico',
            preco_mensal=Decimal('500.00'),
            preco_anual=Decimal('5000.00'),
            desconto_anual=Decimal('16.67'),
            ativo=True
        )
        
        # Criar assinatura
        self.assinatura = Assinatura.objects.create(
            contabilidade=self.contabilidade,
            plano=self.plano,
            data_inicio=timezone.now().date(),
            data_fim=timezone.now().date() + timedelta(days=365),
            status='ativa',
            ciclo_cobranca='mensal',
            valor_mensal=Decimal('500.00'),
            dia_vencimento=10,
            created_by=self.superuser
        )
        
        # Cliente API
        self.client = APIClient()
    
    def test_list_assinaturas_as_superuser(self):
        """Superuser pode listar assinaturas"""
        self.client.force_authenticate(user=self.superuser)
        
        response = self.client.get('/api/billing/superuser/assinaturas/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
    
    def test_list_assinaturas_unauthenticated(self):
        """Usuário não autenticado não pode listar"""
        response = self.client.get('/api/billing/superuser/assinaturas/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_retrieve_assinatura_as_superuser(self):
        """Superuser pode detalhar assinatura"""
        self.client.force_authenticate(user=self.superuser)
        
        response = self.client.get(f'/api/billing/superuser/assinaturas/{self.assinatura.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('contabilidade_dados', response.data)
        self.assertIn('plano_dados', response.data)
    
    def test_create_assinatura_as_superuser(self):
        """Superuser pode criar assinatura"""
        self.client.force_authenticate(user=self.superuser)
        
        # Criar nova contabilidade
        contabilidade2 = Contabilidade.objects.create(
            razao_social='Contábil 2',
            nome_fantasia='Contábil 2',
            cnpj='98765432000190',
            ativo=True
        )
        
        data = {
            'contabilidade': contabilidade2.id,
            'plano': str(self.plano.id),
            'data_inicio': timezone.now().date().isoformat(),
            'ciclo_cobranca': 'mensal',
            'valor_mensal': 500.00,
            'dia_vencimento': 10,
        }
        
        response = self.client.post('/api/billing/superuser/assinaturas/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Assinatura.objects.count(), 2)
    
    def test_update_assinatura_as_superuser(self):
        """Superuser pode atualizar assinatura"""
        self.client.force_authenticate(user=self.superuser)
        
        data = {
            'valor_mensal': 750.00,
        }
        
        response = self.client.patch(
            f'/api/billing/superuser/assinaturas/{self.assinatura.id}/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assinatura.refresh_from_db()
        self.assertEqual(float(self.assinatura.valor_mensal), 750.00)
    
    def test_suspender_assinatura(self):
        """Superuser pode suspender assinatura"""
        self.client.force_authenticate(user=self.superuser)
        
        data = {'motivo': 'Inadimplência'}
        
        response = self.client.post(
            f'/api/billing/superuser/assinaturas/{self.assinatura.id}/suspender/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assinatura.refresh_from_db()
        self.assertEqual(self.assinatura.status, 'suspensa')
    
    def test_reativar_assinatura(self):
        """Superuser pode reativar assinatura"""
        self.client.force_authenticate(user=self.superuser)
        
        # Suspender primeiro
        self.assinatura.status = 'suspensa'
        self.assinatura.save()
        
        response = self.client.post(
            f'/api/billing/superuser/assinaturas/{self.assinatura.id}/reativar/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assinatura.refresh_from_db()
        self.assertEqual(self.assinatura.status, 'ativa')
    
    def test_cancelar_assinatura(self):
        """Superuser pode cancelar assinatura"""
        self.client.force_authenticate(user=self.superuser)
        
        data = {'motivo': 'Solicitação do cliente'}
        
        response = self.client.post(
            f'/api/billing/superuser/assinaturas/{self.assinatura.id}/cancelar/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assinatura.refresh_from_db()
        self.assertEqual(self.assinatura.status, 'cancelada')
    
    def test_gerar_fatura(self):
        """Superuser pode gerar fatura manualmente"""
        self.client.force_authenticate(user=self.superuser)
        
        data = {'competencia': '2025-11'}
        
        response = self.client.post(
            f'/api/billing/superuser/assinaturas/{self.assinatura.id}/gerar_fatura/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Fatura.objects.filter(competencia='2025-11').exists())
    
    def test_estatisticas_assinatura(self):
        """Superuser pode ver estatísticas da assinatura"""
        self.client.force_authenticate(user=self.superuser)
        
        response = self.client.get(
            f'/api/billing/superuser/assinaturas/{self.assinatura.id}/estatisticas/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('periodo', response.data)
        self.assertIn('financeiro', response.data)
        self.assertIn('status', response.data)
    
    def test_resumo_assinaturas(self):
        """Superuser pode ver resumo geral"""
        self.client.force_authenticate(user=self.superuser)
        
        response = self.client.get('/api/billing/superuser/assinaturas/resumo/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total', response.data)
        self.assertIn('por_status', response.data)
        self.assertIn('financeiro', response.data)


class FaturaViewSetTest(TestCase):
    """
    Suite de testes para FaturaViewSet
    """
    
    def setUp(self):
        """Configurar ambiente de testes"""
        # Criar usuários
        self.superuser = Usuario.objects.create_superuser(
            username='admin',
            email='admin@gestk.com',
            password='admin123'
        )
        
        # Criar contabilidade
        self.contabilidade = Contabilidade.objects.create(
            razao_social='Contábil Teste',
            nome_fantasia='Contábil',
            cnpj='12345678000190',
            ativo=True
        )
        
        # Criar plano
        self.plano = Plano.objects.create(
            codigo='basic',
            nome='Plano Básico',
            preco_mensal=Decimal('500.00'),
            ativo=True
        )
        
        # Criar assinatura
        self.assinatura = Assinatura.objects.create(
            contabilidade=self.contabilidade,
            plano=self.plano,
            data_inicio=timezone.now().date(),
            status='ativa',
            ciclo_cobranca='mensal',
            valor_mensal=Decimal('500.00'),
            dia_vencimento=10,
            created_by=self.superuser
        )
        
        # Criar fatura
        self.fatura = Fatura.objects.create(
            assinatura=self.assinatura,
            numero_fatura='FAT-202510-0001',
            competencia='2025-10',
            valor_original=Decimal('500.00'),
            desconto=Decimal('0.00'),
            valor_final=Decimal('500.00'),
            data_emissao=timezone.now().date(),
            data_vencimento=timezone.now().date() + timedelta(days=10),
            status='aberta'
        )
        
        # Cliente API
        self.client = APIClient()
    
    def test_list_faturas_as_superuser(self):
        """Superuser pode listar faturas"""
        self.client.force_authenticate(user=self.superuser)
        
        response = self.client.get('/api/billing/superuser/faturas/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
    
    def test_retrieve_fatura_as_superuser(self):
        """Superuser pode detalhar fatura"""
        self.client.force_authenticate(user=self.superuser)
        
        response = self.client.get(f'/api/billing/superuser/faturas/{self.fatura.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['numero_fatura'], 'FAT-202510-0001')
    
    def test_create_fatura_as_superuser(self):
        """Superuser pode criar fatura"""
        self.client.force_authenticate(user=self.superuser)
        
        data = {
            'assinatura': str(self.assinatura.id),
            'numero_fatura': 'FAT-202511-0001',
            'competencia': '2025-11',
            'valor_original': 500.00,
            'desconto': 0.00,
            'valor_final': 500.00,
            'data_emissao': timezone.now().date().isoformat(),
            'data_vencimento': (timezone.now().date() + timedelta(days=10)).isoformat(),
            'status': 'aberta',
        }
        
        response = self.client.post('/api/billing/superuser/faturas/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Fatura.objects.count(), 2)
    
    def test_marcar_como_paga(self):
        """Superuser pode marcar fatura como paga"""
        self.client.force_authenticate(user=self.superuser)
        
        response = self.client.post(
            f'/api/billing/superuser/faturas/{self.fatura.id}/marcar_como_paga/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.fatura.refresh_from_db()
        self.assertEqual(self.fatura.status, 'paga')
        self.assertIsNotNone(self.fatura.data_pagamento)
    
    def test_cancelar_fatura(self):
        """Superuser pode cancelar fatura"""
        self.client.force_authenticate(user=self.superuser)
        
        data = {'motivo': 'Cancelamento da assinatura'}
        
        response = self.client.post(
            f'/api/billing/superuser/faturas/{self.fatura.id}/cancelar/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.fatura.refresh_from_db()
        self.assertEqual(self.fatura.status, 'cancelada')
    
    def test_estornar_fatura(self):
        """Superuser pode estornar fatura paga"""
        self.client.force_authenticate(user=self.superuser)
        
        # Marcar como paga primeiro
        self.fatura.status = 'paga'
        self.fatura.data_pagamento = timezone.now().date()
        self.fatura.save()
        
        data = {'motivo': 'Pagamento indevido'}
        
        response = self.client.post(
            f'/api/billing/superuser/faturas/{self.fatura.id}/estornar/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.fatura.refresh_from_db()
        self.assertEqual(self.fatura.status, 'estornada')
    
    def test_reabrir_fatura(self):
        """Superuser pode reabrir fatura cancelada"""
        self.client.force_authenticate(user=self.superuser)
        
        # Cancelar primeiro
        self.fatura.status = 'cancelada'
        self.fatura.save()
        
        response = self.client.post(
            f'/api/billing/superuser/faturas/{self.fatura.id}/reabrir/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.fatura.refresh_from_db()
        self.assertIn(self.fatura.status, ['aberta', 'vencida'])
    
    def test_estatisticas_faturas(self):
        """Superuser pode ver estatísticas gerais"""
        self.client.force_authenticate(user=self.superuser)
        
        response = self.client.get('/api/billing/superuser/faturas/estatisticas/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total', response.data)
        self.assertIn('por_status', response.data)
        self.assertIn('valores', response.data)
    
    def test_filter_by_status(self):
        """Filtrar faturas por status"""
        self.client.force_authenticate(user=self.superuser)
        
        response = self.client.get('/api/billing/superuser/faturas/?status=aberta')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
