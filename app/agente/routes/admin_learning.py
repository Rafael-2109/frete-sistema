"""Ciclo de Aprendizado Admin — instrucao do agente via correcoes."""

import logging

from flask import request, jsonify
from flask_login import login_required, current_user

from app.agente.routes import agente_bp
from app import db
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger('sistema_fretes')


def _format_messages_for_correction(messages: list, max_chars: int = 6000) -> str:
    """
    Formata mensagens de sessao para o prompt de correcao.

    Itera de tras para frente e inclui mensagens ate atingir max_chars.
    Cada mensagem individual e truncada em 500 chars.

    Args:
        messages: Lista de mensagens da sessao
        max_chars: Limite de caracteres total

    Returns:
        Texto formatado com [USUARIO]/[AGENTE] prefixos
    """
    formatted_parts = []
    total_chars = 0

    for msg in reversed(messages):
        role = 'USUARIO' if msg.get('role') == 'user' else 'AGENTE'
        content = (msg.get('content') or '')[:500]
        part = f"[{role}]: {content}"

        if total_chars + len(part) > max_chars:
            break

        formatted_parts.insert(0, part)
        total_chars += len(part) + 1

    return '\n'.join(formatted_parts)


@agente_bp.route('/api/admin/sessions/<session_id>/messages', methods=['GET'])
@login_required
def api_admin_session_messages(session_id: str):
    """
    Endpoint admin: retorna mensagens de QUALQUER sessao (sem filtro user_id).

    GET /agente/api/admin/sessions/{session_id}/messages

    Requer perfil administrador. Usado pelo dashboard de insights para
    drill-down em sessoes de qualquer usuario.

    Response:
    {
        "success": true,
        "session_id": "abc123",
        "title": "...",
        "user_name": "...",
        "model": "...",
        "cost_usd": 0.1234,
        "status": "resolved",
        "created_at": "...",
        "messages": [...],
        "total_tokens": 15000,
        "summary": {...}
    }
    """
    if current_user.perfil != 'administrador':
        return jsonify({'success': False, 'error': 'Acesso restrito a administradores'}), 403

    try:
        from app.agente.models import AgentSession
        from app.auth.models import Usuario

        session = AgentSession.query.filter_by(session_id=session_id).first()

        if not session:
            return jsonify({
                'success': False,
                'error': 'Sessao nao encontrada'
            }), 404

        messages = session.get_messages()

        # Buscar nome do usuario
        user_name = 'N/A'
        if session.user_id:
            user = Usuario.query.get(session.user_id)
            if user:
                user_name = user.nome or f'Usuario #{session.user_id}'

        # Computar status (mesma logica do insights_service._calc_sessions)
        msg_count = session.message_count or 0
        has_tools = False
        for msg in messages:
            if msg.get('role') == 'assistant' and msg.get('tools_used'):
                has_tools = True
                break

        if msg_count >= 4 and has_tools:
            status = 'resolved'
        elif msg_count <= 3 and msg_count > 0:
            status = 'abandoned'
        elif msg_count >= 5 and not has_tools:
            status = 'no_tools'
        else:
            status = 'normal'

        response_data = {
            'success': True,
            'session_id': session_id,
            'title': session.title or '(sem titulo)',
            'user_name': user_name,
            'user_id': session.user_id,
            'model': session.model or 'N/A',
            'cost_usd': round(float(session.total_cost_usd or 0), 4),
            'status': status,
            'message_count': msg_count,
            'created_at': session.created_at.isoformat() if session.created_at else None,
            'messages': messages,
            'total_tokens': session.get_total_tokens(),
        }

        if session.summary:
            response_data['summary'] = session.summary

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao buscar mensagens admin: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/admin/generate-correction', methods=['POST'])
@login_required
def api_admin_generate_correction():
    """
    Gera correcao a partir de orientacao do admin sobre uma sessao.

    O admin revisa uma sessao no modal de insights e escreve uma orientacao.
    Sonnet recebe a conversa + orientacao e gera uma correcao na voz do agente,
    pronta para ser salva na memoria persistente.

    POST /agente/api/admin/generate-correction
    {
        "session_id": "abc123",
        "guidance": "Voce deveria ter usado a skill cotando-frete..."
    }

    Response:
    {
        "success": true,
        "correction": "Quando o usuario perguntar sobre preco de frete...",
        "suggested_path": "/memories/corrections/usar-cotando-frete-para-precos.xml",
        "session_id": "abc123",
        "model_used": "claude-sonnet-4-6"
    }
    """
    if current_user.perfil != 'administrador':
        return jsonify({'success': False, 'error': 'Acesso restrito a administradores'}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Body obrigatorio'}), 400

        session_id = data.get('session_id')
        guidance = data.get('guidance', '').strip()

        if not session_id:
            return jsonify({'success': False, 'error': 'session_id obrigatorio'}), 400
        if not guidance:
            return jsonify({'success': False, 'error': 'guidance obrigatorio'}), 400

        from app.agente.models import AgentSession

        # Busca sessao sem filtro user_id (admin pode ver qualquer sessao)
        session = AgentSession.query.filter_by(session_id=session_id).first()
        if not session:
            return jsonify({'success': False, 'error': 'Sessao nao encontrada'}), 404

        # Formatar conversa (max 6000 chars, ultimas N mensagens)
        messages = session.get_messages()
        formatted = _format_messages_for_correction(messages, max_chars=6000)

        if not formatted:
            return jsonify({'success': False, 'error': 'Sessao sem mensagens'}), 400

        # Chamar Sonnet para gerar correcao
        import anthropic
        import re as _re

        SONNET_MODEL = 'claude-sonnet-4-6'

        prompt = (
            "Voce e um agente logistico que cometeu um erro numa conversa.\n"
            "Um administrador revisou e deu esta orientacao:\n\n"
            "<orientacao>\n"
            f"{guidance}\n"
            "</orientacao>\n\n"
            "<conversa>\n"
            f"{formatted}\n"
            "</conversa>\n\n"
            "Gere uma correcao que voce salvaria na sua memoria para nao repetir o erro.\n\n"
            "Regras:\n"
            "- Primeira pessoa (\"Quando perguntarem sobre X, devo usar...\")\n"
            "- Acionavel (O QUE fazer, nao apenas o que NAO fazer)\n"
            "- Concisa (max 150 palavras)\n"
            "- Inclua contexto do erro para match semantico futuro\n\n"
            "Responda EXATAMENTE neste formato:\n"
            "<correction>\n"
            "[sua correcao]\n"
            "</correction>\n"
            "<path>/memories/corrections/[slug-descritivo].xml</path>"
        )

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text if response.content else ''

        # Parsear resposta (regex para extrair <correction> e <path>)
        correction_match = _re.search(
            r'<correction>\s*(.*?)\s*</correction>', response_text, _re.DOTALL
        )
        path_match = _re.search(
            r'<path>\s*(.*?)\s*</path>', response_text, _re.DOTALL
        )

        correction = (
            correction_match.group(1).strip()
            if correction_match
            else response_text.strip()
        )
        suggested_path = (
            path_match.group(1).strip()
            if path_match
            else f'/memories/corrections/correcao-{session_id[:8]}.xml'
        )

        # Garantir que path comeca com /memories/corrections/
        if not suggested_path.startswith('/memories/corrections/'):
            slug = suggested_path.split('/')[-1] or f'correcao-{session_id[:8]}.xml'
            suggested_path = f'/memories/corrections/{slug}'

        # Garantir extensao .xml
        if not suggested_path.endswith('.xml'):
            suggested_path += '.xml'

        logger.info(
            f"[AGENTE] Correcao gerada: session={session_id[:8]}... "
            f"path={suggested_path}"
        )

        return jsonify({
            'success': True,
            'correction': correction,
            'suggested_path': suggested_path,
            'session_id': session_id,
            'model_used': SONNET_MODEL,
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao gerar correcao: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agente_bp.route('/api/admin/save-correction', methods=['POST'])
@login_required
def api_admin_save_correction():
    """
    Salva correcao aprovada pelo admin como memoria empresa (user_id=0).

    Antes: broadcast para TODOS os usuarios (N copias identicas).
    Agora: salva 1 vez com user_id=0, escopo='empresa', visivel para todos.

    POST /agente/api/admin/save-correction
    {
        "correction": "Quando o usuario perguntar sobre preco de frete...",
        "path": "/memories/corrections/usar-cotando-frete.xml",
        "session_id": "abc123"
    }

    Response:
    {
        "success": true,
        "saved_for": "empresa (user_id=0)",
        "path": "/memories/corrections/usar-cotando-frete.xml"
    }
    """
    if current_user.perfil != 'administrador':
        return jsonify({'success': False, 'error': 'Acesso restrito a administradores'}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Body obrigatorio'}), 400

        correction = data.get('correction', '').strip()
        path = data.get('path', '').strip()
        session_id = data.get('session_id', '')

        if not correction:
            return jsonify({'success': False, 'error': 'correction obrigatorio'}), 400
        if not path:
            return jsonify({'success': False, 'error': 'path obrigatorio'}), 400
        if not path.startswith('/memories/corrections/'):
            return jsonify({
                'success': False,
                'error': 'path deve comecar com /memories/corrections/'
            }), 400

        from app.agente.models import AgentMemory
        from app.agente.tools.memory_mcp_tool import (
            _check_memory_duplicate,
            _embed_memory_best_effort,
            _sanitize_content,
        )

        # Sanitizar conteudo contra prompt injection
        correction = _sanitize_content(correction)

        # Verificar duplicata semantica (escopo empresa, user_id=0)
        dup_path = _check_memory_duplicate(0, correction, current_path=path)
        if dup_path:
            return jsonify({
                'success': False,
                'error': f'Correcao similar ja existe: {dup_path}',
            }), 409

        # Wrap em XML estruturado
        admin_name = getattr(current_user, 'nome', None) or str(current_user.id)
        content = (
            f"<admin_correction>\n"
            f"<text>{correction}</text>\n"
            f"<source>admin_instruction</source>\n"
            f"<session_id>{session_id}</session_id>\n"
            f"<admin>{admin_name}</admin>\n"
            f"<created_at>{agora_utc_naive().isoformat()}</created_at>\n"
            f"</admin_correction>"
        )

        # Salvar como memoria empresa (user_id=0) em vez de broadcast
        existing = AgentMemory.get_by_path(0, path)
        if existing:
            existing.content = content
            existing.updated_at = agora_utc_naive()
        else:
            mem = AgentMemory.create_file(0, path, content)
            mem.escopo = 'empresa'
            mem.created_by = current_user.id
            mem.importance_score = 0.9  # Correcoes admin = alta prioridade
            mem.category = 'permanent'

        db.session.commit()

        # Incrementar correction_count nas memórias recentemente injetadas de TODOS os usuários
        # (correção empresa afeta todos)
        try:
            from app.agente.tools.memory_mcp_tool import _track_correction_feedback
            # Para correções empresa, aplicar ao admin que criou (user_id do contexto)
            _track_correction_feedback(current_user.id, path, correction)
        except Exception as fb_err:
            logger.debug(f"[AGENTE] Correction tracking admin falhou (ignorado): {fb_err}")

        # Embedding (best-effort, nao bloqueia)
        try:
            _embed_memory_best_effort(0, path, content)
        except Exception:
            pass

        logger.info(
            f"[AGENTE] Correcao admin salva como empresa: path={path}, "
            f"admin={admin_name}"
        )

        return jsonify({
            'success': True,
            'saved_for': 'empresa (user_id=0)',
            'path': path,
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao salvar correcao: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
