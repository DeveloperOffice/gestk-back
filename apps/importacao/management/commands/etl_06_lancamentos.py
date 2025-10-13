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

def batch_iterator(iterator, batch_size):
    while True:
        batch = list(islice(iterator, batch_size))
        if not batch: break
        yield batch

class Command(BaseETLCommand):
    help = 'ETL para carregar os Lançamentos Contábeis (bethadba.ctlancto) em lotes com criação automática de contas.'

    def __init__(self):
        super().__init__()
        self.cache_nomes_contas = {}  # Cache para nomes de contas do Sybase

    def obter_nome_conta_sybase(self, connection, codigo_conta):
        """
        Busca o nome da conta no Sybase.
        """
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
        """
        Cria uma conta automaticamente quando não existe no plano de contas.
        Busca o nome da conta no Sybase quando possível.
        """
        # Buscar nome da conta no Sybase
        nome_sybase = self.obter_nome_conta_sybase(connection, codigo_conta)
        
        if nome_sybase:
            nome_conta = nome_sybase
            # Determinar natureza baseada no nome
            nome_upper = nome_conta.upper()
            if any(palavra in nome_upper for palavra in ['RECEITA', 'VENDA', 'FATURAMENTO', 'PASSIVO', 'CAPITAL']):
                natureza = "CREDORA"
            elif str(codigo_conta).startswith(('2', '3', '4')):
                natureza = "CREDORA"
            else:
                natureza = "DEVEDORA"
        else:
            # Nome padrão se não encontrar no Sybase
            if tipo == 'D':
                nome_conta = f"Conta Débito {codigo_conta}"
                natureza = "DEVEDORA"
            else:
                nome_conta = f"Conta Crédito {codigo_conta}"
                natureza = "CREDORA"
        
        # Criar a conta
        conta = PlanoContas.objects.create(
            contabilidade=contabilidade,
            id_legado=str(codigo_conta),
            codigo=str(codigo_conta),
            nome=nome_conta,
            nivel=1,  # Conta de nível 1 (sem hierarquia)
            aceita_lancamento=True,
            tipo_conta="ANALITICA",
            natureza=natureza,
            ativo=True
        )
        
        return conta

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Iniciando ETL para Lançamentos Contábeis (Regra de Ouro) ---'))
        self.stdout.write(self.style.WARNING("ATENÇÃO: Esta é uma importação incremental. Dados existentes serão mantidos."))

        # PASSO 1: Construir o mapa histórico de contabilidades
        self.stdout.write("\n[1/4] Construindo mapa histórico de contabilidades...")
        historical_map = self.build_historical_contabilidade_map()

        connection = self.get_sybase_connection()
        if not connection:
            return

        data_inicio_global = date(2019, 1, 1)
        data_fim_global = date.today()
        data_fim_limite = data_fim_global + timedelta(days=1)  # limite exclusivo

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
            self.stdout.write("\n[2/4] Contando o número total de lançamentos a serem importados (por ano)...")
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
                f"✓ Total de lançamentos a serem processados do Sybase: {total_lancamentos:,}"
            ))
            self.stdout.write(self.style.WARNING(f"⏱️  Contagem concluída em {tempo_contagem:.1f}s"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao contar lançamentos no Sybase: {e}"))
            return

        self.stdout.write("\n[3/4] Iniciando importação dos lançamentos...")
        cursor = connection.cursor()
        total_lancamentos_criados = 0
        total_lancamentos_atualizados = 0
        total_contas_criadas = 0
        total_lotes = 0
        total_sem_mapeamento = 0
        total_sem_contrato_ativo = 0
        total_ex_clientes_validos = 0
        total_fora_periodo = 0
        BATCH_SIZE = 500  # Reduzido para commits mais frequentes e feedback visual

        cache_contas = {}
        
        # Variáveis para cálculo de velocidade
        tempo_inicio_importacao = time.time()

        # Construir períodos anuais para evitar overload no Sybase
        for periodo_inicio, periodo_fim in periodos:
            periodo_legivel = f"{periodo_inicio:%Y-%m-%d} até {(periodo_fim - timedelta(days=1)):%Y-%m-%d}"
            self.stdout.write(self.style.WARNING(f"\n➡️  Processando período {periodo_legivel}..."))

            try:
                cursor.execute(query, (periodo_inicio, periodo_fim))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"Erro ao recuperar lançamentos do período {periodo_legivel}: {e}"
                ))
                continue

            while True:
                batch = cursor.fetchmany(BATCH_SIZE)
                if not batch:
                    break

                total_lotes += 1
                inicio_lote = time.time()

                try:
                    with transaction.atomic():
                        for row in batch:
                            cnpj_bruto = str(row[1] or '')
                            documento_limpo = self.limpar_documento(cnpj_bruto)

                            contratos_empresa = historical_map.get(documento_limpo)
                            if not contratos_empresa:
                                total_sem_mapeamento += 1
                                continue

                            data_lancamento = row[2]
                            if not data_lancamento:
                                total_sem_mapeamento += 1
                                continue

                            data_limite_importacao = date(2019, 1, 1)
                            data_atual = date.today()
                            data_limite_5_anos_atras = data_atual - timedelta(days=5*365)

                            if data_lancamento < data_limite_importacao or data_lancamento > data_atual:
                                total_fora_periodo += 1
                                continue

                            contabilidade = None
                            contrato_correto = None

                            for data_inicio, data_termino, contab, contrato in contratos_empresa:
                                if data_inicio and data_termino and data_inicio <= data_lancamento <= data_termino:
                                    contabilidade = contab
                                    contrato_correto = contrato
                                    break

                            if not contabilidade:
                                contratos_validos = []
                                for data_inicio, data_termino, contab, contrato in contratos_empresa:
                                    if data_termino and data_termino >= data_limite_5_anos_atras:
                                        contratos_validos.append((data_inicio, data_termino, contab, contrato))

                                if contratos_validos:
                                    contratos_validos.sort(key=lambda x: x[1] or date.min, reverse=True)
                                    data_inicio, data_termino, contabilidade, contrato_correto = contratos_validos[0]
                                    total_ex_clientes_validos += 1

                            if not contabilidade:
                                total_sem_mapeamento += 1
                                continue

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

                            # Obter nomes das contas de forma otimizada
                            item['nome_deb'] = self.obter_nome_conta_sybase(connection, item['cdeb_lan'])
                            item['nome_cred'] = self.obter_nome_conta_sybase(connection, item['ccre_lan'])

                            chave_conta_debito = (contabilidade.id, str(item.get('cdeb_lan')))
                            if chave_conta_debito not in cache_contas:
                                conta_debito = PlanoContas.objects.filter(
                                    contabilidade=contabilidade,
                                    id_legado=str(item.get('cdeb_lan'))
                                ).first()

                                if not conta_debito:
                                    conta_debito = self.criar_conta_automatica(connection, contabilidade, item.get('cdeb_lan'), tipo='D')
                                    total_contas_criadas += 1

                                cache_contas[chave_conta_debito] = conta_debito
                            else:
                                conta_debito = cache_contas[chave_conta_debito]

                            chave_conta_credito = (contabilidade.id, str(item.get('ccre_lan')))
                            if chave_conta_credito not in cache_contas:
                                conta_credito = PlanoContas.objects.filter(
                                    contabilidade=contabilidade,
                                    id_legado=str(item.get('ccre_lan'))
                                ).first()

                                if not conta_credito:
                                    conta_credito = self.criar_conta_automatica(connection, contabilidade, item.get('ccre_lan'), tipo='C')
                                    total_contas_criadas += 1

                                cache_contas[chave_conta_credito] = conta_credito
                            else:
                                conta_credito = cache_contas[chave_conta_credito]

                            if not item.get('vlor_lan'):
                                continue

                            historico_completo = ''
                            if item.get('codi_his'):
                                historico_completo = f"Código: {item.get('codi_his')} - "
                            if item.get('chis_lan'):
                                historico_completo += str(item.get('chis_lan') or '').strip()

                            lancamento, created = LancamentoContabil.objects.update_or_create(
                                contabilidade=contabilidade,
                                contrato=contrato_correto,
                                numero_lancamento=str(item.get('nume_lan')),
                                defaults={
                                    'data_lancamento': item.get('data_lan'),
                                    'historico': historico_completo[:1000],
                                    'valor_total': item.get('vlor_lan')
                                }
                            )

                            if created:
                                total_lancamentos_criados += 1
                            else:
                                total_lancamentos_atualizados += 1

                            Partida.objects.filter(lancamento=lancamento).delete()
                            Partida.objects.create(lancamento=lancamento, conta=conta_debito, tipo='D', valor=lancamento.valor_total)
                            Partida.objects.create(lancamento=lancamento, conta=conta_credito, tipo='C', valor=lancamento.valor_total)

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Erro no lote {total_lotes}: {str(e)[:300]}"))
                    import traceback
                    self.stdout.write(self.style.ERROR(f"Stack: {traceback.format_exc()[:500]}"))
                    continue

                tempo_lote = time.time() - inicio_lote

                tempo_decorrido = time.time() - tempo_inicio_importacao
                total_processados = total_lancamentos_criados + total_lancamentos_atualizados + total_sem_mapeamento + total_fora_periodo
                velocidade = total_processados / tempo_decorrido if tempo_decorrido > 0 else 0
                registros_restantes = total_lancamentos - total_processados
                tempo_restante_seg = registros_restantes / velocidade if velocidade > 0 else 0
                tempo_restante_min = int(tempo_restante_seg / 60)

                percentual = (total_processados / total_lancamentos * 100) if total_lancamentos > 0 else 0
                barra = '█' * int(percentual / 2) + '░' * (50 - int(percentual / 2))

                mensagem = (
                    f"Lote {total_lotes:>4} | [{barra}] {percentual:5.1f}% | "
                    f"✓ {total_lancamentos_criados:>6} ↻ {total_lancamentos_atualizados:>6} | "
                    f"⊕ {total_contas_criadas:>4} | Ex-cli: {total_ex_clientes_validos:>5} | "
                    f"✗ {total_sem_mapeamento:>6} | {velocidade:>6.0f} reg/s | ETA: {tempo_restante_min}min | "
                    f"lote: {tempo_lote:>5.1f}s"
                )
                self.stdout.write(mensagem)
                self.stdout.flush()

        connection.close()
        
        tempo_total = time.time() - tempo_inicio_importacao
        tempo_total_min = int(tempo_total / 60)
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('           RESUMO FINAL - ETL 06 - LANÇAMENTOS CONTÁBEIS'))
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
        
        self.stdout.write('\n⚙️  PROCESSAMENTO:')
        self.stdout.write(f'   📦 Lotes processados:          {total_lotes:>10,}')
        self.stdout.write(f'   📊 Total de registros:         {total_lancamentos:>10,}')
        self.stdout.write(f'   ⏱️  Tempo total:                {tempo_total_min:>10} min')
        self.stdout.write(f'   ⚡ Velocidade média:           {(total_lancamentos_criados + total_lancamentos_atualizados) / tempo_total if tempo_total > 0 else 0:>10.0f} reg/s')
        
        percentual_importado = ((total_lancamentos_criados + total_lancamentos_atualizados) / total_lancamentos * 100) if total_lancamentos > 0 else 0
        self.stdout.write(f'\n✅ Taxa de importação: {percentual_importado:.1f}%')
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('     ETL de Lançamentos Contábeis finalizado com sucesso!'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))