from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.funcionarios.models import VinculoEmpregaticio
from .serializers import *
from .services import OrganizacionalService

class OrganizacionalViewSet(viewsets.ViewSet):
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

    @action(detail=False, methods=['get'], url_path='departamentos')
    def departamentos(self, request):
        vinculos = self._get_base_queryset(request).filter(ativo=True)
        dados = OrganizacionalService.calcular_estrutura_departamentos(vinculos)
        serializer = EstruturaDepartamentoSerializer(dados, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='cargos')
    def cargos(self, request):
        vinculos = self._get_base_queryset(request).filter(ativo=True)
        dados = OrganizacionalService.calcular_estrutura_cargos(vinculos)
        serializer = EstruturaCargoSerializer(dados, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='hierarquia')
    def hierarquia(self, request):
        vinculos = self._get_base_queryset(request).filter(ativo=True)
        dados = OrganizacionalService.calcular_hierarquia(vinculos)
        serializer = HierarquiaOrganizacionalSerializer(dados)
        return Response(serializer.data)
