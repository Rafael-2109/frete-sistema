"""Testes do CLI da skill `reclassificando-amls-odoo` (parser + exit codes).

Testa SO o parser/argparse e os codigos de saida — DETERMINISTICO, sem app
context, sem Odoo, sem DB. A logica WRITE e coberta por
test_reclassificacao_service.py (FakeOdoo).

Exit codes:
  0 efetivado · 4 dry-run OK · 1 falha · 2 uso invalido.
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / '.claude/skills/reclassificando-amls-odoo/scripts/reclassificar_amls.py'


def _load():
    spec = importlib.util.spec_from_file_location('reclassificar_amls', CLI)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope='module')
def mod():
    return _load()


# ---------------------------------------------------------------------------
# Parser — args obrigatorios e defaults
# ---------------------------------------------------------------------------
def test_parser_args_completos(mod):
    args = mod.build_parser().parse_args([
        '--conta-origem', '26784', '--conta-destino', '26844',
        '--data-inicio', '2025-09-01', '--data-fim', '2025-09-30',
        '--company-id', '4', '--user-id', '74',
    ])
    assert args.conta_origem == 26784
    assert args.conta_destino == 26844
    assert args.data_inicio == '2025-09-01'
    assert args.data_fim == '2025-09-30'
    assert args.company_id == 4
    assert args.journal_id == 845       # default
    assert args.user_id == 74
    assert args.confirmar is False       # dry-run default
    assert args.json is False


def test_parser_journal_default_845(mod):
    args = mod.build_parser().parse_args([
        '--conta-origem', '26784', '--conta-destino', '26844',
        '--data-inicio', '2025-09-01', '--data-fim', '2025-09-30',
        '--company-id', '4', '--user-id', '74',
    ])
    assert args.journal_id == 845


def test_parser_user_id_obrigatorio(mod):
    # Sem --user-id, argparse aborta com SystemExit (exit 2 de uso).
    with pytest.raises(SystemExit):
        mod.build_parser().parse_args([
            '--conta-origem', '26784', '--conta-destino', '26844',
            '--data-inicio', '2025-09-01', '--data-fim', '2025-09-30',
            '--company-id', '4',
        ])


def test_parser_confirmar_flag(mod):
    args = mod.build_parser().parse_args([
        '--conta-origem', '26784', '--conta-destino', '26844',
        '--data-inicio', '2025-09-01', '--data-fim', '2025-09-30',
        '--company-id', '4', '--user-id', '74', '--confirmar',
    ])
    assert args.confirmar is True


# ---------------------------------------------------------------------------
# Mapeamento status -> exit code
# ---------------------------------------------------------------------------
def test_exit_code_dry_run(mod):
    assert mod._exit_para_status('DRY_RUN_OK', dry_run=True) == 4


def test_exit_code_executado(mod):
    assert mod._exit_para_status('EXECUTADO', dry_run=False) == 0


def test_exit_code_falha_post(mod):
    assert mod._exit_para_status('FALHA_POST_NAO_POSTED', dry_run=False) == 1


def test_exit_code_falha_odoo(mod):
    assert mod._exit_para_status('FALHA_ODOO', dry_run=False) == 1


def test_exit_code_executado_parcial(mod):
    assert mod._exit_para_status('EXECUTADO_PARCIAL', dry_run=False) == 1
