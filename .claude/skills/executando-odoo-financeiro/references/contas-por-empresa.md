# Contas por Empresa no Odoo

Mapeamento de IDs de contas contabeis por empresa.

## Empresas (res.company)

| ID | Nome | Codigo |
|----|------|--------|
| 1 | NACOM GOYA - FB | FB |
| 3 | NACOM GOYA - SC | SC |
| 4 | NACOM GOYA - CD | CD |
| 5 | LA FAMIGLIA - LF | LF |

## Contas de Juros de Recebimento

**Conta**: `3702010003 JUROS DE RECEBIMENTOS EM ATRASO`

| Company ID | Company Nome | Account ID |
|------------|--------------|------------|
| 1 | NACOM GOYA - FB | 22778 |
| 3 | NACOM GOYA - SC | 24061 |
| 4 | NACOM GOYA - CD | 25345 |
| 5 | LA FAMIGLIA - LF | 26629 |

```python
CONTA_JUROS_RECEBIMENTOS_POR_COMPANY = {
    1: 22778,  # NACOM GOYA - FB
    3: 24061,  # NACOM GOYA - SC
    4: 25345,  # NACOM GOYA - CD
    5: 26629,  # LA FAMIGLIA - LF
}
```

## Contas Comuns (Todas as Empresas)

### Contas de Ativo

| ID | Codigo | Nome | Uso |
|----|--------|------|-----|
| 26868 | 1110100004 | PAGAMENTOS/RECEBIMENTOS PENDENTES | Contrapartida do payment |
| 22199 | 1110100003 | TRANSITORIA DE VALORES | Contrapartida do extrato |
| 26706 | 1110200029 | BANCO GRAFENO 08140378-4 | Conta bancaria |

### Contas de Cliente

| ID | Codigo | Nome | Uso |
|----|--------|------|-----|
| 24801 | 1120100001 | CLIENTES NACIONAIS | Receivable (titulo a receber) |

## Journals Bancarios

### Journal de Recebimento (Testado)

| ID | Codigo | Nome | Tipo | Banco CNAB |
|----|--------|------|------|------------|
| 883 | GRAFENO | Banco Grafeno | bank | 274 (BMP Money Plus) |

> **FLUXO TESTADO**: Retorno CNAB 274 (BMP Money Plus / Grafeno) em 22/01/2026

### Mapeamento CNAB → Journal

O sistema identifica o journal automaticamente baseado no codigo do banco no arquivo CNAB.

```python
# app/financeiro/services/baixa_titulos_service.py
CNAB_BANCO_PARA_JOURNAL = {
    '274': {  # BMP Money Plus / Banco Grafeno
        'journal_id': 883,
        'journal_code': 'GRAFENO',
        'journal_name': 'Banco Grafeno',
    },
    # Adicionar novos bancos aqui conforme necessario
}

# Fallback quando banco nao mapeado
JOURNAL_GRAFENO_ID = 883  # Padrao GRAFENO
```

### Como Adicionar Novo Banco

1. **Descobrir journal_id no Odoo**:
```python
journals = odoo.search_read(
    'account.journal',
    [['type', '=', 'bank']],
    ['id', 'code', 'name', 'company_id']
)
```

2. **Adicionar em CNAB_BANCO_PARA_JOURNAL** (baixa_titulos_service.py):
```python
'XXX': {  # Codigo do banco no CNAB (posicao 77-79 do header)
    'journal_id': YYY,
    'journal_code': 'CODIGO',
    'journal_name': 'Nome do Banco',
},
```

3. **Testar com arquivo CNAB do novo banco**

## Como Descobrir Novos IDs

### Via Codigo Python

```python
from app.odoo.utils.connection import get_odoo_connection

odoo = get_odoo_connection()

# Buscar conta por codigo
contas = odoo.search_read(
    'account.account',
    [
        ['code', '=', '3702010003'],
        ['company_id', '=', company_id],
    ],
    ['id', 'code', 'name', 'company_id']
)

# Buscar journal por codigo
journals = odoo.search_read(
    'account.journal',
    [['code', '=', 'GRAFENO']],
    ['id', 'code', 'name', 'type', 'company_id']
)
```

### Via Skill descobrindo-odoo-estrutura

```bash
# Ver campos do modelo account.account
source .venv/bin/activate
python .claude/skills/descobrindo-odoo-estrutura/scripts/listar_campos.py account.account
```

## Notas Importantes

1. **Contas sao por empresa**: Mesmo codigo de conta tem IDs diferentes em empresas diferentes.

2. **PENDENTES e TRANSITORIA**: Estas contas sao usadas para conciliacao bancaria e tem o mesmo ID em todas as empresas (contas multi-company).

3. **Journal GRAFENO**: Usado para recebimentos via banco Grafeno, compartilhado entre empresas.

4. **Conta de Juros**: SEMPRE verificar a empresa do titulo antes de usar a conta de juros.
