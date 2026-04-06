"""
Routes para controle de despesas da frota propria.
Blueprint: frota_bp (/fretes/frota)
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
from sqlalchemy import func, desc
import logging
import pandas as pd

from app import db
from app.utils.auth_decorators import require_financeiro
from app.utils.file_storage import get_file_storage
from app.fretes.frota_models import FrotaVeiculo, FrotaDespesa
from app.veiculos.models import Veiculo
from app.transportadoras.models import Transportadora

logger = logging.getLogger(__name__)

frota_bp = Blueprint('frota', __name__, url_prefix='/fretes/frota')


# ═══════════════════════════════════════════════════════════════
# INDEX — Lista de veiculos + stats
# ═══════════════════════════════════════════════════════════════

@frota_bp.route('/')
@login_required
@require_financeiro()
def index():
    """Lista de veiculos da frota com estatisticas do mes."""
    veiculos = FrotaVeiculo.query.order_by(
        FrotaVeiculo.ativo.desc(), FrotaVeiculo.placa
    ).all()

    hoje = date.today()
    primeiro_dia_mes = hoje.replace(day=1)

    # Stats do mes atual
    stats_mes = db.session.query(
        func.count(FrotaDespesa.id).label('qtd'),
        func.coalesce(func.sum(FrotaDespesa.valor), 0).label('total'),
    ).filter(
        FrotaDespesa.data_despesa >= primeiro_dia_mes,
    ).first()

    total_ativos = sum(1 for v in veiculos if v.ativo)

    # Total de despesas por veiculo (para exibir na tabela)
    totais_por_veiculo = dict(
        db.session.query(
            FrotaDespesa.frota_veiculo_id,
            func.coalesce(func.sum(FrotaDespesa.valor), 0),
        ).group_by(FrotaDespesa.frota_veiculo_id).all()
    )

    # Tipos de veiculo e motoristas para os modais
    tipos_veiculo = Veiculo.query.order_by(Veiculo.nome).all()
    motoristas = Transportadora.query.filter_by(
        motorista_proprio=True, ativo=True
    ).order_by(Transportadora.razao_social).all()

    return render_template(
        'fretes/frota/index.html',
        veiculos=veiculos,
        total_ativos=total_ativos,
        despesas_mes_qtd=stats_mes.qtd,
        despesas_mes_total=stats_mes.total,
        totais_por_veiculo=totais_por_veiculo,
        tipos_veiculo=tipos_veiculo,
        motoristas=motoristas,
    )


# ═══════════════════════════════════════════════════════════════
# CRUD VEICULOS
# ═══════════════════════════════════════════════════════════════

@frota_bp.route('/veiculos/novo', methods=['POST'])
@login_required
@require_financeiro()
def novo_veiculo():
    """Criar novo veiculo da frota."""
    try:
        placa = request.form.get('placa', '').strip().upper()
        renavam = request.form.get('renavam', '').strip()

        if not placa or not renavam:
            flash('Placa e Renavam sao obrigatorios.', 'danger')
            return redirect(url_for('frota.index'))

        # Duplicidade
        if FrotaVeiculo.query.filter_by(placa=placa).first():
            flash(f'Ja existe um veiculo com a placa {placa}.', 'danger')
            return redirect(url_for('frota.index'))
        if FrotaVeiculo.query.filter_by(renavam=renavam).first():
            flash(f'Ja existe um veiculo com o Renavam {renavam}.', 'danger')
            return redirect(url_for('frota.index'))

        chassi = request.form.get('chassi', '').strip().upper() or None
        if chassi and FrotaVeiculo.query.filter_by(chassi=chassi).first():
            flash(f'Ja existe um veiculo com o chassi {chassi}.', 'danger')
            return redirect(url_for('frota.index'))

        depreciacao = _parse_decimal(request.form.get('depreciacao_mensal', '0'))

        veiculo = FrotaVeiculo(
            placa=placa,
            marca=request.form.get('marca', '').strip(),
            modelo=request.form.get('modelo', '').strip(),
            renavam=renavam,
            proprietario=request.form.get('proprietario', '').strip(),
            ano_fabricacao=int(request.form.get('ano_fabricacao', 0)),
            ano_modelo=int(request.form.get('ano_modelo', 0)),
            cor=request.form.get('cor', '').strip() or None,
            chassi=chassi,
            veiculo_tipo_id=int(request.form.get('veiculo_tipo_id')),
            transportadora_id=_parse_int_or_none(request.form.get('transportadora_id')),
            km_atual=int(request.form.get('km_atual', 0)),
            depreciacao_mensal=depreciacao,
            observacoes=request.form.get('observacoes', '').strip() or None,
            criado_por=current_user.nome,
        )
        db.session.add(veiculo)
        db.session.commit()

        flash(f'Veiculo {placa} cadastrado com sucesso!', 'success')
        logger.info(f"Veiculo criado: {placa} por {current_user.nome}")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar veiculo: {e}")
        flash(f'Erro ao cadastrar veiculo: {str(e)}', 'danger')

    return redirect(url_for('frota.index'))


@frota_bp.route('/veiculos/<int:id>/editar', methods=['POST'])
@login_required
@require_financeiro()
def editar_veiculo(id):
    """Editar veiculo existente."""
    veiculo = FrotaVeiculo.query.get_or_404(id)

    try:
        placa = request.form.get('placa', '').strip().upper()
        renavam = request.form.get('renavam', '').strip()

        # Duplicidade (excluindo o proprio registro)
        dup_placa = FrotaVeiculo.query.filter(
            FrotaVeiculo.placa == placa, FrotaVeiculo.id != id
        ).first()
        if dup_placa:
            flash(f'Ja existe outro veiculo com a placa {placa}.', 'danger')
            return redirect(url_for('frota.index'))

        dup_renavam = FrotaVeiculo.query.filter(
            FrotaVeiculo.renavam == renavam, FrotaVeiculo.id != id
        ).first()
        if dup_renavam:
            flash(f'Ja existe outro veiculo com o Renavam {renavam}.', 'danger')
            return redirect(url_for('frota.index'))

        chassi = request.form.get('chassi', '').strip().upper() or None
        if chassi:
            dup_chassi = FrotaVeiculo.query.filter(
                FrotaVeiculo.chassi == chassi, FrotaVeiculo.id != id
            ).first()
            if dup_chassi:
                flash(f'Ja existe outro veiculo com o chassi {chassi}.', 'danger')
                return redirect(url_for('frota.index'))

        veiculo.placa = placa
        veiculo.marca = request.form.get('marca', '').strip()
        veiculo.modelo = request.form.get('modelo', '').strip()
        veiculo.renavam = renavam
        veiculo.proprietario = request.form.get('proprietario', '').strip()
        veiculo.ano_fabricacao = int(request.form.get('ano_fabricacao', 0))
        veiculo.ano_modelo = int(request.form.get('ano_modelo', 0))
        veiculo.cor = request.form.get('cor', '').strip() or None
        veiculo.chassi = chassi
        veiculo.veiculo_tipo_id = int(request.form.get('veiculo_tipo_id'))
        veiculo.transportadora_id = _parse_int_or_none(request.form.get('transportadora_id'))
        veiculo.km_atual = int(request.form.get('km_atual', veiculo.km_atual))
        veiculo.depreciacao_mensal = _parse_decimal(request.form.get('depreciacao_mensal', '0'))
        veiculo.observacoes = request.form.get('observacoes', '').strip() or None

        db.session.commit()
        flash(f'Veiculo {placa} atualizado com sucesso!', 'success')
        logger.info(f"Veiculo editado: {placa} por {current_user.nome}")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao editar veiculo {id}: {e}")
        flash(f'Erro ao editar veiculo: {str(e)}', 'danger')

    return redirect(url_for('frota.index'))


@frota_bp.route('/veiculos/<int:id>/inativar', methods=['POST'])
@login_required
@require_financeiro()
def inativar_veiculo(id):
    """Toggle ativo/inativo do veiculo."""
    veiculo = FrotaVeiculo.query.get_or_404(id)
    veiculo.ativo = not veiculo.ativo
    db.session.commit()

    status = 'ativado' if veiculo.ativo else 'inativado'
    flash(f'Veiculo {veiculo.placa} {status}.', 'success')
    return redirect(url_for('frota.index'))


# ═══════════════════════════════════════════════════════════════
# DETALHE DO VEICULO + DESPESAS
# ═══════════════════════════════════════════════════════════════

@frota_bp.route('/veiculos/<int:id>')
@login_required
@require_financeiro()
def detalhe_veiculo(id):
    """Detalhe do veiculo com lista de despesas e filtros."""
    veiculo = FrotaVeiculo.query.get_or_404(id)

    # Filtros
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    categoria = request.args.get('categoria', '')
    tipo_doc = request.args.get('tipo_documento', '')

    query = FrotaDespesa.query.filter_by(frota_veiculo_id=id)

    if data_inicio:
        query = query.filter(FrotaDespesa.data_despesa >= data_inicio)
    if data_fim:
        query = query.filter(FrotaDespesa.data_despesa <= data_fim)
    if categoria:
        query = query.filter(FrotaDespesa.categoria == categoria)
    if tipo_doc:
        query = query.filter(FrotaDespesa.tipo_documento == tipo_doc)

    despesas = query.order_by(desc(FrotaDespesa.data_despesa)).all()

    # Totais por categoria (no periodo filtrado)
    totais_categoria = {}
    total_geral = Decimal('0')
    for d in despesas:
        cat = d.categoria
        val = d.valor or Decimal('0')
        totais_categoria[cat] = totais_categoria.get(cat, Decimal('0')) + val
        total_geral += val

    # Tipos de veiculo e motoristas (para modal de edicao do veiculo)
    tipos_veiculo = Veiculo.query.order_by(Veiculo.nome).all()
    motoristas = Transportadora.query.filter_by(
        motorista_proprio=True, ativo=True
    ).order_by(Transportadora.razao_social).all()

    return render_template(
        'fretes/frota/detalhe_veiculo.html',
        veiculo=veiculo,
        despesas=despesas,
        totais_categoria=totais_categoria,
        total_geral=total_geral,
        categorias=FrotaDespesa.CATEGORIAS,
        tipos_documento=FrotaDespesa.TIPOS_DOCUMENTO,
        filtro_data_inicio=data_inicio,
        filtro_data_fim=data_fim,
        filtro_categoria=categoria,
        filtro_tipo_doc=tipo_doc,
        tipos_veiculo=tipos_veiculo,
        motoristas=motoristas,
    )


# ═══════════════════════════════════════════════════════════════
# CRUD DESPESAS
# ═══════════════════════════════════════════════════════════════

@frota_bp.route('/despesas/nova', methods=['POST'])
@login_required
@require_financeiro()
def nova_despesa():
    """Criar nova despesa para um veiculo."""
    veiculo_id = int(request.form.get('frota_veiculo_id'))
    veiculo = FrotaVeiculo.query.get_or_404(veiculo_id)

    try:
        km = int(request.form.get('km_no_momento', 0))
        valor = _parse_decimal(request.form.get('valor', '0'))
        categoria = request.form.get('categoria', '')
        tipo_doc = request.form.get('tipo_documento', 'SEM_DOCUMENTO')

        if not categoria:
            flash('Categoria e obrigatoria.', 'danger')
            return redirect(url_for('frota.detalhe_veiculo', id=veiculo_id))

        if valor <= 0:
            flash('Valor deve ser maior que zero.', 'danger')
            return redirect(url_for('frota.detalhe_veiculo', id=veiculo_id))

        # Se OUTROS, descricao e obrigatoria
        descricao = request.form.get('descricao', '').strip() or None
        if categoria == 'OUTROS' and not descricao:
            flash('Para categoria OUTROS, a descricao e obrigatoria.', 'danger')
            return redirect(url_for('frota.detalhe_veiculo', id=veiculo_id))

        # Upload de arquivo (NF, recibo, cupom)
        arquivo_path = None
        arquivo = request.files.get('arquivo')
        if arquivo and arquivo.filename:
            try:
                storage = get_file_storage()
                arquivo_path = storage.save_file(
                    file=arquivo,
                    folder='frota_despesas',
                    allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'],
                )
            except Exception as upload_err:
                logger.warning(f"Erro ao fazer upload de arquivo: {upload_err}")
                flash('Despesa salva, mas houve erro ao anexar arquivo.', 'warning')

        despesa = FrotaDespesa(
            frota_veiculo_id=veiculo_id,
            data_despesa=request.form.get('data_despesa'),
            km_no_momento=km,
            categoria=categoria,
            tipo_documento=tipo_doc,
            numero_documento=request.form.get('numero_documento', '').strip() or None,
            valor=valor,
            fornecedor=request.form.get('fornecedor', '').strip() or None,
            descricao=descricao,
            observacoes=request.form.get('observacoes', '').strip() or None,
            arquivo_path=arquivo_path,
            criado_por=current_user.nome,
        )
        db.session.add(despesa)

        # Atualizar KM do veiculo
        if km > veiculo.km_atual:
            veiculo.km_atual = km

        db.session.commit()
        flash(f'Despesa de {categoria} registrada com sucesso!', 'success')
        logger.info(f"Despesa criada: {categoria} R${valor} veiculo={veiculo.placa} por {current_user.nome}")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar despesa: {e}")
        flash(f'Erro ao registrar despesa: {str(e)}', 'danger')

    return redirect(url_for('frota.detalhe_veiculo', id=veiculo_id))


@frota_bp.route('/despesas/<int:id>/editar', methods=['POST'])
@login_required
@require_financeiro()
def editar_despesa(id):
    """Editar despesa existente."""
    despesa = FrotaDespesa.query.get_or_404(id)
    veiculo = despesa.veiculo

    try:
        km = int(request.form.get('km_no_momento', despesa.km_no_momento))
        valor = _parse_decimal(request.form.get('valor', str(despesa.valor)))
        categoria = request.form.get('categoria', despesa.categoria)

        descricao = request.form.get('descricao', '').strip() or None
        if categoria == 'OUTROS' and not descricao:
            flash('Para categoria OUTROS, a descricao e obrigatoria.', 'danger')
            return redirect(url_for('frota.detalhe_veiculo', id=veiculo.id))

        despesa.data_despesa = request.form.get('data_despesa', despesa.data_despesa)
        despesa.km_no_momento = km
        despesa.categoria = categoria
        despesa.tipo_documento = request.form.get('tipo_documento', despesa.tipo_documento)
        despesa.numero_documento = request.form.get('numero_documento', '').strip() or None
        despesa.valor = valor
        despesa.fornecedor = request.form.get('fornecedor', '').strip() or None
        despesa.descricao = descricao
        despesa.observacoes = request.form.get('observacoes', '').strip() or None

        # Upload de arquivo (substituir se novo arquivo enviado)
        arquivo = request.files.get('arquivo')
        if arquivo and arquivo.filename:
            try:
                storage = get_file_storage()
                # Deletar arquivo anterior se existir
                if despesa.arquivo_path:
                    try:
                        storage.delete_file(despesa.arquivo_path)
                    except Exception:
                        pass
                despesa.arquivo_path = storage.save_file(
                    file=arquivo,
                    folder='frota_despesas',
                    allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'],
                )
            except Exception as upload_err:
                logger.warning(f"Erro ao fazer upload de arquivo: {upload_err}")

        # Recalcular KM do veiculo (pega o maximo de todas as despesas)
        _recalcular_km(veiculo)

        db.session.commit()
        flash('Despesa atualizada com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao editar despesa {id}: {e}")
        flash(f'Erro ao editar despesa: {str(e)}', 'danger')

    return redirect(url_for('frota.detalhe_veiculo', id=veiculo.id))


@frota_bp.route('/despesas/<int:id>/excluir', methods=['POST'])
@login_required
@require_financeiro()
def excluir_despesa(id):
    """Excluir despesa com recalculo de KM."""
    despesa = FrotaDespesa.query.get_or_404(id)
    veiculo = despesa.veiculo
    veiculo_id = veiculo.id

    try:
        db.session.delete(despesa)
        db.session.flush()  # Remove antes de recalcular

        # Recalcular KM
        _recalcular_km(veiculo)

        db.session.commit()
        flash('Despesa excluida com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir despesa {id}: {e}")
        flash(f'Erro ao excluir despesa: {str(e)}', 'danger')

    return redirect(url_for('frota.detalhe_veiculo', id=veiculo_id))


# ═══════════════════════════════════════════════════════════════
# EXPORT EXCEL
# ═══════════════════════════════════════════════════════════════

@frota_bp.route('/veiculos/<int:id>/exportar')
@login_required
@require_financeiro()
def exportar_despesas(id):
    """Exportar despesas do veiculo para Excel (respeita filtros ativos)."""
    veiculo = FrotaVeiculo.query.get_or_404(id)

    # Mesmos filtros da pagina de detalhe
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    categoria = request.args.get('categoria', '')
    tipo_doc = request.args.get('tipo_documento', '')

    query = FrotaDespesa.query.filter_by(frota_veiculo_id=id)
    if data_inicio:
        query = query.filter(FrotaDespesa.data_despesa >= data_inicio)
    if data_fim:
        query = query.filter(FrotaDespesa.data_despesa <= data_fim)
    if categoria:
        query = query.filter(FrotaDespesa.categoria == categoria)
    if tipo_doc:
        query = query.filter(FrotaDespesa.tipo_documento == tipo_doc)

    despesas = query.order_by(desc(FrotaDespesa.data_despesa)).all()

    # Montar dados para DataFrame
    dados = []
    for d in despesas:
        tipo_doc_label = dict(FrotaDespesa.TIPOS_DOCUMENTO).get(d.tipo_documento, d.tipo_documento)
        dados.append({
            'Data': d.data_despesa.strftime('%d/%m/%Y') if d.data_despesa else '',
            'Categoria': d.categoria,
            'Fornecedor': d.fornecedor or '',
            'KM': d.km_no_momento,
            'Tipo Documento': tipo_doc_label,
            'N. Documento': d.numero_documento or '',
            'Valor': float(d.valor or 0),
            'Descricao': d.descricao or '',
            'Observacoes': d.observacoes or '',
            'Tem Anexo': 'Sim' if d.arquivo_path else 'Nao',
        })

    if not dados:
        flash('Nenhuma despesa para exportar com os filtros selecionados.', 'warning')
        return redirect(url_for('frota.detalhe_veiculo', id=id))

    df = pd.DataFrame(dados)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Despesas')
        # Auto-ajustar largura das colunas
        worksheet = writer.sheets['Despesas']
        for col_idx, column in enumerate(worksheet.columns, 1):
            max_length = max(len(str(cell.value or '')) for cell in column)
            header_length = len(str(df.columns[col_idx - 1]))
            adjusted = min(max(max_length, header_length) + 2, 50)
            worksheet.column_dimensions[column[0].column_letter].width = adjusted
    output.seek(0)

    placa_clean = veiculo.placa.replace('-', '')
    filename = f"despesas_{placa_clean}_{date.today().strftime('%Y%m%d')}.xlsx"
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename,
    )


# ═══════════════════════════════════════════════════════════════
# ARQUIVO ANEXO (visualizar/download)
# ═══════════════════════════════════════════════════════════════

@frota_bp.route('/despesas/<int:id>/arquivo')
@login_required
@require_financeiro()
def visualizar_arquivo(id):
    """Retorna URL presigned do arquivo anexo da despesa."""
    despesa = FrotaDespesa.query.get_or_404(id)
    if not despesa.arquivo_path:
        flash('Esta despesa nao possui arquivo anexo.', 'warning')
        return redirect(url_for('frota.detalhe_veiculo', id=despesa.frota_veiculo_id))

    try:
        storage = get_file_storage()
        url = storage.get_file_url(despesa.arquivo_path)
        if url:
            return redirect(url)
    except Exception as e:
        logger.error(f"Erro ao obter URL do arquivo: {e}")

    flash('Erro ao acessar arquivo.', 'danger')
    return redirect(url_for('frota.detalhe_veiculo', id=despesa.frota_veiculo_id))


@frota_bp.route('/despesas/<int:id>/remover-arquivo', methods=['POST'])
@login_required
@require_financeiro()
def remover_arquivo(id):
    """Remove arquivo anexo de uma despesa."""
    despesa = FrotaDespesa.query.get_or_404(id)
    veiculo_id = despesa.frota_veiculo_id

    if despesa.arquivo_path:
        try:
            storage = get_file_storage()
            storage.delete_file(despesa.arquivo_path)
        except Exception as e:
            logger.warning(f"Erro ao deletar arquivo S3: {e}")

        despesa.arquivo_path = None
        db.session.commit()
        flash('Arquivo removido com sucesso.', 'success')

    return redirect(url_for('frota.detalhe_veiculo', id=veiculo_id))


# ═══════════════════════════════════════════════════════════════
# APIs JSON
# ═══════════════════════════════════════════════════════════════

@frota_bp.route('/api/motoristas')
@login_required
def api_motoristas():
    """Lista de transportadoras com motorista_proprio=True para selects."""
    motoristas = Transportadora.query.filter_by(
        motorista_proprio=True, ativo=True
    ).order_by(Transportadora.razao_social).all()

    return jsonify([
        {'id': m.id, 'razao_social': m.razao_social, 'cnpj': m.cnpj}
        for m in motoristas
    ])


@frota_bp.route('/api/veiculos')
@login_required
def api_veiculos_json():
    """Lista de veiculos ativos para selects em outros modulos."""
    veiculos = FrotaVeiculo.query.filter_by(ativo=True).order_by(FrotaVeiculo.placa).all()

    return jsonify([
        {
            'id': v.id,
            'placa': v.placa,
            'nome_display': v.nome_display,
            'km_atual': v.km_atual,
        }
        for v in veiculos
    ])


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _recalcular_km(veiculo):
    """Recalcula km_atual do veiculo baseado no MAX das despesas."""
    max_km = db.session.query(
        func.max(FrotaDespesa.km_no_momento)
    ).filter_by(frota_veiculo_id=veiculo.id).scalar()
    veiculo.km_atual = max_km or 0


def _parse_decimal(value):
    """Converte string para Decimal, tratando formato brasileiro."""
    if not value:
        return Decimal('0')
    try:
        # Aceita tanto 1.234,56 (BR) quanto 1234.56 (US)
        cleaned = value.strip().replace('.', '').replace(',', '.')
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return Decimal('0')


def _parse_int_or_none(value):
    """Converte string para int ou None."""
    if not value or value == '' or value == 'None':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
