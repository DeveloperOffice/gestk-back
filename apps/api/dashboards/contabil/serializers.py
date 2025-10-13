from rest_framework import serializers

class IndicadoresContabeisSerializer(serializers.Serializer):
    total_lancamentos = serializers.IntegerField()
    total_debitos = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_creditos = serializers.DecimalField(max_digits=15, decimal_places=2)
    saldo = serializers.DecimalField(max_digits=15, decimal_places=2)

class LancamentoPorGrupoSerializer(serializers.Serializer):
    grupo = serializers.CharField()
    total_debitos = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_creditos = serializers.DecimalField(max_digits=15, decimal_places=2)
    saldo = serializers.DecimalField(max_digits=15, decimal_places=2)

class BalanceteSerializer(serializers.Serializer):
    conta_codigo = serializers.CharField()
    conta_nome = serializers.CharField()
    saldo_anterior = serializers.DecimalField(max_digits=15, decimal_places=2)
    debitos = serializers.DecimalField(max_digits=15, decimal_places=2)
    creditos = serializers.DecimalField(max_digits=15, decimal_places=2)
    saldo_atual = serializers.DecimalField(max_digits=15, decimal_places=2)
