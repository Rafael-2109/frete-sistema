"""Testes da reversao de CarviaFrete ao desfazer fatura (paridade Nacom).

Causa-raiz (embarque 6075): excluir/desanexar a FaturaTransportadora soltava
apenas a FK `fatura_transportadora_id` do CarviaFrete, deixando-o FATURADO +
valor_cte preenchido -> invisivel ao Lancamento Freteiros (filtra valor_cte IS
NULL). O helper `CarviaFreteService.reverter_frete_ao_desfazer_fatura` espelha
o `cancelar_cte` Nacom:
  - freteiro -> PENDENTE total (limpa valor_cte/considerado/pago + conferencia)
    => reaparece no Lancamento;
  - demais   -> FATURADO -> CONFERIDO (preserva CTe real e conferencia).
"""
from datetime import date

from app.carvia.services.documentos.carvia_frete_service import CarviaFreteService


def _criar_transportadora(db, *, freteiro, cnpj='90000000000190'):
    from app.transportadoras.models import Transportadora
    t = Transportadora(
        cnpj=cnpj,
        razao_social='TRANSP REVERSAO TESTE',
        cidade='SAO PAULO',
        uf='SP',
        freteiro=freteiro,
    )
    db.session.add(t)
    db.session.flush()
    return t


def _criar_fatura(db, transp):
    from app.carvia.models import CarviaFaturaTransportadora
    ft = CarviaFaturaTransportadora(
        transportadora_id=transp.id,
        numero_fatura=f'FT-REV-{transp.id}',
        data_emissao=date(2026, 6, 26),
        valor_total=180,
        criado_por='test@bot',
    )
    db.session.add(ft)
    db.session.flush()
    return ft


def _criar_frete_faturado(db, transp, *, valor=180.0):
    from app.carvia.models import CarviaFrete
    ft = _criar_fatura(db, transp)
    f = CarviaFrete(
        transportadora_id=transp.id,
        embarque_id=None,
        cnpj_emitente='11111111000111',
        cnpj_destino='22222222000122',
        uf_destino='SP',
        cidade_destino='SAO PAULO',
        tipo_carga='DIRETA',
        valor_cotado=162.55,
        valor_cte=valor,
        valor_considerado=valor,
        valor_pago=valor,
        status='FATURADO',
        status_conferencia='APROVADO',
        conferido_por='Rafael',
        conferido_em=date(2026, 6, 26),
        detalhes_conferencia={'origem': 'lancamento_freteiros_unificado'},
        fatura_transportadora_id=ft.id,  # sera solto pela reversao
        criado_por='test@bot',
    )
    db.session.add(f)
    db.session.flush()
    return f


def test_reverter_frete_freteiro_volta_pendente(db):
    transp = _criar_transportadora(db, freteiro=True)
    frete = _criar_frete_faturado(db, transp, valor=180.0)

    CarviaFreteService.reverter_frete_ao_desfazer_fatura(frete)

    assert frete.fatura_transportadora_id is None
    assert frete.valor_cte is None          # criterio de pendencia -> reaparece
    assert frete.valor_considerado is None
    assert frete.valor_pago is None
    assert frete.status == 'PENDENTE'
    assert frete.status_conferencia == 'PENDENTE'
    assert frete.conferido_por is None
    assert frete.conferido_em is None
    assert frete.detalhes_conferencia is None
    # valor_cotado (gravado na portaria) e preservado
    assert float(frete.valor_cotado) == 162.55


def test_reverter_frete_cancelado_nao_ressuscita(db):
    """Frete CANCELADO vinculado a FT: reverter SO solta a FK, nao volta a PENDENTE
    (senao um frete cancelado reapareceria no Lancamento e poderia ser refaturado)."""
    transp = _criar_transportadora(db, freteiro=True, cnpj='96000000000196')
    frete = _criar_frete_faturado(db, transp, valor=180.0)
    frete.status = 'CANCELADO'
    db.session.flush()

    CarviaFreteService.reverter_frete_ao_desfazer_fatura(frete)

    assert frete.fatura_transportadora_id is None
    assert frete.status == 'CANCELADO'  # NAO ressuscita


def test_reverter_frete_nao_freteiro_volta_conferido(db):
    transp = _criar_transportadora(db, freteiro=False, cnpj='91000000000191')
    frete = _criar_frete_faturado(db, transp, valor=300.0)

    CarviaFreteService.reverter_frete_ao_desfazer_fatura(frete)

    assert frete.fatura_transportadora_id is None
    assert frete.status == 'CONFERIDO'             # nao volta a PENDENTE
    assert float(frete.valor_cte) == 300.0         # CTe real preservado
    assert frete.status_conferencia == 'APROVADO'  # conferencia preservada
    assert frete.conferido_por == 'Rafael'


def test_reverter_frete_freteiro_reaparece_no_lancamento(db):
    """Apos reverter, o frete freteiro volta a listar_fretes_carvia_pendentes."""
    from app.carvia.services.financeiro.lancamento_freteiro_service import (
        listar_fretes_carvia_pendentes_freteiro,
    )
    from app.embarques.models import Embarque

    emb = Embarque(status='ativo', criado_por='test@bot')
    db.session.add(emb)
    db.session.flush()

    transp = _criar_transportadora(db, freteiro=True, cnpj='92000000000192')
    frete = _criar_frete_faturado(db, transp, valor=180.0)
    frete.embarque_id = emb.id
    db.session.flush()

    # Antes: faturado (valor_cte preenchido) -> NAO aparece
    assert listar_fretes_carvia_pendentes_freteiro(transp.id) == []

    CarviaFreteService.reverter_frete_ao_desfazer_fatura(frete)
    db.session.flush()

    res = listar_fretes_carvia_pendentes_freteiro(transp.id)
    assert len(res) == 1
    assert res[0]['id'] == frete.id


def test_excluir_ft_conferida_bloqueia(db):
    """Paridade Nacom (excluir_fatura) + gap A-7: FT CONFERIDA nao pode ser
    excluida — exige reabrir a conferencia antes."""
    from unittest.mock import patch
    from app.carvia.models import CarviaFaturaTransportadora
    from app.carvia.services.admin.admin_service import AdminService

    transp = _criar_transportadora(db, freteiro=True, cnpj='93000000000193')
    ft = CarviaFaturaTransportadora(
        transportadora_id=transp.id,
        numero_fatura='FT-CONF',
        data_emissao=date(2026, 6, 26),
        valor_total=100,
        status_conferencia='CONFERIDO',
        criado_por='test@bot',
    )
    db.session.add(ft)
    db.session.flush()

    svc = AdminService()
    with patch.object(db.session, 'commit', db.session.flush):
        res = svc.excluir_fatura_transportadora(
            ft.id, 'tentar excluir conferida', 'test@bot',
        )

    assert res['sucesso'] is False
    msg = res['mensagem'].lower()
    assert 'conferid' in msg or 'reabr' in msg
    assert db.session.get(CarviaFaturaTransportadora, ft.id) is not None


def test_excluir_ft_reverte_frete_freteiro(db):
    """Exclusao da FT (reaberta) reverte o CarviaFrete freteiro a PENDENTE."""
    from unittest.mock import patch
    from app.carvia.models import CarviaFaturaTransportadora, CarviaFrete
    from app.carvia.services.admin.admin_service import AdminService

    transp = _criar_transportadora(db, freteiro=True, cnpj='94000000000194')
    ft = CarviaFaturaTransportadora(
        transportadora_id=transp.id,
        numero_fatura='FT-REV-EXC',
        data_emissao=date(2026, 6, 26),
        valor_total=180,
        status_conferencia='PENDENTE',  # reaberta antes de excluir
        criado_por='test@bot',
    )
    db.session.add(ft)
    db.session.flush()
    frete = CarviaFrete(
        transportadora_id=transp.id,
        cnpj_emitente='11111111000111',
        cnpj_destino='22222222000122',
        uf_destino='SP',
        cidade_destino='SAO PAULO',
        tipo_carga='DIRETA',
        valor_cotado=162.55,
        valor_cte=180,
        valor_considerado=180,
        valor_pago=180,
        status='FATURADO',
        status_conferencia='APROVADO',
        fatura_transportadora_id=ft.id,
        criado_por='test@bot',
    )
    db.session.add(frete)
    db.session.flush()
    frete_id = frete.id

    svc = AdminService()
    with patch.object(db.session, 'commit', db.session.flush):
        res = svc.excluir_fatura_transportadora(
            ft.id, 'exclusao reverte frete', 'test@bot',
        )

    db.session.expire_all()
    assert res['sucesso'] is True, res.get('mensagem')
    frete_db = db.session.get(CarviaFrete, frete_id)
    assert frete_db.fatura_transportadora_id is None
    assert frete_db.valor_cte is None
    assert frete_db.status == 'PENDENTE'
    assert frete_db.status_conferencia == 'PENDENTE'


def test_desanexar_subcontrato_reverte_frete_freteiro(client, db):
    """Desanexar um subcontrato de FT (nao conferida) reverte o frete freteiro."""
    from app.auth.models import Usuario
    from app.carvia.models import (
        CarviaFaturaTransportadora, CarviaFrete, CarviaSubcontrato,
    )

    user = Usuario(
        nome='Op CarVia', email='op.carvia@test.bot', senha_hash='x',
        perfil='administrador', status='ativo', sistema_carvia=True,
    )
    db.session.add(user)
    transp = _criar_transportadora(db, freteiro=True, cnpj='95000000000195')
    ft = CarviaFaturaTransportadora(
        transportadora_id=transp.id, numero_fatura='FT-DESANEXA',
        data_emissao=date(2026, 6, 26), valor_total=180,
        status_conferencia='PENDENTE', criado_por='test@bot',
    )
    db.session.add(ft)
    db.session.flush()
    frete = CarviaFrete(
        transportadora_id=transp.id, cnpj_emitente='11111111000111',
        cnpj_destino='22222222000122', uf_destino='SP', cidade_destino='SP',
        tipo_carga='DIRETA', valor_cotado=162.55, valor_cte=180,
        valor_considerado=180, valor_pago=180, status='FATURADO',
        status_conferencia='APROVADO', fatura_transportadora_id=ft.id,
        criado_por='test@bot',
    )
    db.session.add(frete)
    db.session.flush()
    sub = CarviaSubcontrato(
        transportadora_id=transp.id, fatura_transportadora_id=ft.id,
        status='FATURADO', cte_numero='Sub-099', frete_id=frete.id,
        valor_acertado=180, criado_por='test@bot',
    )
    db.session.add(sub)
    db.session.flush()
    frete_id, sub_id = frete.id, sub.id

    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)

    resp = client.post(
        f'/carvia/faturas-transportadora/{ft.id}/desanexar-subcontrato/{sub_id}'
    )
    assert resp.status_code == 200, resp.data[:300]

    db.session.expire_all()
    frete_db = db.session.get(CarviaFrete, frete_id)
    assert frete_db.fatura_transportadora_id is None
    assert frete_db.valor_cte is None
    assert frete_db.status == 'PENDENTE'
