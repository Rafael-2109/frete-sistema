"""Frente A (2026-06-03): editar item de pedido NUNCA troca a moto.

A rota `vendas_item_editar` (`app/hora/routes/vendas.py`) deixou de ler
`novo_chassi` do form. Regra de negocio: ao editar uma moto ja no pedido, so
desconto/valor sao editaveis; trocar a moto = remover + readicionar.

Guard estatico via AST (sem DB, deterministico) — mesmo padrao de
`test_resolver_preco_tabela_arity.py`. Falha na versao anterior (rota lia
`request.form.get('novo_chassi')`) e passa apos o fix. O comportamento do
service `editar_item_pedido` (que mantem a capacidade de troca para os testes
de workflow) NAO muda — so a rota deixa de expor a troca.
"""
from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
VENDAS_PY = RAIZ / 'app' / 'hora' / 'routes' / 'vendas.py'


def _func_node(tree: ast.Module, nome: str):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == nome:
            return node
    return None


def test_rota_editar_item_existe():
    tree = ast.parse(VENDAS_PY.read_text(encoding='utf-8'))
    assert _func_node(tree, 'vendas_item_editar') is not None, (
        'funcao vendas_item_editar nao encontrada — teste perdeu cobertura?'
    )


def test_vendas_item_editar_nao_le_novo_chassi_do_form():
    """A rota nao deve mais ter a string literal 'novo_chassi' (lida do form).

    `request.form.get('novo_chassi')` produziria um ast.Constant 'novo_chassi'.
    Passar `novo_chassi=None` como keyword ao service NAO viola (keyword.arg
    nao e Constant nem Name).
    """
    tree = ast.parse(VENDAS_PY.read_text(encoding='utf-8'))
    fn = _func_node(tree, 'vendas_item_editar')
    assert fn is not None

    strs = {
        n.value for n in ast.walk(fn)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    }
    nomes = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}

    assert 'novo_chassi' not in strs, (
        "rota vendas_item_editar ainda le 'novo_chassi' do form — a edicao de "
        'item nao pode trocar a moto (remover + readicionar).'
    )
    assert 'novo_chassi' not in nomes, (
        'rota vendas_item_editar ainda manipula a variavel novo_chassi.'
    )
