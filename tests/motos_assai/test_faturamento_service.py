"""Testes do serviço de faturamento (geração Excel Q.P.A.)."""
import io
import uuid
from decimal import Decimal

import pytest
import openpyxl
from unittest.mock import patch

from app import db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaItem, AssaiLoja, AssaiModelo,
    AssaiMoto, AssaiSeparacao,
    PEDIDO_STATUS_EM_PRODUCAO, SEPARACAO_STATUS_FECHADA,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
)
from app.motos_assai.services import (
    gerar_excel_qpa,
    get_ou_criar_separacao, registrar_chassi, finalizar_separacao,
    emitir_evento,
)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _setup_separacao_fechada(app, admin):
    """Cria pedido + separação fechada com 1 chassi."""
    modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()
    loja = AssaiLoja.query.first()

    uid = _uid()
    p = AssaiPedidoVenda(
        numero=f'TST-FAT-{uid}',
        status=PEDIDO_STATUS_EM_PRODUCAO,
        criado_por_id=admin.id,
    )
    db.session.add(p)
    db.session.flush()
    db.session.add(AssaiPedidoVendaItem(
        pedido_id=p.id, loja_id=loja.id, modelo_id=modelo_dot.id,
        qtd_pedida=1, valor_unitario=Decimal('6900'), valor_total=Decimal('6900'),
    ))
    db.session.flush()

    chassi = f'TST_F_{_uid()}'
    m = AssaiMoto(chassi=chassi, modelo_id=modelo_dot.id, cor='PRETO')
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


def test_gerar_excel_estrutura_basica(app, admin_user):
    """gerar_excel_qpa deve retornar bytes com 2 abas: PEDIDO + BASE LOJAS."""
    with app.app_context():
        sep = _setup_separacao_fechada(app, admin_user)
        sep_id = sep.id

        with patch('app.motos_assai.services.faturamento_service.FileStorage') as mock_fs:
            mock_fs.return_value.save_file.return_value = f'motos_assai/solicitacoes/{sep_id}.xlsx'
            bytes_xlsx, s3_key = gerar_excel_qpa(sep_id, admin_user.id)

        assert isinstance(bytes_xlsx, bytes)
        assert len(bytes_xlsx) > 0
        assert s3_key

        wb = openpyxl.load_workbook(io.BytesIO(bytes_xlsx))
        assert 'PEDIDO' in wb.sheetnames, "Aba PEDIDO ausente"
        assert 'BASE LOJAS' in wb.sheetnames, "Aba BASE LOJAS ausente"

        ws_pedido = wb['PEDIDO']
        # Deve ter pelo menos 1 linha de dados de chassi
        valores = [ws_pedido.cell(row=r, column=2).value for r in range(1, ws_pedido.max_row + 1)]
        assert any(v and 'TST_F_' in str(v) for v in valores), "Chassi não encontrado no Excel"

        ws_lojas = wb['BASE LOJAS']
        assert ws_lojas.max_row > 1, "Aba BASE LOJAS deve ter lojas"

        db.session.rollback()


def test_gerar_excel_separacao_nao_fechada_falha(app, admin_user):
    """gerar_excel_qpa com separação EM_SEPARACAO deve levantar ValueError (H3)."""
    # H3: service valida status antes de gerar — EM_SEPARACAO não permitido.
    with app.app_context():
        modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()
        loja = AssaiLoja.query.first()
        uid = _uid()
        p = AssaiPedidoVenda(
            numero=f'TST-FAT2-{uid}',
            status=PEDIDO_STATUS_EM_PRODUCAO,
            criado_por_id=admin_user.id,
        )
        db.session.add(p)
        db.session.flush()
        db.session.add(AssaiPedidoVendaItem(
            pedido_id=p.id, loja_id=loja.id, modelo_id=modelo_dot.id,
            qtd_pedida=1, valor_unitario=Decimal('6900'), valor_total=Decimal('6900'),
        ))
        db.session.flush()

        chassi = f'TST_F2_{_uid()}'
        m = AssaiMoto(chassi=chassi, modelo_id=modelo_dot.id, cor='BRANCO')
        db.session.add(m)
        db.session.flush()
        emitir_evento(chassi, EVENTO_ESTOQUE, admin_user.id)
        emitir_evento(chassi, EVENTO_MONTADA, admin_user.id)
        emitir_evento(chassi, EVENTO_DISPONIVEL, admin_user.id)
        db.session.commit()

        registrar_chassi(p.id, loja.id, chassi, admin_user.id)
        sep = AssaiSeparacao.query.filter_by(pedido_id=p.id, loja_id=loja.id).first()
        sep_id = sep.id
        db.session.commit()

        # EM_SEPARACAO: service deve levantar ValueError (status inválido)
        import pytest as _pytest
        with _pytest.raises(ValueError, match='EM_SEPARACAO'):
            gerar_excel_qpa(sep_id, admin_user.id)

        db.session.rollback()
