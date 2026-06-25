from datetime import date
import io
import pandas as pd
from app.manufatura.services import estoque_semanal_service as svc


def test_gerar_planilha_bytes_tem_abas_e_rotulos():
    abas = {
        "Insumos": [{
            "cod_produto": "1001", "nome_produto": "Palmito", "categoria": "Insumo",
            "estoque_seg_anterior": 1000.0, "entradas": 800.0, "consumos": 750.0,
            "outros_ajustes": 0.0, "estoque_seg_atual": 1050.0,
        }],
        "Embalagens": [], "Produto_Acabado": [], "Outros": [],
    }
    conteudo = svc.gerar_planilha_bytes(abas, date(2026, 6, 15), date(2026, 6, 22))
    assert isinstance(conteudo, bytes) and len(conteudo) > 0
    xls = pd.ExcelFile(io.BytesIO(conteudo))
    assert "Insumos" in xls.sheet_names
    df = pd.read_excel(xls, "Insumos")
    # rótulo do componente menciona "compra" e "produção"
    cols = " | ".join(df.columns)
    assert "compra" in cols.lower()
    assert "produ" in cols.lower()
    assert df.iloc[0]["Cód"] == 1001 or str(df.iloc[0]["Cód"]) == "1001"


def test_enviar_dry_run_nao_envia(monkeypatch):
    # Injeta dados sem tocar o banco
    monkeypatch.setattr(svc, "montar_relatorio_semanal",
                        lambda: ({"Insumos": [], "Embalagens": [],
                                  "Produto_Acabado": [], "Outros": []},
                                 date(2026, 6, 15), date(2026, 6, 22)))
    chamou = {"send": False}
    def _nao_chamar(*a, **k):
        chamou["send"] = True
    monkeypatch.setattr(svc.EmailSender, "send", _nao_chamar)
    res = svc.enviar_estoque_semanal_email(dry_run=True)
    assert res["ok"] is True
    assert res["motivo"] == "dry_run"
    assert chamou["send"] is False


def test_enviar_sem_destinatario_retorna_erro(monkeypatch):
    monkeypatch.setattr(svc, "montar_relatorio_semanal",
                        lambda: ({"Insumos": [], "Embalagens": [],
                                  "Produto_Acabado": [], "Outros": []},
                                 date(2026, 6, 15), date(2026, 6, 22)))
    monkeypatch.setenv("ESTOQUE_SEMANAL_EMAIL_TO", "")
    res = svc.enviar_estoque_semanal_email(dry_run=False)
    assert res["ok"] is False
    assert res["motivo"] == "sem_destinatario"
