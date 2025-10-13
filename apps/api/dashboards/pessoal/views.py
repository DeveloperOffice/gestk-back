from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.funcionarios.models import VinculoEmpregaticio
from .serializers import *
from .services import PessoalService

class PessoalViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _get_base_queryset(self, request):
        user = request.user
        if user.tipo_usuario == 'superuser':
            return VinculoEmpregaticio.objects.all()
        elif user.tipo_usuario == 'admin':
            return VinculoEmpregaticio.objects.filter(contabilidade=user.contabilidade)
        else:
            if hasattr(user, 'contrato') and user.contrato:
                return VinculoEmpregaticio.objects.filter(
                    contabilidade=user.contrato.contabilidade,
                    empresa=user.contrato.cliente
                )
            return VinculoEmpregaticio.objects.none()

    @action(detail=False, methods=['get'], url_path='indicadores')
    def indicadores(self, request):
        vinculos = self._get_base_queryset(request)
        dados = PessoalService.calcular_indicadores_folha(vinculos)
        serializer = IndicadoresFolhaSerializer(dados)
        return Response(serializer.data)
