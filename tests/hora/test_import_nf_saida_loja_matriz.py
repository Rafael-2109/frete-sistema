"""TDD: import de NF de saida (DANFE) com emitente = matriz nao grava loja_id=matriz.

Toda NFe sai com o CNPJ da matriz (invariante CLAUDE.md secao 7). O import NAO
pode atribuir a venda a matriz: deve gravar loja_id=NULL + divergencia
CNPJ_DESCONHECIDO (loja a definir), e o evento VENDIDA tambem com loja_id=NULL.
"""
import uuid
from datetime import date

from app import db as _db
from app.hora.models import (
    HoraLoja, HoraMoto, HoraMotoEvento, HoraVenda, HoraVendaDivergencia,
)
from app.hora.services import venda_service
from app.hora.services.moto_service import get_or_create_moto, registrar_evento
from app.utils.timezone import agora_utc_naive


def _cnpj():
    return ''.join(c for c in uuid.uuid4().hex if c.isdigit()).ljust(14, '0')[:14]


def _chave44():
    return ''.join(c for c in uuid.uuid4().hex if c.isdigit()).ljust(44, '0')[:44]


def _loja(is_matriz=False):
    loja = HoraLoja(
        cnpj=_cnpj(), apelido=f'L-{uuid.uuid4().hex[:6]}', nome='Loja Teste',
        ativa=True, is_matriz=is_matriz, atualizado_em=agora_utc_naive(),
    )
    _db.session.add(loja)
    _db.session.flush()
    return loja


def test_import_danfe_emitente_matriz_nao_atribui_loja(db, modelo_moto, monkeypatch):
    matriz = _loja(is_matriz=True)
    loja_fisica = _loja(is_matriz=False)

    chassi = f'CHV{uuid.uuid4().hex[:9].upper()}'
    # Moto conhecida + em estoque na loja fisica real (RECEBIDA).
    moto = HoraMoto(
        numero_chassi=chassi, modelo_id=modelo_moto.id, cor='PRETA',
        numero_motor=None, ano_modelo=2026, criado_por='setup',
    )
    _db.session.add(moto)
    _db.session.flush()
    registrar_evento(
        numero_chassi=chassi, tipo='RECEBIDA', loja_id=loja_fisica.id,
        operador='setup',
    )
    _db.session.flush()

    chave = _chave44()
    payload = {
        'nf': {
            'chave_44': chave,
            'cpf_destinatario': '12345678909',
            'nome_destinatario': 'Cliente Teste',
            'cnpj_emitente': matriz.cnpj,  # emitente = matriz (sempre)
            'data_emissao': date(2026, 6, 1),
            'valor_total': '9990.00',
            'numero_nf': '12345',
            'parser_usado': 'danfe_pdf_parser_v1',
        },
        'itens': [{
            'numero_chassi': chassi,
            'preco_real': '9990.00',
            'codigo_produto': None,
            'cor_texto_original': 'PRETA',
            'numero_motor': None,
            'ano_modelo': 2026,
            'modelo_texto_original': modelo_moto.nome_modelo,
        }],
    }
    monkeypatch.setattr(venda_service, 'parse_danfe_to_hora_payload',
                        lambda **kw: payload)
    monkeypatch.setattr(venda_service, '_salvar_pdf_storage',
                        lambda **kw: 'hora/vendas/fake.pdf')

    venda = venda_service.importar_nf_saida_pdf(
        pdf_bytes=b'fake', nome_arquivo_origem='nf.pdf', criado_por='tester',
    )

    # Header: NUNCA a matriz; loja a definir = NULL.
    assert venda.loja_id is None

    # Divergencia de loja a definir registrada.
    divs = HoraVendaDivergencia.query.filter_by(
        venda_id=venda.id, tipo='CNPJ_DESCONHECIDO',
    ).all()
    assert len(divs) == 1

    # Evento VENDIDA tambem sem a matriz.
    ev = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi, tipo='VENDIDA')
        .order_by(HoraMotoEvento.id.desc())
        .first()
    )
    assert ev is not None
    assert ev.loja_id is None
