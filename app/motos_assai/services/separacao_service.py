"""Separação por (pedido × loja). Fungível por modelo.

Estados:
- EM_SEPARACAO: criada e aceita novos chassis
- FECHADA: operador clicou Finalizar (saldo zero ou parcial)
- FATURADA: NF Q.P.A. importada e bateu
- CANCELADA: cancelada pelo operador (chassis devolvidos via novo evento DISPONIVEL)
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from app import db
from app.motos_assai.models import (
    AssaiSeparacao, AssaiSeparacaoItem, AssaiPedidoVenda, AssaiPedidoVendaItem,
    AssaiMoto, AssaiModelo,
    AssaiNfQpa, AssaiPedidoExcel,
    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
    SEPARACAO_STATUS_CANCELADA, SEPARACAO_STATUS_FATURADA,
    SEPARACAO_STATUS_CARREGADA,
    EVENTO_DISPONIVEL, EVENTO_SEPARADA, EVENTO_FATURADA,
    NF_STATUS_CANCELADA,
    DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo


class SeparacaoError(Exception):
    """Erro base de separacao_service."""


class SeparacaoConflictError(SeparacaoError):
    """Race ao reservar chassi (UNIQUE parcial)."""


class SeparacaoValidationError(SeparacaoError):
    pass


class SeparacaoCrossLojaError(SeparacaoError):
    """Chassi esta em sep ativa de outra loja — operador deve confirmar substituicao.

    Levantada por `registrar_chassi` quando detecta que o chassi escaneado ja
    pertence a uma sep EM_SEPARACAO/FECHADA/CARREGADA/FATURADA de outra loja.
    Route AJAX deve traduzir para HTTP 409 com cenario=cross_loja.
    """
    def __init__(self, msg, *, sep_origem_id, loja_origem_id,
                 sep_destino_id, loja_destino_id, chassi):
        super().__init__(msg)
        self.sep_origem_id = sep_origem_id
        self.loja_origem_id = loja_origem_id
        self.sep_destino_id = sep_destino_id
        self.loja_destino_id = loja_destino_id
        self.chassi = chassi


# ─── helpers de hook reprocessar_match ────────────────────────────────────────
# Padrao: lazy import + try/except. Hook NAO pode quebrar operacao principal
# (commit ja aconteceu). Falha do hook = warning no log, segue normal.

def _hook_reprocessar_match_chassi(
    chassi: str, operador_id: int, motivo_hook: str,
) -> None:
    """Hook: reprocessa NFs que mencionam este chassi."""
    if not chassi:
        return
    try:
        from app.motos_assai.services.reprocessar_match_service import (
            reprocessar_match_nfs, nfs_afetadas_por_chassi,
        )
        nf_ids = nfs_afetadas_por_chassi(chassi)
        if nf_ids:
            reprocessar_match_nfs(
                nf_ids, motivo=motivo_hook, operador_id=operador_id,
            )
    except Exception:
        import logging as _log
        _log.getLogger(__name__).exception(
            'hook reprocessar_match (chassi=%s motivo=%s) falhou — '
            'operacao principal ja commitada',
            chassi, motivo_hook,
        )


def _hook_reprocessar_match_separacao(
    sep_id: int, operador_id: int, motivo_hook: str,
) -> None:
    """Hook: reprocessa NFs vinculadas a uma separacao."""
    if not sep_id:
        return
    try:
        from app.motos_assai.services.reprocessar_match_service import (
            reprocessar_match_nfs, nfs_afetadas_por_separacao,
        )
        nf_ids = nfs_afetadas_por_separacao(sep_id)
        if nf_ids:
            reprocessar_match_nfs(
                nf_ids, motivo=motivo_hook, operador_id=operador_id,
            )
    except Exception:
        import logging as _log
        _log.getLogger(__name__).exception(
            'hook reprocessar_match (sep=%s motivo=%s) falhou — '
            'operacao principal ja commitada',
            sep_id, motivo_hook,
        )


def _hook_reprocessar_match_chassis_em_lote(
    chassis: list, operador_id: int, motivo_hook: str,
) -> None:
    """Hook: reprocessa NFs que mencionam qualquer chassi do lote (1 query)."""
    if not chassis:
        return
    try:
        from app.motos_assai.services.reprocessar_match_service import (
            reprocessar_match_nfs, nfs_afetadas_por_chassis,
        )
        nf_ids = nfs_afetadas_por_chassis(chassis)
        if nf_ids:
            reprocessar_match_nfs(
                nf_ids, motivo=motivo_hook, operador_id=operador_id,
            )
    except Exception:
        import logging as _log
        _log.getLogger(__name__).exception(
            'hook reprocessar_match (chassis=%d motivo=%s) falhou — '
            'operacao principal ja commitada',
            len(chassis), motivo_hook,
        )


def get_separacao_ativa(pedido_id: int, loja_id: int) -> Optional[AssaiSeparacao]:
    """Retorna a AssaiSeparacao EM_SEPARACAO mais ANTIGA do par (pedido, loja).

    Retorna None se nao houver nenhuma. Esta funcao NUNCA cria registro —
    criacao explicita e responsabilidade de `criar_separacao_com_saldos`
    (chamado quando operador usa checkbox+qtd em pedidos_detalhe).

    Hist (2026-05-12): antiga `get_ou_criar_separacao` criava sep
    implicitamente quando a UI navegava para a tela de escaneio sem `?sep_id`.
    Resultado: cada visita à tela gerava sep fantasma no banco. Bug reportado
    em produção (pedido 21439695/L loja 112 ficou com 1 CANCELADA + 1
    EM_SEPARACAO vazia). Esta funcao substitui aquela — caller deve tratar
    None redirecionando para fluxo explicito de criacao.

    Apenas seps EM_SEPARACAO sao consideradas — FECHADA/FATURADA/CANCELADA
    nao reabrem chassi.
    """
    return (
        AssaiSeparacao.query
        .filter(
            AssaiSeparacao.pedido_id == pedido_id,
            AssaiSeparacao.loja_id == loja_id,
            AssaiSeparacao.status == SEPARACAO_STATUS_EM_SEPARACAO,
        )
        .order_by(AssaiSeparacao.id.asc())
        .first()
    )


def saldo_pendente_por_pedido(pedido_id: int) -> Dict[int, List[Dict[str, Any]]]:
    """Versao batch de `saldo_pendente_por_modelo` para TODAS as lojas do pedido.

    Faz 2 queries (mesma quantidade da versao single-loja) e agrupa por loja
    no Python. Usar em telas que listam todas as lojas do pedido (evita N+1
    quando ha 38+ lojas como no layout canonico Q.P.A.).

    Returns:
        {loja_id: [{modelo_id, codigo, nome, qtd_pedida, qtd_separada,
                    qtd_pendente, valor_unitario}]}.
    """
    rows = (
        db.session.query(
            AssaiPedidoVendaItem.loja_id,
            AssaiPedidoVendaItem.modelo_id,
            AssaiModelo.codigo,
            AssaiModelo.nome,
            AssaiPedidoVendaItem.qtd_pedida,
            AssaiPedidoVendaItem.valor_unitario,
        )
        .join(AssaiModelo, AssaiModelo.id == AssaiPedidoVendaItem.modelo_id)
        .filter(AssaiPedidoVendaItem.pedido_id == pedido_id)
        .order_by(AssaiPedidoVendaItem.loja_id, AssaiModelo.codigo)
        .all()
    )

    # SUM total de chassis ja separados por (loja_id, modelo_id) em TODAS as
    # seps nao-canceladas do pedido. Com N seps ativas (Migration 13), agrega.
    sums = (
        db.session.query(
            AssaiSeparacao.loja_id,
            AssaiSeparacaoItem.modelo_id,
            func.count(AssaiSeparacaoItem.id),
        )
        .join(AssaiSeparacao, AssaiSeparacao.id == AssaiSeparacaoItem.separacao_id)
        .filter(
            AssaiSeparacao.pedido_id == pedido_id,
            AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
        )
        .group_by(AssaiSeparacao.loja_id, AssaiSeparacaoItem.modelo_id)
        .all()
    )
    qtd_separada: Dict[tuple, int] = {(lid, mid): int(n) for lid, mid, n in sums}

    result: Dict[int, List[Dict[str, Any]]] = {}
    for r in rows:
        sep_qtd = qtd_separada.get((r.loja_id, r.modelo_id), 0)
        result.setdefault(r.loja_id, []).append({
            'modelo_id': r.modelo_id,
            'codigo': r.codigo,
            'nome': r.nome,
            'qtd_pedida': r.qtd_pedida,
            'qtd_separada': sep_qtd,
            'qtd_pendente': max(0, r.qtd_pedida - sep_qtd),
            'valor_unitario': r.valor_unitario,
        })
    return result


def saldo_pendente_por_modelo(pedido_id: int, loja_id: int) -> List[Dict[str, Any]]:
    """Retorna [{modelo_id, codigo, nome, qtd_pedida, qtd_separada, qtd_pendente, valor_unitario}].

    `qtd_separada` = SUM de chassis em TODAS as separacoes nao-canceladas (EM_SEPARACAO + FECHADA + FATURADA).
    `qtd_pendente` = qtd_pedida - qtd_separada (pode haver N separacoes simultaneas).

    Atualizado 2026-05-12: considera N separacoes ativas por (pedido, loja) — fluxo
    de 2+ veiculos de carregamento (Migration 13 removeu UNIQUE que limitava a 1).
    """
    rows = (
        db.session.query(
            AssaiPedidoVendaItem.modelo_id,
            AssaiModelo.codigo,
            AssaiModelo.nome,
            AssaiPedidoVendaItem.qtd_pedida,
            AssaiPedidoVendaItem.valor_unitario,
        )
        .join(AssaiModelo, AssaiModelo.id == AssaiPedidoVendaItem.modelo_id)
        .filter(
            AssaiPedidoVendaItem.pedido_id == pedido_id,
            AssaiPedidoVendaItem.loja_id == loja_id,
        )
        .order_by(AssaiModelo.codigo)
        .all()
    )

    # SUM total de chassis ja separados por modelo em TODAS as seps nao-canceladas
    # do (pedido, loja). Com N seps ativas (Migration 13), agregar.
    sums = (
        db.session.query(
            AssaiSeparacaoItem.modelo_id,
            func.count(AssaiSeparacaoItem.id),
        )
        .join(AssaiSeparacao, AssaiSeparacao.id == AssaiSeparacaoItem.separacao_id)
        .filter(
            AssaiSeparacao.pedido_id == pedido_id,
            AssaiSeparacao.loja_id == loja_id,
            AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
        )
        .group_by(AssaiSeparacaoItem.modelo_id)
        .all()
    )
    qtd_separada_por_modelo: Dict[int, int] = {mid: int(n) for mid, n in sums}

    result = []
    for r in rows:
        sep_qtd = qtd_separada_por_modelo.get(r.modelo_id, 0)
        result.append({
            'modelo_id': r.modelo_id,
            'codigo': r.codigo,
            'nome': r.nome,
            'qtd_pedida': r.qtd_pedida,
            'qtd_separada': sep_qtd,
            'qtd_pendente': max(0, r.qtd_pedida - sep_qtd),
            'valor_unitario': r.valor_unitario,
        })
    return result


def registrar_chassi(
    pedido_id: int, loja_id: int, chassi: str, registrada_por_id: int,
    separacao_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Vincula chassi à separação. Validações:

    1. Status da moto = DISPONIVEL
    2. Modelo da moto bate com algum saldo > 0 do pedido para essa loja
    3. Sep alvo (se passado) deve estar EM_SEPARACAO e pertencer a (pedido, loja)

    Args:
        separacao_id (opcional): alvo explicito. Necessario quando ha N seps
            EM_SEPARACAO simultaneas no mesmo (pedido, loja) — apos Migration 13.
            Se None, usa `get_separacao_ativa` (sep mais antiga). Se nao houver
            nenhuma sep ativa, levanta erro orientando o operador a criar via
            checkbox+qtd em pedidos_detalhe (criar_separacao_com_saldos).
    """
    chassi_norm = chassi.strip().upper()

    moto = AssaiMoto.query.filter_by(chassi=chassi_norm).with_for_update(of=AssaiMoto).first()
    if not moto:
        raise SeparacaoValidationError(f'Chassi {chassi_norm} não cadastrado')

    status = status_efetivo(chassi_norm)
    if status != EVENTO_DISPONIVEL:
        # Detectar CHASSI_OUTRA_LOJA: chassi esta em sep ativa de outra loja.
        # Permite que o operador confirme substituicao via modal (Plano 4 Task 2).
        # Se estiver em outra sep da MESMA loja, fluxo normal (erro abaixo).
        sep_outra_loja = (
            AssaiSeparacao.query
            .join(AssaiSeparacaoItem, AssaiSeparacaoItem.separacao_id == AssaiSeparacao.id)
            .filter(
                AssaiSeparacaoItem.chassi == chassi_norm,
                AssaiSeparacao.status.in_([
                    SEPARACAO_STATUS_EM_SEPARACAO,
                    SEPARACAO_STATUS_FECHADA,
                    SEPARACAO_STATUS_CARREGADA,
                    SEPARACAO_STATUS_FATURADA,
                ]),
                AssaiSeparacao.loja_id != loja_id,
            )
            .first()
        )
        if sep_outra_loja:
            raise SeparacaoCrossLojaError(
                f'Chassi {chassi_norm} esta em Sep #{sep_outra_loja.id} '
                f'(Loja {sep_outra_loja.loja_id}). '
                f'Confirme substituicao para Loja {loja_id}.',
                sep_origem_id=sep_outra_loja.id,
                loja_origem_id=sep_outra_loja.loja_id,
                sep_destino_id=separacao_id,  # pode ser None — UI escolhe alvo
                loja_destino_id=loja_id,
                chassi=chassi_norm,
            )
        raise SeparacaoValidationError(
            f'Chassi {chassi_norm} está em {status}, esperado DISPONIVEL'
        )

    # Saldo: encontrar item do pedido com modelo bate
    saldos = saldo_pendente_por_modelo(pedido_id, loja_id)
    saldo_modelo = next(
        (s for s in saldos if s['modelo_id'] == moto.modelo_id and s['qtd_pendente'] > 0),
        None,
    )
    if not saldo_modelo:
        raise SeparacaoValidationError(
            f'Modelo {moto.modelo.codigo} sem saldo pendente para esta loja '
            '(ou modelo não pertence ao pedido)'
        )

    # Sep alvo: explicito (Plano 5 — N seps simultaneas) ou fallback get_ou_criar
    if separacao_id:
        sep = AssaiSeparacao.query.get(separacao_id)
        if not sep:
            raise SeparacaoValidationError(
                f'Separação {separacao_id} nao encontrada'
            )
        if sep.pedido_id != pedido_id or sep.loja_id != loja_id:
            raise SeparacaoValidationError(
                f'Separação {separacao_id} pertence a outro (pedido={sep.pedido_id}, loja={sep.loja_id}) '
                f'— esperado (pedido={pedido_id}, loja={loja_id})'
            )
        if sep.status != SEPARACAO_STATUS_EM_SEPARACAO:
            raise SeparacaoValidationError(
                f'Separação {separacao_id} esta {sep.status} — apenas EM_SEPARACAO aceita chassi'
            )
    else:
        # Sem sep_id explicito — busca a EM_SEPARACAO mais antiga.
        # NAO cria mais implicitamente (regressao 2026-05-12: criava sep
        # fantasma a cada navegacao). Operador deve criar via checkbox+qtd
        # em pedidos_detalhe.
        sep = get_separacao_ativa(pedido_id, loja_id)
        if not sep:
            raise SeparacaoValidationError(
                f'Nenhuma separacao ativa para pedido {pedido_id} loja {loja_id}. '
                'Crie uma via tela do pedido (checkbox + qtd a separar).'
            )

    # Code review fix M4 (2026-05-13): savepoint isolado em vez de
    # `db.session.rollback()` global. Rollback total destruia trabalho
    # acumulado do caller (transacoes multi-step de routes).
    try:
        with db.session.begin_nested():
            item = AssaiSeparacaoItem(
                separacao_id=sep.id,
                chassi=chassi_norm,
                modelo_id=moto.modelo_id,
                valor_unitario_qpa=Decimal(str(saldo_modelo['valor_unitario'])),
                registrada_por_id=registrada_por_id,
            )
            db.session.add(item)
    except IntegrityError:
        # Savepoint reverteu apenas o INSERT — sessao continua valida
        raise SeparacaoConflictError(
            f'Chassi {chassi_norm} já em outra separação ativa'
        )

    emitir_evento(
        chassi_norm, EVENTO_SEPARADA,
        operador_id=registrada_por_id,
        dados_extras={
            'separacao_id': sep.id, 'pedido_id': pedido_id, 'loja_id': loja_id,
        },
    )

    # R4.2 (Big Bang Task 20): pedido permanece ABERTO ate primeira NF Q.P.A.
    # ser importada. A transicao para PARCIALMENTE_FATURADO/FATURADO e
    # calculada por `recalcular_status_pedido` quando chassis viram FATURADA.

    db.session.commit()
    return {
        'separacao_id': sep.id,
        'item_id': item.id,
        'chassi': chassi_norm,
        'modelo_codigo': moto.modelo.codigo,
        'cor': moto.cor,
    }


def desfazer_chassi(separacao_item_id: int, operador_id: int) -> Dict[str, Any]:
    """Remove chassi da separação ativa. Emite DISPONIVEL para o chassi voltar."""
    item = AssaiSeparacaoItem.query.get_or_404(separacao_item_id)
    sep = AssaiSeparacao.query.get(item.separacao_id)
    if sep and sep.status != SEPARACAO_STATUS_EM_SEPARACAO:
        raise SeparacaoValidationError(
            f'Separação {sep.id} está {sep.status}, não permite desfazer'
        )

    chassi = item.chassi
    db.session.delete(item)
    emitir_evento(
        chassi, EVENTO_DISPONIVEL,
        operador_id=operador_id,
        observacao='desfeito da separação',
        dados_extras={'separacao_id': sep.id if sep else None},
    )
    db.session.commit()

    # Hook B4 (2026-05-17): chassi removido da sep. NFs com `separacao_item_id`
    # apontando para o item deletado ficam com FK orfa — reprocesso resolve.
    # (defensivo — sep aqui esta em EM_SEPARACAO, baixa probabilidade de ter NF
    # vinculada, mas garante consistencia).
    _hook_reprocessar_match_chassi(
        chassi, operador_id, motivo_hook='HOOK_SEP_ITEM_REMOVIDO',
    )

    return {'chassi': chassi}


def finalizar_separacao(separacao_id: int, operador_id: int) -> AssaiSeparacao:
    sep = AssaiSeparacao.query.get_or_404(separacao_id)
    if sep.status != SEPARACAO_STATUS_EM_SEPARACAO:
        raise SeparacaoValidationError(f'Status atual: {sep.status}')

    from app.utils.timezone import agora_brasil_naive
    sep.status = SEPARACAO_STATUS_FECHADA
    sep.fechada_em = agora_brasil_naive()
    sep.fechada_por_id = operador_id

    # Espelhar para `separacao` Nacom — aparece em lista_pedidos.html via
    # VIEW pedidos Parte 1, permite Cotacao + Embarque + Frete (origem=OP_ASSAI).
    # Idempotente: skip se ja espelhada.
    #
    # CRITICAL (code review 2026-05-11):
    # - MirrorRaceError: outra transacao venceu — espelho ja existe.
    #   Tratamos como sucesso (idempotencia) e re-aplicamos o status FECHADA
    #   em transacao nova.
    # - Demais excecoes: rollback + re-raise como SeparacaoValidationError
    #   para o operador. Sem isso, FECHADA persistiria sem espelho e a
    #   separacao sumiria de lista_pedidos.html.
    try:
        from app.motos_assai.services.separacao_mirror_service import (
            mirror_assai_to_separacao, MirrorRaceError,
        )
        mirror_assai_to_separacao(sep.id)
    except MirrorRaceError:
        # Espelho ja criado por concorrencia — re-buscar a separacao
        # (sessao foi rollbackada) e re-aplicar status FECHADA.
        import logging
        logging.getLogger(__name__).info(
            'finalizar_separacao: race detectada para AssaiSeparacao %s — '
            'espelho ja existe, re-aplicando FECHADA', sep.id,
        )
        sep = AssaiSeparacao.query.get_or_404(separacao_id)
        if sep.status == SEPARACAO_STATUS_EM_SEPARACAO:
            sep.status = SEPARACAO_STATUS_FECHADA
            sep.fechada_em = agora_brasil_naive()
            sep.fechada_por_id = operador_id
        # else: outra transacao ja persistiu — idempotencia OK
    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(
            'mirror_assai_to_separacao FALHOU para AssaiSeparacao %s: %s '
            '— transacao revertida',
            sep.id, e, exc_info=True,
        )
        raise SeparacaoValidationError(
            f'Falha ao espelhar separacao em Nacom: {e}. '
            'Status nao foi alterado — tente novamente. Se persistir, '
            'verifique cadastro de peso dos modelos.'
        )

    db.session.commit()
    return sep


def cancelar_separacao(separacao_id: int, motivo: str, operador_id: int) -> AssaiSeparacao:
    """Cancela. Para cada item: emite DISPONIVEL para devolver chassi ao estoque.

    Regras:
    - FATURADA: não pode cancelar (NF já emitida — cancele a NF antes)
    - CANCELADA: já cancelada, idempotente erro
    - FECHADA, EM_SEPARACAO ou CARREGADA: pode cancelar
      (chassis voltam DISPONIVEL via novo evento; CARREGADA volta direto, sem
      passar por SEPARADA — o evento DISPONIVEL é emitido em sequência apenas)
    """
    if not motivo or len(motivo.strip()) < 3:
        raise SeparacaoValidationError('Motivo obrigatório (≥3 chars)')

    sep = AssaiSeparacao.query.get_or_404(separacao_id)
    if sep.status == SEPARACAO_STATUS_FATURADA:
        raise SeparacaoValidationError(
            f'Sep {separacao_id} esta FATURADA. Cancele a NF (cancelar_nf_qpa) antes.'
        )
    if sep.status == SEPARACAO_STATUS_CANCELADA:
        raise SeparacaoValidationError(f'Sep {separacao_id} ja CANCELADA')

    items = AssaiSeparacaoItem.query.filter_by(separacao_id=sep.id).all()
    for it in items:
        # H6: skip chassis já faturados — não reverter para DISPONIVEL
        if status_efetivo(it.chassi) == EVENTO_FATURADA:
            continue
        emitir_evento(
            it.chassi, EVENTO_DISPONIVEL,
            operador_id=operador_id,
            observacao='separacao_cancelada',
            dados_extras={'separacao_id': sep.id, 'motivo': motivo.strip()},
        )

    # Item 3 corretivo (2026-05-12): deletar AssaiSeparacaoSaldoModelo orfaos.
    # Antes, placeholders de qtd_planejada ficavam ligados a sep CANCELADA
    # como lixo arquitetural. Como sep esta sendo cancelada, o plano deixou
    # de existir conceitualmente — deletar tambem da tabela.
    saldos_deletados = AssaiSeparacaoSaldoModelo.query.filter_by(
        separacao_id=sep.id
    ).delete(synchronize_session=False)
    if saldos_deletados:
        import logging
        logging.getLogger(__name__).info(
            'cancelar_separacao: deletados %d AssaiSeparacaoSaldoModelo '
            'orfaos de sep %s', saldos_deletados, sep.id,
        )

    sep.status = SEPARACAO_STATUS_CANCELADA
    sep.motivo_cancelamento = motivo.strip()

    # Remover espelho em separacao Nacom (se existir). Se ja tem NF no
    # espelho (raro — separacao FATURADA ja foi bloqueada acima), o
    # service nega e cancelar_separacao falha — operador deve cancelar
    # a NF primeiro.
    try:
        from app.motos_assai.services.separacao_mirror_service import (
            unmirror_assai_separacao,
        )
        unmirror_assai_separacao(sep.id)
    except ValueError as e:
        # Bloqueio explicito (NF preenchida no espelho) — propaga como
        # erro de validacao para o operador
        raise SeparacaoValidationError(str(e))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(
            'Falha ao remover espelho de AssaiSeparacao %s: %s',
            sep.id, e, exc_info=True,
        )
        # Nao bloqueia o cancelamento — limpeza manual via SQL se necessario

    # Code review fix C6 / S10 (2026-05-13): chamar recalcular_status_pedido
    # defensivamente apos cancelar sep. Spec §14.2 lista cancelar_separacao
    # como callsite para "sep com chassis FATURADA cancelada (rara)".
    #
    # Cenario: sep tem chassis com evento FATURADA marooned (de outras NFs ou
    # bugs anteriores). Skip no loop linha 447-448 mantem o evento. Mas
    # recalcular_status_pedido conta items em sep com status FATURADA — sep
    # agora e CANCELADA, entao qtd_faturada pode cair, regredindo o pedido.
    try:
        from app.motos_assai.services.pedido_status_service import (
            recalcular_status_pedido,
        )
        recalcular_status_pedido(sep.pedido_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            'cancelar_separacao: recalcular_status_pedido falhou pedido=%s: %s '
            '— segue (nao bloqueia cancelamento)',
            sep.pedido_id, e,
        )

    db.session.commit()

    # Hook B2 (2026-05-17): NFs vinculadas a sep cancelada perdem a referencia.
    # Reprocesso identifica NFs com separacao_id == sep.id OU itens em
    # SeparacaoItem dessa sep, e re-roda match (ficarao NAO_RECONCILIADO ou
    # DIVERGENTE conforme cenario).
    _hook_reprocessar_match_separacao(
        sep.id, operador_id, motivo_hook='HOOK_SEP_CANCELADA',
    )

    return sep


def reabrir_separacao(separacao_id: int, operador_id: int) -> AssaiSeparacao:
    """Reabre uma sep FECHADA -> EM_SEPARACAO para permitir alteracao.

    Equivalente operacional ao botao "Alterar Separacao" da UI (decisao
    2026-05-13: separacoes FECHADAS precisam poder ser editadas quando o
    operador detecta erro pos-fechamento e antes de carregamento/NF).

    Validacoes:
    - Status atual deve ser FECHADA (EM_SEPARACAO ja editavel; CARREGADA
      ja foi para o caminhao; FATURADA tem NF emitida; CANCELADA nao volta).
    - Sep nao pode estar vinculada a Carregamento ATIVO (EM_CARREGAMENTO ou
      FINALIZADO) — operador deve cancelar/alterar Carregamento primeiro.
    - Espelho Nacom nao pode ter NF preenchida — operador deve cancelar a NF
      primeiro (`cancelar_nf_qpa`).

    Acoes:
    - Remove espelho Nacom (`unmirror_assai_separacao`) — separacao deixa de
      aparecer em lista_pedidos.html ate ser refinalizada.
    - status = EM_SEPARACAO; fechada_em / fechada_por_id zerados.
    - recalcular_status_pedido (defensivo).

    Returns:
        AssaiSeparacao: a sep com status atualizado.

    Raises:
        SeparacaoValidationError: status invalido / Carregamento ativo /
            NF preenchida no espelho.
    """
    sep = AssaiSeparacao.query.get_or_404(separacao_id)

    # 1. Status deve ser FECHADA
    if sep.status != SEPARACAO_STATUS_FECHADA:
        raise SeparacaoValidationError(
            f'Sep {separacao_id} esta {sep.status} — apenas FECHADA pode ser reaberta. '
            'EM_SEPARACAO ja e editavel; CARREGADA/FATURADA/CANCELADA nao podem voltar.'
        )

    # 2. Validar que NAO ha Carregamento ATIVO vinculado
    from app.motos_assai.models import (
        AssaiCarregamento,
        CARREGAMENTO_STATUS_EM_CARREGAMENTO, CARREGAMENTO_STATUS_FINALIZADO,
    )
    car_ativo = (
        AssaiCarregamento.query
        .filter_by(separacao_id=sep.id)
        .filter(AssaiCarregamento.status.in_([
            CARREGAMENTO_STATUS_EM_CARREGAMENTO,
            CARREGAMENTO_STATUS_FINALIZADO,
        ]))
        .first()
    )
    if car_ativo:
        raise SeparacaoValidationError(
            f'Sep {separacao_id} esta vinculada ao Carregamento #{car_ativo.id} '
            f'({car_ativo.status}). Cancele ou altere o Carregamento antes de '
            'reabrir a separacao.'
        )

    # 3. Remover espelho Nacom (bloqueia se NF preenchida)
    try:
        from app.motos_assai.services.separacao_mirror_service import (
            unmirror_assai_separacao,
        )
        unmirror_assai_separacao(sep.id)
    except ValueError as e:
        # NF preenchida no espelho — operador deve cancelar NF primeiro
        raise SeparacaoValidationError(str(e))

    # 4. FECHADA -> EM_SEPARACAO + limpar campos de fechamento
    sep.status = SEPARACAO_STATUS_EM_SEPARACAO
    sep.fechada_em = None
    sep.fechada_por_id = None

    import logging
    logging.getLogger(__name__).info(
        'reabrir_separacao: AssaiSeparacao %s revertida FECHADA -> EM_SEPARACAO '
        'pelo operador %s', sep.id, operador_id,
    )

    # 5. Recalcular status do pedido (defensivo) — sep volta a contar como
    # "em andamento" em vez de "fechada", pode regredir status do pedido
    # (FATURADO_PARCIAL -> PARCIALMENTE_FATURADO, etc.).
    try:
        from app.motos_assai.services.pedido_status_service import (
            recalcular_status_pedido,
        )
        recalcular_status_pedido(sep.pedido_id)
    except Exception as e:
        logging.getLogger(__name__).warning(
            'reabrir_separacao: recalcular_status_pedido falhou pedido=%s: %s '
            '— segue (nao bloqueia reabertura)',
            sep.pedido_id, e,
        )

    db.session.commit()

    # Hook B3 (2026-05-17): sep regredida FECHADA -> EM_SEPARACAO. NFs que
    # haviam batido com essa sep continuam BATEU mas a sep voltou a ser
    # mutavel — reprocesso garante consistencia caso UI/operador altere itens
    # apos reabertura sem cancelar a NF antes.
    _hook_reprocessar_match_separacao(
        sep.id, operador_id, motivo_hook='HOOK_SEP_REABERTA',
    )

    return sep


def listar_pares_separaveis() -> List[Dict[str, Any]]:
    """Lista pares (pedido, loja) com saldo pendente de chassis a separar.

    Retorna: [{pedido_id, pedido_numero, pedido_status,
               loja_id, loja_numero, loja_nome, loja_cidade, loja_uf,
               qtd_pedida_total, qtd_separada_total, qtd_pendente_total,
               separacao_ativa_id, separacao_ativa_status,
               modelos: [{codigo, nome, qtd_pedida, qtd_separada, qtd_pendente}]}]

    Considera apenas pedidos NAO FATURADOS / NAO CANCELADOS.
    Mostra pares que tem AO MENOS 1 modelo com qtd_pendente > 0,
    ou que ja tem separacao ATIVA (EM_SEPARACAO ou FECHADA mas nao FATURADA).
    """
    from app.motos_assai.models import AssaiLoja
    pedidos = (
        AssaiPedidoVenda.query
        .filter(AssaiPedidoVenda.status.notin_([
            'FATURADO', 'CANCELADO',
        ]))
        .order_by(AssaiPedidoVenda.criado_em.desc())
        .all()
    )
    if not pedidos:
        return []
    pedido_ids = [p.id for p in pedidos]

    itens = (
        db.session.query(
            AssaiPedidoVendaItem.pedido_id,
            AssaiPedidoVendaItem.loja_id,
            AssaiPedidoVendaItem.modelo_id,
            AssaiPedidoVendaItem.qtd_pedida,
            AssaiModelo.codigo,
            AssaiModelo.nome,
        )
        .join(AssaiModelo, AssaiModelo.id == AssaiPedidoVendaItem.modelo_id)
        .filter(AssaiPedidoVendaItem.pedido_id.in_(pedido_ids))
        .order_by(AssaiModelo.codigo)
        .all()
    )

    # Qtd ja em separacao (qualquer status != CANCELADA - CANCELADA devolve chassi)
    sep_items = (
        db.session.query(
            AssaiSeparacao.pedido_id,
            AssaiSeparacao.loja_id,
            AssaiSeparacaoItem.modelo_id,
            func.count(AssaiSeparacaoItem.id).label('qtd'),
        )
        .join(AssaiSeparacaoItem, AssaiSeparacaoItem.separacao_id == AssaiSeparacao.id)
        .filter(
            AssaiSeparacao.pedido_id.in_(pedido_ids),
            AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
        )
        .group_by(AssaiSeparacao.pedido_id, AssaiSeparacao.loja_id, AssaiSeparacaoItem.modelo_id)
        .all()
    )
    sep_map = {(r.pedido_id, r.loja_id, r.modelo_id): int(r.qtd) for r in sep_items}

    sep_ativas = (
        AssaiSeparacao.query
        .filter(
            AssaiSeparacao.pedido_id.in_(pedido_ids),
            AssaiSeparacao.status.in_([
                SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
            ]),
        )
        .order_by(AssaiSeparacao.iniciada_em.asc())
        .all()
    )
    # M1 (2026-05-12): apos Migration 13 ha N seps possiveis por (pedido, loja).
    # Lista todas em vez de dict que perde N-1. UI usa a primeira EM_SEPARACAO
    # para link compativel + count para badge.
    from collections import defaultdict
    ativa_map_lista: Dict[tuple, list] = defaultdict(list)
    for s in sep_ativas:
        ativa_map_lista[(s.pedido_id, s.loja_id)].append(s)

    lojas = AssaiLoja.query.all()
    loja_por_id = {l.id: l for l in lojas}
    pedido_por_id = {p.id: p for p in pedidos}

    pares: Dict[tuple, Dict[str, Any]] = {}
    for it in itens:
        key = (it.pedido_id, it.loja_id)
        qtd_pedida = int(it.qtd_pedida)
        qtd_sep = sep_map.get((it.pedido_id, it.loja_id, it.modelo_id), 0)
        qtd_pend = max(0, qtd_pedida - qtd_sep)
        bucket = pares.setdefault(key, {
            'pedido_id': it.pedido_id,
            'loja_id': it.loja_id,
            'qtd_pedida_total': 0,
            'qtd_separada_total': 0,
            'qtd_pendente_total': 0,
            'modelos': [],
        })
        bucket['qtd_pedida_total'] += qtd_pedida
        bucket['qtd_separada_total'] += qtd_sep
        bucket['qtd_pendente_total'] += qtd_pend
        bucket['modelos'].append({
            'modelo_id': it.modelo_id,  # Pacote A (2026-05-13): modal Iniciar precisa
            'codigo': it.codigo,
            'nome': it.nome,
            'qtd_pedida': qtd_pedida,
            'qtd_separada': qtd_sep,
            'qtd_pendente': qtd_pend,
        })

    result = []
    for (pid, lid), bucket in pares.items():
        seps_par = ativa_map_lista.get((pid, lid), [])
        # Para retrocompatibilidade da UI: separacao_ativa_id = primeira EM_SEPARACAO,
        # ou primeira FECHADA se nenhuma EM_SEPARACAO. seps_ativas_count = total.
        sep_em_separacao = next((s for s in seps_par if s.status == SEPARACAO_STATUS_EM_SEPARACAO), None)
        sep_ativa = sep_em_separacao or (seps_par[0] if seps_par else None)
        if bucket['qtd_pendente_total'] <= 0 and not sep_ativa:
            continue
        pedido = pedido_por_id.get(pid)
        loja = loja_por_id.get(lid)
        result.append({
            **bucket,
            'pedido_numero': pedido.numero if pedido else '-',
            'pedido_status': pedido.status if pedido else '-',
            'loja_numero': loja.numero if loja else '-',
            'loja_nome': loja.nome if loja else '-',
            'loja_cidade': (loja.cidade if loja else None) or '-',
            'loja_uf': (loja.uf if loja else None) or '-',
            'separacao_ativa_id': sep_ativa.id if sep_ativa else None,
            'separacao_ativa_status': sep_ativa.status if sep_ativa else None,
            'seps_ativas_count': len(seps_par),  # M1: N seps possiveis
            'seps_ativas_ids': [s.id for s in seps_par],  # M1: ids para deeplink
        })

    result.sort(key=lambda r: (
        0 if r['separacao_ativa_id'] else 1,
        r['pedido_numero'],
        r['loja_numero'],
    ))
    return result


# =====================================================================
# Realocacao de saldo ao finalizar separacao (Task #11 — 2026-05-12)
# =====================================================================
#
# Regra de negocio: separacoes representam veiculos de carregamento. Ao
# finalizar uma separacao com saldo nao-separado (qtd_planejada > qtd_escaneada),
# o saldo deve ser realocado para outra separacao EM_SEPARACAO do mesmo
# (pedido, loja). Cenarios:
#
# - Sem saldo: finaliza diretamente (fast-path).
# - Caso A — zero outras seps EM_SEPARACAO: UI mostra modal binario.
#     - Op1 "voltar_saldo": qtd_planejada da origem reduz para qtd_escaneada.
#     - Op2 "manter_planejado": qtd_planejada mantida; sep fica FECHADA com
#       diferenca registrada como divergencia. NF Q.P.A. ajusta posteriormente.
# - Caso B — 1+ outras seps EM_SEPARACAO: UI mostra modal de alocacao manual.
#     - Usuario aloca saldo entre N seps (ou parte volta ao pedido).
#     - realocar_saldo() incrementa qtd_planejada dos destinos, reduz da origem.
#
# `AssaiSeparacaoSaldoModelo` armazena qtd_planejada por modelo. Origem reduz,
# destinos incrementam. Soma das alocacoes deve == saldo.

# Reuso de import existente no topo do arquivo
from app.motos_assai.models import AssaiSeparacaoSaldoModelo  # noqa: E402


def _qtd_planejada_por_modelo(sep_id: int) -> Dict[int, int]:
    """Retorna {modelo_id: qtd_planejada} a partir de AssaiSeparacaoSaldoModelo."""
    rows = (
        db.session.query(
            AssaiSeparacaoSaldoModelo.modelo_id,
            AssaiSeparacaoSaldoModelo.qtd_planejada,
        )
        .filter(AssaiSeparacaoSaldoModelo.separacao_id == sep_id)
        .all()
    )
    return {mid: int(qtd) for mid, qtd in rows}


def _qtd_escaneada_por_modelo(sep_id: int) -> Dict[int, int]:
    """Retorna {modelo_id: qtd_escaneada} contando AssaiSeparacaoItem."""
    rows = (
        db.session.query(
            AssaiSeparacaoItem.modelo_id,
            func.count(AssaiSeparacaoItem.id),
        )
        .filter(AssaiSeparacaoItem.separacao_id == sep_id)
        .group_by(AssaiSeparacaoItem.modelo_id)
        .all()
    )
    return {mid: int(n) for mid, n in rows}


def saldo_planejado_nao_separado(sep_id: int) -> Dict[int, int]:
    """Retorna {modelo_id: qtd_nao_separada} para uma separacao.

    qtd_nao_separada = max(0, qtd_planejada - qtd_escaneada). Modelos com
    qtd_nao_separada == 0 sao omitidos. Se nao ha planejamento para o modelo
    (AssaiSeparacaoSaldoModelo ausente), considera-se 0 (escaneio livre sem
    plano previo nao gera saldo a realocar).
    """
    planejada = _qtd_planejada_por_modelo(sep_id)
    escaneada = _qtd_escaneada_por_modelo(sep_id)

    saldo: Dict[int, int] = {}
    for modelo_id, qtd_plan in planejada.items():
        qtd_esc = escaneada.get(modelo_id, 0)
        nao_sep = qtd_plan - qtd_esc
        if nao_sep > 0:
            saldo[modelo_id] = nao_sep
    return saldo


def outras_seps_em_separacao(pedido_id: int, loja_id: int, exceto_sep_id: int) -> List[AssaiSeparacao]:
    """Lista outras AssaiSeparacao com status EM_SEPARACAO no mesmo (pedido, loja)."""
    return (
        AssaiSeparacao.query
        .filter(
            AssaiSeparacao.pedido_id == pedido_id,
            AssaiSeparacao.loja_id == loja_id,
            AssaiSeparacao.status == SEPARACAO_STATUS_EM_SEPARACAO,
            AssaiSeparacao.id != exceto_sep_id,
        )
        .order_by(AssaiSeparacao.iniciada_em.asc())
        .all()
    )


def analisar_finalizacao(sep_id: int) -> Dict[str, Any]:
    """Analisa o cenario antes de finalizar. Nao muta estado.

    Retorna:
        {
            'cenario': 'sem_saldo' | 'caso_a' | 'caso_b',
            'sep_id': int,
            'saldo': {modelo_id: qtd},          # vazio se sem_saldo
            'modelos_info': [{modelo_id, codigo, nome, qtd_nao_separada}],
            'outras_seps': [{id, criada_em, qtd_escaneada_total}],  # vazio em caso_a
        }
    """
    sep = AssaiSeparacao.query.get(sep_id)
    if not sep:
        raise SeparacaoValidationError(f'AssaiSeparacao {sep_id} nao encontrada')
    if sep.status != SEPARACAO_STATUS_EM_SEPARACAO:
        raise SeparacaoValidationError(
            f'Apenas separacoes EM_SEPARACAO permitem analise. Atual: {sep.status}'
        )

    saldo = saldo_planejado_nao_separado(sep_id)

    if not saldo:
        return {
            'cenario': 'sem_saldo',
            'sep_id': sep_id,
            'saldo': {},
            'modelos_info': [],
            'outras_seps': [],
        }

    # Enriquecer info dos modelos com saldo
    modelos = AssaiModelo.query.filter(AssaiModelo.id.in_(saldo.keys())).all()
    modelo_por_id = {m.id: m for m in modelos}
    modelos_info = [
        {
            'modelo_id': mid,
            'codigo': modelo_por_id[mid].codigo if mid in modelo_por_id else '?',
            'nome': modelo_por_id[mid].nome if mid in modelo_por_id else '?',
            'qtd_nao_separada': qtd,
        }
        for mid, qtd in sorted(saldo.items(), key=lambda x: modelo_por_id[x[0]].codigo if x[0] in modelo_por_id else '')
    ]

    outras = outras_seps_em_separacao(sep.pedido_id, sep.loja_id, sep_id)
    cenario = 'caso_b' if outras else 'caso_a'

    # H4: batch query — evita N+1 (1 query por sep)
    outras_info = []
    if outras:
        outros_ids = [s.id for s in outras]
        counts_por_sep = dict(
            db.session.query(
                AssaiSeparacaoItem.separacao_id,
                func.count(AssaiSeparacaoItem.id),
            )
            .filter(AssaiSeparacaoItem.separacao_id.in_(outros_ids))
            .group_by(AssaiSeparacaoItem.separacao_id)
            .all()
        )
        for s in outras:
            outras_info.append({
                'id': s.id,
                'iniciada_em': s.iniciada_em,
                'qtd_escaneada_total': int(counts_por_sep.get(s.id, 0)),
            })

    return {
        'cenario': cenario,
        'sep_id': sep_id,
        'saldo': saldo,
        'saldo_version': _saldo_version(saldo),  # H3: TOCTOU detection
        'modelos_info': modelos_info,
        'outras_seps': outras_info,
    }


def _saldo_version(saldo: Dict[int, int]) -> str:
    """Gera fingerprint deterministico do saldo para detectar TOCTOU.

    H3 (2026-05-12): frontend recebe via analisar_finalizacao, envia de volta no
    POST finalizar (modo='realocar'). Se saldo atual difere, service retorna 409
    com novo plano (UI re-renderiza modal).
    """
    import hashlib
    import json
    # Ordenar por modelo_id para determinismo
    canonico = json.dumps(sorted(saldo.items()), separators=(',', ':'))
    return hashlib.sha256(canonico.encode()).hexdigest()[:16]


def realocar_saldo(
    sep_origem_id: int,
    alocacoes: List[Dict[str, Any]],
    operador_id: int,
) -> None:
    """Realoca o saldo nao-separado de `sep_origem` entre outras seps e/ou
    devolve ao pedido.

    Args:
        sep_origem_id: id da AssaiSeparacao sendo finalizada.
        alocacoes: lista de dicts com:
            - sep_destino_id (int | None): None = voltar ao pedido (reduz qtd_planejada da origem)
            - modelo_id (int)
            - qtd (int): qtd a realocar
        operador_id: para auditoria/log.

    Validacoes:
        - Soma das alocacoes por modelo == saldo do modelo na origem.
        - Cada sep_destino_id (se != None) deve estar em EM_SEPARACAO no mesmo (pedido, loja).
        - qtd > 0.

    Efeitos:
        - Origem: AssaiSeparacaoSaldoModelo.qtd_planejada reduz para qtd_escaneada (por modelo).
        - Destinos: AssaiSeparacaoSaldoModelo.qtd_planejada incrementa.
            - Se nao existe linha (modelo nunca planejado nesse destino), cria.
        - "Voltar ao pedido": apenas reduz qtd_planejada da origem (sem destino).
    """
    sep_origem = AssaiSeparacao.query.get(sep_origem_id)
    if not sep_origem:
        raise SeparacaoValidationError(f'Sep origem {sep_origem_id} nao encontrada')

    saldo = saldo_planejado_nao_separado(sep_origem_id)
    if not saldo:
        return  # nada a realocar

    # Agregar alocacoes por modelo para validar somas
    agregado_por_modelo: Dict[int, int] = {}
    destinos_distintos: set = set()
    for a in alocacoes:
        modelo_id = int(a['modelo_id'])
        qtd = int(a['qtd'])
        sep_destino_id = a.get('sep_destino_id')
        if qtd <= 0:
            raise SeparacaoValidationError(
                f'qtd deve ser > 0 (modelo {modelo_id}, qtd={qtd})'
            )
        if sep_destino_id is not None:
            destinos_distintos.add(int(sep_destino_id))
        agregado_por_modelo[modelo_id] = agregado_por_modelo.get(modelo_id, 0) + qtd

    # Validar soma = saldo
    for modelo_id, qtd_alocada in agregado_por_modelo.items():
        qtd_saldo = saldo.get(modelo_id, 0)
        if qtd_alocada != qtd_saldo:
            raise SeparacaoValidationError(
                f'Modelo {modelo_id}: alocacao soma {qtd_alocada} mas saldo e {qtd_saldo}. '
                'Deve cobrir 100% do saldo (use sep_destino_id=None para voltar ao pedido).'
            )

    # Validar que todos modelos com saldo estao em alocacoes
    for modelo_id in saldo:
        if modelo_id not in agregado_por_modelo:
            raise SeparacaoValidationError(
                f'Modelo {modelo_id} tem saldo {saldo[modelo_id]} mas nao foi alocado. '
                'Toda alocacao deve ser explicita.'
            )

    # Validar destinos — H1: lock pessimista em cada sep destino para impedir
    # que outra transacao finalize/cancele entre validacao e execucao.
    destinos_seps: Dict[int, AssaiSeparacao] = {}
    if destinos_distintos:
        # ORDER BY id para evitar deadlock entre transacoes lockando seps em ordens distintas.
        # IMPORTANTE: AssaiSeparacao tem 3 relacionamentos lazy='joined' (pedido, loja,
        # fechada_por) que geram LEFT OUTER JOIN — incompativel com FOR UPDATE no PG.
        # Escopar lock + desabilitar eager loads.
        seps = (
            AssaiSeparacao.query
            .filter(AssaiSeparacao.id.in_(destinos_distintos))
            .enable_eagerloads(False)
            .order_by(AssaiSeparacao.id.asc())
            .with_for_update(of=AssaiSeparacao)
            .all()
        )
        destinos_seps = {s.id: s for s in seps}
        for did in destinos_distintos:
            d = destinos_seps.get(did)
            if not d:
                raise SeparacaoValidationError(f'Sep destino {did} nao encontrada')
            if d.status != SEPARACAO_STATUS_EM_SEPARACAO:
                raise SeparacaoValidationError(
                    f'Sep destino {did} esta {d.status} (precisa EM_SEPARACAO)'
                )
            if d.pedido_id != sep_origem.pedido_id or d.loja_id != sep_origem.loja_id:
                raise SeparacaoValidationError(
                    f'Sep destino {did} tem (pedido, loja) diferente da origem'
                )
            if did == sep_origem_id:
                raise SeparacaoValidationError('Sep destino nao pode ser a propria origem')

    # ====== Executar ======
    # 1. Reduzir qtd_planejada da origem para qtd_escaneada por modelo com saldo
    qtd_escaneada_orig = _qtd_escaneada_por_modelo(sep_origem_id)
    for modelo_id in saldo:
        sm = AssaiSeparacaoSaldoModelo.query.filter_by(
            separacao_id=sep_origem_id, modelo_id=modelo_id,
        ).first()
        if sm:
            nova_qtd = qtd_escaneada_orig.get(modelo_id, 0)
            if nova_qtd <= 0:
                # Sem chassis escaneados — remove placeholder (alternativa: deixar 0 viola CHECK qtd>0)
                db.session.delete(sm)
            else:
                sm.qtd_planejada = nova_qtd

    # 2. Incrementar qtd_planejada nos destinos
    for a in alocacoes:
        sep_destino_id = a.get('sep_destino_id')
        modelo_id = int(a['modelo_id'])
        qtd = int(a['qtd'])

        if sep_destino_id is None:
            continue  # voltar ao pedido: ja reduziu da origem; nada mais a fazer

        sm = AssaiSeparacaoSaldoModelo.query.filter_by(
            separacao_id=int(sep_destino_id), modelo_id=modelo_id,
        ).first()
        if sm:
            sm.qtd_planejada = int(sm.qtd_planejada) + qtd
        else:
            sm = AssaiSeparacaoSaldoModelo(
                separacao_id=int(sep_destino_id),
                modelo_id=modelo_id,
                qtd_planejada=qtd,
            )
            db.session.add(sm)

    db.session.flush()

    import logging
    logging.getLogger(__name__).info(
        'realocar_saldo: origem=%s alocacoes=%s operador=%s',
        sep_origem_id, alocacoes, operador_id,
    )


# Modos de finalizacao com saldo
FINALIZAR_MODO_AUTO = 'auto'              # finaliza direto se sem_saldo; senao erro com plano
FINALIZAR_MODO_VOLTAR_SALDO = 'voltar_saldo'   # caso A op1: reduz qtd_planejada para qtd_escaneada
FINALIZAR_MODO_MANTER_PLANEJADO = 'manter_planejado'  # caso A op2: mantem qtd_planejada (divergencia)
FINALIZAR_MODO_REALOCAR = 'realocar'      # caso B: usa alocacoes


class SeparacaoSaldoPendenteError(SeparacaoValidationError):
    """Saldo nao-separado existe e modo='auto' — UI precisa decidir."""
    def __init__(self, plano: Dict[str, Any]):
        super().__init__(
            f'Saldo nao-separado: cenario={plano["cenario"]}, '
            f'modelos={len(plano["modelos_info"])} — UI precisa decidir'
        )
        self.plano = plano


def finalizar_separacao_com_decisao(
    sep_id: int,
    operador_id: int,
    *,
    modo: str = FINALIZAR_MODO_AUTO,
    alocacoes: Optional[List[Dict[str, Any]]] = None,
    saldo_version: Optional[str] = None,
) -> AssaiSeparacao:
    """Finaliza separacao com tratamento de saldo nao-separado.

    Modos:
        - 'auto': se sem saldo, finaliza direto. Se ha saldo, levanta
          SeparacaoSaldoPendenteError com o plano para UI decidir.
        - 'voltar_saldo' (caso A op1): reduz qtd_planejada para qtd_escaneada
          em cada modelo com saldo. Saldo retorna ao pedido (volta a
          saldo_pendente_por_modelo). Finaliza.
        - 'manter_planejado' (caso A op2): mantem qtd_planejada original.
          Finaliza com divergencia registrada (qtd_escaneada < qtd_planejada).
          NF Q.P.A. ajusta posteriormente (task #9).
        - 'realocar' (caso B): chama realocar_saldo() com alocacoes. Finaliza.

    Reaproveita finalizar_separacao() existente para o passo final (mirror + commit).
    """
    sep = AssaiSeparacao.query.get_or_404(sep_id)
    if sep.status != SEPARACAO_STATUS_EM_SEPARACAO:
        raise SeparacaoValidationError(
            f'Apenas EM_SEPARACAO permite finalizar. Atual: {sep.status}'
        )

    plano = analisar_finalizacao(sep_id)
    cenario = plano['cenario']

    if cenario == 'sem_saldo':
        # Fast-path — qualquer modo aceita
        return finalizar_separacao(sep_id, operador_id)

    # Ha saldo nao-separado
    if modo == FINALIZAR_MODO_AUTO:
        raise SeparacaoSaldoPendenteError(plano)

    if modo == FINALIZAR_MODO_VOLTAR_SALDO:
        # Caso A op1: reduz qtd_planejada para qtd_escaneada (saldo volta ao pedido).
        # H2: se ZERO chassis escaneados em todos os modelos com saldo, NAO finaliza
        # como FECHADA fantasma — cancela automaticamente (decisao usuario 2026-05-12).
        qtd_esc = _qtd_escaneada_por_modelo(sep_id)
        total_escaneado = sum(qtd_esc.values())
        if total_escaneado == 0:
            # Separacao sem chassis escaneados — cancelar
            return cancelar_separacao(
                sep_id,
                motivo='Saldo voltado ao pedido sem escaneio (auto-cancelado)',
                operador_id=operador_id,
            )

        # Tem algum chassi escaneado em algum modelo — reduzir qtd_planejada
        for modelo_id in plano['saldo']:
            sm = AssaiSeparacaoSaldoModelo.query.filter_by(
                separacao_id=sep_id, modelo_id=modelo_id,
            ).first()
            if sm:
                nova_qtd = qtd_esc.get(modelo_id, 0)
                if nova_qtd <= 0:
                    db.session.delete(sm)
                else:
                    sm.qtd_planejada = nova_qtd
        db.session.flush()
        return finalizar_separacao(sep_id, operador_id)

    if modo == FINALIZAR_MODO_MANTER_PLANEJADO:
        # Caso A op2: mantem qtd_planejada (sep fica FECHADA com divergencia).
        # Nao mexe em AssaiSeparacaoSaldoModelo. Finaliza direto.
        return finalizar_separacao(sep_id, operador_id)

    if modo == FINALIZAR_MODO_REALOCAR:
        # Caso B: realoca via alocacoes
        if not alocacoes:
            raise SeparacaoValidationError(
                "modo='realocar' exige alocacoes (lista nao vazia)"
            )
        # H3 TOCTOU: validar saldo_version (checksum do saldo no momento do GET)
        # contra saldo atual. Se diferente, outro operador alterou estado entre
        # GET analisar e POST finalizar — UI precisa re-renderizar modal.
        if saldo_version is not None:
            saldo_atual = plano['saldo']
            if _saldo_version(saldo_atual) != saldo_version:
                raise SeparacaoSaldoPendenteError(plano)
        realocar_saldo(sep_id, alocacoes, operador_id)
        return finalizar_separacao(sep_id, operador_id)

    raise SeparacaoValidationError(f'Modo desconhecido: {modo}')


# =====================================================================
# Ajuste pos-NF: NF Q.P.A. e fonte de verdade (Task #9 — 2026-05-12)
# =====================================================================
#
# Regra de negocio (2026-05-12): quando NF Q.P.A. e importada e TODOS os
# chassis existem em assai_moto, a separacao e AJUSTADA para refletir a NF:
#   1. Chassi da NF nao estava na sep alvo? -> ADICIONAR (move de outra sep
#      ativa ou registra novo evento SEPARADA se estava em outro estado).
#   2. Chassi estava na sep alvo mas NAO veio na NF? -> REMOVER (emite
#      DISPONIVEL para o chassi voltar ao estoque).
#
# Apos ajuste, _calcular_match() naturalmente detecta BATEU porque todos os
# chassis da NF estao na sep alvo.
#
# Sep alvo: AssaiSeparacao com mais chassis em comum com a NF, no mesmo
# loja_id, em estado EM_SEPARACAO ou FECHADA. Se NF nao tem loja ou nao ha
# sep candidata, retorna ok=False (fallback para _calcular_match).


def ajustar_separacao_pela_nf(
    nf_id: int, operador_id: int, pedido_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Ajusta separacao(oes) para refletir a NF Q.P.A. (fonte de verdade) v2.

    Plano 3 Tasks 4-5:
    - A7: detecta CHASSI_OUTRA_LOJA antes do match (gera divergencia)
    - S1=b: se nao ha sep candidata mas ha chassis cadastrados, cria sep em FATURADA
    - A11: gera Excel versao 1 quando sep e nascida via NF
    - S19=b: NF parcial (chassis mistos) cria sep parcial + divergencias
    - N-M5: idempotente em relacao a NFs ja processadas

    Args:
        pedido_id: quando fornecido (caller `vincular_nf_manualmente`, que JA
            validou o pedido + cabecalho AssaiPedidoVendaLoja na loja do CNPJ),
            tem prioridade sobre a inferencia automatica. Curto-circuita o branch
            ambiguo S1=b — D8 IMP-2026-06-23-011. None = inferir pela NF (default,
            comportamento dos callers PDF / dados estruturados inalterado).

    Returns:
        {
            'ok': bool,
            'chassis_desconhecidos': [str],
            'chassis_outra_loja': [str],  # NOVO (A7)
            'sep_alvo_id': int | None,
            'sep_criada_via_nf': bool,    # NOVO (S1=b)
            'chassis_adicionados': [str],
            'chassis_removidos': [str],
            'razao': str,
        }
    """
    from app.motos_assai.models import (
        AssaiNfQpa, AssaiNfQpaItem,
        AssaiPedidoVenda, AssaiPedidoVendaItem,
        DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA,
        DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO,
    )
    from app.motos_assai.services.divergencia_service import criar_divergencia
    from app.utils.timezone import agora_brasil_naive

    nf = AssaiNfQpa.query.get(nf_id)
    if not nf:
        return {
            'ok': False, 'chassis_desconhecidos': [], 'chassis_outra_loja': [],
            'sep_alvo_id': None, 'sep_criada_via_nf': False,
            'chassis_adicionados': [], 'chassis_removidos': [],
            'razao': f'NF {nf_id} nao encontrada',
        }

    items_nf = AssaiNfQpaItem.query.filter_by(nf_id=nf_id).all()
    chassis_nf = [it.chassi for it in items_nf if it.chassi]
    chassis_nf_set = set(chassis_nf)

    if not chassis_nf:
        return {
            'ok': False, 'chassis_desconhecidos': [], 'chassis_outra_loja': [],
            'sep_alvo_id': None, 'sep_criada_via_nf': False,
            'chassis_adicionados': [], 'chassis_removidos': [],
            'razao': 'NF sem chassis extraidos',
        }

    # 1. Verificar existencia de TODOS os chassis em assai_moto
    motos = AssaiMoto.query.filter(AssaiMoto.chassi.in_(chassis_nf)).all()
    chassis_existentes = {m.chassi for m in motos}
    desconhecidos = [c for c in chassis_nf if c not in chassis_existentes]
    moto_por_chassi_pre = {m.chassi: m for m in motos}

    # 2. Determinar sep alvo: precisa de loja
    if not nf.loja_id:
        return {
            'ok': False, 'chassis_desconhecidos': desconhecidos,
            'chassis_outra_loja': [],
            'sep_alvo_id': None, 'sep_criada_via_nf': False,
            'chassis_adicionados': [], 'chassis_removidos': [],
            'razao': 'NF sem loja_id — nao foi possivel escolher sep alvo',
        }

    # A7 (Plano 3 Task 4): detectar CHASSI_OUTRA_LOJA ANTES do match
    chassis_outra_loja = []
    for chassi in chassis_nf:
        sep_outra_loja = (
            db.session.query(AssaiSeparacao)
            .join(AssaiSeparacaoItem, AssaiSeparacaoItem.separacao_id == AssaiSeparacao.id)
            .filter(
                AssaiSeparacaoItem.chassi == chassi,
                AssaiSeparacao.status.in_([
                    SEPARACAO_STATUS_EM_SEPARACAO,
                    SEPARACAO_STATUS_FECHADA,
                    SEPARACAO_STATUS_CARREGADA,
                ]),
                AssaiSeparacao.loja_id != nf.loja_id,
            )
            .first()
        )
        if sep_outra_loja:
            criar_divergencia(
                tipo=DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA,
                chassi=chassi, sep_id=sep_outra_loja.id, nf_id=nf.id,
                detalhes={
                    'loja_atual': sep_outra_loja.loja_id,
                    'loja_nf': nf.loja_id,
                    'sep_status': sep_outra_loja.status,
                },
            )
            chassis_outra_loja.append(chassi)

    # Se houver desconhecidos: continua o processamento, mas gera divergencias
    # CHASSI_NAO_CADASTRADO (S19=b: NF parcial cria sep parcial + divergencias)
    if desconhecidos:
        for chassi in desconhecidos:
            criar_divergencia(
                tipo=DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO,
                chassi=chassi, nf_id=nf.id,
                detalhes={'origem': 'ajustar_separacao_pela_nf'},
            )

    # Filtrar chassis para o ajuste (excluir CHASSI_OUTRA_LOJA + desconhecidos)
    chassis_filtrados = [
        c for c in chassis_nf
        if c not in chassis_outra_loja and c in chassis_existentes
    ]
    if not chassis_filtrados:
        return {
            'ok': False, 'chassis_desconhecidos': desconhecidos,
            'chassis_outra_loja': chassis_outra_loja,
            'sep_alvo_id': None, 'sep_criada_via_nf': False,
            'chassis_adicionados': [], 'chassis_removidos': [],
            'razao': (
                f'Nenhum chassi processavel: {len(desconhecidos)} desconhecidos, '
                f'{len(chassis_outra_loja)} em outra loja'
            ),
        }
    chassis_filtrados_set = set(chassis_filtrados)

    # M2 (2026-05-12): derivar pedido_id provavel da NF a partir dos chassis.
    # Filtrando candidatas APENAS dentro do pedido inferido evita parar NF na
    # sep de OUTRO pedido da mesma loja.
    #
    # D8 IMP-2026-06-23-011 (2026-06-24): pedido_id explicito tem PRIORIDADE sobre
    # a inferencia. `vincular_nf_manualmente` ja validou que o pedido existe e tem
    # AssaiPedidoVendaLoja na loja do CNPJ destinatario; propaga-lo aqui curto-
    # circuita tanto a inferencia automatica abaixo quanto o branch ambiguo S1=b
    # (que exige EXATAMENTE 1 pedido ABERTO/PARCIAL na loja — falso negativo para
    # NF de backfill em loja Sendas/Assai com >1 pedido vivo: 98/100 caiam ali).
    pedido_inferido_id = pedido_id
    if pedido_inferido_id is None:
        pedidos_via_chassi = (
            db.session.query(AssaiSeparacao.pedido_id, func.count(AssaiSeparacaoItem.id))
            .join(AssaiSeparacaoItem, AssaiSeparacaoItem.separacao_id == AssaiSeparacao.id)
            .filter(
                AssaiSeparacaoItem.chassi.in_(chassis_filtrados),
                AssaiSeparacao.status.in_([
                    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
                    SEPARACAO_STATUS_CARREGADA,
                ]),
                AssaiSeparacao.loja_id == nf.loja_id,
            )
            .group_by(AssaiSeparacao.pedido_id)
            .order_by(func.count(AssaiSeparacaoItem.id).desc())
            .all()
        )
        if pedidos_via_chassi:
            pedido_inferido_id = pedidos_via_chassi[0][0]
        else:
            # Sem chassis ja separados — fallback: NAO restringir por pedido_id, mas
            # exigir que apenas 1 pedido tenha sep ativa na loja para nao ficar ambiguo
            pedidos_seps_loja = (
                db.session.query(AssaiSeparacao.pedido_id)
                .filter(
                    AssaiSeparacao.loja_id == nf.loja_id,
                    AssaiSeparacao.status.in_([
                        SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
                        SEPARACAO_STATUS_CARREGADA,
                    ]),
                )
                .distinct().all()
            )
            if len(pedidos_seps_loja) == 1:
                pedido_inferido_id = pedidos_seps_loja[0][0]

    # S1=b (Plano 3 Task 5): se nenhum pedido inferido OU sem sep candidata,
    # tenta inferir pedido a partir de pedidos com loja ABERTOS e cria sep em FATURADA.
    seps_candidatas = []
    if pedido_inferido_id:
        seps_candidatas = (
            AssaiSeparacao.query
            .filter(
                AssaiSeparacao.pedido_id == pedido_inferido_id,
                AssaiSeparacao.loja_id == nf.loja_id,
                AssaiSeparacao.status.in_([
                    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
                    SEPARACAO_STATUS_CARREGADA,
                ]),
            )
            .all()
        )

    if not seps_candidatas:
        # S1=b: NF antes da sep — cria sep em FATURADA se houver pedido com loja
        # 1. Se nao temos pedido_inferido, tentar achar pedido com PVL para essa loja
        if not pedido_inferido_id:
            from app.motos_assai.models import (
                AssaiPedidoVendaLoja,
                PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_PARCIALMENTE_FATURADO,
            )
            pvl_q = (
                db.session.query(AssaiPedidoVendaLoja, AssaiPedidoVenda)
                .join(AssaiPedidoVenda, AssaiPedidoVendaLoja.pedido_id == AssaiPedidoVenda.id)
                .filter(
                    AssaiPedidoVendaLoja.loja_id == nf.loja_id,
                    AssaiPedidoVenda.status.in_([
                        PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_PARCIALMENTE_FATURADO,
                    ]),
                )
                .all()
            )
            if len(pvl_q) == 1:
                pedido_inferido_id = pvl_q[0][1].id

        if not pedido_inferido_id:
            return {
                'ok': False, 'chassis_desconhecidos': desconhecidos,
                'chassis_outra_loja': chassis_outra_loja,
                'sep_alvo_id': None, 'sep_criada_via_nf': False,
                'chassis_adicionados': [], 'chassis_removidos': [],
                'razao': (
                    f'NF sem chassis em separacao ativa e loja {nf.loja_id} tem '
                    f'pedido(s) candidato(s) ambiguo(s) — necessita escolha manual'
                ),
            }

        # S1=b: criar nova sep em FATURADA, vincular chassis, gerar Excel v1
        sep_alvo = AssaiSeparacao(
            pedido_id=pedido_inferido_id, loja_id=nf.loja_id,
            status=SEPARACAO_STATUS_FATURADA,
            iniciada_em=agora_brasil_naive(),
            fechada_em=agora_brasil_naive(),
            fechada_por_id=operador_id,
        )
        db.session.add(sep_alvo)
        db.session.flush()

        # Vincular chassis filtrados (cadastrados, nao em outra loja)
        item_nf_por_chassi_s1b = {it.chassi: it for it in items_nf}
        chassis_adicionados_s1b = []
        for chassi in chassis_filtrados:
            moto = moto_por_chassi_pre.get(chassi)
            if not moto:
                continue
            nf_item = item_nf_por_chassi_s1b.get(chassi)
            valor_unit = (
                nf_item.valor_extraido if nf_item and nf_item.valor_extraido is not None
                else Decimal('0')
            )
            db.session.add(AssaiSeparacaoItem(
                separacao_id=sep_alvo.id, chassi=chassi,
                modelo_id=moto.modelo_id,
                valor_unitario_qpa=valor_unit,
                registrada_por_id=operador_id,
            ))
            # Emite SEPARADA + FATURADA para esses chassis
            emitir_evento(
                chassi, EVENTO_SEPARADA, operador_id=operador_id,
                observacao=f'criado via NF {nf.numero} (S1=b)',
                dados_extras={'nf_id': nf_id, 'separacao_id': sep_alvo.id, 'criada_via_nf': True},
            )
            emitir_evento(
                chassi, EVENTO_FATURADA, operador_id=operador_id,
                observacao=f'NF {nf.numero} importada (S1=b)',
                dados_extras={'nf_id': nf_id, 'separacao_id': sep_alvo.id, 'chave_44': nf.chave_44},
            )
            chassis_adicionados_s1b.append(chassi)

        # Vincular NF a sep
        nf.separacao_id = sep_alvo.id

        db.session.flush()

        # A11: gerar Excel versao 1 (best-effort)
        try:
            from app.motos_assai.services.faturamento_service import gerar_excel_qpa
            from app.motos_assai.models import AssaiPedidoExcel
            _, s3_key = gerar_excel_qpa(sep_alvo.id, operador_id)
            db.session.add(AssaiPedidoExcel(
                pedido_id=pedido_inferido_id, separacao_id=sep_alvo.id,
                s3_key=s3_key, versao=1, ativo=True,
                motivo_regeneracao='criada_via_nf_importada',
                gerado_por_id=operador_id,
            ))
            db.session.flush()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                'A11: falha gerar Excel v1 para sep nascida via NF %s: %s',
                nf.numero, e, exc_info=True,
            )

        # Espelhar para Nacom (best-effort)
        try:
            from app.motos_assai.services.separacao_mirror_service import (
                mirror_assai_to_separacao,
            )
            mirror_assai_to_separacao(sep_alvo.id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                'mirror_assai_to_separacao falhou para sep S1=b %s: %s',
                sep_alvo.id, e, exc_info=True,
            )

        return {
            'ok': True, 'chassis_desconhecidos': desconhecidos,
            'chassis_outra_loja': chassis_outra_loja,
            'sep_alvo_id': sep_alvo.id, 'sep_criada_via_nf': True,
            'chassis_adicionados': chassis_adicionados_s1b,
            'chassis_removidos': [],
            'razao': (
                f'sep_alvo={sep_alvo.id} criada via NF (S1=b), '
                f'+{len(chassis_adicionados_s1b)} chassi(s) FATURADA'
            ),
        }

    melhor_sep = None
    melhor_count = -1
    for s in seps_candidatas:
        items = AssaiSeparacaoItem.query.filter_by(separacao_id=s.id).all()
        chassis_s = {it.chassi for it in items}
        em_comum = len(chassis_s & chassis_filtrados_set)
        if em_comum > melhor_count:
            melhor_count = em_comum
            melhor_sep = s
    if melhor_sep is None:
        return {
            'ok': False, 'razao': 'Sem sep candidata identificada',
            'chassis_desconhecidos': desconhecidos,
            'chassis_outra_loja': chassis_outra_loja,
            'sep_alvo_id': None, 'sep_criada_via_nf': False,
            'chassis_adicionados': [], 'chassis_removidos': [],
        }
    assert melhor_sep is not None
    sep_alvo: AssaiSeparacao = melhor_sep

    # 3. Adicionar chassis da NF que nao estao na sep_alvo
    items_alvo = AssaiSeparacaoItem.query.filter_by(separacao_id=sep_alvo.id).all()
    chassis_na_alvo = {it.chassi for it in items_alvo}

    chassis_adicionados: List[str] = []
    item_nf_por_chassi = {it.chassi: it for it in items_nf}
    moto_por_chassi = {m.chassi: m for m in motos}

    for chassi in chassis_filtrados:
        if chassi in chassis_na_alvo:
            continue  # ja esta

        # K7: lock pessimista em AssaiMoto antes de mover/adicionar chassi.
        # Sem isso, race com `registrar_chassi` concorrente pode causar chassi
        # em 2 seps simultaneamente.
        AssaiMoto.query.filter_by(chassi=chassi).with_for_update(of=AssaiMoto).first()

        # Esta em outra sep ativa? (re-query apos lock para visao consistente)
        outra_item = (
            db.session.query(AssaiSeparacaoItem)
            .join(AssaiSeparacao, AssaiSeparacao.id == AssaiSeparacaoItem.separacao_id)
            .filter(
                AssaiSeparacaoItem.chassi == chassi,
                AssaiSeparacao.status.notin_([SEPARACAO_STATUS_CANCELADA, SEPARACAO_STATUS_FATURADA]),
                AssaiSeparacaoItem.separacao_id != sep_alvo.id,
            )
            .first()
        )

        moto = moto_por_chassi.get(chassi)
        if not moto:
            continue  # invariante quebrada — ja validamos acima, mas defensive

        # Valor: priorizar valor do AssaiNfQpaItem (NF e SOT); fallback 0
        nf_item = item_nf_por_chassi.get(chassi)
        valor_unit = (nf_item.valor_extraido if nf_item and nf_item.valor_extraido is not None
                      else Decimal('0'))

        if outra_item:
            # Mover: delete antiga, create nova na alvo. Nao emite evento DISPONIVEL/SEPARADA
            # — o chassi continua SEPARADA, so muda de separacao.
            db.session.delete(outra_item)
            db.session.flush()
            new_item = AssaiSeparacaoItem(
                separacao_id=sep_alvo.id,
                chassi=chassi,
                modelo_id=moto.modelo_id,
                valor_unitario_qpa=valor_unit,
                registrada_por_id=operador_id,
            )
            db.session.add(new_item)
        else:
            # Adicionar: chassi esta DISPONIVEL/MONTADA/etc — registra SEPARADA
            new_item = AssaiSeparacaoItem(
                separacao_id=sep_alvo.id,
                chassi=chassi,
                modelo_id=moto.modelo_id,
                valor_unitario_qpa=valor_unit,
                registrada_por_id=operador_id,
            )
            db.session.add(new_item)
            emitir_evento(
                chassi, EVENTO_SEPARADA,
                operador_id=operador_id,
                observacao=f'ajustado pela NF {nf.numero}',
                dados_extras={'nf_id': nf_id, 'separacao_id': sep_alvo.id, 'ajuste_pos_nf': True},
            )

        chassis_adicionados.append(chassi)

    # 4. Remover chassis da sep_alvo que NAO vieram na NF
    chassis_removidos: List[str] = []
    for it in items_alvo:
        if it.chassi not in chassis_filtrados_set:
            chassi = it.chassi
            db.session.delete(it)
            emitir_evento(
                chassi, EVENTO_DISPONIVEL,
                operador_id=operador_id,
                observacao=f'removido pela NF {nf.numero}',
                dados_extras={'nf_id': nf_id, 'separacao_id': sep_alvo.id, 'ajuste_pos_nf': True},
            )
            chassis_removidos.append(chassi)

    db.session.flush()

    import logging
    logging.getLogger(__name__).info(
        'ajustar_separacao_pela_nf: nf=%s sep_alvo=%s adicionados=%s removidos=%s',
        nf_id, sep_alvo.id, chassis_adicionados, chassis_removidos,
    )

    return {
        'ok': True,
        'chassis_desconhecidos': desconhecidos,
        'chassis_outra_loja': chassis_outra_loja,
        'sep_alvo_id': sep_alvo.id,
        'sep_criada_via_nf': False,
        'chassis_adicionados': chassis_adicionados,
        'chassis_removidos': chassis_removidos,
        'razao': (
            f'sep_alvo={sep_alvo.id}, +{len(chassis_adicionados)} chassi(s), '
            f'-{len(chassis_removidos)} chassi(s)'
        ),
    }


# =====================================================================
# Agendamento por loja (Task #6 — 2026-05-12)
# =====================================================================

_PRESERVAR = object()  # Sentinela para distinguir "preservar" de "limpar (set NULL)"


def atualizar_agendamento_loja(
    pedido_id: int, loja_id: int,
    expedicao=_PRESERVAR, agendamento=_PRESERVAR,
    protocolo=_PRESERVAR,
    agendamento_confirmado=_PRESERVAR,
    operador_id: Optional[int] = None,
):
    """Cria ou atualiza AssaiPedidoVendaLoja com os 4 campos.

    Cabecalho propaga automaticamente para items via FK (relationship).
    Se ja existem separacoes FECHADAS para (pedido, loja), chama
    `propagar_4_campos_para_espelho` para atualizar linhas espelho em
    `separacao` Nacom — assim os campos chegam ao lista_pedidos.html.

    K10 (2026-05-12): semantica explicita via sentinela `_PRESERVAR`:
    - `_PRESERVAR` (default): nao mexe no campo (param omitido).
    - `None`: SET NULL (limpar campo).
    - valor concreto: SET valor.

    Caller via JSON (route `pedidos_agendamento_loja`) DEVE normalizar:
    - chave ausente no body -> passar `_PRESERVAR` (omitir kwarg).
    - chave com valor `''`/`null` -> passar `None` (limpar).
    - chave com valor concreto -> passar o valor.

    Args:
        pedido_id, loja_id: identifica o cabecalho.
        expedicao, agendamento (date|None|_PRESERVAR).
        protocolo (str|None|_PRESERVAR).
        agendamento_confirmado (bool|None|_PRESERVAR) — Boolean, mas pode receber
          None para limpar (campo no DB e NOT NULL DEFAULT FALSE; limpar = False).
        operador_id: para auditoria.

    Returns:
        AssaiPedidoVendaLoja (criado ou atualizado).
    """
    from app.motos_assai.models import AssaiPedidoVendaLoja
    from app.utils.timezone import agora_brasil_naive

    pvl = AssaiPedidoVendaLoja.query.filter_by(
        pedido_id=pedido_id, loja_id=loja_id,
    ).first()

    if not pvl:
        # Criar — verificar que ha pedido/loja
        ped = AssaiPedidoVenda.query.get(pedido_id)
        if not ped:
            raise SeparacaoValidationError(f'Pedido {pedido_id} nao encontrado')
        from app.motos_assai.models import AssaiLoja
        if not AssaiLoja.query.get(loja_id):
            raise SeparacaoValidationError(f'Loja {loja_id} nao encontrada')
        pvl = AssaiPedidoVendaLoja(
            pedido_id=pedido_id, loja_id=loja_id,
        )
        db.session.add(pvl)

    # K10: _PRESERVAR = nao mexer; None = limpar (SET NULL/False); valor = setar.
    if expedicao is not _PRESERVAR:
        pvl.expedicao = expedicao  # date ou None
    if agendamento is not _PRESERVAR:
        pvl.agendamento = agendamento  # date ou None
    if protocolo is not _PRESERVAR:
        # str vazia tambem trata como None (SET NULL)
        pvl.protocolo = protocolo if protocolo else None
    if agendamento_confirmado is not _PRESERVAR:
        # Campo no DB e NOT NULL DEFAULT FALSE. None -> False (default).
        pvl.agendamento_confirmado = bool(agendamento_confirmado) if agendamento_confirmado is not None else False
    pvl.atualizado_em = agora_brasil_naive()

    db.session.flush()

    # Propagar para espelho em separacoes ja FECHADAS (lote ja criado em
    # `separacao` Nacom). Separacoes EM_SEPARACAO ainda nao espelham — quando
    # forem finalizadas, o mirror le os 4 campos via fallback.
    seps_espelhadas = (
        AssaiSeparacao.query
        .filter(
            AssaiSeparacao.pedido_id == pedido_id,
            AssaiSeparacao.loja_id == loja_id,
            AssaiSeparacao.status.in_([SEPARACAO_STATUS_FECHADA, SEPARACAO_STATUS_FATURADA]),
        )
        .all()
    )
    if seps_espelhadas:
        from app.motos_assai.services.separacao_mirror_service import propagar_4_campos_para_espelho
        for sep in seps_espelhadas:
            propagar_4_campos_para_espelho(sep.id)

    db.session.commit()

    import logging
    logging.getLogger(__name__).info(
        'atualizar_agendamento_loja: pedido=%s loja=%s exp=%s ag=%s '
        'prot=%s conf=%s seps_propagadas=%d operador=%s',
        pedido_id, loja_id, pvl.expedicao, pvl.agendamento,
        pvl.protocolo, pvl.agendamento_confirmado, len(seps_espelhadas), operador_id,
    )

    return pvl


# =====================================================================
# Criacao de separacao com placeholder de qtd planejada (Task #7 — 2026-05-12)
# =====================================================================

def criar_separacao_com_saldos(
    pedido_id: int, loja_id: int,
    alocacoes: List[Dict[str, int]],
    operador_id: int,
) -> AssaiSeparacao:
    """Cria nova separacao EM_SEPARACAO com qtd planejada por modelo.

    Args:
        pedido_id, loja_id: (pedido, loja) alvo.
        alocacoes: [{modelo_id, qtd}] — pelo menos 1 modelo com qtd > 0.
        operador_id: para auditoria.

    Validacoes:
        - Cada modelo_id pertence ao pedido (existe item em AssaiPedidoVendaItem).
        - Cada qtd > 0.
        - Sum(qtd por modelo) <= saldo_pendente do modelo (considerando outras seps).

    Concorrencia (K6): serializa criacoes do mesmo pedido via `with_for_update`
    no AssaiPedidoVenda. Sem isso, 2 ops concorrentes podem ambos passar a
    validacao "qtd <= saldo" e gerar overplanning.

    Returns:
        AssaiSeparacao recem-criada.
    """
    if not alocacoes:
        raise SeparacaoValidationError('alocacoes nao pode ser vazia')

    # Lock pessimista no pedido — outras transacoes concorrentes que tentem
    # criar/realocar saldos do mesmo pedido aguardam.
    # IMPORTANTE: AssaiPedidoVenda.criado_por usa lazy='joined' (LEFT OUTER JOIN
    # com usuarios), incompativel com FOR UPDATE no PG. Escopar lock com
    # `of=AssaiPedidoVenda` (PG aceita) e desabilitar eager load.
    ped = (
        AssaiPedidoVenda.query
        .filter_by(id=pedido_id)
        .enable_eagerloads(False)
        .with_for_update(of=AssaiPedidoVenda)
        .first()
    )
    if not ped:
        raise SeparacaoValidationError(f'Pedido {pedido_id} nao encontrado')

    # Validar saldo pendente por modelo (apos lock, leitura consistente)
    saldos = saldo_pendente_por_modelo(pedido_id, loja_id)
    saldo_por_modelo = {s['modelo_id']: s['qtd_pendente'] for s in saldos}

    # Agregar alocacoes por modelo (defender contra duplicatas)
    alocacao_agregada: Dict[int, int] = {}
    for a in alocacoes:
        modelo_id = int(a['modelo_id'])
        qtd = int(a['qtd'])
        if qtd <= 0:
            raise SeparacaoValidationError(
                f'qtd deve ser > 0 (modelo {modelo_id}, qtd={qtd})'
            )
        alocacao_agregada[modelo_id] = alocacao_agregada.get(modelo_id, 0) + qtd

    # Validar contra saldo
    for modelo_id, qtd_total in alocacao_agregada.items():
        saldo = saldo_por_modelo.get(modelo_id)
        if saldo is None:
            raise SeparacaoValidationError(
                f'Modelo {modelo_id} nao pertence ao pedido {pedido_id} loja {loja_id}'
            )
        if qtd_total > saldo:
            raise SeparacaoValidationError(
                f'Modelo {modelo_id}: qtd {qtd_total} excede saldo pendente {saldo}'
            )

    # H8: copiar 4 campos do cabecalho AssaiPedidoVendaLoja como valor INICIAL
    # da sep (operador pode alterar depois via UI). Padrao Nacom: sep tem valor.
    from app.motos_assai.models import AssaiPedidoVendaLoja
    pvl = AssaiPedidoVendaLoja.query.filter_by(
        pedido_id=pedido_id, loja_id=loja_id,
    ).first()

    # Criar separacao + saldos
    sep = AssaiSeparacao(
        pedido_id=pedido_id, loja_id=loja_id,
        status=SEPARACAO_STATUS_EM_SEPARACAO,
        # Inicializa 4 campos da sep com referencia do cabecalho (se existe)
        expedicao=pvl.expedicao if pvl else None,
        agendamento=pvl.agendamento if pvl else None,
        protocolo=pvl.protocolo if pvl else None,
        agendamento_confirmado=bool(pvl.agendamento_confirmado) if pvl else False,
    )
    db.session.add(sep)
    db.session.flush()  # garantir sep.id

    for modelo_id, qtd in alocacao_agregada.items():
        sm = AssaiSeparacaoSaldoModelo(
            separacao_id=sep.id,
            modelo_id=modelo_id,
            qtd_planejada=qtd,
        )
        db.session.add(sm)

    db.session.flush()
    db.session.commit()

    import logging
    logging.getLogger(__name__).info(
        'criar_separacao_com_saldos: pedido=%s loja=%s sep_id=%s '
        'alocacoes=%s operador=%s',
        pedido_id, loja_id, sep.id, alocacao_agregada, operador_id,
    )

    return sep


# =====================================================================
# Substituir chassi entre seps (Plano 4 Task 1 — 2026-05-13)
# =====================================================================
#
# Spec: §11.3 (S20=a + CR-2 + CR-10 + CR-11)
# Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase5-auxiliares.md Task 1
#
# Move chassi entre 2 separacoes (cross-loja ou mesma loja). Usado quando
# operador escaneia chassi que ja esta em sep de outra loja:
#   1. Sep_origem perde o chassi (item deletado)
#   2. Sep_destino recebe (novo item)
#   3. Eventos: <atual> -> DISPONIVEL -> SEPARADA (S20=a, sequencia uniforme)
#   4. Excel sep_origem regenerado SEMPRE (chassi a menos)
#   5. Excel sep_destino regenerado se ja tinha
#   6. Mirror Nacom em ambas (delta)
#   7. Pedido recalculado em ambos lados
#
# CR-11: sep_destino aceita EM_SEPARACAO/FECHADA/CARREGADA. FATURADA bloqueada
#        (cancele NF antes via cancelar_nf_qpa).
# CR-2:  sep_origem FATURADA gera divergencia tipo CHASSI_OUTRA_LOJA.
# CR-10: usa AssaiNfQpa.query.filter_by (nao usa relationship reverse).


def substituir_chassi_entre_seps(
    chassi: str, sep_origem_id: int, sep_destino_id: int, operador_id: int,
    via_divergencia: bool = False,
) -> Dict[str, Any]:
    """Move chassi entre seps com regenerar Excel + mirror Nacom + recalcular pedido.

    S20=a: eventos <atual> -> DISPONIVEL -> SEPARADA (sempre 2 novos eventos).
    CR-11: sep_destino aceita EM_SEPARACAO, FECHADA, CARREGADA. FATURADA bloqueada.
    CR-2: sep_origem FATURADA gera divergencia tipo CHASSI_OUTRA_LOJA.
    CR-10: usa query AssaiNfQpa.query.filter_by (nao usa relationship reverse).
    S10: chama recalcular_status_pedido em ambos pedidos.

    Pacote C (2026-05-13): bloqueia sep_origem FATURADA/CARREGADA quando chamada
    direta (tela sep/carregamento). Para alterar chassi de NF emitida ou carga
    em transito, operador DEVE passar pelo fluxo de Divergencias — caller passa
    via_divergencia=True.

    NAO commita — caller commita.

    Args:
        chassi: chassi a mover.
        sep_origem_id: sep onde chassi esta hoje.
        sep_destino_id: sep para onde mover.
        operador_id: usuario que solicitou.
        via_divergencia: True quando chamada vem do modulo Divergencias
            (permite origem FATURADA/CARREGADA). False (default) bloqueia
            esses statuses — operador deve usar fluxo de divergencia.

    Returns:
        {
            'chassi': str,
            'sep_origem_id': int,
            'sep_destino_id': int,
            'divergencia_id': int | None,  # se sep_origem FATURADA
        }

    Raises:
        SeparacaoValidationError: chassi nao esta na sep origem, sep destino
            invalida (FATURADA, ou nao existe), seps iguais, ou origem
            FATURADA/CARREGADA sem via_divergencia=True.
    """
    chassi_norm = chassi.strip().upper()

    if sep_origem_id == sep_destino_id:
        raise SeparacaoValidationError(
            'sep_origem_id e sep_destino_id sao iguais — nada a substituir'
        )

    # Lock pessimista no chassi (impede race com registrar_chassi/escanear concorrentes)
    moto = AssaiMoto.query.filter_by(chassi=chassi_norm).with_for_update(of=AssaiMoto).first()
    if not moto:
        raise SeparacaoValidationError(f'Chassi {chassi_norm} nao cadastrado')

    sep_origem = AssaiSeparacao.query.get(sep_origem_id)
    if not sep_origem:
        raise SeparacaoValidationError(f'Sep origem {sep_origem_id} nao encontrada')

    sep_destino = AssaiSeparacao.query.get(sep_destino_id)
    if not sep_destino:
        raise SeparacaoValidationError(f'Sep destino {sep_destino_id} nao encontrada')

    # Pacote C (2026-05-13): bloquear substituicao direta de sep origem
    # FATURADA/CARREGADA — operador deve criar divergencia.
    if not via_divergencia and sep_origem.status in (
        SEPARACAO_STATUS_FATURADA, SEPARACAO_STATUS_CARREGADA,
    ):
        raise SeparacaoValidationError(
            f'Sep origem {sep_origem_id} esta {sep_origem.status} — '
            'substituicao direta bloqueada. Use o modulo Divergencias para '
            'alterar chassi de NF emitida ou carga em transito.'
        )

    # CR-11: pre-condicoes do destino
    if sep_destino.status not in (
        SEPARACAO_STATUS_EM_SEPARACAO,
        SEPARACAO_STATUS_FECHADA,
        SEPARACAO_STATUS_CARREGADA,
    ):
        raise SeparacaoValidationError(
            f'Sep destino {sep_destino_id} esta {sep_destino.status} — invalida. '
            'Esperado: EM_SEPARACAO, FECHADA ou CARREGADA. '
            'Para FATURADA, cancele a NF (cancelar_nf_qpa) primeiro.'
        )

    item_origem = AssaiSeparacaoItem.query.filter_by(
        separacao_id=sep_origem_id, chassi=chassi_norm,
    ).first()
    if not item_origem:
        raise SeparacaoValidationError(
            f'Chassi {chassi_norm} nao esta na sep {sep_origem_id}'
        )

    valor_unit_origem = item_origem.valor_unitario_qpa

    # Code review fix H5 (2026-05-13): capturar estado_atual ANTES do delete
    # para auditoria precisa. Antes era capturado APOS delete+flush, refletindo
    # estado intermediario inconsistente (sem item ativo mas com evento ainda
    # SEPARADA/CARREGADA/FATURADA). Agora dados_extras.estado_anterior reflete
    # o estado real antes da operacao.
    estado_atual = status_efetivo(chassi_norm)

    db.session.delete(item_origem)
    db.session.flush()

    # S20=a: eventos <atual> -> DISPONIVEL -> SEPARADA (sequencia uniforme)
    emitir_evento(
        chassi_norm, EVENTO_DISPONIVEL, operador_id=operador_id,
        observacao=(
            f'substituicao cross-loja sep {sep_origem_id} -> sep {sep_destino_id}'
        ),
        dados_extras={
            'sep_origem_id': sep_origem_id,
            'estado_anterior': estado_atual,
        },
    )

    # Adicionar item na sep destino + emitir SEPARADA
    novo_item = AssaiSeparacaoItem(
        separacao_id=sep_destino_id, chassi=chassi_norm,
        modelo_id=moto.modelo_id,
        valor_unitario_qpa=valor_unit_origem,
        registrada_por_id=operador_id,
    )
    db.session.add(novo_item)
    db.session.flush()

    emitir_evento(
        chassi_norm, EVENTO_SEPARADA, operador_id=operador_id,
        observacao=f'substituicao cross-loja vindo de sep {sep_origem_id}',
        dados_extras={'sep_destino_id': sep_destino_id},
    )

    # CR-2 + CR-10: sep_origem FATURADA -> divergencia CHASSI_OUTRA_LOJA
    divergencia_id = None
    if sep_origem.status == SEPARACAO_STATUS_FATURADA:
        # CR-10: usa query direta (nao relationship reverse) + filter status_match
        nf_origem = (
            AssaiNfQpa.query
            .filter_by(separacao_id=sep_origem_id)
            .filter(AssaiNfQpa.status_match != NF_STATUS_CANCELADA)
            .first()
        )
        from app.motos_assai.services.divergencia_service import criar_divergencia
        div = criar_divergencia(
            tipo=DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA,
            chassi=chassi_norm,
            sep_id=sep_origem_id,
            nf_id=nf_origem.id if nf_origem else None,
            detalhes={
                'motivo': 'chassi removido de NF FATURADA por substituicao cross-loja',
                'sep_destino_id': sep_destino_id,
                'loja_origem': sep_origem.loja_id,
                'loja_destino': sep_destino.loja_id,
            },
        )
        divergencia_id = div.id

    # S20: regenerar Excel sep_origem SEMPRE (chassi a menos).
    # Skip se sep_origem ainda EM_SEPARACAO sem Excel ativo (nada a regenerar).
    excel_origem_ativo = AssaiPedidoExcel.query.filter_by(
        separacao_id=sep_origem_id, ativo=True,
    ).first()
    if excel_origem_ativo or sep_origem.status != SEPARACAO_STATUS_EM_SEPARACAO:
        from app.motos_assai.services.faturamento_service import regenerar_excel_qpa
        try:
            regenerar_excel_qpa(
                sep_origem_id, operador_id,
                motivo='substituicao cross-loja: chassi removido',
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                'regenerar_excel_qpa origem sep %s FALHOU: %s — continuando',
                sep_origem_id, e, exc_info=True,
            )

    # Regenerar Excel sep_destino se ja tinha
    excel_destino_ativo = AssaiPedidoExcel.query.filter_by(
        separacao_id=sep_destino_id, ativo=True,
    ).first()
    if excel_destino_ativo:
        from app.motos_assai.services.faturamento_service import regenerar_excel_qpa
        try:
            regenerar_excel_qpa(
                sep_destino_id, operador_id,
                motivo='substituicao cross-loja: chassi adicionado',
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                'regenerar_excel_qpa destino sep %s FALHOU: %s — continuando',
                sep_destino_id, e, exc_info=True,
            )

    # Atualizar mirror Nacom em ambos
    try:
        from app.motos_assai.services.separacao_mirror_service import (
            sincronizar_espelho_com_separacao,
        )
        sincronizar_espelho_com_separacao(sep_origem_id)
        sincronizar_espelho_com_separacao(sep_destino_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(
            'sincronizar_espelho_com_separacao FALHOU em substituicao: %s',
            e, exc_info=True,
        )

    # S10: recalcular pedido em ambos lados
    try:
        from app.motos_assai.services.pedido_status_service import recalcular_status_pedido
        recalcular_status_pedido(sep_origem.pedido_id)
        if sep_destino.pedido_id != sep_origem.pedido_id:
            recalcular_status_pedido(sep_destino.pedido_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(
            'recalcular_status_pedido FALHOU em substituicao: %s', e, exc_info=True,
        )

    db.session.flush()

    import logging
    logging.getLogger(__name__).info(
        'substituir_chassi_entre_seps: chassi=%s origem=%s destino=%s '
        'estado_anterior=%s divergencia=%s operador=%s',
        chassi_norm, sep_origem_id, sep_destino_id,
        estado_atual, divergencia_id, operador_id,
    )

    return {
        'chassi': chassi_norm,
        'sep_origem_id': sep_origem_id,
        'sep_destino_id': sep_destino_id,
        'divergencia_id': divergencia_id,
        'estado_anterior': estado_atual,
    }
