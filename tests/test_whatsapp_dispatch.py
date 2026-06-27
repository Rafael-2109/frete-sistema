"""Testa o dispatcher transport-aware do envio WhatsApp (OpenClaw vs Evolution).

O dispatcher e o ponto unico que o HORA usa: roteia por transporte (env
HORA_WHATSAPP_TRANSPORT) e por presenca de anexo (texto vs documento), sem
acoplar os call-sites a um gateway especifico.
"""
import pytest

import app.utils.whatsapp_dispatch as wd


def _spy(monkeypatch, nome):
    chamadas = {}

    def fake(*args, **kwargs):
        chamadas["args"] = args
        chamadas["kwargs"] = kwargs
        return {"ok": True, "via": nome}

    monkeypatch.setattr(wd, nome, fake)
    return chamadas


def test_evolution_com_anexo_usa_send_media(monkeypatch):
    media = _spy(monkeypatch, "send_media_evolution")
    _spy(monkeypatch, "send_whatsapp_evolution")
    _spy(monkeypatch, "send_whatsapp")

    res = wd.send_whatsapp_unificado(
        "120363@g.us", "Segue NF",
        anexo_b64="JVBERi0x", anexo_filename="danfe.pdf",
        transport="evolution", skip_rate_limit=True,
    )

    assert res["via"] == "send_media_evolution"
    assert media["args"][0] == "120363@g.us"
    assert media["kwargs"]["anexo_b64"] == "JVBERi0x"
    assert media["kwargs"]["anexo_filename"] == "danfe.pdf"


def test_evolution_sem_anexo_usa_send_text(monkeypatch):
    _spy(monkeypatch, "send_media_evolution")
    texto = _spy(monkeypatch, "send_whatsapp_evolution")
    _spy(monkeypatch, "send_whatsapp")

    res = wd.send_whatsapp_unificado(
        "120363@g.us", "Pedido confirmado",
        transport="evolution", skip_rate_limit=True,
    )

    assert res["via"] == "send_whatsapp_evolution"
    assert texto["args"][0] == "120363@g.us"
    assert texto["args"][1] == "Pedido confirmado"


def test_openclaw_com_anexo_usa_send_whatsapp(monkeypatch):
    _spy(monkeypatch, "send_media_evolution")
    _spy(monkeypatch, "send_whatsapp_evolution")
    oc = _spy(monkeypatch, "send_whatsapp")

    res = wd.send_whatsapp_unificado(
        "120363@g.us", "Segue NF",
        anexo_b64="JVBERi0x", anexo_filename="danfe.pdf",
        transport="openclaw", skip_rate_limit=True,
    )

    assert res["via"] == "send_whatsapp"
    assert oc["kwargs"]["anexo_b64"] == "JVBERi0x"
    assert oc["kwargs"]["anexo_filename"] == "danfe.pdf"


def test_transport_none_le_env(monkeypatch):
    monkeypatch.setenv("HORA_WHATSAPP_TRANSPORT", "evolution")
    media = _spy(monkeypatch, "send_media_evolution")
    _spy(monkeypatch, "send_whatsapp_evolution")
    _spy(monkeypatch, "send_whatsapp")

    res = wd.send_whatsapp_unificado(
        "120363@g.us", "x", anexo_b64="AA", anexo_filename="a.pdf",
        skip_rate_limit=True,
    )
    assert res["via"] == "send_media_evolution"
    assert media["kwargs"]["anexo_filename"] == "a.pdf"


def test_transport_default_openclaw_quando_env_ausente(monkeypatch):
    monkeypatch.delenv("HORA_WHATSAPP_TRANSPORT", raising=False)
    _spy(monkeypatch, "send_media_evolution")
    _spy(monkeypatch, "send_whatsapp_evolution")
    oc = _spy(monkeypatch, "send_whatsapp")

    res = wd.send_whatsapp_unificado("120363@g.us", "oi", skip_rate_limit=True)
    assert res["via"] == "send_whatsapp"
    assert oc["args"][0] == "120363@g.us"


def test_transport_desconhecido_levanta_erro(monkeypatch):
    with pytest.raises(wd.WhatsAppNotifyError):
        wd.send_whatsapp_unificado(
            "120363@g.us", "x", transport="telegram", skip_rate_limit=True,
        )
