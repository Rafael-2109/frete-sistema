"""TDD do nucleo deterministico de vinculacao NF×PO por NF (FASE 3 fast-path).

Todos os testes mockam os services subjacentes (validar_dfe/consolidar_pos/
reverter_consolidacao) — zero I/O Odoo, zero DB.
"""
from unittest.mock import patch
from app.recebimento.services import vinculacao_rapida_service as svc


class _Val:
    def __init__(self, id, numero_nf, odoo_dfe_id, status):
        self.id = id
        self.numero_nf = numero_nf
        self.odoo_dfe_id = odoo_dfe_id
        self.status = status


def test_nf_nao_encontrada():
    with patch.object(svc, "_buscar_validacoes_por_nf", return_value=[]):
        r = svc.executar_vinculacao_por_nf("99999", "C1", "vincular", usuario="bot")
    assert r["ok"] is False and r["anomalia"]["tipo"] == "nf_nao_encontrada"


def test_nf_ambigua():
    vals = [_Val(1, "6935", 10, "aprovado"), _Val(2, "6935", 11, "aprovado")]
    with patch.object(svc, "_buscar_validacoes_por_nf", return_value=vals):
        r = svc.executar_vinculacao_por_nf("6935", None, "vincular", usuario="bot")
    assert r["ok"] is False and r["anomalia"]["tipo"] == "nf_ambigua"


def test_vincular_status_bloqueado_vira_anomalia():
    val = _Val(1, "52019744", 43946, "bloqueado")
    with patch.object(svc, "_buscar_validacoes_por_nf", return_value=[val]), \
         patch.object(svc, "ValidacaoNfPoService") as MV:
        MV.return_value.validar_dfe.return_value = {
            "status": "bloqueado", "itens_match": 0, "itens_total": 2}
        r = svc.executar_vinculacao_por_nf("52019744", "C2620066", "vincular", usuario="bot")
    assert r["ok"] is False and r["anomalia"]["tipo"] == "status_nao_aprovado"


def test_vincular_po_diverge_vira_anomalia():
    val = _Val(1, "52019744", 43946, "aprovado")
    with patch.object(svc, "_buscar_validacoes_por_nf", return_value=[val]), \
         patch.object(svc, "ValidacaoNfPoService") as MV, \
         patch.object(svc, "montar_pos_para_consolidar",
                      return_value=[{"po_id": 5, "po_name": "C9999999",
                                     "linhas": [], "valor_total": 1}]):
        MV.return_value.validar_dfe.return_value = {"status": "aprovado"}
        r = svc.executar_vinculacao_por_nf("52019744", "C2620066", "vincular", usuario="bot")
    assert r["ok"] is False and r["anomalia"]["tipo"] == "po_diverge"


def test_vincular_caminho_feliz():
    val = _Val(1, "52019744", 43946, "aprovado")
    with patch.object(svc, "_buscar_validacoes_por_nf", return_value=[val]), \
         patch.object(svc, "ValidacaoNfPoService") as MV, \
         patch.object(svc, "OdooPoService") as MO, \
         patch.object(svc, "montar_pos_para_consolidar",
                      return_value=[{"po_id": 5, "po_name": "C2620066",
                                     "linhas": [], "valor_total": 1}]):
        MV.return_value.validar_dfe.return_value = {"status": "aprovado"}
        MO.return_value.consolidar_pos.return_value = {"sucesso": True, "cenario": "exact_1po"}
        r = svc.executar_vinculacao_por_nf("52019744", "c2620066", "vincular", usuario="bot")
    assert r["ok"] is True and r["status"] == "consolidado"
    MO.return_value.consolidar_pos.assert_called_once()


def test_vincular_ja_finalizado_idempotente():
    val = _Val(1, "6935", 44026, "finalizado_odoo")
    with patch.object(svc, "_buscar_validacoes_por_nf", return_value=[val]), \
         patch.object(svc, "ValidacaoNfPoService") as MV:
        MV.return_value.validar_dfe.return_value = {
            "status": "finalizado_odoo", "odoo_po_vinculado_name": "C2620094"}
        r = svc.executar_vinculacao_por_nf("6935", "C2620094", "vincular", usuario="bot")
    assert r["ok"] is True and r["status"] == "finalizado_odoo"


def test_desvincular_caminho_feliz():
    val = _Val(1, "52019744", 43946, "consolidado")
    with patch.object(svc, "_buscar_validacoes_por_nf", return_value=[val]), \
         patch.object(svc, "OdooPoService") as MO:
        MO.return_value.reverter_consolidacao.return_value = {"sucesso": True}
        r = svc.executar_vinculacao_por_nf("52019744", "C2620066", "desvincular", usuario="bot")
    assert r["ok"] is True and r["status"] == "revertido"
    MO.return_value.reverter_consolidacao.assert_called_once()


def test_nunca_levanta_excecao():
    with patch.object(svc, "_buscar_validacoes_por_nf", side_effect=RuntimeError("boom")):
        r = svc.executar_vinculacao_por_nf("1", "C1", "vincular", usuario="bot")
    assert r["ok"] is False and r["anomalia"]["tipo"] == "erro_execucao"


# ─── Retry dirigido (PO informada + bloqueio do match automatico) ──────────
# Diagnostico 2026-06-11: 6/6 interceptacoes da Gabriella cairam em
# status_nao_aprovado (bloqueio por data/dados locais stale) -> N2 Opus caro.
# O retry dirigido re-roda validar_dfe com escopo na(s) PO(s) informada(s),
# dados frescos do Odoo e tolerancia de data (tipo aprovavel por regra
# existente — TIPOS_APROVACAO_PERMITIDA inclui 'data_entrega').

def test_vincular_bloqueado_com_po_informada_faz_retry_dirigido():
    val = _Val(1, "442228", 44240, "bloqueado")
    with patch.object(svc, "_buscar_validacoes_por_nf", return_value=[val]), \
         patch.object(svc, "ValidacaoNfPoService") as MV, \
         patch.object(svc, "OdooPoService") as MO, \
         patch.object(svc, "montar_pos_para_consolidar",
                      return_value=[{"po_id": 5, "po_name": "C2618524",
                                     "linhas": [], "valor_total": 1}]):
        MV.return_value.validar_dfe.side_effect = [
            {"status": "bloqueado", "divergencias": ["sem_po"]},
            {"status": "aprovado"},
        ]
        MO.return_value.consolidar_pos.return_value = {"sucesso": True, "cenario": "exact_1po"}
        r = svc.executar_vinculacao_por_nf("442228", "C2618524", "vincular", usuario="bot")

    assert r["ok"] is True and r["status"] == "consolidado"
    assert MV.return_value.validar_dfe.call_count == 2
    # 2a chamada DEVE ser dirigida: dados frescos + escopo + tolerancia de data
    _, kwargs = MV.return_value.validar_dfe.call_args
    assert kwargs.get("usar_dados_locais") is False
    assert kwargs.get("pos_escopo") == ["C2618524"]
    assert kwargs.get("tolerar_data") is True


def test_vincular_bloqueado_sem_po_nao_faz_retry():
    val = _Val(1, "442228", 44240, "bloqueado")
    with patch.object(svc, "_buscar_validacoes_por_nf", return_value=[val]), \
         patch.object(svc, "ValidacaoNfPoService") as MV:
        MV.return_value.validar_dfe.return_value = {"status": "bloqueado"}
        r = svc.executar_vinculacao_por_nf("442228", None, "vincular", usuario="bot")

    assert r["ok"] is False and r["anomalia"]["tipo"] == "status_nao_aprovado"
    assert MV.return_value.validar_dfe.call_count == 1


def test_vincular_retry_dirigido_ainda_bloqueado_vira_anomalia():
    val = _Val(1, "442228", 44240, "bloqueado")
    with patch.object(svc, "_buscar_validacoes_por_nf", return_value=[val]), \
         patch.object(svc, "ValidacaoNfPoService") as MV:
        MV.return_value.validar_dfe.side_effect = [
            {"status": "bloqueado", "divergencias": ["sem_po"]},
            {"status": "bloqueado", "divergencias": ["preco_diverge"]},
        ]
        r = svc.executar_vinculacao_por_nf("442228", "C2618524", "vincular", usuario="bot")

    assert r["ok"] is False and r["anomalia"]["tipo"] == "status_nao_aprovado"
    assert MV.return_value.validar_dfe.call_count == 2
    # anomalia carrega o resultado do retry (mais rico) para o N2
    assert r["anomalia"]["validacao"]["divergencias"] == ["preco_diverge"]


def test_vincular_multi_po_lista_caminho_feliz():
    """'juntar os pedidos A/B criar conciliador e vincular na nota N' (frase real)."""
    val = _Val(1, "26577", 44310, "bloqueado")
    pos_montadas = [
        {"po_id": 5, "po_name": "C2618497", "linhas": [], "valor_total": 2},
        {"po_id": 6, "po_name": "C2618499", "linhas": [], "valor_total": 1},
    ]
    with patch.object(svc, "_buscar_validacoes_por_nf", return_value=[val]), \
         patch.object(svc, "ValidacaoNfPoService") as MV, \
         patch.object(svc, "OdooPoService") as MO, \
         patch.object(svc, "montar_pos_para_consolidar", return_value=pos_montadas):
        MV.return_value.validar_dfe.side_effect = [
            {"status": "bloqueado"},
            {"status": "aprovado"},
        ]
        MO.return_value.consolidar_pos.return_value = {"sucesso": True, "cenario": "n_pos"}
        r = svc.executar_vinculacao_por_nf(
            "26577", ["C2618497", "c2618499"], "vincular", usuario="bot")

    assert r["ok"] is True and r["status"] == "consolidado"
    _, kwargs = MV.return_value.validar_dfe.call_args
    assert kwargs.get("pos_escopo") == ["C2618497", "C2618499"]


def test_vincular_multi_po_faltando_uma_vira_po_diverge():
    """PO informada que nao contribuiu com match -> conservador, N2 decide."""
    val = _Val(1, "26577", 44310, "aprovado")
    with patch.object(svc, "_buscar_validacoes_por_nf", return_value=[val]), \
         patch.object(svc, "ValidacaoNfPoService") as MV, \
         patch.object(svc, "montar_pos_para_consolidar",
                      return_value=[{"po_id": 5, "po_name": "C2618497",
                                     "linhas": [], "valor_total": 1}]):
        MV.return_value.validar_dfe.return_value = {"status": "aprovado"}
        r = svc.executar_vinculacao_por_nf(
            "26577", ["C2618497", "C2618499"], "vincular", usuario="bot")

    assert r["ok"] is False and r["anomalia"]["tipo"] == "po_diverge"
