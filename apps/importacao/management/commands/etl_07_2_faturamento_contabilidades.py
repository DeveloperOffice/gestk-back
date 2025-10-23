#!/usr/bin/env python
"""
ETL 07.2 - Faturamento das Contabilidades
Importa dados de faturamento das próprias contabilidades do Sybase para o db_gestk (gestao_faturamento_empresas)
"""

import os
import django
from datetime import date
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from apps.core.models import Contabilidade
from apps.gestao_models.models import FaturamentoEmpresa
from apps.importacao.management.commands._base import BaseETLCommand

class Command(BaseETLCommand):
    def handle(self, *args, **options):
        """Executa a ETL de faturamento das contabilidades"""
        from re import sub
        self.stdout.write(self.style.SUCCESS('=== ETL 07.2 - FATURAMENTO CONTABILIDADES (2019-atual) ==='))

        # Parâmetros
        data_inicio = options['data_inicio']
        data_fim = options['data_fim'] or date.today().strftime('%Y-%m-%d')
        contabilidade_id = options.get('contabilidade_id')
        contabilidade_cnpj = options.get('contabilidade_cnpj')
        listar_contabilidades = options.get('listar_contabilidades')

        if listar_contabilidades:
            contabs = Contabilidade.objects.all()
            self.stdout.write(self.style.SUCCESS('Contabilidades cadastradas:'))
            for c in contabs:
                self.stdout.write(f'UUID: {c.id} | CNPJ: {c.cnpj} | id_legado: {getattr(c, "id_legado", "-")} | Razão: {c.razao_social}')
            return

        # Seleção das contabilidades
        if contabilidade_id:
            contabilidades = Contabilidade.objects.filter(id=contabilidade_id)
        elif contabilidade_cnpj:
            cnpj_limpo = sub(r'\D', '', contabilidade_cnpj)
            contabilidades = Contabilidade.objects.filter(cnpj=cnpj_limpo)
        else:
            contabilidades = Contabilidade.objects.all()

        if not contabilidades.exists():
            self.stdout.write(self.style.ERROR('Nenhuma contabilidade encontrada para os filtros informados.'))
            return

        stats = {
            'total_contabilidades': 0,
            'total_registros': 0,
            'faturamento_total': Decimal('0.00'),
            'erros': 0,
            'tempo_execucao': 0,
        }
        inicio_execucao = timezone.now()

        for contabilidade in contabilidades:
            try:
                dados = self.buscar_faturamento_sybase(contabilidade.cnpj, data_inicio, data_fim)
                if not dados:
                    self.stdout.write(self.style.WARNING(f'[INFO] Nenhum dado Sybase para {contabilidade.razao_social}'))
                    continue
                for item in dados:
                    self.criar_registro_faturamento_mes_ano(contabilidade, item)
                    stats['total_registros'] += 1
                    stats['faturamento_total'] += Decimal(str(item.get('total_saidas', 0))) + Decimal(str(item.get('total_servicos', 0)))
                stats['total_contabilidades'] += 1
                self.stdout.write(self.style.SUCCESS(f'[OK] Processada contabilidade: {contabilidade.razao_social}'))
            except Exception as exc:
                stats['erros'] += 1
                msg = f'[ERROR] Erro ao processar contabilidade {contabilidade.razao_social}: {str(exc)}'
                self.stdout.write(self.style.ERROR(msg))

        stats['tempo_execucao'] = (timezone.now() - inicio_execucao).total_seconds()
        self.stdout.write(self.style.SUCCESS(f'=== ETL FINALIZADA ==='))
        self.stdout.write(f"Contabilidades processadas: {stats['total_contabilidades']}")
        self.stdout.write(f"Registros inseridos/atualizados: {stats['total_registros']}")
        self.stdout.write(f"Faturamento total: R$ {stats['faturamento_total']:,.2f}")
        self.stdout.write(f"Erros: {stats['erros']}")
        self.stdout.write(f"Tempo de execução: {stats['tempo_execucao']:.2f} segundos")
    help = 'ETL 07.2 - Importa faturamento das próprias contabilidades (2019-atual) para gestao_faturamento_empresas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-inicio',
            type=str,
            default='2019-01-01',
            help='Data de início para importação (YYYY-MM-DD). Default: 01/01/2019'
        )
        parser.add_argument(
            '--data-fim',
            type=str,
            default=None,
            help='Data de fim para importação (YYYY-MM-DD). Default: hoje'
        )
        parser.add_argument(
            '--contabilidade-id',
            type=str,
            help='UUID da contabilidade específica (opcional)'
        )
        parser.add_argument(
            '--contabilidade-cnpj',
            type=str,
            help='CNPJ da contabilidade específica (opcional, pode ser usado no lugar do UUID)'
        )
        parser.add_argument(
            '--listar-contabilidades',
            action='store_true',
            help='Lista todas as contabilidades cadastradas com UUID, CNPJ e id_legado.'
        )
    def criar_registro_faturamento_mes_ano(self, contabilidade, item):
        try:
            mes = int(item.get('mes'))
            ano = int(item.get('ano'))
            total_saidas = Decimal(str(item.get('total_saidas', 0)))
            total_servicos = Decimal(str(item.get('total_servicos', 0)))
            total_geral = total_saidas + total_servicos
            content_type = ContentType.objects.get_for_model(contabilidade.__class__)
            # Verifica duplicidade antes de criar/atualizar
            existe = FaturamentoEmpresa.objects.filter(
                contabilidade=contabilidade,
                content_type=content_type,
                object_id=contabilidade.id,
                ano=ano,
                mes=mes
            ).exists()
            if existe:
                self.stdout.write(self.style.WARNING(f'[DUPLICIDADE] Já existe registro para {contabilidade.razao_social} ({ano}/{mes:02d})'))
            faturamento, created = FaturamentoEmpresa.objects.update_or_create(
                contabilidade=contabilidade,
                content_type=content_type,
                object_id=contabilidade.id,
                ano=ano,
                mes=mes,
                defaults={
                    'total_saidas': total_saidas,
                    'total_servicos': total_servicos,
                    'total_geral': total_geral,
                }
            )
            status = "criado" if created else "atualizado"
            self.stdout.write(
                f'[DATA] {contabilidade.razao_social} ({ano}/{mes:02d}): Saídas R$ {total_saidas:,.2f} | Serviços R$ {total_servicos:,.2f} | Total R$ {total_geral:,.2f} [{status}]'
            )
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'[ERROR] Erro ao criar faturamento: {str(exc)}'))
            # Não relança para não interromper a ETL

    def buscar_faturamento_sybase(self, cnpj, data_inicio, data_fim):
        """Executa a query de faturamento das contabilidades no Sybase, buscando codi_emp pelo CNPJ (GEEMPRE.CGCE_EMP)"""
        from re import sub
        cnpj_limpo = sub(r'\D', '', str(cnpj))
        query = f'''
            WITH dados_saidas AS (
                SELECT 
                    codi_emp,
                    EXTRACT(MONTH FROM dsai_sai) as mes,
                    EXTRACT(YEAR FROM dsai_sai) as ano,
                    SUM(vcon_sai) as total_saidas
                FROM bethadba.efsaidas
                WHERE dsai_sai BETWEEN '{data_inicio}' AND '{data_fim}'
                  AND codi_emp = (SELECT codi_emp FROM bethadba.geempre WHERE cgce_emp = '{cnpj_limpo}')
                GROUP BY codi_emp, EXTRACT(MONTH FROM dsai_sai), EXTRACT(YEAR FROM dsai_sai)
            ),
            dados_servicos AS (
                SELECT 
                    codi_emp,
                    EXTRACT(MONTH FROM dser_ser) as mes,
                    EXTRACT(YEAR FROM dser_ser) as ano,
                    SUM(vcon_ser) as total_servicos
                FROM bethadba.efservicos
                WHERE dser_ser BETWEEN '{data_inicio}' AND '{data_fim}'
                  AND codi_emp = (SELECT codi_emp FROM bethadba.geempre WHERE cgce_emp = '{cnpj_limpo}')
                  AND NOT EXISTS (
                      SELECT 1 FROM bethadba.efsaidas
                      WHERE efsaidas.codi_emp = efservicos.codi_emp
                        AND EXTRACT(MONTH FROM efsaidas.dsai_sai) = EXTRACT(MONTH FROM efservicos.dser_ser)
                        AND EXTRACT(YEAR FROM efsaidas.dsai_sai) = EXTRACT(YEAR FROM efservicos.dser_ser)
                  )
                GROUP BY codi_emp, EXTRACT(MONTH FROM dser_ser), EXTRACT(YEAR FROM dser_ser)
            )
            SELECT 
                COALESCE(s.codi_emp, sv.codi_emp) as codi_emp,
                COALESCE(s.mes, sv.mes) as mes,
                COALESCE(s.ano, sv.ano) as ano,
                COALESCE(s.total_saidas, 0) as total_saidas,
                COALESCE(sv.total_servicos, 0) as total_servicos
            FROM dados_saidas s
            FULL OUTER JOIN dados_servicos sv ON s.codi_emp = sv.codi_emp AND s.mes = sv.mes AND s.ano = sv.ano
            ORDER BY codi_emp, ano, mes
        '''
        try:
            with self.get_sybase_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                dados = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return dados
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'[ERROR] Erro ao consultar Sybase: {str(exc)}'))
            return []

    def criar_registro_faturamento(self, contabilidade, item):
        try:
            mes = int(str(item.get('competencia'))[4:6])
            ano = int(str(item.get('competencia'))[0:4])
            total_liquido = Decimal(str(item.get('valor_liquido', 0)))
            # Mapeamento: para contabilidade, usamos ela mesma como empresa
            content_type = ContentType.objects.get_for_model(contabilidade.__class__)
            faturamento, created = FaturamentoEmpresa.objects.update_or_create(
                contabilidade=contabilidade,
                content_type=content_type,
                object_id=contabilidade.id,
                ano=ano,
                mes=mes,
                defaults={
                    'total_saidas': total_liquido,  # ou valor_bruto, conforme regra de negócio
                    'total_servicos': Decimal('0.00'),
                }
            )
            status = "criado" if created else "atualizado"
            self.stdout.write(
                f'[DATA] {contabilidade.razao_social} ({ano}/{mes:02d}): Faturamento R$ {total_liquido:,.2f} [{status}]'
            )
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'[ERROR] Erro ao criar faturamento: {str(exc)}'))
            raise

    def get_sybase_connection(self):
        import pyodbc
        import os
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        driver = os.environ.get('ODBC_DRIVER', 'SQL Anywhere 17')
        server = os.environ.get('ODBC_SERVER')
        database = os.environ.get('ODBC_DATABASE')
        uid = os.environ.get('ODBC_USER')
        pwd = os.environ.get('ODBC_PASSWORD')
        connection_string = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={uid};"
            f"PWD={pwd};"
        )
        self.stdout.write(f'[DEBUG] Conectando ao Sybase: {server}/{database} (driver: {driver})')
        return pyodbc.connect(connection_string)
