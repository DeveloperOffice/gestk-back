from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from datetime import timedelta, date

from apps.core.models import Contabilidade
from apps.funcionarios.models import Funcionario, VinculoEmpregaticio, Departamento, Cargo
from apps.pessoas.models import PessoaJuridica


class OrganizacionalViewSet(viewsets.ViewSet):
    """ViewSet para dashboards organizacionais"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def estrutura(self, request):
        """
        Endpoint para estrutura organizacional (departamentos, cargos)
        Aplica a Regra de Ouro.
        """
        try:
            contabilidade = request.user.contabilidade
            if not contabilidade:
                return Response(
                    {"error": "Usuário não associado a uma contabilidade."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Buscar departamentos da contabilidade
            departamentos = Departamento.objects.filter(contabilidade=contabilidade, ativo=True)
            
            # Buscar cargos da contabilidade
            cargos = Cargo.objects.filter(contabilidade=contabilidade, ativo=True)
            
            # Estrutura organizacional
            estrutura_data = {
                'total_departamentos': departamentos.count(),
                'total_cargos': cargos.count(),
                'departamentos': [],
                'cargos': []
            }
            
            # Dados dos departamentos
            for depto in departamentos:
                vinculos_depto = VinculoEmpregaticio.objects.filter(
                    funcionario__contabilidade=contabilidade,
                    departamento=depto,
                    ativo=True
                )
                
                estrutura_data['departamentos'].append({
                    'id': str(depto.id),
                    'nome': depto.nome,
                    'total_colaboradores': vinculos_depto.count(),
                    'cargos_vinculados': vinculos_depto.values('cargo__nome').distinct().count()
                })
            
            # Dados dos cargos
            for cargo in cargos:
                vinculos_cargo = VinculoEmpregaticio.objects.filter(
                    funcionario__contabilidade=contabilidade,
                    cargo=cargo,
                    ativo=True
                )
                
                estrutura_data['cargos'].append({
                    'id': str(cargo.id),
                    'nome': cargo.nome,
                    'cbo_2002': cargo.cbo_2002,
                    'total_colaboradores': vinculos_cargo.count(),
                    'departamentos_vinculados': vinculos_cargo.values('departamento__nome').distinct().count()
                })

            return Response(estrutura_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Erro ao buscar estrutura organizacional: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def distribuicao_departamentos(self, request):
        """
        Endpoint para distribuição de colaboradores por departamento
        Aplica a Regra de Ouro.
        """
        try:
            contabilidade = request.user.contabilidade
            if not contabilidade:
                return Response(
                    {"error": "Usuário não associado a uma contabilidade."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Buscar distribuição por departamento
            distribuicao = VinculoEmpregaticio.objects.filter(
                funcionario__contabilidade=contabilidade,
                ativo=True
            ).values('departamento__nome').annotate(
                total_colaboradores=Count('id')
            ).order_by('-total_colaboradores')
            
            total_colaboradores = sum(item['total_colaboradores'] for item in distribuicao)
            
            distribuicao_data = []
            for item in distribuicao:
                depto_nome = item['departamento__nome'] or 'Sem Departamento'
                total = item['total_colaboradores']
                percentual = (total / total_colaboradores * 100) if total_colaboradores > 0 else 0
                
                distribuicao_data.append({
                    'departamento': depto_nome,
                    'total_colaboradores': total,
                    'percentual': round(percentual, 2)
                })

            return Response(distribuicao_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Erro ao buscar distribuição por departamento: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def hierarquia(self, request):
        """
        Endpoint para hierarquia organizacional
        Aplica a Regra de Ouro.
        """
        try:
            contabilidade = request.user.contabilidade
            if not contabilidade:
                return Response(
                    {"error": "Usuário não associado a uma contabilidade."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Buscar hierarquia por cargo (assumindo que cargos com nomes específicos são hierárquicos)
            hierarquia_data = []
            
            # Definir níveis hierárquicos baseados no nome do cargo
            niveis_hierarquicos = {
                'diretor': 1,
                'gerente': 2,
                'coordenador': 3,
                'supervisor': 4,
                'analista': 5,
                'assistente': 6,
                'auxiliar': 7
            }
            
            cargos_hierarquia = VinculoEmpregaticio.objects.filter(
                funcionario__contabilidade=contabilidade,
                ativo=True
            ).values('cargo__nome').annotate(
                total_colaboradores=Count('id')
            ).order_by('cargo__nome')
            
            for item in cargos_hierarquia:
                cargo_nome = item['cargo__nome'] or 'Sem Cargo'
                total = item['total_colaboradores']
                
                # Determinar nível hierárquico
                nivel = 8  # Padrão para cargos não identificados
                for palavra_chave, nivel_cargo in niveis_hierarquicos.items():
                    if palavra_chave.lower() in cargo_nome.lower():
                        nivel = nivel_cargo
                        break
                
                hierarquia_data.append({
                    'cargo': cargo_nome,
                    'nivel_hierarquico': nivel,
                    'total_colaboradores': total
                })
            
            # Ordenar por nível hierárquico
            hierarquia_data.sort(key=lambda x: x['nivel_hierarquico'])

            return Response(hierarquia_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Erro ao buscar hierarquia organizacional: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def custo_departamento(self, request):
        """
        Endpoint para custo por departamento
        Aplica a Regra de Ouro.
        """
        try:
            contabilidade = request.user.contabilidade
            if not contabilidade:
                return Response(
                    {"error": "Usuário não associado a uma contabilidade."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Calcular custo por departamento baseado nos salários
            custos_departamento = VinculoEmpregaticio.objects.filter(
                funcionario__contabilidade=contabilidade,
                ativo=True
            ).values('departamento__nome').annotate(
                total_colaboradores=Count('id'),
                custo_total=Sum('salario_base'),
                custo_medio=Avg('salario_base')
            ).order_by('-custo_total')
            
            total_custo_geral = sum(item['custo_total'] or 0 for item in custos_departamento)
            
            custo_data = []
            for item in custos_departamento:
                depto_nome = item['departamento__nome'] or 'Sem Departamento'
                total_colaboradores = item['total_colaboradores']
                custo_total = item['custo_total'] or 0
                custo_medio = item['custo_medio'] or 0
                percentual_custo = (custo_total / total_custo_geral * 100) if total_custo_geral > 0 else 0
                
                custo_data.append({
                    'departamento': depto_nome,
                    'total_colaboradores': total_colaboradores,
                    'custo_total': round(custo_total, 2),
                    'custo_medio': round(custo_medio, 2),
                    'percentual_custo': round(percentual_custo, 2)
                })

            return Response(custo_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Erro ao buscar custos por departamento: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
