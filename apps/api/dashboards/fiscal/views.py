from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.fiscal.models import NotaFiscal
from .serializers import *
from .services import FiscalService

class FiscalViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _get_base_queryset(self, request):
        user = request.user
        if user.tipo_usuario == 'superuser':
            return NotaFiscal.objects.all()
        elif user.tipo_usuario == 'admin':
            return NotaFiscal.objects.filter(contabilidade=user.contabilidade)
        else:
            if hasattr(user, 'contrato') and user.contrato:
                from django.contrib.contenttypes.models import ContentType
                ct = ContentType.objects.get_for_model(user.contrato.cliente.__class__)
                return NotaFiscal.objects.filter(
                    contabilidade=user.contrato.contabilidade
                )
            return NotaFiscal.objects.none()

    @action(detail=False, methods=['get'], url_path='indicadores')
    def indicadores(self, request):
        notas = self._get_base_queryset(request)
        dados = FiscalService.calcular_indicadores(notas)
        serializer = IndicadoresFiscaisSerializer(dados)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='resumo-por-tipo')
    def resumo_por_tipo(self, request):
        notas = self._get_base_queryset(request)
        tipos = notas.values('tipo_nota').annotate(
            quantidade=Count('id'),
            valor_total=Sum('valor_total')
        )
        dados = [{
            'tipo': t['tipo_nota'],
            'quantidade': t['quantidade'],
            'valor_total': t['valor_total'] or 0
        } for t in tipos]
        serializer = NotaFiscalResumoSerializer(dados, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='top-clientes')
    def top_clientes(self, request):
        limit = int(request.query_params.get('limit', 10))
        notas = self._get_base_queryset(request)
        dados = FiscalService.calcular_top_clientes(notas, limit)
        serializer = TopClientesSerializer(dados, many=True)
        return Response(serializer.data)
