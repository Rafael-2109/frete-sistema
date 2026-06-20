# -*- coding: utf-8 -*-
"""Testes do refino de _score_valor por COBERTURA (2026-06-19).

Pagamento AGRUPADO (1 PIX paga N fretes) = 21% das linhas fatura_cliente. Antes,
o saldo do doc individual (fracao da linha) caia para ~0 e o peso 0.50 do valor
zerava o score do doc correto. O refino trata divergencia grande por DIRECAO:
  - doc CABE na linha (saldo <= linha) -> piso 0.50 (agrupado compativel)
  - doc MAIOR que a linha -> proporcao coberta (valor/saldo), teto 0.45 (monotonia)

Validado empiricamente em scripts/carvia/golden_match_conciliacao.py (286 conc.
reais): top3 57.7->64.0%, docs corretos sem label 14.0->2.8%, cauda 77->64.
"""
import types
from datetime import date

from app.carvia.services.financeiro.carvia_sugestao_service import (
    _score_valor, pontuar_documentos,
)


class TestTiersProximidade:
    """Os tiers de valores ~iguais NAO mudaram (nao-regressao)."""

    def test_exato(self):
        assert _score_valor(1000.0, 1000.0) == 1.0

    def test_ate_1pct(self):
        assert _score_valor(1000.0, 1005.0) == 0.95

    def test_ate_5pct(self):
        assert _score_valor(1000.0, 1040.0) == 0.80

    def test_ate_15pct(self):
        assert _score_valor(1000.0, 1100.0) == 0.50

    def test_valor_invalido_neutro(self):
        assert _score_valor(0, 1000.0) == 0.3
        assert _score_valor(1000.0, 0) == 0.3


class TestCoberturaAgrupado:
    """Pagamento AGRUPADO: doc cabe na linha -> nao penaliza (piso 0.50)."""

    def test_doc_fracao_da_linha_nao_zera(self):
        # 1 PIX de 5000 paga um frete de 1000 (entre outros) -> compativel
        assert _score_valor(5000.0, 1000.0) == 0.50

    def test_doc_metade_da_linha(self):
        assert _score_valor(3000.0, 1500.0) == 0.50

    def test_doc_muito_menor_que_linha(self):
        # antes (V0) isso caia para ~0; agora piso 0.50
        assert _score_valor(24590.0, 1380.0) == 0.50


class TestPagamentoParcial:
    """Doc MAIOR que a linha = pagamento parcial: proporcao coberta, teto 0.45."""

    def test_doc_maior_proporcao_coberta(self):
        # linha 1000 cobre 20% de um doc de 5000
        assert _score_valor(1000.0, 5000.0) == min(0.45, 0.50 * (1000.0 / 5000.0))

    def test_doc_maior_nunca_supera_tier_proximidade(self):
        # monotonia: doc maior com diff>15% nunca passa de 0.45 (< tier 0.50)
        for saldo in (1200.0, 2000.0, 10000.0):
            assert _score_valor(1000.0, saldo) <= 0.45


class TestIntegracaoAgrupado:
    """pontuar_documentos: doc agrupado com nome batendo recebe LABEL (nao None)."""

    def test_doc_agrupado_recebe_label(self):
        linha = types.SimpleNamespace(
            valor=5000.0, data=date(2026, 3, 10),
            descricao='Ecomove Brasil Ltda - Pix recebido: "Cp :31872495-ECOMOVE"',
            memo='', razao_social=None,
        )
        doc = {
            'tipo_documento': 'fatura_cliente', 'id': 1, 'saldo': 1000.0,
            'nome': 'ECOMOVE BRASIL LTDA', 'cnpj_cliente': '57339413000112',
            'vencimento': '12/03/2026', 'data': '05/03/2026',
        }
        out = pontuar_documentos(linha, [doc])
        # valor agrupado (0.50) + data proxima + nome forte -> nao pode ser None
        assert out[0]['score_label'] is not None
        assert out[0]['score'] >= 0.30


class TestSelecaoMultiLinhaSoma:
    """Caso ESPORTE BIKE: 2 linhas (1000+750) somadas casam a fatura de 1750.

    O backend (api_documentos_elegiveis) monta uma linha AGREGADA quando >1
    linha e selecionada; aqui simulamos essa linha somada e provamos que a
    fatura exata vai para o TOPO com label ALTO (antes a selecao multipla
    DESLIGAVA o scoring e a fatura caia no meio da lista, por data)."""

    def test_soma_linhas_prioriza_fatura_exata_no_topo(self):
        linha_agregada = types.SimpleNamespace(
            valor=1750.0,  # 1000 + 750
            data=date(2026, 6, 15),
            descricao='Esporte Bike Ltda - Pix recebido: "Cp :08561701-ESPORTE BIKE LTDA"',
            memo='', razao_social=None,
        )
        docs = [
            {'tipo_documento': 'fatura_cliente', 'id': 1, 'saldo': 400.0,
             'numero': '286-1', 'nome': 'RAPHAEL MARCHETTO AUTOMOVEIS LTDA',
             'cnpj_cliente': '38450398000130', 'vencimento': '17/06/2026', 'data': '17/06/2026'},
            {'tipo_documento': 'fatura_cliente', 'id': 2, 'saldo': 3500.0,
             'numero': '288-7', 'nome': 'R BENATTI COMERCIO DE AUTOPROPELIDOS LTD',
             'cnpj_cliente': '23148685000113', 'vencimento': '17/06/2026', 'data': '17/06/2026'},
            {'tipo_documento': 'fatura_cliente', 'id': 3, 'saldo': 1500.0,
             'numero': '289-5', 'nome': 'JAIR SCHEIN',
             'cnpj_cliente': '31688852000147', 'vencimento': '17/06/2026', 'data': '17/06/2026'},
            {'tipo_documento': 'fatura_cliente', 'id': 4, 'saldo': 1750.0,
             'numero': '290-9', 'nome': 'ESPORTE BIKE LTDA',
             'cnpj_cliente': '01823474000104', 'vencimento': '17/06/2026', 'data': '17/06/2026'},
        ]
        out = pontuar_documentos(linha_agregada, docs)
        assert out[0]['id'] == 4              # ESPORTE BIKE no topo
        assert out[0]['score_label'] == 'ALTO'  # valor exato (1750) + nome forte
