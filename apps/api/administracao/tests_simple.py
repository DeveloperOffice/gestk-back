"""
Testes simplificados para API de Administração
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from apps.core.models import Contabilidade, UsuarioAcesso
from apps.administracao.models import ContratoGestk
import json

User = get_user_model()


class ContratoGestkModelTestCase(TestCase):
    """
    Testes para modelo ContratoGestk
    """
    
    def setUp(self):
        """
        Configuração inicial para os testes
        """
        # Criar contabilidade
        self.contabilidade = Contabilidade.objects.create(
            razao_social='Contabilidade Teste LTDA',
            nome_fantasia='Contabilidade Teste',
            cnpj='12345678000195',
            ativo=True
        )
    
    def test_criar_contrato_gestk(self):
        """
        Testa criação de contrato GESTK
        """
        contrato = ContratoGestk.objects.create(
            contabilidade=self.contabilidade,
            numero_contrato='GESTK-2024-001',
            data_inicio='2024-01-01',
            plano_servico='basic',
            modulos_inclusos=['contabil', 'fiscal'],
            limites_usuarios=5,
            limites_empresas=10,
            valor_mensal=299.90,
            status='ativo'
        )
        
        self.assertEqual(contrato.numero_contrato, 'GESTK-2024-001')
        self.assertEqual(contrato.contabilidade, self.contabilidade)
        self.assertEqual(contrato.status, 'ativo')
    
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
        
        contrato.suspender('Inadimplência')
        
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
        
        contrato.cancelar('Solicitação do cliente')
        
        self.assertEqual(contrato.status, 'cancelado')
        self.assertEqual(contrato.motivo_cancelamento, 'Solicitação do cliente')
    
    def test_ativar_contrato_gestk(self):
        """
        Testa ativação de contrato GESTK
        """
        contrato = ContratoGestk.objects.create(
            contabilidade=self.contabilidade,
            numero_contrato='GESTK-2024-001',
            data_inicio='2024-01-01',
            plano_servico='basic',
            valor_mensal=299.90,
            status='suspenso',
            motivo_suspensao='Teste'
        )
        
        contrato.ativar()
        
        self.assertEqual(contrato.status, 'ativo')
        self.assertIsNone(contrato.motivo_suspensao)


class UsuarioAcessoModelTestCase(TestCase):
    """
    Testes para modelo UsuarioAcesso
    """
    
    def setUp(self):
        """
        Configuração inicial para os testes
        """
        # Criar usuário
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
    
    def test_criar_acesso_usuario(self):
        """
        Testa criação de acesso de usuário
        """
        acesso = UsuarioAcesso.objects.create(
            usuario=self.user,
            contabilidade=self.contabilidade,
            role='operacional',
            modulos_acesso=['contabil', 'fiscal'],
            data_inicio='2024-01-01',
            ativo=True
        )
        
        self.assertEqual(acesso.usuario, self.user)
        self.assertEqual(acesso.contabilidade, self.contabilidade)
        self.assertEqual(acesso.role, 'operacional')
        self.assertTrue(acesso.ativo)
    
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
        
        acesso.desativar()
        
        self.assertFalse(acesso.ativo)
    
    def test_ativar_acesso_usuario(self):
        """
        Testa ativação de acesso de usuário
        """
        acesso = UsuarioAcesso.objects.create(
            usuario=self.user,
            contabilidade=self.contabilidade,
            role='operacional',
            data_inicio='2024-01-01',
            ativo=False
        )
        
        acesso.ativar()
        
        self.assertTrue(acesso.ativo)


class BillingModelTestCase(TestCase):
    """
    Testes para modelos de Billing
    """
    
    def setUp(self):
        """
        Configuração inicial para os testes
        """
        from apps.billing.models import Plano, Assinatura, Fatura, Pagamento
        
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
    
    def test_criar_plano(self):
        """
        Testa criação de plano
        """
        from apps.billing.models import Plano
        
        plano = Plano.objects.create(
            codigo='pro',
            nome='Plano Pro',
            preco_mensal=599.90,
            ativo=True
        )
        
        self.assertEqual(plano.codigo, 'pro')
        self.assertEqual(plano.nome, 'Plano Pro')
        self.assertEqual(plano.preco_mensal, 599.90)
    
    def test_criar_assinatura(self):
        """
        Testa criação de assinatura
        """
        from apps.billing.models import Assinatura
        
        assinatura = Assinatura.objects.create(
            contabilidade=self.contabilidade,
            plano=self.plano,
            data_inicio='2024-01-01',
            valor_mensal=299.90,
            status='ativa'
        )
        
        self.assertEqual(assinatura.contabilidade, self.contabilidade)
        self.assertEqual(assinatura.plano, self.plano)
        self.assertEqual(assinatura.status, 'ativa')
    
    def test_criar_fatura(self):
        """
        Testa criação de fatura
        """
        from apps.billing.models import Assinatura, Fatura
        
        assinatura = Assinatura.objects.create(
            contabilidade=self.contabilidade,
            plano=self.plano,
            data_inicio='2024-01-01',
            valor_mensal=299.90,
            status='ativa'
        )
        
        fatura = Fatura.objects.create(
            assinatura=assinatura,
            numero_fatura='FAT-2024-001',
            competencia='2024-01',
            valor_original=299.90,
            valor_final=299.90,
            data_emissao='2024-01-01',
            data_vencimento='2024-01-10',
            status='aberta'
        )
        
        self.assertEqual(fatura.numero_fatura, 'FAT-2024-001')
        self.assertEqual(fatura.assinatura, assinatura)
        self.assertEqual(fatura.status, 'aberta')
    
    def test_criar_pagamento(self):
        """
        Testa criação de pagamento
        """
        from apps.billing.models import Assinatura, Fatura, Pagamento
        
        assinatura = Assinatura.objects.create(
            contabilidade=self.contabilidade,
            plano=self.plano,
            data_inicio='2024-01-01',
            valor_mensal=299.90,
            status='ativa'
        )
        
        fatura = Fatura.objects.create(
            assinatura=assinatura,
            numero_fatura='FAT-2024-001',
            competencia='2024-01',
            valor_original=299.90,
            valor_final=299.90,
            data_emissao='2024-01-01',
            data_vencimento='2024-01-10',
            status='aberta'
        )
        
        pagamento = Pagamento.objects.create(
            fatura=fatura,
            valor=299.90,
            metodo='pix',
            status='pendente'
        )
        
        self.assertEqual(pagamento.fatura, fatura)
        self.assertEqual(pagamento.valor, 299.90)
        self.assertEqual(pagamento.metodo, 'pix')
