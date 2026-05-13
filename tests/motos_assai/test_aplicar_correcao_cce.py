"""Testes aplicar_correcao_cce (P1-2 fix — gap test_aplicar_correcao_cce.py).

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md §7.3
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase5-auxiliares.md Task 9

Cobertura:
1. Caminho feliz: troca chassi em NF + grava AssaiNfQpaItemVinculoHistorico + re-roda match
2. NF CANCELADA bloqueia aplicar_correcao_cce
3. chassis_corrigidos vazio levanta erro
4. Chassi antigo NAO presente na NF e ignorado (sem erro, sem efeito)
"""
import uuid
from decimal import Decimal

import pytest

from app import db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaLoja, AssaiPedidoVendaItem,
    AssaiLoja, AssaiModelo,
    AssaiMoto, AssaiSeparacao, AssaiNfQpa, AssaiNfQpaItem,
    AssaiNfQpaItemVinculoHistorico,
    PEDIDO_STATUS_ABERTO, SEPARACAO_STATUS_FATURADA,
    NF_STATUS_BATEU, NF_STATUS_CANCELADA,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL, EVENTO_SEPARADA,
    EVENTO_FATURADA,
    VINCULO_MOTIVO_CCE_ALTEROU_CHASSI,
)
from app.motos_assai.services import (
    registrar_chassi, finalizar_separacao,
    criar_separacao_com_saldos,
    emitir_evento, status_efetivo,
)
from app.motos_assai.services.cancelamento_nf_service import (
    aplicar_correcao_cce,
    CancelamentoValidationError,
)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _setup_nf_bateu(admin, loja, chassi_original):
    """Cria pedido + sep FATURADA + NF Q.P.A. BATEU com 1 chassi vinculado.

    Retorna (nf, sep, modelo).
    """
    modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()
    assert modelo_dot, 'Seed DOT obrigatorio em conftest'
    uid = _uid()

    # Pedido
    p = AssaiPedidoVenda(
        numero=f'TST-CCE-{uid}', status=PEDIDO_STATUS_ABERTO,
        criado_por_id=admin.id,
    )
    db.session.add(p); db.session.flush()
    pvl = AssaiPedidoVendaLoja(pedido_id=p.id, loja_id=loja.id)
    db.session.add(pvl); db.session.flush()
    db.session.add(AssaiPedidoVendaItem(
        pedido_id=p.id, pedido_loja_id=pvl.id, loja_id=loja.id, modelo_id=modelo_dot.id,
        qtd_pedida=1, valor_unitario=Decimal('6900'), valor_total=Decimal('6900'),
    ))
    db.session.flush()

    # Moto + eventos ate SEPARADA
    m = AssaiMoto(chassi=chassi_original, modelo_id=modelo_dot.id, cor='CINZA')
    db.session.add(m); db.session.flush()
    emitir_evento(chassi_original, EVENTO_ESTOQUE, admin.id)
    emitir_evento(chassi_original, EVENTO_MONTADA, admin.id)
    emitir_evento(chassi_original, EVENTO_DISPONIVEL, admin.id)
    db.session.commit()

    # Sep EM_SEPARACAO -> FECHADA
    criar_separacao_com_saldos(
        pedido_id=p.id, loja_id=loja.id,
        alocacoes=[{'modelo_id': modelo_dot.id, 'qtd': 1}],
        operador_id=admin.id,
    )
    db.session.commit()
    registrar_chassi(p.id, loja.id, chassi_original, admin.id)
    sep = AssaiSeparacao.query.filter_by(pedido_id=p.id, loja_id=loja.id).first()
    finalizar_separacao(sep.id, admin.id)
    db.session.commit()

    # Simula NF BATEU manualmente (evita dependencia do parser DanfePDF)
    chave = '1' * 30 + uid + '0' * (44 - 30 - len(uid))
    chave = chave[:44]
    nf = AssaiNfQpa(
        chave_44=chave,
        numero=f'NF-CCE-{uid}',
        emitente_cnpj='12345678000190',
        destinatario_cnpj='98765432000101',
        destinatario_nome=f'ASSAI LJ{loja.numero}',
        valor_total=Decimal('6900'),
        loja_id=loja.id,
        separacao_id=sep.id,
        status_match=NF_STATUS_BATEU,
        importada_por_id=admin.id,
    )
    db.session.add(nf); db.session.flush()
    sep_item = sep.itens[0]
    db.session.add(AssaiNfQpaItem(
        nf_id=nf.id, chassi=chassi_original,
        modelo_extraido='DOT', valor_extraido=Decimal('6900'),
        separacao_item_id=sep_item.id, tipo_divergencia=None,
    ))
    # Sep -> FATURADA + emitir FATURADA por chassi
    sep.status = SEPARACAO_STATUS_FATURADA
    emitir_evento(chassi_original, EVENTO_FATURADA, admin.id)
    db.session.commit()

    return nf, sep, modelo_dot


def test_aplicar_cce_caminho_feliz_troca_chassi(app, admin_user):
    """CCe substitui chassi_antigo por chassi_novo, grava historico e re-roda match."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        chassi_antigo = f'TST_CCE_ANT_{_uid()}'
        chassi_novo = f'TST_CCE_NOV_{_uid()}'

        nf, sep, modelo = _setup_nf_bateu(admin_user, loja, chassi_antigo)

        # Chassi novo deve existir e estar DISPONIVEL para ser vinculado pelo match
        m_novo = AssaiMoto(chassi=chassi_novo, modelo_id=modelo.id, cor='AZUL')
        db.session.add(m_novo); db.session.flush()
        emitir_evento(chassi_novo, EVENTO_ESTOQUE, admin_user.id)
        emitir_evento(chassi_novo, EVENTO_MONTADA, admin_user.id)
        emitir_evento(chassi_novo, EVENTO_DISPONIVEL, admin_user.id)
        # Chassi novo precisa estar SEPARADA na mesma sep para match BATEU
        emitir_evento(chassi_novo, EVENTO_SEPARADA, admin_user.id)
        # E ter separacao_item — substituir o item da sep que apontava para chassi_antigo
        sep_item = sep.itens[0]
        sep_item.chassi = chassi_novo
        db.session.commit()

        nf_id = nf.id
        chassi_antigo_status_pre = status_efetivo(chassi_antigo)
        assert chassi_antigo_status_pre == EVENTO_FATURADA

        # Aplicar CCe
        nf_after = aplicar_correcao_cce(
            nf_id=nf_id,
            chassis_corrigidos=[(chassi_antigo, chassi_novo)],
            numero_cce=f'CCe-001-{_uid()}',
            operador_id=admin_user.id,
        )
        db.session.commit()

        # 1. Item da NF agora tem chassi_novo
        item = AssaiNfQpaItem.query.filter_by(nf_id=nf_id).first()
        assert item.chassi == chassi_novo, 'chassi da NF deve ser atualizado'

        # 2. Historico foi gravado
        hist = AssaiNfQpaItemVinculoHistorico.query.filter_by(
            nf_qpa_item_id=item.id,
            motivo=VINCULO_MOTIVO_CCE_ALTEROU_CHASSI,
            chassi_no_momento=chassi_antigo,
        ).first()
        assert hist is not None, 'AssaiNfQpaItemVinculoHistorico deve registrar a troca'

        # 3. chassi_antigo nao deve mais estar FATURADA (foi revertido)
        status_antigo_pos = status_efetivo(chassi_antigo)
        assert status_antigo_pos != EVENTO_FATURADA, \
            f'chassi antigo deveria ter sido revertido de FATURADA (esta {status_antigo_pos})'

        # 4. NF refeita: status_match deve estar atualizado (BATEU/DIVERGENTE)
        assert nf_after.status_match in (NF_STATUS_BATEU, 'DIVERGENTE', 'NAO_RECONCILIADO')

        db.session.rollback()


def test_aplicar_cce_nf_cancelada_falha(app, admin_user):
    """NF CANCELADA bloqueia aplicar_correcao_cce."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        chassi = f'TST_CCE_CAN_{_uid()}'
        nf, _sep, _modelo = _setup_nf_bateu(admin_user, loja, chassi)

        # Marca NF como CANCELADA
        nf.status_match = NF_STATUS_CANCELADA
        db.session.commit()

        with pytest.raises(CancelamentoValidationError, match='CANCELADA'):
            aplicar_correcao_cce(
                nf_id=nf.id,
                chassis_corrigidos=[(chassi, f'TST_CCE_NEW_{_uid()}')],
                numero_cce='CCe-001',
                operador_id=admin_user.id,
            )

        db.session.rollback()


def test_aplicar_cce_chassis_corrigidos_vazio_falha(app, admin_user):
    """chassis_corrigidos vazio levanta CancelamentoValidationError."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        chassi = f'TST_CCE_VAZ_{_uid()}'
        nf, _sep, _modelo = _setup_nf_bateu(admin_user, loja, chassi)

        with pytest.raises(CancelamentoValidationError, match='vazio'):
            aplicar_correcao_cce(
                nf_id=nf.id,
                chassis_corrigidos=[],
                numero_cce='CCe-002',
                operador_id=admin_user.id,
            )

        db.session.rollback()


def test_aplicar_cce_chassi_antigo_nao_na_nf_ignora(app, admin_user):
    """Quando chassi_antigo NAO esta na NF, eh ignorado (sem erro, sem efeito).

    Garante idempotencia: aplicar CCe novamente nao quebra (chassi ja trocado).
    """
    with app.app_context():
        loja = AssaiLoja.query.first()
        chassi = f'TST_CCE_IGN_{_uid()}'
        nf, _sep, _modelo = _setup_nf_bateu(admin_user, loja, chassi)
        nf_id = nf.id

        # Tenta corrigir chassi inexistente — nao deve quebrar
        nf_after = aplicar_correcao_cce(
            nf_id=nf_id,
            chassis_corrigidos=[('TST_INEXISTENTE_ABC', 'TST_OUTRO_DEF')],
            numero_cce='CCe-003',
            operador_id=admin_user.id,
        )
        db.session.commit()

        # NF original intacta (chassi nao mudou)
        item = AssaiNfQpaItem.query.filter_by(nf_id=nf_id).first()
        assert item.chassi == chassi, 'chassi original deve permanecer intacto'

        # Sem historico de troca
        hist = AssaiNfQpaItemVinculoHistorico.query.filter_by(
            motivo=VINCULO_MOTIVO_CCE_ALTEROU_CHASSI,
        ).all()
        # pode haver historicos de outros testes — filtrar pelo chassi_no_momento
        hist_relevante = [h for h in hist if h.chassi_no_momento.startswith('TST_INEXISTENTE')]
        assert hist_relevante == [], 'nao deve gravar historico para chassi nao encontrado'

        db.session.rollback()
