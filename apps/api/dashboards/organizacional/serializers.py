from rest_framework import serializers

class EstruturaDepartamentoSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    nome = serializers.CharField()
    total_funcionarios = serializers.IntegerField()
    percentual = serializers.DecimalField(max_digits=5, decimal_places=2)

class EstruturaCargoSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    nome = serializers.CharField()
    cbo_2002 = serializers.CharField(allow_null=True)
    total_funcionarios = serializers.IntegerField()
    departamento = serializers.CharField(allow_null=True)

class HierarquiaOrganizacionalSerializer(serializers.Serializer):
    total_departamentos = serializers.IntegerField()
    total_cargos = serializers.IntegerField()
    total_funcionarios = serializers.IntegerField()
    media_funcionarios_por_departamento = serializers.DecimalField(max_digits=5, decimal_places=2)

class DistribuicaoPorAreaSerializer(serializers.Serializer):
    area = serializers.CharField()
    total = serializers.IntegerField()
    percentual = serializers.DecimalField(max_digits=5, decimal_places=2)
