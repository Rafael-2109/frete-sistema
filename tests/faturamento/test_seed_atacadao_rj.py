"""Testa a integridade da lista embutida no seed do Atacadao RJ (sem banco)."""
import importlib.util
import os

_SEED = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'scripts', 'migrations', '2026_07_01_seed_alertas_faturamento_atacadao_rj.py',
)
_spec = importlib.util.spec_from_file_location('seed_atacadao_rj', _SEED)
seed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed)


def test_lista_tem_31_cnpjs():
    assert len(seed.CNPJS_ATACADAO_RJ) == 31


def test_cnpjs_normalizados_e_unicos():
    cnpjs = [c for c, _ in seed.CNPJS_ATACADAO_RJ]
    assert all(c.isdigit() and len(c) == 14 for c in cnpjs)
    assert len(set(cnpjs)) == 31  # sem duplicados


def test_emails_padrao_quatro_minusculo():
    assert seed.EMAILS_PADRAO.count('@') == 4
    assert seed.EMAILS_PADRAO == seed.EMAILS_PADRAO.lower()
