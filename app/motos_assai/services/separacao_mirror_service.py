"""Espelhamento AssaiSeparacao -> linhas em `separacao` Nacom.

Padrao adotado em 2026-05-11 para integrar a Op. Assai no fluxo Nacom
(lista_pedidos / Cotacao / Embarque / Frete) sem alterar a VIEW pedidos.

## Como funciona

Quando uma `AssaiSeparacao` muda para `FECHADA`, este service cria N linhas
em `separacao` Nacom (1 linha por `AssaiSeparacaoItem`/chassi). A VIEW
`pedidos` Parte 1 ja agrega `separacao` por `separacao_lote_id`, entao a
separacao Assai aparece automaticamente em `lista_pedidos.html`.

Quando a `AssaiSeparacao` e cancelada, deletamos as linhas espelho.

## Convencoes

- `separacao_lote_id = 'ASSAI-SEP-{assai_sep_id}'` (prefix detectado em
  `Pedido.eh_op_assai`, `_is_op_assai_item`, `_apply_origem`).
- `num_pedido = '{pedido.numero_pedido}-{loja.numero}'` (formato decidido
  pelo usuario em 2026-05-11).
- `cnpj_cpf = loja.cnpj` (CNPJ da loja Assai destinataria).
- `cod_produto = modelo.codigo`, `nome_produto = modelo.nome` (visivel em
  detalhes / impressao de embarque).
- `qtd_saldo = 1` por chassi, `valor_saldo = item.valor_unitario_qpa`.
- `peso = modelo.peso_kg` (fisico), `pallet = 0` (motos nao palletizam).
- `status = 'ABERTO'` (listener atualiza para COTADO quando entra em
  embarque, FATURADO quando `numero_nf` for preenchido).

## Listeners do model Separacao Nacom

- `setar_falta_pagamento_inicial`: busca em CarteiraPrincipal pelo
  `num_pedido` — nao encontra (Op. Assai nao tem pedido Nacom). Resultado:
  `falta_pagamento=False` (default). Sem quebra.
- `atualizar_status_automatico`: recalcula status automaticamente. Op. Assai
  e tratada como pedido normal (ABERTO -> COTADO -> FATURADO).
- `recalcular_totais_embarque`: soma `peso/valor/pallet` do lote -> atualiza
  totais do EmbarqueItem. Funciona transparente.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.exc import IntegrityError

from app import db
from app.motos_assai.models import (
    AssaiSeparacao, AssaiSeparacaoItem, AssaiLoja, AssaiModelo,
    AssaiPedidoVenda, AssaiMoto,
)
from app.separacao.models import Separacao
from app.utils.timezone import agora_brasil_naive

logger = logging.getLogger(__name__)


class MirrorRaceError(Exception):
    """Outra transacao ja criou o espelho concorrentemente — UNIQUE partial
    index `uq_separacao_assai_lote_produto` rejeitou o INSERT."""


def lote_id_de(assai_sep_id: int) -> str:
    """Convencao do `separacao_lote_id` para uma AssaiSeparacao."""
    return f'ASSAI-SEP-{assai_sep_id}'


def num_pedido_de(pedido: AssaiPedidoVenda, loja: AssaiLoja) -> str:
    """Convencao do `num_pedido` Op. Assai: '{ped.numero_pedido}-{loja.numero}'."""
    return f'{pedido.numero_pedido}-{loja.numero}'


def mirror_assai_to_separacao(assai_sep_id: int) -> int:
    """Cria linhas em `separacao` Nacom espelhando uma AssaiSeparacao.

    Idempotente: se ja existem linhas com `separacao_lote_id=ASSAI-SEP-{id}`,
    NAO duplica — apenas garante consistencia. Util quando operador faz
    reabertura/refechamento da separacao.

    Pre-requisitos:
        - AssaiSeparacao deve existir
        - AssaiSeparacao.itens deve ter ao menos 1 chassi
        - Cada AssaiModelo dos itens deve ter `peso_kg` (warning se nao tem)

    Returns:
        int: numero de linhas em `separacao` criadas (0 se ja existiam).
    """
    sep = AssaiSeparacao.query.get(assai_sep_id)
    if not sep:
        raise ValueError(f'AssaiSeparacao {assai_sep_id} nao encontrada')

    lote_id = lote_id_de(assai_sep_id)
    pedido = sep.pedido
    loja = sep.loja

    if not pedido or not loja:
        raise ValueError(
            f'AssaiSeparacao {assai_sep_id} sem pedido ({pedido}) '
            f'ou loja ({loja}) — nao espelhada'
        )

    # Idempotencia: ja existem linhas?
    existentes = Separacao.query.filter_by(separacao_lote_id=lote_id).count()
    if existentes > 0:
        logger.info(
            'mirror_assai_to_separacao: lote %s ja tem %d linhas — skip',
            lote_id, existentes,
        )
        return 0

    items = (
        db.session.query(AssaiSeparacaoItem, AssaiMoto, AssaiModelo)
        .join(AssaiMoto, AssaiMoto.chassi == AssaiSeparacaoItem.chassi)
        .join(AssaiModelo, AssaiModelo.id == AssaiSeparacaoItem.modelo_id)
        .filter(AssaiSeparacaoItem.separacao_id == assai_sep_id)
        .all()
    )

    if not items:
        logger.warning(
            'mirror_assai_to_separacao: AssaiSeparacao %s sem itens — '
            'nada espelhado',
            assai_sep_id,
        )
        return 0

    num_pedido = num_pedido_de(pedido, loja)
    raz_social = loja.razao_social or loja.nome or f'Loja {loja.numero}'
    nome_cidade = loja.cidade or ''
    cod_uf = loja.uf or ''

    criadas = 0
    for item, _moto, modelo in items:
        peso_kg = float(modelo.peso_kg or 0)
        if not peso_kg:
            logger.warning(
                'mirror_assai_to_separacao: modelo %s sem peso_kg cadastrado '
                '(chassi %s) — usando 0. CADASTRE o peso antes de cotar.',
                modelo.codigo, item.chassi,
            )

        linha = Separacao(
            separacao_lote_id=lote_id,
            num_pedido=num_pedido,
            data_pedido=sep.iniciada_em.date() if sep.iniciada_em else None,
            cnpj_cpf=loja.cnpj,
            raz_social_red=raz_social,
            nome_cidade=nome_cidade,
            cod_uf=cod_uf,
            cidade_normalizada=nome_cidade,
            uf_normalizada=cod_uf,
            cod_produto=modelo.codigo,
            nome_produto=modelo.nome,
            qtd_saldo=1.0,
            valor_saldo=float(item.valor_unitario_qpa or 0),
            pallet=0.0,
            peso=peso_kg,
            rota=None,
            sub_rota=None,
            observ_ped_1=None,
            roteirizacao=None,
            expedicao=None,
            agendamento=None,
            agendamento_confirmado=False,
            protocolo=None,
            pedido_cliente=None,
            tags_pedido=None,
            tipo_envio='total',
            sincronizado_nf=False,
            numero_nf=None,
            status='ABERTO',  # listener corrige automaticamente
            nf_cd=False,
            data_embarque=None,
            falta_item=False,
            falta_pagamento=False,
            criado_em=agora_brasil_naive(),
            criado_por='Sistema Op. Assaí',
        )
        db.session.add(linha)
        criadas += 1

    try:
        db.session.flush()
    except IntegrityError as e:
        # Race condition: UNIQUE partial index `uq_separacao_assai_lote_produto`
        # rejeitou. Outra transacao ja criou o espelho. Rollback parcial e
        # retornar — caller deve usar o espelho existente.
        db.session.rollback()
        logger.warning(
            'mirror_assai_to_separacao: race detectada (UNIQUE constraint) '
            'para lote %s — espelho ja criado por outra transacao',
            lote_id,
        )
        raise MirrorRaceError(
            f'Espelho de lote {lote_id} ja criado concorrentemente'
        ) from e

    logger.info(
        'mirror_assai_to_separacao: %d linha(s) criada(s) em separacao '
        'para lote %s (pedido %s, loja %s)',
        criadas, lote_id, num_pedido, loja.numero,
    )
    return criadas


def unmirror_assai_separacao(assai_sep_id: int) -> int:
    """Remove linhas em `separacao` Nacom espelhando uma AssaiSeparacao.

    Chamado quando AssaiSeparacao e cancelada. Tambem deleta vinculacao com
    EmbarqueItem (ON DELETE? — Nao: EmbarqueItem.separacao_lote_id e
    VARCHAR sem FK. Linhas em separacao podem ser deletadas livremente).

    SEGURANCA: nao deleta se ja ha NF preenchida em qualquer linha do lote.
    Operador deve cancelar a NF antes (cenario: cancelar separacao apos
    faturamento).

    Returns:
        int: numero de linhas deletadas (0 se nao havia).
    """
    lote_id = lote_id_de(assai_sep_id)

    com_nf = (
        Separacao.query
        .filter_by(separacao_lote_id=lote_id)
        .filter(
            db.or_(
                Separacao.numero_nf.isnot(None),
                Separacao.sincronizado_nf == True,  # noqa: E712
            )
        )
        .count()
    )
    if com_nf > 0:
        raise ValueError(
            f'AssaiSeparacao {assai_sep_id} ja tem {com_nf} linha(s) com '
            'NF preenchida — cancele a NF antes de cancelar a separacao'
        )

    deletadas = Separacao.query.filter_by(
        separacao_lote_id=lote_id
    ).delete(synchronize_session=False)
    db.session.flush()

    logger.info(
        'unmirror_assai_separacao: %d linha(s) deletada(s) em separacao '
        'para lote %s',
        deletadas, lote_id,
    )
    return deletadas


def atualizar_nf_no_espelho(
    assai_sep_id: int, numero_nf: str,
    *, sincronizar: bool = False,
) -> int:
    """Preenche `numero_nf` em todas as linhas espelho do lote.

    Chamado quando AssaiNfQpa BATEU com a AssaiSeparacao. O listener
    `atualizar_status_automatico` da Separacao Nacom recalcula o status
    para FATURADO automaticamente (basta `numero_nf` preenchido — ver
    `app/separacao/models.py:atualizar_status_automatico`).

    CRITICAL (code review 2026-05-11): `sincronizar` default e FALSE
    porque o listener `recalcular_totais_embarque`
    (`app/separacao/models.py:recalcular_totais_embarque`) filtra
    `Separacao.sincronizado_nf == False` na agregacao de totais. Setar
    `sincronizado_nf=True` faria com que apos a propagacao da NF Q.P.A.
    o `EmbarqueItem.peso/valor/pallet` fosse ZERADO (a soma exclui
    linhas com `sincronizado_nf=True`). Para Op. Assai, NF Q.P.A. BATEU
    nao significa "saiu do escopo do embarque" como no fluxo Nacom — e
    apenas marcacao informacional. Status FATURADO ja vem via `numero_nf`
    preenchido.

    Args:
        assai_sep_id: id da AssaiSeparacao
        numero_nf: numero da NF Q.P.A.
        sincronizar: se True, seta `sincronizado_nf=True` (use APENAS se
            entender que vai zerar totais do EmbarqueItem associado).

    Returns:
        int: linhas atualizadas.
    """
    from app.utils.timezone import agora_utc_naive

    lote_id = lote_id_de(assai_sep_id)
    linhas = Separacao.query.filter_by(separacao_lote_id=lote_id).all()
    if not linhas:
        logger.warning(
            'atualizar_nf_no_espelho: lote %s sem linhas em separacao — '
            'AssaiSeparacao %s nao foi espelhada?',
            lote_id, assai_sep_id,
        )
        return 0

    agora = agora_utc_naive()
    for linha in linhas:
        linha.numero_nf = numero_nf
        if sincronizar:
            linha.sincronizado_nf = True
            linha.data_sincronizacao = agora

    db.session.flush()
    logger.info(
        'atualizar_nf_no_espelho: lote %s (AssaiSeparacao %s) -> '
        'numero_nf=%s em %d linha(s)',
        lote_id, assai_sep_id, numero_nf, len(linhas),
    )
    return len(linhas)


def remover_nf_do_espelho(assai_sep_id: int) -> int:
    """Limpa `numero_nf` + `sincronizado_nf` das linhas espelho do lote.

    Util quando NF Q.P.A. e cancelada/desvinculada (status_match volta a
    NAO_RECONCILIADO). Listener recalcula status (FATURADO -> COTADO).
    """
    lote_id = lote_id_de(assai_sep_id)
    linhas = Separacao.query.filter_by(separacao_lote_id=lote_id).all()
    if not linhas:
        return 0

    for linha in linhas:
        linha.numero_nf = None
        linha.sincronizado_nf = False
        linha.data_sincronizacao = None

    db.session.flush()
    logger.info(
        'remover_nf_do_espelho: lote %s (AssaiSeparacao %s) limpou NF em '
        '%d linha(s)',
        lote_id, assai_sep_id, len(linhas),
    )
    return len(linhas)


def assai_sep_id_de_lote(separacao_lote_id: Optional[str]) -> Optional[int]:
    """Extrai assai_sep_id de um separacao_lote_id 'ASSAI-SEP-{N}'.

    Returns None se nao for um lote Op. Assai.
    """
    if not separacao_lote_id or not isinstance(separacao_lote_id, str):
        return None
    prefix = 'ASSAI-SEP-'
    if not separacao_lote_id.startswith(prefix):
        return None
    try:
        return int(separacao_lote_id[len(prefix):])
    except (ValueError, TypeError):
        return None
