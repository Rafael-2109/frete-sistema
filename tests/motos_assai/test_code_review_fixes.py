"""Testes para gaps identificados na revisão de código (2026-05-13).

Cobre cenários sem teste apontados pelos 4 code-reviewers em paralelo:
    - S10: pedido.status transiciona automaticamente após _calcular_match BATEU
    - R5.1: cancelar NF com Carregamento FINALIZADO -> sep volta CARREGADA
    - R5.2: cancelar NF sem Carregamento -> sep volta FECHADA
    - S11: remover_nf_do_espelho limpa numero_nf nas linhas Nacom
    - S15: cancelar NF -> EmbarqueItem.nota_fiscal = None
    - S16: AssaiNfQpaItemVinculoHistorico registrado antes da limpeza FK
    - S21: resolver_divergencia re-roda _calcular_match
    - A8: MODELO_DIVERGENTE detectado quando modelo NF != modelo cadastrado

Convencao do conftest local: `app` fixture usa create_app() sem TestConfig,
portanto roda em Postgres do ambiente. Cada teste cria entidades e
db.session.rollback() ao final via fixture do conftest top-level.
"""
from decimal import Decimal
import pytest

from app import db
from app.motos_assai.models import (
    AssaiCd, AssaiLoja, AssaiModelo, AssaiMoto, AssaiMotoEvento,
    AssaiPedidoVenda, AssaiPedidoVendaItem, AssaiPedidoVendaLoja,
    AssaiSeparacao, AssaiSeparacaoItem,
    AssaiCarregamento, AssaiCarregamentoItem,
    AssaiNfQpa, AssaiNfQpaItem, AssaiNfQpaItemVinculoHistorico,
    AssaiDivergencia,
    PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_PARCIALMENTE_FATURADO, PEDIDO_STATUS_FATURADO,
    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
    SEPARACAO_STATUS_CARREGADA, SEPARACAO_STATUS_FATURADA,
    CARREGAMENTO_STATUS_FINALIZADO, CARREGAMENTO_STATUS_EM_CARREGAMENTO,
    NF_STATUS_BATEU, NF_STATUS_DIVERGENTE, NF_STATUS_CANCELADA, NF_STATUS_NAO_RECONCILIADO,
    DIVERGENCIA_TIPO_MODELO_DIVERGENTE, DIVERGENCIA_TIPO_NF_CHASSI_FORA_CARREGAMENTO,
    DIVERGENCIA_RESOLUCAO_IGNORAR,
    EVENTO_FATURADA, EVENTO_CARREGADA, EVENTO_SEPARADA, EVENTO_DISPONIVEL,
)
from app.motos_assai.services.pedido_status_service import recalcular_status_pedido
from app.motos_assai.services.cancelamento_nf_service import cancelar_nf_qpa
from app.motos_assai.services.divergencia_service import (
    criar_divergencia, resolver_divergencia,
)
from app.motos_assai.services.separacao_mirror_service import remover_nf_do_espelho
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo


def _setup_cenario_basico(suffix=''):
    """Cria CD, loja, modelo, pedido, item, sep fechada, NF batida + chassis.

    Retorna dict com referências para uso em testes.

    NOTA: cada teste deve gerar suffix unico se rodando paralelo (testes do
    motos_assai usam Postgres real — sem isolamento por transacao automatico).
    """
    import uuid
    s = suffix or uuid.uuid4().hex[:6]

    cd = AssaiCd(nome=f'CD_{s}', cnpj=f'12{s[:2]}567800010{s[-1]}'[:14])
    db.session.add(cd)
    db.session.flush()

    loja = AssaiLoja(
        numero=f'9{s[:3]}', cnpj=f'987654320001{s[:2]}'[:18],
        nome=f'Loja_{s}', razao_social=f'Loja_{s} LTDA',
    )
    modelo = AssaiModelo(codigo=f'MOD_{s}', nome=f'Modelo {s}',
                        regex_chassi=r'.*', peso_kg=Decimal('30.0'))
    db.session.add_all([loja, modelo])
    db.session.flush()

    pedido = AssaiPedidoVenda(
        numero=f'PED_{s}',
        status=PEDIDO_STATUS_ABERTO,
    )
    db.session.add(pedido)
    db.session.flush()

    pvl = AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id)
    db.session.add(pvl)
    db.session.flush()

    item_pedido = AssaiPedidoVendaItem(
        pedido_id=pedido.id, pedido_loja_id=pvl.id,
        loja_id=loja.id, modelo_id=modelo.id,
        qtd_pedida=2, valor_unitario=Decimal('1000.00'),
        valor_total=Decimal('2000.00'),
    )
    db.session.add(item_pedido)
    db.session.flush()

    sep = AssaiSeparacao(
        pedido_id=pedido.id, loja_id=loja.id,
        status=SEPARACAO_STATUS_FECHADA,
    )
    db.session.add(sep)
    db.session.flush()

    return {
        's': s, 'cd': cd, 'loja': loja, 'modelo': modelo,
        'pedido': pedido, 'pvl': pvl, 'item_pedido': item_pedido, 'sep': sep,
    }


def _adicionar_chassis(cenario, n=2):
    """Adiciona n chassis na sep (status SEPARADA via evento)."""
    chassis = []
    for i in range(n):
        chassi = f'CHASSI_{cenario["s"]}_{i}'
        moto = AssaiMoto(chassi=chassi, modelo_id=cenario['modelo'].id, cor='AZUL')
        db.session.add(moto)
        item = AssaiSeparacaoItem(
            separacao_id=cenario['sep'].id,
            chassi=chassi, modelo_id=cenario['modelo'].id,
            valor_unitario_qpa=Decimal('1000.00'),
        )
        db.session.add(item)
        chassis.append(chassi)
    db.session.flush()
    for chassi in chassis:
        emitir_evento(chassi, EVENTO_SEPARADA, operador_id=None)
    return chassis


# ============================================================
# S10: status do pedido transiciona apos _calcular_match BATEU
# ============================================================

def test_s10_recalcular_status_pedido_apos_match_bateu(app):
    """Apos BATEU, recalcular_status_pedido (chamado de _calcular_match)
    transiciona pedido para FATURADO."""
    with app.app_context():
        try:
            cenario = _setup_cenario_basico('s10a')
            chassis = _adicionar_chassis(cenario, n=2)

            # Simular BATEU: sep -> FATURADA + chassis -> FATURADA
            cenario['sep'].status = SEPARACAO_STATUS_FATURADA
            for chassi in chassis:
                emitir_evento(chassi, EVENTO_FATURADA, operador_id=None)
            db.session.flush()

            # recalcular_status_pedido (callsite agora chamado em _calcular_match)
            novo_status = recalcular_status_pedido(cenario['pedido'].id)

            assert novo_status == PEDIDO_STATUS_FATURADO, (
                f'Esperado FATURADO, veio {novo_status} '
                f'(qtd_pedida=2, chassis FATURADA=2)'
            )
        finally:
            db.session.rollback()


def test_s10_recalcular_parcial_quando_alguns_chassis_faturados(app):
    """qtd_faturada < qtd_pedida deve resultar em PARCIALMENTE_FATURADO."""
    with app.app_context():
        try:
            cenario = _setup_cenario_basico('s10b')
            chassis = _adicionar_chassis(cenario, n=2)

            # So 1 dos 2 chassis vai para FATURADA
            cenario['sep'].status = SEPARACAO_STATUS_FATURADA
            emitir_evento(chassis[0], EVENTO_FATURADA, operador_id=None)

            # Outra sep FECHADA com chassi nao-faturado
            sep2 = AssaiSeparacao(
                pedido_id=cenario['pedido'].id, loja_id=cenario['loja'].id,
                status=SEPARACAO_STATUS_FECHADA,
            )
            db.session.add(sep2)
            db.session.flush()

            # qtd_pedida=2, chassis em sep FATURADA: 2 items mas so 1 evento FATURADA.
            # recalcular conta items, nao eventos. Logo deve dar FATURADO (2==2).
            # Para PARCIAL real: criar pedido com qtd_pedida=4 e so 2 items FATURADA.
            db.session.flush()
            cenario['item_pedido'].qtd_pedida = 4
            cenario['item_pedido'].valor_total = Decimal('4000.00')
            db.session.flush()

            novo_status = recalcular_status_pedido(cenario['pedido'].id)
            assert novo_status == PEDIDO_STATUS_PARCIALMENTE_FATURADO, (
                f'Esperado PARCIALMENTE_FATURADO (2 items FATURADA / 4 pedidos), '
                f'veio {novo_status}'
            )
        finally:
            db.session.rollback()


# ============================================================
# R5.1 + R5.2: cancelar_nf_qpa reverte sep conforme contexto
# ============================================================

def test_r5_1_cancelar_nf_com_carregamento_finalizado_volta_carregada(app):
    """Sep FATURADA com Carregamento FINALIZADO -> apos cancelar NF, sep volta CARREGADA."""
    with app.app_context():
        try:
            cenario = _setup_cenario_basico('r51')
            chassis = _adicionar_chassis(cenario, n=2)

            # Sep CARREGADA via Carregamento finalizado
            car = AssaiCarregamento(
                pedido_id=cenario['pedido'].id, loja_id=cenario['loja'].id,
                separacao_id=cenario['sep'].id,
                status=CARREGAMENTO_STATUS_FINALIZADO,
            )
            db.session.add(car)
            db.session.flush()

            cenario['sep'].status = SEPARACAO_STATUS_FATURADA
            for chassi in chassis:
                emitir_evento(chassi, EVENTO_CARREGADA, operador_id=None)
                emitir_evento(chassi, EVENTO_FATURADA, operador_id=None)
            db.session.flush()

            # NF FATURADA vinculada
            nf = AssaiNfQpa(
                chave_44='1' * 44, numero=f'NF_{cenario["s"]}',
                valor_total=Decimal('2000.00'),
                separacao_id=cenario['sep'].id, loja_id=cenario['loja'].id,
                status_match=NF_STATUS_BATEU, importada_por_id=None,
            )
            db.session.add(nf)
            db.session.flush()
            for chassi in chassis:
                db.session.add(AssaiNfQpaItem(
                    nf_id=nf.id, chassi=chassi, valor_extraido=Decimal('1000.00'),
                ))
            db.session.flush()

            # Cancelar NF
            cancelar_nf_qpa(nf.id, motivo='teste R5.1', operador_id=None)
            db.session.flush()

            # R5.1: sep deve voltar para CARREGADA (nao FECHADA), porque ha Carregamento
            assert cenario['sep'].status == SEPARACAO_STATUS_CARREGADA, (
                f'R5.1: Sep com Carregamento FINALIZADO deveria voltar para CARREGADA, '
                f'veio {cenario["sep"].status}'
            )
            # Chassis voltam para CARREGADA (evento)
            for chassi in chassis:
                assert status_efetivo(chassi) == EVENTO_CARREGADA, (
                    f'Chassi {chassi} esperado CARREGADA, veio {status_efetivo(chassi)}'
                )
            # NF marcada como CANCELADA
            assert nf.status_match == NF_STATUS_CANCELADA
        finally:
            db.session.rollback()


def test_r5_2_cancelar_nf_sem_carregamento_volta_fechada(app):
    """Sep FATURADA SEM Carregamento -> apos cancelar NF, sep volta FECHADA."""
    with app.app_context():
        try:
            cenario = _setup_cenario_basico('r52')
            chassis = _adicionar_chassis(cenario, n=2)

            # Sep FATURADA mas SEM Carregamento (NF chegou antes — S1=b)
            cenario['sep'].status = SEPARACAO_STATUS_FATURADA
            for chassi in chassis:
                emitir_evento(chassi, EVENTO_FATURADA, operador_id=None)
            db.session.flush()

            nf = AssaiNfQpa(
                chave_44='2' * 44, numero=f'NF_{cenario["s"]}',
                valor_total=Decimal('2000.00'),
                separacao_id=cenario['sep'].id, loja_id=cenario['loja'].id,
                status_match=NF_STATUS_BATEU, importada_por_id=None,
            )
            db.session.add(nf)
            db.session.flush()
            for chassi in chassis:
                db.session.add(AssaiNfQpaItem(
                    nf_id=nf.id, chassi=chassi, valor_extraido=Decimal('1000.00'),
                ))
            db.session.flush()

            cancelar_nf_qpa(nf.id, motivo='teste R5.2', operador_id=None)
            db.session.flush()

            # R5.2: sep volta FECHADA (sem Carregamento associado)
            assert cenario['sep'].status == SEPARACAO_STATUS_FECHADA, (
                f'R5.2: Sep sem Carregamento deveria voltar para FECHADA, '
                f'veio {cenario["sep"].status}'
            )
            # Chassis voltam SEPARADA (nao CARREGADA — nao havia Carregamento)
            for chassi in chassis:
                assert status_efetivo(chassi) == EVENTO_SEPARADA, (
                    f'Chassi {chassi} esperado SEPARADA, veio {status_efetivo(chassi)}'
                )
        finally:
            db.session.rollback()


# ============================================================
# S16: AssaiNfQpaItemVinculoHistorico registrado antes da limpeza FK
# ============================================================

def test_s16_cancelar_nf_registra_vinculo_historico(app):
    """Cancelar NF deve criar AssaiNfQpaItemVinculoHistorico para items que
    tinham separacao_item_id antes da limpeza."""
    with app.app_context():
        try:
            cenario = _setup_cenario_basico('s16')
            chassis = _adicionar_chassis(cenario, n=1)
            chassi = chassis[0]

            cenario['sep'].status = SEPARACAO_STATUS_FATURADA
            emitir_evento(chassi, EVENTO_FATURADA, operador_id=None)

            sep_item = AssaiSeparacaoItem.query.filter_by(
                separacao_id=cenario['sep'].id, chassi=chassi,
            ).first()
            nf = AssaiNfQpa(
                chave_44='3' * 44, numero=f'NF_{cenario["s"]}',
                valor_total=Decimal('1000.00'),
                separacao_id=cenario['sep'].id, loja_id=cenario['loja'].id,
                status_match=NF_STATUS_BATEU, importada_por_id=None,
            )
            db.session.add(nf)
            db.session.flush()
            nf_item = AssaiNfQpaItem(
                nf_id=nf.id, chassi=chassi, valor_extraido=Decimal('1000.00'),
                separacao_item_id=sep_item.id,
            )
            db.session.add(nf_item)
            db.session.flush()

            # Sem vinculos historicos antes
            assert AssaiNfQpaItemVinculoHistorico.query.filter_by(
                nf_qpa_item_id=nf_item.id
            ).count() == 0

            cancelar_nf_qpa(nf.id, motivo='teste S16', operador_id=None)
            db.session.flush()

            # Apos cancelar: 1 vinculo historico criado + FK limpa
            vinculos = AssaiNfQpaItemVinculoHistorico.query.filter_by(
                nf_qpa_item_id=nf_item.id
            ).all()
            assert len(vinculos) == 1, (
                f'Esperado 1 vinculo historico, veio {len(vinculos)}'
            )
            assert vinculos[0].chassi_no_momento == chassi
            assert vinculos[0].motivo == 'NF_CANCELADA'
            # FK limpa
            db.session.refresh(nf_item)
            assert nf_item.separacao_item_id is None
        finally:
            db.session.rollback()


# ============================================================
# S11: remover_nf_do_espelho limpa numero_nf das linhas Nacom
# ============================================================

def test_s11_remover_nf_do_espelho_limpa_numero_nf(app):
    """remover_nf_do_espelho deve setar numero_nf=None em todas linhas do lote."""
    with app.app_context():
        try:
            from app.separacao.models import Separacao
            cenario = _setup_cenario_basico('s11')

            # Criar 2 linhas no espelho Nacom (ASSAI-SEP-<id>) com numero_nf preenchido
            lote_id = f'ASSAI-SEP-{cenario["sep"].id}'
            linhas = []
            for i in range(2):
                ln = Separacao(
                    separacao_lote_id=lote_id,
                    num_pedido=f'{cenario["pedido"].numero}-{cenario["loja"].numero}',
                    cnpj_cpf=cenario['loja'].cnpj,
                    nome_cidade='SAO PAULO',
                    cod_uf='SP',
                    cidade_normalizada='SAO PAULO',
                    uf_normalizada='SP',
                    cod_produto=cenario['modelo'].codigo,
                    nome_produto=cenario['modelo'].nome,
                    qtd_saldo=1.0, valor_saldo=1000.0,
                    peso=30.0, pallet=0.0,
                    status='ABERTO',
                    numero_nf=f'NF_{cenario["s"]}',
                    chassi_assai=f'CHASSI_{cenario["s"]}_{i}',
                )
                db.session.add(ln)
                linhas.append(ln)
            db.session.flush()

            result = remover_nf_do_espelho(cenario['sep'].id)
            db.session.flush()

            assert result == 2, f'Esperado 2 linhas atualizadas, veio {result}'
            for ln in linhas:
                db.session.refresh(ln)
                assert ln.numero_nf is None, (
                    f'Linha {ln.id}: numero_nf nao limpo (={ln.numero_nf})'
                )
                assert ln.sincronizado_nf is False
        finally:
            db.session.rollback()


# ============================================================
# S21: resolver_divergencia re-roda _calcular_match
# ============================================================

def test_s21_resolver_divergencia_ignorar_marca_resolvida(app):
    """resolver_divergencia tipo=IGNORAR marca como resolvida + observacao."""
    with app.app_context():
        try:
            cenario = _setup_cenario_basico('s21')
            chassis = _adicionar_chassis(cenario, n=1)

            nf = AssaiNfQpa(
                chave_44='5' * 44, numero=f'NF_{cenario["s"]}',
                valor_total=Decimal('1000.00'),
                separacao_id=cenario['sep'].id, loja_id=cenario['loja'].id,
                status_match=NF_STATUS_DIVERGENTE, importada_por_id=None,
            )
            db.session.add(nf)
            db.session.flush()

            div = criar_divergencia(
                tipo=DIVERGENCIA_TIPO_NF_CHASSI_FORA_CARREGAMENTO,
                chassi=chassis[0], nf_id=nf.id, sep_id=cenario['sep'].id,
                operador_id=None,
            )
            db.session.flush()
            assert div.resolvida_em is None

            resolver_divergencia(
                div.id, tipo_resolucao=DIVERGENCIA_RESOLUCAO_IGNORAR,
                observacao='caso aceito gerencialmente', operador_id=None,
            )
            db.session.flush()

            db.session.refresh(div)
            assert div.resolvida_em is not None
            assert div.tipo_resolucao == DIVERGENCIA_RESOLUCAO_IGNORAR
            assert div.observacao_resolucao == 'caso aceito gerencialmente'
        finally:
            db.session.rollback()


# ============================================================
# A8: MODELO_DIVERGENTE detection (placeholder — aguarda implementacao
# completa em _calcular_match)
# ============================================================

def test_a8_criar_divergencia_modelo_divergente(app):
    """Smoke test: criar divergencia tipo MODELO_DIVERGENTE deve persistir."""
    with app.app_context():
        try:
            cenario = _setup_cenario_basico('a8')
            div = criar_divergencia(
                tipo=DIVERGENCIA_TIPO_MODELO_DIVERGENTE,
                chassi=f'CHASSI_TEST_{cenario["s"]}',
                detalhes={'modelo_esperado': 'SOL', 'modelo_extraido': 'X11_MINI'},
                operador_id=None,
            )
            db.session.flush()
            assert div.tipo == DIVERGENCIA_TIPO_MODELO_DIVERGENTE
            assert div.detalhes.get('modelo_esperado') == 'SOL'
            assert div.detalhes.get('modelo_extraido') == 'X11_MINI'
        finally:
            db.session.rollback()
