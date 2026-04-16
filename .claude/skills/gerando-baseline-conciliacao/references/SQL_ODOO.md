# SQL Odoo para baseline de conciliacao

Conexao: `app.odoo.utils.connection.get_odoo_connection()` → retorna objeto com metodos `execute_kw()` para XML-RPC.

Alternativa: conectar diretamente via psycopg2 ao banco Odoo (read-only) se configurado.

**Company**: FB (id=1) — Nacom Goya / Conservas Campo Belo.

**Journals monitorados**: SICOOB, GRAFENO, BRADESCO, AGIS GARANTIDA, VORTX GRAFENO.

---

## Query 1: Pendentes por Mes x Journal

```python
from app.odoo.utils.connection import get_odoo_connection

odoo = get_odoo_connection()
uid = odoo['uid']
models = odoo['models']
db = odoo['db']
password = odoo['password']

# Buscar journals monitorados primeiro
journals = models.execute_kw(db, uid, password,
    'account.journal', 'search_read',
    [[('name', 'in', ['SICOOB', 'GRAFENO', 'BRADESCO', 'AGIS GARANTIDA', 'VORTX GRAFENO']),
      ('company_id', '=', 1)]],
    {'fields': ['id', 'name']})
journal_ids = [j['id'] for j in journals]
journal_map = {j['id']: j['name'] for j in journals}

# Buscar linhas pendentes via read_group
results = models.execute_kw(db, uid, password,
    'account.bank.statement.line', 'read_group',
    [[('is_reconciled', '=', False),
      ('journal_id', 'in', journal_ids),
      ('company_id', '=', 1)],
     ['journal_id', 'date'],
     ['journal_id', 'date:month']],
    {'lazy': False})

# Agrupar em Python (read_group limita agregacoes com filter)
from collections import defaultdict
agg = defaultdict(lambda: {'linhas': 0, 'pgtos': 0, 'recebs': 0, 'vl_deb': 0.0, 'vl_cred': 0.0})

# Buscar todas as linhas (batch de 2000 se necessario)
offset = 0
batch_size = 2000
while True:
    linhas = models.execute_kw(db, uid, password,
        'account.bank.statement.line', 'search_read',
        [[('is_reconciled', '=', False),
          ('journal_id', 'in', journal_ids),
          ('company_id', '=', 1)]],
        {'fields': ['journal_id', 'date', 'amount'],
         'limit': batch_size, 'offset': offset})
    if not linhas:
        break
    for linha in linhas:
        mes = linha['date'][:7].replace('-', '/')  # YYYY-MM -> YYYY/MM
        mes = mes[5:] + '/' + mes[:4]  # MM/YYYY
        journal = journal_map[linha['journal_id'][0]]
        key = (mes, journal)
        agg[key]['linhas'] += 1
        if linha['amount'] < 0:
            agg[key]['pgtos'] += 1
            agg[key]['vl_deb'] += linha['amount']  # preserva sinal negativo
        elif linha['amount'] > 0:
            agg[key]['recebs'] += 1
            agg[key]['vl_cred'] += linha['amount']
    offset += batch_size
    if len(linhas) < batch_size:
        break
```

**Resultado esperado**: dict `{(mes, journal): {linhas, pgtos, recebs, vl_deb, vl_cred}}` para preencher aba 1.

---

## Query 2: Pendentes detalhadas (linha por linha)

```python
# Top N=500 por valor absoluto
linhas = models.execute_kw(db, uid, password,
    'account.bank.statement.line', 'search_read',
    [[('is_reconciled', '=', False),
      ('journal_id', 'in', journal_ids),
      ('company_id', '=', 1)]],
    {'fields': ['journal_id', 'date', 'payment_ref', 'partner_id', 'amount', 'payment_id'],
     'order': 'date desc'})

# Ordenar por valor absoluto, pegar top 500
linhas.sort(key=lambda x: abs(x['amount']), reverse=True)
linhas_top = linhas[:500]
```

**Campo `payment_ref`**: texto descritivo (ex: "TED Banco X Fornecedor Y").
**Campo `partner_id`**: `[id, nome]` ou `False` se NULL.
**Campo `payment_id`**: `[id, nome]` ou `False` — maioria das pendentes tem `False`.

---

## Query 3: Conciliacoes D-1 (uniao de 3 fontes)

**Fonte 1 — Odoo `account.bank.statement.line`**:

```python
from datetime import date, timedelta
ontem = (date.today() - timedelta(days=1)).isoformat()
inicio = f"{ontem} 00:00:00"
fim = f"{ontem} 23:59:59"

# Conciliacoes feitas em D-1
conciliacoes = models.execute_kw(db, uid, password,
    'account.bank.statement.line', 'search_read',
    [[('is_reconciled', '=', True),
      ('write_date', '>=', inicio),
      ('write_date', '<=', fim),
      ('journal_id', 'in', journal_ids),
      ('company_id', '=', 1)]],
    {'fields': ['write_uid', 'amount']})

# Resolver nome real do usuario via write_uid
user_ids = list(set(c['write_uid'][0] for c in conciliacoes if c['write_uid']))
users = models.execute_kw(db, uid, password,
    'res.users', 'read',
    [user_ids, ['id', 'name']])
user_map = {u['id']: u['name'] for u in users}

# Montar agregacao por usuario
from collections import defaultdict
per_user = defaultdict(lambda: {'linhas': 0, 'pgtos': 0, 'recebs': 0, 'vl_deb': 0.0, 'vl_cred': 0.0})
for c in conciliacoes:
    if not c['write_uid']:
        continue
    nome = user_map.get(c['write_uid'][0], f"USER_{c['write_uid'][0]}")
    per_user[nome]['linhas'] += 1
    if c['amount'] < 0:
        per_user[nome]['pgtos'] += 1
        per_user[nome]['vl_deb'] += c['amount']
    elif c['amount'] > 0:
        per_user[nome]['recebs'] += 1
        per_user[nome]['vl_cred'] += c['amount']
```

**CRITICO — armadilha documentada**: NUNCA usar `SYNC_ODOO_WRITE_DATE` como usuario. Se `write_uid=False` ou nome comeca com `SYNC_*`, ignorar OU mapear via resolucao adicional — nunca exibir ao usuario.

**Fonte 2 — Local `lancamento_comprovante`** (Postgres Render):

```sql
SELECT usuario, amount
FROM lancamento_comprovante
WHERE data_conciliacao = CURRENT_DATE - INTERVAL '1 day';
```

**Fonte 3 — Local `carvia_conciliacoes`**:

```sql
SELECT usuario, valor_total AS amount
FROM carvia_conciliacoes
WHERE data = CURRENT_DATE - INTERVAL '1 day';
```

**UNIR as 3 fontes** em Python antes de popular a aba 3.

---

## Query 4: Resumo (pivot da aba 1)

Nao requer query — deriva de Query 1 via pivot em Python:

```python
from collections import defaultdict
pivot = defaultdict(lambda: defaultdict(lambda: {'pgtos': 0, 'recebs': 0}))
for (mes, journal), dados in agg.items():
    pivot[mes][journal]['pgtos'] += dados['pgtos']
    pivot[mes][journal]['recebs'] += dados['recebs']

# Montar linhas ordenadas
for mes in sorted(pivot.keys()):
    total_mes_pgtos = sum(j['pgtos'] for j in pivot[mes].values())
    total_mes_recebs = sum(j['recebs'] for j in pivot[mes].values())
    # Subtotal do mes (verde claro)
    # Sub-itens por journal (ordenado alfabetico)
```

---

## Conexao alternativa: psycopg2 direto (read-only)

Se XML-RPC estiver lento ou indisponivel, conectar direto ao banco Odoo read-only. FONTE das credenciais: variavel de ambiente `ODOO_READ_REPLICA_URL` se existir.

```python
import psycopg2
import os

conn_str = os.getenv('ODOO_READ_REPLICA_URL')
if conn_str:
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    cur.execute("""
        SELECT
          TO_CHAR(date, 'MM/YYYY') AS mes,
          aj.name AS journal,
          COUNT(*) AS linhas,
          COUNT(*) FILTER (WHERE amount < 0) AS pgtos,
          COALESCE(SUM(amount) FILTER (WHERE amount < 0), 0) AS vl_deb,
          COUNT(*) FILTER (WHERE amount > 0) AS recebs,
          COALESCE(SUM(amount) FILTER (WHERE amount > 0), 0) AS vl_cred
        FROM account_bank_statement_line abl
        JOIN account_journal aj ON aj.id = abl.journal_id
        WHERE abl.is_reconciled = FALSE
          AND aj.name IN ('SICOOB', 'GRAFENO', 'BRADESCO', 'AGIS GARANTIDA', 'VORTX GRAFENO')
          AND abl.company_id = 1
        GROUP BY 1, 2
        ORDER BY 1, 2;
    """)
    rows = cur.fetchall()
    conn.close()
```

Esse SQL direto e mais rapido que o loop Python via XML-RPC (10x+).

---

## Ordem de execucao no script

```python
# gerar_baseline.py pseudo-codigo
1. agg_aba1 = query_1_mes_x_journal()
2. linhas_aba2 = query_2_pendentes_detalhadas()
3. conciliacoes_aba3 = query_3_dia_anterior_uniao_3_fontes()
4. pivot_aba4 = pivot_from(agg_aba1)  # sem query nova
5. excel = montar_excel(agg_aba1, linhas_aba2, conciliacoes_aba3, pivot_aba4)
6. url = salvar_e_retornar_url(excel)
```
