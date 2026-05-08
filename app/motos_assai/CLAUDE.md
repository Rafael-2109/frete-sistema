# Módulo Motos Assaí

**Data**: 2026-05-07
**Status**: Foundation + Cadastros (Plano 1) + Parser VOE + Pedido + Compra (Plano 2) + Recibo Motochefe + Recebimento físico (Plano 3) + Pipeline de saída completo (Plano 4) — TODOS implementados.
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

Todas as tabelas começam com `assai_`. 16 tabelas no schema atual.

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

---

## Modelo de dados (16 tabelas)

Ver spec em `docs/superpowers/specs/2026-05-07-motos-assai-design.md` §4.

Cadastros: `assai_cd`, `assai_loja`, `assai_modelo`, `assai_modelo_alias`.
Identidade: `assai_moto`, `assai_moto_evento`.
Pipeline: `assai_pedido_venda*`, `assai_compra_motochefe*`, `assai_recibo_motochefe*`.
Saída: `assai_separacao*`, `assai_nf_qpa*`.

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

## Plano 3 implementado (2026-05-07)

### Parsers de recibo Motochefe (PDF + XLSX + LLM)

- `MotochefeReciboPdfExtractor` (`services/parsers/motochefe_recibo_pdf_extractor.py`): pdfplumber + `extract_tables()` com lines strategy. Detecta colunas CHASSI/MOTOR/COR no header. Extrai data, equipe (HAROLDO SP), conferente, total declarado.
- `MotochefeReciboXlsxExtractor` (`services/parsers/motochefe_recibo_xlsx_extractor.py`): openpyxl `data_only=True`. Localiza header da tabela pela presença de células CHASSI.
- `motochefe_recibo_llm_fallback.py`: Haiku 4.5 → Sonnet 4.6. Aceita PDF (document block) ou XLSX serializado como texto.
- **Limiar de confiança**: `CONFIANCA_LIMIAR = 0.80` em `recibo_service`. Acionado quando `chassis_extraidos / total_declarado < 0.80`.

### chassi_validator e moto_evento_service

- `chassi_validator.py`: validação regex do chassi contra padrão configurado no `AssaiModelo.regex_chassi`. Não-bloqueante — retorna `{ok, motivo, regex_usado}`. Motivos: `MOTIVO_REGEX_INVALIDO`, `MOTIVO_MODELO_SEM_REGEX`, `MOTIVO_CHASSI_VAZIO`.
- `moto_evento_service.py`: helpers `emitir_evento(chassi, tipo, ...)`, `status_atual(chassi)`, `historico(chassi)`. Append-only — nunca DELETE.

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

**Confiança** (calculada em `pedido_service`):
```
confianca = lojas_distintas_extraidas / total_paginas
```
Limiar: `CONFIANCA_LIMIAR = 0.70` (em `pedido_service.py`).

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
                              pedidos → status EM_PRODUCAO
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

**SOL no CarVia** (`scripts/migrations/motos_assai_06_carvia_modelo_sol.py`):
- Seed idempotente que adiciona `CarviaModeloMoto(nome='SOL')` para o parser DANFE reconhecer modelo SOL

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

- **16 tabelas** com prefixo `assai_` (ver spec `docs/superpowers/specs/2026-05-07-motos-assai-design.md`)
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
| `registrando-evento-moto-assai` | WRITE | Montagem, disponibilizar, separar, reverter, cancelar |

Agente orquestrador: `gestor-motos-assai` (sub-agent — `model: sonnet`).

Spec: `docs/superpowers/specs/2026-05-08-motos-assai-skills-agents-design.md`
Plan: `docs/superpowers/plans/2026-05-08-motos-assai-skills-agents.md`

---

## Manutenção / Roadmap futuro

Módulo encerrado em 2026-05-07 (Planos 1-4 completos). Evoluções futuras:

- `assai_avaria` — tabela para avarias detectadas pós-recebimento (acréscimo ao wizard)
- Permissões granulares (`assai_user_permissao`) — atualmente toggle único
- Múltiplos CDs — transferência inter-CD
- Modelo MIA — atualmente fora do escopo
- Automação envio Excel à Q.P.A. via SMTP
- Resolver pendência via UI (atualmente só via service diretamente)

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
4. Validar em `/admin/onboarding/health`
5. Preview em `/admin/onboarding/preview?tour=motos_assai.<nome>`

**Mobile-first:** tours das telas de chao (recebimento wizard, montagem, disponibilizar, separacao) estao otimizados para celular do operador.

---

## Referências

- Spec: `docs/superpowers/specs/2026-05-07-motos-assai-design.md`
- Plano 1: `docs/superpowers/plans/2026-05-07-motos-assai-foundation.md`
- Plano 2: `docs/superpowers/plans/2026-05-07-motos-assai-pedido-compra.md`
- Plano 3: `docs/superpowers/plans/2026-05-07-motos-assai-recibo-recebimento.md`
- Plano 4: `docs/superpowers/plans/2026-05-07-motos-assai-saida-polish.md`
- Padrão arquitetural de referência: `app/hora/CLAUDE.md`
- Identificador de documento (rede QPA): `app/pedidos/leitura/identificador.py`
- Parser base de PDF: `app/pedidos/leitura/base.py:PDFExtractor`
- Parser DANFE Q.P.A. (CarVia, adapter sem modificar): `app/carvia/services/parsers/danfe_pdf_parser.py`
- Adapter NF Q.P.A.: `app/motos_assai/services/parsers/nf_qpa_adapter.py`
- Wizard QR de referência: `app/templates/hora/recebimento_wizard.html`
- JS operação rápida (montagem/disponibilizar): `app/static/motos_assai/js/operacao_quick.js`
- JS separação: `app/static/motos_assai/js/separacao_chassi.js`
