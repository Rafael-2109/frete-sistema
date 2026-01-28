"""
Routes de Controle de Pallets v2 - Domínio A

Gerencia créditos, documentos e soluções de pallets:
- GET /controle/vales - Listagem de documentos (canhotos e vales)
- POST /controle/documento - Registrar documento
- GET /controle/solucoes - Listagem de créditos pendentes
- POST /controle/baixa - Registrar baixa
- POST /controle/venda - Registrar venda (N:1)
- POST /controle/recebimento - Registrar recebimento
- POST /controle/substituicao - Registrar substituição

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
"""
import logging
from datetime import date, datetime

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.pallet.models import (
    PalletCredito, PalletDocumento, PalletSolucao
)
from app.pallet.services import CreditoService, SolucaoPalletService
from app.utils.valores_brasileiros import converter_valor_brasileiro

logger = logging.getLogger(__name__)

# Sub-blueprint para Controle de Pallets (Domínio A)
controle_pallets_bp = Blueprint('controle_pallets', __name__, url_prefix='/controle')


# =============================================================================
# LISTAGENS
# =============================================================================

@controle_pallets_bp.route('/vales')
@login_required
def listar_vales():
    """
    Lista documentos (canhotos e vales pallet).

    Query params:
    - tipo: CANHOTO, VALE_PALLET
    - status: PENDENTE (não recebido), RECEBIDO
    - cnpj: CNPJ do responsável
    - page: Página (default: 1)
    """
    tipo = request.args.get('tipo', '')
    status = request.args.get('status', '')
    cnpj = request.args.get('cnpj', '').strip()
    page = request.args.get('page', 1, type=int)

    query = PalletDocumento.query.filter(PalletDocumento.ativo == True)

    # Filtrar por tipo
    if tipo:
        query = query.filter(PalletDocumento.tipo == tipo)

    # Filtrar por status
    if status == 'PENDENTE':
        query = query.filter(PalletDocumento.recebido == False)
    elif status == 'RECEBIDO':
        query = query.filter(PalletDocumento.recebido == True)

    # Filtrar por CNPJ
    if cnpj:
        cnpj_limpo = cnpj.replace('.', '').replace('-', '').replace('/', '')
        query = query.filter(
            db.or_(
                PalletDocumento.cnpj_emissor.ilike(f'%{cnpj_limpo}%'),
                PalletDocumento.nome_emissor.ilike(f'%{cnpj}%')
            )
        )

    # Ordenar por data de validade (mais urgentes primeiro para pendentes)
    if status == 'PENDENTE':
        query = query.order_by(PalletDocumento.data_validade.asc())
    else:
        query = query.order_by(PalletDocumento.criado_em.desc())

    documentos = query.paginate(page=page, per_page=50, error_out=False)

    # Estatísticas
    stats = {
        'total': PalletDocumento.query.filter(PalletDocumento.ativo == True).count(),
        'canhotos_pendentes': PalletDocumento.query.filter(
            PalletDocumento.ativo == True,
            PalletDocumento.tipo == 'CANHOTO',
            PalletDocumento.recebido == False
        ).count(),
        'vales_pendentes': PalletDocumento.query.filter(
            PalletDocumento.ativo == True,
            PalletDocumento.tipo == 'VALE_PALLET',
            PalletDocumento.recebido == False
        ).count(),
        'recebidos': PalletDocumento.query.filter(
            PalletDocumento.ativo == True,
            PalletDocumento.recebido == True
        ).count()
    }

    return render_template(
        'pallet/v2/controle_pallets/vales.html',
        documentos=documentos,
        stats=stats,
        filtro_tipo=tipo,
        filtro_status=status,
        filtro_cnpj=cnpj
    )


@controle_pallets_bp.route('/solucoes')
@login_required
def listar_solucoes():
    """
    Lista créditos pendentes de solução.

    Query params:
    - status: PENDENTE, PARCIAL, RESOLVIDO
    - tipo_responsavel: TRANSPORTADORA, CLIENTE
    - cnpj: CNPJ do responsável
    - page: Página (default: 1)
    """
    status = request.args.get('status', '')
    tipo_responsavel = request.args.get('tipo_responsavel', '')
    cnpj = request.args.get('cnpj', '').strip()
    page = request.args.get('page', 1, type=int)

    query = PalletCredito.query.filter(PalletCredito.ativo == True)

    # Filtrar por status
    if status:
        query = query.filter(PalletCredito.status == status)
    else:
        # Default: mostrar apenas pendentes e parciais
        query = query.filter(PalletCredito.status.in_(['PENDENTE', 'PARCIAL']))

    # Filtrar por tipo de responsável
    if tipo_responsavel:
        query = query.filter(PalletCredito.tipo_responsavel == tipo_responsavel)

    # Filtrar por CNPJ
    if cnpj:
        cnpj_limpo = cnpj.replace('.', '').replace('-', '').replace('/', '')
        query = query.filter(
            db.or_(
                PalletCredito.cnpj_responsavel.ilike(f'%{cnpj_limpo}%'),
                PalletCredito.nome_responsavel.ilike(f'%{cnpj}%')
            )
        )

    # Ordenar por vencimento (mais urgentes primeiro)
    query = query.order_by(
        PalletCredito.data_vencimento.asc().nullsfirst(),
        PalletCredito.criado_em.desc()
    )

    creditos = query.paginate(page=page, per_page=50, error_out=False)

    # Estatísticas
    stats_query = db.session.query(
        PalletCredito.status,
        func.count(PalletCredito.id).label('quantidade'),
        func.sum(PalletCredito.qtd_saldo).label('saldo_total')
    ).filter(
        PalletCredito.ativo == True
    ).group_by(PalletCredito.status).all()

    stats = {
        'pendentes': 0,
        'pendentes_saldo': 0,
        'parciais': 0,
        'parciais_saldo': 0,
        'resolvidos': 0
    }
    for row in stats_query:
        if row.status == 'PENDENTE':
            stats['pendentes'] = row.quantidade
            stats['pendentes_saldo'] = int(row.saldo_total or 0)
        elif row.status == 'PARCIAL':
            stats['parciais'] = row.quantidade
            stats['parciais_saldo'] = int(row.saldo_total or 0)
        elif row.status == 'RESOLVIDO':
            stats['resolvidos'] = row.quantidade

    return render_template(
        'pallet/v2/controle_pallets/solucoes.html',
        creditos=creditos,
        stats=stats,
        filtro_status=status,
        filtro_tipo_responsavel=tipo_responsavel,
        filtro_cnpj=cnpj
    )


@controle_pallets_bp.route('/historico')
@login_required
def historico_solucoes():
    """
    Histórico de soluções registradas.

    Query params:
    - tipo: BAIXA, VENDA, RECEBIMENTO, SUBSTITUICAO
    - data_de: Data inicial
    - data_ate: Data final
    - cnpj: CNPJ do responsável
    - page: Página (default: 1)
    """
    tipo = request.args.get('tipo', '')
    data_de = request.args.get('data_de', '')
    data_ate = request.args.get('data_ate', '')
    cnpj = request.args.get('cnpj', '').strip()
    page = request.args.get('page', 1, type=int)

    query = PalletSolucao.query.filter(PalletSolucao.ativo == True)

    if tipo:
        query = query.filter(PalletSolucao.tipo == tipo)

    if data_de:
        try:
            dt_de = datetime.strptime(data_de, '%Y-%m-%d')
            query = query.filter(PalletSolucao.criado_em >= dt_de)
        except ValueError:
            pass

    if data_ate:
        try:
            dt_ate = datetime.strptime(data_ate, '%Y-%m-%d')
            query = query.filter(PalletSolucao.criado_em <= dt_ate)
        except ValueError:
            pass

    if cnpj:
        cnpj_limpo = cnpj.replace('.', '').replace('-', '').replace('/', '')
        query = query.filter(
            db.or_(
                PalletSolucao.cnpj_responsavel.ilike(f'%{cnpj_limpo}%'),
                PalletSolucao.nome_responsavel.ilike(f'%{cnpj}%')
            )
        )

    query = query.order_by(PalletSolucao.criado_em.desc())

    solucoes = query.paginate(page=page, per_page=50, error_out=False)

    # Estatísticas por tipo
    stats = db.session.query(
        PalletSolucao.tipo,
        func.count(PalletSolucao.id).label('quantidade'),
        func.sum(PalletSolucao.quantidade).label('qtd_total')
    ).filter(
        PalletSolucao.ativo == True
    ).group_by(PalletSolucao.tipo).all()

    # Inicializar com todos os tipos possíveis (evita UndefinedError no template)
    stats_dict = {
        'BAIXA': {'count': 0, 'qtd': 0},
        'VENDA': {'count': 0, 'qtd': 0},
        'RECEBIMENTO': {'count': 0, 'qtd': 0},
        'SUBSTITUICAO': {'count': 0, 'qtd': 0}
    }
    # Popular com dados reais do banco
    for row in stats:
        if row.tipo in stats_dict:
            stats_dict[row.tipo] = {
                'count': row.quantidade,
                'qtd': int(row.qtd_total or 0)
            }

    return render_template(
        'pallet/v2/controle_pallets/historico.html',
        solucoes=solucoes,
        stats=stats_dict,
        filtro_tipo=tipo,
        filtro_data_de=data_de,
        filtro_data_ate=data_ate,
        filtro_cnpj=cnpj
    )


# =============================================================================
# AÇÕES: DOCUMENTOS
# =============================================================================

@controle_pallets_bp.route('/documento', methods=['POST'])
@login_required
def registrar_documento():
    """
    Registra um documento (canhoto ou vale pallet).

    Form params:
    - credito_id: ID do crédito (obrigatório)
    - tipo: CANHOTO ou VALE_PALLET (obrigatório)
    - numero_documento: Número do documento
    - data_emissao: Data de emissão
    - data_validade: Data de validade
    - quantidade: Quantidade de pallets
    - cnpj_emissor: CNPJ do emissor
    - nome_emissor: Nome do emissor
    - observacao: Observações
    """
    credito_id = request.form.get('credito_id', type=int)
    tipo = request.form.get('tipo', '').strip()
    numero_documento = request.form.get('numero_documento', '').strip()

    if not credito_id:
        flash('ID do crédito é obrigatório!', 'danger')
        return redirect(request.referrer or url_for('pallet_v2.controle_pallets.listar_solucoes'))

    if tipo not in ('CANHOTO', 'VALE_PALLET'):
        flash('Tipo de documento inválido!', 'danger')
        return redirect(request.referrer or url_for('pallet_v2.controle_pallets.listar_solucoes'))

    try:
        # Parsear datas
        data_emissao = None
        data_emissao_str = request.form.get('data_emissao', '').strip()
        if data_emissao_str:
            data_emissao = datetime.strptime(data_emissao_str, '%Y-%m-%d').date()

        data_validade = None
        data_validade_str = request.form.get('data_validade', '').strip()
        if data_validade_str:
            data_validade = datetime.strptime(data_validade_str, '%Y-%m-%d').date()

        quantidade = request.form.get('quantidade', type=int) or 0

        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

        documento = CreditoService.registrar_documento(
            credito_id=credito_id,
            tipo=tipo,
            numero_documento=numero_documento or None,
            data_emissao=data_emissao,
            data_validade=data_validade,
            quantidade=quantidade,
            cnpj_emissor=request.form.get('cnpj_emissor', '').replace('.', '').replace('-', '').replace('/', '') or None,
            nome_emissor=request.form.get('nome_emissor', '').strip() or None,
            arquivo_path=None,  # TODO: implementar upload
            usuario=usuario,
            observacao=request.form.get('observacao', '').strip() or None
        )

        flash(f'Documento {tipo} registrado com sucesso! (#{documento.id})', 'success')

    except ValueError as e:
        flash(f'Erro de validação: {str(e)}', 'danger')
    except Exception as e:
        logger.exception(f"Erro ao registrar documento")
        flash(f'Erro ao registrar documento: {str(e)}', 'danger')

    return redirect(request.referrer or url_for('pallet_v2.controle_pallets.listar_solucoes'))


@controle_pallets_bp.route('/documento/<int:doc_id>/receber', methods=['POST'])
@login_required
def receber_documento(doc_id):
    """
    Marca um documento como recebido pela Nacom.
    """
    documento = PalletDocumento.query.get_or_404(doc_id)

    if documento.recebido:
        flash('Este documento já foi recebido!', 'warning')
        return redirect(request.referrer or url_for('pallet_v2.controle_pallets.listar_vales'))

    try:
        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

        CreditoService.registrar_recebimento_documento(
            documento_id=doc_id,
            usuario=usuario,
            observacao=request.form.get('observacao', '').strip() or None
        )

        flash('Documento marcado como recebido!', 'success')

    except Exception as e:
        logger.exception(f"Erro ao receber documento #{doc_id}")
        flash(f'Erro ao receber documento: {str(e)}', 'danger')

    return redirect(request.referrer or url_for('pallet_v2.controle_pallets.listar_vales'))


# =============================================================================
# AÇÕES: SOLUÇÕES
# =============================================================================

@controle_pallets_bp.route('/baixa', methods=['POST'])
@login_required
def registrar_baixa():
    """
    Registra uma baixa (descarte) de pallets.

    Form params:
    - credito_id: ID do crédito (obrigatório)
    - quantidade: Quantidade sendo baixada (obrigatório)
    - motivo: Motivo da baixa (obrigatório)
    - confirmado_cliente: Se cliente confirmou (checkbox)
    - observacao: Observações adicionais
    """
    credito_id = request.form.get('credito_id', type=int)
    quantidade = request.form.get('quantidade', type=int)
    motivo = request.form.get('motivo', '').strip()

    if not credito_id or not quantidade or not motivo:
        flash('Crédito, quantidade e motivo são obrigatórios!', 'danger')
        return redirect(request.referrer or url_for('pallet_v2.controle_pallets.listar_solucoes'))

    try:
        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        confirmado_cliente = request.form.get('confirmado_cliente') == 'on'

        solucao, credito = SolucaoPalletService.registrar_baixa(
            credito_id=credito_id,
            quantidade=quantidade,
            motivo=motivo,
            usuario=usuario,
            confirmado_cliente=confirmado_cliente,
            observacao=request.form.get('observacao', '').strip() or None
        )

        flash(
            f'Baixa de {quantidade} pallet(s) registrada! '
            f'Saldo restante: {credito.qtd_saldo}',
            'success'
        )

    except ValueError as e:
        flash(f'Erro de validação: {str(e)}', 'danger')
    except Exception as e:
        logger.exception(f"Erro ao registrar baixa")
        flash(f'Erro ao registrar baixa: {str(e)}', 'danger')

    return redirect(request.referrer or url_for('pallet_v2.controle_pallets.listar_solucoes'))


@controle_pallets_bp.route('/venda', methods=['POST'])
@login_required
def registrar_venda():
    """
    Registra uma venda de pallets (N:1 - múltiplos créditos → 1 NF venda).

    Form params:
    - nf_venda: Número da NF de venda (obrigatório)
    - data_venda: Data da venda
    - valor_unitario: Valor unitário do pallet
    - cnpj_comprador: CNPJ do comprador
    - nome_comprador: Nome do comprador
    - creditos: JSON com lista de {credito_id, quantidade}
    - observacao: Observações
    """
    nf_venda = request.form.get('nf_venda', '').strip()
    creditos_json = request.form.get('creditos', '[]')

    if not nf_venda:
        flash('Número da NF de venda é obrigatório!', 'danger')
        return redirect(request.referrer or url_for('pallet_v2.controle_pallets.listar_solucoes'))

    try:
        import json
        creditos_quantidades = json.loads(creditos_json)

        if not creditos_quantidades:
            flash('Selecione pelo menos um crédito para a venda!', 'danger')
            return redirect(request.referrer or url_for('pallet_v2.controle_pallets.listar_solucoes'))

        # Parsear data
        data_venda = date.today()
        data_venda_str = request.form.get('data_venda', '').strip()
        if data_venda_str:
            data_venda = datetime.strptime(data_venda_str, '%Y-%m-%d').date()

        # Parsear valor
        valor_unitario = 35.0
        valor_str = request.form.get('valor_unitario', '').strip()
        if valor_str:
            valor_unitario = float(converter_valor_brasileiro(valor_str))

        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

        resultado = SolucaoPalletService.registrar_venda(
            nf_venda=nf_venda,
            creditos_quantidades=creditos_quantidades,
            data_venda=data_venda,
            valor_unitario=valor_unitario,
            cnpj_comprador=request.form.get('cnpj_comprador', '').replace('.', '').replace('-', '').replace('/', ''),
            nome_comprador=request.form.get('nome_comprador', '').strip(),
            usuario=usuario,
            chave_nfe=request.form.get('chave_nfe', '').strip() or None,
            observacao=request.form.get('observacao', '').strip() or None
        )

        flash(
            f'Venda registrada! NF {nf_venda} - '
            f'{len(resultado["solucoes"])} crédito(s), '
            f'{resultado["quantidade_total"]} pallet(s)',
            'success'
        )

    except ValueError as e:
        flash(f'Erro de validação: {str(e)}', 'danger')
    except Exception as e:
        logger.exception(f"Erro ao registrar venda")
        flash(f'Erro ao registrar venda: {str(e)}', 'danger')

    return redirect(request.referrer or url_for('pallet_v2.controle_pallets.listar_solucoes'))


@controle_pallets_bp.route('/recebimento', methods=['POST'])
@login_required
def registrar_recebimento():
    """
    Registra um recebimento (coleta física) de pallets.

    Form params:
    - credito_id: ID do crédito (obrigatório)
    - quantidade: Quantidade recebida (obrigatório)
    - data_recebimento: Data do recebimento
    - local_recebimento: Local onde foi recebido
    - observacao: Observações
    """
    credito_id = request.form.get('credito_id', type=int)
    quantidade = request.form.get('quantidade', type=int)

    if not credito_id or not quantidade:
        flash('Crédito e quantidade são obrigatórios!', 'danger')
        return redirect(request.referrer or url_for('pallet_v2.controle_pallets.listar_solucoes'))

    try:
        # Parsear data
        data_recebimento = date.today()
        data_str = request.form.get('data_recebimento', '').strip()
        if data_str:
            data_recebimento = datetime.strptime(data_str, '%Y-%m-%d').date()

        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

        # Buscar dados do responsável do crédito para preencher recebido_de e cnpj_entregador
        credito_obj = PalletCredito.query.get(credito_id)
        if not credito_obj:
            flash(f'Crédito #{credito_id} não encontrado!', 'danger')
            return redirect(request.referrer or url_for('pallet_v2.controle_pallets.listar_solucoes'))

        # Preparar recebido_de e cnpj_entregador (do formulário ou do crédito)
        recebido_de = request.form.get('recebido_de', '').strip()
        if not recebido_de:
            recebido_de = credito_obj.nome_responsavel or ''

        cnpj_entregador = request.form.get('cnpj_entregador', '').strip()
        if cnpj_entregador:
            cnpj_entregador = cnpj_entregador.replace('.', '').replace('-', '').replace('/', '')
        else:
            cnpj_entregador = credito_obj.cnpj_responsavel or ''

        solucao, credito = SolucaoPalletService.registrar_recebimento(
            credito_id=credito_id,
            quantidade=quantidade,
            data_recebimento=data_recebimento,
            local_recebimento=request.form.get('local_recebimento', '').strip() or 'CD Nacom',
            recebido_de=recebido_de,
            cnpj_entregador=cnpj_entregador,
            usuario=usuario,
            observacao=request.form.get('observacao', '').strip() or None
        )

        flash(
            f'Recebimento de {quantidade} pallet(s) registrado! '
            f'Saldo restante: {credito.qtd_saldo}',
            'success'
        )

    except ValueError as e:
        flash(f'Erro de validação: {str(e)}', 'danger')
    except Exception as e:
        logger.exception(f"Erro ao registrar recebimento")
        flash(f'Erro ao registrar recebimento: {str(e)}', 'danger')

    return redirect(request.referrer or url_for('pallet_v2.controle_pallets.listar_solucoes'))


@controle_pallets_bp.route('/substituicao', methods=['POST'])
@login_required
def registrar_substituicao():
    """
    Registra uma substituição (transferência de responsabilidade).

    Form params:
    - credito_origem_id: ID do crédito de origem (obrigatório)
    - credito_destino_id: ID do crédito de destino (pode ser None para criar novo)
    - quantidade: Quantidade sendo transferida (obrigatório)
    - nf_remessa_destino_id: ID da NF de remessa destino (se criando novo crédito)
    - tipo_responsavel_destino: TRANSPORTADORA ou CLIENTE
    - cnpj_destino: CNPJ do novo responsável
    - nome_destino: Nome do novo responsável
    - observacao: Observações
    """
    credito_origem_id = request.form.get('credito_origem_id', type=int)
    quantidade = request.form.get('quantidade', type=int)

    if not credito_origem_id or not quantidade:
        flash('Crédito de origem e quantidade são obrigatórios!', 'danger')
        return redirect(request.referrer or url_for('pallet_v2.controle_pallets.listar_solucoes'))

    try:
        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

        credito_destino_id = request.form.get('credito_destino_id', type=int)

        # Se não tem crédito destino, pode criar novo
        if not credito_destino_id:
            nf_remessa_destino_id = request.form.get('nf_remessa_destino_id', type=int)
            if nf_remessa_destino_id:
                # Criar novo crédito para a NF de destino
                novo_credito = SolucaoPalletService.criar_credito_para_substituicao(
                    nf_remessa_id=nf_remessa_destino_id,
                    quantidade=quantidade,
                    tipo_responsavel=request.form.get('tipo_responsavel_destino', 'CLIENTE'),
                    cnpj_responsavel=request.form.get('cnpj_destino', '').replace('.', '').replace('-', '').replace('/', ''),
                    nome_responsavel=request.form.get('nome_destino', '').strip(),
                    usuario=usuario
                )
                credito_destino_id = novo_credito.id

        motivo = request.form.get('motivo', '').strip()
        if not motivo:
            motivo = "Substituição de responsabilidade"  # Motivo padrão

        solucao, credito_origem = SolucaoPalletService.registrar_substituicao(
            credito_origem_id=credito_origem_id,
            credito_destino_id=credito_destino_id,
            quantidade=quantidade,
            motivo=motivo,
            usuario=usuario,
            observacao=request.form.get('observacao', '').strip() or None
        )

        flash(
            f'Substituição de {quantidade} pallet(s) registrada! '
            f'Saldo origem: {credito_origem.qtd_saldo}',
            'success'
        )

    except ValueError as e:
        flash(f'Erro de validação: {str(e)}', 'danger')
    except Exception as e:
        logger.exception(f"Erro ao registrar substituição")
        flash(f'Erro ao registrar substituição: {str(e)}', 'danger')

    return redirect(request.referrer or url_for('pallet_v2.controle_pallets.listar_solucoes'))


# =============================================================================
# APIs
# =============================================================================

@controle_pallets_bp.route('/api/creditos')
@login_required
def api_listar_creditos():
    """
    API para listar créditos pendentes.

    Query params:
    - status: PENDENTE, PARCIAL, RESOLVIDO
    - cnpj: CNPJ do responsável
    - limit: Limite de resultados (default: 50)
    """
    status = request.args.get('status', '')
    cnpj = request.args.get('cnpj', '').strip()
    limit = request.args.get('limit', 50, type=int)

    creditos = CreditoService.listar_creditos_pendentes(
        cnpj_responsavel=cnpj if cnpj else None,
        status=status if status else None,
        limite=limit
    )

    return jsonify([{
        'id': c.id,
        'nf_remessa_id': c.nf_remessa_id,
        'numero_nf': c.nf_remessa.numero_nf if c.nf_remessa else None,
        'qtd_original': c.qtd_original,
        'qtd_saldo': c.qtd_saldo,
        'tipo_responsavel': c.tipo_responsavel,
        'cnpj_responsavel': c.cnpj_responsavel,
        'nome_responsavel': c.nome_responsavel,
        'status': c.status,
        'data_vencimento': c.data_vencimento.isoformat() if c.data_vencimento else None
    } for c in creditos])


@controle_pallets_bp.route('/api/credito/<int:credito_id>')
@login_required
def api_detalhe_credito(credito_id):
    """
    API para obter detalhes de um crédito.
    """
    credito = PalletCredito.query.get_or_404(credito_id)

    # Buscar documentos
    documentos = PalletDocumento.query.filter(
        PalletDocumento.credito_id == credito_id,
        PalletDocumento.ativo == True
    ).all()

    # Buscar soluções
    solucoes = PalletSolucao.query.filter(
        PalletSolucao.credito_id == credito_id,
        PalletSolucao.ativo == True
    ).order_by(PalletSolucao.criado_em.desc()).all()

    return jsonify({
        'credito': {
            'id': credito.id,
            'nf_remessa_id': credito.nf_remessa_id,
            'numero_nf': credito.nf_remessa.numero_nf if credito.nf_remessa else None,
            'qtd_original': credito.qtd_original,
            'qtd_saldo': credito.qtd_saldo,
            'tipo_responsavel': credito.tipo_responsavel,
            'cnpj_responsavel': credito.cnpj_responsavel,
            'nome_responsavel': credito.nome_responsavel,
            'status': credito.status,
            'data_vencimento': credito.data_vencimento.isoformat() if credito.data_vencimento else None,
            'prazo_dias': credito.prazo_dias
        },
        'documentos': [{
            'id': d.id,
            'tipo': d.tipo,
            'numero_documento': d.numero_documento,
            'quantidade': d.quantidade,
            'recebido': d.recebido,
            'recebido_em': d.recebido_em.isoformat() if d.recebido_em else None
        } for d in documentos],
        'solucoes': [{
            'id': s.id,
            'tipo': s.tipo,
            'quantidade': s.quantidade,
            'criado_em': s.criado_em.isoformat() if s.criado_em else None,
            'criado_por': s.criado_por
        } for s in solucoes]
    })


@controle_pallets_bp.route('/api/resumo-responsavel/<cnpj>')
@login_required
def api_resumo_responsavel(cnpj):
    """
    API para obter resumo de créditos de um responsável.
    """
    cnpj_limpo = cnpj.replace('.', '').replace('-', '').replace('/', '')
    resumo = CreditoService.obter_resumo_por_responsavel(cnpj_limpo)
    return jsonify(resumo)
