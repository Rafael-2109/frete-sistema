"""Rotas da Cotacao Rapida CarVia.

Tela leve para cotar frete de MOTO por destino (cidade/UF ou CEP), com:
- preenchimento manual (modelo + qtd) OU upload de PDF/imagem lido por LLM Haiku;
- cotacao por modelo (preco por categoria) com todas as tabelas detalhadas;
- historico das ultimas 5 cotacoes de moto por tabela;
- emissao de PDF em papel timbrado (weasyprint).

Nada e persistido — a cotacao e efemera. Padrao do modulo: @login_required +
guard inline `sistema_carvia`, lazy imports (R2).
"""

import logging

from flask import (
    render_template, request, jsonify, make_response, redirect, url_for, flash,
)
from flask_login import login_required, current_user

from app.carvia.routes.cotacao_rapida_common import (
    modelos_orm as _modelos_orm,
    ufs_destino_disponiveis as _ufs_destino_disponiveis,
    resolver_contexto as _resolver_contexto,
)

logger = logging.getLogger(__name__)


def _sem_acesso():
    flash('Acesso negado. Voce nao tem permissao para o sistema CarVia.', 'danger')
    return redirect(url_for('main.dashboard'))


def register_cotacao_rapida_routes(bp):

    @bp.route('/cotacao-rapida')  # type: ignore
    @login_required
    def cotacao_rapida():  # type: ignore
        """Tela da Cotacao Rapida."""
        if not getattr(current_user, 'sistema_carvia', False):
            return _sem_acesso()

        from app.carvia.services.pricing.cotacao_rapida_service import CotacaoRapidaService
        modelos = CotacaoRapidaService().listar_modelos()
        # UFs com tabela CarVia (origem SP) — para o select de destino.
        ufs = _ufs_destino_disponiveis()
        return render_template(
            'carvia/cotacao_rapida/form.html',
            modelos=modelos,
            ufs_destino=ufs,
        )

    @bp.route('/cotacao-rapida/cep/<cep>')  # type: ignore
    @login_required
    def cotacao_rapida_cep(cep):  # type: ignore
        """Resolve CEP -> {cidade, uf, codigo_ibge} (ViaCEP)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'ok': False, 'erro': 'sem_acesso'}), 403

        from app.utils.cep_service import resolver_cep
        dados = resolver_cep(cep)
        if not dados:
            return jsonify({'ok': False, 'erro': 'cep_nao_encontrado'}), 404
        return jsonify({'ok': True, **dados})

    @bp.route('/cotacao-rapida/upload', methods=['POST'])  # type: ignore
    @login_required
    def cotacao_rapida_upload():  # type: ignore
        """Le PDF/imagem via LLM Haiku e devolve motos + regiao."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'ok': False, 'erro': 'sem_acesso'}), 403

        arquivo = request.files.get('arquivo')
        if not arquivo or not arquivo.filename:
            return jsonify({'ok': False, 'erro': 'Nenhum arquivo enviado.'}), 400

        # Guard de tamanho ANTES de ler tudo na RAM (base64 ~+33%) e gastar 2
        # chamadas LLM fadadas a rejeicao (limite Anthropic ~32MB PDF / ~5MB img).
        MAX_BYTES = 20 * 1024 * 1024
        if (request.content_length or 0) > MAX_BYTES:
            return jsonify({'ok': False, 'erro': 'Arquivo muito grande (max 20MB).'}), 413
        file_bytes = arquivo.read()
        if len(file_bytes) > MAX_BYTES:
            return jsonify({'ok': False, 'erro': 'Arquivo muito grande (max 20MB).'}), 413

        from app.carvia.services.parsers.cotacao_rapida_llm_service import (
            extrair_motos_regiao, CotacaoRapidaLlmError,
        )
        modelos = _modelos_orm()
        try:
            resultado = extrair_motos_regiao(
                file_bytes,
                arquivo.mimetype or '',
                modelos,
                filename=arquivo.filename,
            )
        except CotacaoRapidaLlmError as e:
            return jsonify({'ok': False, 'erro': str(e)}), 422
        except Exception as e:  # noqa: BLE001
            logger.exception('Erro inesperado no upload da Cotacao Rapida')
            return jsonify({'ok': False, 'erro': f'Falha ao ler arquivo: {e}'}), 500

        return jsonify({'ok': True, **resultado})

    @bp.route('/cotacao-rapida/calcular', methods=['POST'])  # type: ignore
    @login_required
    def cotacao_rapida_calcular():  # type: ignore
        """Calcula a cotacao (JSON) e o historico por tabela."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'ok': False, 'erro': 'sem_acesso'}), 403

        payload = request.get_json(silent=True) or {}
        contexto = _resolver_contexto(payload)
        if contexto.get('erro'):
            return jsonify({'ok': False, 'erro': contexto['erro']}), 400

        from app.carvia.services.pricing.cotacao_rapida_service import CotacaoRapidaService
        resultado = CotacaoRapidaService().cotar(
            itens=contexto['itens'],
            uf_destino=contexto['uf_destino'],
            cidade_destino=contexto['cidade_destino'],
            cnpj_cliente=contexto['cnpj_cliente'],
            codigo_ibge=contexto['codigo_ibge'],
        )
        from app.utils.json_helpers import sanitize_for_json
        return jsonify(sanitize_for_json(resultado))

    @bp.route('/cotacao-rapida/pdf', methods=['POST'])  # type: ignore
    @login_required
    def cotacao_rapida_pdf():  # type: ignore
        """Re-cota a partir dos inputs e gera o PDF em papel timbrado."""
        if not getattr(current_user, 'sistema_carvia', False):
            return _sem_acesso()

        payload = request.get_json(silent=True) or {}
        contexto = _resolver_contexto(payload)
        if contexto.get('erro'):
            return jsonify({'ok': False, 'erro': contexto['erro']}), 400

        from app.carvia.services.pricing.cotacao_rapida_service import CotacaoRapidaService
        resultado = CotacaoRapidaService().cotar(
            itens=contexto['itens'],
            uf_destino=contexto['uf_destino'],
            cidade_destino=contexto['cidade_destino'],
            cnpj_cliente=contexto['cnpj_cliente'],
            codigo_ibge=contexto['codigo_ibge'],
        )
        if not resultado.get('opcoes'):
            return jsonify({'ok': False, 'erro': 'Nada a cotar para gerar o PDF.'}), 400

        try:
            from app.utils.timezone import agora_brasil_naive
            # Template de impressao auto-contido (imprimir_*): CSS inline por design
            # (PDF nao usa o design system do browser). base_url resolve o logo.
            html = render_template(
                'carvia/cotacao_rapida/imprimir_cotacao.html',
                resultado=resultado,
                destino=resultado['regiao'],
                cliente_nome=(payload.get('cliente_nome') or '').strip() or None,
                emitido_em=agora_brasil_naive(),
            )

            from weasyprint import HTML  # lazy import (custo de boot)
            pdf_bytes = HTML(string=html, base_url=request.host_url).write_pdf()
        except Exception as e:  # noqa: BLE001
            logger.exception('Falha ao gerar PDF da Cotacao Rapida')
            return jsonify({'ok': False, 'erro': f'Falha ao gerar PDF: {e}'}), 500

        resp = make_response(pdf_bytes)
        resp.headers['Content-Type'] = 'application/pdf'
        resp.headers['Content-Disposition'] = (
            'attachment; filename=cotacao_carvia.pdf'
        )
        return resp

