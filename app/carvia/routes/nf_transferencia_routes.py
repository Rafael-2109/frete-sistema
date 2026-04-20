"""
Rotas de NF Triangular (vinculo NF Transferencia -> NF Venda)

Endpoints:
  GET    /carvia/nfs/<venda_id>/transferencia/candidatas
         Lista NFs transf ja importadas candidatas (raiz CNPJ + match de CNPJ)
  POST   /carvia/nfs/<venda_id>/transferencia/upload
         Upload XML -> parse (nao persiste) -> retorna preview
  POST   /carvia/nfs/<venda_id>/transferencia/importar
         Persiste CarviaNf a partir do preview upload
  POST   /carvia/nfs/<venda_id>/transferencia/preview
         Dado nf_transf_id, retorna comparativo peso + vendas candidatas 1-N
  POST   /carvia/nfs/<venda_id>/transferencia/confirmar
         Cria vinculos atomicamente
  DELETE /carvia/nfs/<venda_id>/transferencia
         Remove vinculo
  GET    /carvia/nfs/<transf_id>/transferencia/vendas
         Lista NFs venda vinculadas a uma transferencia
"""

import logging

from flask import jsonify, request
from flask_login import login_required, current_user

from app.carvia.models import CarviaNf
from app.carvia.services.documentos.nf_transferencia_service import (
    CarviaNfTransferenciaService,
)

logger = logging.getLogger(__name__)

_EXTENSOES_PERMITIDAS = {'.xml'}
_MAX_TAMANHO_BYTES = 50 * 1024 * 1024  # 50MB


def _autorizado():
    return bool(getattr(current_user, 'sistema_carvia', False))


def _nf_to_dict(nf: CarviaNf) -> dict:
    """Serializa CarviaNf para JSON (campos minimos para UI)."""
    return {
        'id': nf.id,
        'numero_nf': nf.numero_nf,
        'serie_nf': nf.serie_nf,
        'chave_acesso_nf': nf.chave_acesso_nf,
        'cnpj_emitente': nf.cnpj_emitente,
        'nome_emitente': nf.nome_emitente,
        'cnpj_destinatario': nf.cnpj_destinatario,
        'nome_destinatario': nf.nome_destinatario,
        'uf_emitente': nf.uf_emitente,
        'uf_destinatario': nf.uf_destinatario,
        'cidade_emitente': nf.cidade_emitente,
        'cidade_destinatario': nf.cidade_destinatario,
        'data_emissao': nf.data_emissao.isoformat() if nf.data_emissao else None,
        'peso_bruto': float(nf.peso_bruto) if nf.peso_bruto is not None else None,
        'peso_liquido': float(nf.peso_liquido) if nf.peso_liquido is not None else None,
        'valor_total': float(nf.valor_total) if nf.valor_total is not None else None,
        'status': nf.status,
    }


def register_nf_transferencia_routes(bp):

    # ------------------------------------------------------------------ #
    #  1) Listar transferencias candidatas (ja importadas)
    # ------------------------------------------------------------------ #
    @bp.route('/nfs/<int:venda_id>/transferencia/candidatas', methods=['GET'])
    @login_required
    def listar_transferencias_candidatas(venda_id):
        if not _autorizado():
            return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403

        svc = CarviaNfTransferenciaService
        nf_venda = CarviaNf.query.get(venda_id)
        if not nf_venda:
            return jsonify({'ok': False, 'erro': 'NF venda nao encontrada'}), 404

        candidatas = svc.listar_transferencias_candidatas_existentes(venda_id)
        vinculo_atual = svc.get_vinculo_por_venda(venda_id)
        transf_atual = svc.get_transferencia_de(venda_id)

        return jsonify({
            'ok': True,
            'nf_venda': _nf_to_dict(nf_venda),
            'transferencia_atual': (
                _nf_to_dict(transf_atual) if transf_atual else None
            ),
            'vinculo_atual_retroativo': (
                bool(vinculo_atual.vinculado_retroativamente)
                if vinculo_atual else False
            ),
            'candidatas': [_nf_to_dict(n) for n in candidatas],
        })

    # ------------------------------------------------------------------ #
    #  2) Upload XML -> parse (nao persiste)
    # ------------------------------------------------------------------ #
    @bp.route('/nfs/<int:venda_id>/transferencia/upload', methods=['POST'])
    @login_required
    def upload_xml_transferencia(venda_id):
        if not _autorizado():
            return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403

        if not CarviaNf.query.get(venda_id):
            return jsonify({'ok': False, 'erro': 'NF venda nao encontrada'}), 404

        arquivo = request.files.get('arquivo')
        if not arquivo or arquivo.filename == '':
            return jsonify({'ok': False, 'erro': 'Arquivo nao enviado'}), 400

        nome = arquivo.filename or ''
        ext = ('.' + nome.rsplit('.', 1)[-1].lower()) if '.' in nome else ''
        if ext not in _EXTENSOES_PERMITIDAS:
            return jsonify({
                'ok': False,
                'erro': f'Extensao nao permitida: {ext or "(sem extensao)"}',
            }), 400

        conteudo = arquivo.read()
        if len(conteudo) > _MAX_TAMANHO_BYTES:
            return jsonify({
                'ok': False,
                'erro': 'Arquivo excede 50MB',
            }), 400

        preview = CarviaNfTransferenciaService.parsear_xml_transferencia(
            conteudo, arquivo_nome=nome,
        )
        if not preview.get('ok'):
            return jsonify(preview), 400

        # Cache do conteudo XML em sessao? Para simplicidade, o frontend
        # chama /importar logo apos o upload com os dados do preview.
        return jsonify(preview), 200

    # ------------------------------------------------------------------ #
    #  3) Importar (persistir) a partir do preview
    # ------------------------------------------------------------------ #
    @bp.route('/nfs/<int:venda_id>/transferencia/importar', methods=['POST'])
    @login_required
    def importar_nf_transferencia(venda_id):
        if not _autorizado():
            return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403

        if not CarviaNf.query.get(venda_id):
            return jsonify({'ok': False, 'erro': 'NF venda nao encontrada'}), 404

        payload = request.get_json(silent=True) or {}
        info = payload.get('info') or {}
        if not info.get('chave_acesso_nf') and not info.get('numero_nf'):
            return jsonify({
                'ok': False,
                'erro': 'Preview invalido: falta chave_acesso_nf ou numero_nf',
            }), 400

        # Valida candidatura antes de persistir
        svc = CarviaNfTransferenciaService
        raiz_e = svc._raiz_cnpj(info.get('cnpj_emitente'))
        raiz_d = svc._raiz_cnpj(info.get('cnpj_destinatario'))
        if not raiz_e or raiz_e != raiz_d:
            return jsonify({
                'ok': False,
                'erro': 'NF nao e candidata a transferencia '
                        '(CNPJ emit e dest devem ter mesma raiz)',
            }), 400

        criado_por = getattr(current_user, 'email', None) or 'sistema'
        try:
            nf = svc.upsert_nf_transferencia_a_partir_do_preview(
                info, criado_por=criado_por,
            )
            from app import db
            db.session.commit()
        except Exception as e:
            from app import db
            db.session.rollback()
            logger.exception(f'Erro ao importar NF transf: {e}')
            return jsonify({'ok': False, 'erro': f'Erro ao persistir: {e}'}), 500

        return jsonify({'ok': True, 'nf_transferencia': _nf_to_dict(nf)}), 200

    # ------------------------------------------------------------------ #
    #  4) Preview vinculo (comparativo peso + 1-N candidatas)
    # ------------------------------------------------------------------ #
    @bp.route('/nfs/<int:venda_id>/transferencia/preview', methods=['POST'])
    @login_required
    def preview_vinculo(venda_id):
        if not _autorizado():
            return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403

        payload = request.get_json(silent=True) or {}
        nf_transf_id = payload.get('nf_transf_id')
        if not nf_transf_id:
            return jsonify({'ok': False, 'erro': 'nf_transf_id obrigatorio'}), 400

        svc = CarviaNfTransferenciaService

        nf_venda = CarviaNf.query.get(venda_id)
        nf_transf = CarviaNf.query.get(nf_transf_id)
        if not nf_venda or not nf_transf:
            return jsonify({'ok': False, 'erro': 'NF nao encontrada'}), 404

        if not svc.eh_candidata_transferencia(nf_transf):
            return jsonify({
                'ok': False,
                'erro': 'NF transferencia nao e candidata (raiz CNPJ)',
            }), 400

        # Candidatas 1-N (inclui a venda alvo)
        candidatas = svc.listar_candidatas_venda(
            nf_transf_id, incluir_venda_alvo_id=venda_id,
        )

        # Selecao inicial = apenas a venda alvo
        selecionados_ids = payload.get('nf_venda_ids') or [venda_id]
        selecionados_ids = [int(x) for x in selecionados_ids]

        peso = svc.comparar_pesos(nf_transf_id, selecionados_ids)

        # Retroatividade por venda
        retroativos = {}
        for vid in selecionados_ids:
            ctx = svc.detectar_contexto_retroativo(vid)
            if ctx.get('tem_retroativo'):
                retroativos[vid] = ctx

        return jsonify({
            'ok': True,
            'nf_transferencia': _nf_to_dict(nf_transf),
            'nf_venda_alvo': _nf_to_dict(nf_venda),
            'candidatas_1_n': [_nf_to_dict(n) for n in candidatas],
            'selecionados_ids': selecionados_ids,
            'peso': peso,
            'retroativos': retroativos,
        })

    # ------------------------------------------------------------------ #
    #  5) Confirmar vinculo (cria atomicamente)
    # ------------------------------------------------------------------ #
    @bp.route('/nfs/<int:venda_id>/transferencia/confirmar', methods=['POST'])
    @login_required
    def confirmar_vinculo(venda_id):
        if not _autorizado():
            return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403

        payload = request.get_json(silent=True) or {}
        nf_transf_id = payload.get('nf_transf_id')
        nf_venda_ids = payload.get('nf_venda_ids') or [venda_id]
        confirma_retroativo = bool(payload.get('confirma_retroativo', False))

        if not nf_transf_id:
            return jsonify({'ok': False, 'erro': 'nf_transf_id obrigatorio'}), 400

        # Garantir que a venda alvo esta na lista
        nf_venda_ids = [int(x) for x in nf_venda_ids]
        if venda_id not in nf_venda_ids:
            nf_venda_ids.append(venda_id)

        criado_por = getattr(current_user, 'email', None) or 'sistema'
        ok, msg, vinculos = CarviaNfTransferenciaService.criar_vinculos(
            nf_transf_id=int(nf_transf_id),
            nf_venda_ids=nf_venda_ids,
            criado_por=criado_por,
            confirma_retroativo=confirma_retroativo,
        )
        if not ok:
            return jsonify({
                'ok': False,
                'erro': msg,
                'detalhes': [
                    v if isinstance(v, dict) else {'id': getattr(v, 'id', None)}
                    for v in vinculos
                ] if vinculos else [],
            }), 400

        return jsonify({
            'ok': True,
            'mensagem': msg,
            'vinculos_criados': len(vinculos),
        }), 200

    # ------------------------------------------------------------------ #
    #  6) Remover vinculo
    # ------------------------------------------------------------------ #
    @bp.route('/nfs/<int:venda_id>/transferencia', methods=['DELETE'])
    @login_required
    def desvincular_transferencia(venda_id):
        if not _autorizado():
            return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403

        removido_por = getattr(current_user, 'email', None) or 'sistema'
        ok, msg = CarviaNfTransferenciaService.remover_vinculo(
            venda_id, removido_por=removido_por,
        )
        status = 200 if ok else 400
        return jsonify({'ok': ok, 'mensagem': msg}), status

    # ------------------------------------------------------------------ #
    #  7) Listar vendas vinculadas a uma transferencia (para detalhe)
    # ------------------------------------------------------------------ #
    @bp.route('/nfs/<int:transf_id>/transferencia/vendas', methods=['GET'])
    @login_required
    def listar_vendas_vinculadas(transf_id):
        if not _autorizado():
            return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403

        nf_transf = CarviaNf.query.get(transf_id)
        if not nf_transf:
            return jsonify({'ok': False, 'erro': 'NF nao encontrada'}), 404

        vendas = CarviaNfTransferenciaService.get_vendas_de(transf_id)
        return jsonify({
            'ok': True,
            'nf_transferencia': _nf_to_dict(nf_transf),
            'vendas': [_nf_to_dict(v) for v in vendas],
        })
