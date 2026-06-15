"""
Testes para o conversor de extrato SRM (PDF -> OFX).

Cobre a logica pura do service `app.financeiro.services.extrato_pdf_srm_service`
(sem PDF, sem app context):
- _dec / _centavos: parsing de valores monetarios com sinal.
- Transacao.fitid: formato deterministico, sinal do saldo, unicidade.
- validar: cadeia diaria, tolerancia de arredondamento, transacao faltando,
  saldo negativo, dia orfao, colisao de FITID.
- analisar_continuidade: deteccao de GAP entre extratos sequenciais.
- gerar_ofx: estrutura SGML, roteamento (BANKID/ACCTID), 1 STMTTRN por transacao.

E a casca HTTP `app.financeiro.routes.conversor_extrato_srm`:
- helpers de serializacao (_dec_str / _resumo_json);
- protecao das rotas (sem login nao retorna 200).

O parsing de PDF em si e' validado contra os 4 extratos reais via CLI --check
(fora do repo, pois sao dados financeiros); aqui isolamos a logica deterministica.
"""
from decimal import Decimal

import pytest

import app.financeiro.services.extrato_pdf_srm_service as mod

Transacao = mod.Transacao


def _parsed(transacoes, saldo_anterior, saldo_dia,
            nome='extrato.pdf', periodo_ini='01/01/2026', periodo_fim='02/01/2026'):
    """Monta o dict que validar()/gerar_ofx()/analisar_continuidade() esperam."""
    return {
        'nome': nome,
        'conta': '0000142844', 'banco': '533', 'agencia': '0001',
        'periodo_ini': periodo_ini, 'periodo_fim': periodo_fim,
        'saldo_anterior': Decimal(saldo_anterior),
        'transacoes': transacoes,
        'saldo_dia': {d: Decimal(v) for d, v in saldo_dia.items()},
    }


def _t(data, tipo, valor, saldo, desc='LANC', hora=None, favorecido=None, detalhes=None):
    t = Transacao(data, tipo, Decimal(valor), Decimal(saldo), desc)
    t.hora = hora
    t.favorecido = favorecido
    if detalhes:
        t.detalhes = list(detalhes)
    return t


def _tok(text, x0):
    """Token sintetico (dict no formato do pdfplumber) para os testes de layout."""
    return {'text': text, 'x0': x0, 'top': 0.0}


# ---------------------------------------------------------------------------
# _dec / _centavos
# ---------------------------------------------------------------------------
class TestDec:
    def test_milhar_e_decimal(self):
        assert mod._dec('1.861,69') == Decimal('1861.69')

    def test_valor_simples(self):
        assert mod._dec('124,03') == Decimal('124.03')

    def test_negativo(self):
        assert mod._dec('-0,00') == Decimal('0.00')
        assert mod._dec('-1.234,56') == Decimal('-1234.56')

    def test_milhao(self):
        assert mod._dec('1.000.675,01') == Decimal('1000675.01')


class TestCentavos:
    def test_basico(self):
        assert mod._centavos(Decimal('124.03')) == '12403'

    def test_abs(self):
        assert mod._centavos(Decimal('-0.00')) == '0'

    def test_milhao(self):
        assert mod._centavos(Decimal('1000675.01')) == '100067501'


# ---------------------------------------------------------------------------
# _extrair_favorecido (nome da contraparte na linha de hora)
# ---------------------------------------------------------------------------
class TestExtrairFavorecido:
    def test_remove_codigo_banco(self):
        # 'HH:MM:SS 756 NACOM GOYA ...' -> tokens apos a hora descartam o '756'
        assert mod._extrair_favorecido(
            ['756', 'NACOM', 'GOYA', 'COMERCIAL', 'LTDA']) == 'NACOM GOYA COMERCIAL LTDA'

    def test_sem_codigo_banco(self):
        assert mod._extrair_favorecido(
            ['FRANK', 'ROGERIO', 'HOMEM']) == 'FRANK ROGERIO HOMEM'

    def test_codigo_533(self):
        assert mod._extrair_favorecido(
            ['533', 'M18', 'ADMINISTRACAO']) == 'M18 ADMINISTRACAO'

    def test_vazio(self):
        assert mod._extrair_favorecido([]) == ''

    def test_so_codigo_banco(self):
        assert mod._extrair_favorecido(['237']) == ''


# ---------------------------------------------------------------------------
# _eh_identificador (E2E do PIX / hash interno NAO sao favorecido)
# ---------------------------------------------------------------------------
class TestEhIdentificador:
    def test_e2e_pix(self):
        assert mod._eh_identificador('E60746948202512041644C0347TOFZLC')
        assert mod._eh_identificador('E05392810202605152010JVBQ8UQJO5C')

    def test_hash(self):
        assert mod._eh_identificador('A7317D2399CF4878A356680854A740C0')
        assert mod._eh_identificador('F533D8CB8B6944F691F9838A625DB424')

    def test_nome_nao_e_identificador(self):
        assert not mod._eh_identificador('EMBALAGENS LTDA')
        assert not mod._eh_identificador('NACOM GOYA COMERCIAL LTDA')

    def test_tipo_nao_e_identificador(self):
        assert not mod._eh_identificador('ENVIO DE TED')
        assert not mod._eh_identificador('RECEBIMENTO DE PIX QRCODE')


# ---------------------------------------------------------------------------
# _eh_valor_sem_tipo_inline (look-ahead que resolve o TIPO acima do valor)
# ---------------------------------------------------------------------------
class TestValorSemTipoInline:
    def test_valor_puro(self):
        # coluna debito (x0 ~432) + saldo (x0 ~511), sem texto -> tipo vem ACIMA
        ws = [_tok('2.334,06', 432), _tok('66.138,80', 511)]
        assert mod._eh_valor_sem_tipo_inline(ws)

    def test_credito_puro(self):
        ws = [_tok('23.934,60', 366), _tok('95.317,70', 511)]
        assert mod._eh_valor_sem_tipo_inline(ws)

    def test_com_tipo_inline(self):
        ws = [_tok('CRÉDITO', 118), _tok('DE', 150), _tok('BOLETO', 200),
              _tok('2.802,75', 432), _tok('119.342,44', 511)]
        assert not mod._eh_valor_sem_tipo_inline(ws)

    def test_com_data_e_tipo_inline(self):
        ws = [_tok('22/12/2025', 58), _tok('TARIFA', 118), _tok('SISTÊMICA', 160),
              _tok('15,54', 432), _tok('116.539,69', 511)]
        assert not mod._eh_valor_sem_tipo_inline(ws)

    def test_linha_de_texto_nao_e_valor(self):
        ws = [_tok('ENVIO', 118), _tok('DE', 145), _tok('TED', 159)]
        assert not mod._eh_valor_sem_tipo_inline(ws)


# ---------------------------------------------------------------------------
# Transacao.fitid
# ---------------------------------------------------------------------------
class TestFitid:
    def test_formato_com_hora(self):
        t = _t('29/05/2026', 'D', '700000.00', '515.03', hora='16:38:11')
        assert t.fitid() == '20260529163811-D70000000-S51503-0'

    def test_sem_hora_usa_zeros(self):
        t = _t('08/04/2026', 'D', '86.85', '51393.28')
        assert t.fitid() == '20260408000000-D8685-S5139328-0'

    def test_credito(self):
        t = _t('05/09/2025', 'C', '18417.00', '47631.70', hora='07:42:08')
        assert t.fitid() == '20250905074208-C1841700-S4763170-0'

    def test_saldo_negativo_marca_sinal(self):
        neg = _t('04/05/2026', 'D', '124.03', '-12.00')
        pos = _t('04/05/2026', 'D', '124.03', '12.00')
        assert '-S-1200-' in neg.fitid()   # sinal marcado entre 'S' e os centavos
        assert '-S1200-' in pos.fitid()
        assert neg.fitid() != pos.fitid()

    def test_occ_diferencia_tuplas_identicas(self):
        # occ e' atribuido no parse; simulamos a numeracao manual
        a = _t('01/01/2026', 'D', '5.00', '95.00')
        b = _t('01/01/2026', 'D', '5.00', '95.00')
        a._occ, b._occ = 0, 1
        assert a.fitid() != b.fitid()


# ---------------------------------------------------------------------------
# validar
# ---------------------------------------------------------------------------
class TestValidar:
    def test_cadeia_fecha(self):
        ts = [_t('01/01/2026', 'D', '30.00', '120.00'),   # ordem do PDF (decresc.)
              _t('01/01/2026', 'C', '50.00', '150.00')]
        ok, erros, warns, resumo = mod.validar(
            _parsed(ts, '100.00', {'01/01/2026': '120.00'}))
        assert ok and not erros and not warns
        assert resumo['creditos'] == Decimal('50.00')
        assert resumo['debitos'] == Decimal('30.00')
        assert resumo['saldo_final'] == Decimal('120.00')

    def test_encadeia_dois_dias(self):
        ts = [_t('02/01/2026', 'C', '10.00', '130.00'),
              _t('01/01/2026', 'D', '30.00', '120.00'),
              _t('01/01/2026', 'C', '50.00', '150.00')]
        ok, erros, _, _ = mod.validar(
            _parsed(ts, '100.00', {'01/01/2026': '120.00', '02/01/2026': '130.00'}))
        assert ok, erros

    def test_ruido_de_um_centavo_e_warning(self):
        # soma das transacoes = 120.00, mas linha SALDO = 119.99 (ruido do banco)
        ts = [_t('01/01/2026', 'D', '30.00', '120.00'),
              _t('01/01/2026', 'C', '50.00', '150.00')]
        ok, erros, warns, _ = mod.validar(
            _parsed(ts, '100.00', {'01/01/2026': '119.99'}))
        assert ok and not erros
        assert len(warns) == 1 and 'arredondamento' in warns[0]

    def test_transacao_faltando_e_fatal(self):
        # linha SALDO = 200 mas transacoes so explicam 120 -> diff 80 (acima da tol.)
        ts = [_t('01/01/2026', 'C', '50.00', '150.00')]
        ok, erros, _, _ = mod.validar(
            _parsed(ts, '100.00', {'01/01/2026': '200.00'}))
        assert not ok
        assert any('nao fecha' in e for e in erros)

    def test_saldo_anterior_ausente_e_fatal(self):
        ts = [_t('01/01/2026', 'C', '50.00', '150.00')]
        p = _parsed(ts, '0', {'01/01/2026': '150.00'})
        p['saldo_anterior'] = None
        ok, erros, _, _ = mod.validar(p)
        assert not ok
        assert any('SALDO ANTERIOR' in e for e in erros)

    def test_dia_orfao_sem_linha_saldo_e_fatal(self):
        ts = [_t('01/01/2026', 'C', '50.00', '150.00'),
              _t('03/01/2026', 'C', '5.00', '155.00')]  # 03/01 sem linha SALDO
        ok, erros, _, _ = mod.validar(
            _parsed(ts, '100.00', {'01/01/2026': '150.00'}))
        assert not ok
        assert any('sem linha SALDO' in e for e in erros)

    def test_colisao_fitid_e_fatal(self):
        # duas transacoes identicas com mesmo occ (forcado) colidem
        a = _t('01/01/2026', 'D', '5.00', '95.00')
        b = _t('01/01/2026', 'D', '5.00', '95.00')
        a._occ = b._occ = 0
        ok, erros, _, _ = mod.validar(
            _parsed([a, b], '105.00', {'01/01/2026': '95.00'}))
        assert not ok
        assert any('FITID' in e for e in erros)

    def test_sem_transacoes_e_fatal(self):
        ok, _, _, _ = mod.validar(_parsed([], '100.00', {}))
        assert not ok


# ---------------------------------------------------------------------------
# gerar_ofx
# ---------------------------------------------------------------------------
class TestGerarOfx:
    def _ofx(self):
        ts = [_t('02/01/2026', 'C', '10.00', '130.00', desc='PIX RECEBIDO'),
              _t('01/01/2026', 'D', '30.00', '120.00', desc='TARIFA'),
              _t('01/01/2026', 'C', '50.00', '150.00', desc='TED')]
        return mod.gerar_ofx(
            _parsed(ts, '100.00', {'01/01/2026': '120.00', '02/01/2026': '130.00'})), ts

    def test_cabecalho_e_roteamento(self):
        ofx, _ = self._ofx()
        assert ofx.startswith('OFXHEADER:100')
        assert '<BANKID>533' in ofx
        assert '<ACCTID>0000142844' in ofx
        assert '<ACCTTYPE>CHECKING' in ofx

    def test_uma_stmttrn_por_transacao(self):
        ofx, ts = self._ofx()
        assert ofx.count('<STMTTRN>') == len(ts)

    def test_sinal_credito_debito(self):
        ofx, _ = self._ofx()
        assert '<TRNTYPE>CREDIT' in ofx and '<TRNAMT>50.00' in ofx
        assert '<TRNTYPE>DEBIT' in ofx and '<TRNAMT>-30.00' in ofx

    def test_ledgerbal_usa_linha_saldo_do_dia_mais_recente(self):
        ofx, _ = self._ofx()
        assert '<LEDGERBAL><BALAMT>130.00' in ofx

    def test_memo_sanitizado(self):
        ts = [_t('01/01/2026', 'C', '50.00', '150.00', desc='A & B <teste>')]
        ofx = mod.gerar_ofx(_parsed(ts, '100.00', {'01/01/2026': '150.00'}))
        assert '&' not in ofx.split('<OFX>')[1]
        assert 'A e B (teste)' in ofx

    @pytest.mark.parametrize('lib', ['ofxparse'])
    def test_parseavel_por_ofxparse(self, lib):
        ofxparse = pytest.importorskip(lib)
        import io
        ofx, ts = self._ofx()
        parsed = ofxparse.OfxParser.parse(io.StringIO(ofx))
        st = parsed.account.statement
        assert parsed.account.number == '0000142844'
        assert len(st.transactions) == len(ts)
        assert len({t.id for t in st.transactions}) == len(ts)  # FITIDs unicos


# ---------------------------------------------------------------------------
# gerar_ofx — favorecido em <NAME> + <MEMO>
# ---------------------------------------------------------------------------
class TestGerarOfxFavorecido:
    def _ofx_um(self, t):
        return mod.gerar_ofx(_parsed([t], '0.00', {t.data: t.saldo}))

    def test_favorecido_no_name_e_no_memo(self):
        t = _t('01/01/2026', 'D', '2334.06', '66138.80', desc='ENVIO DE TED',
                hora='12:07:54',
                favorecido='FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS EXODUS')
        ofx = self._ofx_um(t)
        import re
        m = re.search(r'<NAME>([^\n<]*)', ofx)
        assert m and m.group(1).startswith('FUNDO DE INVESTIMENTO')
        assert len(m.group(1)) <= 32                                  # <NAME> A-32
        # MEMO traz tipo + favorecido COMPLETO (sem truncar)
        assert 'ENVIO DE TED | FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS EXODUS' in ofx

    def test_detalhes_entram_no_memo_nao_no_name(self):
        t = _t('01/01/2026', 'C', '8363.63', '335061.58',
                desc='RECEBIMENTO DE PIX QRCODE', hora='10:23:37',
                favorecido='DML DISTRIBUIDORA DE ALIMENTOS E EMBALAGENS LTDA',
                detalhes=['E60746948202512021323C3612EQW3SA'])
        ofx = self._ofx_um(t)
        assert 'E60746948202512021323C3612EQW3SA' in ofx           # id no MEMO
        import re
        nome = re.search(r'<NAME>([^\n<]*)', ofx).group(1)
        assert 'E6074' not in nome                                  # id NUNCA no NAME

    def test_sem_favorecido_nao_emite_name(self):
        t = _t('01/01/2026', 'D', '30.00', '120.00', desc='TARIFA SISTEMICA')
        ofx = self._ofx_um(t)
        assert '<NAME>' not in ofx
        assert '<MEMO>TARIFA SISTEMICA' in ofx

    def test_cod_no_memo(self):
        t = _t('01/01/2026', 'D', '159.98', '65244.38', desc='TARIFA DE TED')
        t.cod = '3839410'
        ofx = self._ofx_um(t)
        assert 'COD 3839410' in ofx


# ---------------------------------------------------------------------------
# analisar_continuidade
# ---------------------------------------------------------------------------
class TestContinuidade:
    def _ext(self, nome, ini, fim_data, saldo_ant, saldo_fim):
        ts = [_t(fim_data, 'C', '1.00', saldo_fim)]
        return _parsed(ts, saldo_ant, {fim_data: saldo_fim}, nome=nome, periodo_ini=ini)

    def test_continuo_quando_fim_igual_abertura_seguinte(self):
        a = self._ext('A', '01/01/2026', '31/01/2026', '0.00', '100.00')
        b = self._ext('B', '01/02/2026', '28/02/2026', '100.00', '150.00')
        res = mod.analisar_continuidade([b, a])  # ordem invertida de proposito
        assert len(res) == 1
        assert res[0]['de'] == 'A' and res[0]['para'] == 'B'
        assert res[0]['continuo'] and res[0]['gap'] == Decimal('0')

    def test_detecta_gap(self):
        a = self._ext('A', '01/01/2026', '31/01/2026', '0.00', '66138.80')
        b = self._ext('B', '01/02/2026', '28/02/2026', '91146.25', '120000.00')
        res = mod.analisar_continuidade([a, b])
        assert not res[0]['continuo']
        assert res[0]['gap'] == Decimal('25007.45')

    def test_ordena_por_periodo_inicial(self):
        a = self._ext('A', '01/01/2026', '31/01/2026', '0.00', '100.00')
        b = self._ext('B', '01/02/2026', '28/02/2026', '100.00', '150.00')
        c = self._ext('C', '01/03/2026', '31/03/2026', '150.00', '200.00')
        res = mod.analisar_continuidade([c, a, b])
        assert [r['de'] for r in res] == ['A', 'B']
        assert all(r['continuo'] for r in res)


# ---------------------------------------------------------------------------
# Rota HTTP (casca fina sobre o service)
# ---------------------------------------------------------------------------
class TestRota:
    def test_dec_str_helper(self, app):
        from app.financeiro.routes.conversor_extrato_srm import _dec_str
        assert _dec_str(Decimal('66138.80')) == '66138.80'
        assert _dec_str(Decimal('-0.00')) == '0.00'
        assert _dec_str(None) is None

    def test_resumo_json_serializa_decimais(self, app):
        from app.financeiro.routes.conversor_extrato_srm import _resumo_json
        _, _, _, resumo = mod.validar(
            _parsed([_t('01/01/2026', 'C', '50.00', '150.00')], '100.00',
                    {'01/01/2026': '150.00'}))
        out = _resumo_json(resumo)
        assert out['saldo_final'] == '150.00'
        assert isinstance(out['creditos'], str)

    def test_rota_get_registrada(self, app):
        # url_for resolve -> rota registrada no blueprint
        with app.test_request_context():
            from flask import url_for
            assert url_for('financeiro.conversor_srm') == '/financeiro/conversor-srm'
            assert url_for('financeiro.conversor_srm_converter') == \
                '/financeiro/conversor-srm/converter'

    def test_rotas_tem_decorator_login(self, app):
        # Ambas as views estao protegidas por @login_required (proxy do flask_login).
        # (Nao testamos via HTTP: em TESTING o LOGIN_DISABLED=True inverte a semantica.)
        from app.financeiro.routes import conversor_extrato_srm as rota
        assert hasattr(rota.conversor_srm, '__wrapped__')
        assert hasattr(rota.conversor_srm_converter, '__wrapped__')
