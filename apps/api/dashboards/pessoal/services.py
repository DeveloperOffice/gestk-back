from decimal import Decimal
from django.db.models import Sum, Count, Avg

class PessoalService:
    
    @staticmethod
    def calcular_indicadores_folha(vinculos):
        total_funcionarios = vinculos.filter(ativo=True).count()
        # Valores simulados - ajustar quando houver dados reais de folha
        return {
            'total_funcionarios': total_funcionarios,
            'total_proventos': Decimal('0.00'),
            'total_descontos': Decimal('0.00'),
            'folha_liquida': Decimal('0.00'),
            'media_salarial': Decimal('0.00')
        }
