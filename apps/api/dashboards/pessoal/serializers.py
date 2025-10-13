from rest_framework import serializers

class RubricaSerializer(serializers.Serializer):
    tipo = serializers.CharField()
    descricao = serializers.CharField()
    total_valor = serializers.DecimalField(max_digits=15, decimal_places=2)
    quantidade_lancamentos = serializers.IntegerField()

class CustoPorFuncionarioSerializer(serializers.Serializer):
    funcionario_nome = serializers.CharField()
    salario_base = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_proventos = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_descontos = serializers.DecimalField(max_digits=10, decimal_places=2)
    custo_total = serializers.DecimalField(max_digits=10, decimal_places=2)

class IndicadoresFolhaSerializer(serializers.Serializer):
    total_funcionarios = serializers.IntegerField()
    total_proventos = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_descontos = serializers.DecimalField(max_digits=15, decimal_places=2)
    folha_liquida = serializers.DecimalField(max_digits=15, decimal_places=2)
    media_salarial = serializers.DecimalField(max_digits=10, decimal_places=2)
