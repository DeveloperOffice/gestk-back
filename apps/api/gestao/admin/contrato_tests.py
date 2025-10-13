"""
Testes para gerenciamento de Contratos (Clientes) por ADMIN
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.core.models import Usuario, Contabilidade
from apps.pessoas.models import Contrato, PessoaJuridica, PessoaFisica
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
import uuid


class ContratoViewSetTest(TestCase):
    """Testes para ContratoViewSet"""
    
    def setUp(self):
        """Configuração inicial dos testes"""
        self.client = APIClient()
        
        # Criar contabilidade
        self.contabilidade = Contabilidade.objects.create(
            razao_social='Contabilidade Teste LTDA',
            nome_fantasia='Contabilidade Teste',
            cnpj='12345678000190',
            ativo=True
        )
        
        # Criar usuário ADMIN
        self.admin_user = Usuario.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='admin123',
            contabilidade=self.contabilidade,
            tipo_usuario='admin',
            pode_administrar_usuarios=True,
            ativo=True,
            is_active=True
        )
        
        # Criar Pessoa Jurídica (cliente)
        self.pessoa_juridica = PessoaJuridica.objects.create(
            cnpj='11111111000111',
            razao_social='Empresa Teste LTDA',
            nome_fantasia='Empresa Teste',
            email='empresa@test.com',
            telefone='1111111111'
        )
        
        # Criar Pessoa Física (cliente)
        self.pessoa_fisica = PessoaFisica.objects.create(
            cpf='12345678901',
            nome_completo='João da Silva',
            email='joao@test.com',
            telefone='2222222222'
        )
        
        # Criar contrato PJ
        pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
        self.contrato_pj = Contrato.objects.create(
            contabilidade=self.contabilidade,
            content_type=pj_content_type,
            object_id=self.pessoa_juridica.id,
            data_inicio=timezone.now().date(),
            data_termino=timezone.now().date() + timedelta(days=365),
            dia_vencimento=10,
            valor_honorario=1000.00,
            plano_servico='BASICO',
            modulos_contratados=['fiscal', 'contabil'],
            limites_usuarios=5,
            limites_empresas=1,
            ativo=True,
            status_cobranca='ativo'
        )
        
        # Criar contrato PF
        pf_content_type = ContentType.objects.get_for_model(PessoaFisica)
        self.contrato_pf = Contrato.objects.create(
            contabilidade=self.contabilidade,
            content_type=pf_content_type,
            object_id=self.pessoa_fisica.id,
            data_inicio=timezone.now().date(),
            data_termino=timezone.now().date() + timedelta(days=180),
            dia_vencimento=15,
            valor_honorario=500.00,
            plano_servico='SIMPLES',
            modulos_contratados=['fiscal'],
            limites_usuarios=1,
            limites_empresas=1,
            ativo=True,
            status_cobranca='ativo'
        )
        
        # URLs
        self.list_url = reverse('admin-contratos-list')
        self.detail_url = lambda pk: reverse('admin-contratos-detail', kwargs={'pk': pk})
    
    def test_list_contratos_admin(self):
        """Testa listagem de contratos por ADMIN"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_retrieve_contrato(self):
        """Testa detalhamento de contrato"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get(self.detail_url(self.contrato_pj.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['valor_honorario'], '1000.00')
        self.assertIn('cliente_info', response.data)
        self.assertIn('estatisticas', response.data)
    
    def test_update_contrato(self):
        """Testa atualização de contrato"""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'valor_honorario': 1500.00,
            'plano_servico': 'PREMIUM'
        }
        
        response = self.client.patch(
            self.detail_url(self.contrato_pj.id),
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['valor_honorario'], '1500.00')
        self.assertEqual(response.data['plano_servico'], 'PREMIUM')
        
        # Verificar no banco
        self.contrato_pj.refresh_from_db()
        self.assertEqual(float(self.contrato_pj.valor_honorario), 1500.00)
    
    def test_delete_contrato(self):
        """Testa deleção de contrato (soft delete)"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.delete(self.detail_url(self.contrato_pj.id))
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verificar soft delete
        self.contrato_pj.refresh_from_db()
        self.assertFalse(self.contrato_pj.ativo)
        self.assertEqual(self.contrato_pj.status_cobranca, 'cancelado')
    
    def test_ativar_contrato(self):
        """Testa ativação de contrato"""
        self.contrato_pj.ativo = False
        self.contrato_pj.save()
        
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.post(
            reverse('admin-contratos-ativar', kwargs={'pk': self.contrato_pj.id})
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar no banco
        self.contrato_pj.refresh_from_db()
        self.assertTrue(self.contrato_pj.ativo)
        self.assertEqual(self.contrato_pj.status_cobranca, 'ativo')
    
    def test_desativar_contrato(self):
        """Testa desativação de contrato"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.post(
            reverse('admin-contratos-desativar', kwargs={'pk': self.contrato_pj.id})
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar no banco
        self.contrato_pj.refresh_from_db()
        self.assertFalse(self.contrato_pj.ativo)
        self.assertEqual(self.contrato_pj.status_cobranca, 'inativo')
    
    def test_suspender_contrato(self):
        """Testa suspensão de contrato"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.post(
            reverse('admin-contratos-suspender', kwargs={'pk': self.contrato_pj.id}),
            {'motivo': 'Inadimplência'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar no banco
        self.contrato_pj.refresh_from_db()
        self.assertFalse(self.contrato_pj.ativo)
        self.assertEqual(self.contrato_pj.status_cobranca, 'suspenso')
    
    def test_renovar_contrato(self):
        """Testa renovação de contrato"""
        self.client.force_authenticate(user=self.admin_user)
        
        nova_data = (timezone.now().date() + timedelta(days=730)).strftime('%Y-%m-%d')
        
        response = self.client.post(
            reverse('admin-contratos-renovar', kwargs={'pk': self.contrato_pj.id}),
            {'nova_data_termino': nova_data}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar no banco
        self.contrato_pj.refresh_from_db()
        self.assertEqual(self.contrato_pj.data_termino.strftime('%Y-%m-%d'), nova_data)
    
    def test_atualizar_modulos(self):
        """Testa atualização de módulos"""
        self.client.force_authenticate(user=self.admin_user)
        
        novos_modulos = ['fiscal', 'contabil', 'rh', 'dashboards']
        
        response = self.client.post(
            reverse('admin-contratos-atualizar-modulos', kwargs={'pk': self.contrato_pj.id}),
            {'modulos': novos_modulos},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar no banco
        self.contrato_pj.refresh_from_db()
        self.assertEqual(set(self.contrato_pj.modulos_contratados), set(novos_modulos))
    
    def test_atualizar_limites(self):
        """Testa atualização de limites"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.post(
            reverse('admin-contratos-atualizar-limites', kwargs={'pk': self.contrato_pj.id}),
            {'limite_usuarios': 10, 'limite_empresas': 3}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar no banco
        self.contrato_pj.refresh_from_db()
        self.assertEqual(self.contrato_pj.limites_usuarios, 10)
        self.assertEqual(self.contrato_pj.limites_empresas, 3)
    
    def test_estatisticas(self):
        """Testa endpoint de estatísticas"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get(reverse('admin-contratos-estatisticas'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total', response.data)
        self.assertIn('ativos', response.data)
        self.assertIn('inativos', response.data)
        self.assertIn('por_status', response.data)
        self.assertIn('valor_total_honorarios', response.data)
        self.assertIn('por_tipo_cliente', response.data)
        
        # Verificar valores
        self.assertEqual(response.data['total'], 2)
        self.assertEqual(response.data['ativos'], 2)
    
    def test_filtro_tipo_cliente(self):
        """Testa filtro por tipo de cliente"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get(self.list_url, {'tipo_cliente': 'PJ'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(
            response.data['results'][0]['cliente_info']['tipo'],
            'PJ'
        )
    
    def test_filtro_busca(self):
        """Testa filtro de busca"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get(self.list_url, {'busca': 'Empresa Teste'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
    
    def test_filtro_vencendo(self):
        """Testa filtro de contratos vencendo"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Alterar data de término para daqui 15 dias
        self.contrato_pj.data_termino = timezone.now().date() + timedelta(days=15)
        self.contrato_pj.save()
        
        response = self.client.get(self.list_url, {'vencendo': 'true'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
    
    def test_filtro_status_cobranca(self):
        """Testa filtro por status de cobrança"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get(self.list_url, {'status_cobranca': 'ativo'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Todos os resultados devem ser ativos
        for contrato in response.data['results']:
            self.assertEqual(contrato['status_cobranca'], 'ativo')
    
    def test_usuario_sem_permissao_nao_acessa(self):
        """Testa que usuário sem permissão não acessa"""
        # Criar usuário sem permissão de administrar
        usuario_sem_permissao = Usuario.objects.create_user(
            username='sem_permissao',
            email='sem@test.com',
            password='senha123',
            contabilidade=self.contabilidade,
            tipo_usuario='operacional',
            pode_administrar_usuarios=False
        )
        
        self.client.force_authenticate(user=usuario_sem_permissao)
        
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
