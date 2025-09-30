import os
import sys
import django
import pyodbc
from django.conf import settings

# Adicionar o caminho do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from apps.core.models import Contabilidade

def get_sybase_connection():
    try:
        connection = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            f'SERVER={settings.SYBASE_HOST};'
            f'DATABASE={settings.SYBASE_DB};'
            f'UID={settings.SYBASE_USER};'
            f'PWD={settings.SYBASE_PASSWORD};'
            'TDS_Version=8.0;'
        )
        print("Conexão com o Sybase (ODBC) estabelecida com sucesso.")
        return connection
    except Exception as e:
        print(f"Erro ao conectar ao Sybase: {e}")
        return None

def check_contabilidade_cnpj():
    print("\n--- Verificando CNPJs das Contabilidades no Sybase ---")
    
    # Pega o CNPJ da contabilidade do usuário de teste no Django
    try:
        contabilidade_django = Contabilidade.objects.get(razao_social__icontains="ASSESSORIA CONTABIL OFFICE")
        cnpj_django = contabilidade_django.cnpj
        print(f"CNPJ da 'ASSESSORIA CONTABIL OFFICE' no Django: {cnpj_django}")
    except Contabilidade.DoesNotExist:
        print("❌ Contabilidade 'ASSESSORIA CONTABIL OFFICE' não encontrada no Django.")
        return
    except Contabilidade.MultipleObjectsReturned:
        print("❌ Múltiplas contabilidades com 'ASSESSORIA CONTABIL OFFICE' encontradas no Django.")
        return

    connection = get_sybase_connection()
    if not connection:
        return

    # Query para buscar os CNPJs das contabilidades que possuem contratos
    query = """
    SELECT DISTINCT
        cont_ge.cgce_emp as cnpj_contabilidade,
        cont_ge.nome_emp as razao_social_contabilidade
    FROM 
        BETHADBA.HRCONTRATO AS hc
    INNER JOIN
        BETHADBA.GEEMPRE AS cont_ge ON hc.codi_emp = cont_ge.codi_emp
    WHERE hc.data_inicio_faturamento >= '2019-01-01'
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            
            if not results:
                print("Nenhum CNPJ de contabilidade encontrado no Sybase para os contratos.")
                return

            print("\nCNPJs de contabilidades com contratos encontrados no Sybase:")
            found_match = False
            for row in results:
                cnpj_sybase = row.cnpj_contabilidade.strip()
                razao_social_sybase = row.razao_social_contabilidade.strip()
                print(f"- Razão Social: {razao_social_sybase}, CNPJ: {cnpj_sybase}")
                if cnpj_sybase == cnpj_django:
                    print(f"  ✅ CORRESPONDÊNCIA ENCONTRADA! Os contratos para '{razao_social_sybase}' devem ser importados corretamente.")
                    found_match = True
            
            if not found_match:
                print("\n❌ ALERTA: O CNPJ da contabilidade no Django não corresponde a NENHUM CNPJ de contabilidade com contratos no Sybase.")
                print("Isso explica por que a API não retorna clientes. Os contratos estão sendo associados a outra(s) contabilidade(s).")

    except Exception as e:
        print(f"Erro ao executar a query no Sybase: {e}")
    finally:
        connection.close()
        print("\nConexão com o Sybase fechada.")

if __name__ == "__main__":
    check_contabilidade_cnpj()
