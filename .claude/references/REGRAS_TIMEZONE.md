# Timezone — Convencao Brasil Naive

**Ultima Atualizacao**: 12/02/2026

---

## Convencao

O sistema armazena TODOS os timestamps como **Brasil naive** (sem tzinfo).
`CURRENT_TIMESTAMP` / `NOW()` no banco ja retornam horario de Brasilia (`config.py` → `timezone=America/Sao_Paulo`).

---

## Proibido

```python
# NUNCA — para armazenamento
datetime.now()       # retorna hora do server (pode nao ser Brasil)
datetime.utcnow()    # deprecated Python 3.12+, retorna UTC
datetime.today()     # alias de datetime.now()
```

Hook `.claude/hooks/ban_datetime_now.py` **bloqueia** (exit 1) qualquer Write/Edit que introduza `datetime.now()` em `.py`.

---

## API — `app/utils/timezone.py`

| Funcao | Retorno | Quando Usar |
|--------|---------|-------------|
| `agora_utc_naive()` | Brasil naive (sem tzinfo) | Armazenamento, model defaults (`default=`, `onupdate=`) |
| `agora_brasil_naive()` | Alias de `agora_utc_naive()` | Idem (nome legado, 235+ usos) |
| `agora_utc()` | UTC aware | Queries Odoo `write_date` (Odoo armazena UTC) |
| `odoo_para_local(dt_str)` | Brasil naive | Converter datetime UTC do Odoo para Brasil |

```python
# Armazenamento e model defaults
from app.utils.timezone import agora_utc_naive
criado_em = agora_utc_naive()

# Queries Odoo write_date
from app.utils.timezone import agora_utc
write_date = agora_utc()

# Converter UTC do Odoo para Brasil
from app.utils.timezone import odoo_para_local
dt_brasil = odoo_para_local(odoo_datetime_str)
```

---

## Excecao: Medicao de Tempo

`datetime.now()` e **permitido** para medicao de duracao (nao vai pro banco):

```python
inicio = datetime.now()
# ... operacao ...
duracao = (datetime.now() - inicio).total_seconds()
```

O hook reconhece esses patterns automaticamente (variavel `inicio`, `start`, `t0`, etc.).

---

## Templates Jinja2

Dados ja estao em Brasil — formatar direto (sem conversao):

```jinja
{{ item.criado_em|formatar_data_segura }}          {# DD/MM/YYYY #}
{{ item.criado_em|formatar_data_hora_brasil }}      {# DD/MM/YYYY HH:MM #}
```

---

## Boundaries Odoo

| Direcao | Funcao | Motivo |
|---------|--------|--------|
| Odoo → Sistema | `odoo_para_local(dt_str)` | Odoo envia UTC, sistema armazena Brasil |
| Sistema → Odoo | `agora_utc()` | Odoo espera UTC em `write_date` |
