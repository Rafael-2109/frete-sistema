"""Cobre o ramo de idempotência de `devolver_single` (CLI operando-picking-odoo).

O service `StockPickingService.devolver()` já tem TDD (test_stock_picking_service.py).
Falta cobrir o wrapper CLI `devolver_single`, que foi corrigido junto (G-AUDIT-3/N23)
e cujo ramo dry-run era o SINTOMA observável do incidente IMP-2026-06-16-002:
o dry-run retornava `reutilizado_idempotente=true` apontando uma devolução
state=cancel (picking morto, move qty=0 que não restaura saldo).
"""
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_CLI_PATH = (
    _ROOT / '.claude' / 'skills' / 'operando-picking-odoo'
    / 'scripts' / 'operar_picking.py'
)


@pytest.fixture(scope='module')
def cli():
    spec = importlib.util.spec_from_file_location(
        'operar_picking_cli', _CLI_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _svc(existentes):
    svc = MagicMock()
    svc.odoo.read.return_value = [{'name': 'PICK-001', 'state': 'done'}]
    svc.odoo.search_read.return_value = existentes
    return svc


def test_cli_devolver_dry_run_so_cancelada_nao_reutiliza_morto(cli):
    """Dry-run com só devolução cancelada: NÃO marca reutilizado (era o bug)."""
    svc = _svc([{'id': 7777, 'state': 'cancel'}])
    out = cli.devolver_single(svc, picking_id=9999, dry_run=True)
    assert out['status'] == 'DRY_RUN_OK'
    assert out.get('reutilizado_idempotente') is not True  # não reutiliza morto
    assert out.get('devolucoes_canceladas_ignoradas') == [7777]
    assert out['plano'].startswith('Criar')  # plano = criar nova
    svc.devolver.assert_not_called()  # dry-run não efetiva


def test_cli_devolver_real_so_cancelada_cria_nova(cli):
    """Real-run com só cancelada: delega a svc.devolver() e cria nova."""
    svc = _svc([{'id': 7777, 'state': 'cancel'}])
    svc.devolver.return_value = 8888
    svc.odoo.read.side_effect = [
        [{'name': 'PICK-001', 'state': 'done'}],  # pk de origem
        [{'name': 'DEV-PICK-001'}],               # name do novo picking
    ]
    out = cli.devolver_single(svc, picking_id=9999, dry_run=False)
    assert out['status'] == 'DEVOLUCAO_CRIADA'
    assert out['picking_id_devolucao'] == 8888  # NOVA, não a cancelada 7777
    assert out['reutilizado_idempotente'] is False
    svc.devolver.assert_called_once_with(9999)


def test_cli_devolver_prefere_viva_sobre_cancelada(cli):
    """Mistura cancelada + viva: reutiliza a viva, sem chamar svc.devolver()."""
    svc = _svc([
        {'id': 7777, 'state': 'cancel'},
        {'id': 9001, 'state': 'done'},
    ])
    out = cli.devolver_single(svc, picking_id=9999, dry_run=False)
    assert out['status'] == 'DEVOLUCAO_REUTILIZADA'
    assert out['picking_id_devolucao'] == 9001
    assert out.get('devolucoes_canceladas_ignoradas') == [7777]
    svc.devolver.assert_not_called()
