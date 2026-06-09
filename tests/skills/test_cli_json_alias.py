"""BUG #3 — `--json` como alias de `--formato json` nos scripts CLI de skill.

A convencao majoritaria dos scripts de skill e `--json` (booleano). Dois scripts
divergiam usando `--formato {json,tabela}`: o agente generalizou `--json` e
quebrou (`Expecting value`). Estes testes garantem que `--json` e aceito e forca
formato='json', sem quebrar `--formato` explicito nem o default de cada script.
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONSULTAR_QUANTS = ROOT / '.claude/skills/consultando-quant-odoo/scripts/consultar_quants.py'
STATUS_ENTREGA = ROOT / '.claude/skills/monitorando-entregas/scripts/consultando_status_entrega.py'


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope='module')
def quants_mod():
    return _load(CONSULTAR_QUANTS)


@pytest.fixture(scope='module')
def entrega_mod():
    return _load(STATUS_ENTREGA)


# ---- consultar_quants.py (default formato=tabela) ----

def test_quants_json_alias_forca_json(quants_mod):
    args = quants_mod._aplicar_alias_json(
        quants_mod.build_parser().parse_args(['--cods', 'X', '--json'])
    )
    assert args.formato == 'json'


def test_quants_default_tabela(quants_mod):
    args = quants_mod._aplicar_alias_json(
        quants_mod.build_parser().parse_args(['--cods', 'X'])
    )
    assert args.formato == 'tabela'


def test_quants_formato_explicito_preservado(quants_mod):
    args = quants_mod._aplicar_alias_json(
        quants_mod.build_parser().parse_args(['--cods', 'X', '--formato', 'json'])
    )
    assert args.formato == 'json'


# ---- consultando_status_entrega.py (default formato=json) ----

def test_entrega_json_alias_forca_json(entrega_mod):
    args = entrega_mod._aplicar_alias_json(
        entrega_mod.build_parser().parse_args(['--nf', '123', '--json'])
    )
    assert args.formato == 'json'


def test_entrega_json_sobrepoe_formato_tabela(entrega_mod):
    """--json tem precedencia sobre --formato tabela."""
    args = entrega_mod._aplicar_alias_json(
        entrega_mod.build_parser().parse_args(['--nf', '123', '--formato', 'tabela', '--json'])
    )
    assert args.formato == 'json'


def test_entrega_formato_tabela_sem_json(entrega_mod):
    args = entrega_mod._aplicar_alias_json(
        entrega_mod.build_parser().parse_args(['--nf', '123', '--formato', 'tabela'])
    )
    assert args.formato == 'tabela'
