"""Endpoints do wizard de recebimento físico Motos Assaí.

Rotas:
  GET  /recibos/<id>/conferir       — renderiza wizard A→B→C→D
  POST /recebimento/validar-chassi  — valida chassi contra recibo (sem persistir)
  POST /recebimento/registrar       — registra conferência de 1 chassi
  POST /recebimento/finalizar/<id>  — finaliza recibo (gera MOTO_FALTANDO em batch)
  POST /recebimento/foto-upload     — upload de foto para S3

Todos os POSTs esperam e retornam JSON. CSRF via X-CSRFToken header.
"""

import io

from flask import (
    render_template, request, url_for, jsonify, current_app,
)
from flask_login import login_required, current_user

from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services import (
    get_recibo, validar_chassi_contra_recibo, registrar_conferencia,
    finalizar_recebimento, listar_modelos,
    RecebimentoConflictError, RecebimentoValidationError,
)
from app.motos_assai.models import AssaiReciboItem
from app.utils.file_storage import FileStorage


# ---------------------------------------------------------------------------
# GET: Wizard
# ---------------------------------------------------------------------------

@motos_assai_bp.route('/recibos/<int:recibo_id>/conferir')
@login_required
@require_motos_assai
def recebimento_wizard(recibo_id):
    """Renderiza o wizard de recebimento físico (A→B→C→D)."""
    recibo = get_recibo(recibo_id)
    total = AssaiReciboItem.query.filter_by(recibo_id=recibo_id).count()
    conferidos = AssaiReciboItem.query.filter_by(
        recibo_id=recibo_id, conferido=True,
    ).count()
    return render_template(
        'motos_assai/recebimento/wizard.html',
        recibo=recibo,
        total_chassis=total,
        conferidos=conferidos,
        pendentes=total - conferidos,
        modelos=listar_modelos(somente_ativos=True),
    )


# ---------------------------------------------------------------------------
# POST: Validar chassi (sem persistir)
# ---------------------------------------------------------------------------

@motos_assai_bp.route('/recebimento/validar-chassi', methods=['POST'])
@login_required
@require_motos_assai
def recebimento_validar_chassi():
    """Valida chassi contra o recibo e retorna contexto (modelo/cor esperados).

    Body JSON: {recibo_id: int, chassi: str}
    Response: {ok, item_id, modelo_id_esperado, cor_esperada,
               modelo_texto_recibo, ja_conferido, na_nf, regex_check, mensagem}
    """
    data = request.get_json(silent=True) or {}
    recibo_id = data.get('recibo_id')
    chassi = data.get('chassi', '')
    if not recibo_id or not chassi:
        return jsonify({'ok': False, 'erro': 'recibo_id e chassi obrigatórios'}), 400
    resultado = validar_chassi_contra_recibo(int(recibo_id), chassi)
    return jsonify(resultado)


# ---------------------------------------------------------------------------
# POST: Registrar conferência de 1 chassi
# ---------------------------------------------------------------------------

@motos_assai_bp.route('/recebimento/registrar', methods=['POST'])
@login_required
@require_motos_assai
def recebimento_registrar():
    """Registra conferência de 1 chassi (cria/atualiza AssaiMoto + evento ESTOQUE).

    Body JSON: {recibo_id, chassi, modelo_id, cor?, qr_code_lido?, foto_s3_key?, avaria_fisica?}
    Response 200: {ok: true, item_id, tipo_divergencia, total, conferidos}
    Response 409: {ok: false, erro, retry: true}  — race condition
    Response 400: {ok: false, erro}               — validação
    """
    data = request.get_json(silent=True) or {}
    try:
        item = registrar_conferencia(
            recibo_id=int(data['recibo_id']),
            chassi=data['chassi'],
            modelo_conferido_id=int(data['modelo_id']),
            cor_conferida=data.get('cor'),
            qr_code_lido=bool(data.get('qr_code_lido')),
            foto_s3_key=data.get('foto_s3_key'),
            operador_id=current_user.id,
            avaria_fisica=bool(data.get('avaria_fisica')),
        )
    except RecebimentoConflictError as e:
        return jsonify({'ok': False, 'erro': str(e), 'retry': True}), 409
    except RecebimentoValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    except Exception:
        current_app.logger.exception('Erro ao registrar conferência')
        return jsonify({'ok': False, 'erro': 'Erro interno ao registrar conferência'}), 500

    total = AssaiReciboItem.query.filter_by(recibo_id=item.recibo_id).count()
    conferidos = AssaiReciboItem.query.filter_by(
        recibo_id=item.recibo_id, conferido=True,
    ).count()
    return jsonify({
        'ok': True,
        'item_id': item.id,
        'tipo_divergencia': item.tipo_divergencia,
        'total': total,
        'conferidos': conferidos,
    })


# ---------------------------------------------------------------------------
# POST: Finalizar recibo
# ---------------------------------------------------------------------------

@motos_assai_bp.route('/recebimento/finalizar/<int:recibo_id>', methods=['POST'])
@login_required
@require_motos_assai
def recebimento_finalizar(recibo_id):
    """Finaliza conferência do recibo. Chassis não conferidos → MOTO_FALTANDO.

    Body JSON: {confirmar_faltantes: bool}
    Response 200: {ok: true, status, redirect}
    Response 400: {ok: false, erro}  — há faltantes e confirmar_faltantes=false
    """
    data = request.get_json(silent=True) or {}
    try:
        recibo = finalizar_recebimento(
            recibo_id=recibo_id,
            operador_id=current_user.id,
            confirmar_faltantes=bool(data.get('confirmar_faltantes')),
        )
    except RecebimentoValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400

    return jsonify({
        'ok': True,
        'status': recibo.status,
        'redirect': url_for('motos_assai.recibos_detalhe', recibo_id=recibo.id),
    })


# ---------------------------------------------------------------------------
# POST: Upload de foto
# ---------------------------------------------------------------------------

@motos_assai_bp.route('/recebimento/foto-upload', methods=['POST'])
@login_required
@require_motos_assai
def recebimento_foto_upload():
    """Faz upload de foto da moto para S3.

    Form-data: foto (file), recibo_id (str), chassi (str)
    Response 200: {ok: true, s3_key}
    Response 400: {ok: false, erro}
    """
    f = request.files.get('foto')
    recibo_id = request.form.get('recibo_id')
    chassi = (request.form.get('chassi') or '').strip().upper()
    if not f or not recibo_id or not chassi:
        return jsonify({'ok': False, 'erro': 'foto, recibo_id e chassi são obrigatórios'}), 400

    buf = io.BytesIO(f.read())
    buf.name = f.filename
    try:
        s3_key = FileStorage().save_file(
            buf,
            folder=f'motos_assai/recebimento/{recibo_id}',
            filename=f'{chassi}_{f.filename}',
            allowed_extensions=['jpg', 'jpeg', 'png', 'webp'],
        )
    except ValueError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    except Exception:
        current_app.logger.exception('Erro ao fazer upload de foto')
        return jsonify({'ok': False, 'erro': 'Erro ao salvar foto'}), 500

    return jsonify({'ok': True, 's3_key': s3_key})
