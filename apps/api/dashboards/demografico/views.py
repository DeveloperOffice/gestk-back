from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from apps.funcionarios.models import VinculoEmpregaticio
from .serializers import *
from .services import DemograficoService
from .filters import VinculoEmpregaticioFilterSet

class DemograficoViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = VinculoEmpregaticioFilterSet

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
        filterset = self.filterset_class(request.GET, queryset=vinculos)
        if filterset.is_valid():
            vinculos = filterset.qs
        indicadores = DemograficoService.calcular_indicadores(vinculos)
        serializer = IndicadoresDemograficosSerializer(indicadores)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='evolucao-mensal')
    def evolucao_mensal(self, request):
        vinculos = self._get_base_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=vinculos)
        if filterset.is_valid():
            vinculos = filterset.qs
        meses = int(request.query_params.get('meses', 12))
        evolucao = DemograficoService.calcular_evolucao_mensal(vinculos, meses)
        serializer = EvolucaoColaboradoresSerializer(evolucao, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='colaboradores')
    def colaboradores(self, request):
        vinculos = self._get_base_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=vinculos)
        if filterset.is_valid():
            vinculos = filterset.qs
        vinculos = vinculos.select_related('funcionario', 'funcionario__pessoa_fisica', 'cargo', 'departamento', 'empresa')
        colaboradores = []
        for vinculo in vinculos:
            func = vinculo.funcionario
            pf = func.pessoa_fisica
            colaboradores.append({
                'id': func.id,
                'nome': pf.nome_completo if pf else 'N/A',
                'cpf': pf.cpf if pf else 'N/A',
                'data_nascimento': func.data_nascimento,
                'idade': DemograficoService.calcular_idade(func.data_nascimento),
                'genero': func.genero,
                'escolaridade': func.escolaridade,
                'cargo': vinculo.cargo.nome if vinculo.cargo else None,
                'departamento': vinculo.departamento.nome if vinculo.departamento else None,
                'data_admissao': vinculo.data_admissao,
                'data_demissao': vinculo.data_demissao,
                'ativo': vinculo.ativo,
                'empresa': vinculo.empresa.razao_social if vinculo.empresa else None,
            })
        serializer = ColaboradorListaSerializer(colaboradores, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='distribuicao-etaria')
    def distribuicao_etaria(self, request):
        vinculos = self._get_base_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=vinculos)
        if filterset.is_valid():
            vinculos = filterset.qs
        distribuicao = DemograficoService.calcular_distribuicao_etaria(vinculos)
        serializer = DistribuicaoEtariaSerializer(distribuicao, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='distribuicao-genero')
    def distribuicao_genero(self, request):
        vinculos = self._get_base_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=vinculos)
        if filterset.is_valid():
            vinculos = filterset.qs
        distribuicao = DemograficoService.calcular_distribuicao_genero(vinculos)
        serializer = DistribuicaoGeneroSerializer(distribuicao, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='distribuicao-escolaridade')
    def distribuicao_escolaridade(self, request):
        vinculos = self._get_base_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=vinculos)
        if filterset.is_valid():
            vinculos = filterset.qs
        distribuicao = DemograficoService.calcular_distribuicao_escolaridade(vinculos)
        serializer = DistribuicaoEscolaridadeSerializer(distribuicao, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='distribuicao-cargo')
    def distribuicao_cargo(self, request):
        vinculos = self._get_base_queryset(request)
        filterset = self.filterset_class(request.GET, queryset=vinculos)
        if filterset.is_valid():
            vinculos = filterset.qs
        distribuicao = DemograficoService.calcular_distribuicao_cargo(vinculos)
        serializer = DistribuicaoCargoSerializer(distribuicao, many=True)
        return Response(serializer.data)
