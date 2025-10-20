import pyodbc
from decimal import Decimal
from django.db import transaction
from tqdm import tqdm
from ._base import BaseETLCommand
from apps.funcionarios.models import VinculoEmpregaticio, Rescisao

class Command(BaseETLCommand):
    help = 'ETL para importar os dados principais de Rescisões do Sybase.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Iniciando ETL de Rescisões ---'))
        
        connection = self.get_sybase_connection()
        if not connection: return

        try:
            self.stdout.write(self.style.HTTP_INFO('\n[1/3] Construindo mapas de referência...'))
            historical_map = self.build_historical_contabilidade_map()
            vinculos_map = self.build_vinculos_map()
            self.stdout.write(self.style.SUCCESS("✓ Mapas construídos."))

            self.stdout.write(self.style.HTTP_INFO('\n[2/3] Extraindo dados de Rescisões (desde 2019)...'))
            rescisoes_data = self.extract_rescisoes(connection)
            if not rescisoes_data:
                self.stdout.write(self.style.WARNING('Nenhum registro de rescisão encontrado.'))
                return
            self.stdout.write(self.style.SUCCESS(f"✓ {len(rescisoes_data):,} registros de rescisão extraídos."))

            self.stdout.write(self.style.HTTP_INFO('\n[3/3] Processando e carregando dados no Gestk...'))
            stats = self.processar_dados(rescisoes_data, historical_map, vinculos_map)

        finally:
            connection.close()
        
        self.stdout.write(self.style.SUCCESS('\n--- Resumo do ETL de Rescisões ---'))
        self.stdout.write(f"  - Rescisões Criadas: {stats['criados']}")
        self.stdout.write(f"  - Rescisões Atualizadas: {stats['atualizados']}")
        self.stdout.write(f"  - Registros sem contabilidade/contrato na data: {stats['sem_contabilidade']}")
        self.stdout.write(f"  - Registros sem vínculo correspondente: {stats['sem_vinculo']}")
        self.stdout.write(self.style.ERROR(f"  - Erros: {stats['erros']}"))
        self.stdout.write(self.style.SUCCESS('--- ETL de Rescisões Finalizado ---'))

    def build_vinculos_map(self):
        self.stdout.write("Construindo mapa de Vínculos Empregatícios...")
        vinculos_map = {}
        # A chave do mapa será (codi_emp_cliente, i_empregados)
        for v in VinculoEmpregaticio.objects.select_related('funcionario', 'contabilidade'):
            if v.funcionario and v.funcionario.id_legado:
                # O id_legado do funcionário é 'codi_emp-i_empregados'
                try:
                    codi_emp, i_empregados = v.funcionario.id_legado.split('-')
                    chave = (int(codi_emp), int(i_empregados))
                    vinculos_map[chave] = v
                except ValueError:
                    continue # Ignora IDs legados malformados
        self.stdout.write(f"✓ Mapa de Vínculos construído com {len(vinculos_map)} registros.")
        return vinculos_map

    def extract_rescisoes(self, connection):
        query = """
        SELECT
            fr.codi_emp, fr.i_empregados, fr.demissao, fr.motivo, fr.data_aviso, fr.aviso_indenizado,
            fr.salario, fr.proventos, fr.descontos, fr.data_pagto, fr.I_CALCULOS, ge.cgce_emp
        FROM bethadba.forescisoes fr
        JOIN bethadba.geempre ge ON fr.codi_emp = ge.codi_emp
        WHERE fr.demissao >= '2019-01-01'
        """
        return self.execute_query(connection, query)

    def processar_dados(self, data, historical_map, vinculos_map):
        stats = {'criados': 0, 'atualizados': 0, 'erros': 0, 'sem_vinculo': 0, 'sem_contabilidade': 0}

        for row in tqdm(data, desc="Processando Rescisões"):
            try:
                codi_emp = row['codi_emp']
                i_empregados = row['i_empregados']
                data_rescisao = row['demissao']
                doc_empregador = self.limpar_documento(row['cgce_emp'])

                # Buscar contabilidade via REGRA DE OURO
                contratos = historical_map.get(doc_empregador)
                if not contratos:
                    stats['sem_contabilidade'] += 1
                    continue
                
                # Buscar contrato válido na data ou usar o mais recente
                contabilidade = None
                for data_inicio, data_termino, contab, contrato in contratos:
                    if data_inicio and data_termino and data_inicio <= data_rescisao <= data_termino:
                        contabilidade = contab
                        break
                if not contabilidade:
                    contabilidade = contratos[0][2]
                
                if not contabilidade:
                    stats['sem_contabilidade'] += 1
                    continue

                # 2. Buscar o Vínculo usando a CHAVE CORRETA
                vinculo_key = (codi_emp, i_empregados)
                vinculo = vinculos_map.get(vinculo_key)
                if not vinculo:
                    stats['sem_vinculo'] += 1
                    continue
                
                # Criar ID_LEGADO composto: codi_emp-i_empregados (sem data por enquanto)
                id_legado_composto = f"{codi_emp}-{i_empregados}"
                
                defaults = {
                    'data_rescisao': data_rescisao,  # ✅ Campo obrigatório que estava faltando!
                    'motivo_codigo': row['motivo'],
                    'salario_base': Decimal(row['salario'] or 0),
                    'proventos': Decimal(row['proventos'] or 0),
                    'descontos': Decimal(row['descontos'] or 0),
                    'valor_liquido': (Decimal(row['proventos'] or 0) - Decimal(row['descontos'] or 0)),
                    'data_aviso': row['data_aviso'],
                    'aviso_indenizado': True if row['aviso_indenizado'] == 'S' else False,
                    'data_pagamento': row['data_pagto'],
                    'id_legado': id_legado_composto,
                    'status': 'homologada'  # Status default
                }

                rescisao, created = Rescisao.objects.update_or_create(
                    contabilidade=contabilidade,
                    vinculo=vinculo,
                    defaults=defaults
                )

                if created:
                    stats['criados'] += 1
                else:
                    stats['atualizados'] += 1
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao processar I_CALCULOS={row.get('I_CALCULOS')}: {e}"))
                stats['erros'] += 1
        
        return stats
