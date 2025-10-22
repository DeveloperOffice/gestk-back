from django.db import transaction
from ._base import BaseETLCommand
from apps.core.models import Contabilidade
from apps.contabil.models import PlanoContas, LancamentoContabil, Partida
from apps.pessoas.models import PessoaJuridica, Contrato
from django.contrib.contenttypes.models import ContentType
from itertools import islice
import datetime
import re
import time
from datetime import date, timedelta
from decimal import Decimal

class Command(BaseETLCommand):
    help = 'ETL 06.1 - Importa lançamentos contábeis das PRÓPRIAS CONTABILIDADES (não dos clientes)'

    def __init__(self):
        super().__init__()
        self.cache_nomes_contas = {}
        self.cache_contas = {}
        
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
            help='ID da contabilidade específica (opcional)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== ETL 06.1 - LANÇAMENTOS DAS CONTABILIDADES ==='))
        
        data_inicio_str = options['data_inicio']
        data_fim_str = options['data_fim'] or date.today().strftime('%Y-%m-%d')
        contabilidade_id = options.get('contabilidade_id')
        
        self.stdout.write(f'Período: {data_inicio_str} a {data_fim_str}')
        self.stdout.write(f'[INFO] Importando lançamentos das PRÓPRIAS CONTABILIDADES')
        
        try:
            data_inicio = datetime.datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            resultado = self.executar_etl_lancamentos_contabilidades(data_inicio, data_fim, contabilidade_id)
            
            self.stdout.write('\n=== RESUMO FINAL ===')
            self.stdout.write(f'Total de contabilidades processadas: {resultado["total_contabilidades"]}')
            self.stdout.write(f'Total de lançamentos importados: {resultado["total_lancamentos"]}')
            self.stdout.write(f'Valor total dos lançamentos: R$ {resultado["valor_total"]:,.2f}')
            self.stdout.write(f'Erros: {resultado["erros"]}')
            self.stdout.write(f'Tempo de execução: {resultado["tempo_execucao"]:.2f}s')
            
            if resultado["erros"] > 0:
                self.stdout.write(self.style.WARNING(f'[WARNING] {resultado["erros"]} erros encontrados'))
            else:
                self.stdout.write(self.style.SUCCESS('[SUCCESS] ETL executada com sucesso!'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Erro na ETL: {str(e)}'))
            raise

    def executar_etl_lancamentos_contabilidades(self, data_inicio, data_fim, contabilidade_id=None):
        inicio_execucao = time.time()
        stats = {
            'total_contabilidades': 0,
            'total_lancamentos': 0,
            'valor_total': Decimal('0.00'),
            'erros': 0,
            'tempo_execucao': 0
        }
        
        try:
            # 1. Buscar contabilidades
            if contabilidade_id:
                contabilidades = Contabilidade.objects.filter(id=contabilidade_id)
            else:
                contabilidades = Contabilidade.objects.all()
            
            self.stdout.write(f'[INFO] Processando {contabilidades.count()} contabilidades')
            
            # 2. Processar cada contabilidade
            for contabilidade in contabilidades:
                try:
                    self.stdout.write(f'[INFO] Processando: {contabilidade.razao_social}')
                    
                    # Buscar lançamentos da contabilidade no Sybase
                    lancamentos_contab = self.buscar_lancamentos_contabilidade_sybase(
                        contabilidade.cnpj, data_inicio, data_fim
                    )
                    
                    if not lancamentos_contab:
                        self.stdout.write(f'[WARNING] Nenhum lançamento encontrado para {contabilidade.razao_social}')
                        continue
                    
                    self.stdout.write(f'[INFO] Encontrados {len(lancamentos_contab)} lançamentos para {contabilidade.razao_social}')
                    
                    # Processar lançamentos
                    lancamentos_processados = self.processar_lancamentos_contabilidade(
                        contabilidade, lancamentos_contab
                    )
                    
                    stats['total_lancamentos'] += lancamentos_processados['total']
                    stats['valor_total'] += lancamentos_processados['valor_total']
                    stats['erros'] += lancamentos_processados['erros']
                    stats['total_contabilidades'] += 1
                    
                    self.stdout.write(f'[SUCCESS] {contabilidade.razao_social}: {lancamentos_processados["total"]} lançamentos processados')
                    
                except Exception as e:
                    stats['erros'] += 1
                    self.stdout.write(self.style.ERROR(f'[ERROR] Erro ao processar {contabilidade.razao_social}: {str(e)}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Erro na ETL: {str(e)}'))
            raise
        
        finally:
            stats['tempo_execucao'] = time.time() - inicio_execucao
        
        return stats

    def buscar_lancamentos_contabilidade_sybase(self, cnpj_contabilidade, data_inicio, data_fim):
        """Busca lançamentos de uma contabilidade específica no Sybase"""
        try:
            with self.get_sybase_connection() as conn:
                cursor = conn.cursor()
                
                # Buscar codi_emp da contabilidade
                query_empresa = f"""
                    SELECT codi_emp 
                    FROM bethadba.geempre 
                    WHERE cgce_emp = '{cnpj_contabilidade}'
                """
                cursor.execute(query_empresa)
                resultado_empresa = cursor.fetchone()
                
                if not resultado_empresa:
                    return []
                
                codi_emp = resultado_empresa[0]
                
                # Buscar lançamentos da contabilidade
                query_lancamentos = f"""
                    SELECT 
                        l.codi_emp,
                        l.nume_lan,
                        l.data_lan,
                        l.vlor_lan,
                        l.cdeb_lan,
                        l.ccre_lan,
                        l.chis_lan,
                        l.codi_usu,
                        l.orig_lan,
                        l.ndoc_lan,
                        l.fili_lan,
                        l.dorig_lan,
                        l.codi_pad,
                        l.origem_reg,
                        l.codi_lote
                    FROM bethadba.ctlancto l
                    WHERE l.codi_emp = {codi_emp}
                      AND l.data_lan BETWEEN '{data_inicio}' AND '{data_fim}'
                    ORDER BY l.data_lan, l.nume_lan
                """
                
                cursor.execute(query_lancamentos)
                columns = [desc[0] for desc in cursor.description]
                dados = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return dados
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Erro ao buscar lançamentos da contabilidade {cnpj_contabilidade}: {str(e)}'))
            return []

    def processar_lancamentos_contabilidade(self, contabilidade, lancamentos_data):
        """Processa lançamentos de uma contabilidade específica"""
        stats = {
            'total': 0,
            'valor_total': Decimal('0.00'),
            'erros': 0
        }
        
        # Processar cada lançamento
        for item in lancamentos_data:
            try:
                with transaction.atomic():
                    # Criar identificador único combinando numero_lancamento + data_lancamento
                    identificador_unico = f"{item['nume_lan']}_{item['data_lan'].strftime('%Y%m%d')}"
                    
                    # Criar ou atualizar lançamento
                    lancamento, created = LancamentoContabil.objects.update_or_create(
                        contabilidade=contabilidade,
                        numero_lancamento=identificador_unico,
                        defaults={
                            'data_lancamento': item['data_lan'],
                            'historico': item['chis_lan'] or '',
                            'valor_total': Decimal(str(item['vlor_lan'])),
                            'contrato': None  # Lançamentos das contabilidades não têm contrato
                        }
                    )
                    
                    # Processar partidas (débito e crédito)
                    self.processar_partidas_lancamento(lancamento, item)
                    
                    stats['total'] += 1
                    stats['valor_total'] += Decimal(str(item['vlor_lan']))
                    
                    if created:
                        self.stdout.write(f'[DATA] {contabilidade.razao_social} - Lançamento {item["nume_lan"]} criado')
                    else:
                        self.stdout.write(f'[DATA] {contabilidade.razao_social} - Lançamento {item["nume_lan"]} atualizado')
                    
            except Exception as e:
                stats['erros'] += 1
                self.stdout.write(self.style.ERROR(f'[ERROR] Erro ao processar lançamento {item["nume_lan"]}: {str(e)}'))
        
        return stats

    def processar_partidas_lancamento(self, lancamento, item):
        """Processa as partidas de um lançamento (débito e crédito)"""
        # Limpar partidas existentes
        lancamento.partidas.all().delete()
        
        try:
            # Partida de débito
            if item['cdeb_lan']:
                conta_debito = self.buscar_ou_criar_conta(
                    lancamento.contabilidade, 
                    item['cdeb_lan']
                )
                
                Partida.objects.create(
                    lancamento=lancamento,
                    conta=conta_debito,
                    tipo_partida='D',
                    valor=Decimal(str(item['vlor_lan']))
                )
            
            # Partida de crédito
            if item['ccre_lan']:
                conta_credito = self.buscar_ou_criar_conta(
                    lancamento.contabilidade, 
                    item['ccre_lan']
                )
                
                Partida.objects.create(
                    lancamento=lancamento,
                    conta=conta_credito,
                    tipo_partida='C',
                    valor=Decimal(str(item['vlor_lan']))
                )
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Erro ao processar partidas: {str(e)}'))

    def buscar_ou_criar_conta(self, contabilidade, codigo_conta):
        """Busca ou cria conta no plano de contas"""
        try:
            return PlanoContas.objects.get(
                contabilidade=contabilidade,
                id_legado=str(codigo_conta)
            )
        except PlanoContas.DoesNotExist:
            # Criar conta automaticamente
            return self.criar_conta_automatica(contabilidade, codigo_conta)

    def criar_conta_automatica(self, contabilidade, codigo_conta):
        """Cria conta automaticamente no plano de contas"""
        nome_conta = f"Conta {codigo_conta}"
        
        # Determinar natureza baseada no código
        if str(codigo_conta).startswith(('2', '3', '4')):
            natureza = "CREDORA"
        else:
            natureza = "DEVEDORA"
        
        return PlanoContas.objects.create(
            contabilidade=contabilidade,
            id_legado=str(codigo_conta),
            codigo=str(codigo_conta),
            nome=nome_conta,
            nivel=1,
            aceita_lancamento=True,
            natureza=natureza
        )

    def get_sybase_connection(self):
        """Conecta ao banco Sybase"""
        import pyodbc
        from django.conf import settings
        
        # Usar configurações do settings.py
        config = settings.SYBASE_CONFIG
        
        connection_string = (
            f"DRIVER={{{config['DRIVER']}}};"
            f"SERVER={config['SERVER']};"
            f"DATABASE={config['DATABASE']};"
            f"UID={config['UID']};"
            f"PWD={config['PWD']};"
        )
        
        self.stdout.write(f'[DEBUG] Conectando ao Sybase: {config["SERVER"]}/{config["DATABASE"]}')
        
        return pyodbc.connect(connection_string)
