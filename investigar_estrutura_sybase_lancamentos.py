import os
import django
import pyodbc
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

def investigar_estrutura_sybase_lancamentos():
    print("=== INVESTIGAÇÃO: ESTRUTURA DE LANÇAMENTOS NO SYBASE ===")
    
    try:
        # Conectar ao Sybase usando variáveis de ambiente
        connection_string = (
            f"DRIVER={{{os.getenv('SYBASE_DRIVER', 'SQL Anywhere 17')}}};"
            f"SERVER={os.getenv('SYBASE_SERVER')};"
            f"DATABASE={os.getenv('SYBASE_DATABASE')};"
            f"UID={os.getenv('SYBASE_UID')};"
            f"PWD={os.getenv('SYBASE_PWD')};"
        )
        
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            
            # 1. Verificar tabelas relacionadas a lançamentos
            print("\n--- TABELAS DE LANÇAMENTOS NO SYBASE ---")
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'bethadba' 
                AND table_name LIKE '%lanc%'
                ORDER BY table_name
            """)
            
            tabelas_lancamentos = cursor.fetchall()
            print(f"Tabelas encontradas: {len(tabelas_lancamentos)}")
            for tabela in tabelas_lancamentos:
                print(f"  - {tabela[0]}")
            
            # 2. Investigar estrutura da tabela principal de lançamentos
            print("\n--- ESTRUTURA DA TABELA PRINCIPAL ---")
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_schema = 'bethadba' 
                AND table_name = 'eflancamentos'
                ORDER BY ordinal_position
            """)
            
            colunas = cursor.fetchall()
            print(f"Colunas da tabela eflancamentos: {len(colunas)}")
            for coluna in colunas:
                print(f"  {coluna[0]} - {coluna[1]} - Nullable: {coluna[2]}")
            
            # 3. Verificar se há campo que identifica a contabilidade
            print("\n--- CAMPOS DE IDENTIFICAÇÃO ---")
            cursor.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_schema = 'bethadba' 
                AND table_name = 'eflancamentos'
                AND (column_name LIKE '%emp%' OR column_name LIKE '%cont%' OR column_name LIKE '%escrit%')
                ORDER BY column_name
            """)
            
            campos_id = cursor.fetchall()
            print(f"Campos de identificação: {len(campos_id)}")
            for campo in campos_id:
                print(f"  {campo[0]} - {campo[1]}")
            
            # 4. Verificar dados de exemplo
            print("\n--- DADOS DE EXEMPLO ---")
            cursor.execute("""
                SELECT TOP 5 *
                FROM bethadba.eflancamentos
                ORDER BY data_lancamento DESC
            """)
            
            colunas_nomes = [desc[0] for desc in cursor.description]
            dados_exemplo = cursor.fetchall()
            
            print(f"Colunas: {colunas_nomes}")
            print("Dados de exemplo:")
            for linha in dados_exemplo:
                print(f"  {dict(zip(colunas_nomes, linha))}")
            
            # 5. Verificar se há tabela de partidas (débito/crédito)
            print("\n--- TABELA DE PARTIDAS ---")
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'bethadba' 
                AND table_name LIKE '%part%'
                ORDER BY table_name
            """)
            
            tabelas_partidas = cursor.fetchall()
            print(f"Tabelas de partidas: {len(tabelas_partidas)}")
            for tabela in tabelas_partidas:
                print(f"  - {tabela[0]}")
            
            # 6. Verificar estrutura da tabela de partidas
            if tabelas_partidas:
                tabela_partidas = tabelas_partidas[0][0]
                print(f"\nEstrutura da tabela {tabela_partidas}:")
                cursor.execute(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_schema = 'bethadba' 
                    AND table_name = '{tabela_partidas}'
                    ORDER BY ordinal_position
                """)
                
                colunas_partidas = cursor.fetchall()
                for coluna in colunas_partidas:
                    print(f"  {coluna[0]} - {coluna[1]} - Nullable: {coluna[2]}")
            
            # 7. Verificar relacionamento entre lançamentos e empresas
            print("\n--- RELACIONAMENTO LANÇAMENTOS x EMPRESAS ---")
            cursor.execute("""
                SELECT 
                    l.codi_emp,
                    e.razao_emp,
                    e.cgce_emp,
                    COUNT(*) as total_lancamentos
                FROM bethadba.eflancamentos l
                INNER JOIN bethadba.geempre e ON l.codi_emp = e.codi_emp
                GROUP BY l.codi_emp, e.razao_emp, e.cgce_emp
                ORDER BY total_lancamentos DESC
                LIMIT 10
            """)
            
            relacoes = cursor.fetchall()
            print(f"Top 10 empresas com mais lançamentos:")
            for rel in relacoes:
                print(f"  {rel[0]} - {rel[1]} ({rel[2]}) - {rel[3]} lançamentos")
            
            # 8. Verificar se há lançamentos das próprias contabilidades
            print("\n--- VERIFICAÇÃO: LANÇAMENTOS DAS CONTABILIDADES ---")
            
            # Buscar CNPJs das contabilidades no GESTK
            from apps.core.models import Contabilidade
            contabilidades = Contabilidade.objects.all()
            
            for contab in contabilidades:
                if contab.cnpj and contab.cnpj != '00000000000100':  # Pular CNPJ de teste
                    print(f"\nVerificando {contab.razao_social} (CNPJ: {contab.cnpj})")
                    
                    # Buscar empresa no Sybase
                    cursor.execute(f"""
                        SELECT codi_emp, razao_emp, cgce_emp
                        FROM bethadba.geempre 
                        WHERE cgce_emp = '{contab.cnpj}'
                    """)
                    
                    empresa_sybase = cursor.fetchone()
                    if empresa_sybase:
                        codi_emp = empresa_sybase[0]
                        print(f"  Empresa encontrada no Sybase: {empresa_sybase[1]} (codi_emp: {codi_emp})")
                        
                        # Contar lançamentos desta empresa
                        cursor.execute(f"""
                            SELECT COUNT(*) as total_lancamentos
                            FROM bethadba.eflancamentos 
                            WHERE codi_emp = {codi_emp}
                        """)
                        
                        total_lanc = cursor.fetchone()[0]
                        print(f"  Total de lançamentos: {total_lanc}")
                        
                        if total_lanc > 0:
                            # Amostra de lançamentos
                            cursor.execute(f"""
                                SELECT TOP 3 data_lancamento, historico, valor_total
                                FROM bethadba.eflancamentos 
                                WHERE codi_emp = {codi_emp}
                                ORDER BY data_lancamento DESC
                            """)
                            
                            lancamentos_amostra = cursor.fetchall()
                            print(f"  Amostra de lançamentos:")
                            for lanc in lancamentos_amostra:
                                print(f"    {lanc[0]} - {lanc[1][:50]}... - R$ {lanc[2]:,.2f}")
                    else:
                        print(f"  Empresa não encontrada no Sybase")
    
    except Exception as e:
        print(f"Erro na investigação: {str(e)}")

if __name__ == '__main__':
    investigar_estrutura_sybase_lancamentos()
