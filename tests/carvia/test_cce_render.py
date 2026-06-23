"""Render de CCe (PDF/imagem -> PNG base64) p/ impressao — C1 do plano."""
import base64


def test_render_imagem_embute_direto(db, monkeypatch):
    from app.carvia.services.documentos import cce_render

    class _Carta:
        id = 1
        descricao = 'x'
        content_type = 'image/png'
        nome_original = 'cce.png'
        caminho_s3 = 'carvia/cartas_correcao/cce.png'

    png_1px = base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
    monkeypatch.setattr(cce_render, '_baixar_bytes', lambda p: png_1px)

    out = cce_render.render_cces_para_impressao([(_Carta(), None)])
    assert len(out) == 1
    assert out[0]['carta_id'] == 1
    assert len(out[0]['paginas']) == 1
    base64.b64decode(out[0]['paginas'][0])  # base64 valido


def test_render_lista_vazia(db):
    from app.carvia.services.documentos import cce_render
    assert cce_render.render_cces_para_impressao([]) == []
