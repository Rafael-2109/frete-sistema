"""
Routes de Tratativa de NFs de Pallet v2 - Domínio B

Gerencia o ciclo de vida documental das NFs:
- GET /tratativa/direcionamento - NFs aguardando vinculação
- GET /tratativa/sugestoes - Sugestões automáticas de match
- POST /tratativa/vincular-devolucao - Vincular devolução (1:N)
- POST /tratativa/registrar-recusa - Registrar recusa (sem NF, apenas controle interno)
- POST /tratativa/confirmar-sugestao/<id> - Confirmar sugestão
- POST /tratativa/rejeitar-sugestao/<id> - Rejeitar sugestão
- GET /tratativa/canceladas - NFs canceladas (histórico)

Tipos de Solução (Domínio B):
- DEVOLUCAO: NF de devolução emitida pelo cliente (1 devolução → N remessas)
- RECUSA: NF recusada pelo cliente (sem NF, registro manual interno)
- CANCELAMENTO: NF cancelada no Odoo (importado automaticamente)
- NOTA_CREDITO: NC vinculada via reversed_entry_id (automático)

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
"""
import logging
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.pallet.models import PalletNFRemessa, PalletNFSolucao, PalletCredito, PalletDocumento, PalletSolucao
from app.pallet.services import NFService, MatchService

logger = logging.getLogger(__name__)

# Sub-blueprint para Tratativa de NFs (Domínio B)
tratativa_nfs_bp = Blueprint('tratativa_nfs', __name__, url_prefix='/tratativa')


# =============================================================================
# LISTAGENS
# =============================================================================

@tratativa_nfs_bp.route('/direcionamento')
@login_required
def direcionamento():
    """
    Lista NFs aguardando vinculação (direcionamento).

    Query params:
    - tipo_destinatario: TRANSPORTADORA, CLIENTE
    - cnpj: CNPJ do destinatário
    - empresa: CD, FB, SC
    - page: Página (default: 1)

    Colunas enriquecidas:
    - Vales: Canhoto e Vale Pallet com quantidades (via PalletCredito → PalletDocumento)
    - Solução Pallets: Progresso de resolução (via PalletCredito → PalletSolucao)
    - Odoo: Soluções automáticas (PalletNFSolucao com vinculacao='AUTOMATICO')
    - Controle: Soluções manuais (PalletNFSolucao com vinculacao='MANUAL')
    """
    tipo_destinatario = request.args.get('tipo_destinatario', '')
    cnpj = request.args.get('cnpj', '').strip()
    empresa = request.args.get('empresa', '')
    page = request.args.get('page', 1, type=int)

    # Query base com eager loading para dados relacionados
    query = PalletNFRemessa.query.options(
        joinedload(PalletNFRemessa.creditos).joinedload(PalletCredito.documentos),
        joinedload(PalletNFRemessa.creditos).joinedload(PalletCredito.solucoes),
        joinedload(PalletNFRemessa.solucoes_nf)
    ).filter(
        PalletNFRemessa.ativo == True,
        PalletNFRemessa.status == 'ATIVA'
    )

    # Filtrar por tipo de destinatário
    if tipo_destinatario:
        query = query.filter(PalletNFRemessa.tipo_destinatario == tipo_destinatario)

    # Filtrar por CNPJ
    if cnpj:
        cnpj_limpo = cnpj.replace('.', '').replace('-', '').replace('/', '')
        query = query.filter(
            db.or_(
                PalletNFRemessa.cnpj_destinatario.ilike(f'%{cnpj_limpo}%'),
                PalletNFRemessa.nome_destinatario.ilike(f'%{cnpj}%')
            )
        )

    # Filtrar por empresa
    if empresa:
        query = query.filter(PalletNFRemessa.empresa == empresa)

    # Ordenar por data de emissão (mais antigas primeiro)
    query = query.order_by(PalletNFRemessa.data_emissao.asc())

    nfs = query.paginate(page=page, per_page=50, error_out=False)

    # Enriquecer cada NF com dados calculados para as novas colunas
    nfs_enriquecidas = []
    for nf in nfs.items:
        nf_data = {
            'nf': nf,
            'vales': _calcular_dados_vales(nf),
            'solucao_pallets': _calcular_dados_solucao_pallets(nf),
            'odoo': _filtrar_solucoes_nf(nf, vinculacao='AUTOMATICO'),
            'controle': _filtrar_solucoes_nf(nf, vinculacao='MANUAL')
        }
        nfs_enriquecidas.append(nf_data)

    # Estatísticas
    stats = {
        'total_ativas': nfs.total,
        'transportadoras': PalletNFRemessa.query.filter(
            PalletNFRemessa.ativo == True,
            PalletNFRemessa.status == 'ATIVA',
            PalletNFRemessa.tipo_destinatario == 'TRANSPORTADORA'
        ).count(),
        'clientes': PalletNFRemessa.query.filter(
            PalletNFRemessa.ativo == True,
            PalletNFRemessa.status == 'ATIVA',
            PalletNFRemessa.tipo_destinatario == 'CLIENTE'
        ).count()
    }

    return render_template(
        'pallet/v2/tratativa_nfs/direcionamento.html',
        nfs=nfs,
        nfs_enriquecidas=nfs_enriquecidas,
        stats=stats,
        filtro_tipo_destinatario=tipo_destinatario,
        filtro_cnpj=cnpj,
        filtro_empresa=empresa
    )


def _calcular_dados_vales(nf: PalletNFRemessa) -> dict:
    """
    Calcula dados de vales (canhoto e vale_pallet) para uma NF de remessa.

    Returns:
        dict: {
            'canhoto': {'qtd_total': int, 'qtd_recebidos': int},
            'vale_pallet': {'qtd_total': int, 'qtd_recebidos': int}
        }
    """
    resultado = {
        'canhoto': {'qtd_total': 0, 'qtd_recebidos': 0},
        'vale_pallet': {'qtd_total': 0, 'qtd_recebidos': 0}
    }

    # Iterar sobre créditos da NF (já carregados via eager loading)
    for credito in nf.creditos:
        for doc in credito.documentos:
            if not doc.ativo:
                continue

            if doc.tipo == 'CANHOTO':
                resultado['canhoto']['qtd_total'] += doc.quantidade or 0
                if doc.recebido:
                    resultado['canhoto']['qtd_recebidos'] += doc.quantidade or 0
            elif doc.tipo == 'VALE_PALLET':
                resultado['vale_pallet']['qtd_total'] += doc.quantidade or 0
                if doc.recebido:
                    resultado['vale_pallet']['qtd_recebidos'] += doc.quantidade or 0

    return resultado


def _calcular_dados_solucao_pallets(nf: PalletNFRemessa) -> dict:
    """
    Calcula dados de soluções de pallets (Domínio A) para uma NF de remessa.

    Tipos de solução: BAIXA, VENDA, RECEBIMENTO, SUBSTITUICAO

    Returns:
        dict: {
            'qtd_original': int,
            'qtd_resolvida': int,
            'qtd_pendente': int,
            'percentual': float
        }
    """
    qtd_original = 0
    qtd_resolvida = 0

    # Iterar sobre créditos da NF (já carregados via eager loading)
    for credito in nf.creditos:
        if not credito.ativo:
            continue

        qtd_original += credito.qtd_original or 0

        # Somar soluções do crédito (BAIXA, VENDA, RECEBIMENTO, SUBSTITUICAO)
        for solucao in credito.solucoes:
            if solucao.ativo:
                qtd_resolvida += solucao.quantidade or 0

    percentual = 0.0
    if qtd_original > 0:
        percentual = round((qtd_resolvida / qtd_original) * 100, 1)

    return {
        'qtd_original': qtd_original,
        'qtd_resolvida': qtd_resolvida,
        'qtd_pendente': qtd_original - qtd_resolvida,
        'percentual': percentual
    }


def _filtrar_solucoes_nf(nf: PalletNFRemessa, vinculacao: str) -> list:
    """
    Filtra soluções documentais (Domínio B) por tipo de vinculação.

    Args:
        nf: NF de remessa
        vinculacao: 'AUTOMATICO' (Odoo) ou 'MANUAL' (Controle)

    Returns:
        list: Lista de dicts com dados das soluções
    """
    solucoes = []

    for solucao in nf.solucoes_nf:
        if not solucao.ativo or solucao.vinculacao != vinculacao:
            continue
        if solucao.rejeitado:
            continue

        solucoes.append({
            'id': solucao.id,
            'tipo': solucao.tipo,
            'tipo_display': solucao.tipo_display,
            'quantidade': solucao.quantidade,
            'numero_nf': solucao.numero_nf_solucao,
            'data': solucao.data_nf_solucao,
            'info_complementar': solucao.info_complementar,  # Motivo da recusa
            'criado_em': solucao.criado_em
        })

    return solucoes


@tratativa_nfs_bp.route('/sugestoes')
@login_required
def listar_sugestoes():
    """
    Lista devoluções de pallet do DFe pendentes de entrada (não têm NC).

    Apenas devoluções DEVOLUCAO são listadas como sugestões, pois:
    - RECUSA: é registro manual (não existe NF fiscal)
    - CANCELAMENTO: é importado automaticamente do Odoo
    - NOTA_CREDITO: é vinculada automaticamente via reversed_entry_id

    Query params:
    - page: Página (default: 1)
    """
    page = request.args.get('page', 1, type=int)

    # Query base: sugestões pendentes - APENAS DEVOLUCAO
    # RECUSA e CANCELAMENTO são registros manuais, não sugestões do DFe
    query = PalletNFSolucao.query.filter(
        PalletNFSolucao.ativo == True,
        PalletNFSolucao.vinculacao == 'SUGESTAO',
        PalletNFSolucao.confirmado == False,
        PalletNFSolucao.rejeitado == False,
        PalletNFSolucao.tipo == 'DEVOLUCAO'  # Apenas devoluções pendentes de entrada
    )

    # Ordenar por data de criação (mais antigas primeiro)
    query = query.order_by(PalletNFSolucao.criado_em.asc())

    sugestoes = query.paginate(page=page, per_page=50, error_out=False)

    # Estatísticas simplificadas - apenas devoluções
    stats = {
        'total_pendentes': sugestoes.total,
        'devolucoes': sugestoes.total
    }

    return render_template(
        'pallet/v2/tratativa_nfs/sugestoes.html',
        sugestoes=sugestoes,
        stats=stats,
        filtro_tipo='DEVOLUCAO'  # Sempre DEVOLUCAO agora
    )


@tratativa_nfs_bp.route('/solucoes')
@login_required
def listar_solucoes():
    """
    Histórico de soluções de NF (devoluções, recusas, cancelamentos, NCs).

    Query params:
    - tipo: DEVOLUCAO, RECUSA, CANCELAMENTO, NOTA_CREDITO
    - vinculacao: AUTOMATICO, MANUAL, SUGESTAO
    - data_de: Data inicial
    - data_ate: Data final
    - page: Página (default: 1)
    """
    tipo = request.args.get('tipo', '')
    vinculacao = request.args.get('vinculacao', '')
    data_de = request.args.get('data_de', '')
    data_ate = request.args.get('data_ate', '')
    page = request.args.get('page', 1, type=int)

    query = PalletNFSolucao.query.filter(PalletNFSolucao.ativo == True)

    # Filtrar por tipo
    if tipo:
        query = query.filter(PalletNFSolucao.tipo == tipo)

    # Filtrar por tipo de vinculação
    if vinculacao:
        query = query.filter(PalletNFSolucao.vinculacao == vinculacao)

    # Filtrar por data
    if data_de:
        try:
            dt_de = datetime.strptime(data_de, '%Y-%m-%d')
            query = query.filter(PalletNFSolucao.criado_em >= dt_de)
        except ValueError:
            pass

    if data_ate:
        try:
            dt_ate = datetime.strptime(data_ate, '%Y-%m-%d')
            query = query.filter(PalletNFSolucao.criado_em <= dt_ate)
        except ValueError:
            pass

    # Ordenar por data de criação (mais recentes primeiro)
    query = query.order_by(PalletNFSolucao.criado_em.desc())

    solucoes = query.paginate(page=page, per_page=50, error_out=False)

    # Estatísticas
    stats_query = db.session.query(
        PalletNFSolucao.tipo,
        func.count(PalletNFSolucao.id).label('quantidade'),
        func.sum(PalletNFSolucao.quantidade).label('qtd_total')
    ).filter(
        PalletNFSolucao.ativo == True
    ).group_by(PalletNFSolucao.tipo).all()

    stats = {}
    for row in stats_query:
        stats[row.tipo] = {
            'count': row.quantidade,
            'qtd': int(row.qtd_total or 0)
        }

    return render_template(
        'pallet/v2/tratativa_nfs/solucoes.html',
        solucoes=solucoes,
        stats=stats,
        filtro_tipo=tipo,
        filtro_vinculacao=vinculacao,
        filtro_data_de=data_de,
        filtro_data_ate=data_ate
    )


@tratativa_nfs_bp.route('/canceladas')
@login_required
def listar_canceladas():
    """
    Lista NFs canceladas (histórico para auditoria).

    Query params:
    - data_de: Data inicial
    - data_ate: Data final
    - page: Página (default: 1)
    """
    data_de = request.args.get('data_de', '')
    data_ate = request.args.get('data_ate', '')
    page = request.args.get('page', 1, type=int)

    query = PalletNFRemessa.query.filter(
        PalletNFRemessa.ativo == True,
        PalletNFRemessa.status == 'CANCELADA'
    )

    # Filtrar por data
    if data_de:
        try:
            dt_de = datetime.strptime(data_de, '%Y-%m-%d')
            query = query.filter(PalletNFRemessa.cancelada_em >= dt_de)
        except ValueError:
            pass

    if data_ate:
        try:
            dt_ate = datetime.strptime(data_ate, '%Y-%m-%d')
            query = query.filter(PalletNFRemessa.cancelada_em <= dt_ate)
        except ValueError:
            pass

    # Ordenar por data de cancelamento (mais recentes primeiro)
    query = query.order_by(PalletNFRemessa.cancelada_em.desc())

    nfs = query.paginate(page=page, per_page=50, error_out=False)

    return render_template(
        'pallet/v2/tratativa_nfs/canceladas.html',
        nfs=nfs,
        filtro_data_de=data_de,
        filtro_data_ate=data_ate
    )


# =============================================================================
# AÇÕES: VINCULAÇÃO
# =============================================================================

@tratativa_nfs_bp.route('/vincular-devolucao', methods=['POST'])
@login_required
def vincular_devolucao():
    """
    Vincula uma NF de devolução a múltiplas NFs de remessa (1:N).

    REGRA 004: 1 NF devolução pode fechar N NFs remessa.

    Form params:
    - numero_nf_devolucao: Número da NF de devolução
    - chave_nfe_devolucao: Chave da NF-e de devolução
    - data_nf_devolucao: Data da NF de devolução
    - nfs_remessa: JSON com lista de {nf_remessa_id, quantidade}
    - observacao: Observações
    """
    numero_nf_devolucao = request.form.get('numero_nf_devolucao', '').strip()
    nfs_remessa_json = request.form.get('nfs_remessa', '[]')

    if not numero_nf_devolucao:
        flash('Número da NF de devolução é obrigatório!', 'danger')
        return redirect(request.referrer or url_for('pallet_v2.tratativa_nfs.direcionamento'))

    try:
        import json
        nfs_remessa = json.loads(nfs_remessa_json)

        if not nfs_remessa:
            flash('Selecione pelo menos uma NF de remessa!', 'danger')
            return redirect(request.referrer or url_for('pallet_v2.tratativa_nfs.direcionamento'))

        # Parsear data
        data_nf_devolucao = None
        data_str = request.form.get('data_nf_devolucao', '').strip()
        if data_str:
            data_nf_devolucao = datetime.strptime(data_str, '%Y-%m-%d')

        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

        # Preparar dados com nomes de campos corretos para NFService.registrar_solucao_nf()
        cnpj_raw = request.form.get('cnpj_emitente', '').strip()
        cnpj_limpo = cnpj_raw.replace('.', '').replace('-', '').replace('/', '') if cnpj_raw else None

        # Quantidade total da NF de devolução (para validação 1:N)
        quantidade_devolucao = request.form.get('quantidade_devolucao', '0')
        try:
            quantidade_devolucao = int(quantidade_devolucao)
        except ValueError:
            quantidade_devolucao = 0

        nf_devolucao = {
            'numero_nf_solucao': numero_nf_devolucao,
            'serie_nf_solucao': request.form.get('serie_nf_devolucao', '').strip() or None,
            'data_nf_solucao': data_nf_devolucao,
            'cnpj_emitente': cnpj_limpo,
            'nome_emitente': request.form.get('nome_emitente', '').strip() or None,
            'quantidade': quantidade_devolucao,  # Para validação no MatchService
        }

        # Extrair IDs e quantidades
        nf_remessa_ids = [item['nf_remessa_id'] for item in nfs_remessa]
        quantidades = {item['nf_remessa_id']: item['quantidade'] for item in nfs_remessa}

        # Usar MatchService para vincular (método 1:N para múltiplas NFs)
        match_service = MatchService()
        solucoes = match_service.vincular_devolucao_manual_multiplas(
            nf_remessa_ids=nf_remessa_ids,
            nf_devolucao=nf_devolucao,
            quantidades=quantidades,
            usuario=usuario
        )

        flash(
            f'Devolução vinculada com sucesso! '
            f'NF {numero_nf_devolucao} → {len(solucoes)} NF(s) de remessa',
            'success'
        )

    except ValueError as e:
        flash(f'Erro de validação: {str(e)}', 'danger')
    except Exception as e:
        logger.exception(f"Erro ao vincular devolução")
        flash(f'Erro ao vincular devolução: {str(e)}', 'danger')

    return redirect(request.referrer or url_for('pallet_v2.tratativa_nfs.direcionamento'))


@tratativa_nfs_bp.route('/registrar-recusa', methods=['POST'])
@login_required
def registrar_recusa():
    """
    Registra uma recusa de NF de remessa (sem NF de retorno).

    RECUSA: O cliente recusou a NF de remessa sem emitir NF de devolução.
    Este é um registro manual interno para controle - não há documento fiscal associado.

    Form params:
    - nf_remessa_id: ID da NF de remessa recusada
    - quantidade: Quantidade de pallets recusados
    - motivo_recusa: Motivo da recusa (obrigatório)
    - observacao: Observações adicionais
    """
    nf_remessa_id = request.form.get('nf_remessa_id', type=int)
    motivo_recusa = request.form.get('motivo_recusa', '').strip()

    if not nf_remessa_id:
        flash('NF de remessa é obrigatória!', 'danger')
        return redirect(request.referrer or url_for('pallet_v2.tratativa_nfs.direcionamento'))

    if not motivo_recusa:
        flash('Motivo da recusa é obrigatório!', 'danger')
        return redirect(request.referrer or url_for('pallet_v2.tratativa_nfs.direcionamento'))

    try:
        quantidade = request.form.get('quantidade', type=int)
        observacao = request.form.get('observacao', '').strip() or None

        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

        # Usar NFService para registrar a recusa
        solucao = NFService.registrar_solucao_nf(
            nf_remessa_id=nf_remessa_id,
            tipo='RECUSA',
            quantidade=quantidade,
            dados={
                'info_complementar': motivo_recusa,
                'observacao': observacao,
            },
            usuario=usuario
        )

        nf_remessa = PalletNFRemessa.query.get(nf_remessa_id)
        flash(
            f'Recusa registrada com sucesso! '
            f'NF remessa {nf_remessa.numero_nf if nf_remessa else nf_remessa_id} - {quantidade} pallets',
            'success'
        )

    except ValueError as e:
        flash(f'Erro de validação: {str(e)}', 'danger')
    except Exception as e:
        logger.exception(f"Erro ao registrar recusa")
        flash(f'Erro ao registrar recusa: {str(e)}', 'danger')

    return redirect(request.referrer or url_for('pallet_v2.tratativa_nfs.direcionamento'))


@tratativa_nfs_bp.route('/confirmar-sugestao/<int:sugestao_id>', methods=['POST'])
@login_required
def confirmar_sugestao(sugestao_id):
    """
    Confirma uma sugestão de vinculação automática.
    """
    sugestao = PalletNFSolucao.query.get_or_404(sugestao_id)

    if sugestao.vinculacao != 'SUGESTAO':
        flash('Esta vinculação não é uma sugestão!', 'warning')
        return redirect(request.referrer or url_for('pallet_v2.tratativa_nfs.listar_sugestoes'))

    if sugestao.confirmado_em:
        flash('Esta sugestão já foi confirmada!', 'warning')
        return redirect(request.referrer or url_for('pallet_v2.tratativa_nfs.listar_sugestoes'))

    try:
        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

        NFService.confirmar_sugestao(sugestao_id, usuario=usuario)

        flash('Sugestão confirmada com sucesso!', 'success')

    except Exception as e:
        logger.exception(f"Erro ao confirmar sugestão #{sugestao_id}")
        flash(f'Erro ao confirmar sugestão: {str(e)}', 'danger')

    return redirect(request.referrer or url_for('pallet_v2.tratativa_nfs.listar_sugestoes'))


@tratativa_nfs_bp.route('/rejeitar-sugestao/<int:sugestao_id>', methods=['POST'])
@login_required
def rejeitar_sugestao(sugestao_id):
    """
    Rejeita uma sugestão de vinculação automática.
    """
    sugestao = PalletNFSolucao.query.get_or_404(sugestao_id)

    if sugestao.vinculacao != 'SUGESTAO':
        flash('Esta vinculação não é uma sugestão!', 'warning')
        return redirect(request.referrer or url_for('pallet_v2.tratativa_nfs.listar_sugestoes'))

    motivo = request.form.get('motivo', '').strip()

    try:
        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

        NFService.rejeitar_sugestao(sugestao_id, motivo=motivo, usuario=usuario)

        flash('Sugestão rejeitada!', 'success')

    except Exception as e:
        logger.exception(f"Erro ao rejeitar sugestão #{sugestao_id}")
        flash(f'Erro ao rejeitar sugestão: {str(e)}', 'danger')

    return redirect(request.referrer or url_for('pallet_v2.tratativa_nfs.listar_sugestoes'))


# =============================================================================
# AÇÕES: BUSCAR DEVOLUÇÕES NO DFE
# =============================================================================

@tratativa_nfs_bp.route('/processar-devolucoes', methods=['POST'])
@login_required
def processar_devolucoes():
    """
    Processa devoluções pendentes do DFe e cria sugestões de vinculação.

    Form params:
    - data_de: Data inicial (YYYY-MM-DD)
    - data_ate: Data final (YYYY-MM-DD)
    """
    data_de = request.form.get('data_de', '').strip() or None
    data_ate = request.form.get('data_ate', '').strip() or None

    try:
        match_service = MatchService()
        resultado = match_service.processar_devolucoes_pendentes(
            data_de=data_de,
            data_ate=data_ate,
            criar_sugestoes=True
        )

        flash(
            f'Processamento concluído! '
            f'{resultado.get("processadas", 0)} NF(s) processadas, '
            f'{resultado.get("sugestoes_criadas", 0)} sugestão(ões) criada(s), '
            f'{resultado.get("retornos_automaticos", 0)} retorno(s) automático(s)',
            'success'
        )

    except Exception as e:
        logger.exception(f"Erro ao processar devoluções")
        flash(f'Erro ao processar devoluções: {str(e)}', 'danger')

    return redirect(url_for('pallet_v2.tratativa_nfs.listar_sugestoes'))


# =============================================================================
# APIs
# =============================================================================

@tratativa_nfs_bp.route('/api/sugestoes')
@login_required
def api_listar_sugestoes():
    """
    API para listar sugestões pendentes.

    Query params:
    - tipo: DEVOLUCAO, RECUSA, NOTA_CREDITO, CANCELAMENTO
    - limit: Limite de resultados (default: 50)
    """
    tipo = request.args.get('tipo', '')
    limit = request.args.get('limit', 50, type=int)

    # Usa confirmado=False (boolean), não confirmado_em IS NULL (datetime)
    query = PalletNFSolucao.query.filter(
        PalletNFSolucao.ativo == True,
        PalletNFSolucao.vinculacao == 'SUGESTAO',
        PalletNFSolucao.confirmado == False,
        PalletNFSolucao.rejeitado == False
    )

    if tipo:
        query = query.filter(PalletNFSolucao.tipo == tipo)

    sugestoes = query.order_by(PalletNFSolucao.criado_em.asc()).limit(limit).all()

    return jsonify([{
        'id': s.id,
        'tipo': s.tipo,
        'nf_remessa_id': s.nf_remessa_id,
        'numero_nf_remessa': s.nf_remessa.numero_nf if s.nf_remessa else None,
        'numero_nf_solucao': s.numero_nf_solucao,
        'quantidade': s.quantidade,
        'score': s.score_match,
        'criado_em': s.criado_em.isoformat() if s.criado_em else None
    } for s in sugestoes])


@tratativa_nfs_bp.route('/api/buscar-devolucoes')
@login_required
def api_buscar_devolucoes():
    """
    API para buscar NFs de devolução no DFe.

    Query params:
    - data_de: Data inicial (YYYY-MM-DD)
    - data_ate: Data final (YYYY-MM-DD)
    """
    data_de = request.args.get('data_de', '')
    data_ate = request.args.get('data_ate', '')

    try:
        match_service = MatchService()
        nfs = match_service.buscar_nfs_devolucao_pallet_dfe(
            data_de=data_de if data_de else None,
            data_ate=data_ate if data_ate else None,
            apenas_nao_processadas=True
        )

        return jsonify({
            'sucesso': True,
            'nfs': nfs
        })

    except Exception as e:
        logger.exception(f"Erro ao buscar devoluções no DFe")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@tratativa_nfs_bp.route('/api/sugerir-vinculacao')
@login_required
def api_sugerir_vinculacao():
    """
    API para obter sugestões de vinculação para uma NF de devolução.

    Query params:
    - numero_nf: Número da NF de devolução
    - cnpj_emitente: CNPJ do emitente
    - quantidade: Quantidade de pallets
    """
    numero_nf = request.args.get('numero_nf', '').strip()
    cnpj_emitente = request.args.get('cnpj_emitente', '').strip()
    quantidade = request.args.get('quantidade', type=int) or 0

    if not numero_nf:
        return jsonify({'erro': 'Número da NF é obrigatório'}), 400

    try:
        # Preparar dados da NF de devolução
        nf_devolucao = {
            'numero_nf': numero_nf,
            'cnpj_emitente': cnpj_emitente.replace('.', '').replace('-', '').replace('/', ''),
            'quantidade': quantidade
        }

        match_service = MatchService()
        sugestoes = match_service.sugerir_vinculacao_devolucao(
            nf_devolucao=nf_devolucao,
            criar_sugestao=False  # Apenas retorna, não cria
        )

        return jsonify({
            'sucesso': True,
            'sugestoes': sugestoes
        })

    except Exception as e:
        logger.exception(f"Erro ao sugerir vinculação")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@tratativa_nfs_bp.route('/api/processar-devolucoes', methods=['POST'])
@login_required
def api_processar_devolucoes():
    """
    API para processar devoluções pendentes do DFe.

    Usada para:
    - Chamadas AJAX do frontend
    - Jobs agendados (cron)
    - Integrações externas

    JSON params:
    - data_de: Data inicial (YYYY-MM-DD) - opcional
    - data_ate: Data final (YYYY-MM-DD) - opcional

    Returns:
        JSON com resultado do processamento:
        {
            'sucesso': bool,
            'processadas': int,
            'devolucoes': int,
            'retornos': int,
            'retornos_automaticos': int,
            'sugestoes_criadas': int,
            'sem_match': int,
            'erros': int,
            'detalhes': [...]
        }
    """
    try:
        data = request.get_json() or {}
        data_de = data.get('data_de') or request.args.get('data_de')
        data_ate = data.get('data_ate') or request.args.get('data_ate')

        match_service = MatchService()
        resultado = match_service.processar_devolucoes_pendentes(
            data_de=data_de,
            data_ate=data_ate,
            criar_sugestoes=True
        )

        return jsonify({
            'sucesso': True,
            **resultado
        })

    except Exception as e:
        logger.exception("Erro ao processar devoluções via API")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@tratativa_nfs_bp.route('/api/nf-solucao/<int:solucao_id>')
@login_required
def api_detalhe_solucao(solucao_id):
    """
    API para obter detalhes de uma solução de NF.
    """
    solucao = PalletNFSolucao.query.get_or_404(solucao_id)

    return jsonify({
        'id': solucao.id,
        'nf_remessa_id': solucao.nf_remessa_id,
        'numero_nf_remessa': solucao.nf_remessa.numero_nf if solucao.nf_remessa else None,
        'tipo': solucao.tipo,
        'quantidade': solucao.quantidade,
        'numero_nf_solucao': solucao.numero_nf_solucao,
        'chave_nfe_solucao': solucao.chave_nfe_solucao,
        'data_nf_solucao': solucao.data_nf_solucao.isoformat() if solucao.data_nf_solucao else None,
        'vinculacao': solucao.vinculacao,
        'score_match': solucao.score_match,
        'criado_em': solucao.criado_em.isoformat() if solucao.criado_em else None,
        'criado_por': solucao.criado_por,
        'confirmado_em': solucao.confirmado_em.isoformat() if solucao.confirmado_em else None,
        'confirmado_por': solucao.confirmado_por,
        'observacao': solucao.observacao
    })
