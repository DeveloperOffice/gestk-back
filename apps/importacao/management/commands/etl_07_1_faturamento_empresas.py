#!/usr/bin/env python
"""
ETL 07.1 - Faturamento Empresas
Importa dados de faturamento das empresas clientes do Sybase aplicando a Regra de Ouro
"""

import os
import sys
import django
from datetime import datetime, date
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from apps.core.models import Contabilidade
from apps.pessoas.models import PessoaJuridica, PessoaFisica
from apps.gestao_models.models import FaturamentoEmpresa
from apps.importacao.management.commands._base import BaseETLCommand


class Command(BaseETLCommand):
    help = 'ETL 07.1 - Importa faturamento das empresas clientes aplicando Regra de Ouro'

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
        """Executa a ETL de faturamento das empresas"""
        self.stdout.write(self.style.SUCCESS('=== ETL 07.1 - FATURAMENTO EMPRESAS (2019-2024) ==='))
        
        # Parâmetros
        data_inicio = options['data_inicio']
        data_fim = options['data_fim'] or date.today().strftime('%Y-%m-%d')
        contabilidade_id = options.get('contabilidade_id')
        
        self.stdout.write(f'Período: {data_inicio} a {data_fim}')
        self.stdout.write(f'[INFO] Importando faturamento de TODOS os clientes (ativos e inativos) dos últimos 5 anos')
        
        try:
            # Executar ETL
            resultado = self.executar_etl_faturamento(data_inicio, data_fim, contabilidade_id)
            
            # Resumo final
            self.stdout.write(self.style.SUCCESS('\n=== RESUMO FINAL ==='))
            self.stdout.write(f'Total de empresas processadas: {resultado["total_empresas"]}')
            self.stdout.write(f'Total de registros de faturamento: {resultado["total_registros"]}')
            self.stdout.write(f'Faturamento total importado: R$ {resultado["faturamento_total"]:,.2f}')
            self.stdout.write(f'Erros: {resultado["erros"]}')
            self.stdout.write(f'Tempo de execução: {resultado["tempo_execucao"]:.2f}s')
            
            if resultado["erros"] > 0:
                self.stdout.write(self.style.WARNING(f'[WARNING] {resultado["erros"]} erros encontrados'))
            else:
                self.stdout.write(self.style.SUCCESS('[SUCCESS] ETL executada com sucesso!'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Erro na ETL: {str(e)}'))
            raise CommandError(f'ETL falhou: {str(e)}')

    def executar_etl_faturamento(self, data_inicio, data_fim, contabilidade_id=None):
        """Executa a ETL de faturamento das empresas"""
        inicio_execucao = timezone.now()
        
        # Estatísticas
        stats = {
            'total_empresas': 0,
            'total_registros': 0,
            'faturamento_total': Decimal('0.00'),
            'erros': 0,
            'tempo_execucao': 0
        }
        
        try:
            # 1. Buscar dados do Sybase
            self.stdout.write('[INFO] Buscando dados de faturamento do Sybase...')
            dados_faturamento = self.buscar_dados_sybase(data_inicio, data_fim)
            
            if not dados_faturamento:
                self.stdout.write(self.style.WARNING('[WARNING] Nenhum dado de faturamento encontrado'))
                return stats
            
            self.stdout.write(f'[INFO] Encontrados {len(dados_faturamento)} registros de faturamento')
            
            # 2. Construir mapeamento Regra de Ouro
            self.stdout.write('[INFO] Construindo mapeamento Regra de Ouro...')
            historical_map = self.build_historical_contabilidade_map_cached()
            
            # 3. Processar dados por contabilidade
            contabilidades_processadas = set()
            
            for item in dados_faturamento:
                try:
                    # Aplicar Regra de Ouro usando historical_map
                    codi_emp = item.get('codi_emp')
                    if not codi_emp:
                        continue
                    
                    # Buscar contabilidade usando Regra de Ouro
                    contabilidade = self.aplicar_regra_ouro_historical(
                        codi_emp, historical_map, contabilidade_id
                    )
                    
                    if not contabilidade:
                        continue
                    
                    # Processar faturamento da empresa
                    self.processar_faturamento_empresa(item, contabilidade)
                    
                    contabilidades_processadas.add(contabilidade.id)
                    stats['total_registros'] += 1
                    stats['faturamento_total'] += Decimal(str(item.get('total_saidas', 0))) + Decimal(str(item.get('total_servicos', 0)))
                    
                except Exception as e:
                    stats['erros'] += 1
                    self.stdout.write(self.style.ERROR(f'[ERROR] Erro ao processar empresa {item.get("codi_emp")}: {str(e)}'))
            
            stats['total_empresas'] = len(contabilidades_processadas)
            
            # 4. Processar faturamento das PRÓPRIAS CONTABILIDADES
            self.stdout.write('[INFO] Processando faturamento das próprias contabilidades...')
            stats_contabilidades = self.processar_faturamento_contabilidades(data_inicio, data_fim, contabilidade_id)
            
            # Somar estatísticas
            stats['total_empresas'] += stats_contabilidades['total_contabilidades']
            stats['total_registros'] += stats_contabilidades['total_registros']
            stats['faturamento_total'] += stats_contabilidades['faturamento_total']
            stats['erros'] += stats_contabilidades['erros']
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Erro na ETL: {str(e)}'))
            raise
        
        finally:
            stats['tempo_execucao'] = (timezone.now() - inicio_execucao).total_seconds()
        
        return stats

    def buscar_dados_sybase(self, data_inicio, data_fim):
        """Busca dados de faturamento do Sybase"""
        query = f"""
            WITH dados_saidas AS (
                SELECT 
                    codi_emp,
                    EXTRACT(MONTH FROM dsai_sai) as mes,
                    EXTRACT(YEAR FROM dsai_sai) as ano,
                    SUM(vcon_sai) as total_saidas
                FROM bethadba.efsaidas
                WHERE dsai_sai BETWEEN '{data_inicio}' AND '{data_fim}'
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
                  AND NOT EXISTS (
                      SELECT 1 FROM bethadba.efsaidas
                      WHERE efsaidas.codi_emp = efservicos.codi_emp
                        AND efsaidas.dsai_sai = efservicos.dser_ser
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
        """
        
        try:
            with self.get_sybase_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                dados = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return dados
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Erro ao consultar Sybase: {str(e)}'))
            raise

    def aplicar_regra_ouro_historical(self, codi_emp, historical_map, contabilidade_id=None):
        """Aplica Regra de Ouro: codi_emp -> geempre.cgce_emp -> historical_map"""
        if not codi_emp:
            return None
        
        try:
            # 1. Buscar CNPJ da empresa na tabela geempre
            cnpj_empresa = self.buscar_cnpj_por_codi_emp(codi_emp)
            if not cnpj_empresa:
                return None
            
            # 2. Limpar CNPJ para usar no historical_map
            cnpj_limpo = self.limpar_documento(cnpj_empresa)
            if not cnpj_limpo:
                return None
            
            # 3. Se especificou contabilidade específica, verificar se a empresa pertence a ela
            if contabilidade_id:
                try:
                    contabilidade = Contabilidade.objects.get(id=contabilidade_id)
                    # Verificar se o CNPJ da empresa está mapeado para esta contabilidade
                    if cnpj_limpo in historical_map:
                        for data_inicio, data_termino, contab, contrato in historical_map[cnpj_limpo]:
                            if contab.id == contabilidade.id:
                                return contabilidade
                    return None
                except Contabilidade.DoesNotExist:
                    return None
            
            # 4. Aplicar Regra de Ouro usando CNPJ no historical_map
            if cnpj_limpo in historical_map:
                # Pegar o contrato mais recente (último da lista)
                contratos = historical_map[cnpj_limpo]
                if contratos:
                    # Ordenar por data de início (mais recente primeiro)
                    contratos_ordenados = sorted(contratos, key=lambda x: x[0], reverse=True)
                    data_inicio, data_termino, contabilidade, contrato = contratos_ordenados[0]
                    return contabilidade
            
            return None
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Erro ao aplicar Regra de Ouro para codi_emp {codi_emp}: {str(e)}'))
            return None

    def buscar_cnpj_por_codi_emp(self, codi_emp):
        """Busca CNPJ da empresa na tabela geempre do Sybase"""
        try:
            with self.get_sybase_connection() as conn:
                cursor = conn.cursor()
                query = f"""
                    SELECT cgce_emp 
                    FROM bethadba.geempre 
                    WHERE codi_emp = {codi_emp}
                """
                cursor.execute(query)
                resultado = cursor.fetchone()
                
                if resultado:
                    return resultado[0]  # cgce_emp
                return None
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Erro ao buscar CNPJ para codi_emp {codi_emp}: {str(e)}'))
            return None

    def processar_faturamento_empresa(self, item, contabilidade):
        """Processa faturamento de uma empresa específica"""
        codi_emp = item.get('codi_emp')
        mes = int(item.get('mes', 0))
        ano = int(item.get('ano', 0))
        total_saidas = Decimal(str(item.get('total_saidas', 0)))
        total_servicos = Decimal(str(item.get('total_servicos', 0)))
        
        if not codi_emp or mes == 0 or ano == 0:
            return
        
        # Buscar empresa (PessoaJuridica ou PessoaFisica)
        empresa = self.buscar_empresa_por_id_legado(codi_emp)
        
        if not empresa:
            self.stdout.write(self.style.WARNING(f'[WARNING] Empresa {codi_emp} não encontrada'))
            return
        
        # Criar/atualizar registro de faturamento
        self.criar_registro_faturamento(
            contabilidade, empresa, ano, mes, total_saidas, total_servicos
        )

    def buscar_empresa_por_id_legado(self, codi_emp):
        """Busca empresa por ID legado"""
        # Tentar PessoaJuridica primeiro
        try:
            return PessoaJuridica.objects.get(id_legado=codi_emp)
        except PessoaJuridica.DoesNotExist:
            pass
        
        # Tentar PessoaFisica
        try:
            return PessoaFisica.objects.get(id_legado=codi_emp)
        except PessoaFisica.DoesNotExist:
            pass
        
        return None

    def criar_registro_faturamento(self, contabilidade, empresa, ano, mes, total_saidas, total_servicos):
        """Cria registro de faturamento no banco"""
        try:
            # Buscar ContentType da empresa
            content_type = ContentType.objects.get_for_model(empresa)
            
            # Criar ou atualizar registro
            faturamento, created = FaturamentoEmpresa.objects.update_or_create(
                contabilidade=contabilidade,
                content_type=content_type,
                object_id=empresa.id,
                ano=ano,
                mes=mes,
                defaults={
                    'total_saidas': total_saidas,
                    'total_servicos': total_servicos,
                }
            )
            
            status = "criado" if created else "atualizado"
            self.stdout.write(
                f'[DATA] {contabilidade.razao_social} - {faturamento.empresa_nome} '
                f'({ano}/{mes:02d}): Saídas R$ {total_saidas:,.2f}, Serviços R$ {total_servicos:,.2f} [{status}]'
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Erro ao criar faturamento: {str(e)}'))
            raise

    def processar_faturamento_contabilidades(self, data_inicio, data_fim, contabilidade_id=None):
        """Processa faturamento das próprias contabilidades"""
        from apps.core.models import Contabilidade
        from apps.gestao_models.models import FaturamentoEmpresa
        from django.contrib.contenttypes.models import ContentType
        
        stats = {
            'total_contabilidades': 0,
            'total_registros': 0,
            'faturamento_total': Decimal('0.00'),
            'erros': 0
        }
        
        try:
            # Buscar contabilidades
            if contabilidade_id:
                contabilidades = Contabilidade.objects.filter(id=contabilidade_id)
            else:
                contabilidades = Contabilidade.objects.all()
            
            for contabilidade in contabilidades:
                try:
                    # Buscar faturamento da contabilidade no Sybase
                    faturamento_contab = self.buscar_faturamento_contabilidade_sybase(
                        contabilidade.cnpj, data_inicio, data_fim
                    )
                    
                    if not faturamento_contab:
                        continue
                    
                    # Processar cada mês de faturamento
                    for item in faturamento_contab:
                        self.criar_registro_faturamento_contabilidade(
                            contabilidade, item
                        )
                        stats['total_registros'] += 1
                        stats['faturamento_total'] += Decimal(str(item.get('total_saidas', 0))) + Decimal(str(item.get('total_servicos', 0)))
                    
                    stats['total_contabilidades'] += 1
                    self.stdout.write(f'[INFO] Processada contabilidade: {contabilidade.razao_social}')
                    
                except Exception as e:
                    stats['erros'] += 1
                    self.stdout.write(self.style.ERROR(f'[ERROR] Erro ao processar contabilidade {contabilidade.razao_social}: {str(e)}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Erro ao processar contabilidades: {str(e)}'))
            stats['erros'] += 1
        
        return stats

    def buscar_faturamento_contabilidade_sybase(self, cnpj_contabilidade, data_inicio, data_fim):
        """Busca faturamento de uma contabilidade específica no Sybase"""
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
                
                # Buscar faturamento da contabilidade
                query_faturamento = f"""
                    WITH dados_saidas AS (
                        SELECT 
                            codi_emp,
                            EXTRACT(MONTH FROM dsai_sai) as mes,
                            EXTRACT(YEAR FROM dsai_sai) as ano,
                            SUM(vcon_sai) as total_saidas
                        FROM bethadba.efsaidas
                        WHERE codi_emp = {codi_emp}
                          AND dsai_sai BETWEEN '{data_inicio}' AND '{data_fim}'
                        GROUP BY codi_emp, EXTRACT(MONTH FROM dsai_sai), EXTRACT(YEAR FROM dsai_sai)
                    ),
                    dados_servicos AS (
                        SELECT 
                            codi_emp,
                            EXTRACT(MONTH FROM dser_ser) as mes,
                            EXTRACT(YEAR FROM dser_ser) as ano,
                            SUM(vcon_ser) as total_servicos
                        FROM bethadba.efservicos
                        WHERE codi_emp = {codi_emp}
                          AND dser_ser BETWEEN '{data_inicio}' AND '{data_fim}'
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
                    ORDER BY ano, mes
                """
                
                cursor.execute(query_faturamento)
                columns = [desc[0] for desc in cursor.description]
                dados = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return dados
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Erro ao buscar faturamento da contabilidade {cnpj_contabilidade}: {str(e)}'))
            return []

    def criar_registro_faturamento_contabilidade(self, contabilidade, item):
        """Cria registro de faturamento para a própria contabilidade"""
        from apps.gestao_models.models import FaturamentoEmpresa
        from django.contrib.contenttypes.models import ContentType
        
        try:
            mes = int(item.get('mes', 0))
            ano = int(item.get('ano', 0))
            total_saidas = Decimal(str(item.get('total_saidas', 0)))
            total_servicos = Decimal(str(item.get('total_servicos', 0)))
            
            # Para contabilidades, usamos a própria contabilidade como "empresa"
            contabilidade_content_type = ContentType.objects.get_for_model(contabilidade.__class__)
            
            faturamento, created = FaturamentoEmpresa.objects.update_or_create(
                contabilidade=contabilidade,
                content_type=contabilidade_content_type,
                object_id=contabilidade.id,
                ano=ano,
                mes=mes,
                defaults={
                    'total_saidas': total_saidas,
                    'total_servicos': total_servicos,
                }
            )
            
            status = "criado" if created else "atualizado"
            self.stdout.write(
                f'[DATA] {contabilidade.razao_social} - PRÓPRIA CONTABILIDADE '
                f'({ano}/{mes:02d}): Saídas R$ {total_saidas:,.2f}, Serviços R$ {total_servicos:,.2f} [{status}]'
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Erro ao criar faturamento da contabilidade: {str(e)}'))
            raise

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
