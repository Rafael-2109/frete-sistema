"""Regressao de aridade: `_resolver_preco_tabela` retorna uma 5-tupla.

Contexto (migration hora_33, 2026-05-06): `_resolver_preco_tabela` passou a
retornar `(preco_ref, desconto_rs, desconto_pct, tabela_id, divergencia)` — 5
valores. O call site em `app/hora/services/tagplus/backfill_service.py`
(`_criar_itens_da_api`) ficou esquecido desempacotando apenas 4, causando em
producao no backfill de NFs TagPlus:

    ValueError: too many values to unpack (expected 4)

Este teste e um guard estatico (sem DB, deterministico): varre todo o modulo
`app/hora` via AST e exige que QUALQUER atribuicao que desempacote o retorno de
`_resolver_preco_tabela` em uma tupla tenha exatamente 5 alvos. Falharia na
versao anterior ao fix (call site com 4 alvos) e passa apos a correcao.

Funciona como contrato vivo: se um dia a funcao mudar de aridade, atualize a
constante `ARIDADE_ESPERADA` e todos os call sites de uma vez.
"""
from __future__ import annotations

import ast
from pathlib import Path

ARIDADE_ESPERADA = 5
RAIZ_HORA = Path(__file__).resolve().parents[2] / 'app' / 'hora'


def _nome_funcao_chamada(call: ast.Call) -> str | None:
    """Extrai o nome da funcao chamada (suporta `f()` e `obj.f()`)."""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _coletar_desempacotamentos(arquivo: Path) -> list[tuple[int, int]]:
    """Retorna [(linha, n_alvos)] de cada desempacotamento em tupla de
    `_resolver_preco_tabela(...)` no arquivo."""
    tree = ast.parse(arquivo.read_text(encoding='utf-8'))
    achados: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        if _nome_funcao_chamada(node.value) != '_resolver_preco_tabela':
            continue
        for alvo in node.targets:
            if isinstance(alvo, (ast.Tuple, ast.List)):
                achados.append((node.lineno, len(alvo.elts)))
    return achados


def test_todos_call_sites_desempacotam_aridade_correta():
    violacoes: list[str] = []
    total_call_sites = 0
    for arquivo in RAIZ_HORA.rglob('*.py'):
        for linha, n_alvos in _coletar_desempacotamentos(arquivo):
            total_call_sites += 1
            if n_alvos != ARIDADE_ESPERADA:
                rel = arquivo.relative_to(RAIZ_HORA.parents[1])
                violacoes.append(
                    f'{rel}:{linha} desempacota {n_alvos} valores '
                    f'(esperado {ARIDADE_ESPERADA})'
                )

    assert total_call_sites > 0, (
        'Nenhum desempacotamento de _resolver_preco_tabela encontrado — '
        'o teste perdeu cobertura (funcao renomeada?).'
    )
    assert not violacoes, (
        'Desempacotamento de _resolver_preco_tabela com aridade errada '
        '(bug "too many values to unpack"):\n  ' + '\n  '.join(violacoes)
    )
