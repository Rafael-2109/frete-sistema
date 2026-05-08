# Módulo Motos Assaí

**Data**: 2026-05-07
**Status**: Foundation + Cadastros (Plano 1) + Parser VOE + Pedido + Compra (Plano 2) + Recibo Motochefe + Recebimento físico (Plano 3) implementados.
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

## Próximos passos

- **Plano 4**: separação + disponibilização, Excel Q.P.A. (saída), importação de NF Q.P.A. + match, polish.

---

## Referências

- Spec: `docs/superpowers/specs/2026-05-07-motos-assai-design.md`
- Plano 1: `docs/superpowers/plans/2026-05-07-motos-assai-foundation.md`
- Plano 2: `docs/superpowers/plans/2026-05-07-motos-assai-pedido-compra.md`
- Plano 3: `docs/superpowers/plans/2026-05-07-motos-assai-recibo-recebimento.md`
- Padrão arquitetural de referência: `app/hora/CLAUDE.md`
- Identificador de documento (rede QPA): `app/pedidos/leitura/identificador.py`
- Parser base de PDF: `app/pedidos/leitura/base.py:PDFExtractor`
- Parser DANFE Q.P.A. (CarVia, sem modificar): `app/carvia/services/parsers/danfe_pdf_parser.py`
- Wizard QR de referência: `app/templates/hora/recebimento_wizard.html`
