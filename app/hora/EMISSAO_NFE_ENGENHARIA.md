# Engenharia de Emissão de NF-e de Venda — Lojas HORA

**Data**: 2026-04-24
**Status**: Desenho aprovado, pendente de implementação.
**Escopo**: Emissão de NF-e de venda (saída, B2C, consumidor final) das lojas HORA para a SEFAZ, via API TagPlus.
**Fora de escopo**: Emissão de NFC-e (cupom fiscal), NF-e de entrada, transferência entre filiais, devolução. Tratar em fase 2.

---

## 1. Posicionamento e fronteira

### 1.1 Por que módulo novo, separado do existente

O código em `app/integracoes/tagplus/` atende a **Nacom Goya** (indústria alimentícia) importando NFs de terceiros (B2B). **NÃO pode ser reusado diretamente** para HORA por três razões:

| Diferença | Nacom existente | HORA novo |
|---|---|---|
| Sentido | Importa NF (entrada) emitida por fornecedor | Emite NF (saída) própria da loja |
| Tenant TagPlus | Conta única Nacom | Conta única HORA (todas as lojas faturam pelo mesmo CNPJ — modelo single-tenant) |
| Persistência de token | Flask session (`session['tagplus_notas_access_token']`) | Banco (token por loja, compartilhado entre requests/workers) |
| Domínio | `FaturamentoProduto`, `RelatorioFaturamentoImportado` | `HoraVenda`, `HoraVendaItem`, `HoraMoto`, `HoraLoja` |
| Fluxo | Síncrono (GET listar/detalhar) | Assíncrono (POST criar → aguardar webhook SEFAZ → atualizar venda) |
| Escopo OAuth | `read:nfes` | `write:nfes` + `read:clientes` + `write:clientes` |

### 1.2 O que reaproveitar

**Permitido via import direto** (utilitários puros, sem estado Nacom):

- `app/utils/timezone.py` — `agora_utc_naive()`.
- `app/utils/json_helpers.py` — `sanitize_for_json()` (body do POST tem `Decimal` de preço).

**Permitido via adapter / cópia adaptada** (lógica OAuth2 genérica do TagPlus):

- **Lógica** do `app/integracoes/tagplus/oauth2_v2.py`:
  - Pattern de `authorize/callback/token exchange/refresh`.
  - Tratamento de 401 → refresh automático.
  - Header `X-Api-Version: 2.0`.

  **Não importar** a classe `TagPlusOAuth2V2` diretamente — ela persiste em `session[...]`, o que quebra no worker RQ (sem request ativo) e mistura credenciais HORA com as da Nacom. Criar `app/hora/services/tagplus/oauth_client.py` com a lógica equivalente mas com persistência em DB (`hora_tagplus_token`).

**Proibido** (viola fronteira `app/hora/CLAUDE.md`):

- Importar de `app/integracoes/tagplus/*` código que mexa com modelos Nacom (`FaturamentoProduto`, `RelatorioFaturamentoImportado`, `CarteiraPrincipal`).
- Reusar `ImportadorTagPlusV2`, `ProcessadorFaturamento`, `correcao_pedidos_service.py`.
- Usar `session` Flask para persistir tokens (tem que funcionar fora de request, em worker RQ).

### 1.3 Onde ficam os arquivos novos

```
app/hora/
├── models/
│   └── tagplus.py                   # 4 tabelas novas (ver §3)
├── services/
│   └── tagplus/
│       ├── __init__.py
│       ├── oauth_client.py          # OAuth2 com persistência DB (espelha oauth2_v2 sem session)
│       ├── api_client.py            # wrapper HTTP autenticado (GET/POST/PATCH com retry e refresh)
│       ├── emissor_nfe.py           # monta payload + dispara POST /nfes
│       ├── payload_builder.py       # traduz HoraVenda → JSON TagPlus
│       ├── webhook_handler.py       # processa callback nfe_aprovada / nfe_rejeitada
│       ├── cancelador_nfe.py        # PATCH /nfes/cancelar/{id}
│       └── cce_service.py           # POST /nfes/gerar_cce/{id}
├── workers/
│   └── emissao_nfe_worker.py        # RQ worker: consome fila, chama emissor
├── routes/
│   └── tagplus_routes.py            # /hora/tagplus/oauth/*, /hora/tagplus/webhook/*
└── templates/hora/tagplus/
    ├── conta_lista.html             # tela de cadastro de contas TagPlus por loja
    └── oauth_result.html            # resultado do callback OAuth
scripts/migrations/
├── hora_16_tagplus.py
└── hora_16_tagplus.sql
```

---

## 2. Visão de fluxo (alto nível)

### 2.1 Diagrama conceitual

```
┌───────────────┐     1 usuario conclui      ┌────────────────────┐
│  HoraVenda    │──────────venda───────────> │  status=CONCLUIDA  │
│  (UI /hora)   │                            │  nf_saida_* = NULL │
└───────────────┘                            └────────┬───────────┘
                                                      │ 2 trigger (service)
                                                      ▼
                                  ┌───────────────────────────────────┐
                                  │  HoraNfeEmissao (insert)          │
                                  │  status=PENDENTE, venda_id=X      │
                                  │  enqueue job RQ (queue=hora_nfe)  │
                                  └────────┬──────────────────────────┘
                                           │ 3 worker RQ
                                           ▼
                      ┌────────────────────────────────────────────────┐
                      │  EmissorNfeHora.emitir(emissao_id)             │
                      │  - get_token(loja_id)  (refresh se expirado)   │
                      │  - payload = PayloadBuilder.build(venda)       │
                      │  - POST /nfes com X-Enviar-Nota: true          │
                      │  - response 201 ou 202:                        │
                      │      status=ENVIADA_SEFAZ, tagplus_id, numero  │
                      │    response erro 4xx:                          │
                      │      status=REJEITADA_LOCAL, error_code/msg    │
                      └────────┬───────────────────────────────────────┘
                               │ 4 async (minutos)
                               ▼
         ┌──────────────────────────────────────────────────────────┐
         │  TagPlus envia POST webhook /hora/tagplus/webhook/<loja> │
         │  body: {event_type: "nfe_aprovada", data: [{id: 7123}]}  │
         └────────┬─────────────────────────────────────────────────┘
                  │ 5 WebhookHandler
                  ▼
         ┌─────────────────────────────────────────────────────────┐
         │  - valida X-Hub-Secret                                   │
         │  - GET /nfes/{id}  (baixa chave, numero, xml, status)    │
         │  - update HoraNfeEmissao.status = APROVADA               │
         │  - update HoraVenda.nf_saida_numero / chave_44 / emit_em │
         │  - insert HoraMotoEvento(tipo=NF_EMITIDA) por chassi     │
         └─────────────────────────────────────────────────────────┘
```

### 2.2 Estados da emissão (`HoraNfeEmissao.status`)

```
PENDENTE ──enqueue──> EM_ENVIO ──POST 201/202──> ENVIADA_SEFAZ ──webhook──> APROVADA
                          │                            │                       │
                          │ POST 4xx/5xx               │ webhook nfe_rejeitada │
                          ▼                            ▼                       │
                    REJEITADA_LOCAL              REJEITADA_SEFAZ               │
                          │                            │                       │
                          └────retry manual────────────┘                       │
                                                                               │
                                               ┌──── cancelamento ─────────────┘
                                               ▼
                                           CANCELADA
```

Máquina de estados:

| De | Para | Gatilho |
|---|---|---|
| `PENDENTE` | `EM_ENVIO` | worker retira da fila |
| `EM_ENVIO` | `ENVIADA_SEFAZ` | POST /nfes retorna 201/202 |
| `EM_ENVIO` | `REJEITADA_LOCAL` | POST /nfes retorna 4xx (falta tributação, campo inválido, etc.) |
| `EM_ENVIO` | `ERRO_INFRA` | POST /nfes retorna 5xx ou timeout → retry com backoff |
| `ENVIADA_SEFAZ` | `APROVADA` | webhook `nfe_aprovada` |
| `ENVIADA_SEFAZ` | `REJEITADA_SEFAZ` | webhook `nfe_rejeitada` |
| `APROVADA` | `CANCELADA` | PATCH /nfes/cancelar/{id} confirmado via webhook `nfe_cancelada` |

---

## 3. Modelo de dados (4 tabelas novas, prefixo `hora_tagplus_`)

### 3.1 `hora_tagplus_conta`

**Singleton**: todas as lojas HORA faturam pelo mesmo CNPJ, portanto a tabela tem **1 linha ativa** apenas. O modelo de tabela (em vez de constantes em env) é preservado para: permitir rotação de credenciais sem redeploy, armazenar tokens criptografados, e manter histórico de cadastros anteriores desativados.

```python
class HoraTagPlusConta(db.Model):
    __tablename__ = 'hora_tagplus_conta'

    id = db.Column(db.Integer, primary_key=True)

    client_id = db.Column(db.String(64), nullable=False)
    client_secret_encrypted = db.Column(db.Text, nullable=False)
    # Encriptar com Fernet/cryptography usando chave em env HORA_TAGPLUS_ENC_KEY.
    # Nunca armazenar secret em plaintext.

    webhook_secret = db.Column(db.String(64), nullable=False)
    # Token compartilhado em X-Hub-Secret. Gerado com secrets.token_urlsafe(32) no cadastro.

    # Padrão anti-CSRF para o OAuth redirect:
    oauth_state_last = db.Column(db.String(64), nullable=True)

    scope_contratado = db.Column(db.String(255), nullable=False,
                                  default='write:nfes read:clientes write:clientes read:produtos')

    ativo = db.Column(db.Boolean, nullable=False, default=True)
    # Constraint de unicidade parcial (ver SQL na §11): só uma linha com ativo=TRUE por vez.

    # Ambiente: producao|homologacao. TagPlus não tem ambiente de homologação separado — NFe é
    # emitida em produção sempre. Usar este campo para bloquear emissão real em ambiente dev.
    ambiente = db.Column(db.String(15), nullable=False, default='producao')

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    @classmethod
    def ativa(cls) -> 'HoraTagPlusConta':
        """Retorna a única conta ativa. Levanta se nenhuma configurada."""
        conta = cls.query.filter_by(ativo=True).first()
        if not conta:
            raise RuntimeError('Nenhuma conta TagPlus HORA ativa — configurar em /hora/tagplus/conta')
        return conta
```

### 3.2 `hora_tagplus_token`

Tokens OAuth2 persistidos (NÃO na sessão Flask).

```python
class HoraTagPlusToken(db.Model):
    __tablename__ = 'hora_tagplus_token'

    id = db.Column(db.Integer, primary_key=True)
    conta_id = db.Column(db.Integer, db.ForeignKey('hora_tagplus_conta.id'),
                         nullable=False, unique=True, index=True)
    # unique: só 1 token válido por conta. Refresh substitui a linha (UPDATE).

    access_token_encrypted = db.Column(db.Text, nullable=False)
    refresh_token_encrypted = db.Column(db.Text, nullable=False)
    token_type = db.Column(db.String(20), nullable=False, default='bearer')

    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    # TagPlus: expires_in=86400 (24h). Armazenar timestamp absoluto.

    obtido_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    refreshed_em = db.Column(db.DateTime, nullable=True)

    conta = db.relationship('HoraTagPlusConta', backref=db.backref('token', uselist=False))
```

### 3.3 `hora_tagplus_produto_map`

De-para entre `HoraModelo` (nosso catálogo) e o produto cadastrado no TagPlus. Como há **1 só CNPJ emissor**, o cadastro de produtos no TagPlus também é único — dispensa `conta_id`.

```python
class HoraTagPlusProdutoMap(db.Model):
    __tablename__ = 'hora_tagplus_produto_map'

    id = db.Column(db.Integer, primary_key=True)
    modelo_id = db.Column(db.Integer, db.ForeignKey('hora_modelo.id'),
                          nullable=False, unique=True, index=True)
    # unique: 1 mapeamento por modelo. Para trocar o produto TagPlus, atualiza a linha.

    tagplus_produto_id = db.Column(db.Integer, nullable=False)
    # ID do produto no TagPlus (endpoint /produtos/{id}). Obrigatório pois POST /nfes
    # referencia item.produto como inteiro (ver doc_tagplus.md:638).

    tagplus_codigo = db.Column(db.String(50), nullable=True)
    # Opcional, só para debug/exibição na tela de mapeamento.

    cfop_default = db.Column(db.String(4), nullable=False, default='5102')
    # 5102 = venda dentro do estado. 6102 = fora do estado.
    # Como a emissão sai sempre do mesmo CNPJ (UF fixa), o PayloadBuilder escolhe entre
    # os dois comparando loja.uf (da loja que vendeu) com cliente.uf (destinatário).
    # Campo fica como fallback quando a UF do cliente = UF do emitente.

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
```

### 3.4 `hora_tagplus_nfe_emissao`

Fila + histórico de emissões. É a **fonte de verdade** para status de emissão.

```python
class HoraTagPlusNfeEmissao(db.Model):
    __tablename__ = 'hora_tagplus_nfe_emissao'

    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(db.Integer, db.ForeignKey('hora_venda.id'),
                         nullable=False, unique=True, index=True)
    # unique: 1 emissão ativa por venda. Para re-emitir, atualiza a linha (não insere nova).
    # Se precisar histórico de tentativas, ver tabela hora_tagplus_nfe_tentativa abaixo.

    conta_id = db.Column(db.Integer, db.ForeignKey('hora_tagplus_conta.id'),
                         nullable=False, index=True)
    # Sempre a conta ativa no momento da emissão. Persistir facilita investigação histórica
    # caso a conta seja rotacionada (client_secret trocado) entre emissões.

    status = db.Column(db.String(30), nullable=False, default='PENDENTE', index=True)
    # PENDENTE, EM_ENVIO, ENVIADA_SEFAZ, APROVADA, REJEITADA_LOCAL,
    # REJEITADA_SEFAZ, ERRO_INFRA, CANCELADA

    # Dados retornados pelo TagPlus
    tagplus_nfe_id = db.Column(db.Integer, nullable=True, index=True)
    # ID interno no TagPlus (retornado em POST 201/202).

    numero_nfe = db.Column(db.String(20), nullable=True)
    serie_nfe = db.Column(db.String(5), nullable=True)
    chave_44 = db.Column(db.String(44), nullable=True, unique=True)
    protocolo_aprovacao = db.Column(db.String(30), nullable=True)

    # Auditoria
    payload_enviado = db.Column(db.JSON, nullable=True)
    # JSONB com body do POST /nfes. Sanitizar com sanitize_for_json() (contém Decimal).
    # Crítico para debug de rejeição e para reprocessar após correção de cadastro.

    response_inicial = db.Column(db.JSON, nullable=True)
    # body da resposta 201/202 ou do erro 4xx.

    response_webhook = db.Column(db.JSON, nullable=True)
    # body do GET /nfes/{id} após webhook nfe_aprovada.

    error_code = db.Column(db.String(60), nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    tentativas = db.Column(db.Integer, nullable=False, default=0)

    enviado_em = db.Column(db.DateTime, nullable=True)
    aprovado_em = db.Column(db.DateTime, nullable=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    venda = db.relationship('HoraVenda', backref=db.backref('emissao_nfe', uselist=False))
    conta = db.relationship('HoraTagPlusConta')
```

**Decisão**: não criar `hora_tagplus_nfe_tentativa` (histórico granular) na v1. O `payload_enviado` + `response_inicial` + `tentativas` no próprio registro cobrem 95% dos casos. Se houver necessidade real de auditoria multi-tentativa, criar na v2.

---

## 4. Payload builder — tradução `HoraVenda` → JSON TagPlus

Este é o núcleo crítico. A API TagPlus `POST /nfes` é descrita em `scripts/doc_tagplus.md:142-489`.

### 4.1 Campos obrigatórios (doc_tagplus.md:161-178)

| Campo TagPlus | Origem HORA | Observação |
|---|---|---|
| `destinatario` (int) | cliente no TagPlus, resolver via `GET /clientes?cpf_cnpj=<cpf>` antes do POST; criar via `POST /clientes` se não existir | Ver §4.3 |
| `itens` (array) | `HoraVendaItem` (1 item por chassi vendido) | Ver §4.2 |
| `cfop` (string) | `hora_tagplus_produto_map.cfop_default` ajustado por UF do cliente | 5102 intra / 6102 inter |

### 4.2 Estrutura de `itens[]`

```python
# Para cada HoraVendaItem:
{
    "produto": tagplus_produto_id,        # de hora_tagplus_produto_map
    "qtd": 1,                             # sempre 1 (chassi é unitário)
    "valor_unitario": float(preco_final), # HoraVendaItem.preco_final (sanitize_for_json!)
    "valor_desconto": float(desconto_aplicado),
    "valor_total_item": float(preco_final),
    "inf_adicional": f"Chassi: {numero_chassi} / Motor: {numero_motor}",
    # TagPlus permite inf_adicional por item (verificar no schema completo em doc_tagplus.md)
    # -- se não existir, concatenar em nfe.inf_contribuinte no nível da nota.

    "numero_pedido_compra": str(venda_id),     # rastreabilidade inversa
}
```

### 4.3 Destinatário (cliente)

**Fluxo de resolução** (implementar em `payload_builder.py:_resolver_destinatario`):

```
1. GET /clientes?cpf_cnpj={cpf_cliente_sem_mascara}&fields=id
2. Se retornar 1 item: usar id
3. Se retornar 0: POST /clientes com:
   {
     "tipo": "F",
     "nome": nome_cliente,
     "cpf": cpf_cliente_sem_mascara,
     "telefone": telefone_cliente,
     "email": email_cliente,
     "enderecos": [...]  // se disponível; senão, cliente sem endereço é aceito para CPF
   }
   Retorna id → usar.
4. Se retornar >1: erro de negócio (CPF duplicado no TagPlus). Marcar emissão como
   REJEITADA_LOCAL com error_code="destinatario_ambiguo" — exige intervenção manual.
```

**Cacheável**: não. A cada emissão, re-consultar por CPF. Custo de latência é trivial (< 300ms) e evita NF com dados desatualizados.

### 4.4 Campos derivados importantes

```python
{
    "tipo": "S",                       # Saída
    "finalidade_emissao": 1,           # Normal
    "consumidor_final": True,          # B2C
    "indicador_presenca": 1,           # Operação presencial (loja física HORA)
    "tipo_emissao": 1,                 # Normal (não contingência)
    "modalidade_frete": 9,             # Sem frete (cliente leva a moto)
    "data_emissao": agora_utc_naive().isoformat(),
    "data_entrada_saida": date.today().isoformat(),
    "cfop": cfop_por_uf(cliente_uf, loja.uf),  # 5102 intra / 6102 inter

    "valor_desconto": sum(item.desconto_aplicado for item in venda.itens),
    "valor_nota": sum(item.preco_final for item in venda.itens),  # == venda.valor_total

    "faturas": _montar_faturas(venda),  # ver §4.5

    # Identificação da loja operacional vai como informação complementar — a NF em si
    # é sempre emitida pelo CNPJ raiz. Operador, loja e vendedor constam como texto:
    "inf_contribuinte": (
        f"Venda #{venda.id} | Loja: {venda.loja.display_name} | "
        f"Vendedor: {venda.vendedor or '-'}"
    ),
    "numero_pedido": str(venda.id),
}
```

**Endereço de emissão por loja** (opcional — consultar contabilidade):

Se a contabilidade exigir que o endereço físico da loja apareça no DANFE (mesmo sendo tudo um CNPJ), o TagPlus permite via `endereco_emitente` e `endereco_retirada` (`scripts/doc_tagplus.md:476-483`), ambos referenciando `/enderecos_entidades`. Isso exige:

1. Cadastrar cada endereço de loja como "endereço adicional" do emitente no TagPlus.
2. Mapear `HoraLoja.id` → `tagplus_endereco_id` (adicionar coluna `tagplus_endereco_retirada_id` em `hora_loja`).
3. Builder inclui `"endereco_retirada": loja.tagplus_endereco_retirada_id` no payload.

**Recomendação v1**: não modelar isso. Toda NF sai pelo endereço principal do emitente e a loja vai em `inf_contribuinte`. Escalar para v2 apenas se contabilidade pedir explicitamente.

### 4.5 Forma de pagamento → `faturas[]`

`HoraVenda.forma_pagamento` enum: `PIX, CARTAO_CREDITO, DINHEIRO, MISTO`.

O TagPlus tem `faturas` como array de objetos `Fatura Pagamento` (ver schema completo em `doc_tagplus.md`). Mapeamento sugerido:

| HORA | TagPlus `forma_pagamento.codigo` |
|---|---|
| `PIX` | `17` (PIX) |
| `CARTAO_CREDITO` | `03` (Cartão de Crédito) |
| `DINHEIRO` | `01` (Dinheiro) |
| `MISTO` | requer campo extra (não tratar na v1; bloquear emissão com erro claro) |

**Validação importante**: se `faturas[]` estiver vazia, TagPlus retorna `nota_sem_faturamento` (`scripts/guia.md:383`). Sempre preencher pelo menos uma fatura.

### 4.6 Sanitização obrigatória

Todos os valores monetários em `HoraVenda/HoraVendaItem` são `Numeric(15,2)` → `Decimal`. Antes de atribuir a `HoraTagPlusNfeEmissao.payload_enviado` (`db.JSON`), passar por `sanitize_for_json()` (ver `~/.claude/CLAUDE.md` seção "JSON SANITIZATION").

Para o HTTP request em si, `requests` / `httpx` convertem `Decimal` se passar `json=dict` direto — mas é mais seguro converter para `float` no builder para garantir que o TagPlus receba números JSON válidos.

---

## 5. Fluxo de emissão detalhado

### 5.1 Gatilho (serviço `venda_service.py`)

No momento em que `HoraVenda.status` passa para `CONCLUIDA`:

```python
from app.hora.services.tagplus.emissor_nfe import EmissorNfeHora

def concluir_venda(venda: HoraVenda, usuario):
    # ... validações ...
    venda.status = 'CONCLUIDA'
    db.session.flush()

    # Cria registro de emissão + enqueue
    EmissorNfeHora.enfileirar(venda_id=venda.id)

    db.session.commit()
```

**Regra**: nunca emitir síncrono no request do checkout. Checkout completa em <200ms; emissão TagPlus pode levar 5-30s (SEFAZ + rede).

### 5.2 Enfileiramento

```python
# app/hora/services/tagplus/emissor_nfe.py
from rq import Queue
from app import db
from app.hora.models.tagplus import HoraTagPlusNfeEmissao, HoraTagPlusConta

class EmissorNfeHora:
    @staticmethod
    def enfileirar(venda_id: int) -> int:
        venda = HoraVenda.query.get_or_404(venda_id)

        conta = HoraTagPlusConta.ativa()  # singleton — única conta ativa no sistema

        emissao = HoraTagPlusNfeEmissao.query.filter_by(venda_id=venda_id).first()
        if emissao and emissao.status in ('APROVADA', 'EM_ENVIO'):
            # idempotência: não re-enfileira se já aprovada ou em envio
            return emissao.id

        if not emissao:
            emissao = HoraTagPlusNfeEmissao(
                venda_id=venda_id,
                conta_id=conta.id,
                status='PENDENTE',
            )
            db.session.add(emissao)
        else:
            # retry de emissão rejeitada
            emissao.status = 'PENDENTE'
            emissao.tentativas = (emissao.tentativas or 0) + 1
            emissao.error_code = None
            emissao.error_message = None

        db.session.flush()

        queue = Queue('hora_nfe', connection=redis_conn)
        queue.enqueue(
            'app.hora.workers.emissao_nfe_worker.processar_emissao',
            emissao.id,
            retry=Retry(max=3, interval=[10, 60, 300]),  # retry p/ erros transientes
        )
        return emissao.id
```

### 5.3 Worker RQ

```python
# app/hora/workers/emissao_nfe_worker.py
from app import create_app
from app.hora.services.tagplus.emissor_nfe import EmissorNfeHora

def processar_emissao(emissao_id: int):
    app = create_app()
    with app.app_context():
        EmissorNfeHora.processar(emissao_id)
```

O worker é iniciado em `worker_hora_nfe.py` (novo, à raiz):

```python
# worker_hora_nfe.py
from rq import Worker, Queue, Connection
from redis import Redis
from app import create_app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        redis_conn = Redis.from_url(app.config['REDIS_URL'])
        with Connection(redis_conn):
            worker = Worker([Queue('hora_nfe')])
            worker.work()
```

### 5.4 Método `processar`

```python
# app/hora/services/tagplus/emissor_nfe.py
@staticmethod
def processar(emissao_id: int):
    emissao = HoraTagPlusNfeEmissao.query.get(emissao_id)
    if not emissao or emissao.status not in ('PENDENTE', 'ERRO_INFRA'):
        return  # idempotência

    emissao.status = 'EM_ENVIO'
    emissao.enviado_em = agora_utc_naive()
    db.session.commit()

    try:
        venda = emissao.venda
        conta = emissao.conta
        client = ApiClient(conta)  # resolve token + refresh

        payload = PayloadBuilder(conta).build(venda)
        emissao.payload_enviado = sanitize_for_json(payload)
        db.session.commit()

        response = client.post('/nfes', json=payload, headers={
            'X-Enviar-Nota': 'true',
            'X-Calculo-Trib-Automatico': 'true',
            'X-Api-Version': '2.0',
        })

        if response.status_code in (201, 202):
            body = response.json()
            emissao.status = 'ENVIADA_SEFAZ'
            emissao.tagplus_nfe_id = body.get('id')
            emissao.numero_nfe = body.get('numero')
            emissao.serie_nfe = body.get('serie')
            emissao.response_inicial = body
            # chave_44, protocolo, xml virão via webhook nfe_aprovada.

        elif 400 <= response.status_code < 500:
            body = response.json()
            emissao.status = 'REJEITADA_LOCAL'
            emissao.error_code = body.get('error_code')
            emissao.error_message = body.get('message') or body.get('dev_message')
            emissao.response_inicial = body

        else:  # 5xx
            emissao.status = 'ERRO_INFRA'
            emissao.error_message = f'HTTP {response.status_code}'
            raise RetryableError()  # RQ retry

    except (ConnectionError, Timeout):
        emissao.status = 'ERRO_INFRA'
        emissao.error_message = 'Timeout/rede'
        db.session.commit()
        raise  # RQ retry

    finally:
        db.session.commit()
```

### 5.5 Webhook receiver

```python
# app/hora/routes/tagplus_routes.py
@hora_bp.route('/tagplus/webhook', methods=['POST'])
def tagplus_webhook():
    conta = HoraTagPlusConta.ativa()

    # Valida X-Hub-Secret em tempo constante
    secret_recebido = request.headers.get('X-Hub-Secret', '')
    if not hmac.compare_digest(secret_recebido, conta.webhook_secret):
        return jsonify({'error': 'secret inválido'}), 401

    body = request.get_json(force=True)
    event_type = body.get('event_type')
    data = body.get('data', [])

    # Enfileira processamento para responder 200 rápido ao TagPlus
    queue = Queue('hora_nfe', connection=redis_conn)
    queue.enqueue(
        'app.hora.workers.emissao_nfe_worker.processar_webhook',
        conta.id, event_type, data,
    )
    return jsonify({'ok': True}), 200
```

### 5.6 Handler do webhook

```python
# app/hora/services/tagplus/webhook_handler.py
class WebhookHandler:
    @staticmethod
    def processar(conta_id: int, event_type: str, data: list[dict]):
        conta = HoraTagPlusConta.query.get(conta_id)
        client = ApiClient(conta)

        for item in data:
            tagplus_nfe_id = item.get('id')
            # Match por tagplus_nfe_id é suficiente (é unique por conta na prática).
            # conta_id não entra no filtro porque é singleton.
            emissao = HoraTagPlusNfeEmissao.query.filter_by(
                tagplus_nfe_id=tagplus_nfe_id
            ).first()
            if not emissao:
                continue  # webhook de nota que não originamos — ignorar

            if event_type == 'nfe_aprovada':
                detalhes = client.get(f'/nfes/{tagplus_nfe_id}').json()
                emissao.status = 'APROVADA'
                emissao.chave_44 = detalhes.get('chave_nfe')
                emissao.protocolo_aprovacao = detalhes.get('protocolo_aprovacao')
                emissao.aprovado_em = agora_utc_naive()
                emissao.response_webhook = detalhes

                # Atualiza a venda
                venda = emissao.venda
                venda.nf_saida_numero = emissao.numero_nfe
                venda.nf_saida_chave_44 = emissao.chave_44
                venda.nf_saida_emitida_em = emissao.aprovado_em

                # Evento por chassi (invariante HORA)
                for vi in venda.itens:
                    db.session.add(HoraMotoEvento(
                        numero_chassi=vi.numero_chassi,
                        tipo='NF_EMITIDA',
                        origem_tabela='hora_tagplus_nfe_emissao',
                        origem_id=emissao.id,
                        loja_id=venda.loja_id,
                        detalhe=f'NF {emissao.numero_nfe} chave {emissao.chave_44}',
                    ))

            elif event_type == 'nfe_rejeitada':
                detalhes = client.get(f'/nfes/{tagplus_nfe_id}').json()
                emissao.status = 'REJEITADA_SEFAZ'
                emissao.error_message = detalhes.get('motivo_rejeicao')
                emissao.response_webhook = detalhes

            elif event_type == 'nfe_cancelada':
                emissao.status = 'CANCELADA'

        db.session.commit()
```

---

## 6. Cancelamento

### 6.1 Regras

- Prazo SEFAZ: 24h após emissão para cancelamento simples. Após, só CC-e ou nota de estorno.
- Exige `justificativa` com ≥ 15 caracteres (`scripts/doc_tagplus.md:2480`).
- Cancelar a NFe **não** reverte automaticamente o `HoraMotoEvento`; deve criar evento `NF_CANCELADA` e, se a venda toda for anulada, o fluxo de venda HORA precisa rodar seu próprio cancelamento (`HoraVenda.status='CANCELADA'`, evento por chassi).

### 6.2 Fluxo

```python
# app/hora/services/tagplus/cancelador_nfe.py
class CanceladorNfe:
    @staticmethod
    def cancelar(emissao_id: int, justificativa: str, usuario: str):
        if len(justificativa) < 15:
            raise ValueError('justificativa precisa ter ≥ 15 caracteres')

        emissao = HoraTagPlusNfeEmissao.query.get_or_404(emissao_id)
        if emissao.status != 'APROVADA':
            raise ValueError(f'NFe em status {emissao.status} não pode ser cancelada')

        client = ApiClient(emissao.conta)
        response = client.patch(
            f'/nfes/cancelar/{emissao.tagplus_nfe_id}',
            json={'justificativa': justificativa},
        )

        if response.status_code == 200:
            # Estado intermediário: envio para SEFAZ. Confirmação vem via webhook nfe_cancelada.
            # Para tracking, marcamos um sub-status:
            emissao.status = 'APROVADA'  # mantém até webhook
            emissao.error_message = f'Cancelamento solicitado por {usuario}: {justificativa}'
            db.session.commit()
        else:
            raise RuntimeError(f'Cancelamento falhou: {response.json()}')
```

### 6.3 Carta de Correção Eletrônica (CC-e)

Para correções permitidas (observação, endereço, etc., nunca valor ou destinatário):

```python
# app/hora/services/tagplus/cce_service.py
@staticmethod
def gerar_cce(emissao_id: int, texto_correcao: str):
    if len(texto_correcao) < 15:
        raise ValueError('texto_correcao precisa ter ≥ 15 caracteres')

    emissao = HoraTagPlusNfeEmissao.query.get_or_404(emissao_id)
    client = ApiClient(emissao.conta)
    response = client.post(
        f'/nfes/gerar_cce/{emissao.tagplus_nfe_id}',
        json={'descricao_correcao': texto_correcao},
    )
    # Resposta 201. CC-e PDF pode ser baixado via GET /nfes/pdf/cce/{id}.
```

---

## 7. OAuth2 — fluxo e diferenças vs existente

### 7.1 Cadastro inicial (singleton — 1 conta global)

```
/hora/tagplus/conta               GET  → mostra conta ativa (ou form de cadastro se vazio)
/hora/tagplus/conta               POST → cria/atualiza conta ativa (secret encriptado)
/hora/tagplus/conta/oauth         GET  → redirect para developers.tagplus.com.br/authorize
/hora/tagplus/conta/callback      GET  → recebe ?code=... e troca por tokens
/hora/tagplus/conta/refresh       POST → força refresh manual do token
/hora/tagplus/conta/rotacionar    POST → desativa atual + cria nova (preserva histórico em hora_tagplus_nfe_emissao.conta_id)
```

### 7.2 `oauth_client.py` (espelho do `oauth2_v2.py` com DB em vez de sessão)

```python
# app/hora/services/tagplus/oauth_client.py
class OAuthClient:
    AUTH_URL = 'https://developers.tagplus.com.br/authorize'
    TOKEN_URL = 'https://api.tagplus.com.br/oauth2/token'

    def __init__(self, conta: HoraTagPlusConta):
        self.conta = conta

    def get_authorization_url(self, state: str) -> str:
        params = {
            'response_type': 'code',
            'client_id': self.conta.client_id,
            'scope': self.conta.scope_contratado,
            'state': state,
        }
        return f'{self.AUTH_URL}?{urlencode(params)}'

    def exchange_code(self, code: str) -> HoraTagPlusToken:
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.conta.client_id,
            'client_secret': decrypt(self.conta.client_secret_encrypted),
        }
        r = requests.post(self.TOKEN_URL, data=data, timeout=30)
        r.raise_for_status()
        return self._save_token(r.json())

    def refresh_if_needed(self) -> HoraTagPlusToken:
        token = self.conta.token
        if token and token.expires_at > agora_utc_naive() + timedelta(minutes=5):
            return token  # ainda válido com margem de 5min
        return self._do_refresh()

    def _do_refresh(self) -> HoraTagPlusToken:
        token = self.conta.token
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': decrypt(token.refresh_token_encrypted),
            'client_id': self.conta.client_id,
            'client_secret': decrypt(self.conta.client_secret_encrypted),
        }
        r = requests.post(self.TOKEN_URL, data=data, timeout=30)
        r.raise_for_status()
        return self._save_token(r.json())

    def _save_token(self, body: dict) -> HoraTagPlusToken:
        expires_at = agora_utc_naive() + timedelta(seconds=body['expires_in'])
        token = self.conta.token
        if token is None:
            token = HoraTagPlusToken(conta_id=self.conta.id)
            db.session.add(token)
        token.access_token_encrypted = encrypt(body['access_token'])
        token.refresh_token_encrypted = encrypt(body['refresh_token'])
        token.token_type = body.get('token_type', 'bearer')
        token.expires_at = expires_at
        token.refreshed_em = agora_utc_naive() if token.id else None
        db.session.commit()
        return token
```

### 7.3 `api_client.py` — wrapper HTTP

```python
# app/hora/services/tagplus/api_client.py
class ApiClient:
    BASE = 'https://api.tagplus.com.br'

    def __init__(self, conta: HoraTagPlusConta):
        self.conta = conta
        self.oauth = OAuthClient(conta)

    def _headers(self, extra=None) -> dict:
        token = self.oauth.refresh_if_needed()
        headers = {
            'Authorization': f'Bearer {decrypt(token.access_token_encrypted)}',
            'X-Api-Version': '2.0',
            'Content-Type': 'application/json; charset=utf-8',
        }
        if extra:
            headers.update(extra)
        return headers

    def get(self, path, params=None):
        return self._request('GET', path, params=params)

    def post(self, path, json=None, headers=None):
        return self._request('POST', path, json=json, extra_headers=headers)

    def patch(self, path, json=None):
        return self._request('PATCH', path, json=json)

    def _request(self, method, path, json=None, params=None, extra_headers=None):
        r = requests.request(
            method,
            self.BASE + path,
            headers=self._headers(extra_headers),
            json=json,
            params=params,
            timeout=60,
        )
        # Se 401, força refresh uma vez e re-tenta
        if r.status_code == 401:
            self.oauth._do_refresh()
            r = requests.request(
                method, self.BASE + path,
                headers=self._headers(extra_headers),
                json=json, params=params, timeout=60,
            )
        return r
```

### 7.4 Encriptação de secrets

```python
# app/hora/services/tagplus/crypto.py
from cryptography.fernet import Fernet
import os

def _fernet():
    key = os.environ.get('HORA_TAGPLUS_ENC_KEY')
    if not key:
        raise RuntimeError('HORA_TAGPLUS_ENC_KEY env var não configurada')
    return Fernet(key.encode())

def encrypt(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()

def decrypt(cipher: str) -> str:
    return _fernet().decrypt(cipher.encode()).decode()
```

A chave é gerada com `Fernet.generate_key()` e configurada no Render como env var. **Nunca** versionar a chave.

---

## 8. Cadastros prévios obrigatórios (configuração única no TagPlus)

Antes da primeira emissão, configurar **uma única vez** no portal TagPlus:

1. **Emissor/CNPJ HORA cadastrado e habilitado para NFe** (`Rejeição: CNPJ Emitente não cadastrado` se faltar).
2. **Série de NFe configurada** (ERP → Configurações → Nota Fiscal). Se a HORA usar séries distintas por loja (prática comum para segregar relatórios), cadastrar as séries como "séries adicionais" no TagPlus e adicionar coluna `tagplus_serie` em `hora_loja` (fallback: série única).
3. **Certificado digital A1 válido** instalado no TagPlus.
4. **Produtos cadastrados** — cada `HoraModelo` como produto no TagPlus com:
   - NCM correto para motos elétricas: `8711.60.00`.
   - CFOP padrão (5102/6102).
   - CST/CSOSN de ICMS conforme regime tributário da HORA (Simples? Real?).
   - Unidade: `UN`.
5. **Aplicativo OAuth cadastrado** em `developers.tagplus.com.br` com `redirect_uri`:
   `https://sistema-fretes.onrender.com/hora/tagplus/conta/callback`.
6. **Webhook cadastrado** no ERP apontando para:
   `https://sistema-fretes.onrender.com/hora/tagplus/webhook`
   com eventos: `nfe_aprovada`, `nfe_rejeitada`, `nfe_cancelada`.

**Tela de onboarding**: `/hora/tagplus/conta/checklist` valida via API:
- `GET /usuario_atual` — valida token e escopos concedidos.
- `GET /produtos?q=<modelo>` — confere se cada `HoraModelo` tem `tagplus_produto_id` mapeado.
- `GET /webhooks` (se TagPlus expor) — confirma receiver registrado.

---

## 9. Tratamento de erros — matriz

Erros da API TagPlus são documentados em `scripts/guia.md:376-401`. Mapeamento para comportamento HORA:

| `error_code` TagPlus | Status HORA | Ação automática | Ação manual necessária |
|---|---|---|---|
| `escopo_nao_autorizado` | `REJEITADA_LOCAL` | Marca conta como `ativo=False`, alerta admin | Re-autorizar OAuth com scope correto |
| `produtos_sem_tributacao` | `REJEITADA_LOCAL` | Nenhuma | Configurar CFOP/CSOSN no produto no TagPlus |
| `campo_obrigatorio` (`field=faturas`) | `REJEITADA_LOCAL` | Nenhuma | Fix no `payload_builder` (dev) |
| `nota_sem_faturamento` | `REJEITADA_LOCAL` | Nenhuma | Mesmo que acima |
| `alterar_nota_nao_autorizado` | `REJEITADA_LOCAL` | Nenhuma (não deve acontecer em POST) | Investigar (possível bug) |
| `error_serie_nfce_nao_configurada` | `REJEITADA_LOCAL` | Marca conta como `ativo=False` | Configurar série no TagPlus |
| `pagamento_pendente` | `ERRO_INFRA` | Retry em 1h | Comercial TagPlus |
| HTTP 401 persistente | `ERRO_INFRA` | Tenta refresh; se falhar, `ativo=False` | Re-autorizar OAuth |
| HTTP 5xx | `ERRO_INFRA` | Retry backoff 10s, 60s, 300s | Se persistir: sentry + contato suporte |

---

## 10. Rotas UI propostas

Todas protegidas por `require_hora_perm('nfs', <acao>)` (módulo `nfs` já existe no `MODULOS_HORA`).

| Rota | Método | Permissão | Finalidade |
|---|---|---|---|
| `/hora/tagplus/conta` | GET/POST | `nfs.editar` | Mostra/edita a conta ativa (client_id/secret) |
| `/hora/tagplus/conta/oauth` | GET | `nfs.editar` | Inicia fluxo OAuth |
| `/hora/tagplus/conta/callback` | GET | (pública) | Recebe code do TagPlus (validado por `state`) |
| `/hora/tagplus/conta/checklist` | GET | `nfs.ver` | Diagnóstico de configuração |
| `/hora/tagplus/conta/mapeamento` | GET/POST | `nfs.editar` | Mapeia `HoraModelo` ↔ `tagplus_produto_id` |
| `/hora/tagplus/webhook` | POST | (pública, secret) | Receiver webhooks TagPlus |
| `/hora/vendas/<id>/nfe` | GET | `nfs.ver` | Status + DANFE/XML da NF da venda |
| `/hora/vendas/<id>/nfe/emitir` | POST | `nfs.criar` | Re-enfileira emissão (se `PENDENTE`/rejeitada) |
| `/hora/vendas/<id>/nfe/cancelar` | POST | `nfs.apagar` | Cancela NF (exige justificativa ≥ 15 chars) |
| `/hora/vendas/<id>/nfe/cce` | POST | `nfs.editar` | Gera CC-e |
| `/hora/vendas/<id>/nfe/danfe.pdf` | GET | `nfs.ver` | Proxy para `GET /nfes/pdf/recibo_a4/{id}` |
| `/hora/vendas/<id>/nfe/xml` | GET | `nfs.ver` | Proxy para `GET /nfes/gerar_link_xml/{id}` |
| `/hora/tagplus/emissoes` | GET | `nfs.ver` | Fila global de emissões (filtro por status/loja/período) |

**Link no menu**: `app/templates/base.html`, submenu "Lojas HORA" → novo item "NF-e / TagPlus" (contas + fila de emissão).

---

## 11. Migrations

Em `scripts/migrations/hora_16_tagplus.{py,sql}` (seguindo regra duas migrations — `~/.claude/CLAUDE.md` seção "MIGRATIONS"):

```sql
-- hora_16_tagplus.sql (idempotente para Render Shell)
CREATE TABLE IF NOT EXISTS hora_tagplus_conta (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(64) NOT NULL,
    client_secret_encrypted TEXT NOT NULL,
    webhook_secret VARCHAR(64) NOT NULL,
    oauth_state_last VARCHAR(64),
    scope_contratado VARCHAR(255) NOT NULL DEFAULT 'write:nfes read:clientes write:clientes read:produtos',
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    ambiente VARCHAR(15) NOT NULL DEFAULT 'producao',
    criado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'America/Sao_Paulo'),
    atualizado_em TIMESTAMP
);
-- Garante singleton: só 1 conta pode estar ativa ao mesmo tempo.
CREATE UNIQUE INDEX IF NOT EXISTS uq_hora_tagplus_conta_ativa
    ON hora_tagplus_conta(ativo) WHERE ativo = TRUE;

CREATE TABLE IF NOT EXISTS hora_tagplus_token (
    id SERIAL PRIMARY KEY,
    conta_id INTEGER NOT NULL UNIQUE REFERENCES hora_tagplus_conta(id) ON DELETE CASCADE,
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT NOT NULL,
    token_type VARCHAR(20) NOT NULL DEFAULT 'bearer',
    expires_at TIMESTAMP NOT NULL,
    obtido_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'America/Sao_Paulo'),
    refreshed_em TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_hora_tagplus_token_expires_at ON hora_tagplus_token(expires_at);

CREATE TABLE IF NOT EXISTS hora_tagplus_produto_map (
    id SERIAL PRIMARY KEY,
    modelo_id INTEGER NOT NULL UNIQUE REFERENCES hora_modelo(id),
    tagplus_produto_id INTEGER NOT NULL,
    tagplus_codigo VARCHAR(50),
    cfop_default VARCHAR(4) NOT NULL DEFAULT '5102',
    criado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'America/Sao_Paulo')
);

CREATE TABLE IF NOT EXISTS hora_tagplus_nfe_emissao (
    id SERIAL PRIMARY KEY,
    venda_id INTEGER NOT NULL UNIQUE REFERENCES hora_venda(id),
    conta_id INTEGER NOT NULL REFERENCES hora_tagplus_conta(id),
    status VARCHAR(30) NOT NULL DEFAULT 'PENDENTE',
    tagplus_nfe_id INTEGER,
    numero_nfe VARCHAR(20),
    serie_nfe VARCHAR(5),
    chave_44 VARCHAR(44) UNIQUE,
    protocolo_aprovacao VARCHAR(30),
    payload_enviado JSONB,
    response_inicial JSONB,
    response_webhook JSONB,
    error_code VARCHAR(60),
    error_message TEXT,
    tentativas INTEGER NOT NULL DEFAULT 0,
    enviado_em TIMESTAMP,
    aprovado_em TIMESTAMP,
    criado_em TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'America/Sao_Paulo'),
    atualizado_em TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_hora_tagplus_nfe_status ON hora_tagplus_nfe_emissao(status);
CREATE INDEX IF NOT EXISTS ix_hora_tagplus_nfe_tagplus_id ON hora_tagplus_nfe_emissao(tagplus_nfe_id);
```

E versão Python equivalente com `db.create_all()` ou `op.create_table` (Alembic), com `sys.path.insert` no topo (memória `feedback_migration_sys_path.md`).

---

## 12. Variáveis de ambiente (Render)

| Var | Exemplo | Finalidade |
|---|---|---|
| `HORA_TAGPLUS_ENC_KEY` | (gerar com `Fernet.generate_key()`) | Chave Fernet para encriptar secrets/tokens |
| `HORA_TAGPLUS_BASE_URL` | `https://api.tagplus.com.br` | Permite override em testes |
| `REDIS_URL` | (já existe) | RQ worker |

Queue RQ: `hora_nfe` (adicionar ao comando do worker do Render).

---

## 13. Gotchas e regras de negócio críticas

1. **Idempotência**: `HoraTagPlusNfeEmissao.venda_id` é UNIQUE. Se um operador tentar emitir 2x (double-click, retry manual), o `enfileirar()` detecta e não duplica.

2. **Chave 44 UNIQUE**: evita 2 vendas diferentes ficarem ligadas à mesma NFe (impossível pelo TagPlus, mas defensivo).

3. **Timezone**: todos os `DateTime` são `naive` em horário de Brasília (padrão do projeto — `~/.claude/CLAUDE.md` regra timezone).

4. **CNPJ único, lojas operacionais**: todas as lojas HORA faturam pelo mesmo CNPJ. A identidade da loja no DANFE vai em `inf_contribuinte` (texto). Isso afeta: (a) numeração de NFe é sequencial global, não por loja; (b) relatório de "NFs por loja" vem do JOIN `hora_tagplus_nfe_emissao ⟂ hora_venda.loja_id`, não da NF no TagPlus; (c) se precisar série distinta por loja, ver item 2 do §8.

5. **CPF do cliente sem máscara**: TagPlus espera `"cpf": "12345678900"` (11 dígitos, sem pontos/traço). Normalizar no builder.

6. **Arredondamento**: sempre arredondar `Decimal(preco_final)` para 2 casas **antes** de converter para float no payload. `Decimal('1234.567').quantize(Decimal('0.01'))`.

7. **Reemissão após rejeição**: se SEFAZ rejeitar, o número da NFe é "queimado" no TagPlus — o próximo POST gera novo número. Para inutilizar a faixa perdida, usar `PATCH /nfes/inutilizar_varias` manualmente (tela dev, não automático).

8. **Ambiente de teste**: TagPlus não tem homologação. Testar com 1 loja real com CNPJ de teste (se houver) ou primeira NF a valor de R$ 1 que se cancela em seguida.

9. **Fronteira HORA preservada**: nenhum import de `app/integracoes/tagplus/*`. Toda lógica vive em `app/hora/services/tagplus/`. Se no futuro quisermos consolidar, extrair para `app/integracoes/tagplus_core/` e os dois domínios importam — mas só quando houver **terceiro** consumidor.

10. **Evento `NF_EMITIDA` no chassi**: respeita invariante 4 do módulo HORA (log de eventos, não UPDATE em `hora_moto`). Se algo falhar após inserir o evento, a venda tem a NF mas o evento pode estar inconsistente — envolver tudo em `db.session.begin_nested()`.

---

## 14. Ordem de implementação sugerida

Dependências críticas primeiro; UI por último.

1. **Migrations** (`hora_16_tagplus.{py,sql}`) + modelos SQLAlchemy. Rodar local, validar schema.
2. **Módulo crypto** (`app/hora/services/tagplus/crypto.py`) + env var no `.env.local`.
3. **`OAuthClient`** + rotas `/hora/tagplus/contas` (CRUD + OAuth flow). Testar ponta a ponta com 1 loja real.
4. **`ApiClient`** + smoketest chamando `GET /usuario_atual` com token real.
5. **`PayloadBuilder`** + testes unitários com fixtures de `HoraVenda` (mocks).
6. **Mapeamento de produto** (`hora_tagplus_produto_map`) + tela de configuração.
7. **`EmissorNfeHora.processar`** + worker RQ (`worker_hora_nfe.py`). Testar emissão real com NFe de R$ 1.
8. **`WebhookHandler`** + rota `/hora/tagplus/webhook/<loja_id>`. Cadastrar webhook no TagPlus e validar recebimento via ngrok (local) ou Render (preview).
9. **Atualização de `HoraVenda` + `HoraMotoEvento`** no handler. Validar que o ciclo completo fecha.
10. **Cancelamento e CC-e** (rotas + services).
11. **Telas UI restantes** (status na tela de venda, proxy DANFE/XML).
12. **Documentação**: atualizar `app/hora/CLAUDE.md` seção "Fase 2" com status da emissão implementada.

Estimativa de esforço: 3-5 dias de dev focado para passos 1-9; 1-2 dias para 10-12.

---

## 15. Pontos em aberto (confirmar com negócio antes de codar)

1. **Emitir assim que venda CONCLUIDA ou exigir confirmação do operador?** O desenho acima é automático. Se operador precisa revisar antes, adicionar botão explícito "Emitir NFe" na tela de venda e só enfileirar no clique.

2. **Série de NFe por loja ou única?** Com CNPJ único, o TagPlus pode usar série única sequencial (1, 2, 3...) ou múltiplas séries (cada loja = 1 série). Séries múltiplas ajudam em relatórios fiscais internos mas exigem configuração extra no TagPlus e coluna `tagplus_serie` em `hora_loja`.

3. **Endereço físico da loja no DANFE**: ver §4.4 parte final. Confirmar com contabilidade se "endereço de retirada" precisa aparecer no DANFE.

4. **Ressarcimento em caso de rejeição SEFAZ**: se o pagamento já foi capturado (PIX/cartão) e a NF é rejeitada, qual o fluxo de compensação? Ver com financeiro — pode exigir campo `status_pagamento` na venda.

5. **NFC-e vs NFe**: para vendas ≤ R$ 200.000 a consumidor final, NFC-e é legalmente permitida e mais simples (não exige destinatário completo). Avaliar se HORA prefere NFC-e (endpoint `/nfces` no TagPlus, fluxo análogo).

6. **Contingência**: se o TagPlus/SEFAZ estiver fora, emitir em contingência FS-DA? Exige DANFE em papel em 2 vias + transmissão posterior. **Recomendação**: v1 **não** implementa contingência; em caso de erro infra, operador segura a venda e tenta depois.

---

## 16. Referências cruzadas

- Doc OpenAPI TagPlus: `scripts/doc_tagplus.md` (POST `/nfes` linha 142, cancelamento 2467, CC-e 2554, webhooks).
- Guia TagPlus: `scripts/guia.md` (OAuth2 137-296, error codes 376-401).
- OpenAPI raw: `scripts/open_api.md`.
- Webhooks: `scripts/webhook.md`.
- Código existente para reuso (engenharia, não import): `app/integracoes/tagplus/oauth2_v2.py`.
- Contrato do módulo HORA: `app/hora/CLAUDE.md`, `docs/hora/INVARIANTES.md`.
- Regras universais: `CLAUDE.md` raiz, `~/.claude/CLAUDE.md` (migrations, JSON sanitization, timezone).
