"""
Testes do classificador de produtos Odoo (produtivo/revenda).

Cobre app/odoo/utils/classificacao_produto.py — funcoes puras (sem Odoo/DB).
Casos baseados na exploracao real do Odoo CIEL IT (2026-05-28).
"""
import pytest

from app.odoo.utils.classificacao_produto import (
    extrair_categoria_raiz,
    classificar_natureza_compra,
    classificar_produto_odoo,
)


class TestExtrairCategoriaRaiz:
    @pytest.mark.parametrize("complete_name,esperado", [
        ("TODOS / MATERIA PRIMA / MP NAC / PALMITO", "MATERIA PRIMA"),
        ("TODOS / EMBALAGEM / EMB 1 / POUCH", "EMBALAGEM"),
        ("TODOS / SEMI ACABADOS", "SEMI ACABADOS"),
        ("TODOS / PRODUTO ACABADO / CONSERVAS / PALMITO", "PRODUTO ACABADO"),
        ("TODOS / USO E CONSUMO / X", "USO E CONSUMO"),
        ("  TODOS / Materia Prima / x  ", "MATERIA PRIMA"),   # case + trim
        ("MATERIA PRIMA / MP NAC", "MATERIA PRIMA"),          # arvore sem "TODOS" no topo
    ])
    def test_extrai_raiz(self, complete_name, esperado):
        assert extrair_categoria_raiz(complete_name) == esperado

    @pytest.mark.parametrize("entrada", [None, "", "   ", "TODOS", "TODOS / "])
    def test_generico_ou_vazio_retorna_none(self, entrada):
        assert extrair_categoria_raiz(entrada) is None


class TestClassificarNaturezaCompra:
    @pytest.mark.parametrize("raiz,tipo,esperado", [
        # produtivo por categoria-raiz
        ("MATERIA PRIMA", None, "PRODUTIVO"),
        ("EMBALAGEM", None, "PRODUTIVO"),
        ("SEMI ACABADOS", None, "PRODUTIVO"),
        # revenda so via tipo fiscal 00
        ("PRODUTO ACABADO", "00", "REVENDA"),
        # categorias que NAO registram
        ("USO E CONSUMO", None, None),
        ("DESPESAS", None, None),
        ("ATIVO FIXO", None, None),
        ("ATIVO INTANGÍVEL", None, None),
        ("SERVIÇO", None, None),
        ("PRODUTO ACABADO", None, None),    # acabado sem tipo revenda nao entra no sync compras
        # produtivo por tipo fiscal explicito
        (None, "01", "PRODUTIVO"),
        (None, "02", "PRODUTIVO"),
        (None, "06", "PRODUTIVO"),
        (None, "10", "PRODUTIVO"),
        # revenda por tipo
        (None, "00", "REVENDA"),
        # tipos que NAO registram
        (None, "07", None),                 # uso e consumo
        (None, "08", None),                 # ativo imobilizado
        (None, "09", None),                 # servico
        (None, "04", None),                 # produto acabado
        (None, None, None),
        (None, False, None),                # Odoo manda False quando vazio
    ])
    def test_classifica(self, raiz, tipo, esperado):
        assert classificar_natureza_compra(raiz, tipo) == esperado

    def test_revenda_tem_prioridade_sobre_categoria(self):
        # tipo 00 (revenda) vence mesmo se a categoria fosse produtiva
        assert classificar_natureza_compra("MATERIA PRIMA", "00") == "REVENDA"


class TestClassificarProdutoOdoo:
    def test_wrapper_combina_extrair_e_classificar(self):
        assert classificar_produto_odoo("TODOS / MATERIA PRIMA / MP NAC", False) == "PRODUTIVO"
        assert classificar_produto_odoo("TODOS / EMBALAGEM / EMB 2 / CAIXA", False) == "PRODUTIVO"
        assert classificar_produto_odoo("TODOS / USO E CONSUMO / X", False) is None
        assert classificar_produto_odoo("TODOS / PRODUTO ACABADO / CONSERVAS", "00") == "REVENDA"
        assert classificar_produto_odoo(None, None) is None
