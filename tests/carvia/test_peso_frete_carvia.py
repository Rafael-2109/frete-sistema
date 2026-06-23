"""
Testes do calculo de peso do frete CarVia.

Regra R3: o frete usa max(peso_bruto, peso_cubado). Quando o EmbarqueItem
nasce sem peso_cubado (varios fluxos de criacao nao propagam a cubagem),
CarviaFreteService resolve o cubado da FONTE DE VERDADE (CarviaCotacaoMoto),
em vez de cair silenciosamente no peso bruto.

Bug origem: frete da NF 37819 (embarque #5336) gerado sobre 984 kg (bruto)
quando o cubado real eram 2.119,38 kg (10x JET + 2x DOT).

Ref: CarviaFreteService._peso_frete_item / _peso_cubado_resolvido
"""

from unittest.mock import MagicMock, patch

from app.carvia.services.documentos.carvia_frete_service import CarviaFreteService

CALC_PATH = (
    'app.carvia.services.documentos.embarque_carvia_service.'
    'EmbarqueCarViaService.calcular_cubado_por_modelos'
)

MRS_PATH = (
    'app.carvia.services.pricing.moto_recognition_service.'
    'MotoRecognitionService'
)


def _fake_item(peso=None, peso_cubado=None, carvia_cotacao_id=None,
               nota_fiscal=None, separacao_lote_id='CARVIA-NF-1'):
    """Mock de EmbarqueItem (sem DB)."""
    item = MagicMock()
    item.peso = peso
    item.peso_cubado = peso_cubado
    item.carvia_cotacao_id = carvia_cotacao_id
    item.nota_fiscal = nota_fiscal
    item.separacao_lote_id = separacao_lote_id
    return item


class TestPesoFreteSnapshot:
    """Snapshot do item presente: nao toca a fonte de verdade."""

    def test_cubado_preenchido_usa_cubado(self):
        item = _fake_item(peso=984, peso_cubado=2119.38)
        assert CarviaFreteService._peso_frete_item(item) == 2119.38

    def test_bruto_maior_que_cubado_usa_bruto(self):
        # Regra R3: max() — carga densa onde bruto > cubado
        item = _fake_item(peso=500, peso_cubado=100)
        assert CarviaFreteService._peso_frete_item(item) == 500

    def test_sem_cubado_sem_cotacao_usa_bruto(self):
        # Carga geral (sem motos / sem cotacao): cubado nao resolve -> bruto
        item = _fake_item(peso=984, peso_cubado=None, carvia_cotacao_id=None)
        assert CarviaFreteService._peso_frete_item(item) == 984


class TestPesoFreteResolveViaNf:
    """Snapshot vazio + item real (NF): resolve cubado pela FONTE CANONICA
    — os ITENS da NF (CarviaNfItem.modelo_moto_id), independente da cotacao.

    Antes (bug): resolvia via calcular_cubado_por_modelos, que casa o texto
    do chassi contra a CarviaCotacaoMoto DA COTACAO. Quando a cotacao nao
    cobria o modelo, retornava 0 -> o frete gravava o peso bruto (ex.: NF
    38312 JET, 675,92 bruto vs 867,54 cubado correto), divergindo da
    tela/export que ja usam a fonte canonica (calcular_peso_cubado_nf).
    """

    @patch('app.carvia.models.CarviaNf')
    @patch(MRS_PATH)
    def test_resolve_cubado_pelos_itens_independe_da_cotacao(
            self, mock_mrs_cls, mock_nf_cls):
        # NF 38312 (JET): modelo AUSENTE da cotacao, mas com CarviaNfItem
        # tendo modelo_moto_id -> cubado vem dos ITENS, nao da cotacao.
        mock_mrs_cls.return_value.calcular_peso_cubado_nf.return_value = {
            'peso_cubado_total': 867.54,
        }
        nf = MagicMock()
        nf.id = 326
        (mock_nf_cls.query.filter_by.return_value
            .order_by.return_value.first.return_value) = nf

        item = _fake_item(peso=675.92, peso_cubado=None, carvia_cotacao_id=84,
                          nota_fiscal='38312', separacao_lote_id='CARVIA-PED-93')

        # max(675.92, 867.54) = 867.54 (cubado canonico via itens da NF)
        assert CarviaFreteService._peso_frete_item(item) == 867.54
        mock_mrs_cls.return_value.calcular_peso_cubado_nf.assert_called_once_with(326)

    @patch('app.carvia.models.CarviaNf')
    @patch(MRS_PATH)
    def test_nf_sem_itens_com_modelo_usa_bruto(self, mock_mrs_cls, mock_nf_cls):
        # calcular_peso_cubado_nf devolve None (nenhum item com modelo) ->
        # nao da pra resolver -> usa bruto (nunca a cotacao inteira, para nao
        # superestimar em multi-NF).
        mock_mrs_cls.return_value.calcular_peso_cubado_nf.return_value = None
        nf = MagicMock()
        nf.id = 999
        (mock_nf_cls.query.filter_by.return_value
            .order_by.return_value.first.return_value) = nf

        item = _fake_item(peso=984, peso_cubado=None, carvia_cotacao_id=84,
                          nota_fiscal='37819')

        assert CarviaFreteService._peso_frete_item(item) == 984


class TestPesoFreteResolveViaCotacao:
    """Snapshot vazio + provisorio (sem NF): resolve via soma da cotacao."""

    @patch('app.carvia.services.documentos.carvia_frete_service.db')
    @patch('app.carvia.models.CarviaCotacaoMoto')
    def test_resolve_cubado_da_cotacao(self, mock_ccm, mock_db):
        mock_ccm.peso_cubado_total = 0  # literal coercivel por func.sum()
        (mock_db.session.query.return_value
            .filter.return_value.scalar.return_value) = 2119.39

        item = _fake_item(peso=0, peso_cubado=None, carvia_cotacao_id=84,
                          nota_fiscal=None, separacao_lote_id='CARVIA-COT-84')

        assert CarviaFreteService._peso_frete_item(item) == 2119.39


class TestPesoFreteItemNaoCarVia:
    """Item nao-CarVia (carga Nacom) — usado no denominador do rateio DIRETA misto."""

    def test_item_nacom_retorna_peso_fisico(self):
        # Embarque DIRETA misto: moto CarVia + carga Nacom no mesmo caminhao.
        # _peso_frete_item de um item Nacom (sem carvia_cotacao_id) retorna o
        # peso fisico — garantindo que o denominador do rateio some a carga
        # Nacom (e nao atribua o frete inteiro a CarVia). Sem cotacao, nao ha
        # cubagem a resolver.
        item = _fake_item(peso=3610.12, peso_cubado=None,
                          carvia_cotacao_id=None,
                          separacao_lote_id='LOTE_20260505_115532_495')
        assert CarviaFreteService._peso_frete_item(item) == 3610.12


class TestPesoTotalDeNfs:
    """Backfill manual (sem EmbarqueItem): peso = sum(max(bruto, cubado)) por
    NF, com o cubado vindo da fonte canonica (itens via
    calcular_peso_cubado_batch). Antes o backfill POST somava SO o peso bruto
    (frete_routes.py), subestimando motos cujo modelo nao estava na cotacao.
    """

    @patch(MRS_PATH)
    def test_usa_max_bruto_cubado_por_nf(self, mock_mrs_cls):
        mock_mrs_cls.return_value.calcular_peso_cubado_batch.return_value = {
            326: 867.54,  # cubado > bruto -> cubado
            330: 50.0,    # cubado < bruto -> bruto
        }
        nf1 = MagicMock(); nf1.id = 326; nf1.peso_bruto = 675.92
        nf2 = MagicMock(); nf2.id = 330; nf2.peso_bruto = 200.0

        total = CarviaFreteService.peso_total_de_nfs([nf1, nf2])
        assert total == 867.54 + 200.0
        mock_mrs_cls.return_value.calcular_peso_cubado_batch.assert_called_once_with(
            [326, 330]
        )

    @patch(MRS_PATH)
    def test_sem_cubado_usa_bruto(self, mock_mrs_cls):
        mock_mrs_cls.return_value.calcular_peso_cubado_batch.return_value = {}
        nf1 = MagicMock(); nf1.id = 1; nf1.peso_bruto = 300.0
        assert CarviaFreteService.peso_total_de_nfs([nf1]) == 300.0
