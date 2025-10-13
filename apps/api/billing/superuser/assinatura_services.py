"""
Services para lógica de negócio de Assinaturas
"""

from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Q, Avg
from decimal import Decimal

from apps.billing.models import Assinatura, Plano, Fatura


class AssinaturaService:
    """
    Service para lógica de negócio de Assinaturas
    """
    
    @staticmethod
    @transaction.atomic
    def criar(dados, usuario):
        """
        Criar nova assinatura com lógica de negócio
        
        Args:
            dados: dict com dados validados
            usuario: usuário que está criando
            
        Returns:
            instance: Assinatura criada
        """
        # Adicionar informações de auditoria
        dados['created_by'] = usuario
        
        # Criar instância
        assinatura = Assinatura.objects.create(**dados)
        
        # Gerar primeira fatura se não estiver em trial
        if not assinatura.esta_em_trial:
            AssinaturaService._gerar_fatura_inicial(assinatura)
        
        # Log de auditoria
        AssinaturaService._log_acao(
            assinatura,
            'criacao',
            usuario,
            f'Assinatura criada - Plano: {assinatura.plano.nome}'
        )
        
        return assinatura
    
    @staticmethod
    @transaction.atomic
    def atualizar(instance, dados, usuario):
        """
        Atualizar assinatura com lógica de negócio
        
        Args:
            instance: Assinatura a ser atualizada
            dados: dict com dados validados
            usuario: usuário que está atualizando
            
        Returns:
            instance: Assinatura atualizada
        """
        # Guardar estado anterior
        estado_anterior = {
            'plano': instance.plano,
            'valor_mensal': instance.valor_mensal,
            'status': instance.status,
        }
        
        # Atualizar campos
        for campo, valor in dados.items():
            setattr(instance, campo, valor)
        
        instance.save()
        
        # Processar mudanças importantes
        AssinaturaService._processar_mudancas(
            instance,
            estado_anterior,
            usuario
        )
        
        return instance
    
    @staticmethod
    @transaction.atomic
    def renovar(instance, usuario, nova_data_fim=None, novo_valor=None):
        """
        Renovar assinatura
        
        Args:
            instance: Assinatura a ser renovada
            usuario: usuário que está renovando
            nova_data_fim: nova data de fim (opcional)
            novo_valor: novo valor mensal (opcional)
        """
        from rest_framework.exceptions import ValidationError
        
        # Validar se pode renovar
        if instance.status == 'cancelada':
            raise ValidationError('Não é possível renovar assinatura cancelada')
        
        # Calcular nova data de renovação
        if nova_data_fim:
            instance.data_fim = nova_data_fim
        else:
            # Renovar baseado no ciclo
            if instance.ciclo_cobranca == 'anual':
                dias = 365
            elif instance.ciclo_cobranca == 'semestral':
                dias = 180
            elif instance.ciclo_cobranca == 'trimestral':
                dias = 90
            else:  # mensal
                dias = 30
            
            if instance.data_fim:
                instance.data_fim = instance.data_fim + timedelta(days=dias)
            else:
                instance.data_fim = timezone.now().date() + timedelta(days=dias)
        
        # Atualizar valor se fornecido
        if novo_valor:
            instance.valor_mensal = novo_valor
        
        # Definir nova data de renovação
        instance.data_renovacao = instance.data_fim - timedelta(days=30)
        
        # Reativar se necessário
        if instance.status in ['suspensa', 'expirada']:
            instance.status = 'ativa'
            instance.motivo_suspensao = None
            instance.data_suspensao = None
        
        instance.save()
        
        AssinaturaService._log_acao(
            instance,
            'renovacao',
            usuario,
            f'Assinatura renovada até {instance.data_fim}'
        )
    
    @staticmethod
    @transaction.atomic
    def suspender(instance, motivo, usuario):
        """
        Suspender assinatura
        
        Args:
            instance: Assinatura a ser suspensa
            motivo: motivo da suspensão
            usuario: usuário que está suspendendo
        """
        instance.status = 'suspensa'
        instance.motivo_suspensao = motivo
        instance.data_suspensao = timezone.now().date()
        instance.save()
        
        # Suspender também a contabilidade
        instance.contabilidade.suspensa_por_inadimplencia = True
        instance.contabilidade.save()
        
        AssinaturaService._log_acao(
            instance,
            'suspensao',
            usuario,
            f'Assinatura suspensa: {motivo}'
        )
    
    @staticmethod
    @transaction.atomic
    def reativar(instance, usuario):
        """
        Reativar assinatura suspensa
        
        Args:
            instance: Assinatura a ser reativada
            usuario: usuário que está reativando
        """
        from rest_framework.exceptions import ValidationError
        
        if instance.status != 'suspensa':
            raise ValidationError('Apenas assinaturas suspensas podem ser reativadas')
        
        instance.status = 'ativa'
        instance.motivo_suspensao = None
        instance.data_suspensao = None
        instance.save()
        
        # Reativar também a contabilidade
        instance.contabilidade.suspensa_por_inadimplencia = False
        instance.contabilidade.save()
        
        AssinaturaService._log_acao(
            instance,
            'reativacao',
            usuario,
            'Assinatura reativada'
        )
    
    @staticmethod
    @transaction.atomic
    def cancelar(instance, motivo, usuario):
        """
        Cancelar assinatura
        
        Args:
            instance: Assinatura a ser cancelada
            motivo: motivo do cancelamento
            usuario: usuário que está cancelando
        """
        instance.status = 'cancelada'
        instance.motivo_cancelamento = motivo
        instance.data_cancelamento = timezone.now().date()
        instance.save()
        
        AssinaturaService._log_acao(
            instance,
            'cancelamento',
            usuario,
            f'Assinatura cancelada: {motivo}'
        )
    
    @staticmethod
    def gerar_fatura(instance, competencia, usuario):
        """
        Gerar fatura para uma competência específica
        
        Args:
            instance: Assinatura
            competencia: competência no formato YYYY-MM
            usuario: usuário que está gerando
            
        Returns:
            Fatura criada
        """
        from rest_framework.exceptions import ValidationError
        
        # Verificar se já existe fatura para essa competência
        if instance.faturas.filter(competencia=competencia).exists():
            raise ValidationError(f'Já existe fatura para a competência {competencia}')
        
        # Calcular valores
        if instance.ciclo_cobranca == 'anual':
            valor_original = instance.valor_anual or (instance.valor_mensal * 12)
        else:
            valor_original = instance.valor_mensal
        
        desconto = valor_original * (Decimal(str(instance.desconto_percentual)) / Decimal('100'))
        valor_final = valor_original - desconto
        
        # Gerar número da fatura
        ano_mes = competencia.replace('-', '')
        ultimo_numero = Fatura.objects.filter(
            numero_fatura__startswith=f'FAT-{ano_mes}'
        ).count()
        numero_fatura = f'FAT-{ano_mes}-{str(ultimo_numero + 1).zfill(4)}'
        
        # Calcular data de vencimento
        ano, mes = map(int, competencia.split('-'))
        data_vencimento = datetime(ano, mes, instance.dia_vencimento).date()
        
        # Criar fatura
        fatura = Fatura.objects.create(
            assinatura=instance,
            numero_fatura=numero_fatura,
            competencia=competencia,
            valor_original=valor_original,
            desconto=desconto,
            valor_final=valor_final,
            data_emissao=timezone.now().date(),
            data_vencimento=data_vencimento,
            status='aberta'
        )
        
        AssinaturaService._log_acao(
            instance,
            'geracao_fatura',
            usuario,
            f'Fatura {numero_fatura} gerada para competência {competencia}'
        )
        
        return fatura
    
    @staticmethod
    def calcular_estatisticas(instance):
        """
        Calcular estatísticas da assinatura
        
        Args:
            instance: Assinatura
            
        Returns:
            dict com estatísticas
        """
        faturas = instance.faturas.all()
        
        total_faturado = faturas.aggregate(Sum('valor_final'))['valor_final__sum'] or Decimal('0')
        total_pago = faturas.filter(status='paga').aggregate(Sum('valor_final'))['valor_final__sum'] or Decimal('0')
        
        # Tempo de assinatura
        if instance.data_inicio:
            dias_assinatura = (timezone.now().date() - instance.data_inicio).days
            meses_assinatura = dias_assinatura // 30
        else:
            dias_assinatura = 0
            meses_assinatura = 0
        
        return {
            'periodo': {
                'data_inicio': instance.data_inicio,
                'data_fim': instance.data_fim,
                'dias_assinatura': dias_assinatura,
                'meses_assinatura': meses_assinatura,
            },
            'financeiro': {
                'valor_mensal_contratado': float(instance.valor_mensal),
                'total_faturado': float(total_faturado),
                'total_pago': float(total_pago),
                'total_pendente': float(total_faturado - total_pago),
                'faturas': {
                    'total': faturas.count(),
                    'pagas': faturas.filter(status='paga').count(),
                    'abertas': faturas.filter(status='aberta').count(),
                    'vencidas': faturas.filter(status='vencida').count(),
                    'canceladas': faturas.filter(status='cancelada').count(),
                }
            },
            'status': {
                'status_atual': instance.status,
                'status_display': instance.get_status_display(),
                'esta_ativa': instance.esta_ativa,
                'esta_em_trial': instance.esta_em_trial,
                'dias_para_vencimento': instance.dias_para_vencimento,
            }
        }
    
    @staticmethod
    def calcular_resumo(queryset):
        """
        Calcular resumo geral de assinaturas
        
        Args:
            queryset: QuerySet filtrado
            
        Returns:
            dict com resumo
        """
        total = queryset.count()
        
        # Contadores por status
        por_status = {
            'ativa': queryset.filter(status='ativa').count(),
            'suspensa': queryset.filter(status='suspensa').count(),
            'cancelada': queryset.filter(status='cancelada').count(),
            'expirada': queryset.filter(status='expirada').count(),
            'trial': queryset.filter(status='trial').count(),
        }
        
        # Assinaturas próximas do vencimento (30 dias)
        data_limite = timezone.now().date() + timedelta(days=30)
        proximas_vencimento = queryset.filter(
            data_fim__lte=data_limite,
            data_fim__gte=timezone.now().date(),
            status='ativa'
        ).count()
        
        # Valores
        valor_mensal_total = queryset.filter(
            status__in=['ativa', 'trial']
        ).aggregate(Sum('valor_mensal'))['valor_mensal__sum'] or Decimal('0')
        
        # MRR (Monthly Recurring Revenue)
        mrr = float(valor_mensal_total)
        arr = mrr * 12  # ARR (Annual Recurring Revenue)
        
        return {
            'total': total,
            'por_status': por_status,
            'percentuais': {
                'ativa': round((por_status['ativa'] / total * 100) if total > 0 else 0, 2),
                'suspensa': round((por_status['suspensa'] / total * 100) if total > 0 else 0, 2),
                'cancelada': round((por_status['cancelada'] / total * 100) if total > 0 else 0, 2),
            },
            'alertas': {
                'proximas_vencimento': proximas_vencimento,
            },
            'financeiro': {
                'mrr': mrr,
                'arr': arr,
            }
        }
    
    # Métodos privados (helper methods)
    
    @staticmethod
    def _gerar_fatura_inicial(assinatura):
        """Gerar primeira fatura da assinatura"""
        competencia = assinatura.data_inicio.strftime('%Y-%m')
        
        # Calcular valores
        if assinatura.ciclo_cobranca == 'anual':
            valor_original = assinatura.valor_anual or (assinatura.valor_mensal * 12)
        else:
            valor_original = assinatura.valor_mensal
        
        desconto = valor_original * (Decimal(str(assinatura.desconto_percentual)) / Decimal('100'))
        valor_final = valor_original - desconto
        
        # Gerar número da fatura
        ano_mes = competencia.replace('-', '')
        ultimo_numero = Fatura.objects.filter(
            numero_fatura__startswith=f'FAT-{ano_mes}'
        ).count()
        numero_fatura = f'FAT-{ano_mes}-{str(ultimo_numero + 1).zfill(4)}'
        
        # Calcular data de vencimento
        data_vencimento = assinatura.data_inicio.replace(day=assinatura.dia_vencimento)
        if data_vencimento < assinatura.data_inicio:
            # Se o dia de vencimento já passou no mês, vence no próximo mês
            if data_vencimento.month == 12:
                data_vencimento = data_vencimento.replace(year=data_vencimento.year + 1, month=1)
            else:
                data_vencimento = data_vencimento.replace(month=data_vencimento.month + 1)
        
        # Criar fatura
        Fatura.objects.create(
            assinatura=assinatura,
            numero_fatura=numero_fatura,
            competencia=competencia,
            valor_original=valor_original,
            desconto=desconto,
            valor_final=valor_final,
            data_emissao=assinatura.data_inicio,
            data_vencimento=data_vencimento,
            status='aberta'
        )
    
    @staticmethod
    def _processar_mudancas(instance, estado_anterior, usuario):
        """Processar mudanças importantes"""
        mudancas = []
        
        if estado_anterior['plano'] != instance.plano:
            mudancas.append(f'Plano alterado de {estado_anterior["plano"].nome} para {instance.plano.nome}')
        
        if estado_anterior['valor_mensal'] != instance.valor_mensal:
            mudancas.append(f'Valor alterado de R$ {estado_anterior["valor_mensal"]} para R$ {instance.valor_mensal}')
        
        if estado_anterior['status'] != instance.status:
            mudancas.append(f'Status alterado de {estado_anterior["status"]} para {instance.status}')
        
        if mudancas:
            AssinaturaService._log_acao(
                instance,
                'atualizacao',
                usuario,
                '; '.join(mudancas)
            )
    
    @staticmethod
    def _log_acao(instance, acao, usuario, mensagem):
        """Log de ação para auditoria"""
        print(f"[AUDIT BILLING] {acao.upper()}: {mensagem} - Assinatura: {instance.id} - Usuário: {usuario.username}")
