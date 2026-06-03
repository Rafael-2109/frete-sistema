#!/usr/bin/env python3
"""S8b — GROUNDING: a 2a NF de componentes via SERVER ACTION no Odoo (READ-only).

Pergunta do Rafael: "nao e' melhor via server_action no Odoo?" (em vez de triggers no
nosso codigo Flask). Avaliar AO VIVO o que o ambiente Odoo suporta:

1. base.automation: quantas existem, em que modelos, com que trigger (on_create/on_write/
   on_time/on_state) — da p/ disparar uma server action AUTOMATICAMENTE quando a NF do PA
   e' posted/transmitida ou quando o picking de retorno e' validado?
2. ir.cron: como o robo 1512 e' disparado hoje (cron? intervalo?). E' o padrao p/ a nossa
   server action de 2a NF.
3. ir.actions.server precedentes: server actions custom em stock.picking / account.move /
   mrp — alguem ja cria picking / fatura / explode BoM via server action? (viabilidade +
   precedente de sobrevivencia a upgrade).
4. Capacidade: create/write em ir.actions.server e base.automation (uid 42).
5. Risco upgrade: idade/autor das server actions custom (sobrevivem a upgrade do CIEL IT?).

NAO escreve NADA. Salva /tmp/s8b_server_action.txt.
"""
import sys
import io
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
_buf = io.StringIO()
def out(*a):
    s = ' '.join(str(x) for x in a); print(s); _buf.write(s + '\n')

def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"
    out(f"UID {o._uid}")

    def rr(model, domain, fields, **kw):
        kwargs = {'fields': fields, 'context': CTX}; kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)
    def rd(model, ids, fields):
        ids = [i for i in ids if i]
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX}) if ids else []
    def fg(model, *needles):
        f = o.execute_kw(model, 'fields_get', [], {'attributes': ['string', 'type', 'relation'], 'context': CTX})
        return {k: v for k, v in f.items() if not needles or any(n in k.lower() for n in needles)}
    def cnt(model, domain):
        return o.execute_kw(model, 'search_count', [domain], {'context': CTX})
    def can(model, op):
        try:
            return o.execute_kw(model, 'check_access_rights', [op], {'raise_exception': False, 'context': CTX})
        except Exception as e:
            return f"ERRO {e}"

    # 1) base.automation
    out("\n" + "=" * 88)
    out("1) base.automation — triggers nativos disponiveis")
    out("=" * 88)
    baf = fg('base.automation', 'trigger', 'model', 'action', 'state', 'active', 'filter')
    out(f"  campos base.automation relevantes: {sorted(baf.keys())}")
    total_ba = cnt('base.automation', [])
    out(f"  total base.automation: {total_ba}")
    bas = rr('base.automation', [], ['id', 'name', 'model_id', 'trigger', 'active'], limit=200)
    by_model = Counter(m2o(b.get('model_id')) for b in bas)
    by_trigger = Counter(str(b.get('trigger')) for b in bas)
    out(f"  por trigger: {dict(by_trigger)}")
    out(f"  por modelo (top 15):")
    for md, n in by_model.most_common(15):
        out(f"     {n:3}x {md}")
    # as que tocam stock.picking / account.move / mrp
    rel = [b for b in bas if any(k in m2o(b.get('model_id')).lower() for k in ('stock.picking', 'account.move', 'mrp', 'stock.move'))]
    out(f"\n  base.automation em picking/move/mrp ({len(rel)}):")
    for b in rel[:20]:
        out(f"     id={b['id']:5} {m2o(b.get('model_id'))[:30]:30} trigger={b.get('trigger')} active={b.get('active')} | {b.get('name')[:40]}")

    # 2) como o robo 1512 e' disparado (cron?)
    out("\n" + "=" * 88)
    out("2) ir.cron que dispara server actions (como o robo 1512 roda)")
    out("=" * 88)
    cf = fg('ir.cron', 'action', 'server', 'interval', 'active', 'name')
    out(f"  campos ir.cron relevantes: {sorted(cf.keys())}")
    crons = rr('ir.cron', [], ['id', 'name', 'active', 'interval_number', 'interval_type', 'ir_actions_server_id'], limit=200)
    out(f"  total crons: {len(crons)}")
    # cron apontando 1512?
    c1512 = [c for c in crons if isinstance(c.get('ir_actions_server_id'), list) and c['ir_actions_server_id'] and c['ir_actions_server_id'][0] == 1512]
    out(f"  cron(s) que disparam a server action 1512 (robo faturamento): {[(c['id'], c['name'], c.get('interval_number'), c.get('interval_type'), c.get('active')) for c in c1512]}")
    # crons de faturamento/industrializacao
    fat = [c for c in crons if any(k in (c.get('name') or '').lower() for k in ('fatur', 'nf', 'robo', 'industri', 'dfe'))]
    out(f"  crons com fatur/nf/robo/industri/dfe no nome ({len(fat)}):")
    for c in fat[:20]:
        out(f"     id={c['id']:5} act_server={m2o(c.get('ir_actions_server_id'))[:8]:8} {c.get('interval_number')}{c.get('interval_type')} active={c.get('active')} | {c.get('name')[:45]}")

    # 3) ir.actions.server precedentes (custom, em picking/move/mrp)
    out("\n" + "=" * 88)
    out("3) ir.actions.server em stock.picking / account.move / mrp.production")
    out("=" * 88)
    for model in ('stock.picking', 'account.move', 'mrp.production', 'stock.move'):
        sas = rr('ir.actions.server', [('model_id.model', '=', model)], ['id', 'name', 'state', 'usage'], limit=40)
        out(f"\n  ir.actions.server em {model}: {len(sas)}")
        for s in sas[:18]:
            out(f"     id={s['id']:5} state={str(s.get('state')):8} usage={str(s.get('usage')):14} | {s.get('name')[:46]}")

    # 4) capacidade
    out("\n" + "=" * 88)
    out("4) Capacidade (uid 42): criar/editar server action e automation")
    out("=" * 88)
    for model in ('ir.actions.server', 'base.automation', 'ir.cron'):
        out(f"  {model}: create={can(model,'create')} write={can(model,'write')} unlink={can(model,'unlink')}")

    # 5) risco upgrade — idade/autor das server actions custom
    out("\n" + "=" * 88)
    out("5) Risco upgrade — server actions: total, e amostra de custom (create_uid != base)")
    out("=" * 88)
    total_sa = cnt('ir.actions.server', [])
    out(f"  total ir.actions.server: {total_sa}")
    # a 1512 sobreviveu? ler metadados
    sa1512 = rd('ir.actions.server', [1512], ['id', 'name', 'create_uid', 'create_date', 'write_date', 'state', 'model_id'])
    for s in sa1512:
        out(f"  robo 1512: name={s.get('name')} create_uid={m2o(s.get('create_uid'))} create={s.get('create_date')} write={s.get('write_date')} model={m2o(s.get('model_id'))}")
    # server actions criadas por humanos (uid >1) recentes — proxy de "custom que persiste"
    sas_all = rr('ir.actions.server', [('state', '=', 'code')], ['id', 'name', 'create_uid', 'create_date'], limit=300)
    humanas = [s for s in sas_all if isinstance(s.get('create_uid'), list) and s['create_uid'] and s['create_uid'][0] not in (1,)]
    out(f"  server actions state=code: {len(sas_all)}; criadas por uid!=1 (custom-humano): {len(humanas)}")
    creators = Counter(m2o(s.get('create_uid')) for s in sas_all)
    out(f"  por create_uid (top): {dict(creators.most_common(8))}")

    out("\n[FIM s8b_server_action_grounding — READ-only]")
    with open('/tmp/s8b_server_action.txt', 'w') as f:
        f.write(_buf.getvalue())
    out(">>> salvo em /tmp/s8b_server_action.txt")


if __name__ == '__main__':
    main()
