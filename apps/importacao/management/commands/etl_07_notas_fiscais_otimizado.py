from django.core.management.base import BaseCommand
from apps.importacao.management.commands._base import BaseETLCommand
from apps.fiscal.models import NotaFiscal, NotaFiscalItem
from apps.pessoas.models import PessoaFisica, PessoaJuridica
from apps.core.models import Contabilidade
from decimal import Decimal
import re
import time
from datetime import datetime, date, timedelta
from django.db import transaction
import sys


class Command(BaseETLCommand):
    help = 'ETL 07 OTIMIZADA: Importacao de Notas Fiscais - Estrategia: Cabecalhos primeiro, depois itens'

    def __init__(self):
        super().__init__()
        self.cache_pessoas = {}
        
        # Configuracoes
        self.ANO_INICIO = 2019
        self.ANO_FIM = date.today().year
        self.LIMITE_NOTAS_POR_QUERY = 50  # Buscar itens de 50 notas por vez
        
        # Estatísticas
        self.stats = {
            'total_cabecalhos_lidos': 0,
            'total_cabecalhos_validos': 0,
            'notas_criadas': 0,
            'notas_puladas': 0,
            'itens_criados': 0,
            'erros': 0,
            'sem_contabilidade': 0,
            'cnpj_invalido': 0,
            'empresas_processadas': set(),
            'tempo_inicio': None,
            'tempo_fim': None
        }
        
        self.stdout.write("="*80)
        self.stdout.write("🚀 ETL 07 OTIMIZADA - IMPORTAÇÃO DE NOTAS FISCAIS")
        self.stdout.write("="*80)
        self.stdout.write(f"📅 Período: {self.ANO_INICIO} até {self.ANO_FIM}")
        self.stdout.write(f"📦 Limite por query: {self.LIMITE_NOTAS_POR_QUERY} notas")
        self.stdout.write("⚡ Estratégia: Cabeçalhos → Filtro → Itens")
        self.stdout.write("="*80)

    def limpar_documento(self, documento):
        """Remove caracteres nao numericos do documento"""
        if not documento:
            return None
        documento_limpo = re.sub(r'\D', '', str(documento))
        if len(documento_limpo) in [11, 14]:  # CPF ou CNPJ
            return documento_limpo
        return None

    def find_contabilidade_por_cliente(self, cnpj_cpf_cliente, data_emissao, historical_map):
        """
        REGRA DE OURO: Busca contabilidade verificando se emitente/destinatário é cliente
        
        Prioridades:
        1. Contrato ativo na data de emissão
        2. Contrato ativo hoje
        3. Ex-cliente válido (< 5 anos)
        """
        if not cnpj_cpf_cliente or not data_emissao:
            return None, None
        
        contratos_cliente = historical_map.get(cnpj_cpf_cliente)
        if not contratos_cliente:
            return None, None
        
        # Converter data_emissao para date
        if isinstance(data_emissao, str):
            try:
                data_emissao = datetime.strptime(data_emissao.split(' ')[0], '%Y-%m-%d').date()
            except:
                return None, None
        elif hasattr(data_emissao, 'date'):
            data_emissao = data_emissao.date()
        
        data_atual = date.today()
        
        # PRIORIDADE 1: Contrato ativo na data de emissão
        for data_inicio, data_termino, contabilidade, contrato in contratos_cliente:
            if data_inicio and data_termino and data_inicio <= data_emissao <= data_termino:
                return contabilidade, contrato
        
        # PRIORIDADE 2: Contrato ativo hoje
        for data_inicio, data_termino, contabilidade, contrato in contratos_cliente:
            if data_inicio and data_termino and data_inicio <= data_atual <= data_termino:
                return contabilidade, contrato
        
        # PRIORIDADE 3: Ex-clientes válidos (< 5 anos)
        data_limite = data_atual - timedelta(days=5*365)
        contratos_validos = []
        for data_inicio, data_termino, contabilidade, contrato in contratos_cliente:
            if data_termino and data_termino >= data_limite:
                contratos_validos.append((data_inicio, data_termino, contabilidade, contrato))
        
        if contratos_validos:
            contratos_validos.sort(key=lambda x: x[1] or date.min, reverse=True)
            return contratos_validos[0][2], contratos_validos[0][3]
        
        return None, None

    def criar_ou_obter_pessoa(self, documento, nome):
        """Cria ou obtém pessoa (física ou jurídica)"""
        documento_limpo = self.limpar_documento(documento)
        if not documento_limpo:
            return None
        
        if documento_limpo in self.cache_pessoas:
            return self.cache_pessoas[documento_limpo]
        
        if len(documento_limpo) == 14:  # CNPJ
            try:
                pessoa = PessoaJuridica.objects.get(cnpj=documento_limpo)
            except PessoaJuridica.DoesNotExist:
                pessoa = PessoaJuridica.objects.create(
                    cnpj=documento_limpo,
                    razao_social=str(nome or '').strip() or 'NAO INFORMADO',
                    nome_fantasia=str(nome or '').strip() or 'NAO INFORMADO'
                )
        else:  # CPF
            try:
                pessoa = PessoaFisica.objects.get(cpf=documento_limpo)
            except PessoaFisica.DoesNotExist:
                pessoa = PessoaFisica.objects.create(
                    cpf=documento_limpo,
                    nome_completo=str(nome or '').strip() or 'NAO INFORMADO'
                )
        
        self.cache_pessoas[documento_limpo] = pessoa
        return pessoa

    def processar_tipo_nota(self, connection, historical_map, tipo_nota, config_queries):
        """
        Processa um tipo de nota (ENTRADA, SAIDA ou SERVICO)
        """
        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(f"📋 TIPO: {tipo_nota}")
        self.stdout.write(f"{'='*80}")
        
        for ano in range(self.ANO_INICIO, self.ANO_FIM + 1):
            self.stdout.write(f"\n📅 ANO {ano}")
            
            for mes in range(1, 13):
                # Parar se for mês futuro
                hoje = date.today()
                if ano == hoje.year and mes > hoje.month:
                    break
                
                self.processar_mes(
                    connection,
                    historical_map,
                    tipo_nota,
                    config_queries,
                    ano,
                    mes
                )

    def processar_mes(self, connection, historical_map, tipo_nota, config_queries, ano, mes):
        """
        Processa um mês específico
        """
        import calendar
        
        data_inicio = f"{ano}-{mes:02d}-01"
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        data_fim = f"{ano}-{mes:02d}-{ultimo_dia}"
        
        self.stdout.write(f"\n   📆 {ano}/{mes:02d} ({data_inicio} a {data_fim})")
        
        # ETAPA 1: Buscar cabeçalhos
        query_cabecalho = config_queries['cabecalho'].format(
            data_inicio=data_inicio,
            data_fim=data_fim
        )
        
        cursor = connection.cursor()
        try:
            cursor.execute(query_cabecalho)
            cabecalhos = cursor.fetchall()
            cursor.close()
            
            self.stats['total_cabecalhos_lidos'] += len(cabecalhos)
            
            if not cabecalhos:
                self.stdout.write(f"      ⏭️  Sem notas")
                return
            
            self.stdout.write(f"      📊 {len(cabecalhos):,} notas encontradas")
            
            # ETAPA 2: Filtrar por REGRA DE OURO
            notas_validas = self.filtrar_por_contabilidade(
                cabecalhos,
                historical_map,
                tipo_nota
            )
            
            if not notas_validas:
                self.stdout.write(f"      ⏭️  Nenhuma pertence às contabilidades")
                return
            
            self.stdout.write(f"      ✅ {len(notas_validas):,} notas válidas")
            
            # ETAPA 3: Buscar itens e criar notas
            self.processar_notas_validas(
                connection,
                notas_validas,
                config_queries['itens'],
                tipo_nota
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"      ❌ Erro: {str(e)}"))
            if cursor:
                cursor.close()

    def filtrar_por_contabilidade(self, cabecalhos, historical_map, tipo_nota):
        """
        Aplica REGRA DE OURO para filtrar notas
        """
        notas_validas = []
        
        for row in cabecalhos:
            chave_nf = str(row[0]).strip() if row[0] else ''
            cnpj_emitente = self.limpar_documento(str(row[1] or ''))
            cpf_cnpj_dest = self.limpar_documento(str(row[2] or ''))
            data_emissao = row[3]
            
            if not chave_nf or len(chave_nf) < 44:
                continue
            
            # Aplicar REGRA DE OURO
            contab_emit, contr_emit = self.find_contabilidade_por_cliente(
                cnpj_emitente, data_emissao, historical_map
            )
            contab_dest, contr_dest = self.find_contabilidade_por_cliente(
                cpf_cnpj_dest, data_emissao, historical_map
            )
            
            # PRIORIDADE: Destinatário > Emitente
            if contab_dest:
                contabilidade, contrato, doc_cliente = contab_dest, contr_dest, cpf_cnpj_dest
            elif contab_emit:
                contabilidade, contrato, doc_cliente = contab_emit, contr_emit, cnpj_emitente
            else:
                self.stats['sem_contabilidade'] += 1
                continue
            
            if doc_cliente:
                self.stats['empresas_processadas'].add(doc_cliente)
            
            notas_validas.append({
                'chave': chave_nf,
                'contabilidade': contabilidade,
                'contrato': contrato,
                'dados': row
            })
        
        self.stats['total_cabecalhos_validos'] += len(notas_validas)
        return notas_validas

    def processar_notas_validas(self, connection, notas_validas, query_itens_template, tipo_nota):
        """
        Para cada nota válida, busca itens e cria no PostgreSQL
        """
        total = len(notas_validas)
        
        # Processar em lotes
        for i in range(0, total, self.LIMITE_NOTAS_POR_QUERY):
            lote = notas_validas[i:i + self.LIMITE_NOTAS_POR_QUERY]
            lote_num = (i // self.LIMITE_NOTAS_POR_QUERY) + 1
            total_lotes = (total + self.LIMITE_NOTAS_POR_QUERY - 1) // self.LIMITE_NOTAS_POR_QUERY
            
            self.stdout.write(f"      📦 Lote {lote_num}/{total_lotes} ({len(lote)} notas)")
            
            # Buscar itens
            chaves = [n['chave'] for n in lote]
            query_itens = query_itens_template.format(
                chaves="'" + "','".join(chaves) + "'"
            )
            
            cursor = connection.cursor()
            try:
                cursor.execute(query_itens)
                itens_rows = cursor.fetchall()
                cursor.close()
                
                # Agrupar itens por chave
                itens_por_chave = {}
                for item in itens_rows:
                    chave = str(item[0]).strip()
                    if chave not in itens_por_chave:
                        itens_por_chave[chave] = []
                    itens_por_chave[chave].append(item)
                
                # Criar notas
                resultado = self.criar_notas_lote(lote, itens_por_chave, tipo_nota)
                
                self.stats['notas_criadas'] += resultado['criadas']
                self.stats['notas_puladas'] += resultado['puladas']
                self.stats['itens_criados'] += resultado['itens']
                self.stats['erros'] += resultado['erros']
                
                self.stdout.write(f"         ✅ +{resultado['criadas']} notas | +{resultado['itens']} itens")
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"         ❌ Erro: {str(e)}"))
                if cursor:
                    cursor.close()

    def criar_notas_lote(self, lote_notas, itens_por_chave, tipo_nota):
        """
        Cria notas fiscais e itens no PostgreSQL
        """
        resultado = {'criadas': 0, 'puladas': 0, 'itens': 0, 'erros': 0}
        
        for nota_info in lote_notas:
            chave = nota_info['chave']
            contabilidade = nota_info['contabilidade']
            contrato = nota_info['contrato']
            dados = nota_info['dados']
            
            try:
                # IDEMPOTÊNCIA
                if NotaFiscal.objects.filter(contabilidade=contabilidade, chave_acesso=chave).exists():
                    resultado['puladas'] += 1
                    continue
                
                # Extrair dados
                numero = str(dados[4])
                serie = str(dados[5])
                data_emissao = dados[3]
                data_movimento = dados[6]
                situacao = str(dados[7] or 'AUTORIZADA')
                valor_total = Decimal(str(dados[8] or 0))
                cod_empresa = str(dados[9])
                cod_parceiro = str(dados[10])
                nome_parceiro = str(dados[11] or '')
                cpf_cnpj_parceiro = dados[2]
                
                # Parceiro
                parceiro = self.criar_ou_obter_pessoa(cpf_cnpj_parceiro, nome_parceiro)
                if not parceiro:
                    resultado['erros'] += 1
                    continue
                
                # Itens
                itens = itens_por_chave.get(chave, [])
                
                # Criar nota
                with transaction.atomic():
                    nota_fiscal = NotaFiscal.objects.create(
                        contabilidade=contabilidade,
                        contrato=contrato,
                        parceiro_pj=parceiro if hasattr(parceiro, 'cnpj') else None,
                        parceiro_pf=parceiro if hasattr(parceiro, 'cpf') else None,
                        tipo_nota=tipo_nota,
                        chave_acesso=chave,
                        numero_documento=numero,
                        serie=serie,
                        data_emissao=data_emissao,
                        data_entrada_saida=data_movimento,
                        situacao=situacao,
                        valor_total=valor_total,
                        id_legado_empresa=cod_empresa,
                        id_legado_nota=f"{cod_empresa}-{numero}",
                        id_legado_cli_for=cod_parceiro
                    )
                    
                    resultado['criadas'] += 1
                    
                    # Criar itens
                    itens_obj = []
                    for seq, item in enumerate(itens, 1):
                        itens_obj.append(NotaFiscalItem(
                            nota_fiscal=nota_fiscal,
                            sequencial_item=seq,
                            tipo_item='PRODUTO' if tipo_nota in ['ENTRADA', 'SAIDA'] else 'SERVICO',
                            descricao=str(item[1] or ''),
                            cfop=str(item[2] or ''),
                            ncm=str(item[3] or ''),
                            quantidade=Decimal(str(item[4] or 0)),
                            valor_unitario=Decimal(str(item[5] or 0)),
                            valor_total=Decimal(str(item[6] or 0)),
                            valor_desconto=Decimal(str(item[7] or 0)),
                            valor_frete=Decimal(str(item[8] or 0)),
                            valor_desp_aces=Decimal(str(item[9] or 0))
                        ))
                    
                    if itens_obj:
                        NotaFiscalItem.objects.bulk_create(itens_obj)
                        resultado['itens'] += len(itens_obj)
                
            except Exception as e:
                resultado['erros'] += 1
        
        return resultado

    def handle(self, *args, **options):
        """
        Método principal
        """
        self.stats['tempo_inicio'] = time.time()
        
        self.stdout.write("\n" + "="*80)
        self.stdout.write("📋 FASE 1: PREPARAÇÃO")
        self.stdout.write("="*80)
        
        # Mapa histórico
        self.stdout.write("🔍 Construindo mapa de contabilidades...")
        historical_map = self.build_historical_contabilidade_map()
        self.stdout.write(f"✅ {len(historical_map):,} empresas mapeadas")
        
        if not historical_map:
            self.stdout.write(self.style.ERROR("❌ Nenhuma empresa mapeada"))
            return
        
        # Conexão Sybase
        self.stdout.write("\n🔌 Conectando ao Sybase...")
        connection = self.get_sybase_connection()
        if not connection:
            self.stdout.write(self.style.ERROR("❌ Falha na conexão"))
            return
        self.stdout.write("✅ Conectado")
        
        # Configuração de queries
        queries_config = {
            'ENTRADA': {
                'cabecalho': """
                    SELECT DISTINCT
                        EFENTRADAS.CHAVE_NFE_ENT as CHAVE_NF,
                        GEEMPRE.CGCE_EMP AS CNPJ_EMITENTE,
                        EFFORNECE.CGCE_FOR AS CPF_CNPJ_DEST,
                        EFENTRADAS.DENT_ENT as DATA_EMISSAO,
                        EFENTRADAS.NUME_ENT as NUM_DOC,
                        EFENTRADAS.SERI_ENT as SERIE,
                        EFENTRADAS.DATA_ENTRADA as DATA_MOV,
                        EFENTRADAS.SITUACAO_ENT as SITUACAO,
                        EFENTRADAS.VCON_ENT as VALOR_TOTAL,
                        EFENTRADAS.CODI_EMP as COD_EMP,
                        EFENTRADAS.CODI_FOR as COD_PARC,
                        EFFORNECE.NOME_FOR as NOME_PARC
                    FROM BETHADBA.EFENTRADAS
                    INNER JOIN BETHADBA.EFFORNECE ON EFENTRADAS.CODI_FOR = EFFORNECE.CODI_FOR
                    LEFT JOIN BETHADBA.GEEMPRE ON EFENTRADAS.CODI_EMP = GEEMPRE.CODI_EMP
                    WHERE EFENTRADAS.DENT_ENT >= '{data_inicio}'
                    AND EFENTRADAS.DENT_ENT <= '{data_fim}'
                    AND EFENTRADAS.CHAVE_NFE_ENT IS NOT NULL
                    AND EFENTRADAS.CHAVE_NFE_ENT <> ''
                    ORDER BY EFENTRADAS.DENT_ENT
                """,
                'itens': """
                    SELECT
                        EFENTRADAS.CHAVE_NFE_ENT as CHAVE_NF,
                        UPPER(EFPRODUTOS.DESC_PDI) as DESCRICAO,
                        EFMVEPRO.CFOP_MEP as CFOP,
                        EFPRODUTOS.CNCM_PDI as NCM,
                        EFMVEPRO.QTDE_MEP as QTDE,
                        EFMVEPRO.VALOR_UNIT_MEP as VLR_UNIT,
                        EFMVEPRO.VPRO_MEP as VLR_TOTAL,
                        EFMVEPRO.VDES_MEP as VLR_DESC,
                        EFMVEPRO.VFRE_MEP as VLR_FRETE,
                        EFMVEPRO.VDESACE_MEP as VLR_DESP
                    FROM BETHADBA.EFMVEPRO
                    INNER JOIN BETHADBA.EFENTRADAS ON EFMVEPRO.CODI_ENT = EFENTRADAS.CODI_ENT
                    INNER JOIN BETHADBA.EFPRODUTOS ON EFMVEPRO.CODI_PDI = EFPRODUTOS.CODI_PDI
                    WHERE EFENTRADAS.CHAVE_NFE_ENT IN ({chaves})
                """
            },
            'SAIDA': {
                'cabecalho': """
                    SELECT DISTINCT
                        EFSAIDAS.CHAVE_NFE_SAI as CHAVE_NF,
                        GEEMPRE.CGCE_EMP AS CNPJ_EMITENTE,
                        EFCLIENTES.CGCE_CLI AS CPF_CNPJ_DEST,
                        EFSAIDAS.DSAI_SAI as DATA_EMISSAO,
                        EFSAIDAS.NUME_SAI as NUM_DOC,
                        EFSAIDAS.SERI_SAI as SERIE,
                        EFSAIDAS.DATA_SAIDA as DATA_MOV,
                        EFSAIDAS.SITUACAO_SAI as SITUACAO,
                        EFSAIDAS.VCON_SAI as VALOR_TOTAL,
                        EFSAIDAS.CODI_EMP as COD_EMP,
                        EFSAIDAS.CODI_CLI as COD_PARC,
                        EFCLIENTES.NOME_CLI as NOME_PARC
                    FROM BETHADBA.EFSAIDAS
                    INNER JOIN BETHADBA.EFCLIENTES ON EFSAIDAS.CODI_CLI = EFCLIENTES.CODI_CLI
                    LEFT JOIN BETHADBA.GEEMPRE ON EFSAIDAS.CODI_EMP = GEEMPRE.CODI_EMP
                    WHERE EFSAIDAS.DSAI_SAI >= '{data_inicio}'
                    AND EFSAIDAS.DSAI_SAI <= '{data_fim}'
                    AND EFSAIDAS.CHAVE_NFE_SAI IS NOT NULL
                    AND EFSAIDAS.CHAVE_NFE_SAI <> ''
                    ORDER BY EFSAIDAS.DSAI_SAI
                """,
                'itens': """
                    SELECT
                        EFSAIDAS.CHAVE_NFE_SAI as CHAVE_NF,
                        UPPER(EFPRODUTOS.DESC_PDI) as DESCRICAO,
                        EFMVSPRO.CFOP_MSP as CFOP,
                        EFPRODUTOS.CNCM_PDI as NCM,
                        EFMVSPRO.QTDE_MSP as QTDE,
                        EFMVSPRO.VALOR_UNIT_MSP as VLR_UNIT,
                        EFMVSPRO.VPRO_MSP as VLR_TOTAL,
                        EFMVSPRO.VDES_MSP as VLR_DESC,
                        EFMVSPRO.VFRE_MSP as VLR_FRETE,
                        EFMVSPRO.VDESACE_MSP as VLR_DESP
                    FROM BETHADBA.EFMVSPRO
                    INNER JOIN BETHADBA.EFSAIDAS ON EFMVSPRO.CODI_SAI = EFSAIDAS.CODI_SAI
                    INNER JOIN BETHADBA.EFPRODUTOS ON EFMVSPRO.CODI_PDI = EFPRODUTOS.CODI_PDI
                    WHERE EFSAIDAS.CHAVE_NFE_SAI IN ({chaves})
                """
            },
            'SERVICO': {
                'cabecalho': """
                    SELECT DISTINCT
                        EFSERVICOS.CHAVE_ELETRONICA as CHAVE_NF,
                        GEEMPRE.CGCE_EMP AS CNPJ_EMITENTE,
                        EFCLIENTES.CGCE_CLI AS CPF_CNPJ_DEST,
                        EFSERVICOS.DSER_SER as DATA_EMISSAO,
                        EFSERVICOS.NUME_SER as NUM_DOC,
                        EFSERVICOS.SERI_SER as SERIE,
                        EFSERVICOS.DDOC_SER as DATA_MOV,
                        EFSERVICOS.SITUACAO_SER as SITUACAO,
                        EFSERVICOS.VCON_SER as VALOR_TOTAL,
                        EFSERVICOS.CODI_EMP as COD_EMP,
                        EFSERVICOS.CODI_CLI as COD_PARC,
                        EFCLIENTES.NOME_CLI as NOME_PARC
                    FROM BETHADBA.EFSERVICOS
                    INNER JOIN BETHADBA.EFCLIENTES ON EFSERVICOS.CODI_CLI = EFCLIENTES.CODI_CLI
                    LEFT JOIN BETHADBA.GEEMPRE ON EFSERVICOS.CODI_EMP = GEEMPRE.CODI_EMP
                    WHERE EFSERVICOS.DSER_SER >= '{data_inicio}'
                    AND EFSERVICOS.DSER_SER <= '{data_fim}'
                    AND EFSERVICOS.CHAVE_ELETRONICA IS NOT NULL
                    AND EFSERVICOS.CHAVE_ELETRONICA <> ''
                    ORDER BY EFSERVICOS.DSER_SER
                """,
                'itens': """
                    SELECT
                        EFSERVICOS.CHAVE_ELETRONICA as CHAVE_NF,
                        UPPER(EFSERVICOS.ATEX_SER) as DESCRICAO,
                        EFSERVICOS.CFPS_SER as CFOP,
                        '' as NCM,
                        1 as QTDE,
                        EFSERVICOS.VCON_SER as VLR_UNIT,
                        EFSERVICOS.VCON_SER as VLR_TOTAL,
                        0 as VLR_DESC,
                        0 as VLR_FRETE,
                        0 as VLR_DESP
                    FROM BETHADBA.EFSERVICOS
                    WHERE EFSERVICOS.CHAVE_ELETRONICA IN ({chaves})
                """
            }
        }
        
        # Processar
        self.stdout.write("\n" + "="*80)
        self.stdout.write("📋 FASE 2: PROCESSAMENTO")
        self.stdout.write("="*80)
        
        self.processar_tipo_nota(connection, historical_map, 'ENTRADA', queries_config['ENTRADA'])
        self.processar_tipo_nota(connection, historical_map, 'SAIDA', queries_config['SAIDA'])
        self.processar_tipo_nota(connection, historical_map, 'SERVICO', queries_config['SERVICO'])
        
        # Resumo
        self.stats['tempo_fim'] = time.time()
        tempo_total = self.stats['tempo_fim'] - self.stats['tempo_inicio']
        
        self.stdout.write("\n" + "="*80)
        self.stdout.write("📊 RESUMO FINAL")
        self.stdout.write("="*80)
        self.stdout.write(f"📋 Cabeçalhos lidos: {self.stats['total_cabecalhos_lidos']:,}")
        self.stdout.write(f"✅ Cabeçalhos válidos: {self.stats['total_cabecalhos_validos']:,}")
        self.stdout.write(f"⏭️  Sem contabilidade: {self.stats['sem_contabilidade']:,}")
        self.stdout.write(f"\n📦 Notas criadas: {self.stats['notas_criadas']:,}")
        self.stdout.write(f"⏭️  Notas puladas: {self.stats['notas_puladas']:,}")
        self.stdout.write(f"📋 Itens criados: {self.stats['itens_criados']:,}")
        self.stdout.write(f"\n🏢 Empresas: {len(self.stats['empresas_processadas']):,}")
        self.stdout.write(f"❌ Erros: {self.stats['erros']}")
        self.stdout.write(f"⏱️  Tempo: {tempo_total/60:.1f} min")
        self.stdout.write("="*80)
        
        if self.stats['notas_criadas'] > 0:
            self.stdout.write(self.style.SUCCESS("✅ ETL 07 CONCLUÍDA COM SUCESSO!"))
        else:
            self.stdout.write(self.style.WARNING("⚠️  ETL 07 CONCLUÍDA - NENHUMA NOTA IMPORTADA"))
        
        connection.close()
        self.stdout.write("🔌 Conexão encerrada\n")
