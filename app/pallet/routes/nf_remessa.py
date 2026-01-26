"""
Routes de NF de Remessa de Pallet v2

CRUD e consultas de NFs de remessa:
- GET /nf-remessa - Listagem com filtros
- GET /nf-remessa/<id> - Detalhe da NF
- POST /nf-remessa/<id>/cancelar - Cancelar NF
- GET /api/nf-remessa/buscar - API de busca

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
"""
import logging
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user

from app import db
from app.pallet.models import PalletNFRemessa, PalletCredito, PalletNFSolucao
from app.pallet.services import NFService

logger = logging.getLogger(__name__)

# Sub-blueprint para NF Remessa
nf_remessa_bp = Blueprint('nf_remessa', __name__, url_prefix='/nf-remessa')


@nf_remessa_bp.route('/')
@login_required
def listar():
    """
    Lista NFs de remessa com filtros.

    Query params:
    - status: ATIVA, RESOLVIDA, CANCELADA
    - empresa: CD, FB, SC
    - tipo_destinatario: TRANSPORTADORA, CLIENTE
    - cnpj: CNPJ do destinatário
    - data_de: Data inicial (YYYY-MM-DD)
    - data_ate: Data final (YYYY-MM-DD)
    - page: Página (default: 1)
    """
    # Parâmetros de filtro
    status = request.args.get('status', '')
    empresa = request.args.get('empresa', '')
    tipo_destinatario = request.args.get('tipo_destinatario', '')
    cnpj = request.args.get('cnpj', '').strip()
    data_de = request.args.get('data_de', '')
    data_ate = request.args.get('data_ate', '')
    page = request.args.get('page', 1, type=int)

    # Query base
    query = PalletNFRemessa.query.filter(PalletNFRemessa.ativo == True)

    # Aplicar filtros
    if status:
        query = query.filter(PalletNFRemessa.status == status)

    if empresa:
        query = query.filter(PalletNFRemessa.empresa == empresa)

    if tipo_destinatario:
        query = query.filter(PalletNFRemessa.tipo_destinatario == tipo_destinatario)

    if cnpj:
        # Limpar CNPJ e buscar
        cnpj_limpo = cnpj.replace('.', '').replace('-', '').replace('/', '')
        query = query.filter(
            db.or_(
                PalletNFRemessa.cnpj_destinatario.ilike(f'%{cnpj_limpo}%'),
                PalletNFRemessa.nome_destinatario.ilike(f'%{cnpj}%')
            )
        )

    if data_de:
        try:
            dt_de = datetime.strptime(data_de, '%Y-%m-%d')
            query = query.filter(PalletNFRemessa.data_emissao >= dt_de)
        except ValueError:
            pass

    if data_ate:
        try:
            dt_ate = datetime.strptime(data_ate, '%Y-%m-%d')
            query = query.filter(PalletNFRemessa.data_emissao <= dt_ate)
        except ValueError:
            pass

    # Ordenar por data de emissão (mais recentes primeiro)
    query = query.order_by(PalletNFRemessa.data_emissao.desc())

    # Paginar
    nfs = query.paginate(page=page, per_page=50, error_out=False)

    # Estatísticas rápidas
    stats = {
        'total': nfs.total,
        'ativas': PalletNFRemessa.query.filter(
            PalletNFRemessa.ativo == True,
            PalletNFRemessa.status == 'ATIVA'
        ).count(),
        'resolvidas': PalletNFRemessa.query.filter(
            PalletNFRemessa.ativo == True,
            PalletNFRemessa.status == 'RESOLVIDA'
        ).count(),
        'canceladas': PalletNFRemessa.query.filter(
            PalletNFRemessa.ativo == True,
            PalletNFRemessa.status == 'CANCELADA'
        ).count()
    }

    return render_template(
        'pallet/v2/nf_remessa/listagem.html',
        nfs=nfs,
        stats=stats,
        # Filtros atuais (para manter no form)
        filtro_status=status,
        filtro_empresa=empresa,
        filtro_tipo_destinatario=tipo_destinatario,
        filtro_cnpj=cnpj,
        filtro_data_de=data_de,
        filtro_data_ate=data_ate
    )


@nf_remessa_bp.route('/<int:nf_id>')
@login_required
def detalhe(nf_id):
    """
    Exibe detalhe de uma NF de remessa.

    Mostra:
    - Dados da NF
    - Status dos dois domínios (Crédito e NF)
    - Histórico de documentos e soluções
    - Ações contextuais
    """
    nf = PalletNFRemessa.query.get_or_404(nf_id)

    # Buscar créditos associados a esta NF
    creditos = PalletCredito.query.filter(
        PalletCredito.nf_remessa_id == nf_id,
        PalletCredito.ativo == True
    ).all()

    # Buscar soluções de NF associadas
    solucoes_nf = PalletNFSolucao.query.filter(
        PalletNFSolucao.nf_remessa_id == nf_id,
        PalletNFSolucao.ativo == True
    ).order_by(PalletNFSolucao.criado_em.desc()).all()

    # Obter resumo completo via service
    resumo = NFService.obter_resumo_nf(nf_id)

    return render_template(
        'pallet/v2/nf_remessa/detalhe.html',
        nf=nf,
        creditos=creditos,
        solucoes_nf=solucoes_nf,
        resumo=resumo
    )


@nf_remessa_bp.route('/<int:nf_id>/cancelar', methods=['POST'])
@login_required
def cancelar(nf_id):
    """
    Cancela uma NF de remessa.

    REGRA 005: Nunca deleta, apenas marca cancelada=True.

    Form params:
    - motivo: Motivo do cancelamento (obrigatório)
    """
    nf = PalletNFRemessa.query.get_or_404(nf_id)

    # Validar se pode cancelar
    if nf.status == 'CANCELADA':
        flash('Esta NF já está cancelada!', 'warning')
        return redirect(url_for('pallet_v2.nf_remessa.detalhe', nf_id=nf_id))

    if nf.status == 'RESOLVIDA':
        flash('Não é possível cancelar uma NF já resolvida!', 'danger')
        return redirect(url_for('pallet_v2.nf_remessa.detalhe', nf_id=nf_id))

    motivo = request.form.get('motivo', '').strip()
    if not motivo:
        flash('Motivo do cancelamento é obrigatório!', 'danger')
        return redirect(url_for('pallet_v2.nf_remessa.detalhe', nf_id=nf_id))

    try:
        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        NFService.cancelar_nf(nf_id, motivo=motivo, usuario=usuario)
        flash(f'NF {nf.numero_nf} cancelada com sucesso!', 'success')
    except Exception as e:
        logger.exception(f"Erro ao cancelar NF #{nf_id}")
        flash(f'Erro ao cancelar NF: {str(e)}', 'danger')

    return redirect(url_for('pallet_v2.nf_remessa.detalhe', nf_id=nf_id))


# =============================================================================
# APIs
# =============================================================================

@nf_remessa_bp.route('/api/buscar')
@login_required
def api_buscar():
    """
    API para buscar NFs de remessa.

    Query params:
    - q: Termo de busca (número NF, CNPJ ou nome)
    - status: Filtrar por status
    - limit: Limite de resultados (default: 20)
    """
    termo = request.args.get('q', '').strip()
    status = request.args.get('status', '')
    limit = request.args.get('limit', 20, type=int)

    query = PalletNFRemessa.query.filter(PalletNFRemessa.ativo == True)

    if termo:
        # Buscar por número NF, CNPJ ou nome
        termo_limpo = termo.replace('.', '').replace('-', '').replace('/', '')
        query = query.filter(
            db.or_(
                PalletNFRemessa.numero_nf.ilike(f'%{termo}%'),
                PalletNFRemessa.chave_nfe.ilike(f'%{termo}%'),
                PalletNFRemessa.cnpj_destinatario.ilike(f'%{termo_limpo}%'),
                PalletNFRemessa.nome_destinatario.ilike(f'%{termo}%')
            )
        )

    if status:
        query = query.filter(PalletNFRemessa.status == status)

    nfs = query.order_by(PalletNFRemessa.data_emissao.desc()).limit(limit).all()

    return jsonify([{
        'id': nf.id,
        'numero_nf': nf.numero_nf,
        'serie': nf.serie,
        'data_emissao': nf.data_emissao.strftime('%d/%m/%Y') if nf.data_emissao else None,
        'empresa': nf.empresa,
        'tipo_destinatario': nf.tipo_destinatario,
        'cnpj_destinatario': nf.cnpj_destinatario,
        'nome_destinatario': nf.nome_destinatario,
        'quantidade': nf.quantidade,
        'status': nf.status,
        'valor_total': float(nf.valor_total) if nf.valor_total else None
    } for nf in nfs])


@nf_remessa_bp.route('/api/<int:nf_id>')
@login_required
def api_detalhe(nf_id):
    """
    API para obter detalhes de uma NF de remessa.
    """
    nf = NFService.obter_nf_por_id(nf_id)
    if not nf:
        return jsonify({'error': 'NF não encontrada'}), 404

    resumo = NFService.obter_resumo_nf(nf_id)

    return jsonify({
        'nf': {
            'id': nf.id,
            'numero_nf': nf.numero_nf,
            'serie': nf.serie,
            'chave_nfe': nf.chave_nfe,
            'data_emissao': nf.data_emissao.isoformat() if nf.data_emissao else None,
            'empresa': nf.empresa,
            'tipo_destinatario': nf.tipo_destinatario,
            'cnpj_destinatario': nf.cnpj_destinatario,
            'nome_destinatario': nf.nome_destinatario,
            'quantidade': nf.quantidade,
            'valor_unitario': float(nf.valor_unitario) if nf.valor_unitario else None,
            'valor_total': float(nf.valor_total) if nf.valor_total else None,
            'status': nf.status,
            'cancelada': nf.cancelada,
            'cancelada_em': nf.cancelada_em.isoformat() if nf.cancelada_em else None,
            'motivo_cancelamento': nf.motivo_cancelamento
        },
        'resumo': resumo
    })


@nf_remessa_bp.route('/api/por-numero')
@login_required
def api_por_numero():
    """
    API para buscar NF pelo número exato.

    Query params:
    - numero: Número da NF (obrigatório)
    - serie: Série da NF (opcional)
    """
    numero = request.args.get('numero', '').strip()
    serie = request.args.get('serie', '').strip() or None

    if not numero:
        return jsonify({'error': 'Número da NF é obrigatório'}), 400

    nf = NFService.obter_nf_por_numero(numero, serie)

    if not nf:
        return jsonify({'error': 'NF não encontrada'}), 404

    return jsonify({
        'id': nf.id,
        'numero_nf': nf.numero_nf,
        'serie': nf.serie,
        'chave_nfe': nf.chave_nfe,
        'data_emissao': nf.data_emissao.strftime('%d/%m/%Y') if nf.data_emissao else None,
        'empresa': nf.empresa,
        'tipo_destinatario': nf.tipo_destinatario,
        'cnpj_destinatario': nf.cnpj_destinatario,
        'nome_destinatario': nf.nome_destinatario,
        'quantidade': nf.quantidade,
        'status': nf.status
    })


@nf_remessa_bp.route('/api/pendentes-vinculacao')
@login_required
def api_pendentes_vinculacao():
    """
    API para listar NFs pendentes de vinculação (status ATIVA).

    Usado pelo Domínio B para mostrar NFs aguardando devolução/retorno.

    Query params:
    - cnpj: Filtrar por CNPJ do destinatário
    - limit: Limite de resultados (default: 50)
    """
    cnpj = request.args.get('cnpj', '').strip()
    limit = request.args.get('limit', 50, type=int)

    nfs = NFService.listar_nfs_pendentes_vinculacao()

    # Filtrar por CNPJ se informado
    if cnpj:
        cnpj_limpo = cnpj.replace('.', '').replace('-', '').replace('/', '')
        nfs = [nf for nf in nfs if cnpj_limpo in (nf.cnpj_destinatario or '')]

    # Limitar resultados
    nfs = nfs[:limit]

    return jsonify([{
        'id': nf.id,
        'numero_nf': nf.numero_nf,
        'data_emissao': nf.data_emissao.strftime('%d/%m/%Y') if nf.data_emissao else None,
        'tipo_destinatario': nf.tipo_destinatario,
        'cnpj_destinatario': nf.cnpj_destinatario,
        'nome_destinatario': nf.nome_destinatario,
        'quantidade': nf.quantidade,
        'saldo_pendente': nf.quantidade - (nf.quantidade_resolvida or 0)
    } for nf in nfs])
