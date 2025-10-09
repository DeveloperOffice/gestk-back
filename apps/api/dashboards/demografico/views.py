from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta, date

from apps.core.models import Contabilidade, Usuario
from apps.funcionarios.models import Funcionario, VinculoEmpregaticio
from ..serializers import (
    IndicadoresDemograficosSerializer, EvolucaoColaboradoresSerializer,
    DistribuicaoEtariaSerializer, DistribuicaoEscolaridadeSerializer,
    DistribuicaoCargoSerializer, DistribuicaoGeneroSerializer
)

class DemograficoViewSet(viewsets.ViewSet):
    """ViewSet para dashboards demográficos"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def indicadores(self, request):
        """
        Endpoint para indicadores demográficos gerais (Turnover, etc.) (RF01)
        Aplica a Regra de Ouro.
        """
        try:
            contabilidade = request.user.contabilidade
            if not contabilidade:
                return Response(
                    {"error": "Usuário não associado a uma contabilidade."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Buscar vínculos empregatícios da contabilidade
            vinculos = VinculoEmpregaticio.objects.filter(funcionario__contabilidade=contabilidade)
            
            # Calcular indicadores básicos
            total_colaboradores = vinculos.count()
            colaboradores_ativos = vinculos.filter(ativo=True).count()
            colaboradores_inativos = total_colaboradores - colaboradores_ativos
            
            # Calcular turnover mensal
            data_limite = timezone.now().date() - timedelta(days=30)
            admissões_mes = vinculos.filter(
                data_admissao__gte=data_limite
            ).count()
            demissões_mes = vinculos.filter(
                data_demissao__gte=data_limite
            ).count()
            
            turnover_mensal = (demissões_mes / max(total_colaboradores, 1)) * 100
            
            # Calcular turnover anual
            data_limite_ano = timezone.now().date() - timedelta(days=365)
            admissões_ano = vinculos.filter(
                data_admissao__gte=data_limite_ano
            ).count()
            demissões_ano = vinculos.filter(
                data_demissao__gte=data_limite_ano
            ).count()
            
            turnover_anual = (demissões_ano / max(total_colaboradores, 1)) * 100
            
            # Buscar funcionários da contabilidade
            funcionarios = Funcionario.objects.filter(contabilidade=contabilidade)
            
            # Calcular média de idade real
            funcionarios_com_idade = funcionarios.filter(data_nascimento__isnull=False)
            if funcionarios_com_idade.exists():
                from datetime import date
                hoje = date.today()
                idades = []
                for func in funcionarios_com_idade:
                    if func.data_nascimento:
                        idade = hoje.year - func.data_nascimento.year - ((hoje.month, hoje.day) < (func.data_nascimento.month, func.data_nascimento.day))
                        idades.append(idade)
                media_idade = sum(idades) / len(idades) if idades else 35.0
            else:
                media_idade = 35.0
            
            # Calcular distribuição por gênero real
            total_funcionarios = funcionarios.count()
            if total_funcionarios > 0:
                masculino_count = funcionarios.filter(genero='M').count()
                feminino_count = funcionarios.filter(genero='F').count()
                percentual_masculino = (masculino_count / total_funcionarios) * 100
                percentual_feminino = (feminino_count / total_funcionarios) * 100
            else:
                percentual_masculino = 0.0
                percentual_feminino = 0.0

            data = {
                'total_colaboradores': total_colaboradores,
                'colaboradores_ativos': colaboradores_ativos,
                'colaboradores_inativos': colaboradores_inativos,
                'turnover_mensal': round(turnover_mensal, 2),
                'turnover_anual': round(turnover_anual, 2),
                'media_idade': media_idade,
                'percentual_masculino': percentual_masculino,
                'percentual_feminino': percentual_feminino
            }

            serializer = IndicadoresDemograficosSerializer(data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Erro ao buscar indicadores demográficos: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def colaboradores(self, request):
        """
        Endpoint para evolução mensal de colaboradores (RF02)
        Aplica a Regra de Ouro.
        """
        try:
            contabilidade = request.user.contabilidade
            if not contabilidade:
                return Response(
                    {"error": "Usuário não associado a uma contabilidade."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Dados reais de evolução mensal dos últimos 12 meses
            evolucao_data = []
            for i in range(12):
                month = timezone.now().date() - timedelta(days=30 * i)
                month_str = month.strftime('%Y-%m')
                
                # Dados reais baseados nos vínculos empregatícios
                total_colaboradores = VinculoEmpregaticio.objects.filter(
                    funcionario__contabilidade=contabilidade,
                    data_admissao__lte=month
                ).count()
                
                admissões = VinculoEmpregaticio.objects.filter(
                    funcionario__contabilidade=contabilidade,
                    data_admissao__year=month.year,
                    data_admissao__month=month.month
                ).count()
                
                demissões = VinculoEmpregaticio.objects.filter(
                    funcionario__contabilidade=contabilidade,
                    data_demissao__year=month.year,
                    data_demissao__month=month.month
                ).count()
                
                saldo_liquido = admissões - demissões
                
                evolucao_data.append({
                    'mes_ano': month_str,
                    'total_colaboradores': total_colaboradores,
                    'admissões': admissões,
                    'demissões': demissões,
                    'saldo_liquido': saldo_liquido
                })
            
            # Inverter para ordem cronológica crescente
            evolucao_data.reverse()

            serializer = EvolucaoColaboradoresSerializer(evolucao_data, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Erro ao buscar evolução de colaboradores: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def distribuicoes(self, request):
        """
        Endpoint para distribuições etária, escolaridade, cargo, gênero (RF05-RF08)
        Aplica a Regra de Ouro.
        """
        try:
            contabilidade = request.user.contabilidade
            if not contabilidade:
                return Response(
                    {"error": "Usuário não associado a uma contabilidade."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            funcionarios = Funcionario.objects.filter(contabilidade=contabilidade, ativo=True)
            total_funcionarios = funcionarios.count()

            # Distribuição etária real
            from datetime import date
            hoje = date.today()
            distribuicao_etaria = []
            faixas_etarias = [
                ('18-25', 18, 25),
                ('26-35', 26, 35),
                ('36-45', 36, 45),
                ('46-55', 46, 55),
                ('56+', 56, 999)
            ]
            
            for faixa, min_idade, max_idade in faixas_etarias:
                count = 0
                for func in funcionarios.filter(data_nascimento__isnull=False):
                    if func.data_nascimento:
                        idade = hoje.year - func.data_nascimento.year - ((hoje.month, hoje.day) < (func.data_nascimento.month, func.data_nascimento.day))
                        if min_idade <= idade <= max_idade:
                            count += 1
                
                percentual = (count / total_funcionarios * 100) if total_funcionarios > 0 else 0
                distribuicao_etaria.append({
                    'faixa_etaria': faixa,
                    'total_colaboradores': count,
                    'percentual': round(percentual, 2)
                })

            # Distribuição por escolaridade real
            distribuicao_escolaridade = []
            escolaridades = [
                ('fundamental', 'Ensino Fundamental'),
                ('medio', 'Ensino Médio'),
                ('superior', 'Ensino Superior'),
                ('pos', 'Pós-graduação')
            ]
            
            for codigo, nome in escolaridades:
                count = funcionarios.filter(escolaridade=codigo).count()
                percentual = (count / total_funcionarios * 100) if total_funcionarios > 0 else 0
                distribuicao_escolaridade.append({
                    'escolaridade': nome,
                    'total_colaboradores': count,
                    'percentual': round(percentual, 2)
                })

            # Distribuição por cargo real
            distribuicao_cargo = []
            vinculos_ativos = VinculoEmpregaticio.objects.filter(
                funcionario__contabilidade=contabilidade,
                ativo=True
            ).select_related('cargo')
            
            cargos_data = {}
            for vinculo in vinculos_ativos:
                cargo_nome = vinculo.cargo.nome if vinculo.cargo else 'Sem Cargo'
                cargos_data[cargo_nome] = cargos_data.get(cargo_nome, 0) + 1
            
            for cargo, count in cargos_data.items():
                percentual = (count / len(vinculos_ativos) * 100) if len(vinculos_ativos) > 0 else 0
                distribuicao_cargo.append({
                    'cargo': cargo,
                    'total_colaboradores': count,
                    'percentual': round(percentual, 2)
                })

            # Distribuição por gênero real
            distribuicao_genero = []
            generos = [('M', 'Masculino'), ('F', 'Feminino')]
            
            for codigo, nome in generos:
                count = funcionarios.filter(genero=codigo).count()
                percentual = (count / total_funcionarios * 100) if total_funcionarios > 0 else 0
                distribuicao_genero.append({
                    'genero': nome,
                    'total_colaboradores': count,
                    'percentual': round(percentual, 2)
                })

            data = {
                'etaria': distribuicao_etaria,
                'escolaridade': distribuicao_escolaridade,
                'cargo': distribuicao_cargo,
                'genero': distribuicao_genero
            }

            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Erro ao buscar distribuições demográficas: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
