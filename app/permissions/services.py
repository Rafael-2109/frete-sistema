"""
Serviços de Permissões - Lógica de Negócio Centralizada
======================================================

Service layer para centralizar toda a lógica de permissões:
- Verificação de permissões
- Filtros automáticos de dados
- Aplicação de regras de negócio
- Cache e otimização de consultas
"""

from typing import List, Dict, Any, Optional, Union
from sqlalchemy import or_, and_
from flask_login import current_user
import logging

from app import db
from app.permissions.models import (
    PerfilUsuario, ModuloSistema, FuncaoModulo, PermissaoUsuario,
    UsuarioVendedor, UsuarioEquipeVendas, LogPermissao
)
from app.auth.models import Usuario

logger = logging.getLogger(__name__)

class PermissaoService:
    """
    Service principal para gestão de permissões
    Centraliza toda a lógica de verificação e aplicação de permissões
    """
    
    # ========================================================================
    # VERIFICAÇÃO DE PERMISSÕES
    # ========================================================================
    
    @staticmethod
    def usuario_tem_permissao(usuario_id: int, modulo: str, funcao: str, 
                             nivel: str = 'visualizar') -> bool:
        """
        Verifica se usuário tem permissão específica
        
        Args:
            usuario_id: ID do usuário
            modulo: Nome do módulo (ex: 'faturamento')
            funcao: Nome da função (ex: 'listar_faturas')
            nivel: 'visualizar' ou 'editar'
            
        Returns:
            True se tem permissão, False caso contrário
        """
        try:
            # Cache de verificação (TODO: implementar Redis)
            cache_key = f"perm_{usuario_id}_{modulo}_{funcao}_{nivel}"
            
            # Buscar permissão na base
            permissao = db.session.query(PermissaoUsuario)\
                .join(FuncaoModulo)\
                .join(ModuloSistema)\
                .filter(
                    PermissaoUsuario.usuario_id == usuario_id,
                    ModuloSistema.nome == modulo,
                    FuncaoModulo.nome == funcao,
                    PermissaoUsuario.ativo == True
                ).first()
            
            if not permissao:
                return False
            
            # Verificar se não está expirada
            if permissao.esta_expirada:
                return False
            
            # Verificar nível solicitado
            if nivel == 'visualizar':
                return permissao.pode_visualizar
            elif nivel == 'editar':
                return permissao.pode_editar
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao verificar permissão: {e}")
            return False
    
    @staticmethod
    def usuario_tem_acesso_admin(usuario_id: int) -> bool:
        """
        Verifica se usuário tem acesso administrativo total
        """
        return PermissaoService.usuario_tem_permissao(
            usuario_id, 'admin', 'acesso_total', 'editar'
        )
    
    @staticmethod
    def listar_permissoes_usuario(usuario_id: int) -> Dict[str, Any]:
        """
        Lista todas as permissões de um usuário
        Organizado por módulo → função
        """
        try:
            permissoes = {}
            
            # Buscar todas as permissões ativas
            query = db.session.query(PermissaoUsuario, FuncaoModulo, ModuloSistema)\
                .join(FuncaoModulo)\
                .join(ModuloSistema)\
                .filter(
                    PermissaoUsuario.usuario_id == usuario_id,
                    PermissaoUsuario.ativo == True
                ).all()
            
            for permissao, funcao, modulo in query:
                if modulo.nome not in permissoes:
                    permissoes[modulo.nome] = {
                        'modulo_info': {
                            'nome': modulo.nome,
                            'nome_exibicao': modulo.nome_exibicao,
                            'icone': modulo.icone
                        },
                        'funcoes': {}
                    }
                
                permissoes[modulo.nome]['funcoes'][funcao.nome] = {
                    'nome_exibicao': funcao.nome_exibicao,
                    'pode_visualizar': permissao.pode_visualizar,
                    'pode_editar': permissao.pode_editar,
                    'nivel_critico': funcao.nivel_critico
                }
            
            return permissoes
            
        except Exception as e:
            logger.error(f"Erro ao listar permissões do usuário {usuario_id}: {e}")
            return {}
    
    # ========================================================================
    # VENDEDORES E EQUIPES
    # ========================================================================
    
    @staticmethod
    def obter_vendedores_usuario(usuario_id: int) -> List[str]:
        """
        Retorna lista de vendedores que usuário tem acesso
        """
        try:
            vendedores = UsuarioVendedor.query.filter_by(
                usuario_id=usuario_id, ativo=True
            ).all()
            
            return [v.vendedor for v in vendedores]
            
        except Exception as e:
            logger.error(f"Erro ao obter vendedores do usuário {usuario_id}: {e}")
            return []
    
    @staticmethod
    def obter_equipes_usuario(usuario_id: int) -> List[str]:
        """
        Retorna lista de equipes que usuário tem acesso
        """
        try:
            equipes = UsuarioEquipeVendas.query.filter_by(
                usuario_id=usuario_id, ativo=True
            ).all()
            
            return [e.equipe_vendas for e in equipes]
            
        except Exception as e:
            logger.error(f"Erro ao obter equipes do usuário {usuario_id}: {e}")
            return []
    
    @staticmethod
    def usuario_tem_vendedor(usuario_id: int, vendedor: str) -> bool:
        """
        Verifica se usuário tem acesso a vendedor específico
        """
        return UsuarioVendedor.usuario_tem_vendedor(usuario_id, vendedor)
    
    @staticmethod
    def usuario_tem_equipe(usuario_id: int, equipe_vendas: str) -> bool:
        """
        Verifica se usuário tem acesso a equipe específica
        """
        return UsuarioEquipeVendas.usuario_tem_equipe(usuario_id, equipe_vendas)
    
    # ========================================================================
    # FILTROS AUTOMÁTICOS DE DADOS
    # ========================================================================
    
    @staticmethod
    def aplicar_filtro_vendedor_automatico(query, model, usuario_id: int):
        """
        Aplica filtro automático baseado nos vendedores/equipes do usuário
        
        Args:
            query: Query SQLAlchemy
            model: Modelo que possui campos vendedor/equipe_vendas
            usuario_id: ID do usuário
            
        Returns:
            Query filtrada ou original se tem acesso total
        """
        try:
            # Verificar se tem acesso administrativo total
            if PermissaoService.usuario_tem_acesso_admin(usuario_id):
                return query  # Sem filtro = acesso total
            
            # Obter vendedores e equipes autorizados
            vendedores = PermissaoService.obter_vendedores_usuario(usuario_id)
            equipes = PermissaoService.obter_equipes_usuario(usuario_id)
            
            if not vendedores and not equipes:
                 # Usuário sem acesso a nenhum vendedor/equipe
                 return query.filter(db.text('1=0'))  # Retorna vazio
             
             # Construir filtros
            filtros = []
            
            # Filtro por vendedores
            if vendedores and hasattr(model, 'vendedor'):
                filtros.append(model.vendedor.in_(vendedores))
            
            # Filtro por equipes (se o modelo tem o campo)
            if equipes and hasattr(model, 'equipe_vendas'):
                filtros.append(model.equipe_vendas.in_(equipes))
            
            # Aplicar filtros com OR (usuário pode ter dados por vendedor OU por equipe)
            if filtros:
                return query.filter(or_(*filtros))
            else:
                return query.filter(False)  # Sem dados autorizados
                
        except Exception as e:
            logger.error(f"Erro ao aplicar filtro automático: {e}")
            return query.filter(False)  # Seguro: sem dados em caso de erro
    
    @staticmethod
    def obter_dados_com_filtro_usuario(model_class, usuario_id: int = None, **filtros):
        """
        Busca dados aplicando filtros automáticos de vendedor/equipe
        
        Args:
            model_class: Classe do modelo
            usuario_id: ID do usuário (usa current_user se None)
            **filtros: Filtros adicionais
            
        Returns:
            Query filtrada
        """
        try:
            if usuario_id is None:
                usuario_id = current_user.id if current_user.is_authenticated else None
            
            if not usuario_id:
                return model_class.query.filter(False)  # Sem usuário = sem dados
            
            # Criar query base
            query = model_class.query
            
            # Aplicar filtros adicionais
            for campo, valor in filtros.items():
                if hasattr(model_class, campo):
                    query = query.filter(getattr(model_class, campo) == valor)
            
            # Aplicar filtro automático de vendedor/equipe
            query = PermissaoService.aplicar_filtro_vendedor_automatico(
                query, model_class, usuario_id
            )
            
            return query
            
        except Exception as e:
            logger.error(f"Erro ao obter dados com filtro: {e}")
            return model_class.query.filter(False)
    
    # ========================================================================
    # OPERAÇÕES DE GESTÃO
    # ========================================================================
    
    @staticmethod
    def conceder_permissao(usuario_id: int, modulo: str, funcao: str,
                          pode_visualizar: bool = True, pode_editar: bool = False,
                          concedida_por: int = None, observacoes: str = None) -> bool:
        """
        Concede uma permissão específica a um usuário
        """
        try:
            # Validar se módulo e função existem
            funcao_obj = db.session.query(FuncaoModulo)\
                .join(ModuloSistema)\
                .filter(
                    ModuloSistema.nome == modulo,
                    FuncaoModulo.nome == funcao
                ).first()
            
            if not funcao_obj:
                raise ValueError(f"Função {modulo}.{funcao} não encontrada")
            
            # Buscar permissão existente
            permissao = PermissaoUsuario.query.filter_by(
                usuario_id=usuario_id,
                funcao_id=funcao_obj.id
            ).first()
            
            if permissao:
                # Atualizar existente
                permissao.pode_visualizar = pode_visualizar
                permissao.pode_editar = pode_editar
                permissao.observacoes = observacoes
                permissao.ativo = True
            else:
                # Criar nova
                permissao = PermissaoUsuario(
                    usuario_id=usuario_id,
                    funcao_id=funcao_obj.id,
                    pode_visualizar=pode_visualizar,
                    pode_editar=pode_editar,
                    concedida_por=concedida_por,
                    observacoes=observacoes
                )
                db.session.add(permissao)
            
            db.session.commit()
            
            # Log de auditoria
            LogPermissao.registrar(
                usuario_id=usuario_id,
                acao='PERMISSAO_CONCEDIDA',
                funcao_id=funcao_obj.id,
                detalhes=f"Visualizar: {pode_visualizar}, Editar: {pode_editar}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao conceder permissão: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def revogar_permissao(usuario_id: int, modulo: str, funcao: str) -> bool:
        """
        Revoga uma permissão específica de um usuário
        """
        try:
            # Buscar permissão
            permissao = db.session.query(PermissaoUsuario)\
                .join(FuncaoModulo)\
                .join(ModuloSistema)\
                .filter(
                    PermissaoUsuario.usuario_id == usuario_id,
                    ModuloSistema.nome == modulo,
                    FuncaoModulo.nome == funcao
                ).first()
            
            if not permissao:
                return False
            
            # Soft delete
            permissao.ativo = False
            db.session.commit()
            
            # Log de auditoria
            LogPermissao.registrar(
                usuario_id=usuario_id,
                acao='PERMISSAO_REVOGADA',
                funcao_id=permissao.funcao_id,
                detalhes=f"Revogada permissão {modulo}.{funcao}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao revogar permissão: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def adicionar_vendedor_usuario(usuario_id: int, vendedor: str,
                                  adicionado_por: int = None) -> bool:
        """
        Adiciona vendedor às autorizações do usuário
        """
        try:
            # Verificar se já existe
            vendedor_existente = UsuarioVendedor.query.filter_by(
                usuario_id=usuario_id,
                vendedor=vendedor
            ).first()
            
            if vendedor_existente:
                if vendedor_existente.ativo:
                    return False  # Já existe e está ativo
                else:
                    # Reativar
                    vendedor_existente.ativo = True
                    vendedor_existente.adicionado_por = adicionado_por
                    vendedor_existente.adicionado_em = db.func.now()
            else:
                # Criar novo
                vendedor_existente = UsuarioVendedor(
                    usuario_id=usuario_id,
                    vendedor=vendedor,
                    adicionado_por=adicionado_por
                )
                db.session.add(vendedor_existente)
            
            db.session.commit()
            
            # Log de auditoria
            LogPermissao.registrar(
                usuario_id=usuario_id,
                acao='VENDEDOR_ADICIONADO',
                detalhes=f"Vendedor: {vendedor}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao adicionar vendedor: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def remover_vendedor_usuario(usuario_id: int, vendedor: str) -> bool:
        """
        Remove vendedor das autorizações do usuário
        """
        try:
            vendedor_obj = UsuarioVendedor.query.filter_by(
                usuario_id=usuario_id,
                vendedor=vendedor,
                ativo=True
            ).first()
            
            if not vendedor_obj:
                return False
            
            # Soft delete
            vendedor_obj.ativo = False
            db.session.commit()
            
            # Log de auditoria
            LogPermissao.registrar(
                usuario_id=usuario_id,
                acao='VENDEDOR_REMOVIDO',
                detalhes=f"Vendedor: {vendedor}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao remover vendedor: {e}")
            db.session.rollback()
            return False
    
    # ========================================================================
    # UTILITÁRIOS E CACHE
    # ========================================================================
    
    @staticmethod
    def limpar_cache_usuario(usuario_id: int):
        """
        Limpa cache de permissões de um usuário
        TODO: Implementar com Redis
        """
        pass
    
    @staticmethod
    def obter_estatisticas_permissoes() -> Dict[str, Any]:
        """
        Retorna estatísticas gerais do sistema de permissões
        """
        try:
            stats = {
                'usuarios_ativos': Usuario.query.filter_by(status='ativo').count(),
                'permissoes_ativas': PermissaoUsuario.query.filter_by(ativo=True).count(),
                'vendedores_autorizados': UsuarioVendedor.query.filter_by(ativo=True).count(),
                'equipes_autorizadas': UsuarioEquipeVendas.query.filter_by(ativo=True).count(),
                'modulos_sistema': ModuloSistema.query.filter_by(ativo=True).count(),
                'funcoes_sistema': FuncaoModulo.query.filter_by(ativo=True).count(),
                'logs_ultimo_mes': LogPermissao.query.filter(
                    LogPermissao.timestamp >= db.func.date_sub(db.func.now(), db.text('INTERVAL 1 MONTH'))
                ).count()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {}
    
    @staticmethod
    def validar_consistencia_permissoes() -> Dict[str, Any]:
        """
        Valida consistência do sistema de permissões
        Identifica permissões órfãs, usuários sem acesso, etc.
        """
        try:
            problemas = []
            
            # Verificar permissões órfãs (função/módulo inativo)
            permissoes_orfas = db.session.query(PermissaoUsuario)\
                .join(FuncaoModulo)\
                .join(ModuloSistema)\
                .filter(
                    PermissaoUsuario.ativo == True,
                    or_(FuncaoModulo.ativo == False, ModuloSistema.ativo == False)
                ).count()
            
            if permissoes_orfas > 0:
                problemas.append(f"{permissoes_orfas} permissões órfãs encontradas")
            
            # Verificar usuários sem permissões
            usuarios_sem_permissoes = db.session.query(Usuario)\
                .outerjoin(PermissaoUsuario)\
                .filter(
                    Usuario.status == 'ativo',
                    PermissaoUsuario.id.is_(None)
                ).count()
            
            if usuarios_sem_permissoes > 0:
                problemas.append(f"{usuarios_sem_permissoes} usuários ativos sem permissões")
            
            return {
                'status': 'OK' if not problemas else 'PROBLEMAS',
                'problemas': problemas,
                'permissoes_orfas': permissoes_orfas,
                'usuarios_sem_permissoes': usuarios_sem_permissoes
            }
            
        except Exception as e:
            logger.error(f"Erro ao validar consistência: {e}")
            return {'status': 'ERRO', 'erro': str(e)} 