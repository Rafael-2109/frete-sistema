from datetime import date
from app.manufatura.services.estoque_semanal_calc import (
    semanas_referencia, classificar_movimento, montar_abas,
)


def test_semanas_referencia_normaliza_para_segunda():
    # Quarta 25/06/2026 -> seg_atual = 22/06, seg_anterior = 15/06
    seg_ant, seg_atual = semanas_referencia(date(2026, 6, 25))
    assert seg_atual == date(2026, 6, 22)
    assert seg_ant == date(2026, 6, 15)


def test_semanas_referencia_em_segunda():
    seg_ant, seg_atual = semanas_referencia(date(2026, 6, 22))
    assert seg_atual == date(2026, 6, 22)
    assert seg_ant == date(2026, 6, 15)


def test_classificar_movimento_componente():
    assert classificar_movimento("INSUMOS", "ENTRADA", "COMPRA") == "ENTRADA"
    assert classificar_movimento("EMBALAGENS", "CONSUMO", "PRODUCAO") == "CONSUMO"
    assert classificar_movimento("INSUMOS", "AJUSTE", "AJUSTE") == "OUTRO"
    # venda de insumo não é o "consumo" do grupo -> OUTRO
    assert classificar_movimento("INSUMOS", "SAIDA", "VENDA") == "OUTRO"


def test_classificar_movimento_produto_acabado():
    assert classificar_movimento("PRODUTO_ACABADO", "PRODUÇÃO", "PRODUCAO") == "ENTRADA"
    assert classificar_movimento("PRODUTO_ACABADO", "PRODUCAO", "PRODUCAO") == "ENTRADA"
    assert classificar_movimento("PRODUTO_ACABADO", "SAIDA", "VENDA") == "CONSUMO"
    assert classificar_movimento("PRODUTO_ACABADO", "ENTRADA", "DEVOLUCAO") == "OUTRO"


def test_montar_abas_fecha_a_conta_e_classifica():
    cadastro = {
        "1001": {"nome_produto": "Palmito granel", "tipo_materia_prima": "", "categoria": "Insumo", "embalagem": ""},
        "2001": {"nome_produto": "Tampa", "tipo_materia_prima": "", "categoria": "", "embalagem": "Tampa"},
        "4001": {"nome_produto": "Conserva 300g", "tipo_materia_prima": "", "categoria": "PA", "embalagem": ""},
    }
    estoque0 = {"1001": 1000.0, "2001": 5000.0, "4001": 200.0}
    estoque_hoje = {"1001": 1050.0, "2001": 5000.0, "4001": 150.0}
    # (cod, tipo, local, soma_qtd) — soma já com sinal
    movimentos = [
        ("1001", "ENTRADA", "COMPRA", 800.0),     # entrada insumo
        ("1001", "CONSUMO", "PRODUCAO", -750.0),   # consumo insumo
        ("2001", "ENTRADA", "COMPRA", 2000.0),
        ("2001", "CONSUMO", "PRODUCAO", -1800.0),
        ("2001", "AJUSTE", "AJUSTE", -200.0),      # outros
        ("4001", "PRODUÇÃO", "PRODUCAO", 100.0),   # entrada PA = produção
        ("4001", "SAIDA", "VENDA", -150.0),        # saída PA = venda
    ]
    abas = montar_abas(estoque0, estoque_hoje, movimentos, cadastro, {})

    insumo = next(l for l in abas["Insumos"] if l["cod_produto"] == "1001")
    assert insumo["estoque_seg_anterior"] == 1000.0
    assert insumo["entradas"] == 800.0
    assert insumo["consumos"] == 750.0          # exibido positivo
    assert insumo["outros_ajustes"] == 0.0
    assert insumo["estoque_seg_atual"] == 1050.0
    # fechamento: 1000 + 800 - 750 + 0 == 1050
    assert (insumo["estoque_seg_anterior"] + insumo["entradas"]
            - insumo["consumos"] + insumo["outros_ajustes"]
            == insumo["estoque_seg_atual"])

    emb = next(l for l in abas["Embalagens"] if l["cod_produto"] == "2001")
    assert emb["outros_ajustes"] == -200.0       # ajuste cai em outros
    assert (emb["estoque_seg_anterior"] + emb["entradas"]
            - emb["consumos"] + emb["outros_ajustes"] == emb["estoque_seg_atual"])

    pa = next(l for l in abas["Produto_Acabado"] if l["cod_produto"] == "4001")
    assert pa["entradas"] == 100.0               # produção
    assert pa["consumos"] == 150.0               # venda, exibida positiva
    assert (pa["estoque_seg_anterior"] + pa["entradas"]
            - pa["consumos"] + pa["outros_ajustes"] == pa["estoque_seg_atual"])


def test_montar_abas_ignora_produto_zerado_sem_movimento():
    cadastro = {"1001": {"nome_produto": "X", "tipo_materia_prima": "", "categoria": "", "embalagem": ""}}
    abas = montar_abas({"1001": 0.0}, {"1001": 0.0}, [], cadastro, {})
    assert abas["Insumos"] == []


def test_montar_abas_exibe_estoque_negativo_sem_piso():
    cadastro = {"1001": {"nome_produto": "X", "tipo_materia_prima": "", "categoria": "", "embalagem": ""}}
    abas = montar_abas({"1001": -50.0}, {"1001": -30.0},
                       [("1001", "ENTRADA", "COMPRA", 20.0)], cadastro, {})
    linha = abas["Insumos"][0]
    assert linha["estoque_seg_anterior"] == -50.0
    assert linha["estoque_seg_atual"] == -30.0


def test_montar_abas_colapsa_por_unificacao():
    cadastro = {
        "1001": {"nome_produto": "Palmito", "tipo_materia_prima": "", "categoria": "Insumo", "embalagem": ""},
        "1002": {"nome_produto": "Palmito (substituto)", "tipo_materia_prima": "", "categoria": "Insumo", "embalagem": ""},
    }
    estoque0 = {"1001": 600.0, "1002": 400.0}      # -> 1000 no canônico
    estoque_hoje = {"1001": 600.0, "1002": 450.0}  # -> 1050
    movimentos = [("1002", "ENTRADA", "COMPRA", 50.0)]
    mapa_unif = {"1002": "1001"}
    abas = montar_abas(estoque0, estoque_hoje, movimentos, cadastro, mapa_unif)
    insumos = abas["Insumos"]
    assert len(insumos) == 1
    linha = insumos[0]
    assert linha["cod_produto"] == "1001"
    assert linha["estoque_seg_anterior"] == 1000.0
    assert linha["estoque_seg_atual"] == 1050.0
    assert linha["entradas"] == 50.0
    assert (linha["estoque_seg_anterior"] + linha["entradas"]
            - linha["consumos"] + linha["outros_ajustes"] == linha["estoque_seg_atual"])
