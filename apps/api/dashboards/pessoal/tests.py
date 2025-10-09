from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from apps.core.models import Contabilidade
from apps.funcionarios.models import Funcionario, VinculoEmpregaticio, Departamento, Cargo, Rubrica
from apps.pessoas.models import PessoaFisica, PessoaJuridica

User = get_user_model()


class PessoalViewSetTestCase(APITestCase):
    def setUp(self):
        """Configurar dados de teste"""
        # Criar contabilidade
        self.contabilidade = Contabilidade.objects.create(
            razao_social="Teste Contabilidade",
            cnpj="12345678000199"
        )
        
        # Criar usuário
        self.user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="testpass123",
            contabilidade=self.contabilidade
        )
        
        # Criar pessoa física
        self.pessoa_fisica = PessoaFisica.objects.create(
            cpf="12345678901",
            nome_completo="João Silva"
        )
        
        # Criar funcionário
        self.funcionario = Funcionario.objects.create(
            contabilidade=self.contabilidade,
            pessoa_fisica=self.pessoa_fisica
        )
        
        # Criar departamento
        self.departamento = Departamento.objects.create(
            contabilidade=self.contabilidade,
            nome="Departamento Teste"
        )
        
        # Criar cargo
        self.cargo = Cargo.objects.create(
            contabilidade=self.contabilidade,
            nome="Cargo Teste"
        )
        
        # Criar vínculo empregatício
        self.vinculo = VinculoEmpregaticio.objects.create(
            contabilidade=self.contabilidade,
            funcionario=self.funcionario,
            matricula="001",
            cargo=self.cargo,
            departamento=self.departamento,
            data_admissao="2024-01-01",
            salario_base=5000.00
        )
        
        # Criar rubrica de benefício
        self.rubrica = Rubrica.objects.create(
            contabilidade=self.contabilidade,
            nome="Vale Refeição",
            tipo="P"  # Provento
        )
        
        # Autenticar usuário
        self.client.force_authenticate(user=self.user)

    def test_folha_pagamento_endpoint(self):
        """Testar endpoint de folha de pagamento"""
        url = reverse('pessoal-folha-pagamento')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('resumo', response.data)
        self.assertIn('distribuicao_salarial', response.data)

    def test_beneficios_endpoint(self):
        """Testar endpoint de benefícios"""
        url = reverse('pessoal-beneficios')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_custos_trabalhistas_endpoint(self):
        """Testar endpoint de custos trabalhistas"""
        url = reverse('pessoal-custos-trabalhistas')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('salarios_base', response.data)
        self.assertIn('encargos', response.data)
        self.assertIn('custo_total', response.data)

    def test_evolucao_folha_endpoint(self):
        """Testar endpoint de evolução da folha"""
        url = reverse('pessoal-evolucao-folha')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_unauthorized_access(self):
        """Testar acesso não autorizado"""
        self.client.logout()
        
        url = reverse('pessoal-folha-pagamento')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_without_contabilidade(self):
        """Testar usuário sem contabilidade"""
        # Criar usuário sem contabilidade
        user_sem_contabilidade = User.objects.create_user(
            username="user_sem_cont",
            email="sem@test.com",
            password="testpass123"
        )
        
        self.client.force_authenticate(user=user_sem_contabilidade)
        
        url = reverse('pessoal-folha-pagamento')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Usuário não associado a uma contabilidade', response.data['error'])
