"""Sincronizacao de AssaiNfQpa -> EntregaMonitorada (origem='OP_ASSAI').

Espelho funcional de `app/utils/sincronizar_entregas.py:sincronizar_entrega_por_nf`,
adaptado para o universo Op. Assai (B2B Q.P.A. Sendas):
  - Fonte de dados: `AssaiNfQpa` (NF Q.P.A. importada) + `AssaiSeparacao` +
    `AssaiLoja` + `EmbarqueItem` + `Embarque`.
  - Filtro: `origem='OP_ASSAI'` para nao colidir com NACOM/CARVIA mesmo
    quando o `numero_nf` se repete entre universos.

## Quando chamar

1. Apos `_calcular_match` (nf_qpa_adapter) quando `status_match='BATEU'`:
   ao importar NF Q.P.A. e bater com separacao, cria EntregaMonitorada
   inicial com os dados da NF (cliente=loja, valor, data_faturamento).

2. Apos portaria seta `data_embarque` no Embarque: atualiza data_embarque
   + transportadora (similar ao gatilho que ja existe para CarVia).

## Convencoes

- `numero_nf` filtro: AssaiNfQpa.numero (corresponde ao que `_calcular_match`
  propaga para `Separacao.numero_nf` e `EmbarqueItem.nota_fiscal`).
- `origem='OP_ASSAI'`. Compativel com 3 origens (NACOM, CARVIA, OP_ASSAI)
  ja gerenciadas pela tabela `entregas_monitoradas.origem`.
- Upsert parcial: campos TECNICOS (cliente, transportadora, data_embarque,
  valor_nf, municipio, uf) sao sempre atualizados; campos OPERACIONAIS
  preenchidos pelo operador (data_agenda, canhoto, status_finalizacao,
  entregue, observacoes_operacionais) NAO sao sobrescritos.
- Nao bloqueante: callers envolvem em try/except para nao quebrar fluxo.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import func

from app import db
from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
from app.embarques.models import Embarque, EmbarqueItem
from app.vinculos.models import CidadeAtendida
from app.transportadoras.models import Transportadora
from app.utils.timezone import agora_utc_naive
from app.utils.sincronizar_entregas import adicionar_dias_uteis

logger = logging.getLogger(__name__)


def _get_usuario_nome():
    """Nome do usuario atual ou fallback (igual sincronizar_entregas.py)."""
    try:
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            return current_user.nome
    except (AttributeError, RuntimeError):
        pass
    return "Sistema - Op. Assai"


def sincronizar_entrega_op_assai_por_nf(numero_nf: str) -> Optional[EntregaMonitorada]:
    """Upsert EntregaMonitorada (origem='OP_ASSAI') a partir de AssaiNfQpa.

    Args:
        numero_nf: AssaiNfQpa.numero (NF Q.P.A. importada)

    Returns:
        EntregaMonitorada atualizada/criada, ou None se:
          - AssaiNfQpa nao existe / status_match != BATEU
          - AssaiSeparacao nao espelhada (sem linha em separacao)
    """
    from app.motos_assai.models import (
        AssaiNfQpa, AssaiSeparacao, AssaiLoja,
        NF_STATUS_BATEU,
    )
    from app.motos_assai.services.separacao_mirror_service import lote_id_de

    nf_qpa = (
        AssaiNfQpa.query
        .filter_by(numero=numero_nf, status_match=NF_STATUS_BATEU)
        .order_by(AssaiNfQpa.id.desc())
        .first()
    )
    if not nf_qpa:
        logger.debug(
            'sincronizar_entrega_op_assai_por_nf: NF %s nao encontrada em '
            'AssaiNfQpa com BATEU — skip', numero_nf,
        )
        return None

    assai_sep = (
        AssaiSeparacao.query.get(nf_qpa.separacao_id)
        if nf_qpa.separacao_id else None
    )
    if not assai_sep:
        logger.warning(
            'sincronizar_entrega_op_assai_por_nf: NF %s sem AssaiSeparacao '
            'vinculada — skip', numero_nf,
        )
        return None

    loja = AssaiLoja.query.get(assai_sep.loja_id) if assai_sep.loja_id else None

    entrega = EntregaMonitorada.query.filter_by(
        numero_nf=str(numero_nf), origem='OP_ASSAI',
    ).first()
    is_new = entrega is None
    if is_new:
        entrega = EntregaMonitorada(
            numero_nf=str(numero_nf),
            origem='OP_ASSAI',
            cliente=(loja.razao_social if loja else '-') or '-',
            criado_por=_get_usuario_nome(),
        )
        db.session.add(entrega)

    # Campos TECNICOS — sempre atualizados
    if loja:
        entrega.cliente = loja.razao_social or entrega.cliente or '-'
        entrega.cnpj_cliente = loja.cnpj
        entrega.municipio = loja.cidade
        entrega.uf = loja.uf
    entrega.valor_nf = float(nf_qpa.valor_total or 0)
    entrega.data_faturamento = nf_qpa.data_emissao
    # Op. Assai nao tem vendedor (B2B contrato Q.P.A.)
    entrega.vendedor = entrega.vendedor  # preserva valor manual se existir

    # Buscar EmbarqueItem do lote para extrair embarque/data/transportadora
    lote_id = lote_id_de(assai_sep.id)
    item_emb = (
        db.session.query(EmbarqueItem)
        .join(Embarque, Embarque.id == EmbarqueItem.embarque_id)
        .filter(
            EmbarqueItem.separacao_lote_id == lote_id,
            EmbarqueItem.status == 'ativo',
            Embarque.status == 'ativo',
        )
        .order_by(Embarque.id.desc())
        .first()
    )

    embarque: Optional[Embarque] = None
    data_agenda_embarque = None
    protocolo_embarque = None

    if item_emb:
        embarque = item_emb.embarque
        if embarque:
            entrega.data_embarque = embarque.data_embarque or entrega.data_embarque
            if embarque.transportadora:
                entrega.transportadora = embarque.transportadora.razao_social or '-'
            else:
                entrega.transportadora = entrega.transportadora or '-'

        entrega.separacao_lote_id = entrega.separacao_lote_id or item_emb.separacao_lote_id

        if item_emb.data_agenda:
            try:
                data_agenda_embarque = datetime.strptime(
                    item_emb.data_agenda, "%d/%m/%Y"
                ).date()
            except (ValueError, TypeError):
                data_agenda_embarque = None
            # Se a entrega nao tem data_agenda, herda do EmbarqueItem
            if (not entrega.data_agenda) and data_agenda_embarque:
                entrega.data_agenda = data_agenda_embarque

        protocolo_embarque = (item_emb.protocolo_agendamento or '').strip() or None
    else:
        entrega.transportadora = entrega.transportadora or '-'

    # Cria AgendamentoEntrega se ainda nao existe (espelha sincronizar Nacom)
    if data_agenda_embarque:
        ja_existe = any(a.data_agendada for a in entrega.agendamentos)
        if not ja_existe:
            confirmado = getattr(item_emb, 'agendamento_confirmado', False) if item_emb else False
            ag = AgendamentoEntrega(
                entrega=entrega,
                data_agendada=data_agenda_embarque,
                forma_agendamento='Embarque Op. Assai',
                autor=_get_usuario_nome(),
                status='confirmado' if confirmado else 'aguardando',
                protocolo_agendamento=protocolo_embarque,
            )
            if confirmado:
                ag.confirmado_por = _get_usuario_nome()
                ag.confirmado_em = agora_utc_naive()
            db.session.add(ag)

    # data_entrega_prevista via lead_time (CidadeAtendida) ou data_agenda
    if entrega.data_agenda:
        if entrega.data_entrega_prevista != entrega.data_agenda:
            entrega.data_entrega_prevista = entrega.data_agenda
    elif embarque and embarque.data_embarque and item_emb and embarque.transportadora:
        try:
            cnpj_transp = embarque.transportadora.cnpj
            uf_dest = item_emb.uf_destino
            nome_cid = item_emb.cidade_destino
            assoc = (
                CidadeAtendida.query
                .join(Transportadora)
                .filter(
                    func.upper(Transportadora.cnpj) == func.upper(cnpj_transp),
                    func.upper(CidadeAtendida.uf) == func.upper(uf_dest or ''),
                    func.upper(CidadeAtendida.nome) == func.upper(nome_cid or ''),
                )
                .first()
            )
            lead = int(getattr(assoc, 'lead_time', 0) or 0) if assoc else 0
            if lead > 0:
                entrega.lead_time = lead
                entrega.data_entrega_prevista = adicionar_dias_uteis(
                    embarque.data_embarque, lead
                )
        except Exception as e:
            logger.warning('OP_ASSAI lead_time: %s', e)

    db.session.flush()
    return entrega


def sincronizar_entregas_op_assai_por_embarque(embarque_id: int) -> int:
    """Sincroniza TODAS as entregas Op. Assai de um embarque.

    Usado em gatilho de portaria (apos data_embarque preenchida).
    Itera EmbarqueItem com `separacao_lote_id ASSAI-SEP-%` e chama
    `sincronizar_entrega_op_assai_por_nf` para cada NF.

    IMPORTANTE (code review 2026-05-11): esta funcao NAO faz `commit()`.
    A responsabilidade do `commit` e do CALLER (geralmente portaria
    `registrar_movimento` ou outro service transacional). Commit
    interno causava split-brain quando o caller fazia rollback apos —
    parte das EntregaMonitorada ficavam orfas.

    Returns:
        int: quantidade de entregas sincronizadas (apenas staged via flush).
    """
    itens = EmbarqueItem.query.filter(
        EmbarqueItem.embarque_id == embarque_id,
        EmbarqueItem.status == 'ativo',
        EmbarqueItem.separacao_lote_id.ilike('ASSAI-SEP-%'),
        EmbarqueItem.nota_fiscal.isnot(None),
    ).all()
    sincronizadas = 0
    for item in itens:
        try:
            r = sincronizar_entrega_op_assai_por_nf(item.nota_fiscal)
            if r is not None:
                sincronizadas += 1
        except Exception as e:
            logger.error(
                'sincronizar_entregas_op_assai_por_embarque: erro NF %s: %s',
                item.nota_fiscal, e, exc_info=True,
            )
    # Commit removido — caller controla transacao.
    return sincronizadas
