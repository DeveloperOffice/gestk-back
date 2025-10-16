from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from tqdm import tqdm
from datetime import datetime
from apps.importacao.management.commands._base import BaseETLCommand
from apps.pessoas.models import PessoaFisica, PessoaJuridica
from apps.fiscal.models import NotaFiscal, NotaFiscalItem


class Command(BaseETLCommand):
    help = 'ETL 17 OTIMIZADA: Importação de Cupons Fiscais (CFE e ECF) - Processamento em Lotes'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== ETL 17 OTIMIZADA: CUPONS FISCAIS ==='))
        self.stdout.write(self.style.WARNING('PROCESSAMENTO EM LOTES - ALTA PERFORMANCE'))
        
        # Construir mapa histórico de contabilidades
        self.stdout.write("\n[1/6] Construindo mapa histórico de contabilidades...")
        historical_map = self.build_historical_contabilidade_map()
        
        # Verificar mapeamento CNPJ -> Contrato -> Contabilidade
        self.stdout.write("\n[1.1/6] Verificando mapeamento CNPJ -> Contrato -> Contabilidade...")
        total_empresas_mapeadas = len(historical_map)
        self.stdout.write(f"  Empresas mapeadas: {total_empresas_mapeadas:,}")
        
        # Mostrar alguns exemplos de mapeamento para verificação
        exemplos = list(historical_map.items())[:3]
        for cnpj, contratos in exemplos:
            self.stdout.write(f"  CNPJ: {cnpj} -> {len(contratos)} contrato(s)")
            for data_inicio, data_termino, contab, contrato in contratos[:1]:
                self.stdout.write(f"    Contrato: {contrato.id} | Contabilidade: {contab.id} | Periodo: {data_inicio} a {data_termino}")
        
        # Conectar ao Sybase
        connection = self.get_sybase_connection()
        if not connection:
            return

        # Configurações de importação otimizada
        BATCH_SIZE = 1000  # Cupons por lote
        CUPONS_POR_QUERY = 5000  # Cupons por query do Sybase
        
        # PASSO 1: Buscar total de cupons para estimativa
        self.stdout.write("\n[2/6] Contando cupons disponíveis...")
        count_query = """
        SELECT COUNT(*)
        FROM BETHADBA.EFCUPOM_FISCAL_ELETRONICO ef
        INNER JOIN BETHADBA.GEEMPRE emp ON emp.codi_emp = ef.codi_emp
        WHERE ef.chave_cfe IS NOT NULL AND ef.chave_cfe != '' 
            AND ef.DATA_CFE >= '2019-01-01'
        """
        
        cursor = connection.cursor()
        cursor.execute(count_query)
        total_cupons = cursor.fetchone()[0]
        self.stdout.write(f"  Total de cupons encontrados: {total_cupons:,}")
        
        # PASSO 2: Carregar TODAS as chaves existentes em memória (OTIMIZAÇÃO CRÍTICA)
        self.stdout.write("\n[3/6] Carregando chaves de cupons já importados...")
        chaves_existentes = set(
            NotaFiscal.objects.values_list('chave_acesso', flat=True)
        )
        self.stdout.write(f"  Chaves existentes carregadas: {len(chaves_existentes):,}")
        
        # Criar pessoa genérica UMA VEZ (otimização)
        pessoa, created = PessoaFisica.objects.get_or_create(
            cpf='00000000000',
            defaults={'nome': 'CLIENTE CUPOM FISCAL'}
        )
        
        # Estatísticas
        total_notas_criadas = 0
        total_notas_puladas = 0
        total_itens_criados = 0
        total_sem_contabilidade = 0
        total_erros = 0
        cupons_processados = 0
        
        # PASSO 3: Processar cupons em lotes
        self.stdout.write(f"\n[4/6] Processando cupons em lotes de {BATCH_SIZE:,}...")
        
        # Query para buscar cupons em lotes
        query_cupons_lote = f"""
        SELECT 
            emp.nome_emp,  
            emp.cgce_emp,
            ef.codi_emp, 
            ef.I_CFE,
            ef.chave_cfe,
            ef.DATA_CFE
        FROM BETHADBA.EFCUPOM_FISCAL_ELETRONICO ef
        INNER JOIN BETHADBA.GEEMPRE emp ON emp.codi_emp = ef.codi_emp
        WHERE ef.chave_cfe IS NOT NULL AND ef.chave_cfe != '' 
            AND ef.DATA_CFE >= '2019-01-01'
        ORDER BY ef.codi_emp, ef.I_CFE
        """
        
        cursor.execute(query_cupons_lote)
        
        # Processar em lotes
        lote_cupons = []
        lote_numero = 0
        
        with tqdm(total=total_cupons, desc="Processando cupons", unit="cupons") as pbar:
            while True:
                # Buscar próximo lote de cupons
                cupons_batch = cursor.fetchmany(BATCH_SIZE)
                if not cupons_batch:
                    break
                
                lote_numero += 1
                lote_cupons = [dict(zip([column[0] for column in cursor.description], row)) for row in cupons_batch]
                
                # Processar lote
                resultado_lote = self.processar_lote_cupons(
                    lote_cupons, historical_map, chaves_existentes, pessoa, connection
                )
                
                # Atualizar estatísticas
                total_notas_criadas += resultado_lote['notas_criadas']
                total_notas_puladas += resultado_lote['notas_puladas']
                total_itens_criados += resultado_lote['itens_criados']
                total_sem_contabilidade += resultado_lote['sem_contabilidade']
                total_erros += resultado_lote['erros']
                cupons_processados += len(lote_cupons)
                
                # Atualizar progresso
                pbar.update(len(lote_cupons))
                
                # Mostrar estatísticas do lote
                if lote_numero % 10 == 0:  # A cada 10 lotes
                    self.stdout.write(f"\n  Lote {lote_numero}: {resultado_lote['notas_criadas']} criadas, {resultado_lote['notas_puladas']} puladas")
                    self.stdout.write(f"  Velocidade atual: {pbar.format_dict['rate']:.0f} cupons/seg")
        
        # Fechar conexão
        connection.close()
        
        # Resumo final
        self.stdout.write(self.style.SUCCESS(f"\n[5/6] RESUMO FINAL:"))
        self.stdout.write(f"  Cupons processados: {cupons_processados:,}")
        self.stdout.write(f"  Notas fiscais criadas: {total_notas_criadas:,}")
        self.stdout.write(f"  Notas fiscais puladas (ja existiam): {total_notas_puladas:,}")
        self.stdout.write(f"  Itens criados: {total_itens_criados:,}")
        self.stdout.write(f"  Sem contabilidade: {total_sem_contabilidade:,}")
        self.stdout.write(f"  Erros: {total_erros:,}")
        
        # Calcular estatísticas de performance
        if cupons_processados > 0:
            taxa_puladas = (total_notas_puladas / cupons_processados) * 100
            self.stdout.write(f"  Taxa de cupons ja importados: {taxa_puladas:.1f}%")
        
        self.stdout.write(self.style.SUCCESS("\n=== ETL 17 OTIMIZADA CONCLUIDA ==="))

    def processar_lote_cupons(self, lote_cupons, historical_map, chaves_existentes, pessoa, connection):
        """Processa um lote de cupons de forma otimizada"""
        
        resultado = {
            'notas_criadas': 0,
            'notas_puladas': 0,
            'itens_criados': 0,
            'sem_contabilidade': 0,
            'erros': 0
        }
        
        # Filtrar cupons que já existem (otimização em memória)
        cupons_novos = []
        for cupom in lote_cupons:
            if cupom['chave_cfe'] in chaves_existentes:
                resultado['notas_puladas'] += 1
            else:
                cupons_novos.append(cupom)
        
        if not cupons_novos:
            return resultado
        
        # Buscar TODOS os itens dos cupons do lote em uma única query
        cupom_ids = [(c['codi_emp'], c['I_CFE']) for c in cupons_novos]
        itens_por_cupom = self.buscar_itens_lote(connection, cupom_ids)
        
        # Processar cada cupom do lote
        for cupom in cupons_novos:
            try:
                # Aplicar Regra de Ouro: identificar contabilidade pelo CNPJ da empresa emitente
                cgce_empresa = cupom['cgce_emp']
                documento_limpo = self.limpar_documento(cgce_empresa)
                
                if not documento_limpo:
                    resultado['sem_contabilidade'] += 1
                    continue
                
                # Buscar contabilidade no mapa histórico
                contratos_empresa = historical_map.get(documento_limpo)
                if not contratos_empresa:
                    resultado['sem_contabilidade'] += 1
                    continue
                
                # Encontrar a contabilidade correta para a data do cupom
                data_cupom = cupom['DATA_CFE']
                if not data_cupom:
                    resultado['sem_contabilidade'] += 1
                    continue
                
                # Buscar contabilidade diretamente no mapa
                contabilidade = None
                for data_inicio, data_termino, contab, contrato in contratos_empresa:
                    if data_inicio and data_termino and data_inicio <= data_cupom <= data_termino:
                        contabilidade = contab
                        break
                
                if not contabilidade:
                    resultado['sem_contabilidade'] += 1
                    continue
                
                # Buscar itens do cupom na memória
                chave_cupom = (cupom['codi_emp'], cupom['I_CFE'])
                itens_cupom = itens_por_cupom.get(chave_cupom, [])
                
                # Calcular valor total do cupom
                valor_total_cupom = Decimal('0.00')
                for item in itens_cupom:
                    valor_item = Decimal(str(item['VALOR_PRODUTO'] or 0))
                    valor_total_cupom += valor_item
                
                # Criar NotaFiscal e itens
                with transaction.atomic():
                    nota_fiscal = NotaFiscal.objects.create(
                        contabilidade=contabilidade,
                        chave_acesso=cupom['chave_cfe'],
                        numero_documento=str(cupom['I_CFE']),
                        serie='CFE',
                        data_emissao=cupom['DATA_CFE'],
                        data_entrada_saida=cupom['DATA_CFE'],
                        situacao='AUTORIZADA',
                        tipo_nota='SAIDA',
                        valor_total=valor_total_cupom,
                        parceiro_pf=pessoa,
                        id_legado_nota=f"{cupom['codi_emp']}-{cupom['I_CFE']}",
                        id_legado_empresa=str(cupom['codi_emp']),
                        id_legado_cli_for=str(cupom['I_CFE']),
                    )
                    
                    resultado['notas_criadas'] += 1
                    
                    # Criar itens do cupom
                    for i, item in enumerate(itens_cupom, 1):
                        NotaFiscalItem.objects.create(
                            nota_fiscal=nota_fiscal,
                            sequencial_item=i,
                            tipo_item='PRODUTO',
                            descricao=item['desc_pdi'] or '',
                            cfop='5102',
                            ncm=str(item['cncm_pdi'] or ''),
                            quantidade=Decimal(str(item['quantidade'] or 0)),
                            valor_unitario=Decimal(str(item['valor_unitario'] or 0)),
                            valor_total=Decimal(str(item['VALOR_PRODUTO'] or 0)),
                        )
                        resultado['itens_criados'] += 1
                    
                    # Adicionar chave ao cache em memória para próximos lotes
                    chaves_existentes.add(cupom['chave_cfe'])
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao processar cupom {cupom.get('chave_cfe', 'N/A')}: {e}"))
                resultado['erros'] += 1
                continue
        
        return resultado

    def buscar_itens_lote(self, connection, cupom_ids):
        """Busca todos os itens de um lote de cupons em uma única query"""
        
        if not cupom_ids:
            return {}
        
        # Construir query com OR conditions para compatibilidade com Sybase
        conditions = []
        params = []
        
        for codi_emp, i_cfe in cupom_ids:
            conditions.append("(efe.codi_emp = ? AND efe.I_CFE = ?)")
            params.extend([codi_emp, i_cfe])
        
        where_clause = " OR ".join(conditions)
        
        query_itens_lote = f"""
        SELECT 
            efe.codi_emp,
            efe.I_CFE,
            pd.codi_pdi,
            pd.desc_pdi,
            pd.cncm_pdi,
            efe.quantidade,
            efe.valor_unitario,
            efe.VALOR_PRODUTO
        FROM BETHADBA.EFCUPOM_FISCAL_ELETRONICO_ESTOQUE efe
        INNER JOIN BETHADBA.EFPRODUTOS pd ON pd.codi_emp = efe.codi_emp AND pd.codi_pdi = efe.codi_pdi
        WHERE {where_clause}
        ORDER BY efe.codi_emp, efe.I_CFE, efe.codi_pdi
        """
        
        cursor = connection.cursor()
        cursor.execute(query_itens_lote, params)
        
        # Agrupar itens por cupom
        itens_por_cupom = {}
        columns = [column[0] for column in cursor.description]
        
        for row in cursor.fetchall():
            item = dict(zip(columns, row))
            chave_cupom = (item['codi_emp'], item['I_CFE'])
            
            if chave_cupom not in itens_por_cupom:
                itens_por_cupom[chave_cupom] = []
            
            itens_por_cupom[chave_cupom].append(item)
        
        return itens_por_cupom
