"""Cotacao Rapida PUBLICA (tela SEM login) — blueprint isolado na raiz /cotacao.

Reusa o motor da Cotacao Rapida (CotacaoRapidaService) e o LLM, mas exige nome
do solicitante e PERSISTE cada calculo com opcoes (lead). Rate-limit por IP no
upload/calcular (LLM/custo exposto). Sem @login_required, sem guard sistema_carvia.
"""
import logging

from flask import Blueprint, render_template, request, jsonify, make_response

from app.carvia.utils.rate_limit import permitir
from app.carvia.routes.cotacao_rapida_common import (
    modelos_orm, ufs_destino_disponiveis, resolver_contexto,
)

logger = logging.getLogger(__name__)

cotacao_publica_bp = Blueprint(
    'cotacao_publica', __name__, url_prefix='/cotacao',
    template_folder='../templates/carvia',
)

LIMITE_UPLOAD = 20      # por IP / hora
LIMITE_CALCULAR = 60    # por IP / hora
LIMITE_PDF = 30         # por IP / hora
LIMITE_CEP = 120        # por IP / hora
JANELA = 3600


def _ip():
    """Retorna o IP do cliente lendo o primeiro hop de X-Forwarded-For.

    Nota: X-Forwarded-For e' um header controlado pelo cliente — sem ProxyFix
    configurado no app, o valor nao e' validado. O rate-limit por IP e' uma
    medida anti-abuso de melhor-esforco, nao uma barreira de seguranca contra
    um atacante que forje esse header.
    """
    fwd = request.headers.get('X-Forwarded-For', '')
    return (fwd.split(',')[0].strip() if fwd else request.remote_addr) or ''


@cotacao_publica_bp.route('')
@cotacao_publica_bp.route('/')
def cotacao_publica():
    from app.carvia.services.pricing.cotacao_rapida_service import CotacaoRapidaService
    return render_template(
        'carvia/cotacao_publica/form.html',
        modelos=CotacaoRapidaService().listar_modelos(),
        ufs_destino=ufs_destino_disponiveis(),
    )


@cotacao_publica_bp.route('/cidades/<uf>')
def cotacao_publica_cidades(uf):
    from app.localidades.models import Cidade
    cidades = Cidade.query.filter_by(uf=uf).order_by(Cidade.nome).all()
    return jsonify([{'nome': c.nome, 'codigo_ibge': c.codigo_ibge} for c in cidades])


@cotacao_publica_bp.route('/cep/<cep>')
def cotacao_publica_cep(cep):
    if not permitir('cep', _ip(), limite=LIMITE_CEP, janela_seg=JANELA):
        return jsonify({'ok': False, 'erro': 'Muitas requisicoes. Tente mais tarde.'}), 429
    from app.utils.cep_service import resolver_cep
    dados = resolver_cep(cep)
    if not dados:
        return jsonify({'ok': False, 'erro': 'cep_nao_encontrado'}), 404
    return jsonify({'ok': True, **dados})


@cotacao_publica_bp.route('/upload', methods=['POST'])
def cotacao_publica_upload():
    if not permitir('upload', _ip(), limite=LIMITE_UPLOAD, janela_seg=JANELA):
        return jsonify({'ok': False, 'erro': 'Muitas requisicoes. Tente mais tarde.'}), 429

    arquivo = request.files.get('arquivo')
    if not arquivo or not arquivo.filename:
        return jsonify({'ok': False, 'erro': 'Nenhum arquivo enviado.'}), 400

    MAX_BYTES = 20 * 1024 * 1024
    if (request.content_length or 0) > MAX_BYTES:
        return jsonify({'ok': False, 'erro': 'Arquivo muito grande (max 20MB).'}), 413
    file_bytes = arquivo.read()
    if len(file_bytes) > MAX_BYTES:
        return jsonify({'ok': False, 'erro': 'Arquivo muito grande (max 20MB).'}), 413

    from app.carvia.services.parsers.cotacao_rapida_llm_service import (
        extrair_motos_regiao, CotacaoRapidaLlmError,
    )
    try:
        resultado = extrair_motos_regiao(
            file_bytes, arquivo.mimetype or '', modelos_orm(), filename=arquivo.filename)
    except CotacaoRapidaLlmError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 422
    except Exception as e:  # noqa: BLE001
        logger.exception('Erro inesperado no upload da Cotacao Publica')
        return jsonify({'ok': False, 'erro': f'Falha ao ler arquivo: {e}'}), 500
    return jsonify({'ok': True, **resultado})


@cotacao_publica_bp.route('/calcular', methods=['POST'])
def cotacao_publica_calcular():
    if not permitir('calcular', _ip(), limite=LIMITE_CALCULAR, janela_seg=JANELA):
        return jsonify({'ok': False, 'erro': 'Muitas requisicoes. Tente mais tarde.'}), 429

    payload = request.get_json(silent=True) or {}
    solicitante_nome = (payload.get('solicitante_nome') or '').strip()
    if not solicitante_nome:
        return jsonify({'ok': False, 'erro': 'Informe seu nome para cotar.'}), 400

    contexto = resolver_contexto(payload)
    if contexto.get('erro'):
        return jsonify({'ok': False, 'erro': contexto['erro']}), 400

    from app import db
    from app.carvia.services.pricing.cotacao_rapida_service import CotacaoRapidaService
    svc = CotacaoRapidaService()
    resultado = svc.cotar(
        itens=contexto['itens'], uf_destino=contexto['uf_destino'],
        cidade_destino=contexto['cidade_destino'], cnpj_cliente=contexto['cnpj_cliente'],
        codigo_ibge=contexto['codigo_ibge'],
    )

    if resultado.get('opcoes'):
        try:
            svc.registrar_cotacao_publica(
                resultado, solicitante_nome=solicitante_nome,
                cnpj_cliente=contexto['cnpj_cliente'], codigo_ibge=contexto['codigo_ibge'],
                ip=_ip(), user_agent=request.headers.get('User-Agent'))
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
            logger.exception('Falha ao persistir cotacao publica (cotacao devolvida mesmo assim)')

    from app.utils.json_helpers import sanitize_for_json
    return jsonify(sanitize_for_json(resultado))


@cotacao_publica_bp.route('/pdf', methods=['POST'])
def cotacao_publica_pdf():
    if not permitir('pdf', _ip(), limite=LIMITE_PDF, janela_seg=JANELA):
        return jsonify({'ok': False, 'erro': 'Muitas requisicoes. Tente mais tarde.'}), 429
    payload = request.get_json(silent=True) or {}
    contexto = resolver_contexto(payload)
    if contexto.get('erro'):
        return jsonify({'ok': False, 'erro': contexto['erro']}), 400

    from app.carvia.services.pricing.cotacao_rapida_service import CotacaoRapidaService
    resultado = CotacaoRapidaService().cotar(
        itens=contexto['itens'], uf_destino=contexto['uf_destino'],
        cidade_destino=contexto['cidade_destino'], cnpj_cliente=contexto['cnpj_cliente'],
        codigo_ibge=contexto['codigo_ibge'],
    )
    if not resultado.get('opcoes'):
        return jsonify({'ok': False, 'erro': 'Nada a cotar para gerar o PDF.'}), 400

    try:
        from app.utils.timezone import agora_brasil_naive
        cliente_nome = (payload.get('cliente_nome') or payload.get('solicitante_nome') or '').strip() or None
        html = render_template(
            'carvia/cotacao_rapida/imprimir_cotacao.html',
            resultado=resultado, destino=resultado['regiao'],
            cliente_nome=cliente_nome, emitido_em=agora_brasil_naive())
        from weasyprint import HTML
        pdf_bytes = HTML(string=html, base_url=request.host_url).write_pdf()
    except Exception as e:  # noqa: BLE001
        logger.exception('Falha ao gerar PDF da Cotacao Publica')
        return jsonify({'ok': False, 'erro': f'Falha ao gerar PDF: {e}'}), 500

    resp = make_response(pdf_bytes)
    resp.headers['Content-Type'] = 'application/pdf'
    resp.headers['Content-Disposition'] = 'attachment; filename=cotacao_carvia.pdf'
    return resp
