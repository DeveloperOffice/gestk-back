from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from apps.core.models import Contabilidade
from apps.funcionarios.models import Funcionario, VinculoEmpregaticio, Departamento, Cargo
from apps.pessoas.models import PessoaFisica, PessoaJuridica

User = get_user_model()


class OrganizacionalViewSetTestCase(APITestCase):
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
        
        # Autenticar usuário
        self.client.force_authenticate(user=self.user)

    def test_estrutura_endpoint(self):
        """Testar endpoint de estrutura organizacional"""
        url = reverse('organizacional-estrutura')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_departamentos', response.data)
        self.assertIn('total_cargos', response.data)
        self.assertIn('departamentos', response.data)
        self.assertIn('cargos', response.data)

    def test_distribuicao_departamentos_endpoint(self):
        """Testar endpoint de distribuição por departamento"""
        url = reverse('organizacional-distribuicao-departamentos')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_hierarquia_endpoint(self):
        """Testar endpoint de hierarquia organizacional"""
        url = reverse('organizacional-hierarquia')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_custo_departamento_endpoint(self):
        """Testar endpoint de custo por departamento"""
        url = reverse('organizacional-custo-departamento')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_unauthorized_access(self):
        """Testar acesso não autorizado"""
        self.client.logout()
        
        url = reverse('organizacional-estrutura')
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
        
        url = reverse('organizacional-estrutura')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Usuário não associado a uma contabilidade', response.data['error'])
