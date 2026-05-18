"""Testes de importar_nf_qpa: cenários BATEU / DIVERGENTE / NAO_RECONCILIADO + idempotência."""
import uuid
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from app import db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaLoja, AssaiPedidoVendaItem,
    AssaiLoja, AssaiModelo,
    AssaiMoto, AssaiSeparacao, AssaiSeparacaoItem, AssaiNfQpa,
    AssaiCompraMotochefe, AssaiReciboMotochefe, AssaiReciboItem,
    PEDIDO_STATUS_ABERTO,
    SEPARACAO_STATUS_FECHADA, SEPARACAO_STATUS_FATURADA,
    NF_STATUS_BATEU, NF_STATUS_DIVERGENTE, NF_STATUS_NAO_RECONCILIADO,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
)
from app.motos_assai.services import (
    # get_ou_criar_separacao foi renomeada para get_separacao_ativa
    # e perdeu o side-effect de criar implicitamente (Migration 17 corretivo).
    registrar_chassi, finalizar_separacao, emitir_evento,
    criar_separacao_com_saldos,
)
from app.motos_assai.services.parsers.nf_qpa_adapter import (
    importar_nf_qpa, NfQpaParseError, NfQpaJaImportadaError,
)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _criar_recibo_conferido(chassi, modelo, admin):
    """Helper 2026-05-17: cria recibo Motochefe CONCLUIDO com chassi conferido.

    _calcular_match exige AssaiReciboItem(conferido=True, ativo=True) — sem
    isso, vira divergencia CHASSI_FATURADO_SEM_RECIBO.
    """
    uid = _uid()
    compra = AssaiCompraMotochefe(
        numero=f'COMP-TST-HELPER-{uid}', criada_por_id=admin.id,
    )
    db.session.add(compra)
    db.session.flush()
    recibo = AssaiReciboMotochefe(
        compra_id=compra.id, total_motos_declarado=1,
        status='CONCLUIDO',
        criado_por_id=admin.id,
    )
    db.session.add(recibo)
    db.session.flush()
    item = AssaiReciboItem(
        recibo_id=recibo.id, chassi=chassi,
        modelo_id=modelo.id, cor_texto='CINZA',
        conferido=True, ativo=True,
    )
    db.session.add(item)
    db.session.flush()
    return item


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
        # R4.2 (Big Bang Task 20): pedido fica ABERTO ate primeira NF.
        status=PEDIDO_STATUS_ABERTO,
        criado_por_id=admin.id,
    )
    db.session.add(p)
    db.session.flush()
    pvl = AssaiPedidoVendaLoja(pedido_id=p.id, loja_id=loja.id)
    db.session.add(pvl); db.session.flush()
    db.session.add(AssaiPedidoVendaItem(
        pedido_id=p.id, pedido_loja_id=pvl.id, loja_id=loja.id, modelo_id=modelo_dot.id,
        qtd_pedida=1, valor_unitario=valor, valor_total=valor,
    ))
    db.session.flush()

    m = AssaiMoto(chassi=chassi, modelo_id=modelo_dot.id, cor='CINZA')
    db.session.add(m)
    db.session.flush()

    # 2026-05-17 update: _calcular_match agora exige AssaiReciboItem conferido
    # (DIVERGENCIA_TIPO_CHASSI_FATURADO_SEM_RECIBO). Criar recibo+item de teste.
    compra = AssaiCompraMotochefe(
        numero=f'COMP-TST-{uid}', criada_por_id=admin.id,
    )
    db.session.add(compra)
    db.session.flush()
    recibo = AssaiReciboMotochefe(
        compra_id=compra.id, total_motos_declarado=1,
        status='CONCLUIDO',
        criado_por_id=admin.id,
    )
    db.session.add(recibo)
    db.session.flush()
    recibo_item = AssaiReciboItem(
        recibo_id=recibo.id, chassi=chassi,
        modelo_id=modelo_dot.id, cor_texto='CINZA',
        conferido=True, ativo=True,
    )
    db.session.add(recibo_item)
    db.session.flush()

    emitir_evento(chassi, EVENTO_ESTOQUE, admin.id)
    emitir_evento(chassi, EVENTO_MONTADA, admin.id)
    emitir_evento(chassi, EVENTO_DISPONIVEL, admin.id)
    db.session.commit()

    # Cria sep EM_SEPARACAO explicitamente (registrar_chassi nao cria mais —
    # Migration 17 corretivo 2026-05-12).
    criar_separacao_com_saldos(
        pedido_id=p.id, loja_id=loja.id,
        alocacoes=[{'modelo_id': modelo_dot.id, 'qtd': 1}],
        operador_id=admin.id,
    )
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

def test_match_bateu_chassi_extra_adicionado_pela_nf(app, admin_user):
    """BATEU: NF tem 2 chassis e ajustar_separacao_pela_nf v2 adiciona o extra
    a sep antes do match.

    Mudanca de comportamento (Plano Fase 4 — 2026-05-12):
    `ajustar_separacao_pela_nf` v2 roda ANTES do `_calcular_match` em
    `importar_nf_qpa`. NF passa a ser fonte de verdade — chassis extras sao
    incorporados na sep alvo automaticamente (commit eaf6564a).

    Antes (pre-Fase 4): cenario seria DIVERGENTE com CHASSI_SEM_SEPARACAO.
    """
    with app.app_context():
        loja = AssaiLoja.query.first()
        chassi_ok = f'TST_NF_DO_{_uid()}'
        chassi_extra = f'TST_NF_DX_{_uid()}'

        _setup_separacao_com_chassi(admin_user, loja, chassi_ok, Decimal('6900'))

        # chassi_extra existe no estoque (DISPONIVEL) mas nao esta em sep.
        # ajustar_separacao_pela_nf vai movimentar para SEPARADA e adicionar a sep.
        modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()
        m = AssaiMoto(chassi=chassi_extra, modelo_id=modelo_dot.id, cor='AZUL')
        db.session.add(m)
        db.session.flush()
        _criar_recibo_conferido(chassi_extra, modelo_dot, admin_user)
        db.session.flush()
        emitir_evento(chassi_extra, EVENTO_ESTOQUE, admin_user.id)
        emitir_evento(chassi_extra, EVENTO_MONTADA, admin_user.id)
        emitir_evento(chassi_extra, EVENTO_DISPONIVEL, admin_user.id)
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

        # Apos Fase 4: ajustar_separacao_pela_nf adiciona chassi_extra a sep,
        # depois _calcular_match detecta match natural -> BATEU.
        assert nf.status_match == NF_STATUS_BATEU, \
            f"Esperava BATEU (sep ajustada pela NF), veio {nf.status_match}"

        itens = nf.itens
        chassis_match = {it.chassi: it for it in itens}
        # Ambos chassis devem estar vinculados a separacao_item agora
        assert chassis_match[chassi_ok].separacao_item_id is not None
        assert chassis_match[chassi_extra].separacao_item_id is not None, \
            'chassi_extra foi adicionado a sep pelo ajustar_separacao_pela_nf'
        # Sem divergencia — match natural BATEU
        assert chassis_match[chassi_ok].tipo_divergencia is None
        assert chassis_match[chassi_extra].tipo_divergencia is None

        db.session.rollback()


def test_match_divergente_valor_acima_tolerancia(app, admin_user):
    """DIVERGENTE: chassi existe na separação mas valor diverge > R$ 1,00 (absoluto).

    Mudanca 2026-05-17: regra de tolerancia migrou de 1% relativo para R$ 1,00
    absoluto. Diff de R$ 345 (5%) continua sendo divergencia legitima sob ambos
    os criterios — teste mantido para garantir comportamento end-to-end.
    """
    with app.app_context():
        loja = AssaiLoja.query.first()
        chassi = f'TST_NF_DV_{_uid()}'
        _setup_separacao_com_chassi(admin_user, loja, chassi, Decimal('6900'))

        # Valor na NF: 6900 + R$ 345 de diferenca = 7245 (>> R$ 1,00 → DIVERGENTE)
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


def test_match_chassi_faturado_sem_recibo(app, admin_user):
    """DIVERGENCIA: chassi em assai_moto + sep ativa, MAS sem AssaiReciboItem
    conferido. Indica chassi cadastrado errado ou faturado sem recebimento
    fisico — bloqueia BATEU e cria divergencia CHASSI_FATURADO_SEM_RECIBO.
    """
    with app.app_context():
        loja = AssaiLoja.query.first()
        modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()
        chassi = f'TST_NF_SR_{_uid()}'

        # Setup parcial: cria moto + sep mas NAO cria AssaiReciboItem
        p = AssaiPedidoVenda(
            numero=f'TST-SR-{_uid()}', status=PEDIDO_STATUS_ABERTO,
            criado_por_id=admin_user.id,
        )
        db.session.add(p)
        db.session.flush()
        pvl = AssaiPedidoVendaLoja(pedido_id=p.id, loja_id=loja.id)
        db.session.add(pvl); db.session.flush()
        db.session.add(AssaiPedidoVendaItem(
            pedido_id=p.id, pedido_loja_id=pvl.id, loja_id=loja.id,
            modelo_id=modelo_dot.id, qtd_pedida=1,
            valor_unitario=Decimal('6900'), valor_total=Decimal('6900'),
        ))
        m = AssaiMoto(chassi=chassi, modelo_id=modelo_dot.id, cor='CINZA')
        db.session.add(m); db.session.flush()
        # NAO chamamos _criar_recibo_conferido — esse e o ponto do teste!
        emitir_evento(chassi, EVENTO_ESTOQUE, admin_user.id)
        emitir_evento(chassi, EVENTO_MONTADA, admin_user.id)
        emitir_evento(chassi, EVENTO_DISPONIVEL, admin_user.id)
        db.session.commit()

        criar_separacao_com_saldos(
            pedido_id=p.id, loja_id=loja.id,
            alocacoes=[{'modelo_id': modelo_dot.id, 'qtd': 1}],
            operador_id=admin_user.id,
        )
        db.session.commit()
        registrar_chassi(p.id, loja.id, chassi, admin_user.id)
        sep = AssaiSeparacao.query.filter_by(pedido_id=p.id, loja_id=loja.id).first()
        finalizar_separacao(sep.id, admin_user.id)
        db.session.commit()

        chave = _chave_fake()
        resultado = _make_resultado_parser(
            chave=chave, nome_dest=f'ASSAI LJ{loja.numero}',
            chassis=[chassi], valor_total=Decimal('6900'),
        )
        nf = _call_importar(resultado, chave=chave,
                            nome_dest=f'ASSAI LJ{loja.numero}',
                            admin_id=admin_user.id)

        # Deve virar DIVERGENTE com CHASSI_FATURADO_SEM_RECIBO no item
        assert nf.status_match in (NF_STATUS_DIVERGENTE, NF_STATUS_NAO_RECONCILIADO), \
            f"Esperava DIVERGENTE, veio {nf.status_match}"
        nf_item = nf.itens[0]
        assert nf_item.tipo_divergencia == 'CHASSI_FATURADO_SEM_RECIBO', \
            f"Esperava CHASSI_FATURADO_SEM_RECIBO, veio {nf_item.tipo_divergencia}"

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


# ─── Resolucao de loja_id (P0 2026-05-17) ─────────────────────────────────────
#
# Cobertura dos 3 caminhos da nova logica em nf_qpa_adapter.py:72-125:
#   1) matched-by-cnpj    — CNPJ destinatario casa com AssaiLoja.cnpj
#   2) matched-by-name-regex — fallback regex LJ\d+ (compat com NFs antigas)
#   3) no-match           — nem CNPJ nem regex resolvem
#
# Bug raiz: 2026-05-17 Rafael importou 14 NFs com destinatario_nome="SENDAS
# DISTRIBUIDORA S/A" (sem "LJ<n>") — regex falhou em 100% e loja_id ficou
# NULL. P0 adiciona match por CNPJ ANTES do regex.

def test_resolver_loja_por_cnpj_destinatario(app, admin_user):
    """matched-by-cnpj: CNPJ destinatario casa com AssaiLoja mesmo sem 'LJ' no nome."""
    with app.app_context():
        loja = AssaiLoja.query.filter(AssaiLoja.cnpj.isnot(None)).first()
        assert loja is not None and loja.cnpj, 'fixture de loja com CNPJ ausente'
        chassi = f'TST_CNPJ_{_uid()}'
        _setup_separacao_com_chassi(admin_user, loja, chassi, Decimal('6900'))

        chave = _chave_fake()
        resultado = _make_resultado_parser(
            chave=chave,
            nome_dest='SENDAS DISTRIBUIDORA S/A',  # sem 'LJ<n>'
            chassis=[chassi],
            valor_total=Decimal('6900'),
        )
        # Sobrescreve cnpj_destinatario para o CNPJ real da loja
        resultado['cnpj_destinatario'] = loja.cnpj

        nf = _call_importar(resultado, chave=chave,
                            nome_dest='SENDAS DISTRIBUIDORA S/A',
                            admin_id=admin_user.id)

        # loja_id resolvido via CNPJ -> match natural BATEU
        assert nf.loja_id == loja.id, (
            f'Esperava loja_id={loja.id} (matched-by-cnpj), '
            f'veio {nf.loja_id}'
        )
        # Como chassi bate na sep da mesma loja, status_match deve ser BATEU
        assert nf.status_match == NF_STATUS_BATEU
        db.session.rollback()


def test_resolver_loja_por_regex_fallback_quando_cnpj_nao_existe(app, admin_user):
    """matched-by-name-regex: CNPJ nao casa, mas 'LJ<n>' no nome resolve (fallback compat)."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        chassi = f'TST_REGEX_{_uid()}'
        _setup_separacao_com_chassi(admin_user, loja, chassi, Decimal('6900'))

        chave = _chave_fake()
        resultado = _make_resultado_parser(
            chave=chave,
            nome_dest=f'ASSAI LJ{loja.numero}',
            chassis=[chassi],
            valor_total=Decimal('6900'),
        )
        # CNPJ que NAO existe em assai_loja
        resultado['cnpj_destinatario'] = '99999999000199'

        nf = _call_importar(resultado, chave=chave,
                            nome_dest=f'ASSAI LJ{loja.numero}',
                            admin_id=admin_user.id)

        # CNPJ nao casou -> caiu no regex -> loja resolvida
        assert nf.loja_id == loja.id
        assert nf.status_match == NF_STATUS_BATEU
        db.session.rollback()


def test_resolver_loja_no_match_quando_cnpj_e_regex_falham(app, admin_user):
    """no-match: nem CNPJ nem regex resolvem loja_id. NF fica NAO_RECONCILIADO."""
    with app.app_context():
        chave = _chave_fake()
        resultado = _make_resultado_parser(
            chave=chave,
            nome_dest='SUPERMERCADOS SEM NUMERO LTDA',  # sem 'LJ<n>'
            chassis=[f'TST_NM_{_uid()}'],
            valor_total=Decimal('6900'),
        )
        # CNPJ que NAO existe em assai_loja
        resultado['cnpj_destinatario'] = '88888888000188'

        nf = _call_importar(resultado, chave=chave,
                            nome_dest='SUPERMERCADOS SEM NUMERO LTDA',
                            admin_id=admin_user.id)

        # Nenhum caminho resolveu -> loja_id segue NULL
        assert nf.loja_id is None
        assert nf.status_match == NF_STATUS_NAO_RECONCILIADO
        db.session.rollback()


def test_tolerancia_valor_borda_um_real(app, admin_user):
    """Borda R$ 1,00: diff de R$ 1,00 EXATO bate (<=); diff de R$ 1,01 diverge.

    Regra: TOLERANCIA_VALOR_ABS = Decimal('1.00'), comparacao `diff_abs > TOL`
    (estritamente maior). Logo R$ 1,00 ainda eh aceito como match.
    """
    with app.app_context():
        loja = AssaiLoja.query.first()

        # Caso 1: diff exatamente R$ 1,00 -> BATEU (limiar inclusivo)
        chassi_ok = f'TST_BORDA_OK_{_uid()}'
        _setup_separacao_com_chassi(admin_user, loja, chassi_ok, Decimal('6900'))
        chave1 = _chave_fake()
        resultado1 = _make_resultado_parser(
            chave=chave1,
            nome_dest=f'ASSAI LJ{loja.numero}',
            chassis=[chassi_ok],
            valor_total=Decimal('6901'),  # diff R$ 1,00
        )
        nf1 = _call_importar(resultado1, chave=chave1,
                             nome_dest=f'ASSAI LJ{loja.numero}',
                             admin_id=admin_user.id)
        assert nf1.status_match == NF_STATUS_BATEU, (
            f'diff R$ 1,00 deveria BATER (tol inclusiva), veio {nf1.status_match}'
        )
        assert nf1.itens[0].tipo_divergencia is None

        # Caso 2: diff R$ 1,01 -> DIVERGENTE
        chassi_div = f'TST_BORDA_DV_{_uid()}'
        _setup_separacao_com_chassi(admin_user, loja, chassi_div, Decimal('6900'))
        chave2 = _chave_fake()
        resultado2 = _make_resultado_parser(
            chave=chave2,
            nome_dest=f'ASSAI LJ{loja.numero}',
            chassis=[chassi_div],
            valor_total=Decimal('6901.01'),  # diff R$ 1,01
        )
        nf2 = _call_importar(resultado2, chave=chave2,
                             nome_dest=f'ASSAI LJ{loja.numero}',
                             admin_id=admin_user.id)
        assert nf2.itens[0].tipo_divergencia == 'VALOR_DIVERGENTE', (
            f'diff R$ 1,01 deveria divergir, veio tipo={nf2.itens[0].tipo_divergencia}'
        )
        db.session.rollback()


def test_resolver_loja_cnpj_tem_prioridade_sobre_regex(app, admin_user):
    """Quando CNPJ e regex apontam para LOJAS DIFERENTES, CNPJ vence."""
    with app.app_context():
        lojas_com_cnpj = AssaiLoja.query.filter(AssaiLoja.cnpj.isnot(None)).limit(2).all()
        if len(lojas_com_cnpj) < 2:
            pytest.skip('precisa de 2 lojas com CNPJ na fixture')
        loja_via_cnpj, loja_via_regex = lojas_com_cnpj[0], lojas_com_cnpj[1]

        chassi = f'TST_PRIO_{_uid()}'
        # Setup separacao na loja do CNPJ (BATEU final esperado)
        _setup_separacao_com_chassi(admin_user, loja_via_cnpj, chassi, Decimal('6900'))

        chave = _chave_fake()
        resultado = _make_resultado_parser(
            chave=chave,
            nome_dest=f'ASSAI LJ{loja_via_regex.numero}',  # regex aponta para loja errada
            chassis=[chassi],
            valor_total=Decimal('6900'),
        )
        resultado['cnpj_destinatario'] = loja_via_cnpj.cnpj  # CNPJ aponta para correta

        nf = _call_importar(resultado, chave=chave,
                            nome_dest=f'ASSAI LJ{loja_via_regex.numero}',
                            admin_id=admin_user.id)

        # CNPJ teve prioridade -> loja_id = loja_via_cnpj
        assert nf.loja_id == loja_via_cnpj.id, (
            f'CNPJ ({loja_via_cnpj.id}) deveria ter prioridade sobre '
            f'regex ({loja_via_regex.id}), veio {nf.loja_id}'
        )
        db.session.rollback()
