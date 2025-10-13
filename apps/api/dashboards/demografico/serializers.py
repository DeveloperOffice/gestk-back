"""
Serializers para Dashboard Demográfico
"""
from rest_framework import serializers


class IndicadoresDemograficosSerializer(serializers.Serializer):
    """Serializer para indicadores demográficos gerais"""
    total_colaboradores = serializers.IntegerField()
    colaboradores_ativos = serializers.IntegerField()
    colaboradores_inativos = serializers.IntegerField()
    admissoes_mes = serializers.IntegerField()
    demissoes_mes = serializers.IntegerField()
    turnover_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    idade_media = serializers.DecimalField(max_digits=5, decimal_places=2)
    tempo_medio_empresa = serializers.DecimalField(max_digits=5, decimal_places=2)


class EvolucaoColaboradoresSerializer(serializers.Serializer):
    """Serializer para evolução mensal de colaboradores"""
    mes = serializers.CharField()
    total = serializers.IntegerField()
    admissoes = serializers.IntegerField()
    demissoes = serializers.IntegerField()


class ColaboradorListaSerializer(serializers.Serializer):
    """Serializer para listagem de colaboradores"""
    id = serializers.UUIDField()
    nome = serializers.CharField()
    cpf = serializers.CharField()
    data_nascimento = serializers.DateField(allow_null=True)
    idade = serializers.IntegerField(allow_null=True)
    genero = serializers.CharField(allow_null=True)
    escolaridade = serializers.CharField(allow_null=True)
    cargo = serializers.CharField(allow_null=True)
    departamento = serializers.CharField(allow_null=True)
    data_admissao = serializers.DateField(allow_null=True)
    data_demissao = serializers.DateField(allow_null=True)
    ativo = serializers.BooleanField()
    empresa = serializers.CharField(allow_null=True)


class DistribuicaoEtariaSerializer(serializers.Serializer):
    """Serializer para distribuição por faixa etária"""
    faixa_etaria = serializers.CharField()
    quantidade = serializers.IntegerField()
    percentual = serializers.DecimalField(max_digits=5, decimal_places=2)


class DistribuicaoGeneroSerializer(serializers.Serializer):
    """Serializer para distribuição por gênero"""
    genero = serializers.CharField()
    quantidade = serializers.IntegerField()
    percentual = serializers.DecimalField(max_digits=5, decimal_places=2)


class DistribuicaoEscolaridadeSerializer(serializers.Serializer):
    """Serializer para distribuição por escolaridade"""
    escolaridade = serializers.CharField()
    quantidade = serializers.IntegerField()
    percentual = serializers.DecimalField(max_digits=5, decimal_places=2)


class DistribuicaoCargoSerializer(serializers.Serializer):
    """Serializer para distribuição por cargo"""
    cargo = serializers.CharField()
    quantidade = serializers.IntegerField()
    percentual = serializers.DecimalField(max_digits=5, decimal_places=2)
