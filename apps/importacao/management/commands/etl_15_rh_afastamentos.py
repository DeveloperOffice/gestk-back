from django.db import transaction
from tqdm import tqdm
from ._base import BaseETLCommand
from apps.funcionarios.models import VinculoEmpregaticio, Afastamento
from decimal import Decimal

class Command(BaseETLCommand):
    help = 'ETL para importar Afastamentos seguindo a Regra de Ouro'

    def add_arguments(self, parser):
        parser.add_argument(
            '--teste',
            action='store_true',
            help='Executa apenas um teste com 100 registros'
        )

    def handle(self, *args, **options):
        modo_teste = options['teste']
        
        self.stdout.write(self.style.SUCCESS('--- Iniciando ETL de Afastamentos ---'))
        if modo_teste:
            self.stdout.write(self.style.WARNING('🧪 MODO TESTE ATIVADO - Apenas 100 registros'))
        self.stdout.flush()
        
        connection = self.get_sybase_connection()
        if not connection: return

        try:
            self.stdout.write(self.style.HTTP_INFO('\n[1/4] Construindo mapas de referência...'))
            self.stdout.flush()
            historical_map = self.build_historical_contabilidade_map()
            vinculos_map = self.build_vinculos_map()
            self.stdout.write(self.style.SUCCESS("✓ Mapas construídos."))
            self.stdout.flush()

            self.stdout.write(self.style.HTTP_INFO('\n[2/4] Extraindo afastamentos...'))
            self.stdout.flush()
            afastamentos_data = self.extract_afastamentos(connection, modo_teste)
            if not afastamentos_data:
                self.stdout.write(self.style.WARNING('Nenhum afastamento encontrado.'))
                self.stdout.flush()
                return
            self.stdout.write(self.style.SUCCESS(f"✓ {len(afastamentos_data):,} registros de afastamentos extraídos."))
            self.stdout.flush()
            
            self.stdout.write(self.style.HTTP_INFO('\n[3/4] Processando e carregando dados...'))
            self.stdout.flush()
            stats = self.processar_dados(afastamentos_data, historical_map, vinculos_map)

        finally:
            connection.close()
        
        self.stdout.write(self.style.SUCCESS('\n--- Resumo do ETL ---'))
        self.stdout.write(f"  - Afastamentos Criados: {stats['criados']}")
        self.stdout.write(f"  - Afastamentos Atualizados: {stats['atualizados']}")
        self.stdout.write(f"  - Sem Contabilidade: {stats['sem_contabilidade']}")
        self.stdout.write(f"  - Sem Vínculo: {stats['sem_vinculo']}")
        self.stdout.write(f"  - Erros: {stats['erros']}")
        self.stdout.write(self.style.SUCCESS('--- ETL Finalizado ---'))
        self.stdout.flush()

    def build_vinculos_map(self):
        """Constrói mapa de vínculos por matricula (NUMCARTPROF do Sybase)"""
        self.stdout.write("  - Carregando mapa de vínculos...", ending='\r')
        self.stdout.flush()
        vinculos_map = {}
        for v in VinculoEmpregaticio.objects.select_related('contabilidade').all():
            vinculos_map[(v.contabilidade.id, v.matricula)] = v
        self.stdout.write(self.style.SUCCESS(f"  - Mapa de vínculos: {len(vinculos_map)} registros"))
        self.stdout.flush()
        return vinculos_map

    def extract_afastamentos(self, connection, modo_teste):
        """
        Extrai afastamentos aplicando a REGRA DE OURO:
        - Busca CNPJ da empresa (cgce_emp)
        - Busca matrícula correta (matricula)
        - Valida data de afastamento
        """
        limit_clause = "TOP 100" if modo_teste else ""
        
        query = f"""
        SELECT {limit_clause}
            a.CODI_EMP,
            a.I_EMPREGADOS,
            a.I_AFASTAMENTOS,
            a.DATA_REAL as data_inicio,
            a.DATA_FIM as data_fim,
            a.DATA_FIM_TMP as previsao_fim,
            a.NUMERO_DIAS as dias_afastado,
            a.CODIGO_DOENCA,
            a.NOME_MEDICO,
            a.CRM_MEDICO,
            a.OBSERVACAO_LICENCA_SEM_VENCIMENTO as observacoes,
            ge.cgce_emp,
            e.matricula
        FROM bethadba.FOAFASTAMENTOS a
        INNER JOIN bethadba.GEEMPRE ge ON ge.codi_emp = a.codi_emp
        INNER JOIN bethadba.FOEMPREGADOS e ON e.codi_emp = a.codi_emp AND e.i_empregados = a.i_empregados
        WHERE a.DATA_REAL >= '2019-01-01'
        ORDER BY a.DATA_REAL, a.I_AFASTAMENTOS
        """
        return self.execute_query(connection, query)

    def processar_dados(self, data, historical_map, vinculos_map):
        """Processa afastamentos aplicando REGRA DE OURO"""
        stats = {
            'criados': 0,
            'atualizados': 0,
            'erros': 0,
            'sem_contabilidade': 0,
            'sem_vinculo': 0
        }
        
        for row in tqdm(data, desc="Processando Afastamentos"):
            try:
                # 1. Buscar contabilidade via CNPJ (REGRA DE OURO)
                doc_empregador = self.limpar_documento(row['cgce_emp'])
                contratos = historical_map.get(doc_empregador)
                
                if not contratos:
                    stats['sem_contabilidade'] += 1
                    continue
                
                # 2. Validar contrato na data de início do afastamento
                data_inicio = row['data_inicio']
                contabilidade = None
                
                for data_inicio_contrato, data_termino_contrato, contab, contrato in contratos:
                    if data_inicio_contrato and data_termino_contrato:
                        if data_inicio_contrato <= data_inicio <= data_termino_contrato:
                            contabilidade = contab
                            break
                
                if not contabilidade:
                    stats['sem_contabilidade'] += 1
                    continue
                
                # 3. Buscar vínculo por matricula
                matricula = str(row['matricula']).strip() if row['matricula'] else None
                if not matricula:
                    stats['sem_vinculo'] += 1
                    continue
                
                vinculo_key = (contabilidade.id, matricula)
                vinculo = vinculos_map.get(vinculo_key)
                
                if not vinculo:
                    stats['sem_vinculo'] += 1
                    continue

                # 4. Preparar dados
                defaults = {
                    'data_inicio': data_inicio,
                    'data_fim': row['data_fim'],
                    'previsao_fim': row['previsao_fim'],
                    'dias_afastado': int(row['dias_afastado']) if row['dias_afastado'] else 0,
                    'codigo_doenca': row['CODIGO_DOENCA'],
                    'nome_medico': row['NOME_MEDICO'],
                    'crm_medico': row['CRM_MEDICO'],
                    'observacoes': row['observacoes'],
                }

                # 5. Criar/atualizar afastamento
                with transaction.atomic():
                    obj, created = Afastamento.objects.update_or_create(
                        contabilidade=contabilidade,
                        vinculo=vinculo,
                        id_legado=str(row['I_AFASTAMENTOS']),
                        defaults=defaults
                    )
                    
                    if created:
                        stats['criados'] += 1
                    else:
                        stats['atualizados'] += 1
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao processar afastamento: {e}"))
                stats['erros'] += 1
        
        return stats
