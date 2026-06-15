"""Testes de integração para recibo_service.importar."""

import os
import pytest
from unittest.mock import patch

from app import db
from app.motos_assai.services import importar_recibo, ReciboParserError
from app.motos_assai.services.compra_service import criar_consolidado
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiCompraMotochefe, AssaiReciboMotochefe, AssaiReciboItem,
)


FIXTURE_PDF = os.path.join(os.path.dirname(__file__), 'fixtures', 'recibo_motochefe_exemplo.pdf')
FIXTURE_XLSX = os.path.join(os.path.dirname(__file__), 'fixtures', 'recibo_motochefe_exemplo.xlsx')

# Fixtures binarias nao versionadas (.gitignore exclui *.pdf/*.xlsx). Os testes
# que abrem o arquivo real ficam SKIP (em vez de ERROR ambiental) quando ausente.
# Testes com mock/bytes inline neste modulo continuam rodando normalmente.
_skip_sem_fixture = pytest.mark.skipif(
    not (os.path.exists(FIXTURE_PDF) and os.path.exists(FIXTURE_XLSX)),
    reason='Fixtures binarias de recibo ausentes (nao versionadas)',
)


def _criar_compra_minima(admin_user):
    """Cria um AssaiPedidoVenda e consolida numa compra para usar nos testes."""
    import uuid
    numero = f'RECIBO-TEST-{uuid.uuid4().hex[:8].upper()}'
    p = AssaiPedidoVenda(numero=numero, criado_por_id=admin_user.id, status='ABERTO')
    db.session.add(p)
    db.session.flush()
    return criar_consolidado([p.id], None, admin_user.id)


@_skip_sem_fixture
def test_importar_pdf_recibo(app, admin_user):
    """Importa PDF canônico e persiste > 50 chassis com rollback no final."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        with open(FIXTURE_PDF, 'rb') as f:
            pdf_bytes = f.read()

        with patch('app.motos_assai.services.recibo_service.FileStorage') as mock_fs:
            mock_fs.return_value.save_file.return_value = (
                f'motos_assai/recibos/{compra.id}/recibo_motochefe_exemplo.pdf'
            )

            recibo = importar_recibo(
                compra_id=compra.id,
                file_bytes=pdf_bytes,
                nome_arquivo='haroldo_sp.pdf',
                mime_type='application/pdf',
                importado_por_id=admin_user.id,
            )

        assert recibo.tipo_documento == 'PDF'
        assert recibo.compra_id == compra.id
        assert recibo.status == 'RECEBIDO_AGUARDANDO_CONFERENCIA'
        assert recibo.parser_usado == 'DETERMINISTICO'

        items = AssaiReciboItem.query.filter_by(recibo_id=recibo.id).all()
        assert len(items) > 50, f'Esperava > 50 chassis (canon: 115), veio {len(items)}'

        # Pelo menos alguns chassis devem ter modelo_id resolvido (assume modelos seeded)
        dot_resolvidos = [i for i in items if i.modelo_id is not None]
        assert len(dot_resolvidos) > 0, 'Nenhum modelo_id resolvido'

        db.session.rollback()


@_skip_sem_fixture
def test_importar_xlsx_recibo(app, admin_user):
    """Importa XLSX canônico e persiste chassis."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        with open(FIXTURE_XLSX, 'rb') as f:
            xlsx_bytes = f.read()

        with patch('app.motos_assai.services.recibo_service.FileStorage') as mock_fs:
            mock_fs.return_value.save_file.return_value = (
                f'motos_assai/recibos/{compra.id}/recibo_motochefe_exemplo.xlsx'
            )

            recibo = importar_recibo(
                compra_id=compra.id,
                file_bytes=xlsx_bytes,
                nome_arquivo='recibo.xlsx',
                mime_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                importado_por_id=admin_user.id,
            )

        assert recibo.tipo_documento == 'EXCEL'
        assert recibo.compra_id == compra.id
        items = AssaiReciboItem.query.filter_by(recibo_id=recibo.id).all()
        assert len(items) > 0

        db.session.rollback()


def test_tipo_arquivo_invalido(app, admin_user):
    """Arquivo com extensão não suportada levanta ReciboParserError antes de acessar S3."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        with pytest.raises(ReciboParserError, match='não suportado'):
            importar_recibo(
                compra_id=compra.id, file_bytes=b'fake',
                nome_arquivo='x.txt', mime_type='text/plain',
                importado_por_id=admin_user.id,
            )
        db.session.rollback()


def test_compra_inexistente_retorna_404(app, admin_user):
    """compra_id inválido resulta em 404 (get_or_404)."""
    with app.app_context():
        with pytest.raises(Exception):  # 404 / NotFound
            importar_recibo(
                compra_id=999999,
                file_bytes=b'',
                nome_arquivo='x.pdf',
                mime_type='application/pdf',
                importado_por_id=admin_user.id,
            )
        db.session.rollback()


@_skip_sem_fixture
def test_s3_upload_ocorre_apos_parsing(app, admin_user):
    """Garante que S3 upload (save_file) é chamado SOMENTE após parsing OK — lição C2."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        with open(FIXTURE_PDF, 'rb') as f:
            pdf_bytes = f.read()

        call_order = []

        original_extract = None

        # Rastreia a ordem: primeiro extractor, depois FileStorage.save_file
        from app.motos_assai.services.parsers.motochefe_recibo_pdf_extractor import (
            MotochefeReciboPdfExtractor,
        )
        original_extract = MotochefeReciboPdfExtractor.extract

        def tracked_extract(self, path):
            call_order.append('EXTRACT')
            return original_extract(self, path)

        with patch.object(MotochefeReciboPdfExtractor, 'extract', tracked_extract):
            with patch('app.motos_assai.services.recibo_service.FileStorage') as mock_fs:
                def tracked_save(*args, **kwargs):
                    call_order.append('S3_UPLOAD')
                    return 'motos_assai/recibos/test/recibo.pdf'
                mock_fs.return_value.save_file.side_effect = tracked_save

                importar_recibo(
                    compra_id=compra.id,
                    file_bytes=pdf_bytes,
                    nome_arquivo='haroldo_sp.pdf',
                    mime_type='application/pdf',
                    importado_por_id=admin_user.id,
                )

        # EXTRACT deve aparecer ANTES de S3_UPLOAD
        assert 'EXTRACT' in call_order
        assert 'S3_UPLOAD' in call_order
        extract_idx = call_order.index('EXTRACT')
        s3_idx = call_order.index('S3_UPLOAD')
        assert extract_idx < s3_idx, f'S3 upload antes do extract! Ordem: {call_order}'

        db.session.rollback()


def test_recibo_sem_chassis_levanta_erro(app, admin_user):
    """Se o parser retorna lista vazia e LLM também falha, ReciboParserError é levantado."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)

        with patch('app.motos_assai.services.recibo_service.MotochefeReciboPdfExtractor') as mock_ext, \
             patch('app.motos_assai.services.recibo_service.parse_pdf_via_llm') as mock_llm:
            mock_ext.return_value.extract.return_value = []
            from app.motos_assai.services.parsers.motochefe_recibo_llm_fallback import (
                MotochefeReciboLlmFallbackError,
            )
            mock_llm.side_effect = MotochefeReciboLlmFallbackError('LLM timeout')

            with pytest.raises(ReciboParserError, match='Determinístico zero'):
                importar_recibo(
                    compra_id=compra.id,
                    file_bytes=b'%PDF-1.4 fake content',
                    nome_arquivo='empty.pdf',
                    mime_type='application/pdf',
                    importado_por_id=admin_user.id,
                )
        db.session.rollback()


def test_confianca_total_desconhecido_aciona_llm():
    """IMP-2026-05-20-001: total ausente NAO pode devolver 0.85 (acima do limiar).

    Antes do fix, total desconhecido devolvia 0.85 e o LLM nunca era acionado —
    recibo importava 3 de 60 motos. Agora devolve < limiar para escalar ao LLM.
    """
    from app.motos_assai.services.recibo_service import (
        _calcular_confianca, CONFIANCA_LIMIAR, CONFIANCA_TOTAL_DESCONHECIDO,
    )
    items_sem_total = [
        {'chassi': 'LA2026SA030008284', 'total_motos_declarado': None},
        {'chassi': 'LA2026SA030008353', 'total_motos_declarado': None},
        {'chassi': 'LA2026SA030008383', 'total_motos_declarado': None},
    ]
    conf = _calcular_confianca(items_sem_total)
    assert conf == CONFIANCA_TOTAL_DESCONHECIDO
    assert conf < CONFIANCA_LIMIAR, 'confianca deve forcar fallback LLM'


def test_confianca_proporcional_quando_total_presente():
    """Com total declarado, confianca = extraidos / total."""
    from app.motos_assai.services.recibo_service import _calcular_confianca
    items = [
        {'chassi': f'CH{i:03d}ABC0000', 'total_motos_declarado': 60}
        for i in range(3)
    ]
    conf = _calcular_confianca(items)
    assert abs(conf - (3 / 60)) < 1e-9  # 0.05, bem abaixo do limiar


def test_chassis_duplicados_sao_deduplicados(app, admin_user):
    """Chassis duplicados no mesmo recibo são deduplicated (set chassis_vistos)."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)

        # Simula parser retornando chassi duplicado
        fake_items = [
            {
                'chassi': 'CHASSI001ABC', 'modelo_texto': 'DOT 1000W',
                'equipe': 'TESTE', 'conferente': 'CONF',
                'total_motos_declarado': 2, 'data_recibo': '05/05/2026',
                'cor': 'PRETO', 'motor': 'MOTOR001',
            },
            {
                'chassi': 'CHASSI001ABC', 'modelo_texto': 'DOT 1000W',  # duplicado
                'equipe': 'TESTE', 'conferente': 'CONF',
                'total_motos_declarado': 2, 'data_recibo': '05/05/2026',
                'cor': 'PRETO', 'motor': 'MOTOR001',
            },
            {
                'chassi': 'CHASSI002DEF', 'modelo_texto': 'MIA 1000W',
                'equipe': 'TESTE', 'conferente': 'CONF',
                'total_motos_declarado': 2, 'data_recibo': '05/05/2026',
                'cor': 'BRANCO', 'motor': 'MOTOR002',
            },
        ]

        with patch('app.motos_assai.services.recibo_service.MotochefeReciboPdfExtractor') as mock_ext, \
             patch('app.motos_assai.services.recibo_service.FileStorage') as mock_fs:
            mock_ext.return_value.extract.return_value = fake_items
            mock_fs.return_value.save_file.return_value = 'motos_assai/recibos/test/dup.pdf'

            recibo = importar_recibo(
                compra_id=compra.id,
                file_bytes=b'%PDF-1.4',
                nome_arquivo='dup_test.pdf',
                mime_type='application/pdf',
                importado_por_id=admin_user.id,
            )

        items = AssaiReciboItem.query.filter_by(recibo_id=recibo.id).all()
        chassis = [i.chassi for i in items]
        # Deve ter 2 chassis únicos, não 3
        assert len(chassis) == 2
        assert chassis.count('CHASSI001ABC') == 1

        db.session.rollback()
