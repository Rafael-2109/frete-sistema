"""auditar_reclassificacao.py — skill `auditando-reclassificacao-odoo` (READ-only).

Auditoria de reclassificacao contabil em lotes no Odoo via XML-RPC, em 3 modos:

  - medir-saldos        n_linhas + total_debito por conta/empresa/journal/periodo
  - validar-lote        arquivo-alvo JSON vs estado real (divergencias/ausentes/
                        duplicados/draft)
  - monitorar-andamento processadas vs pendentes de uma execucao em curso (% conc.)

ESTRITAMENTE READ-only: usa apenas `search_read` sobre account.move.line e
account.move. NAO escreve (sem button_draft / write account_id / action_post).
A reclassificacao em si (write) esta FORA do escopo desta skill (C4 da decisao
4-maos #164; a sugestao irma de write em massa #163 foi rejeitada).

Origem: 17 scripts distintos do cluster 4 (sessao 4ce68a88, Marcus user 18),
reclassificacao CPV/VarNeg/FFF mes a mes (ago/2025 -> jan/2026) na empresa CD.

Constantes reais recorrentes (defaults, sempre overridaveis):
  company_id=4 (CD)  journal_id=845  CPV=25091  VARNEG=26785  FFF=26854

Estrutura do arquivo-alvo (JSON):
  {"venda_NF": [{"line": <move_id>, "lid": <move_line_id>, "debit": <valor>}, ...]}

Exemplos:
  python auditar_reclassificacao.py medir-saldos \\
      --contas 25091:CPV,26785:VARNEG,26854:FFF \\
      --data-inicio 2025-09-01 --data-fim 2025-09-30 --json
  python auditar_reclassificacao.py validar-lote \\
      --arquivo /tmp/reclass/setembro_alvo.json \\
      --conta-destino 25091 --conta-origem 26785 --json
  python auditar_reclassificacao.py monitorar-andamento \\
      --arquivo /tmp/reclass/setembro_alvo.json \\
      --conta-destino 25091 --conta-origem 26785
"""
import argparse
import json
import sys
from pathlib import Path

# Defaults reais (cluster 4). Overridaveis por flag.
DEFAULT_COMPANY_ID = 4      # CD
DEFAULT_JOURNAL_ID = 845
DEFAULT_CHAVE = 'venda_NF'

MODEL_LINE = 'account.move.line'
MODEL_MOVE = 'account.move'


# ---------------------------------------------------------------------------
# Helpers puros (logica testavel — recebem a conexao Odoo `c` injetada)
# ---------------------------------------------------------------------------
def parse_contas(s):
    """'25091:CPV,26785:VARNEG' -> [(25091,'CPV'),(26785,'VARNEG')].

    Sem rotulo apos ':' usa o proprio id como rotulo. Ignora itens vazios.
    """
    contas = []
    for parte in (s or '').split(','):
        parte = parte.strip()
        if not parte:
            continue
        if ':' in parte:
            cid, rotulo = parte.split(':', 1)
            cid, rotulo = cid.strip(), rotulo.strip()
        else:
            cid, rotulo = parte, ''
        cid_int = int(cid)
        contas.append((cid_int, rotulo or str(cid_int)))
    return contas


def carregar_alvo(path, chave=DEFAULT_CHAVE):
    """Le o arquivo-alvo JSON e retorna a lista sob `chave`.

    Levanta KeyError (mensagem clara) se a chave nao existir.
    """
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if chave not in data:
        raise KeyError(
            f"chave '{chave}' ausente no arquivo {path}. "
            f"Chaves disponiveis: {sorted(data.keys())}"
        )
    return data[chave]


def detectar_duplicados(registros):
    """Retorna os `lid` que aparecem mais de uma vez (ordem de 1a ocorrencia)."""
    vistos = set()
    dups = []
    for r in registros:
        lid = r['lid']
        if lid in vistos and lid not in dups:
            dups.append(lid)
        vistos.add(lid)
    return dups


def _acc_id(row):
    """Extrai o id da conta de um row (account_id vem como [id, nome] ou False)."""
    acc = row.get('account_id')
    if isinstance(acc, (list, tuple)) and acc:
        return acc[0]
    return acc or None


def _dominio_saldo(conta_id, data_inicio, data_fim, company_id, journal_id, state='posted'):
    dom = [
        ('account_id', '=', conta_id),
        ('company_id', '=', company_id),
        ('journal_id', '=', journal_id),
        ('date', '>=', data_inicio),
        ('date', '<=', data_fim),
        ('debit', '>', 0),
    ]
    if state in ('posted', 'draft'):
        dom.append(('parent_state', '=', state))
    # state == 'both' -> sem filtro de parent_state (posted + draft)
    return dom


def medir_saldos(c, contas, data_inicio, data_fim,
                 company_id=DEFAULT_COMPANY_ID, journal_id=DEFAULT_JOURNAL_ID,
                 state='posted'):
    """Mede n_linhas + total_debito por conta (debit>0) no periodo.

    state: 'posted' (default, comportamento historico), 'draft' ou 'both' — filtra
    parent_state do move. 'both' inclui lancamentos ainda em rascunho (ex: contar
    o que falta postar pos-reclassificacao).
    """
    saldos = []
    for conta_id, rotulo in contas:
        dom = _dominio_saldo(conta_id, data_inicio, data_fim, company_id, journal_id, state)
        rows = c.search_read(MODEL_LINE, dom, ['debit'])
        saldos.append({
            'conta_id': conta_id,
            'rotulo': rotulo,
            'n_linhas': len(rows),
            'total_debito': round(sum(r['debit'] for r in rows), 2),
        })
    return {
        'modo': 'medir-saldos',
        'company_id': company_id,
        'journal_id': journal_id,
        'state': state,
        'periodo': {'inicio': data_inicio, 'fim': data_fim},
        'saldos': saldos,
    }


def _contar_moves_draft(c, registros):
    moves = list({r['line'] for r in registros})
    if not moves:
        return 0
    draft = c.search_read(MODEL_MOVE, [('id', 'in', moves), ('state', '=', 'draft')], ['id'])
    return len(draft)


def validar_lote(c, registros, conta_destino, conta_origem):
    """Compara o arquivo-alvo vs estado real no Odoo.

    Classifica cada lid unico em processada (conta_destino), pendente
    (conta_origem) ou divergente (outra conta); detecta ausentes (lid que nao
    existe mais no Odoo) e duplicados (lid repetido no arquivo). Conta moves em
    draft. `integro` = sem anomalias estruturais (dup/ausente/divergente).
    """
    lids_unicos = list(dict.fromkeys(r['lid'] for r in registros))
    duplicados = detectar_duplicados(registros)
    rows = c.search_read(MODEL_LINE, [('id', 'in', lids_unicos)],
                         ['account_id', 'parent_state'])
    por_id = {r['id']: r for r in rows}
    encontrados = set(por_id)
    ausentes = [lid for lid in lids_unicos if lid not in encontrados]

    processadas = 0
    pendentes = 0
    divergentes = []
    for lid in lids_unicos:
        if lid not in por_id:
            continue
        acc = _acc_id(por_id[lid])
        if acc == conta_destino:
            processadas += 1
        elif acc == conta_origem:
            pendentes += 1
        else:
            divergentes.append({'lid': lid, 'account_id': acc})

    moves_draft = _contar_moves_draft(c, registros)
    integro = not duplicados and not ausentes and not divergentes
    return {
        'modo': 'validar-lote',
        'conta_destino': conta_destino,
        'conta_origem': conta_origem,
        'total_alvo': len(registros),
        'linhas_unicas': len(lids_unicos),
        'duplicados': duplicados,
        'processadas': processadas,
        'pendentes': pendentes,
        'divergentes': divergentes,
        'ausentes': ausentes,
        'moves_draft': moves_draft,
        'integro': integro,
    }


def monitorar_andamento(c, registros, conta_destino, conta_origem):
    """Progresso de uma execucao em curso: processadas vs pendentes (% conc.)."""
    lids_unicos = list(dict.fromkeys(r['lid'] for r in registros))
    total = len(lids_unicos)
    rows = c.search_read(MODEL_LINE, [('id', 'in', lids_unicos)], ['account_id'])
    processadas = sum(1 for r in rows if _acc_id(r) == conta_destino)
    pendentes = sum(1 for r in rows if _acc_id(r) == conta_origem)
    moves_draft = _contar_moves_draft(c, registros)
    pct = round(100 * processadas / total, 1) if total else 0.0
    concluido = (total > 0 and processadas == total and moves_draft == 0)
    return {
        'modo': 'monitorar-andamento',
        'total': total,
        'processadas': processadas,
        'pendentes': pendentes,
        'pct_concluido': pct,
        'moves_draft': moves_draft,
        'concluido': concluido,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser():
    ap = argparse.ArgumentParser(description=(__doc__ or '').strip().split('\n')[0])
    sub = ap.add_subparsers(dest='modo', required=True)

    p_med = sub.add_parser('medir-saldos',
                           help='Saldo (n_linhas + total_debito) por conta no periodo')
    p_med.add_argument('--contas', required=True,
                       help='id:rotulo separados por virgula (ex: 25091:CPV,26785:VARNEG)')
    p_med.add_argument('--data-inicio', required=True, help='YYYY-MM-DD')
    p_med.add_argument('--data-fim', required=True, help='YYYY-MM-DD')
    p_med.add_argument('--company-id', type=int, default=DEFAULT_COMPANY_ID,
                       help=f'Default {DEFAULT_COMPANY_ID} (CD)')
    p_med.add_argument('--journal-id', type=int, default=DEFAULT_JOURNAL_ID,
                       help=f'Default {DEFAULT_JOURNAL_ID}')
    p_med.add_argument('--state', choices=['posted', 'draft', 'both'], default='posted',
                       help='Estado dos lancamentos: posted (default), draft ou both')
    p_med.add_argument('--json', action='store_true', help='Saida JSON (default: tabela)')

    for nome, ajuda in (('validar-lote', 'Arquivo-alvo vs estado real (integridade)'),
                        ('monitorar-andamento', 'Progresso processadas vs pendentes')):
        p = sub.add_parser(nome, help=ajuda)
        p.add_argument('--arquivo', required=True, help='Caminho do JSON-alvo')
        p.add_argument('--chave', default=DEFAULT_CHAVE,
                       help=f'Chave da lista no JSON (default {DEFAULT_CHAVE})')
        p.add_argument('--conta-destino', type=int, required=True,
                       help='Conta para onde as linhas devem migrar (ex: 25091 CPV)')
        p.add_argument('--conta-origem', type=int, required=True,
                       help='Conta de origem das linhas (ex: 26785 VarNeg)')
        p.add_argument('--json', action='store_true', help='Saida JSON (default: tabela)')

    return ap


def _conectar():
    """Fronteira de I/O — import lazy para nao acoplar os helpers ao app."""
    _THIS = Path(__file__).resolve()
    sys.path.insert(0, str(_THIS.parents[4]))
    from app.odoo.utils.connection import get_odoo_connection  # noqa: E402
    c = get_odoo_connection()
    if not c.authenticate():
        raise RuntimeError('Falha na autenticacao com Odoo')
    return c


def _print(res, as_json):
    if as_json:
        print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
        return
    modo = res['modo']
    if modo == 'medir-saldos':
        print(f"=== MEDIR SALDOS | company={res['company_id']} journal={res['journal_id']} "
              f"state={res['state']} | {res['periodo']['inicio']} a {res['periodo']['fim']} ===")
        print(f"{'conta':>8} {'rotulo':<10} {'n_linhas':>9} {'total_debito':>16}")
        for s in res['saldos']:
            print(f"{s['conta_id']:>8} {s['rotulo']:<10} {s['n_linhas']:>9} "
                  f"R$ {s['total_debito']:>13,.2f}")
    elif modo == 'validar-lote':
        print(f"=== VALIDAR LOTE | destino={res['conta_destino']} origem={res['conta_origem']} ===")
        print(f"alvo total:   {res['total_alvo']} (unicos: {res['linhas_unicas']})")
        print(f"processadas:  {res['processadas']} (em destino)")
        print(f"pendentes:    {res['pendentes']} (em origem)")
        print(f"divergentes:  {len(res['divergentes'])}  {res['divergentes'][:10]}")
        print(f"ausentes:     {len(res['ausentes'])}  {res['ausentes'][:10]}")
        print(f"duplicados:   {len(res['duplicados'])}  {res['duplicados'][:10]}")
        print(f"moves draft:  {res['moves_draft']}")
        print(f"INTEGRO:      {res['integro']}")
    else:  # monitorar-andamento
        print("=== MONITORAR ANDAMENTO ===")
        print(f"total:        {res['total']}")
        print(f"processadas:  {res['processadas']}")
        print(f"pendentes:    {res['pendentes']}")
        print(f"moves draft:  {res['moves_draft']}")
        print(f"concluido:    {res['concluido']}  ({res['pct_concluido']:.1f}%)")


def main(argv=None):
    args = build_parser().parse_args(argv)
    c = _conectar()
    if args.modo == 'medir-saldos':
        res = medir_saldos(c, parse_contas(args.contas), args.data_inicio, args.data_fim,
                           company_id=args.company_id, journal_id=args.journal_id,
                           state=args.state)
    else:
        registros = carregar_alvo(args.arquivo, args.chave)
        if args.modo == 'validar-lote':
            res = validar_lote(c, registros, args.conta_destino, args.conta_origem)
        else:
            res = monitorar_andamento(c, registros, args.conta_destino, args.conta_origem)
    _print(res, args.json)
    return 0


if __name__ == '__main__':
    sys.exit(main())
