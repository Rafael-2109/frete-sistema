# Roadmap — Sistema de Licitacao/Contratacao de Frete (Despacho para Freteiros)

**Criado em**: 28/02/2026
**Status**: Planejado (nao iniciado)
**Prioridade**: A definir

---

## Indice

1. [Problema e Solucao](#1-problema-e-solucao)
2. [Arquitetura e Fluxo](#2-arquitetura-e-fluxo)
3. [API WhatsApp — Opcoes](#3-api-whatsapp--opcoes)
4. [Modelos de Dados](#4-modelos-de-dados)
5. [Fluxo Detalhado — Passo a Passo](#5-fluxo-detalhado--passo-a-passo)
6. [Arquivos a Criar/Modificar](#6-arquivos-a-criarmodificar)
7. [Seguranca](#7-seguranca)
8. [Fases de Implementacao](#8-fases-de-implementacao)
9. [Verificacao e Testes](#9-verificacao-e-testes)
10. [Codigo de Referencia Existente](#10-codigo-de-referencia-existente)

---

## 1. Problema e Solucao

### Problema

Hoje o processo de contratacao de freteiros (transportadores autonomos) e manual:
- Operador identifica pedidos prontos para embarque
- Liga/manda WhatsApp para freteiros um a um perguntando disponibilidade
- Negocia preco verbalmente
- Espera confirmacao
- So entao cria embarque no sistema

Isso gera atrasos, falta de rastreabilidade e impossibilidade de escalar.

### Solucao Proposta

Sistema de **despacho automatizado** que:
1. Cria um **lote de despacho** a partir da tela de cotacao existente
2. Identifica freteiros elegiveis por cidade/modalidade
3. Calcula o valor do frete pela **tabela de cada freteiro** (cada um ve seu preco)
4. Envia ofertas via **WhatsApp API** (automatico) ou **link copiavel** (manual)
5. **First-to-accept**: primeiro freteiro a responder ganha a carga
6. Sistema **auto-cria embarque** quando freteiro confirma

### Decisoes Confirmadas

| Decisao | Definicao |
|---------|-----------|
| Quando nasce o embarque | SOMENTE apos freteiro confirmar |
| Onde inicia o fluxo | Tela de cotacao existente (`/cotacao/tela`) |
| Calculo do frete | Tabela individual de CADA freteiro |
| Modelo de contratacao | First-to-accept (primeiro a responder ganha) |
| Canal de comunicacao | Hibrido: WhatsApp API + link copiavel manual |
| API WhatsApp | Ainda nao contratada — roadmap inclui setup |

---

## 2. Arquitetura e Fluxo

### Fluxo Atual (mantido para transportadoras regulares)

```
Separacao → Cotacao → Seleciona transportadora → Embarque
```

Este fluxo NAO e alterado. Continua funcionando normalmente.

### Fluxo Novo (para freteiros)

```
Separacao → Cotacao → "Despachar para Freteiros"
                            ↓
                  Cria LoteDespacho (pseudoEmbarque)
                            ↓
                  Sistema acha freteiros elegiveis
                  (Target: cidade + modalidade)
                            ↓
                  Calcula frete por freteiro
                  (tabela individual de cada um)
                            ↓
                  Cria OfertaFreteiro com token unico para cada
                            ↓
            ┌───────────────┴───────────────┐
            ↓                               ↓
    WhatsApp API (auto)              Links copiados (manual)
            ↓                               ↓
    Freteiro recebe msg          Usuario cola no WhatsApp
            ↓                               ↓
    Responde "SIM CODIGO"        Freteiro abre link no celular
    via WhatsApp                   e clica "Aceitar"
            ↓                               ↓
            └───────────────┬───────────────┘
                            ↓
                  Sistema recebe confirmacao
                            ↓
                  Auto-cria Cotacao + Embarque + EmbarqueItems
                            ↓
                  Expira todas as outras ofertas
                            ↓
                  Notifica usuario: "Freteiro X confirmou #456"
```

### Diagrama de Estados — LoteDespacho

```
RASCUNHO → DESPACHADO → CONFIRMADO → EMBARQUE_CRIADO
                ↓              ↓
            EXPIRADO      (rollback)
                ↓
           CANCELADO
```

### Diagrama de Estados — OfertaFreteiro

```
PENDENTE → ENVIADO → ACEITO
               ↓        ↓
          RECUSADO   EXPIRADO
```

---

## 3. API WhatsApp — Opcoes

### Opcao Recomendada: Evolution API (self-hosted, open-source)

| Aspecto | Detalhe |
|---------|---------|
| Tipo | Open-source, self-hosted |
| Custo | Sem licenca (custo de infra apenas) |
| Hospedagem | Render web service (mesmo ambiente do sistema) |
| API | REST completa: enviar msg, receber webhook, gerenciar sessao |
| Recursos | Mensagem com link clicavel, webhook nativo |
| Comunidade | Brasileira, ativa |
| Repo | github.com/EvolutionAPI/evolution-api |

### Alternativa Paga: Z-API

| Aspecto | Detalhe |
|---------|---------|
| Tipo | SaaS brasileiro |
| Custo | ~R$ 90-150/mes por instancia |
| API | REST simples, webhook nativo |
| Vantagem | Nao precisa manter infra extra |
| Desvantagem | Custo recorrente |

### Integracao com o Sistema

Independente da API escolhida, o sistema se comunica via:

1. **Envio**: `POST /message/sendText` com numero + mensagem
2. **Recebimento**: Webhook `POST /despacho/webhook/whatsapp` recebe respostas

O service `WhatsAppService` abstrai a API especifica — trocar de Evolution para Z-API e mudar 1 arquivo (`whatsapp_service.py`).

### Variaveis de Ambiente Necessarias

```bash
# WhatsApp API
WHATSAPP_API_URL=https://evolution-api.onrender.com
WHATSAPP_API_KEY=sua-chave-aqui
WHATSAPP_INSTANCE=nacom-frete
WHATSAPP_WEBHOOK_SECRET=secret-para-validar-webhook

# Despacho
DESPACHO_EXPIRACAO_HORAS=24
DESPACHO_URL_BASE=https://sistema.nacom.com.br
```

---

## 4. Modelos de Dados

### 4.1 `LoteDespacho` (o pseudoEmbarque)

Tabela: `lotes_despacho`

```python
class LoteDespacho(db.Model):
    """Lote de pedidos aguardando contratacao de freteiro.

    Representa um agrupamento de pedidos para uma mesma cidade/modalidade
    que sera oferecido a freteiros. Funciona como um 'pre-embarque' que
    so se torna embarque real apos confirmacao do freteiro.
    """
    __tablename__ = 'lotes_despacho'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, unique=True, nullable=False)  # Sequencial auto

    # Target (cidade + modalidade)
    uf_destino = db.Column(db.String(2), nullable=False)
    cidade_destino = db.Column(db.String(100), nullable=False)
    codigo_ibge = db.Column(db.String(10), nullable=True)
    modalidade = db.Column(db.String(50), nullable=False)       # Tipo de veiculo
    tipo_carga = db.Column(db.String(20), nullable=False)       # DIRETA / FRACIONADA

    # Totais agregados dos pedidos
    peso_total = db.Column(db.Float, nullable=False)
    valor_total = db.Column(db.Float, nullable=False)
    qtd_pedidos = db.Column(db.Integer, nullable=False)

    # Data prevista
    data_prevista_embarque = db.Column(db.Date, nullable=True)

    # Status: RASCUNHO → DESPACHADO → CONFIRMADO → EMBARQUE_CRIADO | EXPIRADO | CANCELADO
    status = db.Column(db.String(20), default='RASCUNHO', nullable=False)

    # Resultado (preenchido apos confirmacao)
    embarque_id = db.Column(db.Integer, db.ForeignKey('embarques.id'), nullable=True)
    transportadora_confirmada_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'), nullable=True)
    confirmado_em = db.Column(db.DateTime, nullable=True)

    # Controle de tempo
    despachado_em = db.Column(db.DateTime, nullable=True)
    expira_em = db.Column(db.DateTime, nullable=True)  # Default: 24h apos despacho

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100))

    # Relacionamentos
    itens = db.relationship('LoteDespachoItem', backref='lote', lazy='dynamic')
    ofertas = db.relationship('OfertaFreteiro', backref='lote', lazy='dynamic')
    embarque = db.relationship('Embarque', backref='lote_despacho', uselist=False)
    transportadora_confirmada = db.relationship('Transportadora')
```

### 4.2 `LoteDespachoItem` (pedidos do lote)

Tabela: `lote_despacho_itens`

```python
class LoteDespachoItem(db.Model):
    """Separacoes/pedidos que compoem o lote de despacho."""
    __tablename__ = 'lote_despacho_itens'

    id = db.Column(db.Integer, primary_key=True)
    lote_id = db.Column(db.Integer, db.ForeignKey('lotes_despacho.id'), nullable=False)
    separacao_lote_id = db.Column(db.String(50), nullable=False)  # ID da separacao
    cnpj_cliente = db.Column(db.String(20))
    cliente = db.Column(db.String(120))
    num_pedido = db.Column(db.String(50))
    peso = db.Column(db.Float)
    valor = db.Column(db.Float)
    pallets = db.Column(db.Integer, default=0)
```

### 4.3 `OfertaFreteiro` (oferta enviada a cada freteiro)

Tabela: `ofertas_freteiro`

```python
class OfertaFreteiro(db.Model):
    """Oferta enviada a um freteiro especifico.

    Cada freteiro elegivel recebe uma oferta com:
    - Token unico para link publico (64 chars)
    - Codigo curto para resposta via WhatsApp (6 chars)
    - Valor de frete pre-calculado pela tabela DESTE freteiro
    """
    __tablename__ = 'ofertas_freteiro'

    id = db.Column(db.Integer, primary_key=True)
    lote_id = db.Column(db.Integer, db.ForeignKey('lotes_despacho.id'), nullable=False)
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'), nullable=False)

    # Token para link publico (sem auth)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)

    # Frete pre-calculado pela tabela DESTE freteiro
    valor_frete_calculado = db.Column(db.Float)
    nome_tabela = db.Column(db.String(100))          # Nome da tabela usada
    dados_tabela = db.Column(JSONB, nullable=True)    # Snapshot completo dos parametros

    # Status: PENDENTE → ENVIADO → ACEITO | RECUSADO | EXPIRADO
    status = db.Column(db.String(20), default='PENDENTE')

    # Envio
    enviado_em = db.Column(db.DateTime, nullable=True)
    canal_envio = db.Column(db.String(20))             # whatsapp | manual | webhook
    whatsapp_message_id = db.Column(db.String(100), nullable=True)

    # Resposta
    respondido_em = db.Column(db.DateTime, nullable=True)
    motivo_recusa = db.Column(db.String(255), nullable=True)

    # Codigo curto para resposta WhatsApp (ex: "ABC123")
    codigo_resposta = db.Column(db.String(10), unique=True, nullable=False)

    # Auditoria da resposta
    ip_resposta = db.Column(db.String(45), nullable=True)
    user_agent_resposta = db.Column(db.String(500), nullable=True)
    canal_resposta = db.Column(db.String(20), nullable=True)  # link | whatsapp

    # Relacionamentos
    transportadora = db.relationship('Transportadora')
```

### 4.4 Campos Novos em `Transportadora`

```python
# Adicionar a app/transportadoras/models.py
telefone = db.Column(db.String(20), nullable=True)
email_contato = db.Column(db.String(255), nullable=True)
whatsapp = db.Column(db.String(20), nullable=True)           # Formato: 5511999998888
aceita_despacho_whatsapp = db.Column(db.Boolean, default=False)  # Opt-in
```

### 4.5 Campo Novo em `Embarque`

```python
# Adicionar a app/embarques/models.py
lote_despacho_id = db.Column(db.Integer, db.ForeignKey('lotes_despacho.id'), nullable=True)
```

### Diagrama ER Simplificado

```
┌──────────────────┐     ┌──────────────────────┐     ┌──────────────────┐
│  LoteDespacho    │────<│  LoteDespachoItem     │     │  Transportadora  │
│                  │     │                       │     │  (+4 campos)     │
│  numero          │     │  separacao_lote_id    │     │                  │
│  cidade/uf       │     │  cnpj_cliente         │     │  whatsapp        │
│  modalidade      │     │  num_pedido           │     │  aceita_despacho │
│  peso/valor      │     │  peso/valor           │     │                  │
│  status          │     └───────────────────────┘     └────────┬─────────┘
│                  │                                            │
│  embarque_id ──────────────────────────────────> Embarque     │
│  transp_conf_id ─────────────────────────────────────────────┘
│                  │
│                  │────<┌──────────────────────┐
│                  │     │  OfertaFreteiro       │
└──────────────────┘     │                       │
                         │  token (64 chars)     │
                         │  codigo_resposta (6)  │
                         │  valor_frete_calc     │
                         │  status               │
                         │  transportadora_id ──────> Transportadora
                         └───────────────────────┘
```

---

## 5. Fluxo Detalhado — Passo a Passo

### Etapa 1: Criacao do Lote (na tela de cotacao)

**Onde**: Tela de cotacao existente (`/cotacao/tela`)

**Mudanca na UI**: Botao "Despachar para Freteiros" ao lado do botao existente "Fechar Cotacao"

**Fluxo**:

1. Usuario seleciona pedidos e entra na tela de cotacao (fluxo existente, inalterado)
2. Sistema mostra opcoes de transporte como hoje
3. **Novo**: Botao "Despachar para Freteiros" aparece quando ha freteiros com tabela para a cidade/modalidade
4. Ao clicar:
   - Modal pede: modalidade (dropdown com opcoes disponiveis) + data prevista
   - Sistema cria `LoteDespacho` + `LoteDespachoItem` (1 por pedido)
   - Redireciona para tela de despacho do lote

**Criterio de elegibilidade do freteiro**:
- `Transportadora.freteiro = True`
- `Transportadora.ativo = True`
- Possui `TabelaFrete` com preco para a cidade/UF de destino
- Tabela compativel com a modalidade selecionada

### Etapa 2: Tela de Despacho do Lote

**Rota**: `GET /despacho/lote/<id>`

**Conteudo da tela**:
- Resumo do lote: cidade, UF, modalidade, peso total, valor total, qtd pedidos
- Lista de pedidos do lote (LoteDespachoItem)
- Lista de freteiros elegiveis com:
  - Nome do freteiro
  - Valor de frete calculado pela tabela dele
  - Status da oferta (pendente / enviado / aceito / recusado / expirado)
  - Icone WhatsApp verde se `aceita_despacho_whatsapp = True`
- Botoes de acao:
  - "Enviar para Todos via WhatsApp" — dispara para todos com whatsapp configurado
  - "Copiar Todos os Links" — gera lista de links para envio manual
  - Link individual por freteiro — copiar 1 link especifico
  - "Cancelar Lote" — cancela e expira todas as ofertas

### Etapa 3: Envio via WhatsApp

**Service**: `WhatsAppDespachoService.enviar_ofertas(lote_id)`

Para cada `OfertaFreteiro` cuja transportadora tem `aceita_despacho_whatsapp = True`:

1. Monta mensagem formatada:

```
*NACOM LOGISTICA - Oferta de Frete #{numero}*

Destino: {cidade}/{uf}
Veiculo: {modalidade}
Peso: {peso_total} kg
Data prevista: {data_prevista}
Valor frete: R$ {valor_frete_calculado}

Para ACEITAR, responda *SIM {codigo_resposta}*
Para RECUSAR, responda *NAO {codigo_resposta}*

Ou acesse: {link_oferta}
```

2. Envia via API WhatsApp: `POST /message/sendText`
3. Salva `whatsapp_message_id` na oferta
4. Atualiza status da oferta para `ENVIADO`, registra `enviado_em`
5. Atualiza status do lote para `DESPACHADO`, registra `despachado_em`
6. Calcula e salva `expira_em` (default: 24h apos despacho)

### Etapa 4: Recebimento da Resposta

#### Canal A: Via Link Publico

**Rota GET**: `/despacho/oferta/<token>` (publica, sem autenticacao)

- Pagina mobile-first, standalone (NAO usa `base.html`)
- Mostra: destino, veiculo, peso, data, valor frete
- Logo Nacom no topo
- Dois botoes grandes: "Aceitar Carga" (verde) / "Recusar" (cinza)
- Se ja respondido: mostra status atual ("Voce ja aceitou esta carga" ou "Oferta expirada")

**Rota POST**: `/despacho/oferta/<token>/responder`
- Body: `{ "acao": "aceitar" | "recusar", "motivo": "..." }`
- Registra `ip_resposta`, `user_agent_resposta`, `canal_resposta = "link"`

#### Canal B: Via WhatsApp (webhook)

**Rota POST**: `/despacho/webhook/whatsapp` (webhook da API WhatsApp)

1. Recebe payload do webhook (mensagem recebida)
2. Valida assinatura/secret do webhook
3. Extrai texto da mensagem
4. Faz parsing: busca padrao `SIM XXXXXX` ou `NAO XXXXXX` (case insensitive)
5. Resolve `codigo_resposta` → `OfertaFreteiro`
6. Processa aceite ou recusa
7. Envia mensagem de confirmacao de volta ao freteiro

#### Processamento da Resposta (comum a ambos canais)

```python
def processar_resposta(oferta_id, aceitar, motivo=None, canal='link', ip=None, user_agent=None):
    """
    Processa a resposta de um freteiro a uma oferta.

    Usa SELECT ... FOR UPDATE no LoteDespacho para prevenir race condition
    (dois freteiros aceitando ao mesmo tempo).
    """
    oferta = OfertaFreteiro.query.get(oferta_id)

    # 1. Lock otimista: verificar se lote ainda esta DESPACHADO
    lote = db.session.query(LoteDespacho).filter_by(
        id=oferta.lote_id
    ).with_for_update().first()

    if lote.status != 'DESPACHADO':
        return {'sucesso': False, 'erro': 'Oferta ja preenchida por outro freteiro'}

    # Registrar auditoria
    oferta.respondido_em = agora_utc_naive()
    oferta.canal_resposta = canal
    oferta.ip_resposta = ip
    oferta.user_agent_resposta = user_agent

    if aceitar:
        # 2. Marcar oferta como ACEITO
        oferta.status = 'ACEITO'

        # 3. Atualizar lote
        lote.status = 'CONFIRMADO'
        lote.transportadora_confirmada_id = oferta.transportadora_id
        lote.confirmado_em = agora_utc_naive()

        # 4. AUTO-CRIAR Embarque
        embarque = criar_embarque_do_lote(lote, oferta)
        lote.embarque_id = embarque.id
        lote.status = 'EMBARQUE_CRIADO'

        # 5. Expirar todas as outras ofertas do mesmo lote
        OfertaFreteiro.query.filter(
            OfertaFreteiro.lote_id == lote.id,
            OfertaFreteiro.id != oferta.id
        ).update({'status': 'EXPIRADO'})

        # 6. Notificar usuario do sistema
        enviar_notificacao(
            tipo='DESPACHO_CONFIRMADO',
            titulo=f'Freteiro confirmou embarque #{embarque.numero}',
            corpo=f'{oferta.transportadora.razao_social} aceitou o lote #{lote.numero}',
        )

        # 7. (Opcional) Notificar freteiros expirados via WhatsApp
        notificar_expirados(lote)

        db.session.commit()
        return {'sucesso': True, 'embarque_id': embarque.id}

    else:
        # Recusa
        oferta.status = 'RECUSADO'
        oferta.motivo_recusa = motivo
        db.session.commit()

        # Verificar se todas as ofertas foram respondidas
        pendentes = OfertaFreteiro.query.filter(
            OfertaFreteiro.lote_id == lote.id,
            OfertaFreteiro.status.in_(['PENDENTE', 'ENVIADO'])
        ).count()

        if pendentes == 0:
            lote.status = 'EXPIRADO'  # Todos recusaram
            db.session.commit()

        return {'sucesso': True, 'acao': 'recusado'}
```

### Etapa 5: Criacao Automatica do Embarque

**Funcao**: `criar_embarque_do_lote(lote, oferta_aceita)`

Reutiliza a logica existente em `app/cotacao/routes.py` (linhas ~1450-1596):

1. Cria `Cotacao` com snapshot da tabela do freteiro (dados de `oferta.dados_tabela`)
2. Cria `Embarque` com:
   - `transportadora_id` = freteiro que aceitou
   - `tipo_carga` = lote.tipo_carga
   - `modalidade` = lote.modalidade
   - `lote_despacho_id` = lote.id
   - `status` = 'ativo'
3. Para cada `LoteDespachoItem`, cria `EmbarqueItem` com `separacao_lote_id`
4. Atualiza `Separacao.cotacao_id` para vincular ao embarque
5. Se tipo DIRETA: cria `RastreamentoEmbarque`

---

## 6. Arquivos a Criar/Modificar

### Novos Arquivos

```
app/despacho/
├── __init__.py                        # Blueprint registration
├── models.py                          # LoteDespacho, LoteDespachoItem, OfertaFreteiro
├── routes.py                          # Rotas internas (auth) + publicas (token)
└── services/
    ├── __init__.py
    ├── despacho_service.py            # Criacao de lote, dispatch, processamento
    ├── whatsapp_service.py            # Abstrai API WhatsApp (Evolution/Z-API)
    └── embarque_auto_service.py       # Cria embarque a partir de lote confirmado

app/templates/despacho/
├── lote_detalhe.html                  # Dashboard do lote com freteiros e status
├── oferta_publica.html                # Pagina mobile-first para freteiro (sem base.html)
└── oferta_expirada.html               # "Oferta ja preenchida"

app/static/css/modules/_despacho.css   # Estilos do modulo

scripts/migrations/
├── criar_lotes_despacho.py            # Migration Python (LoteDespacho + LoteDespachoItem)
├── criar_lotes_despacho.sql           # SQL idempotente para Render Shell
├── criar_ofertas_freteiro.py          # Migration Python (OfertaFreteiro)
├── criar_ofertas_freteiro.sql         # SQL idempotente para Render Shell
├── adicionar_contato_transportadora.py  # +4 campos contato
├── adicionar_contato_transportadora.sql
├── adicionar_lote_despacho_embarque.py  # +lote_despacho_id FK em embarques
└── adicionar_lote_despacho_embarque.sql
```

### Arquivos Modificados

```
app/transportadoras/models.py          # +4 campos de contato (telefone, email, whatsapp, aceita_despacho)
app/transportadoras/forms.py           # +campos de contato no form de edicao
app/embarques/models.py                # +lote_despacho_id FK
app/cotacao/routes.py                  # +botao "Despachar para Freteiros" na logica
app/templates/cotacao/cotacao.html     # +botao no template
app/templates/base.html                # +link "Despachos" no menu lateral
app/__init__.py                        # Registrar blueprint despacho
```

---

## 7. Seguranca

### Token de Oferta
- **64 caracteres** gerados via `secrets.token_urlsafe(48)`
- Brute-force inviavel: 256^48 combinacoes
- Cada oferta tem token unico indexado

### Codigo de Resposta WhatsApp
- **6 caracteres alfanumericos uppercase** (ex: "ABC123")
- Curto para o freteiro digitar no WhatsApp
- Unico por oferta, indexado

### Rate Limiting
- Max **10 requests/min por IP** na rota publica `/despacho/oferta/<token>`
- Previne abuso de scraping ou tentativa de brute-force

### Expiracao
- Ofertas expiram apos X horas (configuravel via `DESPACHO_EXPIRACAO_HORAS`, default 24h)
- Job periodico verifica e expira ofertas vencidas
- Link expirado mostra pagina informativa

### Race Condition (First-to-Accept)
- `SELECT ... FOR UPDATE` no `LoteDespacho` ao processar aceite
- Garante que apenas 1 freteiro consegue aceitar o lote
- Segundo freteiro recebe "Oferta ja preenchida por outro freteiro"

### Webhook WhatsApp
- Validar assinatura/secret da API (header especifico do provider)
- Rejeitar requests sem assinatura valida
- Logar tentativas invalidas

### Auditoria
- Toda resposta registra: IP, user-agent, canal (link/whatsapp), timestamp
- Historico completo de envios e respostas por oferta

---

## 8. Fases de Implementacao

### Fase 1: Fundacao (Estimativa: 1-2 semanas)

**Objetivo**: Infraestrutura basica, modelos e migrations.

- [ ] Criar modulo `app/despacho/` com `__init__.py`
- [ ] Criar models: `LoteDespacho`, `LoteDespachoItem`, `OfertaFreteiro`
- [ ] Criar migrations (Python + SQL) para todas as tabelas
- [ ] Adicionar campos de contato em `Transportadora`
- [ ] Adicionar `lote_despacho_id` em `Embarque`
- [ ] Registrar blueprint em `app/__init__.py`
- [ ] Executar migrations em staging

### Fase 2: Criacao de Lote + Tela de Despacho (Estimativa: 1-2 semanas)

**Objetivo**: Permitir criar lotes e visualizar freteiros elegiveis.

- [ ] Implementar `despacho_service.py`: criar lote a partir de pedidos selecionados
- [ ] Calcular frete por freteiro (reutilizar logica de cotacao existente)
- [ ] Criar rota `GET /despacho/lote/<id>` com template `lote_detalhe.html`
- [ ] Adicionar botao "Despachar para Freteiros" na tela de cotacao
- [ ] Gerar tokens e codigos de resposta
- [ ] Link "Despachos" no menu lateral
- [ ] CSS do modulo (`_despacho.css`)

### Fase 3: Link Publico + Aceite Manual (Estimativa: 1 semana)

**Objetivo**: Freteiro pode aceitar/recusar via link (sem WhatsApp ainda).

- [ ] Criar rota publica `GET /despacho/oferta/<token>` (sem auth)
- [ ] Template mobile-first `oferta_publica.html` (standalone)
- [ ] Rota `POST /despacho/oferta/<token>/responder`
- [ ] `processar_resposta()` com lock otimista
- [ ] Auto-criacao de embarque (`embarque_auto_service.py`)
- [ ] Expiracao de ofertas concorrentes
- [ ] Botao "Copiar Links" na tela de despacho
- [ ] Template `oferta_expirada.html`
- [ ] Rate limiting na rota publica

### Fase 4: Integracao WhatsApp API (Estimativa: 2-3 semanas)

**Objetivo**: Envio e recebimento automatico via WhatsApp.

- [ ] Escolher e configurar API WhatsApp (Evolution API ou Z-API)
- [ ] Deploy da API WhatsApp (se self-hosted) no Render
- [ ] Implementar `whatsapp_service.py` (envio de mensagem)
- [ ] Implementar webhook `POST /despacho/webhook/whatsapp`
- [ ] Parsing de respostas: "SIM CODIGO" / "NAO CODIGO"
- [ ] Validacao de assinatura do webhook
- [ ] Formulario de contato na tela de transportadora (whatsapp, opt-in)
- [ ] Botao "Enviar para Todos via WhatsApp" na tela de despacho
- [ ] Confirmacao de volta ao freteiro apos aceite/recusa

### Fase 5: Refinamentos e Producao (Estimativa: 1 semana)

**Objetivo**: Polish, monitoramento e deploy em producao.

- [ ] Job periodico para expirar ofertas vencidas
- [ ] Notificacoes no sistema (toast/badge) quando freteiro confirma
- [ ] Dashboard de lotes com filtros (status, data, cidade)
- [ ] Listagem de todos os lotes na tela de despachos
- [ ] Relatorio: taxa de aceite por freteiro, tempo medio de resposta
- [ ] Testes end-to-end do fluxo completo
- [ ] Deploy em producao

### Timeline Estimada Total: 6-9 semanas

```
Semana 1-2:  [████████] Fase 1 — Fundacao
Semana 3-4:  [████████] Fase 2 — Lote + Tela
Semana 5:    [████]     Fase 3 — Link Publico
Semana 6-8:  [████████████] Fase 4 — WhatsApp
Semana 9:    [████]     Fase 5 — Refinamentos
```

---

## 9. Verificacao e Testes

### Cenarios de Teste

| # | Cenario | Entrada | Saida Esperada |
|---|---------|---------|----------------|
| 1 | Criar lote | Selecionar 3 pedidos para Manaus/AM | `LoteDespacho` criado com 3 `LoteDespachoItem` |
| 2 | Freteiros elegiveis | Lote para Manaus, van | Apenas freteiros com tabela Manaus + van aparecem |
| 3 | Valor por freteiro | 2 freteiros com tabelas diferentes | Cada um ve valor calculado pela tabela dele |
| 4 | Envio WhatsApp | Clicar "Enviar via WhatsApp" | Mensagem recebida no celular do freteiro |
| 5 | Link publico | Abrir `/despacho/oferta/<token>` no celular | Pagina mobile mostra detalhes e botoes |
| 6 | Aceite via link | Clicar "Aceitar Carga" | Embarque criado, demais ofertas expiradas |
| 7 | Aceite via WhatsApp | Responder "SIM ABC123" | Webhook recebe, embarque criado |
| 8 | Race condition | 2 freteiros aceitam simultaneamente | Apenas 1 embarque criado, outro recebe erro |
| 9 | Expiracao | 24h sem resposta | Ofertas marcadas como expiradas |
| 10 | Fluxo paralelo | Cotacao normal (sem despacho) | Funciona normalmente, sem interferencia |
| 11 | Freteiro recusa | Clicar "Recusar" com motivo | Oferta marcada como recusada, motivo salvo |
| 12 | Todos recusam | Todos os freteiros recusam | Lote muda para status EXPIRADO |
| 13 | Link ja usado | Abrir link apos outro aceitar | Mostra pagina "Oferta ja preenchida" |
| 14 | Cancelar lote | Cancelar lote antes de enviar | Status CANCELADO, ofertas expiradas |

---

## 10. Codigo de Referencia Existente

### Logica de Cotacao (reutilizar)

**Arquivo**: `app/cotacao/routes.py`
- Linhas ~1450-1596: Criacao de embarque a partir de cotacao
- Logica de criacao de `EmbarqueItem` a partir de separacoes
- Vinculacao de `Separacao.cotacao_id`
- Criacao de `RastreamentoEmbarque` para carga DIRETA

### Calculo de Frete (reutilizar)

**Skill**: `cotando-frete`
- Calculo de frete por tabela de transportadora
- Resolucao de cidade/UF para parametros da tabela
- Logica de peso cubado vs peso bruto

### Modelos Existentes

- `app/transportadoras/models.py` — Transportadora (adicionar campos)
- `app/embarques/models.py` — Embarque (adicionar FK)
- `app/separacao/models.py` — Separacao (vincular ao embarque)
- `app/cotacao/models.py` — Cotacao (criar snapshot)

### Template de Referencia (mobile-first)

A pagina publica de oferta (`oferta_publica.html`) deve ser:
- Standalone (sem `base.html`, sem menu, sem auth)
- Mobile-first (maioria dos freteiros abre pelo celular)
- Simples: logo + dados da carga + 2 botoes grandes
- Dark/light mode nao necessario (pagina simples)

---

## Apendice: Glossario

| Termo | Significado |
|-------|-------------|
| **Freteiro** | Transportador autonomo (pessoa fisica ou pequena empresa) contratado por viagem |
| **Lote de Despacho** | Agrupamento de pedidos para uma mesma cidade/modalidade, oferecido a freteiros |
| **Oferta** | Proposta enviada a um freteiro especifico com valor pre-calculado |
| **First-to-accept** | Modelo onde o primeiro freteiro a responder "SIM" ganha a carga |
| **Token** | Identificador unico de 64 chars para acesso publico a oferta (sem login) |
| **Codigo de resposta** | Identificador curto de 6 chars para resposta via WhatsApp |
| **Despacho** | Ato de enviar ofertas aos freteiros (mudar status do lote para DESPACHADO) |
| **Target** | Combinacao cidade + modalidade que define quais freteiros sao elegiveis |
