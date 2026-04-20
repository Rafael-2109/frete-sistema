"""Helpers para resolver papeis (emitente/destinatario/tomador) em qualquer
documento CarVia: Fatura Cliente, Fatura Transportadora, CTe Complementar.

Centraliza logica que antes estava duplicada em rotas/templates e garante
que CTe Complementar (sem emit/dest proprios) use a operacao pai como fonte.

SOT do tomador = XML do CTe (cte_tomador em CarviaOperacao). Nao ha mais
fallback FOB/CIF -> tomador (removido 2026-04-20): granularidade errada e
cobertura parcial das 5 categorias SEFAZ.

Todos os helpers retornam dicionarios com a mesma estrutura:
    {
        'emit': {'nome', 'cnpj', 'cidade', 'uf'} | None,
        'dest': {'nome', 'cnpj', 'cidade', 'uf'} | None,
        'tomador': {'codigo', 'label_visual', 'label_completo'} | None,
        'origem': str  # 'operacao' | 'cte_comp_pai' | 'subcontrato'
    }

O template consome via macro `emitente_destinatario_v2` em _macros.html.
"""

from app import db
from app.carvia.utils.tomador import resolver_tomador


# ---------------------------------------------------------------------- #
#  Funcoes single-record (usadas em paginas de detalhe)
# ---------------------------------------------------------------------- #

def _nf_para_papel(nf, papel):
    """Converte CarviaNf em dict do lado emit ou dest."""
    if nf is None:
        return None
    if papel == 'emit':
        return {
            'nome': nf.nome_emitente,
            'cnpj': nf.cnpj_emitente,
            'cidade': nf.cidade_emitente,
            'uf': nf.uf_emitente,
        }
    return {
        'nome': nf.nome_destinatario,
        'cnpj': nf.cnpj_destinatario,
        'cidade': nf.cidade_destinatario,
        'uf': nf.uf_destinatario,
    }


def _primeira_nf_da_operacao(operacao):
    """Retorna primeira CarviaNf vinculada a uma operacao, ou None."""
    if operacao is None:
        return None
    try:
        return operacao.nfs.first()
    except Exception:
        return None


def resolver_papeis_operacao(operacao):
    """Papeis a partir de uma CarviaOperacao: primeira NF + cte_tomador."""
    if operacao is None:
        return None
    primeira_nf = _primeira_nf_da_operacao(operacao)
    emit = _nf_para_papel(primeira_nf, 'emit')
    dest = _nf_para_papel(primeira_nf, 'dest')
    tomador = resolver_tomador(getattr(operacao, 'cte_tomador', None))
    if emit is None and dest is None and tomador is None:
        return None
    return {
        'emit': emit,
        'dest': dest,
        'tomador': tomador,
        'origem': 'operacao',
    }


def resolver_papeis_cte_complementar(cte_comp):
    """Papeis de CTe Complementar via operacao pai."""
    if cte_comp is None or cte_comp.operacao is None:
        return None
    papeis = resolver_papeis_operacao(cte_comp.operacao)
    if papeis:
        papeis['origem'] = 'cte_comp_pai'
    return papeis


def resolver_papeis_fatura_cliente(fatura):
    """Papeis de Fatura Cliente (single-record, sem N+1)."""
    if fatura is None:
        return None
    resultado = batch_papeis_por_fatura_cliente([fatura.id])
    return resultado.get(fatura.id)


def resolver_papeis_fatura_transportadora(fatura):
    """Papeis de Fatura Transportadora (single-record, sem N+1)."""
    if fatura is None:
        return None
    resultado = batch_papeis_por_fatura_transportadora([fatura.id])
    return resultado.get(fatura.id)


# ---------------------------------------------------------------------- #
#  Funcoes batch (usadas em listagens e exports para evitar N+1)
# ---------------------------------------------------------------------- #

def _row_to_papel(emit_nome, emit_cnpj, emit_cidade, emit_uf,
                  dest_nome, dest_cnpj, dest_cidade, dest_uf):
    """Converte row de query em par emit/dest."""
    emit = None
    if emit_nome or emit_cnpj:
        emit = {
            'nome': emit_nome,
            'cnpj': emit_cnpj,
            'cidade': emit_cidade,
            'uf': emit_uf,
        }
    dest = None
    if dest_nome or dest_cnpj:
        dest = {
            'nome': dest_nome,
            'cnpj': dest_cnpj,
            'cidade': dest_cidade,
            'uf': dest_uf,
        }
    return emit, dest


def batch_papeis_por_fatura_cliente(fatura_ids):
    """Batch papeis para lista de Faturas Cliente.

    Resolve via 2 joins:
    1. fatura -> operacao -> OperacaoNf -> Nf (primeira NF + cte_tomador)
    2. fatura -> CteComplementar -> operacao -> OperacaoNf -> Nf (fallback)

    SEM fallback FOB/CIF: se operacao nao tem cte_tomador nem NF, a fatura
    fica sem papeis e a UI exibe vazio (correto — SOT e o CTe).

    Args:
        fatura_ids: iteravel de ids

    Returns:
        {fatura_id: papeis_dict}
    """
    from app.carvia.models import (
        CarviaCteComplementar, CarviaNf, CarviaOperacao, CarviaOperacaoNf,
    )

    fatura_ids = list(fatura_ids or [])
    if not fatura_ids:
        return {}

    resultado = {}

    # 1. Via operacoes diretas. ORDER BY garante determinismo do "primeira NF wins"
    rows_op = db.session.query(
        CarviaOperacao.fatura_cliente_id,
        CarviaOperacao.cte_tomador,
        CarviaNf.nome_emitente, CarviaNf.cnpj_emitente,
        CarviaNf.cidade_emitente, CarviaNf.uf_emitente,
        CarviaNf.nome_destinatario, CarviaNf.cnpj_destinatario,
        CarviaNf.cidade_destinatario, CarviaNf.uf_destinatario,
    ).join(
        CarviaOperacaoNf, CarviaOperacaoNf.operacao_id == CarviaOperacao.id
    ).join(
        CarviaNf, CarviaNf.id == CarviaOperacaoNf.nf_id
    ).filter(
        CarviaOperacao.fatura_cliente_id.in_(fatura_ids)
    ).order_by(
        CarviaOperacao.fatura_cliente_id,
        CarviaOperacao.id,
        CarviaNf.id,
    ).all()

    for row in rows_op:
        (fid, cte_tom,
         emit_nome, emit_cnpj, emit_cidade, emit_uf,
         dest_nome, dest_cnpj, dest_cidade, dest_uf) = row
        emit, dest = _row_to_papel(
            emit_nome, emit_cnpj, emit_cidade, emit_uf,
            dest_nome, dest_cnpj, dest_cidade, dest_uf,
        )
        existente = resultado.get(fid)
        if existente is None:
            resultado[fid] = {
                'emit': emit, 'dest': dest,
                'tomador': resolver_tomador(cte_tom),
                'origem': 'operacao',
            }
        else:
            # Atualiza tomador se ainda nao resolveu e este tem cte_tomador
            if existente['tomador'] is None and cte_tom:
                existente['tomador'] = resolver_tomador(cte_tom)

    # 2. Fallback via CTe Complementares (so para faturas ainda sem papeis)
    faturas_sem_papeis = [fid for fid in fatura_ids if fid not in resultado]
    if faturas_sem_papeis:
        rows_comp = db.session.query(
            CarviaCteComplementar.fatura_cliente_id,
            CarviaOperacao.cte_tomador,
            CarviaNf.nome_emitente, CarviaNf.cnpj_emitente,
            CarviaNf.cidade_emitente, CarviaNf.uf_emitente,
            CarviaNf.nome_destinatario, CarviaNf.cnpj_destinatario,
            CarviaNf.cidade_destinatario, CarviaNf.uf_destinatario,
        ).join(
            CarviaOperacao, CarviaOperacao.id == CarviaCteComplementar.operacao_id
        ).join(
            CarviaOperacaoNf, CarviaOperacaoNf.operacao_id == CarviaOperacao.id
        ).join(
            CarviaNf, CarviaNf.id == CarviaOperacaoNf.nf_id
        ).filter(
            CarviaCteComplementar.fatura_cliente_id.in_(faturas_sem_papeis)
        ).order_by(
            CarviaCteComplementar.fatura_cliente_id,
            CarviaCteComplementar.id,
            CarviaNf.id,
        ).all()

        for row in rows_comp:
            (fid, cte_tom,
             emit_nome, emit_cnpj, emit_cidade, emit_uf,
             dest_nome, dest_cnpj, dest_cidade, dest_uf) = row
            if fid in resultado:
                continue
            emit, dest = _row_to_papel(
                emit_nome, emit_cnpj, emit_cidade, emit_uf,
                dest_nome, dest_cnpj, dest_cidade, dest_uf,
            )
            resultado[fid] = {
                'emit': emit, 'dest': dest,
                'tomador': resolver_tomador(cte_tom),
                'origem': 'cte_comp_pai',
            }

    return resultado


def batch_papeis_por_fatura_transportadora(fatura_ids):
    """Batch papeis para Faturas Transportadora.

    fatura_transp -> subcontrato -> operacao -> OperacaoNf -> Nf.
    Tomador vem diretamente de CarviaOperacao.cte_tomador (SOT).
    """
    from app.carvia.models import (
        CarviaNf, CarviaOperacao, CarviaOperacaoNf, CarviaSubcontrato,
    )

    fatura_ids = list(fatura_ids or [])
    if not fatura_ids:
        return {}

    rows = db.session.query(
        CarviaSubcontrato.fatura_transportadora_id,
        CarviaOperacao.cte_tomador,
        CarviaNf.nome_emitente, CarviaNf.cnpj_emitente,
        CarviaNf.cidade_emitente, CarviaNf.uf_emitente,
        CarviaNf.nome_destinatario, CarviaNf.cnpj_destinatario,
        CarviaNf.cidade_destinatario, CarviaNf.uf_destinatario,
    ).join(
        CarviaOperacao, CarviaOperacao.id == CarviaSubcontrato.operacao_id
    ).join(
        CarviaOperacaoNf, CarviaOperacaoNf.operacao_id == CarviaOperacao.id
    ).join(
        CarviaNf, CarviaNf.id == CarviaOperacaoNf.nf_id
    ).filter(
        CarviaSubcontrato.fatura_transportadora_id.in_(fatura_ids)
    ).order_by(
        CarviaSubcontrato.fatura_transportadora_id,
        CarviaSubcontrato.id,
        CarviaNf.id,
    ).all()

    resultado = {}
    for row in rows:
        (fid, cte_tom,
         emit_nome, emit_cnpj, emit_cidade, emit_uf,
         dest_nome, dest_cnpj, dest_cidade, dest_uf) = row
        emit, dest = _row_to_papel(
            emit_nome, emit_cnpj, emit_cidade, emit_uf,
            dest_nome, dest_cnpj, dest_cidade, dest_uf,
        )
        existente = resultado.get(fid)
        if existente is None:
            resultado[fid] = {
                'emit': emit, 'dest': dest,
                'tomador': resolver_tomador(cte_tom),
                'origem': 'subcontrato',
            }
        else:
            if existente['tomador'] is None and cte_tom:
                existente['tomador'] = resolver_tomador(cte_tom)
    return resultado


def batch_papeis_por_cte_complementar(cte_comp_ids):
    """Batch papeis para CTes Complementares via operacao pai -> NFs."""
    from app.carvia.models import (
        CarviaCteComplementar, CarviaNf, CarviaOperacao, CarviaOperacaoNf,
    )

    cte_comp_ids = list(cte_comp_ids or [])
    if not cte_comp_ids:
        return {}

    rows = db.session.query(
        CarviaCteComplementar.id,
        CarviaOperacao.cte_tomador,
        CarviaNf.nome_emitente, CarviaNf.cnpj_emitente,
        CarviaNf.cidade_emitente, CarviaNf.uf_emitente,
        CarviaNf.nome_destinatario, CarviaNf.cnpj_destinatario,
        CarviaNf.cidade_destinatario, CarviaNf.uf_destinatario,
    ).join(
        CarviaOperacao, CarviaOperacao.id == CarviaCteComplementar.operacao_id
    ).join(
        CarviaOperacaoNf, CarviaOperacaoNf.operacao_id == CarviaOperacao.id
    ).join(
        CarviaNf, CarviaNf.id == CarviaOperacaoNf.nf_id
    ).filter(
        CarviaCteComplementar.id.in_(cte_comp_ids)
    ).order_by(
        CarviaCteComplementar.id,
        CarviaNf.id,
    ).all()

    resultado = {}
    for row in rows:
        (cid, cte_tom,
         emit_nome, emit_cnpj, emit_cidade, emit_uf,
         dest_nome, dest_cnpj, dest_cidade, dest_uf) = row
        if cid in resultado:
            existente = resultado[cid]
            if existente['tomador'] is None and cte_tom:
                existente['tomador'] = resolver_tomador(cte_tom)
            continue
        emit, dest = _row_to_papel(
            emit_nome, emit_cnpj, emit_cidade, emit_uf,
            dest_nome, dest_cnpj, dest_cidade, dest_uf,
        )
        resultado[cid] = {
            'emit': emit, 'dest': dest,
            'tomador': resolver_tomador(cte_tom),
            'origem': 'cte_comp_pai',
        }
    return resultado
