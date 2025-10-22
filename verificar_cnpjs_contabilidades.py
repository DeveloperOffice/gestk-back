import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from apps.core.models import Contabilidade

def verificar_cnpjs_contabilidades():
    print("=== CNPJs DAS CONTABILIDADES ===")
    
    contabilidades = Contabilidade.objects.all().order_by('razao_social')
    
    print(f"Total de contabilidades: {contabilidades.count()}")
    print("\nLista de contabilidades:")
    
    for contab in contabilidades:
        print(f"- {contab.razao_social}")
        print(f"  CNPJ: {contab.cnpj}")
        print(f"  ID: {contab.id}")
        print()

if __name__ == '__main__':
    verificar_cnpjs_contabilidades()
