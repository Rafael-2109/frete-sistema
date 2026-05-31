"""Routes do Inventário Cíclico — contagem parcial por quant + plano de ajustes.

Fluxo: criar+gerar base (extrai quants Odoo) → download Excel → você preenche →
preview (sem gravar) → confirmar (grava) → relatório/plano (Excel).
Aplicação no Odoo é externa (skills gestor-estoque-odoo).
"""
from io import BytesIO

from flask import render_template, request, jsonify, send_file
from flask_login import login_required, current_user

from app import db
from app.inventario import inventario_bp
from app.inventario.models import ContagemInventario, ContagemInventarioItem
from app.inventario.services.contagem_service import ContagemService
from app.inventario.services.contagem_export_service import ContagemExportService
from app.utils.auth_decorators import require_admin
from app.utils.json_helpers import sanitize_for_json

_XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def _user_nome():
    try:
        return getattr(current_user, 'nome', None) or getattr(current_user, 'email', 'unknown')
    except Exception:
        return 'unknown'


def _split_csv(valor):
    if not valor:
        return None
    bruto = str(valor).replace(';', ',').replace('\n', ',')
    itens = [x.strip() for x in bruto.split(',') if x.strip()]
    return itens or None


@inventario_bp.route('/contagens', endpoint='listar_contagens')
@login_required
@require_admin
def listar_contagens():
    contagens = (ContagemInventario.query
                 .order_by(ContagemInventario.criado_em.desc()).all())
    return render_template('inventario/contagens.html', contagens=contagens)


@inventario_bp.route('/contagens/nova', methods=['POST'], endpoint='criar_contagem')
@login_required
@require_admin
def criar_contagem():
    empresa = (request.form.get('empresa') or '').strip().upper()
    if empresa not in ('FB', 'CD', 'LF'):
        return jsonify({'erro': 'empresa deve ser FB, CD ou LF'}), 400
    filtro_locais = _split_csv(request.form.get('filtro_locais'))
    filtro_codigos = _split_csv(request.form.get('filtro_codigos'))
    incluir_indisponivel = (request.form.get('incluir_indisponivel')
                            in ('1', 'true', 'on', 'True'))
    descricao = (request.form.get('descricao') or '').strip() or None
    try:
        contagem = ContagemService.criar_e_gerar_base(
            empresa, filtro_locais=filtro_locais, filtro_codigos=filtro_codigos,
            incluir_indisponivel=incluir_indisponivel, descricao=descricao,
            criado_por=_user_nome(),
        )
        db.session.commit()
        return jsonify(sanitize_for_json({
            'id': contagem.id, 'codigo': contagem.codigo,
            'tot_itens': contagem.tot_itens,
        })), 201
    except ValueError as exc:
        db.session.rollback()
        return jsonify({'erro': str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({'erro': f'Falha ao gerar base: {exc}'}), 500


@inventario_bp.route('/contagens/<int:contagem_id>', endpoint='detalhe_contagem')
@login_required
@require_admin
def detalhe_contagem(contagem_id):
    contagem = ContagemInventario.query.get_or_404(contagem_id)
    return render_template('inventario/contagem_detalhe.html', contagem=contagem)


@inventario_bp.route('/contagens/<int:contagem_id>/base.xlsx', endpoint='download_base')
@login_required
@require_admin
def download_base(contagem_id):
    contagem = ContagemInventario.query.get_or_404(contagem_id)
    data = ContagemExportService.excel_base(contagem)
    return send_file(BytesIO(data), mimetype=_XLSX_MIME, as_attachment=True,
                     download_name=f'{contagem.codigo}_base.xlsx')


@inventario_bp.route('/contagens/<int:contagem_id>/relatorio.xlsx',
                     endpoint='download_relatorio')
@login_required
@require_admin
def download_relatorio(contagem_id):
    contagem = ContagemInventario.query.get_or_404(contagem_id)
    data = ContagemExportService.excel_relatorio(contagem)
    return send_file(BytesIO(data), mimetype=_XLSX_MIME, as_attachment=True,
                     download_name=f'{contagem.codigo}_plano.xlsx')


@inventario_bp.route('/contagens/<int:contagem_id>/preview', methods=['POST'],
                     endpoint='preview_contagem')
@login_required
@require_admin
def preview_contagem(contagem_id):
    if 'arquivo' not in request.files:
        return jsonify({'erro': 'arquivo ausente'}), 400
    f = request.files['arquivo']
    if not (f.filename or '').lower().endswith('.xlsx'):
        return jsonify({'erro': 'envie um arquivo .xlsx'}), 400
    try:
        resultado = ContagemService.preview_reupload(contagem_id, f.stream)
        return jsonify(sanitize_for_json(resultado))
    except ValueError as exc:
        return jsonify({'erro': str(exc)}), 400
    except Exception as exc:
        return jsonify({'erro': str(exc)}), 500


@inventario_bp.route('/contagens/<int:contagem_id>/confirmar', methods=['POST'],
                     endpoint='confirmar_contagem')
@login_required
@require_admin
def confirmar_contagem(contagem_id):
    if 'arquivo' not in request.files:
        return jsonify({'erro': 'arquivo ausente'}), 400
    f = request.files['arquivo']
    if not (f.filename or '').lower().endswith('.xlsx'):
        return jsonify({'erro': 'envie um arquivo .xlsx'}), 400
    try:
        resultado = ContagemService.confirmar_reupload(contagem_id, f.stream)
        db.session.commit()
        return jsonify(sanitize_for_json(resultado))
    except ValueError as exc:
        db.session.rollback()
        return jsonify({'erro': str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({'erro': str(exc)}), 500


@inventario_bp.route('/contagens/<int:contagem_id>/itens', endpoint='itens_contagem')
@login_required
@require_admin
def itens_contagem(contagem_id):
    ContagemInventario.query.get_or_404(contagem_id)
    so_ajuste = request.args.get('so_ajuste') in ('1', 'true', 'True')
    itens = (ContagemInventarioItem.query
             .filter_by(contagem_id=contagem_id)
             .order_by(ContagemInventarioItem.location_name,
                       ContagemInventarioItem.cod_produto,
                       ContagemInventarioItem.lote).all())
    linhas = []
    for it in itens:
        if so_ajuste and (it.ajuste in (None, 0) or it.classe in (None, 'SEM_AJUSTE')):
            continue
        linhas.append({
            'location_name': it.location_name, 'local_tipo': it.local_tipo,
            'cod_produto': it.cod_produto, 'nome_produto': it.nome_produto,
            'lote': it.lote, 'company_id': it.company_id, 'is_migracao': it.is_migracao,
            'qtd_esperada': it.qtd_esperada, 'reservado_esperado': it.reservado_esperado,
            'contagem': it.contagem, 'ajuste': it.ajuste, 'classe': it.classe,
        })
    return jsonify(sanitize_for_json({'linhas': linhas, 'total': len(linhas)}))


@inventario_bp.route('/contagens/<int:contagem_id>/excluir', methods=['POST'],
                     endpoint='excluir_contagem')
@login_required
@require_admin
def excluir_contagem(contagem_id):
    contagem = ContagemInventario.query.get_or_404(contagem_id)
    db.session.delete(contagem)
    db.session.commit()
    return jsonify({'ok': True})
