from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.models import Contabilidade
from apps.cadastros_gerais.models import CNAE
from apps.pessoas.models import Contrato, PessoaJuridica, PessoaFisica
from apps.contabil.models import PlanoContas
from django.contrib.contenttypes.models import ContentType
import random
from datetime import date, datetime, timedelta

class Command(BaseCommand):
    help = 'Simula a execução das ETLs 01-04 criando dados de teste'

    def add_arguments(self, parser):
        parser.add_argument(
            '--etl',
            type=str,
            help='Executar ETL específica (01, 02, 03, 04)',
        )

    def handle(self, *args, **options):
        etl_especifica = options.get('etl')
        
        if etl_especifica == '01' or not etl_especifica:
            self.etl_01_contabilidades()
        
        if etl_especifica == '02' or not etl_especifica:
            self.etl_02_cnaes()
        
        if etl_especifica == '03' or not etl_especifica:
            self.etl_03_contratos()
        
        if etl_especifica == '04' or not etl_especifica:
            self.etl_04_quadro_societario()

    def etl_01_contabilidades(self):
        """ETL 01 - Contabilidades"""
        self.stdout.write(self.style.SUCCESS('=== ETL 01 - CONTABILIDADES ==='))
        
        with transaction.atomic():
            contabilidades_data = [
                {
                    'id_legado': '1',
                    'razao_social': 'Contabilidade Matriz LTDA',
                    'nome_fantasia': 'ContaMatriz',
                    'cnpj': '12345678000195'
                },
                {
                    'id_legado': '2',
                    'razao_social': 'Escritório Central Contábil S/A',
                    'nome_fantasia': 'CentralCont',
                    'cnpj': '98765432000123'
                },
                {
                    'id_legado': '3',
                    'razao_social': 'Soluções Contábeis Integradas LTDA',
                    'nome_fantasia': 'SoluCont',
                    'cnpj': '11223344000156'
                }
            ]

            for contab_data in contabilidades_data:
                contabilidade, created = Contabilidade.objects.get_or_create(
                    id_legado=contab_data['id_legado'],
                    defaults=contab_data
                )
                if created:
                    self.stdout.write(f'  + Contabilidade criada: {contabilidade.razao_social}')
                else:
                    self.stdout.write(f'  ~ Contabilidade já existe: {contabilidade.razao_social}')

        self.stdout.write(self.style.SUCCESS('ETL 01 concluída!'))

    def etl_02_cnaes(self):
        """ETL 02 - CNAEs"""
        self.stdout.write(self.style.SUCCESS('=== ETL 02 - CNAES ==='))
        
        with transaction.atomic():
            cnaes_data = [
                {'codigo': '6201500', 'descricao': 'Desenvolvimento de programas de computador sob encomenda'},
                {'codigo': '6202300', 'descricao': 'Desenvolvimento e licenciamento de programas de computador customizáveis'},
                {'codigo': '6203100', 'descricao': 'Desenvolvimento e licenciamento de programas de computador não customizáveis'},
                {'codigo': '6204000', 'descricao': 'Consultoria em tecnologia da informação'},
                {'codigo': '6209100', 'descricao': 'Suporte técnico, manutenção e outros serviços em tecnologia da informação'},
                {'codigo': '4711301', 'descricao': 'Comércio varejista de mercadorias em geral, com predominância de produtos alimentícios - hipermercados'},
                {'codigo': '4711302', 'descricao': 'Comércio varejista de mercadorias em geral, com predominância de produtos alimentícios - supermercados'},
                {'codigo': '4712100', 'descricao': 'Comércio varejista de mercadorias em geral, com predominância de produtos alimentícios - minimercados, mercearias e armazéns'},
                {'codigo': '4721101', 'descricao': 'Comércio varejista de produtos farmacêuticos, sem manipulação de fórmulas'},
                {'codigo': '4721102', 'descricao': 'Comércio varejista de produtos farmacêuticos, com manipulação de fórmulas'},
            ]

            for cnae_data in cnaes_data:
                cnae, created = CNAE.objects.get_or_create(
                    codigo=cnae_data['codigo'],
                    defaults=cnae_data
                )
                if created:
                    self.stdout.write(f'  + CNAE criado: {cnae.codigo} - {cnae.descricao}')

        self.stdout.write(self.style.SUCCESS('ETL 02 concluída!'))

    def etl_03_contratos(self):
        """ETL 03 - Contratos"""
        self.stdout.write(self.style.SUCCESS('=== ETL 03 - CONTRATOS ==='))
        
        contabilidades = list(Contabilidade.objects.all())
        cnaes = list(CNAE.objects.all())
        
        if not contabilidades:
            self.stdout.write(self.style.WARNING('Nenhuma contabilidade encontrada. Execute primeiro a ETL 01.'))
            return

        with transaction.atomic():
            # Criar Pessoa Jurídica (empresa matriz)
            pj_matriz, created = PessoaJuridica.objects.get_or_create(
                cnpj='11111111000111',
                defaults={
                    'razao_social': 'Empresa Matriz LTDA',
                    'nome_fantasia': 'MatrizCorp',
                    'cnae_principal': random.choice(cnaes) if cnaes else None,
                    'regime_fiscal': 'simples',
                    'ramo_atividade': 'servicos'
                }
            )
            if created:
                self.stdout.write(f'  + Pessoa Jurídica criada: {pj_matriz}')

            # Criar Pessoa Física (sócio)
            pf_socio, created = PessoaFisica.objects.get_or_create(
                cpf='12345678901',
                defaults={
                    'nome_completo': 'João Silva Santos',
                    'email': 'joao.silva@email.com'
                }
            )
            if created:
                self.stdout.write(f'  + Pessoa Física criada: {pf_socio}')

            # Contrato para Pessoa Jurídica
            contrato_pj = Contrato.objects.create(
                contabilidade=contabilidades[0],
                content_type=ContentType.objects.get_for_model(PessoaJuridica),
                object_id=pj_matriz.id,
                data_inicio=date(2024, 1, 1),
                data_termino=date(2024, 12, 31),
                valor_honorario=500.00,
                plano_servico='contabil_basico',
                modulos_contratados=['contabil', 'fiscal'],
                limites_usuarios=3,
                limites_empresas=1,
                status_cobranca='ativo'
            )
            self.stdout.write(f'  + Contrato PJ criado: {pj_matriz} - {contabilidades[0]}')
            
            # Contrato para Pessoa Física
            contrato_pf = Contrato.objects.create(
                contabilidade=contabilidades[0],
                content_type=ContentType.objects.get_for_model(PessoaFisica),
                object_id=pf_socio.id,
                data_inicio=date(2024, 1, 1),
                data_termino=date(2024, 12, 31),
                valor_honorario=200.00,
                plano_servico='pessoal_basico',
                modulos_contratados=['pessoal'],
                limites_usuarios=1,
                limites_empresas=0,
                status_cobranca='ativo'
            )
            self.stdout.write(f'  + Contrato PF criado: {pf_socio} - {contabilidades[0]}')

        self.stdout.write(self.style.SUCCESS('ETL 03 concluída!'))

    def etl_04_quadro_societario(self):
        """ETL 04 - Quadro Societário"""
        self.stdout.write(self.style.SUCCESS('=== ETL 04 - QUADRO SOCIETÁRIO ==='))
        
        # Esta ETL seria responsável por criar o quadro societário das empresas
        # Por enquanto, vamos apenas simular a criação de dados relacionados
        
        with transaction.atomic():
            # Criar mais pessoas físicas para simular sócios
            socios_data = [
                {
                    'nome_completo': 'Maria Oliveira Costa',
                    'cpf': '98765432100',
                    'email': 'maria.oliveira@email.com'
                },
                {
                    'nome_completo': 'Pedro Santos Lima',
                    'cpf': '11122233344',
                    'email': 'pedro.santos@email.com'
                },
                {
                    'nome_completo': 'Ana Paula Ferreira',
                    'cpf': '55566677788',
                    'email': 'ana.ferreira@email.com'
                }
            ]

            for socio_data in socios_data:
                socio, created = PessoaFisica.objects.get_or_create(
                    cpf=socio_data['cpf'],
                    defaults=socio_data
                )
                if created:
                    self.stdout.write(f'  + Sócio criado: {socio.nome_completo}')

        self.stdout.write(self.style.SUCCESS('ETL 04 concluída!'))
