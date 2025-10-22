import os
import django
import pyodbc
from django.conf import settings
from collections import defaultdict

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

def investigar_duplicatas_lancamentos():
    print("=== INVESTIGAÇÃO: DUPLICATAS DE LANÇAMENTOS NO SYBASE ===")
    
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
            
            # 1. Verificar duplicatas por numero_lancamento + data_lancamento
            print("\n--- DUPLICATAS POR NUMERO + DATA ---")
            cursor.execute("""
                SELECT TOP 20
                    nume_lan,
                    data_lan,
                    COUNT(*) as quantidade,
                    LIST(DISTINCT codi_emp, ', ') as empresas
                FROM bethadba.ctlancto
                GROUP BY nume_lan, data_lan
                HAVING COUNT(*) > 1
                ORDER BY quantidade DESC
            """)
            
            duplicatas_data = cursor.fetchall()
            print(f"Encontradas {len(duplicatas_data)} combinações duplicadas (numero + data)")
            
            for row in duplicatas_data:
                print(f"  Número: {row[0]}, Data: {row[1]}, Qtd: {row[2]}, Empresas: {row[3]}")
            
            # 2. Verificar duplicatas apenas por numero_lancamento
            print("\n--- DUPLICATAS APENAS POR NUMERO ---")
            cursor.execute("""
                SELECT TOP 20
                    nume_lan,
                    COUNT(*) as quantidade,
                    COUNT(DISTINCT data_lan) as datas_diferentes,
                    LIST(DISTINCT codi_emp, ', ') as empresas
                FROM bethadba.ctlancto
                GROUP BY nume_lan
                HAVING COUNT(*) > 1
                ORDER BY quantidade DESC
            """)
            
            duplicatas_numero = cursor.fetchall()
            print(f"Encontradas {len(duplicatas_numero)} números duplicados")
            
            for row in duplicatas_numero:
                print(f"  Número: {row[0]}, Qtd: {row[1]}, Datas diferentes: {row[2]}, Empresas: {row[3]}")
            
            # 3. Verificar duplicatas por empresa específica
            print("\n--- DUPLICATAS PARA EMPRESA 206 (ASSESSORIA CONTABIL) ---")
            cursor.execute("""
                SELECT TOP 10
                    nume_lan,
                    data_lan,
                    COUNT(*) as quantidade,
                    LIST(DISTINCT vlor_lan, ', ') as valores
                FROM bethadba.ctlancto
                WHERE codi_emp = 206
                GROUP BY nume_lan, data_lan
                HAVING COUNT(*) > 1
                ORDER BY quantidade DESC
            """)
            
            duplicatas_empresa = cursor.fetchall()
            print(f"Encontradas {len(duplicatas_empresa)} duplicatas para empresa 206")
            
            for row in duplicatas_empresa:
                print(f"  Número: {row[0]}, Data: {row[1]}, Qtd: {row[2]}, Valores: {row[3]}")
            
            # 4. Verificar se há diferenças nos valores para o mesmo número
            print("\n--- DIFERENÇAS DE VALORES PARA MESMO NÚMERO ---")
            cursor.execute("""
                SELECT TOP 10
                    nume_lan,
                    data_lan,
                    COUNT(DISTINCT vlor_lan) as valores_diferentes,
                    LIST(DISTINCT vlor_lan, ', ') as valores,
                    LIST(DISTINCT chis_lan, ' | ') as historicos
                FROM bethadba.ctlancto
                WHERE codi_emp = 206
                GROUP BY nume_lan, data_lan
                HAVING COUNT(DISTINCT vlor_lan) > 1
                ORDER BY valores_diferentes DESC
            """)
            
            valores_diferentes = cursor.fetchall()
            print(f"Encontradas {len(valores_diferentes)} combinações com valores diferentes")
            
            for row in valores_diferentes:
                print(f"  Número: {row[0]}, Data: {row[1]}, Valores diferentes: {row[2]}")
                print(f"    Valores: {row[3]}")
                print(f"    Históricos: {row[4][:100]}...")
                print()
            
            # 5. Verificar se há diferenças nos códigos de débito/crédito
            print("\n--- DIFERENÇAS DE CÓDIGOS DE DÉBITO/CRÉDITO ---")
            cursor.execute("""
                SELECT TOP 10
                    nume_lan,
                    data_lan,
                    COUNT(DISTINCT cdeb_lan) as debitos_diferentes,
                    COUNT(DISTINCT ccre_lan) as creditos_diferentes,
                    LIST(DISTINCT cdeb_lan, ', ') as debitos,
                    LIST(DISTINCT ccre_lan, ', ') as creditos
                FROM bethadba.ctlancto
                WHERE codi_emp = 206
                GROUP BY nume_lan, data_lan
                HAVING COUNT(DISTINCT cdeb_lan) > 1 OR COUNT(DISTINCT ccre_lan) > 1
                ORDER BY (COUNT(DISTINCT cdeb_lan) + COUNT(DISTINCT ccre_lan)) DESC
            """)
            
            codigos_diferentes = cursor.fetchall()
            print(f"Encontradas {len(codigos_diferentes)} combinações com códigos diferentes")
            
            for row in codigos_diferentes:
                print(f"  Número: {row[0]}, Data: {row[1]}")
                print(f"    Débitos diferentes: {row[2]}, Códigos: {row[4]}")
                print(f"    Créditos diferentes: {row[3]}, Códigos: {row[5]}")
                print()
            
            # 6. Resumo geral
            print("\n--- RESUMO GERAL ---")
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_lancamentos,
                    COUNT(DISTINCT nume_lan) as numeros_unicos,
                    COUNT(DISTINCT nume_lan + '_' + CAST(data_lan AS VARCHAR(10))) as combinacoes_unicas,
                    COUNT(DISTINCT codi_emp) as empresas_diferentes
                FROM bethadba.ctlancto
            """)
            
            resumo = cursor.fetchone()
            print(f"Total de lançamentos: {resumo[0]:,}")
            print(f"Números únicos: {resumo[1]:,}")
            print(f"Combinações únicas (numero + data): {resumo[2]:,}")
            print(f"Empresas diferentes: {resumo[3]}")
            
            # Calcular duplicatas
            duplicatas_totais = resumo[0] - resumo[2]
            percentual_duplicatas = (duplicatas_totais / resumo[0]) * 100 if resumo[0] > 0 else 0
            print(f"Duplicatas totais: {duplicatas_totais:,} ({percentual_duplicatas:.2f}%)")
    
    except Exception as e:
        print(f"Erro na investigação: {str(e)}")

if __name__ == '__main__':
    investigar_duplicatas_lancamentos()
