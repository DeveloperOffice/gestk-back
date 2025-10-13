"""
Services para lógica de negócio de Contratos GESTK
Contratos entre GESTK e contabilidades clientes (SaaS)
"""

from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Q, Avg

from apps.administracao.models import ContratoGestk


class ContratoGestkService:
    """
    Service para lógica de negócio de Contratos GESTK
    """
    
    @staticmethod
    @transaction.atomic
    def criar(dados, usuario):
        """
        Criar novo contrato GESTK com lógica de negócio
        
        Args:
            dados: dict com dados validados
            usuario: usuário que está criando
            
        Returns:
            instance: ContratoGestk criado
        """
        # Adicionar informações de auditoria
        dados['created_by'] = usuario
        
        # Criar instância
        contrato = ContratoGestk.objects.create(**dados)
        
        # Log de auditoria
        ContratoGestkService._log_acao(
            contrato,
            'criacao',
            usuario,
            f'Contrato GESTK {contrato.numero_contrato} criado'
        )
        
        return contrato
    
    @staticmethod
    @transaction.atomic
    def atualizar(instance, dados, usuario):
        """
        Atualizar contrato com lógica de negócio
        
        Args:
            instance: ContratoGestk a ser atualizado
            dados: dict com dados validados
            usuario: usuário que está atualizando
            
        Returns:
            instance: ContratoGestk atualizado
        """
        # Guardar estado anterior
        estado_anterior = {
            'plano_servico': instance.plano_servico,
            'valor_mensal': instance.valor_mensal,
            'limites_usuarios': instance.limites_usuarios,
        }
        
        # Atualizar campos
        for campo, valor in dados.items():
            setattr(instance, campo, valor)
        
        instance.save()
        
        # Processar mudanças importantes
        ContratoGestkService._processar_mudancas(
            instance,
            estado_anterior,
            usuario
        )
        
        return instance
    
    @staticmethod
    @transaction.atomic
    def renovar(instance, usuario, nova_data_termino=None, novo_valor=None):
        """
        Renovar contrato
        
        Args:
            instance: ContratoGestk a ser renovado
            usuario: usuário que está renovando
            nova_data_termino: nova data de término (opcional)
            novo_valor: novo valor mensal (opcional)
        """
        from rest_framework.exceptions import ValidationError
        
        # Validar se pode renovar
        if instance.status == 'cancelado':
            raise ValidationError('Não é possível renovar contrato cancelado')
        
        # Calcular nova data de renovação
        if nova_data_termino:
            instance.data_termino = nova_data_termino
        else:
            # Renovar por mais 12 meses
            if instance.data_termino:
                instance.data_termino = instance.data_termino + timedelta(days=365)
            else:
                instance.data_termino = timezone.now().date() + timedelta(days=365)
        
        # Atualizar valor se fornecido
        if novo_valor:
            instance.valor_mensal = novo_valor
        
        # Definir nova data de renovação
        instance.data_renovacao = instance.data_termino - timedelta(days=30)
        
        # Reativar se necessário
        if instance.status in ['suspenso', 'vencido']:
            instance.status = 'ativo'
            instance.motivo_suspensao = None
            instance.data_suspensao = None
        
        instance.save()
        
        ContratoGestkService._log_acao(
            instance,
            'renovacao',
            usuario,
            f'Contrato renovado até {instance.data_termino}'
        )
    
    @staticmethod
    @transaction.atomic
    def suspender(instance, motivo, usuario):
        """
        Suspender contrato
        
        Args:
            instance: ContratoGestk a ser suspenso
            motivo: motivo da suspensão
            usuario: usuário que está suspendendo
        """
        instance.status = 'suspenso'
        instance.motivo_suspensao = motivo
        instance.data_suspensao = timezone.now().date()
        instance.save()
        
        # Suspender também a contabilidade
        instance.contabilidade.suspensa_por_inadimplencia = True
        instance.contabilidade.save()
        
        ContratoGestkService._log_acao(
            instance,
            'suspensao',
            usuario,
            f'Contrato suspenso: {motivo}'
        )
    
    @staticmethod
    @transaction.atomic
    def reativar(instance, usuario):
        """
        Reativar contrato suspenso
        
        Args:
            instance: ContratoGestk a ser reativado
            usuario: usuário que está reativando
        """
        from rest_framework.exceptions import ValidationError
        
        if instance.status != 'suspenso':
            raise ValidationError('Apenas contratos suspensos podem ser reativados')
        
        instance.status = 'ativo'
        instance.motivo_suspensao = None
        instance.data_suspensao = None
        instance.save()
        
        # Reativar também a contabilidade
        instance.contabilidade.suspensa_por_inadimplencia = False
        instance.contabilidade.save()
        
        ContratoGestkService._log_acao(
            instance,
            'reativacao',
            usuario,
            'Contrato reativado'
        )
    
    @staticmethod
    @transaction.atomic
    def cancelar(instance, motivo, usuario):
        """
        Cancelar contrato
        
        Args:
            instance: ContratoGestk a ser cancelado
            motivo: motivo do cancelamento
            usuario: usuário que está cancelando
        """
        instance.status = 'cancelado'
        instance.motivo_cancelamento = motivo
        instance.data_cancelamento = timezone.now().date()
        instance.save()
        
        ContratoGestkService._log_acao(
            instance,
            'cancelamento',
            usuario,
            f'Contrato cancelado: {motivo}'
        )
    
    @staticmethod
    def calcular_estatisticas(instance, data_inicio=None, data_fim=None):
        """
        Calcular estatísticas do contrato
        
        Args:
            instance: ContratoGestk
            data_inicio: data inicial (opcional)
            data_fim: data final (opcional)
            
        Returns:
            dict com estatísticas
        """
        # Definir período
        if not data_inicio:
            data_inicio = instance.data_inicio
        if not data_fim:
            data_fim = timezone.now().date()
        
        # Uso de recursos
        usuarios = instance.contabilidade.usuarios.filter(ativo=True)
        contratos_internos = instance.contabilidade.contratos.filter(ativo=True)
        
        # Estatísticas financeiras (faturas)
        from apps.billing.models import Fatura
        faturas = Fatura.objects.filter(
            assinatura__contabilidade=instance.contabilidade,
            data_emissao__gte=data_inicio,
            data_emissao__lte=data_fim
        )
        
        total_faturado = faturas.aggregate(Sum('valor_final'))['valor_final__sum'] or 0
        total_pago = faturas.filter(status='paga').aggregate(Sum('valor_final'))['valor_final__sum'] or 0
        
        # Tempo de contrato
        dias_contrato = (data_fim - instance.data_inicio).days
        
        return {
            'periodo': {
                'data_inicio': data_inicio,
                'data_fim': data_fim,
                'dias_contrato': dias_contrato,
            },
            'uso_recursos': {
                'usuarios': {
                    'usado': usuarios.count(),
                    'limite': instance.limites_usuarios,
                    'percentual': round((usuarios.count() / instance.limites_usuarios * 100) if instance.limites_usuarios > 0 else 0, 2),
                    'disponivel': max(0, instance.limites_usuarios - usuarios.count())
                },
                'contratos_internos': {
                    'usado': contratos_internos.count(),
                    'limite': instance.limites_contratos_internos,
                    'percentual': round((contratos_internos.count() / instance.limites_contratos_internos * 100) if instance.limites_contratos_internos > 0 else 0, 2),
                    'disponivel': max(0, instance.limites_contratos_internos - contratos_internos.count())
                }
            },
            'financeiro': {
                'valor_mensal_contratado': float(instance.valor_mensal),
                'total_faturado': float(total_faturado),
                'total_pago': float(total_pago),
                'total_pendente': float(total_faturado - total_pago),
                'faturas': {
                    'total': faturas.count(),
                    'pagas': faturas.filter(status='paga').count(),
                    'pendentes': faturas.filter(status='aberta').count(),
                    'vencidas': faturas.filter(status='vencida').count(),
                }
            },
            'status_contrato': {
                'status': instance.status,
                'status_display': instance.get_status_display(),
                'esta_vencido': instance.esta_vencido,
                'esta_em_trial': bool(instance.trial_ate and instance.trial_ate >= timezone.now().date()),
                'dias_ate_vencimento': (instance.data_termino - timezone.now().date()).days if instance.data_termino else None,
            }
        }
    
    @staticmethod
    def calcular_resumo(queryset):
        """
        Calcular resumo geral de contratos GESTK
        
        Args:
            queryset: QuerySet filtrado
            
        Returns:
            dict com resumo
        """
        total = queryset.count()
        
        # Contadores por status
        por_status = {
            'trial': queryset.filter(status='trial').count(),
            'ativo': queryset.filter(status='ativo').count(),
            'suspenso': queryset.filter(status='suspenso').count(),
            'cancelado': queryset.filter(status='cancelado').count(),
            'vencido': queryset.filter(status='vencido').count(),
        }
        
        # Contratos próximos do vencimento (30 dias)
        data_limite = timezone.now().date() + timedelta(days=30)
        proximos_vencimento = queryset.filter(
            data_termino__lte=data_limite,
            data_termino__gte=timezone.now().date(),
            status='ativo'
        ).count()
        
        # Valores
        valor_mensal_total = queryset.filter(
            status__in=['trial', 'ativo']
        ).aggregate(Sum('valor_mensal'))['valor_mensal__sum'] or 0
        
        valor_anual_estimado = float(valor_mensal_total) * 12
        
        return {
            'total': total,
            'por_status': por_status,
            'percentuais': {
                'trial': round((por_status['trial'] / total * 100) if total > 0 else 0, 2),
                'ativo': round((por_status['ativo'] / total * 100) if total > 0 else 0, 2),
                'suspenso': round((por_status['suspenso'] / total * 100) if total > 0 else 0, 2),
            },
            'alertas': {
                'proximos_vencimento': proximos_vencimento,
            },
            'financeiro': {
                'receita_mensal_recorrente': float(valor_mensal_total),
                'receita_anual_estimada': valor_anual_estimado,
            }
        }
    
    # Métodos privados (helper methods)
    
    @staticmethod
    def _processar_mudancas(instance, estado_anterior, usuario):
        """Processar mudanças importantes"""
        mudancas = []
        
        if estado_anterior['plano_servico'] != instance.plano_servico:
            mudancas.append(f'Plano alterado de {estado_anterior["plano_servico"]} para {instance.plano_servico}')
        
        if estado_anterior['valor_mensal'] != instance.valor_mensal:
            mudancas.append(f'Valor alterado de R$ {estado_anterior["valor_mensal"]} para R$ {instance.valor_mensal}')
        
        if estado_anterior['limites_usuarios'] != instance.limites_usuarios:
            mudancas.append(f'Limite de usuários alterado de {estado_anterior["limites_usuarios"]} para {instance.limites_usuarios}')
        
        if mudancas:
            ContratoGestkService._log_acao(
                instance,
                'atualizacao',
                usuario,
                '; '.join(mudancas)
            )
    
    @staticmethod
    def _log_acao(instance, acao, usuario, mensagem):
        """Log de ação para auditoria"""
        # TODO: Implementar sistema de log de auditoria
        print(f"[AUDIT GESTK] {acao.upper()}: {mensagem} - Contrato: {instance.numero_contrato} - Usuário: {usuario.username}")
