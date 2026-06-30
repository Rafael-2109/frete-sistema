"""Service de Troca em Garantia (Motos Assai).

Cliente final do Assai troca a moto defeituosa A por outra B (mesmo modelo,
cor pode variar), SEM NF. Modelagem: swap A->B na propria NF Q.P.A. —
B vira FATURADA (assume o slot de A na NF e na separacao), A vira PENDENTE
(volta ao estoque). Registro centralizado no pos-venda
(AssaiPosVendaOcorrencia tipo=TROCA_GARANTIA, com chassi_substituto e nf_qpa_id).

Swap CIRURGICO (spec 2026-06-30 §5.1): NAO usa _calcular_match (ignora seps
FATURADA) nem sincronizar_espelho_com_separacao (delta bloqueado por numero_nf).
"""
from __future__ import annotations

from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiNfQpa, AssaiNfQpaItem, AssaiNfQpaItemVinculoHistorico,
    AssaiSeparacaoItem, AssaiPosVendaOcorrencia,
    EVENTO_FATURADA, EVENTO_PENDENTE, EVENTO_SEPARADA, EVENTO_DISPONIVEL,
    NF_STATUS_CANCELADA,
    VINCULO_MOTIVO_TROCA_GARANTIA, TIPO_TROCA_GARANTIA, CATEGORIA_CLIENTE,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo
from app.motos_assai.services.separacao_mirror_service import trocar_chassi_no_espelho
from app.utils.timezone import agora_brasil_naive


class TrocaGarantiaError(Exception):
    """Erro de validacao/execucao da troca em garantia."""


def _validar(nf_id, chassi_a, chassi_b):
    """Valida pre-condicoes. Retorna (nf, nf_item, sep_item, moto_a, moto_b)
    ou levanta TrocaGarantiaError."""
    chassi_a = (chassi_a or '').strip().upper()
    chassi_b = (chassi_b or '').strip().upper()
    if not chassi_a or not chassi_b:
        raise TrocaGarantiaError('chassi_a e chassi_b sao obrigatorios')
    if chassi_a == chassi_b:
        raise TrocaGarantiaError('chassi_a e chassi_b nao podem ser iguais')

    nf = AssaiNfQpa.query.get(nf_id)
    if not nf:
        raise TrocaGarantiaError(f'NF {nf_id} nao encontrada')
    if nf.status_match == NF_STATUS_CANCELADA:
        raise TrocaGarantiaError(f'NF {nf_id} esta CANCELADA — nao permite troca')

    nf_item = AssaiNfQpaItem.query.filter_by(nf_id=nf_id, chassi=chassi_a).first()
    if not nf_item:
        raise TrocaGarantiaError(f'chassi {chassi_a} nao consta na NF {nf_id}')
    if not nf_item.separacao_item_id:
        raise TrocaGarantiaError(
            f'chassi {chassi_a} na NF {nf_id} sem vinculo de separacao (separacao_item_id nulo)'
        )
    if status_efetivo(chassi_a) != EVENTO_FATURADA:
        raise TrocaGarantiaError(
            f'chassi {chassi_a} nao esta FATURADA (estado={status_efetivo(chassi_a)})'
        )

    if status_efetivo(chassi_b) != EVENTO_DISPONIVEL:
        raise TrocaGarantiaError(
            f'chassi substituto {chassi_b} nao esta DISPONIVEL '
            f'(estado={status_efetivo(chassi_b)})'
        )

    moto_a = AssaiMoto.query.filter_by(chassi=chassi_a).first()
    moto_b = AssaiMoto.query.filter_by(chassi=chassi_b).first()
    if not moto_a or not moto_b:
        raise TrocaGarantiaError('moto A ou B nao cadastrada em assai_moto')
    if moto_a.modelo_id != moto_b.modelo_id:
        raise TrocaGarantiaError(
            f'modelo divergente: A={moto_a.modelo_id} != B={moto_b.modelo_id}'
        )

    sep_item = AssaiSeparacaoItem.query.get(nf_item.separacao_item_id)
    if not sep_item:
        raise TrocaGarantiaError('AssaiSeparacaoItem do chassi A nao encontrado')

    return nf, nf_item, sep_item, moto_a, moto_b


def registrar_troca(*, nf_id, chassi_a, chassi_b, operador_id, motivo, dry_run=True):
    """Registra uma troca em garantia A->B.

    dry_run=True (default): valida e retorna o plano, sem escrever.
    """
    chassi_a = (chassi_a or '').strip().upper()
    chassi_b = (chassi_b or '').strip().upper()
    motivo = (motivo or '').strip()
    if not motivo:
        raise TrocaGarantiaError('motivo (descricao do defeito) obrigatorio')

    nf, nf_item, sep_item, moto_a, moto_b = _validar(nf_id, chassi_a, chassi_b)
    sep_id = sep_item.separacao_id

    plano = [
        f'NF {nf.numero}: item {chassi_a} -> {chassi_b} (vinculo TROCA_GARANTIA)',
        f'AssaiSeparacaoItem #{sep_item.id}: chassi {chassi_a} -> {chassi_b}',
        f'evento: {chassi_b} SEPARADA + FATURADA',
        f'evento: {chassi_a} PENDENTE (volta ao estoque)',
        f'espelho Nacom (sep {sep_id}): chassi_assai {chassi_a} -> {chassi_b}',
        'cria AssaiPosVendaOcorrencia TROCA_GARANTIA (CLIENTE)',
    ]

    if dry_run:
        return {
            'ok': True, 'dry_run': True, 'nf_id': nf.id, 'nf_numero': nf.numero,
            'chassi_a': chassi_a, 'chassi_b': chassi_b, 'sep_id': sep_id,
            'ocorrencia_id': None, 'plano': plano,
        }

    # Lock pessimista nas duas motos (anti-corrida)
    # `of=AssaiMoto` evita erro "FOR UPDATE cannot be applied to nullable side
    # of an outer join" que ocorre quando o modelo tem relationship carregado.
    db.session.query(AssaiMoto).filter(
        AssaiMoto.chassi.in_([chassi_a, chassi_b])
    ).with_for_update(of=AssaiMoto).all()

    # Re-valida sob o lock (anti-TOCTOU): o estado pode ter mudado entre o
    # _validar (sem lock) e a aquisicao do lock. Mirror de separacao_service.py:304-308.
    if status_efetivo(chassi_a) != EVENTO_FATURADA:
        raise TrocaGarantiaError(
            f'chassi {chassi_a} deixou de estar FATURADA antes do lock '
            f'(estado={status_efetivo(chassi_a)}) — troca abortada'
        )
    if status_efetivo(chassi_b) != EVENTO_DISPONIVEL:
        raise TrocaGarantiaError(
            f'chassi substituto {chassi_b} deixou de estar DISPONIVEL antes do lock '
            f'(estado={status_efetivo(chassi_b)}) — troca abortada'
        )

    # 1) Vinculo historico (auditoria do swap na NF) — antes de mudar o item
    db.session.add(AssaiNfQpaItemVinculoHistorico(
        nf_qpa_item_id=nf_item.id,
        separacao_item_id=sep_item.id,
        motivo=VINCULO_MOTIVO_TROCA_GARANTIA,
        chassi_no_momento=chassi_a,
        registrado_por_id=operador_id,
        detalhes={'chassi_novo': chassi_b, 'nf_id': nf.id, 'motivo': motivo},
    ))

    # 2) Muta o slot de separacao A->B (preserva valor/modelo/sep) e religa a NF
    sep_item.chassi = chassi_b
    nf_item.chassi = chassi_b
    nf_item.tipo_divergencia = None
    # nf_item.separacao_item_id mantido — ja aponta para o slot (agora B)

    # 3) Eventos: B passa a ser a vendida (SEPARADA->FATURADA); A volta PENDENTE
    extras_b = {'origem': 'troca_garantia', 'nf_id': nf.id, 'chassi_substituido': chassi_a}
    emitir_evento(chassi_b, EVENTO_SEPARADA, operador_id=operador_id,
                  observacao=f'Troca garantia NF {nf.numero}', dados_extras=extras_b)
    emitir_evento(chassi_b, EVENTO_FATURADA, operador_id=operador_id,
                  observacao=f'Troca garantia NF {nf.numero}', dados_extras=extras_b)
    emitir_evento(chassi_a, EVENTO_PENDENTE, operador_id=operador_id,
                  observacao=f'Troca garantia NF {nf.numero}: substituida por {chassi_b}',
                  dados_extras={'origem': 'troca_garantia', 'nf_id': nf.id,
                                'chassi_substituto': chassi_b})

    # 4) Espelho Nacom in-place (preserva numero_nf — sem leg nova de frete)
    trocar_chassi_no_espelho(sep_id, chassi_a, chassi_b)

    # 5) Registro de pos-venda (centralizado)
    oc = AssaiPosVendaOcorrencia(
        chassi=chassi_a, categoria=CATEGORIA_CLIENTE, descricao=motivo,
        tipo=TIPO_TROCA_GARANTIA, chassi_substituto=chassi_b, nf_qpa_id=nf.id,
        criado_em=agora_brasil_naive(), criado_por_id=operador_id,
    )
    db.session.add(oc)
    db.session.flush()

    db.session.commit()

    return {
        'ok': True, 'dry_run': False, 'nf_id': nf.id, 'nf_numero': nf.numero,
        'chassi_a': chassi_a, 'chassi_b': chassi_b, 'sep_id': sep_id,
        'ocorrencia_id': oc.id, 'plano': plano,
    }
