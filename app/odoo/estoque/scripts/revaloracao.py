# etapa: WRITE
# doc-dono: app/odoo/estoque/CLAUDE.md §6
"""RevaloracaoCustoService — átomo WRITE para ajustar o custo (AVCO) de um produto no
Odoo via wizard `stock.valuation.layer.revaluation`.

Skill: `revalorando-custo-odoo` (objeto Odoo = `stock.valuation.layer` via o wizard).
Constituição: `app/odoo/estoque/CLAUDE.md` §1.1 (1 skill = 1 objeto novo).

Caso de uso provado (s65/s67 — FLUXO L3 1.2.4, passo C): na entrada do retorno de
industrialização, nenhuma das 2 NFs incorpora o PA por Ic+S. Após escriturar, ajusta-se
o custo do PA por **+Ic** com contrapartida na conta que **SOBRA na NF-2** (transitória
`1150100011`, NÃO o CMV — `s65`): `D 1150100007 PA / C 1150100011`, fechando a transitória.

🔴 Achado AVCO (s67): o wizard opera sobre o **AVCO do produto inteiro** (pool de N un) →
o `added_value` DILUI por unidade (inevitável — qualquer veículo recalcula a média). O
gate `PA=Ic+S` é medido pela **CONTA de estoque** (`1150100007`), não pelo `std_price`
unitário (decisão Rafael 2026-06-15).

Reversão: não há `unlink` de revaloração — compensar por revaloração INVERSA (padrão s66).

`--dry-run` é o DEFAULT (mostra o plano do wizard, NÃO escreve) → `--confirmar` executa.
"""
import logging
from typing import Any, Dict, List, Optional

from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


class RevaloracaoCustoService:
    """Skill `revalorando-custo-odoo`: ajusta AVCO via stock.valuation.layer.revaluation."""

    def __init__(self, odoo=None):
        self.odoo = odoo or get_odoo_connection()

    def revalorar_custo(
        self,
        *,
        product_id: int,
        added_value: float,
        account_id: int,
        account_journal_id: int,
        company_id: int,
        reason: str,
        currency_id: Optional[int] = None,
        allowed_company_ids: Optional[List[int]] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Revaloriza o custo (AVCO) de `product_id` por `added_value`.

        Args:
            product_id: produto a revalorizar (ex.: PA 27834).
            added_value: delta de valor (+Ic). Positivo sobe o custo; negativo desfaz.
            account_id: account.account da contrapartida. Na industrialização = a conta
                que SOBRA na NF-2 (transitória 1150100011 = id 26842), NÃO o CMV (s65/s67).
            account_journal_id: diário da revaloração (ex.: 8 general ESTOQ).
            company_id: empresa (ex.: FB=1).
            reason: descrição (ex.: 'Ic industrializacao retorno PILOTO 4870112').
            currency_id: moeda; se None, resolve da res.company.
            allowed_company_ids: contexto multi-company (default [company_id]).
            dry_run: True (default) NÃO escreve — retorna o plano do wizard.

        Returns:
            status: 'DRY_RUN_OK' | 'REVALORADO' | 'FALHA'
            + plano (dry-run) | wizard_id (real) | added_value | erro
        """
        out: Dict[str, Any] = {'status': 'FALHA', 'wizard_id': None, 'erro': None}
        # pré-cond LEVES (sem raise — dry-run sempre planeja; AP4)
        for campo, val in (('product_id', product_id), ('account_id', account_id),
                           ('account_journal_id', account_journal_id), ('company_id', company_id)):
            if not isinstance(val, int) or val <= 0:
                out['erro'] = f'{campo}_invalido'
                return out
        if not added_value:
            out['erro'] = 'added_value_zero (revaloracao no-op)'
            return out

        plano = {
            'product_id': product_id,
            'added_value': added_value,
            'account_id': account_id,           # contrapartida = transitória, NÃO CMV (s65)
            'account_journal_id': account_journal_id,
            'company_id': company_id,
            'reason': reason,
        }
        if dry_run:
            out.update(status='DRY_RUN_OK', plano=plano, added_value=added_value)
            return out

        ctx = {'allowed_company_ids': allowed_company_ids or [company_id],
               'company_id': company_id, 'lang': 'pt_BR'}
        try:
            if currency_id is None:
                comp = self.odoo.read('res.company', [company_id], ['currency_id'])
                currency_id = comp[0]['currency_id'][0] if comp and comp[0].get('currency_id') else None
            wid = self.odoo.execute_kw(
                'stock.valuation.layer.revaluation', 'create',
                [{'company_id': company_id, 'currency_id': currency_id, 'product_id': product_id,
                  'added_value': added_value, 'account_id': account_id,
                  'account_journal_id': account_journal_id, 'reason': reason}],
                {'context': ctx})
            self.odoo.execute_kw(
                'stock.valuation.layer.revaluation', 'action_validate_revaluation',
                [[wid]], {'context': ctx})
        except Exception as e:
            out['erro'] = f'revaloracao_falhou: {str(e)[:200]}'
            return out

        out.update(status='REVALORADO',
                   wizard_id=int(wid) if isinstance(wid, (int, float)) else None,
                   added_value=added_value)
        return out
