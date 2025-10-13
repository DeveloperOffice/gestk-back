from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.contrib.contenttypes.models import ContentType

class FiscalService:
    
    @staticmethod
    def calcular_indicadores(notas):
        total_notas = notas.count()
        notas_entrada = notas.filter(tipo_nota='ENTRADA').count()
        notas_saida = notas.filter(tipo_nota='SAIDA').count()
        
        valor_entrada = notas.filter(tipo_nota='ENTRADA').aggregate(
            total=Sum('valor_total')
        )['total'] or Decimal('0.00')
        
        valor_saida = notas.filter(tipo_nota='SAIDA').aggregate(
            total=Sum('valor_total')
        )['total'] or Decimal('0.00')
        
        return {
            'total_notas': total_notas,
            'notas_entrada': notas_entrada,
            'notas_saida': notas_saida,
            'valor_total_entrada': valor_entrada,
            'valor_total_saida': valor_saida,
            'faturamento_liquido': valor_saida - valor_entrada
        }
    
    @staticmethod
    def calcular_top_clientes(notas, limit=10):
        from apps.pessoas.models import PessoaJuridica
        
        notas_saida = notas.filter(tipo_nota='SAIDA', parceiro_pj__isnull=False)
        
        clientes = notas_saida.values(
            'parceiro_pj__id', 
            'parceiro_pj__razao_social', 
            'parceiro_pj__cnpj'
        ).annotate(
            total_notas=Count('id'),
            valor_total=Sum('valor_total')
        ).order_by('-valor_total')[:limit]
        
        resultado = []
        for cliente in clientes:
            resultado.append({
                'cliente_nome': cliente['parceiro_pj__razao_social'],
                'cliente_cnpj': cliente['parceiro_pj__cnpj'],
                'total_notas': cliente['total_notas'],
                'valor_total': cliente['valor_total'] or Decimal('0.00')
            })
        
        return resultado
