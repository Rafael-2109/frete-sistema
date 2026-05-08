# Módulo Motos Assaí — Design

**Data**: 2026-05-07
**Autor**: Rafael Nascimento (validado iterativamente com Claude)
**Status**: design aprovado pelo dono do produto, pronto para writing-plans
**Decisões aprovadas em 4 rounds de Q&A**: 7 de maio de 2026

---

## 1. Contexto e escopo

### 1.1 Operação

A Nacom Goya começou a vender motos elétricas para o cliente **Sendas Distribuidora (Assaí)** através da empresa **Q.P.A. Distribuição LTDA** (CNPJ `53.780.554/0001-15`). A operação é **isolada das demais** (Carteira de Pedidos Nacom, Lojas HORA Motochefe, CarVia transportadora).

A operação acontece em **um único CD** chamado **"Operação VOE"** (Voe X Sendas). Equipe operacional fixa.

### 1.2 Pipeline de 8 etapas (origem do design)

| # | Etapa | Documento de exemplo |
|---|-------|---------------------|
| 1 | Pedido VOE recebido da Sendas (1 PDF multi-loja, gerado pelo Consinco) | `pedido VOE 1 (1).pdf` — 38 páginas/lojas, 34 motos cada, R$ 225.600/loja |
| 2 | Pedido de compra emitido para a Motochefe, consolidando N pedidos VOE | (geramos no sistema) |
| 3 | Recibo da Motochefe entregue por carga (contra-prova de recebimento) | `HAROLDO SP 05.05 (1).pdf` — 115 motos DOT+MIA |
| 4 | Recebimento físico no CD via QR Code + código de barras + manual | (replica wizard Hora) |
| 5 | Montagem das motos: status `MONTADA` ou `PENDENTE` (peça com defeito) | — |
| 6 | Disponibilização: tag/manual colocados → `DISPONIVEL` | — |
| 7 | Separação: equipe vincula chassis disponíveis a um pedido por modelo | — |
| 8 | Faturamento: solicitação Excel à Q.P.A.; importação da NF Q.P.A. emitida | `285.xlsx` (template da solicitação); NF Q.P.A. via parser CarVia existente |

### 1.3 Modelos e produtos

A Q.P.A. comercializa **3 modelos** neste módulo (todos `1000W 60V 20AH` autopropelidos):

| Modelo canônico | Aliases conhecidos | Código Q.P.A. (visto) | Cores observadas | `regex_chassi` durável |
|-----------------|--------------------|-----------------------|------------------|------------------------|
| `X11_MINI` | "X11 NAC", "AUTOPROPELIDO X11 MINI 1000W 60V 20AH" | `1342056` | AZUL | `^(MCBRX11M\d{9}\|LA\d+V1000W\d{4})$` |
| `DOT` | "DOT 1000W", "AUTOPROPELIDO DOT 1000W 60V 20AH" | `1342059` | CINZA, PRETO | `^(LA\d+SA\d+\d{5}\|LA\d+V1000W\d{4}\|HL5TCAH3[0-9X]S9W57\d{3}\|MCBRDOT\d{10})$` |
| `SOL` | "AUTOPROPELIDO SOL 1000W 60V 20AH" | `1342063` | CINZA, PRETO | `^17292\d{10}$` |

`MIA` aparece no recibo HAROLDO SP mas **não é escopo** deste módulo. Modelo `X12` (com chassi `HL5TCAH3*[A-Z]9W*` ou `MCBRX122*`) também **não é escopo v1**.

**Colisão admitida**: o regex `LA\d+V1000W\d{4}` bate tanto X11_MINI (lote `LA250860V1000W*`) quanto DOT (lotes `LA25860V1000W*` e `LA250960V1000W*`). Como a validação `regex_chassi` é alerta amarelo (não bloqueia) e o modelo de cada chassi vem do recibo Motochefe, a colisão é aceitável — sistema confia no recibo. Reescrita do regex para distinguir é possível via UI (Task 24 do Plano 1) sem deploy.

### 1.4 Fronteira do módulo

O módulo **não compartilha dados** com:

| Módulo vizinho | Motivo da fronteira |
|---|---|
| `app/hora/` (Lojas HORA Motochefe) | PJ diferente; HORA é B2C varejo, Motos Assaí é B2B atacadista. Não importar `HoraMoto`, `HoraVenda`. |
| `app/carvia/` (transportadora) | CarVia só transporta. Reuso permitido **apenas via adapter** do parser DANFE Q.P.A. (não import direto de modelos). |
| `app/pedidos/leitura/` | Reuso da classe base `PDFExtractor` e `IdentificadorDocumento` permitido — extensão por subclasse + novos padrões na lookup table. |
| `app/motochefe/` (distribuidora) | PJ diferente. Zero relação. |

---

## 2. Decisões aprovadas (Q&A com dono do produto)

| # | Decisão | Aprovado |
|---|---------|----------|
| 1 | Pedidos VOE entram via **parser PDF determinístico** (regex/pdfplumber) com **fallback LLM** quando confiança < 70% | ✅ |
| 2 | Consolidação **N pedidos VOE → 1 PO Motochefe** (operador seleciona via checkbox) | ✅ |
| 3 | Separação **fungível por modelo** (qualquer chassi DISPONIVEL do modelo serve, cor não importa) | ✅ |
| 4 | Status `PENDENTE` (peça com defeito) **bloqueia** transição para `DISPONIVEL` até resolver | ✅ |
| 5 | **1 único CD** chamado "Operação VOE" (1 registro seed em `assai_cd`) | ✅ |
| 6 | Histórico das **3 últimas disponibilizações globais** inline na própria tela, com botão "Reverter" | ✅ |
| 7 | Solicitação de faturamento à Q.P.A.: **Excel idêntico ao 285.xlsx** para download manual | ✅ |
| 8 | Permissões: **apenas toggle master** `sistema_motos_assai` em `Usuario` (sem granular v1) | ✅ |
| 9 | Modelos: **X11 MINI (alias X11 NAC), DOT 1000W, SOL 1000W** (MIA fora do escopo) | ✅ |
| 10 | Recibo Motochefe: aceita **PDF E Excel**, determinístico com fallback LLM | ✅ |
| 11 | Máscaras de chassi: cadastro flexível (`assai_modelo.regex_chassi`); **dono envia máscara, Claude monta o regex** | ✅ |
| 12 | Reverter MONTADA: **motivo obrigatório em modal** (textarea ≥3 chars) | ✅ |

---

## 3. Arquitetura

### 3.1 Abordagem: módulo standalone (Hora-style)

Novo blueprint `app/motos_assai/` registrado em `url_prefix='/motos-assai'`. Tabelas com prefixo `assai_*`. Toggle `sistema_motos_assai` em `Usuario`.

**Reuso via adapters** (sem modificar módulos vizinhos):
- `app/pedidos/leitura/base.PDFExtractor` — classe base do parser determinístico
- `app/pedidos/leitura/identificador.IdentificadorDocumento` — adicionar padrões `QPA` (CNPJ + texto)
- `app/carvia/services/parsers/danfe_pdf_parser.DanfePDFParser` — parser de NF Q.P.A. já trata H3 repeat detection
- `app/carvia/services/pricing/moto_recognition_service` — adicionar `SOL` (1 linha **OU** seed em `CarviaModeloMoto`)
- `html5-qrcode@2.3.8` — wizard de recebimento (CDN, sem mudança)

### 3.2 Estrutura de pastas

```
app/motos_assai/
├── CLAUDE.md
├── __init__.py
├── decorators.py                 # require_motos_assai
├── models/
│   ├── cd.py                     # AssaiCd
│   ├── loja.py                   # AssaiLoja
│   ├── modelo.py                 # AssaiModelo + AssaiModeloAlias
│   ├── moto.py                   # AssaiMoto + AssaiMotoEvento
│   ├── pedido.py                 # AssaiPedidoVenda + AssaiPedidoVendaItem
│   ├── compra.py                 # AssaiCompraMotochefe + AssaiCompraMotochefePedido
│   ├── recibo.py                 # AssaiReciboMotochefe + AssaiReciboItem
│   ├── separacao.py              # AssaiSeparacao + AssaiSeparacaoItem
│   └── nf_qpa.py                 # AssaiNfQpa + AssaiNfQpaItem
├── routes/
│   ├── dashboard.py
│   ├── cadastros.py              # /lojas /modelos /cd
│   ├── pedidos.py                # upload + lista + detalhe
│   ├── compras.py
│   ├── recibos.py
│   ├── recebimento.py            # wizard A→B→C→D
│   ├── montagem.py
│   ├── disponibilizar.py
│   ├── separacao.py
│   ├── faturamento.py            # gera Excel + importa NF Q.P.A.
│   └── pendencias.py
├── services/
│   ├── parsers/
│   │   ├── qpa_pedido_extractor.py
│   │   ├── qpa_pedido_llm_fallback.py
│   │   ├── motochefe_recibo_extractor.py
│   │   ├── motochefe_recibo_llm_fallback.py
│   │   └── nf_qpa_adapter.py
│   ├── pedido_service.py
│   ├── compra_service.py
│   ├── recibo_service.py
│   ├── recebimento_service.py
│   ├── montagem_service.py
│   ├── disponibilizar_service.py
│   ├── separacao_service.py
│   ├── faturamento_service.py
│   ├── modelo_resolver.py
│   ├── chassi_validator.py
│   └── moto_evento_service.py
└── workers/
    └── parsing_worker.py         # RQ async (caso parsing pesado)

app/static/motos_assai/
├── js/
│   ├── recebimento_wizard.js
│   ├── montagem_quick.js
│   ├── disponibilizar_quick.js
│   └── separacao_chassi.js
└── css/_motos_assai.css

app/templates/motos_assai/
├── base_motos_assai.html
├── dashboard.html
├── cadastros/
├── pedidos/
├── compras/
├── recibos/
├── recebimento/wizard.html
├── montagem/quick.html
├── disponibilizar/quick.html
├── separacao/
├── faturamento/
└── partials/_historico_3_ultimas.html

scripts/migrations/
├── motos_assai_01_schema.{py,sql}
├── motos_assai_02_toggle_usuario.{py,sql}
├── motos_assai_03_seed_lojas.py
├── motos_assai_04_seed_modelos.py
├── motos_assai_05_seed_cd.py
└── motos_assai_06_carvia_modelo_sol.py   # opcional
```

---

## 4. Modelo de dados (16 tabelas)

### 4.1 Cadastros

**`assai_cd`** — 1 registro fixo (seed)
- `id`, `nome` ('Operação VOE'), `endereco`, `cnpj`, `ativo`

**`assai_loja`** — 39 lojas Sendas/Assaí (seed via planilha 285 aba BASE LOJAS)
- `id`, `numero` (12, 18, 24, …, 350) UNIQUE, `nome`, `cnpj`, `ie`, `razao_social`, `endereco`, `bairro`, `cep`, `cidade`, `uf`, `regional`, `ativo`

**`assai_modelo`** — 3 modelos (seed: X11_MINI, DOT, SOL)
- `id`, `codigo` UNIQUE (X11_MINI, DOT, SOL), `nome` (X11 MINI 1000W), `descricao_qpa` (AUTOPROPELIDO X11 MINI 1000W 60V 20AH), `codigo_qpa` (1342056), `regex_chassi` (preenchido após dono enviar máscaras), `ativo`

**`assai_modelo_alias`** — N nomes → 1 modelo canônico
- `id`, `modelo_id` FK, `alias` (texto), `tipo` (NOME_LIVRE / CODIGO_QPA / DESCRICAO_RECIBO), `ativo`
- UNIQUE (`tipo`, `alias`)

### 4.2 Identidade da moto

**`assai_moto`** — insert-once, chave universal
- `id`, `chassi` UNIQUE, `modelo_id` FK, `cor`, `motor`, `ano`, `criada_em`
- UPDATE permitido apenas em `cor` e `modelo_id` (recebimento como SOT, padrão Hora)

**`assai_moto_evento`** — log append-only
- `id`, `chassi` FK indexada, `tipo` (enum string), `ocorrido_em`, `operador_id` FK usuarios, `observacao`, `dados_extras` JSONB
- Tipos: `ESTOQUE`, `MONTADA`, `PENDENTE`, `PENDENCIA_RESOLVIDA`, `DISPONIVEL`, `REVERTIDA_PARA_MONTADA`, `SEPARADA`, `FATURADA`, `CANCELADA`, `MOTO_FALTANDO`

**Status efetivo** = último evento por chassi (`ORDER BY ocorrido_em DESC LIMIT 1`).
**EVENTOS_EM_ESTOQUE** = `{ESTOQUE, MONTADA, DISPONIVEL}`. PENDENTE conta como em estoque mas bloqueia DISPONIVEL.

### 4.3 Pipeline pedido → compra → recibo

**`assai_pedido_venda`** — header pedido VOE
- `id`, `numero` UNIQUE ("21439695/L"), `data_emissao`, `previsao_entrega`, `fornecedor_cnpj` (Q.P.A.), `pdf_s3_key`, `parser_usado` (DETERMINISTICO/LLM_HAIKU/LLM_SONNET/MANUAL), `parsing_confianca` Decimal(3,2), `status` (ABERTO / EM_PRODUCAO / SEPARANDO / FATURADO_PARCIAL / FATURADO / CANCELADO), `criado_por_id`, `criado_em`

**`assai_pedido_venda_item`** — linha por (pedido × loja × modelo)
- `id`, `pedido_id` FK, `loja_id` FK, `modelo_id` FK, `qtd_pedida`, `valor_unitario`, `valor_total`
- UNIQUE (`pedido_id`, `loja_id`, `modelo_id`)
- Campos derivados (não materializados): `qtd_separada`, `qtd_faturada` (calculados via JOIN)

**`assai_compra_motochefe`** — PO consolidado
- `id`, `numero` UNIQUE (auto MA-AAAA-NNNN), `data_emissao`, `motochefe_cnpj`, `status` (ABERTA / RECEBIMENTO_PARCIAL / FECHADA / CANCELADA), `criada_por_id`, `criada_em`

**`assai_compra_motochefe_pedido`** — N:N
- `id`, `compra_id` FK, `pedido_id` FK
- UNIQUE (`compra_id`, `pedido_id`)

**`assai_recibo_motochefe`** — recibo de carga (contra-prova)
- `id`, `compra_id` FK, `numero_recibo`, `data_recibo`, `equipe`, `conferente_motochefe`, `total_motos_declarado`, `doc_s3_key`, `tipo_documento` (PDF / EXCEL), `parser_usado`, `parsing_confianca`, `status` (RECEBIDO_AGUARDANDO_CONFERENCIA / EM_CONFERENCIA / CONCLUIDO / COM_DIVERGENCIA), `criado_por_id`

**`assai_recibo_item`** — linha do recibo (1 chassi)
- `id`, `recibo_id` FK, `chassi` (não FK — pode não existir ainda em assai_moto), `modelo_texto_recibo`, `modelo_id` FK (após resolver via alias), `cor_texto`, `motor`, `conferido` Boolean, `tipo_divergencia` (NULL / MODELO_DIFERENTE / COR_DIFERENTE / CHASSI_EXTRA / MOTO_FALTANDO / AVARIA_FISICA), `qr_code_lido` Boolean, `foto_s3_key`

### 4.4 Separação e faturamento

**`assai_separacao`** — 1 por pedido × loja
- `id`, `pedido_id` FK, `loja_id` FK, `status` (EM_SEPARACAO / FECHADA / FATURADA / CANCELADA), `iniciada_em`, `fechada_em`, `fechada_por_id`, `solicitacao_excel_s3_key`, `motivo_cancelamento`
- UNIQUE (`pedido_id`, `loja_id`) parcial WHERE status NOT IN ('CANCELADA') — permite recriar após cancelar

**`assai_separacao_item`** — chassi vinculado a separação
- `id`, `separacao_id` FK, `chassi` FK indexada, `modelo_id` FK, `valor_unitario_qpa` (snapshot do pedido), `registrada_em`, `registrada_por_id`
- UNIQUE `chassi` parcial WHERE `separacao.status NOT IN ('CANCELADA')` — chassi cancelado libera para nova separação

**`assai_nf_qpa`** — NF emitida pela Q.P.A.
- `id`, `separacao_id` FK (preenchido após match), `chave_44` UNIQUE, `numero`, `serie`, `emitente_cnpj`, `destinatario_cnpj`, `destinatario_nome` (contém "LJ\<n\>"), `loja_id` FK (extraído de "LJ\<n\>"), `valor_total`, `data_emissao`, `pdf_s3_key`, `status_match` (BATEU / DIVERGENTE / NAO_RECONCILIADO), `importada_em`, `importada_por_id`

**`assai_nf_qpa_item`** — item da NF
- `id`, `nf_id` FK, `chassi`, `modelo_extraido`, `valor_extraido`, `separacao_item_id` FK (após match), `tipo_divergencia`

### 4.5 Invariantes (paralelo ao Hora)

1. `assai_moto.chassi` é a chave universal do módulo.
2. Toda tabela transacional tem `chassi` FK indexada.
3. `assai_moto` é insert-once. UPDATE permitido APENAS em `cor` e `modelo_id` quando recebimento físico diverge do recibo Motochefe (SOT).
4. Estado atual da moto = consulta à tabela de eventos, não UPDATE em coluna `status`.
5. `assai_moto_evento` é append-only — nunca DELETE; reverter cria nova linha (`REVERTIDA_PARA_MONTADA`).
6. PDF/Excel originais persistem em S3 (`assai_*_s3_key`) — fonte de verdade documental.

---

## 5. Fluxos por etapa

### 5.1 Etapa 1 — Pedido VOE entra

**Rota**: `POST /motos-assai/pedidos/upload`
**Service**: `pedido_service.importar_pdf_voe(pdf_bytes, importado_por_id)`

**Fluxo**:
1. Salva PDF em S3 (`motos_assai/pedidos/<numero>.pdf`)
2. `IdentificadorDocumento` confirma rede=`QPA` + tipo=`PEDIDO`
3. `QpaPedidoExtractor.extract()` (determinístico) processa página por página:
   - Extrai header da loja: `LJ<num>`, CNPJ, razão social
   - Extrai itens: `codigo_qpa`, `descricao`, `qtd`, `valor_unitario`, `valor_total`
4. Calcula confiança: `(itens_extraidos / itens_esperados) * (paginas_processadas / paginas_total)`
5. Se confiança < 70% **OU** zero itens: aciona fallback LLM
   - Tentativa 1: Haiku 4.5 com schema JSON
   - Tentativa 2: Sonnet 4.6 (se Haiku falhar parse)
6. Cria `assai_pedido_venda` (status=`ABERTO`, `parser_usado`, `parsing_confianca`)
7. Para cada item: resolve modelo via `modelo_resolver(descricao, origem='PEDIDO_VOE')` → cria `assai_pedido_venda_item`
8. Renderiza tela de detalhe com lojas/modelos extraídos para conferência humana

**Tela de conferência**: lista as 38 lojas com totais por modelo. Operador valida visualmente e clica "Confirmar pedido". Status fica `ABERTO` aguardando ser consolidado em PO Motochefe.

### 5.2 Etapa 2 — PO Motochefe consolidado

**Rota**: `POST /motos-assai/compras/nova`
**Service**: `compra_service.criar_consolidado(pedido_ids: list[int], motochefe_cnpj: str)`

**Fluxo**:
1. Operador acessa `/motos-assai/compras/nova` e vê lista de pedidos `ABERTO`
2. Marca checkboxes dos pedidos a consolidar
3. Tela mostra preview: SUM por modelo dos pedidos selecionados
4. Operador clica "Gerar PO"
5. Service:
   - Cria `assai_compra_motochefe` (numero auto MA-AAAA-NNNN)
   - Cria `assai_compra_motochefe_pedido` para cada pedido
   - Atualiza pedidos para status `EM_PRODUCAO`
   - Gera PDF do PO (template Jinja → wkhtmltopdf ou WeasyPrint) com totalizadores por modelo + assinatura
6. Tela de detalhe da compra mostra link para baixar PDF e botão "Marcar como enviada à Motochefe"

### 5.3 Etapa 3 — Recibo Motochefe entra

**Rota**: `POST /motos-assai/compras/<id>/recibos/upload`
**Service**: `recibo_service.importar(compra_id, file_bytes, mime_type, importado_por_id)`

**Fluxo**:
1. Detecta tipo: `application/pdf` → `MotochefeReciboPdfExtractor`; `xlsx` → `MotochefeReciboXlsxExtractor`
2. Extractor extrai header (data, equipe, conferente, total declarado) + linhas de chassi
3. Calcula confiança: `(linhas_extraidas / total_declarado_no_header)`
4. Confiança < 80% → fallback LLM Haiku → fallback Sonnet
5. Cria `assai_recibo_motochefe` (status=`RECEBIDO_AGUARDANDO_CONFERENCIA`) + N `assai_recibo_item` (chassi, modelo_texto, cor, motor)
6. Para cada item: tenta resolver modelo via `modelo_resolver(modelo_texto, origem='RECIBO_MOTOCHEFE')` → preenche `modelo_id` quando bate alias

### 5.4 Etapa 4 — Recebimento físico (QR + Barcode + manual)

**Rota**: `GET /motos-assai/recibos/<id>/conferir` — wizard A→B→C→D
**Service**: `recebimento_service.registrar_conferencia(recibo_id, chassi, qr_code_lido, foto_s3_key)`

**Wizard 4 passos** (cópia adaptada de `app/templates/hora/recebimento_wizard.html`):

- **Passo A**: input grande com foco automático aceita digitação ou leitor USB (Enter dispara). Botão "Câmera (mobile)" abre `Html5Qrcode@2.3.8` com `facingMode: 'environment'`. Detecta `window.isSecureContext`; em HTTP sem cert oculta câmera.
- **Passo B**: chassi enviado a `/motos-assai/recebimento/validar-chassi` (AJAX). Backend:
   - Verifica `assai_recibo_item.chassi == informado` → preenche modelo+cor esperados
   - Aplica `chassi_validator.validar(chassi, modelo_id)` → bate com `regex_chassi` do modelo? Se não, alerta amarelo (não bloqueia)
   - Retorna divergências detectadas
- **Passo C**: confirmação com foto opcional (input `accept="image/*" capture="environment"` → S3) + seletor de divergências (modelo, cor, avaria) via modal Bootstrap (não usar `prompt()` — quebra em iOS PWA)
- **Passo D**: gravação. Insere `assai_moto` (se não existe) com cor/modelo conferidos. Emite `assai_moto_evento(tipo='ESTOQUE')`. Atualiza `assai_recibo_item.conferido=True`. Foco volta para Passo A automaticamente. Contador "X de Y conferidos".

**Finalização**:
- Botão "Finalizar conferência" só habilita quando todos chassis foram conferidos OU quando operador confirma divergência via modal
- `recebimento_service.finalizar_recebimento(recibo_id)`:
   - Para cada `assai_recibo_item.conferido=False`: emite `assai_moto_evento(tipo='MOTO_FALTANDO')` (chassi declarado não chegou — exclui de estoque)
   - Para chassis conferidos com divergência: aplica `_aplicar_correcao_moto_se_divergir` (UPDATE em cor/modelo se conferiu diferente do recibo)
   - Status do recibo → `CONCLUIDO` (zero divergência) ou `COM_DIVERGENCIA`

**Lock pessimista**: UNIQUE em (`recibo_id`, `chassi`) — race de submit simultâneo retorna 409.

### 5.5 Etapa 5 — Montagem (ESTOQUE → MONTADA / PENDENTE)

**Rota**: `POST /motos-assai/montagem/registrar`
**Service**: `montagem_service.registrar(chassi, pendencia: bool, descricao_pendencia, chassi_doador, operador_id)`

**Tela rápida** (`/motos-assai/montagem`):
```
┌─ Header: "Montagem — Operação VOE"
├─ [Input QR/Barcode/Chassi (foco automático)] [Câmera]
├─ Toggle "Pendência peça com defeito?"
│  └─ Se ON: textarea descrição (≥3 chars obrigatório) + chassi doador (autocomplete opcional)
├─ Botão "Registrar" (Ctrl+Enter)
└─ Histórico (3 últimas globais):
   ┌ Chassi LA2025SA110007354 · DOT · CINZA   12:34 · você   [Reverter]
   ├ Chassi MCBRX11M251104233 · X11 MINI · AZUL  12:31 · joao [Reverter]
   └ Chassi 172922504672358   · SOL · CINZA   12:28 · maria [Reverter]
```

**Validações**:
- Status atual = `ESTOQUE` (rejeita se MONTADA, DISPONIVEL etc.)
- Pendência ON → emite `PENDENTE` (com descrição em `dados_extras.descricao` + `dados_extras.chassi_doador`)
- Pendência OFF → emite `MONTADA`

### 5.6 Etapa 6 — Disponibilizar (MONTADA → DISPONIVEL)

**Rota**: `POST /motos-assai/disponibilizar/registrar`
**Service**: `disponibilizar_service.disponibilizar(chassi, operador_id)`

**Tela rápida** (`/motos-assai/disponibilizar`):
- Layout idêntico ao Montagem
- Validação: status efetivo da moto DEVE ser `MONTADA`. Sequência de eventos válida: `ESTOQUE → MONTADA → DISPONIVEL` (caminho feliz) ou `ESTOQUE → MONTADA → PENDENTE → PENDENCIA_RESOLVIDA (volta a MONTADA) → DISPONIVEL`. O service `disponibilizar_service.disponibilizar` calcula status efetivo via último evento e rejeita 409 se não for `MONTADA`.
- Histórico das 3 últimas disponibilizações globais com botão "Reverter para MONTADA"

**Reverter**:
- Botão abre modal Bootstrap:
   ```
   Reverter chassi LA2025SA110007354 para MONTADA?
   Motivo (obrigatório, ≥3 chars):
   [textarea]
   [Cancelar] [Confirmar reversão]
   ```
- Service `disponibilizar_service.reverter(chassi, motivo, operador_id)`:
   - Valida `motivo.strip() >= 3`
   - Emite `assai_moto_evento(tipo='REVERTIDA_PARA_MONTADA', dados_extras={'motivo': '…', 'evento_revertido_id': N})`
   - Moto sai do histórico das 3 últimas (substituída pela próxima disponibilização)

### 5.7 Etapa 7 — Separação (DISPONIVEL → SEPARADA, vinculado a pedido+loja)

**Rota**: `GET /motos-assai/pedidos/<pid>/separar/<lid>` — tela principal
**Service**: `separacao_service.registrar_chassi(pedido_id, loja_id, chassi, registrada_por_id)`

**Tela**:
```
Pedido 21439695/L · Loja 285 Freguesia do Ó · status: EM_SEPARACAO
─────────────────────────────────────────
Saldo pendente:
  X11 MINI    3 / 10  ████░░░░░░  (pendentes 7)
  DOT        14 / 14  ██████████  ✓ COMPLETO
  SOL         0 / 10  ░░░░░░░░░░  (pendentes 10)
─────────────────────────────────────────
[Input: QR / Barcode / Chassi]  [Câmera]

Chassis registrados nesta separação (17):
  LA2025SA110007354 · DOT · CINZA   ↩ desfazer
  MCBRX11M251104233 · X11 MINI · AZUL  ↩ desfazer
  ...

[Finalizar separação] [Gerar solicitação Q.P.A.] [Cancelar separação]
```

**Validações inline ao escanear chassi**:
- Status atual = `DISPONIVEL` (rejeita outros)
- Modelo bate com algum modelo com saldo > 0 no pedido para esta loja
- Não pertence a outra separação ativa (UNIQUE chassi parcial)

**Sucesso**:
1. Cria `assai_separacao` (se primeiro chassi) com status `EM_SEPARACAO`
2. Insere `assai_separacao_item` com `valor_unitario_qpa` snapshot do `assai_pedido_venda_item.valor_unitario`
3. Emite `assai_moto_evento(tipo='SEPARADA', dados_extras={'separacao_id', 'pedido_id', 'loja_id'})`

**Finalizar separação**:
- Permitido com saldo zero OU com saldo aberto (operador decide se separa parcial)
- Status separação → `FECHADA`. Pedido pode ir a `SEPARANDO` (algumas lojas pendentes) ou continuar `EM_PRODUCAO`

**Cancelar separação**:
- Modal motivo obrigatório (textarea ≥3 chars)
- Service `separacao_service.cancelar(separacao_id, motivo, operador_id)`:
   - Atualiza `assai_separacao.status='CANCELADA'` + `motivo_cancelamento`
   - Para cada `assai_separacao_item` ativo: emite `assai_moto_evento(tipo='DISPONIVEL', observacao='separacao_cancelada', dados_extras={'separacao_id': N, 'motivo': '…'})` — moto volta direto a `DISPONIVEL` (não passa por MONTADA pois já estava montada+tag+manual)
- Pedido pode voltar a `EM_PRODUCAO` se nenhuma outra separação estava aberta

**Gerar solicitação faturamento Q.P.A.**:
- Service `faturamento_service.gerar_excel_qpa(separacao_id)`:
   - Cria xlsx com 2 abas idênticas ao `285.xlsx`:
      - Aba **PEDIDO**: header com `Nº LOJA`, `CLIENTE`, `CNPJ`, `IE`, `ENDEREÇO`, `BAIRRO`, `UF`, `CIDADE`, `CEP` (preenchido de `assai_loja`) + tabela `ITEM | CHASSI | MODELO | COR | VALOR` + linha TOTAL
      - Aba **BASE LOJAS**: cópia do template das 39 lojas
   - Salva em S3 (`motos_assai/solicitacoes/<separacao_id>.xlsx`)
   - Atualiza `assai_separacao.solicitacao_excel_s3_key`
   - Retorna URL de download

### 5.8 Etapa 8 — Importar NF Q.P.A. + match

**Rota**: `POST /motos-assai/faturamento/upload-nf`
**Service**: `nf_qpa_adapter.importar(pdf_bytes, importada_por_id)`

**Fluxo**:
1. Salva PDF em S3
2. Instancia `app.carvia.services.parsers.danfe_pdf_parser.DanfePDFParser` e chama `parser.parse(pdf_bytes)`
3. Extrai: `chave_44`, `numero`, `serie`, `cnpj_emitente`, `cnpj_destinatario`, `nome_destinatario` (contém "LJ\<n\>"), `valor_total`, `data_emissao`, `veiculos[]`
4. Extrai loja_id de `nome_destinatario` via regex `r'LJ\s*(\d+)'` → busca `AssaiLoja.numero == match`
5. Cria `assai_nf_qpa` (status_match=NAO_RECONCILIADO inicialmente)
6. Para cada veículo: cria `assai_nf_qpa_item` + tenta match com `assai_separacao_item` ativo do (loja, modelo, chassi)
7. Calcula `status_match`:
   - **BATEU**: todos chassis batem (loja, modelo, valor_unitario com tolerância 1%)
   - **DIVERGENTE**: algum não bate (loja, modelo, valor)
   - **NAO_RECONCILIADO**: nenhum bate (NF de loja sem separação ou inversamente)
8. Se `BATEU`: separação → `FATURADA`. Para cada moto: emite `assai_moto_evento(tipo='FATURADA', dados_extras={'nf_id', 'chave_44'})`
9. Se `DIVERGENTE`: tela de revisão manual (operador resolve item a item)

**Modelo SOL**: adicionar antes da primeira NF Q.P.A. com SOL:
- Opção A (1 linha): `app/carvia/services/pricing/moto_recognition_service.py:49` — adicionar `|SOL` ao regex
- Opção B (zero código): seed em `CarviaModeloMoto` com `regex_pattern=r'\bSOL\b'`

---

## 6. Telas dinâmicas — UX/UI

### 6.1 Princípios

- Sem `<style>` em templates — CSS em `app/static/css/modules/_motos_assai.css`
- Cores via design tokens (`var(--text)`, `var(--bg-light)`)
- Light/dark mode via tokens automaticamente
- Atalhos de teclado: Enter (submit), Tab (navegação), Esc (cancelar), Ctrl+Enter (registrar/registrar)
- Mobile-first nas telas operacionais (montagem, disponibilizar, recebimento, separação)
- Listagens: filtros via GET form, paginação por cursor (250 default), `selectinload` no service para evitar N+1

### 6.2 Tela de listagem padrão

Cabeçalho:
- Filtros como `<form method="GET">` com loja, modelo, status, data_inicio, data_fim, busca chassi (autocomplete substring)
- Botões de ação (novo, exportar) à direita

Corpo:
- Tabela com badges coloridos por status (light/dark via tokens)
- Click na linha → drawer Bootstrap com detalhes inline (sem nav full-page)

Rodapé:
- Paginação com info "Mostrando X-Y de Z"

### 6.3 Tela de wizard (recebimento)

4 passos com indicador de progresso. Detalhes em §5.4.

### 6.4 Telas rápidas (montagem, disponibilizar)

Single-column mobile-first. Detalhes em §5.5 e §5.6.

### 6.5 Tela de separação

Saldo pendente em barras de progresso. Lista de chassis registrados com botão "↩ desfazer". Detalhes em §5.7.

### 6.6 Dashboard

Cards com totais de estoque por status, pedidos por status, compras Motochefe abertas, atalhos para telas operacionais.

---

## 7. Permissões

### 7.1 Toggle master apenas (v1)

Coluna `sistema_motos_assai` em `usuarios` (BOOLEAN DEFAULT FALSE).

Método `Usuario.pode_acessar_motos_assai()`:
```python
def pode_acessar_motos_assai(self):
    if self.status != 'ativo':
        return False
    return self.sistema_motos_assai or self.perfil == 'administrador'
```

### 7.2 Decorator (`app/motos_assai/decorators.py`)

```python
def require_motos_assai(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.pode_acessar_motos_assai():
            if request.is_json or 'application/json' in request.headers.get('Accept', ''):
                return jsonify({'error': 'Acesso negado ao módulo Motos Assai'}), 403
            flash('Acesso negado ao módulo Motos Assai.', 'danger')
            return redirect(url_for('main.dashboard'))
        return func(*args, **kwargs)
    return wrapper
```

Aplicado em **todas** as rotas do blueprint.

### 7.3 Tela admin de usuários (formulário)

Adicionar checkbox "Acesso ao Sistema Motos Assai" nos forms `AprovarUsuarioForm` e `EditarUsuarioForm` (`app/auth/forms.py`).

Adicionar leitura/escrita do campo nas rotas `aprovar_usuario` e `editar_usuario` (`app/auth/routes.py`).

Adicionar checkbox no template `app/templates/auth/editar_usuario.html`.

### 7.4 Menu (`app/templates/base.html`)

```jinja
{% if current_user.is_authenticated and current_user.pode_acessar_motos_assai() %}
  <li>
    <a class="dropdown-item" href="{{ url_for('motos_assai.dashboard') }}">
      <i class="fas fa-motorcycle"></i> Motos Assaí
    </a>
  </li>
{% endif %}
```

### 7.5 Redirect pós-login (`app/auth/utils.py`)

Adicionar em `url_primeiro_dashboard_disponivel` na ordem `lojas → motochefe → motos_assai → carvia → comercial`:
```python
if getattr(user, 'sistema_motos_assai', False):
    return url_for('motos_assai.dashboard')
```

### 7.6 Isolamento

Usuário com apenas `sistema_motos_assai=True` é redirecionado direto a `/motos-assai/dashboard` no login. Não vê menu Nacom (gate global em `base.html`). Acesso direto a URLs de outros módulos é bloqueado pelos respectivos decorators.

---

## 8. Parsers em detalhe

### 8.1 Pedido VOE Q.P.A. — extrator determinístico

`app/motos_assai/services/parsers/qpa_pedido_extractor.py` herda de `app.pedidos.leitura.base.PDFExtractor`.

**Estratégia por página** (cada página = 1 loja):

```python
class QpaPedidoExtractor(PDFExtractor):
    REGEX_LOJA_NUMERO = re.compile(r'SENDAS\s+DISTRIBUIDORA\s+S/A\s+LJ(\d+)')
    REGEX_CNPJ_LOJA = re.compile(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})')
    REGEX_PRODUTO = re.compile(
        r'^(\d{7})\s*([A-ZÀ-Ÿ0-9 ]+?)\s+UN\s+1\s+'
        r'([\d,\.]+)\s+([\d,\.]+)\s+([\d,\.]+)'
    )
    REGEX_NUMERO_PEDIDO = re.compile(r'PEDIDO\s+DE\s+COMPRAS\s+(\d+/[A-Z])')

    def extract(self, pdf_path, texto_pre_extraido=None):
        # Phase 1: parsing leve
        with pdfplumber.open(pdf_path) as pdf:
            paginas_dados = []
            for page in pdf.pages:
                texto = page.extract_text() or ""
                paginas_dados.append(self._parse_pagina(texto))

        # Phase 2: preload batch (assai_loja + assai_modelo + alias)
        self._preload_lojas([p['numero_loja'] for p in paginas_dados])
        self._preload_modelos([item['codigo_qpa'] for p in paginas_dados for item in p['itens']])

        # Phase 3: monta items finais
        items = []
        for p in paginas_dados:
            loja = self.loja_cache.get(p['numero_loja'])
            for item in p['itens']:
                modelo = self.modelo_cache.get(item['codigo_qpa'])
                items.append({
                    'numero_pedido': p['numero_pedido'],
                    'numero_loja': p['numero_loja'],
                    'loja_id': loja.id if loja else None,
                    'modelo_id': modelo.id if modelo else None,
                    **item
                })
        return items
```

### 8.2 Pedido VOE — fallback LLM

`app/motos_assai/services/parsers/qpa_pedido_llm_fallback.py`:

```python
PROMPT = """
Você está extraindo dados de um PEDIDO DE COMPRAS da Q.P.A. Distribuição emitido pelo Consinco para a Sendas Distribuidora (Assaí).

O PDF tem N páginas, cada página = 1 loja Assaí.

Extraia em JSON:
{
  "numero_pedido": "21439695/L",
  "data_emissao": "DD/MM/YYYY",
  "fornecedor_cnpj": "53780554000115",
  "lojas": [
    {
      "numero_loja": "12",
      "cnpj_loja": "06057223027290",
      "razao_social": "SENDAS DISTRIBUIDORA S/A LJ12",
      "itens": [
        {"codigo_qpa": "1342056", "descricao": "AUTOPROPELIDO X11 MINI 1000W 60V 20AH", "qtd": 10, "valor_unitario": 7100.00, "valor_total": 71000.00}
      ]
    }
  ]
}

Modelos esperados: X11 MINI, DOT, SOL.
"""
```

**Prioridade**: Haiku 4.5 → fallback Sonnet 4.6 se Haiku falhar parse JSON ou retornar dados incompletos.

### 8.3 Recibo Motochefe

**Identificação automática**:
- MIME `application/pdf` → `MotochefeReciboPdfExtractor` (pdfplumber + tabela)
- MIME `xlsx` → `MotochefeReciboXlsxExtractor` (openpyxl)
- Validação: presença de "RECIBO DO PEDIDO" + CNPJ Motochefe (a confirmar com dono)

**Determinístico PDF** — extrai header via regex e tabela via `page.extract_tables(table_settings={'vertical_strategy':'lines','horizontal_strategy':'lines'})`. Colunas: PEDIDO (vazio), DESCRIÇÃO (modelo), CHASSI, MOTOR, COR.

**Determinístico XLSX** — `openpyxl.load_workbook(data_only=True)`. Detecta header pela presença das células "CHASSI", "MOTOR", "COR" + extrai header (data, equipe, conferente).

**Fallback LLM**: quando linhas extraídas < 80% do total declarado no header.

### 8.4 NF Q.P.A. — adapter sem modificar CarVia

`app/motos_assai/services/parsers/nf_qpa_adapter.py`:

```python
from app.carvia.services.parsers.danfe_pdf_parser import DanfePDFParser

def importar_nf_qpa(pdf_bytes: bytes, importada_por_id: int) -> AssaiNfQpa:
    parser = DanfePDFParser()
    resultado = parser.parse(pdf_bytes)

    loja_match = re.search(r'LJ\s*(\d+)', resultado.get('nome_destinatario', ''))
    loja = AssaiLoja.query.filter_by(numero=loja_match.group(1)).first() if loja_match else None

    nf = AssaiNfQpa(
        chave_44=resultado['chave_44'],
        numero=resultado['numero'],
        serie=resultado.get('serie'),
        emitente_cnpj=resultado['cnpj_emitente'],
        destinatario_cnpj=resultado['cnpj_destinatario'],
        destinatario_nome=resultado['nome_destinatario'],
        loja_id=loja.id if loja else None,
        valor_total=Decimal(str(resultado['valor_total'])),
        data_emissao=resultado['data_emissao'],
        pdf_s3_key=...,
        status_match='NAO_RECONCILIADO',
        importada_em=now_brasil(),
        importada_por_id=importada_por_id,
    )
    db.session.add(nf)

    for veiculo in resultado.get('veiculos', []):
        modelo = modelo_resolver.resolver_modelo(veiculo['modelo'], origem='NF_QPA')
        item = AssaiNfQpaItem(
            nf=nf,
            chassi=veiculo['chassi'],
            modelo_extraido=veiculo['modelo'],
            valor_extraido=Decimal(str(veiculo.get('valor_unitario', 0))),
        )
        db.session.add(item)

    db.session.flush()
    _calcular_match(nf)
    db.session.commit()
    return nf
```

`_calcular_match` faz JOIN com `assai_separacao_item` ativos por chassi e calcula `status_match`.

### 8.5 Resolução de modelo (`modelo_resolver`)

`app/motos_assai/services/modelo_resolver.py`:

```python
def resolver_modelo(texto: str, origem: str) -> AssaiModelo | None:
    texto_normalizado = _normalizar(texto)

    # 1. Match exato em assai_modelo.codigo
    m = AssaiModelo.query.filter(
        func.upper(AssaiModelo.codigo) == texto_normalizado,
        AssaiModelo.ativo == True
    ).first()
    if m:
        return m

    # 2. Match em assai_modelo_alias
    alias = AssaiModeloAlias.query.filter(
        func.upper(AssaiModeloAlias.alias) == texto_normalizado,
        AssaiModeloAlias.ativo == True
    ).first()
    if alias:
        return alias.modelo

    # 3. Substring de descricao_qpa
    m = AssaiModelo.query.filter(
        AssaiModelo.descricao_qpa.ilike(f'%{texto}%'),
        AssaiModelo.ativo == True
    ).first()
    if m:
        return m

    return None
```

---

## 9. Migrations e seeds

### 9.1 Migrations duais (DDL .sql + Python verificação)

| # | Arquivo | Conteúdo |
|---|---------|----------|
| 1 | `motos_assai_01_schema.{py,sql}` | CREATE TABLE das 16 tabelas com `IF NOT EXISTS`, índices em `chassi`, `pedido_id`, `loja_id`, `modelo_id`, UNIQUE constraints |
| 2 | `motos_assai_02_toggle_usuario.{py,sql}` | `ALTER TABLE usuarios ADD COLUMN sistema_motos_assai BOOLEAN DEFAULT FALSE` |
| 3 | `motos_assai_03_seed_lojas.py` | INSERT 39 lojas Assaí (planilha 285 aba BASE LOJAS) |
| 4 | `motos_assai_04_seed_modelos.py` | INSERT X11_MINI, DOT, SOL + aliases (X11 NAC, AUTOPROPELIDO X11 MINI etc) + `regex_chassi` (preenchido após dono enviar máscaras) |
| 5 | `motos_assai_05_seed_cd.py` | INSERT 1 registro CD "Operação VOE" |
| 6 | `motos_assai_06_carvia_modelo_sol.py` | INSERT em `CarviaModeloMoto` com `regex_pattern=r'\bSOL\b'` (opção zero-código alternativa a editar moto_recognition_service.py) |

### 9.2 Itens necessários do dono do produto antes da implementação

1. ~~Máscaras de chassi~~ — **resolvido em 2026-05-07**: regex duráveis confirmados (ver §1.3).
2. ~~CNPJ canônico da Motochefe~~ — **descartado em 2026-05-07**: campos `motochefe_cnpj` e `assai_cd.cnpj` opcionais. Operação fiscal é Q.P.A. → Sendas/Assaí; CNPJs internos não são chave do modelo.
3. **Endereço do CD "Operação VOE"** (opcional para seed de `assai_cd` — pode ficar vazio v1 e ser preenchido depois via tela admin Task 25 do Plano 1).
4. ~~Confirmar campos canônicos do Excel 285.xlsx~~ — **resolvido**: estrutura extraída diretamente da planilha (2 abas: PEDIDO + BASE LOJAS).

**Status**: zero pendências bloqueantes. Implementação pode começar imediatamente.

---

## 10. Sequência de implementação

| Fase | Conteúdo | Tempo estimado |
|------|----------|----------------|
| **1. Foundation** | Migrations 1-2, modelos SQLAlchemy + relationships, decorator `require_motos_assai`, integração em `auth/forms.py`, `auth/routes.py`, `auth/utils.py`, `editar_usuario.html`, `base.html`, blueprint registrado, dashboard inicial vazio | 2 dias |
| **2. Cadastros** | CRUD `assai_loja` + seed 39 lojas, CRUD `assai_modelo` + seed 3 modelos + tela admin de regex_chassi, CRUD `assai_cd` + seed 1 | 1 dia |
| **3. Pipeline pedido → compra → recibo** | `QpaPedidoExtractor` + fallback LLM + tela upload + tela detalhe pedido, tela criar PO Motochefe + preview totalizadores, `MotochefeReciboExtractor` (PDF + Excel) + fallback LLM + tela upload | 3 dias |
| **4. Recebimento físico** | Cópia adaptada do `recebimento_wizard.html`, `recebimento_service` com validações + lock, eventos de moto + status derivado, `MOTO_FALTANDO` em batch | 2 dias |
| **5. Montagem + Disponibilizar** | Tela montagem (input + toggle pendência + histórico 3), service registrar com bloqueio se pendência, pendência de peça, tela disponibilizar (input + histórico 3 + reverter com motivo) | 2 dias |
| **6. Separação** | Tela separação por pedido+loja, service registrar + validar saldo, geração Excel idêntico ao 285.xlsx (2 abas) + download S3 | 2 dias |
| **7. NF Q.P.A. + faturamento** | Adapter `nf_qpa_adapter` chamando `DanfePDFParser`, tela upload NF + match com separação, status BATEU/DIVERGENTE/NAO_RECONCILIADO, atualizar SOL no parser CarVia (1 linha OU CarviaModeloMoto seed) | 1.5 dias |
| **8. Polish** | Testes (`tests/motos_assai/`) cobrindo regras críticas, CLAUDE.md do módulo, UI lint (P1-P9), visual regression test | 1 dia |

**Total**: ~14.5 dias (paralelizável: Fases 2/3/5 podem rodar simultaneamente após Fase 1).

---

## 11. Não-objetivos v1

1. **Múltiplos CDs** — apenas 1 CD ("Operação VOE"). Schema future-proof (`assai_cd` já existe).
2. **Permissões granulares** — apenas toggle master. Adicionar `assai_user_permissao` se equipe crescer.
3. **Transferência entre CDs** — não aplicável até existir 2º CD.
4. **Modelo MIA** — não escopo neste módulo.
5. **NFC-e, contingência** — sistema só importa NF emitida pela Q.P.A. externamente.
6. **Pipeline de avaria em estoque** — divergência no recebimento captura `AVARIA_FISICA` como `tipo_divergencia` em `assai_recibo_item` (com foto em S3), mas não há tabela dedicada `assai_avaria` para registrar avarias detectadas pós-recebimento (durante montagem/separação). Pode ser adicionado em v2 inspirado no padrão `hora_avaria`.
7. **Automação de envio de Excel à Q.P.A.** (e-mail SMTP) — operador baixa e envia manualmente em v1.
8. **Integração TagPlus / emissão de NFe pela Nacom** — Q.P.A. é o emissor fiscal, não a Nacom.

---

## 12. Riscos e mitigações

| Risco | Probabilidade | Mitigação |
|-------|---------------|-----------|
| Layout do PDF VOE muda (Consinco atualiza) | Média | Fallback LLM cobre. Logs de `parser_usado` permitem detectar drift. |
| Layout do recibo Motochefe varia entre cargas | Alta | Aceita PDF + Excel; fallback LLM. |
| Confiança LLM < 100% gera erro silencioso | Média | Tela de conferência humana após parse — operador valida visualmente antes de confirmar pedido. |
| Race ao reservar chassi em separação simultânea | Baixa | UNIQUE chassi parcial WHERE separacao.status NOT IN CANCELADA — race retorna 409. |
| Operador esquece de gerar Excel antes de finalizar | Baixa | UI: botão "Finalizar separação" pergunta "Gerar Excel agora?" se ainda não gerou. |
| Modelo SOL não reconhecido pelo parser CarVia da NF Q.P.A. | Alta (gap conhecido) | Seed em `CarviaModeloMoto` antes da primeira NF SOL OU 1 linha em `moto_recognition_service.py`. |
| Múltiplas separações para mesma (pedido, loja) após cancelamento | Tratada | UNIQUE parcial permite recriar após CANCELADA. |

---

## 13. Referências

- **Pipeline de 8 etapas**: definido pelo dono do produto Rafael Nascimento em 2026-05-07
- **Documentos de exemplo**:
   - Pedido VOE: `/mnt/c/Users/rafael.nascimento/Downloads/pedido VOE 1 (1).pdf`
   - Recibo Motochefe: `/mnt/c/Users/rafael.nascimento/Downloads/HAROLDO SP 05.05 (1).pdf`
   - Solicitação faturamento template: `/mnt/c/Users/rafael.nascimento/Downloads/285.xlsx`
- **Módulos de referência arquitetural**:
   - `app/hora/CLAUDE.md` — padrão de invariantes, eventos, permissões granulares
   - `app/pedidos/leitura/assai.py` — template de PDFExtractor com preload batch
   - `app/pedidos/leitura/identificador.py` — `IdentificadorDocumento` por CNPJ + texto
   - `app/carvia/services/parsers/danfe_pdf_parser.py` — parser de NF Q.P.A. (já trata H3 repeat detection)
- **Padrão de toggle master**: `sistema_lojas` em `app/auth/models.py:208-216`
- **Wizard QR Code de referência**: `app/templates/hora/recebimento_wizard.html`

---

**Este design foi aprovado pelo dono do produto em 2026-05-07. Pronto para writing-plans.**
