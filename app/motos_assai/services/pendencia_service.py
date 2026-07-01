"""Pendencias de montagem (defeitos de peca).

Pendencia aberta: chassi com ultimo evento = PENDENTE.
Pendencia resolvida: cada evento PENDENCIA_RESOLVIDA representa uma resolucao
historica (append-only). Mantemos o registro para auditoria mesmo apos o chassi
voltar para MONTADA.

2026-05-13: filtros adicionados — chassi (ilike), modelo_id, data_inicio,
data_fim, operador_id. Auxiliares para autocomplete (operadores distintos +
modelos distintos com pendencias).
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import List, Dict, Any, Optional, TypedDict
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from app import db
from app.auth.models import Usuario
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiPendencia,
    EVENTO_PENDENTE, EVENTO_PENDENCIA_RESOLVIDA, EVENTO_MONTADA,
    EVENTOS_FORA_ESTOQUE,
    PENDENCIA_CATEGORIAS_VALIDAS, PENDENCIA_ORIGENS_VALIDAS, ORIGENS_FISICAS,
    PENDENCIA_TRATATIVAS_VALIDAS, PENDENCIA_FASE_AGUARDANDO_PECA,
)
from app.utils.json_helpers import sanitize_for_json
from app.utils.timezone import agora_brasil_naive
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo


class FiltrosPendencias(TypedDict, total=False):
    chassi: Optional[str]            # ilike %chassi%
    modelo_id: Optional[int]
    data_inicio: Optional[date]      # ocorrido_em >= data_inicio (00:00)
    data_fim: Optional[date]         # ocorrido_em <= data_fim (23:59:59)
    operador_id: Optional[int]
    categoria: Optional[str]
    origem: Optional[str]
    tratativa: Optional[str]


def listar_abertas(filtros: Optional[FiltrosPendencias] = None) -> List[Dict[str, Any]]:
    """Fichas de pendencia ABERTAS (resolvida_em IS NULL AND cancelada_em IS NULL).

    Le a tabela assai_pendencia (E1: a ficha e a verdade do tratamento). Filtros:
    chassi (ilike), modelo_id (via assai_moto), data_inicio/data_fim (aberta_em),
    operador_id (aberta_por_id).

    Retorna dicts com as chaves consumidas por pendencias/abertas.html.
    """
    q = (
        AssaiPendencia.query
        .options(joinedload(AssaiPendencia.aberta_por))
        .filter(
            AssaiPendencia.resolvida_em.is_(None),
            AssaiPendencia.cancelada_em.is_(None),
        )
    )

    if filtros:
        chassi = (filtros.get('chassi') or '').strip().upper()
        if chassi:
            q = q.filter(AssaiPendencia.chassi.ilike(f'%{chassi}%'))
        operador_id = filtros.get('operador_id')
        if operador_id:
            q = q.filter(AssaiPendencia.aberta_por_id == operador_id)
        data_inicio = filtros.get('data_inicio')
        if data_inicio:
            q = q.filter(
                AssaiPendencia.aberta_em >= datetime.combine(data_inicio, time.min)
            )
        data_fim = filtros.get('data_fim')
        if data_fim:
            q = q.filter(
                AssaiPendencia.aberta_em <= datetime.combine(data_fim, time.max)
            )
        categoria = filtros.get('categoria')
        if categoria:
            q = q.filter(AssaiPendencia.categoria == categoria)
        origem = filtros.get('origem')
        if origem:
            q = q.filter(AssaiPendencia.origem == origem)
        tratativa = filtros.get('tratativa')
        if tratativa:
            q = q.filter(AssaiPendencia.tratativa == tratativa)

    fichas = q.order_by(AssaiPendencia.aberta_em.desc()).all()
    if not fichas:
        return []

    chassis = [f.chassi for f in fichas]
    motos = (
        AssaiMoto.query
        .options(joinedload(AssaiMoto.modelo))
        .filter(AssaiMoto.chassi.in_(chassis))
        .all()
    )
    moto_por_chassi = {m.chassi: m for m in motos}

    filtro_modelo_id = (filtros or {}).get('modelo_id')

    result = []
    for f in fichas:
        moto = moto_por_chassi.get(f.chassi)
        if filtro_modelo_id and (not moto or moto.modelo_id != filtro_modelo_id):
            continue
        result.append({
            'evento_id': f.id,
            'pendencia_id': f.id,
            'chassi': f.chassi,
            'modelo_id': moto.modelo_id if moto else None,
            'modelo_codigo': moto.modelo.codigo if moto and moto.modelo else '-',
            'modelo_nome': moto.modelo.nome if moto and moto.modelo else '-',
            'cor': (moto.cor if moto else None) or '-',
            'observacao': f.descricao or '(sem observacao)',
            'chassi_doador': f.chassi_doador,
            'operador': f.aberta_por.nome if f.aberta_por else '-',
            'operador_id': f.aberta_por_id,
            'ocorrido_em': f.aberta_em,
            'categoria': f.categoria,
            'origem': f.origem,
            'tratativa': f.tratativa,
            'fase': f.fase,
        })
    return result


def listar_historico_resolvidas(
    limit: int = 200,
    filtros: Optional[FiltrosPendencias] = None,
) -> List[Dict[str, Any]]:
    """Fichas RESOLVIDAS (resolvida_em IS NOT NULL), 1:1 com a ficha (E1).

    Filtros operador/data se aplicam a RESOLUCAO (resolvida_por_id / resolvida_em).
    Retorna chaves consumidas por pendencias/historico.html.
    """
    q = (
        AssaiPendencia.query
        .options(
            joinedload(AssaiPendencia.aberta_por),
            joinedload(AssaiPendencia.resolvida_por),
        )
        .filter(AssaiPendencia.resolvida_em.isnot(None))
    )

    if filtros:
        chassi = (filtros.get('chassi') or '').strip().upper()
        if chassi:
            q = q.filter(AssaiPendencia.chassi.ilike(f'%{chassi}%'))
        operador_id = filtros.get('operador_id')
        if operador_id:
            q = q.filter(AssaiPendencia.resolvida_por_id == operador_id)
        data_inicio = filtros.get('data_inicio')
        if data_inicio:
            q = q.filter(
                AssaiPendencia.resolvida_em >= datetime.combine(data_inicio, time.min)
            )
        data_fim = filtros.get('data_fim')
        if data_fim:
            q = q.filter(
                AssaiPendencia.resolvida_em <= datetime.combine(data_fim, time.max)
            )
        categoria = filtros.get('categoria')
        if categoria:
            q = q.filter(AssaiPendencia.categoria == categoria)
        origem = filtros.get('origem')
        if origem:
            q = q.filter(AssaiPendencia.origem == origem)
        tratativa = filtros.get('tratativa')
        if tratativa:
            q = q.filter(AssaiPendencia.tratativa == tratativa)

    fichas = q.order_by(AssaiPendencia.resolvida_em.desc()).limit(limit).all()
    if not fichas:
        return []

    chassis = list({f.chassi for f in fichas})
    motos = (
        AssaiMoto.query
        .options(joinedload(AssaiMoto.modelo))
        .filter(AssaiMoto.chassi.in_(chassis))
        .all()
    )
    moto_por_chassi = {m.chassi: m for m in motos}

    filtro_modelo_id = (filtros or {}).get('modelo_id')

    result = []
    for f in fichas:
        moto = moto_por_chassi.get(f.chassi)
        if filtro_modelo_id and (not moto or moto.modelo_id != filtro_modelo_id):
            continue
        result.append({
            'evento_id': f.id,
            'pendencia_id': f.id,
            'chassi': f.chassi,
            'modelo_id': moto.modelo_id if moto else None,
            'modelo_codigo': moto.modelo.codigo if moto and moto.modelo else '-',
            'modelo_nome': moto.modelo.nome if moto and moto.modelo else '-',
            'cor': (moto.cor if moto else None) or '-',
            'observacao_pendencia': f.descricao or '(sem registro)',
            'descricao_resolucao': f.resolucao_descricao or '(sem descricao)',
            'operador_pendencia': f.aberta_por.nome if f.aberta_por else '-',
            'operador_resolucao': f.resolvida_por.nome if f.resolvida_por else '-',
            'operador_resolucao_id': f.resolvida_por_id,
            'data_pendencia': f.aberta_em.strftime('%d/%m/%Y %H:%M') if f.aberta_em else '-',
            'data_resolucao': f.resolvida_em.strftime('%d/%m/%Y %H:%M') if f.resolvida_em else '-',
            'categoria': f.categoria,
            'origem': f.origem,
            'tratativa': f.tratativa,
            'fase': f.fase,
        })
    return result


def contar_pendencias_abertas() -> int:
    """Conta fichas assai_pendencia abertas (resolvida_em IS NULL AND cancelada_em IS NULL)."""
    return (
        db.session.query(func.count(AssaiPendencia.id))
        .filter(
            AssaiPendencia.resolvida_em.is_(None),
            AssaiPendencia.cancelada_em.is_(None),
        )
        .scalar() or 0
    )


# ---------------------------------------------------------------------------
# Helpers para autocomplete dos filtros
# ---------------------------------------------------------------------------


def operadores_que_registraram_pendencia(tipos: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Usuarios distintos que abriram ou resolveram uma ficha de pendencia.

    `tipos` mantido por retrocompat com a rota do Spec 1 (ignorado: a tabela ja
    distingue abertura/resolucao). Retorna [{id, nome, email}] ordenado por nome.
    """
    abertos = db.session.query(AssaiPendencia.aberta_por_id).filter(
        AssaiPendencia.aberta_por_id.isnot(None)
    )
    resolvidos = db.session.query(AssaiPendencia.resolvida_por_id).filter(
        AssaiPendencia.resolvida_por_id.isnot(None)
    )
    ids = {oid for (oid,) in abertos.distinct().all()}
    ids |= {oid for (oid,) in resolvidos.distinct().all()}
    if not ids:
        return []
    usuarios = (
        Usuario.query
        .filter(Usuario.id.in_(ids))
        .order_by(Usuario.nome)
        .all()
    )
    return [{'id': u.id, 'nome': u.nome, 'email': u.email} for u in usuarios]


def modelos_com_pendencias(tipos: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Modelos distintos com ao menos uma ficha de pendencia (qualquer estado).

    `tipos` mantido por retrocompat (ignorado). Retorna [{id, codigo, nome}].
    """
    chassis_subq = (
        db.session.query(AssaiPendencia.chassi).distinct().subquery()
    )
    modelos = (
        db.session.query(AssaiModelo)
        .join(AssaiMoto, AssaiMoto.modelo_id == AssaiModelo.id)
        .filter(AssaiMoto.chassi.in_(db.session.query(chassis_subq.c.chassi)))
        .distinct()
        .order_by(AssaiModelo.codigo)
        .all()
    )
    return [{'id': m.id, 'codigo': m.codigo, 'nome': m.nome} for m in modelos]


# ===========================================================================
# Escrita: ciclo de vida da ficha de pendencia (Spec 1 — back-end)
# ===========================================================================


class PendenciaError(Exception):
    """Erro de dominio de pendencia_service (escrita)."""


def afeta_estado_moto(p) -> bool:
    """Predicado fisico (derivado, nao-coluna): a ficha trava o estado da moto?

    Fisica  => origem em ORIGENS_FISICAS, OU veio de devolucao (NFd), OU a moto
    retornou fisicamente sem NFd (retorno_fisico). So fichas fisicas emitem/
    compartilham o evento PENDENTE.
    """
    return (
        (p.origem in ORIGENS_FISICAS)
        or (p.devolucao_item_id is not None)
        or bool(p.retorno_fisico)
    )


def _get_or_emit_pendente_event(chassi: str, operador_id: int) -> int:
    """Reusa o PENDENTE vivo do chassi (D1: 1 evento por chassi) ou emite um novo.

    DEVE rodar sob pg_advisory_xact_lock(hashtext(chassi)) — garantido pelos
    callers (abrir_pendencia). Uma ficha so recebe evento_pendente_id quando e
    fisica, logo `evento_pendente_id IS NOT NULL` ja implica ficha fisica.
    """
    existente = (
        AssaiPendencia.query
        .filter(
            AssaiPendencia.chassi == chassi,
            AssaiPendencia.evento_pendente_id.isnot(None),
            AssaiPendencia.resolvida_em.is_(None),
            AssaiPendencia.cancelada_em.is_(None),
        )
        .first()
    )
    if existente is not None:
        return existente.evento_pendente_id
    ev = emitir_evento(chassi, EVENTO_PENDENTE, operador_id=operador_id)
    return ev.id


def count_fisicas_abertas(chassi: str) -> int:
    """Conta fichas FISICAS abertas (nao resolvidas e nao canceladas) do chassi."""
    return (
        AssaiPendencia.query
        .filter(
            AssaiPendencia.chassi == chassi,
            AssaiPendencia.resolvida_em.is_(None),
            AssaiPendencia.cancelada_em.is_(None),
            or_(
                AssaiPendencia.origem.in_(list(ORIGENS_FISICAS)),
                AssaiPendencia.devolucao_item_id.isnot(None),
                AssaiPendencia.retorno_fisico.is_(True),
            ),
        )
        .count()
    )


def abrir_pendencia(
    *,
    chassi: str,
    categoria: str,
    origem: str,
    descricao: str,
    operador_id: int,
    retorno_fisico: bool = False,
    evento_pendente_id: Optional[int] = None,
    peca_id: Optional[int] = None,
    pendencia_pai_id: Optional[int] = None,
    devolucao_item_id: Optional[int] = None,
    pos_venda_ocorrencia_id: Optional[int] = None,
    divergencia_origem_id: Optional[int] = None,
    detalhes: Optional[Dict[str, Any]] = None,
) -> AssaiPendencia:
    """Abre uma ficha de pendencia (add + flush, SEM commit — caller commita).

    Acoplamento com o evento PENDENTE (Spec 1 §6):
      - `evento_pendente_id` explicito (emissores legados que JA emitiram o
        PENDENTE): usa-o direto e PULA `_get_or_emit_pendente_event` (sem 2o PENDENTE);
      - senao, se `afeta_estado_moto(ficha)`: reusa/emite via helper travado
        (N fisicas no mesmo chassi = 1 evento, D1);
      - senao (nao fisica — pos-venda sem retorno): `evento_pendente_id = NULL`.
    """
    chassi_norm = (chassi or '').strip().upper()
    if not chassi_norm:
        raise PendenciaError('Chassi obrigatorio.')
    if categoria not in PENDENCIA_CATEGORIAS_VALIDAS:
        raise PendenciaError(
            f'Categoria invalida: {categoria}. Validas: {sorted(PENDENCIA_CATEGORIAS_VALIDAS)}'
        )
    if origem not in PENDENCIA_ORIGENS_VALIDAS:
        raise PendenciaError(
            f'Origem invalida: {origem}. Validas: {sorted(PENDENCIA_ORIGENS_VALIDAS)}'
        )
    descricao_norm = (descricao or '').strip()
    if len(descricao_norm) < 3:
        raise PendenciaError('Descricao obrigatoria (>= 3 caracteres).')

    # Serializa emissao/consulta do PENDENTE compartilhado por chassi.
    db.session.execute(
        db.text('SELECT pg_advisory_xact_lock(hashtext(:c))'),
        {'c': chassi_norm},
    )

    ficha = AssaiPendencia(
        chassi=chassi_norm,
        categoria=categoria,
        origem=origem,
        retorno_fisico=bool(retorno_fisico),
        descricao=descricao_norm,
        peca_id=peca_id,
        pendencia_pai_id=pendencia_pai_id,
        devolucao_item_id=devolucao_item_id,
        pos_venda_ocorrencia_id=pos_venda_ocorrencia_id,
        divergencia_origem_id=divergencia_origem_id,
        detalhes=sanitize_for_json(dict(detalhes or {})),
        aberta_em=agora_brasil_naive(),
        aberta_por_id=operador_id,
    )
    db.session.add(ficha)
    db.session.flush()  # ficha.id disponivel; evento_pendente_id ainda NULL

    if evento_pendente_id is not None:
        ficha.evento_pendente_id = evento_pendente_id
    elif afeta_estado_moto(ficha):
        ficha.evento_pendente_id = _get_or_emit_pendente_event(chassi_norm, operador_id)
    else:
        ficha.evento_pendente_id = None

    db.session.flush()
    return ficha


def reclassificar(*, pendencia_id, categoria, origem, operador_id):
    """Reclassifica categoria/origem de uma ficha (S2 — INDETERMINADA -> real).

    Guard S6: se a ficha ja trava a moto (evento_pendente_id) e a nova origem a
    tornaria nao-fisica, levanta — nao da para destravar via troca de origem.
    add+flush, SEM commit.
    """
    ficha = db.session.get(AssaiPendencia, pendencia_id)
    if ficha is None:
        raise PendenciaError(f'Pendencia {pendencia_id} nao encontrada.')
    if categoria not in PENDENCIA_CATEGORIAS_VALIDAS:
        raise PendenciaError(f'Categoria invalida: {categoria}.')
    if origem not in PENDENCIA_ORIGENS_VALIDAS:
        raise PendenciaError(f'Origem invalida: {origem}.')

    # Avalia o predicado fisico sobre os valores CANDIDATOS, ANTES de mutar a ficha
    # (guard robusto: se qualquer guard levantar, o objeto ORM nao fica sujo num
    # estado invalido — so origem muda na reclassificacao).
    afeta_depois = (
        (origem in ORIGENS_FISICAS)
        or (ficha.devolucao_item_id is not None)
        or bool(ficha.retorno_fisico)
    )
    # Guard S6 (fisica -> nao-fisica): nao destravar a moto via troca de origem.
    if ficha.evento_pendente_id is not None and not afeta_depois:
        raise PendenciaError(
            'Nao e possivel tornar nao-fisica uma pendencia que ja trava a moto '
            '(evento PENDENTE ja emitido).')
    # Guard inverso (nao-fisica -> fisica): a ficha passa a afetar o estado mas ainda
    # nao tem evento PENDENTE. Precisa de lastro coerente sob advisory lock:
    #   - moto EM estoque  -> emite/reusa o PENDENTE (a moto de fato vai a PENDENTE);
    #   - moto FORA do estoque (FATURADA/SEPARADA/...) -> BLOQUEIA. Sem isto, ao
    #     resolver, o gate fisico emitiria MONTADA e ressuscitaria uma moto vendida.
    #     Retorno pos-venda legitimo deve entrar pelo fluxo de Devolucao (NFd).
    novo_evento_id = None
    if ficha.evento_pendente_id is None and afeta_depois:
        db.session.execute(
            db.text('SELECT pg_advisory_xact_lock(hashtext(:c))'), {'c': ficha.chassi})
        if status_efetivo(ficha.chassi) in EVENTOS_FORA_ESTOQUE:
            raise PendenciaError(
                'Nao e possivel tornar fisica uma pendencia de moto fora do estoque '
                '(ex.: FATURADA/SEPARADA). Para retorno pos-venda use o fluxo de Devolucao.')
        novo_evento_id = _get_or_emit_pendente_event(ficha.chassi, operador_id)

    de = {'categoria': ficha.categoria, 'origem': ficha.origem}
    ficha.categoria = categoria
    ficha.origem = origem
    if novo_evento_id is not None:
        ficha.evento_pendente_id = novo_evento_id

    det = dict(ficha.detalhes or {})
    det['reclassificacao'] = {
        'de': de, 'para': {'categoria': categoria, 'origem': origem},
        'por_id': operador_id, 'em': agora_brasil_naive().isoformat(),
    }
    ficha.detalhes = sanitize_for_json(det)
    db.session.flush()
    return ficha


# ===========================================================================
# Fechamento: resolver_pendencia + cancelar_pendencia (Spec 1 Task 7)
# ===========================================================================


def _emitir_resolucao_fisica(ficha, observacao, operador_id):
    """Gate de fechamento fisico: se esta era a ULTIMA ficha fisica aberta do
    chassi, emite PENDENCIA_RESOLVIDA (marcador) + MONTADA (O1). Caso contrario
    nao emite (chassi segue PENDENTE). Chamado SOB advisory lock, APOS marcar a
    ficha como fechada (para que ela ja nao conte em count_fisicas_abertas).
    """
    if not afeta_estado_moto(ficha):
        return
    if count_fisicas_abertas(ficha.chassi) == 0:
        emitir_evento(
            ficha.chassi, EVENTO_PENDENCIA_RESOLVIDA,
            operador_id=operador_id, observacao=observacao,
        )
        emitir_evento(ficha.chassi, EVENTO_MONTADA, operador_id=operador_id)


def resolver_pendencia(
    *, pendencia_id: int, tratativa: Optional[str],
    resolucao_descricao: str, operador_id: int,
) -> AssaiPendencia:
    """Fecha a ficha (E1: resolucao mora na ficha) e dispara o gate fisico.

    Idempotente: ficha ja resolvida/cancelada => no-op (retorna a ficha).
    O movimento de estoque da tratativa (CONSUMO/CANIBALIZACAO) e responsabilidade
    de chamadas separadas a movimento_service (Task 8) ligadas por pendencia_id —
    esta funcao NAO movimenta estoque.
    """
    ficha = db.session.get(AssaiPendencia, pendencia_id)
    if ficha is None:
        raise PendenciaError(f'Pendencia {pendencia_id} nao encontrada.')
    if ficha.resolvida_em is not None or ficha.cancelada_em is not None:
        return ficha  # idempotente
    if tratativa is not None and tratativa not in PENDENCIA_TRATATIVAS_VALIDAS:
        raise PendenciaError(
            f'Tratativa invalida: {tratativa}. Validas: {sorted(PENDENCIA_TRATATIVAS_VALIDAS)}'
        )

    db.session.execute(
        db.text('SELECT pg_advisory_xact_lock(hashtext(:c))'),
        {'c': ficha.chassi},
    )
    db.session.refresh(ficha)               # re-le estado committed (double-click / tx concorrente)
    if ficha.resolvida_em is not None or ficha.cancelada_em is not None:
        return ficha                        # idempotente sob concorrencia (TOCTOU guard)

    ficha.resolvida_em = agora_brasil_naive()
    ficha.resolvida_por_id = operador_id
    ficha.tratativa = tratativa
    ficha.resolucao_descricao = (resolucao_descricao or '').strip() or None
    db.session.flush()  # ficha sai da contagem de fisicas abertas

    _emitir_resolucao_fisica(ficha, ficha.resolucao_descricao, operador_id)
    db.session.flush()
    return ficha


def cancelar_pendencia(
    *, pendencia_id: int, motivo: str, operador_id: int,
) -> AssaiPendencia:
    """Fecha a ficha SEM resolver (sem movimento de estoque). Mesmo gate fisico:
    se era a ultima fisica aberta, a moto volta a MONTADA. Idempotente.
    """
    ficha = db.session.get(AssaiPendencia, pendencia_id)
    if ficha is None:
        raise PendenciaError(f'Pendencia {pendencia_id} nao encontrada.')
    if ficha.resolvida_em is not None or ficha.cancelada_em is not None:
        return ficha  # idempotente
    motivo_norm = (motivo or '').strip()
    if len(motivo_norm) < 3:
        raise PendenciaError('Motivo de cancelamento obrigatorio (>= 3 caracteres).')

    db.session.execute(
        db.text('SELECT pg_advisory_xact_lock(hashtext(:c))'),
        {'c': ficha.chassi},
    )
    db.session.refresh(ficha)               # re-le estado committed (double-click / tx concorrente)
    if ficha.resolvida_em is not None or ficha.cancelada_em is not None:
        return ficha                        # idempotente sob concorrencia (TOCTOU guard)

    ficha.cancelada_em = agora_brasil_naive()
    ficha.cancelada_por_id = operador_id
    det = dict(ficha.detalhes or {})
    det['cancelamento_motivo'] = motivo_norm
    ficha.detalhes = sanitize_for_json(det)
    db.session.flush()

    _emitir_resolucao_fisica(ficha, motivo_norm, operador_id)
    db.session.flush()
    return ficha


def detalhe_pendencia(pendencia_id):
    """Visao 360 read-only de uma ficha (Spec 2 §4.4). Retorna dict ou None."""
    from decimal import Decimal
    from app.motos_assai.models import (
        AssaiEstoqueMovimento, AssaiPecaCompraItem, AssaiPecaCompra,
    )
    ficha = db.session.get(AssaiPendencia, pendencia_id)
    if ficha is None:
        return None
    moto = AssaiMoto.query.options(joinedload(AssaiMoto.modelo)).filter_by(chassi=ficha.chassi).first()

    movs = (AssaiEstoqueMovimento.query
            .options(joinedload(AssaiEstoqueMovimento.peca))
            .filter(AssaiEstoqueMovimento.pendencia_id == pendencia_id)
            .order_by(AssaiEstoqueMovimento.id.desc()).all())
    custo_total = sum((m.custo_total or Decimal('0')) for m in movs) or Decimal('0')

    itens = (AssaiPecaCompraItem.query
             .filter(AssaiPecaCompraItem.pendencia_id == pendencia_id).all())
    compra_ids = {it.compra_id for it in itens}
    compras = (AssaiPecaCompra.query.filter(AssaiPecaCompra.id.in_(compra_ids)).all()
               if compra_ids else [])

    return {
        'ficha': {
            'id': ficha.id, 'chassi': ficha.chassi, 'categoria': ficha.categoria,
            'origem': ficha.origem, 'fase': ficha.fase, 'tratativa': ficha.tratativa,
            'descricao': ficha.descricao, 'resolucao_descricao': ficha.resolucao_descricao,
            'esta_aberta': ficha.esta_aberta, 'chassi_doador': ficha.chassi_doador,
            'aberta_em': ficha.aberta_em, 'aberta_por': ficha.aberta_por.nome if ficha.aberta_por else '-',
            'resolvida_em': ficha.resolvida_em,
            'resolvida_por': ficha.resolvida_por.nome if ficha.resolvida_por else None,
            'cancelada_em': ficha.cancelada_em,
            'devolucao_item_id': ficha.devolucao_item_id,
            'pos_venda_ocorrencia_id': ficha.pos_venda_ocorrencia_id,
            'divergencia_origem_id': ficha.divergencia_origem_id,
            'detalhes': ficha.detalhes or {},
        },
        'moto': {
            'modelo_codigo': moto.modelo.codigo if moto and moto.modelo else '-',
            'modelo_nome': moto.modelo.nome if moto and moto.modelo else '-',
            'cor': (moto.cor if moto else None) or '-',
        } if moto else None,
        'movimentos': [{
            'tipo': m.tipo, 'peca_nome': m.peca.nome if m.peca else '-',
            'quantidade': m.quantidade, 'custo_unitario': m.custo_unitario,
            'custo_total': m.custo_total, 'receita_total': m.receita_total,
            'chassi_origem': m.chassi_origem, 'chassi_destino': m.chassi_destino,
            'ocorrido_em': m.ocorrido_em,
        } for m in movs],
        'custo_total': custo_total,
        'compras': [{
            'id': c.id, 'numero': c.numero, 'tipo': c.tipo, 'status': c.status,
        } for c in compras],
        'filhas': [{'id': fi.id, 'categoria': fi.categoria, 'esta_aberta': fi.esta_aberta}
                   for fi in ficha.filhas],
        'pai': ({'id': ficha.pai.id} if ficha.pai else None),
    }


def solicitar_compra(
    *, pendencia_id: int, tipo: str, itens, operador_id: int,
    fornecedor: str = 'MOTOCHEFE',
):
    """Provisao (R3): cria assai_peca_compra (tipo GARANTIA/COMPRA) + itens
    ligados a esta ficha por pendencia_id, e seta fase=AGUARDANDO_PECA. NAO
    resolve a ficha (nao grava resolvida_em). Delega ao compra_peca_service.
    add + flush, SEM commit.
    """
    from app.motos_assai.services import compra_peca_service

    ficha = db.session.get(AssaiPendencia, pendencia_id)
    if ficha is None:
        raise PendenciaError(f'Pendencia {pendencia_id} nao encontrada.')

    itens_com_pendencia = []
    for it in (itens or []):
        d = dict(it)
        d.setdefault('pendencia_id', pendencia_id)
        itens_com_pendencia.append(d)

    compra = compra_peca_service.criar_compra(
        tipo=tipo, itens=itens_com_pendencia,
        operador_id=operador_id, fornecedor=fornecedor,
    )
    ficha.fase = PENDENCIA_FASE_AGUARDANDO_PECA
    db.session.flush()
    return compra
