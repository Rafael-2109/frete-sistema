"""TDD — normalizacao do modulo app/resolvedores. Funcoes puras (sem banco).

Port fiel de resolver_entidades.py: normalizar_texto (:61) e _normalizar_token (:1117).
"""
from app.resolvedores.normalizacao import normalizar_texto, _normalizar_token


class TestNormalizarTexto:
    def test_remove_acento_e_minuscula(self):
        assert normalizar_texto("Itanhaém") == "itanhaem"

    def test_sao_paulo(self):
        assert normalizar_texto("São Paulo") == "sao paulo"

    def test_peruibe_maiuscula(self):
        assert normalizar_texto("PERUÍBE") == "peruibe"

    def test_mongagua(self):
        assert normalizar_texto("Mongaguá") == "mongagua"

    def test_strip_espacos(self):
        assert normalizar_texto("  Santos  ") == "santos"

    def test_vazio(self):
        assert normalizar_texto("") == ""

    def test_none(self):
        assert normalizar_texto(None) == ""

    def test_accent_insensitive_equivalencia(self):
        # Prova da correcao do bug da split: termo cru e termo com acento normalizam igual.
        # E o que torna a busca de cidade accent-insensitive de verdade.
        assert normalizar_texto("itanhaem") == normalizar_texto("Itanhaém")


class TestNormalizarToken:
    def test_plural_stemming(self):
        assert _normalizar_token("azeitonas") == "azeitona"

    def test_palmitos(self):
        assert _normalizar_token("palmitos") == "palmito"

    def test_token_curto_preserva_s(self):
        # < 5 chars: nao remove 's' (protege abreviacoes/embalagens como 'br', 'bd', 'gl')
        assert _normalizar_token("cs") == "cs"

    def test_br_preservado(self):
        assert _normalizar_token("br") == "br"

    def test_lowercase(self):
        assert _normalizar_token("AZEITONA") == "azeitona"

    def test_sem_s_final_inalterado(self):
        assert _normalizar_token("balde") == "balde"
