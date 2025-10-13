"""
Tests para ContabilidadeViewSet (SUPERUSER)
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.core.models import Usuario, Contabilidade


class ContabilidadeViewSetTest(TestCase):
    """
    Testes para ContabilidadeViewSet
    """
    
    def setUp(self):
        """Configurar dados de teste"""
        self.client = APIClient()
        
        # Criar contabilidade de teste
        self.contabilidade = Contabilidade.objects.create(
            cnpj='12345678000190',
            razao_social='Test Contabilidade',
            nome_fantasia='Test',
            email='test@contabilidade.com',
        )
        
        # Criar outra contabilidade
        self.contabilidade2 = Contabilidade.objects.create(
            cnpj='98765432000190',
            razao_social='Segunda Contabilidade',
            nome_fantasia='Segunda',
            email='segunda@contabilidade.com',
        )
        
        # Criar usuários
        self.superuser = Usuario.objects.create_user(
            username='superuser',
            password='testpass123',
            tipo_usuario='superuser',
            contabilidade=self.contabilidade,
            is_superuser=True
        )
        
        self.admin = Usuario.objects.create_user(
            username='admin',
            password='testpass123',
            tipo_usuario='admin',
            contabilidade=self.contabilidade
        )
        
        self.usuario = Usuario.objects.create_user(
            username='usuario',
            password='testpass123',
            tipo_usuario='operacional',
            contabilidade=self.contabilidade
        )
    
    def test_list_contabilidades_superuser(self):
        """SUPERUSER pode listar todas as contabilidades"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('contabilidades-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 2)
    
    def test_list_contabilidades_admin_forbidden(self):
        """ADMIN não pode listar contabilidades (endpoint SUPERUSER)"""
        self.client.force_authenticate(user=self.admin)
        url = reverse('contabilidades-list')
        response = self.client.get(url)
        
        # Deve retornar lista vazia ou 403
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN])
        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(len(response.data['results']), 0)
    
    def test_list_contabilidades_unauthorized(self):
        """Usuário não autenticado não pode listar"""
        url = reverse('contabilidades-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_contabilidade_superuser(self):
        """SUPERUSER pode criar contabilidade"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('contabilidades-list')
        data = {
            'razao_social': 'Nova Contabilidade Ltda',
            'nome_fantasia': 'Nova Contábil',
            'cnpj': '11111111000190',
            'email': 'nova@contabilidade.com',
            'telefone': '11999999999',
            'ativo': True,
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['razao_social'], data['razao_social'])
        self.assertEqual(response.data['cnpj'], data['cnpj'])
    
    def test_create_contabilidade_duplicate_cnpj(self):
        """Não pode criar contabilidade com CNPJ duplicado"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('contabilidades-list')
        data = {
            'razao_social': 'Duplicada',
            'cnpj': '12345678000190',  # CNPJ já existe
            'email': 'duplicada@contabilidade.com',
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cnpj', response.data)
    
    def test_retrieve_contabilidade_superuser(self):
        """SUPERUSER pode ver detalhes da contabilidade"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('contabilidades-detail', args=[self.contabilidade.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['razao_social'], self.contabilidade.razao_social)
    
    def test_update_contabilidade_superuser(self):
        """SUPERUSER pode atualizar contabilidade"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('contabilidades-detail', args=[self.contabilidade.id])
        data = {
            'razao_social': 'Nome Atualizado Ltda',
            'telefone': '11888888888',
        }
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['razao_social'], data['razao_social'])
        self.assertEqual(response.data['telefone'], data['telefone'])
    
    def test_delete_contabilidade_superuser(self):
        """SUPERUSER pode deletar contabilidade (soft delete)"""
        # Criar contabilidade sem dependências
        contabilidade_teste = Contabilidade.objects.create(
            cnpj='22222222000190',
            razao_social='Para Deletar',
            email='deletar@test.com',
        )
        
        self.client.force_authenticate(user=self.superuser)
        url = reverse('contabilidades-detail', args=[contabilidade_teste.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verificar soft delete
        contabilidade_teste.refresh_from_db()
        self.assertFalse(contabilidade_teste.ativo)
    
    def test_ativar_contabilidade(self):
        """Teste de ativação de contabilidade"""
        # Desativar primeiro
        self.contabilidade.ativo = False
        self.contabilidade.save()
        
        self.client.force_authenticate(user=self.superuser)
        url = reverse('contabilidades-ativar', args=[self.contabilidade.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar ativação
        self.contabilidade.refresh_from_db()
        self.assertTrue(self.contabilidade.ativo)
    
    def test_desativar_contabilidade(self):
        """Teste de desativação de contabilidade"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('contabilidades-desativar', args=[self.contabilidade2.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar desativação
        self.contabilidade2.refresh_from_db()
        self.assertFalse(self.contabilidade2.ativo)
    
    def test_suspender_contabilidade(self):
        """Teste de suspensão por inadimplência"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('contabilidades-suspender', args=[self.contabilidade.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar suspensão
        self.contabilidade.refresh_from_db()
        self.assertTrue(self.contabilidade.suspensa_por_inadimplencia)
    
    def test_liberar_contabilidade(self):
        """Teste de liberação de inadimplência"""
        # Suspender primeiro
        self.contabilidade.suspensa_por_inadimplencia = True
        self.contabilidade.save()
        
        self.client.force_authenticate(user=self.superuser)
        url = reverse('contabilidades-liberar', args=[self.contabilidade.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar liberação
        self.contabilidade.refresh_from_db()
        self.assertFalse(self.contabilidade.suspensa_por_inadimplencia)
    
    def test_estatisticas_contabilidade(self):
        """Teste de endpoint de estatísticas"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('contabilidades-estatisticas', args=[self.contabilidade.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('periodo', response.data)
        self.assertIn('usuarios', response.data)
        self.assertIn('contratos', response.data)
        self.assertIn('financeiro', response.data)
    
    def test_resumo_contabilidades(self):
        """Teste de resumo geral"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('contabilidades-resumo')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total', response.data)
        self.assertIn('ativas', response.data)
        self.assertIn('inativas', response.data)
        self.assertIn('suspensas_inadimplencia', response.data)
    
    def test_filtro_ativo(self):
        """Teste de filtro por status ativo"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('contabilidades-list')
        response = self.client.get(url, {'ativo': 'true'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Todas devem estar ativas
        for item in response.data['results']:
            self.assertTrue(item['ativo'])
    
    def test_busca_contabilidade(self):
        """Teste de busca por texto"""
        self.client.force_authenticate(user=self.superuser)
        url = reverse('contabilidades-list')
        response = self.client.get(url, {'busca': 'Test'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)
