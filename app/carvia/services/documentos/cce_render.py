"""Render de Cartas de Correção (CCe) para impressão embutida.

Converte cada CCe (PDF -> imagem por página via pypdfium2; imagem -> embute
direto) em PNG base64, para sair como página(s) no HTML que window.print()
imprime (capa do embarque, detalhe da NF, monitoramento). Padrão pypdfium2
espelha app/financeiro/leitor_comprovantes_sicoob.py:244.
"""
import base64
import io
import logging

logger = logging.getLogger(__name__)

_ESCALA_PDF = 2.5  # nitidez razoavel sem estourar memoria


def _baixar_bytes(caminho_s3):
    from app.utils.file_storage import get_file_storage
    return get_file_storage().download_file(caminho_s3)


def _png_base64(pil_image):
    buf = io.BytesIO()
    pil_image.convert('RGB').save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode('ascii')


def _paginas_de_pdf(pdf_bytes):
    import pypdfium2 as pdfium
    paginas = []
    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        for i in range(len(pdf)):
            bitmap = pdf[i].render(scale=_ESCALA_PDF)
            paginas.append(_png_base64(bitmap.to_pil()))
    finally:
        pdf.close()
    return paginas


def render_cces_para_impressao(cces):
    """cces = lista de pares (carta, vinculo) (saida de listar). Retorna
    list[{'carta_id', 'descricao', 'paginas': [png_base64,...]}]."""
    from PIL import Image

    resultado = []
    for carta, _vinc in (cces or []):
        try:
            dados = _baixar_bytes(carta.caminho_s3)
            if not dados:
                logger.warning("CCe #%s sem bytes no storage (%s)",
                               carta.id, carta.caminho_s3)
                continue
            ct = (carta.content_type or '').lower()
            nome = (carta.nome_original or '').lower()
            eh_pdf = 'pdf' in ct or nome.endswith('.pdf')
            if eh_pdf:
                paginas = _paginas_de_pdf(dados)
            else:
                paginas = [_png_base64(Image.open(io.BytesIO(dados)))]
            if paginas:
                resultado.append({
                    'carta_id': carta.id,
                    'descricao': carta.descricao,
                    'paginas': paginas,
                })
        except Exception as e:  # noqa: BLE001
            logger.error("Falha ao renderizar CCe #%s: %s",
                         getattr(carta, 'id', '?'), e)
    return resultado
