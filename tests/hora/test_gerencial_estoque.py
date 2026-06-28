"""KPIs de Estoque & Giro (F4.1) e Suprimento (F4.2) da seção Gerencial.

Estado da moto = último evento (MAX(id)). Testes escopam à loja única do teste
(lojas_permitidas) para isolar o resíduo do banco de teste local.
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

from app import db as _db
from app.hora.services.gerencial.filtros import Filtros
from app.utils.timezone import agora_brasil_naive


def _filtros(loja, ini=date(2026, 6, 1), fim=date(2026, 6, 30)):
    return Filtros(data_ini=ini, data_fim=fim, granularidade='dia',
                   loja_id=None, lojas_permitidas=[loja.id])


def _moto_eventos(loja, modelo, eventos):
    """Cria HoraMoto + eventos (tipo, dias_atras) em ordem (id crescente)."""
    from app.hora.models import HoraMoto, HoraMotoEvento
    chassi = f'M{uuid.uuid4().hex[:18].upper()}'
    _db.session.add(HoraMoto(numero_chassi=chassi, modelo_id=modelo.id, cor='PRETA'))
    _db.session.flush()
    base = agora_brasil_naive()
    for tipo, dias in eventos:
        _db.session.add(HoraMotoEvento(
            numero_chassi=chassi, tipo=tipo, loja_id=loja.id,
            timestamp=base - timedelta(days=dias),
        ))
        _db.session.flush()  # id crescente preserva a ordem (MAX(id) = último)
    return chassi


# ───────────────────────── Estoque / Estado / Aging / Giro ──────────────────

def test_estado_atual_pega_max_id(db, loja_factory, modelo_moto):
    from app.hora.services.gerencial import estoque_kpi_service as eks
    loja = loja_factory()
    # RECEBIDA depois VENDIDA -> estado atual = VENDIDA (fora de estoque)
    _moto_eventos(loja, modelo_moto, [('RECEBIDA', 10), ('VENDIDA', 0)])
    estoque = eks.estoque_por_loja_modelo(_filtros(loja))
    assert sum(r['qtd'] for r in estoque) == 0


def test_estoque_conta_em_estoque(db, loja_factory, modelo_moto):
    from app.hora.services.gerencial import estoque_kpi_service as eks
    loja = loja_factory()
    _moto_eventos(loja, modelo_moto, [('RECEBIDA', 5)])             # em estoque
    _moto_eventos(loja, modelo_moto, [('RECEBIDA', 5), ('VENDIDA', 0)])  # fora
    estoque = eks.estoque_por_loja_modelo(_filtros(loja))
    assert sum(r['qtd'] for r in estoque) == 1


def test_aging_classifica_faixas(db, loja_factory, modelo_moto):
    from app.hora.services.gerencial import estoque_kpi_service as eks
    loja = loja_factory()
    _moto_eventos(loja, modelo_moto, [('RECEBIDA', 10)])   # 0-30
    _moto_eventos(loja, modelo_moto, [('RECEBIDA', 45)])   # 31-60
    _moto_eventos(loja, modelo_moto, [('RECEBIDA', 120)])  # 90+
    aging = eks.aging_estoque(_filtros(loja))
    assert aging['faixas']['0-30'] == 1
    assert aging['faixas']['31-60'] == 1
    assert aging['faixas']['90+'] == 1
    assert aging['total'] == 3


def test_giro_calcula_dias(db, loja_factory, modelo_moto, venda_factory):
    from app.hora.services.gerencial import estoque_kpi_service as eks
    loja = loja_factory()
    # moto recebida há 10 dias, vendida (FATURADO) hoje -> giro 10 dias
    chassi = _moto_eventos(loja, modelo_moto, [('RECEBIDA', 10)])
    hoje = agora_brasil_naive().date()
    venda_factory(loja=loja, status='FATURADO', data_venda=hoje,
                  itens=[{'chassi': chassi, 'preco_final': 1000, 'preco_real': None}])
    giro = eks.giro_dias(_filtros(loja, ini=hoje - timedelta(days=1), fim=hoje))
    assert giro
    assert giro[0]['dias_medios'] == 10


def test_reservadas_conta_ultimo_evento(db, loja_factory, modelo_moto):
    from app.hora.services.gerencial import estoque_kpi_service as eks
    loja = loja_factory()
    _moto_eventos(loja, modelo_moto, [('RECEBIDA', 5), ('RESERVADA', 0)])  # reservada
    _moto_eventos(loja, modelo_moto, [('RECEBIDA', 5)])                    # em estoque
    rt = eks.reservadas_em_transito(_filtros(loja))
    assert rt['reservadas'] == 1


# ───────────────────────── Suprimento (F4.2) ────────────────────────────────

def _nf_entrada(loja, modelo, itens, data_emissao=None):
    """Cria HoraNfEntrada na loja + itens (preco_real, desconsiderado)."""
    from app.hora.models import HoraNfEntrada, HoraNfEntradaItem, HoraMoto
    uid = uuid.uuid4().hex[:12].upper()
    nf = HoraNfEntrada(
        chave_44=uid.zfill(44), numero_nf=uid[:8],
        cnpj_emitente='12345678000199', cnpj_destinatario=loja.cnpj,
        loja_destino_id=loja.id, data_emissao=data_emissao or date(2026, 6, 15),
        valor_total=1000, criado_em=agora_brasil_naive(),
    )
    _db.session.add(nf)
    _db.session.flush()
    for preco, desc in itens:
        chassi = f'N{uuid.uuid4().hex[:18].upper()}'
        _db.session.add(HoraMoto(numero_chassi=chassi, modelo_id=modelo.id, cor='PRETA'))
        _db.session.flush()
        _db.session.add(HoraNfEntradaItem(
            nf_id=nf.id, numero_chassi=chassi,
            preco_real=Decimal(str(preco)), desconsiderado=desc,
        ))
    _db.session.flush()
    return nf


def test_custo_medio_entrada_ignora_desconsiderado(db, loja_factory, modelo_moto):
    from app.hora.services.gerencial import suprimento_kpi_service as sks
    loja = loja_factory()
    # 1000 normal + 5000 desconsiderado -> custo médio do modelo = 1000
    _nf_entrada(loja, modelo_moto, [(1000, False), (5000, True)])
    res = sks.custo_medio_entrada(_filtros(loja))
    assert len(res) == 1
    assert res[0]['custo_medio'] == Decimal('1000')


def test_suprimento_funcoes_retornam_estrutura(db, loja_factory, modelo_moto):
    from app.hora.services.gerencial import suprimento_kpi_service as sks
    loja = loja_factory()
    lt = sks.lead_time_recebimento(_filtros(loja))
    assert 'dias_medios_nf_recebimento' in lt
    assert isinstance(sks.taxa_divergencia(_filtros(loja)), list)
    assert isinstance(sks.desvio_custo(_filtros(loja)), list)


def test_lead_time_recebimento_ignora_provisorias(db, loja_factory, modelo_moto):
    """Recebimento sem NF (provisória, data_emissao=hoje -> lead ~0) não pode
    diluir o lead time fiscal; só NF REAL conta. (fix auditoria BAIXA #4)"""
    from app.hora.services.gerencial import suprimento_kpi_service as sks
    from app.hora.services import recebimento_service
    hoje = agora_brasil_naive().date()
    loja = loja_factory()

    # REAL: emissão há 10 dias, recebido hoje -> lead 10
    nf = _nf_entrada(loja, modelo_moto, [(1000, False)], data_emissao=hoje - timedelta(days=10))
    nf.tipo = 'REAL'
    _db.session.flush()
    recebimento_service.iniciar_recebimento(nf_id=nf.id, loja_id=loja.id, operador='tester')

    # PROVISÓRIO: emissão e recebimento hoje -> lead 0 (não deve entrar na média)
    recebimento_service.criar_recebimento_sem_nf(loja_id=loja.id, operador='tester')
    _db.session.expire_all()

    lt = sks.lead_time_recebimento(_filtros(loja, ini=hoje - timedelta(days=30), fim=hoje))
    assert lt['dias_medios_nf_recebimento'] == 10.0  # só o REAL; provisória excluída


# ───────────────────────── Smoke das telas (renderização autenticada) ────────

def test_estoque_renderiza_autenticado(client_admin, loja_factory, modelo_moto):
    loja = loja_factory()
    _moto_eventos(loja, modelo_moto, [('RECEBIDA', 5)])
    r = client_admin.get(f'/hora/gerencial/estoque?loja_id={loja.id}')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Em estoque' in body
    assert 'ger-chart-aging' in body


def test_suprimento_renderiza_autenticado(client_admin, loja_factory, modelo_moto):
    loja = loja_factory()
    _nf_entrada(loja, modelo_moto, [(1000, False)])
    r = client_admin.get(f'/hora/gerencial/suprimento?loja_id={loja.id}&data_ini=2026-06-01&data_fim=2026-06-30')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Lead time' in body
    assert 'Custo médio de entrada' in body
