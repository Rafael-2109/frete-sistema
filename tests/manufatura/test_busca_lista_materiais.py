"""
Testes da busca de produtos na tela de Lista de Materiais (BOM).

Cobre `listar_produtos_produzidos` em
app/manufatura/routes/lista_materiais_routes.py — especificamente o requisito de
que a busca casa NÃO SÓ no produto acabado, mas TAMBÉM nos componentes contidos
nele (um produto produzido aparece se algum componente da sua BOM casar com o
termo). Usa a fixture `db` (savepoint + rollback) e `client` de tests/conftest.py.

Cada teste usa um TOKEN único no termo de busca para isolar do conteúdo real do
banco PostgreSQL local de teste.
"""
import uuid

from app.producao.models import CadastroPalletizacao
from app.manufatura.models import ListaMateriais

URL = '/manufatura/api/lista-materiais/produtos-produzidos'


def _cod():
    return f"T{uuid.uuid4().hex[:11]}"


def _token():
    return f"ZZ{uuid.uuid4().hex[:8].upper()}"


def _criar_acabado(db, nome):
    cod = _cod()
    db.session.add(CadastroPalletizacao(
        cod_produto=cod, nome_produto=nome,
        palletizacao=1, peso_bruto=1,
        produto_produzido=True, produto_vendido=True, ativo=True))
    db.session.flush()
    return cod


def _criar_componente(db, nome):
    cod = _cod()
    db.session.add(CadastroPalletizacao(
        cod_produto=cod, nome_produto=nome,
        palletizacao=1, peso_bruto=1,
        produto_comprado=True, ativo=True))
    db.session.flush()
    return cod


def _ligar_bom(db, cod_acabado, nome_acabado, cod_comp, nome_comp):
    db.session.add(ListaMateriais(
        cod_produto_produzido=cod_acabado, nome_produto_produzido=nome_acabado,
        cod_produto_componente=cod_comp, nome_produto_componente=nome_comp,
        qtd_utilizada=2, status='ativo', versao='v1'))
    db.session.flush()


class TestBuscaPorComponente:
    def test_acabado_aparece_quando_componente_casa_pelo_nome(self, db, client):
        token = _token()
        nome_acabado = f"AZEITONA VERDE {_token()}"   # NÃO contém o token buscado
        nome_comp = f"TAMPA METALICA {token}"          # contém o token buscado

        cod_acabado = _criar_acabado(db, nome_acabado)
        cod_comp = _criar_componente(db, nome_comp)
        _ligar_bom(db, cod_acabado, nome_acabado, cod_comp, nome_comp)

        resp = client.get(f"{URL}?busca={token}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['sucesso'] is True

        produtos = {p['cod_produto']: p for p in data['produtos']}
        # O acabado entrou na busca SÓ por causa do componente
        assert cod_acabado in produtos, "Produto acabado deveria aparecer via componente"

        match = produtos[cod_acabado]['match_componentes']
        assert any(m['cod'] == cod_comp for m in match), \
            "match_componentes deveria apontar o componente que casou"

    def test_acabado_aparece_quando_componente_casa_pelo_codigo(self, db, client):
        # Componente cujo CÓDIGO contém o token (busca por código de componente)
        token = _token()
        cod_acabado = _criar_acabado(db, f"PALMITO {_token()}")
        cod_comp = f"{token}{uuid.uuid4().hex[:4]}"
        db.session.add(CadastroPalletizacao(
            cod_produto=cod_comp, nome_produto="MATERIA PRIMA",
            palletizacao=1, peso_bruto=1, produto_comprado=True, ativo=True))
        db.session.flush()
        _ligar_bom(db, cod_acabado, "PALMITO", cod_comp, "MATERIA PRIMA")

        resp = client.get(f"{URL}?busca={token}")
        data = resp.get_json()
        produtos = {p['cod_produto']: p for p in data['produtos']}
        assert cod_acabado in produtos
        assert any(m['cod'] == cod_comp for m in produtos[cod_acabado]['match_componentes'])

    def test_busca_pelo_proprio_acabado_continua_funcionando(self, db, client):
        # Regressão: busca pelo nome do próprio produto acabado deve seguir achando-o,
        # com match_componentes vazio (não entrou por componente).
        token = _token()
        nome_acabado = f"CONSERVA {token}"
        cod_acabado = _criar_acabado(db, nome_acabado)

        resp = client.get(f"{URL}?busca={token}")
        data = resp.get_json()
        produtos = {p['cod_produto']: p for p in data['produtos']}
        assert cod_acabado in produtos
        assert produtos[cod_acabado]['match_componentes'] == []

    def test_componente_inativo_nao_traz_acabado(self, db, client):
        # Componente com BOM status='inativo' não deve fazer o acabado aparecer.
        token = _token()
        nome_comp = f"ROTULO {token}"
        cod_acabado = _criar_acabado(db, f"GELEIA {_token()}")
        cod_comp = _criar_componente(db, nome_comp)
        db.session.add(ListaMateriais(
            cod_produto_produzido=cod_acabado, nome_produto_produzido="GELEIA",
            cod_produto_componente=cod_comp, nome_produto_componente=nome_comp,
            qtd_utilizada=1, status='inativo', versao='v1'))
        db.session.flush()

        resp = client.get(f"{URL}?busca={token}")
        data = resp.get_json()
        produtos = {p['cod_produto'] for p in data['produtos']}
        assert cod_acabado not in produtos

    def test_token_inexistente_nao_retorna_nada_meu(self, client):
        token = _token()  # nunca gravado em lugar nenhum
        resp = client.get(f"{URL}?busca={token}")
        data = resp.get_json()
        assert data['sucesso'] is True
        # nenhum produto de teste casa com um token totalmente novo
        assert all(token not in p['cod_produto'] for p in data['produtos'])
