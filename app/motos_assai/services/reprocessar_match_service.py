"""Reprocessamento automatico de match NF Q.P.A. apos mudanca em fonte de dados.

Contexto: ate 2026-05-17 o match Q.P.A. era one-shot na importacao da NF
(`nf_qpa_adapter._calcular_match`). Quando a fonte mudava (cadastro de
chassi, criacao de loja, cancelamento de separacao, etc.), divergencias
antigas persistiam sem reavaliacao.

Este service introduz:
  1. `reprocessar_match_nf(nf_id, motivo, operador_id)` — re-roda o match
     em UMA NF com reset previo de estado.
  2. `reprocessar_match_nfs(nf_ids, motivo, operador_id)` — batch helper
     resiliente (commit por NF).
  3. Helpers `nfs_afetadas_por_*` — queries para identificar quais NFs
     reprocessar a partir de uma mudanca especifica.

Padrao de uso (hook nos services que modificam fonte):

    # exemplo: apos cadastrar chassi via recibo
    from app.motos_assai.services.reprocessar_match_service import (
        reprocessar_match_nfs, nfs_afetadas_por_chassi,
    )
    nf_ids = nfs_afetadas_por_chassi(item.chassi)
    if nf_ids:
        reprocessar_match_nfs(nf_ids, motivo='CHASSI_CADASTRADO',
                              operador_id=operador_id)

PADRAO DE INTEGRACAO:
  - SINCRONO (commit dentro do mesmo request do caller).
  - IDEMPOTENTE: re-rodar 2x = mesmo resultado se nada mudou.
  - LOCK PESSIMISTA por NF (with_for_update).
  - EARLY-RETURN em NF CANCELADA.
  - NAO entra em loop: hooks chamam ESTE service, ESTE service nao chama
    de volta a logica de service que tem hook (apenas `_calcular_match`,
    que e funcao pura sem efeitos cascata).

LIMITACOES CONHECIDAS (MVP 2026-05-17):
  - NAO reverte sep.status (se NF era BATEU e fica DIVERGENTE, sep continua
    FATURADA mesmo sem NF apontando). Operador resolve manualmente.
  - NAO desfaz eventos FATURADA dos chassis (eventos append-only). Status
    efetivo do chassi continuara FATURADA mesmo apos NF perder match.

CALLSITES (mapeamento 2026-05-17 — investigar antes de adicionar novo hook):
  - C1: recebimento_service.registrar_conferencia → criacao AssaiMoto
  - B2: separacao_service.cancelar_separacao
  - B3: separacao_service.reabrir_separacao
  - B4: separacao_service.desfazer_chassi
  - B5: separacao_service.substituir_chassi_entre_seps (via_divergencia=False)
  - B1: separacao_service.criar_separacao_com_saldos
  - B8: carregamento_service.alterar_carregamento
  - A1: loja_service.atualizar_loja
  - A2: loja_service.criar_loja
  - F1: modelo_service.atualizar_modelo

JA TRATADOS HOJE (NAO adicionar hook):
  - cce_service.aplicar_correcao_cce → chama _calcular_match
  - divergencia_service.resolver_divergencia → chama _calcular_match
  - nf_qpa_adapter.vincular_nf_manualmente → chama _calcular_match
  - cancelamento_nf_service.cancelar_nf_qpa → NF vira CANCELADA (early-return)
"""

from __future__ import annotations

import logging
from typing import Optional

from app import db
from app.utils.cnpj_utils import normalizar_cnpj
from app.utils.timezone import agora_brasil_naive


logger = logging.getLogger(__name__)


MOTIVO_DEFAULT = 'REPROCESSAMENTO_AUTOMATICO'
MOTIVO_HOOK_LOJA_ATUALIZADA = 'HOOK_LOJA_ATUALIZADA'
MOTIVO_HOOK_LOJA_CRIADA = 'HOOK_LOJA_CRIADA'
MOTIVO_HOOK_MODELO_ATUALIZADO = 'HOOK_MODELO_ATUALIZADO'
MOTIVO_HOOK_CHASSI_CADASTRADO = 'HOOK_CHASSI_CADASTRADO'
MOTIVO_HOOK_SEP_CANCELADA = 'HOOK_SEP_CANCELADA'
MOTIVO_HOOK_SEP_REABERTA = 'HOOK_SEP_REABERTA'
MOTIVO_HOOK_SEP_CRIADA = 'HOOK_SEP_CRIADA'
MOTIVO_HOOK_SEP_ITEM_REMOVIDO = 'HOOK_SEP_ITEM_REMOVIDO'
MOTIVO_HOOK_SEP_SUBSTITUICAO_CHASSI = 'HOOK_SEP_SUBSTITUICAO_CHASSI'
MOTIVO_HOOK_CARREGAMENTO_ALTERADO = 'HOOK_CARREGAMENTO_ALTERADO'


# ─── core ─────────────────────────────────────────────────────────────────────

def reprocessar_match_nf(
    nf_id: int,
    motivo: str = MOTIVO_DEFAULT,
    operador_id: Optional[int] = None,
    *,
    commit: bool = True,
) -> dict:
    """Re-roda `_calcular_match` em UMA NF apos reset de estado.

    Args:
        nf_id: ID da AssaiNfQpa.
        motivo: rastreabilidade ('HOOK_LOJA_ATUALIZADA', etc).
        operador_id: para eventos emitidos por `_calcular_match`. None = 1.
        commit: se True, commita antes de retornar. Se False, caller decide.

    Returns:
        {
            'nf_id': int,
            'status_anterior': str | None,
            'status_novo': str | None,
            'divergencias_resolvidas': int,
            'motivo': str,
            'skipped': bool,
            'reason': str | None,
        }
    """
    from app.motos_assai.models import (
        AssaiNfQpa, AssaiDivergencia,
        NF_STATUS_BATEU, NF_STATUS_CANCELADA,
        DIVERGENCIA_RESOLUCAO_IGNORAR,
    )
    from app.motos_assai.services.parsers.nf_qpa_adapter import _calcular_match

    # `with_for_update(of=AssaiNfQpa)` qualifica o lock apenas na tabela alvo
    # — sem isso, lazy='joined' propaga FOR UPDATE para os LEFT JOINs (separacao,
    # loja, etc.) violando "FOR UPDATE cannot be applied to the nullable side
    # of an outer join". Mesmo padrao usado em recebimento_service:200-208.
    nf = (
        db.session.query(AssaiNfQpa)
        .filter(AssaiNfQpa.id == nf_id)
        .with_for_update(of=AssaiNfQpa)
        .first()
    )
    if not nf:
        logger.warning('reprocessar_match_nf: NF %s nao encontrada', nf_id)
        return {
            'nf_id': nf_id, 'status_anterior': None, 'status_novo': None,
            'divergencias_resolvidas': 0, 'motivo': motivo,
            'skipped': True, 'reason': 'not_found',
        }

    status_anterior = nf.status_match

    if status_anterior == NF_STATUS_CANCELADA:
        logger.info('reprocessar_match_nf: NF %s CANCELADA — SKIP', nf_id)
        return {
            'nf_id': nf_id, 'status_anterior': status_anterior,
            'status_novo': status_anterior, 'divergencias_resolvidas': 0,
            'motivo': motivo, 'skipped': True, 'reason': 'nf_cancelada',
        }

    # Se NF nao tem loja_id e tem CNPJ destinatario, tenta resolver loja
    # antes do match (mesma logica de `importar_nf_qpa:79-118` — CNPJ primeiro,
    # regex LJ como fallback). Sem isso, hooks A1/A2 nao teriam efeito real:
    # _calcular_match nao resolve loja_id, so valida match item-por-item.
    if not nf.loja_id:
        _resolver_loja_id_da_nf(nf)

    # Se NF era BATEU + tinha separacao_id, REGREDIR a sep para FECHADA antes
    # do reset. Sem isso, `_calcular_match` filtra sep FATURADA fora do JOIN
    # e nao acha mais match — NF vira NAO_RECONCILIADO mesmo sem motivo real.
    # Cuidado: so regride se NAO houver outras NFs vinculadas (BATEU/DIVERGENTE).
    if status_anterior == NF_STATUS_BATEU and nf.separacao_id:
        from app.motos_assai.models import (
            AssaiSeparacao, SEPARACAO_STATUS_FATURADA, SEPARACAO_STATUS_FECHADA,
            NF_STATUS_BATEU as _BATEU, NF_STATUS_DIVERGENTE as _DIV,
        )
        sep_alvo = AssaiSeparacao.query.get(nf.separacao_id)
        if sep_alvo and sep_alvo.status == SEPARACAO_STATUS_FATURADA:
            outras_nfs = (
                AssaiNfQpa.query
                .filter(
                    AssaiNfQpa.separacao_id == sep_alvo.id,
                    AssaiNfQpa.id != nf.id,
                    AssaiNfQpa.status_match.in_([_BATEU, _DIV]),
                )
                .count()
            )
            if outras_nfs == 0:
                sep_alvo.status = SEPARACAO_STATUS_FECHADA
                logger.debug(
                    'reprocessar_match_nf NF %s: sep %s regredida FATURADA -> '
                    'FECHADA para permitir re-match',
                    nf_id, sep_alvo.id,
                )

    for item in nf.itens:
        item.separacao_item_id = None
        item.tipo_divergencia = None
    nf.separacao_id = None

    divs_abertas = (
        AssaiDivergencia.query
        .filter_by(nf_id=nf_id)
        .filter(AssaiDivergencia.resolvida_em.is_(None))
        .all()
    )
    for div in divs_abertas:
        div.resolvida_em = agora_brasil_naive()
        div.resolvida_por_id = operador_id
        div.tipo_resolucao = DIVERGENCIA_RESOLUCAO_IGNORAR
        div.observacao_resolucao = (
            f'Resolvida via reprocessamento automatico (motivo={motivo})'
        )

    try:
        _calcular_match(nf, operador_id or 1)
    except Exception:
        db.session.rollback()
        logger.exception('reprocessar_match_nf NF %s falhou', nf_id)
        raise

    status_novo = nf.status_match

    if commit:
        db.session.commit()

    if status_anterior != status_novo:
        logger.info(
            'reprocessar_match_nf NF %s: %s -> %s (motivo=%s, divs resolvidas=%d)',
            nf_id, status_anterior, status_novo, motivo, len(divs_abertas),
        )

    return {
        'nf_id': nf_id,
        'status_anterior': status_anterior,
        'status_novo': status_novo,
        'divergencias_resolvidas': len(divs_abertas),
        'motivo': motivo,
        'skipped': False,
        'reason': None,
    }


def reprocessar_match_nfs(
    nf_ids: list[int],
    motivo: str = MOTIVO_DEFAULT,
    operador_id: Optional[int] = None,
) -> dict:
    """Batch helper resiliente (commit por NF).

    Erro em uma NF NAO interrompe as demais. Cada NF e commitada
    independentemente — caller nao precisa gerenciar transaction.
    """
    stats = {
        'total': len(nf_ids), 'ok': 0, 'skipped': 0, 'erro': 0,
        'mudou_status': 0, 'motivo': motivo, 'detalhes': [],
    }
    for nf_id in nf_ids:
        try:
            r = reprocessar_match_nf(
                nf_id, motivo=motivo, operador_id=operador_id, commit=True,
            )
            if r.get('skipped'):
                stats['skipped'] += 1
            else:
                stats['ok'] += 1
                if r.get('status_anterior') != r.get('status_novo'):
                    stats['mudou_status'] += 1
            stats['detalhes'].append(r)
        except Exception as e:
            stats['erro'] += 1
            stats['detalhes'].append({
                'nf_id': nf_id, 'erro': f'{type(e).__name__}: {e}',
            })
            logger.error('reprocessar_match_nfs NF %s erro: %s', nf_id, e)

    if stats['mudou_status'] or stats['ok'] or stats['erro']:
        logger.info(
            'reprocessar_match_nfs[%s]: total=%d ok=%d mudou=%d skipped=%d erro=%d',
            motivo, stats['total'], stats['ok'], stats['mudou_status'],
            stats['skipped'], stats['erro'],
        )
    return stats


# ─── helpers internos ─────────────────────────────────────────────────────────

def _resolver_loja_id_da_nf(nf) -> None:
    """Resolve loja_id de uma NF via CNPJ destinatario ou regex nome.

    Reusa a logica de `nf_qpa_adapter.importar_nf_qpa:79-125` (P0 commit
    848b992a). Necessario aqui porque `_calcular_match` valida match
    item-por-item mas NAO resolve loja_id da NF.

    Modifica `nf.loja_id` in-place. NAO commita.
    """
    import re
    from app.motos_assai.models import AssaiLoja

    nome_dest = nf.destinatario_nome or ''
    cnpj_dest = nf.destinatario_cnpj or ''

    if cnpj_dest:
        cnpj_norm = normalizar_cnpj(cnpj_dest)
        if cnpj_norm:
            todas_lojas = AssaiLoja.query.filter_by(ativo=True).all()
            lojas_match = [
                ll for ll in todas_lojas
                if normalizar_cnpj(ll.cnpj) == cnpj_norm
            ]
            if len(lojas_match) == 1:
                nf.loja_id = lojas_match[0].id
                return

    loja_match = re.search(r'LJ\s*(\d+)', nome_dest)
    if loja_match:
        loja = AssaiLoja.query.filter_by(numero=loja_match.group(1)).first()
        if loja:
            nf.loja_id = loja.id


# ─── helpers de identificacao ─────────────────────────────────────────────────

def nfs_afetadas_por_separacao(sep_id: int) -> list[int]:
    """NFs vinculadas a uma separacao (direta ou via item)."""
    from app.motos_assai.models import (
        AssaiNfQpa, AssaiNfQpaItem, AssaiSeparacaoItem, NF_STATUS_CANCELADA,
    )
    nfs_diretas = (
        db.session.query(AssaiNfQpa.id)
        .filter(
            AssaiNfQpa.separacao_id == sep_id,
            AssaiNfQpa.status_match != NF_STATUS_CANCELADA,
        )
        .all()
    )
    nfs_via_item = (
        db.session.query(AssaiNfQpa.id)
        .join(AssaiNfQpaItem, AssaiNfQpaItem.nf_id == AssaiNfQpa.id)
        .join(
            AssaiSeparacaoItem,
            AssaiSeparacaoItem.id == AssaiNfQpaItem.separacao_item_id,
        )
        .filter(
            AssaiSeparacaoItem.separacao_id == sep_id,
            AssaiNfQpa.status_match != NF_STATUS_CANCELADA,
        )
        .all()
    )
    return sorted({n[0] for n in nfs_diretas} | {n[0] for n in nfs_via_item})


def nfs_afetadas_por_chassi(chassi: str) -> list[int]:
    """NFs com algum AssaiNfQpaItem.chassi == X (qualquer status menos CANCELADA)."""
    from app.motos_assai.models import (
        AssaiNfQpa, AssaiNfQpaItem, NF_STATUS_CANCELADA,
    )
    if not chassi:
        return []
    chassi_norm = chassi.strip().upper()
    rows = (
        db.session.query(AssaiNfQpa.id)
        .join(AssaiNfQpaItem, AssaiNfQpaItem.nf_id == AssaiNfQpa.id)
        .filter(
            AssaiNfQpaItem.chassi == chassi_norm,
            AssaiNfQpa.status_match != NF_STATUS_CANCELADA,
        )
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


def nfs_afetadas_por_chassis(chassis: list[str]) -> list[int]:
    """Variante em batch — N chassis em uma query."""
    from app.motos_assai.models import (
        AssaiNfQpa, AssaiNfQpaItem, NF_STATUS_CANCELADA,
    )
    if not chassis:
        return []
    chassis_norm = [c.strip().upper() for c in chassis if c]
    if not chassis_norm:
        return []
    rows = (
        db.session.query(AssaiNfQpa.id)
        .join(AssaiNfQpaItem, AssaiNfQpaItem.nf_id == AssaiNfQpa.id)
        .filter(
            AssaiNfQpaItem.chassi.in_(chassis_norm),
            AssaiNfQpa.status_match != NF_STATUS_CANCELADA,
        )
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


def nfs_afetadas_por_loja(
    loja_id: int, cnpj_antigo: Optional[str] = None,
) -> list[int]:
    """NFs vinculadas a loja (direta ou via CNPJ destinatario).

    Combina:
      1. NFs com `loja_id == X` (qualquer status menos CANCELADA)
      2. NFs com `loja_id IS NULL` em NAO_RECONCILIADO cujo `destinatario_cnpj`
         casa com o CNPJ atual da loja OU com `cnpj_antigo` (se fornecido —
         usado quando o CNPJ foi alterado e queremos NFs que antes nao casavam).
    """
    from app.motos_assai.models import (
        AssaiNfQpa, AssaiLoja, NF_STATUS_CANCELADA, NF_STATUS_NAO_RECONCILIADO,
    )

    nf_ids: set[int] = set()

    q1 = (
        db.session.query(AssaiNfQpa.id)
        .filter(
            AssaiNfQpa.loja_id == loja_id,
            AssaiNfQpa.status_match != NF_STATUS_CANCELADA,
        )
        .all()
    )
    nf_ids.update(r[0] for r in q1)

    cnpjs_a_casar: set[str] = set()
    loja = AssaiLoja.query.get(loja_id)
    if loja and loja.cnpj:
        n = normalizar_cnpj(loja.cnpj)
        if n:
            cnpjs_a_casar.add(n)
    if cnpj_antigo:
        n = normalizar_cnpj(cnpj_antigo)
        if n:
            cnpjs_a_casar.add(n)

    if cnpjs_a_casar:
        all_nfs_nulas = (
            AssaiNfQpa.query
            .filter(
                AssaiNfQpa.loja_id.is_(None),
                AssaiNfQpa.status_match == NF_STATUS_NAO_RECONCILIADO,
                AssaiNfQpa.destinatario_cnpj.isnot(None),
            )
            .all()
        )
        for nf in all_nfs_nulas:
            cn = normalizar_cnpj(nf.destinatario_cnpj)
            if cn and cn in cnpjs_a_casar:
                nf_ids.add(nf.id)

    return sorted(nf_ids)


def nfs_afetadas_por_cnpj_novo(cnpj: str) -> list[int]:
    """NFs com loja_id NULL em NAO_RECONCILIADO cujo CNPJ destinatario casa.

    Usado por hook `criar_loja` — uma loja nova com CNPJ pode resolver
    NFs antigas que ate entao nao casavam por nao haver loja cadastrada.
    """
    from app.motos_assai.models import (
        AssaiNfQpa, NF_STATUS_NAO_RECONCILIADO,
    )
    n_alvo = normalizar_cnpj(cnpj or '')
    if not n_alvo:
        return []

    all_nfs_nulas = (
        AssaiNfQpa.query
        .filter(
            AssaiNfQpa.loja_id.is_(None),
            AssaiNfQpa.status_match == NF_STATUS_NAO_RECONCILIADO,
            AssaiNfQpa.destinatario_cnpj.isnot(None),
        )
        .all()
    )
    nf_ids: list[int] = []
    for nf in all_nfs_nulas:
        cn = normalizar_cnpj(nf.destinatario_cnpj)
        if cn and cn == n_alvo:
            nf_ids.append(nf.id)
    return nf_ids


def nfs_afetadas_por_modelo(modelo_id: int) -> list[int]:
    """NFs com chassis cujo AssaiMoto.modelo_id == X.

    Hook de modelo: alteracao em codigo/descricao_qpa/regex pode afetar
    `resolver_modelo` no `_calcular_match` (validacao MODELO_DIVERGENTE).
    """
    from app.motos_assai.models import (
        AssaiNfQpa, AssaiNfQpaItem, AssaiMoto, NF_STATUS_CANCELADA,
    )
    rows = (
        db.session.query(AssaiNfQpa.id)
        .join(AssaiNfQpaItem, AssaiNfQpaItem.nf_id == AssaiNfQpa.id)
        .join(AssaiMoto, AssaiMoto.chassi == AssaiNfQpaItem.chassi)
        .filter(
            AssaiMoto.modelo_id == modelo_id,
            AssaiNfQpa.status_match != NF_STATUS_CANCELADA,
        )
        .distinct()
        .all()
    )
    return [r[0] for r in rows]
