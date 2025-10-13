"""
Services para gerenciamento de Contratos (Clientes) por ADMIN
Contém a lógica de negócio para operações de contratos
"""
import logging
from django.db import transaction
from django.utils import timezone
from apps.pessoas.models import Contrato, PessoaJuridica, PessoaFisica
from apps.core.models import Contabilidade

logger = logging.getLogger(__name__)


class ContratoService:
    """Service para operações de contrato"""
    
    @staticmethod
    @transaction.atomic
    def atualizar_contrato(contrato, dados, usuario_admin):
        """
        Atualiza um contrato existente
        
        Args:
            contrato: Contrato a ser atualizado
            dados: dict com os dados para atualização
            usuario_admin: Usuário ADMIN que está atualizando
            
        Returns:
            Contrato: Contrato atualizado
        """
        try:
            # Campos permitidos para atualização
            campos_permitidos = [
                'data_inicio', 'data_termino', 'dia_vencimento',
                'valor_honorario', 'plano_servico',
                'modulos_contratados',
                'limites_usuarios', 'limites_empresas',
                'ativo', 'status_cobranca'
            ]
            
            # Atualizar campos
            for campo in campos_permitidos:
                if campo in dados:
                    setattr(contrato, campo, dados[campo])
            
            contrato.save()
            
            logger.info(
                f"Contrato {contrato.id} atualizado por ADMIN {usuario_admin.username}"
            )
            
            return contrato
            
        except Exception as e:
            logger.error(f"Erro ao atualizar contrato: {str(e)}")
            raise
    
    @staticmethod
    @transaction.atomic
    def ativar_contrato(contrato, usuario_admin):
        """
        Ativa um contrato
        
        Args:
            contrato: Contrato a ser ativado
            usuario_admin: Usuário ADMIN que está ativando
            
        Returns:
            Contrato: Contrato ativado
        """
        try:
            contrato.ativo = True
            contrato.status_cobranca = 'ativo'
            contrato.save(update_fields=['ativo', 'status_cobranca'])
            
            logger.info(
                f"Contrato {contrato.id} ativado por ADMIN {usuario_admin.username}"
            )
            
            return contrato
            
        except Exception as e:
            logger.error(f"Erro ao ativar contrato: {str(e)}")
            raise
    
    @staticmethod
    @transaction.atomic
    def desativar_contrato(contrato, usuario_admin):
        """
        Desativa um contrato
        
        Args:
            contrato: Contrato a ser desativado
            usuario_admin: Usuário ADMIN que está desativando
            
        Returns:
            Contrato: Contrato desativado
        """
        try:
            contrato.ativo = False
            contrato.status_cobranca = 'inativo'
            contrato.save(update_fields=['ativo', 'status_cobranca'])
            
            logger.info(
                f"Contrato {contrato.id} desativado por ADMIN {usuario_admin.username}"
            )
            
            return contrato
            
        except Exception as e:
            logger.error(f"Erro ao desativar contrato: {str(e)}")
            raise
    
    @staticmethod
    @transaction.atomic
    def suspender_contrato(contrato, motivo, usuario_admin):
        """
        Suspende um contrato
        
        Args:
            contrato: Contrato a ser suspenso
            motivo: Motivo da suspensão
            usuario_admin: Usuário ADMIN que está suspendendo
            
        Returns:
            Contrato: Contrato suspenso
        """
        try:
            contrato.ativo = False
            contrato.status_cobranca = 'suspenso'
            contrato.save(update_fields=['ativo', 'status_cobranca'])
            
            logger.info(
                f"Contrato {contrato.id} suspenso por ADMIN {usuario_admin.username}. Motivo: {motivo}"
            )
            
            return contrato
            
        except Exception as e:
            logger.error(f"Erro ao suspender contrato: {str(e)}")
            raise
    
    @staticmethod
    @transaction.atomic
    def renovar_contrato(contrato, nova_data_termino, usuario_admin):
        """
        Renova um contrato
        
        Args:
            contrato: Contrato a ser renovado
            nova_data_termino: Nova data de término
            usuario_admin: Usuário ADMIN que está renovando
            
        Returns:
            Contrato: Contrato renovado
        """
        try:
            if nova_data_termino <= timezone.now().date():
                raise ValueError("Data de término deve ser futura")
            
            contrato.data_termino = nova_data_termino
            contrato.ativo = True
            contrato.status_cobranca = 'ativo'
            contrato.save(update_fields=['data_termino', 'ativo', 'status_cobranca'])
            
            logger.info(
                f"Contrato {contrato.id} renovado até {nova_data_termino} por ADMIN {usuario_admin.username}"
            )
            
            return contrato
            
        except Exception as e:
            logger.error(f"Erro ao renovar contrato: {str(e)}")
            raise
    
    @staticmethod
    @transaction.atomic
    def atualizar_modulos(contrato, modulos, usuario_admin):
        """
        Atualiza os módulos contratados
        
        Args:
            contrato: Contrato para atualizar módulos
            modulos: Lista de módulos
            usuario_admin: Usuário ADMIN que está atualizando
            
        Returns:
            Contrato: Contrato atualizado
        """
        try:
            if not isinstance(modulos, list):
                raise ValueError("Módulos deve ser uma lista")
            
            contrato.modulos_contratados = modulos
            contrato.save(update_fields=['modulos_contratados'])
            
            logger.info(
                f"Módulos do contrato {contrato.id} atualizados por ADMIN {usuario_admin.username}"
            )
            
            return contrato
            
        except Exception as e:
            logger.error(f"Erro ao atualizar módulos: {str(e)}")
            raise
    
    @staticmethod
    @transaction.atomic
    def atualizar_limites(contrato, limite_usuarios, limite_empresas, usuario_admin):
        """
        Atualiza os limites do contrato
        
        Args:
            contrato: Contrato para atualizar limites
            limite_usuarios: Novo limite de usuários
            limite_empresas: Novo limite de empresas
            usuario_admin: Usuário ADMIN que está atualizando
            
        Returns:
            Contrato: Contrato atualizado
        """
        try:
            if limite_usuarios < 1:
                raise ValueError("Limite de usuários deve ser no mínimo 1")
            if limite_empresas < 1:
                raise ValueError("Limite de empresas deve ser no mínimo 1")
            
            contrato.limites_usuarios = limite_usuarios
            contrato.limites_empresas = limite_empresas
            contrato.save(update_fields=['limites_usuarios', 'limites_empresas'])
            
            logger.info(
                f"Limites do contrato {contrato.id} atualizados por ADMIN {usuario_admin.username}"
            )
            
            return contrato
            
        except Exception as e:
            logger.error(f"Erro ao atualizar limites: {str(e)}")
            raise
    
    @staticmethod
    @transaction.atomic
    def deletar_contrato(contrato, usuario_admin):
        """
        Deleta um contrato (desativa permanentemente)
        
        Args:
            contrato: Contrato a ser deletado
            usuario_admin: Usuário ADMIN que está deletando
            
        Returns:
            bool: True se deletado com sucesso
        """
        try:
            # Não deletar fisicamente, apenas marcar como inativo
            contrato.ativo = False
            contrato.status_cobranca = 'cancelado'
            contrato.save(update_fields=['ativo', 'status_cobranca'])
            
            logger.info(
                f"Contrato {contrato.id} deletado por ADMIN {usuario_admin.username}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao deletar contrato: {str(e)}")
            raise
    
    @staticmethod
    def calcular_estatisticas(contabilidade=None):
        """
        Calcula estatísticas de contratos
        
        Args:
            contabilidade: Contabilidade para filtrar (opcional)
            
        Returns:
            dict: Estatísticas calculadas
        """
        try:
            from django.db.models import Sum, Count, Avg
            from django.contrib.contenttypes.models import ContentType
            
            queryset = Contrato.objects.all()
            
            if contabilidade:
                queryset = queryset.filter(contabilidade=contabilidade)
            
            total = queryset.count()
            ativos = queryset.filter(ativo=True).count()
            inativos = total - ativos
            
            # Por status de cobrança
            por_status = {}
            for status in ['ativo', 'inativo', 'suspenso', 'cancelado']:
                por_status[status] = queryset.filter(status_cobranca=status).count()
            
            # Valores
            valor_total = queryset.aggregate(
                total=Sum('valor_honorario')
            )['total'] or 0
            
            valor_medio = queryset.aggregate(
                media=Avg('valor_honorario')
            )['media'] or 0
            
            # Contratos vencendo
            hoje = timezone.now().date()
            proximos_30_dias = hoje + timezone.timedelta(days=30)
            vencendo = queryset.filter(
                ativo=True,
                data_termino__isnull=False,
                data_termino__gte=hoje,
                data_termino__lte=proximos_30_dias
            ).count()
            
            # Contratos vencidos
            vencidos = queryset.filter(
                ativo=True,
                data_termino__isnull=False,
                data_termino__lt=hoje
            ).count()
            
            # Tipo de cliente
            pj_content_type = ContentType.objects.get_for_model(PessoaJuridica)
            pf_content_type = ContentType.objects.get_for_model(PessoaFisica)
            
            total_pj = queryset.filter(content_type=pj_content_type).count()
            total_pf = queryset.filter(content_type=pf_content_type).count()
            
            return {
                'total': total,
                'ativos': ativos,
                'inativos': inativos,
                'por_status': por_status,
                'valor_total_honorarios': float(valor_total),
                'valor_medio_honorarios': float(valor_medio),
                'vencendo_30_dias': vencendo,
                'vencidos': vencidos,
                'por_tipo_cliente': {
                    'pessoa_juridica': total_pj,
                    'pessoa_fisica': total_pf
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas: {str(e)}")
            raise


from django.contrib.contenttypes.models import ContentType
