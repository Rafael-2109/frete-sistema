"""Testes da geração de documentos do Pedido de Venda (PDV + termos).

Cobre:
  - titulo_pdv por status (Cotação vs Pedido de Venda).
  - classificação de ciclomotor (modelo.autopropelido is False).
  - geração real dos 4 PDFs (exercita os templates com dados reais).
  - critério de status do pacote (COTACAO = só PDV; CONFIRMADO = + termos).
  - guarda do termo ciclomotor (erro quando nenhuma moto é ciclomotor).
  - emitente de fallback (matriz) quando a venda não tem loja.

PDF gerado de verdade (weasyprint) — o foco é não quebrar o template e respeitar
os critérios. Mantém 1 moto por venda para o custo de render ficar baixo.
"""
import uuid
from decimal import Decimal
from io import BytesIO

import pytest

from app import db as _db
from app.hora.models import HoraMoto, HoraModelo, HoraVenda, HoraVendaItem
from app.hora.services import documento_venda_service as docsvc
from app.utils.timezone import agora_utc_naive


def _modelo(autopropelido=True, potencia=None):
    m = HoraModelo(
        nome_modelo=f'MODEL-{uuid.uuid4().hex[:8].upper()}',
        ativo=True, autopropelido=autopropelido, potencia_motor=potencia,
    )
    _db.session.add(m)
    _db.session.flush()
    return m


def _venda_com_moto(loja, modelo, status='COTACAO'):
    chassi = f'DOC{uuid.uuid4().hex[:12].upper()}'
    moto = HoraMoto(numero_chassi=chassi, modelo_id=modelo.id, cor='PRETA')
    _db.session.add(moto)
    v = HoraVenda(
        loja_id=loja.id if loja else None,
        cpf_cliente='12345678909', nome_cliente='Cliente Teste',
        valor_total=Decimal('1000'), status=status,
        data_venda=agora_utc_naive().date(), origem_criacao='MANUAL',
    )
    _db.session.add(v)
    _db.session.flush()
    it = HoraVendaItem(
        venda_id=v.id, numero_chassi=chassi,
        preco_tabela_referencia=Decimal('1000'), desconto_aplicado=Decimal('0'),
        desconto_percentual=Decimal('0'), preco_final=Decimal('1000'),
    )
    _db.session.add(it)
    _db.session.flush()
    return v


def _n_paginas(blob: bytes) -> int:
    from pypdf import PdfReader
    return len(PdfReader(BytesIO(blob)).pages)


# --------------------------------------------------------------------------
# Lógica pura (título, classificação)
# --------------------------------------------------------------------------
@pytest.mark.parametrize('status,esperado', [
    ('INCOMPLETO', 'Cotação'),
    ('COTACAO', 'Cotação'),
    ('CONFIRMADO', 'Pedido de Venda'),
    ('FATURADO', 'Pedido de Venda'),
])
def test_titulo_pdv_por_status(db, loja_factory, status, esperado):
    v = _venda_com_moto(loja_factory(), _modelo(), status=status)
    assert docsvc.titulo_pdv(v) == esperado


def test_tem_ciclomotor_classifica_por_autopropelido(db, loja_factory):
    v_auto = _venda_com_moto(loja_factory(), _modelo(autopropelido=True))
    v_ciclo = _venda_com_moto(loja_factory(), _modelo(autopropelido=False))
    assert docsvc.tem_ciclomotor(v_auto) is False
    assert docsvc.tem_ciclomotor(v_ciclo) is True
    assert len(docsvc.itens_ciclomotor(v_ciclo)) == 1
    assert docsvc.itens_ciclomotor(v_auto) == []


# --------------------------------------------------------------------------
# Geração dos PDFs (templates reais)
# --------------------------------------------------------------------------
def test_gerar_pdv_pdf_valido(db, loja_factory):
    v = _venda_com_moto(loja_factory(), _modelo(), status='CONFIRMADO')
    blob = docsvc.gerar_pdv_pdf(v)
    assert blob[:4] == b'%PDF'
    assert _n_paginas(blob) >= 1


def test_gerar_termo_garantia_e_checagem(db, loja_factory):
    v = _venda_com_moto(loja_factory(), _modelo(potencia='1000W'), status='CONFIRMADO')
    g = docsvc.gerar_termo_garantia_pdf(v)
    c = docsvc.gerar_termo_checagem_pdf(v)
    assert g[:4] == b'%PDF' and _n_paginas(g) >= 4  # termo longo (multi-página)
    assert c[:4] == b'%PDF' and _n_paginas(c) == 1


def test_termo_ciclomotor_guarda_e_geracao(db, loja_factory):
    # Sem ciclomotor -> erro de negócio.
    v_auto = _venda_com_moto(loja_factory(), _modelo(autopropelido=True))
    with pytest.raises(docsvc.DocumentoVendaError, match='ciclomotor'):
        docsvc.gerar_termo_ciclomotor_pdf(v_auto)
    # Com ciclomotor -> PDF válido.
    v_ciclo = _venda_com_moto(loja_factory(), _modelo(autopropelido=False), status='CONFIRMADO')
    blob = docsvc.gerar_termo_ciclomotor_pdf(v_ciclo)
    assert blob[:4] == b'%PDF'


@pytest.mark.parametrize('status', ['INCOMPLETO', 'COTACAO'])
def test_termos_bloqueados_antes_de_confirmar(db, loja_factory, status):
    """Defesa em profundidade: garantia/checagem só geram em CONFIRMADO/FATURADO,
    mesmo via URL direta (o dropdown desabilita o link, mas a rota é acessível)."""
    v = _venda_com_moto(loja_factory(), _modelo(), status=status)
    with pytest.raises(docsvc.DocumentoVendaError, match='Confirmados ou Faturados'):
        docsvc.gerar_termo_garantia_pdf(v)
    with pytest.raises(docsvc.DocumentoVendaError, match='Confirmados ou Faturados'):
        docsvc.gerar_termo_checagem_pdf(v)


def test_pacote_respeita_status(db, loja_factory):
    """COTACAO empacota só o PDV; CONFIRMADO acrescenta os termos (mais páginas)."""
    modelo = _modelo()
    v_cot = _venda_com_moto(loja_factory(), modelo, status='COTACAO')
    v_conf = _venda_com_moto(loja_factory(), modelo, status='CONFIRMADO')
    pag_cot = docsvc.gerar_pacote_pdf(v_cot)
    pag_conf = docsvc.gerar_pacote_pdf(v_conf)
    # COTACAO = só o PDV (1 página); CONFIRMADO = PDV + garantia + checagem.
    assert _n_paginas(pag_cot) == _n_paginas(docsvc.gerar_pdv_pdf(v_cot))
    assert _n_paginas(pag_conf) > _n_paginas(pag_cot)


def test_pacote_confirmado_inclui_ciclomotor(db, loja_factory):
    """Pacote CONFIRMADO com moto ciclomotor é maior que sem (inclui o termo extra)."""
    loja = loja_factory()
    v_auto = _venda_com_moto(loja, _modelo(autopropelido=True), status='CONFIRMADO')
    v_ciclo = _venda_com_moto(loja, _modelo(autopropelido=False), status='CONFIRMADO')
    assert _n_paginas(docsvc.gerar_pacote_pdf(v_ciclo)) > _n_paginas(docsvc.gerar_pacote_pdf(v_auto))


def test_emitente_matriz_fixa_e_vendido_por(db, loja_factory):
    """Emitente é sempre a matriz (razão/CNPJ/e-mail fixos); a loja física da venda
    aparece só como `vendido_por` (nome, sem CNPJ)."""
    loja = loja_factory()
    v = _venda_com_moto(loja, _modelo(), status='CONFIRMADO')
    emit = docsvc._emitente(v)
    assert emit['razao_social'] == docsvc.EMITENTE_MATRIZ['razao_social']
    assert emit['cnpj'] == docsvc.EMITENTE_MATRIZ['cnpj']
    assert emit['email'] == docsvc.EMITENTE_MATRIZ['email']
    assert emit['vendido_por'] == loja.rotulo_display
    # Sem loja, vendido_por é None e o PDV ainda gera normalmente.
    v_sem = _venda_com_moto(None, _modelo(), status='CONFIRMADO')
    assert docsvc._emitente(v_sem)['vendido_por'] is None
    assert docsvc.gerar_pdv_pdf(v_sem)[:4] == b'%PDF'
