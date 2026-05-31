"""
Testa verifier arithmético (Parte A — B2, Onda 2).

Cobertura:
- test_verify_arithmetic_ok: LLM diz OK → retorna ok=True, issues=[]
- test_verify_arithmetic_erro: LLM aponta erro → retorna ok=False + issues preenchido
- test_verify_arithmetic_best_effort: exceção em _call_sonnet_verifier → ok=True, issues=[] (sem propagar)
- test_verify_arithmetic_contexto_injeta_no_prompt: contexto opcional aparece no prompt enviado ao LLM
"""


# ─── Fixtures ─────────────────────────────────────────────────────────────────

RESPONSE_COM_TABELA = """
## Resumo de pedidos

| Pedido | Qtd | Total |
|--------|-----|-------|
| VCD001 | 10  | R$ 100 |
| VCD002 | 5   | R$ 50  |
| VCD003 | 3   | R$ 30  |

Total geral: 20 itens, R$ 200
"""

RESPONSE_CURTA = "OK, o pedido foi processado."


# ─── Testes unitários (sem LLM real) ─────────────────────────────────────────

def test_verify_arithmetic_ok(monkeypatch):
    """LLM diz OK → retorna ok=True, issues=[] (nenhum problema aritmético)."""
    from app.agente.sdk import verifiers

    # Mock: _call_sonnet_verifier retorna "OK"
    monkeypatch.setattr(verifiers, '_call_sonnet_verifier', lambda prompt: 'OK')

    result = verifiers.verify_arithmetic(RESPONSE_COM_TABELA)

    assert result['ok'] is True
    assert result['issues'] == []


def test_verify_arithmetic_erro(monkeypatch):
    """LLM aponta erro aritmético → retorna ok=False + issues com descrição."""
    from app.agente.sdk import verifiers

    erro_mensagem = 'Total diz 20 itens mas tabela soma 18'
    monkeypatch.setattr(verifiers, '_call_sonnet_verifier', lambda prompt: erro_mensagem)

    result = verifiers.verify_arithmetic(RESPONSE_COM_TABELA)

    assert result['ok'] is False
    assert len(result['issues']) > 0
    assert any('20' in issue or '18' in issue or 'total' in issue.lower()
               for issue in result['issues'])


def test_verify_arithmetic_best_effort(monkeypatch):
    """Exceção em _call_sonnet_verifier → best-effort: ok=True, issues=[] (não propaga)."""
    from app.agente.sdk import verifiers

    def _explode(prompt):
        raise RuntimeError("API timeout simulado")

    monkeypatch.setattr(verifiers, '_call_sonnet_verifier', _explode)

    # Não deve levantar exceção
    result = verifiers.verify_arithmetic(RESPONSE_COM_TABELA)

    assert result['ok'] is True
    assert result['issues'] == []


def test_verify_arithmetic_contexto_injeta_no_prompt(monkeypatch):
    """Contexto opcional é incluído no prompt enviado ao LLM."""
    from app.agente.sdk import verifiers

    prompts_capturados = []

    def _captura_prompt(prompt):
        prompts_capturados.append(prompt)
        return 'OK'

    monkeypatch.setattr(verifiers, '_call_sonnet_verifier', _captura_prompt)

    contexto = "Sessão: sess-abc-123, Usuário: Rafael"
    verifiers.verify_arithmetic(RESPONSE_COM_TABELA, contexto=contexto)

    assert len(prompts_capturados) == 1
    assert contexto in prompts_capturados[0]


def test_verify_arithmetic_resposta_none():
    """None como response_text → ok=True, issues=[] sem chamar LLM."""
    from app.agente.sdk import verifiers

    result = verifiers.verify_arithmetic(None)

    assert result['ok'] is True
    assert result['issues'] == []


def test_verify_arithmetic_resposta_vazia():
    """String vazia → ok=True, issues=[] sem chamar LLM."""
    from app.agente.sdk import verifiers

    result = verifiers.verify_arithmetic('')

    assert result['ok'] is True
    assert result['issues'] == []
