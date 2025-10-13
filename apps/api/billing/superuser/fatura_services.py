"""
Services para lógica de negócio de Faturas
"""

from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Q, Avg
from decimal import Decimal

from apps.billing.models import Fatura, Assinatura


class FaturaService:
    """
    Service para lógica de negócio de Faturas
    """
    
    @staticmethod
    @transaction.atomic
    def criar(dados):
        """
        Criar nova fatura com lógica de negócio
        
        Args:
            dados: dict com dados validados
            
        Returns:
            instance: Fatura criada
        """
        # Criar instância
        fatura = Fatura.objects.create(**dados)
        
        # Log de auditoria
        FaturaService._log_acao(
            fatura,
            'criacao',
            f'Fatura {fatura.numero_fatura} criada - Competência: {fatura.competencia}'
        )
        
        return fatura
    
    @staticmethod
    @transaction.atomic
    def atualizar(instance, dados):
        """
        Atualizar fatura com lógica de negócio
        
        Args:
            instance: Fatura a ser atualizada
            dados: dict com dados validados
            
        Returns:
            instance: Fatura atualizada
        """
        # Guardar estado anterior
        estado_anterior = {
            'valor_final': instance.valor_final,
            'status': instance.status,
            'data_vencimento': instance.data_vencimento,
        }
        
        # Atualizar campos
        for campo, valor in dados.items():
            setattr(instance, campo, valor)
        
        instance.save()
        
        # Processar mudanças importantes
        FaturaService._processar_mudancas(
            instance,
            estado_anterior
        )
        
        return instance
    
    @staticmethod
    @transaction.atomic
    def marcar_como_paga(instance, data_pagamento=None, metadados_pagamento=None):
        """
        Marcar fatura como paga
        
        Args:
            instance: Fatura a ser marcada como paga
            data_pagamento: data do pagamento (opcional, usa hoje se não fornecida)
            metadados_pagamento: dados adicionais do pagamento
        """
        from rest_framework.exceptions import ValidationError
        
        # Validar se pode marcar como paga
        if instance.status == 'paga':
            raise ValidationError('Fatura já está marcada como paga')
        
        if instance.status == 'cancelada':
            raise ValidationError('Não é possível marcar fatura cancelada como paga')
        
        # Definir data de pagamento
        if data_pagamento is None:
            data_pagamento = timezone.now().date()
        
        # Atualizar status
        instance.status = 'paga'
        instance.data_pagamento = data_pagamento
        
        # Adicionar metadados de pagamento
        if metadados_pagamento:
            if not instance.metadados:
                instance.metadados = {}
            instance.metadados['pagamento'] = metadados_pagamento
        
        instance.save()
        
        # Reativar assinatura se estava suspensa por inadimplência
        assinatura = instance.assinatura
        if assinatura.status == 'suspensa':
            # Verificar se não há outras faturas pendentes
            faturas_pendentes = assinatura.faturas.filter(
                status__in=['aberta', 'vencida']
            ).exclude(id=instance.id).count()
            
            if faturas_pendentes == 0:
                # Reativar assinatura
                assinatura.status = 'ativa'
                assinatura.motivo_suspensao = None
                assinatura.data_suspensao = None
                assinatura.save()
                
                # Reativar contabilidade
                assinatura.contabilidade.suspensa_por_inadimplencia = False
                assinatura.contabilidade.save()
        
        FaturaService._log_acao(
            instance,
            'pagamento',
            f'Fatura {instance.numero_fatura} marcada como paga'
        )
    
    @staticmethod
    @transaction.atomic
    def cancelar(instance, motivo):
        """
        Cancelar fatura
        
        Args:
            instance: Fatura a ser cancelada
            motivo: motivo do cancelamento
        """
        from rest_framework.exceptions import ValidationError
        
        # Validar se pode cancelar
        if instance.status == 'paga':
            raise ValidationError('Não é possível cancelar fatura já paga (use estornar)')
        
        if instance.status == 'cancelada':
            raise ValidationError('Fatura já está cancelada')
        
        # Cancelar
        instance.status = 'cancelada'
        
        # Adicionar motivo aos metadados
        if not instance.metadados:
            instance.metadados = {}
        instance.metadados['cancelamento'] = {
            'motivo': motivo,
            'data': timezone.now().isoformat()
        }
        
        instance.save()
        
        FaturaService._log_acao(
            instance,
            'cancelamento',
            f'Fatura {instance.numero_fatura} cancelada: {motivo}'
        )
    
    @staticmethod
    @transaction.atomic
    def estornar(instance, motivo):
        """
        Estornar fatura paga
        
        Args:
            instance: Fatura a ser estornada
            motivo: motivo do estorno
        """
        from rest_framework.exceptions import ValidationError
        
        # Validar se pode estornar
        if instance.status != 'paga':
            raise ValidationError('Apenas faturas pagas podem ser estornadas')
        
        # Estornar
        instance.status = 'estornada'
        instance.data_pagamento = None
        
        # Adicionar motivo aos metadados
        if not instance.metadados:
            instance.metadados = {}
        instance.metadados['estorno'] = {
            'motivo': motivo,
            'data': timezone.now().isoformat()
        }
        
        instance.save()
        
        FaturaService._log_acao(
            instance,
            'estorno',
            f'Fatura {instance.numero_fatura} estornada: {motivo}'
        )
    
    @staticmethod
    @transaction.atomic
    def reabrir(instance):
        """
        Reabrir fatura cancelada
        
        Args:
            instance: Fatura a ser reaberta
        """
        from rest_framework.exceptions import ValidationError
        
        # Validar se pode reabrir
        if instance.status not in ['cancelada', 'estornada']:
            raise ValidationError('Apenas faturas canceladas ou estornadas podem ser reabertas')
        
        # Verificar se está vencida
        if instance.data_vencimento < timezone.now().date():
            instance.status = 'vencida'
        else:
            instance.status = 'aberta'
        
        instance.save()
        
        FaturaService._log_acao(
            instance,
            'reabertura',
            f'Fatura {instance.numero_fatura} reaberta'
        )
    
    @staticmethod
    def processar_vencimentos():
        """
        Processar faturas vencidas (atualizar status)
        Task para ser executada diariamente
        
        Returns:
            dict com estatísticas do processamento
        """
        hoje = timezone.now().date()
        
        # Buscar faturas abertas vencidas
        faturas_vencidas = Fatura.objects.filter(
            status='aberta',
            data_vencimento__lt=hoje
        )
        
        count = faturas_vencidas.count()
        
        # Atualizar status
        faturas_vencidas.update(status='vencida')
        
        # Identificar assinaturas com faturas vencidas há mais de X dias
        dias_suspensao = 15
        data_limite = hoje - timedelta(days=dias_suspensao)
        
        assinaturas_suspender = Assinatura.objects.filter(
            faturas__status='vencida',
            faturas__data_vencimento__lt=data_limite,
            status='ativa'
        ).distinct()
        
        assinaturas_count = 0
        for assinatura in assinaturas_suspender:
            assinatura.status = 'suspensa'
            assinatura.motivo_suspensao = f'Inadimplência - Faturas vencidas há mais de {dias_suspensao} dias'
            assinatura.data_suspensao = hoje
            assinatura.save()
            
            # Suspender contabilidade
            assinatura.contabilidade.suspensa_por_inadimplencia = True
            assinatura.contabilidade.save()
            
            assinaturas_count += 1
        
        return {
            'faturas_vencidas': count,
            'assinaturas_suspensas': assinaturas_count,
            'data_processamento': hoje
        }
    
    @staticmethod
    def calcular_estatisticas(queryset):
        """
        Calcular estatísticas de faturas
        
        Args:
            queryset: QuerySet filtrado
            
        Returns:
            dict com estatísticas
        """
        total = queryset.count()
        
        # Contadores por status
        por_status = {
            'aberta': queryset.filter(status='aberta').count(),
            'paga': queryset.filter(status='paga').count(),
            'vencida': queryset.filter(status='vencida').count(),
            'cancelada': queryset.filter(status='cancelada').count(),
            'estornada': queryset.filter(status='estornada').count(),
        }
        
        # Valores
        valor_total = queryset.aggregate(Sum('valor_final'))['valor_final__sum'] or Decimal('0')
        valor_pago = queryset.filter(status='paga').aggregate(Sum('valor_final'))['valor_final__sum'] or Decimal('0')
        valor_pendente = queryset.filter(status__in=['aberta', 'vencida']).aggregate(Sum('valor_final'))['valor_final__sum'] or Decimal('0')
        
        # Faturas próximas do vencimento (7 dias)
        data_limite = timezone.now().date() + timedelta(days=7)
        proximas_vencimento = queryset.filter(
            status='aberta',
            data_vencimento__lte=data_limite,
            data_vencimento__gte=timezone.now().date()
        ).count()
        
        return {
            'total': total,
            'por_status': por_status,
            'percentuais': {
                'paga': round((por_status['paga'] / total * 100) if total > 0 else 0, 2),
                'pendente': round(((por_status['aberta'] + por_status['vencida']) / total * 100) if total > 0 else 0, 2),
                'vencida': round((por_status['vencida'] / total * 100) if total > 0 else 0, 2),
            },
            'valores': {
                'total': float(valor_total),
                'pago': float(valor_pago),
                'pendente': float(valor_pendente),
            },
            'alertas': {
                'proximas_vencimento': proximas_vencimento,
                'vencidas': por_status['vencida'],
            }
        }
    
    # Métodos privados (helper methods)
    
    @staticmethod
    def _processar_mudancas(instance, estado_anterior):
        """Processar mudanças importantes"""
        mudancas = []
        
        if estado_anterior['valor_final'] != instance.valor_final:
            mudancas.append(f'Valor alterado de R$ {estado_anterior["valor_final"]} para R$ {instance.valor_final}')
        
        if estado_anterior['status'] != instance.status:
            mudancas.append(f'Status alterado de {estado_anterior["status"]} para {instance.status}')
        
        if estado_anterior['data_vencimento'] != instance.data_vencimento:
            mudancas.append(f'Vencimento alterado de {estado_anterior["data_vencimento"]} para {instance.data_vencimento}')
        
        if mudancas:
            FaturaService._log_acao(
                instance,
                'atualizacao',
                '; '.join(mudancas)
            )
    
    @staticmethod
    def _log_acao(instance, acao, mensagem):
        """Log de ação para auditoria"""
        print(f"[AUDIT FATURA] {acao.upper()}: {mensagem} - Fatura: {instance.numero_fatura}")
