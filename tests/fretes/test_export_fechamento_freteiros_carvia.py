"""Integração do export 'Fechamento Freteiros' com a parte CarVia (2026-06-24).

Garante o delta pedido pelo Rafael: 3 abas — Detalhamento (Nacom + CarVia na
MESMA aba, diferenciado pela coluna 'Operação'), 'Resumo Nacom' e 'Resumo Carvia'.
Verifica por EXECUÇÃO (HTTP + leitura do xlsx) que:
  - os fretes CarVia entram na aba 'Detalhamento' com Operação='CARVIA';
  - os custos de entrega CarVia entram na mesma aba e SOMAM no 'Resumo Carvia';
  - a aba separada antiga 'Detalhamento CarVia' não existe mais (regressão).
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pandas as pd


def _criar_admin(db):
    from app.auth.models import Usuario
    u = Usuario(
        nome='Admin Teste',
        email='admin.fechamento@test.bot',
        senha_hash='x',
        perfil='administrador',
        status='ativo',
    )
    db.session.add(u)
    db.session.flush()
    return u


def _criar_freteiro(db):
    from app.transportadoras.models import Transportadora
    t = Transportadora(
        cnpj='88888888000188',
        razao_social='FRETEIRO CARVIA TESTE',
        cidade='SAO PAULO',
        uf='SP',
        freteiro=True,
        banco='Banco Teste',
        agencia='0001',
        conta='12345-6',
        pix='88888888000188',
    )
    db.session.add(t)
    db.session.flush()
    return t


def _criar_frete_carvia(db, transp, *, valor_cotado=162.55, numeros_nfs='5187'):
    from app.carvia.models import CarviaFrete
    f = CarviaFrete(
        transportadora_id=transp.id,
        embarque_id=None,
        cnpj_emitente='11111111000111',
        nome_emitente='EMITENTE T',
        cnpj_destino='22222222000122',
        nome_destino='CLIENTE CARVIA T',
        uf_destino='SP',
        cidade_destino='SAO PAULO',
        tipo_carga='DIRETA',
        peso_total=164.0,
        valor_total_nfs=5000.0,
        quantidade_nfs=1,
        numeros_nfs=numeros_nfs,
        valor_cotado=valor_cotado,
        status='PENDENTE',
        criado_por='test@bot',
    )
    db.session.add(f)
    db.session.flush()
    return f


def test_export_inclui_carvia_na_aba_detalhamento_e_resumo(client, db):
    from app.carvia.models import CarviaCustoEntrega
    from app.carvia.services.financeiro.lancamento_freteiro_service import (
        emitir_fatura_freteiro_carvia,
    )

    admin = _criar_admin(db)
    transp = _criar_freteiro(db)
    frete = _criar_frete_carvia(db, transp)

    # CE criado ANTES (pendente) e vinculado VIA emissao (fluxo Parte 2 2026-06-26):
    # assim a FT nasce integra (valor_total = frete + custo) e entra no fechamento.
    # Anexar o CE manualmente depois (sem recalcular valor_total) deixaria a FT
    # inconsistente -> aba Inconsistencias (coberto em test_export_fechamento_integridade).
    custo = CarviaCustoEntrega(
        numero_custo='CE-TEST-1',
        tipo_custo='DIARIA',
        valor=Decimal('50.00'),
        data_custo=date(2026, 6, 30),
        frete_id=frete.id,
        status='PENDENTE',
        criado_por='test@bot',
    )
    db.session.add(custo)
    db.session.flush()

    res = emitir_fatura_freteiro_carvia(
        transportadora_id=transp.id,
        itens=[{'frete_id': frete.id, 'valor_considerado': 162.55}],
        custos_entrega=[{'ce_id': custo.id, 'valor': 50.00}],
        data_vencimento=date(2026, 6, 30),
        usuario_nome='Rafael Teste',
    )
    fatura_id = res['fatura_id']

    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin.id)

    resp = client.get('/fretes/faturas/exportar-fechamento-freteiros')
    assert resp.status_code == 200, resp.data[:300]
    assert 'spreadsheetml' in resp.headers['Content-Type']

    sheets = pd.read_excel(BytesIO(resp.data), sheet_name=None)

    # 3 abas: a separada antiga 'Detalhamento CarVia' NÃO existe mais
    assert 'Detalhamento' in sheets
    assert 'Resumo Carvia' in sheets
    assert 'Detalhamento CarVia' not in sheets

    det = sheets['Detalhamento']
    # CarVia na MESMA aba, diferenciado por 'Operação'
    assert (det['Operação'] == 'CARVIA').any()
    # frete + custo de entrega aparecem
    assert (det['Tipo'] == 'Frete').any()
    assert (det['Tipo'] == 'DIARIA').any()

    # Resumo Carvia soma frete (162,55) + custo (50,00) = 212,55
    resumo = sheets['Resumo Carvia']
    assert len(resumo) == 1
    valor_str = str(resumo.iloc[0]['Valor Total'])
    valor = float(valor_str.replace('.', '').replace(',', '.'))
    assert valor == 212.55
