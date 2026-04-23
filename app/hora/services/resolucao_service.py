"""Resolucao pos-recebimento de divergencias.

Cada linha de HoraRecebimentoConferencia com tipo_divergencia != NULL
pode ser tratada por uma acao:

    ACEITAR       -> registra nota de aceitacao (sem mudar estado)
    DEVOLVER      -> cria/anexa em devolucao fornecedor
    MARCAR_AVARIA -> emite evento AVARIADA na moto
    PECA_FALTANDO -> cria pendencia hora_peca_faltando + evento FALTANDO_PECA
    DESCARTAR     -> emite evento DEVOLVIDA com motivo=DESCARTE (sai do estoque)
"""
from __future__ import annotations

from typing import Optional

from app import db
from app.hora.models import (
    HoraDevolucaoFornecedor,
    HoraRecebimento,
    HoraRecebimentoConferencia,
)
from app.hora.services import devolucao_service, peca_service
from app.hora.services.moto_service import registrar_evento


ACOES_VALIDAS = {
    'ACEITAR',
    'DEVOLVER',
    'MARCAR_AVARIA',
    'PECA_FALTANDO',
    'DESCARTAR',
}


def listar_divergencias(recebimento_id: int):
    """Retorna conferencias com divergencia pendente de resolucao.

    "Pendente" = ainda sem evento de resolucao posterior
    (heuristica leve: todas as divergencias aparecem; UI destaca status).
    """
    rec = HoraRecebimento.query.get(recebimento_id)
    if not rec:
        raise ValueError(f'recebimento {recebimento_id} nao encontrado')
    # Ativas (nao substituidas) que tenham: (a) tipo_divergencia snapshot OU
    # (b) ao menos 1 linha em hora_conferencia_divergencia (1-N pos-redesign).
    divergencias = [
        c for c in rec.conferencias
        if not c.substituida and (c.tipo_divergencia or c.divergencias)
    ]
    return divergencias


def resolver_divergencia(
    conferencia_id: int,
    acao: str,
    motivo: Optional[str] = None,
    observacoes: Optional[str] = None,
    devolucao_id: Optional[int] = None,
    descricao_peca: Optional[str] = None,
    operador: Optional[str] = None,
) -> dict:
    """Aplica uma acao sobre uma conferencia de divergencia.

    Args:
        conferencia_id: id da conferencia.
        acao: uma das ACOES_VALIDAS.
        motivo: rotulo livre (opcional).
        observacoes: texto complementar.
        devolucao_id: se acao=DEVOLVER e ja existe devolucao ABERTA,
            reusar; se None, cria nova.
        descricao_peca: obrigatorio se acao=PECA_FALTANDO.
        operador: quem executou.
    """
    if acao not in ACOES_VALIDAS:
        raise ValueError(f'acao invalida: {acao}. Aceitos: {ACOES_VALIDAS}')

    conf = HoraRecebimentoConferencia.query.get(conferencia_id)
    if not conf:
        raise ValueError(f'conferencia {conferencia_id} nao encontrada')
    rec = HoraRecebimento.query.get(conf.recebimento_id)

    if acao == 'ACEITAR':
        detalhe = (
            f'Divergencia aceita ({conf.tipo_divergencia}). '
            f'{observacoes or motivo or ""}'
        ).strip()
        # Append em detalhe_divergencia para auditoria
        conf.detalhe_divergencia = (
            (conf.detalhe_divergencia or '') + f'\n[ACEITA] {detalhe}'
        ).strip()
        db.session.commit()
        return {'ok': True, 'acao': acao, 'conferencia_id': conferencia_id}

    if acao == 'MARCAR_AVARIA':
        registrar_evento(
            numero_chassi=conf.numero_chassi,
            tipo='AVARIADA',
            origem_tabela='hora_recebimento_conferencia',
            origem_id=conf.id,
            loja_id=rec.loja_id if rec else None,
            operador=operador,
            detalhe=(observacoes or motivo or 'Avaria registrada'),
        )
        db.session.commit()
        return {'ok': True, 'acao': acao, 'conferencia_id': conferencia_id}

    if acao == 'PECA_FALTANDO':
        if not descricao_peca or not descricao_peca.strip():
            raise ValueError('descricao_peca e obrigatorio para acao PECA_FALTANDO')
        peca = peca_service.registrar_peca_faltando(
            numero_chassi=conf.numero_chassi,
            descricao=descricao_peca,
            recebimento_conferencia_id=conf.id,
            loja_id=rec.loja_id if rec else None,
            observacoes=observacoes,
            criado_por=operador,
        )
        return {
            'ok': True,
            'acao': acao,
            'conferencia_id': conferencia_id,
            'peca_faltando_id': peca.id,
        }

    if acao == 'DEVOLVER':
        if not rec:
            raise ValueError('Recebimento nao encontrado para devolver.')
        # Reusa devolucao ABERTA existente ou cria nova ATOMICAMENTE (header + item).
        if devolucao_id:
            dev = HoraDevolucaoFornecedor.query.get(devolucao_id)
            if not dev:
                raise ValueError(f'devolucao {devolucao_id} nao encontrada')
            if dev.status != 'ABERTA':
                raise ValueError(f'devolucao {devolucao_id} nao esta ABERTA')
            # devolucao existente: so adiciona item (commit isolado aceitavel,
            # header ja foi comitado)
            item = devolucao_service.adicionar_item(
                devolucao_id=dev.id,
                numero_chassi=conf.numero_chassi,
                motivo_especifico=motivo or conf.detalhe_divergencia,
                recebimento_conferencia_id=conf.id,
            )
            return {
                'ok': True,
                'acao': acao,
                'conferencia_id': conferencia_id,
                'devolucao_id': dev.id,
                'devolucao_item_id': item.id,
            }
        # Cria header + item em 1 transacao atomica
        dev = devolucao_service.criar_devolucao_com_itens(
            loja_id=rec.loja_id,
            motivo=conf.tipo_divergencia or 'OUTROS',
            itens=[{
                'numero_chassi': conf.numero_chassi,
                'motivo_especifico': motivo or conf.detalhe_divergencia,
                'recebimento_conferencia_id': conf.id,
            }],
            nf_entrada_id=rec.nf_id,
            observacoes=observacoes,
            criado_por=operador,
        )
        return {
            'ok': True,
            'acao': acao,
            'conferencia_id': conferencia_id,
            'devolucao_id': dev.id,
            'devolucao_item_id': dev.itens[0].id if dev.itens else None,
        }

    if acao == 'DESCARTAR':
        # Emite DEVOLVIDA (sai do estoque) com detalhe DESCARTE
        registrar_evento(
            numero_chassi=conf.numero_chassi,
            tipo='DEVOLVIDA',
            origem_tabela='hora_recebimento_conferencia',
            origem_id=conf.id,
            loja_id=rec.loja_id if rec else None,
            operador=operador,
            detalhe=f'DESCARTE: {observacoes or motivo or conf.tipo_divergencia}',
        )
        db.session.commit()
        return {'ok': True, 'acao': acao, 'conferencia_id': conferencia_id}

    raise ValueError(f'acao nao implementada: {acao}')
