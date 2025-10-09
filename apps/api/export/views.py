from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.db.models import Count, Sum, Avg
from django.utils import timezone

from apps.core.models import Contabilidade
from apps.pessoas.models import PessoaJuridica, Contrato
from apps.funcionarios.models import Funcionario, VinculoEmpregaticio
from apps.fiscal.models import NotaFiscal
from .services import PDFExporter, ExcelExporter


class ExportViewSet(viewsets.ViewSet):
    """ViewSet para exportação de dados"""
    permission_classes = [IsAuthenticated]

    def _get_contabilidade(self, request):
        """Helper para obter contabilidade do usuário"""
        contabilidade = request.user.contabilidade
        if not contabilidade:
            raise ValueError("Usuário não associado a uma contabilidade.")
        return contabilidade

    @action(detail=False, methods=['post'])
    def carteira_pdf(self, request):
        """
        Exporta dados da carteira para PDF
        """
        try:
            contabilidade = self._get_contabilidade(request)
            
            # Buscar dados da carteira
            empresas = PessoaJuridica.objects.filter(
                contabilidade_atual=contabilidade
            ).select_related('cnae_principal')
            
            # Calcular estatísticas
            total_empresas = empresas.count()
            empresas_ativas = empresas.filter(ativo=True).count()
            empresas_inativas = total_empresas - empresas_ativas
            
            # Calcular total de funcionários
            total_funcionarios = VinculoEmpregaticio.objects.filter(
                funcionario__contabilidade=contabilidade,
                ativo=True
            ).count()
            
            # Calcular faturamento total
            faturamento_total = NotaFiscal.objects.filter(
                contabilidade=contabilidade
            ).aggregate(
                total=Sum('valor_total')
            )['total'] or 0
            
            # Preparar dados para export
            carteira_data = {
                'resumo': {
                    'total_empresas': total_empresas,
                    'empresas_ativas': empresas_ativas,
                    'empresas_inativas': empresas_inativas,
                    'total_funcionarios': total_funcionarios,
                    'faturamento_total': float(faturamento_total)
                },
                'empresas': []
            }
            
            # Dados das empresas
            for empresa in empresas[:100]:  # Limitar a 100 empresas
                funcionarios_empresa = VinculoEmpregaticio.objects.filter(
                    funcionario__contabilidade=contabilidade,
                    empresa=empresa,
                    ativo=True
                ).count()
                
                carteira_data['empresas'].append({
                    'razao_social': empresa.razao_social,
                    'cnpj': empresa.cnpj,
                    'ativo': empresa.ativo,
                    'total_funcionarios': funcionarios_empresa,
                    'cnae': empresa.cnae_principal.descricao if empresa.cnae_principal else 'Não informado'
                })
            
            # Gerar PDF
            exporter = PDFExporter("Relatório de Carteira")
            pdf_buffer = exporter.export_carteira(carteira_data, contabilidade.razao_social)
            
            # Retornar PDF
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="carteira_{contabilidade.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
            return response
            
        except Exception as e:
            return Response({"error": f"Erro ao gerar PDF da carteira: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def carteira_excel(self, request):
        """
        Exporta dados da carteira para Excel
        """
        try:
            contabilidade = self._get_contabilidade(request)
            
            # Buscar dados da carteira (mesmo código do PDF)
            empresas = PessoaJuridica.objects.filter(
                contabilidade_atual=contabilidade
            ).select_related('cnae_principal')
            
            # Calcular estatísticas
            total_empresas = empresas.count()
            empresas_ativas = empresas.filter(ativo=True).count()
            empresas_inativas = total_empresas - empresas_ativas
            
            total_funcionarios = VinculoEmpregaticio.objects.filter(
                funcionario__contabilidade=contabilidade,
                ativo=True
            ).count()
            
            faturamento_total = NotaFiscal.objects.filter(
                contabilidade=contabilidade
            ).aggregate(
                total=Sum('valor_total')
            )['total'] or 0
            
            # Preparar dados para export
            carteira_data = {
                'resumo': {
                    'total_empresas': total_empresas,
                    'empresas_ativas': empresas_ativas,
                    'empresas_inativas': empresas_inativas,
                    'total_funcionarios': total_funcionarios,
                    'faturamento_total': float(faturamento_total)
                },
                'empresas': []
            }
            
            for empresa in empresas:
                funcionarios_empresa = VinculoEmpregaticio.objects.filter(
                    funcionario__contabilidade=contabilidade,
                    empresa=empresa,
                    ativo=True
                ).count()
                
                carteira_data['empresas'].append({
                    'razao_social': empresa.razao_social,
                    'cnpj': empresa.cnpj,
                    'ativo': empresa.ativo,
                    'total_funcionarios': funcionarios_empresa,
                    'cnae': empresa.cnae_principal.descricao if empresa.cnae_principal else 'Não informado'
                })
            
            # Gerar Excel
            exporter = ExcelExporter()
            excel_buffer = exporter.export_carteira(carteira_data, contabilidade.razao_social)
            
            # Retornar Excel
            response = HttpResponse(excel_buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="carteira_{contabilidade.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
            return response
            
        except Exception as e:
            return Response({"error": f"Erro ao gerar Excel da carteira: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def clientes_pdf(self, request):
        """
        Exporta dados de clientes para PDF
        """
        try:
            contabilidade = self._get_contabilidade(request)
            
            # Buscar clientes com maior faturamento
            contratos = Contrato.objects.filter(contabilidade=contabilidade, ativo=True)
            
            clientes_data = []
            for contrato in contratos:
                cliente = contrato.cliente
                if not cliente:
                    continue
                
                # Calcular faturamento do cliente
                notas_cliente = NotaFiscal.objects.filter(
                    contabilidade=contabilidade,
                    cliente=cliente
                )
                
                total_faturamento = sum(nota.valor_total or 0 for nota in notas_cliente)
                quantidade_notas = notas_cliente.count()
                
                if total_faturamento > 0:
                    clientes_data.append({
                        'nome': cliente.razao_social if hasattr(cliente, 'razao_social') else cliente.nome_completo,
                        'documento': cliente.cnpj if hasattr(cliente, 'cnpj') else cliente.cpf,
                        'total_transacoes': total_faturamento,
                        'quantidade_transacoes': quantidade_notas
                    })
            
            # Ordenar por faturamento
            clientes_data.sort(key=lambda x: x['total_transacoes'], reverse=True)
            
            # Gerar PDF
            exporter = PDFExporter("Relatório de Clientes")
            pdf_buffer = exporter.export_clientes(clientes_data, contabilidade.razao_social)
            
            # Retornar PDF
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="clientes_{contabilidade.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
            return response
            
        except Exception as e:
            return Response({"error": f"Erro ao gerar PDF de clientes: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def clientes_excel(self, request):
        """
        Exporta dados de clientes para Excel
        """
        try:
            contabilidade = self._get_contabilidade(request)
            
            # Buscar clientes (mesmo código do PDF)
            contratos = Contrato.objects.filter(contabilidade=contabilidade, ativo=True)
            
            clientes_data = []
            for contrato in contratos:
                cliente = contrato.cliente
                if not cliente:
                    continue
                
                notas_cliente = NotaFiscal.objects.filter(
                    contabilidade=contabilidade,
                    cliente=cliente
                )
                
                total_faturamento = sum(nota.valor_total or 0 for nota in notas_cliente)
                quantidade_notas = notas_cliente.count()
                
                if total_faturamento > 0:
                    clientes_data.append({
                        'nome': cliente.razao_social if hasattr(cliente, 'razao_social') else cliente.nome_completo,
                        'documento': cliente.cnpj if hasattr(cliente, 'cnpj') else cliente.cpf,
                        'total_transacoes': total_faturamento,
                        'quantidade_transacoes': quantidade_notas
                    })
            
            clientes_data.sort(key=lambda x: x['total_transacoes'], reverse=True)
            
            # Gerar Excel
            exporter = ExcelExporter()
            excel_buffer = exporter.export_clientes(clientes_data, contabilidade.razao_social)
            
            # Retornar Excel
            response = HttpResponse(excel_buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="clientes_{contabilidade.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
            return response
            
        except Exception as e:
            return Response({"error": f"Erro ao gerar Excel de clientes: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def relatorio_geral_pdf(self, request):
        """
        Exporta relatório geral para PDF
        """
        try:
            contabilidade = self._get_contabilidade(request)
            
            # Coletar dados de diferentes módulos
            dados_gerais = {}
            
            # Dados demográficos
            funcionarios = Funcionario.objects.filter(contabilidade=contabilidade, ativo=True)
            vinculos_ativos = VinculoEmpregaticio.objects.filter(
                funcionario__contabilidade=contabilidade,
                ativo=True
            )
            
            dados_gerais['demograficos'] = [
                {'indicador': 'Total de Funcionários', 'valor': funcionarios.count()},
                {'indicador': 'Vínculos Ativos', 'valor': vinculos_ativos.count()},
                {'indicador': 'Média Salarial', 'valor': f"R$ {vinculos_ativos.aggregate(media=Avg('salario_base'))['media'] or 0:,.2f}"}
            ]
            
            # Dados fiscais
            notas_fiscais = NotaFiscal.objects.filter(contabilidade=contabilidade)
            total_faturamento = notas_fiscais.aggregate(total=Sum('valor_total'))['total'] or 0
            
            dados_gerais['fiscais'] = [
                {'indicador': 'Total de Notas Fiscais', 'valor': notas_fiscais.count()},
                {'indicador': 'Faturamento Total', 'valor': f"R$ {total_faturamento:,.2f}"},
                {'indicador': 'Média por Nota', 'valor': f"R$ {(total_faturamento / max(notas_fiscais.count(), 1)):,.2f}"}
            ]
            
            # Dados organizacionais
            departamentos = vinculos_ativos.values('departamento__nome').annotate(
                total=Count('id')
            ).order_by('-total')
            
            dados_gerais['organizacionais'] = [
                {'departamento': item['departamento__nome'] or 'Sem Departamento', 'total_funcionarios': item['total']}
                for item in departamentos[:10]
            ]
            
            # Gerar PDF
            exporter = PDFExporter("Relatório Geral")
            pdf_buffer = exporter.export_relatorio_geral(dados_gerais, contabilidade.razao_social)
            
            # Retornar PDF
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="relatorio_geral_{contabilidade.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
            return response
            
        except Exception as e:
            return Response({"error": f"Erro ao gerar PDF do relatório geral: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def relatorio_geral_excel(self, request):
        """
        Exporta relatório geral para Excel
        """
        try:
            contabilidade = self._get_contabilidade(request)
            
            # Coletar dados (mesmo código do PDF)
            dados_gerais = {}
            
            funcionarios = Funcionario.objects.filter(contabilidade=contabilidade, ativo=True)
            vinculos_ativos = VinculoEmpregaticio.objects.filter(
                funcionario__contabilidade=contabilidade,
                ativo=True
            )
            
            dados_gerais['demograficos'] = [
                {'indicador': 'Total de Funcionários', 'valor': funcionarios.count()},
                {'indicador': 'Vínculos Ativos', 'valor': vinculos_ativos.count()},
                {'indicador': 'Média Salarial', 'valor': vinculos_ativos.aggregate(media=Avg('salario_base'))['media'] or 0}
            ]
            
            notas_fiscais = NotaFiscal.objects.filter(contabilidade=contabilidade)
            total_faturamento = notas_fiscais.aggregate(total=Sum('valor_total'))['total'] or 0
            
            dados_gerais['fiscais'] = [
                {'indicador': 'Total de Notas Fiscais', 'valor': notas_fiscais.count()},
                {'indicador': 'Faturamento Total', 'valor': total_faturamento},
                {'indicador': 'Média por Nota', 'valor': total_faturamento / max(notas_fiscais.count(), 1)}
            ]
            
            departamentos = vinculos_ativos.values('departamento__nome').annotate(
                total=Count('id')
            ).order_by('-total')
            
            dados_gerais['organizacionais'] = [
                {'departamento': item['departamento__nome'] or 'Sem Departamento', 'total_funcionarios': item['total']}
                for item in departamentos[:10]
            ]
            
            # Gerar Excel
            exporter = ExcelExporter()
            excel_buffer = exporter.export_relatorio_geral(dados_gerais, contabilidade.razao_social)
            
            # Retornar Excel
            response = HttpResponse(excel_buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="relatorio_geral_{contabilidade.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
            return response
            
        except Exception as e:
            return Response({"error": f"Erro ao gerar Excel do relatório geral: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
