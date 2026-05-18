"""PreEtapaEstoqueService — planejador da pre-etapa CD/FB (D007).

Substitui NFs inter-filial CD↔FB (R$ 32,9 mi) e INDISPONIBILIZAR_*
(R$ 60,5 mi) por transferencias INTERNAS na company + residual minimo.

Algoritmo (por produto):
    1. Agrega linhas inv por lote (lote vazio → 'P-15/05')
    2. Calcula custo medio ponderado (D004)
    3. Identifica doadores:
       - Quants de lote NAO em inv: doam total
       - Quants de lote em inv com saldo > desejada: doam excesso
    4. Aloca doadores FIFO (quant_id) para cobrir deficits dos lotes alvo (POS)
    5. Sobras restantes dos doadores → MIGRAÇÃO da propria company (NEG)
    6. Deficits restantes:
       - Tenta puxar da FB (residual_fb_cd) — gera NF FB→CD (CFOP 5152)
       - Senao: ajuste positivo puro (inventory adjustment, sem origem)

Executor (`09b_executar_pre_etapa.py`) consome o plano via:
- StockInternalTransferService.transferir_entre_lotes (D006) para internas
- StockPickingService.criar_transferencia para residual_fb_cd
- stock.quant.action_apply_inventory direto para ajuste positivo puro

Restricao temporal (D007):
- ENQUANTO FB nao tiver passado pela propria pre-etapa, qualquer lote FB
  pode doar para CD.
- APOS pre-etapa FB, so o lote MIGRAÇÃO da FB pode doar (preserva
  corretude FB) — caller deve filtrar `quants_fb_disponivel` ao chamar.

Spec: docs/inventario-2026-05/00-decisoes/D007-pre-etapa-cd-fb-minimizar-nf.md
"""
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


@dataclass
class TransferenciaInternaPlanejada:
    """Transferencia interna planejada (lote → lote, mesma company)."""
    cod_produto: str
    company_id: int
    location_id: int
    qty: float
    lot_id_origem: Optional[int]
    lote_origem_nome: str
    lote_destino_nome: str
    tipo: str  # 'POS' (preencher lote alvo) ou 'NEG' (consolidar em MIGRAÇÃO)
    custo_medio: Decimal


@dataclass
class ResidualFbCdPlanejado:
    """Residual que precisa vir da FB para o CD via NF (CFOP 5152)."""
    cod_produto: str
    qty: float
    custo_medio: Decimal
    lote_origem_fb_sugerido: str
    lote_destino_cd_nome: str


@dataclass
class AjustePositivoPuroPlanejado:
    """Ajuste positivo direto (sem doador), via inventory adjustment."""
    cod_produto: str
    company_id: int
    location_id: int
    qty: float
    lote_destino_nome: str
    custo_medio: Decimal


@dataclass
class PlanoPreEtapa:
    """Plano consolidado da pre-etapa por produto."""
    transferencias_internas: List[TransferenciaInternaPlanejada] = field(
        default_factory=list
    )
    residual_fb_cd: List[ResidualFbCdPlanejado] = field(default_factory=list)
    ajustes_positivos_puros: List[AjustePositivoPuroPlanejado] = field(
        default_factory=list
    )
    warnings: List[str] = field(default_factory=list)


class PreEtapaEstoqueService:
    """Planejador da pre-etapa CD/FB (D007)."""

    LOTE_DEFAULT_SEM_NOME = 'P-15/05'
    LOTE_CONSOLIDADOR_NEG = 'MIGRAÇÃO'

    def __init__(self, odoo=None):
        self.odoo = odoo or get_odoo_connection()

    # ============================================================
    # Helpers de agregacao
    # ============================================================

    @staticmethod
    def _custo_medio_cod(quants: List[Dict[str, Any]]) -> Decimal:
        """Media ponderada `value/quantity` por produto (D004)."""
        total_val = Decimal('0')
        total_qty = Decimal('0')
        for q in quants:
            qty = Decimal(str(q.get('quantity', 0) or 0))
            val = Decimal(str(q.get('value', 0) or 0))
            if qty > 0 and val != 0:
                total_val += val
                total_qty += qty
        return total_val / total_qty if total_qty > 0 else Decimal('0')

    def _agregar_inv_por_lote(
        self, linhas_inv: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Soma qtd_inventario por nome de lote.

        Linhas sem lote sao agregadas em LOTE_DEFAULT_SEM_NOME ('P-15/05').
        """
        agg: Dict[str, float] = {}
        for linha in linhas_inv:
            nome = (linha.get('lote_inventariado') or '').strip()
            if not nome:
                nome = self.LOTE_DEFAULT_SEM_NOME
            qty = float(linha.get('qtd_inventario', 0) or 0)
            agg[nome] = agg.get(nome, 0.0) + qty
        return agg

    # ============================================================
    # Algoritmo principal
    # ============================================================

    def planejar(
        self,
        cod_produto: str,
        company_id: int,
        location_id: int,
        quants_odoo: List[Dict[str, Any]],
        linhas_inv: List[Dict[str, Any]],
        quants_fb_disponivel: Optional[List[Dict[str, Any]]] = None,
    ) -> PlanoPreEtapa:
        """Plano da pre-etapa para 1 produto.

        Args:
            cod_produto: default_code Odoo (informacional no plano).
            company_id: 4 (CD) ou 1 (FB).
            location_id: location interna principal da company
                (32 CD, 8 FB, 42 LF) — usada apenas para ajuste positivo puro.
            quants_odoo: lista de dicts da company com chaves:
                quant_id, lot_id, lote_nome (str, '' se sem lote),
                quantity, reserved_quantity, location_id, value.
            linhas_inv: lista de dicts do inventario com chaves:
                lote_inventariado (str, '' se sem lote), qtd_inventario.
            quants_fb_disponivel: para CD, quants da FB disponiveis para
                cobrir residual positivo (opcional). Se None ou vazia,
                deficits restantes viram ajuste positivo puro. Caller
                aplica restricao temporal (qualquer lote ou so MIGRAÇÃO).

        Returns:
            PlanoPreEtapa com 4 listas: transferencias_internas (POS+NEG),
            residual_fb_cd, ajustes_positivos_puros, warnings.
        """
        plano = PlanoPreEtapa()

        # 1. Agregar inv por lote
        inv_por_lote = self._agregar_inv_por_lote(linhas_inv)

        # 2. Agregar Odoo por lote
        odoo_por_lote: Dict[str, List[Dict[str, Any]]] = {}
        for q in quants_odoo:
            nome = (q.get('lote_nome') or '').strip()
            odoo_por_lote.setdefault(nome, []).append(q)

        # 3. Custo medio ponderado
        custo_medio = self._custo_medio_cod(quants_odoo)

        # 4. Saldo total atual por lote
        saldo_por_lote: Dict[str, float] = {
            nome: sum(float(q['quantity']) for q in quants)
            for nome, quants in odoo_por_lote.items()
        }

        # 5. Identificar doadores
        # Estrutura: {'quant': dict, 'qty_disponivel': float, 'qty_original': float}
        doadores: List[Dict[str, Any]] = []
        for nome, quants in odoo_por_lote.items():
            if nome == self.LOTE_CONSOLIDADOR_NEG and nome not in inv_por_lote:
                # MIGRAÇÃO ja consolidador: nao move (a menos que inv pida)
                continue
            if nome not in inv_por_lote:
                # Lote nao-alvo: doa total
                for q in quants:
                    qty_q = float(q['quantity'])
                    if qty_q > 0:
                        doadores.append({
                            'quant': q,
                            'qty_disponivel': qty_q,
                            'qty_original': qty_q,
                        })
            else:
                # Lote alvo com possivel excesso
                saldo = saldo_por_lote[nome]
                qty_desejada = inv_por_lote[nome]
                excesso = saldo - qty_desejada
                if excesso > 0:
                    excesso_rest = excesso
                    quants_ord = sorted(
                        quants, key=lambda x: x['quant_id']
                    )
                    for q in quants_ord:
                        if excesso_rest <= 0:
                            break
                        qty_doar = min(float(q['quantity']), excesso_rest)
                        if qty_doar > 0:
                            doadores.append({
                                'quant': q,
                                'qty_disponivel': qty_doar,
                                'qty_original': qty_doar,
                            })
                            excesso_rest -= qty_doar

        # 6. Calcular deficits
        deficits: Dict[str, float] = {}
        for nome, qty_desejada in inv_por_lote.items():
            saldo = saldo_por_lote.get(nome, 0.0)
            if saldo < qty_desejada:
                deficits[nome] = qty_desejada - saldo

        # 7. Doadores FIFO preenchem deficits (POS)
        doadores.sort(key=lambda d: d['quant']['quant_id'])
        # Lotes alvo ordenados para determinismo
        for lote_alvo in sorted(deficits.keys()):
            deficit_rest = deficits[lote_alvo]
            for doador in doadores:
                if deficit_rest <= 0:
                    break
                if doador['qty_disponivel'] <= 0:
                    continue
                qty_take = min(doador['qty_disponivel'], deficit_rest)
                q = doador['quant']
                plano.transferencias_internas.append(
                    TransferenciaInternaPlanejada(
                        cod_produto=cod_produto,
                        company_id=company_id,
                        location_id=int(q.get('location_id') or location_id),
                        qty=qty_take,
                        lot_id_origem=q.get('lot_id'),
                        lote_origem_nome=(q.get('lote_nome') or ''),
                        lote_destino_nome=lote_alvo,
                        tipo='POS',
                        custo_medio=custo_medio,
                    )
                )
                doador['qty_disponivel'] -= qty_take
                deficit_rest -= qty_take
            deficits[lote_alvo] = deficit_rest

        # 8. Sobras dos doadores → MIGRAÇÃO (NEG)
        for doador in doadores:
            qty_sobra = doador['qty_disponivel']
            if qty_sobra <= 0:
                continue
            q = doador['quant']
            origem_nome = (q.get('lote_nome') or '')
            # Skip se ja e MIGRAÇÃO (nao mover para si mesmo)
            if origem_nome == self.LOTE_CONSOLIDADOR_NEG:
                continue
            plano.transferencias_internas.append(
                TransferenciaInternaPlanejada(
                    cod_produto=cod_produto,
                    company_id=company_id,
                    location_id=int(q.get('location_id') or location_id),
                    qty=qty_sobra,
                    lot_id_origem=q.get('lot_id'),
                    lote_origem_nome=origem_nome,
                    lote_destino_nome=self.LOTE_CONSOLIDADOR_NEG,
                    tipo='NEG',
                    custo_medio=custo_medio,
                )
            )
            doador['qty_disponivel'] = 0.0

        # 9. Warnings de reserva (apos calcular doacoes finais)
        for doador in doadores:
            q = doador['quant']
            qty_doada = doador['qty_original'] - doador['qty_disponivel']
            if qty_doada <= 0:
                continue
            reservada = float(q.get('reserved_quantity', 0) or 0)
            qty_restante = float(q['quantity']) - qty_doada
            if qty_restante < reservada:
                plano.warnings.append(
                    f'quant {q.get("quant_id")} ({cod_produto}, lote='
                    f'{q.get("lote_nome") or "(sem lote)"}): tem {reservada} '
                    f'un reservadas em pickings ativos; saldo apos doacao '
                    f'({qty_restante}) ficaria < reservada. Pode bloquear '
                    f'a execucao via StockInternalTransferService.'
                )

        # 10. Deficits restantes: FB → ajuste positivo puro
        for lote_alvo in sorted(deficits.keys()):
            deficit = deficits[lote_alvo]
            if deficit <= 0:
                continue
            if quants_fb_disponivel:
                disponivel_fb = sum(
                    float(q.get('quantity', 0) or 0)
                    for q in quants_fb_disponivel
                )
                qty_de_fb = min(disponivel_fb, deficit)
                if qty_de_fb > 0:
                    doador_fb = max(
                        quants_fb_disponivel,
                        key=lambda q: float(q.get('quantity', 0) or 0),
                    )
                    plano.residual_fb_cd.append(ResidualFbCdPlanejado(
                        cod_produto=cod_produto,
                        qty=qty_de_fb,
                        custo_medio=custo_medio,
                        lote_origem_fb_sugerido=(
                            doador_fb.get('lote_nome') or ''
                        ),
                        lote_destino_cd_nome=lote_alvo,
                    ))
                    deficit -= qty_de_fb
            if deficit > 0:
                plano.ajustes_positivos_puros.append(
                    AjustePositivoPuroPlanejado(
                        cod_produto=cod_produto,
                        company_id=company_id,
                        location_id=location_id,
                        qty=deficit,
                        lote_destino_nome=lote_alvo,
                        custo_medio=custo_medio,
                    )
                )

        return plano
