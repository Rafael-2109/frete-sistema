# -*- coding: utf-8 -*-
"""
Service unificado de CTe Complementar (CarVia)
==============================================

Fonte unica de criacao + vinculo de CarviaCteComplementar, substituindo:
  - `_executar_gerar_cte_complementar` em custo_entrega_routes.py (virou shim)
  - logica inline em `criar_cte_complementar` em cte_complementar_routes.py

Cobre 2 modos de criacao:
  - `EMISSAO_SSW`     -> calcula grossing-up, cria emissao, enfileira opcao 222
  - `IMPORTACAO_XML`  -> delega para `persistir_cte_complementar_completo`

Vinculo com `CarviaCustoEntrega` e SEMPRE OPCIONAL.

Mutex de emissao (item 3 do plano):
  - N CTes Comp por operacao sao permitidos sequencialmente
  - Bloqueia apenas concorrencia: status PENDENTE/EM_PROCESSAMENTO ja existe
    para a mesma `operacao_id`.

Filtros deterministicos para `ces_elegiveis_para_vincular`:
  - mesma `operacao_id` (HARD)
  - `cte_complementar_id IS NULL`
  - status IN ('PENDENTE', 'VINCULADO_FT')
"""

import logging
from typing import Optional, Tuple, List, Dict, Any

from app import db

logger = logging.getLogger(__name__)

# Mapeamento tipo_custo -> motivo SSW opcao 222 (espelha custo_entrega_routes)
TIPO_CUSTO_MOTIVO_SSW = {
    'TAXA_DESCARGA': 'D',
    'DIARIA': 'E',
    'REENTREGA': 'R',
    'DEVOLUCAO': 'R',
    'ARMAZENAGEM': 'R',
    'AVARIA': 'C',
    'PEDAGIO_EXTRA': 'C',
    'GNRE_ICMS': 'C',
    'OUTROS': 'C',
}


class CteComplementarService:
    """Service unico para criar/vincular/desvincular CarviaCteComplementar."""

    # ====================================================================
    # CRIACAO — Modo EMISSAO_SSW
    # ====================================================================

    @staticmethod
    def criar_para_emissao_ssw(
        operacao_id: int,
        valor_base: float,
        tipo_custo: str,
        motivo_texto: str,
        usuario: str,
        custo_entrega_id: Optional[int] = None,
        motivo_ssw_override: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[int]]:
        """Cria CarviaCteComplementar (RASCUNHO) e enfileira emissao SSW 222.

        Args:
            operacao_id: id do CarviaOperacao pai (CTe CarVia)
            valor_base: valor LIQUIDO do custo a complementar (R$)
            tipo_custo: chave em TIPO_CUSTO_MOTIVO_SSW (ex: 'DIARIA')
            motivo_texto: texto livre para <ObsCont> e cte_comp.motivo
            usuario: email do usuario (auditoria)
            custo_entrega_id: vinculo OPCIONAL com CarviaCustoEntrega
            motivo_ssw_override: override do motivo SSW (C/D/E/R) — se None,
                deriva de `tipo_custo` via TIPO_CUSTO_MOTIVO_SSW

        Returns:
            (sucesso, mensagem, emissao_id_ou_None)
        """
        from app.carvia.models import (
            CarviaOperacao,
            CarviaCteComplementar,
            CarviaEmissaoCteComplementar,
            CarviaCustoEntrega,
        )
        from app.carvia.services.cte_complementar_persistencia import (
            calcular_valor_complementar,
            extrair_icms_do_pai,
        )

        # ── Validacoes basicas ──
        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            return (False, 'Operacao (CTe CarVia) nao encontrada.', None)
        if not operacao.ctrc_numero:
            return (
                False,
                'Operacao nao possui CTRC. Importe o CTe XML primeiro.',
                None,
            )
        if operacao.status == 'CANCELADO':
            return (False, 'Operacao esta CANCELADA.', None)

        try:
            valor_base_f = float(valor_base)
        except (TypeError, ValueError):
            return (False, f'valor_base invalido: {valor_base}', None)
        if valor_base_f <= 0:
            return (False, 'valor_base deve ser maior que zero.', None)

        if tipo_custo not in TIPO_CUSTO_MOTIVO_SSW:
            return (False, f'tipo_custo invalido: {tipo_custo}', None)

        # ── Mutex (revisado item 3): permite N sequenciais, bloqueia paralelas ──
        emissao_paralela = (
            CarviaEmissaoCteComplementar.query
            .filter(
                CarviaEmissaoCteComplementar.operacao_id == operacao_id,
                CarviaEmissaoCteComplementar.status.in_(
                    ['PENDENTE', 'EM_PROCESSAMENTO']
                ),
            )
            .first()
        )
        if emissao_paralela:
            return (
                False,
                (
                    f'Ja existe emissao em andamento (id #{emissao_paralela.id}, '
                    f'status={emissao_paralela.status}) para esta operacao. '
                    f'Aguarde concluir antes de emitir outra.'
                ),
                None,
            )

        # ── Resolver ICMS do CTe pai ──
        icms_info = extrair_icms_do_pai(operacao)
        icms = float(icms_info.get('aliquota_icms') or 0)
        if icms == 0:
            return (
                False,
                'ICMS nao encontrado. Verifique se o XML do CTe pai foi importado.',
                None,
            )

        # ── Calcular valor com grossing-up ──
        try:
            valor_cte = calcular_valor_complementar(valor_base_f, icms)
        except ValueError as e:
            return (False, str(e), None)

        motivo_ssw = motivo_ssw_override or TIPO_CUSTO_MOTIVO_SSW.get(tipo_custo, 'C')

        # ── Validar CE opcional ──
        custo = None
        if custo_entrega_id:
            custo = db.session.get(CarviaCustoEntrega, custo_entrega_id)
            if not custo:
                return (False, f'CarviaCustoEntrega #{custo_entrega_id} nao encontrado.', None)
            if custo.cte_complementar_id:
                return (
                    False,
                    f'Custo {custo.numero_custo} ja possui CTe Complementar vinculado.',
                    None,
                )
            if custo.status in ('CANCELADO', 'PAGO'):
                return (
                    False,
                    f'Custo {custo.numero_custo} esta {custo.status} — nao pode ser vinculado.',
                    None,
                )

        try:
            # ── Criar CTe Comp ──
            cte_comp = CarviaCteComplementar(
                numero_comp=CarviaCteComplementar.gerar_numero_comp(),
                operacao_id=operacao.id,
                cte_valor=valor_cte,
                cnpj_cliente=operacao.cnpj_cliente,
                nome_cliente=operacao.nome_cliente,
                status='RASCUNHO',
                motivo=(motivo_texto or '').strip()[:500] or None,
                observacoes=(
                    f'Gerado via emissao SSW. Tipo={tipo_custo}, '
                    f'Base=R$ {valor_base_f:.2f}, PIS/COFINS=9.25%, ICMS={icms}%.'
                    + (f' CE={custo.numero_custo}.' if custo else '')
                ),
                criado_por=usuario,
            )
            db.session.add(cte_comp)
            db.session.flush()

            # Auto-link frete_id (best-effort)
            CteComplementarService._tentar_vincular_frete_cte_comp(cte_comp)

            # Vinculo CE opcional
            if custo:
                custo.cte_complementar_id = cte_comp.id
                if not custo.operacao_id:
                    custo.operacao_id = operacao.id

            # ── Criar tracking de emissao ──
            emissao = CarviaEmissaoCteComplementar(
                custo_entrega_id=custo.id if custo else None,  # nullable agora
                cte_complementar_id=cte_comp.id,
                operacao_id=operacao.id,
                ctrc_pai=operacao.ctrc_numero,
                motivo_ssw=motivo_ssw,
                filial_ssw='CAR',
                valor_calculado=valor_cte,
                icms_aliquota_usada=icms,
                status='PENDENTE',
                criado_por=usuario,
            )
            db.session.add(emissao)
            db.session.flush()

            # Enfileirar job RQ
            from app.portal.workers import enqueue_job
            from app.carvia.workers.ssw_cte_complementar_jobs import (
                emitir_cte_complementar_job,
            )

            job = enqueue_job(
                emitir_cte_complementar_job,
                emissao.id,
                queue_name='high',
                timeout='10m',
            )
            emissao.job_id = job.id
            db.session.commit()

            ce_label = f' (CE {custo.numero_custo})' if custo else ''
            logger.info(
                'CteComplementarService.criar_para_emissao_ssw: cte_comp=%s '
                'op=%s valor_base=%.2f icms=%.2f valor_cte=%.2f motivo_ssw=%s%s',
                cte_comp.numero_comp, operacao.id, valor_base_f, icms,
                valor_cte, motivo_ssw, ce_label,
            )
            return (
                True,
                (
                    f'CTe Complementar {cte_comp.numero_comp} criado{ce_label} — '
                    f'valor R$ {valor_cte:.2f} (base R$ {valor_base_f:.2f} '
                    f'+ PIS/COFINS 9.25% + ICMS {icms}%). '
                    f'Emissao SSW em andamento...'
                ),
                emissao.id,
            )

        except Exception as e:
            db.session.rollback()
            logger.exception(
                'Erro em criar_para_emissao_ssw op=%s: %s', operacao_id, e,
            )
            return (False, f'Erro ao criar CTe Complementar: {e}', None)

    # ====================================================================
    # VINCULO CE
    # ====================================================================

    @staticmethod
    def vincular_ce(cte_comp_id: int, custo_entrega_id: int, usuario: str) -> Dict[str, Any]:
        """Vincula um CarviaCustoEntrega a um CarviaCteComplementar existente.

        Filtros deterministicos:
          - cte_comp.status != 'CANCELADO'
          - CE.operacao_id == cte_comp.operacao_id (HARD)
          - CE.cte_complementar_id IS NULL
          - CE.status IN ('PENDENTE', 'VINCULADO_FT')

        Returns:
            dict com sucesso, ce_numero, cte_comp_numero
        """
        from app.carvia.models import CarviaCteComplementar, CarviaCustoEntrega

        cte_comp = db.session.get(CarviaCteComplementar, cte_comp_id)
        if not cte_comp:
            raise ValueError(f'CTe Complementar #{cte_comp_id} nao encontrado.')
        if cte_comp.status == 'CANCELADO':
            raise ValueError('CTe Complementar esta CANCELADO.')

        custo = db.session.get(CarviaCustoEntrega, custo_entrega_id)
        if not custo:
            raise ValueError(f'Custo de entrega #{custo_entrega_id} nao encontrado.')
        if custo.cte_complementar_id:
            raise ValueError(
                f'Custo {custo.numero_custo} ja esta vinculado a CTe Comp #{custo.cte_complementar_id}.'
            )
        if custo.status not in ('PENDENTE', 'VINCULADO_FT'):
            raise ValueError(
                f'Custo {custo.numero_custo} esta {custo.status} — nao pode ser vinculado.'
            )
        if custo.operacao_id and custo.operacao_id != cte_comp.operacao_id:
            raise ValueError(
                f'Custo pertence a outra operacao (#{custo.operacao_id}). '
                f'CTe Comp e da operacao #{cte_comp.operacao_id}.'
            )

        custo.cte_complementar_id = cte_comp_id
        if not custo.operacao_id:
            custo.operacao_id = cte_comp.operacao_id

        logger.info(
            'CteComplementarService.vincular_ce: CE=%s -> cte_comp=%s por %s',
            custo.numero_custo, cte_comp.numero_comp, usuario,
        )
        return {
            'sucesso': True,
            'ce_numero': custo.numero_custo,
            'cte_comp_numero': cte_comp.numero_comp,
        }

    @staticmethod
    def desvincular_ce(custo_entrega_id: int, usuario: str) -> Dict[str, Any]:
        """Remove o vinculo CE -> CTe Complementar.

        Bloqueios:
          - CE.status == 'PAGO' (pagamento ja foi processado)
          - CE.status == 'VINCULADO_FT' com FT CONFERIDA/PAGA: o CTe Comp e
            parte da rastreabilidade financeira ja consolidada — desvincular
            quebraria a trilha de auditoria. Para alterar, usar fluxo de
            cancelamento da FT primeiro.
          - CTe Comp em status FATURADO: desvincular CE de um CTe Comp ja
            faturado quebra reconciliacao com a Fatura Cliente.

        Returns:
            dict com sucesso, ce_numero
        """
        from app.carvia.models import (
            CarviaCustoEntrega, CarviaCteComplementar,
            CarviaFaturaTransportadora,
        )

        custo = db.session.get(CarviaCustoEntrega, custo_entrega_id)
        if not custo:
            raise ValueError(f'Custo de entrega #{custo_entrega_id} nao encontrado.')
        if not custo.cte_complementar_id:
            raise ValueError('Custo nao esta vinculado a nenhum CTe Complementar.')
        if custo.status == 'PAGO':
            raise ValueError(
                f'Custo {custo.numero_custo} esta PAGO — nao pode desvincular.'
            )

        # Guard VINCULADO_FT: bloquear apenas se a FT estiver CONFERIDA ou PAGA.
        # FT em construcao (PENDENTE/EM_CONFERENCIA) ainda permite desvincular,
        # consistente com `pode_editar()` da FT.
        if custo.status == 'VINCULADO_FT' and custo.fatura_transportadora_id:
            ft = db.session.get(
                CarviaFaturaTransportadora, custo.fatura_transportadora_id,
            )
            if ft:
                pode_editar, razao = ft.pode_editar()
                if not pode_editar:
                    raise ValueError(
                        f'Custo {custo.numero_custo} esta vinculado a Fatura '
                        f'Transportadora #{ft.numero_fatura} ({razao}). '
                        f'Reabra a conferencia da FT antes de desvincular.'
                    )

        # Guard FATURADO: CTe Comp ja em fatura cliente nao pode perder CE
        cte_comp = db.session.get(CarviaCteComplementar, custo.cte_complementar_id)
        if cte_comp and cte_comp.status == 'FATURADO':
            raise ValueError(
                f'CTe Complementar {cte_comp.numero_comp} esta FATURADO. '
                f'Desvincular CE quebraria a reconciliacao com a Fatura Cliente.'
            )

        old_id = custo.cte_complementar_id
        custo.cte_complementar_id = None

        logger.info(
            'CteComplementarService.desvincular_ce: CE=%s desvinculado de cte_comp=%d por %s',
            custo.numero_custo, old_id, usuario,
        )
        return {'sucesso': True, 'ce_numero': custo.numero_custo}

    @staticmethod
    def ces_elegiveis_para_vincular(cte_comp_id: int) -> List[Dict[str, Any]]:
        """Retorna CEs elegiveis para vincular a este CTe Complementar.

        Filtros deterministicos (item 5 do plano):
          - mesma operacao_id
          - cte_complementar_id IS NULL
          - status IN ('PENDENTE', 'VINCULADO_FT')

        Inclui flags:
          - valor_match: |CE.valor - cte_comp.cte_valor / 0.9075| <= 0.01
          - motivo_match: TIPO_CUSTO_MOTIVO_SSW[CE.tipo_custo] == cte_comp.motivo_ssw
            (motivo_ssw vem de CarviaEmissaoCteComplementar mais recente)
        """
        from app.carvia.models import (
            CarviaCteComplementar, CarviaCustoEntrega, CarviaEmissaoCteComplementar,
        )

        cte_comp = db.session.get(CarviaCteComplementar, cte_comp_id)
        if not cte_comp:
            return []

        # Resolver motivo_ssw do CTe Comp (via emissao mais recente, se houver)
        emissao = (
            CarviaEmissaoCteComplementar.query
            .filter_by(cte_complementar_id=cte_comp_id)
            .order_by(CarviaEmissaoCteComplementar.criado_em.desc())
            .first()
        )
        motivo_ssw_cte_comp = emissao.motivo_ssw if emissao else None

        ces = (
            CarviaCustoEntrega.query
            .filter(
                CarviaCustoEntrega.operacao_id == cte_comp.operacao_id,
                CarviaCustoEntrega.cte_complementar_id.is_(None),
                CarviaCustoEntrega.status.in_(['PENDENTE', 'VINCULADO_FT']),
            )
            .order_by(CarviaCustoEntrega.criado_em.desc())
            .all()
        )

        valor_cte_comp = float(cte_comp.cte_valor or 0)
        resultado = []
        for ce in ces:
            valor_ce = float(ce.valor or 0)
            motivo_ce = TIPO_CUSTO_MOTIVO_SSW.get(ce.tipo_custo, 'C')
            resultado.append({
                'id': ce.id,
                'numero_custo': ce.numero_custo,
                'tipo_custo': ce.tipo_custo,
                'motivo_ssw': motivo_ce,
                'motivo_match': (
                    motivo_ssw_cte_comp == motivo_ce if motivo_ssw_cte_comp else None
                ),
                'valor': valor_ce,
                'valor_match': abs(valor_ce - valor_cte_comp / 0.9075) <= 0.01 if valor_cte_comp else False,
                'data_custo': ce.data_custo.strftime('%d/%m/%Y') if ce.data_custo else '-',
                'descricao': ce.descricao or '-',
                'status': ce.status,
                'fornecedor_nome': ce.fornecedor_nome or '-',
            })
        return resultado

    # ====================================================================
    # Helper interno
    # ====================================================================

    @staticmethod
    def _tentar_vincular_frete_cte_comp(cte_comp) -> None:
        """Auto-link frete_id no CTe Comp via operacao_id. Best-effort."""
        if cte_comp.frete_id or not cte_comp.operacao_id:
            return
        from app.carvia.models import CarviaFrete
        frete = (
            CarviaFrete.query
            .filter_by(operacao_id=cte_comp.operacao_id)
            .order_by(CarviaFrete.criado_em.desc())
            .first()
        )
        if frete:
            cte_comp.frete_id = frete.id
            logger.info(
                'autolink_frete_cte_comp: cte_comp=%s vinculado a CarviaFrete #%d',
                cte_comp.numero_comp, frete.id,
            )
