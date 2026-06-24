<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-23
-->
# Módulo Motos Assaí

> **Papel:** guia de desenvolvimento do modulo Motos Assai — operacao B2B Q.P.A. -> Sendas/Assai com motos eletricas, isolada de outros modulos.

## Indice

- [Contexto](#contexto)
- [Fronteira do módulo (o que NÃO fazer)](#fronteira-do-módulo-o-que-não-fazer)
- [Convenções obrigatórias](#convenções-obrigatórias)
  - [1. Prefixo de tabela `assai_`](#1-prefixo-de-tabela-assai_)
  - [2. Blueprint isolado](#2-blueprint-isolado)
  - [3. Toggle master `sistema_motos_assai`](#3-toggle-master-sistema_motos_assai)
  - [4. Menu](#4-menu)
- [Invariante central](#invariante-central)
- [Eventos por chassi (`assai_moto_evento.tipo`)](#eventos-por-chassi-assai_moto_eventotipo)
- [Modelo de dados (29 tabelas)](#modelo-de-dados-29-tabelas)
- [Lista de constantes/aliases por arquivo](#lista-de-constantesaliases-por-arquivo)
- [Services complementares (responsabilidades)](#services-complementares-responsabilidades)
- [Plano 3 implementado (2026-05-07)](#plano-3-implementado-2026-05-07)
  - [Parsers de recibo Motochefe (PDF + XLSX + LLM)](#parsers-de-recibo-motochefe-pdf-xlsx-llm)
  - [chassi_validator e moto_evento_service](#chassi_validator-e-moto_evento_service)
  - [Wizard de recebimento físico A→B→C→D](#wizard-de-recebimento-físico-abcd)
  - [Lock pessimista e invariantes de concorrência](#lock-pessimista-e-invariantes-de-concorrência)
  - [Recebimento como SOT](#recebimento-como-sot)
  - [Status do recibo](#status-do-recibo)
  - [Rotas adicionadas (Plano 3)](#rotas-adicionadas-plano-3)
  - [Fixtures de teste](#fixtures-de-teste)
- [Plano 2 implementado (2026-05-07)](#plano-2-implementado-2026-05-07)
  - [Parsers de PDF (`services/parsers/`)](#parsers-de-pdf-servicesparsers)
  - [`modelo_resolver` — service COMPARTILHADO](#modelo_resolver-service-compartilhado)
  - [Fluxo Pedido VOE → Compra Motochefe](#fluxo-pedido-voe-compra-motochefe)
- [Plano 4 implementado (2026-05-07)](#plano-4-implementado-2026-05-07)
  - [Pipeline de saída (ESTOQUE → MONTADA/PENDENTE → DISPONIVEL → SEPARADA → FATURADA)](#pipeline-de-saída-estoque-montadapendente-disponivel-separada-faturada)
- [Plano 5 implementado (2026-05-12) — Integração lista_pedidos.html](#plano-5-implementado-2026-05-12-integração-lista_pedidoshtml)
  - [Novos modelos (2 tabelas)](#novos-modelos-2-tabelas)
  - [`AssaiSeparacao` ganhou 4 campos override](#assaiseparacao-ganhou-4-campos-override)
  - [Mudança crítica: N separações por (pedido, loja)](#mudança-crítica-n-separações-por-pedido-loja)
  - [Espelhamento Nacom — fallback dos 4 campos](#espelhamento-nacom-fallback-dos-4-campos)
  - [Fluxo de finalização com saldo planejado](#fluxo-de-finalização-com-saldo-planejado)
  - [Ajuste pós-NF (NF é fonte de verdade)](#ajuste-pós-nf-nf-é-fonte-de-verdade)
  - [Novas rotas (blueprint `/motos-assai`)](#novas-rotas-blueprint-motos-assai)
  - [Endpoints retrocompatíveis (sem `?sep_id`)](#endpoints-retrocompatíveis-sem-sep_id)
  - [Telas rápidas](#telas-rápidas)
  - [Endpoints adicionados (Plano 4)](#endpoints-adicionados-plano-4)
  - [Estados de evento finais (Plano 4)](#estados-de-evento-finais-plano-4)
- [Módulo completo — visão geral arquitetural](#módulo-completo-visão-geral-arquitetural)
- [Skills + Agente disponíveis](#skills-agente-disponíveis)
- [Manutenção / Roadmap futuro](#manutenção-roadmap-futuro)
- [CCe como entidade (2026-05-13)](#cce-como-entidade-2026-05-13)
  - [Por que esse design](#por-que-esse-design)
  - [Modelo `AssaiCce` (Migration 28)](#modelo-assaicce-migration-28)
  - [Cenários cobertos (3 entradas)](#cenários-cobertos-3-entradas)
  - [Match reverso ao importar NF](#match-reverso-ao-importar-nf)
  - [Tipo `IGNORADA` (DUPLICATAS / ENDERECO)](#tipo-ignorada-duplicatas-endereco)
  - [Idempotência](#idempotência)
  - [Rotas (`/motos-assai/cce/*`)](#rotas-motos-assaicce)
  - [Arquivos](#arquivos)
  - [Gotchas](#gotchas)
- [Onboarding Tours (2026-05-08)](#onboarding-tours-2026-05-08)
- [Fix parser zero-padding + edição manual (2026-06-18)](#fix-parser-zero-padding--edição-manual-2026-06-18)
- [Guards de import de NF Q.P.A. (2026-06-23)](#guards-de-import-de-nf-qpa-2026-06-23)
- [Referências](#referências)

## Contexto

29 tabelas com prefixo `assai_`, blueprint isolado. Pipeline completo implementado: Cadastros -> Parser VOE -> Pedido -> Compra -> Recibo Motochefe -> Recebimento fisico -> Saida (NF Q.P.A.). Fronteira estrita contra HORA/CarVia/Motochefe (reuso so via adapter/subclasse).

**Data da implementacao**: 2026-05-13
**Status**: Foundation + Cadastros (Plano 1) + Parser VOE + Pedido + Compra (Plano 2) + Recibo Motochefe + Recebimento físico (Plano 3) + Pipeline de saída completo (Plano 4) + **Integração lista_pedidos.html (Plano 5)** + **CCe como entidade com match reverso (2026-05-13)** — TODOS implementados.
**Propósito**: gerenciar a operação B2B Q.P.A. → Sendas/Assaí com motos elétricas, isolada de outros módulos.

---

## Fronteira do módulo (o que NÃO fazer)

| Módulo vizinho | Motivo da fronteira |
|---|---|
| `app/hora/` | PJ diferente; HORA é B2C varejo, Motos Assaí é B2B atacadista |
| `app/carvia/` | CarVia só transporta. Reuso permitido APENAS via adapter |
| `app/motochefe/` | PJ diferente |
| `app/pedidos/leitura/` | Reuso permitido via subclasse de `PDFExtractor` |

---

## Convenções obrigatórias

### 1. Prefixo de tabela `assai_`

Todas as tabelas começam com `assai_`. **29 tabelas** no schema atual
(lista completa: `grep -rhoE "__tablename__\s*=\s*['\"]assai_[a-z0-9_]+" app/motos_assai/`).

### 2. Blueprint isolado

Rotas em `app/motos_assai/routes/`, services em `app/motos_assai/services/`,
models em `app/motos_assai/models/`. Blueprint `motos_assai_bp` registrado em
`app/__init__.py` com `url_prefix='/motos-assai'`.

### 3. Toggle master `sistema_motos_assai`

Coluna em `usuarios`. Método `Usuario.pode_acessar_motos_assai()`:
admin sempre passa; status != 'ativo' bloqueia mesmo com flag.

Decorator `@require_motos_assai` em TODAS as rotas (sem exceção).

### 4. Menu

Link em `app/templates/base.html` condicionado a
`current_user.pode_acessar_motos_assai()`.

---

## Invariante central

**`assai_moto.chassi` é a chave universal do módulo.**

1. Toda tabela transacional tem `chassi` indexada.
2. `assai_moto` é insert-once com atributos imutáveis (UPDATE apenas em `cor`/`modelo_id`
   quando recebimento físico diverge do recibo Motochefe — SOT, padrão Hora).
3. Estado atual de uma moto = consulta à tabela de eventos
   (`assai_moto_evento` ordenado por `ocorrido_em DESC`), nunca UPDATE em coluna `status`.
4. `assai_moto_evento` é append-only — nunca DELETE; reversão cria nova linha
   (`REVERTIDA_PARA_MONTADA`).

---

## Eventos por chassi (`assai_moto_evento.tipo`)

| Tipo | Significado | Conta como em estoque? |
|------|-------------|------------------------|
| `ESTOQUE` | Recebida no CD | Sim |
| `MONTADA` | Montada e OK | Sim |
| `PENDENTE` | Peça com defeito a resolver | Sim, mas bloqueia DISPONIVEL |
| `PENDENCIA_RESOLVIDA` | Voltou a MONTADA após pendência | Sim (efetivo MONTADA) |
| `DISPONIVEL` | Tag + manual + pronta para separação | Sim |
| `REVERTIDA_PARA_MONTADA` | Operador reverteu disponibilização | Sim (efetivo MONTADA) |
| `SEPARADA` | Vinculada a separação ativa | Não |
| `FATURADA` | NF Q.P.A. importada e bateu | Não |
| `CANCELADA` | Separação cancelada (volta como DISPONIVEL via novo evento) | Depende |
| `MOTO_FALTANDO` | Declarada no recibo mas não chegou | Não |
| `DEMONSTRACAO` | Moto cedida para demonstração (backfill manual) | Não |

> `DEMONSTRACAO` adicionado em 2026-06-20 (Migration 33 — ALTER do CHECK
> `ck_assai_moto_evento_tipo`; **adicionar evento ao model exige migration**, a
> coluna tem CHECK). Em `EVENTOS_FORA_ESTOQUE`. Usado pela skill `corrigindo-dados-assai`.
> ⚠️ A Migration 33 **NÃO consta no build.sh**: foi aplicada manualmente em prod
> (padrão da 32); os arquivos `scripts/migrations/motos_assai_33_*` ficam só como
> registro do DDL (idempotente — DROP IF EXISTS + recriar, se precisar re-rodar).

---

## Modelo de dados (29 tabelas)

Ver spec em `docs/superpowers/specs/2026-05-07-motos-assai-design.md` §4.

Cadastros: `assai_cd`, `assai_loja`, `assai_modelo`, `assai_modelo_alias`.
Identidade: `assai_moto`, `assai_moto_evento`.
Pipeline: `assai_pedido_venda*` (3 tabelas: `assai_pedido_venda`,
`assai_pedido_venda_loja` ⭐, `assai_pedido_venda_item`),
`assai_compra_motochefe*`, `assai_recibo_motochefe*`.
Saída: `assai_separacao*` (3 tabelas: `assai_separacao`, `assai_separacao_item`,
`assai_separacao_saldo_modelo` ⭐), `assai_nf_qpa*` (3 tabelas: `assai_nf_qpa`,
`assai_nf_qpa_item`, `assai_nf_qpa_item_vinculo_historico`).
CCe: `assai_cce` (Carta de Correção Eletrônica como entidade própria; pode chegar ANTES da NF — flag `tem_nf` + match reverso; status PENDENTE/APLICADA/IGNORADA/ERRO; `protocolo_cce` UNIQUE).
Recibo (itens): `assai_recibo_item` (chassis declarados no recibo Motochefe; `assai_recibo_motochefe*` acima cobre só o cabeçalho).
Carregamento: `assai_carregamento`, `assai_carregamento_item` (etapa física entre Separação e NF; escaneia chassi por chassi).
Divergências: `assai_divergencia` (sistema centralizado: 8 tipos + 5 resoluções; `detalhes` JSONB).
Excel Q.P.A.: `assai_pedido_excel` (histórico versionado do Excel por separação em S3; `versao`, `ativo`).
Devolução NFd: `assai_devolucao_nfd` + `assai_devolucao_item` + `assai_devolucao_anexo` (cliente devolve chassi FATURADO → volta a PENDENTE; UNIQUE `(nf_qpa_origem_id, numero_nfd)`).
Pós-venda: `assai_pos_venda_ocorrencia` + `assai_pos_venda_ocorrencia_anexo` (ocorrências LOJA/CLIENTE sobre chassi vendido; NÃO append-only — admite UPDATE/DELETE).

⭐ = adicionadas no Plano 5 (2026-05-12).

---

## Lista de constantes/aliases por arquivo

- `app/motos_assai/models/moto.py`: `EVENTO_*`, `EVENTOS_VALIDOS`, `EVENTOS_EM_ESTOQUE`
- `app/motos_assai/models/pedido.py`: `PEDIDO_STATUS_*`, `PEDIDO_STATUS_VALIDOS`
- `app/motos_assai/models/compra.py`: `COMPRA_STATUS_*`, `COMPRA_STATUS_VALIDOS`
- `app/motos_assai/models/recibo.py`: `RECIBO_STATUS_*`, `DIVERGENCIA_*`
- `app/motos_assai/models/separacao.py`: `SEPARACAO_STATUS_*`
- `app/motos_assai/models/nf_qpa.py`: `NF_STATUS_*`
- `app/motos_assai/models/modelo.py`: `ALIAS_TIPO_*`
- `app/motos_assai/services/pedido_service.py`: `CONFIANCA_LIMIAR = 0.70`
- `app/motos_assai/services/compra_service.py`: `CompraValidationError`
- `app/motos_assai/services/chassi_validator.py`: `MOTIVO_REGEX_INVALIDO`, `MOTIVO_MODELO_SEM_REGEX`, `MOTIVO_CHASSI_VAZIO`
- `app/motos_assai/services/recebimento_service.py`: `RecebimentoConflictError`, `RecebimentoValidationError`
- `app/motos_assai/services/montagem_service.py`: `MontagemError` (chassi não em ESTOQUE)
- `app/motos_assai/services/disponibilizar_service.py`: `DisponibilizarError` (PENDENTE bloqueia), `ReverterError` (motivo obrigatório ≥3 chars)
- `app/motos_assai/services/separacao_service.py`: `SeparacaoError`, `SeparacaoConflictError` (race condition → 409)
- `app/motos_assai/services/faturamento_service.py`: `gerar_excel_qpa()`, `FaturamentoError`
- `app/motos_assai/services/parsers/nf_qpa_adapter.py`: `NfQpaAdapter`, `extrair_nf_qpa()`, `match_nf_separacao()`

---

## Services complementares (responsabilidades)

Não indexados na lista de constantes acima:
- `carregamento_service` — ciclo de `AssaiCarregamento` (etapa física Sep→NF): criar, escanear chassi, cancelar item/carregamento, finalizar (integra `pedido_status` + `separacao_mirror`). Exc.: `Carregamento{Validation,Conflict,State,Excedente,CrossLoja}Error`.
- `divergencia_service` — cria/resolve `AssaiDivergencia` (8 tipos, 5 resoluções); `criar_divergencia` NÃO commita (caller decide); `resolver_divergencia` re-roda `_calcular_match`.
- `devolucao_service` — registra NFd do cliente p/ chassis FATURADOS → voltam a PENDENTE (`devolvido=True`); idempotência UNIQUE, rollback S3 se commit DB falhar.
- `pos_venda_service` — CRUD de ocorrências pós-venda (LOJA/CLIENTE) + anexos S3; só chassis em `assai_nf_qpa_item` contam como vendidos.
- `cancelamento_nf_service` — cancela NF Q.P.A. (FATURADA → CARREGADA/SEPARADA/DISPONIVEL) e aplica correção de chassi via CCe (`aplicar_correcao_cce` + re-match).
- `geocoding_service` — geocodifica `AssaiLoja` (Google Geocoding API → fallback Nominatim 1 req/s); cacheia `latitude/longitude/geocoded_at`.
- `resumo_service` — agrega pipeline por modelo × status efetivo (último evento); `resumo_por_modelo`, `metricas_por_pedido[_loja]`.
- `pedido_status_service` — recalcula `AssaiPedidoVenda.status` (qtd_faturada vs qtd_pedida); não recalcula CANCELADO (estado terminal).
- `pendencia_service` — consultas read-only de pendências de montagem (abertas, histórico resolvidas, contagens, por operador/modelo).
- `reprocessar_match_service` — re-roda `_calcular_match` em NFs quando a fonte muda (cadastro de chassi, criação de loja, cancelamento de separação); helpers `nfs_afetadas_por_*`.
- `chassi_autocomplete_service` — autocomplete read-only de chassi por contexto (recebimento/montagem/disponibilizar/separacao/montagem_doador); `buscar_chassis(q, contexto, ...)`.
- `separacao_mirror_service` — espelha `AssaiSeparacao` FECHADA → `separacao` Nacom (`separacao_lote_id='ASSAI-SEP-{id}'`) p/ integrar ao fluxo Cotação/Embarque/Frete; resolve os 4 campos (expedicao/agendamento/protocolo/confirmado).

---

## Plano 3 implementado (2026-05-07)

### Parsers de recibo Motochefe (PDF + XLSX + LLM)

- `MotochefeReciboPdfExtractor` (`services/parsers/motochefe_recibo_pdf_extractor.py`): pdfplumber + `extract_tables()` com lines strategy. Detecta colunas CHASSI/MOTOR/COR no header. Extrai data, equipe (HAROLDO SP), conferente, total declarado.
- `MotochefeReciboXlsxExtractor` (`services/parsers/motochefe_recibo_xlsx_extractor.py`): openpyxl `data_only=True`. Localiza header da tabela pela presença de células CHASSI.
- `motochefe_recibo_llm_fallback.py`: Haiku 4.5 → Sonnet 4.6. Aceita PDF (document block) ou XLSX serializado como texto.
- **Limiar de confiança**: `CONFIANCA_LIMIAR = 0.80` em `recibo_service`. Acionado quando `chassis_extraidos / total_declarado < 0.80`.

### chassi_validator e moto_evento_service

- `chassi_validator.py`: validação regex do chassi contra padrão configurado no `AssaiModelo.regex_chassi`. Não-bloqueante — retorna `{ok, motivo, regex_usado}`. Motivos: `MOTIVO_REGEX_INVALIDO`, `MOTIVO_MODELO_SEM_REGEX`, `MOTIVO_CHASSI_VAZIO`.
- `moto_evento_service.py`: helpers `emitir_evento(chassi, tipo, ...)`, `status_atual(chassi)`, `historico(chassi)`. Append-only — nunca DELETE.
  - **`ocorrido_em` opcional** (2026-06-19, D8 IMP-2026-06-18-005 / IMP-2026-06-19-001):
    `emitir_evento(..., ocorrido_em=<datetime Brasil naive>)` registra evento com
    data retroativa para **carga histórica / backfill / correção**. Quando omitido,
    o model aplica `agora_brasil_naive` (comportamento atual dos ~25 callers
    inalterado). Use este parâmetro em vez de instanciar `AssaiMotoEvento` na mão —
    preserva a validação de tipo e a normalização do chassi do service.

### Wizard de recebimento físico A→B→C→D

```
A: selecionar recibo  →  B: escanear chassi  →  C: confirmar modelo/cor  →  D: progresso/finalizar
```

- Template `recebimento/wizard.html` com 4 passos + indicador de progresso.
- JS `recebimento_wizard.js`: `html5-qrcode@2.3.8` para câmera mobile, leitor USB (Enter dispara), digitação manual. `cfg.endpoints` injetado via template.
- Foto opcional: `<input type="file" capture="environment">` → upload S3 (`motos_assai/recebimento/<recibo_id>/<chassi>_<filename>`).

**Endpoints AJAX (todos `require_motos_assai` + `login_required`)**:
- `POST /recebimento/validar-chassi` → `{ok, na_nf, ja_conferido, modelo_id_esperado, cor_esperada, regex_check, mensagem}`
- `POST /recebimento/registrar` → `{ok, item_id, tipo_divergencia, total, conferidos}` | 409 em race
- `POST /recebimento/finalizar/<recibo_id>` → `{ok, status, redirect}` | 400 se faltantes sem confirmar
- `POST /recebimento/foto-upload` → `{ok, s3_key}`

### Lock pessimista e invariantes de concorrência

- UNIQUE parcial em `(recibo_id, chassi)` (Migration 07 — idempotente).
- `with_for_update(of=AssaiMoto)` ao buscar `AssaiMoto` antes de criar/atualizar.
- `IntegrityError` → `RecebimentoConflictError` → HTTP 409 com `{retry: true}`.

### Recebimento como SOT

Se modelo/cor conferidos divergem do recibo, aplica UPDATE em `AssaiMoto.cor` e `AssaiMoto.modelo_id` (exceção autorizada à invariante 3).

### Status do recibo

`RECEBIDO_AGUARDANDO_CONFERENCIA` → `EM_CONFERENCIA` (1º chassi conferido) → `CONCLUIDO` (zero divergências) ou `COM_DIVERGENCIA`.

### Rotas adicionadas (Plano 3)

- `GET /recibos/upload` — upload PDF/XLSX recibo Motochefe, extração, resultado
- `GET /recibos/<id>` — detalhe do recibo com lista de itens
- `GET /recibos` — lista de recibos
- `GET /recibos/<id>/conferir` — wizard A→B→C→D
- `POST /recebimento/validar-chassi` — validação AJAX
- `POST /recebimento/registrar` — conferência AJAX
- `POST /recebimento/finalizar/<id>` — finalização AJAX
- `POST /recebimento/foto-upload` — upload S3 AJAX

### Fixtures de teste

Exemplos de arquivos recibo em `.gitignore` (não commitados):
- `tests/motos_assai/fixtures/recibo_motochefe_exemplo.pdf`
- `tests/motos_assai/fixtures/recibo_motochefe_exemplo.xlsx`

---

## Plano 2 implementado (2026-05-07)

### Parsers de PDF (`services/parsers/`)

**Identificação de documento** (`app/pedidos/leitura/identificador.py`):
- `IdentificadorDocumento` identifica rede=QPA via CNPJ emitente + header Consinco.
- Chamado antes de escolher o extractor correto.

**Parser determinístico** (`services/parsers/qpa_pedido_extractor.py`):
- Subclasse de `app.pedidos.leitura.base.PDFExtractor`.
- Cada página = 1 loja Sendas; layout Consinco com header `LJ<n>` + tabela de produtos.
- Regex principal: `REGEX_PRODUTO = r'^(\d{7})\s*([A-ZÀ-Ÿ0-9 ]+?)\s+UN\s+1\s+([\d\.,]+)\s+...'`
- PDF canônico: 38 páginas × 3 modelos = 114 itens.

**Fallback LLM** (`services/parsers/qpa_pedido_llm_fallback.py`):
- Acionado quando `confianca < CONFIANCA_LIMIAR` ou zero itens extraídos.
- Escalada: Haiku 4.5 (`claude-haiku-4-5-20251001`) → Sonnet 4.6 (`claude-sonnet-4-6`).
- Anthropic SDK 0.98.1, lazy init (não constrói cliente se não acionado).

**Confiança** — DOIS momentos (corrigido em 2026-06-18, ver seção
"Fix parser zero-padding + edição manual" abaixo):
- **Gate do LLM fallback** (pré-persistência, `_calcular_confianca`):
  `lojas_distintas_extraidas / total_paginas`. Se `< CONFIANCA_LIMIAR = 0.70` →
  aciona LLM. Mede só o que o extractor LEU.
- **Confiança GRAVADA** (pós-persistência): `lojas_gravadas / lojas_no_documento`.
  Reflete o que de fato entrou no banco — não esconde lojas perdidas no match.

---

### `modelo_resolver` — service COMPARTILHADO

`app/motos_assai/services/modelo_resolver.py` — usado por TODOS os parsers (pedido, recibo futuro, NF QPA futura).

3 camadas de match (primeiro que bate retorna):
1. Código exato: `assai_modelo.codigo` (ex: `'X11_MINI'`, `'DOT'`, `'SOL'`).
2. Alias: `assai_modelo_alias.alias` case-insensitive, qualquer `ALIAS_TIPO_*`.
3. Substring: `assai_modelo.descricao_qpa` (ilike).

Retorna `AssaiModelo | None` — caller decide criar pendência ou pular item.
Função de conveniência: `resolver_por_codigo_qpa(codigo_str)` para lookup direto por código QPA.

---

### Fluxo Pedido VOE → Compra Motochefe

```
1 PDF VOE Q.P.A.  →  N páginas  →  N itens (loja × modelo)
                                           ↓
                              assai_pedido_venda (status ABERTO)
                              assai_pedido_venda_item (1 por loja×modelo)
                                           ↓  (consolidação N→1)
                              assai_compra_motochefe (status ABERTA, nº MA-AAAA-NNNN)
                              assai_compra_motochefe_pedido (N:N)
                              pedidos → status ABERTO (mantido — Big Bang Task 19 2026-05-13
                                          removeu EM_PRODUCAO; status muda apenas com NF Q.P.A.)
                                           ↓
                              PDF do PO gerado via WeasyPrint
                              (template: templates/motos_assai/compras/pdf_template.html)
```

**Rotas adicionadas (blueprint `/motos-assai`)**:
- `GET/POST /pedidos/upload` — upload PDF VOE, extração, resultado
- `GET /pedidos/<id>` — detalhe com totais e accordion por loja
- `GET /pedidos` — lista com filtro de status
- `GET/POST /compras/nova` — multi-select pedidos + preview totalizadores
- `GET /compras/<id>` — detalhe da compra consolidada
- `GET /compras/<id>/pdf` — download do PO em PDF
- `GET /compras` — lista de compras

---

## Plano 4 implementado (2026-05-07)

### Pipeline de saída (ESTOQUE → MONTADA/PENDENTE → DISPONIVEL → SEPARADA → FATURADA)

**Montagem** (`montagem_service`):
- ESTOQUE → MONTADA (caminho feliz) ou ESTOQUE → PENDENTE (com descrição obrigatória)
- PENDENTE → PENDENCIA_RESOLVIDA → MONTADA efetivo (via `resolver_pendencia()`)
- Tela rápida `/motos-assai/montagem` com input QR/manual (operação de chão de fábrica)
- Histórico 3 últimas ações exibido em `partials/_historico_3_ultimas.html`

**Disponibilizar** (`disponibilizar_service`):
- MONTADA ou REVERTIDA_PARA_MONTADA → DISPONIVEL
- Reverter: DISPONIVEL → REVERTIDA_PARA_MONTADA (motivo ≥ 3 chars obrigatório)
- Tela rápida `/motos-assai/disponibilizar` com modal motivo + reload pós-reverter

**Separação** (`separacao_service`):
- Fungível por modelo: chassi DISPONIVEL atende qualquer saldo do mesmo modelo
- UNIQUE parcial em chassi (status != CANCELADA) — race condition retorna 409
- Cancelar emite evento DISPONIVEL para cada chassi (volta direto, sem passar por MONTADA)
- Tela `/motos-assai/separacao` e `/motos-assai/pedidos/<pid>/separar/<lid>` com saldo visual em barras

**Excel Q.P.A.** (`faturamento_service.gerar_excel_qpa`):
- Espelha `285.xlsx` — 2 abas (PEDIDO + BASE LOJAS) geradas por openpyxl
- Persiste em `motos_assai/solicitacoes/` no S3
- Atualiza `assai_separacao.solicitacao_excel_s3_key`

**Importação de NF Q.P.A.** (`parsers/nf_qpa_adapter.py`):
- Adapter sobre `app.carvia.services.parsers.danfe_pdf_parser.DanfePDFParser` — zero modificações ao módulo CarVia
- Extrai loja_id de `nome_destinatario` via regex `LJ\d+`
- Match BATEU / DIVERGENTE / NAO_RECONCILIADO com tolerância 1% no valor unitário
- Quando BATEU: separação → status FATURADA; cada chassi emite evento FATURADA
- **`criar_nf_qpa_de_dados(dados, operador_id)`** (2026-06-20): grava NF Q.P.A. a partir de dados ESTRUTURADOS (sem PDF) reusando o mesmo pós-match (`_finalizar_match_nf`). Usado pela skill `corrigindo-dados-assai` (`--registrar-nf-manual`) p/ faturamento histórico sem PDF. `importar_nf_qpa` (PDF) permanece intocado. Lastro = a própria NF (nunca FATURADA órfã).

**Upload em lote (2026-05-12)** — `UploadNfQpaForm.pdfs` (`MultipleFileField`):
- Variante global `/motos-assai/faturamento/upload-nf` aceita 1 ou N PDFs.
- 1 PDF + sucesso → redirect detalhe (UX antiga preservada).
- 1 PDF + erro → flash + re-render upload.
- N PDFs → `upload_nf_resultado.html` com tabela arquivo|status|NF|match|erro + resumo (total/ok/duplicada/erro_parse/**falha**). Uma exceção INESPERADA num arquivo (além de `NfQpaParseError`/`NfQpaJaImportadaError`) **não aborta o lote**: `db.session.rollback()` + status `falha` no relatório e segue para o próximo. Antes o lote inteiro caía em 500 e os arquivos seguintes sumiam sem rastro (`importar_nf_qpa` commita por arquivo → data loss silencioso).
- Acesso: botão "Importar NFs em lote" no header de `lista_separacoes.html` (tela Faturamento).
- Botão "Upload NF" por-linha (variante per-separação) também continua aceitando N PDFs.

**SOL no CarVia** (`scripts/migrations/motos_assai_06_carvia_modelo_sol.py`):
- Seed idempotente que adiciona `CarviaModeloMoto(nome='SOL')` para o parser DANFE reconhecer modelo SOL

---

## Plano 5 implementado (2026-05-12) — Integração lista_pedidos.html

Integra a Op. Assaí ao fluxo Nacom de pedidos (lista_pedidos → cotação → embarque → frete)
via 4 campos de agendamento + planejamento de qtd por modelo + realocação de saldo.

### Novos modelos (2 tabelas)

**`AssaiPedidoVendaLoja`** (`models/pedido.py`) — cabeçalho por (pedido, loja):
- `expedicao` (Date), `agendamento` (Date), `protocolo` (String 50),
  `agendamento_confirmado` (Boolean default False).
- UNIQUE (pedido_id, loja_id).
- `AssaiPedidoVendaItem.pedido_loja_id` FK aponta para cá → propagação automática
  dos 4 campos para todos os itens da mesma loja no pedido.
- Migration 10 (`motos_assai_10_pedido_venda_loja.sql/py`) com backfill 1 cabeçalho
  por (pedido_id, loja_id) distinto. Itens existentes recebem FK via backfill.

**`AssaiSeparacaoSaldoModelo`** (`models/separacao.py`) — placeholder de qtd planejada:
- `separacao_id`, `modelo_id`, `qtd_planejada` (Integer > 0).
- UNIQUE (separacao_id, modelo_id).
- Criado quando operador usa checkbox+qtd para "Criar separação". Não bloqueia
  escaneio livre (decisão 2026-05-12: realidade prevalece — chassi efetivo pode
  divergir do plano por variações de carregamento).
- Migration 12 (`motos_assai_12_separacao_saldo_modelo.sql/py`).

### `AssaiSeparacao` ganhou 4 campos override

Mesmos 4 nomes do cabeçalho da loja: `expedicao/agendamento/protocolo/agendamento_confirmado`.
NULL = herda do `AssaiPedidoVendaLoja` correspondente via (pedido_id, loja_id).
Migration 11 (`motos_assai_11_separacao_4campos.sql/py`).

### Mudança crítica: N separações por (pedido, loja)

UNIQUE `ux_assai_separacao_pedido_loja_ativa` (Migration 01) bloqueava 2 separações
ativas no mesmo (pedido, loja). Migration 13 (`motos_assai_13_drop_unique_em_separacao`)
removeu esse UNIQUE — agora N separações EM_SEPARACAO simultâneas são permitidas
(regra: "separações = veículos de carregamento; 2+ veículos podem carregar paralelamente").

Concorrência de chassi continua protegida via:
1. `with_for_update` em `AssaiMoto` (lock pessimista por chassi)
2. Validação `status_atual(chassi) == DISPONIVEL` antes de SEPARADA

Side effect: `get_separacao_ativa` pode retornar QUALQUER sep EM_SEPARACAO (não
há mais "a única"). Rota `/separar/<pid>/<lid>` aceita `?sep_id=N` para target
explícito (links da UI passam sep_id).

**Atualizado 2026-05-12 (Migration 17 / item 3 corretivo)**: a função antiga
`get_ou_criar_separacao` foi renomeada para `get_separacao_ativa` e perdeu o
side effect de criar separação implicitamente quando não havia nenhuma. Bug
reportado em prod: cada navegação para `/pedidos/<pid>/separar/<lid>` sem
`?sep_id` criava sep fantasma no banco. Agora, quando não há sep ativa,
`separacao_tela` redireciona para `pedidos_detalhe` com flash orientativo —
operador deve criar via checkbox+qtd (que chama `criar_separacao_com_saldos`).

### Espelhamento Nacom — fallback dos 4 campos

`separacao_mirror_service._resolver_4_campos(sep, pvl)`:
1. `AssaiSeparacao.{campo}` (override por separação) se preenchido
2. `AssaiPedidoVendaLoja.{campo}` (cabeçalho) se existe
3. None / False (default)

`agendamento_confirmado` usa semântica OR — confirmado em qualquer nível propaga True.

`propagar_4_campos_para_espelho(assai_sep_id)` re-aplica nos espelhos quando os
campos forem editados pós-FECHADA (operador altera agendamento depois da sep
já estar refletida em `separacao` Nacom).

### Fluxo de finalização com saldo planejado

`separacao_service.analisar_finalizacao(sep_id)` classifica o cenário:
- **`sem_saldo`**: qtd_escaneada == qtd_planejada por modelo. Finaliza direto.
- **`caso_a`**: há saldo mas não há outra sep EM_SEPARACAO no (pedido, loja).
- **`caso_b`**: há saldo E há 1+ outras seps EM_SEPARACAO no mesmo (pedido, loja).

`finalizar_separacao_com_decisao(sep_id, operador_id, *, modo, alocacoes)` aceita modos:
- `'auto'` (default): se sem_saldo, finaliza. Se há saldo, levanta `SeparacaoSaldoPendenteError(plano)`
  — UI captura e mostra modal apropriado.
- `'voltar_saldo'` (Caso A op1): `qtd_planejada` reduz para `qtd_escaneada`.
  Saldo retorna a `saldo_pendente_por_modelo()` (disponível para nova sep).
- `'manter_planejado'` (Caso A op2): `qtd_planejada` mantida. Sep fecha com
  divergência. **NF Q.P.A. ajusta posteriormente.**
- `'realocar'` (Caso B): `realocar_saldo(sep_origem_id, alocacoes, operador_id)`.
  Cada alocação: `{sep_destino_id: int|None, modelo_id, qtd}`. `sep_destino_id=None`
  = voltar ao pedido. Soma deve == saldo.

### Ajuste pós-NF (NF é fonte de verdade)

`separacao_service.ajustar_separacao_pela_nf(nf_id, operador_id)`:
- Pré-condição: TODOS os chassis da NF devem existir em `assai_moto`. Se algum
  não existe, retorna ok=False sem mutar estado.
- Sep alvo: AssaiSeparacao com mais chassis em comum (mesma loja, status não-CANCELADA/FATURADA).
- Para cada chassi da NF:
  - Já está na sep alvo → OK
  - Em outra sep ativa → MOVE (delete antiga, create na alvo)
  - Em outro estado (DISPONIVEL/MONTADA/...) → ADD na sep alvo + emite SEPARADA
- Para cada chassi na sep alvo que NÃO veio na NF → REMOVE + emite DISPONIVEL.

`nf_qpa_adapter.importar_nf_qpa` chama `ajustar_separacao_pela_nf` ANTES de
`_calcular_match`. Após ajuste, match natural detecta BATEU.

### Novas rotas (blueprint `/motos-assai`)

- `GET /pedidos/<pid>` — detalhe agora mostra agendamento por loja + tabela com
  checkbox+qtd para criar separação + lista de seps ativas (acesso por `?sep_id=`)
- `POST /pedidos/<pid>/loja/<lid>/agendamento` — atualiza 4 campos do cabeçalho.
  Propaga para espelhos FECHADOS via `propagar_4_campos_para_espelho`.
- `POST /pedidos/<pid>/loja/<lid>/separacao/criar` — cria nova `AssaiSeparacao`
  EM_SEPARACAO + N `AssaiSeparacaoSaldoModelo`. Retorna sep_id + redirect.
- `GET /separacao/<sep_id>/analisar-finalizacao` — retorna plano para UI (read-only).
- `POST /separacao/<sep_id>/finalizar` (modificado) — aceita body `{modo, alocacoes}`.
  Retorna 409 `requer_decisao=true` quando modo=auto e há saldo.

### Endpoints retrocompatíveis (sem `?sep_id`)

`/pedidos/<pid>/separar/<lid>` (tela de escaneio) sem `?sep_id` busca a primeira
EM_SEPARACAO via `get_separacao_ativa`. **Se NÃO houver nenhuma sep ativa,
redireciona para `pedidos_detalhe` com flash orientativo** (antes criava sep
fantasma — bug corrigido em 2026-05-12, ver Migration 17).

UI deve passar `?sep_id=N` explicitamente:
- `separacao/lista.html`: linha com sep EM_SEPARACAO → `?sep_id={{ s.id }}`;
  outras (FECHADA/CANCELADA/FATURADA) → link para `pedidos_detalhe` (sem tela
  de escaneio).
- `separacao/nova.html`: "Continuar" → `?sep_id={{ p.separacao_ativa_id }}`;
  "Iniciar" → `pedidos_detalhe#loja-{{ p.loja_id }}` (fluxo via checkbox+qtd).
- `pedidos/detalhe.html`: sempre `?sep_id={{ s.id }}` em cada sep ativa listada.

### Telas rápidas

| Tela | URL | Descrição |
|------|-----|-----------|
| Montagem rápida | `/motos-assai/montagem` | QR/manual → ESTOQUE→MONTADA/PENDENTE |
| Disponibilizar rápido | `/motos-assai/disponibilizar` | QR/manual → MONTADA→DISPONIVEL |
| Separação lista | `/motos-assai/separacao` | Lista separações em andamento |
| Faturamento lista | `/motos-assai/faturamento` | Separações prontas para faturar |
| Upload NF Q.P.A. | `/motos-assai/faturamento/upload-nf` | Importação DANFE PDF + match |

### Endpoints adicionados (Plano 4)

- `GET /motos-assai/montagem` + `POST /motos-assai/montagem/registrar`
- `GET /motos-assai/disponibilizar` + `POST /motos-assai/disponibilizar/registrar` + `POST /motos-assai/disponibilizar/reverter`
- `GET /motos-assai/separacao` + `GET /motos-assai/pedidos/<pid>/separar/<lid>`
- `POST /motos-assai/separacao/registrar-chassi`
- `POST /motos-assai/separacao/desfazer/<item_id>`
- `POST /motos-assai/separacao/<id>/finalizar`
- `POST /motos-assai/separacao/<id>/cancelar`
- `GET /motos-assai/faturamento` (lista separações)
- `GET /motos-assai/faturamento/separacao/<id>/excel` (download Excel Q.P.A.)
- `GET/POST /motos-assai/faturamento/separacao/<id>/upload-nf` (upload NF por separação)
- `GET/POST /motos-assai/faturamento/upload-nf` (upload NF global)
- `GET /motos-assai/faturamento/nfs/<id>` (detalhe + match BATEU/DIVERGENTE)

### Estados de evento finais (Plano 4)

Os seguintes tipos de evento em `assai_moto_evento` foram ativados neste plano:
- `SEPARADA` — chassi vinculado a separação ativa (não conta como estoque disponível)
- `FATURADA` — NF Q.P.A. importada e match BATEU (saída definitiva)
- `CANCELADA` — separação cancelada (chassi retorna como DISPONIVEL via novo evento)
- `MOTO_FALTANDO` — declarada no recibo mas não chegou fisicamente (implementado no Plano 3)
- `REVERTIDA_PARA_MONTADA` — operador reverteu disponibilização (implementado no Plano 4)

---

## Módulo completo — visão geral arquitetural

- **29 tabelas** com prefixo `assai_` (ver secao "Modelo de dados (29 tabelas)" acima; a spec inicial `docs/superpowers/specs/2026-05-07-motos-assai-design.md` descreve as 16 tabelas da fundacao, expandidas pelos Planos 2-5)
- **Toggle master** `sistema_motos_assai` em `usuarios` → decorator `@require_motos_assai`
- **9 etapas do pipeline** implementadas (ESTOQUE → MONTADA → DISPONIVEL → SEPARADA → FATURADA)
- **Parsers determinísticos** com fallback LLM (Haiku 4.5 → Sonnet 4.6) em PDFs e Excel
- **Wizard QR/Barcode** adaptado de Hora (`html5-qrcode@2.3.8`) — reutilizado em recebimento/montagem/disponibilizar
- **Reuso CarVia** DANFE parser via adapter (zero modificação ao módulo CarVia)
- **Concorrência** controlada por UNIQUE parcial + `with_for_update` + IntegrityError → 409

---

## Skills + Agente disponíveis

Para consultas e operações via Claude Code ou agente web Nacom Goya:

| Skill | Tipo | Uso |
|-------|------|-----|
| `consultando-estoque-assai` | READ | Pipeline (ESTOQUE/MONTADA/DISPONIVEL/SEPARADA/FATURADA) |
| `rastreando-chassi-assai` | READ | Histórico completo de um chassi |
| `acompanhando-pedido-compra-assai` | READ | Pedidos VOE Q.P.A. + compras Motochefe |
| `acompanhando-saida-assai` | READ | Separações + NFs Q.P.A. (match BATEU/DIVERGENTE) |
| `conferindo-recibo-assai` | READ + WRITE | Recibos Motochefe + wizard A→B→C→D |
| `registrando-evento-moto-assai` | WRITE | Montagem, disponibilizar, separar, reverter, cancelar (pontual, 1 chassi, agora) |
| `carregando-motos-assai` | READ + WRITE | Carregamento (Sep→NF): listar/detalhar + iniciar/escanear/finalizar/cancelar/alterar |
| `corrigindo-dados-assai` | WRITE | **Backfill / correção manual**: carga em lote (planilha Excel), eventos com data retroativa, cadastros (loja/modelo), item de pedido ABERTO, gravar faturamento (NF Q.P.A.), alterar chassi em NF e registrar devolução (NFd, `--registrar-devolucao-nfd` → FATURADA→PENDENTE via `devolucao_service`). Traz o mapa do módulo (`references/MAPA_MODULO.md`) p/ o agente escrever scripts ad-hoc. Dry-run + `--confirmar`. |

Agente orquestrador: `gestor-motos-assai` (sub-agent — `model: sonnet`).

Spec: `docs/superpowers/specs/2026-05-08-motos-assai-skills-agents-design.md`
Plan: `docs/superpowers/plans/2026-05-08-motos-assai-skills-agents.md`

---

## Manutenção / Roadmap futuro

Planos 1-5 completos (2026-05-12). Evoluções futuras:

- `assai_avaria` — tabela para avarias detectadas pós-recebimento (acréscimo ao wizard)
- Permissões granulares (`assai_user_permissao`) — atualmente toggle único
- Múltiplos CDs — transferência inter-CD
- Modelo MIA — atualmente fora do escopo
- Automação envio Excel à Q.P.A. via SMTP
- Resolver pendência via UI (atualmente só via service diretamente)
- Skills atualizadas com novos campos (agendamento por loja + plano por modelo)

---

## CCe como entidade (2026-05-13)

A Carta de Correção Eletrônica agora é uma entidade própria (tabela `assai_cce`)
com ciclo de vida, em vez de apenas trigger de mutação numa divergência.

### Por que esse design

**Cenário motivador**: a CCe pode chegar ANTES da NF correspondente (ex: operador
recebeu CCe por e-mail antes do XML/PDF da NF ser importado). O modelo antigo
exigia divergência aberta → bloqueava importação fora de ordem.

### Modelo `AssaiCce` (Migration 28)

| Campo | Tipo | Função |
|-------|------|--------|
| `protocolo_cce` | str UNIQUE | Identidade SEFAZ — idempotência |
| `chave_nfe` | str(44) | Match preferencial com `AssaiNfQpa.chave_44` |
| `numero_nf_referenciada` | str | Match fallback com `AssaiNfQpa.numero` |
| `sequencia_cce` | int | Sequência (uma NF pode ter N CCes) |
| `tipo_correcao` | str | `CHASSI` / `DUPLICATAS` / `ENDERECO` / `OUTRO` |
| `dados_parsed` | JSONB | Dump completo do parser (chassis_detalhes, duplicatas...) |
| `tem_nf` | bool | False = NF ainda não chegou (query de match reverso) |
| `nf_id` | FK NULLABLE | NF vinculada (preenchido quando aplica) |
| `status` | str | `PENDENTE` / `APLICADA` / `IGNORADA` / `ERRO` |
| `pdf_s3_key` | str | PDF original em S3 |
| `divergencia_origem_id` | FK NULLABLE | Se veio do botão CCe em divergência |
| `chassis_aplicados` | JSONB | Auditoria do que foi efetivamente trocado |

### Cenários cobertos (3 entradas)

1. **CCe avulsa sem NF** (`POST /motos-assai/cce/upload` + NF não existe)
   → Status `PENDENTE`, `tem_nf=False`. Aguarda NF chegar.

2. **CCe avulsa com NF presente** (`POST /motos-assai/cce/upload` + NF já importada)
   → Aplica imediato. Status `APLICADA`, `tem_nf=True`, chassis trocados.

3. **CCe via divergência** (`POST /motos-assai/divergencias/<div_id>/upload-cce`)
   → Aplica + fecha divergência (tipo=CCE). Mesmo `cce_service.registrar_cce`,
   só passa `divergencia_id=div_id`.

### Match reverso ao importar NF

`nf_qpa_adapter.importar_nf_qpa()` chama `aplicar_cce_pendentes_para_nf(nf, operador_id)`
APÓS `_calcular_match` e ANTES do commit final. Query:

```sql
SELECT * FROM assai_cce
WHERE tem_nf = false
  AND status = 'PENDENTE'
  AND (chave_nfe = :chave_44
       OR numero_nf_referenciada IN (:numero, :numero_lstripped))
```

Para cada CCe casada, chama `_tentar_aplicar_cce` → `aplicar_correcao_cce` →
re-roda `_calcular_match`. Side effect: divergências podem ser criadas
naturalmente se troca de chassi não bater com separação atual.

### Tipo `IGNORADA` (DUPLICATAS / ENDERECO)

CCes de duplicatas ou endereço **são registradas para auditoria** mas:
- Não alteram chassis (não há chassis nelas)
- Status = `IGNORADA`
- Mensagem orienta operador a fazer correção manual no financeiro / cadastro

### Idempotência

UNIQUE em `protocolo_cce`. Re-upload do mesmo PDF retorna o registro existente
(`duplicada=True` no resultado). Garante que job/operador pode re-tentar sem
duplicar dados.

### Rotas (`/motos-assai/cce/*`)

- `GET /cce` — lista com filtros (status, tipo, tem_nf, busca textual)
- `GET /cce/upload` — formulário
- `POST /cce/upload` — processa 1+ PDFs em lote
- `GET /cce/<id>` — detalhe (com painel "aplicar agora" se NF chegou depois)
- `POST /cce/<id>/tentar-aplicar` — re-tenta CCe em status PENDENTE/ERRO

### Arquivos

- `app/motos_assai/models/cce.py` — `AssaiCce` + constantes `CCE_STATUS_*`
- `app/motos_assai/services/cce_service.py` — orquestrador: `registrar_cce`,
  `aplicar_cce_pendentes_para_nf`, `_tentar_aplicar_cce`, `_resolver_nf_da_cce`
- `app/motos_assai/services/parsers/cce_pdf_extractor.py` — parser determinístico
  (formatos Q.P.A. RELATÓRIO + MOTOCHEFE Dados, 4 subtipos)
- `app/motos_assai/services/parsers/cce_llm_fallback.py` — Haiku → Sonnet
- `app/motos_assai/routes/cce.py` — 4 rotas
- `app/templates/motos_assai/cce/{lista,upload,upload_resultado,detalhe}.html`
- `scripts/migrations/motos_assai_28_cce_entidade.{sql,py}`
- `tests/motos_assai/test_cce_service.py` — 5 cenários cobertos
- `tests/motos_assai/test_parser_cce.py` — 12 testes (formatos Q.P.A. + Motochefe + edge cases)

### Gotchas

- **Match por número da NF**: AssaiNfQpa.numero é salvo SEM zeros à esquerda
  (lstrip). O parser também normaliza. Match testa ambas formas.
- **MOTOCHEFE não tem protocolo SEFAZ**: `cce_service.registrar_cce` gera
  pseudo-protocolo `PSEUDO-<chave>-<seq>` para manter idempotência.
- **DUPLICATAS/ENDERECO ficam IGNORADA mesmo com NF presente**: vincula nf_id
  para auditoria, mas não tenta trocar chassis (não há).
- **Re-importação após NF cancelada**: CCe não aplica em NF status `CANCELADA`
  (fica status `ERRO` com observação clara).
- **Double `_calcular_match` no match reverso**: `importar_nf_qpa` chama
  `_calcular_match` antes de `aplicar_cce_pendentes_para_nf`. Para cada CCe
  pendente, `aplicar_correcao_cce` re-roda `_calcular_match` após trocar
  chassis. Isto NÃO duplica `FATURADA` no mesmo chassi (são chassis diferentes
  — antigo e novo) e `aplicar_correcao_cce` reverte explicitamente o antigo.
  Side effect: divergências criadas na primeira passagem para chassis que
  serão corrigidos pela CCe ficam abertas (já apontam para chassi antigo que
  saiu da NF). Re-rodar match não as fecha — operador resolve manualmente
  ou ignora.
- **Race condition em `registrar_cce`**: tratada via `IntegrityError`
  fallback (busca registro existente). PDF S3 órfão é deletado (fix C1).
- **Retry de CCe APLICADA com status resetado manualmente**: bloqueado
  via guard `cce.chassis_aplicados` no route `/cce/<id>/tentar-aplicar`
  (fix H3). Evita double-swap de chassis.
- **Falha de uma CCe não contamina match reverso**: `aplicar_cce_pendentes_para_nf`
  usa savepoint por CCe (fix H4). Erro em uma CCe específica não impede a NF
  principal de commitar nem outras CCes pendentes de serem aplicadas.

---

## Onboarding Tours (2026-05-08)

Tours guiados in-app via Driver.js para usuarios novos.

**Spec:** `docs/superpowers/specs/2026-05-08-onboarding-tours-hora-assai-design.md`
**Plano:** `docs/superpowers/plans/2026-05-08-onboarding-tours-hora-assai.md`

**Estrutura:**
- 1 macro (`motos_assai.macro`) com 8 passos (3 com `adminOnly`)
- 9 mini-tours em `app/static/onboarding/tours/motos_assai/`
- Filtragem: 4 universais + 5 admin-only (toggle via `current_user.perfil == 'administrador'`)
- Quando o modulo ganhar permissoes granulares (roadmap), trocar `adminOnly` por `requirePerm` no engine — sem refactor

**Adicionar tour novo:**
1. Criar `app/static/onboarding/tours/motos_assai/<nome>.js` (com `adminOnly: true` se for admin)
2. Adicionar IDs nos elementos do template alvo
3. Incluir no `{% block onboarding_tours %}` do template
4. **OBRIGATORIO**: incluir `<script>` em `app/templates/admin/onboarding_health.html` E `onboarding_preview.html`. Sem isso o tour nao aparece nas paginas admin
5. Validar em `/admin/onboarding/health`
6. Preview em `/admin/onboarding/preview?tour=motos_assai.<nome>`

**Mobile-first:** tours das telas de chao (recebimento wizard, montagem, disponibilizar, separacao) estao otimizados para celular do operador.

---

## Fix parser zero-padding + edição manual (2026-06-18)

Origem: **IMP-2026-06-18-001/-003/-004** (sessões da usuária Rayssa). O parser
VOE cortou 3 das 9 lojas do pedido `21589890/L` gravando `parsing_confianca=1.00`
(silent data loss).

**Causa-raiz** (NÃO era offset/header-skip como hipotetizado): mismatch de
zero-padding. O PDF Consinco traz `LJ14` → regex extrai `"14"`; o cadastro
`assai_loja.numero` é **inconsistente** (algumas lojas `"12"`, outras `"014"`).
O match exato `filter_by(numero="14")` perdia em silêncio toda loja zero-padded.
A "perda do início" foi coincidência: o PDF vem ordenado por número.

**Correções** (`pedido_service.py`):
1. `_resolver_loja` / `_variantes_numero_loja` — match TOLERANTE a zero-padding
   (exato → variantes `lstrip`/`zfill(2|3)`; >1 candidato = ambíguo → None).
2. Confiança GRAVADA recalculada pós-persistência (ver "Confiança" no Plano 2).
3. `assai_pedido_venda.import_resumo` (JSONB, **Migration 32**) registra
   `lojas_extraidas/gravadas`, `itens_extraidos/gravados` e lista de `pulados`
   — exibido como alerta em `pedidos/detalhe.html` e flash no upload.
   ⚠️ A Migration 32 **NÃO consta no build.sh**: foi aplicada manualmente em
   prod via `DATABASE_URL_PROD` (e no schema JSON via `generate_schemas.py`); os
   arquivos `scripts/migrations/motos_assai_32_*` ficam só como registro do DDL.

**Edição manual** (IMP-003/-004 — fallback do parser, só em pedido `ABERTO`):
- Service: `adicionar_item_manual` / `editar_item_manual` / `remover_item_manual`
  (+ `PedidoVoeEdicaoError`). Remoção bloqueada se a loja tem separação ativa.
  `import_resumo.editado_manual=True` marca auditoria.
- Rotas: `POST /pedidos/<id>/itens/adicionar|<item_id>/editar|<item_id>/remover`
  (form POST + redirect). Seção colapsável em `pedidos/detalhe.html`.
- Testes: `tests/motos_assai/test_pedido_fix_e_edicao.py` (9 casos).

> **Higiene pendente**: padronizar `assai_loja.numero` (014→14 etc.). Com o match
> tolerante deixou de ser bloqueante, mas a inconsistência segue no cadastro.

---

## Guards de import de NF Q.P.A. (2026-06-23)

Origem: **IMP-2026-06-23-002/-004/-008** (carga histórica da Rayssa). O upload de
PDF de NF Q.P.A. (`routes/faturamento.py:faturamento_upload_nf` →
`services/parsers/nf_qpa_adapter.py:importar_nf_qpa`) ganhou 3 guards cirúrgicos
para parar a perda silenciosa de dados:

1. **Porteiro CCe-vs-NF** (IMP-008): `cce_pdf_extractor.eh_documento_cce(pdf_bytes)`
   detecta, pelos marcadores de formato (`RE_FORMATO_QPA`/`RE_FORMATO_MOTOCHEFE`),
   um PDF de Carta de Correção enviado ao endpoint de NF. `importar_nf_qpa` rejeita
   com `NfQpaDocumentoCceError` (subclasse de `NfQpaParseError` — o loop em lote
   nunca perde o arquivo) **antes** de construir o parser/LLM; a rota mostra status
   `documento_errado` orientando a usar a tela de CCe.
2. **Fail-loud de completude** (IMP-004): `_validar_completude_chassis(resultado)`
   roda após validar chave/duplicata e **antes** de qualquer escrita. Levanta
   `NfQpaParseError` se 0 chassis ou se `len(veiculos) < qtd_declarada_itens_veiculo`
   (o gabarito NCM 8711 que o parser já calcula) — espelha o guard que já existia no
   caminho de dados estruturados (`criar_nf_qpa_de_dados`). Modelos SOL (chassi
   puro-numérico) que o parser perde por layout deixam de gravar NF incompleta em
   silêncio.
3. **Cap + liberação de memória no lote** (IMP-002): `forms/faturamento_forms.py`
   limita `MAX_PDFS_POR_UPLOAD=25` por request (upload é síncrono: pdfplumber + até
   3 LLM/arquivo + S3, sem worker RQ); a rota libera memória entre arquivos
   (`f.close()` + `gc.collect()`); `danfe_pdf_parser._extrair_com_pdfplumber` passou
   a usar `with pdfplumber.open(...)` (liberava o handle só no happy path).

Testes: `tests/motos_assai/test_nf_qpa_import_guards.py` (10 casos).

> **Pendente (não coberto aqui — exige sessão dev)**: o blocker crítico IMP-23-005
> (faturar ~100 NFs históricas em `NAO_RECONCILIADO` sem separação viva — o
> *double-match trap* em `nf_qpa_adapter._calcular_match` que exclui seps FATURADA
> do JOIN, desfazendo o S1=b) e o parser de CCe que classifica "correção de pedido"
> como CHASSI / perde SOL (IMP-23-009) seguem ABERTOS.

---

## Referências

- Spec: `docs/superpowers/specs/2026-05-07-motos-assai-design.md`
- Plano 1: `docs/superpowers/plans/2026-05-07-motos-assai-foundation.md`
- Plano 2: `docs/superpowers/plans/2026-05-07-motos-assai-pedido-compra.md`
- Plano 3: `docs/superpowers/plans/2026-05-07-motos-assai-recibo-recebimento.md`
- Plano 4: `docs/superpowers/plans/2026-05-07-motos-assai-saida-polish.md`
- Plano fase 1 (fundacao): `docs/superpowers/plans/2026-05-12-motos-assai-fase1-fundacao.md`
- Plano fase 2-3 (carregamento): `docs/superpowers/plans/2026-05-12-motos-assai-fase2-3-carregamento.md`
- Plano fase 4 (NF + divergencias): `docs/superpowers/plans/2026-05-12-motos-assai-fase4-nf-divergencias.md`
- Plano fase 5 (auxiliares): `docs/superpowers/plans/2026-05-12-motos-assai-fase5-auxiliares.md`
- Padrão arquitetural de referência: `app/hora/CLAUDE.md`
- Identificador de documento (rede QPA): `app/pedidos/leitura/identificador.py`
- Parser base de PDF: `app/pedidos/leitura/base.py:PDFExtractor`
- Parser DANFE Q.P.A. (CarVia, adapter sem modificar): `app/carvia/services/parsers/danfe_pdf_parser.py`
- Adapter NF Q.P.A.: `app/motos_assai/services/parsers/nf_qpa_adapter.py`
- Wizard QR de referência: `app/templates/hora/recebimento_wizard.html`
- JS operação rápida (montagem/disponibilizar): `app/static/motos_assai/js/operacao_quick.js`
- JS separação: `app/static/motos_assai/js/separacao_chassi.js`
