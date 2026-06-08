"""Testes determinísticos da tool buscar_tabelas (S1 — progressive disclosure).

Gate S1 (MASTER text-to-sql): golden set de intencoes -> tabela esperada, top-3
em >=90% (acordado na sessao). Determinístico: roda sobre a busca TEXTUAL (sem
DB/Voyage) lendo o catalog.json real. A camada semantica e testada via mock
(fusao) — invariante 6: SEM evals LLM caros.

Tambem trava a invariante de SEGURANCA: tabela bloqueada/pessoal NUNCA vaza em
buscar_tabelas (mesma matriz de permissao do executor de SQL).
"""
import pytest

from app.agente.tools import buscar_tabelas_tool as B

# Usuarios de teste (vs B.USUARIOS_SQL_ADMIN / B.USUARIOS_PESSOAL)
COMUM = 99          # nao-admin, nao-pessoal
ADMIN = sorted(B.USUARIOS_SQL_ADMIN)[0]  # 1 (admin + pessoal)


@pytest.fixture(scope="module")
def catalog():
    return B._get_catalog()


# =====================================================================
# GOLDEN SET — gate S1 (top-3 >= 90%)
# =====================================================================
# Intencoes realistas cujo alvo e identificavel pelo vocabulario da propria
# tabela (nome/descricao/key_fields pos-S2). Casos puramente semanticos (a
# palavra do conceito ausente da intencao) sao da camada de embeddings.
GOLDEN_SET = [
    ('carteira de pedidos pendentes', 'carteira_principal'),
    ('separacao de itens para expedicao', 'separacao'),
    ('faturamento por produto', 'faturamento_produto'),
    ('faturamento mensal de notas fiscais', 'faturamento_produto'),
    ('fretes pendentes de pagamento', 'fretes'),
    ('despesas extras de frete', 'despesas_extras'),
    ('cotacao de frete', 'cotacoes'),
    ('embarques por transportadora', 'embarques'),
    ('itens do embarque', 'embarque_itens'),
    ('entregas monitoradas atrasadas', 'entregas_monitoradas'),
    ('agendamento de entrega', 'agendamentos_entrega'),
    ('movimentacao de estoque', 'movimentacao_estoque'),
    ('programacao de producao', 'programacao_producao'),
    ('nf de devolucao', 'nf_devolucao'),
    ('contas a receber vencidas', 'contas_a_receber'),
    ('cadastro de transportadoras', 'transportadoras'),
    ('conta corrente de transportadora', 'conta_corrente_transportadoras'),
    ('controle de portaria', 'controle_portaria'),
    ('creditos de pallets a receber', 'pallet_creditos'),
    ('cidades atendidas por transportadora', 'cidades_atendidas'),
]

GATE_TOP_N = 3
GATE_PRECISION = 0.90  # acordado na sessao


class TestGoldenSetGate:
    def test_top3_precision_atinge_gate(self, catalog):
        acertos = 0
        falhas = []
        for intencao, esperada in GOLDEN_SET:
            nomes = [r['tabela'] for r in B.buscar(intencao, COMUM, catalog, None, 5)]
            if esperada in nomes[:GATE_TOP_N]:
                acertos += 1
            else:
                falhas.append((intencao, esperada, nomes[:GATE_TOP_N]))
        precisao = acertos / len(GOLDEN_SET)
        assert precisao >= GATE_PRECISION, (
            f"precisao@{GATE_TOP_N}={precisao:.0%} < {GATE_PRECISION:.0%}. Falhas: {falhas}"
        )

    @pytest.mark.parametrize("intencao,esperada", [
        ('carteira de pedidos pendentes', 'carteira_principal'),
        ('faturamento por produto', 'faturamento_produto'),
        ('separacao de itens para expedicao', 'separacao'),
    ])
    def test_flagship_top1(self, catalog, intencao, esperada):
        """As 3 tabelas-chave do MASTER devem vir em 1o lugar."""
        nomes = [r['tabela'] for r in B.buscar(intencao, COMUM, catalog, None, 5)]
        assert nomes[:1] == [esperada], f"{intencao!r} -> {nomes[:3]}"

    def test_resultado_tem_dominio_e_key_fields(self, catalog):
        res = B.buscar('faturamento por produto', COMUM, catalog, None, 3)
        assert res, "deveria retornar candidatas"
        top = res[0]
        assert top['tabela'] == 'faturamento_produto'
        assert top['dominio'] == 'Faturamento'
        assert top['key_fields']  # nao vazio
        # sem semantic_fn -> origem textual, similaridade None
        assert top['origem'] == 'textual'
        assert top['similaridade'] is None


# =====================================================================
# PERMISSAO — tabela bloqueada/pessoal NUNCA vaza (invariante 5)
# =====================================================================
class TestPermissao:
    def test_comum_nao_ve_pessoal(self, catalog):
        # a query CASA pessoal_* (pessoais~pessoal), mas o comum nao pode ve-las
        res = B.buscar('membros e contas pessoais', COMUM, catalog, None, 20)
        nomes = {r['tabela'] for r in res}
        assert not (nomes & B.TABELAS_PESSOAL), f"vazou pessoal: {nomes & B.TABELAS_PESSOAL}"

    def test_pessoal_admin_ve_pessoal(self, catalog):
        # user em PESSOAL/ADMIN pode ver pessoal_*
        if not (set(B.USUARIOS_PESSOAL) | B.USUARIOS_SQL_ADMIN):
            pytest.skip("sem usuarios pessoal/admin configurados")
        res = B.buscar('membros e contas pessoais', ADMIN, catalog, None, 20)
        nomes = {r['tabela'] for r in res}
        assert nomes & B.TABELAS_PESSOAL, "admin/pessoal deveria ver pessoal_*"

    def test_comum_nao_ve_tabelas_admin(self, catalog):
        # tabelas_admin (auth/agente) nunca aparecem p/ comum
        admin_names = {e['name'] for e in catalog.get('tabelas_admin', [])}
        res = B.buscar('usuarios e sessoes do agente', COMUM, catalog, None, 20)
        nomes = {r['tabela'] for r in res}
        assert not (nomes & admin_names), f"vazou admin: {nomes & admin_names}"

    def test_admin_ve_tabelas_admin(self, catalog):
        admin_names = {e['name'] for e in catalog.get('tabelas_admin', [])}
        if not admin_names:
            pytest.skip("sem tabelas_admin no catalogo")
        res = B.buscar('usuarios e sessoes do agente', ADMIN, catalog, None, 20)
        nomes = {r['tabela'] for r in res}
        assert nomes & admin_names, "admin deveria ver tabelas_admin"


# =====================================================================
# FUSAO SEMANTICA (mock — sem Voyage/DB)
# =====================================================================
class TestFusaoSemantica:
    def test_semantica_none_usa_textual(self, catalog):
        """semantic_fn=None (embeddings off) -> resultado puramente textual."""
        res = B.buscar('faturamento por produto', COMUM, catalog, None, 3)
        assert res[0]['tabela'] == 'faturamento_produto'

    def test_semantica_e_primaria(self, catalog):
        """Semantica PRIMARIA: a tabela da semantica vem no TOPO (mesmo sem match
        textual), com origem/similaridade preenchidas."""
        def fake_semantic(intencao, limite):
            return [{'table_name': 'embarques', 'similarity': 0.9}]
        res = B.buscar('xyz termo inexistente zzz', COMUM, catalog, fake_semantic, 5)
        assert res[0]['tabela'] == 'embarques'
        assert res[0]['origem'] == 'semantica'
        assert res[0]['similaridade'] == 0.9

    def test_textual_preenche_apos_semantica(self, catalog):
        """Textual entra como APPEND: tabela textual relevante aparece depois da
        semantica (fallback/preenchimento + freshness de tabela nova)."""
        def fake_semantic(intencao, limite):
            return [{'table_name': 'embarques', 'similarity': 0.9}]
        res = B.buscar('faturamento por produto', COMUM, catalog, fake_semantic, 5)
        nomes = [r['tabela'] for r in res]
        assert nomes[0] == 'embarques'                 # semantica primeiro
        assert 'faturamento_produto' in nomes          # textual preenche
        fat = next(r for r in res if r['tabela'] == 'faturamento_produto')
        assert fat['origem'] == 'textual'

    def test_semantica_nao_vaza_bloqueada(self, catalog):
        """Mesmo que a semantica retorne tabela nao-visivel, ela e filtrada."""
        def leaky_semantic(intencao, limite):
            return [{'table_name': 'pessoal_membros'},
                    {'table_name': 'agent_sessions'}]
        res = B.buscar('qualquer coisa', COMUM, catalog, leaky_semantic, 10)
        nomes = {r['tabela'] for r in res}
        assert 'pessoal_membros' not in nomes
        assert 'agent_sessions' not in nomes

    def test_semantica_falha_cai_para_textual(self, catalog):
        """semantic_fn que lanca excecao nao quebra a busca."""
        def boom(intencao, limite):
            raise RuntimeError("voyage indisponivel")
        res = B.buscar('faturamento por produto', COMUM, catalog, boom, 3)
        assert res[0]['tabela'] == 'faturamento_produto'


# =====================================================================
# NORMALIZACAO E MATCHING
# =====================================================================
class TestNormalizacaoMatching:
    def test_normalize_remove_acento_e_stopword(self):
        toks = B._normalize('Notas Fiscais do cliente')
        assert 'fiscais' in toks
        assert 'do' not in toks   # stopword
        assert all(t == B._strip_accents(t) for t in toks)  # sem acento

    def test_tok_match_plural(self):
        assert B._tok_match('pedidos', 'pedido')
        assert B._tok_match('pendentes', 'pendente')
        assert B._tok_match('faturadas', 'faturamento')  # raiz comum >= 5

    def test_tok_match_nao_casa_diferentes(self):
        assert not B._tok_match('estado', 'estoque')
        assert not B._tok_match('nota', 'rota')


# =====================================================================
# EDGE CASES
# =====================================================================
class TestEdgeCases:
    def test_intencao_vazia(self, catalog):
        assert B.buscar('', COMUM, catalog, None, 5) == []

    def test_intencao_so_stopwords(self, catalog):
        assert B.buscar('de o a para com', COMUM, catalog, None, 5) == []

    def test_intencao_sem_match(self, catalog):
        # termos que nao casam nenhuma tabela -> lista vazia (sem semantica)
        assert B.buscar('zzzqxw kkkjjj', COMUM, catalog, None, 5) == []

    def test_respeita_limite(self, catalog):
        res = B.buscar('frete', COMUM, catalog, None, 3)
        assert len(res) <= 3
