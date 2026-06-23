"""Regressao: upload em lote de NF Q.P.A. nao pode perder arquivos quando um
deles levanta excecao INESPERADA (data loss silencioso).

Antes: o loop em faturamento.py so capturava NfQpaJaImportadaError e
NfQpaParseError; qualquer outra excecao (IntegrityError, decimal, anthropic,
AttributeError...) abortava o lote e os arquivos restantes sumiam sem
relatorio. Como importar_nf_qpa commita POR ARQUIVO, os ja processados
ficavam e os demais desapareciam (ex.: 10 PDFs -> 4 entram, 6 somem).
"""
from io import BytesIO
from unittest.mock import MagicMock, patch


def _pdf(nome):
    return (BytesIO(b'%PDF-1.4 fake'), nome)


@patch('app.motos_assai.routes.faturamento.importar_nf_qpa')
def test_upload_lote_excecao_inesperada_nao_perde_arquivos(mock_importar, login_admin):
    # Simula o handler de producao (excecao -> 500), em vez de propagar no
    # test client.
    login_admin.application.config['PROPAGATE_EXCEPTIONS'] = False

    nf_ok = MagicMock()
    nf_ok.status_match = 'NAO_RECONCILIADO'
    nf_ok.id = 1
    nf_ok.numero = '1'
    # arquivo 1 ok, arquivo 2 estoura, arquivo 3 ok -> NAO pode abortar:
    # os 3 devem aparecer no relatorio e o 3o tem que ser processado.
    mock_importar.side_effect = [
        nf_ok,
        RuntimeError('erro inesperado de banco'),
        nf_ok,
    ]

    data = {'pdfs': [_pdf('nf1.pdf'), _pdf('nf2.pdf'), _pdf('nf3.pdf')]}
    r = login_admin.post('/motos-assai/faturamento/upload-nf',
                         data=data, content_type='multipart/form-data')

    # Nao aborta (sem 500) e processou os 3 arquivos
    assert r.status_code == 200
    assert mock_importar.call_count == 3  # continuou ate o 3o apos a falha
    html = r.get_data(as_text=True)
    assert 'nf3.pdf' in html                    # arquivo apos a falha aparece
    assert 'erro inesperado de banco' in html   # a falha vira linha visivel
