# CarVia — Guia de Desenvolvimento

**24 arquivos** | **~5.9K LOC** | **21 templates** | **Atualizado**: 04/03/2026

Gestao de frete subcontratado: importar NF PDFs/XMLs + CTe XMLs, matchear NF-CTe,
subcontratar transportadoras com cotacao via tabelas existentes, gerar faturas cliente e transportadora.

> Campos de tabelas: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`
> Revisao de gaps: `app/carvia/REVISAO_GAPS.md` — 37 gaps mapeados com fluxogramas (03/03/2026)

---

## Estrutura de Telas (5 documentos + 1 importacao + 1 fluxo caixa)

| # | Documento | Entidade | URL | Tela |
|---|-----------|----------|-----|------|
| 1 | **NF Venda** | `CarviaNf` | `/carvia/nfs` | Lista + Detalhe (com itens de produto) |
| 2 | **CTe CarVia** | `CarviaOperacao` | `/carvia/operacoes` | Lista (com colunas Transp. Subcontratada + CTe Subcontrato) + Detalhe + Criar/Editar |
| 3 | **CTe Subcontrato** | `CarviaSubcontrato` | `/carvia/subcontratos` | Lista + Detalhe |
| 4 | **Fatura CarVia** | `CarviaFaturaCliente` | `/carvia/faturas-cliente` | Lista + Nova + Detalhe |
| 5 | **Fatura Subcontrato** | `CarviaFaturaTransportadora` | `/carvia/faturas-transportadora` | Lista + Nova + Detalhe |
| 6 | **Importacao** | `ImportacaoService` | `/carvia/importar` | Upload + Review + Confirmar |
| 7 | **Fluxo de Caixa** | `FluxoCaixaService` | `/carvia/fluxo-de-caixa` | Accordions por dia + Pagar/Desfazer + Card Saldo |
| 8 | **Extrato da Conta** | `FluxoCaixaService` | `/carvia/extrato-conta` | Movimentacoes com saldo acumulado + Saldo inicial |

### Cross-links entre documentos (navegacao completa)

A partir de QUALQUER documento, e possivel navegar para os outros 4.

```
NF Venda ──── N:M ──── CTe CarVia ──── FK ──── Fatura CarVia
│  (junction)              │                        │
│                          │ 1:N                    │ itens (FK→operacao, FK→nf)
│ (via fat_cli_item.nf_id) │                        │
│                     CTe Subcontrato ── FK ── Fatura Subcontrato
│ (via fat_transp         │                        │
│  _item.nf_id)           │ (via operacao)         │ itens (FK→sub, FK→op, FK→nf)
│                         │                        │
└─────────────────────────┴────────────────────────┘
      Todos os 5 documentos interligados por FK
```

**Itens de detalhe** sao o elo principal:
- `CarviaFaturaClienteItem` → FK `operacao_id`, `nf_id`
- `CarviaFaturaTransportadoraItem` → FK `subcontrato_id`, `operacao_id`, `nf_id`

---

## Estrutura de Arquivos

```
app/carvia/
  ├── routes/          # 8 sub-rotas (dashboard, importacao, nf, operacao, subcontrato, fatura, api, fluxo_caixa)
  ├── services/        # 10 services (parsers incl. dacte_pdf_parser, matching, importacao, cotacao, fatura_pdf_parser, linking, fluxo_caixa)
  ├── models.py        # 11 models (NF, NfItem, Operacao, Junction, Subcontrato, 2 Faturas, 2 FaturaItem, Despesa, ContaMovimentacao)
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

### R8: Numeracao sequencial CTe-### e Sub-###
Toda CarviaOperacao recebe `cte_numero = CTe-###` (ex: CTe-001, CTe-002).
Todo CarviaSubcontrato recebe `cte_numero = Sub-###` (ex: Sub-001, Sub-002).
Gerado via `CarviaOperacao.gerar_numero_cte()` e `CarviaSubcontrato.gerar_numero_sub()` — metodos estaticos com `with_for_update()`.
Campo `cte_numero VARCHAR(20)` ja existia — sem DDL, apenas backfill.
Backfill: `scripts/migrations/backfill_numeracao_sequencial_carvia.py`.

---

## Modelos

> Campos: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`

| Modelo | Tabela | Gotchas |
|--------|--------|---------|
| CarviaNf | `carvia_nfs` | `chave_acesso_nf` UNIQUE mas nullable (manual/referencia). `tipo_fonte`: PDF_DANFE, XML_NFE, MANUAL, FATURA_REFERENCIA (stub criado por backfill/importacao). **`status`**: ATIVA (default), CANCELADA (soft-delete GAP-20). Campos de auditoria: `cancelado_em`, `cancelado_por`, `motivo_cancelamento`. Rotas: `POST /carvia/nfs/<id>/cancelar`, **`POST /carvia/nfs/<id>/criar-cte`** (cria CTe CarVia diretamente da NF). Helpers: `get_faturas_cliente()`, `get_faturas_transportadora()` |
| CarviaNfItem | `carvia_nf_itens` | Itens de produto da NF. FK `nf_id`. Cascade delete-orphan |
| CarviaOperacao | `carvia_operacoes` | `cte_chave_acesso` UNIQUE nullable. `peso_utilizado` e CALCULADO (R3). FK `fatura_cliente_id`. `nfs_referenciadas_json` (JSONB) armazena refs NF do CTe XML para re-linking retroativo. **`gerar_numero_cte()`**: static method, retorna CTe-### (R8) |
| CarviaOperacaoNf | `carvia_operacao_nfs` | Junction N:N com UNIQUE(operacao_id, nf_id) |
| CarviaSubcontrato | `carvia_subcontratos` | `valor_final` e @property (valor_acertado ou valor_cotado). FK `transportadora_id` e `tabela_frete_id`. `numero_sequencial_transportadora` (R7). **`gerar_numero_sub()`**: static method, retorna Sub-### (R8) |
| CarviaFaturaCliente | `carvia_faturas_cliente` | **UNIQUE(numero_fatura, cnpj_cliente)**. Status: PENDENTE, EMITIDA, PAGA, CANCELADA. `pago_por`/`pago_em` preenchidos ao pagar. 14 campos extras SSW (tipo_frete, pagador_*, cancelada, etc). `cnpj_cliente` = CNPJ do PAGADOR (NAO do beneficiario/CarVia). Relationship `itens` → CarviaFaturaClienteItem |
| CarviaFaturaClienteItem | `carvia_fatura_cliente_itens` | Itens CTe de detalhe por fatura. FK `fatura_cliente_id` CASCADE. **FK `operacao_id` e `nf_id`** (nullable, resolvidos por LinkingService). Campos: cte_numero, contraparte_cnpj/nome, nf_numero, valor_mercadoria, peso_kg, frete, icms, iss, st, base_calculo |
| CarviaFaturaTransportadora | `carvia_faturas_transportadora` | **UNIQUE(numero_fatura, transportadora_id)**. **2 status independentes**: `status_conferencia` (conferencia documental: PENDENTE/EM_CONFERENCIA/CONFERIDO/DIVERGENTE) e `status_pagamento` (financeiro: PENDENTE/PAGO). `pago_por`/`pago_em` preenchidos ao pagar. Relationship `itens` → CarviaFaturaTransportadoraItem |
| CarviaFaturaTransportadoraItem | `carvia_fatura_transportadora_itens` | Itens de detalhe por fatura subcontrato. FK `fatura_transportadora_id` CASCADE. **FK `subcontrato_id`, `operacao_id`, `nf_id`** (nullable). Campos: cte_numero, cte_data_emissao, contraparte_cnpj/nome, nf_numero, valor_mercadoria, peso_kg, valor_frete, valor_cotado, valor_acertado |
| CarviaContaMovimentacao | `carvia_conta_movimentacoes` | Movimentacoes financeiras da conta. `tipo_doc`: fatura_cliente/fatura_transportadora/despesa/saldo_inicial/ajuste. `doc_id`=0 para saldo_inicial. **UNIQUE(tipo_doc, doc_id)** impede duplicata. `tipo_movimento`: CREDITO/DEBITO. `valor` sempre positivo. Saldo calculado por SUM (nao armazenado) |

---

## Importacao — Fluxo de Classificacao

```
Upload (NF-e XML, CTe XML, DACTE PDF, DANFE PDF, Fatura PDF)
    │
    ├── NF-e XML / PDF DANFE → CarviaNf + CarviaNfItem
    │   └── XML: is_nfe() verifica mod==55 (rejeita CTe disfarçado)
    │
    ├── CTe XML / PDF DACTE → Classificar por CNPJ emitente (R6)
    │   ├── CNPJ == CARVIA_CNPJ → CarviaOperacao (CTe CarVia)
    │   │   └── Vincular NFs via junction (matching por chave de acesso)
    │   └── CNPJ != CARVIA_CNPJ → CarviaSubcontrato (CTe Subcontrato)
    │       └── Vincular a CarviaOperacao via NFs compartilhadas
    │           Se nao encontrar operacao → erro/warning
    │
    ├── [PRE-CHECK] Verificar transportadoras para subcontratos + faturas
    │   └── CNPJs nao cadastrados → transportadoras_nao_encontradas (alerta + modal)
    │
    └── Fatura PDF → parse_multi() (1 fatura por pagina)
        │   Parser: regex → Haiku → Sonnet (3 camadas escalonadas)
        │   Extrai: pagador (cliente), beneficiario (CarVia), tipo frete, itens CTe
        │
        ├── Dedup: verifica banco por (numero_fatura, cnpj_cliente/data_emissao)
        │   Se ja existe → log "Fatura ja existe (ignorando)" + return None
        │
        ├── CNPJ beneficiario == transportadora cadastrada → CarviaFaturaTransportadora
        │   └── Warning se CNPJ beneficiario nao cadastrado e != CARVIA_CNPJ
        └── Outro CNPJ → CarviaFaturaCliente + CarviaFaturaClienteItem (itens)
            cnpj_cliente = cnpj_PAGADOR (NAO cnpj_emissor/beneficiario)
```

**Env var necessaria**: `CARVIA_CNPJ` (apenas digitos, ex: `12345678000199`).
Se nao configurada, todos CTes sao classificados como CarVia (compatibilidade) e um aviso e emitido.

**Pre-check de transportadoras** (no review, ANTES de confirmar):
- `processar_arquivos()` verifica se CNPJs de emitentes de CTes subcontrato e beneficiarios de faturas
  estao cadastrados como transportadoras no banco
- Resultado inclui `transportadoras_nao_encontradas` — lista de CNPJs pendentes com nome/uf/cidade
- Template `importar_resultado.html` mostra alerta com botoes de cadastro rapido (modal AJAX)
- Endpoint `POST /carvia/api/cadastrar-transportadora` (CNPJ, razao_social, cidade, UF, freteiro)
  - Dedup: se CNPJ ja existe, retorna transportadora existente sem erro
  - Formata CNPJ automaticamente (XX.XXX.XXX/XXXX-XX)
- Ao cadastrar, badges na tabela de CTes mudam de vermelho para verde via JS

**Classificacao PDF** (ordem de verificacao):
1. **DACTE**: texto "DACTE"/"Conhecimento de Transporte" ou chave com modelo=57 → `PDF_DACTE`
2. **DANFE**: chave 44 digitos com modelo != 57 → `PDF_DANFE`
3. **Fatura**: fallback → `PDF_FATURA`

**CNPJ matriz vs filial**: Faturas podem usar CNPJ matriz (ex: 0001-49) enquanto DACTEs
usam filial (ex: 0002-20). A classificacao de transportadora busca por CNPJ exato cadastrado.

### Fatura PDF — Multi-Pagina (formato SSW)

PDFs SSW (`ssw.inf.br`) contem N faturas por arquivo (1 por pagina).
`parse_multi()` retorna `List[Dict]` (1 dict por pagina). `parse()` retorna apenas 1o resultado (backwards compat).

**Pagador vs Beneficiario**:
- `cnpj_emissor` / `nome_emissor` = beneficiario (CarVia, quem emite a fatura)
- `cnpj_pagador` / `nome_pagador` = cliente (quem paga) — usado como `cnpj_cliente`
- Bug anterior: `cnpj_emissor` era gravado como `cnpj_cliente` (CNPJ da CarVia em TODAS as faturas)

**Campos SSW extras** (14 novos em CarviaFaturaCliente):
- `tipo_frete` (CIF/FOB), `quantidade_documentos`, `valor_mercadoria`, `valor_icms`, `aliquota_icms`, `valor_pedagio`
- `vencimento_original` (antes de reprogramacao), `cancelada` (flag FATURA CANCELADA → status=CANCELADA)
- `pagador_endereco`, `pagador_cep`, `pagador_cidade`, `pagador_uf`, `pagador_ie`, `pagador_telefone`

---

## Parsers — Ordem de Confiabilidade

| Parser | Confiabilidade | Notas |
|--------|---------------|-------|
| `nfe_xml_parser.py` | Alta | Namespace-agnostic. Fonte de verdade para NF-e. Extrai itens de produto. `is_nfe()` verifica mod==55 |
| `cte_xml_parser_carvia.py` | Alta | Herda CTeXMLParser. `get_nfs_referenciadas()` para matching. `get_emitente()` para classificacao |
| `dacte_pdf_parser.py` | Media-Alta | Multi-formato (SSW, Bsoft, ESL, Lonngren, Montenegro). Deteccao automatica via `_detectar_formato()`. Separa chaves modelo=57 (CTe) de modelo=55 (NF-e). Saida identica a `cte_xml_parser_carvia` + campos extras (formato, tipo_servico, cte_carvia_ref, componentes_frete, volumes) |
| `danfe_pdf_parser.py` | Media | Regex-based com pdfplumber+pypdf fallback. Campo `confianca` (0.0-1.0) |
| `fatura_pdf_parser.py` | Variavel | 3 camadas: Regex (alta) -> Haiku (media) -> Sonnet (baixa). Campo `confianca` + `metodo_extracao` |

### DACTE Multi-Formato — Deteccao e Suporte

| Formato | Emitente(s) | Deteccao (footer) | Campos Extras |
|---------|-------------|-------------------|---------------|
| **SSW** | Tocantins, Velocargas, Dago | `SSW.INF.BR` | Referencia completa |
| **Bsoft** | Transmenezes | `Bsoft Internetworks` | Peso via "PESO X/KG" |
| **ESL** | Transperola | `ESL Informatica` | Origem/Destino via "INICIO/TERMINO DA PRESTACAO", UF-Cidade invertido, PESO TAXADO/CUBADO |
| **Lonngren** | CD Uni Brasil | `Lonngren Sistemas` | Frete via "VALOR TOTAL DO SERVICO" |
| **Montenegro** | Montenegro | `Impresso por :` | Chave robusta (sem strip global), fallback "A RECEBER" |

**Chave de acesso (3 niveis)**: 1) 44 digitos consecutivos → 2) Blocos formatados com separadores (limpa por match, NAO global) → 3) Busca localizada na secao "Chave de acesso"

**Confianca ponderada**: chave=2x, frete=2x, rota=1.5x cada, numero/emitente/peso=1x cada (total 10 pontos)

---

## Matching — Algoritmo de 3 Niveis

1. **CHAVE** — Match exato por `chave_acesso_nf` 44 digitos (alta confianca)
2. **CNPJ_NUMERO** — Fallback por `(cnpj_emitente, numero_nf)` (media confianca)
3. **NAO_ENCONTRADA** — NF referenciada no CTe nao importada

---

## Linking — Vinculacao Cross-Documento

`LinkingService` (`app/carvia/services/linking_service.py`) resolve FKs entre documentos:

| Metodo | Funcao |
|--------|--------|
| `resolver_operacao_por_cte(cte_numero)` | Busca CarviaOperacao por CTe, normaliza zeros a esquerda |
| `resolver_nf_por_numero(nf_numero, cnpj)` | Busca CarviaNf por numero + CNPJ (emitente OU destinatario) |
| `vincular_nf_a_operacoes_orfas(nf)` | Re-linking CTe→NF: busca operacoes com nfs_referenciadas_json que referenciam a NF e cria junctions |
| `vincular_operacao_a_itens_fatura_orfaos(operacao)` | Re-linking CTe→Fat: atualiza operacao_id em itens de fatura orfaos + cria junctions |
| `vincular_nf_a_itens_fatura_orfaos(nf)` | Re-linking NF→Fat: atualiza nf_id em itens de fatura orfaos (incl. stubs FATURA_REFERENCIA) + cria junctions |
| `vincular_operacoes_da_fatura(fatura_id)` | **Backward binding**: seta `fatura_cliente_id` e `status=FATURADO` nas operacoes via itens ja resolvidos |
| `vincular_itens_fatura_cliente(fatura_id, auto_criar_nf)` | Resolve `operacao_id` e `nf_id` em itens existentes (3 niveis de fallback) |
| `_criar_nf_referencia(nf_numero, cnpj, ...)` | Cria CarviaNf stub (FATURA_REFERENCIA) — idempotente |
| `_resolver_nf_via_junction(nf_numero, operacao_id)` | Busca NF via junction carvia_operacao_nfs |
| `_criar_junction_se_necessario(operacao_id, nf_id)` | Cria junction se nao existe — idempotente |
| `criar_itens_fatura_transportadora(fatura_id)` | Gera itens a partir de subcontratos vinculados |
| `criar_itens_fatura_cliente_from_operacoes(fatura_id)` | Gera itens a partir de operacoes (faturas manuais) |
| `backfill_todas_faturas()` | One-time para dados existentes |

**Matching de CTe**: `ltrim(cte_numero, '0')` normaliza "00000001" == "1".
**Matching de NF**: numero + CNPJ contraparte (emitente OU destinatario), ambos normalizados.
**Fallback 3 niveis**: 1) Match direto → 2) Via junction → 3) Criar NF referencia (se `auto_criar_nf=True`).

**Chamado automaticamente por**:
- `ImportacaoService.salvar_importacao()` — durante import de fatura PDF
- `ImportacaoService.salvar_importacao()` — apos criar NF: `vincular_nf_a_operacoes_orfas` + `vincular_nf_a_itens_fatura_orfaos`
- `ImportacaoService.salvar_importacao()` — apos criar/reusar CTe: `vincular_operacao_a_itens_fatura_orfaos`
- `fatura_routes.nova_fatura_cliente()` — ao criar fatura manualmente
- `fatura_routes.nova_fatura_transportadora()` — ao criar fatura manualmente

**Ordem de importacao**: Independente. Re-linking retroativo garante que TODAS as 6 permutacoes (NF, CTe, Fatura) criam vinculos corretos.

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
- `scripts/migrations/adicionar_campos_fatura_cliente_v2.py` + `.sql` — 14 novos campos em `carvia_faturas_cliente` + tabela `carvia_fatura_cliente_itens`
- `scripts/migrations/carvia_linking_v1_schema.py` + `.sql` — FK `operacao_id`/`nf_id` em `carvia_fatura_cliente_itens` + tabela `carvia_fatura_transportadora_itens` (15 cols, 4 indices)
- `scripts/migrations/carvia_linking_v2_backfill.py` — Backfill de FKs em itens existentes (requer v1 antes)
- `scripts/migrations/backfill_carvia_nf_linking.py` + `.sql` — Cria CarviaNf stubs (FATURA_REFERENCIA) para NFs referenciadas em faturas que nunca foram importadas, vincula nf_id e cria junctions
- `scripts/migrations/adicionar_status_pagamento_fatura_transportadora.py` + `.sql` — 3 novos campos (`status_pagamento`, `pago_por`, `pago_em`) + indice
- `scripts/migrations/add_nfs_referenciadas_json_operacoes.py` + `.sql` — Campo JSONB `nfs_referenciadas_json` em carvia_operacoes (refs NF do CTe XML)
- `scripts/migrations/backfill_nfs_referenciadas_json.py` + `.sql` — Backfill: popula JSON a partir de junctions existentes
- `scripts/migrations/criar_tabela_carvia_conta_movimentacoes.py` + `.sql` — Tabela `carvia_conta_movimentacoes` (saldo por SUM, UNIQUE tipo_doc+doc_id)
- `scripts/migrations/adicionar_pago_em_por_carvia.py` + `.sql` — `pago_em`/`pago_por` em `carvia_faturas_cliente` e `carvia_despesas`
- `scripts/migrations/backfill_carvia_fatura_operacao_binding.py` + `.sql` — Backfill: seta `fatura_cliente_id` e `status=FATURADO` em operacoes via itens de fatura existentes
- `scripts/migrations/fix_carvia_faturas_duplicadas.py` + `.sql` — Fix: remover 21 faturas cliente duplicadas (importacao 2x do mesmo PDF)
- `scripts/migrations/add_unique_faturas_carvia.py` + `.sql` — UNIQUE(numero_fatura, cnpj_cliente) em faturas_cliente + UNIQUE(numero_fatura, transportadora_id) em faturas_transportadora
- `scripts/migrations/adicionar_status_carvia_nfs.py` + `.sql` — Campo `status` VARCHAR(20) DEFAULT 'ATIVA' + `cancelado_em`, `cancelado_por`, `motivo_cancelamento` + indice
- `scripts/migrations/backfill_numeracao_sequencial_carvia.py` — Backfill: preenche `cte_numero` NULL com CTe-### (operacoes) e Sub-### (subcontratos). Sem DDL

---

## Componentes UI

### Wizard Criar CTe CarVia (`criar_manual.html`)
2 cards: **NFs** (selecao com filtro por cliente + checkbox) + **Valor** (R$, obrigatorio).
Sem step de transportadora (removido — CarVia e sempre a transportadora).
NF selecionada popula resumo (peso, valor, destino). Submit cria CarviaOperacao + junctions.

### Criar CTe via NF (`POST /carvia/nfs/<id>/criar-cte`)
Modal no detalhe da NF com valor CTe + observacoes. Cria operacao diretamente da NF (1:1).
Popula automaticamente: cliente (emitente), destino (destinatario), peso, valor mercadoria.

### Autocomplete Transportadora (`selecionar_transportadora.html`)
Input com debounce 300ms + dropdown absoluto `.carvia-autocomplete-results`.
Busca via `GET /carvia/api/opcoes-transportadora?busca=X&uf_destino=Y`.
Ultimo item fixo: "Criar Nova Transportadora" → modal `#modalCriarTransportadora`.
Modal usa `POST /carvia/api/cadastrar-transportadora` (JSON). Apos cadastro: fecha modal + auto-seleciona.
CSS: `css/modules/_carvia.css` (`.carvia-autocomplete-*`)
