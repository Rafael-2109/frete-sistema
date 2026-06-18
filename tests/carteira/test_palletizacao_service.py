"""Testes da Camada 1 do simulador de conservas (palletizacao_service)."""
import uuid
from app.carteira.services.palletizacao_service import (
    calcular_lastro, calcular_altura, CaixaItem, montar_pallets,
    montar_pallets_da_separacao,
)
from app.separacao.models import Separacao
from app.producao.models import CadastroPalletizacao


class TestGeometria:
    def test_lastro_caixa_quadrada_4830103(self):
        # caixa 26x26 -> lastro efetivo (100+5)/26=4 x (120+5)/26=4 = 16
        r = calcular_lastro(largura_cm=26, comprimento_cm=26)
        assert r['lastro'] == 16
        assert r['merc_x'] == 104
        assert r['merc_y'] == 104

    def test_lastro_escolhe_melhor_orientacao(self):
        # caixa 40x30: orient A (40 em X,30 em Y)=floor(105/40)*floor(125/30)=2*4=8
        #              orient B (30 em X,40 em Y)=floor(105/30)*floor(125/40)=3*3=9 -> vence
        r = calcular_lastro(largura_cm=40, comprimento_cm=30)
        assert r['lastro'] == 9

    def test_lastro_caixa_invalida(self):
        assert calcular_lastro(0, 26)['lastro'] == 0

    def test_altura_4_camadas(self):
        # 64 caixas / lastro 16 = 4 camadas; 15 + 4*30.5 = 137.0
        r = calcular_altura(caixas=64, lastro=16, altura_cm=30.5)
        assert r['camadas'] == 4
        assert r['altura_total'] == 137.0

    def test_altura_arredonda_para_cima(self):
        # 65 caixas / 16 = 4.06 -> 5 camadas
        assert calcular_altura(caixas=65, lastro=16, altura_cm=30.5)['camadas'] == 5

    def test_altura_lastro_zero(self):
        assert calcular_altura(caixas=10, lastro=0, altura_cm=30)['altura_total'] == 15.0


def _item(cod='A', ped='P1', cnpj='C1', qtd=64, larg=26, comp=26, alt=30.5,
          palt=64, peso=1.0):
    return CaixaItem(cod, ped, cnpj, qtd, larg, comp, alt, palt, peso)


class TestMontagem:
    def test_pallet_fechado_regra1(self):
        # 128 caixas, limite 64 -> 2 pallets fechados, sem fracao
        pallets, pend = montar_pallets([_item(qtd=128, palt=64)])
        assert len(pallets) == 2
        assert all(p.fechado for p in pallets)
        assert pend == []

    def test_fechado_mais_fracao(self):
        # 70 caixas, limite 64 -> 1 fechado (64) + 1 fracao (6)
        pallets, _ = montar_pallets([_item(qtd=70, palt=64)])
        assert len(pallets) == 2
        assert [p.fechado for p in pallets] == [True, False]

    def test_fracoes_mesma_dimensao_juntam_regra2(self):
        # 2 produtos mesma caixa (26x26), 56+56=112 <= limite 120 -> 1 pallet
        a = _item(cod='4320147', qtd=56, palt=120)
        b = _item(cod='4360147', qtd=56, palt=120)
        pallets, _ = montar_pallets([a, b], modo='A', separado_por_pallet=False)
        assert len(pallets) == 1
        cods = {c['cod_produto'] for c in pallets[0].conteudo}
        assert cods == {'4320147', '4360147'}

    def test_overbooking_50pct(self):
        # 150 caixas, palletizacao 100, overbooking 0.5 -> limite 150 -> 1 fechado
        pallets, _ = montar_pallets([_item(qtd=150, palt=100)], overbooking_pct=0.5)
        assert len([p for p in pallets if p.fechado]) == 1

    def test_modo_A_nao_mistura_pedidos(self):
        a = _item(cod='X', ped='P1', qtd=10, palt=120)
        b = _item(cod='X', ped='P2', qtd=10, palt=120)
        pallets, _ = montar_pallets([a, b], modo='A')
        # pedidos diferentes -> escopos diferentes -> 2 pallets (nunca compartilham)
        assert len(pallets) == 2

    def test_modo_B_mesmo_cnpj_compartilha(self):
        a = _item(cod='X', ped='P1', cnpj='C1', qtd=10, palt=120)
        b = _item(cod='X', ped='P2', cnpj='C1', qtd=10, palt=120)
        pallets, _ = montar_pallets([a, b], modo='B', separado_por_pallet=False)
        assert len(pallets) == 1  # mesmo CNPJ, off -> compartilham

    def test_modo_B_separado_por_pallet(self):
        a = _item(cod='X', ped='P1', cnpj='C1', qtd=10, palt=120)
        b = _item(cod='X', ped='P2', cnpj='C1', qtd=10, palt=120)
        pallets, _ = montar_pallets([a, b], modo='B', separado_por_pallet=True)
        assert len(pallets) == 2  # on -> pedidos nao dividem pallet

    def test_modo_D_ignora_pedido_e_cliente(self):
        a = _item(cod='X', ped='P1', cnpj='C1', qtd=60, palt=120)
        b = _item(cod='X', ped='P2', cnpj='C2', qtd=60, palt=120)
        pallets, _ = montar_pallets([a, b], modo='D')
        assert len(pallets) == 1  # so produto: 120 caixas num pallet
        assert pallets[0].conteudo[0]['num_pedido'] == ''

    def test_pendencia_cadastro_incompleto(self):
        bom = _item(cod='OK', qtd=10)
        ruim = _item(cod='RUIM', qtd=10, palt=0)
        pallets, pend = montar_pallets([bom, ruim])
        assert len(pend) == 1 and pend[0]['cod_produto'] == 'RUIM'
        assert all('RUIM' not in [c['cod_produto'] for c in p.conteudo] for p in pallets)

    def test_to_dict_serializa(self):
        pallets, _ = montar_pallets([_item(qtd=64, palt=64)])
        d = pallets[0].to_dict()
        assert d['tipo'] == 'pallet'
        assert d['altura_total'] == 137.0
        assert d['merc_x'] == 104


class TestLoader:
    def _cod(self):
        return f"TEST{uuid.uuid4().hex[:8]}"

    def test_carrega_separacao_e_monta(self, db):
        cod = self._cod()
        lote = f"LOTE_{uuid.uuid4().hex[:10]}"
        db.session.add(CadastroPalletizacao(
            cod_produto=cod, nome_produto='CONSERVA TESTE',
            palletizacao=64, peso_bruto=1.0,
            altura_cm=30.5, largura_cm=26, comprimento_cm=26, ativo=True))
        db.session.add(Separacao(
            separacao_lote_id=lote, num_pedido='PED1', cnpj_cpf='C1',
            cod_produto=cod, qtd_saldo=128, cod_uf='SP'))
        db.session.flush()

        out = montar_pallets_da_separacao(lote)
        assert out['resumo']['n_pallets'] == 2
        assert out['pendencias'] == []
        assert out['pallets'][0]['tipo'] == 'pallet'

    def test_separacao_vazia(self, db):
        out = montar_pallets_da_separacao(f"LOTE_INEXISTENTE_{uuid.uuid4().hex[:6]}")
        assert out['resumo']['n_pallets'] == 0


def _login_carvia(client, db):
    """Cria e loga um usuario com sistema_carvia (LOGIN_DISABLED nao afeta current_user)."""
    from app.auth.models import Usuario
    user = Usuario(nome='Teste Carvia', email=f"carvia_{uuid.uuid4().hex[:8]}@t.com",
                   senha_hash='x', sistema_carvia=True)
    db.session.add(user)
    db.session.flush()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True
    return user


class TestEndpoint:
    def test_pallets_por_separacao_ok(self, client, db):
        _login_carvia(client, db)
        cod = f"TEST{uuid.uuid4().hex[:8]}"
        lote = f"LOTE_{uuid.uuid4().hex[:10]}"
        db.session.add(CadastroPalletizacao(
            cod_produto=cod, nome_produto='X', palletizacao=64, peso_bruto=1.0,
            altura_cm=30.5, largura_cm=26, comprimento_cm=26, ativo=True))
        db.session.add(Separacao(separacao_lote_id=lote, num_pedido='P1',
                                 cnpj_cpf='C1', cod_produto=cod, qtd_saldo=128, cod_uf='SP'))
        db.session.flush()
        resp = client.get(f'/carvia/api/simulador-carga/pallets-por-separacao?lote={lote}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['resumo']['n_pallets'] == 2

    def test_pallets_por_separacao_sem_lote(self, client, db):
        _login_carvia(client, db)
        resp = client.get('/carvia/api/simulador-carga/pallets-por-separacao')
        assert resp.status_code == 400
