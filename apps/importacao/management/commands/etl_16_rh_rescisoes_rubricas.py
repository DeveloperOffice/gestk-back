from django.db import transaction
from tqdm import tqdm
from ._base import BaseETLCommand
from apps.funcionarios.models import Rescisao, Rubrica, RescisaoRubrica
from decimal import Decimal

class Command(BaseETLCommand):
    help = 'ETL para importar Rubricas de Rescisão seguindo a Regra de Ouro'

    def add_arguments(self, parser):
        parser.add_argument(
            '--teste',
            action='store_true',
            help='Executa apenas um teste com 10 rescisões'
        )

    def handle(self, *args, **options):
        modo_teste = options['teste']
        
        self.stdout.write(self.style.SUCCESS('--- Iniciando ETL de Rubricas de Rescisão ---'))
        if modo_teste:
            self.stdout.write(self.style.WARNING('🧪 MODO TESTE ATIVADO - Apenas 10 rescisões'))
        self.stdout.flush()
        
        connection = self.get_sybase_connection()
        if not connection: return

        try:
            self.stdout.write(self.style.HTTP_INFO('\n[1/4] Construindo mapas de referência...'))
            self.stdout.flush()
            rescisoes_map = self.build_rescisoes_map()
            rubricas_map = self.build_rubricas_map()
            self.stdout.write(self.style.SUCCESS("✓ Mapas construídos."))
            self.stdout.flush()

            self.stdout.write(self.style.HTTP_INFO('\n[2/4] Extraindo rubricas das rescisões...'))
            self.stdout.flush()
            rubricas_data = self.extract_rubricas_corretas(connection, modo_teste)
            if not rubricas_data:
                self.stdout.write(self.style.WARNING('Nenhuma rubrica de rescisão encontrada.'))
                self.stdout.flush()
                return
            self.stdout.write(self.style.SUCCESS(f"✓ {len(rubricas_data):,} registros de rubricas extraídos."))
            self.stdout.flush()
            
            self.stdout.write(self.style.HTTP_INFO('\n[3/4] Processando e carregando dados...'))
            self.stdout.flush()
            stats = self.processar_dados_corretos(rubricas_data, rescisoes_map, rubricas_map)

        finally:
            connection.close()
        
        self.stdout.write(self.style.SUCCESS('\n--- Resumo do ETL ---'))
        self.stdout.write(f"  - Rubricas Criadas: {stats['criados']}")
        self.stdout.write(f"  - Rubricas Atualizadas: {stats['atualizados']}")
        self.stdout.write(f"  - Sem Contabilidade: {stats['sem_contabilidade']}")
        self.stdout.write(f"  - Sem Rescisão: {stats['sem_rescisao']}")
        self.stdout.write(f"  - Sem Rubrica: {stats['sem_rubrica']}")
        self.stdout.write(f"  - Erros: {stats['erros']}")
        self.stdout.write(self.style.SUCCESS('--- ETL Finalizado ---'))
        self.stdout.flush()

    def build_rescisoes_map(self):
        self.stdout.write("  - Carregando mapa de rescisões...", ending='\r')
        self.stdout.flush()
        rescisoes_map = {r.id_legado: r for r in Rescisao.objects.all()}
        self.stdout.write(self.style.SUCCESS(f"  - Mapa de rescisões: {len(rescisoes_map)} registros"))
        self.stdout.flush()
        return rescisoes_map

    def build_rubricas_map(self):
        self.stdout.write("  - Carregando mapa de rubricas...", ending='\r')
        self.stdout.flush()
        rubricas_map = {}
        for r in Rubrica.objects.select_related('contabilidade'):
            rubricas_map[(r.contabilidade.id, r.id_legado)] = r
        self.stdout.write(self.style.SUCCESS(f"  - Mapa de rubricas: {len(rubricas_map)} registros"))
        self.stdout.flush()
        return rubricas_map

    def extract_rubricas_corretas(self, connection, modo_teste):
        """
        Query CORRETA seguindo a Regra de Ouro:
        
        ESTRATÉGIA:
        1. Usar FORESCISOES como base (rescisões específicas)
        2. JOIN com GEEMPRE para obter cgce_emp (CNPJ/CPF)
        3. JOIN com FOMOVTOSERV para pegar movimentos financeiros
        4. JOIN com FOEVENTOS para pegar tipos de rubricas
        5. Filtrar apenas movimentos de rescisão (TIPO_PROCES = 11)
        6. Criar ID_LEGADO composto: codi_emp-i_empregados
        """
        limit_clause = "TOP 10" if modo_teste else ""  # Remover limite em produção
        
        query = f"""
        SELECT {limit_clause}
            fs.i_calculos,
            m.i_eventos,
            e.nome as descricao_rubrica,
            e.prov_desc as tipo_rubrica,
            SUM(m.valor_cal) as valor_total,
            fs.codi_emp,
            fs.i_empregados,
            fs.demissao,
            ge.cgce_emp,
            -- Criar ID_LEGADO composto para correspondência (com RTRIM para remover espaços)
            RTRIM(CAST(fs.codi_emp AS VARCHAR)) + '-' + RTRIM(CAST(fs.i_empregados AS VARCHAR)) as id_legado_composto
        FROM bethadba.FORESCISOES fs
        INNER JOIN bethadba.GEEMPRE ge ON ge.codi_emp = fs.codi_emp
        INNER JOIN bethadba.FOMOVTOSERV m ON 
            m.codi_emp = fs.codi_emp AND 
            m.i_empregados = fs.i_empregados AND
            m.i_calculos = fs.i_calculos AND
            m.TIPO_PROCES = 11
        INNER JOIN bethadba.FOEVENTOS e ON m.i_eventos = e.i_eventos
        WHERE fs.demissao >= '2019-01-01'
            AND m.valor_cal != 0
        GROUP BY fs.i_calculos, m.i_eventos, e.nome, e.prov_desc, 
                 fs.codi_emp, fs.i_empregados, fs.demissao, ge.cgce_emp
        HAVING SUM(m.valor_cal) != 0
        ORDER BY fs.i_calculos, m.i_eventos
        """
        return self.execute_query(connection, query)

    def processar_dados_corretos(self, data, rescisoes_map, rubricas_map):
        """Processamento simplificado: Rescisão já tem contabilidade."""
        stats = {
            'criados': 0,
            'atualizados': 0,
            'erros': 0,
            'sem_rescisao': 0,
            'sem_rubrica': 0,
            'sem_contabilidade': 0
        }
        
        # Controle de duplicatas
        rubricas_processadas = set()
        
        for row in tqdm(data, desc="Processando Rubricas"):
            try:
                # 1. Buscar rescisão pelo id_legado_composto da query
                id_legado_composto = row['id_legado_composto']
                rescisao = rescisoes_map.get(id_legado_composto)
                
                if not rescisao:
                    stats['sem_rescisao'] += 1
                    continue
                
                # 2. A contabilidade vem da rescisão!
                contabilidade = rescisao.contabilidade
                
                # 3. Verificar duplicata usando id_legado + i_eventos
                chave_rubrica = f"{id_legado_composto}_{row['i_eventos']}_{row['tipo_rubrica']}"
                if chave_rubrica in rubricas_processadas:
                    continue
                
                rubricas_processadas.add(chave_rubrica)
                
                # 4. Buscar rubrica correspondente
                id_legado_rubrica = str(row['i_eventos'])
                rubrica_key = (contabilidade.id, id_legado_rubrica)
                rubrica = rubricas_map.get(rubrica_key)
                if not rubrica:
                    stats['sem_rubrica'] += 1
                    continue
                
                # 7. Validar valor
                try:
                    valor = Decimal(str(row['valor_total'] or 0))
                    if valor <= 0:
                        continue
                except (ValueError, TypeError):
                    stats['erros'] += 1
                    continue
                
                # 8. Criar/atualizar RescisaoRubrica usando CNPJ/CPF + contabilidade_id
                tipo_rubrica = str(row['tipo_rubrica'])[:1] if row['tipo_rubrica'] else 'P'  # Pegar apenas 1º caractere
                
                with transaction.atomic():
                    rr, created = RescisaoRubrica.objects.update_or_create(
                        rescisao=rescisao,
                        rubrica=rubrica,
                        tipo=tipo_rubrica,
                        descricao=row['descricao_rubrica'],
                        defaults={'valor': valor}
                    )

                    if created:
                        stats['criados'] += 1
                    else:
                        stats['atualizados'] += 1
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao processar rubrica: {e}"))
                stats['erros'] += 1
        
        return stats
