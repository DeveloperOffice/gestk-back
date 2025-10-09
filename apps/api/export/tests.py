from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from apps.core.models import Contabilidade
from apps.pessoas.models import PessoaJuridica, Contrato
from apps.funcionarios.models import Funcionario, VinculoEmpregaticio, Departamento, Cargo
from apps.pessoas.models import PessoaFisica
from apps.fiscal.models import NotaFiscal

User = get_user_model()


class ExportViewSetTestCase(APITestCase):
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

    def test_carteira_pdf_endpoint(self):
        """Testar endpoint de exportação de carteira para PDF"""
        url = reverse('export-carteira-pdf')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])

    def test_carteira_excel_endpoint(self):
        """Testar endpoint de exportação de carteira para Excel"""
        url = reverse('export-carteira-excel')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('attachment', response['Content-Disposition'])

    def test_clientes_pdf_endpoint(self):
        """Testar endpoint de exportação de clientes para PDF"""
        url = reverse('export-clientes-pdf')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])

    def test_clientes_excel_endpoint(self):
        """Testar endpoint de exportação de clientes para Excel"""
        url = reverse('export-clientes-excel')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('attachment', response['Content-Disposition'])

    def test_relatorio_geral_pdf_endpoint(self):
        """Testar endpoint de exportação de relatório geral para PDF"""
        url = reverse('export-relatorio-geral-pdf')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])

    def test_relatorio_geral_excel_endpoint(self):
        """Testar endpoint de exportação de relatório geral para Excel"""
        url = reverse('export-relatorio-geral-excel')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('attachment', response['Content-Disposition'])

    def test_unauthorized_access(self):
        """Testar acesso não autorizado"""
        self.client.logout()
        
        url = reverse('export-carteira-pdf')
        response = self.client.post(url)
        
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
        
        url = reverse('export-carteira-pdf')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('Usuário não associado a uma contabilidade', response.data['error'])
