"""
Services para lógica de negócio de Contabilidades
"""

from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Q, Avg

from apps.core.models import Contabilidade


class ContabilidadeService:
    """
    Service para lógica de negócio de Contabilidades
    """
    
    @staticmethod
    @transaction.atomic
    def criar(dados, usuario):
        """
        Criar nova contabilidade com lógica de negócio
        
        Args:
            dados: dict com dados validados
            usuario: usuário que está criando
            
        Returns:
            instance: Contabilidade criada
        """
        # Criar instância
        contabilidade = Contabilidade.objects.create(**dados)
        
        # Log de auditoria
        ContabilidadeService._log_acao(
            contabilidade,
            'criacao',
            usuario,
            'Contabilidade criada'
        )
        
        return contabilidade
    
    @staticmethod
    @transaction.atomic
    def atualizar(instance, dados, usuario):
        """
        Atualizar contabilidade com lógica de negócio
        
        Args:
            instance: Contabilidade a ser atualizada
            dados: dict com dados validados
            usuario: usuário que está atualizando
            
        Returns:
            instance: Contabilidade atualizada
        """
        # Guardar estado anterior
        estado_anterior = {
            'ativo': instance.ativo,
            'suspensa_por_inadimplencia': instance.suspensa_por_inadimplencia,
        }
        
        # Atualizar campos
        for campo, valor in dados.items():
            setattr(instance, campo, valor)
        
        instance.save()
        
        # Processar mudanças importantes
        ContabilidadeService._processar_mudancas(
            instance,
            estado_anterior,
            usuario
        )
        
        return instance
    
    @staticmethod
    @transaction.atomic
    def deletar(instance, usuario):
        """
        Deletar contabilidade (soft delete)
        
        Args:
            instance: Contabilidade a ser deletada
            usuario: usuário que está deletando
        """
        from rest_framework.exceptions import ValidationError
        
        # Validar se pode deletar
        usuarios_ativos = instance.usuarios.filter(ativo=True).count()
        if usuarios_ativos > 0:
            raise ValidationError(
                f'Não é possível deletar. Existem {usuarios_ativos} usuários ativos.'
            )
        
        contratos_ativos = instance.contratos.filter(ativo=True).count()
        if contratos_ativos > 0:
            raise ValidationError(
                f'Não é possível deletar. Existem {contratos_ativos} contratos ativos com clientes.'
            )
        
        # Soft delete
        instance.ativo = False
        instance.save()
        
        # Log
        ContabilidadeService._log_acao(
            instance,
            'exclusao',
            usuario,
            'Contabilidade desativada'
        )
    
    @staticmethod
    def ativar(instance, usuario):
        """Ativar contabilidade"""
        instance.ativo = True
        instance.suspensa_por_inadimplencia = False
        instance.save()
        
        ContabilidadeService._log_acao(
            instance,
            'ativacao',
            usuario,
            'Contabilidade ativada'
        )
    
    @staticmethod
    def desativar(instance, usuario):
        """Desativar contabilidade"""
        instance.ativo = False
        instance.save()
        
        ContabilidadeService._log_acao(
            instance,
            'desativacao',
            usuario,
            'Contabilidade desativada'
        )
    
    @staticmethod
    def suspender_por_inadimplencia(instance, usuario):
        """Suspender contabilidade por inadimplência"""
        instance.suspensa_por_inadimplencia = True
        instance.save()
        
        ContabilidadeService._log_acao(
            instance,
            'suspensao',
            usuario,
            'Contabilidade suspensa por inadimplência'
        )
    
    @staticmethod
    def liberar_inadimplencia(instance, usuario):
        """Liberar contabilidade da inadimplência"""
        instance.suspensa_por_inadimplencia = False
        instance.save()
        
        ContabilidadeService._log_acao(
            instance,
            'liberacao',
            usuario,
            'Contabilidade liberada da inadimplência'
        )
    
    @staticmethod
    def calcular_estatisticas(instance, data_inicio=None, data_fim=None):
        """
        Calcular estatísticas da contabilidade
        
        Args:
            instance: Contabilidade
            data_inicio: data inicial (opcional)
            data_fim: data final (opcional)
            
        Returns:
            dict com estatísticas
        """
        from apps.pessoas.models import Contrato
        
        # Definir período
        if not data_inicio:
            data_inicio = timezone.now().date() - timedelta(days=30)
        if not data_fim:
            data_fim = timezone.now().date()
        
        # Estatísticas de usuários
        usuarios = instance.usuarios.all()
        usuarios_ativos = usuarios.filter(ativo=True)
        
        # Estatísticas de contratos (clientes da contabilidade)
        contratos = Contrato.objects.filter(
            contabilidade=instance,
            data_inicio__lte=data_fim,
        ).filter(
            Q(data_termino__gte=data_inicio) | Q(data_termino__isnull=True)
        )
        
        # Estatísticas financeiras
        # TODO: Implementar quando modelo Cobranca for criado
        # from apps.billing.models import Cobranca
        # cobrancas = Cobranca.objects.filter(
        #     contabilidade=instance,
        #     data_vencimento__gte=data_inicio,
        #     data_vencimento__lte=data_fim
        # )
        cobrancas_count = 0
        cobrancas_valor_total = 0
        cobrancas_pagas = 0
        cobrancas_pendentes = 0
        cobrancas_vencidas = 0
        
        return {
            'periodo': {
                'data_inicio': data_inicio,
                'data_fim': data_fim,
            },
            'usuarios': {
                'total': usuarios.count(),
                'ativos': usuarios_ativos.count(),
                'inativos': usuarios.filter(ativo=False).count(),
                'por_tipo': {
                    'superuser': usuarios_ativos.filter(tipo_usuario='superuser').count(),
                    'admin': usuarios_ativos.filter(tipo_usuario='admin').count(),
                    'operacional': usuarios_ativos.filter(tipo_usuario='operacional').count(),
                    'etl': usuarios_ativos.filter(tipo_usuario='etl').count(),
                    'readonly': usuarios_ativos.filter(tipo_usuario='readonly').count(),
                }
            },
            'contratos': {
                'total': contratos.count(),
                'ativos': contratos.filter(ativo=True).count(),
                'inativos': contratos.filter(ativo=False).count(),
            },
            'financeiro': {
                'total_cobrancas': cobrancas_count,
                'valor_total': cobrancas_valor_total,
                'pagas': cobrancas_pagas,
                'pendentes': cobrancas_pendentes,
                'vencidas': cobrancas_vencidas,
                'saldo_creditos': instance.saldo_creditos,
            }
        }
    
    @staticmethod
    def calcular_resumo(queryset):
        """
        Calcular resumo geral de contabilidades
        
        Args:
            queryset: QuerySet filtrado
            
        Returns:
            dict com resumo
        """
        total = queryset.count()
        ativas = queryset.filter(ativo=True).count()
        inativas = queryset.filter(ativo=False).count()
        suspensas = queryset.filter(suspensa_por_inadimplencia=True).count()
        
        return {
            'total': total,
            'ativas': ativas,
            'inativas': inativas,
            'suspensas_inadimplencia': suspensas,
            'percentual_ativas': round((ativas / total * 100) if total > 0 else 0, 2),
            'saldo_creditos_total': queryset.aggregate(
                Sum('saldo_creditos')
            )['saldo_creditos__sum'] or 0,
        }
    
    # Métodos privados (helper methods)
    
    @staticmethod
    def _processar_mudancas(instance, estado_anterior, usuario):
        """Processar mudanças importantes"""
        # Se mudou status de ativo
        if estado_anterior['ativo'] != instance.ativo:
            acao = 'ativacao' if instance.ativo else 'desativacao'
            mensagem = f'Contabilidade {"ativada" if instance.ativo else "desativada"}'
            ContabilidadeService._log_acao(instance, acao, usuario, mensagem)
        
        # Se mudou status de inadimplência
        if estado_anterior['suspensa_por_inadimplencia'] != instance.suspensa_por_inadimplencia:
            acao = 'suspensao' if instance.suspensa_por_inadimplencia else 'liberacao'
            mensagem = f'Contabilidade {"suspensa" if instance.suspensa_por_inadimplencia else "liberada"}'
            ContabilidadeService._log_acao(instance, acao, usuario, mensagem)
    
    @staticmethod
    def _log_acao(instance, acao, usuario, mensagem):
        """Log de ação para auditoria"""
        # TODO: Implementar sistema de log de auditoria
        # Por enquanto, apenas print para debug
        print(f"[AUDIT] {acao.upper()}: {mensagem} - Contabilidade: {instance.razao_social} - Usuário: {usuario.username}")
