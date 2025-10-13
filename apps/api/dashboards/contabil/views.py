from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.contabil.models import LancamentoContabil
from datetime import date, timedelta
from .serializers import *
from .services import ContabilService

class ContabilViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _get_base_queryset(self, request):
        user = request.user
        if user.tipo_usuario == 'superuser':
            return LancamentoContabil.objects.all()
        elif user.tipo_usuario == 'admin':
            return LancamentoContabil.objects.filter(contabilidade=user.contabilidade)
        else:
            if hasattr(user, 'contrato') and user.contrato:
                return LancamentoContabil.objects.filter(contrato=user.contrato)
            return LancamentoContabil.objects.none()

    @action(detail=False, methods=['get'], url_path='indicadores')
    def indicadores(self, request):
        lancamentos = self._get_base_queryset(request)
        dados = ContabilService.calcular_indicadores(lancamentos)
        serializer = IndicadoresContabeisSerializer(dados)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='balancete')
    def balancete(self, request):
        data_inicio = request.query_params.get('data_inicio', (date.today() - timedelta(days=30)).isoformat())
        data_fim = request.query_params.get('data_fim', date.today().isoformat())
        
        lancamentos = self._get_base_queryset(request)
        dados = ContabilService.calcular_balancete(lancamentos, data_inicio, data_fim)
        serializer = BalanceteSerializer(dados, many=True)
        return Response(serializer.data)
