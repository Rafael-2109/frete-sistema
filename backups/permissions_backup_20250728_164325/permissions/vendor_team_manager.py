"""
Gerenciador de Vendedores e Equipes
===================================

Sistema para gerenciar associações de vendedores e equipes com usuários,
incluindo herança de permissões e lógica de negócio.
"""

from app import db
from app.permissions.models import (
    Vendedor, EquipeVendas, UsuarioVendedor, UsuarioEquipeVendas,
    PermissaoVendedor, PermissaoEquipe, PermissaoUsuario, FuncaoModulo,
    LogPermissao
)
from sqlalchemy import and_, or_
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class VendorTeamManager:
    """
    Gerenciador para operações relacionadas a vendedores e equipes
    """
    
    @staticmethod
    def criar_vendedor(codigo, nome, razao_social=None, cnpj_cpf=None, 
                      email=None, telefone=None, criado_por=None):
        """
        Cria um novo vendedor no sistema
        """
        try:
            # Verificar se vendedor já existe
            if Vendedor.query.filter_by(codigo=codigo).first():
                return False, "Vendedor com este código já existe"
            
            vendedor = Vendedor(
                codigo=codigo,
                nome=nome,
                razao_social=razao_social,
                cnpj_cpf=cnpj_cpf,
                email=email,
                telefone=telefone,
                criado_por=criado_por
            )
            db.session.add(vendedor)
            db.session.commit()
            
            logger.info(f"Vendedor {codigo} - {nome} criado com sucesso")
            return True, vendedor
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar vendedor: {e}")
            return False, str(e)
    
    @staticmethod
    def criar_equipe(codigo, nome, descricao=None, gerente_id=None, criado_por=None):
        """
        Cria uma nova equipe de vendas
        """
        try:
            # Verificar se equipe já existe
            if EquipeVendas.query.filter_by(codigo=codigo).first():
                return False, "Equipe com este código já existe"
            
            equipe = EquipeVendas(
                codigo=codigo,
                nome=nome,
                descricao=descricao,
                gerente_id=gerente_id,
                criado_por=criado_por
            )
            db.session.add(equipe)
            db.session.commit()
            
            logger.info(f"Equipe {codigo} - {nome} criada com sucesso")
            return True, equipe
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar equipe: {e}")
            return False, str(e)
    
    @staticmethod
    def associar_usuario_vendedor(usuario_id, vendedor_id, tipo_acesso='visualizar', 
                                 adicionado_por=None, observacoes=None):
        """
        Associa um usuário a um vendedor
        """
        try:
            # Verificar se associação já existe
            associacao = UsuarioVendedor.query.filter_by(
                usuario_id=usuario_id,
                vendedor_id=vendedor_id
            ).first()
            
            if associacao:
                if associacao.ativo:
                    return False, "Usuário já está associado a este vendedor"
                else:
                    # Reativar associação existente
                    associacao.ativo = True
                    associacao.tipo_acesso = tipo_acesso
                    associacao.adicionado_por = adicionado_por
                    associacao.adicionado_em = datetime.utcnow()
            else:
                # Criar nova associação
                associacao = UsuarioVendedor(
                    usuario_id=usuario_id,
                    vendedor_id=vendedor_id,
                    tipo_acesso=tipo_acesso,
                    adicionado_por=adicionado_por,
                    observacoes=observacoes
                )
                db.session.add(associacao)
            
            db.session.commit()
            
            # Registrar no log
            LogPermissao.registrar(
                usuario_id=usuario_id,
                acao='VENDEDOR_ASSOCIADO',
                detalhes=f'Vendedor ID: {vendedor_id}, Tipo: {tipo_acesso}'
            )
            
            logger.info(f"Usuário {usuario_id} associado ao vendedor {vendedor_id}")
            return True, associacao
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao associar usuário a vendedor: {e}")
            return False, str(e)
    
    @staticmethod
    def associar_usuario_equipe(usuario_id, equipe_id, cargo_equipe=None, 
                               tipo_acesso='membro', adicionado_por=None, observacoes=None):
        """
        Associa um usuário a uma equipe
        """
        try:
            # Verificar se associação já existe
            associacao = UsuarioEquipeVendas.query.filter_by(
                usuario_id=usuario_id,
                equipe_id=equipe_id
            ).first()
            
            if associacao:
                if associacao.ativo:
                    return False, "Usuário já está associado a esta equipe"
                else:
                    # Reativar associação existente
                    associacao.ativo = True
                    associacao.cargo_equipe = cargo_equipe
                    associacao.tipo_acesso = tipo_acesso
                    associacao.adicionado_por = adicionado_por
                    associacao.adicionado_em = datetime.utcnow()
            else:
                # Criar nova associação
                associacao = UsuarioEquipeVendas(
                    usuario_id=usuario_id,
                    equipe_id=equipe_id,
                    cargo_equipe=cargo_equipe,
                    tipo_acesso=tipo_acesso,
                    adicionado_por=adicionado_por,
                    observacoes=observacoes
                )
                db.session.add(associacao)
            
            db.session.commit()
            
            # Registrar no log
            LogPermissao.registrar(
                usuario_id=usuario_id,
                acao='EQUIPE_ASSOCIADA',
                detalhes=f'Equipe ID: {equipe_id}, Cargo: {cargo_equipe}, Tipo: {tipo_acesso}'
            )
            
            logger.info(f"Usuário {usuario_id} associado à equipe {equipe_id}")
            return True, associacao
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao associar usuário a equipe: {e}")
            return False, str(e)
    
    @staticmethod
    def desassociar_usuario_vendedor(usuario_id, vendedor_id):
        """
        Remove associação entre usuário e vendedor
        """
        try:
            associacao = UsuarioVendedor.query.filter_by(
                usuario_id=usuario_id,
                vendedor_id=vendedor_id,
                ativo=True
            ).first()
            
            if not associacao:
                return False, "Associação não encontrada"
            
            associacao.ativo = False
            db.session.commit()
            
            # Registrar no log
            LogPermissao.registrar(
                usuario_id=usuario_id,
                acao='VENDEDOR_DESASSOCIADO',
                detalhes=f'Vendedor ID: {vendedor_id}'
            )
            
            logger.info(f"Usuário {usuario_id} desassociado do vendedor {vendedor_id}")
            return True, "Desassociado com sucesso"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao desassociar usuário de vendedor: {e}")
            return False, str(e)
    
    @staticmethod
    def desassociar_usuario_equipe(usuario_id, equipe_id):
        """
        Remove associação entre usuário e equipe
        """
        try:
            associacao = UsuarioEquipeVendas.query.filter_by(
                usuario_id=usuario_id,
                equipe_id=equipe_id,
                ativo=True
            ).first()
            
            if not associacao:
                return False, "Associação não encontrada"
            
            associacao.ativo = False
            db.session.commit()
            
            # Registrar no log
            LogPermissao.registrar(
                usuario_id=usuario_id,
                acao='EQUIPE_DESASSOCIADA',
                detalhes=f'Equipe ID: {equipe_id}'
            )
            
            logger.info(f"Usuário {usuario_id} desassociado da equipe {equipe_id}")
            return True, "Desassociado com sucesso"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao desassociar usuário de equipe: {e}")
            return False, str(e)
    
    @staticmethod
    def atribuir_permissao_vendedor(vendedor_id, funcao_id, pode_visualizar=True, 
                                   pode_editar=False, concedida_por=None):
        """
        Atribui permissão a todos os usuários de um vendedor
        """
        try:
            # Verificar se permissão já existe
            permissao = PermissaoVendedor.query.filter_by(
                vendedor_id=vendedor_id,
                funcao_id=funcao_id
            ).first()
            
            if permissao:
                permissao.pode_visualizar = pode_visualizar
                permissao.pode_editar = pode_editar
                permissao.ativo = True
                permissao.concedida_por = concedida_por
                permissao.concedida_em = datetime.utcnow()
            else:
                permissao = PermissaoVendedor(
                    vendedor_id=vendedor_id,
                    funcao_id=funcao_id,
                    pode_visualizar=pode_visualizar,
                    pode_editar=pode_editar,
                    concedida_por=concedida_por
                )
                db.session.add(permissao)
            
            db.session.commit()
            
            logger.info(f"Permissão atribuída ao vendedor {vendedor_id} para função {funcao_id}")
            return True, permissao
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atribuir permissão a vendedor: {e}")
            return False, str(e)
    
    @staticmethod
    def atribuir_permissao_equipe(equipe_id, funcao_id, pode_visualizar=True, 
                                 pode_editar=False, concedida_por=None):
        """
        Atribui permissão a todos os usuários de uma equipe
        """
        try:
            # Verificar se permissão já existe
            permissao = PermissaoEquipe.query.filter_by(
                equipe_id=equipe_id,
                funcao_id=funcao_id
            ).first()
            
            if permissao:
                permissao.pode_visualizar = pode_visualizar
                permissao.pode_editar = pode_editar
                permissao.ativo = True
                permissao.concedida_por = concedida_por
                permissao.concedida_em = datetime.utcnow()
            else:
                permissao = PermissaoEquipe(
                    equipe_id=equipe_id,
                    funcao_id=funcao_id,
                    pode_visualizar=pode_visualizar,
                    pode_editar=pode_editar,
                    concedida_por=concedida_por
                )
                db.session.add(permissao)
            
            db.session.commit()
            
            logger.info(f"Permissão atribuída à equipe {equipe_id} para função {funcao_id}")
            return True, permissao
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atribuir permissão a equipe: {e}")
            return False, str(e)
    
    @staticmethod
    def get_permissoes_efetivas_usuario(usuario_id):
        """
        Obtém todas as permissões efetivas de um usuário considerando:
        1. Permissões diretas do usuário
        2. Permissões herdadas dos vendedores
        3. Permissões herdadas das equipes
        
        Retorna dict com a maior permissão para cada função
        """
        permissoes_efetivas = {}
        
        try:
            # 1. Permissões diretas do usuário
            permissoes_usuario = PermissaoUsuario.query.filter_by(
                usuario_id=usuario_id,
                ativo=True
            ).all()
            
            for perm in permissoes_usuario:
                if not perm.esta_expirada:
                    funcao_key = f"{perm.funcao.modulo.nome}.{perm.funcao.nome}"
                    permissoes_efetivas[funcao_key] = {
                        'funcao_id': perm.funcao_id,
                        'modulo': perm.funcao.modulo.nome,
                        'funcao': perm.funcao.nome,
                        'pode_visualizar': perm.pode_visualizar,
                        'pode_editar': perm.pode_editar,
                        'origem': 'usuario',
                        'origem_id': usuario_id
                    }
            
            # 2. Permissões herdadas dos vendedores
            vendedores = UsuarioVendedor.query.filter_by(
                usuario_id=usuario_id,
                ativo=True
            ).all()
            
            for uv in vendedores:
                permissoes_vendedor = PermissaoVendedor.query.filter_by(
                    vendedor_id=uv.vendedor_id,
                    ativo=True
                ).all()
                
                for perm in permissoes_vendedor:
                    funcao_key = f"{perm.funcao.modulo.nome}.{perm.funcao.nome}"
                    
                    # Se já existe permissão, manter a maior
                    if funcao_key in permissoes_efetivas:
                        if perm.pode_editar and not permissoes_efetivas[funcao_key]['pode_editar']:
                            permissoes_efetivas[funcao_key]['pode_editar'] = True
                            permissoes_efetivas[funcao_key]['origem'] = 'vendedor'
                            permissoes_efetivas[funcao_key]['origem_id'] = uv.vendedor_id
                        elif perm.pode_visualizar and not permissoes_efetivas[funcao_key]['pode_visualizar']:
                            permissoes_efetivas[funcao_key]['pode_visualizar'] = True
                    else:
                        permissoes_efetivas[funcao_key] = {
                            'funcao_id': perm.funcao_id,
                            'modulo': perm.funcao.modulo.nome,
                            'funcao': perm.funcao.nome,
                            'pode_visualizar': perm.pode_visualizar,
                            'pode_editar': perm.pode_editar,
                            'origem': 'vendedor',
                            'origem_id': uv.vendedor_id
                        }
            
            # 3. Permissões herdadas das equipes
            equipes = UsuarioEquipeVendas.query.filter_by(
                usuario_id=usuario_id,
                ativo=True
            ).all()
            
            for ue in equipes:
                permissoes_equipe = PermissaoEquipe.query.filter_by(
                    equipe_id=ue.equipe_id,
                    ativo=True
                ).all()
                
                for perm in permissoes_equipe:
                    funcao_key = f"{perm.funcao.modulo.nome}.{perm.funcao.nome}"
                    
                    # Se já existe permissão, manter a maior
                    if funcao_key in permissoes_efetivas:
                        if perm.pode_editar and not permissoes_efetivas[funcao_key]['pode_editar']:
                            permissoes_efetivas[funcao_key]['pode_editar'] = True
                            permissoes_efetivas[funcao_key]['origem'] = 'equipe'
                            permissoes_efetivas[funcao_key]['origem_id'] = ue.equipe_id
                        elif perm.pode_visualizar and not permissoes_efetivas[funcao_key]['pode_visualizar']:
                            permissoes_efetivas[funcao_key]['pode_visualizar'] = True
                    else:
                        permissoes_efetivas[funcao_key] = {
                            'funcao_id': perm.funcao_id,
                            'modulo': perm.funcao.modulo.nome,
                            'funcao': perm.funcao.nome,
                            'pode_visualizar': perm.pode_visualizar,
                            'pode_editar': perm.pode_editar,
                            'origem': 'equipe',
                            'origem_id': ue.equipe_id
                        }
            
            return permissoes_efetivas
            
        except Exception as e:
            logger.error(f"Erro ao obter permissões efetivas: {e}")
            return {}
    
    @staticmethod
    def usuario_tem_permissao(usuario_id, modulo, funcao, nivel='visualizar'):
        """
        Verifica se usuário tem permissão para módulo/função específica
        considerando herança de vendedores e equipes
        """
        try:
            permissoes = VendorTeamManager.get_permissoes_efetivas_usuario(usuario_id)
            funcao_key = f"{modulo}.{funcao}"
            
            if funcao_key in permissoes:
                perm = permissoes[funcao_key]
                if nivel == 'editar':
                    return perm['pode_editar']
                else:
                    return perm['pode_visualizar'] or perm['pode_editar']
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao verificar permissão: {e}")
            return False
    
    @staticmethod
    def listar_usuarios_vendedor(vendedor_id):
        """
        Lista todos os usuários associados a um vendedor
        """
        try:
            associacoes = UsuarioVendedor.query.filter_by(
                vendedor_id=vendedor_id,
                ativo=True
            ).all()
            
            usuarios = []
            for assoc in associacoes:
                usuarios.append({
                    'usuario_id': assoc.usuario_id,
                    'nome': assoc.usuario.nome,
                    'email': assoc.usuario.email,
                    'tipo_acesso': assoc.tipo_acesso,
                    'adicionado_em': assoc.adicionado_em
                })
            
            return usuarios
            
        except Exception as e:
            logger.error(f"Erro ao listar usuários do vendedor: {e}")
            return []
    
    @staticmethod
    def listar_usuarios_equipe(equipe_id):
        """
        Lista todos os usuários associados a uma equipe
        """
        try:
            associacoes = UsuarioEquipeVendas.query.filter_by(
                equipe_id=equipe_id,
                ativo=True
            ).all()
            
            usuarios = []
            for assoc in associacoes:
                usuarios.append({
                    'usuario_id': assoc.usuario_id,
                    'nome': assoc.usuario.nome,
                    'email': assoc.usuario.email,
                    'cargo_equipe': assoc.cargo_equipe,
                    'tipo_acesso': assoc.tipo_acesso,
                    'adicionado_em': assoc.adicionado_em
                })
            
            return usuarios
            
        except Exception as e:
            logger.error(f"Erro ao listar usuários da equipe: {e}")
            return []
    
    @staticmethod
    def get_dashboard_stats():
        """
        Retorna estatísticas para dashboard de vendedores e equipes
        """
        try:
            stats = {
                'total_vendedores': Vendedor.query.filter_by(ativo=True).count(),
                'total_equipes': EquipeVendas.query.filter_by(ativo=True).count(),
                'usuarios_com_vendedor': db.session.query(UsuarioVendedor.usuario_id)\
                    .filter_by(ativo=True).distinct().count(),
                'usuarios_com_equipe': db.session.query(UsuarioEquipeVendas.usuario_id)\
                    .filter_by(ativo=True).distinct().count(),
                'permissoes_vendedor': PermissaoVendedor.query.filter_by(ativo=True).count(),
                'permissoes_equipe': PermissaoEquipe.query.filter_by(ativo=True).count()
            }
            return stats
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {}