import os
import pytest
from unittest.mock import patch

from app import db
from app.motos_assai.services import (
    importar_pdf_voe, PedidoVoeJaExisteError,
)
from app.motos_assai.models import AssaiPedidoVenda, AssaiPedidoVendaItem


FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'pedido_voe_exemplo.pdf')

# Fixture binaria nao versionada (.gitignore exclui *.pdf). Testes que abrem o
# arquivo real ficam SKIP (em vez de FileNotFoundError) quando ausente — mesmo
# padrao de test_recibo_service.py.
_skip_sem_fixture = pytest.mark.skipif(
    not os.path.exists(FIXTURE),
    reason='Fixture binaria de pedido VOE ausente (nao versionada)',
)


@_skip_sem_fixture
def test_importar_pdf_voe_sucesso(app, admin_user):
    """Importa o PDF canônico e persiste 38 lojas × 3 modelos = 114 items."""
    with app.app_context():
        with open(FIXTURE, 'rb') as f:
            pdf_bytes = f.read()

        # Limpa pedido se já existe (re-run)
        existing = AssaiPedidoVenda.query.filter_by(numero='21439695/L').first()
        if existing:
            db.session.delete(existing)
            db.session.commit()

        with patch('app.motos_assai.services.pedido_service.FileStorage') as mock_fs:
            mock_fs.return_value.save_file.return_value = 'motos_assai/pedidos/pedido_voe_exemplo.pdf'

            pedido = importar_pdf_voe(
                pdf_bytes=pdf_bytes,
                nome_arquivo='pedido_voe_exemplo.pdf',
                importado_por_id=admin_user.id,
            )

        assert pedido.numero == '21439695/L'
        assert pedido.parser_usado == 'DETERMINISTICO'
        assert float(pedido.parsing_confianca) >= 0.95
        assert pedido.status == 'ABERTO'

        items = AssaiPedidoVendaItem.query.filter_by(pedido_id=pedido.id).all()
        # 38 lojas seeded × 3 modelos = 114 (assume todas lojas em assai_loja)
        assert len(items) == 38 * 3, f'Esperava 114 items, veio {len(items)}'


@_skip_sem_fixture
def test_importar_duplicado_falha(app, admin_user):
    with app.app_context():
        with open(FIXTURE, 'rb') as f:
            pdf_bytes = f.read()

        # Garante que já existe
        if not AssaiPedidoVenda.query.filter_by(numero='21439695/L').first():
            with patch('app.motos_assai.services.pedido_service.FileStorage') as mock_fs:
                mock_fs.return_value.save_file.return_value = 'motos_assai/pedidos/p.pdf'
                importar_pdf_voe(pdf_bytes, 'p.pdf', admin_user.id)

        with pytest.raises(PedidoVoeJaExisteError):
            with patch('app.motos_assai.services.pedido_service.FileStorage') as mock_fs:
                mock_fs.return_value.save_file.return_value = 'motos_assai/pedidos/p2.pdf'
                importar_pdf_voe(pdf_bytes, 'p2.pdf', admin_user.id)
