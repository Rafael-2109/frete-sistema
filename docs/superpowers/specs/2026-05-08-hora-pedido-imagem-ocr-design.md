# Fallback OCR para pedidos HORA via imagem (print de WhatsApp)

**Data**: 2026-05-08
**Modulo**: `app/hora`
**Status**: design aprovado, aguardando plano de implementacao

---

## 1. Contexto

Hoje os pedidos de compra HORA (Lojas → Motochefe) chegam via WhatsApp como
**prints de tela** do XLSX da loja. O fluxo manual atual:

1. Operador recebe print no WhatsApp.
2. Manda para o ChatGPT/Cowork.
3. Cowork extrai dados (vision) e devolve XLSX no formato canonico
   (`DD.MMH-XX.xlsx`).
4. Operador baixa o XLSX e sobe em `/hora/pedidos/importar-xlsx`.

O sistema ja tem fluxo completo de import via XLSX em
`app/hora/routes/pedidos.py:312` (`pedidos_importar_xlsx`) com:

- Parser `app/hora/services/parsers/pedido_xlsx_parser.py:435`
  (`parse_pedido_xlsx`) → retorna `PedidoExtraido`.
- Preview em cards (`pedido_importar_preview.html`) com triagem de CNPJ
  matriz HORA, resolucao automatica de loja por apelido, e desmarcar
  individual antes de confirmar.
- Confirmacao em batch cria `HoraPedido` para cada card marcado.

Este design adiciona um **fallback** que aceita imagem (JPG/PNG) e produz
o mesmo `PedidoExtraido`, eliminando a etapa manual XLSX intermediario.

## 2. Objetivos

- Operador sobe N imagens em `/hora/pedidos/importar-imagem` e ve o mesmo
  preview consolidado que ja existe para XLSX.
- Mesma triagem (CNPJ matriz HORA), mesma resolucao de loja, mesmo
  fluxo de confirmacao.
- XLSX equivalente gerado em background e disponivel para download
  posterior (auditoria) — nao bloqueia o operador.
- Origem do pedido auditavel (`HoraPedido.origem`).

**Nao-objetivos v1**:

- Substituir o fluxo XLSX atual (continua existindo).
- Suporte a multi-imagem por pedido (1 imagem = 1 pedido, igual ao XLSX
  hoje).
- OCR offline (Tesseract) — fica como Plano B se custos Anthropic
  explodirem.
- Tratamento automatico de imagens rotacionadas/distorcidas (Sonnet
  ja lida bem com isso na pratica).

## 3. Decisao de motor de OCR

**Sonnet 4.6** (`claude-sonnet-4-6`) primario e unico.

**Por que nao Haiku 4.5**: chassis longos (`LYDAE393XT1203290`,
`MCBRMIA2511270089`) sao o pior caso de OCR — sem contexto que ajude o
modelo a desambiguar `O` vs `0`, `X` vs `K`. Risco de chassi errado entrar
no sistema e alto. Volume HORA atual (~dezenas de prints/mes) nao
justifica economia. Sonnet historicamente erra menos em alfanumericos
sem dicionario.

**Por que nao Haiku-com-fallback-Sonnet**: padrao usado em parser DANFE
da CarVia, mas ali Haiku tem ancoras (codigos de produto, qtd_esperada).
Aqui o LLM tem so a imagem — nao ha sinal forte que detecte erro de
chassi alem de "JSON valido + soma fechando". Mais seguro ir direto
no Sonnet.

**Validacao pos-extracao** (independente do modelo) compensa qualquer
falha residual:

| Validacao | Acao |
|---|---|
| Soma `produtos[*][-1]` ≠ `total_declarado` ± R$ 0,01 | Warning no card (nao bloqueia) |
| Chassi `len<15` ou `len>18` ou nao-alfanumerico | `item.aviso='chassi_suspeito'`, UI destaca |
| Chassi duplicado no mesmo pedido | Warning |
| PALLET nao-numerico e nao-vazio (rejeita "????" mas aceita "A","B") | Warning |
| Data fora `DD/MM/AAAA` | Fallback `date.today()` (mesmo XLSX parser) |
| `len(produtos)==0` | Erro fatal — card descartado |

## 4. Arquitetura

```
imagem (JPG/PNG/WEBP)
    │
    ▼
┌────────────────────────────────────────────┐
│ pedido_imagem_parser.py (NOVO)              │
│   parse_pedido_imagem(bytes, nome, mime)    │
│   • Sonnet 4.6 (multimodal)                 │
│   • System prompt (regras chassi/motor BR)  │
│   • Output: dict no schema interno          │
│   • Validacao pos-extracao                  │
│   • Adapter dict→PedidoExtraido             │
└────────────────────────────────────────────┘
    │
    ▼
PedidoExtraido (mesmo formato XLSX)
    │
    ├──► triagem CNPJ matriz HORA (cnpj_matriz_presente)
    ├──► resolucao loja (resolver_loja_por_apelido)
    ├──► preview cards (template existente)
    ├──► confirm em batch (rota existente)
    │
    ▼
Apos criar HoraPedido (origem='IMAGEM'):
    ├──► upload imagem original ao S3 (sincrono)
    └──► enfileira RQ job → background:
              gerar XLSX equivalente
              upload S3 → hora_pedido.xlsx_origem_s3_key
```

**Principio**: parser de imagem e fonte alternativa de `PedidoExtraido`.
Tudo apos o parser reusa codigo existente sem modificacao.

## 5. Componentes

### 5.1 Arquivos novos

#### `app/hora/services/parsers/pedido_imagem_parser.py` (~250 LOC)

```python
def parse_pedido_imagem(
    image_bytes: bytes,
    nome_arquivo: str | None = None,
    mime_type: str = 'image/jpeg',
) -> PedidoExtraido:
    """Parseia imagem de pedido HORA via Sonnet 4.6.

    Levanta:
        PedidoParseError: API indisponivel, JSON invalido, ou produtos vazios.
    """

def _chamar_llm_visao(image_bytes: bytes, mime_type: str) -> dict:
    """POST imagem em base64 + system prompt para Anthropic Sonnet 4.6.

    Retorna dict bruto. Sem retry — se falhar, levanta a excecao para o
    caller tratar."""

def _validar_extracao(dict_bruto: dict) -> tuple[dict, list[str]]:
    """Aplica validacao pos-extracao. Retorna (dict_normalizado, warnings).

    Warnings vao para PedidoExtraido.avisos. Erros fatais levantam
    PedidoParseError."""

def _dict_para_pedido_extraido(
    d: dict, nome_arquivo: str | None,
) -> PedidoExtraido:
    """Converte dict do LLM em PedidoExtraido reusando helpers do XLSX parser
    (_normalizar_chassi, _normalizar_preco, _normalizar_modelo).

    Para metadados (CNPJ, data, UF, apelido), reusa regex do XLSX parser
    aplicando sobre o cliente_str + endereco_str + cidade_str do dict."""

# System prompt: adaptado de pb_pkg/extract_pedido.py com:
# - regras de chassi/motor da CarVia danfe_pdf_parser
# - exigencia de total_declarado para validacao
# - regras de preco BR ("5.750,00" → 5750.00)
SYSTEM_PROMPT = """Voce e um extrator de dados estruturados.
Recebe imagem de "PEDIDO DE VENDA - SCOOTER ELETRICA" e devolve JSON valido.

Schema obrigatorio:
{
  "cliente": "string (linha CLIENTE)",
  "cnpj": "string",
  "ie": "string",
  "endereco": "string",
  "bairro": "string",
  "cidade": "string (so o nome)",
  "estado": "string (UF)",
  "cep": "string",
  "telefone": "string",
  "email": "string",
  "contato": "string DD/MM/AAAA",
  "has_motor": true|false,
  "produtos": [[PRODUTO, CHASSI, COR, (MOTOR), PALLET, VALOR_UNITARIO], ...],
  "total_declarado": <float, valor lido na celula TOTAL>
}

Regras:
- has_motor=true: 6 elementos por linha [PRODUTO,CHASSI,COR,MOTOR,PALLET,VALOR]
- has_motor=false: 5 elementos [PRODUTO,CHASSI,COR,PALLET,VALOR]
- CHASSI: string, preserve apostrofo inicial se houver. Sao alfanumericos
  longos (15-18 chars). Cuidado com O vs 0, I vs 1, X vs K.
- VALOR: float (5.750,00 → 5750.00)
- total_declarado: leia a celula TOTAL na linha amarela do rodape
- Nao invente. Campo nao visivel = string vazia ""
- Devolva SOMENTE o JSON, sem cercas de codigo, sem prosa
"""
```

#### `app/hora/services/pedido_xlsx_builder.py` (~200 LOC)

Porta de `pb_pkg/pedido_builder.py` do Cowork (openpyxl). Funcao
`build_pedido_xlsx(pedido_id) -> bytes` carrega o `HoraPedido` + itens +
loja e gera XLSX no formato canonico HORA (mesma estrutura visual que o
print: header mesclado, bloco cliente, tabela com header cinza, fundo
verde no VALOR UNITARIO, linha TOTAL amarela com `=SUM()`).

#### `app/hora/workers/pedido_imagem_worker.py` (~80 LOC)

```python
def gerar_xlsx_para_pedido_imagem_job(pedido_id: int) -> dict:
    """Job RQ executado pelo worker_hora_pedidos.

    1. Carrega HoraPedido (verifica origem='IMAGEM' e xlsx_origem_s3_key
       IS NULL — idempotente).
    2. Gera XLSX via build_pedido_xlsx.
    3. Upload S3: hora/pedidos/imagem-import/<pedido_id>.xlsx
    4. UPDATE hora_pedido SET xlsx_origem_s3_key, xlsx_origem_gerado_em.
    5. Retorna {pedido_id, s3_key, gerado_em}.

    Falha nao trava o pedido — XLSX e nice-to-have."""
```

#### Migration `scripts/migrations/hora_40_pedido_imagem_origem.{py,sql}`

```sql
ALTER TABLE hora_pedido
  ADD COLUMN IF NOT EXISTS origem VARCHAR(20) DEFAULT 'XLSX' NOT NULL,
  ADD COLUMN IF NOT EXISTS imagem_origem_s3_key VARCHAR(500),
  ADD COLUMN IF NOT EXISTS xlsx_origem_s3_key VARCHAR(500),
  ADD COLUMN IF NOT EXISTS xlsx_origem_gerado_em TIMESTAMP;

-- Backfill: pedidos legados ficam com origem='XLSX' (default).
-- Pedidos manuais (sem upload) ficariam tambem 'XLSX' tecnicamente —
-- aceitavel, mas adicionar tag no service criar_pedido se origem nao
-- vier explicitamente: 'MANUAL' quando criado via /pedidos/novo.

-- Valores validos via CHECK:
ALTER TABLE hora_pedido
  ADD CONSTRAINT hora_pedido_origem_check
  CHECK (origem IN ('XLSX', 'IMAGEM', 'MANUAL'));
```

Python equivalente (`hora_40_pedido_imagem_origem.py`) com `create_app()`
+ verificacao before/after segue padrao `~/.claude/CLAUDE.md` "MIGRATIONS".

#### Template `app/templates/hora/pedido_importar_imagem.html`

Espelho de `pedido_importar.html` mas:

- `accept="image/jpeg,image/png,image/webp"` em vez de `.xlsx,.xls`
- Limites: 5 MB/imagem, 50 imagens/batch (imagens > XLSX em tamanho)
- Texto explicativo: "Suba prints do PEDIDO DE VENDA - SCOOTER ELETRICA.
  O sistema usa AI (Claude Sonnet 4.6) para extrair os dados."

### 5.2 Arquivos modificados

#### `app/hora/routes/pedidos.py`

Nova rota `pedidos_importar_imagem` (espelho de `pedidos_importar_xlsx`):

```python
@hora_bp.route('/pedidos/importar-imagem', methods=['GET', 'POST'])
@require_hora_perm('pedidos', 'criar')
def pedidos_importar_imagem():
    """Upload de N imagens → parseia cada uma via LLM → preview consolidado.

    Reusa _serializar_extracao_dict / _deserializar_extracao_dict — token
    carrega imagem_bytes_b64 + imagem_mime_type ao inves de xlsx_bytes.

    Apos confirmar, fluxo:
      1. criar_pedido(..., origem='IMAGEM', imagem_bytes=..., mime=...)
         (service uploada imagem ao S3 sincronamente)
      2. enqueue gerar_xlsx_para_pedido_imagem_job(pedido_id)
    """
```

Ajustes:

- `_serializar_extracao_dict`: aceita `imagem_bytes` ou `xlsx_bytes`
  (so um dos dois preenchido).
- `MAX_IMG_BYTES = 5 * 1024 * 1024`, `MAX_BATCH_IMG = 50`,
  `MAX_BATCH_BYTES_IMG = 100 MB`.
- `pedidos_importar_imagem_confirmar` (rota nova) ou estender
  `pedidos_importar_xlsx_confirmar` para detectar tipo via token e
  rotear (mais simples: rota nova dedicada).

#### `app/hora/services/pedido_service.py`

```python
def criar_pedido(
    *,
    numero_pedido,
    cnpj_destino,
    data_pedido,
    itens,
    criado_por=None,
    origem='MANUAL',                # NOVO — default MANUAL para criar_pedido manual
    imagem_bytes=None,                # NOVO — quando origem='IMAGEM'
    imagem_mime_type=None,            # NOVO
    xlsx_bytes=None,                  # NOVO — para guardar XLSX original quando origem='XLSX'
):
    """Mantem assinatura retrocompativel. Quando origem='IMAGEM',
    faz upload da imagem ao S3 e grava em imagem_origem_s3_key."""
```

Rota `pedidos_importar_xlsx_confirmar` passa `origem='XLSX'` e
`xlsx_bytes`.
Rota nova passa `origem='IMAGEM'` e `imagem_bytes`/`mime`.
Rota `pedidos_novo` (criar manual) passa `origem='MANUAL'`.

#### `app/templates/hora/pedido_detalhe.html`

Adiciona bloco "Origem":

```jinja
<div class="card mt-3">
  <div class="card-body">
    <h6>Origem do pedido</h6>
    {% if pedido.origem == 'IMAGEM' %}
      <span class="badge bg-info">📷 Imagem (Claude Sonnet 4.6)</span>
      <div class="mt-2">
        {% if pedido.imagem_origem_s3_key %}
          <a href="{{ url_for('hora.pedidos_baixar_imagem_origem', pedido_id=pedido.id) }}"
             class="btn btn-sm btn-outline-secondary">
            <i class="fas fa-image"></i> Baixar imagem original
          </a>
        {% endif %}
        {% if pedido.xlsx_origem_s3_key %}
          <a href="{{ url_for('hora.pedidos_baixar_xlsx_equivalente', pedido_id=pedido.id) }}"
             class="btn btn-sm btn-outline-success">
            <i class="fas fa-file-excel"></i> Baixar XLSX equivalente
          </a>
        {% else %}
          <span class="text-muted small">XLSX equivalente sendo gerado em background...</span>
        {% endif %}
      </div>
    {% elif pedido.origem == 'XLSX' %}
      <span class="badge bg-secondary">📊 XLSX importado</span>
    {% else %}
      <span class="badge bg-light text-dark">✏️ Manual</span>
    {% endif %}
  </div>
</div>
```

Mais 2 rotas `pedidos_baixar_imagem_origem` e `pedidos_baixar_xlsx_equivalente`
(redirecionam para presigned URL S3 — padrao `app/devolucao` e
`app/hora/services/venda_service.py`).

#### `app/templates/base.html`

Submenu HORA → Pedidos:

```jinja
<a class="dropdown-item" href="{{ url_for('hora.pedidos_importar_xlsx') }}">
  <i class="fas fa-file-excel"></i> Importar XLSX
</a>
<a class="dropdown-item" href="{{ url_for('hora.pedidos_importar_imagem') }}">
  <i class="fas fa-camera"></i> Importar Imagem (OCR)
</a>
```

#### Worker

Opcao A: estender `worker_hora_nfe.py` para escutar tambem queue
`hora_pedidos_imagem`.
Opcao B: criar `worker_hora_pedidos.py` dedicado.

**Recomendacao**: Opcao A (1 worker a menos para gerenciar; carga e
baixa). Adicionar `--queues hora_nfe,hora_pedidos_imagem` no comando.

### 5.3 Modelo

`HoraPedido` ganha 4 campos novos (migration 5.1):

| Campo | Tipo | Default | Descricao |
|---|---|---|---|
| `origem` | VARCHAR(20) NOT NULL | `'XLSX'` | `XLSX`/`IMAGEM`/`MANUAL` |
| `imagem_origem_s3_key` | VARCHAR(500) NULL | NULL | S3 key da imagem original (so se origem=IMAGEM) |
| `xlsx_origem_s3_key` | VARCHAR(500) NULL | NULL | S3 key do XLSX equivalente gerado em background |
| `xlsx_origem_gerado_em` | TIMESTAMP NULL | NULL | Quando o job RQ gerou o XLSX |

CHECK constraint em `origem`.

## 6. Fluxo detalhado

### 6.1 Upload (sincrono)

```
1. POST /hora/pedidos/importar-imagem
   Form-data: imagens[] (N arquivos)

2. Validacoes:
   • len(imagens) <= 50
   • cada imagem <= 5 MB
   • soma <= 100 MB
   • mime in {image/jpeg, image/png, image/webp}

3. Para cada imagem:
   a. parse_pedido_imagem(bytes, nome, mime):
      - chamar Sonnet 4.6 com imagem em base64
      - extrai JSON da resposta (regex robusta)
      - valida (soma=total_declarado, chassi 15-18 chars, ...)
      - converte para PedidoExtraido
   b. cnpj_matriz_presente(extracao.cnpjs_candidatos):
      - se False → card descartado com erro
   c. resolver_loja_por_apelido(extracao.apelido_detectado):
      - sugere loja_destino, mostra mensagem de match
   d. Card vai para preview

4. Preview consolidado (mesmo template do XLSX):
   • Cada card mostra: nome arquivo, tamanho, loja sugerida,
     itens extraidos, avisos (incluindo "Total nao fecha", "Chassi
     suspeito" do passo 3.a)
   • Operador desmarca/edita loja/confirma
```

### 6.2 Confirmacao (sincrono + assincrono)

```
5. POST /hora/pedidos/importar-imagem/confirmar
   Form-data: token, incluir_idx[], loja_id_<idx> (override)

6. Para cada idx em incluir_indices:
   a. Reconstruct PedidoExtraido + imagem_bytes do token
   b. pedido_service.criar_pedido(
        ...,
        origem='IMAGEM',
        imagem_bytes=imagem_bytes,
        imagem_mime_type=mime,
      )
      • Service: cria HoraPedido + itens
      • Service: upload imagem ao S3 hora/pedidos/imagem-import/<id>.<ext>
      • Service: SET imagem_origem_s3_key
      • Service: COMMIT
   c. RQ enqueue gerar_xlsx_para_pedido_imagem_job(pedido_id)
      • queue 'hora_pedidos_imagem'
      • timeout 120s, retry 2

7. Redirect → lista pedidos com flash "N pedidos criados via imagem.
   XLSX equivalente sera gerado em segundos."
```

### 6.3 Background (worker)

```
Worker pega job:
1. Carrega HoraPedido + itens + loja
2. Monta dict (cliente, cnpj, endereco, contato, has_motor, produtos[])
3. build_pedido_xlsx(pedido) → bytes
4. Upload S3 → hora/pedidos/imagem-import/<pedido_id>.xlsx
5. UPDATE hora_pedido SET xlsx_origem_s3_key, xlsx_origem_gerado_em
6. Audit: HoraPedidoAuditoria action='XLSX_GERADO_EM_BACKGROUND'
   (se modulo de auditoria de pedido existir; senao, log info)
```

### 6.4 Error handling

| Cenario | Comportamento |
|---|---|
| ANTHROPIC_API_KEY ausente | Rota retorna 503 com mensagem clara |
| Anthropic API timeout/erro | Card com erro, operador retry |
| Sonnet retorna JSON invalido | Card com erro, log da resposta bruta |
| Soma ≠ total_declarado | Warning visivel no card (nao bloqueia) |
| Chassi suspeito (len ou nao-alfa) | aviso='chassi_suspeito', destaque visual no preview |
| CNPJ matriz ausente | Card descartado (mesma triagem do XLSX) |
| Apelido nao casa com loja | Card mostra "selecionar manualmente" |
| Imagem corrompida/formato invalido | Erro na decodificacao, card com erro |
| Job XLSX falha | UPDATE nao acontece, mas pedido segue normal — XLSX e nice-to-have |

## 7. Testes

`tests/hora/test_pedido_imagem_parser.py`:

1. Mock Sonnet retorna dict valido (Praia Grande, 2 itens, sem motor) →
   PedidoExtraido com loja sugerida correta.
2. Mock Sonnet retorna dict valido (Tatuape, 8 itens, com motor) →
   has_motor=True respeitado.
3. Mock Sonnet retorna `total_declarado=11.500` mas itens somam 11.450 →
   warning "Total nao fecha".
4. Mock retorna chassi com `len=14` → `item.aviso='chassi_suspeito'`.
5. Mock retorna chassi duplicado → warning de duplicidade.
6. Mock retorna CNPJ matriz ausente → triagem rejeita.
7. Mock retorna `produtos=[]` → PedidoParseError.
8. JSON invalido na resposta do mock → PedidoParseError com log.
9. Apelido "MOTOCHEFE PRAIA GRANDE" → resolve loja_id correto.

`tests/hora/test_pedido_xlsx_builder.py`:

1. Dict has_motor=True → XLSX 6 colunas, formula =SUM() em VALOR.
2. Dict has_motor=False → XLSX 5 colunas.
3. Roundtrip: builder → bytes → re-parse com `parse_pedido_xlsx` →
   mesmo PedidoExtraido (validacao final do contrato).

`tests/hora/test_pedidos_importar_imagem.py` (integracao):

1. Upload de imagem mockada → parse → preview render.
2. Confirmacao cria HoraPedido com `origem='IMAGEM'` e
   `imagem_origem_s3_key` preenchido.
3. RQ job enfileirado (mock RQ).
4. Permissao `pedidos/criar` aplicada (decorator `require_hora_perm`).

Sem teste de integracao real com Anthropic API — usa mock. Validacao
manual com as 3 imagens reais ja anexadas (Praia Grande, Tatuape,
Bragança).

## 8. Riscos e mitigacoes

| Risco | Mitigacao |
|---|---|
| Custo Anthropic | Sonnet 4.6 ≈ $0.01/imagem. 100 prints/mes = $1. Aceitavel. Se volume crescer 10x, reavaliar Haiku-fallback. |
| LLM extrai chassi errado (`O` vs `0`) | (1) validacao soma; (2) chassi suspeito por len; (3) preview obrigatorio antes de confirmar. |
| Layout muda no futuro | System prompt declarativo. Sonnet lida com variacoes. Validacao detecta extracao quebrada. |
| Job XLSX trava worker | Job bem leve (~1s). Timeout 120s + retry 2. Falha nao trava pedido. |
| Imagem rotacionada/escura | Sonnet lida bem. Caso extremo: card vem sem dados, operador refoto. |
| ANTHROPIC_API_KEY ausente em prod | Boot do app verifica e log warning. Rota retorna 503 com mensagem clara. |
| S3 down ao salvar imagem original | Cria pedido sem imagem (warning), nao bloqueia. Job XLSX nao roda nesse caso. |

## 9. Plano de implementacao (alto-nivel)

Detalhes virao no plano executavel. Resumo de fases:

1. **Migration `hora_40`** — adicionar campos em `hora_pedido`.
2. **Parser de imagem** — `pedido_imagem_parser.py` + system prompt + validacao.
3. **Adapter dict→PedidoExtraido** — reuso de helpers do XLSX parser.
4. **Builder XLSX** — porta de `pb_pkg/pedido_builder.py`.
5. **Worker + job RQ** — `pedido_imagem_worker.py`.
6. **Service** — extender `pedido_service.criar_pedido` com kwargs novos +
   upload S3.
7. **Rotas** — `pedidos_importar_imagem` + confirm + downloads.
8. **Templates** — `pedido_importar_imagem.html` + ajustes em
   `pedido_detalhe.html` + link em `base.html`.
9. **Worker setup** — adicionar queue `hora_pedidos_imagem` no
   `worker_hora_nfe.py`.
10. **Testes** — unit (parser/builder) + integracao (rotas).
11. **Validacao manual** — subir as 3 imagens reais e confirmar
    pedidos criados.

**Estimativa**: 1-2 sessoes de implementacao.

## 10. Referencias

- Parser XLSX existente: `app/hora/services/parsers/pedido_xlsx_parser.py:435`
- Rota XLSX existente: `app/hora/routes/pedidos.py:312`
- Pacote do Cowork (base do builder): `/mnt/c/Users/rafael.nascimento/Downloads/pb_pkg/`
- Padrao parser DANFE multimodal: `app/carvia/services/parsers/danfe_pdf_parser.py`
- CLAUDE.md HORA: `app/hora/CLAUDE.md`
- Regra de migrations duais: `~/.claude/CLAUDE.md` secao MIGRATIONS
- Imagens de teste: `/mnt/c/Users/rafael.nascimento/Downloads/WhatsApp Image 2026-05-08 at 11.24.{32,33,33 (1)}.jpeg`
