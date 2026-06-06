"""Endurecimento do gerador A4 (auditoria de sensores 2026-06-06): rejeitar candidatas-lixo.

Sintoma PROD: das 9 diretrizes-empresa em shadow, 8 eram lixo — "Abordagem validada pelo
judge: BOM DIA", "...: Ola", "Fluxo: Cancelar 3 payments orfaos (33439...) [1 passos]".
Causa (directive_promotion_service.py:220-234 e :100-106): o gerador usa o prompt literal
do usuario como 'when' (saudacoes viram heuristica) e aceita plano de 1 passo (acao unica
hiper-especifica, nao fluxo transferivel). E reward-hacking embrionario — o judge da nota
alta a uma sessao trivial e ela vira diretriz (ver critica/A-flywheel.md secao C1).

Filtro CONSERVADOR (preferir abster a promover ruido — alinhado ao docstring do proprio
gerador judge-driven). NAO altera o pipeline a jusante (R9 anti-gaming + gate continuam).
Funcoes PURAS (sem DB) — teste rapido sem app_context.
"""
import pytest

from app.agente.services.directive_promotion_service import (
    propose_directive_from_judge_session,
    propose_directive_from_plan,
)


def _judge_steps(*pairs, tools=None):
    return [
        {'score': sc, 'label': lb, 'evidencia': f'evid {sc}', 'tools': tools or ['consultando-sql']}
        for sc, lb in pairs
    ]


def _plano(*subjects):
    return {'steps': {str(i + 1): {'subject': s, 'status': 'completed'}
                      for i, s in enumerate(subjects)}}


# ── judge-driven: prompt trivial NAO vira diretriz ──────────────────────────

@pytest.mark.parametrize('meta', [
    'BOM DIA', 'Ola', 'olá', 'oi', 'oi, tudo bem?', 'Obrigado!', 'boa tarde', 'blz',
])
def test_judge_meta_trivial_nao_promove(meta):
    steps = _judge_steps((85, 'success'), (80, 'success'))
    assert propose_directive_from_judge_session('s-triv', steps, user_meta=meta) is None


def test_judge_meta_tarefa_real_promove():
    steps = _judge_steps((85, 'success'), (80, 'success'))
    r = propose_directive_from_judge_session(
        's-real', steps, user_meta='Analise a carteira do Atacadao e priorize os pedidos',
    )
    assert r is not None and r['status'] == 'candidata'


def test_judge_meta_vazio_mantem_fallback():
    """meta vazio cai no fallback generico (comportamento preservado — nao e o lixo trivial)."""
    steps = _judge_steps((85, 'success'), (80, 'success'))
    r = propose_directive_from_judge_session('s-vazio', steps, user_meta='')
    assert r is not None


# ── plan-driven: plano de 1 passo NAO e fluxo transferivel ──────────────────

def test_plano_um_passo_nao_promove():
    assert propose_directive_from_plan(
        _plano('Cancelar payment orfao 33439 no Odoo'), 's-1passo',
    ) is None


def test_plano_dois_passos_promove():
    r = propose_directive_from_plan(_plano('consultar saldo', 'validar lote'), 's-2passos')
    assert r is not None and r['status'] == 'candidata'
