# Scripts — Rastreando Odoo (Detalhes)

Referencia detalhada de parametros, retornos e modos de operacao.

---

## Ambiente Virtual

Sempre ativar antes de executar:
```bash
source .venv/bin/activate
```

---

## 1. normalizar.py

**Proposito:** Transforma mencoes humanas em identificadores Odoo. Detecta tipo de entrada.

```bash
source .venv/bin/activate && \
python .claude/skills/rastreando-odoo/scripts/normalizar.py [entrada] [opcoes]
```

| Parametro | Obrig | Descricao | Exemplo |
|-----------|-------|-----------|---------|
| `entrada` | Sim | Texto a normalizar (NF, PO, SO, parceiro, CNPJ, chave NF-e) | `"NF 12345"`, `"PO00789"`, `"Atacadao"` |
| `--json` | Nao | Saida em formato JSON | flag |
| `--detectar` | Nao | Apenas detectar tipo (sem buscar no Odoo) | flag |

**Tipos detectados:**
- `NF` → numero de nota fiscal
- `PO` → pedido de compra (formatos: PO00123, C2513147)
- `SO` → pedido de venda (prefixos: VCD, VFB, VSC)
- `CHAVE` → chave NF-e (44 digitos)
- `CNPJ` → CNPJ parcial ou completo
- `PARCEIRO` → nome de parceiro/fornecedor/cliente

---

## 2. rastrear.py

**Proposito:** Rastreia fluxo completo a partir de qualquer entrada. Script principal.

```bash
source .venv/bin/activate && \
python .claude/skills/rastreando-odoo/scripts/rastrear.py [entrada] [opcoes]
```

| Parametro | Obrig | Descricao | Exemplo |
|-----------|-------|-----------|---------|
| `entrada` | Sim | Qualquer identificador (NF, PO, SO, parceiro, CNPJ, chave) | `"NF 12345"`, `"VCD123"` |
| `--json` | Nao | Saida em formato JSON | flag |
| `--fluxo` | Nao | Forcar tipo de fluxo (compra, venda, devolucao) | `--fluxo compra` |

**Retorno JSON (compra):**
```json
{
  "entrada": "NF 12345",
  "sucesso": true,
  "fluxo": {
    "tipo": "compra",
    "dfe": { "id": 1234, "nfe_infnfe_ide_nnf": "12345" },
    "pedido_compra": { "id": 789, "name": "PO00789", "amount_total": 10000.00 },
    "fatura": { "id": 456, "name": "BILL/2025/0001", "payment_state": "paid" },
    "titulos": [{ "date_maturity": "2025-01-15", "debit": 10000.00, "reconciled": true }]
  }
}
```

**Retorno JSON (venda):**
```json
{
  "fluxo": {
    "tipo": "venda",
    "pedido_venda": { "id": 500, "name": "VCD123", "state": "sale" },
    "pickings": [{ "name": "WH/OUT/00600", "state": "done" }],
    "faturas": [...],
    "titulos": [...]
  }
}
```

---

## 3. auditoria_faturas_compra.py

**Proposito:** Auditoria completa de faturas de compra com titulos, pagamentos e conciliacoes.

```bash
source .venv/bin/activate && \
python .claude/skills/rastreando-odoo/scripts/auditoria_faturas_compra.py [opcoes]
```

| Parametro | Obrig | Descricao | Exemplo |
|-----------|-------|-----------|---------|
| `--mes` | * | Mes da auditoria (1-12) | `--mes 11` |
| `--ano` | * | Ano da auditoria | `--ano 2025` |
| `--all` | * | Todo o periodo disponivel | flag |
| `--json` | Nao | Saida em formato JSON | flag |
| `--excel` | Nao | Formato tabular (para exportar via exportando-arquivos) | flag |

\* Usar `--mes + --ano` OU `--all`

**Dados extraidos:** fatura, fornecedor, CNPJ, parcelas, vencimentos, pagamentos, conciliacao bancaria, notas de credito/estornos.

---

## 4. auditoria_extrato_bancario.py

**Proposito:** Auditoria de extrato bancario com status de conciliacao.

```bash
source .venv/bin/activate && \
python .claude/skills/rastreando-odoo/scripts/auditoria_extrato_bancario.py [opcoes]
```

| Parametro | Obrig | Descricao | Exemplo |
|-----------|-------|-----------|---------|
| `--inicio` | Sim | Data inicio (YYYY-MM-DD) | `--inicio 2024-07-01` |
| `--fim` | Sim | Data fim (YYYY-MM-DD) | `--fim 2025-12-31` |
| `--json` | Nao | Saida em formato JSON | flag |
| `--excel` | Nao | Formato tabular | flag |

**Dados extraidos:** data, referencia, valor, parceiro, conta bancaria, status conciliacao.

---

## 5. mapeamento_vinculos_completo.py

**Proposito:** 5 visoes cruzadas para identificar registros "soltos" (sem vinculo).

```bash
source .venv/bin/activate && \
python .claude/skills/rastreando-odoo/scripts/mapeamento_vinculos_completo.py [opcoes]
```

| Parametro | Obrig | Descricao | Exemplo |
|-----------|-------|-----------|---------|
| `--inicio` | Sim | Data inicio (YYYY-MM-DD) | `--inicio 2024-07-01` |
| `--fim` | Sim | Data fim (YYYY-MM-DD) | `--fim 2025-12-31` |
| `--pagamentos` | Nao | Apenas mapeamento de pagamentos (extratos < 0) | flag |
| `--json` | Nao | Saida JSON completo | flag |
| `--excel` | Nao | Formato tabular | flag |

**Visoes extraidas:**
- EXTRATOS: titulo_ids, fatura_ids, nc_ids, payment_ids, CNPJ, conta_bancaria
- TITULOS: extrato_ids, fatura_id, nc_ids, payment_ids, parcela, CNPJ
- FATURAS: titulo_ids, extrato_ids, nc_ids, chave_nfe, CNPJ
- NOTAS_CREDITO: fatura_origem_id, titulo_ids, extrato_ids, CNPJ
- PAGAMENTOS: extrato_ids, titulo_ids, CNPJ

---

## 6. vincular_extrato_fatura_excel.py

**Proposito:** Processa planilha Excel para vincular extratos com faturas automaticamente.

```bash
source .venv/bin/activate && \
python .claude/skills/rastreando-odoo/scripts/vincular_extrato_fatura_excel.py [opcoes]
```

| Parametro | Obrig | Descricao | Exemplo |
|-----------|-------|-----------|---------|
| `-a` | Sim | Caminho da planilha Excel | `-a planilha.xlsx` |
| `--dry-run` | Nao | Simular sem executar | flag |
| `--otimizado` | Nao | Modo otimizado (3-4x mais rapido) | flag |
| `-o` | Nao | Offset (pular N linhas) | `-o 0` |
| `-b` | Nao | Batch size (default: todas) | `-b 500` |

**Colunas esperadas na planilha:**

| Coluna | Indice | Conteudo |
|--------|--------|----------|
| A | 0 | ID do extrato |
| H | 7 | FATURA (name) |
| I | 8 | CNPJ |
| K | 10 | FATURA.1 (ID) |
| L | 11 | PARCELA |
| M | 12 | VALOR |
| T | 19 | Movimento |

**Processo:** Cria account.payment → posta → reconcilia com titulo e extrato.

---

## Exemplos de Uso

### Cenario 1: Rastrear NF de compra
```
Pergunta: "rastreie NF 12345"
Comando: rastrear.py "NF 12345" --json
```

### Cenario 2: Rastrear pedido de venda
```
Pergunta: "fluxo do VCD123 no Odoo"
Comando: rastrear.py "VCD123" --json
```

### Cenario 3: Auditoria faturas novembro
```
Pergunta: "auditoria de faturas de compra de novembro"
Comando: auditoria_faturas_compra.py --mes 11 --ano 2025 --json
```

### Cenario 4: Extratos sem vinculo
```
Pergunta: "quais extratos estao sem vinculo?"
Comando: mapeamento_vinculos_completo.py --inicio 2024-07-01 --fim 2025-12-31 --json
```

### Cenario 5: Vincular via planilha (dry-run)
```
Pergunta: "processa essa planilha de vinculacao"
Comando: vincular_extrato_fatura_excel.py -a planilha.xlsx --dry-run
```
