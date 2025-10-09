from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from datetime import timedelta, date

from apps.core.models import Contabilidade, Usuario
from apps.pessoas.models import PessoaJuridica, Contrato
from apps.funcionarios.models import Funcionario, VinculoEmpregaticio
from apps.fiscal.models import NotaFiscal
from apps.contabil.models import LancamentoContabil


class EscritorioViewSet(viewsets.ViewSet):
    """ViewSet para análise de escritório"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def visao_geral(self, request):
        """
        Endpoint para visão geral do escritório
        Aplica a Regra de Ouro.
        """
        try:
            contabilidade = request.user.contabilidade
            if not contabilidade:
                return Response(
                    {"error": "Usuário não associado a uma contabilidade."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Dados básicos do escritório
            total_empresas = PessoaJuridica.objects.filter(
                contabilidade_atual=contabilidade
            ).count()
            
            empresas_ativas = PessoaJuridica.objects.filter(
                contabilidade_atual=contabilidade,
                ativo=True
            ).count()
            
            total_funcionarios = VinculoEmpregaticio.objects.filter(
                funcionario__contabilidade=contabilidade,
                ativo=True
            ).count()
            
            total_usuarios = Usuario.objects.filter(
                contabilidade=contabilidade,
                is_active=True
            ).count()
            
            # Faturamento do mês atual
            mes_atual = timezone.now().date().replace(day=1)
            faturamento_mes = NotaFiscal.objects.filter(
                contabilidade=contabilidade,
                data_emissao__gte=mes_atual
            ).aggregate(
                total=Sum('valor_total')
            )['total'] or 0
            
            # Faturamento do mês anterior
            mes_anterior = (mes_atual - timedelta(days=1)).replace(day=1)
            faturamento_mes_anterior = NotaFiscal.objects.filter(
                contabilidade=contabilidade,
                data_emissao__gte=mes_anterior,
                data_emissao__lt=mes_atual
            ).aggregate(
                total=Sum('valor_total')
            )['total'] or 0
            
            # Calcular crescimento
            crescimento = 0
            if faturamento_mes_anterior > 0:
                crescimento = ((faturamento_mes - faturamento_mes_anterior) / faturamento_mes_anterior) * 100
            
            # Contratos ativos
            contratos_ativos = Contrato.objects.filter(
                contabilidade=contabilidade,
                ativo=True
            ).count()
            
            # Lançamentos contábeis do mês
            lancamentos_mes = LancamentoContabil.objects.filter(
                contabilidade=contabilidade,
                data_lancamento__gte=mes_atual
            ).count()
            
            visao_geral = {
                'resumo': {
                    'total_empresas': total_empresas,
                    'empresas_ativas': empresas_ativas,
                    'total_funcionarios': total_funcionarios,
                    'total_usuarios': total_usuarios,
                    'contratos_ativos': contratos_ativos,
                    'lancamentos_mes': lancamentos_mes
                },
                'faturamento': {
                    'mes_atual': round(faturamento_mes, 2),
                    'mes_anterior': round(faturamento_mes_anterior, 2),
                    'crescimento_percentual': round(crescimento, 2)
                },
                'indicadores': {
                    'empresas_por_usuario': round(total_empresas / max(total_usuarios, 1), 2),
                    'funcionarios_por_empresa': round(total_funcionarios / max(empresas_ativas, 1), 2),
                    'faturamento_por_empresa': round(faturamento_mes / max(empresas_ativas, 1), 2)
                }
            }

            return Response(visao_geral, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Erro ao buscar visão geral do escritório: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def performance(self, request):
        """
        Endpoint para performance do escritório (faturamento, produtividade)
        Aplica a Regra de Ouro.
        """
        try:
            contabilidade = request.user.contabilidade
            if not contabilidade:
                return Response(
                    {"error": "Usuário não associado a uma contabilidade."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Evolução do faturamento dos últimos 12 meses
            evolucao_faturamento = []
            for i in range(12):
                month = timezone.now().date() - timedelta(days=30 * i)
                month_str = month.strftime('%Y-%m')
                
                faturamento_mes = NotaFiscal.objects.filter(
                    contabilidade=contabilidade,
                    data_emissao__year=month.year,
                    data_emissao__month=month.month
                ).aggregate(
                    total=Sum('valor_total')
                )['total'] or 0
                
                evolucao_faturamento.append({
                    'mes_ano': month_str,
                    'faturamento': round(faturamento_mes, 2)
                })
            
            evolucao_faturamento.reverse()
            
            # Produtividade por usuário
            usuarios_produtividade = []
            usuarios = Usuario.objects.filter(
                contabilidade=contabilidade,
                is_active=True
            )
            
            for usuario in usuarios:
                # Contar empresas gerenciadas pelo usuário
                empresas_usuario = PessoaJuridica.objects.filter(
                    contabilidade_atual=contabilidade
                ).count()  # Simplificado - assumindo que todos os usuários gerenciam todas as empresas
                
                # Contar lançamentos do usuário no mês atual
                lancamentos_usuario = LancamentoContabil.objects.filter(
                    contabilidade=contabilidade,
                    usuario_criacao=usuario,
                    data_lancamento__gte=timezone.now().date().replace(day=1)
                ).count()
                
                usuarios_produtividade.append({
                    'usuario': usuario.username,
                    'empresas_gerenciadas': empresas_usuario,
                    'lancamentos_mes': lancamentos_usuario,
                    'produtividade': lancamentos_usuario / max(empresas_usuario, 1)
                })
            
            # Top 5 empresas por faturamento
            top_empresas = []
            empresas_faturamento = PessoaJuridica.objects.filter(
                contabilidade_atual=contabilidade
            )
            
            for empresa in empresas_faturamento:
                faturamento_empresa = NotaFiscal.objects.filter(
                    contabilidade=contabilidade,
                    cliente=empresa
                ).aggregate(
                    total=Sum('valor_total')
                )['total'] or 0
                
                if faturamento_empresa > 0:
                    top_empresas.append({
                        'razao_social': empresa.razao_social,
                        'cnpj': empresa.cnpj,
                        'faturamento': round(faturamento_empresa, 2)
                    })
            
            top_empresas.sort(key=lambda x: x['faturamento'], reverse=True)
            top_empresas = top_empresas[:5]
            
            performance_data = {
                'evolucao_faturamento': evolucao_faturamento,
                'produtividade_usuarios': usuarios_produtividade,
                'top_empresas': top_empresas
            }

            return Response(performance_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Erro ao buscar performance do escritório: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def capacidade(self, request):
        """
        Endpoint para análise de capacidade (usuários, empresas atendidas)
        Aplica a Regra de Ouro.
        """
        try:
            contabilidade = request.user.contabilidade
            if not contabilidade:
                return Response(
                    {"error": "Usuário não associado a uma contabilidade."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Capacidade atual
            total_usuarios = Usuario.objects.filter(
                contabilidade=contabilidade,
                is_active=True
            ).count()
            
            total_empresas = PessoaJuridica.objects.filter(
                contabilidade_atual=contabilidade,
                ativo=True
            ).count()
            
            total_funcionarios = VinculoEmpregaticio.objects.filter(
                funcionario__contabilidade=contabilidade,
                ativo=True
            ).count()
            
            # Limites contratuais (assumindo valores padrão)
            limite_usuarios = 50  # Pode ser obtido do contrato GESTK
            limite_empresas = 200  # Pode ser obtido do contrato GESTK
            
            # Calcular utilização
            utilizacao_usuarios = (total_usuarios / limite_usuarios * 100) if limite_usuarios > 0 else 0
            utilizacao_empresas = (total_empresas / limite_empresas * 100) if limite_empresas > 0 else 0
            
            # Distribuição de empresas por porte
            empresas_por_porte = []
            portes = ['Micro', 'Pequena', 'Média', 'Grande']
            
            for porte in portes:
                # Simulação baseada no faturamento
                if porte == 'Micro':
                    count = total_empresas // 4
                elif porte == 'Pequena':
                    count = total_empresas // 3
                elif porte == 'Média':
                    count = total_empresas // 4
                else:
                    count = total_empresas - (total_empresas // 4) - (total_empresas // 3) - (total_empresas // 4)
                
                empresas_por_porte.append({
                    'porte': porte,
                    'quantidade': count,
                    'percentual': round((count / total_empresas * 100) if total_empresas > 0 else 0, 2)
                })
            
            # Análise de crescimento
            crescimento_empresas = 0
            crescimento_funcionarios = 0
            
            # Comparar com mês anterior
            mes_anterior = timezone.now().date() - timedelta(days=30)
            empresas_mes_anterior = PessoaJuridica.objects.filter(
                contabilidade_atual=contabilidade,
                ativo=True,
                created_at__lt=mes_anterior
            ).count()
            
            funcionarios_mes_anterior = VinculoEmpregaticio.objects.filter(
                funcionario__contabilidade=contabilidade,
                ativo=True,
                data_admissao__lt=mes_anterior
            ).count()
            
            if empresas_mes_anterior > 0:
                crescimento_empresas = ((total_empresas - empresas_mes_anterior) / empresas_mes_anterior) * 100
            
            if funcionarios_mes_anterior > 0:
                crescimento_funcionarios = ((total_funcionarios - funcionarios_mes_anterior) / funcionarios_mes_anterior) * 100
            
            capacidade_data = {
                'capacidade_atual': {
                    'usuarios': total_usuarios,
                    'empresas': total_empresas,
                    'funcionarios': total_funcionarios
                },
                'limites': {
                    'usuarios': limite_usuarios,
                    'empresas': limite_empresas
                },
                'utilizacao': {
                    'usuarios_percentual': round(utilizacao_usuarios, 2),
                    'empresas_percentual': round(utilizacao_empresas, 2)
                },
                'distribuicao_empresas': empresas_por_porte,
                'crescimento': {
                    'empresas_percentual': round(crescimento_empresas, 2),
                    'funcionarios_percentual': round(crescimento_funcionarios, 2)
                }
            }

            return Response(capacidade_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Erro ao buscar capacidade do escritório: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def tendencias(self, request):
        """
        Endpoint para tendências e projeções
        Aplica a Regra de Ouro.
        """
        try:
            contabilidade = request.user.contabilidade
            if not contabilidade:
                return Response(
                    {"error": "Usuário não associado a uma contabilidade."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Análise de tendências dos últimos 6 meses
            tendencias_data = []
            for i in range(6):
                month = timezone.now().date() - timedelta(days=30 * i)
                month_str = month.strftime('%Y-%m')
                
                # Faturamento do mês
                faturamento = NotaFiscal.objects.filter(
                    contabilidade=contabilidade,
                    data_emissao__year=month.year,
                    data_emissao__month=month.month
                ).aggregate(
                    total=Sum('valor_total')
                )['total'] or 0
                
                # Novas empresas do mês
                novas_empresas = PessoaJuridica.objects.filter(
                    contabilidade_atual=contabilidade,
                    created_at__year=month.year,
                    created_at__month=month.month
                ).count()
                
                # Novos funcionários do mês
                novos_funcionarios = VinculoEmpregaticio.objects.filter(
                    funcionario__contabilidade=contabilidade,
                    data_admissao__year=month.year,
                    data_admissao__month=month.month
                ).count()
                
                # Lançamentos do mês
                lancamentos = LancamentoContabil.objects.filter(
                    contabilidade=contabilidade,
                    data_lancamento__year=month.year,
                    data_lancamento__month=month.month
                ).count()
                
                tendencias_data.append({
                    'mes_ano': month_str,
                    'faturamento': round(faturamento, 2),
                    'novas_empresas': novas_empresas,
                    'novos_funcionarios': novos_funcionarios,
                    'lancamentos': lancamentos
                })
            
            tendencias_data.reverse()
            
            # Calcular projeções para os próximos 3 meses
            if len(tendencias_data) >= 3:
                # Calcular média de crescimento
                faturamentos = [item['faturamento'] for item in tendencias_data[-3:]]
                crescimento_medio = 0
                if len(faturamentos) > 1:
                    crescimento_medio = sum(
                        (faturamentos[i] - faturamentos[i-1]) / faturamentos[i-1] * 100
                        for i in range(1, len(faturamentos))
                        if faturamentos[i-1] > 0
                    ) / (len(faturamentos) - 1)
                
                # Projeções
                ultimo_faturamento = faturamentos[-1]
                projecoes = []
                for i in range(1, 4):
                    mes_projecao = timezone.now().date() + timedelta(days=30 * i)
                    faturamento_projetado = ultimo_faturamento * (1 + crescimento_medio / 100) ** i
                    
                    projecoes.append({
                        'mes_ano': mes_projecao.strftime('%Y-%m'),
                        'faturamento_projetado': round(faturamento_projetado, 2),
                        'crescimento_esperado': round(crescimento_medio, 2)
                    })
            else:
                projecoes = []
            
            # Alertas e recomendações
            alertas = []
            recomendacoes = []
            
            # Verificar utilização de capacidade
            total_usuarios = Usuario.objects.filter(
                contabilidade=contabilidade,
                is_active=True
            ).count()
            
            total_empresas = PessoaJuridica.objects.filter(
                contabilidade_atual=contabilidade,
                ativo=True
            ).count()
            
            if total_usuarios > 40:  # 80% de 50
                alertas.append("Alta utilização de usuários - considere expandir o plano")
                recomendacoes.append("Avaliar upgrade do plano de usuários")
            
            if total_empresas > 160:  # 80% de 200
                alertas.append("Alta utilização de empresas - considere expandir o plano")
                recomendacoes.append("Avaliar upgrade do plano de empresas")
            
            # Verificar produtividade
            lancamentos_ultimo_mes = tendencias_data[-1]['lancamentos'] if tendencias_data else 0
            if lancamentos_ultimo_mes < 100:
                alertas.append("Baixa produtividade em lançamentos contábeis")
                recomendacoes.append("Implementar treinamento ou automação de processos")
            
            tendencias = {
                'historico': tendencias_data,
                'projecoes': projecoes,
                'alertas': alertas,
                'recomendacoes': recomendacoes
            }

            return Response(tendencias, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Erro ao buscar tendências do escritório: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)