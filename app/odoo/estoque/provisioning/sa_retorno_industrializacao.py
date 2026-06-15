# etapa: infra-Odoo (provisionamento de automação)
# doc-dono: docs/industrializacao-fb-lf/SOT_OPERACOES.md §6.3
"""Provisionamento das server actions + crons da automação da SAÍDA do retorno de
industrialização (G1 monta a NF-2 / G2 transmite a NF-2). Opção B (DECISÃO SOT §6.3):
`ir.cron`-Odoo + SA PERSISTENTE server-side, padrão dos robôs CIEL IT.

CONSTITUIÇÃO: categoria **infra-Odoo**, FORA do sistema de skills (escrever
`ir.actions.server`/`ir.cron` é provisionar config do ERP, não operar estoque — §1.1 +
CLAUDE.md:410-412). O **body** de cada SA é uma **string versionada = fonte de verdade**;
o provisionamento é idempotente (re-cria por `name`) — dívida obrigatória porque records
custom somem em upgrade CIEL IT (precedente DFE NFD).

🔴🔴🔴 GATE DE SEGURANÇA — NADA é escrito no Odoo sem `--confirmar` E go fresco do Rafael.
  - `provisionar(dry_run=True)` (DEFAULT) só PLANEJA (não cria SA/cron).
  - O body G1 (`SA_BODY_G1`) tem a **GENEALOGIA em `safe_eval`** (port iterativo do
    `DescobertaIndustrializacaoService`) que **NÃO foi validada server-side** — exige
    **CANARY READ-only** contra o oráculo (`SaidaRetornoIndustrializacaoExecutor.validar`)
    ANTES de habilitar o cron G1. Pontos abertos marcados `# 🔴 CANARY` no body.
  - G2 transmite ao SEFAZ (IRREVERSÍVEL): o cron G2 só liga após o piloto validado; em
    canary, cada transmissão exige go fresco. A transmissão humana da NF-1 É a autorização.
"""
import argparse
import logging
import sys
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Identidade estável (busca idempotente) ────────────────────────────────────────
SA_G1_NAME = 'NACOM AUTO: Retorno Industrializacao G1 (monta NF-2)'
SA_G2_NAME = 'NACOM AUTO: Retorno Industrializacao G2 (transmite NF-2)'
CRON_G1_NAME = 'NACOM AUTO: Retorno Industrializacao G1 (cron)'
CRON_G2_NAME = 'NACOM AUTO: Retorno Industrializacao G2 (cron)'

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}

# 🔴 TODO FOCO 3 — consolidar em L0 (account.account é company-specific; verificar no Odoo vivo)
RETIND = 1083            # NF-2 insumos (LF sale, no_payment PASSIVA 5101020001=26667)
OP_5902 = 2864
FP_RETIND = 111
J847 = 847               # NF-1 serviço (gatilho do ciclo)
LOC_TERCEIROS = 31092


# ── BODIES VERSIONADOS (fonte de verdade — o `code` do Odoo é derivado destes) ────

# G2 — transmissão da NF-2 ao SEFAZ. FIEL ao s54 (PROVADO 2026-06-14: NF-1 791437 +
# NF-2 791441 cstat=100 via action_previsualizar_xml_nfe + action_gerar_nfe). active_id =
# a NF-1 serviço (gatilho do cron G2: NF-1 cstat=100 com NF-2 do ciclo não transmitida).
SA_BODY_G2 = r'''
nf1 = env['account.move'].sudo().with_context(allowed_company_ids=[5], lang='pt_BR').browse(env.context.get('active_id'))
ciclo = nf1.invoice_origin
nf2 = env['account.move'].sudo().with_context(allowed_company_ids=[5]).search(
    [('journal_id','=',1083),('invoice_origin','=',ciclo),('state','=','posted')], limit=1)
if not nf2:
    log('G2-RESULT skip nf1=%s motivo=nf2_ausente_ou_nao_posted' % nf1.id)
elif nf2.l10n_br_cstat_nf == '100':
    log('G2-RESULT skip nf2=%s motivo=ja_transmitida' % nf2.id)
elif nf1.l10n_br_cstat_nf != '100':
    log('G2-RESULT skip nf1=%s motivo=nf1_nao_autorizada cstat=%s' % (nf1.id, nf1.l10n_br_cstat_nf))
else:
    chaves2 = nf2.referencia_ids.mapped('l10n_br_chave_nf')
    if nf1.l10n_br_chave_nf and nf1.l10n_br_chave_nf not in chaves2:
        nf2.with_context(check_move_validity=False).write(
            {'referencia_ids': [(0, 0, {'l10n_br_chave_nf': nf1.l10n_br_chave_nf, 'company_id': 5})]})
    err = ''
    try:
        nf2.action_previsualizar_xml_nfe()
    except Exception as e:
        err = 'preview:' + str(e)[:120]
    try:
        nf2.action_gerar_nfe()
    except Exception as e:
        err = err + ' gerar:' + str(e)[:200]
    log('G2-RESULT nf2=%s situacao=%s cstat=%s chave=%s xmotivo=%s err=%s' % (
        nf2.id, nf2.l10n_br_situacao_nf, nf2.l10n_br_cstat_nf, nf2.l10n_br_chave_nf,
        (nf2.l10n_br_xmotivo_nf or '')[:70], err))
'''

# G1 — monta+posta a NF-2 (insumos 5902) a partir da NF-1 serviço (active_id). MONTAGEM
# fiel ao s37 (seção NF-2); GENEALOGIA = port iterativo de DescobertaIndustrializacaoService
# (recursão `_explodir` → stack; `_precos_svl_entrada`; voto da remessa).
# 🔴 CANARY REQUIRED: a genealogia em safe_eval NÃO foi validada server-side. Rodar
#    `saida_retorno_industrializacao validar` (oráculo) contra a NF-2 gerada por um canary
#    READ-only ANTES de habilitar o cron G1. Pontos abertos marcados `# 🔴 CANARY`.
SA_BODY_G1 = r'''
LOC_TERCEIROS = 31092
RETIND = 1083
OP_5902 = 2864
FP_RETIND = 111
nf1 = env['account.move'].sudo().with_context(allowed_company_ids=[5], lang='pt_BR').browse(env.context.get('active_id'))
pa_line = nf1.invoice_line_ids.filtered(lambda l: l.l10n_br_cfop_codigo == '5124')[:1]
if not pa_line:
    log('G1-RESULT skip nf1=%s motivo=sem_linha_5124' % nf1.id)
else:
    pa = pa_line.product_id
    pa_qty = pa_line.quantity
    ciclo = 'RET-IND-%s-%s' % (pa.id, nf1.id)
    ja = env['account.move'].sudo().search([('journal_id', '=', RETIND), ('invoice_origin', '=', ciclo)], limit=1)
    if ja:
        log('G1-RESULT skip ciclo=%s nf2=%s motivo=ja_existe' % (ciclo, ja.id))
    else:
        pick = env['stock.picking'].sudo().search(['|', ('invoice_id', '=', nf1.id), ('invoice_ids', 'in', [nf1.id])], limit=1)
        ml = pick.move_line_ids.filtered(lambda m: m.product_id == pa)[:1]
        lote_pa = ml.lot_id
        # === GENEALOGIA (iterativa; espelha _explodir + _producao_total) ===
        acc = {}
        stack = [(lote_pa.id, pa_qty)]
        for _ in range(200):                                   # guard anti-loop (semis rasos)
            if not stack:
                break
            lote_id, fator = stack.pop()
            mos = env['mrp.production'].sudo().search([('lot_producing_id', '=', lote_id), ('state', '=', 'done')])
            if not mos:
                continue
            tot = sum(m.qty_producing or m.product_qty or 0 for m in mos) or 1.0
            for mo in mos:
                for r in mo.move_raw_ids.filtered(lambda x: x.state == 'done'):
                    q = r.product_qty or 0
                    share = q * fator / tot
                    cl = r.move_line_ids[:1].lot_id
                    is_semi = bool(cl) and bool(env['mrp.production'].sudo().search_count(
                        [('lot_producing_id', '=', cl.id), ('state', '=', 'done')]))
                    if is_semi:
                        stack.append((cl.id, share))
                    elif r.location_id.id == LOC_TERCEIROS:
                        acc[r.product_id.id] = acc.get(r.product_id.id, 0.0) + share
        prods = env['product.product'].sudo().browse(list(acc.keys()))
        comps = [p for p in prods if p.type != 'consu']        # exclui ÁGUA (consumo local)
        comp_ids = [p.id for p in comps]
        entrada = env['stock.move'].sudo().search(
            [('product_id', 'in', comp_ids), ('location_dest_id', '=', LOC_TERCEIROS), ('state', '=', 'done')])
        # preço = unit_cost do SVL da ENTRADA mais recente em 31092 (invariante 5902=5901)
        precos = {}
        for pid in comp_ids:
            ems = entrada.filtered(lambda m: m.product_id.id == pid).sorted(key=lambda m: m.date or '', reverse=True)
            for em in ems:
                svl = env['stock.valuation.layer'].sudo().search([('stock_move_id', '=', em.id)], limit=1)
                if svl and svl.unit_cost:
                    precos[pid] = svl.unit_cost
                    break
        # voto da remessa (picking de entrada em 31092 mais votado) → chave RPI p/ R3
        votos = {}
        for em in entrada:
            pk = em.picking_id
            if pk:
                votos[pk.id] = votos.get(pk.id, 0) + 1
        remessa_pick = env['stock.picking'].sudo().browse(max(votos, key=lambda k: votos[k])) if votos else False
        # chave da NF de remessa (RPI) p/ R3: `picking.origin` é o nome da PO (ex.: 'C2619830'),
        # NÃO o nome da NF. A NF de entrada da remessa (ENTIN LF) tem `invoice_origin` == esse
        # origin + a chave. Validado READ contra PROD (canary G1, picking 322451 → NF 737062 →
        # chave ...6795 == oráculo). `chave!=False` ignora docs sem chave do mesmo origin.
        chave_remessa = ''
        if remessa_pick and remessa_pick.origin:
            rem_nf = env['account.move'].sudo().search(
                [('invoice_origin', '=', remessa_pick.origin), ('company_id', '=', 5),
                 ('l10n_br_chave_nf', '!=', False)], limit=1)
            chave_remessa = rem_nf.l10n_br_chave_nf or ''
        # === MONTAGEM (fiel s37 — NF-2 insumos) ===
        nf2 = env['account.move'].sudo().with_context(allowed_company_ids=[5], lang='pt_BR').create({
            'move_type': 'out_invoice', 'journal_id': RETIND, 'partner_id': 1, 'company_id': 5,
            'l10n_br_tipo_pedido': 'venda-industrializacao', 'l10n_br_operacao_id': OP_5902,
            'fiscal_position_id': FP_RETIND,
            'invoice_incoterm_id': 6, 'l10n_br_carrier_id': 999, 'payment_provider_id': 31,
            'l10n_br_calcular_imposto': False, 'invoice_origin': ciclo,
            'invoice_date': nf1.invoice_date or datetime.date.today()})
        erros = []
        for p in comps:
            try:
                env['account.move.line'].sudo().with_context(allowed_company_ids=[5], check_move_validity=False).create({
                    'move_id': nf2.id, 'product_id': p.id, 'quantity': acc[p.id],
                    'l10n_br_operacao_id': OP_5902, 'l10n_br_operacao_manual': True,
                    'price_unit': precos.get(p.id, p.standard_price)})
            except Exception as e:
                erros.append(str(e)[:40])
        try:
            nf2.onchange_l10n_br_calcular_imposto(); nf2.onchange_l10n_br_calcular_imposto_btn()
        except Exception as e:
            log('G1 recompute erro: %s' % str(e)[:120])
        amap = {}
        for fa in env['account.fiscal.position.account'].sudo().search([('position_id', '=', FP_RETIND)]):
            amap[fa.account_src_id.id] = fa.account_dest_id.id
        for l in nf2.invoice_line_ids.filtered(lambda x: x.display_type == 'product'):
            dest = amap.get(l.account_id.id)
            if dest and dest != l.account_id.id:
                l.with_context(check_move_validity=False).write({'account_id': dest})
        if chave_remessa:
            nf2.with_context(check_move_validity=False).write(
                {'referencia_ids': [(0, 0, {'l10n_br_chave_nf': chave_remessa, 'company_id': 5})]})
        # post (baixa a PASSIVA 5101020001) — reversível (journal hash=False), NÃO SEFAZ
        try:
            nf2.action_post()
        except Exception as e:
            erros.append('post:' + str(e)[:60])
        log('G1-RESULT nf1=%s nf2=%s ciclo=%s n_linhas=%s total=%s state=%s chave_rem=%s erros=%s' % (
            nf1.id, nf2.id, ciclo, len(comps), nf2.amount_untaxed, nf2.state,
            'OK' if chave_remessa else 'FALTA', str(erros[:2])))
'''


class SaRetornoIndustrializacaoProvisioner:
    """Provisiona/verifica as SAs + crons (idempotente). dry_run=True (default) só PLANEJA."""

    ARTEFATOS = (
        ('sa', SA_G1_NAME, 'SA_BODY_G1'),
        ('sa', SA_G2_NAME, 'SA_BODY_G2'),
    )

    def __init__(self, odoo):
        self.odoo = odoo
        self._bodies = {'SA_BODY_G1': SA_BODY_G1, 'SA_BODY_G2': SA_BODY_G2}

    # ── helpers READ ──────────────────────────────────────────────────────────
    def _buscar_sa(self, name: str) -> Optional[Dict[str, Any]]:
        rows = self._sr('ir.actions.server', [('name', '=', name), ('state', '=', 'code')],
                        ['id', 'name', 'code', 'state', 'model_id'])
        return rows[0] if rows else None

    def _buscar_cron(self, name: str) -> Optional[Dict[str, Any]]:
        rows = self._sr('ir.cron', [('name', '=', name)],
                        ['id', 'name', 'active', 'interval_number', 'interval_type', 'ir_actions_server_id'])
        return rows[0] if rows else None

    def _model_account_move_id(self) -> Optional[int]:
        rows = self._sr('ir.model', [('model', '=', 'account.move')], ['id'])
        return rows[0]['id'] if rows else None

    # ── VERIFICAR (READ-only — núcleo do monitor anti-upgrade) ────────────────
    def verificar(self) -> Dict[str, Any]:
        """READ-only — confere se as SAs existem e se o `code` no Odoo BATE com o body
        versionado (= fonte de verdade). Usado pelo monitor (D8 + hook SessionStart).
        Retorna `acao_necessaria=True` se algo sumiu/divergiu (upgrade CIEL IT, etc.)."""
        detalhes: List[Dict[str, Any]] = []
        acao = False
        for _, name, body_key in self.ARTEFATOS:
            sa = self._buscar_sa(name)
            body = self._bodies[body_key]
            if not sa:
                detalhes.append({'artefato': name, 'status': 'AUSENTE', 'acao': 're-aplicar'})
                acao = True
                continue
            code_ok = (sa.get('code') or '').strip() == body.strip()
            detalhes.append({'artefato': name, 'status': 'OK' if code_ok else 'CODE_DIVERGENTE',
                             'sa_id': sa['id'], 'acao': None if code_ok else 're-aplicar (code drift)'})
            if not code_ok:
                acao = True
        for cron_name, sa_name in ((CRON_G1_NAME, SA_G1_NAME), (CRON_G2_NAME, SA_G2_NAME)):
            cron = self._buscar_cron(cron_name)
            if not cron:
                detalhes.append({'artefato': cron_name, 'status': 'AUSENTE', 'acao': 're-aplicar'})
                acao = True
                continue
            if not cron.get('active'):
                detalhes.append({'artefato': cron_name, 'status': 'INATIVO', 'cron_id': cron['id'],
                                 'acao': 'reativar'})
                acao = True
                continue
            # integridade: o cron aponta para a SA certa?
            sa = self._buscar_sa(sa_name)
            srv = cron.get('ir_actions_server_id')
            srv_id = (srv[0] if isinstance(srv, list) else srv) if srv else None
            if sa and srv_id != sa['id']:
                detalhes.append({'artefato': cron_name, 'status': 'SA_LINK_ERRADO', 'cron_id': cron['id'],
                                 'aponta_para': srv_id, 'esperado': sa['id'], 'acao': 're-apontar'})
                acao = True
            else:
                detalhes.append({'artefato': cron_name, 'status': 'OK', 'cron_id': cron['id'], 'acao': None})
        return {'ok': not acao, 'acao_necessaria': acao, 'detalhes': detalhes}

    # ── PROVISIONAR (dry-run-first — cria/atualiza SA; cron fica gated) ───────
    def provisionar(self, *, dry_run: bool = True, incluir_cron: bool = False) -> Dict[str, Any]:
        """Idempotente: SA ausente → create; code divergente → write. `dry_run=True`
        (DEFAULT) só PLANEJA. `incluir_cron` (default False) liga os crons — só após o
        canary do body G1 e validação contra o oráculo (G1) / piloto SEFAZ (G2)."""
        plano: List[Dict[str, Any]] = []
        model_id = self._model_account_move_id()
        for _, name, body_key in self.ARTEFATOS:
            body = self._bodies[body_key]
            sa = self._buscar_sa(name)
            if not sa:
                plano.append({'acao': 'CREATE_SA', 'name': name, 'model_id': model_id})
                if not dry_run:
                    self.odoo.execute_kw('ir.actions.server', 'create',
                                         [{'name': name, 'model_id': model_id, 'state': 'code', 'code': body}],
                                         {'context': CTX})
            elif (sa.get('code') or '').strip() != body.strip():
                plano.append({'acao': 'UPDATE_SA', 'name': name, 'sa_id': sa['id']})
                if not dry_run:
                    self.odoo.execute_kw('ir.actions.server', 'write',
                                         [[sa['id']], {'code': body}], {'context': CTX})
            else:
                plano.append({'acao': 'NOOP_SA', 'name': name, 'sa_id': sa['id']})
        if incluir_cron:
            plano.append({'acao': 'CRON_PENDENTE_CANARY',
                          'nota': '🔴 crons G1/G2 só após canary do body G1 + piloto SEFAZ G2 '
                                  '(campos ir.cron a confirmar no Odoo vivo — numbercall/nextcall)'})
        return {'dry_run': dry_run, 'plano': plano,
                'gate': 'NADA escrito' if dry_run else 'SAs aplicadas (crons NÃO — gated)'}

    def _sr(self, model: str, domain: list, fields: list) -> list:
        try:
            rows = self.odoo.search_read(model, domain, fields)
            return rows if isinstance(rows, list) else []
        except Exception as e:
            logger.warning(f'_sr {model} falhou: {str(e)[:120]}')
            return []


# ── CLI ─────────────────────────────────────────────────────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(
        description='Provisiona/verifica as SAs+crons da automação da SAÍDA de industrialização '
                    '(infra-Odoo). dry-run-first; crons gated por canary.')
    ap.add_argument('modo', choices=('verificar', 'provisionar'), help='verificar (READ) | provisionar')
    ap.add_argument('--confirmar', action='store_true', help='EXECUTA o provisionamento (default = dry-run)')
    ap.add_argument('--incluir-cron', action='store_true', help='(gated) inclui os crons no plano')
    args = ap.parse_args(argv)

    from app.odoo.utils.connection import get_odoo_connection
    import json
    odoo = get_odoo_connection()
    assert odoo.authenticate(), 'falha autenticacao Odoo'
    prov = SaRetornoIndustrializacaoProvisioner(odoo)
    if args.modo == 'verificar':
        out = prov.verificar()
    else:
        out = prov.provisionar(dry_run=not args.confirmar, incluir_cron=args.incluir_cron)
    print(json.dumps(out, default=str, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main(sys.argv[1:])
