---
name: rastreando-odoo
description: |
  Rastreia fluxos documentais completos no Odoo a partir de qualquer ponto de entrada.

  USAR QUANDO:
  - Rastrear NF de compra/venda: "rastreie NF 12345", "fluxo da nota 54321"
  - Rastrear pedido de compra: "rastreie PO00789", "fluxo do pedido de compra"
  - Rastrear pedido de venda: "rastreie VCD123", "fluxo do VFB456"
  - Rastrear por parceiro: "documentos do Atacadao", "fluxo do fornecedor Vale Sul"
  - Rastrear por CNPJ: "rastreie 18467441000123"
  - Rastrear por chave NF-e: "rastreie 3525..."
  - Ver titulos e conciliacoes: "pagamentos da NF 12345", "titulos do PO00789"
  - Verificar devolucoes: "devolucao da NF 54321", "nota de credito"

  NAO USAR QUANDO:
  - Descobrir campos de modelo desconhecido → usar descobrindo-odoo-estrutura
  - Criar lancamentos fiscais → usar integracao-odoo
  - Apenas listar registros sem rastrear fluxo
---

# Rastreando Odoo

Rastreia fluxo completo de documentos, retornando JSON com todos os documentos vinculados.

## Fluxos Suportados

| Fluxo | Caminho |
|-------|---------|
| **Compra** | DFE → Requisicao → PO → Fatura → Titulos → Conciliacao |
| **Venda** | SO (VCD/VFB/VSC) → Picking → Fatura → Titulos → Conciliacao |
| **Devolucao** | DFE (finnfe=4) → Nota Credito → NF Original → Pedido Original |

## Workflow

1. **Normalizar entrada** → Transforma texto humano em ID Odoo
2. **Detectar tipo** → Identifica se e compra, venda ou devolucao
3. **Rastrear fluxo** → Navega pelos relacionamentos
4. **Retornar JSON** → Estrutura completa com todos os documentos

## Scripts

### [normalizar.py](scripts/normalizar.py)

Transforma mencoes humanas em identificadores Odoo.

```bash
source .venv/bin/activate

# Por nome de parceiro
python .claude/skills/rastreando-odoo/scripts/normalizar.py "Atacadao" --json

# Por CNPJ
python .claude/skills/rastreando-odoo/scripts/normalizar.py "18467441" --json

# Por numero de NF
python .claude/skills/rastreando-odoo/scripts/normalizar.py "NF 12345" --json

# Por PO
python .claude/skills/rastreando-odoo/scripts/normalizar.py "PO00789" --json

# Por SO (prefixos de filial: VCD, VFB, VSC)
python .claude/skills/rastreando-odoo/scripts/normalizar.py "VCD123" --json

# Apenas detectar tipo (sem buscar no Odoo)
python .claude/skills/rastreando-odoo/scripts/normalizar.py "VCD123" --detectar
```

**Tipos detectados:**
| Padrao | Tipo | Exemplo |
|--------|------|---------|
| 44 digitos | `chave_nfe` | 35251218467441000163... |
| PO + numeros | `po` | PO00123 |
| VCD/VFB/VSC + numeros | `so` | VCD789 |
| NF/NFe + numeros | `nf_numero` | NF 12345 |
| numero/serie | `nf_serie` | 12345/1 |
| 8-14 digitos | `cnpj` | 18467441000123 |
| Texto livre | `parceiro` | Atacadao |

### [rastrear.py](scripts/rastrear.py)

Rastreia fluxo completo a partir de qualquer entrada.

```bash
source .venv/bin/activate

# Por chave NF-e
python .claude/skills/rastreando-odoo/scripts/rastrear.py "35251218467441..." --json

# Por numero de NF
python .claude/skills/rastreando-odoo/scripts/rastrear.py "NF 12345" --json

# Por PO
python .claude/skills/rastreando-odoo/scripts/rastrear.py "PO00789" --json

# Por SO
python .claude/skills/rastreando-odoo/scripts/rastrear.py "VCD123" --json

# Por parceiro (lista documentos recentes)
python .claude/skills/rastreando-odoo/scripts/rastrear.py "Atacadao" --json

# Forcar tipo de fluxo
python .claude/skills/rastreando-odoo/scripts/rastrear.py "12345" --fluxo compra --json
```

## Estrutura do JSON

### Fluxo de Compra

```json
{
  "entrada": "NF 12345",
  "sucesso": true,
  "fluxo": {
    "tipo": "compra",
    "dfe": { "id": 1234, "protnfe_infnfe_chnfe": "3525...", "nfe_infnfe_ide_nnf": "12345" },
    "requisicao": { "id": 100, "name": "REQ00100", "state": "done" },
    "pedido_compra": { "id": 789, "name": "PO00789", "amount_total": 10000.00 },
    "fatura": { "id": 456, "name": "BILL/2025/0001", "payment_state": "paid" },
    "titulos": [{ "date_maturity": "2025-01-15", "debit": 10000.00, "reconciled": true }],
    "conciliacoes": [...]
  }
}
```

### Fluxo de Venda

```json
{
  "fluxo": {
    "tipo": "venda",
    "pedido_venda": { "id": 500, "name": "VCD123", "state": "sale" },
    "pickings": [{ "name": "WH/OUT/00600", "state": "done" }],
    "faturas": [...],
    "titulos": [...],
    "conciliacoes": [...]
  }
}
```

## References

Para detalhes dos relacionamentos entre tabelas Odoo, consultar [relacionamentos.md](references/relacionamentos.md).

## Tipos de Documento

| DFE (finnfe) | Descricao | Fatura (move_type) | Descricao |
|--------------|-----------|-------------------|-----------|
| 1 | Normal | out_invoice | Fatura Venda |
| 2 | Complementar | out_refund | Credito Venda |
| 3 | Ajuste | in_invoice | Fatura Compra |
| 4 | Devolucao | in_refund | Credito Compra |

## Prefixos de Pedido de Venda

| Prefixo | Filial |
|---------|--------|
| VCD | Centro de Distribuicao |
| VFB | Filial FB |
| VSC | Filial SC |

## Skills Relacionadas

| Skill | Quando usar |
|-------|-------------|
| [descobrindo-odoo-estrutura](../descobrindo-odoo-estrutura/SKILL.md) | Descobrir campos de modelos nao mapeados |
| [integracao-odoo](../integracao-odoo/SKILL.md) | Criar novos lancamentos fiscais (CTe, despesas) |
