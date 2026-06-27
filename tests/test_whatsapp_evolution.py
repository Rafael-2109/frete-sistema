"""Testa o envio de mídia (anexo PDF) via Evolution API — sem rede (mocka requests.post).

Paridade com o anexo do OpenClaw (`send_whatsapp` com buffer/mimeType): a Evolution
usa o endpoint POST /message/sendMedia/{instance} com mediatype=document.
"""
import json
from unittest.mock import patch, MagicMock

import app.utils.whatsapp_evolution as we


def _fake_resp(status=201, body=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = body if body is not None else {"key": {"id": "ABC123"}}
    r.text = json.dumps(r.json.return_value)
    return r


def _config(monkeypatch):
    monkeypatch.setattr(we, "_API_URL", "https://evo.example.com")
    monkeypatch.setattr(we, "_API_KEY", "apikey123")
    monkeypatch.setattr(we, "_INSTANCE", "hora")
    monkeypatch.setattr(we, "_ENABLED", True)


def test_send_media_evolution_monta_payload_document(monkeypatch):
    _config(monkeypatch)
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _fake_resp()

    with patch.object(we.requests, "post", side_effect=fake_post):
        we.send_media_evolution(
            "120363@g.us",
            "Segue a NF",
            anexo_b64="JVBERi0xLjQK",
            anexo_filename="danfe_3706.pdf",
            skip_rate_limit=True,
        )

    assert captured["url"] == "https://evo.example.com/message/sendMedia/hora"
    assert captured["headers"]["apikey"] == "apikey123"
    body = captured["json"]
    assert body["number"] == "120363@g.us"  # grupo: JID mantido
    assert body["mediatype"] == "document"
    assert body["mimetype"] == "application/pdf"
    assert body["media"] == "JVBERi0xLjQK"
    assert body["fileName"] == "danfe_3706.pdf"
    assert body["caption"] == "Segue a NF"


def test_send_media_evolution_dm_normaliza_numero(monkeypatch):
    _config(monkeypatch)
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["json"] = json
        return _fake_resp()

    with patch.object(we.requests, "post", side_effect=fake_post):
        we.send_media_evolution(
            "+55 (11) 99164-2998",
            "Recibo",
            anexo_b64="JVBERi0xLjQK",
            anexo_filename="r.pdf",
            skip_rate_limit=True,
        )

    assert captured["json"]["number"] == "5511991642998"  # DM: só dígitos


def test_send_media_evolution_sem_config_levanta_erro(monkeypatch):
    monkeypatch.setattr(we, "_API_URL", "")
    monkeypatch.setattr(we, "_API_KEY", "")
    monkeypatch.setattr(we, "_INSTANCE", "")
    monkeypatch.setattr(we, "_ENABLED", True)

    import pytest
    with pytest.raises(we.WhatsAppNotifyError):
        we.send_media_evolution(
            "120363@g.us", "x", anexo_b64="AAAA", anexo_filename="a.pdf",
            skip_rate_limit=True,
        )


def test_send_media_evolution_anexo_vazio_levanta_erro(monkeypatch):
    _config(monkeypatch)
    import pytest
    with pytest.raises(we.WhatsAppNotifyError):
        we.send_media_evolution(
            "120363@g.us", "x", anexo_b64="", anexo_filename="a.pdf",
            skip_rate_limit=True,
        )


def test_send_media_evolution_auth_401(monkeypatch):
    _config(monkeypatch)

    def fake_post(url, json=None, headers=None, timeout=None):
        return _fake_resp(status=401, body={"error": "unauthorized"})

    import pytest
    with patch.object(we.requests, "post", side_effect=fake_post):
        with pytest.raises(we.WhatsAppAuthError):
            we.send_media_evolution(
                "120363@g.us", "x", anexo_b64="AAAA", anexo_filename="a.pdf",
                skip_rate_limit=True,
            )


def test_fetch_grupos_evolution_lista(monkeypatch):
    _config(monkeypatch)

    def fake_get(url, headers=None, params=None, timeout=None):
        assert url == "https://evo.example.com/group/fetchAllGroups/hora"
        assert headers["apikey"] == "apikey123"
        m = MagicMock()
        m.status_code = 200
        m.json.return_value = [
            {"id": "120@g.us", "subject": "Loja Centro", "size": 5},
            {"id": "121@g.us", "subject": "Loja Norte"},
            {"subject": "sem id — deve ser ignorado"},
        ]
        return m

    with patch.object(we.requests, "get", side_effect=fake_get):
        grupos = we.fetch_grupos_evolution()

    assert grupos == [
        {"id": "120@g.us", "subject": "Loja Centro"},
        {"id": "121@g.us", "subject": "Loja Norte"},
    ]


def test_fetch_grupos_evolution_sem_config(monkeypatch):
    monkeypatch.setattr(we, "_API_URL", "")
    monkeypatch.setattr(we, "_API_KEY", "")
    monkeypatch.setattr(we, "_INSTANCE", "")
    import pytest
    with pytest.raises(we.WhatsAppNotifyError):
        we.fetch_grupos_evolution()


def test_fetch_grupos_evolution_auth_401(monkeypatch):
    _config(monkeypatch)

    def fake_get(url, headers=None, params=None, timeout=None):
        m = MagicMock()
        m.status_code = 401
        m.text = "unauthorized"
        return m

    import pytest
    with patch.object(we.requests, "get", side_effect=fake_get):
        with pytest.raises(we.WhatsAppAuthError):
            we.fetch_grupos_evolution()


def test_send_media_evolution_desabilitado_skipa(monkeypatch):
    _config(monkeypatch)
    monkeypatch.setattr(we, "_ENABLED", False)

    def fake_post(url, json=None, headers=None, timeout=None):
        raise AssertionError("nao deveria chamar a rede quando desabilitado")

    with patch.object(we.requests, "post", side_effect=fake_post):
        res = we.send_media_evolution(
            "120363@g.us", "x", anexo_b64="AAAA", anexo_filename="a.pdf",
            skip_rate_limit=True,
        )
    assert res.get("ok") is False and res.get("skipped") is True
