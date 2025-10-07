"""
Testes para API de Billing
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from apps.core.models import Contabilidade
from apps.billing.models import Plano, Assinatura, Fatura, Pagamento
import json

User = get_user_model()


class PlanoAPITestCase(APITestCase):
    """
    Testes para API de Planos
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
        
        # Token de autenticação
        refresh = RefreshToken.for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        self.client.force_authenticate(user=self.admin_user)
    
    def test_criar_plano(self):
        """
        Testa criação de plano
        """
        url = reverse('plano-list')
        data = {
            'codigo': 'basic',
            'nome': 'Plano Básico',
            'descricao': 'Plano básico para pequenas contabilidades',
            'preco_mensal': 299.90,
            'preco_anual': 2999.00,
            'desconto_anual': 10.0,
            'modulos_inclusos': ['contabil', 'fiscal'],
            'limites': {
                'usuarios': 5,
                'empresas': 10,
                'contratos': 100
            },
            'ativo': True,
            'ordem_exibicao': 1
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Plano.objects.count(), 1)
        
        plano = Plano.objects.first()
        self.assertEqual(plano.codigo, 'basic')
        self.assertEqual(plano.nome, 'Plano Básico')
    
    def test_listar_planos(self):
        """
        Testa listagem de planos
        """
        # Criar plano
        Plano.objects.create(
            codigo='basic',
            nome='Plano Básico',
            preco_mensal=299.90,
            ativo=True
        )
        
        url = reverse('plano-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_resumo_planos(self):
        """
        Testa endpoint de resumo de planos
        """
        # Criar planos
        Plano.objects.create(
            codigo='basic',
            nome='Plano Básico',
            preco_mensal=299.90,
            ativo=True
        )
        Plano.objects.create(
            codigo='pro',
            nome='Plano Pro',
            preco_mensal=599.90,
            ativo=False
        )
        
        url = reverse('plano-resumo')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 2)
        self.assertEqual(response.data['ativos'], 1)
        self.assertEqual(response.data['inativos'], 1)


class AssinaturaAPITestCase(APITestCase):
    """
    Testes para API de Assinaturas
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
        
        # Criar plano
        self.plano = Plano.objects.create(
            codigo='basic',
            nome='Plano Básico',
            preco_mensal=299.90,
            ativo=True
        )
        
        # Token de autenticação
        refresh = RefreshToken.for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        self.client.force_authenticate(user=self.admin_user)
    
    def test_criar_assinatura(self):
        """
        Testa criação de assinatura
        """
        url = reverse('assinatura-criar-assinatura')
        data = {
            'contabilidade': str(self.contabilidade.id),
            'plano': str(self.plano.id),
            'data_inicio': '2024-01-01',
            'ciclo_cobranca': 'mensal',
            'valor_mensal': 299.90,
            'dia_vencimento': 10,
            'status': 'ativa'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Assinatura.objects.count(), 1)
        
        assinatura = Assinatura.objects.first()
        self.assertEqual(assinatura.contabilidade, self.contabilidade)
        self.assertEqual(assinatura.plano, self.plano)
    
    def test_suspender_assinatura(self):
        """
        Testa suspensão de assinatura
        """
        assinatura = Assinatura.objects.create(
            contabilidade=self.contabilidade,
            plano=self.plano,
            data_inicio='2024-01-01',
            valor_mensal=299.90,
            status='ativa'
        )
        
        url = reverse('assinatura-suspender', kwargs={'pk': assinatura.id})
        data = {'motivo': 'Inadimplência'}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        assinatura.refresh_from_db()
        self.assertEqual(assinatura.status, 'suspensa')
        self.assertEqual(assinatura.motivo_suspensao, 'Inadimplência')
    
    def test_cancelar_assinatura(self):
        """
        Testa cancelamento de assinatura
        """
        assinatura = Assinatura.objects.create(
            contabilidade=self.contabilidade,
            plano=self.plano,
            data_inicio='2024-01-01',
            valor_mensal=299.90,
            status='ativa'
        )
        
        url = reverse('assinatura-cancelar', kwargs={'pk': assinatura.id})
        data = {'motivo': 'Solicitação do cliente'}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        assinatura.refresh_from_db()
        self.assertEqual(assinatura.status, 'cancelada')
        self.assertEqual(assinatura.motivo_cancelamento, 'Solicitação do cliente')


class FaturaAPITestCase(APITestCase):
    """
    Testes para API de Faturas
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
        
        # Criar plano
        self.plano = Plano.objects.create(
            codigo='basic',
            nome='Plano Básico',
            preco_mensal=299.90,
            ativo=True
        )
        
        # Criar assinatura
        self.assinatura = Assinatura.objects.create(
            contabilidade=self.contabilidade,
            plano=self.plano,
            data_inicio='2024-01-01',
            valor_mensal=299.90,
            status='ativa'
        )
        
        # Token de autenticação
        refresh = RefreshToken.for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        self.client.force_authenticate(user=self.admin_user)
    
    def test_criar_fatura(self):
        """
        Testa criação de fatura
        """
        url = reverse('fatura-list')
        data = {
            'assinatura': str(self.assinatura.id),
            'numero_fatura': 'FAT-2024-001',
            'competencia': '2024-01',
            'valor_original': 299.90,
            'valor_final': 299.90,
            'data_emissao': '2024-01-01',
            'data_vencimento': '2024-01-10',
            'status': 'aberta'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Fatura.objects.count(), 1)
        
        fatura = Fatura.objects.first()
        self.assertEqual(fatura.numero_fatura, 'FAT-2024-001')
        self.assertEqual(fatura.assinatura, self.assinatura)
    
    def test_marcar_fatura_como_paga(self):
        """
        Testa marcação de fatura como paga
        """
        fatura = Fatura.objects.create(
            assinatura=self.assinatura,
            numero_fatura='FAT-2024-001',
            competencia='2024-01',
            valor_original=299.90,
            valor_final=299.90,
            data_emissao='2024-01-01',
            data_vencimento='2024-01-10',
            status='aberta'
        )
        
        url = reverse('fatura-marcar-como-paga', kwargs={'pk': fatura.id})
        data = {'data_pagamento': '2024-01-05'}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        fatura.refresh_from_db()
        self.assertEqual(fatura.status, 'paga')
        self.assertEqual(fatura.data_pagamento.strftime('%Y-%m-%d'), '2024-01-05')
    
    def test_cancelar_fatura(self):
        """
        Testa cancelamento de fatura
        """
        fatura = Fatura.objects.create(
            assinatura=self.assinatura,
            numero_fatura='FAT-2024-001',
            competencia='2024-01',
            valor_original=299.90,
            valor_final=299.90,
            data_emissao='2024-01-01',
            data_vencimento='2024-01-10',
            status='aberta'
        )
        
        url = reverse('fatura-cancelar', kwargs={'pk': fatura.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        fatura.refresh_from_db()
        self.assertEqual(fatura.status, 'cancelada')


class PagamentoAPITestCase(APITestCase):
    """
    Testes para API de Pagamentos
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
        
        # Criar plano
        self.plano = Plano.objects.create(
            codigo='basic',
            nome='Plano Básico',
            preco_mensal=299.90,
            ativo=True
        )
        
        # Criar assinatura
        self.assinatura = Assinatura.objects.create(
            contabilidade=self.contabilidade,
            plano=self.plano,
            data_inicio='2024-01-01',
            valor_mensal=299.90,
            status='ativa'
        )
        
        # Criar fatura
        self.fatura = Fatura.objects.create(
            assinatura=self.assinatura,
            numero_fatura='FAT-2024-001',
            competencia='2024-01',
            valor_original=299.90,
            valor_final=299.90,
            data_emissao='2024-01-01',
            data_vencimento='2024-01-10',
            status='aberta'
        )
        
        # Token de autenticação
        refresh = RefreshToken.for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        self.client.force_authenticate(user=self.admin_user)
    
    def test_criar_pagamento(self):
        """
        Testa criação de pagamento
        """
        url = reverse('pagamento-list')
        data = {
            'fatura': str(self.fatura.id),
            'valor': 299.90,
            'metodo': 'pix',
            'transacao_id': 'TXN-123456',
            'referencia': 'REF-123456',
            'status': 'pendente'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Pagamento.objects.count(), 1)
        
        pagamento = Pagamento.objects.first()
        self.assertEqual(pagamento.fatura, self.fatura)
        self.assertEqual(pagamento.valor, 299.90)
    
    def test_confirmar_pagamento(self):
        """
        Testa confirmação de pagamento
        """
        pagamento = Pagamento.objects.create(
            fatura=self.fatura,
            valor=299.90,
            metodo='pix',
            status='pendente'
        )
        
        url = reverse('pagamento-confirmar', kwargs={'pk': pagamento.id})
        data = {'data_confirmacao': '2024-01-05 10:30:00'}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        pagamento.refresh_from_db()
        self.assertEqual(pagamento.status, 'confirmado')
        
        # Verificar se a fatura foi marcada como paga
        self.fatura.refresh_from_db()
        self.assertEqual(self.fatura.status, 'paga')
    
    def test_estornar_pagamento(self):
        """
        Testa estorno de pagamento
        """
        pagamento = Pagamento.objects.create(
            fatura=self.fatura,
            valor=299.90,
            metodo='pix',
            status='confirmado'
        )
        
        url = reverse('pagamento-estornar', kwargs={'pk': pagamento.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        pagamento.refresh_from_db()
        self.assertEqual(pagamento.status, 'estornado')
        
        # Verificar se a fatura voltou para aberta
        self.fatura.refresh_from_db()
        self.assertEqual(self.fatura.status, 'aberta')
