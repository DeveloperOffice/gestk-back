import pyodbc
import django
import os

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from apps.funcionarios.models import Rescisao

print("=" * 80)
print("VERIFICAÇÃO DE MAPEAMENTO - RESCISÕES")
print("=" * 80)

# 1. Verificar rescisões no Django
print("\n1. RESCISÕES NO DJANGO (bd_gestk):")
print("-" * 80)
rescisoes = Rescisao.objects.all()
print(f"Total rescisões: {rescisoes.count()}")

# Extrair codi_emp únicos
ids_legado = [r.id_legado for r in rescisoes if r.id_legado]
codi_emps_django = set()
for id_leg in ids_legado:
    if id_leg and '-' in id_leg:
        codi_emp = id_leg.split('-')[0]
        codi_emps_django.add(codi_emp)

print(f"Códigos de empresa únicos: {len(codi_emps_django)}")
print(f"Códigos: {sorted(codi_emps_django, key=lambda x: int(x) if x.isdigit() else 0)}")

# 2. Verificar rescisões no Sybase
print("\n2. RESCISÕES NO SYBASE (bethadba.FORESCISOES):")
print("-" * 80)
try:
    conn = pyodbc.connect('DSN=SybaseProducao')
    cursor = conn.cursor()
    
    # Contar total de rescisões
    cursor.execute("""
        SELECT COUNT(*) 
        FROM bethadba.FORESCISOES 
        WHERE demissao >= '2019-01-01'
    """)
    total_sybase = cursor.fetchone()[0]
    print(f"Total rescisões no Sybase: {total_sybase}")
    
    # Buscar codi_emp únicos
    cursor.execute("""
        SELECT DISTINCT codi_emp 
        FROM bethadba.FORESCISOES 
        WHERE demissao >= '2019-01-01'
        ORDER BY codi_emp
    """)
    codi_emps_sybase = [str(row[0]) for row in cursor.fetchall()]
    print(f"Códigos de empresa únicos: {len(codi_emps_sybase)}")
    print(f"Códigos: {codi_emps_sybase}")
    
    # 3. Comparar
    print("\n3. ANÁLISE DE DIFERENÇAS:")
    print("-" * 80)
    
    sybase_set = set(codi_emps_sybase)
    django_set = codi_emps_django
    
    faltando = sybase_set - django_set
    excesso = django_set - sybase_set
    
    print(f"Códigos no Sybase mas NÃO no Django: {len(faltando)}")
    if faltando:
        print(f"  Códigos: {sorted(faltando, key=lambda x: int(x) if x.isdigit() else 0)}")
    
    print(f"\nCódigos no Django mas NÃO no Sybase: {len(excesso)}")
    if excesso:
        print(f"  Códigos: {sorted(excesso, key=lambda x: int(x) if x.isdigit() else 0)}")
    
    # 4. Verificar rubricas
    print("\n4. RUBRICAS NO SYBASE (bethadba.FOMOVTOSERV):")
    print("-" * 80)
    cursor.execute("""
        SELECT COUNT(*) 
        FROM bethadba.FORESCISOES fs
        INNER JOIN bethadba.FOMOVTOSERV m ON 
            m.codi_emp = fs.codi_emp AND 
            m.i_empregados = fs.i_empregados AND
            m.i_calculos = fs.i_calculos AND
            m.TIPO_PROCES = 11
        WHERE fs.demissao >= '2019-01-01'
            AND m.valor_cal != 0
    """)
    total_rubricas = cursor.fetchone()[0]
    print(f"Total rubricas de rescisão: {total_rubricas}")
    
    # Códigos únicos nas rubricas
    cursor.execute("""
        SELECT DISTINCT fs.codi_emp 
        FROM bethadba.FORESCISOES fs
        INNER JOIN bethadba.FOMOVTOSERV m ON 
            m.codi_emp = fs.codi_emp AND 
            m.i_empregados = fs.i_empregados AND
            m.i_calculos = fs.i_calculos AND
            m.TIPO_PROCES = 11
        WHERE fs.demissao >= '2019-01-01'
            AND m.valor_cal != 0
        ORDER BY fs.codi_emp
    """)
    codi_emps_rubricas = [str(row[0]) for row in cursor.fetchall()]
    print(f"Códigos de empresa únicos: {len(codi_emps_rubricas)}")
    print(f"Códigos: {codi_emps_rubricas}")
    
    conn.close()
    
except Exception as e:
    print(f"Erro ao conectar ao Sybase: {e}")

print("\n" + "=" * 80)
