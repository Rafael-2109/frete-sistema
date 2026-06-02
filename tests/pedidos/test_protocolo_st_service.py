"""
Testes do ProtocoloStService — split de NF por protocolo ST (Atacadão RJ).

A função `gerar_grupos_lancamento` é PURA (sem DB) e concentra a regra de split.
Os enrichers tocam o banco (fixture `db`).
"""
from app.pedidos.services.protocolo_st_service import (
    gerar_grupos_lancamento,
    enriquecer_itens_raw,
    enriquecer_separar_flag,
)


def _item(nosso_codigo, protocolo_st, divergente=False, qtd=10, preco_doc=100.0,
          preco_final=None, codigo_rede=None):
    return {
        'codigo_rede': codigo_rede or f'A{nosso_codigo}',
        'nosso_codigo': nosso_codigo,
        'descricao': f'PRODUTO {nosso_codigo}',
        'quantidade': qtd,
        'preco_documento': preco_doc,
        'preco_tabela': preco_doc if not divergente else preco_doc - 5,
        'preco_final': preco_final if preco_final is not None else preco_doc,
        'divergente': divergente,
        'diferenca_percentual': 0 if not divergente else 5.0,
        'protocolo_st': protocolo_st,
    }


def _filial(itens, separar, uf='RJ'):
    return {
        'cnpj': '93.209.765/0599-44',
        'nome_cliente': 'ATACADAO SA',
        'uf': uf,
        'separar_protocolo_st': separar,
        'numero_pedido_cliente': '4500123456',
        'itens': itens,
    }


# ===================== gerar_grupos_lancamento (PURO) =====================

class TestGerarGruposLancamento:

    def test_flag_off_com_dois_tipos_retorna_um_grupo(self):
        """Flag OFF: nunca separa, mesmo com produtos ST e não-ST juntos."""
        filial = _filial([
            _item('111', protocolo_st=True),
            _item('222', protocolo_st=False),
        ], separar=False)

        grupos = gerar_grupos_lancamento(filial)

        assert len(grupos) == 1
        assert grupos[0]['rotulo_st'] is None
        assert len(grupos[0]['itens_odoo']) == 2

    def test_flag_on_so_st_retorna_um_grupo(self):
        """Flag ON mas só produtos ST → não há o que separar → 1 grupo."""
        filial = _filial([
            _item('111', protocolo_st=True),
            _item('333', protocolo_st=True),
        ], separar=True)

        grupos = gerar_grupos_lancamento(filial)

        assert len(grupos) == 1
        assert grupos[0]['rotulo_st'] is None
        assert len(grupos[0]['itens_odoo']) == 2

    def test_flag_on_so_demais_retorna_um_grupo(self):
        """Flag ON mas só produtos não-ST → 1 grupo."""
        filial = _filial([
            _item('222', protocolo_st=False),
            _item('444', protocolo_st=False),
        ], separar=True)

        grupos = gerar_grupos_lancamento(filial)

        assert len(grupos) == 1
        assert grupos[0]['rotulo_st'] is None

    def test_flag_on_dois_tipos_separa_em_dois_grupos(self):
        """Flag ON + ambos os tipos → 2 grupos: ST primeiro, depois Demais."""
        filial = _filial([
            _item('111', protocolo_st=True),
            _item('222', protocolo_st=False),
            _item('333', protocolo_st=True),
        ], separar=True)

        grupos = gerar_grupos_lancamento(filial)

        assert len(grupos) == 2
        # ST primeiro
        assert grupos[0]['rotulo_st'] == 'ST'
        assert {i['nosso_codigo'] for i in grupos[0]['itens_odoo']} == {'111', '333'}
        # Demais depois
        assert grupos[1]['rotulo_st'] == 'NORMAL'
        assert {i['nosso_codigo'] for i in grupos[1]['itens_odoo']} == {'222'}

    def test_itens_odoo_tem_estrutura_correta(self):
        """itens_odoo carrega nosso_codigo, quantidade, preco (preco_final), uf, nome_cliente."""
        filial = _filial([
            _item('111', protocolo_st=False, qtd=7, preco_doc=200.0, preco_final=190.0),
        ], separar=False)

        grupos = gerar_grupos_lancamento(filial)
        item_odoo = grupos[0]['itens_odoo'][0]

        assert item_odoo['nosso_codigo'] == '111'
        assert item_odoo['quantidade'] == 7
        assert item_odoo['preco'] == 190.0  # usa preco_final
        assert item_odoo['uf'] == 'RJ'
        assert item_odoo['nome_cliente'] == 'ATACADAO SA'

    def test_divergencias_por_grupo(self):
        """Cada grupo carrega apenas as divergências dos seus próprios itens."""
        filial = _filial([
            _item('111', protocolo_st=True, divergente=True),
            _item('222', protocolo_st=False, divergente=False),
        ], separar=True)

        grupos = gerar_grupos_lancamento(filial)

        grupo_st = next(g for g in grupos if g['rotulo_st'] == 'ST')
        grupo_normal = next(g for g in grupos if g['rotulo_st'] == 'NORMAL')

        assert grupo_st['tem_divergencia'] is True
        assert grupo_st['divergencias'] is not None
        assert len(grupo_st['divergencias']) == 1
        assert grupo_st['divergencias'][0]['codigo'] == '111'

        assert grupo_normal['tem_divergencia'] is False
        assert grupo_normal['divergencias'] is None

    def test_item_sem_nosso_codigo_nao_entra_em_itens_odoo(self):
        """Itens sem De-Para (sem nosso_codigo) não geram linha Odoo."""
        filial = _filial([
            _item('111', protocolo_st=False),
            {'codigo_rede': 'X', 'nosso_codigo': None, 'quantidade': 5,
             'preco_documento': 10, 'preco_final': 10, 'divergente': False,
             'protocolo_st': False},
        ], separar=False)

        grupos = gerar_grupos_lancamento(filial)

        assert len(grupos) == 1
        assert len(grupos[0]['itens_odoo']) == 1
        assert grupos[0]['itens_odoo'][0]['nosso_codigo'] == '111'

    def test_protocolo_st_ausente_tratado_como_false(self):
        """Item sem chave protocolo_st é tratado como não-ST (default False)."""
        item_sem_flag = _item('111', protocolo_st=False)
        del item_sem_flag['protocolo_st']
        filial = _filial([item_sem_flag, _item('222', protocolo_st=True)], separar=True)

        grupos = gerar_grupos_lancamento(filial)

        # 111 (sem flag) vira Demais, 222 vira ST → separa em 2
        assert len(grupos) == 2
        grupo_normal = next(g for g in grupos if g['rotulo_st'] == 'NORMAL')
        assert {i['nosso_codigo'] for i in grupo_normal['itens_odoo']} == {'111'}


# ===================== enrichers (DB) =====================

class TestEnriquecerSepararFlag:
    # Usa rede ficticia 'TESTE_ST' p/ isolar dos dados reais do banco local
    # (UniqueConstraint(rede, uf) impede reusar ATACADAO/RJ existente).

    def test_marca_filial_quando_uf_tem_flag(self, db):
        from app.pedidos.validacao.models import RegiaoTabelaRede
        db.session.add(RegiaoTabelaRede(
            rede='TESTE_ST', uf='RJ', regiao='SUDESTE/SUL',
            separar_protocolo_st=True, ativo=True,
        ))
        db.session.add(RegiaoTabelaRede(
            rede='TESTE_ST', uf='SP', regiao='SAO PAULO',
            separar_protocolo_st=False, ativo=True,
        ))
        db.session.flush()

        dados_filiais = [{'uf': 'RJ', 'itens': []}, {'uf': 'SP', 'itens': []}]
        enriquecer_separar_flag(dados_filiais, 'TESTE_ST')

        assert dados_filiais[0]['separar_protocolo_st'] is True
        assert dados_filiais[1]['separar_protocolo_st'] is False

    def test_uf_sem_registro_fica_false(self, db):
        dados_filiais = [{'uf': 'RJ', 'itens': []}]
        enriquecer_separar_flag(dados_filiais, 'TESTE_ST')
        assert dados_filiais[0]['separar_protocolo_st'] is False


class TestEnriquecerItensRaw:
    # Usa codigos ficticios (ZZTEST*) p/ isolar dos De-Para reais do banco local.

    def test_marca_protocolo_st_por_nosso_codigo(self, db):
        from app.portal.atacadao.models import ProdutoDeParaAtacadao
        db.session.add(ProdutoDeParaAtacadao(
            codigo_nosso='ZZTEST_A', codigo_atacadao='ZZTA',
            protocolo_st=True, ativo=True,
        ))
        db.session.add(ProdutoDeParaAtacadao(
            codigo_nosso='ZZTEST_B', codigo_atacadao='ZZTB',
            protocolo_st=False, ativo=True,
        ))
        db.session.flush()

        itens = [
            {'nosso_codigo': 'ZZTEST_A', 'codigo': 'ZZTA', 'cnpj_filial': 'x'},
            {'nosso_codigo': 'ZZTEST_B', 'codigo': 'ZZTB', 'cnpj_filial': 'x'},
        ]
        enriquecer_itens_raw(itens, 'ATACADAO')

        assert itens[0]['protocolo_st'] is True
        assert itens[1]['protocolo_st'] is False

    def test_any_agregacao_quando_multiplas_linhas(self, db):
        """Se qualquer linha do De-Para do mesmo nosso_codigo é ST, produto é ST."""
        from app.portal.atacadao.models import ProdutoDeParaAtacadao
        db.session.add(ProdutoDeParaAtacadao(
            codigo_nosso='ZZTEST_999', codigo_atacadao='ZZAAA', cnpj_cliente=None,
            protocolo_st=False, ativo=True,
        ))
        db.session.add(ProdutoDeParaAtacadao(
            codigo_nosso='ZZTEST_999', codigo_atacadao='ZZBBB', cnpj_cliente='123',
            protocolo_st=True, ativo=True,
        ))
        db.session.flush()

        itens = [{'nosso_codigo': 'ZZTEST_999', 'codigo': 'ZZAAA', 'cnpj_filial': 'x'}]
        enriquecer_itens_raw(itens, 'ATACADAO')

        assert itens[0]['protocolo_st'] is True

    def test_rede_nao_atacadao_define_false_sem_query(self, db):
        itens = [{'nosso_codigo': '111', 'codigo': 'Z'}]
        enriquecer_itens_raw(itens, 'ASSAI')
        assert itens[0]['protocolo_st'] is False

    def test_sobrescreve_protocolo_st_false_obsoleto(self, db):
        """Regressão /reprocessar: item que ficou protocolo_st=False no upload (sem De-Para)
        é corrigido ao re-enriquecer depois de ganhar nosso_codigo via De-Para tardio."""
        from app.portal.atacadao.models import ProdutoDeParaAtacadao
        db.session.add(ProdutoDeParaAtacadao(
            codigo_nosso='ZZTEST_RE', codigo_atacadao='ZZRE',
            protocolo_st=True, ativo=True,
        ))
        db.session.flush()

        # Estado pós-reprocessar: nosso_codigo já resolvido, mas protocolo_st obsoleto (False).
        itens = [{'nosso_codigo': 'ZZTEST_RE', 'codigo': 'ZZRE', 'protocolo_st': False}]
        enriquecer_itens_raw(itens, 'ATACADAO')

        assert itens[0]['protocolo_st'] is True
