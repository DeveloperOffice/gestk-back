from decimal import Decimal
from django.db.models import Count

class OrganizacionalService:
    
    @staticmethod
    def calcular_estrutura_departamentos(vinculos):
        departamentos = vinculos.filter(
            departamento__isnull=False
        ).values(
            'departamento__id', 'departamento__nome'
        ).annotate(
            total=Count('id')
        ).order_by('-total')
        
        total_geral = sum(d['total'] for d in departamentos)
        resultado = []
        for dept in departamentos:
            percentual = (dept['total'] / total_geral * 100) if total_geral > 0 else 0
            resultado.append({
                'id': dept['departamento__id'],
                'nome': dept['departamento__nome'],
                'total_funcionarios': dept['total'],
                'percentual': round(Decimal(str(percentual)), 2)
            })
        return resultado
    
    @staticmethod
    def calcular_estrutura_cargos(vinculos):
        cargos = vinculos.filter(
            cargo__isnull=False
        ).values(
            'cargo__id', 'cargo__nome', 'cargo__cbo_2002', 'departamento__nome'
        ).annotate(
            total=Count('id')
        ).order_by('-total')
        
        resultado = []
        for cargo in cargos:
            resultado.append({
                'id': cargo['cargo__id'],
                'nome': cargo['cargo__nome'],
                'cbo_2002': cargo['cargo__cbo_2002'],
                'total_funcionarios': cargo['total'],
                'departamento': cargo['departamento__nome']
            })
        return resultado
    
    @staticmethod
    def calcular_hierarquia(vinculos):
        from apps.funcionarios.models import Departamento, Cargo
        
        total_departamentos = Departamento.objects.filter(
            id__in=vinculos.values_list('departamento_id', flat=True)
        ).count()
        
        total_cargos = Cargo.objects.filter(
            id__in=vinculos.values_list('cargo_id', flat=True)
        ).count()
        
        total_funcionarios = vinculos.count()
        
        media = (total_funcionarios / total_departamentos) if total_departamentos > 0 else 0
        
        return {
            'total_departamentos': total_departamentos,
            'total_cargos': total_cargos,
            'total_funcionarios': total_funcionarios,
            'media_funcionarios_por_departamento': round(Decimal(str(media)), 2)
        }
