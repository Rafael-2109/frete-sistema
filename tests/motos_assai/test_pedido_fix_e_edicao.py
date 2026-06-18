"""Testes do fix do parser VOE (IMP-2026-06-18-001) + edição manual (-003/-004).

Cobre:
- _variantes_numero_loja / _resolver_loja: match tolerante a zero-padding
  (causa-raiz — PDF traz "LJ14"→"14", cadastro grava "014").
- importar_pdf_voe: confiança HONESTA (lojas_gravadas/lojas_extraidas) +
  import_resumo com lista de pulados (silent data loss agora visível).
- adicionar/editar/remover item manual em pedido ABERTO.

Dados de teste são criados e limpos pela fixture `cenario` (prefixos ZZTEST/
LJTEST), sem depender de fixture binária de PDF.
"""
from decimal import Decimal
from unittest.mock import patch

import pytest

from app import db
from app.motos_assai.models import (
    AssaiLoja, AssaiModelo,
    AssaiPedidoVenda, AssaiPedidoVendaItem, AssaiPedidoVendaLoja,
    PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_FATURADO,
)
from app.motos_assai.services import (
    importar_pdf_voe,
    adicionar_item_manual, editar_item_manual, remover_item_manual,
    PedidoVoeEdicaoError,
)
from app.motos_assai.services.pedido_service import (
    _variantes_numero_loja, _resolver_loja,
)


def _limpar():
    for p in AssaiPedidoVenda.query.filter(AssaiPedidoVenda.numero.like('ZZTEST%')).all():
        db.session.delete(p)
    db.session.commit()
    for m in AssaiModelo.query.filter(AssaiModelo.codigo.like('ZZTEST%')).all():
        db.session.delete(m)
    for l in AssaiLoja.query.filter(AssaiLoja.nome.like('LJTEST%')).all():
        db.session.delete(l)
    db.session.commit()


def _numeros_livres():
    """Escolhe um número zero-padded (0XX) livre + um número 'plain' (≥900) livre."""
    existentes = {n for (n,) in db.session.query(AssaiLoja.numero).all()}
    zero_padded = stripped = plain = None
    for i in range(1, 100):
        cand, strip = f'{i:03d}', str(i)
        if cand not in existentes and strip not in existentes:
            zero_padded, stripped = cand, strip
            break
    for i in range(900, 1000):
        if str(i) not in existentes:
            plain = str(i)
            break
    assert zero_padded and plain, 'sem números livres para teste'
    return zero_padded, stripped, plain


@pytest.fixture
def cenario(app):
    with app.app_context():
        _limpar()
        zero_padded, stripped, plain = _numeros_livres()
        loja_zero = AssaiLoja(numero=zero_padded, nome='LJTEST ZERO',
                              razao_social='RS TESTE ZERO', cnpj='00.000.000/0001-00')
        loja_plain = AssaiLoja(numero=plain, nome='LJTEST PLAIN',
                               razao_social='RS TESTE PLAIN', cnpj='00.000.000/0002-00')
        modelo = AssaiModelo(codigo='ZZTEST_MOD', nome='Modelo Teste',
                             codigo_qpa='9999999', descricao_qpa='MODELO TESTE')
        db.session.add_all([loja_zero, loja_plain, modelo])
        db.session.commit()
        ids = {
            'loja_zero_id': loja_zero.id, 'loja_zero_num': zero_padded, 'stripped': stripped,
            'loja_plain_id': loja_plain.id, 'loja_plain_num': plain,
            'modelo_id': modelo.id,
        }
        yield ids
        _limpar()


# ----------------------------------------------------------------------
# Causa-raiz: match tolerante a zero-padding
# ----------------------------------------------------------------------

def test_variantes_numero_loja_pura():
    assert '014' in _variantes_numero_loja('14')
    assert '14' in _variantes_numero_loja('14')
    assert '61' in _variantes_numero_loja('061')
    assert '174' in _variantes_numero_loja('174')


def test_resolver_loja_tolera_zero_padding(app, cenario):
    with app.app_context():
        # PDF extrai "99" (sem zero); cadastro tem "099" → match exato falharia.
        loja = _resolver_loja(cenario['stripped'])
        assert loja is not None, 'fallback de zero-padding deveria resolver a loja'
        assert loja.id == cenario['loja_zero_id']
        assert loja.numero == cenario['loja_zero_num']


def test_resolver_loja_match_exato_e_inexistente(app, cenario):
    with app.app_context():
        assert _resolver_loja(cenario['loja_plain_num']).id == cenario['loja_plain_id']
        assert _resolver_loja(cenario['loja_zero_num']).id == cenario['loja_zero_id']
        assert _resolver_loja('99998') is None


# ----------------------------------------------------------------------
# Confiança honesta + import_resumo (o que o parser cortava em silêncio)
# ----------------------------------------------------------------------

def _item(numero_loja, codigo_qpa='9999999', qtd=10, vu='7100.00', vt='71000.00'):
    return {
        'numero_pedido': 'ZZTEST-IMP-001', 'data_emissao': '01/01/2026',
        'previsao_entrega': '02/01/2026', 'fornecedor_cnpj': '53.780.554/0001-15',
        'numero_loja': numero_loja, 'codigo_qpa': codigo_qpa,
        'descricao': 'MODELO TESTE', 'qtd': qtd,
        'valor_unitario': Decimal(vu), 'valor_total': Decimal(vt),
    }


def test_importar_confianca_honesta_e_pulados(app, cenario, admin_user):
    """Loja zero-padded é resolvida; loja inexistente é pulada → confiança < 1.0
    e import_resumo lista o pulado (antes gravava 1.00 escondendo a perda)."""
    items = [
        _item(cenario['stripped']),   # "99" → resolve para "099" (tolerante)
        _item('99997'),               # loja inexistente → pulada
    ]
    with app.app_context():
        with patch('app.motos_assai.services.pedido_service.QpaPedidoExtractor') as MockExt, \
             patch('app.motos_assai.services.pedido_service._calcular_confianca', return_value=1.0), \
             patch('app.motos_assai.services.pedido_service.FileStorage') as mock_fs:
            MockExt.return_value.extract.return_value = items
            mock_fs.return_value.save_file.return_value = 'motos_assai/pedidos/zz.pdf'
            pedido = importar_pdf_voe(b'%PDF-fake', 'zz.pdf', admin_user.id)

        # 2 lojas extraídas, 1 gravada → confiança 0.50 (NÃO 1.00)
        assert float(pedido.parsing_confianca) == 0.50
        resumo = pedido.import_resumo
        assert resumo['lojas_extraidas'] == 2
        assert resumo['lojas_gravadas'] == 1
        assert len(resumo['pulados']) == 1
        assert resumo['pulados'][0]['numero_loja'] == '99997'

        # A loja zero-padded foi de fato persistida (match tolerante funcionou)
        itens = AssaiPedidoVendaItem.query.filter_by(pedido_id=pedido.id).all()
        assert len(itens) == 1
        assert itens[0].loja_id == cenario['loja_zero_id']


def test_importar_tudo_gravado_confianca_total(app, cenario, admin_user):
    items = [_item(cenario['stripped']), _item(cenario['loja_plain_num'])]
    with app.app_context():
        with patch('app.motos_assai.services.pedido_service.QpaPedidoExtractor') as MockExt, \
             patch('app.motos_assai.services.pedido_service._calcular_confianca', return_value=1.0), \
             patch('app.motos_assai.services.pedido_service.FileStorage') as mock_fs:
            MockExt.return_value.extract.return_value = items
            mock_fs.return_value.save_file.return_value = 'motos_assai/pedidos/zz.pdf'
            pedido = importar_pdf_voe(b'%PDF-fake', 'zz.pdf', admin_user.id)

        assert float(pedido.parsing_confianca) == 1.0
        assert pedido.import_resumo['pulados'] == []


# ----------------------------------------------------------------------
# Edição manual (IMP-2026-06-18-003/-004)
# ----------------------------------------------------------------------

def _novo_pedido_aberto():
    p = AssaiPedidoVenda(numero='ZZTEST-EDIT-001', status=PEDIDO_STATUS_ABERTO,
                         parser_usado='MANUAL', parsing_confianca=Decimal('1.00'))
    db.session.add(p)
    db.session.commit()
    return p


def test_adicionar_editar_remover_item(app, cenario):
    with app.app_context():
        pedido = _novo_pedido_aberto()

        item = adicionar_item_manual(
            pedido.id, cenario['loja_plain_id'], cenario['modelo_id'],
            qtd=5, valor_unitario='100.00', operador_id=1,
        )
        assert item.qtd_pedida == 5
        assert item.valor_total == Decimal('500.00')
        # cabeçalho criado on-demand
        assert AssaiPedidoVendaLoja.query.filter_by(
            pedido_id=pedido.id, loja_id=cenario['loja_plain_id']).count() == 1

        # adicionar de novo (mesma loja×modelo) SOMA
        adicionar_item_manual(pedido.id, cenario['loja_plain_id'], cenario['modelo_id'],
                              qtd=3, valor_unitario='100.00', operador_id=1)
        item = AssaiPedidoVendaItem.query.get(item.id)
        assert item.qtd_pedida == 8

        # editar substitui (não soma)
        editar_item_manual(item.id, qtd=10, valor_unitario='120.00', operador_id=1)
        item = AssaiPedidoVendaItem.query.get(item.id)
        assert item.qtd_pedida == 10
        assert item.valor_total == Decimal('1200.00')

        # marca auditoria
        pedido = AssaiPedidoVenda.query.get(pedido.id)
        assert pedido.import_resumo.get('editado_manual') is True

        # remover → item e cabeçalho órfão somem
        remover_item_manual(item.id, operador_id=1)
        assert AssaiPedidoVendaItem.query.get(item.id) is None
        assert AssaiPedidoVendaLoja.query.filter_by(
            pedido_id=pedido.id, loja_id=cenario['loja_plain_id']).count() == 0


def test_edicao_bloqueada_se_nao_aberto(app, cenario):
    with app.app_context():
        pedido = _novo_pedido_aberto()
        pedido.status = PEDIDO_STATUS_FATURADO
        db.session.commit()
        with pytest.raises(PedidoVoeEdicaoError):
            adicionar_item_manual(pedido.id, cenario['loja_plain_id'], cenario['modelo_id'],
                                  qtd=1, valor_unitario='10.00', operador_id=1)


def test_validacao_qtd_valor(app, cenario):
    with app.app_context():
        pedido = _novo_pedido_aberto()
        with pytest.raises(PedidoVoeEdicaoError):
            adicionar_item_manual(pedido.id, cenario['loja_plain_id'], cenario['modelo_id'],
                                  qtd=0, valor_unitario='10.00', operador_id=1)
        with pytest.raises(PedidoVoeEdicaoError):
            adicionar_item_manual(pedido.id, cenario['loja_plain_id'], cenario['modelo_id'],
                                  qtd=1, valor_unitario='0', operador_id=1)


# ----------------------------------------------------------------------
# Render: a tela de detalhe com a seção de edição + alerta de pulados
# ----------------------------------------------------------------------

def test_detalhe_renderiza_edicao_e_alerta(app, cenario, login_admin):
    with app.app_context():
        pedido = _novo_pedido_aberto()
        pedido.import_resumo = {
            'lojas_extraidas': 2, 'lojas_gravadas': 1,
            'itens_extraidos': 2, 'itens_gravados': 1,
            'pulados': [{'numero_loja': '61', 'codigo_qpa': '9999999',
                         'descricao': 'MODELO TESTE', 'qtd': 20,
                         'motivo': 'loja 61 não cadastrada'}],
        }
        db.session.commit()
        adicionar_item_manual(pedido.id, cenario['loja_plain_id'], cenario['modelo_id'],
                              qtd=2, valor_unitario='50.00', operador_id=1)
        pid = pedido.id

    resp = login_admin.get(f'/motos-assai/pedidos/{pid}')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'Edição manual do pedido' in html            # seção de edição (ABERTO)
    assert 'Nem tudo do PDF foi importado' in html      # alerta de pulados
    assert 'Adicionar item' in html                     # form de adição
