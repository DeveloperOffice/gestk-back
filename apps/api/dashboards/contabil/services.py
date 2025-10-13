from decimal import Decimal
from django.db.models import Sum, Count, Q

class ContabilService:
    
    @staticmethod
    def calcular_indicadores(lancamentos):
        total = lancamentos.count()
        partidas = lancamentos.values_list('partidas', flat=True)
        
        from apps.contabil.models import Partida
        todas_partidas = Partida.objects.filter(lancamento__in=lancamentos)
        
        debitos = todas_partidas.filter(tipo='D').aggregate(
            total=Sum('valor')
        )['total'] or Decimal('0.00')
        
        creditos = todas_partidas.filter(tipo='C').aggregate(
            total=Sum('valor')
        )['total'] or Decimal('0.00')
        
        return {
            'total_lancamentos': total,
            'total_debitos': debitos,
            'total_creditos': creditos,
            'saldo': debitos - creditos
        }
    
    @staticmethod
    def calcular_balancete(lancamentos, data_inicio, data_fim):
        from apps.contabil.models import PlanoContas, Partida
        
        contas = PlanoContas.objects.filter(
            aceita_lancamento=True,
            ativo=True
        )
        
        resultado = []
        for conta in contas:
            partidas = Partida.objects.filter(
                conta=conta,
                lancamento__in=lancamentos,
                lancamento__data_lancamento__range=[data_inicio, data_fim]
            )
            
            debitos = partidas.filter(tipo='D').aggregate(
                total=Sum('valor')
            )['total'] or Decimal('0.00')
            
            creditos = partidas.filter(tipo='C').aggregate(
                total=Sum('valor')
            )['total'] or Decimal('0.00')
            
            saldo = debitos - creditos
            
            if debitos > 0 or creditos > 0:
                resultado.append({
                    'conta_codigo': conta.codigo,
                    'conta_nome': conta.nome,
                    'saldo_anterior': Decimal('0.00'),
                    'debitos': debitos,
                    'creditos': creditos,
                    'saldo_atual': saldo
                })
        
        return resultado
