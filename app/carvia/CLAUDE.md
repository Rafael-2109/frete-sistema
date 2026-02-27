# CarVia — Guia de Desenvolvimento

**20 arquivos** | **~4.5K LOC** | **20 templates** | **Atualizado**: 27/02/2026

Gestao de frete subcontratado: importar NF PDFs/XMLs + CTe XMLs, matchear NF-CTe,
subcontratar transportadoras com cotacao via tabelas existentes, gerar faturas cliente e transportadora.

> Campos de tabelas: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`

---

## Estrutura de Telas (5 documentos + 1 importacao)

| # | Documento | Entidade | URL | Tela |
|---|-----------|----------|-----|------|
| 1 | **NF Venda** | `CarviaNf` | `/carvia/nfs` | Lista + Detalhe (com itens de produto) |
| 2 | **CTe CarVia** | `CarviaOperacao` | `/carvia/operacoes` | Lista + Detalhe + Criar/Editar |
| 3 | **CTe Subcontrato** | `CarviaSubcontrato` | `/carvia/subcontratos` | Lista + Detalhe |
| 4 | **Fatura CarVia** | `CarviaFaturaCliente` | `/carvia/faturas-cliente` | Lista + Nova + Detalhe |
| 5 | **Fatura Subcontrato** | `CarviaFaturaTransportadora` | `/carvia/faturas-transportadora` | Lista + Nova + Detalhe |
| 6 | **Importacao** | `ImportacaoService` | `/carvia/importar` | Upload + Review + Confirmar |

### Cross-links entre documentos

```
NF Venda ──────────── CTe CarVia ──────────── Fatura CarVia
    (via junction)    │    (via fatura_cliente_id)
                      │
                CTe Subcontrato ────────── Fatura Subcontrato
               (via operacao_id)    (via fatura_transportadora_id)
```

---

## Estrutura de Arquivos

```
app/carvia/
  ├── routes/          # 7 sub-rotas (dashboard, importacao, nf, operacao, subcontrato, fatura, api)
  ├── services/        # 6 services (parsers, matching, importacao, cotacao)
  ├── models.py        # 7 models (NF, NfItem, Operacao, Junction, Subcontrato, 2 Faturas)
  └── forms.py         # 4 forms WTForms

app/templates/carvia/
  ├── dashboard.html
  ├── importar.html, importar_resultado.html
  ├── nfs/             # listar.html, detalhe.html
  ├── listar_operacoes.html, detalhe_operacao.html, criar_manual.html, etc.
  ├── subcontratos/    # listar.html, detalhe.html
  ├── faturas_cliente/  # listar.html, nova.html, detalhe.html
  └── faturas_transportadora/  # listar.html, nova.html, detalhe.html
```

---

## Regras Criticas

### R1: Modulo Isolado — SEM dependencia de Embarque/Frete
CarVia e um subsistema INDEPENDENTE. NAO importar de `app/fretes/`, `app/carteira/`, `app/financeiro/`.
Dominio DIFERENTE: frete inbound (CarVia subcontrata) vs frete outbound (Nacom embarca).
Excecoes permitidas: `app/transportadoras/models.py`, `app/tabelas/models.py`, `app/odoo/utils/cte_xml_parser.py`.

### R2: Lazy Imports nos Routes e Services
Imports de services e models de outros modulos sao LAZY (dentro de funcoes).
NAO mover para module-level — circular imports e startup overhead.
```python
# CORRETO — dentro da funcao
def api_calcular_cotacao():
    from app.carvia.services.cotacao_service import CotacaoService
```

### R3: peso_utilizado = max(bruto, cubado) — SEMPRE recalcular
Apos alterar `peso_bruto` ou `peso_cubado`, OBRIGATORIO chamar `operacao.calcular_peso_utilizado()`.
Cotacao usa `peso_utilizado` — valor stale = cotacao errada.

### R4: Fluxo de Status e Irreversivel (exceto cancelamento)
```
CTe CarVia: RASCUNHO → COTADO → CONFIRMADO → FATURADO    [CANCELADO de qualquer estado exceto FATURADO]
CTe Subcontrato: PENDENTE → COTADO → CONFIRMADO → FATURADO → CONFERIDO  [CANCELADO exceto FATURADO]
```
NUNCA mover status para tras (ex: CONFIRMADO → COTADO). Cancelar e criar novo.

### R5: Fatura vincula por status CONFIRMADO + fatura_id IS NULL
Faturas CarVia selecionam operacoes `status=CONFIRMADO, fatura_cliente_id IS NULL`.
Faturas Subcontrato selecionam subcontratos `status=CONFIRMADO, fatura_transportadora_id IS NULL`.
Ao vincular, status muda para FATURADO. NUNCA desvincular apos faturamento.

### R6: Classificacao de CTe por CNPJ emitente
Na importacao, CTes sao classificados automaticamente:
- CNPJ emitente == `CARVIA_CNPJ` (env var) → **CTe CarVia** (CarviaOperacao)
- CNPJ emitente != `CARVIA_CNPJ` → **CTe Subcontrato** (CarviaSubcontrato)
Se `CARVIA_CNPJ` nao configurado, todos CTes sao tratados como CarVia (compatibilidade).

### R7: numero_sequencial_transportadora — auto-increment logico
Cada subcontrato recebe numero sequencial por transportadora.
Gerado via `MAX(numero_sequencial_transportadora) + 1` filtrado por `transportadora_id`.
Unique index parcial: `(transportadora_id, numero_sequencial_transportadora) WHERE NOT NULL`.

---

## Modelos

> Campos: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`

| Modelo | Tabela | Gotchas |
|--------|--------|---------|
| CarviaNf | `carvia_nfs` | `chave_acesso_nf` UNIQUE mas nullable (manual). `tipo_fonte`: PDF_DANFE, XML_NFE, MANUAL |
| CarviaNfItem | `carvia_nf_itens` | Itens de produto da NF. FK `nf_id`. Cascade delete-orphan |
| CarviaOperacao | `carvia_operacoes` | `cte_chave_acesso` UNIQUE nullable. `peso_utilizado` e CALCULADO (R3). FK `fatura_cliente_id` |
| CarviaOperacaoNf | `carvia_operacao_nfs` | Junction N:N com UNIQUE(operacao_id, nf_id) |
| CarviaSubcontrato | `carvia_subcontratos` | `valor_final` e @property (valor_acertado ou valor_cotado). FK `transportadora_id` e `tabela_frete_id`. `numero_sequencial_transportadora` (R7) |
| CarviaFaturaCliente | `carvia_faturas_cliente` | Status: PENDENTE, EMITIDA, PAGA, CANCELADA |
| CarviaFaturaTransportadora | `carvia_faturas_transportadora` | `status_conferencia` (nao `status`). `conferido_por`/`conferido_em` preenchidos na conferencia |

---

## Importacao — Fluxo de Classificacao

```
Upload (NF-e XML, CTe XML, DANFE PDF)
    │
    ├── NF-e XML / PDF DANFE → CarviaNf + CarviaNfItem
    │
    └── CTe XML → Classificar por CNPJ emitente (R6)
        ├── CNPJ == CARVIA_CNPJ → CarviaOperacao (CTe CarVia)
        │   └── Vincular NFs via junction (matching por chave de acesso)
        └── CNPJ != CARVIA_CNPJ → CarviaSubcontrato (CTe Subcontrato)
            └── Vincular a CarviaOperacao via NFs compartilhadas
                Se nao encontrar operacao → erro/warning
```

**Env var necessaria**: `CARVIA_CNPJ` (apenas digitos, ex: `12345678000199`)

---

## Parsers — Ordem de Confiabilidade

| Parser | Confiabilidade | Notas |
|--------|---------------|-------|
| `nfe_xml_parser.py` | Alta | Namespace-agnostic. Fonte de verdade para NF-e. Extrai itens de produto |
| `cte_xml_parser_carvia.py` | Alta | Herda CTeXMLParser. `get_nfs_referenciadas()` para matching. `get_emitente()` para classificacao |
| `danfe_pdf_parser.py` | Media | Regex-based com pdfplumber+pypdf fallback. Campo `confianca` (0.0-1.0) |

---

## Matching — Algoritmo de 3 Niveis

1. **CHAVE** — Match exato por `chave_acesso_nf` 44 digitos (alta confianca)
2. **CNPJ_NUMERO** — Fallback por `(cnpj_emitente, numero_nf)` (media confianca)
3. **NAO_ENCONTRADA** — NF referenciada no CTe nao importada

---

## Cotacao — Reutiliza Infraestrutura Existente

`CotacaoService.cotar_subcontrato()` usa `CalculadoraFrete.calcular_frete_unificado()`.
Busca `TabelaFrete` por `transportadora_id + uf_destino + ativo=True`.
Testa TODAS as tabelas e retorna menor valor.

---

## Interdependencias

| Importa de | O que | Cuidado |
|-----------|-------|---------|
| `app/transportadoras/models.py` | `Transportadora` | Campo `razao_social` (NAO `nome`), `cnpj`, `freteiro`, `ativo` |
| `app/tabelas/models.py` | `TabelaFrete` | FK de subcontratos. Filtro por `uf_destino + ativo` |
| `app/odoo/utils/cte_xml_parser.py` | `CTeXMLParser` | Classe pai de CTeXMLParserCarvia |
| `app/utils/calculadora_frete.py` | `CalculadoraFrete` | Calculo unificado de frete |
| `app/utils/timezone.py` | `agora_utc_naive` | Todos os models |

| Exporta para | O que | Cuidado |
|-------------|-------|---------|
| `app/__init__.py` | `init_app()` | Registro do blueprint |
| NINGUEM | — | Modulo isolado, sem dependentes externos |

---

## Permissao

Toggle `sistema_carvia` no model `Usuario`. Decorator `@require_carvia()` em `app/utils/auth_decorators.py`.
Menu condicional em `base.html`: `{% if current_user.sistema_carvia %}`.

---

## Migrations

- `scripts/migrations/criar_tabelas_carvia.py` + `.sql` — 6 tabelas base, 18 indices
- `scripts/migrations/adicionar_sistema_carvia_usuarios.py` + `.sql` — Campo no Usuario
- `scripts/migrations/adicionar_seq_subcontrato.py` + `.sql` — `numero_sequencial_transportadora` + unique index parcial + backfill
