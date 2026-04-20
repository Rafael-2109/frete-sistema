"""Devolucao de motos ao fornecedor (Motochefe).

Fluxo (UI multi-step — criacao e adicao de itens em telas separadas):
    1. criar_devolucao (ABERTA) — seleciona loja + motivo (+ NF entrada de ref).
    2. adicionar_item (chassi N por devolucao, 1 por vez via form).
    3. enviar_devolucao (ENVIADA) — emite evento DEVOLVIDA em cada chassi.
    4. confirmar_devolucao (CONFIRMADA) — fornecedor recebeu.
    5. cancelar_devolucao (CANCELADA) — reverte eventos.

Fluxo programatico (atomico — quando um caller ja tem a lista completa):
    - criar_devolucao_com_itens() — cria header + N itens em 1 commit.
      Preferir este em codigo novo. O multi-step e mantido para a UI onde o
      operador digita 1 chassi por vez.

Observacao sobre devolucoes ABERTAS sem itens: o fluxo UI pode deixar uma
devolucao sem itens se o operador abandonar a tela. `enviar_devolucao` recusa
enviar sem itens, entao nao ha risco funcional — mas a lista de devolucoes
pode acumular "lixo". Limpeza e um follow-up.

HoraMoto e insert-once (invariante 3). Status atual vem do ultimo evento.
"""
from __future__ import annotations

from typing import List, Optional

from app import db
from app.hora.models import (
    HoraDevolucaoFornecedor,
    HoraDevolucaoFornecedorItem,
    HoraLoja,
    HoraMoto,
    HoraNfEntrada,
)
from app.hora.services.moto_service import registrar_evento, status_atual
from app.utils.timezone import agora_utc_naive


MOTIVOS_VALIDOS = {
    'CHASSI_EXTRA',
    'MODELO_DIFERENTE',
    'COR_DIFERENTE',
    'MOTOR_DIFERENTE',
    'AVARIA_FISICA',
    'OUTROS',
}

STATUS_VALIDOS = {'ABERTA', 'ENVIADA', 'CONFIRMADA', 'CANCELADA'}


def criar_devolucao(
    loja_id: int,
    motivo: str,
    nf_entrada_id: Optional[int] = None,
    observacoes: Optional[str] = None,
    criado_por: Optional[str] = None,
) -> HoraDevolucaoFornecedor:
    if motivo not in MOTIVOS_VALIDOS:
        raise ValueError(f'motivo invalido: {motivo}. Aceitos: {MOTIVOS_VALIDOS}')
    if not HoraLoja.query.get(loja_id):
        raise ValueError(f'loja {loja_id} nao encontrada')
    if nf_entrada_id and not HoraNfEntrada.query.get(nf_entrada_id):
        raise ValueError(f'NF {nf_entrada_id} nao encontrada')

    dev = HoraDevolucaoFornecedor(
        loja_id=loja_id,
        nf_entrada_id=nf_entrada_id,
        motivo=motivo,
        observacoes=observacoes,
        status='ABERTA',
        data_devolucao=agora_utc_naive().date(),
        criado_por=criado_por,
    )
    db.session.add(dev)
    db.session.commit()
    return dev


def criar_devolucao_com_itens(
    loja_id: int,
    motivo: str,
    itens: List[dict],
    nf_entrada_id: Optional[int] = None,
    observacoes: Optional[str] = None,
    criado_por: Optional[str] = None,
) -> HoraDevolucaoFornecedor:
    """Atomico: cria header + N itens em 1 commit.

    `itens` = [{'numero_chassi': str, 'motivo_especifico'?: str,
                'recebimento_conferencia_id'?: int}, ...]

    Usar em codigo novo (ex: resolucao_service). A UI 2-step (criar_devolucao
    sem itens + adicionar_item) e mantida para o fluxo operador.
    """
    if motivo not in MOTIVOS_VALIDOS:
        raise ValueError(f'motivo invalido: {motivo}. Aceitos: {MOTIVOS_VALIDOS}')
    if not HoraLoja.query.get(loja_id):
        raise ValueError(f'loja {loja_id} nao encontrada')
    if nf_entrada_id and not HoraNfEntrada.query.get(nf_entrada_id):
        raise ValueError(f'NF {nf_entrada_id} nao encontrada')
    if not itens:
        raise ValueError('Informe pelo menos 1 item.')

    dev = HoraDevolucaoFornecedor(
        loja_id=loja_id,
        nf_entrada_id=nf_entrada_id,
        motivo=motivo,
        observacoes=observacoes,
        status='ABERTA',
        data_devolucao=agora_utc_naive().date(),
        criado_por=criado_por,
    )
    db.session.add(dev)
    db.session.flush()  # gera dev.id sem commitar

    vistos = set()
    for it in itens:
        chassi = (it.get('numero_chassi') or '').strip().upper()
        if not chassi:
            raise ValueError('Item sem numero_chassi.')
        if chassi in vistos:
            raise ValueError(f'chassi {chassi} duplicado no lote.')
        vistos.add(chassi)
        if not HoraMoto.query.get(chassi):
            raise ValueError(f'chassi {chassi} nao existe em hora_moto')
        db.session.add(HoraDevolucaoFornecedorItem(
            devolucao_id=dev.id,
            numero_chassi=chassi,
            motivo_especifico=it.get('motivo_especifico'),
            recebimento_conferencia_id=it.get('recebimento_conferencia_id'),
        ))

    db.session.commit()
    return dev


def adicionar_item(
    devolucao_id: int,
    numero_chassi: str,
    motivo_especifico: Optional[str] = None,
    recebimento_conferencia_id: Optional[int] = None,
) -> HoraDevolucaoFornecedorItem:
    dev = HoraDevolucaoFornecedor.query.get(devolucao_id)
    if not dev:
        raise ValueError(f'devolucao {devolucao_id} nao encontrada')
    if dev.status != 'ABERTA':
        raise ValueError(
            f'devolucao {devolucao_id} nao esta ABERTA (status={dev.status})'
        )

    chassi = numero_chassi.strip().upper()
    moto = HoraMoto.query.get(chassi)
    if not moto:
        raise ValueError(f'chassi {chassi} nao existe em hora_moto')

    dup = (
        HoraDevolucaoFornecedorItem.query
        .filter_by(devolucao_id=devolucao_id, numero_chassi=chassi)
        .first()
    )
    if dup:
        raise ValueError(f'chassi {chassi} ja esta nesta devolucao')

    item = HoraDevolucaoFornecedorItem(
        devolucao_id=devolucao_id,
        numero_chassi=chassi,
        motivo_especifico=motivo_especifico,
        recebimento_conferencia_id=recebimento_conferencia_id,
    )
    db.session.add(item)
    db.session.commit()
    return item


def remover_item(devolucao_id: int, item_id: int) -> None:
    dev = HoraDevolucaoFornecedor.query.get(devolucao_id)
    if not dev:
        raise ValueError(f'devolucao {devolucao_id} nao encontrada')
    if dev.status != 'ABERTA':
        raise ValueError(f'devolucao nao esta ABERTA')
    item = HoraDevolucaoFornecedorItem.query.get(item_id)
    if not item or item.devolucao_id != devolucao_id:
        raise ValueError(f'item {item_id} nao pertence a devolucao {devolucao_id}')
    db.session.delete(item)
    db.session.commit()


def enviar_devolucao(
    devolucao_id: int,
    nf_saida_numero: Optional[str] = None,
    nf_saida_chave_44: Optional[str] = None,
    operador: Optional[str] = None,
) -> HoraDevolucaoFornecedor:
    """Marca ENVIADA e emite evento DEVOLVIDA em cada chassi."""
    dev = HoraDevolucaoFornecedor.query.get(devolucao_id)
    if not dev:
        raise ValueError(f'devolucao {devolucao_id} nao encontrada')
    if dev.status != 'ABERTA':
        raise ValueError(f'devolucao nao esta ABERTA (status={dev.status})')
    if not dev.itens:
        raise ValueError('devolucao sem itens')

    dev.status = 'ENVIADA'
    dev.data_envio = agora_utc_naive().date()
    if nf_saida_numero:
        dev.nf_saida_numero = nf_saida_numero
    if nf_saida_chave_44:
        # Valida unicidade
        chave = nf_saida_chave_44.strip()
        if len(chave) != 44:
            raise ValueError('nf_saida_chave_44 deve ter 44 caracteres')
        dup = (
            HoraDevolucaoFornecedor.query
            .filter(
                HoraDevolucaoFornecedor.nf_saida_chave_44 == chave,
                HoraDevolucaoFornecedor.id != dev.id,
            )
            .first()
        )
        if dup:
            raise ValueError(f'chave {chave} ja usada em devolucao #{dup.id}')
        dev.nf_saida_chave_44 = chave

    # Emite eventos DEVOLVIDA
    for item in dev.itens:
        registrar_evento(
            numero_chassi=item.numero_chassi,
            tipo='DEVOLVIDA',
            origem_tabela='hora_devolucao_fornecedor_item',
            origem_id=item.id,
            loja_id=dev.loja_id,
            operador=operador,
            detalhe=f'Devolucao #{dev.id} motivo={dev.motivo}',
        )
    db.session.commit()
    return dev


def confirmar_devolucao(devolucao_id: int) -> HoraDevolucaoFornecedor:
    dev = HoraDevolucaoFornecedor.query.get(devolucao_id)
    if not dev:
        raise ValueError(f'devolucao {devolucao_id} nao encontrada')
    if dev.status != 'ENVIADA':
        raise ValueError(f'devolucao nao esta ENVIADA (status={dev.status})')
    dev.status = 'CONFIRMADA'
    dev.data_confirmacao = agora_utc_naive().date()
    db.session.commit()
    return dev


def cancelar_devolucao(
    devolucao_id: int,
    operador: Optional[str] = None,
) -> HoraDevolucaoFornecedor:
    """Cancela. Se estava ENVIADA/CONFIRMADA, emite evento de reposicao (CONFERIDA)
    para trazer o chassi de volta ao estoque."""
    dev = HoraDevolucaoFornecedor.query.get(devolucao_id)
    if not dev:
        raise ValueError(f'devolucao {devolucao_id} nao encontrada')
    if dev.status == 'CANCELADA':
        raise ValueError('devolucao ja esta cancelada')

    status_anterior = dev.status
    dev.status = 'CANCELADA'

    skipped = []
    if status_anterior in ('ENVIADA', 'CONFIRMADA'):
        # Reemite CONFERIDA para cada chassi cuja DEVOLVIDA ainda e o ultimo
        # evento (traz de volta para o estoque). Se ja teve evento posterior
        # (ex: VENDIDA, AVARIADA, FALTANDO_PECA), pula para nao corromper o
        # estado atual da moto.
        for item in dev.itens:
            ult = status_atual(item.numero_chassi)
            if ult != 'DEVOLVIDA':
                skipped.append((item.numero_chassi, ult))
                continue
            registrar_evento(
                numero_chassi=item.numero_chassi,
                tipo='CONFERIDA',
                origem_tabela='hora_devolucao_fornecedor_item',
                origem_id=item.id,
                loja_id=dev.loja_id,
                operador=operador,
                detalhe=f'Cancelamento devolucao #{dev.id}',
            )
    db.session.commit()
    if skipped:
        # Anota nas observacoes para auditoria (nao bloqueia o fluxo)
        nota = '\n[CANCELAMENTO] Chassis com evento posterior (NAO restaurados): ' + \
               ', '.join(f'{c}={st}' for c, st in skipped)
        dev.observacoes = ((dev.observacoes or '') + nota).strip()
        db.session.commit()
    return dev


def listar_devolucoes(
    loja_id: Optional[int] = None,
    status: Optional[str] = None,
    lojas_permitidas_ids: Optional[List[int]] = None,
    limit: int = 200,
) -> List[HoraDevolucaoFornecedor]:
    q = HoraDevolucaoFornecedor.query.order_by(
        HoraDevolucaoFornecedor.data_devolucao.desc(),
        HoraDevolucaoFornecedor.id.desc(),
    )
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        q = q.filter(HoraDevolucaoFornecedor.loja_id.in_(lojas_permitidas_ids))
    if loja_id:
        q = q.filter(HoraDevolucaoFornecedor.loja_id == loja_id)
    if status:
        q = q.filter(HoraDevolucaoFornecedor.status == status)
    return q.limit(limit).all()
