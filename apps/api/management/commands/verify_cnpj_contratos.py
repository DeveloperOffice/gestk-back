import os
import sys
import django
import pyodbc
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.models import Contabilidade

class Command(BaseCommand):
    help = 'Verifica a consistência dos CNPJs de contabilidades entre o Django e o Sybase'

    def get_sybase_connection(self):
        try:
            # Usa a configuração centralizada do settings.py
            connection_string = (
                f"DRIVER={{{settings.SYBASE_CONFIG['DRIVER']}}};"
                f"SERVER={settings.SYBASE_CONFIG['SERVER']};"
                f"DATABASE={settings.SYBASE_CONFIG['DATABASE']};"
                f"UID={settings.SYBASE_CONFIG['UID']};"
                f"PWD={settings.SYBASE_CONFIG['PWD']};"
            )
            connection = pyodbc.connect(connection_string)
            self.stdout.write(self.style.SUCCESS("Conexão com o Sybase (ODBC) estabelecida com sucesso."))
            return connection
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao conectar ao Sybase: {e}"))
            return None

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("\n--- Verificando CNPJs das Contabilidades no Sybase ---"))
        
        try:
            contabilidade_django = Contabilidade.objects.get(razao_social__icontains="ASSESSORIA CONTABIL OFFICE")
            cnpj_django = contabilidade_django.cnpj
            self.stdout.write(f"CNPJ da 'ASSESSORIA CONTABIL OFFICE' no Django: {cnpj_django}")
        except Contabilidade.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ Contabilidade 'ASSESSORIA CONTABIL OFFICE' não encontrada no Django."))
            return
        except Contabilidade.MultipleObjectsReturned:
            self.stdout.write(self.style.ERROR("❌ Múltiplas contabilidades com 'ASSESSORIA CONTABIL OFFICE' encontradas no Django."))
            return

        connection = self.get_sybase_connection()
        if not connection:
            return

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
                    self.stdout.write(self.style.WARNING("Nenhum CNPJ de contabilidade encontrado no Sybase para os contratos."))
                    return

                self.stdout.write(self.style.SUCCESS("\nCNPJs de contabilidades com contratos encontrados no Sybase:"))
                found_match = False
                for row in results:
                    cnpj_sybase = row.cnpj_contabilidade.strip()
                    razao_social_sybase = row.razao_social_contabilidade.strip()
                    self.stdout.write(f"- Razão Social: {razao_social_sybase}, CNPJ: {cnpj_sybase}")
                    if cnpj_sybase == cnpj_django:
                        self.stdout.write(self.style.SUCCESS(f"  ✅ CORRESPONDÊNCIA ENCONTRADA! Os contratos para '{razao_social_sybase}' devem ser importados corretamente."))
                        found_match = True
                
                if not found_match:
                    self.stdout.write(self.style.WARNING("\n❌ ALERTA: O CNPJ da contabilidade no Django não corresponde a NENHUM CNPJ de contabilidade com contratos no Sybase."))
                    self.stdout.write(self.style.WARNING("Isso explica por que a API não retorna clientes. Os contratos estão sendo associados a outra(s) contabilidade(s)."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao executar a query no Sybase: {e}"))
        finally:
            connection.close()
            self.stdout.write("\nConexão com o Sybase fechada.")
