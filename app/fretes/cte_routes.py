"""
Rotas para Gerenciamento de CTes (Conhecimentos de Transporte)
===============================================================

Rotas para listar, sincronizar e visualizar CTes importados do Odoo

AUTOR: Sistema de Fretes
DATA: 13/11/2025
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, desc, func
import logging
from io import BytesIO

from app import db
from app.fretes.models import ConhecimentoTransporte, Frete
from app.odoo.services.cte_service import CteService
from app.utils.auth_decorators import require_financeiro
from app.utils.file_storage import get_file_storage

logger = logging.getLogger(__name__)

cte_bp = Blueprint('cte', __name__, url_prefix='/fretes/ctes')


@cte_bp.route('/')
@login_required
@require_financeiro()
def listar_ctes():
    """Lista todos os CTes importados do Odoo"""

    # Parâmetros de filtro
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Filtros
    filtro_status = request.args.get('status', '')
    filtro_transportadora = request.args.get('transportadora', '')
    filtro_data_inicio = request.args.get('data_inicio', '')
    filtro_data_fim = request.args.get('data_fim', '')
    filtro_vinculado = request.args.get('vinculado', '')

    # Query base - Filtrar CTes com valor >= R$ 1,00
    query = ConhecimentoTransporte.query.filter(
        ConhecimentoTransporte.ativo == True,
        ConhecimentoTransporte.valor_total >= 1.00
    )

    # Aplicar filtros
    if filtro_status:
        query = query.filter_by(odoo_status_codigo=filtro_status)

    if filtro_transportadora:
        query = query.filter(
            or_(
                ConhecimentoTransporte.cnpj_emitente.contains(filtro_transportadora),
                ConhecimentoTransporte.nome_emitente.contains(filtro_transportadora)
            )
        )

    if filtro_data_inicio:
        try:
            data_inicio = datetime.strptime(filtro_data_inicio, '%Y-%m-%d').date()
            query = query.filter(ConhecimentoTransporte.data_emissao >= data_inicio)
        except ValueError:
            pass

    if filtro_data_fim:
        try:
            data_fim = datetime.strptime(filtro_data_fim, '%Y-%m-%d').date()
            query = query.filter(ConhecimentoTransporte.data_emissao <= data_fim)
        except ValueError:
            pass

    if filtro_vinculado == 'sim':
        query = query.filter(ConhecimentoTransporte.frete_id.isnot(None))
    elif filtro_vinculado == 'nao':
        query = query.filter(ConhecimentoTransporte.frete_id.is_(None))

    # Ordenar por data de emissão (mais recentes primeiro)
    query = query.order_by(desc(ConhecimentoTransporte.data_emissao))

    # Paginar
    ctes_paginado = query.paginate(page=page, per_page=per_page, error_out=False)

    # Estatísticas
    total_ctes = ConhecimentoTransporte.query.filter_by(ativo=True).count()
    ctes_nao_vinculados = ConhecimentoTransporte.query.filter_by(ativo=True, frete_id=None).count()
    ctes_vinculados = ConhecimentoTransporte.query.filter(
        ConhecimentoTransporte.ativo == True,
        ConhecimentoTransporte.frete_id.isnot(None)
    ).count()

    # Valor total de CTes não vinculados
    valor_total_nao_vinculados = db.session.query(
        func.sum(ConhecimentoTransporte.valor_total)
    ).filter(
        ConhecimentoTransporte.ativo == True,
        ConhecimentoTransporte.frete_id.is_(None)
    ).scalar() or 0

    return render_template(
        'fretes/ctes/index.html',
        ctes=ctes_paginado.items,
        paginacao=ctes_paginado,
        total_ctes=total_ctes,
        ctes_nao_vinculados=ctes_nao_vinculados,
        ctes_vinculados=ctes_vinculados,
        valor_total_nao_vinculados=valor_total_nao_vinculados,
        filtro_status=filtro_status,
        filtro_transportadora=filtro_transportadora,
        filtro_data_inicio=filtro_data_inicio,
        filtro_data_fim=filtro_data_fim,
        filtro_vinculado=filtro_vinculado
    )


@cte_bp.route('/sincronizar', methods=['POST'])
@login_required
@require_financeiro()
def sincronizar_ctes():
    """Sincroniza CTes do Odoo"""

    try:
        # Parâmetros
        dias_retroativos = request.form.get('dias_retroativos', 30, type=int)
        limite = request.form.get('limite', None, type=int)

        logger.info(f"Iniciando sincronização de CTes - Dias: {dias_retroativos}, Limite: {limite}")

        # Executar sincronização
        service = CteService()
        resultado = service.importar_ctes(
            dias_retroativos=dias_retroativos,
            limite=limite
        )

        if resultado['sucesso']:
            flash(
                f"✅ Sincronização concluída! "
                f"Processados: {resultado['ctes_processados']}, "
                f"Novos: {resultado['ctes_novos']}, "
                f"Atualizados: {resultado['ctes_atualizados']}",
                'success'
            )
        else:
            flash(
                f"⚠️ Sincronização concluída com erros. "
                f"Processados: {resultado['ctes_processados']}, "
                f"Erros: {len(resultado['erros'])}",
                'warning'
            )

        # Se houver erros, mostrar os primeiros 3
        if resultado['erros']:
            for erro in resultado['erros'][:3]:
                flash(f"❌ {erro}", 'danger')

            if len(resultado['erros']) > 3:
                flash(f"... e mais {len(resultado['erros']) - 3} erros", 'warning')

    except Exception as e:
        logger.error(f"Erro ao sincronizar CTes: {e}")
        flash(f"❌ Erro ao sincronizar CTes: {str(e)}", 'danger')

    return redirect(url_for('cte.listar_ctes'))


@cte_bp.route('/<int:cte_id>')
@login_required
@require_financeiro()
def detalhar_cte(cte_id):
    """Mostra detalhes de um CTe específico"""

    cte = ConhecimentoTransporte.query.get_or_404(cte_id)

    return render_template('fretes/ctes/detalhe.html', cte=cte)


@cte_bp.route('/<int:cte_id>/pdf')
@login_required
@require_financeiro()
def visualizar_pdf(cte_id):
    """Visualiza o PDF do CTe"""

    cte = ConhecimentoTransporte.query.get_or_404(cte_id)

    if not cte.cte_pdf_path:
        flash('PDF não disponível para este CTe', 'warning')
        return redirect(url_for('cte.detalhar_cte', cte_id=cte_id))

    try:
        file_storage = get_file_storage()
        pdf_url = file_storage.get_file_url(cte.cte_pdf_path)

        if not pdf_url:
            flash('Arquivo PDF não encontrado no storage', 'warning')
            return redirect(url_for('cte.detalhar_cte', cte_id=cte_id))

        # Redireciona para a URL do arquivo (S3 assinada ou estática local)
        return redirect(pdf_url)

    except Exception as e:
        logger.error(f"Erro ao buscar PDF do CTe {cte_id}: {e}")
        flash(f"Erro ao buscar PDF: {str(e)}", 'danger')
        return redirect(url_for('cte.detalhar_cte', cte_id=cte_id))


@cte_bp.route('/<int:cte_id>/xml')
@login_required
@require_financeiro()
def visualizar_xml(cte_id):
    """Baixa o XML do CTe"""

    cte = ConhecimentoTransporte.query.get_or_404(cte_id)

    if not cte.cte_xml_path:
        flash('XML não disponível para este CTe', 'warning')
        return redirect(url_for('cte.detalhar_cte', cte_id=cte_id))

    try:
        file_storage = get_file_storage()
        xml_url = file_storage.get_file_url(cte.cte_xml_path)

        if not xml_url:
            flash('Arquivo XML não encontrado no storage', 'warning')
            return redirect(url_for('cte.detalhar_cte', cte_id=cte_id))

        # Redireciona para a URL do arquivo (S3 assinada ou estática local)
        return redirect(xml_url)

    except Exception as e:
        logger.error(f"Erro ao buscar XML do CTe {cte_id}: {e}")
        flash(f"Erro ao buscar XML: {str(e)}", 'danger')
        return redirect(url_for('cte.detalhar_cte', cte_id=cte_id))


@cte_bp.route('/<int:cte_id>/vincular-frete', methods=['POST'])
@login_required
@require_financeiro()
def vincular_frete(cte_id):
    """Vincula um CTe com um Frete"""

    cte = ConhecimentoTransporte.query.get_or_404(cte_id)
    frete_id = request.form.get('frete_id', type=int)

    if not frete_id:
        flash('ID do frete não informado', 'warning')
        return redirect(url_for('cte.detalhar_cte', cte_id=cte_id))

    try:
        service = CteService()
        sucesso = service.vincular_cte_com_frete(
            cte_id=cte_id,
            frete_id=frete_id,
            manual=True,
            usuario=current_user.username if current_user else 'Sistema'
        )

        if sucesso:
            flash(f'✅ CTe {cte.numero_cte} vinculado ao frete {frete_id} com sucesso!', 'success')
        else:
            flash('❌ Erro ao vincular CTe com frete', 'danger')

    except Exception as e:
        logger.error(f"Erro ao vincular CTe {cte_id} com frete {frete_id}: {e}")
        flash(f'❌ Erro ao vincular: {str(e)}', 'danger')

    return redirect(url_for('cte.detalhar_cte', cte_id=cte_id))


@cte_bp.route('/<int:cte_id>/desvincular-frete', methods=['POST'])
@login_required
@require_financeiro()
def desvincular_frete(cte_id):
    """Desvincula um CTe de um Frete"""

    cte = ConhecimentoTransporte.query.get_or_404(cte_id)

    if not cte.frete_id:
        flash('CTe não está vinculado a nenhum frete', 'warning')
        return redirect(url_for('cte.detalhar_cte', cte_id=cte_id))

    try:
        frete_id_anterior = cte.frete_id
        cte.frete_id = None
        cte.vinculado_manualmente = False
        cte.vinculado_em = None
        cte.vinculado_por = None
        cte.atualizado_em = datetime.now()
        cte.atualizado_por = current_user.username if current_user else 'Sistema'

        db.session.commit()

        flash(f'✅ CTe {cte.numero_cte} desvinculado do frete {frete_id_anterior}', 'success')

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao desvincular CTe {cte_id}: {e}")
        flash(f'❌ Erro ao desvincular: {str(e)}', 'danger')

    return redirect(url_for('cte.detalhar_cte', cte_id=cte_id))


@cte_bp.route('/api/buscar-fretes')
@login_required
@require_financeiro()
def buscar_fretes_api():
    """API para buscar fretes disponíveis para vincular com CTe"""

    query = request.args.get('q', '').strip()

    if len(query) < 2:
        return jsonify([])

    # Buscar fretes por número de CTe, cliente ou transportadora
    fretes = Frete.query.filter(
        or_(
            Frete.numero_cte.contains(query),
            Frete.nome_cliente.contains(query),
            Frete.cnpj_cliente.contains(query)
        )
    ).limit(20).all()

    resultados = []
    for frete in fretes:
        resultados.append({
            'id': frete.id,
            'numero_cte': frete.numero_cte,
            'cliente': frete.nome_cliente,
            'cnpj': frete.cnpj_cliente,
            'valor_cte': float(frete.valor_cte) if frete.valor_cte else 0,
            'transportadora': frete.transportadora.nome if frete.transportadora else 'N/A'
        })

    return jsonify(resultados)
