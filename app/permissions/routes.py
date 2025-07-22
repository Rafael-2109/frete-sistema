"""
Rotas para Administração de Permissões Granulares
================================================

Interface web para gestão completa de permissões:
- Visualização hierárquica módulo → função
- Gestão de múltiplos vendedores/equipes por usuário
- Controle granular visualizar/editar
- Log de auditoria em tempo real
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
import logging

from app import db
from app.permissions import permissions_bp
from app.permissions.models import (
    PerfilUsuario, ModuloSistema, FuncaoModulo, PermissaoUsuario,
    UsuarioVendedor, UsuarioEquipeVendas, LogPermissao
)
from app.auth.models import Usuario
from app.utils.auth_decorators import require_admin
from app.permissions.services import PermissaoService

logger = logging.getLogger(__name__)

# ============================================================================
# PÁGINA PRINCIPAL DE ADMINISTRAÇÃO
# ============================================================================

@permissions_bp.route('/')
@login_required
@require_admin
def index():
    """
    Página principal de administração de permissões
    Interface hierárquica para gestão completa
    """
    try:
        # Carregar dados para interface
        usuarios = Usuario.query.filter_by(status='ativo').order_by(Usuario.nome).all()
        modulos = ModuloSistema.query.filter_by(ativo=True).order_by(ModuloSistema.ordem).all()
        perfis = PerfilUsuario.query.filter_by(ativo=True).order_by(PerfilUsuario.nivel_hierarquico.desc()).all()
        
        # Estatísticas gerais
        stats = {
            'total_usuarios': Usuario.query.filter_by(status='ativo').count(),
            'total_permissoes': PermissaoUsuario.query.filter_by(ativo=True).count(),
            'total_modulos': ModuloSistema.query.filter_by(ativo=True).count(),
            'total_funcoes': FuncaoModulo.query.filter_by(ativo=True).count(),
        }
        
        return render_template(
            'permissions/admin_index.html',
            usuarios=usuarios,
            modulos=modulos,
            perfis=perfis,
            stats=stats
        )
        
    except Exception as e:
        logger.error(f"Erro ao carregar página de administração: {e}")
        flash('Erro ao carregar página de administração', 'error')
        return redirect(url_for('main.dashboard'))

# ============================================================================
# API: CARREGAR PERMISSÕES DE USUÁRIO
# ============================================================================

@permissions_bp.route('/api/usuario/<int:usuario_id>/permissoes')
@login_required
@require_admin
def api_permissoes_usuario(usuario_id):
    """
    API: Carrega permissões completas de um usuário
    Retorna estrutura hierárquica módulo → função → permissões
    """
    try:
        usuario = Usuario.query.get_or_404(usuario_id)
        
        # Carregar estrutura completa
        resultado = {
            'usuario': {
                'id': usuario.id,
                'nome': usuario.nome,
                'email': usuario.email,
                'perfil': usuario.perfil
            },
            'modulos': [],
            'vendedores': [],
            'equipes_vendas': [],
            'estatisticas': {}
        }
        
        # Carregar módulos e funções com permissões
        modulos = ModuloSistema.query.filter_by(ativo=True).order_by(ModuloSistema.ordem).all()
        
        for modulo in modulos:
            modulo_data = {
                'id': modulo.id,
                'nome': modulo.nome,
                'nome_exibicao': modulo.nome_exibicao,
                'icone': modulo.icone,
                'cor': modulo.cor,
                'funcoes': []
            }
            
            # Carregar funções do módulo
            funcoes = FuncaoModulo.query.filter_by(
                modulo_id=modulo.id, ativo=True
            ).order_by(FuncaoModulo.ordem).all()
            
            for funcao in funcoes:
                # Buscar permissão existente
                permissao = PermissaoUsuario.query.filter_by(
                    usuario_id=usuario_id,
                    funcao_id=funcao.id,
                    ativo=True
                ).first()
                
                funcao_data = {
                    'id': funcao.id,
                    'nome': funcao.nome,
                    'nome_exibicao': funcao.nome_exibicao,
                    'nivel_critico': funcao.nivel_critico,
                    'permissao': {
                        'id': permissao.id if permissao else None,
                        'pode_visualizar': permissao.pode_visualizar if permissao else False,
                        'pode_editar': permissao.pode_editar if permissao else False,
                        'concedida_em': permissao.concedida_em.isoformat() if permissao else None
                    }
                }
                
                modulo_data['funcoes'].append(funcao_data)
            
            resultado['modulos'].append(modulo_data)
        
        # Carregar vendedores autorizados
        vendedores = UsuarioVendedor.query.filter_by(
            usuario_id=usuario_id, ativo=True
        ).all()
        
        resultado['vendedores'] = [{
            'id': v.id,
            'vendedor': v.vendedor,
            'adicionado_em': v.adicionado_em.isoformat(),
            'observacoes': v.observacoes
        } for v in vendedores]
        
        # Carregar equipes autorizadas
        equipes = UsuarioEquipeVendas.query.filter_by(
            usuario_id=usuario_id, ativo=True
        ).all()
        
        resultado['equipes_vendas'] = [{
            'id': e.id,
            'equipe_vendas': e.equipe_vendas,
            'adicionado_em': e.adicionado_em.isoformat(),
            'observacoes': e.observacoes
        } for e in equipes]
        
        # Estatísticas do usuário
        resultado['estatisticas'] = {
            'total_permissoes': PermissaoUsuario.query.filter_by(usuario_id=usuario_id, ativo=True).count(),
            'total_vendedores': len(resultado['vendedores']),
            'total_equipes': len(resultado['equipes_vendas']),
            'ultimo_login': usuario.ultimo_login.isoformat() if usuario.ultimo_login else None
        }
        
        return jsonify({
            'success': True,
            'data': resultado
        })
        
    except Exception as e:
        logger.error(f"Erro ao carregar permissões do usuário {usuario_id}: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500

# ============================================================================
# API: SALVAR PERMISSÃO INDIVIDUAL
# ============================================================================

@permissions_bp.route('/api/permissao', methods=['POST'])
@login_required
@require_admin
def api_salvar_permissao():
    """
    API: Salva uma permissão individual usuário → função
    Permite controle granular visualizar/editar
    """
    try:
        data = request.get_json()
        
        # Validar dados obrigatórios
        required_fields = ['usuario_id', 'funcao_id', 'pode_visualizar', 'pode_editar']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo obrigatório: {field}'
                }), 400
        
        # Validar se usuário e função existem
        usuario = Usuario.query.get(data['usuario_id'])
        if not usuario:
            return jsonify({
                'success': False,
                'message': 'Usuário não encontrado'
            }), 404
        
        funcao = FuncaoModulo.query.get(data['funcao_id'])
        if not funcao:
            return jsonify({
                'success': False,
                'message': 'Função não encontrada'
            }), 404
        
        # Buscar permissão existente
        permissao = PermissaoUsuario.query.filter_by(
            usuario_id=data['usuario_id'],
            funcao_id=data['funcao_id']
        ).first()
        
        # Criar ou atualizar permissão
        if permissao:
            # Atualizar existente
            permissao.pode_visualizar = bool(data['pode_visualizar'])
            permissao.pode_editar = bool(data['pode_editar'])
            permissao.observacoes = data.get('observacoes')
            permissao.ativo = True
            acao = 'ATUALIZADA'
        else:
            # Criar nova
            permissao = PermissaoUsuario(
                usuario_id=data['usuario_id'],
                funcao_id=data['funcao_id'],
                pode_visualizar=bool(data['pode_visualizar']),
                pode_editar=bool(data['pode_editar']),
                concedida_por=current_user.id,
                observacoes=data.get('observacoes')
            )
            db.session.add(permissao)
            acao = 'CONCEDIDA'
        
        db.session.commit()
        
        # Registrar no log de auditoria
        LogPermissao.registrar(
            usuario_id=data['usuario_id'],
            acao=f'PERMISSAO_{acao}',
            funcao_id=data['funcao_id'],
            detalhes=f"Visualizar: {data['pode_visualizar']}, Editar: {data['pode_editar']}",
            ip_origem=request.environ.get('REMOTE_ADDR'),
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': f'Permissão {acao.lower()} com sucesso',
            'data': {
                'id': permissao.id,
                'pode_visualizar': permissao.pode_visualizar,
                'pode_editar': permissao.pode_editar,
                'nivel_acesso': permissao.nivel_acesso
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao salvar permissão: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500

# ============================================================================
# API: SALVAR PERMISSÕES DE MÓDULO (EM LOTE)
# ============================================================================

@permissions_bp.route('/api/modulo/<int:modulo_id>/permissoes', methods=['POST'])
@login_required
@require_admin
def api_salvar_permissoes_modulo(modulo_id):
    """
    API: Salva permissões de todas as funções de um módulo em lote
    Permite aplicar visualizar/editar a todas as funções rapidamente
    """
    try:
        data = request.get_json()
        
        # Validar dados
        if 'usuario_id' not in data:
            return jsonify({
                'success': False,
                'message': 'Campo obrigatório: usuario_id'
            }), 400
        
        # Validar se usuário e módulo existem
        usuario = Usuario.query.get(data['usuario_id'])
        if not usuario:
            return jsonify({
                'success': False,
                'message': 'Usuário não encontrado'
            }), 404
        
        modulo = ModuloSistema.query.get(modulo_id)
        if not modulo:
            return jsonify({
                'success': False,
                'message': 'Módulo não encontrado'
            }), 404
        
        # Buscar todas as funções do módulo
        funcoes = FuncaoModulo.query.filter_by(
            modulo_id=modulo_id, ativo=True
        ).all()
        
        if not funcoes:
            return jsonify({
                'success': False,
                'message': 'Nenhuma função encontrada no módulo'
            }), 404
        
        # Aplicar permissões a todas as funções
        permissoes_atualizadas = 0
        permissoes_criadas = 0
        
        for funcao in funcoes:
            # Buscar permissão existente
            permissao = PermissaoUsuario.query.filter_by(
                usuario_id=data['usuario_id'],
                funcao_id=funcao.id
            ).first()
            
            if permissao:
                # Atualizar existente
                permissao.pode_visualizar = bool(data.get('pode_visualizar', False))
                permissao.pode_editar = bool(data.get('pode_editar', False))
                permissao.ativo = True
                permissoes_atualizadas += 1
            else:
                # Criar nova
                permissao = PermissaoUsuario(
                    usuario_id=data['usuario_id'],
                    funcao_id=funcao.id,
                    pode_visualizar=bool(data.get('pode_visualizar', False)),
                    pode_editar=bool(data.get('pode_editar', False)),
                    concedida_por=current_user.id
                )
                db.session.add(permissao)
                permissoes_criadas += 1
        
        db.session.commit()
        
        # Registrar no log de auditoria
        LogPermissao.registrar(
            usuario_id=data['usuario_id'],
            acao='MODULO_CONFIGURADO',
            detalhes=f"Módulo: {modulo.nome}, Visualizar: {data.get('pode_visualizar')}, Editar: {data.get('pode_editar')}, Funções: {len(funcoes)}",
            ip_origem=request.environ.get('REMOTE_ADDR'),
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': f'Permissões aplicadas: {permissoes_criadas} criadas, {permissoes_atualizadas} atualizadas',
            'data': {
                'modulo': modulo.nome,
                'funcoes_afetadas': len(funcoes),
                'permissoes_criadas': permissoes_criadas,
                'permissoes_atualizadas': permissoes_atualizadas
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao salvar permissões do módulo {modulo_id}: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500

# ============================================================================
# API: GERENCIAR VENDEDORES DE USUÁRIO
# ============================================================================

@permissions_bp.route('/api/usuario/<int:usuario_id>/vendedores', methods=['GET', 'POST', 'DELETE'])
@login_required
@require_admin
def api_gerenciar_vendedores(usuario_id):
    """
    API: Gerencia vendedores autorizados para um usuário
    GET: Lista vendedores autorizados
    POST: Adiciona novo vendedor
    DELETE: Remove vendedor (via query param vendedor_id)
    """
    try:
        usuario = Usuario.query.get_or_404(usuario_id)
        
        if request.method == 'GET':
            # Listar vendedores autorizados
            vendedores = UsuarioVendedor.query.filter_by(
                usuario_id=usuario_id, ativo=True
            ).all()
            
            # Buscar todos os vendedores disponíveis no sistema
            from app.faturamento.models import RelatorioFaturamentoImportado
            vendedores_sistema = db.session.query(RelatorioFaturamentoImportado.vendedor)\
                .filter(RelatorioFaturamentoImportado.vendedor.isnot(None))\
                .distinct().all()
            vendedores_disponiveis = [v[0] for v in vendedores_sistema if v[0]]
            
            return jsonify({
                'success': True,
                'data': {
                    'vendedores_autorizados': [{
                        'id': v.id,
                        'vendedor': v.vendedor,
                        'adicionado_em': v.adicionado_em.isoformat()
                    } for v in vendedores],
                    'vendedores_disponiveis': sorted(vendedores_disponiveis)
                }
            })
        
        elif request.method == 'POST':
            # Adicionar novo vendedor
            data = request.get_json()
            
            if 'vendedor' not in data:
                return jsonify({
                    'success': False,
                    'message': 'Campo obrigatório: vendedor'
                }), 400
            
            # Verificar se já existe
            vendedor_existente = UsuarioVendedor.query.filter_by(
                usuario_id=usuario_id,
                vendedor=data['vendedor']
            ).first()
            
            if vendedor_existente:
                if vendedor_existente.ativo:
                    return jsonify({
                        'success': False,
                        'message': 'Vendedor já autorizado para este usuário'
                    }), 400
                else:
                    # Reativar vendedor
                    vendedor_existente.ativo = True
                    vendedor_existente.adicionado_por = current_user.id
                    vendedor_existente.adicionado_em = datetime.now()
            else:
                # Criar novo
                vendedor_existente = UsuarioVendedor(
                    usuario_id=usuario_id,
                    vendedor=data['vendedor'],
                    adicionado_por=current_user.id,
                    observacoes=data.get('observacoes')
                )
                db.session.add(vendedor_existente)
            
            db.session.commit()
            
            # Registrar no log
            LogPermissao.registrar(
                usuario_id=usuario_id,
                acao='VENDEDOR_ADICIONADO',
                detalhes=f"Vendedor: {data['vendedor']}",
                ip_origem=request.environ.get('REMOTE_ADDR')
            )
            
            return jsonify({
                'success': True,
                'message': 'Vendedor adicionado com sucesso',
                'data': {
                    'id': vendedor_existente.id,
                    'vendedor': vendedor_existente.vendedor
                }
            })
        
        elif request.method == 'DELETE':
            # Remover vendedor
            vendedor_id = request.args.get('vendedor_id')
            if not vendedor_id:
                return jsonify({
                    'success': False,
                    'message': 'Parâmetro obrigatório: vendedor_id'
                }), 400
            
            vendedor = UsuarioVendedor.query.filter_by(
                id=vendedor_id,
                usuario_id=usuario_id
            ).first()
            
            if not vendedor:
                return jsonify({
                    'success': False,
                    'message': 'Vendedor não encontrado'
                }), 404
            
            # Soft delete
            vendedor.ativo = False
            db.session.commit()
            
            # Registrar no log
            LogPermissao.registrar(
                usuario_id=usuario_id,
                acao='VENDEDOR_REMOVIDO',
                detalhes=f"Vendedor: {vendedor.vendedor}",
                ip_origem=request.environ.get('REMOTE_ADDR')
            )
            
            return jsonify({
                'success': True,
                'message': 'Vendedor removido com sucesso'
            })
        
    except Exception as e:
        logger.error(f"Erro ao gerenciar vendedores do usuário {usuario_id}: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500

# ============================================================================
# API: GERENCIAR EQUIPES DE VENDAS DE USUÁRIO
# ============================================================================

@permissions_bp.route('/api/usuario/<int:usuario_id>/equipes', methods=['GET', 'POST', 'DELETE'])
@login_required
@require_admin
def api_gerenciar_equipes(usuario_id):
    """
    API: Gerencia equipes de vendas autorizadas para um usuário
    Mesmo padrão da API de vendedores
    """
    try:
        usuario = Usuario.query.get_or_404(usuario_id)
        
        if request.method == 'GET':
            # Listar equipes autorizadas
            equipes = UsuarioEquipeVendas.query.filter_by(
                usuario_id=usuario_id, ativo=True
            ).all()
            
            # Buscar todas as equipes disponíveis no sistema
            from app.carteira.models import CarteiraPrincipal
            equipes_sistema = db.session.query(CarteiraPrincipal.equipe_vendas)\
                .filter(CarteiraPrincipal.equipe_vendas.isnot(None))\
                .distinct().all()
            equipes_disponiveis = [e[0] for e in equipes_sistema if e[0]]
            
            return jsonify({
                'success': True,
                'data': {
                    'equipes_autorizadas': [{
                        'id': e.id,
                        'equipe_vendas': e.equipe_vendas,
                        'adicionado_em': e.adicionado_em.isoformat()
                    } for e in equipes],
                    'equipes_disponiveis': sorted(equipes_disponiveis)
                }
            })
        
        elif request.method == 'POST':
            # Adicionar nova equipe
            data = request.get_json()
            
            if 'equipe_vendas' not in data:
                return jsonify({
                    'success': False,
                    'message': 'Campo obrigatório: equipe_vendas'
                }), 400
            
            # Verificar se já existe
            equipe_existente = UsuarioEquipeVendas.query.filter_by(
                usuario_id=usuario_id,
                equipe_vendas=data['equipe_vendas']
            ).first()
            
            if equipe_existente:
                if equipe_existente.ativo:
                    return jsonify({
                        'success': False,
                        'message': 'Equipe já autorizada para este usuário'
                    }), 400
                else:
                    # Reativar equipe
                    equipe_existente.ativo = True
                    equipe_existente.adicionado_por = current_user.id
                    equipe_existente.adicionado_em = datetime.now()
            else:
                # Criar nova
                equipe_existente = UsuarioEquipeVendas(
                    usuario_id=usuario_id,
                    equipe_vendas=data['equipe_vendas'],
                    adicionado_por=current_user.id,
                    observacoes=data.get('observacoes')
                )
                db.session.add(equipe_existente)
            
            db.session.commit()
            
            # Registrar no log
            LogPermissao.registrar(
                usuario_id=usuario_id,
                acao='EQUIPE_ADICIONADA',
                detalhes=f"Equipe: {data['equipe_vendas']}",
                ip_origem=request.environ.get('REMOTE_ADDR')
            )
            
            return jsonify({
                'success': True,
                'message': 'Equipe adicionada com sucesso',
                'data': {
                    'id': equipe_existente.id,
                    'equipe_vendas': equipe_existente.equipe_vendas
                }
            })
        
        elif request.method == 'DELETE':
            # Remover equipe
            equipe_id = request.args.get('equipe_id')
            if not equipe_id:
                return jsonify({
                    'success': False,
                    'message': 'Parâmetro obrigatório: equipe_id'
                }), 400
            
            equipe = UsuarioEquipeVendas.query.filter_by(
                id=equipe_id,
                usuario_id=usuario_id
            ).first()
            
            if not equipe:
                return jsonify({
                    'success': False,
                    'message': 'Equipe não encontrada'
                }), 404
            
            # Soft delete
            equipe.ativo = False
            db.session.commit()
            
            # Registrar no log
            LogPermissao.registrar(
                usuario_id=usuario_id,
                acao='EQUIPE_REMOVIDA',
                detalhes=f"Equipe: {equipe.equipe_vendas}",
                ip_origem=request.environ.get('REMOTE_ADDR')
            )
            
            return jsonify({
                'success': True,
                'message': 'Equipe removida com sucesso'
            })
        
    except Exception as e:
        logger.error(f"Erro ao gerenciar equipes do usuário {usuario_id}: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500

# ============================================================================
# API: LOG DE AUDITORIA
# ============================================================================

@permissions_bp.route('/api/logs')
@login_required
@require_admin
def api_logs_auditoria():
    """
    API: Busca logs de auditoria de permissões
    Suporte a filtros por usuário, ação, período
    """
    try:
        # Parâmetros de filtro
        usuario_id = request.args.get('usuario_id')
        acao = request.args.get('acao')
        dias = int(request.args.get('dias', 7))
        limite = int(request.args.get('limite', 50))
        
        # Construir query
        query = LogPermissao.query
        
        if usuario_id:
            query = query.filter_by(usuario_id=usuario_id)
        
        if acao:
            query = query.filter(LogPermissao.acao.like(f'%{acao}%'))
        
        # Filtro por período
        from datetime import datetime, timedelta
        data_inicio = datetime.now() - timedelta(days=dias)
        query = query.filter(LogPermissao.timestamp >= data_inicio)
        
        # Ordenar e limitar
        logs = query.order_by(LogPermissao.timestamp.desc()).limit(limite).all()
        
        return jsonify({
            'success': True,
            'data': [{
                'id': log.id,
                'usuario': log.usuario.nome if log.usuario else 'Sistema',
                'acao': log.acao,
                'funcao': log.funcao.nome_completo if log.funcao else None,
                'detalhes': log.detalhes,
                'resultado': log.resultado,
                'timestamp': log.timestamp.isoformat(),
                'ip_origem': log.ip_origem
            } for log in logs],
            'total': len(logs),
            'filtros': {
                'usuario_id': usuario_id,
                'acao': acao,
                'dias': dias,
                'limite': limite
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar logs de auditoria: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500 