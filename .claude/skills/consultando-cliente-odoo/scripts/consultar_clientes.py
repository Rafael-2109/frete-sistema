"""consultar_clientes.py — skill `consultando-cliente-odoo`: READ-only de res.partner AO VIVO no Odoo.

Consulta o cadastro de clientes/parceiros direto no Odoo CIEL IT (NAO no banco local
sincronizado). Sem --dry-run/--confirmar: e' sempre READ (search_read/read_group), nunca escreve.

Robustez: descobre via fields_get quais campos existem em res.partner ANTES de pedi-los,
entao nao quebra se a instancia nao tiver um campo opcional (ex.: city/email customizados).

Modos:
  - clientes (default)   busca/lista clientes por filtro (cnpj, nome, cidade, ativo, cliente)
  - detalhes             cadastro completo de UM cliente (por --cliente-id ou --cnpj) + ultimas vendas
  - por-vendedor         agrupa pedidos de venda (sale.order) por vendedor (user_id) — read_group

Exemplos:
  # Buscar cliente por CNPJ (parcial ou completo)
  python consultar_clientes.py --cnpj 18467441
  # Clientes ativos de uma cidade (so' quem e' cliente: customer_rank>0)
  python consultar_clientes.py --cidade "Sao Paulo" --limit 50
  # Contagem total de clientes ativos
  python consultar_clientes.py --apenas-total
  # Detalhe de um cliente + ultimas 10 vendas
  python consultar_clientes.py --modo detalhes --cnpj 61724241000178
  # Ranking de pedidos por vendedor (so' confirmados), empresa LF
  python consultar_clientes.py --modo por-vendedor --company-id 5 --confirmados --json
"""
import argparse
import json
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[4]))

from app.odoo.estoque._cli_utils import (  # noqa: E402
    adicionar_args_padrao, setup_cli_completo,
)
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

# Companies Odoo (IDS_FIXOS.md). NAO confundir com o "CD=34" de docs financeiros.
COMPANIES = {1: 'FB', 3: 'SC', 4: 'CD', 5: 'LF'}

# Campos DESEJADOS em res.partner (filtrados pelos que existem de fato — fields_get).
# Confirmados em uso real: name, l10n_br_cnpj, l10n_br_ie (cached_lookups.py),
# l10n_br_razao_social (carteira_mapper.py). Os demais sao padrao Odoo res.partner.
CAMPOS_PARTNER = [
    'id', 'name', 'l10n_br_cnpj', 'l10n_br_cpf', 'l10n_br_razao_social', 'l10n_br_ie',
    'active', 'customer_rank', 'supplier_rank', 'create_date',
    'email', 'phone', 'mobile', 'city', 'state_id', 'user_id', 'company_id', 'category_id',
]
CAMPOS_VENDA = [
    'id', 'name', 'date_order', 'amount_total', 'state', 'user_id', 'partner_id', 'company_id',
]


def _m2o(v):
    """Sanitiza many2one Odoo: [id, nome] -> {id, nome}; False -> None."""
    if isinstance(v, (list, tuple)) and len(v) == 2:
        return {'id': v[0], 'nome': v[1]}
    return None


def _so_digitos(s):
    return ''.join(c for c in str(s) if c.isdigit()) if s else ''


def _fmt_cnpj_parcial(digs):
    """Aplica a mascara CNPJ (XX.XXX.XXX/XXXX-XX) ate onde houver digito.

    O campo l10n_br_cnpj no Odoo e' armazenado FORMATADO, entao buscar por digitos
    puros ('like 18467441000163') nunca casa. Reconstruir o prefixo formatado
    ('18.467.441') faz o 'like' encontrar tanto CNPJ completo quanto parcial.
    """
    seps = {2: '.', 5: '.', 8: '/', 12: '-'}
    out = ''
    for i, ch in enumerate(digs[:14]):
        if i in seps:
            out += seps[i]
        out += ch
    return out


def _cnpj_domain(campo, valor):
    """Domain OR para casar CNPJ digitado de varias formas contra o campo formatado."""
    pats = set()
    if any(c in str(valor) for c in './-'):  # usuario ja digitou formatado
        pats.add(str(valor))
    digs = _so_digitos(valor)
    if digs:
        pats.add(_fmt_cnpj_parcial(digs))  # mascara CNPJ parcial (caminho principal)
        pats.add(digs)                       # defensivo: registro eventualmente sem mascara
    pats = [p for p in pats if p]
    if not pats:
        return []
    if len(pats) == 1:
        return [(campo, 'like', pats[0])]
    dom = ['|'] * (len(pats) - 1)
    for p in pats:
        dom.append((campo, 'like', p))
    return dom


class ClienteOdooQuery:
    """Atomos READ sobre res.partner / sale.order. Cada metodo retorna dict JSON-serializavel."""

    def __init__(self, odoo):
        self.odoo = odoo
        self._campos_partner_ok = None

    def _campos_validos(self, desejados):
        """Intersecao entre 'desejados' e os campos que a instancia realmente tem."""
        if self._campos_partner_ok is None:
            try:
                meta = self.odoo.execute_kw('res.partner', 'fields_get', [], {'attributes': ['type']})
                self._campos_partner_ok = set(meta.keys())
            except Exception:
                # Fallback conservador: so' os comprovadamente existentes no codigo do projeto.
                self._campos_partner_ok = {
                    'id', 'name', 'l10n_br_cnpj', 'l10n_br_ie', 'l10n_br_razao_social',
                    'active', 'create_date',
                }
        return [c for c in desejados if c in self._campos_partner_ok]

    @staticmethod
    def _fmt_partner(p):
        return {
            'id': p.get('id'),
            'nome': (p.get('name') or '').strip(),
            'razao_social': (p.get('l10n_br_razao_social') or '').strip() or None,
            'cnpj': (p.get('l10n_br_cnpj') or '').strip() or None,
            'cpf': (p.get('l10n_br_cpf') or '').strip() or None,
            'ie': (p.get('l10n_br_ie') or '').strip() or None,
            'ativo': p.get('active'),
            'customer_rank': p.get('customer_rank'),
            'cidade': (p.get('city') or '').strip() or None,
            'uf': (_m2o(p.get('state_id')) or {}).get('nome'),
            'email': (p.get('email') or '').strip() or None,
            'telefone': (p.get('phone') or p.get('mobile') or '').strip() or None,
            'vendedor': _m2o(p.get('user_id')),
            'empresa': _m2o(p.get('company_id')),
            'criado_em': p.get('create_date'),
        }

    def _domain_clientes(self, args):
        domain = []
        if not args.incluir_inativos:
            domain.append(('active', '=', True))
        if not args.todos and 'customer_rank' in self._campos_validos(['customer_rank']):
            domain.append(('customer_rank', '>', 0))
        if args.company_id:
            domain.append(('company_id', '=', args.company_id))
        if args.cnpj:
            domain += _cnpj_domain('l10n_br_cnpj', args.cnpj)
        if args.nome:
            domain.append(('name', 'ilike', args.nome))
        if args.cidade:
            domain.append(('city', 'ilike', args.cidade))
        return domain

    def listar_clientes(self, args):
        domain = self._domain_clientes(args)
        total = self.odoo.search_count('res.partner', domain)
        if args.apenas_total:
            return {'modo': 'clientes', 'total': total, 'clientes': [], 'filtros': self._filtros(args)}
        fields = self._campos_validos(CAMPOS_PARTNER)
        rows = self.odoo.search_read(
            'res.partner', domain, fields=fields,
            limit=args.limit, order='name asc',
        )
        return {
            'modo': 'clientes',
            'total': total,
            'retornados': len(rows),
            'limit': args.limit,
            'filtros': self._filtros(args),
            'clientes': [self._fmt_partner(p) for p in rows],
        }

    def detalhar_cliente(self, args):
        domain = []
        if args.cliente_id:
            domain = [('id', '=', args.cliente_id)]
        elif args.cnpj:
            domain = _cnpj_domain('l10n_br_cnpj', args.cnpj)
        else:
            return {'erro': 'modo detalhes exige --cliente-id ou --cnpj'}
        fields = self._campos_validos(CAMPOS_PARTNER)
        rows = self.odoo.search_read('res.partner', domain, fields=fields, limit=5)
        if not rows:
            return {'modo': 'detalhes', 'encontrado': False, 'cliente': None}
        cli = self._fmt_partner(rows[0])
        vendas = self.odoo.search_read(
            'sale.order', [('partner_id', '=', cli['id'])],
            fields=CAMPOS_VENDA, limit=args.limit_vendas, order='date_order desc',
        )
        cli['ultimas_vendas'] = [{
            'pedido': v.get('name'),
            'data': v.get('date_order'),
            'valor_total': v.get('amount_total'),
            'status': v.get('state'),
            'vendedor': _m2o(v.get('user_id')),
        } for v in vendas]
        cli['outros_partners_mesmo_cnpj'] = len(rows) - 1
        return {'modo': 'detalhes', 'encontrado': True, 'cliente': cli}

    def agrupar_por_vendedor(self, args):
        domain = []
        if args.confirmados:
            domain.append(('state', 'in', ['sale', 'done']))
        if args.company_id:
            domain.append(('company_id', '=', args.company_id))
        if args.desde:
            domain.append(('date_order', '>=', args.desde))
        grupos = self.odoo.execute_kw(
            'sale.order', 'read_group',
            [domain, ['amount_total:sum'], ['user_id']],
            {'lazy': False},
        )
        out = []
        for g in grupos:
            out.append({
                'vendedor': _m2o(g.get('user_id')) or {'id': None, 'nome': '(sem vendedor)'},
                'qtd_pedidos': g.get('__count') or g.get('user_id_count'),
                'valor_total': g.get('amount_total'),
            })
        out.sort(key=lambda x: (x['valor_total'] or 0), reverse=True)
        return {
            'modo': 'por-vendedor',
            'filtros': {'confirmados': args.confirmados, 'company': COMPANIES.get(args.company_id), 'desde': args.desde},
            'vendedores': out,
        }

    @staticmethod
    def _filtros(args):
        return {
            'cnpj': args.cnpj, 'nome': args.nome, 'cidade': args.cidade,
            'company': COMPANIES.get(args.company_id), 'incluir_inativos': args.incluir_inativos,
            'todos_ranks': args.todos,
        }


# ------------------------------- CLI -------------------------------

def build_parser():
    ap = argparse.ArgumentParser(description='Consulta READ-only de clientes (res.partner) no Odoo.')
    ap.add_argument('--modo', choices=['clientes', 'detalhes', 'por-vendedor'], default='clientes',
                    help='clientes (busca/lista), detalhes (1 cliente+vendas), por-vendedor (read_group).')
    # filtros modo clientes
    ap.add_argument('--cnpj', help='CNPJ (parcial ou completo; aceita formatado ou so digitos).')
    ap.add_argument('--nome', help='Nome/razao (ilike).')
    ap.add_argument('--cidade', help='Cidade (ilike).')
    ap.add_argument('--company-id', type=int, dest='company_id',
                    help='Empresa Odoo: 1=FB, 3=SC, 4=CD, 5=LF.')
    ap.add_argument('--incluir-inativos', action='store_true', help='Inclui parceiros active=False.')
    ap.add_argument('--todos', action='store_true',
                    help='Nao filtra por customer_rank>0 (inclui fornecedores/contatos).')
    ap.add_argument('--apenas-total', action='store_true', help='So a contagem (search_count), sem listar.')
    ap.add_argument('--limit', type=int, default=200, help='Maximo de clientes retornados (default 200).')
    # modo detalhes
    ap.add_argument('--cliente-id', type=int, dest='cliente_id', help='[detalhes] ID do res.partner.')
    ap.add_argument('--limit-vendas', type=int, default=10, dest='limit_vendas',
                    help='[detalhes] Qtd de ultimas vendas (default 10).')
    # modo por-vendedor
    ap.add_argument('--confirmados', action='store_true',
                    help='[por-vendedor] So pedidos confirmados (state in sale,done).')
    ap.add_argument('--desde', help='[por-vendedor] Data minima do pedido (YYYY-MM-DD).')
    # saida
    ap.add_argument('--formato', choices=['json', 'tabela'], default='tabela')
    ap.add_argument('--json', action='store_true', help='Alias de --formato json.')
    adicionar_args_padrao(ap)  # --quiet + --forcar-concorrencia
    return ap


def _aplicar_alias_json(args):
    if getattr(args, 'json', False):
        args.formato = 'json'
    return args


def _print_clientes(res, args):
    if args.formato == 'json':
        print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
        return 0
    print(f"Total (search_count): {res['total']}")
    if res.get('apenas_total') or args.apenas_total:
        return 0
    print(f"Retornados: {res.get('retornados', 0)} (limit {res.get('limit')})")
    if not res['clientes']:
        print('(nenhum cliente encontrado)')
        return 0
    print('=' * 90)
    for c in res['clientes']:
        cnpj = c['cnpj'] or c['cpf'] or '-'
        cidade = c['cidade'] or '-'
        vend = (c['vendedor'] or {}).get('nome', '-')
        print(f"{c['id']:>8}  {(c['nome'] or '')[:42]:<42}  {cnpj:<18}  {cidade[:18]:<18}  vend={vend}")
    return 0


def _print_detalhes(res, args):
    if args.formato == 'json':
        print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
        return 0
    if not res.get('encontrado'):
        print('(cliente nao encontrado)')
        return 0
    c = res['cliente']
    print(f"Cliente #{c['id']}: {c['nome']}")
    print(f"  Razao social : {c['razao_social'] or '-'}")
    print(f"  CNPJ/CPF     : {c['cnpj'] or c['cpf'] or '-'}   IE: {c['ie'] or '-'}")
    print(f"  Cidade/UF    : {c['cidade'] or '-'} / {c['uf'] or '-'}")
    print(f"  Contato      : {c['email'] or '-'}  {c['telefone'] or '-'}")
    print(f"  Vendedor     : {(c['vendedor'] or {}).get('nome', '-')}")
    print(f"  Empresa      : {(c['empresa'] or {}).get('nome', '-')}")
    print(f"  Ativo        : {c['ativo']}   Criado: {c['criado_em']}")
    print(f"  Ultimas vendas ({len(c.get('ultimas_vendas', []))}):")
    for v in c.get('ultimas_vendas', []):
        print(f"    {v['pedido']:<16} {str(v['data'])[:10]:<12} R$ {v['valor_total']:<12} {v['status']}")
    return 0


def _print_por_vendedor(res, args):
    if args.formato == 'json':
        print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
        return 0
    print(f"Pedidos por vendedor  (filtros: {res['filtros']})")
    print('=' * 70)
    for v in res['vendedores']:
        print(f"{(v['vendedor'] or {}).get('nome', '-')[:36]:<36}  pedidos={v['qtd_pedidos']:<6}  R$ {v['valor_total']}")
    return 0


def main():
    args = _aplicar_alias_json(build_parser().parse_args())
    app = setup_cli_completo(__file__, args.quiet, args.forcar_concorrencia)
    with app.app_context():
        odoo = get_odoo_connection()
        q = ClienteOdooQuery(odoo)
        if args.modo == 'clientes':
            return _print_clientes(q.listar_clientes(args), args)
        if args.modo == 'detalhes':
            res = q.detalhar_cliente(args)
            if res.get('erro'):
                print(res['erro'], file=sys.stderr)
                return 2
            return _print_detalhes(res, args)
        if args.modo == 'por-vendedor':
            return _print_por_vendedor(q.agrupar_por_vendedor(args), args)
    return 0


if __name__ == '__main__':
    sys.exit(main())
