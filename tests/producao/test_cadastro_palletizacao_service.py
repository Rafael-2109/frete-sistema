"""
Testes do service garantir_cadastro_basico (CadastroPalletizacao).

Cobre app/producao/services/cadastro_palletizacao_service.py.
Usa a fixture `db` (savepoint + rollback) do tests/conftest.py.
"""
import uuid
import pytest

from app.producao.services.cadastro_palletizacao_service import garantir_cadastro_basico
from app.producao.models import CadastroPalletizacao


def _cod():
    """Codigo de produto unico para nao colidir com dados existentes."""
    return f"TEST{uuid.uuid4().hex[:10]}"


class TestGarantirCadastroBasico:
    def test_cria_produtivo_flags(self, db):
        cod = _cod()
        cad, criado = garantir_cadastro_basico(cod, "MP TESTE", "PRODUTIVO", "pytest")
        assert criado is True
        assert cad.cod_produto == cod
        assert cad.nome_produto == "MP TESTE"
        assert cad.palletizacao == 0
        assert cad.peso_bruto == 0
        assert cad.ativo is True
        assert cad.produto_comprado is True
        assert cad.produto_produzido is False
        assert cad.produto_vendido is False

    def test_cria_revenda_flags(self, db):
        cad, criado = garantir_cadastro_basico(_cod(), "REV TESTE", "REVENDA", "pytest")
        assert criado is True
        assert cad.produto_comprado is True
        assert cad.produto_produzido is False
        assert cad.produto_vendido is True

    def test_cria_acabado_lf_flags(self, db):
        cad, criado = garantir_cadastro_basico(_cod(), "ACABADO LF", "ACABADO_LF", "pytest")
        assert criado is True
        assert cad.produto_comprado is False
        assert cad.produto_produzido is True
        assert cad.produto_vendido is True

    def test_idempotente_nao_duplica_nem_altera(self, db):
        cod = _cod()
        cad1, criado1 = garantir_cadastro_basico(cod, "ORIGINAL", "PRODUTIVO", "pytest")
        cad2, criado2 = garantir_cadastro_basico(cod, "Y DIFERENTE", "REVENDA", "pytest")
        assert criado1 is True
        assert criado2 is False
        assert cad1.id == cad2.id
        # nao altera o cadastro existente
        assert cad2.nome_produto == "ORIGINAL"
        assert cad2.produto_vendido is False  # manteve flags de PRODUTIVO
        assert CadastroPalletizacao.query.filter_by(cod_produto=cod).count() == 1

    def test_nome_truncado_255(self, db):
        cad, _ = garantir_cadastro_basico(_cod(), "A" * 300, "PRODUTIVO", "pytest")
        assert len(cad.nome_produto) == 255

    def test_nome_vazio_usa_codigo(self, db):
        cod = _cod()
        cad, _ = garantir_cadastro_basico(cod, "", "PRODUTIVO", "pytest")
        assert cad.nome_produto == cod

    def test_natureza_invalida_levanta(self, db):
        with pytest.raises(ValueError, match="Natureza desconhecida"):
            garantir_cadastro_basico(_cod(), "X", "INEXISTENTE", "pytest")

    def test_cod_vazio_levanta(self, db):
        with pytest.raises(ValueError, match="cod_produto vazio"):
            garantir_cadastro_basico("", "X", "PRODUTIVO", "pytest")
