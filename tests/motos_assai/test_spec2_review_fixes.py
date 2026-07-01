"""Regressao dos 5 defeitos achados na revisao 4-maos do Spec 2 (2026-07-01).

Cada teste codifica o comportamento CORRETO (deve falhar antes do fix):
  #1 resolucao_service: double-submit nao duplica CONSUMO no ledger
  #2 pendencias route: EstoqueError vira flash (302), nao 500
  #3 pendencia_service.reclassificar: nao-fisica->fisica em moto fora do estoque bloqueia;
     em moto em estoque emite PENDENTE (lastro coerente)
  #4 movimento_service.canibalizar: doador fora do estoque bloqueia
  #5 compra_peca_nova: getlist alinhado (linha com peca vazia nao desloca qtd/custo)
"""
import uuid
from decimal import Decimal

import pytest
from werkzeug.datastructures import MultiDict

from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiPecaCompraItem,
    PENDENCIA_TRATATIVA_USAR_ESTOQUE,
    PENDENCIA_CATEGORIA_AVARIA, PENDENCIA_CATEGORIA_FALTA_PECA,
    PENDENCIA_ORIGEM_GALPAO, PENDENCIA_ORIGEM_POS_VENDA_CLIENTE,
    EVENTO_FATURADA, EVENTO_PENDENTE, EVENTO_DISPONIVEL,
)
from app.motos_assai.services.peca_service import criar_peca
from app.motos_assai.services.movimento_service import (
    registrar_entrada, saldo, canibalizar, EstoqueError,
)
from app.motos_assai.services.pendencia_service import (
    abrir_pendencia, reclassificar, PendenciaError,
)
from app.motos_assai.services.moto_evento_service import status_efetivo, emitir_evento
from app.motos_assai.services.resolucao_service import resolver_com_tratativa, ResolucaoError


def _uid(p): return f'{p}{uuid.uuid4().hex[:6].upper()}'


def _moto(chassi):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
    db.session.flush()


# ---- #1 ----
def test_double_submit_nao_duplica_consumo(app, admin_user):
    with app.app_context():
        chassi = _uid('F1')
        _moto(chassi)
        p = criar_peca(nome=_uid('PZ'), operador_id=admin_user.id)
        registrar_entrada(peca_id=p.id, quantidade=5, custo_unitario='10.00', operador_id=admin_user.id)
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='falta', operador_id=admin_user.id)
        db.session.flush()
        resolver_com_tratativa(pendencia_id=f.id, tratativa=PENDENCIA_TRATATIVA_USAR_ESTOQUE,
                               resolucao_descricao='ok', operador_id=admin_user.id,
                               peca_id=p.id, quantidade=1)
        db.session.flush()
        # 2o submit da MESMA ficha (ja resolvida) deve ser rejeitado, sem novo consumo
        with pytest.raises(ResolucaoError):
            resolver_com_tratativa(pendencia_id=f.id, tratativa=PENDENCIA_TRATATIVA_USAR_ESTOQUE,
                                   resolucao_descricao='ok', operador_id=admin_user.id,
                                   peca_id=p.id, quantidade=1)
        db.session.flush()
        assert saldo(p.id) == Decimal('4.000')  # baixou 1x, nao 2x
        db.session.rollback()


# ---- #2 ----
def test_doador_inexistente_vira_flash_nao_500(login_admin, app, admin_user):
    with app.app_context():
        chassi = _uid('F2')
        _moto(chassi)
        p = criar_peca(nome=_uid('PZ'), operador_id=admin_user.id)
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='falta', operador_id=admin_user.id)
        db.session.commit()
        pid = f.id; peca_id = p.id
    resp = login_admin.post(f'/motos-assai/pendencias/{pid}/resolver', data={
        'acao': 'resolver', 'tratativa': 'USAR_OUTRA_MOTO', 'peca_id': str(peca_id),
        'quantidade': '1', 'chassi_doador': 'NAOEXISTE999', 'resolucao_descricao': 'x'})
    assert resp.status_code == 302  # redirect com flash, nao 500 nem excecao


# ---- #3a ----
def test_reclassificar_fisica_moto_faturada_bloqueia(app, admin_user):
    with app.app_context():
        chassi = _uid('F3')
        _moto(chassi)
        emitir_evento(chassi, EVENTO_FATURADA, operador_id=admin_user.id)  # vendida
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_AVARIA,
                            origem=PENDENCIA_ORIGEM_POS_VENDA_CLIENTE, descricao='reclamacao',
                            operador_id=admin_user.id)
        db.session.commit()  # persiste o setup (senao o rollback pos-excecao o apaga)
        assert f.evento_pendente_id is None
        with pytest.raises(PendenciaError):
            reclassificar(pendencia_id=f.id, categoria=PENDENCIA_CATEGORIA_AVARIA,
                          origem=PENDENCIA_ORIGEM_GALPAO, operador_id=admin_user.id)
        db.session.rollback()
        assert status_efetivo(chassi) == EVENTO_FATURADA  # continua vendida


# ---- #3b ----
def test_reclassificar_fisica_moto_em_estoque_emite_pendente(app, admin_user):
    with app.app_context():
        chassi = _uid('F3B')
        _moto(chassi)
        emitir_evento(chassi, EVENTO_DISPONIVEL, operador_id=admin_user.id)  # em estoque
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_AVARIA,
                            origem=PENDENCIA_ORIGEM_POS_VENDA_CLIENTE, descricao='reclamacao',
                            operador_id=admin_user.id)
        db.session.flush()
        assert f.evento_pendente_id is None
        reclassificar(pendencia_id=f.id, categoria=PENDENCIA_CATEGORIA_AVARIA,
                      origem=PENDENCIA_ORIGEM_GALPAO, operador_id=admin_user.id)
        db.session.flush()
        assert f.evento_pendente_id is not None      # lastro fisico coerente
        assert status_efetivo(chassi) == EVENTO_PENDENTE
        db.session.rollback()


# ---- #4 ----
def test_canibalizar_doador_faturado_bloqueia(app, admin_user):
    with app.app_context():
        recep = _uid('F4R'); doad = _uid('F4D')
        _moto(recep); _moto(doad)
        emitir_evento(doad, EVENTO_FATURADA, operador_id=admin_user.id)  # doador vendido
        p = criar_peca(nome=_uid('PZ'), operador_id=admin_user.id)
        f = abrir_pendencia(chassi=recep, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='falta', operador_id=admin_user.id)
        db.session.commit()  # persiste o setup (senao o rollback pos-excecao o apaga)
        with pytest.raises(EstoqueError):
            canibalizar(peca_id=p.id, quantidade=1, chassi_origem=doad, chassi_destino=recep,
                        pendencia_id=f.id, operador_id=admin_user.id)
        db.session.rollback()
        assert status_efetivo(doad) == EVENTO_FATURADA  # continua vendida


# ---- #5 ----
def test_compra_nova_getlist_alinha_indices(login_admin, app, admin_user):
    with app.app_context():
        pa = criar_peca(nome=_uid('PA'), operador_id=admin_user.id)
        pb = criar_peca(nome=_uid('PB'), operador_id=admin_user.id)
        db.session.commit()
        id_a = pa.id; id_b = pb.id
    # 3 linhas; a do meio com peca vazia mas qtd preenchida (MultiDict preserva
    # chaves repetidas — o test client exige mapping, nao lista de tuplas)
    data = MultiDict([
        ('tipo', 'COMPRA'), ('fornecedor', 'MOTOCHEFE'),
        ('peca_id', str(id_a)), ('quantidade', '5'), ('custo_estimado', '1,00'),
        ('peca_id', ''),        ('quantidade', '99'), ('custo_estimado', '2,00'),
        ('peca_id', str(id_b)), ('quantidade', '3'),  ('custo_estimado', '3,00'),
    ])
    resp = login_admin.post('/motos-assai/compras-peca/nova', data=data)
    assert resp.status_code in (302, 200)
    with app.app_context():
        itens = {it.peca_id: it for it in AssaiPecaCompraItem.query.filter(
            AssaiPecaCompraItem.peca_id.in_([id_a, id_b])).all()}
        assert id_a in itens and id_b in itens
        assert itens[id_a].quantidade == Decimal('5')
        assert itens[id_b].quantidade == Decimal('3')  # nao '99' da linha vazia
