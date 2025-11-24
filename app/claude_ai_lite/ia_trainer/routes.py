"""
Rotas do IA Trainer.

Endpoints para:
- Listar perguntas nao respondidas
- Iniciar sessao de ensino
- Salvar decomposicao
- Gerar codigo
- Debater/refinar
- Testar
- Ativar

Acesso: Apenas administradores
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('ia_trainer', __name__, url_prefix='/claude-lite/trainer')


def admin_required(f):
    """Decorator para verificar se usuario e admin."""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'erro': 'Nao autenticado'}), 401

        # Verifica se é admin (multiplas formas)
        is_admin = (
            getattr(current_user, 'is_admin', False) or
            getattr(current_user, 'admin', False) or
            getattr(current_user, 'perfil', '') == 'administrador' or
            current_user.id == 1  # Fallback: primeiro usuario é admin
        )

        if not is_admin:
            return jsonify({'erro': 'Acesso restrito a administradores'}), 403
        return f(*args, **kwargs)
    return decorated_function


# ==========================================
# PAGINAS
# ==========================================

@bp.route('/')
@login_required
@admin_required
def index():
    """Pagina principal do IA Trainer."""
    return render_template('claude_ai_lite/ia_trainer/index.html')


@bp.route('/ensinar/<int:pergunta_id>')
@login_required
@admin_required
def ensinar(pergunta_id: int):
    """Pagina de ensino para uma pergunta especifica."""
    from ..models import ClaudePerguntaNaoRespondida

    pergunta = ClaudePerguntaNaoRespondida.query.get_or_404(pergunta_id)

    return render_template(
        'claude_ai_lite/ia_trainer/ensinar.html',
        pergunta=pergunta.to_dict()
    )


@bp.route('/sessao/<int:sessao_id>')
@login_required
@admin_required
def ver_sessao(sessao_id: int):
    """Pagina de uma sessao de ensino."""
    from .services import TrainerService

    service = TrainerService()
    sessao = service.obter_sessao(sessao_id)

    if not sessao:
        return "Sessao nao encontrada", 404

    return render_template(
        'claude_ai_lite/ia_trainer/sessao.html',
        sessao=sessao
    )


# ==========================================
# API - PERGUNTAS NAO RESPONDIDAS
# ==========================================

@bp.route('/api/perguntas')
@login_required
@admin_required
def api_listar_perguntas():
    """Lista perguntas nao respondidas."""
    from ..models import ClaudePerguntaNaoRespondida

    status = request.args.get('status', 'pendente')
    limite = request.args.get('limite', 50, type=int)

    if status == 'todas':
        perguntas = ClaudePerguntaNaoRespondida.query.order_by(
            ClaudePerguntaNaoRespondida.criado_em.desc()
        ).limit(limite).all()
    else:
        perguntas = ClaudePerguntaNaoRespondida.query.filter_by(
            status=status
        ).order_by(
            ClaudePerguntaNaoRespondida.criado_em.desc()
        ).limit(limite).all()

    return jsonify({
        'sucesso': True,
        'total': len(perguntas),
        'perguntas': [p.to_dict() for p in perguntas]
    })


@bp.route('/api/perguntas/estatisticas')
@login_required
@admin_required
def api_estatisticas_perguntas():
    """Estatisticas de perguntas nao respondidas."""
    from ..models import ClaudePerguntaNaoRespondida

    dias = request.args.get('dias', 7, type=int)
    stats = ClaudePerguntaNaoRespondida.estatisticas(dias=dias)

    return jsonify({
        'sucesso': True,
        **stats
    })


# ==========================================
# API - SESSOES DE ENSINO
# ==========================================

@bp.route('/api/sessao/iniciar', methods=['POST'])
@login_required
@admin_required
def api_iniciar_sessao():
    """Inicia uma nova sessao de ensino."""
    from .services import TrainerService

    dados = request.get_json()
    pergunta_id = dados.get('pergunta_id')

    if not pergunta_id:
        return jsonify({'sucesso': False, 'erro': 'pergunta_id obrigatorio'}), 400

    service = TrainerService()
    resultado = service.iniciar_sessao(
        pergunta_id=pergunta_id,
        usuario=current_user.nome
    )

    return jsonify(resultado)


@bp.route('/api/sessao/<int:sessao_id>')
@login_required
@admin_required
def api_obter_sessao(sessao_id: int):
    """Obtem dados de uma sessao."""
    from .services import TrainerService

    service = TrainerService()
    sessao = service.obter_sessao(sessao_id)

    if not sessao:
        return jsonify({'sucesso': False, 'erro': 'Sessao nao encontrada'}), 404

    return jsonify({'sucesso': True, 'sessao': sessao})


@bp.route('/api/sessao/<int:sessao_id>/sugerir-decomposicao', methods=['POST'])
@login_required
@admin_required
def api_sugerir_decomposicao(sessao_id: int):
    """Sugere decomposicao inicial."""
    from .services import TrainerService

    service = TrainerService()
    resultado = service.sugerir_decomposicao(sessao_id)

    return jsonify(resultado)


@bp.route('/api/sessao/<int:sessao_id>/decomposicao', methods=['POST'])
@login_required
@admin_required
def api_salvar_decomposicao(sessao_id: int):
    """Salva decomposicao do usuario."""
    from .services import TrainerService

    dados = request.get_json()
    decomposicao = dados.get('decomposicao', [])

    if not decomposicao:
        return jsonify({'sucesso': False, 'erro': 'decomposicao obrigatoria'}), 400

    service = TrainerService()
    resultado = service.salvar_decomposicao(sessao_id, decomposicao)

    return jsonify(resultado)


@bp.route('/api/sessao/<int:sessao_id>/gerar', methods=['POST'])
@login_required
@admin_required
def api_gerar_codigo(sessao_id: int):
    """Gera codigo baseado na decomposicao."""
    from .services import TrainerService

    service = TrainerService()
    resultado = service.gerar_codigo(sessao_id)

    return jsonify(resultado)


@bp.route('/api/sessao/<int:sessao_id>/debater', methods=['POST'])
@login_required
@admin_required
def api_debater(sessao_id: int):
    """Envia mensagem de debate."""
    from .services import TrainerService

    dados = request.get_json()
    mensagem = dados.get('mensagem', '')

    if not mensagem:
        return jsonify({'sucesso': False, 'erro': 'mensagem obrigatoria'}), 400

    service = TrainerService()
    resultado = service.debater(sessao_id, mensagem)

    return jsonify(resultado)


@bp.route('/api/sessao/<int:sessao_id>/testar', methods=['POST'])
@login_required
@admin_required
def api_testar_codigo(sessao_id: int):
    """Testa o codigo gerado."""
    from .services import TrainerService

    service = TrainerService()
    resultado = service.testar_codigo(sessao_id)

    return jsonify(resultado)


@bp.route('/api/sessao/<int:sessao_id>/ativar', methods=['POST'])
@login_required
@admin_required
def api_ativar_codigo(sessao_id: int):
    """Ativa o codigo gerado."""
    from .services import TrainerService

    service = TrainerService()
    resultado = service.ativar_codigo(sessao_id, current_user.nome)

    return jsonify(resultado)


@bp.route('/api/sessao/<int:sessao_id>/cancelar', methods=['POST'])
@login_required
@admin_required
def api_cancelar_sessao(sessao_id: int):
    """Cancela uma sessao."""
    from .services import TrainerService

    service = TrainerService()
    resultado = service.cancelar_sessao(sessao_id)

    return jsonify(resultado)


@bp.route('/api/sessoes')
@login_required
@admin_required
def api_listar_sessoes():
    """Lista sessoes de ensino."""
    from .services import TrainerService

    status = request.args.get('status')
    limite = request.args.get('limite', 20, type=int)

    service = TrainerService()
    sessoes = service.listar_sessoes(status=status, limite=limite)

    return jsonify({
        'sucesso': True,
        'total': len(sessoes),
        'sessoes': sessoes
    })


# ==========================================
# API - CODIGOS GERADOS
# ==========================================

@bp.route('/api/codigos')
@login_required
@admin_required
def api_listar_codigos():
    """Lista codigos gerados."""
    from .models import CodigoSistemaGerado

    ativo = request.args.get('ativo')
    tipo = request.args.get('tipo')
    limite = request.args.get('limite', 50, type=int)

    query = CodigoSistemaGerado.query

    if ativo is not None:
        query = query.filter_by(ativo=(ativo == 'true'))
    if tipo:
        query = query.filter_by(tipo_codigo=tipo)

    codigos = query.order_by(CodigoSistemaGerado.criado_em.desc()).limit(limite).all()

    return jsonify({
        'sucesso': True,
        'total': len(codigos),
        'codigos': [c.to_dict() for c in codigos]
    })


@bp.route('/api/codigos/<int:codigo_id>/toggle', methods=['POST'])
@login_required
@admin_required
def api_toggle_codigo(codigo_id: int):
    """Ativa/desativa um codigo."""
    from .models import CodigoSistemaGerado
    from .services.codigo_loader import invalidar_cache
    from app import db

    codigo = CodigoSistemaGerado.query.get_or_404(codigo_id)
    codigo.ativo = not codigo.ativo
    codigo.atualizado_por = current_user.nome
    db.session.commit()

    # Invalida cache para que a mudanca tenha efeito imediato
    invalidar_cache()

    return jsonify({
        'sucesso': True,
        'ativo': codigo.ativo,
        'mensagem': f"Codigo {'ativado' if codigo.ativo else 'desativado'}"
    })


# ==========================================
# API - CACHE DE CODIGOS (para debug/monitoramento)
# ==========================================

@bp.route('/api/codigos/cache/stats')
@login_required
@admin_required
def api_cache_stats():
    """Retorna estatisticas do cache de codigos ativos."""
    from .services.codigo_loader import estatisticas

    return jsonify({
        'sucesso': True,
        'cache': estatisticas()
    })


@bp.route('/api/codigos/cache/invalidar', methods=['POST'])
@login_required
@admin_required
def api_invalidar_cache():
    """Invalida o cache de codigos manualmente."""
    from .services.codigo_loader import invalidar_cache

    invalidar_cache()

    return jsonify({
        'sucesso': True,
        'mensagem': 'Cache invalidado com sucesso'
    })


# ==========================================
# API - CODEBASE (para debug)
# ==========================================

@bp.route('/api/codebase/models/<modulo>')
@login_required
@admin_required
def api_listar_models(modulo: str):
    """Lista models de um modulo."""
    from .services import CodebaseReader

    reader = CodebaseReader()
    resultado = reader.listar_models(modulo)

    return jsonify(resultado)


@bp.route('/api/codebase/campos/<model>')
@login_required
@admin_required
def api_listar_campos(model: str):
    """Lista campos de um model."""
    from .services import CodebaseReader

    reader = CodebaseReader()
    resultado = reader.listar_campos_model(model)

    return jsonify(resultado)


# ==========================================
# API - MODO DISCUSSAO AVANCADA
# ==========================================

# Instancia singleton do servico de discussao (para manter propostas em memoria)
_discussion_service = None


def _get_discussion_service():
    """Retorna instancia singleton do DiscussionService."""
    global _discussion_service
    if _discussion_service is None:
        from .services.discussion_service import DiscussionService
        _discussion_service = DiscussionService()
    return _discussion_service


@bp.route('/discussao')
@login_required
@admin_required
def pagina_discussao():
    """Pagina do Modo Discussao Avancada."""
    return render_template('claude_ai_lite/ia_trainer/discussao.html')


@bp.route('/discussao/<int:codigo_id>')
@login_required
@admin_required
def pagina_discussao_codigo(codigo_id: int):
    """Pagina de discussao para um codigo especifico."""
    from .models import CodigoSistemaGerado

    codigo = CodigoSistemaGerado.query.get_or_404(codigo_id)

    return render_template(
        'claude_ai_lite/ia_trainer/discussao.html',
        codigo=codigo.to_dict()
    )


@bp.route('/api/discussao/iniciar', methods=['POST'])
@login_required
@admin_required
def api_iniciar_discussao():
    """Inicia uma discussao sobre um codigo ou sessao."""
    dados = request.get_json() or {}
    codigo_id = dados.get('codigo_id')
    sessao_id = dados.get('sessao_id')

    service = _get_discussion_service()
    resultado = service.iniciar_discussao(
        codigo_id=codigo_id,
        sessao_id=sessao_id,
        contexto_adicional=dados.get('contexto')
    )

    return jsonify(resultado)


@bp.route('/api/discussao/chat', methods=['POST'])
@login_required
@admin_required
def api_discussao_chat():
    """Envia mensagem na discussao e recebe resposta do Claude."""
    dados = request.get_json()
    mensagem = dados.get('mensagem', '')
    codigo_id = dados.get('codigo_id')
    sessao_id = dados.get('sessao_id')
    modo = dados.get('modo', 'critico')  # critico, colaborativo, tecnico

    if not mensagem:
        return jsonify({'sucesso': False, 'erro': 'mensagem obrigatoria'}), 400

    service = _get_discussion_service()
    resultado = service.discutir(
        mensagem=mensagem,
        codigo_id=codigo_id,
        sessao_id=sessao_id,
        modo=modo
    )

    return jsonify(resultado)


@bp.route('/api/discussao/validar/<int:codigo_id>', methods=['POST'])
@login_required
@admin_required
def api_validar_codigo(codigo_id: int):
    """Valida um codigo contra o CLAUDE.md."""
    service = _get_discussion_service()
    resultado = service.validar_codigo_contra_claude_md(codigo_id)

    return jsonify(resultado)


@bp.route('/api/discussao/problemas')
@login_required
@admin_required
def api_listar_problemas():
    """Lista todos os codigos com problemas detectados."""
    service = _get_discussion_service()
    resultado = service.listar_codigos_com_problemas()

    return jsonify(resultado)


@bp.route('/api/discussao/propor-correcao', methods=['POST'])
@login_required
@admin_required
def api_propor_correcao():
    """
    Propoe uma correcao para um codigo.

    NAO aplica imediatamente - retorna comparativo ANTES/DEPOIS
    para aprovacao do usuario.
    """
    dados = request.get_json()
    codigo_id = dados.get('codigo_id')
    correcoes = dados.get('correcoes', {})
    motivo = dados.get('motivo', 'Correcao via Modo Discussao')

    if not codigo_id or not correcoes:
        return jsonify({'sucesso': False, 'erro': 'codigo_id e correcoes obrigatorios'}), 400

    service = _get_discussion_service()
    resultado = service.propor_correcao(
        codigo_id=codigo_id,
        correcoes=correcoes,
        motivo=motivo
    )

    return jsonify(resultado)


@bp.route('/api/discussao/aprovar-correcao', methods=['POST'])
@login_required
@admin_required
def api_aprovar_correcao():
    """
    Aprova e aplica uma correcao proposta.

    Requer proposta_id da correcao previamente proposta.
    """
    dados = request.get_json()
    proposta_id = dados.get('proposta_id')

    if not proposta_id:
        return jsonify({'sucesso': False, 'erro': 'proposta_id obrigatorio'}), 400

    service = _get_discussion_service()
    resultado = service.aplicar_correcao_aprovada(
        proposta_id=proposta_id,
        usuario=current_user.nome
    )

    return jsonify(resultado)


@bp.route('/api/discussao/rejeitar-correcao', methods=['POST'])
@login_required
@admin_required
def api_rejeitar_correcao():
    """Rejeita uma proposta de correcao."""
    dados = request.get_json()
    proposta_id = dados.get('proposta_id')

    if not proposta_id:
        return jsonify({'sucesso': False, 'erro': 'proposta_id obrigatorio'}), 400

    service = _get_discussion_service()
    resultado = service.rejeitar_correcao(proposta_id)

    return jsonify(resultado)


@bp.route('/api/discussao/propostas-pendentes')
@login_required
@admin_required
def api_propostas_pendentes():
    """Lista propostas de correcao pendentes de aprovacao."""
    service = _get_discussion_service()
    resultado = service.listar_propostas_pendentes()

    return jsonify(resultado)


@bp.route('/api/discussao/consultar-banco', methods=['POST'])
@login_required
@admin_required
def api_consultar_banco():
    """
    Consulta o banco via linguagem natural.

    SEGURANCA: Apenas SELECT, com limites.
    """
    dados = request.get_json()
    consulta = dados.get('consulta', '')

    if not consulta:
        return jsonify({'sucesso': False, 'erro': 'consulta obrigatoria'}), 400

    service = _get_discussion_service()
    resultado = service.consultar_banco(consulta)

    return jsonify(resultado)
