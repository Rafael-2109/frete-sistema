"""
Auditoria 100% Bidirecional: Extrato Sistema vs Odoo (v2)
==========================================================

Cruza TODAS as linhas de extrato_item (Render) com TODAS as linhas do Odoo
(account.bank.statement.line) para detectar divergencias de reconciliacao.

Melhorias v2:
- Bidirecional: detecta linhas no Odoo NAO importadas no sistema
- Deep: valida cadeia completa (payment, partial_reconcile, full_reconcile, move_line)
- 10 categorias de divergencia (vs 4 na v1)

Pre-requisitos:
    Fase A: exportar dados do sistema via MCP Render (manual)
    -> /tmp/auditoria_v2_sistema.json
    -> /tmp/auditoria_v2_sistema_mn.json

Execute:
    source .venv/bin/activate
    python scripts/auditoria_extrato_vs_odoo.py --fase-b     # Exportar Odoo
    python scripts/auditoria_extrato_vs_odoo.py --fase-c     # Comparar
    python scripts/auditoria_extrato_vs_odoo.py --completo   # B + C
"""

import sys
import os
import json
import argparse
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ============================================================================
# Paths
# ============================================================================
SISTEMA_JSON = '/tmp/auditoria_v2_sistema.json'
SISTEMA_MN_JSON = '/tmp/auditoria_v2_sistema_mn.json'
ODOO_LINES_JSON = '/tmp/auditoria_v2_odoo_lines.json'
ODOO_MOVE_LINES_JSON = '/tmp/auditoria_v2_odoo_move_lines.json'
ODOO_PAYMENTS_JSON = '/tmp/auditoria_v2_odoo_payments.json'
ODOO_RECONCILES_JSON = '/tmp/auditoria_v2_odoo_reconciles.json'
RELATORIO_JSON = '/tmp/auditoria_v2_relatorio.json'
RESUMO_TXT = '/tmp/auditoria_v2_resumo.txt'

# ============================================================================
# Constantes
# ============================================================================
BATCH_SIZE = 500

# Journals bancarios que importamos (8 journals)
JOURNAL_IDS = [10, 386, 388, 389, 883, 1030, 1046, 1054]

JOURNAL_NAMES = {
    10: 'SIC',
    386: 'SIC2',
    388: 'BRAD',
    389: 'CAIXA',
    883: 'GRA1',
    1030: 'SANT',
    1046: 'AGISG',
    1054: 'VORTX',
}


def _serializar_odoo(dados):
    """Converte valores Odoo (date, many2one) para JSON-serializavel."""
    resultado = {}
    for k, v in dados.items():
        if hasattr(v, 'isoformat'):
            resultado[k] = v.isoformat()
        elif isinstance(v, list) and len(v) == 2 and isinstance(v[0], int):
            # many2one: [id, name] -> salva como id
            resultado[k] = v[0]
            resultado[f'{k}_name'] = v[1]
        elif v is False:
            resultado[k] = None
        else:
            resultado[k] = v
    return resultado


def _batched(iterable, n):
    """Divide iterable em batches de tamanho n."""
    items = list(iterable)
    for i in range(0, len(items), n):
        yield items[i:i + n]


# ============================================================================
# FASE A — Exportar TUDO do Render (SQLAlchemy, read-only)
# ============================================================================

def fase_a():
    """Fase A: exportar extrato_item e extrato_item_titulo do banco local."""
    from app import create_app
    from sqlalchemy import text

    print("=" * 70)
    print("FASE A — EXPORTAR DADOS DO SISTEMA (Render DB)")
    print("=" * 70)

    app = create_app()
    with app.app_context():
        from app import db

        # --- extrato_item ---
        print("\n  Exportando extrato_item (statement_line_id NOT NULL)...")
        query = text("""
            SELECT id, statement_line_id, status, status_match, aprovado, aprovado_por,
                   mensagem, valor, data_transacao::text, lote_id,
                   titulo_receber_id, titulo_pagar_id,
                   partial_reconcile_id, full_reconcile_id, payment_id,
                   move_id, credit_line_id, journal_id, journal_code,
                   processado_em::text, criado_em::text
            FROM extrato_item
            WHERE statement_line_id IS NOT NULL
            ORDER BY id
        """)

        with db.engine.connect() as conn:
            result = conn.execute(query)
            columns = list(result.keys())
            sistema_data = []
            for row in result:
                row_dict = {}
                for i, col in enumerate(columns):
                    val = row[i]
                    if hasattr(val, 'isoformat'):
                        val = val.isoformat()
                    elif isinstance(val, float):
                        val = round(val, 2)
                    row_dict[col] = val
                sistema_data.append(row_dict)

        print(f"  Total extrato_item exportados: {len(sistema_data)}")

        with open(SISTEMA_JSON, 'w') as f:
            json.dump(sistema_data, f, indent=2, default=str)
        print(f"  Salvo: {SISTEMA_JSON}")

        # --- extrato_item_titulo (M:N) ---
        print("\n  Exportando extrato_item_titulo...")
        query_mn = text("""
            SELECT eit.id, eit.extrato_item_id, eit.titulo_receber_id, eit.titulo_pagar_id,
                   eit.valor_alocado::float, eit.payment_id,
                   eit.partial_reconcile_id, eit.full_reconcile_id,
                   eit.status
            FROM extrato_item_titulo eit
            ORDER BY eit.id
        """)

        with db.engine.connect() as conn:
            result = conn.execute(query_mn)
            columns_mn = list(result.keys())
            mn_data = []
            for row in result:
                row_dict = {}
                for i, col in enumerate(columns_mn):
                    val = row[i]
                    if hasattr(val, 'isoformat'):
                        val = val.isoformat()
                    elif isinstance(val, float):
                        val = round(val, 2)
                    row_dict[col] = val
                mn_data.append(row_dict)

        print(f"  Total extrato_item_titulo exportados: {len(mn_data)}")

        with open(SISTEMA_MN_JSON, 'w') as f:
            json.dump(mn_data, f, indent=2, default=str)
        print(f"  Salvo: {SISTEMA_MN_JSON}")

    # Estatisticas rapidas
    por_status = defaultdict(int)
    for item in sistema_data:
        por_status[item.get('status', 'NULL')] += 1
    print("\n  Por status:")
    for status, count in sorted(por_status.items()):
        print(f"    {status:20s} {count:>8}")

    print("\n" + "=" * 70)
    print("FASE A COMPLETA")
    print("=" * 70)


# ============================================================================
# FASE B — Exportar TUDO do Odoo
# ============================================================================

def fase_b():
    """Fase B: buscar dados do Odoo (4 sub-etapas)."""
    from app import create_app
    from app.odoo.utils.connection import get_odoo_connection

    print("=" * 70)
    print("FASE B — EXPORTAR DADOS DO ODOO (bidirecional + deep)")
    print("=" * 70)

    # Carregar dados do sistema para coletar IDs a validar
    if not os.path.exists(SISTEMA_JSON):
        print(f"ERRO: {SISTEMA_JSON} nao encontrado.")
        print("Execute a Fase A (MCP Render) primeiro.")
        sys.exit(1)

    with open(SISTEMA_JSON) as f:
        sistema_data = json.load(f)
    print(f"Registros do sistema carregados: {len(sistema_data)}")

    app = create_app()
    with app.app_context():
        print("\nConectando ao Odoo...")
        conn = get_odoo_connection()
        if not conn.authenticate():
            print("ERRO: Falha na autenticacao com Odoo")
            sys.exit(1)
        print("Conectado ao Odoo.\n")

        _fase_b1_all_statement_lines(conn)
        _fase_b2_move_lines(conn)
        _fase_b3_payments(conn, sistema_data)
        _fase_b4_reconciles(conn, sistema_data)

    print("\n" + "=" * 70)
    print("FASE B COMPLETA")
    print("=" * 70)


def _fase_b1_all_statement_lines(conn):
    """B1: Buscar TODAS as statement lines dos journals monitorados (bidirecional)."""
    print("-" * 70)
    print("B1: Exportando TODAS as statement lines do Odoo (bidirecional)")
    print(f"    Journals: {JOURNAL_IDS}")
    print("-" * 70)

    fields = [
        'id', 'is_reconciled', 'date', 'amount', 'payment_ref',
        'journal_id', 'statement_id', 'move_id', 'partner_id',
        'write_date', 'company_id'
    ]

    domain = [['journal_id', 'in', JOURNAL_IDS]]
    all_lines = {}
    offset = 0
    batch_num = 0

    while True:
        batch_num += 1
        print(f"  Batch {batch_num}: offset={offset}, limit={BATCH_SIZE}...", end=" ", flush=True)

        try:
            results = conn.search_read(
                'account.bank.statement.line', domain,
                fields=fields, limit=BATCH_SIZE, offset=offset,
                order='id asc'
            )
        except Exception as e:
            print(f"ERRO: {e}")
            break

        if not results:
            print("(vazio — fim)")
            break

        for r in results:
            all_lines[r['id']] = _serializar_odoo(r)

        print(f"OK ({len(results)} registros, total acumulado: {len(all_lines)})")

        if len(results) < BATCH_SIZE:
            break
        offset += BATCH_SIZE

    # Salvar
    output = {
        'metadata': {
            'exportado_em': datetime.now().isoformat(),
            'total_linhas': len(all_lines),
            'journals': JOURNAL_IDS,
        },
        'dados': {str(k): v for k, v in all_lines.items()},
    }
    with open(ODOO_LINES_JSON, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"  Salvo: {ODOO_LINES_JSON} ({len(all_lines)} linhas)")

    # Estatisticas por journal
    por_journal = defaultdict(int)
    por_journal_rec = defaultdict(int)
    for line in all_lines.values():
        jid = line.get('journal_id')
        por_journal[jid] += 1
        if line.get('is_reconciled'):
            por_journal_rec[jid] += 1
    print("\n  Por journal:")
    for jid in sorted(por_journal.keys()):
        nome = JOURNAL_NAMES.get(jid, f'?{jid}')
        total = por_journal[jid]
        rec = por_journal_rec.get(jid, 0)
        print(f"    {nome:8s} (ID={jid}): {total:>6} total, {rec:>6} reconciliados ({rec/total*100:.1f}%)")


def _fase_b2_move_lines(conn):
    """B2: Buscar move lines dos statement lines para validar cadeia de reconciliacao."""
    print("\n" + "-" * 70)
    print("B2: Exportando move lines (cadeia de reconciliacao)")
    print("-" * 70)

    # Carregar linhas do Odoo exportadas em B1
    if not os.path.exists(ODOO_LINES_JSON):
        print("ERRO: Execute B1 primeiro.")
        return

    with open(ODOO_LINES_JSON) as f:
        odoo_data = json.load(f)

    # Coletar move_ids distintos (nao-None)
    move_ids = set()
    for line in odoo_data['dados'].values():
        mid = line.get('move_id')
        if mid:
            move_ids.add(mid)

    move_ids = sorted(move_ids)
    print(f"  move_ids distintos: {len(move_ids)}")

    if not move_ids:
        print("  Nenhum move_id encontrado. Pulando.")
        with open(ODOO_MOVE_LINES_JSON, 'w') as f:
            json.dump({'metadata': {'total': 0}, 'dados': {}}, f)
        return

    fields = [
        'id', 'move_id', 'account_id', 'reconciled',
        'full_reconcile_id', 'matched_credit_ids', 'matched_debit_ids',
        'amount_residual', 'debit', 'credit'
    ]

    all_move_lines = {}
    total_batches = (len(move_ids) + BATCH_SIZE - 1) // BATCH_SIZE
    erros = []

    for i, batch in enumerate(_batched(move_ids, BATCH_SIZE), 1):
        print(f"  Batch {i}/{total_batches}: {len(batch)} move_ids...", end=" ", flush=True)

        try:
            domain = [['move_id', 'in', list(batch)]]
            results = conn.search_read(
                'account.move.line', domain,
                fields=fields, limit=0
            )
            for r in results:
                all_move_lines[r['id']] = _serializar_odoo(r)
            print(f"OK ({len(results)} linhas)")
        except Exception as e:
            print(f"ERRO: {e}")
            erros.append({'batch': i, 'erro': str(e)})

    # Indexar por move_id para facilitar lookup
    by_move_id = defaultdict(list)
    for ml in all_move_lines.values():
        mid = ml.get('move_id')
        if mid:
            by_move_id[mid].append(ml['id'])

    output = {
        'metadata': {
            'exportado_em': datetime.now().isoformat(),
            'total_move_lines': len(all_move_lines),
            'total_move_ids_solicitados': len(move_ids),
            'total_move_ids_com_linhas': len(by_move_id),
            'erros': erros,
        },
        'dados': {str(k): v for k, v in all_move_lines.items()},
        'indice_por_move_id': {str(k): v for k, v in by_move_id.items()},
    }
    with open(ODOO_MOVE_LINES_JSON, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"  Salvo: {ODOO_MOVE_LINES_JSON} ({len(all_move_lines)} move lines)")


def _fase_b3_payments(conn, sistema_data):
    """B3: Validar payment_ids referenciados no sistema."""
    print("\n" + "-" * 70)
    print("B3: Validando payments referenciados no sistema")
    print("-" * 70)

    # Coletar payment_ids do sistema (NOT NULL)
    payment_ids = set()
    for item in sistema_data:
        pid = item.get('payment_id')
        if pid:
            payment_ids.add(pid)

    payment_ids = sorted(payment_ids)
    print(f"  payment_ids distintos no sistema: {len(payment_ids)}")

    if not payment_ids:
        print("  Nenhum payment_id. Pulando.")
        with open(ODOO_PAYMENTS_JSON, 'w') as f:
            json.dump({'metadata': {'total': 0}, 'dados': {}}, f)
        return

    fields = [
        'id', 'state', 'amount', 'payment_type', 'partner_id',
        'move_id', 'reconciled_statement_line_ids'
    ]

    all_payments = {}
    total_batches = (len(payment_ids) + BATCH_SIZE - 1) // BATCH_SIZE
    erros = []

    for i, batch in enumerate(_batched(payment_ids, BATCH_SIZE), 1):
        print(f"  Batch {i}/{total_batches}: {len(batch)} IDs...", end=" ", flush=True)

        try:
            results = conn.read('account.payment', list(batch), fields=fields)
            for r in results:
                all_payments[r['id']] = _serializar_odoo(r)
            print(f"OK ({len(results)} payments)")
        except Exception as e:
            print(f"ERRO: {e}")
            erros.append({'batch': i, 'erro': str(e)})

    # IDs nao encontrados
    ids_encontrados = set(all_payments.keys())
    ids_nao_encontrados = set(payment_ids) - ids_encontrados

    output = {
        'metadata': {
            'exportado_em': datetime.now().isoformat(),
            'total_solicitados': len(payment_ids),
            'total_encontrados': len(all_payments),
            'total_nao_encontrados': len(ids_nao_encontrados),
            'ids_nao_encontrados': sorted(ids_nao_encontrados),
            'erros': erros,
        },
        'dados': {str(k): v for k, v in all_payments.items()},
    }
    with open(ODOO_PAYMENTS_JSON, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"  Salvo: {ODOO_PAYMENTS_JSON} ({len(all_payments)} payments)")
    if ids_nao_encontrados:
        print(f"  ATENCAO: {len(ids_nao_encontrados)} payment_ids NAO encontrados no Odoo!")


def _fase_b4_reconciles(conn, sistema_data):
    """B4: Validar partial_reconcile_ids e full_reconcile_ids referenciados no sistema."""
    print("\n" + "-" * 70)
    print("B4: Validando reconcile IDs referenciados no sistema")
    print("-" * 70)

    # Coletar IDs distintos
    partial_ids = set()
    full_ids = set()
    for item in sistema_data:
        pid = item.get('partial_reconcile_id')
        if pid:
            partial_ids.add(pid)
        fid = item.get('full_reconcile_id')
        if fid:
            full_ids.add(fid)

    partial_ids = sorted(partial_ids)
    full_ids = sorted(full_ids)
    print(f"  partial_reconcile_ids distintos: {len(partial_ids)}")
    print(f"  full_reconcile_ids distintos: {len(full_ids)}")

    # --- Partial Reconcile ---
    all_partials = {}
    if partial_ids:
        fields = ['id', 'debit_move_id', 'credit_move_id', 'amount', 'full_reconcile_id']
        erros_partial = []
        total_batches = (len(partial_ids) + BATCH_SIZE - 1) // BATCH_SIZE

        for i, batch in enumerate(_batched(partial_ids, BATCH_SIZE), 1):
            print(f"  Partial batch {i}/{total_batches}: {len(batch)} IDs...", end=" ", flush=True)
            try:
                results = conn.read('account.partial.reconcile', list(batch), fields=fields)
                for r in results:
                    all_partials[r['id']] = _serializar_odoo(r)
                print(f"OK ({len(results)})")
            except Exception as e:
                print(f"ERRO: {e}")
                erros_partial.append({'batch': i, 'erro': str(e)})

        partial_nao_enc = set(partial_ids) - set(all_partials.keys())
        if partial_nao_enc:
            print(f"  ATENCAO: {len(partial_nao_enc)} partial_reconcile_ids NAO encontrados!")
    else:
        erros_partial = []
        partial_nao_enc = set()

    # --- Full Reconcile ---
    all_fulls = {}
    if full_ids:
        fields = ['id', 'partial_reconcile_ids']
        erros_full = []
        total_batches = (len(full_ids) + BATCH_SIZE - 1) // BATCH_SIZE

        for i, batch in enumerate(_batched(full_ids, BATCH_SIZE), 1):
            print(f"  Full batch {i}/{total_batches}: {len(batch)} IDs...", end=" ", flush=True)
            try:
                results = conn.read('account.full.reconcile', list(batch), fields=fields)
                for r in results:
                    all_fulls[r['id']] = _serializar_odoo(r)
                print(f"OK ({len(results)})")
            except Exception as e:
                print(f"ERRO: {e}")
                erros_full.append({'batch': i, 'erro': str(e)})

        full_nao_enc = set(full_ids) - set(all_fulls.keys())
        if full_nao_enc:
            print(f"  ATENCAO: {len(full_nao_enc)} full_reconcile_ids NAO encontrados!")
    else:
        erros_full = []
        full_nao_enc = set()

    output = {
        'metadata': {
            'exportado_em': datetime.now().isoformat(),
            'partial': {
                'total_solicitados': len(partial_ids),
                'total_encontrados': len(all_partials),
                'total_nao_encontrados': len(partial_nao_enc),
                'ids_nao_encontrados': sorted(partial_nao_enc),
                'erros': erros_partial,
            },
            'full': {
                'total_solicitados': len(full_ids),
                'total_encontrados': len(all_fulls),
                'total_nao_encontrados': len(full_nao_enc),
                'ids_nao_encontrados': sorted(full_nao_enc),
                'erros': erros_full,
            },
        },
        'partial_reconciles': {str(k): v for k, v in all_partials.items()},
        'full_reconciles': {str(k): v for k, v in all_fulls.items()},
    }
    with open(ODOO_RECONCILES_JSON, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"  Salvo: {ODOO_RECONCILES_JSON}")
    print(f"    Partials: {len(all_partials)}, Fulls: {len(all_fulls)}")


# ============================================================================
# FASE C — Comparacao 100% bidirecional + deep
# ============================================================================

def fase_c():
    """Fase C: comparar todos os dados e gerar relatorio com 10 categorias."""
    print("=" * 70)
    print("FASE C — COMPARACAO 100% BIDIRECIONAL + DEEP")
    print("=" * 70)

    # --- Carregar todos os arquivos ---
    arquivos_necessarios = {
        'sistema': SISTEMA_JSON,
        'odoo_lines': ODOO_LINES_JSON,
        'odoo_move_lines': ODOO_MOVE_LINES_JSON,
        'odoo_payments': ODOO_PAYMENTS_JSON,
        'odoo_reconciles': ODOO_RECONCILES_JSON,
    }
    dados = {}
    for nome, path in arquivos_necessarios.items():
        if not os.path.exists(path):
            print(f"ERRO: {path} nao encontrado.")
            if nome == 'sistema':
                print("Execute a Fase A (MCP Render) primeiro.")
            else:
                print("Execute a Fase B primeiro.")
            sys.exit(1)
        with open(path) as f:
            dados[nome] = json.load(f)
        print(f"  Carregado: {nome} ({path})")

    # Carregar M:N (opcional)
    sistema_mn = []
    if os.path.exists(SISTEMA_MN_JSON):
        with open(SISTEMA_MN_JSON) as f:
            sistema_mn = json.load(f)
        print(f"  Carregado: sistema_mn ({SISTEMA_MN_JSON}, {len(sistema_mn)} vinculos)")

    sistema_data = dados['sistema']
    odoo_lines = dados['odoo_lines']['dados']
    odoo_move_lines = dados['odoo_move_lines']['dados']
    odoo_payments = dados['odoo_payments']['dados']
    odoo_reconciles_partial = dados['odoo_reconciles']['partial_reconciles']
    odoo_reconciles_full = dados['odoo_reconciles']['full_reconciles']

    # Indice de move_lines agrupadas por move_id (para Cat 10)
    odoo_ml_por_move_id = dados['odoo_move_lines'].get('indice_por_move_id', {})

    print(f"\n  Sistema: {len(sistema_data)} registros")
    print(f"  Odoo lines: {len(odoo_lines)} registros")
    print(f"  Odoo move lines: {len(odoo_move_lines)} registros")
    print(f"  Odoo payments: {len(odoo_payments)} registros")
    print(f"  Odoo partials: {len(odoo_reconciles_partial)} registros")
    print(f"  Odoo fulls: {len(odoo_reconciles_full)} registros")

    # --- Indexar sistema por statement_line_id ---
    sistema_por_line_id = {}
    for item in sistema_data:
        lid = item.get('statement_line_id')
        if lid:
            sistema_por_line_id[str(lid)] = item

    # --- 10 categorias de divergencia ---
    divergencias = {
        'CONCILIADO_LOCAL_NAO_RECONCILIADO_ODOO': [],   # 1 CRITICA
        'NAO_CONCILIADO_LOCAL_RECONCILIADO_ODOO': [],    # 2 MEDIA
        'ORFAO_LOCAL': [],                                # 3 ALTA
        'NAO_IMPORTADO': [],                              # 4 ALTA
        'PAYMENT_INEXISTENTE': [],                        # 5 CRITICA
        'PAYMENT_NAO_POSTED': [],                         # 6 ALTA
        'PARTIAL_RECONCILE_INEXISTENTE': [],              # 7 ALTA
        'FULL_RECONCILE_INEXISTENTE': [],                 # 8 ALTA
        'VALOR_DIVERGENTE': [],                           # 9 INFO
        'MOVE_LINE_NAO_RECONCILIADA': [],                 # 10 CRITICA
    }

    severidade_map = {
        'CONCILIADO_LOCAL_NAO_RECONCILIADO_ODOO': 'CRITICA',
        'NAO_CONCILIADO_LOCAL_RECONCILIADO_ODOO': 'MEDIA',
        'ORFAO_LOCAL': 'ALTA',
        'NAO_IMPORTADO': 'ALTA',
        'PAYMENT_INEXISTENTE': 'CRITICA',
        'PAYMENT_NAO_POSTED': 'ALTA',
        'PARTIAL_RECONCILE_INEXISTENTE': 'ALTA',
        'FULL_RECONCILE_INEXISTENTE': 'ALTA',
        'VALOR_DIVERGENTE': 'INFO',
        'MOVE_LINE_NAO_RECONCILIADA': 'CRITICA',
    }

    # Contadores
    stats = {
        'total_sistema_processado': 0,
        'total_concordante': 0,
        'total_divergente_unico': 0,
        'por_status_sistema': defaultdict(int),
        'por_status_match_sistema': defaultdict(int),
        'por_journal_sistema': defaultdict(int),
        'por_journal_odoo': defaultdict(int),
        'por_journal_nao_importado': defaultdict(int),
        'conciliado_e_reconciliado': 0,
        'pendente_e_nao_reconciliado': 0,
        'payments_validos': 0,
        'payments_invalidos': 0,
        'partials_validos': 0,
        'partials_invalidos': 0,
        'fulls_validos': 0,
        'fulls_invalidos': 0,
    }

    # --- Processar linhas do SISTEMA (direcao Sistema → Odoo) ---
    print("\n  Processando Sistema -> Odoo...")
    ids_sistema_divergentes = set()

    for item in sistema_data:
        stats['total_sistema_processado'] += 1
        stats['por_status_sistema'][item.get('status', 'NULL')] += 1
        stats['por_status_match_sistema'][item.get('status_match', 'NULL')] += 1

        jcode = item.get('journal_code', 'NULL')
        stats['por_journal_sistema'][jcode] += 1

        line_id = str(item.get('statement_line_id'))
        odoo_line = odoo_lines.get(line_id)

        item_divergente = False

        # --- Cat 3: ORFAO_LOCAL ---
        if odoo_line is None:
            divergencias['ORFAO_LOCAL'].append({
                'extrato_item_id': item['id'],
                'statement_line_id': item.get('statement_line_id'),
                'status': item.get('status'),
                'valor': item.get('valor'),
                'data_transacao': item.get('data_transacao'),
                'lote_id': item.get('lote_id'),
                'journal_code': jcode,
                'mensagem': item.get('mensagem'),
            })
            item_divergente = True
        else:
            is_conciliado_local = item.get('status') == 'CONCILIADO'
            is_reconciled_odoo = odoo_line.get('is_reconciled', False)

            # --- Cat 1: CONCILIADO_LOCAL_NAO_RECONCILIADO_ODOO ---
            if is_conciliado_local and not is_reconciled_odoo:
                divergencias['CONCILIADO_LOCAL_NAO_RECONCILIADO_ODOO'].append({
                    'extrato_item_id': item['id'],
                    'statement_line_id': item.get('statement_line_id'),
                    'status_local': item.get('status'),
                    'aprovado': item.get('aprovado'),
                    'aprovado_por': item.get('aprovado_por'),
                    'valor_local': item.get('valor'),
                    'valor_odoo': odoo_line.get('amount'),
                    'data_transacao': item.get('data_transacao'),
                    'lote_id': item.get('lote_id'),
                    'journal_code': jcode,
                    'payment_id': item.get('payment_id'),
                    'partial_reconcile_id': item.get('partial_reconcile_id'),
                    'full_reconcile_id': item.get('full_reconcile_id'),
                    'mensagem': item.get('mensagem'),
                    'odoo_payment_ref': odoo_line.get('payment_ref'),
                    'odoo_write_date': odoo_line.get('write_date'),
                    'odoo_move_id': odoo_line.get('move_id'),
                })
                item_divergente = True

            # --- Cat 2: NAO_CONCILIADO_LOCAL_RECONCILIADO_ODOO ---
            elif not is_conciliado_local and is_reconciled_odoo:
                divergencias['NAO_CONCILIADO_LOCAL_RECONCILIADO_ODOO'].append({
                    'extrato_item_id': item['id'],
                    'statement_line_id': item.get('statement_line_id'),
                    'status_local': item.get('status'),
                    'status_match_local': item.get('status_match'),
                    'valor_local': item.get('valor'),
                    'valor_odoo': odoo_line.get('amount'),
                    'data_transacao': item.get('data_transacao'),
                    'lote_id': item.get('lote_id'),
                    'journal_code': jcode,
                    'mensagem': item.get('mensagem'),
                    'odoo_payment_ref': odoo_line.get('payment_ref'),
                    'odoo_write_date': odoo_line.get('write_date'),
                })
                item_divergente = True

            # Concordante
            elif is_conciliado_local and is_reconciled_odoo:
                stats['conciliado_e_reconciliado'] += 1
            elif not is_conciliado_local and not is_reconciled_odoo:
                stats['pendente_e_nao_reconciliado'] += 1

            # --- Cat 9: VALOR_DIVERGENTE ---
            valor_local = abs(item.get('valor', 0) or 0)
            valor_odoo = abs(odoo_line.get('amount', 0) or 0)
            if abs(valor_local - valor_odoo) > 0.01:
                divergencias['VALOR_DIVERGENTE'].append({
                    'extrato_item_id': item['id'],
                    'statement_line_id': item.get('statement_line_id'),
                    'valor_local': item.get('valor'),
                    'valor_odoo': odoo_line.get('amount'),
                    'diferenca': round(valor_local - valor_odoo, 2),
                    'status_local': item.get('status'),
                    'journal_code': jcode,
                })
                # Nao marca item_divergente pois e informativo

        # --- Cat 5: PAYMENT_INEXISTENTE ---
        pid = item.get('payment_id')
        if pid:
            if str(pid) in odoo_payments:
                payment = odoo_payments[str(pid)]
                stats['payments_validos'] += 1
                # --- Cat 6: PAYMENT_NAO_POSTED ---
                if payment.get('state') != 'posted':
                    divergencias['PAYMENT_NAO_POSTED'].append({
                        'extrato_item_id': item['id'],
                        'statement_line_id': item.get('statement_line_id'),
                        'payment_id': pid,
                        'payment_state': payment.get('state'),
                        'payment_amount': payment.get('amount'),
                        'status_local': item.get('status'),
                        'journal_code': jcode,
                    })
                    item_divergente = True
            else:
                divergencias['PAYMENT_INEXISTENTE'].append({
                    'extrato_item_id': item['id'],
                    'statement_line_id': item.get('statement_line_id'),
                    'payment_id': pid,
                    'status_local': item.get('status'),
                    'journal_code': jcode,
                })
                stats['payments_invalidos'] += 1
                item_divergente = True

        # --- Cat 7: PARTIAL_RECONCILE_INEXISTENTE ---
        prid = item.get('partial_reconcile_id')
        if prid:
            if str(prid) in odoo_reconciles_partial:
                stats['partials_validos'] += 1
            else:
                divergencias['PARTIAL_RECONCILE_INEXISTENTE'].append({
                    'extrato_item_id': item['id'],
                    'statement_line_id': item.get('statement_line_id'),
                    'partial_reconcile_id': prid,
                    'status_local': item.get('status'),
                    'journal_code': jcode,
                })
                stats['partials_invalidos'] += 1
                item_divergente = True

        # --- Cat 8: FULL_RECONCILE_INEXISTENTE ---
        frid = item.get('full_reconcile_id')
        if frid:
            if str(frid) in odoo_reconciles_full:
                stats['fulls_validos'] += 1
            else:
                divergencias['FULL_RECONCILE_INEXISTENTE'].append({
                    'extrato_item_id': item['id'],
                    'statement_line_id': item.get('statement_line_id'),
                    'full_reconcile_id': frid,
                    'status_local': item.get('status'),
                    'journal_code': jcode,
                })
                stats['fulls_invalidos'] += 1
                item_divergente = True

        # --- Cat 10: MOVE_LINE_NAO_RECONCILIADA ---
        # Verifica se ALGUMA move line do move esta reconciliada.
        # No Odoo, o move de um statement line gera 2 move lines:
        #   - Linha do BANCO (conta de liquidez) → NUNCA reconciliada
        #   - Linha TRANSITORIA (conta PAG/REC PENDENTES) → reconciliada via payment
        # O credit_line_id salvo no sistema aponta para a linha do BANCO (credit>0),
        # entao verificar apenas ela gera falso positivo.
        # A verificacao correta: checar se a linha transitoria foi reconciliada.
        if item.get('status') == 'CONCILIADO' and item.get('move_id') and odoo_line:
            move_id_str = str(item['move_id'])
            ml_ids = odoo_ml_por_move_id.get(move_id_str, [])

            # Verificar se ALGUMA move line desse move tem reconciled=True
            alguma_reconciliada = False
            detalhes_mls = []
            for ml_id in ml_ids:
                ml = odoo_move_lines.get(str(ml_id))
                if ml:
                    detalhes_mls.append({
                        'ml_id': ml_id,
                        'account_id': ml.get('account_id'),
                        'account_id_name': ml.get('account_id_name'),
                        'reconciled': ml.get('reconciled'),
                        'amount_residual': ml.get('amount_residual'),
                        'full_reconcile_id': ml.get('full_reconcile_id'),
                        'debit': ml.get('debit'),
                        'credit': ml.get('credit'),
                    })
                    if ml.get('reconciled'):
                        alguma_reconciliada = True

            if not alguma_reconciliada:
                divergencias['MOVE_LINE_NAO_RECONCILIADA'].append({
                    'extrato_item_id': item['id'],
                    'statement_line_id': item.get('statement_line_id'),
                    'move_id': item['move_id'],
                    'credit_line_id': item.get('credit_line_id'),
                    'move_lines': detalhes_mls,
                    'status_local': item.get('status'),
                    'journal_code': jcode,
                })
                item_divergente = True

        if item_divergente:
            ids_sistema_divergentes.add(item['id'])

    stats['total_concordante'] = stats['total_sistema_processado'] - len(ids_sistema_divergentes)
    stats['total_divergente_unico'] = len(ids_sistema_divergentes)

    # --- Processar linhas do ODOO nao importadas (direcao Odoo → Sistema) ---
    print("  Processando Odoo -> Sistema (bidirecional)...")

    for line_id_str, odoo_line in odoo_lines.items():
        jid = odoo_line.get('journal_id')
        stats['por_journal_odoo'][jid] += 1

        # --- Cat 4: NAO_IMPORTADO ---
        if line_id_str not in sistema_por_line_id:
            divergencias['NAO_IMPORTADO'].append({
                'statement_line_id': int(line_id_str),
                'journal_id': jid,
                'journal_name': JOURNAL_NAMES.get(jid, f'?{jid}'),
                'is_reconciled': odoo_line.get('is_reconciled'),
                'amount': odoo_line.get('amount'),
                'date': odoo_line.get('date'),
                'payment_ref': odoo_line.get('payment_ref'),
                'partner_id': odoo_line.get('partner_id'),
                'write_date': odoo_line.get('write_date'),
            })
            stats['por_journal_nao_importado'][jid] += 1

    print(f"  NAO_IMPORTADO: {len(divergencias['NAO_IMPORTADO'])} linhas no Odoo sem correspondente no sistema")

    # --- Estatisticas de cobertura por journal ---
    cobertura = {}
    for jid in JOURNAL_IDS:
        total_odoo = stats['por_journal_odoo'].get(jid, 0)
        nao_imp = stats['por_journal_nao_importado'].get(jid, 0)
        importados = total_odoo - nao_imp
        cobertura[jid] = {
            'journal': JOURNAL_NAMES.get(jid, f'?{jid}'),
            'total_odoo': total_odoo,
            'importados': importados,
            'nao_importados': nao_imp,
            'cobertura_pct': round(importados / total_odoo * 100, 1) if total_odoo > 0 else 0,
        }

    # --- Montar relatorio ---
    pct_concordante = (
        stats['total_concordante'] / stats['total_sistema_processado'] * 100
        if stats['total_sistema_processado'] > 0 else 0
    )

    relatorio = {
        'gerado_em': datetime.now().isoformat(),
        'versao': 'v2.1 — bidirecional + deep (fix Cat10 transitional account)',
        'estatisticas': {
            'total_sistema_processado': stats['total_sistema_processado'],
            'total_odoo_lines': len(odoo_lines),
            'total_concordante': stats['total_concordante'],
            'total_divergente_unico': stats['total_divergente_unico'],
            'percentual_concordancia': round(pct_concordante, 2),
            'conciliado_e_reconciliado': stats['conciliado_e_reconciliado'],
            'pendente_e_nao_reconciliado': stats['pendente_e_nao_reconciliado'],
            'payments_validos': stats['payments_validos'],
            'payments_invalidos': stats['payments_invalidos'],
            'partials_validos': stats['partials_validos'],
            'partials_invalidos': stats['partials_invalidos'],
            'fulls_validos': stats['fulls_validos'],
            'fulls_invalidos': stats['fulls_invalidos'],
            'por_status_sistema': dict(stats['por_status_sistema']),
            'por_status_match_sistema': dict(stats['por_status_match_sistema']),
        },
        'cobertura_por_journal': cobertura,
        'divergencias': {
            'resumo': {cat: len(items) for cat, items in divergencias.items()},
            'por_severidade': {
                sev: sum(
                    len(divergencias[cat]) for cat, s in severidade_map.items() if s == sev
                )
                for sev in ['CRITICA', 'ALTA', 'MEDIA', 'INFO']
            },
        },
        'divergencias_detalhadas': divergencias,
    }

    # Salvar JSON
    with open(RELATORIO_JSON, 'w') as f:
        json.dump(relatorio, f, indent=2, default=str)
    print(f"\n  Relatorio JSON: {RELATORIO_JSON}")

    # --- Gerar resumo legivel ---
    _gerar_resumo(relatorio, divergencias, stats, cobertura)


def _gerar_resumo(relatorio, divergencias, stats, cobertura):
    """Gera resumo legivel em TXT."""
    L = []  # linhas do resumo
    est = relatorio['estatisticas']
    pct = est['percentual_concordancia']

    L.append("=" * 80)
    L.append("AUDITORIA 100% BIDIRECIONAL: EXTRATO SISTEMA vs ODOO (v2)")
    L.append(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    L.append("=" * 80)

    # --- Estatisticas gerais ---
    L.append("")
    L.append("ESTATISTICAS GERAIS")
    L.append("-" * 50)
    L.append(f"  Total sistema (extrato_item):    {est['total_sistema_processado']:>8}")
    L.append(f"  Total Odoo (statement lines):    {est['total_odoo_lines']:>8}")
    L.append(f"  Concordantes (sistema):          {est['total_concordante']:>8} ({pct:.1f}%)")
    L.append(f"  Divergentes unicos (sistema):    {est['total_divergente_unico']:>8} ({100-pct:.1f}%)")
    L.append("")
    L.append(f"    Conciliado + Reconciliado:     {est['conciliado_e_reconciliado']:>8}")
    L.append(f"    Pendente + Nao Reconciliado:   {est['pendente_e_nao_reconciliado']:>8}")

    # --- Validacao de IDs ---
    L.append("")
    L.append("VALIDACAO DE IDs ODOO")
    L.append("-" * 50)
    L.append(f"  Payments validos / invalidos:    {est['payments_validos']:>6} / {est['payments_invalidos']:>6}")
    L.append(f"  Partials validos / invalidos:    {est['partials_validos']:>6} / {est['partials_invalidos']:>6}")
    L.append(f"  Fulls validos / invalidos:       {est['fulls_validos']:>6} / {est['fulls_invalidos']:>6}")

    # --- Cobertura por journal ---
    L.append("")
    L.append("COBERTURA DE IMPORTACAO POR JOURNAL")
    L.append("-" * 70)
    L.append(f"  {'Journal':10s} {'Total Odoo':>12} {'Importados':>12} {'Nao Imp.':>10} {'Cobertura':>10}")
    L.append(f"  {'-'*10:10s} {'-'*12:>12} {'-'*12:>12} {'-'*10:>10} {'-'*10:>10}")
    for jid in JOURNAL_IDS:
        c = cobertura.get(jid, {})
        nome = c.get('journal', f'?{jid}')
        L.append(f"  {nome:10s} {c.get('total_odoo',0):>12} {c.get('importados',0):>12} "
                 f"{c.get('nao_importados',0):>10} {c.get('cobertura_pct',0):>9.1f}%")

    # Total
    total_odoo = sum(c.get('total_odoo', 0) for c in cobertura.values())
    total_imp = sum(c.get('importados', 0) for c in cobertura.values())
    total_nao = sum(c.get('nao_importados', 0) for c in cobertura.values())
    pct_total = round(total_imp / total_odoo * 100, 1) if total_odoo > 0 else 0
    L.append(f"  {'TOTAL':10s} {total_odoo:>12} {total_imp:>12} {total_nao:>10} {pct_total:>9.1f}%")

    # --- Por status sistema ---
    L.append("")
    L.append("POR STATUS (SISTEMA)")
    L.append("-" * 50)
    for status, count in sorted(stats['por_status_sistema'].items()):
        L.append(f"  {status:30s} {count:>8}")

    L.append("")
    L.append("POR STATUS_MATCH (SISTEMA)")
    L.append("-" * 50)
    for status, count in sorted(stats['por_status_match_sistema'].items()):
        L.append(f"  {status:30s} {count:>8}")

    # --- Resumo de divergencias por severidade ---
    L.append("")
    L.append("=" * 80)
    L.append("DIVERGENCIAS — RESUMO")
    L.append("=" * 80)

    por_sev = relatorio['divergencias']['por_severidade']

    L.append("")
    L.append(f"  CRITICA:  {por_sev.get('CRITICA', 0):>8}")
    L.append(f"  ALTA:     {por_sev.get('ALTA', 0):>8}")
    L.append(f"  MEDIA:    {por_sev.get('MEDIA', 0):>8}")
    L.append(f"  INFO:     {por_sev.get('INFO', 0):>8}")
    total_div = sum(por_sev.values())
    L.append(f"  TOTAL:    {total_div:>8}")

    # --- Detalhamento por categoria ---
    L.append("")
    L.append("=" * 80)
    L.append("DIVERGENCIAS — DETALHAMENTO")
    L.append("=" * 80)

    categorias_ordem = [
        ('CONCILIADO_LOCAL_NAO_RECONCILIADO_ODOO', 'CRITICA',
         'Sistema diz CONCILIADO mas Odoo is_reconciled=False'),
        ('MOVE_LINE_NAO_RECONCILIADA', 'CRITICA',
         'CONCILIADO mas NENHUMA move line do move tem reconciled=True no Odoo'),
        ('PAYMENT_INEXISTENTE', 'CRITICA',
         'payment_id no sistema mas payment NAO existe no Odoo'),
        ('ORFAO_LOCAL', 'ALTA',
         'statement_line_id do sistema NAO encontrado no Odoo'),
        ('NAO_IMPORTADO', 'ALTA',
         'Statement line existe no Odoo mas NAO no sistema'),
        ('PAYMENT_NAO_POSTED', 'ALTA',
         'payment_id existe mas state != posted'),
        ('PARTIAL_RECONCILE_INEXISTENTE', 'ALTA',
         'partial_reconcile_id no sistema mas NAO existe no Odoo'),
        ('FULL_RECONCILE_INEXISTENTE', 'ALTA',
         'full_reconcile_id no sistema mas NAO existe no Odoo'),
        ('NAO_CONCILIADO_LOCAL_RECONCILIADO_ODOO', 'MEDIA',
         'Odoo reconciliou mas sistema ainda nao atualizou'),
        ('VALOR_DIVERGENTE', 'INFO',
         'Diferenca de valor > R$ 0.01 entre sistema e Odoo'),
    ]

    for cat, sev, desc in categorias_ordem:
        items = divergencias[cat]
        L.append("")
        L.append(f"[{sev}] {cat}: {len(items)}")
        L.append("-" * 70)
        L.append(f"  {desc}")

        if not items:
            L.append("  Nenhuma divergencia.")
            continue

        # Primeiros 30 detalhados
        max_detalhe = 30
        if cat == 'NAO_IMPORTADO':
            # Agrupar por journal
            por_j = defaultdict(list)
            for d in items:
                por_j[d.get('journal_name', '?')].append(d)
            for jname, jitems in sorted(por_j.items()):
                L.append(f"  {jname}: {len(jitems)} linhas")
                for d in jitems[:5]:
                    L.append(f"    line={d['statement_line_id']:>8} | "
                             f"valor={d.get('amount', 0):>12.2f} | "
                             f"data={d.get('date', '?')} | "
                             f"rec={d.get('is_reconciled')}")
                if len(jitems) > 5:
                    L.append(f"    ... e mais {len(jitems) - 5} (ver JSON)")

        elif cat in ('CONCILIADO_LOCAL_NAO_RECONCILIADO_ODOO', 'NAO_CONCILIADO_LOCAL_RECONCILIADO_ODOO'):
            for d in items[:max_detalhe]:
                L.append(f"  ID={d['extrato_item_id']:>6} | "
                         f"line={d['statement_line_id']:>8} | "
                         f"valor={d.get('valor_local', 0):>12.2f} | "
                         f"journal={d.get('journal_code', '?')} | "
                         f"data={d.get('data_transacao', '?')}")
            if len(items) > max_detalhe:
                L.append(f"  ... e mais {len(items) - max_detalhe} (ver JSON)")

        elif cat in ('PAYMENT_INEXISTENTE', 'PAYMENT_NAO_POSTED'):
            for d in items[:max_detalhe]:
                extra = f"state={d.get('payment_state', '?')}" if cat == 'PAYMENT_NAO_POSTED' else ''
                L.append(f"  ID={d['extrato_item_id']:>6} | "
                         f"line={d['statement_line_id']:>8} | "
                         f"payment={d['payment_id']:>8} | "
                         f"status={d.get('status_local', '?')} | "
                         f"{extra}")
            if len(items) > max_detalhe:
                L.append(f"  ... e mais {len(items) - max_detalhe} (ver JSON)")

        elif cat in ('PARTIAL_RECONCILE_INEXISTENTE', 'FULL_RECONCILE_INEXISTENTE'):
            id_field = 'partial_reconcile_id' if 'PARTIAL' in cat else 'full_reconcile_id'
            for d in items[:max_detalhe]:
                L.append(f"  ID={d['extrato_item_id']:>6} | "
                         f"line={d['statement_line_id']:>8} | "
                         f"{id_field}={d[id_field]:>8} | "
                         f"status={d.get('status_local', '?')}")
            if len(items) > max_detalhe:
                L.append(f"  ... e mais {len(items) - max_detalhe} (ver JSON)")

        elif cat == 'ORFAO_LOCAL':
            for d in items[:max_detalhe]:
                L.append(f"  ID={d['extrato_item_id']:>6} | "
                         f"line={d['statement_line_id']:>8} | "
                         f"valor={d.get('valor', 0):>12.2f} | "
                         f"status={d.get('status', '?')} | "
                         f"journal={d.get('journal_code', '?')}")
            if len(items) > max_detalhe:
                L.append(f"  ... e mais {len(items) - max_detalhe} (ver JSON)")

        elif cat == 'MOVE_LINE_NAO_RECONCILIADA':
            for d in items[:max_detalhe]:
                n_mls = len(d.get('move_lines', []))
                L.append(f"  ID={d['extrato_item_id']:>6} | "
                         f"line={d['statement_line_id']:>8} | "
                         f"move={d.get('move_id', '?'):>8} | "
                         f"mls={n_mls} | "
                         f"journal={d.get('journal_code', '?')}")
            if len(items) > max_detalhe:
                L.append(f"  ... e mais {len(items) - max_detalhe} (ver JSON)")

        elif cat == 'VALOR_DIVERGENTE':
            for d in items[:max_detalhe]:
                L.append(f"  ID={d['extrato_item_id']:>6} | "
                         f"line={d['statement_line_id']:>8} | "
                         f"local={d.get('valor_local', 0):>12.2f} | "
                         f"odoo={d.get('valor_odoo', 0):>12.2f} | "
                         f"diff={d.get('diferenca', 0):>10.2f}")
            if len(items) > max_detalhe:
                L.append(f"  ... e mais {len(items) - max_detalhe} (ver JSON)")

    # --- Verificacao de completude ---
    L.append("")
    L.append("=" * 80)
    L.append("VERIFICACAO DE COMPLETUDE")
    L.append("=" * 80)

    total_sistema = est['total_sistema_processado']
    total_odoo = est['total_odoo_lines']
    orfaos = len(divergencias['ORFAO_LOCAL'])
    nao_imp = len(divergencias['NAO_IMPORTADO'])

    # Sistema: concordantes + divergentes deve = total
    soma_sistema = est['total_concordante'] + est['total_divergente_unico']
    ok_sistema = soma_sistema == total_sistema
    L.append(f"  Sistema: concordantes({est['total_concordante']}) + divergentes({est['total_divergente_unico']}) "
             f"= {soma_sistema} {'== OK' if ok_sistema else '!= ERRO'} (total={total_sistema})")

    # Odoo: importados + nao_importados deve = total odoo
    sistema_com_match = total_sistema - orfaos
    soma_odoo = sistema_com_match + nao_imp
    ok_odoo = soma_odoo == total_odoo
    L.append(f"  Odoo: importados({sistema_com_match}) + nao_imp({nao_imp}) "
             f"= {soma_odoo} {'== OK' if ok_odoo else '!= ERRO'} (total odoo={total_odoo})")

    L.append("")
    L.append("=" * 80)
    L.append("FIM DO RELATORIO")
    L.append("=" * 80)

    resumo_text = "\n".join(L)
    with open(RESUMO_TXT, 'w') as f:
        f.write(resumo_text)
    print(f"\n  Resumo TXT: {RESUMO_TXT}")

    # Imprimir no terminal
    print("\n" + resumo_text)


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Auditoria 100%% Bidirecional: Extrato Sistema vs Odoo (v2)'
    )
    parser.add_argument('--fase-a', action='store_true',
                        help='Fase A: exportar dados do sistema (Render DB)')
    parser.add_argument('--fase-b', action='store_true',
                        help='Fase B: exportar dados do Odoo (4 sub-etapas)')
    parser.add_argument('--fase-c', action='store_true',
                        help='Fase C: comparar e gerar relatorio')
    parser.add_argument('--completo', action='store_true',
                        help='Executar fases A + B + C sequencialmente')
    args = parser.parse_args()

    if not (args.fase_a or args.fase_b or args.fase_c or args.completo):
        parser.print_help()
        print("\nNenhuma fase selecionada. Use --fase-a, --fase-b, --fase-c ou --completo")
        print("\nFluxo completo:")
        print("  1. --fase-a — exportar extrato_item do Render DB")
        print("  2. --fase-b — exportar Odoo (statement lines, payments, reconciles)")
        print("  3. --fase-c — comparar e gerar relatorio")
        print("  ou --completo para executar A + B + C")
        sys.exit(1)

    if args.fase_a or args.completo:
        fase_a()

    if args.fase_b or args.completo:
        fase_b()

    if args.fase_c or args.completo:
        fase_c()


if __name__ == '__main__':
    main()
