"""Testa o provisionador idempotente das SAs+crons da automação da SAÍDA (infra-Odoo).
dry-run-first: `verificar` é READ-only (núcleo do monitor anti-upgrade); `provisionar`
NÃO escreve sem `dry_run=False`. Os bodies são a fonte de verdade (Git)."""
from app.odoo.estoque.provisioning.sa_retorno_industrializacao import (
    SaRetornoIndustrializacaoProvisioner as Prov,
    SA_G1_NAME, SA_G2_NAME, CRON_G1_NAME, CRON_G2_NAME,
    SA_BODY_G1, SA_BODY_G2,
)


def _dom_get(domain, field):
    for t in domain:
        if isinstance(t, (list, tuple)) and len(t) == 3 and t[0] == field:
            return t[2]
    return None


class FakeOdoo:
    """Modela ir.model + ir.actions.server + ir.cron e grava execute_kw (create/write)."""
    def __init__(self, *, sas=None, crons=None):
        self.sas = sas or {}        # name -> {id, code}
        self.crons = crons or {}    # name -> {id, active, ir_actions_server_id}
        self.escritas = []

    def search_read(self, model, domain, fields=None, **k):
        if model == 'ir.model':
            return [{'id': 100}]
        if model == 'ir.actions.server':
            name = _dom_get(domain, 'name')
            sa = self.sas.get(name)
            return [{'id': sa['id'], 'name': name, 'code': sa['code'], 'state': 'code', 'model_id': [100, 'account.move']}] if sa else []
        if model == 'ir.cron':
            name = _dom_get(domain, 'name')
            c = self.crons.get(name)
            return [{'id': c['id'], 'name': name, 'active': c['active'],
                     'interval_number': 5, 'interval_type': 'minutes',
                     'ir_actions_server_id': c.get('ir_actions_server_id')}] if c else []
        return []

    def execute_kw(self, model, method, args, kw=None):
        self.escritas.append((model, method, args))
        return 999


def _saudavel():
    """Estado íntegro: 2 SAs com code == body + 2 crons ativos apontando p/ as SAs certas."""
    return FakeOdoo(
        sas={SA_G1_NAME: {'id': 1, 'code': SA_BODY_G1}, SA_G2_NAME: {'id': 2, 'code': SA_BODY_G2}},
        crons={CRON_G1_NAME: {'id': 10, 'active': True, 'ir_actions_server_id': [1, 'g1']},
               CRON_G2_NAME: {'id': 11, 'active': True, 'ir_actions_server_id': [2, 'g2']}})


# ── verificar (monitor anti-upgrade) ──────────────────────────────────────────
def test_verificar_ok_quando_tudo_integro():
    res = Prov(_saudavel()).verificar()
    assert res['ok'] is True
    assert res['acao_necessaria'] is False
    assert all(d['status'] == 'OK' for d in res['detalhes'])


def test_verificar_detecta_sa_ausente():
    fake = _saudavel()
    del fake.sas[SA_G1_NAME]                       # upgrade CIEL IT apagou a SA G1
    res = Prov(fake).verificar()
    assert res['acao_necessaria'] is True
    g1 = next(d for d in res['detalhes'] if d['artefato'] == SA_G1_NAME)
    assert g1['status'] == 'AUSENTE'


def test_verificar_detecta_code_drift():
    fake = _saudavel()
    fake.sas[SA_G2_NAME]['code'] = SA_BODY_G2 + '\n# alterado por terceiro\n'
    res = Prov(fake).verificar()
    assert res['acao_necessaria'] is True
    g2 = next(d for d in res['detalhes'] if d['artefato'] == SA_G2_NAME)
    assert g2['status'] == 'CODE_DIVERGENTE'


def test_verificar_detecta_cron_inativo_e_link_errado():
    fake = _saudavel()
    fake.crons[CRON_G1_NAME]['active'] = False
    fake.crons[CRON_G2_NAME]['ir_actions_server_id'] = [999, 'outra']
    res = Prov(fake).verificar()
    assert res['acao_necessaria'] is True
    g1 = next(d for d in res['detalhes'] if d['artefato'] == CRON_G1_NAME)
    g2 = next(d for d in res['detalhes'] if d['artefato'] == CRON_G2_NAME)
    assert g1['status'] == 'INATIVO'
    assert g2['status'] == 'SA_LINK_ERRADO'


def test_verificar_e_read_only():
    fake = _saudavel()
    Prov(fake).verificar()
    assert fake.escritas == []


# ── provisionar (dry-run-first) ───────────────────────────────────────────────
def test_provisionar_dry_run_nao_escreve():
    fake = FakeOdoo()                              # nada existe
    res = Prov(fake).provisionar(dry_run=True)
    assert res['dry_run'] is True
    assert fake.escritas == []                     # 🔴 NADA escrito no Odoo
    acoes = {p['acao'] for p in res['plano']}
    assert acoes == {'CREATE_SA'}                  # planeja criar as 2 SAs


def test_provisionar_dry_run_detecta_noop_e_update():
    fake = _saudavel()
    fake.sas[SA_G1_NAME]['code'] = SA_BODY_G1 + '\n# drift\n'   # G1 divergente, G2 igual
    res = Prov(fake).provisionar(dry_run=True)
    by_name = {p['name']: p['acao'] for p in res['plano'] if 'name' in p}
    assert by_name[SA_G1_NAME] == 'UPDATE_SA'
    assert by_name[SA_G2_NAME] == 'NOOP_SA'
    assert fake.escritas == []


def test_provisionar_confirmar_cria_sa_ausente():
    fake = FakeOdoo(sas={SA_G2_NAME: {'id': 2, 'code': SA_BODY_G2}})   # só G2 existe
    Prov(fake).provisionar(dry_run=False)
    metodos = [(m, meth) for (m, meth, _a) in fake.escritas]
    assert ('ir.actions.server', 'create') in metodos      # cria a G1 ausente
    # G2 já bate o body → NÃO reescreve
    assert ('ir.actions.server', 'write') not in metodos


def test_provisionar_confirmar_atualiza_code_divergente():
    fake = _saudavel()
    fake.sas[SA_G1_NAME]['code'] = 'codigo antigo'
    Prov(fake).provisionar(dry_run=False)
    writes = [a for (m, meth, a) in fake.escritas if meth == 'write']
    assert writes and writes[0][0] == [1]                  # write na SA G1 (id=1)


def test_provisionar_cron_fica_gated_por_canary():
    res = Prov(_saudavel()).provisionar(dry_run=True, incluir_cron=True)
    cron = [p for p in res['plano'] if p['acao'] == 'CRON_PENDENTE_CANARY']
    assert cron and 'canary' in cron[0]['nota'].lower()
