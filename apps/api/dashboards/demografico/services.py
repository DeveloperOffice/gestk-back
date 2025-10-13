"""
Services para Dashboard Demográfico
Contém lógica de negócio e agregações
"""
from django.db.models import Count, Avg, Q, F
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal


class DemograficoService:
    """Service para calcular métricas demográficas"""

    @staticmethod
    def calcular_idade(data_nascimento):
        """Calcula idade a partir da data de nascimento"""
        if not data_nascimento:
            return None
        hoje = date.today()
        return hoje.year - data_nascimento.year - (
            (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day)
        )

    @staticmethod
    def calcular_tempo_empresa(data_admissao):
        """Calcula tempo de empresa em anos"""
        if not data_admissao:
            return None
        hoje = date.today()
        delta = hoje - data_admissao
        return round(delta.days / 365.25, 2)

    @staticmethod
    def obter_faixa_etaria(idade):
        """Retorna faixa etária baseada na idade"""
        if idade is None:
            return 'Não informado'
        if idade < 18:
            return 'Menor de 18'
        elif idade < 25:
            return '18-24'
        elif idade < 35:
            return '25-34'
        elif idade < 45:
            return '35-44'
        elif idade < 55:
            return '45-54'
        else:
            return '55+'

    @staticmethod
    def calcular_indicadores(vinculos):
        """
        Calcula indicadores demográficos gerais
        
        Args:
            vinculos: QuerySet de VinculoEmpregaticio
            
        Returns:
            dict com indicadores calculados
        """
        from apps.funcionarios.models import Funcionario
        
        total_colaboradores = vinculos.count()
        colaboradores_ativos = vinculos.filter(ativo=True).count()
        colaboradores_inativos = total_colaboradores - colaboradores_ativos
        
        # Calcular turnover mensal (últimos 30 dias)
        data_limite = timezone.now().date() - timedelta(days=30)
        admissoes_mes = vinculos.filter(data_admissao__gte=data_limite).count()
        demissoes_mes = vinculos.filter(data_demissao__gte=data_limite).count()
        
        # Taxa de turnover = (admissões + demissões) / 2 / total * 100
        if total_colaboradores > 0:
            turnover_rate = ((admissoes_mes + demissoes_mes) / 2 / total_colaboradores) * 100
        else:
            turnover_rate = 0
        
        # Calcular idade média
        funcionarios_ids = vinculos.values_list('funcionario_id', flat=True)
        funcionarios = Funcionario.objects.filter(id__in=funcionarios_ids, data_nascimento__isnull=False)
        
        idades = []
        for func in funcionarios:
            idade = DemograficoService.calcular_idade(func.data_nascimento)
            if idade:
                idades.append(idade)
        
        idade_media = sum(idades) / len(idades) if idades else 0
        
        # Calcular tempo médio de empresa
        tempos = []
        for vinculo in vinculos.filter(data_admissao__isnull=False):
            tempo = DemograficoService.calcular_tempo_empresa(vinculo.data_admissao)
            if tempo:
                tempos.append(tempo)
        
        tempo_medio_empresa = sum(tempos) / len(tempos) if tempos else 0
        
        return {
            'total_colaboradores': total_colaboradores,
            'colaboradores_ativos': colaboradores_ativos,
            'colaboradores_inativos': colaboradores_inativos,
            'admissoes_mes': admissoes_mes,
            'demissoes_mes': demissoes_mes,
            'turnover_rate': round(Decimal(str(turnover_rate)), 2),
            'idade_media': round(Decimal(str(idade_media)), 2),
            'tempo_medio_empresa': round(Decimal(str(tempo_medio_empresa)), 2),
        }

    @staticmethod
    def calcular_evolucao_mensal(vinculos, meses=12):
        """
        Calcula evolução mensal de colaboradores
        
        Args:
            vinculos: QuerySet de VinculoEmpregaticio
            meses: Número de meses para retornar
            
        Returns:
            list de dicts com evolução mensal
        """
        from dateutil.relativedelta import relativedelta
        
        hoje = date.today()
        resultado = []
        
        for i in range(meses - 1, -1, -1):
            data_ref = hoje - relativedelta(months=i)
            primeiro_dia = data_ref.replace(day=1)
            
            # Último dia do mês
            if data_ref.month == 12:
                ultimo_dia = data_ref.replace(day=31)
            else:
                proximo_mes = data_ref.replace(day=1) + relativedelta(months=1)
                ultimo_dia = proximo_mes - timedelta(days=1)
            
            # Colaboradores ativos no final do mês
            ativos_mes = vinculos.filter(
                data_admissao__lte=ultimo_dia
            ).filter(
                Q(data_demissao__isnull=True) | Q(data_demissao__gt=ultimo_dia)
            ).count()
            
            # Admissões no mês
            admissoes = vinculos.filter(
                data_admissao__gte=primeiro_dia,
                data_admissao__lte=ultimo_dia
            ).count()
            
            # Demissões no mês
            demissoes = vinculos.filter(
                data_demissao__gte=primeiro_dia,
                data_demissao__lte=ultimo_dia
            ).count()
            
            resultado.append({
                'mes': data_ref.strftime('%Y-%m'),
                'total': ativos_mes,
                'admissoes': admissoes,
                'demissoes': demissoes,
            })
        
        return resultado

    @staticmethod
    def calcular_distribuicao_etaria(vinculos):
        """Calcula distribuição por faixa etária"""
        from apps.funcionarios.models import Funcionario
        
        funcionarios_ids = vinculos.values_list('funcionario_id', flat=True)
        funcionarios = Funcionario.objects.filter(id__in=funcionarios_ids)
        
        distribuicao = {}
        total = 0
        
        for func in funcionarios:
            idade = DemograficoService.calcular_idade(func.data_nascimento)
            faixa = DemograficoService.obter_faixa_etaria(idade)
            distribuicao[faixa] = distribuicao.get(faixa, 0) + 1
            total += 1
        
        resultado = []
        for faixa, quantidade in sorted(distribuicao.items()):
            percentual = (quantidade / total * 100) if total > 0 else 0
            resultado.append({
                'faixa_etaria': faixa,
                'quantidade': quantidade,
                'percentual': round(Decimal(str(percentual)), 2)
            })
        
        return resultado

    @staticmethod
    def calcular_distribuicao_genero(vinculos):
        """Calcula distribuição por gênero"""
        from apps.funcionarios.models import Funcionario
        
        funcionarios_ids = vinculos.values_list('funcionario_id', flat=True)
        
        distribuicao = Funcionario.objects.filter(
            id__in=funcionarios_ids
        ).values('genero').annotate(
            quantidade=Count('id')
        ).order_by('genero')
        
        total = sum(item['quantidade'] for item in distribuicao)
        
        resultado = []
        genero_map = {'M': 'Masculino', 'F': 'Feminino', None: 'Não informado'}
        
        for item in distribuicao:
            genero_label = genero_map.get(item['genero'], 'Não informado')
            percentual = (item['quantidade'] / total * 100) if total > 0 else 0
            resultado.append({
                'genero': genero_label,
                'quantidade': item['quantidade'],
                'percentual': round(Decimal(str(percentual)), 2)
            })
        
        return resultado

    @staticmethod
    def calcular_distribuicao_escolaridade(vinculos):
        """Calcula distribuição por escolaridade"""
        from apps.funcionarios.models import Funcionario
        
        funcionarios_ids = vinculos.values_list('funcionario_id', flat=True)
        
        distribuicao = Funcionario.objects.filter(
            id__in=funcionarios_ids
        ).values('escolaridade').annotate(
            quantidade=Count('id')
        ).order_by('escolaridade')
        
        total = sum(item['quantidade'] for item in distribuicao)
        
        resultado = []
        escolaridade_map = {
            'fundamental': 'Ensino Fundamental',
            'medio': 'Ensino Médio',
            'superior': 'Ensino Superior',
            'pos': 'Pós-graduação',
            None: 'Não informado'
        }
        
        for item in distribuicao:
            escolaridade_label = escolaridade_map.get(item['escolaridade'], 'Não informado')
            percentual = (item['quantidade'] / total * 100) if total > 0 else 0
            resultado.append({
                'escolaridade': escolaridade_label,
                'quantidade': item['quantidade'],
                'percentual': round(Decimal(str(percentual)), 2)
            })
        
        return resultado

    @staticmethod
    def calcular_distribuicao_cargo(vinculos):
        """Calcula distribuição por cargo"""
        from apps.funcionarios.models import Cargo
        
        distribuicao = vinculos.filter(
            cargo__isnull=False
        ).values(
            cargo_nome=F('cargo__nome')
        ).annotate(
            quantidade=Count('id')
        ).order_by('-quantidade')[:10]  # Top 10 cargos
        
        total = sum(item['quantidade'] for item in distribuicao)
        
        resultado = []
        for item in distribuicao:
            percentual = (item['quantidade'] / total * 100) if total > 0 else 0
            resultado.append({
                'cargo': item['cargo_nome'],
                'quantidade': item['quantidade'],
                'percentual': round(Decimal(str(percentual)), 2)
            })
        
        return resultado
