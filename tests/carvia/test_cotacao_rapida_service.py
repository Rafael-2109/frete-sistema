"""Cotacao Rapida CarVia — agrupamento modelo->categoria, re-expansao por modelo,
avisos (modelo sem categoria / tabela sem preco) e historico por tabela.

Usa UF de destino fake 'ZZ' para isolar dos dados reais do banco local.
"""

from decimal import Decimal


def _seed(db):
    from app.carvia.models import (
        CarviaCategoriaMoto, CarviaModeloMoto, CarviaTabelaFrete,
        CarviaPrecoCategoriaMoto,
    )

    leve = CarviaCategoriaMoto(nome='CR_Leve', ordem=1, criado_por='test')
    pesada = CarviaCategoriaMoto(nome='CR_Pesada', ordem=2, criado_por='test')
    db.session.add_all([leve, pesada])
    db.session.flush()

    m1 = CarviaModeloMoto(nome='CR_M1', comprimento=100, largura=50, altura=110,
                          categoria_moto_id=leve.id, criado_por='test')
    m2 = CarviaModeloMoto(nome='CR_M2', comprimento=100, largura=50, altura=110,
                          categoria_moto_id=leve.id, criado_por='test')
    m3 = CarviaModeloMoto(nome='CR_M3', comprimento=120, largura=60, altura=120,
                          categoria_moto_id=pesada.id, criado_por='test')
    m4 = CarviaModeloMoto(nome='CR_M4_SemCat', comprimento=100, largura=50, altura=110,
                          categoria_moto_id=None, criado_por='test')
    db.session.add_all([m1, m2, m3, m4])
    db.session.flush()

    t_dir = CarviaTabelaFrete(uf_origem='SP', uf_destino='ZZ', nome_tabela='CR_TAB',
                              tipo_carga='DIRETA', modalidade='RODO', criado_por='test')
    t_fra = CarviaTabelaFrete(uf_origem='SP', uf_destino='ZZ', nome_tabela='CR_TAB',
                              tipo_carga='FRACIONADA', modalidade='RODO', criado_por='test')
    db.session.add_all([t_dir, t_fra])
    db.session.flush()

    # Precos apenas na DIRETA (FRACIONADA fica sem preco -> aviso).
    db.session.add_all([
        CarviaPrecoCategoriaMoto(tabela_frete_id=t_dir.id, categoria_moto_id=leve.id,
                                 valor_unitario=Decimal('100.00'), criado_por='test'),
        CarviaPrecoCategoriaMoto(tabela_frete_id=t_dir.id, categoria_moto_id=pesada.id,
                                 valor_unitario=Decimal('200.00'), criado_por='test'),
    ])
    db.session.flush()

    return dict(leve=leve, pesada=pesada, m1=m1, m2=m2, m3=m3, m4=m4,
                t_dir=t_dir, t_fra=t_fra)


def test_cotar_agrupa_por_categoria_e_reexpande_por_modelo(db):
    s = _seed(db)
    from app.carvia.services.pricing.cotacao_rapida_service import CotacaoRapidaService

    res = CotacaoRapidaService().cotar(
        itens=[
            {'modelo_id': s['m1'].id, 'quantidade': 2},
            {'modelo_id': s['m2'].id, 'quantidade': 1},
            {'modelo_id': s['m3'].id, 'quantidade': 1},
            {'modelo_id': s['m4'].id, 'quantidade': 1},
        ],
        uf_destino='ZZ',
    )

    assert res['ok'] is True
    # So a DIRETA tem preco por categoria -> 1 opcao
    assert len(res['opcoes']) == 1
    op = res['opcoes'][0]
    assert op['tipo_carga'] == 'DIRETA'
    # 100*2 (M1) + 100*1 (M2) + 200*1 (M3) = 500
    assert op['valor_total'] == 500.0

    nomes = {m['modelo_nome']: m for m in op['modelos']}
    assert nomes['CR_M1']['valor_unitario'] == 100.0
    assert nomes['CR_M1']['valor_total'] == 200.0
    assert nomes['CR_M2']['valor_total'] == 100.0
    assert nomes['CR_M3']['valor_total'] == 200.0
    # modelo sem categoria aparece, mas sem preco
    assert nomes['CR_M4_SemCat']['sem_preco'] is True

    # soma das linhas com preco bate com o total da opcao
    soma = sum(m['valor_total'] for m in op['modelos'] if not m['sem_preco'])
    assert round(soma, 2) == op['valor_total']

    # Avisos: modelo sem categoria + tabela FRACIONADA sem preco
    assert 'CR_M4_SemCat' in res['modelos_sem_categoria']
    assert any('FRACIONADA' in a for a in res['avisos'])


def test_cotar_sem_modelo_valido_retorna_vazio(db):
    _seed(db)
    from app.carvia.services.pricing.cotacao_rapida_service import CotacaoRapidaService
    res = CotacaoRapidaService().cotar(itens=[{'modelo_id': 0, 'quantidade': 5}], uf_destino='ZZ')
    assert res['ok'] is False
    assert res['opcoes'] == []


def test_historico_por_tabela(db):
    s = _seed(db)
    from app.carvia.models import (
        CarviaCliente, CarviaClienteEndereco, CarviaCotacao, CarviaCotacaoMoto,
    )

    cli = CarviaCliente(nome_comercial='Cliente CR', criado_por='test')
    db.session.add(cli)
    db.session.flush()

    e_orig = CarviaClienteEndereco(cliente_id=None, tipo='ORIGEM', criado_por='test')
    e_dest = CarviaClienteEndereco(cliente_id=cli.id, tipo='DESTINO', razao_social='Dest CR',
                                   fisico_cidade='Manaus', fisico_uf='ZZ', criado_por='test')
    db.session.add_all([e_orig, e_dest])
    db.session.flush()

    cot = CarviaCotacao(
        numero_cotacao='COT-CRTEST', cliente_id=cli.id,
        endereco_origem_id=e_orig.id, endereco_destino_id=e_dest.id,
        tipo_material='MOTO', tabela_carvia_id=s['t_dir'].id,
        valor_final_aprovado=Decimal('600.00'), status='APROVADO', criado_por='test',
    )
    db.session.add(cot)
    db.session.flush()
    db.session.add(CarviaCotacaoMoto(cotacao_id=cot.id, modelo_moto_id=s['m1'].id, quantidade=3))
    db.session.flush()

    from app.carvia.services.pricing.cotacao_rapida_service import CotacaoRapidaService
    hist = CotacaoRapidaService().historico_por_tabela('CR_TAB', 'ZZ')

    assert len(hist) == 1
    h = hist[0]
    assert h['qtd_motos'] == 3
    assert h['valor_total'] == 600.0
    assert h['valor_por_moto'] == 200.0
    assert h['destinatario']['nome'] == 'Dest CR'
    assert h['destinatario']['cidade'] == 'Manaus'
