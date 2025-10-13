from rest_framework import serializers

class IndicadoresFiscaisSerializer(serializers.Serializer):
    total_notas = serializers.IntegerField()
    notas_entrada = serializers.IntegerField()
    notas_saida = serializers.IntegerField()
    valor_total_entrada = serializers.DecimalField(max_digits=15, decimal_places=2)
    valor_total_saida = serializers.DecimalField(max_digits=15, decimal_places=2)
    faturamento_liquido = serializers.DecimalField(max_digits=15, decimal_places=2)

class NotaFiscalResumoSerializer(serializers.Serializer):
    tipo = serializers.CharField()
    quantidade = serializers.IntegerField()
    valor_total = serializers.DecimalField(max_digits=15, decimal_places=2)

class TopClientesSerializer(serializers.Serializer):
    cliente_nome = serializers.CharField()
    cliente_cnpj = serializers.CharField(allow_null=True)
    total_notas = serializers.IntegerField()
    valor_total = serializers.DecimalField(max_digits=15, decimal_places=2)

class ImpostosSerializer(serializers.Serializer):
    tipo_imposto = serializers.CharField()
    valor_total = serializers.DecimalField(max_digits=15, decimal_places=2)
