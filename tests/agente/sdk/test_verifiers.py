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


# ─── Bug do parser (2026-06-03) — falso-positivo 42/201 em PROD ───────────────
# O Sonnet é um modelo de raciocínio: ignora "responda EXATAMENTE OK" e RACIOCINA
# passo-a-passo, concluindo com "OK"/✓ (aritmética correta). O parser antigo exigia
# `resultado.upper() == 'OK'` exato → o raciocínio (len≫5, ≠ 'OK') caía no else e
# marcava ok=False com o próprio raciocínio como "issue". Fix: discriminar pela
# CONCLUSÃO (última linha == OK OU veredito estruturado), não por igualdade exata
# nem pela palavra "ERRO" (uma descrição de erro pode não conter "ERRO").

class TestVerifyArithmeticParserRobusto:
    """Parser robusto a raciocínio do Sonnet (bug 2026-06-03)."""

    def _run(self, fake_out, monkeypatch):
        from app.agente.sdk import verifiers
        monkeypatch.setattr(verifiers, '_call_sonnet_verifier', lambda prompt: fake_out)
        return verifiers.verify_arithmetic("resposta com numeros")

    def test_raciocinio_concluindo_ok(self, monkeypatch):
        # Caso real PROD (step 196/199): raciocínio correto concluindo com OK.
        out = "Verificando: 1.549 + 290 + 2 + 25 = 1.866 (confere)\n\nOK"
        assert self._run(out, monkeypatch) == {'ok': True, 'issues': []}

    def test_raciocinio_confere_concluindo_ok(self, monkeypatch):
        # Caso real PROD (step 195): linha única de cálculo + conclusão OK.
        out = "41 + 37 + 3 = 81, confere com o total declarado.\n\nOK"
        assert self._run(out, monkeypatch)['ok'] is True

    def test_veredito_estruturado_ok(self, monkeypatch):
        # Novo contrato do prompt: veredito explícito.
        assert self._run("VEREDITO: OK", monkeypatch)['ok'] is True

    def test_veredito_estruturado_erro(self, monkeypatch):
        out = "Conferindo a soma...\nVEREDITO: ERRO — total diz 5 itens mas a tabela tem 8"
        r = self._run(out, monkeypatch)
        assert r['ok'] is False
        assert r['issues'] and 'ERRO' in r['issues'][0]

    def test_descricao_de_erro_sem_palavra_erro(self, monkeypatch):
        # Garante que o fix NÃO regride o contrato existente: uma descrição de
        # discrepância (sem 'OK' na conclusão) continua sendo ok=False.
        out = "Total diz 20 itens mas a tabela soma 18"
        assert self._run(out, monkeypatch)['ok'] is False
