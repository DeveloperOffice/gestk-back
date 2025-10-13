"""
Services para gerenciamento de Usuarios por ADMIN
Contém a lógica de negócio para operações de usuários
"""
import logging
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from apps.core.models import Usuario, Contabilidade

logger = logging.getLogger(__name__)


class UsuarioService:
    """Service para operações de usuário"""
    
    @staticmethod
    @transaction.atomic
    def criar_usuario(dados, usuario_admin):
        """
        Cria um novo usuário
        
        Args:
            dados: dict com os dados do usuário (validated_data do serializer)
            usuario_admin: Usuário ADMIN que está criando
            
        Returns:
            Usuario: Usuário criado
        """
        try:
            # Extrair contabilidade (já vem como objeto do serializer)
            contabilidade = dados.get('contabilidade')
            
            # Criar usuário
            usuario = Usuario(
                username=dados['username'],
                email=dados.get('email', ''),
                first_name=dados.get('first_name', ''),
                last_name=dados.get('last_name', ''),
                cpf=dados.get('cpf'),
                contabilidade=contabilidade,
                tipo_usuario=dados.get('tipo_usuario', 'operacional'),
                modulos_acessiveis=dados.get('modulos_acessiveis', []),
                pode_executar_etl=dados.get('pode_executar_etl', False),
                pode_administrar_usuarios=dados.get('pode_administrar_usuarios', False),
                pode_ver_dados_sensiveis=dados.get('pode_ver_dados_sensiveis', False),
                ativo=dados.get('ativo', True),
                is_active=dados.get('is_active', True),
                is_staff=dados.get('is_staff', False)
            )
            
            # Definir senha
            if 'password' in dados:
                usuario.set_password(dados['password'])
            
            usuario.save()
            
            logger.info(
                f"Usuário {usuario.username} criado por ADMIN {usuario_admin.username}"
            )
            
            return usuario
            
        except Exception as e:
            logger.error(f"Erro ao criar usuário: {str(e)}")
            raise
    
    @staticmethod
    @transaction.atomic
    def atualizar_usuario(usuario, dados, usuario_admin):
        """
        Atualiza um usuário existente
        
        Args:
            usuario: Usuario a ser atualizado
            dados: dict com os dados para atualização
            usuario_admin: Usuário ADMIN que está atualizando
            
        Returns:
            Usuario: Usuário atualizado
        """
        try:
            # Campos permitidos para atualização
            campos_permitidos = [
                'email', 'first_name', 'last_name', 'cpf',
                'tipo_usuario', 'modulos_acessiveis',
                'pode_executar_etl', 'pode_administrar_usuarios',
                'pode_ver_dados_sensiveis',
                'ativo', 'is_active', 'is_staff'
            ]
            
            # Atualizar campos
            for campo in campos_permitidos:
                if campo in dados:
                    setattr(usuario, campo, dados[campo])
            
            # Atualizar senha se fornecida
            if 'password' in dados and dados['password']:
                usuario.set_password(dados['password'])
            
            usuario.save()
            
            logger.info(
                f"Usuário {usuario.username} atualizado por ADMIN {usuario_admin.username}"
            )
            
            return usuario
            
        except Exception as e:
            logger.error(f"Erro ao atualizar usuário: {str(e)}")
            raise
    
    @staticmethod
    @transaction.atomic
    def desativar_usuario(usuario, usuario_admin):
        """
        Desativa um usuário
        
        Args:
            usuario: Usuario a ser desativado
            usuario_admin: Usuário ADMIN que está desativando
            
        Returns:
            Usuario: Usuário desativado
        """
        try:
            usuario.ativo = False
            usuario.is_active = False
            usuario.save(update_fields=['ativo', 'is_active'])
            
            logger.info(
                f"Usuário {usuario.username} desativado por ADMIN {usuario_admin.username}"
            )
            
            return usuario
            
        except Exception as e:
            logger.error(f"Erro ao desativar usuário: {str(e)}")
            raise
    
    @staticmethod
    @transaction.atomic
    def ativar_usuario(usuario, usuario_admin):
        """
        Ativa um usuário
        
        Args:
            usuario: Usuario a ser ativado
            usuario_admin: Usuário ADMIN que está ativando
            
        Returns:
            Usuario: Usuário ativado
        """
        try:
            usuario.ativo = True
            usuario.is_active = True
            usuario.save(update_fields=['ativo', 'is_active'])
            
            logger.info(
                f"Usuário {usuario.username} ativado por ADMIN {usuario_admin.username}"
            )
            
            return usuario
            
        except Exception as e:
            logger.error(f"Erro ao ativar usuário: {str(e)}")
            raise
    
    @staticmethod
    @transaction.atomic
    def resetar_senha(usuario, nova_senha, usuario_admin):
        """
        Reseta a senha de um usuário
        
        Args:
            usuario: Usuario para resetar senha
            nova_senha: Nova senha
            usuario_admin: Usuário ADMIN que está resetando
            
        Returns:
            Usuario: Usuário com senha resetada
        """
        try:
            usuario.set_password(nova_senha)
            usuario.token_version += 1  # Invalidar tokens existentes
            usuario.save(update_fields=['password', 'token_version'])
            
            logger.info(
                f"Senha do usuário {usuario.username} resetada por ADMIN {usuario_admin.username}"
            )
            
            return usuario
            
        except Exception as e:
            logger.error(f"Erro ao resetar senha: {str(e)}")
            raise
    
    @staticmethod
    @transaction.atomic
    def atualizar_modulos(usuario, modulos, usuario_admin):
        """
        Atualiza os módulos acessíveis do usuário
        
        Args:
            usuario: Usuario para atualizar módulos
            modulos: Lista de módulos
            usuario_admin: Usuário ADMIN que está atualizando
            
        Returns:
            Usuario: Usuário atualizado
        """
        try:
            # Validar módulos
            modulos_validos = [escolha[0] for escolha in Usuario.MODULO_CHOICES]
            for modulo in modulos:
                if modulo not in modulos_validos:
                    raise ValueError(f"Módulo inválido: {modulo}")
            
            usuario.modulos_acessiveis = modulos
            usuario.save(update_fields=['modulos_acessiveis'])
            
            logger.info(
                f"Módulos do usuário {usuario.username} atualizados por ADMIN {usuario_admin.username}"
            )
            
            return usuario
            
        except Exception as e:
            logger.error(f"Erro ao atualizar módulos: {str(e)}")
            raise
    
    @staticmethod
    @transaction.atomic
    def deletar_usuario(usuario, usuario_admin):
        """
        Deleta um usuário (soft delete)
        
        Args:
            usuario: Usuario a ser deletado
            usuario_admin: Usuário ADMIN que está deletando
            
        Returns:
            bool: True se deletado com sucesso
        """
        try:
            username = usuario.username
            
            # Soft delete - apenas desativa
            usuario.ativo = False
            usuario.is_active = False
            usuario.username = f"{usuario.username}_deleted_{timezone.now().timestamp()}"
            usuario.save()
            
            logger.info(
                f"Usuário {username} deletado por ADMIN {usuario_admin.username}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao deletar usuário: {str(e)}")
            raise
    
    @staticmethod
    def calcular_estatisticas(contabilidade=None):
        """
        Calcula estatísticas de usuários
        
        Args:
            contabilidade: Contabilidade para filtrar (opcional)
            
        Returns:
            dict: Estatísticas calculadas
        """
        try:
            queryset = Usuario.objects.all()
            
            if contabilidade:
                queryset = queryset.filter(contabilidade=contabilidade)
            
            total = queryset.count()
            ativos = queryset.filter(ativo=True, is_active=True).count()
            inativos = total - ativos
            
            # Por tipo de usuário
            por_tipo = {}
            for tipo, _ in Usuario.TIPO_USUARIO_CHOICES:
                por_tipo[tipo] = queryset.filter(tipo_usuario=tipo).count()
            
            # Por módulo
            todos_usuarios = queryset.values_list('modulos_acessiveis', flat=True)
            modulos_count = {}
            for modulos in todos_usuarios:
                if modulos:
                    for modulo in modulos:
                        modulos_count[modulo] = modulos_count.get(modulo, 0) + 1
            
            return {
                'total': total,
                'ativos': ativos,
                'inativos': inativos,
                'por_tipo': por_tipo,
                'por_modulo': modulos_count,
                'com_mfa': queryset.filter(mfa_enabled=True).count(),
                'pode_executar_etl': queryset.filter(pode_executar_etl=True).count(),
                'pode_administrar': queryset.filter(pode_administrar_usuarios=True).count(),
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas: {str(e)}")
            raise
