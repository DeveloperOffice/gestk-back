from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from apps.core.models import Contabilidade, Usuario
from apps.pessoas.models import PessoaJuridica, Contrato
from apps.funcionarios.models import Funcionario, VinculoEmpregaticio, Departamento, Cargo
from apps.pessoas.models import PessoaFisica
from apps.fiscal.models import NotaFiscal
from apps.contabil.models import LancamentoContabil

User = get_user_model()


class EscritorioViewSetTestCase(APITestCase):
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
        
        # Criar empresa
        self.empresa = PessoaJuridica.objects.create(
            cnpj="98765432000188",
            razao_social="Empresa Teste"
        )
        
        # Criar contrato
        self.contrato = Contrato.objects.create(
            contabilidade=self.contabilidade,
            content_type=self.empresa._meta.get_content_type(),
            object_id=self.empresa.id,
            data_inicio="2024-01-01",
            valor_honorario=1000.00
        )
        
        # Autenticar usuário
        self.client.force_authenticate(user=self.user)

    def test_visao_geral_endpoint(self):
        """Testar endpoint de visão geral do escritório"""
        url = reverse('escritorio-visao-geral')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('resumo', response.data)
        self.assertIn('faturamento', response.data)
        self.assertIn('indicadores', response.data)

    def test_performance_endpoint(self):
        """Testar endpoint de performance do escritório"""
        url = reverse('escritorio-performance')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('evolucao_faturamento', response.data)
        self.assertIn('produtividade_usuarios', response.data)
        self.assertIn('top_empresas', response.data)

    def test_capacidade_endpoint(self):
        """Testar endpoint de capacidade do escritório"""
        url = reverse('escritorio-capacidade')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('capacidade_atual', response.data)
        self.assertIn('limites', response.data)
        self.assertIn('utilizacao', response.data)
        self.assertIn('distribuicao_empresas', response.data)
        self.assertIn('crescimento', response.data)

    def test_tendencias_endpoint(self):
        """Testar endpoint de tendências do escritório"""
        url = reverse('escritorio-tendencias')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('historico', response.data)
        self.assertIn('projecoes', response.data)
        self.assertIn('alertas', response.data)
        self.assertIn('recomendacoes', response.data)

    def test_unauthorized_access(self):
        """Testar acesso não autorizado"""
        self.client.logout()
        
        url = reverse('escritorio-visao-geral')
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
        
        url = reverse('escritorio-visao-geral')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Usuário não associado a uma contabilidade', response.data['error'])
