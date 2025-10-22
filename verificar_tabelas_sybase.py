import os
import django
import pyodbc
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

def verificar_tabelas_sybase():
    print("=== VERIFICAÇÃO: TABELAS NO SYBASE ===")
    
    try:
        # Conectar ao Sybase
        config = settings.SYBASE_CONFIG
        connection_string = (
            f"DRIVER={{{config['DRIVER']}}};"
            f"SERVER={config['SERVER']};"
            f"DATABASE={config['DATABASE']};"
            f"UID={config['UID']};"
            f"PWD={config['PWD']};"
        )
        
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            
            # 1. Listar todas as tabelas do schema bethadba
            print("\n--- TABELAS NO SCHEMA BETHADBA ---")
            cursor.execute("""
                SELECT table_name 
                FROM SYS.SYSTABLE 
                WHERE creator = USER_ID('bethadba')
                AND table_type = 'BASE'
                ORDER BY table_name
            """)
            
            tabelas = cursor.fetchall()
            print(f"Total de tabelas: {len(tabelas)}")
            
            # Filtrar tabelas relacionadas a lançamentos
            tabelas_lancamentos = [t[0] for t in tabelas if 'lanc' in t[0].lower() or 'part' in t[0].lower()]
            print(f"\nTabelas relacionadas a lançamentos: {len(tabelas_lancamentos)}")
            for tabela in tabelas_lancamentos:
                print(f"  - {tabela}")
            
            # 2. Verificar se há dados na tabela principal de lançamentos
            print(f"\n--- DADOS DE EXEMPLO DA TABELA CTLANCTO ---")
            
            cursor.execute("""
                SELECT TOP 3 *
                FROM bethadba.ctlancto
            """)
            
            colunas_nomes = [desc[0] for desc in cursor.description]
            dados = cursor.fetchall()
            
            print(f"Colunas: {colunas_nomes}")
            for linha in dados:
                print(f"  {dict(zip(colunas_nomes, linha))}")
            
            # 3. Verificar tabela de partidas
            print(f"\n--- DADOS DE EXEMPLO DA TABELA CTPARTIDAS ---")
            
            cursor.execute("""
                SELECT TOP 3 *
                FROM bethadba.ctpartidas
            """)
            
            colunas_partidas = [desc[0] for desc in cursor.description]
            dados_partidas = cursor.fetchall()
            
            print(f"Colunas: {colunas_partidas}")
            for linha in dados_partidas:
                print(f"  {dict(zip(colunas_partidas, linha))}")
            
            # 4. Verificar tabelas relacionadas a empresas
            print("\n--- TABELAS RELACIONADAS A EMPRESAS ---")
            tabelas_empresas = [t[0] for t in tabelas if 'emp' in t[0].lower() or 'empre' in t[0].lower()]
            for tabela in tabelas_empresas:
                print(f"  - {tabela}")
    
    except Exception as e:
        print(f"Erro na verificação: {str(e)}")

if __name__ == '__main__':
    verificar_tabelas_sybase()
