"""Testes de importar_nf_qpa: cenários BATEU / DIVERGENTE / NAO_RECONCILIADO + idempotência."""
import uuid
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from app import db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaItem, AssaiLoja, AssaiModelo,
    AssaiMoto, AssaiSeparacao, AssaiSeparacaoItem, AssaiNfQpa,
    PEDIDO_STATUS_EM_PRODUCAO,
    SEPARACAO_STATUS_FECHADA, SEPARACAO_STATUS_FATURADA,
    NF_STATUS_BATEU, NF_STATUS_DIVERGENTE, NF_STATUS_NAO_RECONCILIADO,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
)
from app.motos_assai.services import (
    get_ou_criar_separacao, registrar_chassi, finalizar_separacao, emitir_evento,
)
from app.motos_assai.services.parsers.nf_qpa_adapter import (
    importar_nf_qpa, NfQpaParseError, NfQpaJaImportadaError,
)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _chave_fake():
    """Gera uma chave de 44 dígitos aleatória."""
    import random
    return ''.join([str(random.randint(0, 9)) for _ in range(44)])


def _make_resultado_parser(chave, nome_dest, chassis, valor_total=Decimal('6900')):
    """Monta dict no formato de DanfePDFParser.get_todas_informacoes()."""
    return {
        'chave_acesso_nf': chave,
        'numero_nf': '123456',
        'serie_nf': '1',
        'cnpj_emitente': '12345678000190',
        'cnpj_destinatario': '98765432000101',
        'nome_destinatario': nome_dest,
        'valor_total': float(valor_total),
        'data_emissao': None,
        'veiculos': [
            {'chassi': ch, 'modelo': 'DOT'} for ch in chassis
        ],
    }


def _setup_separacao_com_chassi(admin, loja, chassi, valor=Decimal('6900')):
    """Cria pedido + separação fechada com um chassi DOT."""
    modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()
    uid = _uid()

    p = AssaiPedidoVenda(
        numero=f'TST-NF-{uid}',
        status=PEDIDO_STATUS_EM_PRODUCAO,
        criado_por_id=admin.id,
    )
    db.session.add(p)
    db.session.flush()
    db.session.add(AssaiPedidoVendaItem(
        pedido_id=p.id, loja_id=loja.id, modelo_id=modelo_dot.id,
        qtd_pedida=1, valor_unitario=valor, valor_total=valor,
    ))
    db.session.flush()

    m = AssaiMoto(chassi=chassi, modelo_id=modelo_dot.id, cor='CINZA')
    db.session.add(m)
    db.session.flush()

    emitir_evento(chassi, EVENTO_ESTOQUE, admin.id)
    emitir_evento(chassi, EVENTO_MONTADA, admin.id)
    emitir_evento(chassi, EVENTO_DISPONIVEL, admin.id)
    db.session.commit()

    registrar_chassi(p.id, loja.id, chassi, admin.id)
    sep = AssaiSeparacao.query.filter_by(pedido_id=p.id, loja_id=loja.id).first()
    finalizar_separacao(sep.id, admin.id)
    db.session.commit()
    return sep


def _call_importar(resultado_parser, chave=None, nome_dest='ASSAI LJ01', admin_id=1):
    """Helper: chama importar_nf_qpa com DanfePDFParser e FileStorage mockados.

    DanfePDFParser é importado dentro da função (lazy), portanto patchamos
    o módulo carvia diretamente.
    """
    if chave is None:
        chave = _chave_fake()
    resultado_parser['chave_acesso_nf'] = chave
    resultado_parser['nome_destinatario'] = nome_dest

    mock_instance = MagicMock()
    mock_instance.get_todas_informacoes.return_value = resultado_parser

    with patch('app.carvia.services.parsers.danfe_pdf_parser.DanfePDFParser',
               return_value=mock_instance) as _mock_cls, \
         patch('app.motos_assai.services.parsers.nf_qpa_adapter.FileStorage') as mock_fs:
        mock_fs.return_value.save_file.return_value = f'motos_assai/nfs_qpa/{chave}.pdf'

        return importar_nf_qpa(
            pdf_bytes=b'%PDF-fake',
            nome_arquivo='test_nf.pdf',
            importada_por_id=admin_id,
        )


# ─── Cenário BATEU ────────────────────────────────────────────────────────────

def test_match_bateu_todos_chassis_batem(app, admin_user):
    """BATEU: NF com 1 chassi que bate com separação ativa da mesma loja."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        chassi = f'TST_NF_B_{_uid()}'
        sep = _setup_separacao_com_chassi(admin_user, loja, chassi, Decimal('6900'))

        chave = _chave_fake()
        resultado = _make_resultado_parser(
            chave=chave,
            nome_dest=f'ASSAI LJ{loja.numero}',
            chassis=[chassi],
            valor_total=Decimal('6900'),
        )
        nf = _call_importar(resultado, chave=chave, nome_dest=f'ASSAI LJ{loja.numero}',
                            admin_id=admin_user.id)

        assert nf.status_match == NF_STATUS_BATEU, f"Esperava BATEU, veio {nf.status_match}"
        assert nf.separacao_id == sep.id

        sep_after = AssaiSeparacao.query.get(sep.id)
        assert sep_after.status == SEPARACAO_STATUS_FATURADA

        nf_item = nf.itens[0]
        assert nf_item.separacao_item_id is not None
        assert nf_item.tipo_divergencia is None

        db.session.rollback()


# ─── Cenário DIVERGENTE ───────────────────────────────────────────────────────

def test_match_divergente_chassi_extra_na_nf(app, admin_user):
    """DIVERGENTE: NF tem 2 chassis mas só 1 está na separação."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        chassi_ok = f'TST_NF_DO_{_uid()}'
        chassi_extra = f'TST_NF_DX_{_uid()}'

        _setup_separacao_com_chassi(admin_user, loja, chassi_ok, Decimal('6900'))

        # chassi_extra não tem separação
        modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()
        m = AssaiMoto(chassi=chassi_extra, modelo_id=modelo_dot.id, cor='AZUL')
        db.session.add(m)
        db.session.flush()
        emitir_evento(chassi_extra, EVENTO_ESTOQUE, admin_user.id)
        db.session.commit()

        chave = _chave_fake()
        resultado = _make_resultado_parser(
            chave=chave,
            nome_dest=f'ASSAI LJ{loja.numero}',
            chassis=[chassi_ok, chassi_extra],
            valor_total=Decimal('13800'),
        )
        nf = _call_importar(resultado, chave=chave, nome_dest=f'ASSAI LJ{loja.numero}',
                            admin_id=admin_user.id)

        assert nf.status_match == NF_STATUS_DIVERGENTE, f"Esperava DIVERGENTE, veio {nf.status_match}"

        itens = nf.itens
        chassis_match = {it.chassi: it for it in itens}
        assert chassis_match[chassi_ok].separacao_item_id is not None
        assert chassis_match[chassi_extra].tipo_divergencia == 'CHASSI_SEM_SEPARACAO'

        db.session.rollback()


def test_match_divergente_valor_acima_tolerancia(app, admin_user):
    """DIVERGENTE: chassi existe na separação mas valor diverge > 1%."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        chassi = f'TST_NF_DV_{_uid()}'
        _setup_separacao_com_chassi(admin_user, loja, chassi, Decimal('6900'))

        # Valor na NF: 6900 + 5% de diferença = 7245
        chave = _chave_fake()
        resultado = _make_resultado_parser(
            chave=chave,
            nome_dest=f'ASSAI LJ{loja.numero}',
            chassis=[chassi],
            valor_total=Decimal('7245'),
        )
        nf = _call_importar(resultado, chave=chave, nome_dest=f'ASSAI LJ{loja.numero}',
                            admin_id=admin_user.id)

        assert nf.status_match == NF_STATUS_NAO_RECONCILIADO or nf.status_match == NF_STATUS_DIVERGENTE, \
            f"Esperava NAO_RECONCILIADO ou DIVERGENTE, veio {nf.status_match}"
        nf_item = nf.itens[0]
        assert nf_item.tipo_divergencia == 'VALOR_DIVERGENTE'

        db.session.rollback()


# ─── Cenário NAO_RECONCILIADO ─────────────────────────────────────────────────

def test_match_nao_reconciliado_loja_inexistente(app, admin_user):
    """NAO_RECONCILIADO: nome_destinatario não contém "LJ\d+" reconhecível."""
    with app.app_context():
        chave = _chave_fake()
        resultado = _make_resultado_parser(
            chave=chave,
            nome_dest='SUPERMERCADOS SEM NUMERO LTDA',
            chassis=[f'TST_NF_NR_{_uid()}'],
            valor_total=Decimal('6900'),
        )
        nf = _call_importar(resultado, chave=chave,
                            nome_dest='SUPERMERCADOS SEM NUMERO LTDA',
                            admin_id=admin_user.id)

        assert nf.status_match == NF_STATUS_NAO_RECONCILIADO
        assert nf.loja_id is None
        assert nf.separacao_id is None

        db.session.rollback()


def test_match_nao_reconciliado_chassi_sem_separacao(app, admin_user):
    """NAO_RECONCILIADO: chassi não existe em nenhuma separação ativa."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        chassi = f'TST_NF_NS_{_uid()}'

        # Não cria separação para este chassi
        modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()
        m = AssaiMoto(chassi=chassi, modelo_id=modelo_dot.id, cor='VERMELHO')
        db.session.add(m)
        db.session.flush()
        emitir_evento(chassi, EVENTO_ESTOQUE, admin_user.id)
        db.session.commit()

        chave = _chave_fake()
        resultado = _make_resultado_parser(
            chave=chave,
            nome_dest=f'ASSAI LJ{loja.numero}',
            chassis=[chassi],
            valor_total=Decimal('6900'),
        )
        nf = _call_importar(resultado, chave=chave,
                            nome_dest=f'ASSAI LJ{loja.numero}',
                            admin_id=admin_user.id)

        assert nf.status_match == NF_STATUS_NAO_RECONCILIADO
        assert nf.itens[0].tipo_divergencia == 'CHASSI_SEM_SEPARACAO'

        db.session.rollback()


# ─── Idempotência ─────────────────────────────────────────────────────────────

def test_idempotencia_re_upload_mesmo_chave(app, admin_user):
    """Segunda importação com mesma chave_44 deve levantar NfQpaJaImportadaError."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        chassi = f'TST_NF_ID_{_uid()}'
        _setup_separacao_com_chassi(admin_user, loja, chassi, Decimal('6900'))

        chave = _chave_fake()
        resultado = _make_resultado_parser(
            chave=chave,
            nome_dest=f'ASSAI LJ{loja.numero}',
            chassis=[chassi],
            valor_total=Decimal('6900'),
        )

        # Primeira importação
        nf = _call_importar(resultado, chave=chave,
                            nome_dest=f'ASSAI LJ{loja.numero}',
                            admin_id=admin_user.id)
        assert nf.id is not None

        # Segunda importação: deve falhar com NfQpaJaImportadaError
        with pytest.raises(NfQpaJaImportadaError, match='já importada'):
            _call_importar(resultado, chave=chave,
                           nome_dest=f'ASSAI LJ{loja.numero}',
                           admin_id=admin_user.id)

        # Apenas 1 registro deve existir
        count = AssaiNfQpa.query.filter_by(chave_44=chave).count()
        assert count == 1

        db.session.rollback()


def test_parse_error_pdf_vazio(app, admin_user):
    """PDF vazio deve levantar NfQpaParseError."""
    with app.app_context():
        with pytest.raises(NfQpaParseError, match='PDF vazio'):
            importar_nf_qpa(pdf_bytes=b'', nome_arquivo='vazio.pdf',
                            importada_por_id=admin_user.id)


def test_parse_error_chave_invalida(app, admin_user):
    """Parser que retorna chave_acesso_nf inválida deve levantar NfQpaParseError."""
    with app.app_context():
        resultado = {
            'chave_acesso_nf': '123',  # menos de 44 dígitos
            'numero_nf': '1',
            'cnpj_emitente': '12345678000190',
            'cnpj_destinatario': '98765432000101',
            'nome_destinatario': 'ASSAI LJ01',
            'valor_total': 6900.0,
            'data_emissao': None,
            'veiculos': [],
        }

        mock_inst = MagicMock()
        mock_inst.get_todas_informacoes.return_value = resultado

        with patch('app.carvia.services.parsers.danfe_pdf_parser.DanfePDFParser',
                   return_value=mock_inst), \
             patch('app.motos_assai.services.parsers.nf_qpa_adapter.FileStorage'):

            with pytest.raises(NfQpaParseError, match='chave_acesso_nf inválida'):
                importar_nf_qpa(pdf_bytes=b'%PDF-fake', nome_arquivo='bad.pdf',
                                importada_por_id=admin_user.id)
