# etapa: C1
# doc-dono: app/odoo/estoque/CLAUDE.md §6
"""StockQuantAdjustmentService — ajuste atomico de inventario de UM quant.

Primitiva REUTILIZAVEL: aplica um ajuste de saldo em um unico stock.quant via
INVENTORY ADJUSTMENT (`stock.quant.inventory_quantity` + `action_apply_inventory`),
o padrao oficial do Odoo 16+. Gera 1 stock.move automatico (origem
'Physical Inventory', visivel em Inventory > Reporting > Stock Moves) — auditavel.

E o ATOMO de ajuste de estoque. Operacoes maiores sao ORQUESTRADORES sobre ele:
- ajuste por planilha (1 ajuste por linha)        -> scripts/.../ajuste_inventario.py
- transferencia entre lotes (= 2 ajustes: -origem +destino) -> StockInternalTransferService
- realocacao net-zero (N ajustes balanceados por produto)
- zerar negativos (valor_absoluto=0 + reduzir lotes-fonte por delta)
- correcao de reserved_quantity negativo (resetar_reserva + valor_absoluto=0)

Identificacao do quant (2 formas, mutuamente exclusivas):
- quant_id direto                                  (ex: limpeza de quant fantasma)
- (product_id, company_id, location_id, lot_id)    (lot_id=None => quant sem lote)

Quantidade alvo (2 formas, mutuamente exclusivas):
- delta=X           : inventory_quantity = quantidade_atual + X   (SOMA; X pode ser +/-)
- valor_absoluto=X  : inventory_quantity = X                      (SET; zerar => X=0)

Por que NAO mexer direto no campo `quantity`?
O Odoo so movimenta estoque (e mantem rastreabilidade/contabilidade) ao escrever
`inventory_quantity` e chamar `action_apply_inventory`, que calcula o move pela
diferenca. Escrever `quantity` direto corromperia o razao de estoque.

Spec: consolidacao dos scripts 11/12/13/14/criar_saldo (inventario 2026-05).
"""
import logging
import time
from typing import Any, Dict, List, Optional

from app.odoo.services.stock_lot_service import StockLotService
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)

# Tolerancia de arredondamento (banco local guarda 4 casas, Odoo guarda 6;
# fracoes 1/3, 2/3, 1/6 divergem). Mesma constante do transfer service.
TOL_ARREDONDAMENTO = 0.001

_CAMPOS_QUANT = ['id', 'quantity', 'reserved_quantity', 'lot_id', 'location_id']


class StockQuantAdjustmentService:
    """Ajuste atomico de inventario de 1 quant via inventory adjustment."""

    def __init__(self, odoo=None, lot_svc=None):
        self.odoo = odoo or get_odoo_connection()
        self.lot_svc = lot_svc or StockLotService(odoo=self.odoo)

    # ============================================================
    # Helpers de leitura
    # ============================================================

    def buscar_quant(
        self,
        *,
        product_id: int,
        company_id: int,
        location_id: int,
        lot_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Busca 1 quant por (product, company, location, lot_id).

        lot_id=None busca quant sem lote (lot_id=False no Odoo). Retorna o
        primeiro se houver multiplos (defensivo — UK cobre a combinacao).
        """
        domain: List = [
            ['product_id', '=', product_id],
            ['company_id', '=', company_id],
            ['location_id', '=', location_id],
        ]
        domain.append(['lot_id', '=', False] if lot_id is None else ['lot_id', '=', lot_id])
        quants = self.odoo.search_read('stock.quant', domain, _CAMPOS_QUANT, limit=2)
        if not quants:
            return None
        if len(quants) > 1:
            logger.warning(
                f'product={product_id} company={company_id} location={location_id} '
                f'lot={lot_id}: {len(quants)} quants — usando primeiro {quants}'
            )
        return quants[0]

    def _ler_quant_por_id(self, quant_id: int) -> Optional[Dict[str, Any]]:
        res = self.odoo.read('stock.quant', [quant_id], _CAMPOS_QUANT)
        return res[0] if res else None

    # ============================================================
    # Operacao atomica: ajustar 1 quant
    # ============================================================

    def ajustar_quant(
        self,
        *,
        # --- identificacao do quant (uma das duas formas) ---
        quant_id: Optional[int] = None,
        product_id: Optional[int] = None,
        company_id: Optional[int] = None,
        location_id: Optional[int] = None,
        lot_id: Optional[int] = None,
        # --- quantidade alvo (uma das duas formas) ---
        delta: Optional[float] = None,
        valor_absoluto: Optional[float] = None,
        # --- comportamento ---
        criar_se_faltar: bool = False,
        validar_nao_negativar: bool = True,
        validar_nao_abaixo_reserva: bool = True,
        resetar_reserva: bool = False,
        casas_decimais: int = 6,
        # --- guard anti-bug: validar ajuste contra pedido original ---
        delta_esperado: Optional[float] = None,
        tolerancia_delta: float = 0.1,
        corrigir_para_esperado: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Aplica um ajuste de inventario em 1 quant.

        Args:
            quant_id: identifica o quant diretamente. Alternativa a
                (product_id, company_id, location_id, lot_id).
            product_id, company_id, location_id: identificam o quant quando
                quant_id nao e dado (os 3 sao obrigatorios nesse caso).
            lot_id: stock.lot.id; None => quant sem lote (lot_id=False).
            delta: ajuste relativo (qty_apos = qty_antes + delta). +/- permitido.
            valor_absoluto: ajuste absoluto (qty_apos = valor_absoluto). Use 0
                para zerar. Exatamente um de (delta, valor_absoluto) e obrigatorio.
            criar_se_faltar: se o quant nao existe, cria via stock.quant.create
                + action_apply_inventory. Exige identificacao por
                (product_id, company_id, location_id) — nao por quant_id.
            validar_nao_negativar: bloqueia (status FALHA_QUANT_NEGATIVO) se
                qty_apos < 0.
            validar_nao_abaixo_reserva: bloqueia (status FALHA_RESERVADO) se
                qty_apos < reserva ativa. Ignorada se resetar_reserva=True.
            resetar_reserva: escreve reserved_quantity=0 antes do ajuste (reset
                de cache inconsistente — NAO cancela pickings). Para corrigir
                quants com reserved_quantity negativo/orfao.
            casas_decimais: arredondamento (default 6, padrao Odoo).
            delta_esperado: pedido ORIGINAL de ajuste (opcional, mas recomendado
                em retomadas de FALHA com `valor_absoluto`/`resetar_reserva`).
                Quando informado, valida que `|ajuste_aplicado - delta_esperado|
                <= tolerancia_delta`. Se diverge, retorna FALHA_DELTA_DIVERGENTE
                sem escrever (ou EXECUTADO_AUTO_CORRIGIDO se
                corrigir_para_esperado=True). Protege contra o bug operacional
                2026-05-23 do CICLAMATO (politica homogenea `delta=-qty_atual`
                zerou 40.73 un quando o pedido original era -7).
            tolerancia_delta: tolerancia absoluta para comparacao com
                delta_esperado (default 0.1 un). Use 0.001 para casamento exato.
                ValueError se < 0 (negativo desarma o guard silenciosamente).
                ATENCAO: delta_esperado=0.0 ativa o guard (espera NOOP). Se sua
                planilha tem campo vazio que vira 0.0 numerico, trate antes (filtre
                ou converta para None). Passe None para desabilitar o guard.
            corrigir_para_esperado: quando divergente, AUTO-CORRIGE aplicando
                `delta_esperado` no lugar de `delta`/`valor_absoluto` enviados.
                Status final = EXECUTADO_AUTO_CORRIGIDO (resultado inclui o
                pedido original que foi sobrescrito). Default False (bloqueia).
                Usar em orquestrador de planilha que traz delta_esperado na
                coluna original — divergencias se auto-corrigem.
            dry_run: nao escreve no Odoo; retorna o plano calculado.

        Returns:
            dict com status e detalhes:
                status: DRY_RUN_OK | EXECUTADO | EXECUTADO_AUTO_CORRIGIDO | NOOP
                        | FALHA_QUANT_VAZIO | FALHA_QUANT_NEGATIVO
                        | FALHA_RESERVADO | FALHA_DELTA_DIVERGENTE | FALHA_ODOO
                quant_id, qty_antes, qty_apos, reservada, ajuste_aplicado,
                acao ('updated'|'created'|'reset_reserva'|'none'),
                tempo_ms, erro (se houver). FALHA_DELTA_DIVERGENTE inclui
                delta_esperado, tolerancia_delta, divergencia.
                EXECUTADO_AUTO_CORRIGIDO inclui delta_original_solicitado,
                ajuste_aplicado_original, divergencia_resolvida.

        Raises:
            ValueError: erro de uso (args incompativeis) — bug do orquestrador,
                nao condicao de dado. Condicoes de dado retornam status.
        """
        inicio = time.time()

        # --- 1. Validacao de uso (raise: e bug, nao dado) ---
        if (delta is None) == (valor_absoluto is None):
            raise ValueError('Forneca exatamente um de: delta OU valor_absoluto')
        if tolerancia_delta < 0:
            raise ValueError(
                f'tolerancia_delta deve ser >= 0 (recebido: {tolerancia_delta}). '
                f'Valor negativo desarma o guard silenciosamente.'
            )
        if quant_id is None:
            faltando = [
                n for n, v in (
                    ('product_id', product_id),
                    ('company_id', company_id),
                    ('location_id', location_id),
                ) if v is None
            ]
            if faltando:
                raise ValueError(
                    f'Sem quant_id, sao obrigatorios product_id/company_id/'
                    f'location_id (faltando: {faltando})'
                )
        if criar_se_faltar and quant_id is not None:
            raise ValueError(
                'criar_se_faltar exige identificacao por '
                '(product_id, company_id, location_id) — nao por quant_id'
            )

        r: Dict[str, Any] = {
            'quant_id': quant_id,
            'product_id': product_id,
            'company_id': company_id,
            'location_id': location_id,
            'lot_id': lot_id,
            'delta': delta,
            'valor_absoluto': valor_absoluto,
            'acao': 'none',
        }

        # --- 2. Localizar quant ---
        if quant_id is not None:
            quant = self._ler_quant_por_id(quant_id)
        else:
            assert product_id is not None and company_id is not None and location_id is not None
            quant = self.buscar_quant(
                product_id=product_id, company_id=company_id,
                location_id=location_id, lot_id=lot_id,
            )

        existe = quant is not None
        qty_antes = round(float(quant['quantity']), casas_decimais) if existe else 0.0
        reservada = round(float(quant.get('reserved_quantity') or 0), casas_decimais) if existe else 0.0
        r['qty_antes'] = qty_antes
        r['reservada'] = reservada
        if existe:
            r['quant_id'] = quant['id']

        # --- 3. Calcular qty_apos ---
        if delta is not None:
            qty_apos = round(qty_antes + float(delta), casas_decimais)
        else:
            assert valor_absoluto is not None
            qty_apos = round(float(valor_absoluto), casas_decimais)
        r['qty_apos'] = qty_apos
        r['ajuste_aplicado'] = round(qty_apos - qty_antes, casas_decimais)

        # --- 3b. Guard anti-bug: validar ajuste vs pedido original ---
        # Protege contra politica homogenea em retomadas de FALHA
        # (bug CICLAMATO 2026-05-23: delta=-40.73 quando pedido era -7).
        if delta_esperado is not None:
            divergencia = round(abs(r['ajuste_aplicado'] - float(delta_esperado)), casas_decimais)
            if divergencia > tolerancia_delta:
                if corrigir_para_esperado:
                    # AUTO-CORRECAO: aplicar delta_esperado em vez do enviado.
                    # Preserva info original p/ auditoria; recalcula qty_apos.
                    r['auto_correcao_aplicada'] = True
                    r['delta_original_solicitado'] = delta
                    r['valor_absoluto_original_solicitado'] = valor_absoluto
                    r['ajuste_aplicado_original'] = r['ajuste_aplicado']
                    r['delta_esperado'] = float(delta_esperado)
                    r['tolerancia_delta'] = tolerancia_delta
                    r['divergencia_resolvida'] = divergencia
                    # Recalcular qty_apos como qty_antes + delta_esperado
                    qty_apos = round(qty_antes + float(delta_esperado), casas_decimais)
                    r['qty_apos'] = qty_apos
                    r['ajuste_aplicado'] = round(qty_apos - qty_antes, casas_decimais)
                    # Fluxo continua p/ validar negativar/reserva no novo qty_apos
                    # e executar normalmente. Status sera trocado p/
                    # EXECUTADO_AUTO_CORRIGIDO no fim (secao 8).
                else:
                    r['status'] = 'FALHA_DELTA_DIVERGENTE'
                    r['delta_esperado'] = float(delta_esperado)
                    r['tolerancia_delta'] = tolerancia_delta
                    r['divergencia'] = divergencia
                    r['erro'] = (
                        f'ajuste_aplicado={r["ajuste_aplicado"]} diverge de '
                        f'delta_esperado={delta_esperado} em {divergencia} '
                        f'(tolerancia_delta={tolerancia_delta}). Cruzar quant_id '
                        f'com pedido original antes de retomar (regra inviolavel 10). '
                        f'Ou use --corrigir-para-esperado p/ aplicar delta_esperado.'
                    )
                    return r

        # --- 4. Quant inexistente ---
        if not existe:
            if quant_id is not None:
                r['status'] = 'FALHA_QUANT_VAZIO'
                r['erro'] = f'quant_id={quant_id} nao encontrado'
                return r
            if not criar_se_faltar:
                r['status'] = 'FALHA_QUANT_VAZIO'
                r['erro'] = (
                    f'sem quant para product={product_id} company={company_id} '
                    f'location={location_id} lot={lot_id} e criar_se_faltar=False'
                )
                return r
            if qty_apos < 0:
                r['status'] = 'FALHA_QUANT_NEGATIVO'
                r['erro'] = f'criar_se_faltar com qty_apos={qty_apos} < 0'
                return r

        # --- 5. Validacoes anti-negativacao / anti-reserva ---
        if validar_nao_negativar and qty_apos < 0:
            r['status'] = 'FALHA_QUANT_NEGATIVO'
            r['erro'] = f'qty_apos={qty_apos} < 0 (antes={qty_antes})'
            return r
        reserva_efetiva = 0.0 if resetar_reserva else reservada
        if validar_nao_abaixo_reserva and qty_apos < reserva_efetiva:
            r['status'] = 'FALHA_RESERVADO'
            r['erro'] = (
                f'qty_apos={qty_apos} < reserva={reserva_efetiva} '
                f'(antes={qty_antes}); cancelar pickings ou usar resetar_reserva'
            )
            return r

        # --- 6. NOOP (nada muda e sem reset) ---
        if existe and qty_apos == qty_antes and not resetar_reserva:
            r['status'] = 'NOOP'
            return r

        # --- 7. Dry-run ---
        if dry_run:
            r['status'] = 'DRY_RUN_OK'
            return r

        # --- 8. Executar ---
        try:
            if existe:
                if resetar_reserva and reservada != 0:
                    self.odoo.write('stock.quant', [quant['id']], {'reserved_quantity': 0})
                    r['acao'] = 'reset_reserva'
                self.odoo.write('stock.quant', [quant['id']], {'inventory_quantity': qty_apos})
                self.odoo.execute_kw('stock.quant', 'action_apply_inventory', [[quant['id']]])
                r['quant_id'] = quant['id']
                r['acao'] = 'updated' if r['acao'] != 'reset_reserva' else 'reset_reserva+updated'
            else:
                payload = {
                    'product_id': product_id,
                    'company_id': company_id,
                    'location_id': location_id,
                    'inventory_quantity': qty_apos,
                }
                if lot_id is not None:
                    payload['lot_id'] = lot_id
                novo_id = self.odoo.create('stock.quant', payload)
                self.odoo.execute_kw('stock.quant', 'action_apply_inventory', [[novo_id]])
                r['quant_id'] = novo_id
                r['acao'] = 'created'
            r['status'] = 'EXECUTADO_AUTO_CORRIGIDO' if r.get('auto_correcao_aplicada') else 'EXECUTADO'
        except Exception as exc:
            r['status'] = 'FALHA_ODOO'
            r['erro'] = str(exc)
            logger.exception(
                f'Falha ajustar quant (product={product_id} lot={lot_id} '
                f'qty_apos={qty_apos}): {exc}'
            )

        r['tempo_ms'] = int((time.time() - inicio) * 1000)
        return r
