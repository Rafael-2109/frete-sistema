"""
Rotas de Administração do Claude AI Lite.
Apenas para administradores.

Endpoints:
- GET /claude-lite/admin/aprendizados - Lista aprendizados
- POST /claude-lite/admin/aprendizados - Cria aprendizado
- PUT /claude-lite/admin/aprendizados/<id> - Atualiza aprendizado
- DELETE /claude-lite/admin/aprendizados/<id> - Remove aprendizado
- GET /claude-lite/admin/historico - Lista histórico
- DELETE /claude-lite/admin/historico/<usuario_id> - Limpa histórico
- GET /claude-lite/admin/estatisticas - Estatísticas gerais
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from functools import wraps

logger = logging.getLogger(__name__)

claude_lite_admin_bp = Blueprint('claude_lite_admin', __name__, url_prefix='/claude-lite/admin')


def admin_required(f):
    """Decorator que exige permissão de administrador."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Não autenticado'}), 401

        # Verifica se é admin (ajuste conforme seu modelo de usuário)
        is_admin = (
            getattr(current_user, 'is_admin', False) or
            getattr(current_user, 'admin', False) or
            getattr(current_user, 'perfil', '') == 'administrador' or
            current_user.id == 1  # Fallback: primeiro usuário é admin
        )

        if not is_admin:
            return jsonify({'success': False, 'error': 'Acesso negado. Apenas administradores.'}), 403

        return f(*args, **kwargs)
    return decorated_function


def _exempt_csrf():
    """Isenta rotas de API do CSRF."""
    try:
        from app import csrf
        csrf.exempt(claude_lite_admin_bp)
    except Exception:
        pass


_exempt_csrf()


# ============================================
# PÁGINA PRINCIPAL DE ADMINISTRAÇÃO
# ============================================

@claude_lite_admin_bp.route('/', methods=['GET'])
@login_required
@admin_required
def admin_dashboard():
    """Página principal de administração do Claude AI Lite."""
    return render_template('claude_ai_lite/admin.html')


# ============================================
# APRENDIZADOS
# ============================================

@claude_lite_admin_bp.route('/aprendizados', methods=['GET'])
@login_required
@admin_required
def listar_aprendizados():
    """Lista todos os aprendizados."""
    try:
        from .models import ClaudeAprendizado

        categoria = request.args.get('categoria')
        usuario_id = request.args.get('usuario_id', type=int)
        apenas_ativos = request.args.get('ativos', 'true').lower() == 'true'

        query = ClaudeAprendizado.query

        if apenas_ativos:
            query = query.filter(ClaudeAprendizado.ativo == True)

        if categoria:
            query = query.filter(ClaudeAprendizado.categoria == categoria)

        if usuario_id:
            query = query.filter(ClaudeAprendizado.usuario_id == usuario_id)

        aprendizados = query.order_by(
            ClaudeAprendizado.prioridade.desc(),
            ClaudeAprendizado.criado_em.desc()
        ).all()

        return jsonify({
            'success': True,
            'aprendizados': [a.to_dict() for a in aprendizados],
            'total': len(aprendizados)
        })

    except Exception as e:
        logger.error(f"[Admin] Erro ao listar aprendizados: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@claude_lite_admin_bp.route('/aprendizados', methods=['POST'])
@login_required
@admin_required
def criar_aprendizado():
    """Cria um novo aprendizado."""
    try:
        from .models import ClaudeAprendizado

        data = request.get_json()

        campos_obrigatorios = ['categoria', 'chave', 'valor']
        for campo in campos_obrigatorios:
            if not data.get(campo):
                return jsonify({'success': False, 'error': f'Campo {campo} obrigatório'}), 400

        aprendizado, criado = ClaudeAprendizado.adicionar(
            categoria=data['categoria'],
            chave=data['chave'],
            valor=data['valor'],
            usuario_id=data.get('usuario_id'),  # None = global
            criado_por=current_user.nome,
            prioridade=data.get('prioridade', 5),
            contexto=data.get('contexto')
        )

        return jsonify({
            'success': True,
            'aprendizado': aprendizado.to_dict(),
            'criado': criado,
            'mensagem': 'Aprendizado criado!' if criado else 'Aprendizado atualizado!'
        })

    except Exception as e:
        logger.error(f"[Admin] Erro ao criar aprendizado: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@claude_lite_admin_bp.route('/aprendizados/<int:id>', methods=['PUT'])
@login_required
@admin_required
def atualizar_aprendizado(id):
    """Atualiza um aprendizado existente."""
    try:
        from .models import ClaudeAprendizado
        from app import db

        aprendizado = ClaudeAprendizado.query.get(id)
        if not aprendizado:
            return jsonify({'success': False, 'error': 'Aprendizado não encontrado'}), 404

        data = request.get_json()

        if 'categoria' in data:
            aprendizado.categoria = data['categoria']
        if 'chave' in data:
            aprendizado.chave = data['chave']
        if 'valor' in data:
            aprendizado.valor = data['valor']
        if 'prioridade' in data:
            aprendizado.prioridade = data['prioridade']
        if 'ativo' in data:
            aprendizado.ativo = data['ativo']
        if 'contexto' in data:
            aprendizado.contexto = data['contexto']

        aprendizado.atualizado_por = current_user.nome
        db.session.commit()

        return jsonify({
            'success': True,
            'aprendizado': aprendizado.to_dict(),
            'mensagem': 'Aprendizado atualizado!'
        })

    except Exception as e:
        logger.error(f"[Admin] Erro ao atualizar aprendizado: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@claude_lite_admin_bp.route('/aprendizados/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def remover_aprendizado(id):
    """Remove (desativa) um aprendizado."""
    try:
        from .models import ClaudeAprendizado
        from app import db

        aprendizado = ClaudeAprendizado.query.get(id)
        if not aprendizado:
            return jsonify({'success': False, 'error': 'Aprendizado não encontrado'}), 404

        # Soft delete
        aprendizado.ativo = False
        aprendizado.atualizado_por = current_user.nome
        db.session.commit()

        return jsonify({
            'success': True,
            'mensagem': 'Aprendizado removido!'
        })

    except Exception as e:
        logger.error(f"[Admin] Erro ao remover aprendizado: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# HISTÓRICO
# ============================================

@claude_lite_admin_bp.route('/historico', methods=['GET'])
@login_required
@admin_required
def listar_historico():
    """Lista histórico de conversas."""
    try:
        from .models import ClaudeHistoricoConversa
        from app.auth.models import Usuario

        usuario_id = request.args.get('usuario_id', type=int)
        limite = request.args.get('limite', 100, type=int)

        query = ClaudeHistoricoConversa.query

        if usuario_id:
            query = query.filter(ClaudeHistoricoConversa.usuario_id == usuario_id)

        mensagens = query.order_by(
            ClaudeHistoricoConversa.criado_em.desc()
        ).limit(limite).all()

        # Busca nomes dos usuários
        usuarios = {}
        for msg in mensagens:
            if msg.usuario_id not in usuarios:
                user = Usuario.query.get(msg.usuario_id)
                usuarios[msg.usuario_id] = user.nome if user else f"Usuário {msg.usuario_id}"

        resultado = []
        for msg in mensagens:
            item = msg.to_dict()
            item['usuario_nome'] = usuarios.get(msg.usuario_id, 'Desconhecido')
            resultado.append(item)

        return jsonify({
            'success': True,
            'historico': resultado,
            'total': len(resultado)
        })

    except Exception as e:
        logger.error(f"[Admin] Erro ao listar histórico: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@claude_lite_admin_bp.route('/historico/<int:usuario_id>', methods=['DELETE'])
@login_required
@admin_required
def limpar_historico(usuario_id):
    """Limpa histórico de um usuário."""
    try:
        from .memory import MemoryService

        deletados = MemoryService.limpar_historico_usuario(usuario_id)

        return jsonify({
            'success': True,
            'mensagem': f'Histórico limpo! {deletados} mensagens removidas.'
        })

    except Exception as e:
        logger.error(f"[Admin] Erro ao limpar histórico: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# ESTATÍSTICAS
# ============================================

@claude_lite_admin_bp.route('/estatisticas', methods=['GET'])
@login_required
@admin_required
def estatisticas():
    """Retorna estatísticas gerais do Claude AI Lite."""
    try:
        from .models import ClaudeHistoricoConversa, ClaudeAprendizado
        from app.auth.models import Usuario
        from sqlalchemy import func

        # Total de mensagens
        total_mensagens = ClaudeHistoricoConversa.query.count()

        # Mensagens por tipo
        por_tipo = dict(
            ClaudeHistoricoConversa.query.with_entities(
                ClaudeHistoricoConversa.tipo,
                func.count(ClaudeHistoricoConversa.id)
            ).group_by(ClaudeHistoricoConversa.tipo).all()
        )

        # Aprendizados
        aprendizados_globais = ClaudeAprendizado.query.filter_by(
            usuario_id=None, ativo=True
        ).count()

        aprendizados_usuarios = ClaudeAprendizado.query.filter(
            ClaudeAprendizado.usuario_id.isnot(None),
            ClaudeAprendizado.ativo == True
        ).count()

        # Usuários ativos (com histórico)
        usuarios_ativos = ClaudeHistoricoConversa.query.with_entities(
            ClaudeHistoricoConversa.usuario_id
        ).distinct().count()

        # Top usuários
        top_usuarios = ClaudeHistoricoConversa.query.with_entities(
            ClaudeHistoricoConversa.usuario_id,
            func.count(ClaudeHistoricoConversa.id).label('total')
        ).group_by(
            ClaudeHistoricoConversa.usuario_id
        ).order_by(
            func.count(ClaudeHistoricoConversa.id).desc()
        ).limit(10).all()

        # Busca nomes
        top_com_nomes = []
        for uid, total in top_usuarios:
            user = Usuario.query.get(uid)
            top_com_nomes.append({
                'usuario_id': uid,
                'nome': user.nome if user else f'Usuário {uid}',
                'total_mensagens': total
            })

        return jsonify({
            'success': True,
            'estatisticas': {
                'total_mensagens': total_mensagens,
                'mensagens_por_tipo': por_tipo,
                'aprendizados_globais': aprendizados_globais,
                'aprendizados_usuarios': aprendizados_usuarios,
                'usuarios_ativos': usuarios_ativos,
                'top_usuarios': top_com_nomes
            }
        })

    except Exception as e:
        logger.error(f"[Admin] Erro ao buscar estatísticas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# CATEGORIAS
# ============================================

@claude_lite_admin_bp.route('/categorias', methods=['GET'])
@login_required
@admin_required
def listar_categorias():
    """Lista categorias disponíveis para aprendizados."""
    categorias = [
        {'valor': 'preferencia', 'nome': 'Preferência', 'descricao': 'Preferências pessoais do usuário'},
        {'valor': 'correcao', 'nome': 'Correção', 'descricao': 'Correções de informações'},
        {'valor': 'regra_negocio', 'nome': 'Regra de Negócio', 'descricao': 'Regras e políticas da empresa'},
        {'valor': 'fato', 'nome': 'Fato', 'descricao': 'Fatos gerais sobre o sistema'},
        {'valor': 'cliente', 'nome': 'Cliente', 'descricao': 'Informações sobre clientes'},
        {'valor': 'produto', 'nome': 'Produto', 'descricao': 'Informações sobre produtos'},
        {'valor': 'processo', 'nome': 'Processo', 'descricao': 'Processos e procedimentos'},
    ]

    return jsonify({
        'success': True,
        'categorias': categorias
    })


# ============================================
# IA TRAINER - APIs integradas na Admin
# ============================================

@claude_lite_admin_bp.route('/trainer/estatisticas', methods=['GET'])
@login_required
@admin_required
def trainer_estatisticas():
    """Retorna estatísticas do IA Trainer."""
    try:
        from .models import ClaudePerguntaNaoRespondida
        from .ia_trainer.models import CodigoSistemaGerado, SessaoEnsinoIA

        # Perguntas pendentes
        perguntas_pendentes = ClaudePerguntaNaoRespondida.query.filter_by(
            status='pendente'
        ).count()

        # Códigos ativos
        codigos_ativos = CodigoSistemaGerado.query.filter_by(
            ativo=True
        ).count()

        # Sessões em andamento
        sessoes_andamento = SessaoEnsinoIA.query.filter(
            SessaoEnsinoIA.status.in_(['iniciada', 'decomposta', 'gerada'])
        ).count()

        # Cache stats
        cache_stats = {}
        try:
            from .cache import get_stats
            cache_stats = get_stats()
        except Exception:
            cache_stats = {'disponivel': False}

        return jsonify({
            'success': True,
            'estatisticas': {
                'perguntas_pendentes': perguntas_pendentes,
                'codigos_ativos': codigos_ativos,
                'sessoes_andamento': sessoes_andamento,
                'cache': {
                    'total_chaves': cache_stats.get('total_chaves', 0),
                    'tipo': 'Redis' if cache_stats.get('disponivel') else 'Memória'
                }
            }
        })

    except Exception as e:
        logger.error(f"[Admin] Erro ao buscar estatísticas do trainer: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@claude_lite_admin_bp.route('/trainer/perguntas', methods=['GET'])
@login_required
@admin_required
def trainer_perguntas():
    """Lista perguntas não respondidas."""
    try:
        from .models import ClaudePerguntaNaoRespondida

        status = request.args.get('status', 'pendente')
        limite = request.args.get('limite', 50, type=int)

        query = ClaudePerguntaNaoRespondida.query

        if status and status != 'todas':
            query = query.filter_by(status=status)

        perguntas = query.order_by(
            ClaudePerguntaNaoRespondida.criado_em.desc()
        ).limit(limite).all()

        return jsonify({
            'success': True,
            'total': len(perguntas),
            'perguntas': [p.to_dict() for p in perguntas]
        })

    except Exception as e:
        logger.error(f"[Admin] Erro ao listar perguntas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@claude_lite_admin_bp.route('/trainer/codigos', methods=['GET'])
@login_required
@admin_required
def trainer_codigos():
    """Lista códigos gerados pelo IA Trainer."""
    try:
        from .ia_trainer.models import CodigoSistemaGerado

        tipo = request.args.get('tipo')
        ativo = request.args.get('ativo')
        limite = request.args.get('limite', 50, type=int)

        query = CodigoSistemaGerado.query

        if tipo:
            query = query.filter_by(tipo_codigo=tipo)
        if ativo is not None:
            query = query.filter_by(ativo=(ativo == 'true'))

        codigos = query.order_by(
            CodigoSistemaGerado.criado_em.desc()
        ).limit(limite).all()

        return jsonify({
            'success': True,
            'total': len(codigos),
            'codigos': [c.to_dict() for c in codigos]
        })

    except Exception as e:
        logger.error(f"[Admin] Erro ao listar códigos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@claude_lite_admin_bp.route('/trainer/codigos/<int:codigo_id>/toggle', methods=['POST'])
@login_required
@admin_required
def trainer_toggle_codigo(codigo_id):
    """Ativa/desativa um código."""
    try:
        from .ia_trainer.models import CodigoSistemaGerado
        from .ia_trainer.services.codigo_loader import invalidar_cache
        from app import db

        codigo = CodigoSistemaGerado.query.get_or_404(codigo_id)
        codigo.ativo = not codigo.ativo
        codigo.atualizado_por = current_user.nome
        db.session.commit()

        # Invalida cache
        invalidar_cache()

        return jsonify({
            'success': True,
            'ativo': codigo.ativo,
            'mensagem': f"Código {'ativado' if codigo.ativo else 'desativado'} com sucesso!"
        })

    except Exception as e:
        logger.error(f"[Admin] Erro ao toggle código: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@claude_lite_admin_bp.route('/trainer/codigos/<int:codigo_id>', methods=['PUT'])
@login_required
@admin_required
def trainer_atualizar_codigo(codigo_id):
    """Atualiza definição técnica de um código."""
    try:
        from .ia_trainer.models import CodigoSistemaGerado
        from .ia_trainer.services.codigo_loader import invalidar_cache
        from app import db

        codigo = CodigoSistemaGerado.query.get_or_404(codigo_id)
        data = request.get_json()

        # Atualizar definição técnica
        if 'definicao_tecnica' in data:
            definicao = data['definicao_tecnica']
            # Se veio como string, validar JSON
            if isinstance(definicao, str):
                import json
                try:
                    json.loads(definicao)  # Apenas valida
                except json.JSONDecodeError as e:
                    return jsonify({'success': False, 'error': f'JSON inválido: {e}'}), 400
            codigo.definicao_tecnica = definicao

        codigo.atualizado_por = current_user.nome
        db.session.commit()

        # Invalida cache
        invalidar_cache()

        return jsonify({
            'success': True,
            'mensagem': 'Código atualizado com sucesso!'
        })

    except Exception as e:
        logger.error(f"[Admin] Erro ao atualizar código: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@claude_lite_admin_bp.route('/trainer/cache/invalidar', methods=['POST'])
@login_required
@admin_required
def trainer_invalidar_cache():
    """Invalida todo o cache do Claude AI Lite."""
    try:
        from .cache import invalidar_tudo
        from .ia_trainer.services.codigo_loader import invalidar_cache

        # Invalida cache de códigos
        invalidar_cache()

        # Invalida todo cache do módulo
        removidos = invalidar_tudo()

        return jsonify({
            'success': True,
            'mensagem': f'Cache invalidado com sucesso! ({removidos} chaves removidas)'
        })

    except Exception as e:
        logger.error(f"[Admin] Erro ao invalidar cache: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
