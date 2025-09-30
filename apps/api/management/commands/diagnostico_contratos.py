import os
import sys
import django

# Adicionar o caminho do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from django.core.management.base import BaseCommand
from apps.core.models import Contabilidade
from apps.pessoas.models import Contrato

class Command(BaseCommand):
    help = 'Diagnostica a associação de contratos a contabilidades no banco de dados Django.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- Diagnóstico de Associação de Contratos ---"))

        # 1. Encontrar a contabilidade alvo
        try:
            contabilidade_alvo = Contabilidade.objects.get(cnpj='10662155000147')
            self.stdout.write(f"Contabilidade Alvo: '{contabilidade_alvo.razao_social}' (ID: {contabilidade_alvo.id})")
        except Contabilidade.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ Contabilidade com CNPJ 10662155000147 não encontrada no Django."))
            return

        # 2. Contar contratos associados a esta contabilidade
        contratos_associados = Contrato.objects.filter(contabilidade=contabilidade_alvo).count()
        self.stdout.write(f"Contratos associados diretamente à contabilidade alvo: {contratos_associados}")

        if contratos_associados > 0:
            self.stdout.write(self.style.SUCCESS("✅ Parece haver contratos associados corretamente."))
        else:
            self.stdout.write(self.style.WARNING("⚠️ Nenhum contrato está associado diretamente a esta contabilidade."))

        # 3. Verificar o total de contratos e a quais contabilidades eles pertencem
        total_contratos = Contrato.objects.count()
        self.stdout.write(f"\nTotal de contratos no banco de dados: {total_contratos}")

        if total_contratos > 0 and contratos_associados == 0:
            self.stdout.write(self.style.WARNING("Os contratos existem, mas estão associados a outras contabilidades. Verificando..."))
            
            # Agrupar contratos por contabilidade
            from django.db.models import Count
            contratos_por_contabilidade = Contrato.objects.values(
                'contabilidade__razao_social', 
                'contabilidade__cnpj'
            ).annotate(total=Count('id')).order_by('-total')

            if contratos_por_contabilidade:
                self.stdout.write("\nDistribuição de contratos por contabilidade:")
                for item in contratos_por_contabilidade:
                    self.stdout.write(
                        f"- {item['contabilidade__razao_social']} (CNPJ: {item['contabilidade__cnpj']}): {item['total']} contratos"
                    )
                self.stdout.write(self.style.ERROR("\nConclusão: A ETL_03 está associando todos os contratos a uma contabilidade incorreta."))
            else:
                self.stdout.write(self.style.WARNING("Não foi possível agrupar os contratos por contabilidade."))

if __name__ == "__main__":
    Command().handle()
