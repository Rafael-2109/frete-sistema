"""Testes dos refinos de conciliacao (2026-04-19).

Refinos baseados em analise de 178 linhas OFX reais:
  1. Filtro de tokens numericos longos (>= 5 digitos) — IDs transacionais
  2. Extracao de nome do pagador antes de " - "
  3. Boost adaptativo por ocorrencias do historico R17
"""

from __future__ import annotations


class TestNormalizarFiltraIdsTransacionais:
    def test_token_numerico_5_digitos_descartado(self):
        from app.carvia.services.financeiro.carvia_sugestao_service import (
            _normalizar,
        )
        tokens = _normalizar('cliente abc 474055892 fatura')
        assert '474055892' not in tokens
        assert 'cliente' in tokens
        assert 'abc' in tokens
        assert 'fatura' in tokens

    def test_token_numerico_curto_preservado(self):
        from app.carvia.services.financeiro.carvia_sugestao_service import (
            _normalizar,
        )
        # "2026" (4 digitos) ainda vira token — pode ser numero de fatura curto
        tokens = _normalizar('fatura 2026 cliente')
        assert '2026' in tokens

    def test_token_alfanumerico_preservado(self):
        from app.carvia.services.financeiro.carvia_sugestao_service import (
            _normalizar,
        )
        tokens = _normalizar('nf12345 cliente')
        assert 'nf12345' in tokens  # alfanumerico nao eh ID puro


class TestExtrairNomePagador:
    def test_padrao_pix_recebido(self):
        from app.carvia.services.financeiro.carvia_sugestao_service import (
            extrair_nome_pagador,
        )
        r = extrair_nome_pagador(
            'D.a. De Mattos & Cia Ltda - Pix recebido: "Cp :08561701"'
        )
        assert r == 'D.a. De Mattos & Cia Ltda'

    def test_padrao_pagamento_efetuado(self):
        from app.carvia.services.financeiro.carvia_sugestao_service import (
            extrair_nome_pagador,
        )
        r = extrair_nome_pagador(
            'CAZAN TRANSPORTES LTDA - Pagamento efetuado: "CAZAN"'
        )
        assert r == 'CAZAN TRANSPORTES LTDA'

    def test_sem_separador_retorna_completo(self):
        from app.carvia.services.financeiro.carvia_sugestao_service import (
            extrair_nome_pagador,
        )
        r = extrair_nome_pagador('TRANSFERENCIA XYZ')
        assert r == 'TRANSFERENCIA XYZ'

    def test_vazio_retorna_vazio(self):
        from app.carvia.services.financeiro.carvia_sugestao_service import (
            extrair_nome_pagador,
        )
        assert extrair_nome_pagador('') == ''
        assert extrair_nome_pagador(None) == ''


class TestBoostAdaptativo:
    def _linha(self, valor, descricao):
        """Cria mock-like de CarviaExtratoLinha."""
        from datetime import date
        class _L:
            def __init__(self):
                self.valor = valor
                self.razao_social = None
                self.descricao = descricao
                self.memo = None
                self.data = date(2026, 4, 10)
        return _L()

    def test_1_ocorrencia_boost_115(self):
        from app.carvia.services.financeiro.carvia_sugestao_service import (
            pontuar_documentos,
        )
        linha = self._linha(1000.0, 'CLIENTE X - Pix recebido')
        docs = [{
            'tipo_documento': 'fatura_cliente', 'id': 1,
            'saldo': 1000.0, 'nome': 'CLIENTE Y',
            'vencimento': '10/04/2026', 'data': '01/04/2026',
            'cnpj_cliente': '11222333000144',
        }]
        r = pontuar_documentos(
            linha, docs,
            cnpjs_historico={'11222333000144': 1},
        )
        assert r[0]['score_historico'] is True
        assert r[0]['score_historico_fator'] == 1.15
        assert r[0]['score_historico_ocorrencias'] == 1

    def test_3_ocorrencias_boost_140_cap(self):
        from app.carvia.services.financeiro.carvia_sugestao_service import (
            pontuar_documentos,
        )
        linha = self._linha(1000.0, 'CLIENTE X - Pix recebido')
        docs = [{
            'tipo_documento': 'fatura_cliente', 'id': 1,
            'saldo': 1000.0, 'nome': 'CLIENTE Y',
            'vencimento': '10/04/2026', 'data': '01/04/2026',
            'cnpj_cliente': '11222333000144',
        }]
        r = pontuar_documentos(
            linha, docs,
            cnpjs_historico={'11222333000144': 10},  # muitas ocorrencias
        )
        # Cap: min(0.4, 10*0.15=1.5) = 0.4 -> fator = 1.4
        assert r[0]['score_historico_fator'] == 1.4

    def test_sem_historico_fator_ausente(self):
        from app.carvia.services.financeiro.carvia_sugestao_service import (
            pontuar_documentos,
        )
        linha = self._linha(1000.0, 'CLIENTE X - Pix recebido')
        docs = [{
            'tipo_documento': 'fatura_cliente', 'id': 1,
            'saldo': 1000.0, 'nome': 'CLIENTE X',
            'vencimento': '10/04/2026', 'data': '01/04/2026',
            'cnpj_cliente': '11222333000144',
        }]
        r = pontuar_documentos(linha, docs, cnpjs_historico={})
        assert r[0]['score_historico'] is False
        assert 'score_historico_fator' not in r[0]


class TestScoringUsaNomePagador:
    def test_descricao_com_prefixo_pagador_usa_nome(self):
        """Score de nome deve subir quando extraimos corretamente o nome
        do pagador do prefixo (vs usar descricao completa cheia de ruido)."""
        from datetime import date
        from app.carvia.services.financeiro.carvia_sugestao_service import (
            pontuar_documentos,
        )

        class _L:
            valor = 1000.0
            razao_social = None
            descricao = 'CAZAN TRANSPORTES LTDA - Pagamento efetuado: "CAZAN 474055892"'
            memo = None
            data = date(2026, 4, 10)

        docs = [{
            'tipo_documento': 'fatura_transportadora', 'id': 1,
            'saldo': 1000.0, 'nome': 'CAZAN TRANSPORTES LTDA',
            'vencimento': '10/04/2026', 'data': '01/04/2026',
        }]
        r = pontuar_documentos(_L(), docs)
        # Score de nome deve ser alto pois "cazan transportes" bate
        assert r[0]['score_detalhes']['nome'] >= 0.5
        # Score total razoavel (valor 100% + data OK + nome OK)
        assert r[0]['score'] >= 0.7


class TestE10ManualComHistorico:
    def test_sugestao_sem_linha_extrato_funciona(self, db):
        """E10 continua funcionando sem linha_extrato_id (backward compat)."""
        from app.carvia.services.financeiro.carvia_conciliacao_service import (
            CarviaConciliacaoService,
        )
        r = CarviaConciliacaoService.sugerir_distribuicao_fifo(
            cnpj_cliente='11222333000144', valor_disponivel=100.0,
        )
        assert r['sucesso'] is True
        assert r['metodo'] == 'SUGESTAO_MANUAL'
        assert r['historico_match'] is None

    def test_sugestao_com_linha_inexistente_retorna_none(self, db):
        """Linha_extrato_id invalido nao quebra — historico_match=None."""
        from app.carvia.services.financeiro.carvia_conciliacao_service import (
            CarviaConciliacaoService,
        )
        r = CarviaConciliacaoService.sugerir_distribuicao_fifo(
            cnpj_cliente='11222333000144', valor_disponivel=100.0,
            linha_extrato_id=999999,
        )
        assert r['sucesso'] is True
        assert r['metodo'] == 'SUGESTAO_MANUAL'
        assert r['historico_match'] is None
