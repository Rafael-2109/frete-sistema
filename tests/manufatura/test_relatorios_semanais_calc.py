"""
Testes unitários (puros, sem DB) do núcleo de cálculo dos Relatórios Semanais
de Manufatura.

Cobre as 4 regras algorítmicas sensíveis:
  - classificar_aba       (split por prefixo de código + flag MP)
  - flatten_bom_folhas    (agregação das folhas da árvore explodir_bom)
  - simular_producao_pa   (buffer de Produto Acabado absorvendo a venda média)
  - tempo_estoque_sem_pa / tempo_estoque_com_pa (cobertura em dias)

São funções PURAS: nenhuma toca banco, app context ou rede.
"""
import math

from app.manufatura.services.relatorios_semanais_calc import (
    classificar_aba,
    flatten_bom_folhas,
    simular_producao_pa,
    tempo_estoque_sem_pa,
    tempo_estoque_com_pa,
    colapsar_por_unificacao,
    DIAS_MES,
    MESES_HORIZONTE,
)


# ---------------------------------------------------------------------------
# classificar_aba — contexto rel2 (3 abas + exclusão MP)
# ---------------------------------------------------------------------------
class TestClassificarAbaRel2:
    def test_codigo_1_com_mp_e_excluido(self):
        assert classificar_aba("110001", "MP", contexto="rel2") == "MP_EXCLUIDO"

    def test_codigo_1_sem_mp_e_insumo(self):
        assert classificar_aba("110001", "PALMITO", contexto="rel2") == "INSUMOS"

    def test_codigo_1_materia_prima_none_e_insumo(self):
        assert classificar_aba("110001", None, contexto="rel2") == "INSUMOS"

    def test_codigo_2_e_embalagem(self):
        assert classificar_aba("210050", None, contexto="rel2") == "EMBALAGENS"

    def test_codigo_4_e_produto_acabado(self):
        assert classificar_aba("410999", None, contexto="rel2") == "PRODUTO_ACABADO"

    def test_codigo_outro_prefixo_e_outros(self):
        assert classificar_aba("310000", None, contexto="rel2") == "OUTROS"

    def test_mp_case_insensitive_e_com_espaco(self):
        assert classificar_aba("110001", " mp ", contexto="rel2") == "MP_EXCLUIDO"


# ---------------------------------------------------------------------------
# classificar_aba — contexto rel1 (somente Insumos/Embalagens, SEM exclusão MP)
# ---------------------------------------------------------------------------
class TestClassificarAbaRel1:
    def test_codigo_1_com_mp_ainda_e_insumo(self):
        # Rel.1 NÃO exclui MP (só o Rel.2 exclui)
        assert classificar_aba("110001", "MP", contexto="rel1") == "INSUMOS"

    def test_codigo_2_e_embalagem(self):
        assert classificar_aba("210050", None, contexto="rel1") == "EMBALAGENS"

    def test_codigo_4_cai_em_outros_no_rel1(self):
        # Rel.1 não tem aba de Produto Acabado
        assert classificar_aba("410999", None, contexto="rel1") == "OUTROS"


# ---------------------------------------------------------------------------
# flatten_bom_folhas — agrega folhas da árvore do explodir_bom
# ---------------------------------------------------------------------------
class TestFlattenBomFolhas:
    def test_coleta_folhas_em_multiplos_niveis(self):
        tree = {
            "cod_produto": "A", "qtd_necessaria": 1, "tipo": "ACABADO",
            "componentes": [
                {"cod_produto": "B", "qtd_necessaria": 10, "tipo": "COMPONENTE",
                 "componentes": []},
                {"cod_produto": "C", "qtd_necessaria": 1, "tipo": "INTERMEDIARIO",
                 "componentes": [
                     {"cod_produto": "D", "qtd_necessaria": 5, "tipo": "COMPONENTE",
                      "componentes": []},
                     {"cod_produto": "E", "qtd_necessaria": 7, "tipo": "COMPONENTE",
                      "componentes": []},
                 ]},
            ],
        }
        assert flatten_bom_folhas(tree) == {"B": 10.0, "D": 5.0, "E": 7.0}

    def test_soma_folha_repetida_em_branches_diferentes(self):
        tree = {
            "cod_produto": "A", "qtd_necessaria": 1, "componentes": [
                {"cod_produto": "B", "qtd_necessaria": 10, "componentes": []},
                {"cod_produto": "C", "qtd_necessaria": 1, "componentes": [
                    {"cod_produto": "B", "qtd_necessaria": 4, "componentes": []},
                ]},
            ],
        }
        assert flatten_bom_folhas(tree) == {"B": 14.0}

    def test_ignora_no_tipo_erro(self):
        tree = {
            "cod_produto": "A", "qtd_necessaria": 1, "componentes": [
                {"cod_produto": "B", "qtd_necessaria": 10, "componentes": []},
                {"cod_produto": "X", "qtd_necessaria": 99, "tipo": "ERRO",
                 "componentes": []},
            ],
        }
        assert flatten_bom_folhas(tree) == {"B": 10.0}

    def test_raiz_sem_estrutura_retorna_a_propria_raiz(self):
        # PA sem BOM: a raiz é folha. O CALLER decide rotular "S/ Estrutura"
        # via tem_estrutura — flatten apenas reporta o nó.
        tree = {"cod_produto": "A", "qtd_necessaria": 3, "componentes": []}
        assert flatten_bom_folhas(tree) == {"A": 3.0}


# ---------------------------------------------------------------------------
# simular_producao_pa — buffer de PA absorvendo a venda média
# ---------------------------------------------------------------------------
class TestSimularProducaoPa:
    def test_buffer_parcial_no_mes_que_esgota_depois_cheio(self):
        # estoque 250, venda 100/mês → cobre 2,5 meses
        prod = simular_producao_pa(250, 100)
        assert len(prod) == MESES_HORIZONTE
        assert prod[:5] == [0.0, 0.0, 50.0, 100.0, 100.0]

    def test_sem_estoque_produz_cheio_desde_o_mes_1(self):
        prod = simular_producao_pa(0, 100)
        assert prod == [100.0] * MESES_HORIZONTE

    def test_estoque_cobre_todo_horizonte_produz_zero(self):
        prod = simular_producao_pa(100000, 100)
        assert prod == [0.0] * MESES_HORIZONTE

    def test_venda_zero_nao_produz(self):
        assert simular_producao_pa(0, 0) == [0.0] * MESES_HORIZONTE


# ---------------------------------------------------------------------------
# tempo_estoque_sem_pa — divisão direta estoque/consumo (em dias)
# ---------------------------------------------------------------------------
class TestTempoEstoqueSemPa:
    def test_divisao_direta_em_dias(self):
        # 300 / 200 = 1,5 mês = 45 dias
        assert tempo_estoque_sem_pa(300, 200) == 45.0

    def test_consumo_zero_e_infinito(self):
        assert math.isinf(tempo_estoque_sem_pa(300, 0))


# ---------------------------------------------------------------------------
# tempo_estoque_com_pa — caminhada mês a mês com buffer de PA
# ---------------------------------------------------------------------------
class TestTempoEstoqueComPa:
    def test_exemplo_canonico_do_design(self):
        # estoque comp 300, consumo [0,0,100,200,200,...] → 120 dias
        consumo = [0, 0, 100, 200, 200, 200, 200, 200, 200, 200, 200, 200]
        assert tempo_estoque_com_pa(300, consumo) == 120.0

    def test_meses_cobertos_por_pa_somam_30_dias_gratis(self):
        consumo = [0.0] * MESES_HORIZONTE
        assert tempo_estoque_com_pa(0, consumo) == MESES_HORIZONTE * DIAS_MES

    def test_mes_parcial_divide_proporcional(self):
        # saldo 50 < consumo 200 logo no mês 1 → 30 * (50/200) = 7,5 dias
        assert tempo_estoque_com_pa(50, [200] * MESES_HORIZONTE) == 7.5

    def test_estoque_cobre_horizonte_inteiro_e_capado(self):
        # estoque enorme cobre os 12 meses → cap = 360 dias
        assert tempo_estoque_com_pa(100000, [100] * MESES_HORIZONTE) == MESES_HORIZONTE * DIAS_MES


# ---------------------------------------------------------------------------
# Clamp de estoque negativo (decisão: clampar tempo E produção em 0)
# ---------------------------------------------------------------------------
class TestClampNegativos:
    def test_simular_clampa_estoque_pa_negativo(self):
        # estoque -50 NÃO infla a produção do mês 1 (não vira 150)
        assert simular_producao_pa(-50, 100)[0] == 100.0

    def test_tempo_sem_pa_estoque_negativo_vira_zero(self):
        assert tempo_estoque_sem_pa(-60, 30) == 0.0

    def test_tempo_com_pa_estoque_negativo_vira_zero(self):
        assert tempo_estoque_com_pa(-50, [100] * MESES_HORIZONTE) == 0.0


# ---------------------------------------------------------------------------
# colapsar_por_unificacao — consolida valores sob o código canônico
# ---------------------------------------------------------------------------
class TestColapsarPorUnificacao:
    def test_soma_substituto_no_canonico(self):
        assert colapsar_por_unificacao(
            {"1": 10.0, "2": 5.0, "3": 7.0}, {"2": "1"}
        ) == {"1": 15.0, "3": 7.0}

    def test_sem_unificacao_inalterado(self):
        assert colapsar_por_unificacao({"1": 10.0, "2": 5.0}, {}) == {"1": 10.0, "2": 5.0}

    def test_canonico_preexistente_soma(self):
        assert colapsar_por_unificacao(
            {"100": 3.0, "200": 4.0}, {"200": "100"}
        ) == {"100": 7.0}
