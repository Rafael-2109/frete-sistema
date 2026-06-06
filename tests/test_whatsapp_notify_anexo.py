# tests/integracoes/tagplus/test_send_whatsapp_anexo.py
"""Testa o anexo base64 no send_whatsapp (sem rede — mocka requests.post)."""
import json
from unittest.mock import patch, MagicMock

import app.utils.whatsapp_notify as wn


def _fake_resp(ok=True):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = {"ok": ok, "result": {}}
    return r


def test_send_whatsapp_sem_anexo_mantem_args_atuais(monkeypatch):
    monkeypatch.setattr(wn, "_GATEWAY_TOKEN", "tok")
    monkeypatch.setattr(wn, "_ENABLED", True)
    captured = {}

    def fake_post(url, data=None, headers=None, timeout=None):
        captured["body"] = json.loads(data.decode())
        return _fake_resp()

    with patch.object(wn.requests, "post", side_effect=fake_post):
        wn.send_whatsapp("120363@g.us", "Oi", skip_rate_limit=True)

    args = captured["body"]["args"]
    assert args["action"] == "send"
    assert args["channel"] == "whatsapp"
    assert args["target"] == "120363@g.us"
    assert args["message"] == "Oi"
    assert "buffer" not in args


def test_send_whatsapp_com_anexo_monta_buffer(monkeypatch):
    monkeypatch.setattr(wn, "_GATEWAY_TOKEN", "tok")
    monkeypatch.setattr(wn, "_ENABLED", True)
    captured = {}

    def fake_post(url, data=None, headers=None, timeout=None):
        captured["body"] = json.loads(data.decode())
        return _fake_resp()

    with patch.object(wn.requests, "post", side_effect=fake_post):
        wn.send_whatsapp(
            "120363@g.us",
            "Segue a NF",
            skip_rate_limit=True,
            anexo_b64="JVBERi0xLjQK",
            anexo_filename="danfe_3706.pdf",
            anexo_mimetype="application/pdf",
        )

    args = captured["body"]["args"]
    assert args["buffer"] == "JVBERi0xLjQK"
    assert args["filename"] == "danfe_3706.pdf"
    assert args["mimeType"] == "application/pdf"
    assert args["caption"] == "Segue a NF"
    assert args["message"] == "Segue a NF"
