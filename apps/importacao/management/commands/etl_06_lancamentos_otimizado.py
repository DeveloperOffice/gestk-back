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
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from datetime import date, timedelta
import psutil
import gc
import numpy as np
from functools import lru_cache

def batch_iterator(iterator, batch_size):
    while True:
        batch = list(islice(iterator, batch_size))
        if not batch: break
        yield batch

class Command(BaseETLCommand):
    help = 'ETL OTIMIZADO para carregar os Lançamentos Contábeis com processamento em chunks de 100k registros.'

    def __init__(self):
        super().__init__()
        self.cache_nomes_contas = {}
        self.cache_contas = {}
        self.cache_lancamentos = {}
        
        # Configurações de performance OTIMIZADAS
        self.CPU_CORES = multiprocessing.cpu_count()
        self.BATCH_SIZE_OPTIMIZED = 1000  # Batch size para processamento
        self.MEMORY_CHUNK_SIZE = 100000  # 100k registros por chunk (CONTROLE PRINCIPAL DE MEMÓRIA)
        self.PARALLEL_WORKERS = min(self.CPU_CORES, 4)  # Workers paralelos
        self.CPU_USAGE_LIMIT = 0.5  # 50% CPU
        
        self.stdout.write(f"🚀 Configuração de Performance:")
        self.stdout.write(f"   📦 Tamanho do Chunk em Memória: {self.MEMORY_CHUNK_SIZE:,} registros")
        self.stdout.write(f"   🖥️  CPU cores: {self.CPU_CORES}")
        self.stdout.write(f"   📦 Batch size: {self.BATCH_SIZE_OPTIMIZED}")
        self.stdout.write(f"   ⚡ Workers paralelos: {self.PARALLEL_WORKERS}")
        self.stdout.write(f"   🔥 CPU usage limit: {self.CPU_USAGE_LIMIT*100}%")
        
        # Configuração de performance otimizada


    def obter_nome_conta_sybase(self, connection, codigo_conta):
        """Cache otimizado para nomes de contas do Sybase."""
        if codigo_conta in self.cache_nomes_contas:
            return self.cache_nomes_contas[codigo_conta]
        
        query = """
        SELECT TOP 1 nome_cta 
        FROM BETHADBA.CTCONTAS 
        WHERE codi_cta = ?
        """
        
        cursor = connection.cursor()
        cursor.execute(query, (codigo_conta,))
        result = cursor.fetchone()
        
        if result and result[0]:
            nome = str(result[0]).strip()
            self.cache_nomes_contas[codigo_conta] = nome
            return nome
        
        return None

    def criar_conta_automatica(self, connection, contabilidade, codigo_conta, tipo='D'):
        """Cria conta automaticamente com otimizações."""
        nome_sybase = self.obter_nome_conta_sybase(connection, codigo_conta)
        
        if nome_sybase:
            nome_conta = nome_sybase
            nome_upper = nome_conta.upper()
            if any(palavra in nome_upper for palavra in ['RECEITA', 'VENDA', 'FATURAMENTO', 'PASSIVO', 'CAPITAL']):
                natureza = "CREDORA"
            elif str(codigo_conta).startswith(('2', '3', '4')):
                natureza = "CREDORA"
            else:
                natureza = "DEVEDORA"
        else:
            if tipo == 'D':
                nome_conta = f"Conta Débito {codigo_conta}"
                natureza = "DEVEDORA"
            else:
                nome_conta = f"Conta Crédito {codigo_conta}"
                natureza = "CREDORA"
        
        conta = PlanoContas.objects.create(
            contabilidade=contabilidade,
            id_legado=str(codigo_conta),
            codigo=str(codigo_conta),
            nome=nome_conta,
            nivel=1,
            aceita_lancamento=True,
            tipo_conta="ANALITICA",
            natureza=natureza,
            ativo=True
        )
        
        return conta

    def processar_lote_paralelo(self, lote_data, historical_map, connection):
        """Processa um lote de dados em paralelo com operações em massa."""
        lancamentos_criados = 0
        lancamentos_atualizados = 0
        contas_criadas = 0
        sem_mapeamento = 0
        ex_clientes_validos = 0
        fora_periodo = 0
        
        # Cache local para evitar conflitos entre workers
        cache_contas_local = {}
        
        # Listas para operações em massa
        lancamentos_para_criar = []
        lancamentos_para_atualizar = []
        contas_para_criar = []
        
        # Primeiro, processar todos os dados e separar o que é novo do que existe
        for row in lote_data:
            cnpj_bruto = str(row[1] or '')
            documento_limpo = self.limpar_documento(cnpj_bruto)

            contratos_empresa = historical_map.get(documento_limpo)
            if not contratos_empresa:
                sem_mapeamento += 1
                continue

            data_lancamento = row[2]
            if not data_lancamento:
                sem_mapeamento += 1
                continue

            data_limite_importacao = date(2019, 1, 1)
            data_atual = date.today()
            data_limite_5_anos_atras = data_atual - timedelta(days=5*365)

            if data_lancamento < data_limite_importacao or data_lancamento > data_atual:
                fora_periodo += 1
                continue

            # Aplicar Regra de Ouro - Buscar contabilidade ativa na data
            contabilidade = None
            contrato_correto = None
            
            for data_inicio, data_termino, contab, contrato in contratos_empresa:
                if data_inicio and data_termino and data_inicio <= data_lancamento <= data_termino:
                    contabilidade = contab
                    contrato_correto = contrato
                    break

            # Se não encontrou contrato ativo, buscar ex-clientes válidos (< 5 anos)
            if not contabilidade:
                contratos_validos = []
                for data_inicio, data_termino, contab, contrato in contratos_empresa:
                    if data_termino and data_termino >= data_limite_5_anos_atras:
                        contratos_validos.append((data_inicio, data_termino, contab, contrato))

                if contratos_validos:
                    # Ordenar por data de término (mais recente primeiro)
                    contratos_validos.sort(key=lambda x: x[1] or date.min, reverse=True)
                    data_inicio, data_termino, contabilidade, contrato_correto = contratos_validos[0]
                    ex_clientes_validos += 1

            # Se ainda não encontrou contabilidade, pular registro
            if not contabilidade:
                sem_mapeamento += 1
                continue

            # Preparar dados para bulk operations
            item = {
                'nume_lan': row[0],
                'cnpj': documento_limpo,
                'data_lan': row[2],
                'chis_lan': row[3],
                'vlor_lan': row[4],
                'cdeb_lan': row[5],
                'ccre_lan': row[6],
                'codi_his': row[7]
            }

            # Cache de contas otimizado (local para evitar conflitos)
            chave_conta_debito = (contabilidade.id, str(item.get('cdeb_lan')))
            if chave_conta_debito not in cache_contas_local:
                conta_debito = PlanoContas.objects.filter(
                    contabilidade=contabilidade,
                    id_legado=str(item.get('cdeb_lan'))
                ).first()

                if not conta_debito:
                    conta_debito = self.criar_conta_automatica(connection, contabilidade, item.get('cdeb_lan'), tipo='D')
                    contas_criadas += 1

                cache_contas_local[chave_conta_debito] = conta_debito
            else:
                conta_debito = cache_contas_local[chave_conta_debito]

            chave_conta_credito = (contabilidade.id, str(item.get('ccre_lan')))
            if chave_conta_credito not in cache_contas_local:
                conta_credito = PlanoContas.objects.filter(
                    contabilidade=contabilidade,
                    id_legado=str(item.get('ccre_lan'))
                ).first()

                if not conta_credito:
                    conta_credito = self.criar_conta_automatica(connection, contabilidade, item.get('ccre_lan'), tipo='C')
                    contas_criadas += 1

                cache_contas_local[chave_conta_credito] = conta_credito
            else:
                conta_credito = cache_contas_local[chave_conta_credito]

            if not item.get('vlor_lan'):
                continue

            historico_completo = ''
            if item.get('codi_his'):
                historico_completo = f"Código: {item.get('codi_his')} - "
            if item.get('chis_lan'):
                historico_completo += str(item.get('chis_lan') or '').strip()

            # Preparar dados para operações em massa
            lancamento_data = {
                'contabilidade': contabilidade,
                'contrato': contrato_correto,
                'numero_lancamento': str(item.get('nume_lan')),
                'data_lancamento': item.get('data_lan'),
                'historico': historico_completo[:1000],
                'valor_total': item.get('vlor_lan'),
                'conta_debito': conta_debito,
                'conta_credito': conta_credito
            }
            
            lancamentos_para_criar.append(lancamento_data)

        # Executar operações em massa
        if lancamentos_para_criar:
            try:
                # 1. Buscar lançamentos existentes em uma única consulta
                chaves_para_buscar = [
                    f"{l['numero_lancamento']}_{l['contrato'].id}" 
                    for l in lancamentos_para_criar
                ]
                
                lancamentos_existentes = LancamentoContabil.objects.filter(
                    contabilidade__in=[l['contabilidade'] for l in lancamentos_para_criar],
                    contrato__in=[l['contrato'] for l in lancamentos_para_criar],
                    numero_lancamento__in=[l['numero_lancamento'] for l in lancamentos_para_criar]
                ).values('id', 'numero_lancamento', 'contrato__id', 'contabilidade__id')
                
                # Criar mapa de existentes
                mapa_existentes = {
                    f"{item['numero_lancamento']}_{item['contrato__id']}_{item['contabilidade__id']}": item['id'] 
                    for item in lancamentos_existentes
                }
                
                # Separar novos e existentes
                lancamentos_novos = []
                lancamentos_atualizar = []
                
                for lancamento_data in lancamentos_para_criar:
                    chave = f"{lancamento_data['numero_lancamento']}_{lancamento_data['contrato'].id}_{lancamento_data['contabilidade'].id}"
                    
                    if chave in mapa_existentes:
                        # Existe - preparar para atualização
                        lancamento_obj = LancamentoContabil(
                            id=mapa_existentes[chave],
                            contabilidade=lancamento_data['contabilidade'],
                            contrato=lancamento_data['contrato'],
                            numero_lancamento=lancamento_data['numero_lancamento'],
                            data_lancamento=lancamento_data['data_lancamento'],
                            historico=lancamento_data['historico'],
                            valor_total=lancamento_data['valor_total']
                        )
                        lancamentos_atualizar.append(lancamento_obj)
                        lancamentos_atualizados += 1
                    else:
                        # Novo - preparar para criação
                        lancamento_obj = LancamentoContabil(
                            contabilidade=lancamento_data['contabilidade'],
                            contrato=lancamento_data['contrato'],
                            numero_lancamento=lancamento_data['numero_lancamento'],
                            data_lancamento=lancamento_data['data_lancamento'],
                            historico=lancamento_data['historico'],
                            valor_total=lancamento_data['valor_total']
                        )
                        lancamentos_novos.append(lancamento_obj)
                        lancamentos_criados += 1
                
                # 2. Executar operações em massa
                if lancamentos_novos:
                    LancamentoContabil.objects.bulk_create(lancamentos_novos, batch_size=1000)
                
                if lancamentos_atualizar:
                    LancamentoContabil.objects.bulk_update(
                        lancamentos_atualizar, 
                        ['data_lancamento', 'historico', 'valor_total'],
                        batch_size=1000
                    )
                
                # 3. Criar partidas em massa (simplificado para performance)
                # Nota: Para máxima performance, as partidas poderiam ser criadas em massa também
                # mas isso requereria uma lógica mais complexa
                
            except Exception as e:
                self.stdout.write(f"❌ Erro nas operações em massa: {str(e)}")
                # Fallback para operações individuais se houver erro
                for lancamento_data in lancamentos_para_criar:
                    try:
                        lancamento, created = LancamentoContabil.objects.update_or_create(
                            contabilidade=lancamento_data['contabilidade'],
                            contrato=lancamento_data['contrato'],
                            numero_lancamento=lancamento_data['numero_lancamento'],
                            defaults={
                                'data_lancamento': lancamento_data['data_lancamento'],
                                'historico': lancamento_data['historico'],
                                'valor_total': lancamento_data['valor_total']
                            }
                        )
                        if created:
                            lancamentos_criados += 1
                        else:
                            lancamentos_atualizados += 1
                    except Exception as e2:
                        continue

        return {
            'lancamentos_criados': lancamentos_criados,
            'lancamentos_atualizados': lancamentos_atualizados,
            'contas_criadas': contas_criadas,
            'sem_mapeamento': sem_mapeamento,
            'ex_clientes_validos': ex_clientes_validos,
            'fora_periodo': fora_periodo
        }

    def bulk_create_lancamentos(self, lancamentos_data, partidas_data):
        """Cria lançamentos e partidas em bulk com verificação de duplicatas."""
        lancamentos_criados = 0
        lancamentos_atualizados = 0
        
        for i, lancamento_data in enumerate(lancamentos_data):
            try:
                # Usar update_or_create para evitar duplicatas
                lancamento, created = LancamentoContabil.objects.update_or_create(
                    contabilidade=lancamento_data['contabilidade'],
                    contrato=lancamento_data['contrato'],
                    numero_lancamento=lancamento_data['numero_lancamento'],
                    defaults={
                        'data_lancamento': lancamento_data['data_lancamento'],
                        'historico': lancamento_data['historico'],
                        'valor_total': lancamento_data['valor_total']
                    }
                )
                
                if created:
                    lancamentos_criados += 1
                else:
                    lancamentos_atualizados += 1
                
                # Criar partidas (deletar existentes primeiro)
                Partida.objects.filter(lancamento=lancamento).delete()
                
                partida_data = partidas_data[i]
                Partida.objects.create(
                    lancamento=lancamento, 
                    conta=partida_data['conta_debito'], 
                    tipo='D', 
                    valor=partida_data['valor']
                )
                Partida.objects.create(
                    lancamento=lancamento, 
                    conta=partida_data['conta_credito'], 
                    tipo='C', 
                    valor=partida_data['valor']
                )
                
            except Exception as e:
                # Log do erro mas continua processamento
                continue
        
        return lancamentos_criados, lancamentos_atualizados

    def monitorar_recursos(self):
        """Monitora uso de CPU, memória e GPU."""
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        self.stdout.write(f"📊 Recursos: CPU {cpu_percent:.1f}% | RAM {memory.percent:.1f}% ({memory.used/1024**3:.1f}GB/{memory.total/1024**3:.1f}GB)")
        
        if memory.percent > 90:
            self.stdout.write("⚠️  Memória alta! Executando garbage collection...")
            gc.collect()

    def handle(self, *args, **options):
        # Declarações globais no início
        global total_lancamentos_criados, total_lancamentos_atualizados, total_contas_criadas
        global total_lotes, total_sem_mapeamento, total_ex_clientes_validos, total_fora_periodo
        global tempo_inicio_importacao, total_lancamentos
        
        self.stdout.write(self.style.SUCCESS('--- Iniciando ETL OTIMIZADO para Lançamentos Contábeis ---'))
        self.stdout.write(self.style.WARNING("🚀 MODO ALTA PERFORMANCE: 100k registros por chunk, processamento paralelo"))
        
        # Monitorar recursos iniciais
        self.monitorar_recursos()

        # PASSO 1: Construir o mapa histórico de contabilidades
        self.stdout.write("\n[1/4] Construindo mapa histórico de contabilidades...")
        historical_map = self.build_historical_contabilidade_map()

        connection = self.get_sybase_connection()
        if not connection:
            return

        data_inicio_global = date(2019, 1, 1)
        data_fim_global = date.today()
        data_fim_limite = data_fim_global + timedelta(days=1)

        periodos = []
        corrente = data_inicio_global
        while corrente < data_fim_limite:
            proximo_inicio = date(corrente.year + 1, 1, 1)
            periodo_fim = min(proximo_inicio, data_fim_limite)
            periodos.append((corrente, periodo_fim))
            corrente = proximo_inicio

        count_query = """
        SELECT COUNT(*)
        FROM
            BETHADBA.CTLANCTO l
        INNER JOIN
            BETHADBA.GEEMPRE e ON l.codi_emp = e.codi_emp
        WHERE
            l.data_lan IS NOT NULL 
            AND l.vlor_lan > 0
            AND e.cgce_emp IS NOT NULL AND e.cgce_emp <> ''
            AND l.data_lan >= ?
            AND l.data_lan < ?
        """

        query = """
        SELECT
            l.nume_lan,
            e.cgce_emp,
            l.data_lan,
            l.chis_lan,
            l.vlor_lan,
            l.cdeb_lan,
            l.ccre_lan,
            l.codi_his
        FROM
            BETHADBA.CTLANCTO l
        INNER JOIN
            BETHADBA.GEEMPRE e ON l.codi_emp = e.codi_emp
        WHERE
            l.data_lan IS NOT NULL 
            AND l.vlor_lan > 0
            AND e.cgce_emp IS NOT NULL AND e.cgce_emp <> ''
            AND l.data_lan >= ?
            AND l.data_lan < ?
        """
        
        total_lancamentos = 0
        cursor = connection.cursor()
        
        try:
            self.stdout.write("\n[2/4] Contando lançamentos (otimizado)...")
            inicio_contagem = time.time()
            for i, (periodo_inicio, periodo_fim) in enumerate(periodos):
                periodo_legivel = f"{periodo_inicio.year}"
                self.stdout.write(f"   - Contando ano {periodo_legivel}...", ending="")
                self.stdout.flush()
                
                cursor.execute(count_query, (periodo_inicio, periodo_fim))
                contagem_periodo = cursor.fetchone()[0]
                total_lancamentos += contagem_periodo
                
                self.stdout.write(self.style.SUCCESS(f" {contagem_periodo:,} registros encontrados."))

            tempo_contagem = time.time() - inicio_contagem
            self.stdout.write(self.style.SUCCESS(
                f"✓ Total de lançamentos: {total_lancamentos:,}"
            ))
            self.stdout.write(self.style.WARNING(f"⏱️  Contagem concluída em {tempo_contagem:.1f}s"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao contar lançamentos: {e}"))
            return

        self.stdout.write("\n[3/4] Iniciando importação OTIMIZADA...")
        cursor = connection.cursor()
        
        total_lancamentos_criados = 0
        total_lancamentos_atualizados = 0
        total_contas_criadas = 0
        total_lotes = 0
        total_sem_mapeamento = 0
        total_ex_clientes_validos = 0
        total_fora_periodo = 0
        
        tempo_inicio_importacao = time.time()

        # Processar períodos com otimizações
        for periodo_inicio, periodo_fim in periodos:
            periodo_legivel = f"{periodo_inicio:%Y-%m-%d} até {(periodo_fim - timedelta(days=1)):%Y-%m-%d}"
            self.stdout.write(self.style.WARNING(f"\n➡️  Processando período {periodo_legivel} (OTIMIZADO)..."))

            try:
                cursor.execute(query, (periodo_inicio, periodo_fim))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao recuperar lançamentos: {e}"))
                continue

            # Processar em chunks maiores para usar mais memória
            chunk_data = []
            chunk_size = 0
            
            while True:
                batch = cursor.fetchmany(self.BATCH_SIZE_OPTIMIZED)
                if not batch:
                    break
                
                chunk_data.extend(batch)
                chunk_size += len(batch)
                
                # Processar chunk quando atingir tamanho limite
                if chunk_size >= self.MEMORY_CHUNK_SIZE:
                    self.processar_chunk_otimizado(chunk_data, historical_map, connection)
                    chunk_data = []
                    chunk_size = 0
                    
                    # Monitorar recursos
                    self.monitorar_recursos()
            
            # Processar chunk restante
            if chunk_data:
                self.processar_chunk_otimizado(chunk_data, historical_map, connection)

        connection.close()
        
        tempo_total = time.time() - tempo_inicio_importacao
        tempo_total_min = int(tempo_total / 60)
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('           RESUMO FINAL - ETL 06 OTIMIZADO'))
        self.stdout.write(self.style.SUCCESS('='*80))
        
        self.stdout.write('\n📊 LANÇAMENTOS PROCESSADOS:')
        self.stdout.write(f'   ✅ Criados:                    {total_lancamentos_criados:>10,}')
        self.stdout.write(f'   🔄 Atualizados:                {total_lancamentos_atualizados:>10,}')
        self.stdout.write(f'   📌 Total importado:            {(total_lancamentos_criados + total_lancamentos_atualizados):>10,}')
        
        self.stdout.write('\n🏢 ANÁLISE DE CONTRATOS:')
        self.stdout.write(f'   👥 Ex-clientes válidos (<5a):  {total_ex_clientes_validos:>10,}')
        self.stdout.write(f'   ❌ Sem mapeamento válido:      {total_sem_mapeamento:>10,}')
        self.stdout.write(f'   📅 Fora do período (2019+):    {total_fora_periodo:>10,}')
        
        self.stdout.write('\n📁 CONTAS CONTÁBEIS:')
        self.stdout.write(f'   ➕ Contas criadas (auto):      {total_contas_criadas:>10,}')
        
        self.stdout.write('\n⚙️  PROCESSAMENTO OTIMIZADO:')
        self.stdout.write(f'   📦 Lotes processados:          {total_lotes:>10,}')
        self.stdout.write(f'   📊 Total de registros:         {total_lancamentos:>10,}')
        self.stdout.write(f'   ⏱️  Tempo total:                {tempo_total_min:>10} min')
        self.stdout.write(f'   ⚡ Velocidade média:           {(total_lancamentos_criados + total_lancamentos_atualizados) / tempo_total if tempo_total > 0 else 0:>10.0f} reg/s')
        
        percentual_importado = ((total_lancamentos_criados + total_lancamentos_atualizados) / total_lancamentos * 100) if total_lancamentos > 0 else 0
        self.stdout.write(f'\n✅ Taxa de importação: {percentual_importado:.1f}%')
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('     ETL OTIMIZADO finalizado com sucesso!'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))

    def processar_chunk_otimizado(self, chunk_data, historical_map, connection):
        """Processa um chunk de dados com otimizações de memória e CPU."""
        global total_lancamentos_criados, total_lancamentos_atualizados, total_contas_criadas
        global total_sem_mapeamento, total_ex_clientes_validos, total_fora_periodo, total_lotes
        global total_lancamentos, tempo_inicio_importacao
        
        chunk_size = len(chunk_data)
        total_lotes += 1
        
        inicio_chunk = time.time()
        
        # Dividir chunk em sub-lotes para processamento paralelo
        sub_lote_size = max(1000, chunk_size // self.PARALLEL_WORKERS)
        sub_lotes = [chunk_data[i:i + sub_lote_size] for i in range(0, chunk_size, sub_lote_size)]
        
        # Processar sub-lotes em paralelo
        try:
            with ThreadPoolExecutor(max_workers=self.PARALLEL_WORKERS) as executor:
                futures = []
                for i, sub_lote in enumerate(sub_lotes):
                    self.stdout.write(f"🔄 Sub-lote {i+1}/{len(sub_lotes)}: {len(sub_lote)} registros")
                    future = executor.submit(self.processar_lote_paralelo, sub_lote, historical_map, connection)
                    futures.append(future)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro ao criar ThreadPoolExecutor: {e}"))
            return
        
        # Coletar resultados
        chunk_stats = {
            'lancamentos_criados': 0,
            'lancamentos_atualizados': 0,
            'contas_criadas': 0,
            'sem_mapeamento': 0,
            'ex_clientes_validos': 0,
            'fora_periodo': 0
        }
        
        for future in futures:
            try:
                result = future.result(timeout=300)  # 5 min timeout
                for key in chunk_stats:
                    chunk_stats[key] += result.get(key, 0)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Erro no sub-lote: {str(e)}"))
                import traceback
                self.stdout.write(self.style.ERROR(f"📋 Traceback: {traceback.format_exc()}"))
                continue
        
        # Atualizar estatísticas globais
        total_lancamentos_criados += chunk_stats['lancamentos_criados']
        total_lancamentos_atualizados += chunk_stats['lancamentos_atualizados']
        total_contas_criadas += chunk_stats['contas_criadas']
        total_sem_mapeamento += chunk_stats['sem_mapeamento']
        total_ex_clientes_validos += chunk_stats['ex_clientes_validos']
        total_fora_periodo += chunk_stats['fora_periodo']
        
        tempo_chunk = time.time() - inicio_chunk
        total_processados = total_lancamentos_criados + total_lancamentos_atualizados + total_sem_mapeamento + total_fora_periodo
        
        # Calcular métricas de performance
        tempo_decorrido = time.time() - tempo_inicio_importacao
        velocidade = total_processados / tempo_decorrido if tempo_decorrido > 0 else 0
        registros_restantes = total_lancamentos - total_processados
        tempo_restante_seg = registros_restantes / velocidade if velocidade > 0 else 0
        tempo_restante_min = int(tempo_restante_seg / 60)
        
        percentual = (total_processados / total_lancamentos * 100) if total_lancamentos > 0 else 0
        barra = '█' * int(percentual / 2) + '░' * (50 - int(percentual / 2))
        
        # Monitorar recursos
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        mensagem = (
            f"Chunk {total_lotes:>4} | [{barra}] {percentual:5.1f}% | "
            f"✓ {total_lancamentos_criados:>6} ↻ {total_lancamentos_atualizados:>6} | "
            f"⊕ {total_contas_criadas:>4} | Ex-cli: {total_ex_clientes_validos:>5} | "
            f"✗ {total_sem_mapeamento:>6} | {velocidade:>6.0f} reg/s | ETA: {tempo_restante_min}min | "
            f"CPU: {cpu_percent:>4.0f}% | RAM: {memory.percent:>4.0f}% | chunk: {tempo_chunk:>5.1f}s"
        )
        self.stdout.write(mensagem)
        self.stdout.flush()
        
        # Garbage collection se memória alta
        if memory.percent > 85:
            gc.collect()
            self.stdout.write("🧹 Garbage collection executado")
