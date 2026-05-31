"""
Testes do GATE combinado de _processar_movimento (entrada_material_service).

Cobre a decisão "registrar ou pular" + criação de cadastro básico:
  - LEGADO: cadastro com produto_comprado=True -> registra (preserva comportamento)
  - NOVO: produto produtivo/revenda (classificação Odoo) -> registra + cria cadastro
  - resto (uso/consumo, despesas...) -> pula

Instancia o service via object.__new__ para NÃO abrir conexão Odoo (o __init__
chama get_odoo_connection). _processar_movimento não usa self.odoo quando o
picking não tem purchase_id (não processa DFe).
"""
import uuid

from app.odoo.services.entrada_material_service import EntradaMaterialService
from app.estoque.models import MovimentacaoEstoque
from app.producao.models import CadastroPalletizacao


def _svc():
    """Instância sem __init__ (evita conexão Odoo)."""
    return object.__new__(EntradaMaterialService)


def _cache(codigos=None, cadastros=None, classificacao=None):
    return {
        'cnpjs': {},
        'codigos': codigos or {},
        'cadastros': cadastros or {},
        'classificacao': classificacao or {},
        'pedidos': {},
        'movimentos_por_picking': {},
        'dfe_por_pedido': {},
    }


def _picking(pid, sufixo):
    # sem purchase_id -> não entra no fluxo de DFe (não usa self.odoo)
    return {
        'id': pid,
        'name': f'WH/IN/{sufixo}',
        'date_done': '2026-05-28 10:00:00',
        'origin': f'PO{sufixo}',
    }


def _movimento(mid, product_id, qty=10):
    return {'id': mid, 'product_id': [product_id, 'PRODUTO TESTE'], 'quantity': qty}


class TestGateEntradaMaterial:
    def test_produtivo_sem_cadastro_cria_e_registra(self, db):
        u = uuid.uuid4().hex[:8]
        mid, cod = f'TESTMOVE{u}', f'TESTGATE{u}'
        cache = _cache(codigos={111: cod}, classificacao={cod: 'PRODUTIVO'})

        r = _svc()._processar_movimento(_picking(1, u), _movimento(mid, 111),
                                        '11.111.111/0001-11', cache)

        assert r['novo'] is True
        cad = CadastroPalletizacao.query.filter_by(cod_produto=cod).first()
        assert cad is not None
        assert cad.produto_comprado is True and cad.produto_vendido is False
        mov = MovimentacaoEstoque.query.filter_by(odoo_move_id=mid).first()
        assert mov is not None
        assert mov.tipo_movimentacao == 'ENTRADA' and mov.local_movimentacao == 'COMPRA'
        assert mov.cod_produto == cod

    def test_revenda_sem_cadastro_cria_com_vendido(self, db):
        u = uuid.uuid4().hex[:8]
        mid, cod = f'TESTMOVE{u}', f'TESTGATE{u}'
        cache = _cache(codigos={555: cod}, classificacao={cod: 'REVENDA'})

        r = _svc()._processar_movimento(_picking(5, u), _movimento(mid, 555),
                                        '11.111.111/0001-11', cache)

        assert r['novo'] is True
        cad = CadastroPalletizacao.query.filter_by(cod_produto=cod).first()
        assert cad is not None and cad.produto_comprado is True and cad.produto_vendido is True

    def test_uso_consumo_sem_cadastro_pula(self, db):
        u = uuid.uuid4().hex[:8]
        mid, cod = f'TESTMOVE{u}', f'TESTGATE{u}'
        cache = _cache(codigos={222: cod})  # sem classificação (None) e sem cadastro

        r = _svc()._processar_movimento(_picking(2, u), _movimento(mid, 222),
                                        '11.111.111/0001-11', cache)

        assert r['novo'] is False
        assert MovimentacaoEstoque.query.filter_by(odoo_move_id=mid).first() is None
        assert CadastroPalletizacao.query.filter_by(cod_produto=cod).first() is None

    def test_legado_comprado_registra_mesmo_sem_natureza(self, db):
        u = uuid.uuid4().hex[:8]
        mid, cod = f'TESTMOVE{u}', f'TESTGATE{u}'
        cad = CadastroPalletizacao(cod_produto=cod, nome_produto='LEGADO', palletizacao=0,
                                   peso_bruto=0, produto_comprado=True, ativo=True)
        db.session.add(cad)
        db.session.flush()
        cache = _cache(codigos={333: cod}, cadastros={cod: cad})  # classificação vazia (None)

        r = _svc()._processar_movimento(_picking(3, u), _movimento(mid, 333),
                                        '11.111.111/0001-11', cache)

        assert r['novo'] is True
        assert MovimentacaoEstoque.query.filter_by(odoo_move_id=mid).first() is not None

    def test_cadastro_nao_comprado_mas_produtivo_registra_sem_criar_novo(self, db):
        u = uuid.uuid4().hex[:8]
        mid, cod = f'TESTMOVE{u}', f'TESTGATE{u}'
        cad = CadastroPalletizacao(cod_produto=cod, nome_produto='MP EXISTENTE', palletizacao=0,
                                   peso_bruto=0, produto_comprado=False, ativo=True)
        db.session.add(cad)
        db.session.flush()
        cache = _cache(codigos={444: cod}, cadastros={cod: cad}, classificacao={cod: 'PRODUTIVO'})

        r = _svc()._processar_movimento(_picking(4, u), _movimento(mid, 444),
                                        '11.111.111/0001-11', cache)

        assert r['novo'] is True
        assert CadastroPalletizacao.query.filter_by(cod_produto=cod).count() == 1  # reusou
        assert MovimentacaoEstoque.query.filter_by(odoo_move_id=mid).first() is not None
