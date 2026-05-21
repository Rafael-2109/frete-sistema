"""Testa estrutura de MATRIZ_INTERCOMPANY (constantes consolidadas, dados validados em F0)."""
import pytest


def test_matriz_intercompany_tem_4_tipos():
    from app.odoo.constants.operacoes_fiscais import MATRIZ_INTERCOMPANY
    assert set(MATRIZ_INTERCOMPANY.keys()) == {
        'industrializacao', 'perda', 'dev-industrializacao', 'transf-filial'
    }


def test_industrializacao_FB_para_LF():
    from app.odoo.constants.operacoes_fiscais import MATRIZ_INTERCOMPANY
    op = MATRIZ_INTERCOMPANY['industrializacao']
    assert op['l10n_br_tipo_pedido'] == 'industrializacao'
    assert op['move_type'] == 'out_invoice'
    assert op['tipo_produto'] == [1, 2, 3]
    assert op['nf_referencia'] == 94457
    assert op['fiscal_position_id'] == {(1, 5): 25}


def test_perda_LF_para_FB():
    from app.odoo.constants.operacoes_fiscais import MATRIZ_INTERCOMPANY
    op = MATRIZ_INTERCOMPANY['perda']
    assert op['l10n_br_tipo_pedido'] == 'perda'
    assert op['tipo_produto'] == [1, 2, 3]
    assert op['fiscal_position_id'] == {(5, 1): 91}


def test_dev_industrializacao_inclui_4_direcoes_incluindo_P011():
    """P011: FB<->LF assumido por simetria, mesmo sem precedente historico."""
    from app.odoo.constants.operacoes_fiscais import MATRIZ_INTERCOMPANY
    op = MATRIZ_INTERCOMPANY['dev-industrializacao']
    assert op['l10n_br_tipo_pedido'] == 'dev-industrializacao'
    assert op['tipo_produto'] == [4]
    # 4 direcoes (2 com precedente + 2 por simetria P011)
    assert set(op['fiscal_position_id'].keys()) == {(1, 5), (4, 5), (5, 1), (5, 4)}
    assert op['fiscal_position_id'][(4, 5)] == 74  # CD → LF (precedente)
    assert op['fiscal_position_id'][(5, 4)] == 89  # LF → CD (precedente)
    assert op['fiscal_position_id'][(1, 5)] == 74  # FB → LF (P011 simetria)
    assert op['fiscal_position_id'][(5, 1)] == 89  # LF → FB (P011 simetria)


def test_transf_filial_FB_e_CD_bidirecionais():
    from app.odoo.constants.operacoes_fiscais import MATRIZ_INTERCOMPANY
    op = MATRIZ_INTERCOMPANY['transf-filial']
    assert op['l10n_br_tipo_pedido'] == 'transf-filial'
    assert op['tipo_produto'] == [1, 2, 3, 4]
    assert op['fiscal_position_id'] == {(1, 4): 20, (4, 1): 49}


def test_company_locations_3_empresas():
    from app.odoo.constants.locations import COMPANY_LOCATIONS, get_location_id
    assert COMPANY_LOCATIONS == {1: 8, 4: 32, 5: 42}
    assert get_location_id(1) == 8
    assert get_location_id(4) == 32
    assert get_location_id(5) == 42


def test_get_location_id_raises_para_company_desconhecida():
    from app.odoo.constants.locations import get_location_id
    with pytest.raises(ValueError, match='company_id=99'):
        get_location_id(99)


def test_company_partner_id_consistente():
    from app.odoo.constants.operacoes_fiscais import COMPANY_PARTNER_ID
    assert COMPANY_PARTNER_ID == {1: 1, 4: 34, 5: 35}


def test_resolver_operacao_LF_tipo123_positivo():
    from app.odoo.constants.operacoes_fiscais import resolver_operacao_por_tipo_produto
    # LF + tipo 1/2/3 + sinal+ → industrializacao FB→LF
    assert resolver_operacao_por_tipo_produto(tipo=1, company_id=5, sinal=+1) == 'industrializacao'
    assert resolver_operacao_por_tipo_produto(tipo=2, company_id=5, sinal=+1) == 'industrializacao'
    assert resolver_operacao_por_tipo_produto(tipo=3, company_id=5, sinal=+1) == 'industrializacao'


def test_resolver_operacao_LF_tipo123_negativo():
    from app.odoo.constants.operacoes_fiscais import resolver_operacao_por_tipo_produto
    # LF + tipo 1/2/3 + sinal- → perda LF→FB
    assert resolver_operacao_por_tipo_produto(tipo=1, company_id=5, sinal=-1) == 'perda'


def test_resolver_operacao_LF_tipo4_ambos_sinais():
    from app.odoo.constants.operacoes_fiscais import resolver_operacao_por_tipo_produto
    # LF + tipo 4 → dev-industrializacao (independente de sinal)
    assert resolver_operacao_por_tipo_produto(tipo=4, company_id=5, sinal=+1) == 'dev-industrializacao'
    assert resolver_operacao_por_tipo_produto(tipo=4, company_id=5, sinal=-1) == 'dev-industrializacao'


def test_resolver_operacao_FB_ou_CD():
    from app.odoo.constants.operacoes_fiscais import resolver_operacao_por_tipo_produto
    # FB ou CD com qualquer tipo → transf-filial
    assert resolver_operacao_por_tipo_produto(tipo=1, company_id=4, sinal=+1) == 'transf-filial'
    assert resolver_operacao_por_tipo_produto(tipo=4, company_id=1, sinal=-1) == 'transf-filial'


def test_resolver_operacao_company_invalida_raises():
    from app.odoo.constants.operacoes_fiscais import resolver_operacao_por_tipo_produto
    with pytest.raises(ValueError, match='company_id=99'):
        resolver_operacao_por_tipo_produto(tipo=1, company_id=99, sinal=+1)


def test_get_operacao_raises_para_tipo_invalido():
    from app.odoo.constants.operacoes_fiscais import get_operacao
    with pytest.raises(KeyError, match='invalido'):
        get_operacao('invalido')


def test_get_operacao_retorna_entrada():
    from app.odoo.constants.operacoes_fiscais import get_operacao
    op = get_operacao('industrializacao')
    assert op['nf_referencia'] == 94457


def test_resolver_fiscal_position_id_por_direcao():
    """Service deve poder pedir fiscal_position para (tipo_op, origem, destino)."""
    from app.odoo.constants.operacoes_fiscais import resolver_fiscal_position
    assert resolver_fiscal_position('industrializacao', 1, 5) == 25
    assert resolver_fiscal_position('perda', 5, 1) == 91
    assert resolver_fiscal_position('dev-industrializacao', 4, 5) == 74
    assert resolver_fiscal_position('dev-industrializacao', 5, 4) == 89
    assert resolver_fiscal_position('dev-industrializacao', 1, 5) == 74  # P011
    assert resolver_fiscal_position('dev-industrializacao', 5, 1) == 89  # P011
    assert resolver_fiscal_position('transf-filial', 1, 4) == 20
    assert resolver_fiscal_position('transf-filial', 4, 1) == 49


def test_resolver_fiscal_position_direcao_invalida_raises():
    from app.odoo.constants.operacoes_fiscais import resolver_fiscal_position
    with pytest.raises(ValueError, match='fiscal_position'):
        # transf-filial nao tem direcao FB→LF
        resolver_fiscal_position('transf-filial', 1, 5)


# --- ENTRADA (in_invoice no destino) — validado no Odoo PROD 2026-05-21 ---

def test_entrada_industrializacao_FB_LF():
    """FB→LF industrializacao: saida 5901 / entrada 1901 (fp 131, serv-industrializacao)."""
    from app.odoo.constants.operacoes_fiscais import MATRIZ_INTERCOMPANY
    op = MATRIZ_INTERCOMPANY['industrializacao']
    assert op['entrada'][(1, 5)] == {
        'fiscal_position_id': 131, 'cfop': '1901',
        'l10n_br_tipo_pedido_entrada': 'serv-industrializacao',
    }


def test_entrada_perda_LF_FB():
    """LF→FB perda: saida 5903 / entrada 1903 (fp 97, retorno nao aplicado)."""
    from app.odoo.constants.operacoes_fiscais import MATRIZ_INTERCOMPANY
    op = MATRIZ_INTERCOMPANY['perda']
    assert op['entrada'][(5, 1)] == {
        'fiscal_position_id': 97, 'cfop': '1903',
        'l10n_br_tipo_pedido_entrada': 'retorno',
    }


def test_dev_industrializacao_produto4_sempre_5949():
    """Regra de negocio (Rafael 2026-05-21): produto acabado (tipo 4) usa 5949 em TODAS as
    direcoes (retrabalho/retorno/ajuste). 5902 NUNCA se aplica a produto acabado — e exclusivo
    de insumos (tipo 1,2,3) na operacao venda-industrializacao (fp 111), par interno de 5124."""
    from app.odoo.constants.operacoes_fiscais import MATRIZ_INTERCOMPANY
    op = MATRIZ_INTERCOMPANY['dev-industrializacao']
    assert op['tipo_produto'] == [4]
    for direcao in [(4, 5), (5, 4), (5, 1), (1, 5)]:
        assert op['cfop_esperado'][direcao] == '5949', direcao
        assert op['entrada'][direcao]['cfop'] == '1949', direcao
    # nenhuma variante 5902 deve existir (5902 nao e CFOP de produto acabado)
    assert 'cfop_variantes' not in op


def test_dev_industrializacao_sem_precedente_LF_FB_e_FB_LF():
    """Sem precedente VALIDO de 5949 produto tipo 4 em LF->FB nem FB->LF.
    (5,1) tem NFs historicas porem com 5902 (erro de classificacao) -> nao conta."""
    from app.odoo.constants.operacoes_fiscais import MATRIZ_INTERCOMPANY
    op = MATRIZ_INTERCOMPANY['dev-industrializacao']
    assert op['direcoes_sem_precedente_historico'] == [(1, 5), (5, 1)]


def test_resolver_cfop_variante_removido():
    """resolver_cfop_variante foi removido (variante 5902 era classificacao incorreta)."""
    import app.odoo.constants.operacoes_fiscais as mod
    assert not hasattr(mod, 'resolver_cfop_variante')


def test_entrada_transf_filial_ambas_direcoes():
    """transf-filial entrada confirmada no Odoo 2026-05-21:
    FB→CD entrada 1152 (fp 50); CD→FB entrada 1151 (fp 22). fps de entrada distintas."""
    from app.odoo.constants.operacoes_fiscais import MATRIZ_INTERCOMPANY
    op = MATRIZ_INTERCOMPANY['transf-filial']
    assert op['entrada'][(1, 4)] == {
        'fiscal_position_id': 50, 'cfop': '1152', 'l10n_br_tipo_pedido_entrada': 'transf-filial'}
    assert op['entrada'][(4, 1)] == {
        'fiscal_position_id': 22, 'cfop': '1151', 'l10n_br_tipo_pedido_entrada': 'transf-filial'}


def test_resolver_entrada_direcoes_confirmadas():
    from app.odoo.constants.operacoes_fiscais import resolver_entrada
    assert resolver_entrada('industrializacao', 1, 5)['cfop'] == '1901'
    assert resolver_entrada('perda', 5, 1)['cfop'] == '1903'
    assert resolver_entrada('dev-industrializacao', 4, 5)['cfop'] == '1949'
    assert resolver_entrada('dev-industrializacao', 5, 4)['cfop'] == '1949'
    # produto tipo 4 LF→FB = retorno/ajuste -> 1949 (5902 NAO se aplica a produto acabado)
    assert resolver_entrada('dev-industrializacao', 5, 1)['cfop'] == '1949'
    assert resolver_entrada('transf-filial', 1, 4)['cfop'] == '1152'
    assert resolver_entrada('transf-filial', 4, 1)['cfop'] == '1151'


def test_resolver_entrada_direcao_invalida_raises():
    from app.odoo.constants.operacoes_fiscais import resolver_entrada
    with pytest.raises(ValueError, match='entrada nao mapeada'):
        resolver_entrada('perda', 1, 4)
    # transf-filial so tem (1,4) e (4,1); direcao com LF nao existe
    with pytest.raises(ValueError, match='entrada nao mapeada'):
        resolver_entrada('transf-filial', 1, 5)
