from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from datetime import timedelta, date

from apps.core.models import Contabilidade
from apps.funcionarios.models import Funcionario, VinculoEmpregaticio, Rubrica


class PessoalViewSet(viewsets.ViewSet):
    """ViewSet para dashboards de recursos humanos"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def folha_pagamento(self, request):
        """
        Endpoint para resumo da folha de pagamento
        Aplica a Regra de Ouro.
        """
        try:
            contabilidade = request.user.contabilidade
            if not contabilidade:
                return Response(
                    {"error": "Usuário não associado a uma contabilidade."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Buscar vínculos ativos
            vinculos_ativos = VinculoEmpregaticio.objects.filter(
                funcionario__contabilidade=contabilidade,
                ativo=True
            )
            
            # Calcular totais da folha
            total_colaboradores = vinculos_ativos.count()
            total_salarios = vinculos_ativos.aggregate(
                total=Sum('salario_base')
            )['total'] or 0
            
            salario_medio = vinculos_ativos.aggregate(
                medio=Avg('salario_base')
            )['medio'] or 0
            
            # Calcular encargos sociais (estimativa de 30% sobre salários)
            encargos_sociais = total_salarios * 0.30
            custo_total_folha = total_salarios + encargos_sociais
            
            # Distribuição por faixa salarial
            faixas_salariais = [
                {'faixa': 'Até R$ 1.500', 'min': 0, 'max': 1500, 'total_colaboradores': 0},
                {'faixa': 'R$ 1.501 - R$ 3.000', 'min': 1501, 'max': 3000, 'total_colaboradores': 0},
                {'faixa': 'R$ 3.001 - R$ 5.000', 'min': 3001, 'max': 5000, 'total_colaboradores': 0},
                {'faixa': 'R$ 5.001 - R$ 10.000', 'min': 5001, 'max': 10000, 'total_colaboradores': 0},
                {'faixa': 'Acima de R$ 10.000', 'min': 10001, 'max': 999999, 'total_colaboradores': 0}
            ]
            
            for vinculo in vinculos_ativos:
                salario = vinculo.salario_base or 0
                for faixa in faixas_salariais:
                    if faixa['min'] <= salario <= faixa['max']:
                        faixa['total_colaboradores'] += 1
                        break
            
            # Calcular percentuais
            for faixa in faixas_salariais:
                faixa['percentual'] = (faixa['total_colaboradores'] / total_colaboradores * 100) if total_colaboradores > 0 else 0

            folha_data = {
                'resumo': {
                    'total_colaboradores': total_colaboradores,
                    'total_salarios': round(total_salarios, 2),
                    'salario_medio': round(salario_medio, 2),
                    'encargos_sociais': round(encargos_sociais, 2),
                    'custo_total_folha': round(custo_total_folha, 2)
                },
                'distribuicao_salarial': faixas_salariais
            }

            return Response(folha_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Erro ao buscar dados da folha de pagamento: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def beneficios(self, request):
        """
        Endpoint para benefícios por tipo
        Aplica a Regra de Ouro.
        """
        try:
            contabilidade = request.user.contabilidade
            if not contabilidade:
                return Response(
                    {"error": "Usuário não associado a uma contabilidade."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Buscar rubricas de benefícios (proventos)
            rubricas_beneficios = Rubrica.objects.filter(
                contabilidade=contabilidade,
                tipo='P',  # Proventos
                ativo=True
            )
            
            beneficios_data = []
            for rubrica in rubricas_beneficios:
                # Contar quantos funcionários recebem este benefício
                vinculos_com_beneficio = VinculoEmpregaticio.objects.filter(
                    funcionario__contabilidade=contabilidade,
                    ativo=True
                ).count()  # Simplificado - assumindo que todos recebem
                
                beneficios_data.append({
                    'nome': rubrica.nome,
                    'tipo': 'Provento',
                    'incide_inss': rubrica.incide_inss,
                    'incide_irrf': rubrica.incide_irrf,
                    'incide_fgts': rubrica.incide_fgts,
                    'total_funcionarios': vinculos_com_beneficio
                })

            return Response(beneficios_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Erro ao buscar dados de benefícios: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def custos_trabalhistas(self, request):
        """
        Endpoint para custos trabalhistas totais
        Aplica a Regra de Ouro.
        """
        try:
            contabilidade = request.user.contabilidade
            if not contabilidade:
                return Response(
                    {"error": "Usuário não associado a uma contabilidade."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Buscar vínculos ativos
            vinculos_ativos = VinculoEmpregaticio.objects.filter(
                funcionario__contabilidade=contabilidade,
                ativo=True
            )
            
            total_salarios = vinculos_ativos.aggregate(
                total=Sum('salario_base')
            )['total'] or 0
            
            # Calcular encargos trabalhistas (estimativas)
            inss_empresa = total_salarios * 0.20  # 20% INSS Patronal
            fgts = total_salarios * 0.08  # 8% FGTS
            terceiros = total_salarios * 0.05  # 5% Terceiros (SESI, SENAI, etc.)
            outros_encargos = total_salarios * 0.02  # 2% Outros encargos
            
            total_encargos = inss_empresa + fgts + terceiros + outros_encargos
            custo_total = total_salarios + total_encargos
            
            custos_data = {
                'salarios_base': round(total_salarios, 2),
                'encargos': {
                    'inss_empresa': round(inss_empresa, 2),
                    'fgts': round(fgts, 2),
                    'terceiros': round(terceiros, 2),
                    'outros': round(outros_encargos, 2),
                    'total': round(total_encargos, 2)
                },
                'custo_total': round(custo_total, 2),
                'percentual_encargos': round((total_encargos / total_salarios * 100) if total_salarios > 0 else 0, 2)
            }

            return Response(custos_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Erro ao buscar custos trabalhistas: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def evolucao_folha(self, request):
        """
        Endpoint para evolução mensal da folha de pagamento
        Aplica a Regra de Ouro.
        """
        try:
            contabilidade = request.user.contabilidade
            if not contabilidade:
                return Response(
                    {"error": "Usuário não associado a uma contabilidade."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Simular evolução mensal dos últimos 12 meses
            evolucao_data = []
            for i in range(12):
                month = timezone.now().date() - timedelta(days=30 * i)
                month_str = month.strftime('%Y-%m')
                
                # Buscar vínculos ativos no mês
                vinculos_mes = VinculoEmpregaticio.objects.filter(
                    funcionario__contabilidade=contabilidade,
                    data_admissao__lte=month
                ).filter(
                    Q(data_demissao__isnull=True) | Q(data_demissao__gt=month)
                )
                
                total_colaboradores = vinculos_mes.count()
                total_salarios = vinculos_mes.aggregate(
                    total=Sum('salario_base')
                )['total'] or 0
                
                salario_medio = (total_salarios / total_colaboradores) if total_colaboradores > 0 else 0
                encargos = total_salarios * 0.30
                custo_total = total_salarios + encargos
                
                evolucao_data.append({
                    'mes_ano': month_str,
                    'total_colaboradores': total_colaboradores,
                    'total_salarios': round(total_salarios, 2),
                    'salario_medio': round(salario_medio, 2),
                    'encargos': round(encargos, 2),
                    'custo_total': round(custo_total, 2)
                })
            
            # Inverter para ordem cronológica crescente
            evolucao_data.reverse()

            return Response(evolucao_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Erro ao buscar evolução da folha: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
