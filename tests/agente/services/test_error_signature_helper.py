"""Helper `gerar_error_signature` — captura universal de error_signature (loop corretivo).

Gera a assinatura de intencao normalizada de um erro a partir da descricao/prescricao,
usando Haiku (mesma instrucao do extrator) com fallback DETERMINISTICO quando o LLM esta
indisponivel. Reusado por: (a) backfill universal do passivo historico; (b) fallback
organico em `_save_personal_insight` quando o extrator omite o campo.

Sem custo de API: o cliente LLM e' SEMPRE injetado (fake) ou ausente (-> deterministico).
"""


class _FakeResp:
    def __init__(self, text):
        self.content = [type('Block', (), {'text': text})()]


class _FakeMessages:
    def __init__(self, text=None, exc=None):
        self._text = text
        self._exc = exc
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._exc is not None:
            raise self._exc
        return _FakeResp(self._text)


class _FakeClient:
    """Stub do Anthropic client: retorna `text` fixo ou levanta `exc`."""
    def __init__(self, text=None, exc=None):
        self.messages = _FakeMessages(text=text, exc=exc)


def _so_chars_validos(s: str) -> bool:
    return all(c.islower() or c.isdigit() or c == '_' for c in s)


def test_gera_assinatura_via_llm():
    from app.agente.services.pattern_analyzer import gerar_error_signature
    cli = _FakeClient(text='troca_de_escopo')
    out = gerar_error_signature('agente trocou de escopo', 'confirmar antes', client=cli)
    assert out == 'troca_de_escopo'
    # usou o LLM (1 chamada)
    assert len(cli.messages.calls) == 1


def test_normaliza_saida_do_llm_para_snake_case():
    from app.agente.services.pattern_analyzer import gerar_error_signature
    cli = _FakeClient(text='Troca DE Escopo!!')
    assert gerar_error_signature('x relevante', 'y relevante', client=cli) == 'troca_de_escopo'


def test_trunca_em_64_chars():
    from app.agente.services.pattern_analyzer import gerar_error_signature
    cli = _FakeClient(text='a' * 100)
    out = gerar_error_signature('erro relevante', 'faca assim', client=cli)
    assert len(out) <= 64
    assert out == 'a' * 64


def test_remove_acentos_e_caracteres_invalidos():
    from app.agente.services.pattern_analyzer import gerar_error_signature
    cli = _FakeClient(text='Não Pão #$% Test')
    out = gerar_error_signature('erro relevante', 'faca assim', client=cli)
    assert out == 'nao_pao_test'
    assert _so_chars_validos(out)


def test_fallback_deterministico_quando_llm_falha():
    from app.agente.services.pattern_analyzer import gerar_error_signature
    cli = _FakeClient(exc=RuntimeError('sem api'))
    desc = 'Agente buscou produto errado para pepino-ind'
    out = gerar_error_signature(desc, 'usar o codigo correto', client=cli)
    assert out, 'fallback deterministico nao pode ser vazio'
    assert _so_chars_validos(out)
    assert len(out) <= 64
    # DETERMINISTICO: mesma entrada -> mesma saida (condicao para casar reincidencia)
    out2 = gerar_error_signature(desc, 'usar o codigo correto', client=cli)
    assert out == out2


def test_fallback_deterministico_sem_client_e_sem_api(monkeypatch):
    """client=None e sem ANTHROPIC_API_KEY -> NUNCA toca a rede, vai direto ao deterministico."""
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    import app.agente.services.pattern_analyzer as pa
    # se tentar instanciar o client real, falha o teste (nao deve ser chamado)
    monkeypatch.setattr(pa, '_get_anthropic_client',
                        lambda: (_ for _ in ()).throw(AssertionError('nao deve chamar o LLM')))
    out = pa.gerar_error_signature('agente ignorou o veto do usuario', 'nunca executar item vetado')
    assert out
    assert _so_chars_validos(out)


def test_descricao_vazia_retorna_vazio():
    from app.agente.services.pattern_analyzer import gerar_error_signature
    cli = _FakeClient(text='qualquer_coisa')
    assert gerar_error_signature('', '', client=cli) == ''
    assert gerar_error_signature('   ', None, client=cli) == ''


def test_llm_retorna_vazio_cai_no_fallback():
    from app.agente.services.pattern_analyzer import gerar_error_signature
    cli = _FakeClient(text='   ')
    out = gerar_error_signature('erro relevante que importa', 'faca assim', client=cli)
    assert out, 'LLM vazio deve cair no fallback deterministico'
    assert _so_chars_validos(out)
