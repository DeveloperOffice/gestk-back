import re
from django.db import transaction
from tqdm import tqdm
from django.contrib.contenttypes.models import ContentType

from ._base import BaseETLCommand
from apps.core.models import Contabilidade
from apps.pessoas.models import PessoaJuridica, PessoaFisica, Contrato
from apps.funcionarios.models import Cargo

def batch_iterator(iterator, batch_size):
    """Gera lotes de um iterador."""
    batch = []
    for item in iterator:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch

class Command(BaseETLCommand):
    help = 'ETL para importar os Cargos de RH do Sybase.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Iniciando ETL de Cargos de RH ---'))

        # PASSO 1: Construir mapa histórico de CNPJ/CPF -> Contabilidade (REGRA DE OURO)
        self.stdout.write(self.style.HTTP_INFO('\n[1/3] Construindo mapa histórico de contabilidades (últimos 5 anos)...'))
        historical_map = self.build_historical_contabilidade_map()
        self.stdout.write(self.style.SUCCESS(f"✓ Mapa histórico construído com {len(historical_map):,} empresas únicas."))

        # PASSO 2: Extração de Dados do Sybase
        connection = self.get_sybase_connection()
        if not connection: return

        self.stdout.write(self.style.HTTP_INFO('\n[2/3] Extraindo dados de Cargos do Sybase...'))
        
        query = """
        SELECT c.codi_emp, c.i_cargos, c.nome, c.cbo_2002, c.situacao, e.cgce_emp
        FROM bethadba.focargos c
        JOIN bethadba.geempre e ON c.codi_emp = e.codi_emp
        """
        
        try:
            data = self.execute_query(connection, query)
        finally:
            connection.close()
        
        if not data:
            self.stdout.write(self.style.WARNING('Nenhum cargo encontrado no Sybase.'))
            return
            
        self.stdout.write(self.style.SUCCESS(f"✓ {len(data):,} registros de cargos extraídos."))

        # PASSO 3: Processamento e Carga
        self.stdout.write(self.style.HTTP_INFO('\n[3/3] Processando e carregando dados no Gestk...'))
        
        stats = {'criados': 0, 'atualizados': 0, 'erros': 0, 'sem_contabilidade': 0}
        batch_size = 1000

        for lote in tqdm(batch_iterator(data, batch_size), total=(len(data) + batch_size - 1) // batch_size, desc="Processando Lotes de Cargos"):
            with transaction.atomic():
                for row in lote:
                    try:
                        documento_empregador = self.limpar_documento(row['cgce_emp'])
                        
                        # Aplicar REGRA DE OURO: buscar contabilidade via mapa histórico
                        contratos = historical_map.get(documento_empregador)
                        if not contratos:
                            stats['sem_contabilidade'] += 1
                            continue
                        
                        # Pegar a contabilidade do contrato mais recente
                        contabilidade = contratos[0][2]  # (data_inicio, data_termino, contabilidade, contrato)
                        
                        defaults = {
                            'nome': row['nome'],
                            'cbo_2002': row['cbo_2002'],
                            'ativo': True if row['situacao'] == 'A' else False
                        }
                        
                        cargo, created = Cargo.objects.update_or_create(
                            contabilidade=contabilidade,
                            id_legado=str(row['i_cargos']),
                            defaults=defaults
                        )

                        if created:
                            stats['criados'] += 1
                        else:
                            stats['atualizados'] += 1
                    
                    except Exception as e:
                        self.log_error(f"Erro ao processar cargo com i_cargos={row.get('i_cargos')}: {e}")
                        stats['erros'] += 1

        self.stdout.write(self.style.SUCCESS('\n--- Resumo do ETL de Cargos ---'))
        self.stdout.write(f"  - Cargos Criados: {stats['criados']}")
        self.stdout.write(f"  - Cargos Atualizados: {stats['atualizados']}")
        self.stdout.write(f"  - Registros sem contabilidade mapeada: {stats['sem_contabilidade']}")
        self.stdout.write(self.style.ERROR(f"  - Erros: {stats['erros']}"))
        self.stdout.write(self.style.SUCCESS('--- ETL de Cargos de RH Finalizado ---'))


    
    def limpar_documento(self, documento):
        return re.sub(r'\D', '', str(documento or ''))

