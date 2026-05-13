"""Cancelamento de NF Q.P.A. + aplicar correção CCe.

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md §9, §7.3
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase5-auxiliares.md Task 9

Funcoes:
- `cancelar_nf_qpa(nf_id, motivo, operador_id)` - reverte FATURADA -> CARREGADA/SEPARADA/DISPONIVEL
- `aplicar_correcao_cce(nf_id, chassis_corrigidos, numero_cce, operador_id)` - troca chassis em
  AssaiNfQpaItem + re-roda match
"""
from __future__ import annotations

from typing import List, Tuple

from app import db
from app.motos_assai.models import (
    AssaiNfQpa, AssaiNfQpaItem, AssaiNfQpaItemVinculoHistorico,
    AssaiCarregamento,
    SEPARACAO_STATUS_FECHADA, SEPARACAO_STATUS_CARREGADA,
    SEPARACAO_STATUS_FATURADA, NF_STATUS_CANCELADA,
    EVENTO_CARREGADA, EVENTO_SEPARADA, EVENTO_FATURADA,
    CARREGAMENTO_STATUS_FINALIZADO,
    VINCULO_MOTIVO_NF_CANCELADA, VINCULO_MOTIVO_CCE_ALTEROU_CHASSI,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo
from app.utils.timezone import agora_brasil_naive


class CancelamentoError(Exception):
    """Erro base de cancelamento_nf_service."""


class CancelamentoValidationError(CancelamentoError):
    """Validacao falhou (NF ja cancelada, motivo vazio, etc)."""


def cancelar_nf_qpa(nf_id: int, motivo: str, operador_id: int) -> AssaiNfQpa:
    """Cancela NF Q.P.A. e reverte estado da Sep + chassis (R5).

    R5.1: Sep com Carregamento FINALIZADO -> CARREGADA (chassis voltam CARREGADA).
    R5.2: Sep sem Carregamento -> FECHADA (chassis voltam SEPARADA).

    Etapas:
        1. Reverter eventos FATURADA -> CARREGADA OU SEPARADA OU DISPONIVEL
        2. Reverter Sep status (FATURADA -> CARREGADA ou FECHADA)
        3. Marcar NF como CANCELADA
        4. Remover NF do espelho Nacom (S11=a)
        5. Limpar EmbarqueItem.nota_fiscal (S15=a)
        6. Auditar e limpar vinculo NF-item <-> Sep-item (S16=c)
        7. Recalcular status do pedido

    Args:
        nf_id: id da AssaiNfQpa.
        motivo: justificativa (>= 3 chars).
        operador_id: usuario que cancelou.

    Returns:
        AssaiNfQpa com status_match=CANCELADA. Caller commita.

    Raises:
        CancelamentoValidationError: NF nao existe, ja cancelada, ou motivo vazio.
    """
    if not motivo or len(motivo.strip()) < 3:
        raise CancelamentoValidationError('Motivo obrigatorio (>= 3 chars)')

    nf = AssaiNfQpa.query.get(nf_id)
    if not nf:
        raise CancelamentoValidationError(f'NF {nf_id} nao encontrada')
    if nf.status_match == NF_STATUS_CANCELADA:
        raise CancelamentoValidationError(f'NF {nf_id} ja CANCELADA')

    sep = nf.separacao  # via assai_nf_qpa.separacao_id
    motivo_norm = motivo.strip()

    # Code review fix H1 (2026-05-13): query unica de Carregamento FINALIZADO
    # antes do loop, evita TOCTOU (passo 1 + passo 2 viam estados potencialmente
    # divergentes em concorrencia). Variavel reutilizada em ambos passos.
    tem_carregamento_finalizado = bool(
        sep and AssaiCarregamento.query.filter_by(
            separacao_id=sep.id, status=CARREGAMENTO_STATUS_FINALIZADO,
        ).first()
    )

    # 1. Reverter eventos FATURADA -> CARREGADA/SEPARADA/DISPONIVEL
    for item in nf.itens:
        chassi = item.chassi
        status_atual = status_efetivo(chassi)
        if status_atual == EVENTO_FATURADA:
            # R5.1: respeita CARREGADA se Sep esta FATURADA (Carregamento existe)
            if sep and sep.status == SEPARACAO_STATUS_FATURADA:
                if tem_carregamento_finalizado:
                    novo_evento = EVENTO_CARREGADA
                else:
                    novo_evento = EVENTO_SEPARADA  # R5.2
            else:
                # Sep nao estava FATURADA (caso NF antes da Sep, etc)
                novo_evento = EVENTO_SEPARADA
            emitir_evento(
                chassi, novo_evento, operador_id=operador_id,
                observacao=f'NF {nf.numero} cancelada: {motivo_norm}',
                dados_extras={'nf_id': nf.id, 'origem': 'cancelar_nf_qpa'},
            )

    # 2. Reverter Sep status (usa mesmo valor cacheado — H1)
    if sep and sep.status == SEPARACAO_STATUS_FATURADA:
        if tem_carregamento_finalizado:
            sep.status = SEPARACAO_STATUS_CARREGADA  # R5.1
        else:
            sep.status = SEPARACAO_STATUS_FECHADA  # R5.2

    # 3. Marcar NF como CANCELADA
    nf.status_match = NF_STATUS_CANCELADA
    nf.cancelada_em = agora_brasil_naive()
    nf.cancelada_por_id = operador_id
    nf.motivo_cancelamento = motivo_norm

    # 4. Remover NF do espelho Nacom (S11=a)
    if sep:
        try:
            from app.motos_assai.services.separacao_mirror_service import remover_nf_do_espelho
            remover_nf_do_espelho(sep.id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                'remover_nf_do_espelho FALHOU para sep %s (NF %s cancelada): %s',
                sep.id, nf.numero, e, exc_info=True,
            )

    # 5. Limpar EmbarqueItem.nota_fiscal (S15=a)
    if nf.numero:
        try:
            from app.embarques.models import EmbarqueItem
            EmbarqueItem.query.filter_by(
                nota_fiscal=str(nf.numero),
            ).update({'nota_fiscal': None}, synchronize_session=False)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                'Limpar EmbarqueItem.nota_fiscal FALHOU para NF %s: %s',
                nf.numero, e, exc_info=True,
            )

    # 6. Auditar e limpar vinculo NF-item <-> Sep-item (S16=c)
    for item in nf.itens:
        if item.separacao_item_id:
            db.session.add(AssaiNfQpaItemVinculoHistorico(
                nf_qpa_item_id=item.id,
                separacao_item_id=item.separacao_item_id,
                motivo=VINCULO_MOTIVO_NF_CANCELADA,
                chassi_no_momento=item.chassi,
                registrado_por_id=operador_id,
                detalhes={'nf_id': nf.id, 'motivo_nf': motivo_norm},
            ))
            item.separacao_item_id = None  # FK limpa apos auditoria

    # 7. Recalcular status do pedido
    # Code review nota H7 (2026-05-13): se sep=None, NF nunca bateu (status_match
    # NAO_RECONCILIADO). Nessas NFs, nenhum chassi tem evento FATURADA — entao
    # qtd_faturada nao muda e pedido associado e desconhecido (sem path para
    # encontrar pedido via FK). Skip e intencional.
    if sep:
        try:
            from app.motos_assai.services.pedido_status_service import recalcular_status_pedido
            recalcular_status_pedido(sep.pedido_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                'recalcular_status_pedido FALHOU para pedido %s: %s',
                sep.pedido_id, e, exc_info=True,
            )

    db.session.flush()

    import logging
    logging.getLogger(__name__).info(
        'cancelar_nf_qpa: nf=%s sep=%s motivo=%s operador=%s',
        nf_id, sep.id if sep else None, motivo_norm, operador_id,
    )

    return nf


def aplicar_correcao_cce(
    nf_id: int,
    chassis_corrigidos: List[Tuple[str, str]],
    numero_cce: str,
    operador_id: int,
) -> AssaiNfQpa:
    """Aplica correcao CCe: substitui chassis em assai_nf_qpa_item.

    S16: registra AssaiNfQpaItemVinculoHistorico antes de limpar separacao_item_id.
    S21 + A14: re-roda _calcular_match para refletir novo vinculo NF-Sep.

    Args:
        nf_id: ID da NF original.
        chassis_corrigidos: list[(chassi_antigo, chassi_novo)].
        numero_cce: numero da CCe (auditoria).
        operador_id: usuario que aplicou.

    Returns:
        AssaiNfQpa atualizada (status_match recalculado). Caller commita.

    Raises:
        CancelamentoValidationError: NF cancelada / nao encontrada.
    """
    nf = AssaiNfQpa.query.get(nf_id)
    if not nf:
        raise CancelamentoValidationError(f'NF {nf_id} nao encontrada')
    if nf.status_match == NF_STATUS_CANCELADA:
        raise CancelamentoValidationError(
            f'NF {nf_id} CANCELADA — nao aplica CCe'
        )

    if not chassis_corrigidos:
        raise CancelamentoValidationError('chassis_corrigidos vazio')

    chassis_aplicados = []
    for chassi_antigo, chassi_novo in chassis_corrigidos:
        chassi_antigo = (chassi_antigo or '').strip().upper()
        chassi_novo = (chassi_novo or '').strip().upper()
        if not chassi_antigo or not chassi_novo:
            continue

        item = AssaiNfQpaItem.query.filter_by(nf_id=nf_id, chassi=chassi_antigo).first()
        if not item:
            continue  # chassi antigo nao esta na NF — pular

        # S16: registrar vinculo historico antes de mudar
        if item.separacao_item_id:
            db.session.add(AssaiNfQpaItemVinculoHistorico(
                nf_qpa_item_id=item.id,
                separacao_item_id=item.separacao_item_id,
                motivo=VINCULO_MOTIVO_CCE_ALTEROU_CHASSI,
                chassi_no_momento=chassi_antigo,
                registrado_por_id=operador_id,
                detalhes={'numero_cce': numero_cce, 'chassi_novo': chassi_novo},
            ))
            item.separacao_item_id = None  # limpa vinculo antigo

        item.chassi = chassi_novo
        item.tipo_divergencia = None  # zera divergencia legacy (sera recalculada)
        chassis_aplicados.append((chassi_antigo, chassi_novo))

        # Code review fix M3 (2026-05-13): chassi_antigo pode estar com evento
        # FATURADA (de quando NF original bateu). Apos CCe, NF aponta para
        # chassi_novo. Sem reverter, chassi_antigo fica "marooned" — status
        # FATURADA mas sem NF ativa apontando. Reverter para SEPARADA/CARREGADA/
        # DISPONIVEL conforme contexto.
        status_antigo = status_efetivo(chassi_antigo)
        if status_antigo == EVENTO_FATURADA:
            # Determinar destino do antigo: se sep tem Carregamento FINALIZADO,
            # vai CARREGADA. Se sep apenas FECHADA, vai SEPARADA. Sem sep, DISPONIVEL.
            sep_antiga = nf.separacao if nf.separacao_id else None
            if sep_antiga:
                tem_car_finalizado = AssaiCarregamento.query.filter_by(
                    separacao_id=sep_antiga.id,
                    status=CARREGAMENTO_STATUS_FINALIZADO,
                ).first()
                novo_evento_antigo = EVENTO_CARREGADA if tem_car_finalizado else EVENTO_SEPARADA
            else:
                from app.motos_assai.models import EVENTO_DISPONIVEL
                novo_evento_antigo = EVENTO_DISPONIVEL
            emitir_evento(
                chassi_antigo, novo_evento_antigo, operador_id=operador_id,
                observacao=f'CCe {numero_cce}: substituido por {chassi_novo}',
                dados_extras={'nf_id': nf_id, 'origem': 'aplicar_correcao_cce',
                              'chassi_novo': chassi_novo},
            )

    db.session.flush()

    # Re-roda match (S21 + A14) — pode adicionar/remover separacao_item_id
    # e atualizar nf.status_match para BATEU/DIVERGENTE/NAO_RECONCILIADO.
    from app.motos_assai.services.parsers.nf_qpa_adapter import _calcular_match
    _calcular_match(nf, operador_id)
    db.session.flush()

    import logging
    logging.getLogger(__name__).info(
        'aplicar_correcao_cce: nf=%s cce=%s aplicados=%s operador=%s',
        nf_id, numero_cce, chassis_aplicados, operador_id,
    )

    return nf
