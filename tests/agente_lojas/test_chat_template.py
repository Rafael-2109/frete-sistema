"""Testes de regressao do template chat.html do Agente Lojas HORA.

Cobre dois bugs reais que tornavam o chat inutilizavel (a tela "piscava" e a
mensagem sumia):

  Bug 1 — `new bootstrap.Modal(...)` rodava em parse-time DENTRO do
    `{% block content %}`. No base.html o `{% block content %}` e renderizado
    ANTES da tag <script> do bootstrap.bundle.min.js, entao `bootstrap` ainda
    nao existia -> ReferenceError abortava o IIFE inteiro -> o
    `form.addEventListener('submit', ...)` nunca era registrado -> o <form>
    fazia submit HTTP nativo (reload). Fix: mover o <script> para
    `{% block scripts %}` (renderizado DEPOIS do bootstrap no base.html).

  Bug 2 — os fetch POST (/api/chat e /api/user-answer) nao enviavam o header
    X-CSRFToken. Como CSRFProtect e global e as rotas /agente-lojas/api/* nao
    estao isentas, o POST retornaria 400. Fix: enviar X-CSRFToken lido do
    <meta name="csrf-token">.

Testes 100% estaticos (AST Jinja + source) — deterministicos, sem app/db.
"""
import os

import jinja2
import pytest
from jinja2 import nodes

TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..',
    'app', 'agente_lojas', 'templates', 'agente_lojas', 'chat.html',
)


def _source():
    with open(TEMPLATE_PATH, encoding='utf-8') as fh:
        return fh.read()


def _block_text_map(source):
    """Mapa {nome_do_block: texto_literal_concatenado} via AST do Jinja.

    `env.parse` levanta TemplateSyntaxError se os blocks estiverem
    desbalanceados, cobrindo o smoke de sintaxe de graca.
    """
    ast = jinja2.Environment().parse(source)
    mapping = {}
    for block in ast.find_all(nodes.Block):
        literais = [n.data for n in block.find_all(nodes.TemplateData)]
        mapping[block.name] = ''.join(literais)
    return mapping


class TestChatTemplateEstrutura:
    def test_template_compila_sem_erro(self):
        # Blocks desbalanceados levantariam TemplateSyntaxError aqui.
        _block_text_map(_source())

    def test_existe_block_scripts(self):
        blocks = _block_text_map(_source())
        assert 'scripts' in blocks, (
            "O <script> do chat precisa morar em {% block scripts %} para "
            "rodar DEPOIS do bootstrap.bundle.min.js (base.html)."
        )

    def test_bootstrap_modal_no_block_scripts_nao_no_content(self):
        """Bug 1: codigo bootstrap-dependente NAO pode estar no block content."""
        blocks = _block_text_map(_source())
        assert 'new bootstrap.Modal' in blocks.get('scripts', ''), (
            "new bootstrap.Modal deve estar no block scripts (apos o bootstrap)."
        )
        assert 'new bootstrap.Modal' not in blocks.get('content', ''), (
            "REGRESSAO Bug 1: new bootstrap.Modal voltou ao block content — "
            "vai estourar ReferenceError em parse-time e quebrar o submit."
        )

    def test_listener_submit_no_block_scripts(self):
        """O handler de submit (que faz preventDefault) precisa ser registrado."""
        blocks = _block_text_map(_source())
        assert "addEventListener('submit'" in blocks.get('scripts', '')


class TestChatTemplateCsrf:
    def test_const_csrf_definida(self):
        assert 'const csrfToken' in _source()

    def test_ambos_posts_enviam_csrf(self):
        """Bug 2: os 2 fetch POST devem mandar X-CSRFToken."""
        src = _source()
        assert src.count("'X-CSRFToken': csrfToken") == 2, (
            "REGRESSAO Bug 2: esperados 2 headers X-CSRFToken (chat + "
            "user-answer); encontrados "
            f"{src.count(chr(39) + 'X-CSRFToken' + chr(39) + ': csrfToken')}."
        )

    def test_endpoints_post_presentes(self):
        src = _source()
        assert "fetch('/agente-lojas/api/chat'" in src
        assert "fetch('/agente-lojas/api/user-answer'" in src


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
