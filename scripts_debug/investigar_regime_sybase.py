"""
Script para investigar no Sybase se as 290 empresas sem regime 
possuem dados na tabela EFPARAMETRO_VIGENCIA que não foram capturados
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from apps.pessoas.models import PessoaJuridica
from apps.importacao.management.commands._base import BaseETLCommand
import pyodbc
from datetime import datetime

def investigar_regime_sybase():
    """Investiga empresas sem regime no PostgreSQL mas que podem ter no Sybase"""
    
    print("=" * 80)
    print("INVESTIGAÇÃO: EMPRESAS SEM REGIME - VERIFICAÇÃO NO SYBASE")
    print("=" * 80)
    print()
    
    # 1. Obter mapa histórico e empresas sem regime
    print("1️⃣ Identificando empresas sem regime...")
    etl_command = BaseETLCommand()
    historical_map = etl_command.build_historical_contabilidade_map()
    cnpjs_validos = set(historical_map.keys())
    
    # PJs válidas sem regime_fiscal
    pjs_sem_regime = PessoaJuridica.objects.filter(
        cnpj__in=cnpjs_validos,
        regime_fiscal__isnull=True
    )
    
    total_sem_regime = pjs_sem_regime.count()
    print(f"   ✅ Empresas sem regime no PostgreSQL: {total_sem_regime}")
    
    # Pegar amostra de 10 empresas
    amostra = list(pjs_sem_regime[:10])
    print(f"   📋 Analisando amostra de {len(amostra)} empresas...\n")
    
    # 2. Conectar ao Sybase
    print("2️⃣ Conectando ao Sybase...")
    try:
        conn = etl_command.get_sybase_connection()
        cursor = conn.cursor()
        print("   ✅ Conexão estabelecida\n")
    except Exception as e:
        print(f"   ❌ Erro ao conectar: {str(e)}")
        return
    
    # 3. Verificar cada empresa na amostra
    print("3️⃣ Verificando empresas no Sybase...")
    print("-" * 80)
    
    empresas_com_dados = 0
    empresas_sem_dados = 0
    detalhes = []
    
    for pj in amostra:
        cnpj_limpo = pj.cnpj.replace('.', '').replace('/', '').replace('-', '')
        
        # Query original da ETL (mesma que está na etl_03_1)
        query = """
            SELECT 
                GE.COD_EMP,
                GE.RAZAO_EMP,
                GE.CNPJ_EMP,
                EP.RFED_PAR,
                EP.VIGENCIA_PAR
            FROM GEEMPRE GE
            LEFT JOIN EFPARAMETRO_VIGENCIA EP 
                ON GE.COD_EMP = EP.EMP_PAR 
                AND EP.VIGENCIA_PAR = (
                    SELECT MAX(EP2.VIGENCIA_PAR) 
                    FROM EFPARAMETRO_VIGENCIA EP2 
                    WHERE EP2.EMP_PAR = GE.COD_EMP
                )
            WHERE GE.CNPJ_EMP = ?
        """
        
        try:
            cursor.execute(query, (cnpj_limpo,))
            row = cursor.fetchone()
            
            if row:
                cod_emp = row[0]
                razao = row[1]
                cnpj_sybase = row[2]
                rfed_par = row[3]
                vigencia = row[4]
                
                status = "✅ TEM DADOS" if rfed_par else "❌ SEM DADOS"
                
                if rfed_par:
                    empresas_com_dados += 1
                    regime_map = {1: 'Simples', 2: 'Presumido', 3: 'Real'}
                    regime = regime_map.get(rfed_par, f'Desconhecido ({rfed_par})')
                    vigencia_str = vigencia.strftime('%Y-%m-%d') if vigencia else 'NULL'
                    
                    detalhes.append({
                        'razao': razao[:40],
                        'cnpj': pj.cnpj,
                        'cod_emp': cod_emp,
                        'status': '✅ ENCONTRADO',
                        'regime': regime,
                        'vigencia': vigencia_str,
                        'observacao': '⚠️ Dado existe no Sybase mas não foi importado!'
                    })
                else:
                    empresas_sem_dados += 1
                    detalhes.append({
                        'razao': razao[:40],
                        'cnpj': pj.cnpj,
                        'cod_emp': cod_emp,
                        'status': '❌ SEM REGIME',
                        'regime': 'NULL',
                        'vigencia': 'NULL',
                        'observacao': 'Empresa não tem regime no Sybase'
                    })
            else:
                empresas_sem_dados += 1
                detalhes.append({
                    'razao': pj.razao_social[:40],
                    'cnpj': pj.cnpj,
                    'cod_emp': 'N/A',
                    'status': '❌ NÃO ENCONTRADA',
                    'regime': 'N/A',
                    'vigencia': 'N/A',
                    'observacao': 'Empresa não encontrada no Sybase'
                })
                
        except Exception as e:
            print(f"   ❌ Erro ao consultar {pj.cnpj}: {str(e)}")
    
    cursor.close()
    conn.close()
    
    # 4. Exibir resultados
    print()
    print("📊 RESULTADOS DA AMOSTRA:")
    print("-" * 80)
    
    for item in detalhes:
        print(f"\n{item['status']} {item['razao']}")
        print(f"   CNPJ: {item['cnpj']}")
        print(f"   Cód. Empresa: {item['cod_emp']}")
        print(f"   Regime: {item['regime']}")
        print(f"   Vigência: {item['vigencia']}")
        print(f"   {item['observacao']}")
    
    # 5. Resumo final
    print()
    print("=" * 80)
    print("RESUMO DA INVESTIGAÇÃO")
    print("=" * 80)
    print(f"✅ Empresas COM dados no Sybase: {empresas_com_dados}/{len(amostra)} ({empresas_com_dados/len(amostra)*100:.1f}%)")
    print(f"❌ Empresas SEM dados no Sybase: {empresas_sem_dados}/{len(amostra)} ({empresas_sem_dados/len(amostra)*100:.1f}%)")
    print()
    
    if empresas_com_dados > 0:
        print("⚠️  PROBLEMA IDENTIFICADO!")
        print(f"   {empresas_com_dados} empresas TÊM regime no Sybase mas NÃO foram importadas!")
        print()
        print("   POSSÍVEIS CAUSAS:")
        print("   1. ETL 03_1 executada ANTES dos dados serem inseridos no Sybase")
        print("   2. Problema na query de importação (JOIN ou filtro incorreto)")
        print("   3. Dados inseridos/atualizados no Sybase após a última execução da ETL")
        print()
        print("   SOLUÇÃO:")
        print("   → Executar novamente: python manage.py etl_03_1_pessoas_juridicas")
        print()
    else:
        print("✅ DADOS CONSISTENTES")
        print("   As empresas sem regime no PostgreSQL também não têm no Sybase.")
        print("   Isso indica que o dado realmente não existe na origem.")
    
    # 6. Estimativa para todas as 290 empresas
    if len(amostra) > 0:
        percentual_com_dados = empresas_com_dados / len(amostra)
        estimativa = int(total_sem_regime * percentual_com_dados)
        
        print()
        print("📈 PROJEÇÃO PARA TODAS AS 290 EMPRESAS:")
        print(f"   Estimativa de empresas com dados no Sybase: ~{estimativa}")
        print(f"   Isso representa ~{percentual_com_dados*100:.1f}% do total")
    
    print()
    print("=" * 80)

if __name__ == '__main__':
    investigar_regime_sybase()
