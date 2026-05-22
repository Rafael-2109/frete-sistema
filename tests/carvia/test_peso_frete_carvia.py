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


def _veiculo(modelo):
    v = MagicMock()
    v.modelo = modelo
    return v


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
    """Snapshot vazio + item real (NF): resolve cubado pelos veiculos da NF."""

    @patch('app.carvia.models.CarviaNf')
    @patch(CALC_PATH)
    def test_resolve_cubado_da_nf_caso_37819(self, mock_calc, mock_nf_cls):
        # 10x JET + 2x DOT = 2.119,39 kg (cenario real do embarque #5336)
        mock_calc.return_value = 2119.39
        nf = MagicMock()
        nf.veiculos.all.return_value = (
            [_veiculo('MOTO ELETRICA JET')] * 10
            + [_veiculo('SCOOTER ELETRICA DOT')] * 2
        )
        (mock_nf_cls.query.filter_by.return_value
            .order_by.return_value.first.return_value) = nf

        item = _fake_item(peso=984, peso_cubado=None, carvia_cotacao_id=84,
                          nota_fiscal='37819', separacao_lote_id='CARVIA-PED-93')

        # max(984, 2119.39) = 2119.39 (cubado da fonte de verdade)
        assert CarviaFreteService._peso_frete_item(item) == 2119.39
        # passou os 12 modelos da NF para a cotacao 84
        cot_id_arg, modelos_arg = mock_calc.call_args[0]
        assert cot_id_arg == 84
        assert len(modelos_arg) == 12

    @patch('app.carvia.models.CarviaNf')
    @patch(CALC_PATH)
    def test_nf_sem_veiculos_nao_superestima_usa_bruto(self, mock_calc, mock_nf_cls):
        # NF sem veiculos com modelo: nao da pra resolver -> usa bruto
        # (nunca a cotacao inteira, para nao superestimar em multi-NF)
        nf = MagicMock()
        nf.veiculos.all.return_value = []
        (mock_nf_cls.query.filter_by.return_value
            .order_by.return_value.first.return_value) = nf

        item = _fake_item(peso=984, peso_cubado=None, carvia_cotacao_id=84,
                          nota_fiscal='37819')

        assert CarviaFreteService._peso_frete_item(item) == 984
        mock_calc.assert_not_called()


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
