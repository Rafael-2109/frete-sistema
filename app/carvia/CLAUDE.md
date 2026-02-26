# CarVia — Guia de Desenvolvimento

**16 arquivos** | **3.3K LOC** | **16 templates** | **Atualizado**: 26/02/2026

Gestao de frete subcontratado: importar NF PDFs/XMLs + CTe XMLs, matchear NF-CTe,
subcontratar transportadoras com cotacao via tabelas existentes, gerar faturas cliente e transportadora.

> Campos de tabelas: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`

---

## Estrutura

```
app/carvia/
  ├── routes/          # 5 sub-rotas (dashboard, importacao, operacao, fatura, api)
  ├── services/        # 6 services (parsers, matching, importacao, cotacao)
  ├── models.py        # 6 models (NF, Operacao, Junction, Subcontrato, 2 Faturas)
  └── forms.py         # 4 forms WTForms

app/templates/carvia/  # 16 templates (dashboard, operacoes, faturas, subcontrato)
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
Operacao: RASCUNHO → COTADO → CONFIRMADO → FATURADO    [CANCELADO de qualquer estado exceto FATURADO]
Subcontrato: PENDENTE → COTADO → CONFIRMADO → FATURADO → CONFERIDO  [CANCELADO exceto FATURADO]
```
NUNCA mover status para tras (ex: CONFIRMADO → COTADO). Cancelar e criar novo.

### R5: Fatura vincula por status CONFIRMADO + fatura_id IS NULL
Faturas cliente selecionam operacoes `status=CONFIRMADO, fatura_cliente_id IS NULL`.
Faturas transportadora selecionam subcontratos `status=CONFIRMADO, fatura_transportadora_id IS NULL`.
Ao vincular, status muda para FATURADO. NUNCA desvincular apos faturamento.

---

## Modelos

> Campos: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`

| Modelo | Tabela | Gotchas |
|--------|--------|---------|
| CarviaNf | `carvia_nfs` | `chave_acesso_nf` UNIQUE mas nullable (manual). `tipo_fonte`: PDF_DANFE, XML_NFE, MANUAL |
| CarviaOperacao | `carvia_operacoes` | `cte_chave_acesso` UNIQUE nullable. `peso_utilizado` e CALCULADO (R3). FK `fatura_cliente_id` |
| CarviaOperacaoNf | `carvia_operacao_nfs` | Junction N:N com UNIQUE(operacao_id, nf_id) |
| CarviaSubcontrato | `carvia_subcontratos` | `valor_final` e @property (valor_acertado ou valor_cotado). FK `transportadora_id` e `tabela_frete_id` |
| CarviaFaturaCliente | `carvia_faturas_cliente` | Status: PENDENTE, EMITIDA, PAGA, CANCELADA |
| CarviaFaturaTransportadora | `carvia_faturas_transportadora` | `status_conferencia` (nao `status`). `conferido_por`/`conferido_em` preenchidos na conferencia |

---

## Parsers — Ordem de Confiabilidade

| Parser | Confiabilidade | Notas |
|--------|---------------|-------|
| `nfe_xml_parser.py` | Alta | Namespace-agnostic. Fonte de verdade para NF-e |
| `cte_xml_parser_carvia.py` | Alta | Herda CTeXMLParser. `get_nfs_referenciadas()` para matching |
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

- `scripts/migrations/criar_tabelas_carvia.py` + `.sql` — 6 tabelas, 18 indices
- `scripts/migrations/adicionar_sistema_carvia_usuarios.py` + `.sql` — Campo no Usuario
