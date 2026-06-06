"""
Testes da Análise de Produção — inclusão de componentes apontados FORA do BOM atual.

Cobre `_anexar_componentes_fora_bom` em
app/manufatura/routes/analise_producao_routes.py (dedup BOM ∪ apontados +
inversão de sinal do ajuste). Usa a fixture `db` (savepoint + rollback) de
tests/conftest.py.
"""
import uuid

from app.manufatura.routes.analise_producao_routes import _anexar_componentes_fora_bom
from app.producao.models import CadastroPalletizacao


def _cod():
    return f"TEST{uuid.uuid4().hex[:10]}"


def _comp_bom(cod, previsto, consumo_real, ajuste_registrado=0):
    """Linha de componente como o achatar_bom monta (vinda do BOM atual)."""
    return {
        'cod_produto': cod,
        'nome_produto': f'BOM {cod}',
        'tipo': 'COMPONENTE',
        'nivel': 1,
        'qtd_necessaria': previsto,
        'consumo_previsto': previsto,
        'consumo_registrado': consumo_real - ajuste_registrado,
        'ajuste_registrado': ajuste_registrado,
        'consumo_real': consumo_real,
        'estoque_atual': 0,
        'tem_estrutura': False,
    }


class TestAnexarComponentesForaBom:
    def test_apontado_fora_do_bom_entra_com_previsto_zero(self, db):
        # Componente A foi consumido (500) mas NÃO está no BOM atual (só B está)
        cod_a = _cod()
        db.session.add(CadastroPalletizacao(
            cod_produto=cod_a, nome_produto='AZEITONA A',
            palletizacao=1, peso_bruto=1, produto_comprado=True, ativo=True))
        db.session.flush()

        componentes = [_comp_bom('B', previsto=10, consumo_real=0)]
        res = _anexar_componentes_fora_bom(componentes, {cod_a: 500}, {})

        a = next(c for c in res if c['cod_produto'] == cod_a)
        assert a['fora_bom'] is True
        assert a['consumo_previsto'] == 0
        assert a['qtd_necessaria'] == 0
        assert a['consumo_registrado'] == 500
        assert a['consumo_real'] == 500
        assert a['nome_produto'] == 'AZEITONA A'  # nome veio do cadastro

        # Componente do BOM é marcado como dentro do BOM
        b = next(c for c in res if c['cod_produto'] == 'B')
        assert b['fora_bom'] is False

    def test_ajuste_registrado_invertido_para_visao_consumo(self, db):
        # ajuste_estoque = -5 (consumiu 5 a mais) -> ajuste_registrado = +5
        cod = _cod()
        res = _anexar_componentes_fora_bom([], {cod: 0}, {cod: -5})
        a = res[0]
        assert a['fora_bom'] is True
        assert a['ajuste_registrado'] == 5
        assert a['consumo_real'] == 5  # consumo_registrado(0) + ajuste_registrado(5)

    def test_nao_duplica_componente_ja_no_bom(self, db):
        # X está no BOM E foi apontado: não deve ser duplicado
        componentes = [_comp_bom('X', previsto=10, consumo_real=10)]
        res = _anexar_componentes_fora_bom(componentes, {'X': 10}, {'X': 0})
        ocorrencias = [c for c in res if c['cod_produto'] == 'X']
        assert len(ocorrencias) == 1
        assert ocorrencias[0]['fora_bom'] is False

    def test_sem_apontados_retorna_lista_intacta(self, db):
        componentes = [_comp_bom('B', previsto=10, consumo_real=10)]
        res = _anexar_componentes_fora_bom(componentes, {}, {})
        assert len(res) == 1
        assert res[0]['fora_bom'] is False

    def test_nome_fallback_quando_sem_cadastro(self, db):
        cod = _cod()  # não cadastrado
        res = _anexar_componentes_fora_bom([], {cod: 100}, {})
        a = res[0]
        assert a['nome_produto'] == f'Produto {cod}'
        assert a['fora_bom'] is True
