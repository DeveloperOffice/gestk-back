import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from apps.core.models import Contabilidade
from apps.api.gestao.carteira.views import CarteiraViewSet

User = get_user_model()

class Command(BaseCommand):
    help = 'Testa o endpoint de carteira/clientes e imprime o resultado.'

    def handle(self, *args, **options):
        # 1. Forçar a busca do usuário e contabilidade do banco de dados para garantir que estamos usando os objetos corretos
        try:
            contabilidade = Contabilidade.objects.get(cnpj='10662155000147')
            user = User.objects.get(username='testuser')
            user.contabilidade = contabilidade
            user.save(update_fields=['contabilidade'])
        except (User.DoesNotExist, Contabilidade.DoesNotExist):
            self.stdout.write(self.style.ERROR("Usuário de teste ou contabilidade não encontrados. Execute a ETL primeiro."))
            return

        self.stdout.write(self.style.SUCCESS(f'Usando usuário "{user.username}" associado à contabilidade "{contabilidade.razao_social}"'))

        # 2. Simular uma requisição
        factory = APIRequestFactory()
        view = CarteiraViewSet.as_view({'get': 'clientes'})
        
        request = factory.get('/api/gestao/carteira/clientes/')
        force_authenticate(request, user=user)

        self.stdout.write(self.style.WARNING('Executando a view...'))
        
        try:
            # 3. Executar a view
            response = view(request)
            response.render()

            # 4. Imprimir o resultado
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS('Requisição bem-sucedida!'))
                
                # Imprimir o corpo completo da resposta
                pretty_json = json.dumps(response.data, indent=4, ensure_ascii=False)
                self.stdout.write(pretty_json)

                # Imprimir apenas o resumo no final para fácil visualização
                self.stdout.write(self.style.SUCCESS('\n' + '='*50))
                self.stdout.write(self.style.SUCCESS('Resumo da Carteira:'))
                summary_json = json.dumps(response.data.get('summary', {}), indent=4, ensure_ascii=False)
                self.stdout.write(summary_json)
                self.stdout.write(self.style.SUCCESS('='*50))

            else:
                self.stdout.write(self.style.ERROR(f'Erro na requisição: {response.status_code}'))
                self.stdout.write(response.content.decode('utf-8'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ocorreu uma exceção: {e}'))
