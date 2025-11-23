"""
Rotas Flask para Claude AI Lite.
Inclui página de conversa e endpoints de API.
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user

logger = logging.getLogger(__name__)

# Blueprint
claude_lite_bp = Blueprint('claude_lite', __name__, url_prefix='/claude-lite')


def _exempt_csrf():
    """Isenta rotas de API do CSRF."""
    try:
        from app import csrf
        csrf.exempt(claude_lite_bp)
    except Exception:
        pass


_exempt_csrf()


# ============================================
# PÁGINA DE CONVERSA
# ============================================

@claude_lite_bp.route('/', methods=['GET'])
@login_required
def pagina_conversa():
    """Página dedicada para conversar com o Claude."""
    return render_template('claude_ai_lite/conversa.html')


# ============================================
# API ENDPOINTS
# ============================================

@claude_lite_bp.route('/api/query', methods=['POST'])
@login_required
def api_query():
    """
    Endpoint principal - processa consulta em linguagem natural.

    POST /claude-lite/api/query
    {
        "query": "Pedido VCD2509030 tem separacao?",
        "usar_claude": true  // opcional, default true
    }
    """
    try:
        data = request.get_json()

        if not data or not data.get('query'):
            return jsonify({'success': False, 'error': 'Campo "query" obrigatorio'}), 400

        consulta = data['query'].strip()
        usar_claude = data.get('usar_claude', True)

        usuario = getattr(current_user, 'nome', 'Desconhecido')
        usuario_id = getattr(current_user, 'id', None)
        logger.info(f"[Claude Lite] {usuario} (ID:{usuario_id}): '{consulta[:100]}'")

        # Usa o core para processar (passa usuario e usuario_id para memória)
        from .core import processar_consulta
        resposta = processar_consulta(
            consulta,
            usar_claude_resposta=usar_claude,
            usuario=usuario,
            usuario_id=usuario_id
        )

        return jsonify({
            'success': True,
            'response': resposta,
            'source': 'claude_ai_lite',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"[Claude Lite] Erro: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@claude_lite_bp.route('/api/query/direct', methods=['POST'])
@login_required
def api_query_direct():
    """
    Consulta direta sem NLP - para integracoes programaticas.

    POST /claude-lite/api/query/direct
    {
        "valor": "VCD2509030",
        "campo": "num_pedido",
        "dominio": "carteira"  // opcional, default "carteira"
    }
    """
    try:
        data = request.get_json()

        if not data or not data.get('valor'):
            return jsonify({'success': False, 'error': 'Campo "valor" obrigatorio'}), 400

        valor = data['valor'].strip()
        campo = data.get('campo', 'num_pedido')
        dominio = data.get('dominio', 'carteira')

        from .domains import get_loader
        loader_class = get_loader(dominio)

        if not loader_class:
            return jsonify({'success': False, 'error': f'Dominio invalido: {dominio}'}), 400

        loader = loader_class()

        if not loader.validar_campo(campo):
            return jsonify({
                'success': False,
                'error': f'Campo invalido. Aceitos: {loader.CAMPOS_BUSCA}'
            }), 400

        resultado = loader.buscar(valor, campo)

        return jsonify({
            **resultado,
            'source': 'claude_ai_lite',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"[Claude Lite] Erro direto: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@claude_lite_bp.route('/api/action/criar-separacao', methods=['POST'])
@login_required
def api_criar_separacao():
    """
    Cria separacao baseada em opcao escolhida.

    POST /claude-lite/api/action/criar-separacao
    {
        "num_pedido": "VCD2509030",
        "opcao": "A"  // A, B ou C
    }
    """
    try:
        data = request.get_json()

        if not data or not data.get('num_pedido') or not data.get('opcao'):
            return jsonify({
                'success': False,
                'error': 'Campos "num_pedido" e "opcao" obrigatorios'
            }), 400

        num_pedido = data['num_pedido'].strip()
        opcao = data['opcao'].strip().upper()

        if opcao not in ['A', 'B', 'C']:
            return jsonify({
                'success': False,
                'error': 'Opcao deve ser A, B ou C'
            }), 400

        usuario = getattr(current_user, 'nome', 'Claude AI')
        logger.info(f"[Claude Lite] {usuario}: Criando separacao {num_pedido} opcao {opcao}")

        from .domains.carteira.services import CriarSeparacaoService
        resultado = CriarSeparacaoService.criar_separacao_opcao(
            num_pedido=num_pedido,
            opcao_codigo=opcao,
            usuario=usuario
        )

        return jsonify({
            **resultado,
            'source': 'claude_ai_lite',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"[Claude Lite] Erro ao criar separacao: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@claude_lite_bp.route('/health', methods=['GET'])
def health_check():
    """Health check do servico."""
    try:
        from .claude_client import get_claude_client
        from .domains import listar_dominios

        client = get_claude_client()

        return jsonify({
            'status': 'healthy',
            'api_configured': bool(client.api_key),
            'model': client.model,
            'dominios_disponiveis': listar_dominios(),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
