# HORA — Transferência entre Filiais + Registro de Avaria

**Data**: 2026-04-22
**Módulo**: `app/hora/` (Lojas HORA — PJ varejo B2C de motos elétricas)
**Status**: spec aprovado — aguardando plano de implementação
**Author**: brainstorming colaborativo (Rafael + Claude)

---

## 1. Contexto e motivação

O módulo HORA (`app/hora/`) já cobre pedido → NF → recebimento → conferência → venda + devolução/peças faltando. Duas lacunas operacionais:

1. **Transferência de motos entre lojas** — hoje sem rastreio sistêmico. Ex: Tatuapé tem 3 unidades de um modelo, Bragança vendeu as últimas e precisa de 1.
2. **Registro de avaria em moto que já está no estoque** — avaria só é capturada hoje no momento da conferência de recebimento (`hora_recebimento_conferencia.avaria_fisica`). Não há fluxo para avarias surgidas **depois** (test-drive, queda na loja, dano de armazenagem).

Ambas preservam os 4 invariantes do módulo (`app/hora/CLAUDE.md:45-56`):
- chassi é chave universal;
- toda transacional tem FK chassi indexada;
- `hora_moto` é insert-once (nunca UPDATE);
- estado atual = último evento em `hora_moto_evento` (append-only).

---

## 2. Decisões aprovadas (brainstorming 2026-04-22)

| # | Decisão | Resposta |
|---|---------|----------|
| D1 | Fluxo de transferência | **Em trânsito (2 eventos)** — A emite `EM_TRANSITO`, B confirma com `TRANSFERIDA` |
| D2 | Avaria bloqueia venda? | **Não bloqueia, apenas registra** — moto continua vendável com badge de aviso |
| D3 | Detalhes obrigatórios de avaria | **Fotos obrigatórias + descrição textual + múltiplas avarias por moto**. Sem tipo enum. |
| D4 | Cancelamento em trânsito | **Origem cancela enquanto em trânsito** (motivo obrigatório). Após `CONFIRMADA`, não cancela. |
| D5 | Tabela de auditoria dedicada | **Sim na Fase 1** (`hora_transferencia_auditoria`, append-only) |
| D6 | Foto na confirmação do destino | **Opcional** |
| D7 | Motivo de cancelamento | **Obrigatório** (CHECK constraint + validação service) |
| D8 | Escopo de loja | **Usuário escopado emite apenas da sua loja** (admin sem restrição) |

---

## 3. Arquitetura de alto nível

```
     ┌─────────────────────────────────────────────────────────────┐
     │                    hora_moto_evento (log)                   │
     │  Invariante 4: estado atual = último evento por chassi      │
     └─────────────────────────────────────────────────────────────┘
                                  ▲
          ┌───────────────────────┼──────────────────────┐
          │                       │                      │
    Transferência              Avaria                Recebimento / Venda
    (NOVO)                     (NOVO)                (existente)
    - header                   - header              - recebimento
    - item (N chassis)         - foto (N fotos)      - conferência
    - auditoria                                      - venda / item
    - emite EM_TRANSITO        - emite AVARIADA
    - emite TRANSFERIDA
    - emite CANCELADA
```

### 3.1 Novos tipos de evento em `moto_service.TIPOS_VALIDOS`

Adicionar em `app/hora/services/moto_service.py:65-69`:

- `EM_TRANSITO` — saiu da loja origem e ainda não chegou no destino
- `CANCELADA` — transferência cancelada; moto retornou pra origem

`AVARIADA` e `TRANSFERIDA` já existem e serão reutilizados.

### 3.2 Ajuste em `estoque_service.EVENTOS_EM_ESTOQUE`

- **Incluir**: `CANCELADA` (moto retornou pra origem e volta a estoque)
- **NÃO incluir**: `EM_TRANSITO` (moto em limbo, não é estoque vendável de nenhuma loja)

Nova categoria virtual de listagem: "Motos em trânsito" (último evento = `EM_TRANSITO`), visível em ambas lojas envolvidas.

---

## 4. Modelo de dados

### 4.1 `hora_transferencia` (header)

| Campo | Tipo | Constraints |
|---|---|---|
| `id` | BIGSERIAL | PK |
| `loja_origem_id` | INT | NOT NULL, FK → `hora_loja.id`, INDEX |
| `loja_destino_id` | INT | NOT NULL, FK → `hora_loja.id`, INDEX, `CHECK (loja_origem_id <> loja_destino_id)` |
| `status` | VARCHAR(30) | NOT NULL, INDEX, valores: `EM_TRANSITO`, `CONFIRMADA`, `CANCELADA` |
| `emitida_em` | TIMESTAMP | NOT NULL |
| `emitida_por` | VARCHAR(100) | NOT NULL |
| `confirmada_em` | TIMESTAMP | NULL |
| `confirmada_por` | VARCHAR(100) | NULL |
| `cancelada_em` | TIMESTAMP | NULL |
| `cancelada_por` | VARCHAR(100) | NULL |
| `motivo_cancelamento` | VARCHAR(255) | NULL |
| `observacoes` | TEXT | NULL |
| `criado_em` | TIMESTAMP | NOT NULL (default `agora_utc_naive()`) |
| `atualizado_em` | TIMESTAMP | NOT NULL |

**CHECK composto (motivo obrigatório quando cancelada)**:
```sql
CHECK (
  (cancelada_em IS NULL AND motivo_cancelamento IS NULL)
  OR
  (cancelada_em IS NOT NULL
    AND motivo_cancelamento IS NOT NULL
    AND length(trim(motivo_cancelamento)) >= 3)
)
```

**CHECK de coerência de datas**:
```sql
CHECK (confirmada_em IS NULL OR confirmada_em >= emitida_em)
CHECK (cancelada_em IS NULL OR cancelada_em >= emitida_em)
CHECK (NOT (confirmada_em IS NOT NULL AND cancelada_em IS NOT NULL))  -- mutuamente exclusivos
```

### 4.2 `hora_transferencia_item` (linha)

| Campo | Tipo | Constraints |
|---|---|---|
| `id` | BIGSERIAL | PK |
| `transferencia_id` | INT | NOT NULL, FK → `hora_transferencia.id` ON DELETE CASCADE, INDEX |
| `numero_chassi` | VARCHAR(30) | NOT NULL, FK → `hora_moto.numero_chassi`, INDEX |
| `conferido_destino_em` | TIMESTAMP | NULL |
| `conferido_destino_por` | VARCHAR(100) | NULL |
| `qr_code_lido` | BOOLEAN | NOT NULL DEFAULT FALSE |
| `foto_s3_key` | VARCHAR(500) | NULL (opcional) |
| `observacao_item` | TEXT | NULL |

**UNIQUE**: `(transferencia_id, numero_chassi)` — mesmo chassi não repete na mesma transferência.

**Validação de unicidade de trânsito ativo** (no service, não no DB, pois PostgreSQL UNIQUE parcial com subquery é limitado):
```python
# app/hora/services/transferencia_service.py
def _validar_chassi_disponivel(numero_chassi):
    em_transito = db.session.query(HoraTransferenciaItem.id).join(
        HoraTransferencia
    ).filter(
        HoraTransferenciaItem.numero_chassi == numero_chassi,
        HoraTransferencia.status == 'EM_TRANSITO',
    ).first()
    if em_transito:
        raise ValueError(f"Chassi {numero_chassi} já está em trânsito (transferência ativa)")
```

### 4.3 `hora_transferencia_auditoria` (append-only)

Padrão idêntico ao `hora_conferencia_auditoria`.

| Campo | Tipo | Constraints |
|---|---|---|
| `id` | BIGSERIAL | PK |
| `transferencia_id` | INT | NOT NULL, FK → `hora_transferencia.id` ON DELETE CASCADE, INDEX |
| `item_id` | INT | NULL, FK → `hora_transferencia_item.id`, INDEX |
| `usuario` | VARCHAR(100) | NOT NULL |
| `acao` | VARCHAR(40) | NOT NULL, INDEX, valores: `EMITIU`, `CONFIRMOU_ITEM`, `FINALIZOU`, `CANCELOU`, `ADICIONOU_FOTO`, `EDITOU_OBSERVACAO` |
| `campo_alterado` | VARCHAR(60) | NULL |
| `valor_antes` | TEXT | NULL |
| `valor_depois` | TEXT | NULL |
| `detalhe` | TEXT | NULL |
| `criado_em` | TIMESTAMP | NOT NULL |

**Índice composto**: `(transferencia_id, criado_em DESC)` — timeline rápida.

**Regra de service**: `append-only`. Nunca UPDATE/DELETE. Registra em cada ação.

### 4.4 `hora_avaria` (header)

| Campo | Tipo | Constraints |
|---|---|---|
| `id` | BIGSERIAL | PK |
| `numero_chassi` | VARCHAR(30) | NOT NULL, FK → `hora_moto.numero_chassi`, INDEX |
| `loja_id` | INT | NOT NULL, FK → `hora_loja.id`, INDEX — loja onde estava quando avaria registrada (snapshot) |
| `descricao` | TEXT | NOT NULL, `CHECK (length(trim(descricao)) >= 3)` |
| `status` | VARCHAR(20) | NOT NULL DEFAULT 'ABERTA', INDEX, valores: `ABERTA`, `RESOLVIDA`, `IGNORADA` |
| `criado_em` | TIMESTAMP | NOT NULL, INDEX |
| `criado_por` | VARCHAR(100) | NOT NULL |
| `resolvido_em` | TIMESTAMP | NULL |
| `resolvido_por` | VARCHAR(100) | NULL |
| `resolucao_observacao` | TEXT | NULL |

**CHECK**: `resolvido_em IS NULL OR status IN ('RESOLVIDA','IGNORADA')` (coerência estado).

### 4.5 `hora_avaria_foto` (N fotos por avaria)

| Campo | Tipo | Constraints |
|---|---|---|
| `id` | BIGSERIAL | PK |
| `avaria_id` | INT | NOT NULL, FK → `hora_avaria.id` ON DELETE CASCADE, INDEX |
| `foto_s3_key` | VARCHAR(500) | NOT NULL |
| `legenda` | VARCHAR(255) | NULL |
| `criado_em` | TIMESTAMP | NOT NULL |
| `criado_por` | VARCHAR(100) | NOT NULL |

**Regra de service** (não DB): ao criar `hora_avaria`, exigir ≥ 1 `hora_avaria_foto` na mesma transaction. Se não houver foto, rollback.

---

## 5. Fluxo de eventos (`hora_moto_evento`)

### 5.1 Transferência — 3 tipos de evento

| Momento | `tipo` | `loja_id` | `origem_tabela` | `origem_id` | `detalhe` exemplo |
|---|---|---|---|---|---|
| Loja A emite | `EM_TRANSITO` | **destino (B)** | `hora_transferencia_item` | `item.id` | `"Transf #42: de Tatuapé (1) para Bragança (2)"` |
| Loja B confirma item | `TRANSFERIDA` | **destino (B)** | `hora_transferencia_item` | `item.id` | `"Chegou em Bragança via Transf #42"` |
| Loja A cancela em trânsito | `CANCELADA` | **origem (A)** | `hora_transferencia` | `transferencia.id` | `"Transf #42 cancelada: <motivo>"` |

**Justificativa do `loja_id`**:
- `EM_TRANSITO` com `loja_id=destino`: operador da loja destino vê "motos chegando" filtrado por sua loja.
- `CANCELADA` com `loja_id=origem`: moto volta pra origem administrativamente; listagem da origem volta a mostrar.

**Padrão de emissão no service**:
```python
registrar_evento(
    numero_chassi=chassi,
    tipo='EM_TRANSITO',
    origem_tabela='hora_transferencia_item',
    origem_id=item.id,
    loja_id=transferencia.loja_destino_id,
    operador=usuario,
    detalhe=f"Transf #{transferencia.id}: de {origem.rotulo_display} para {destino.rotulo_display}",
)
```

### 5.2 Avaria — 1 evento por ocorrência

| Momento | `tipo` | `loja_id` | `origem_tabela` | `origem_id` | `detalhe` exemplo |
|---|---|---|---|---|---|
| Operador registra avaria | `AVARIADA` | loja atual | `hora_avaria` | `avaria.id` | `"Avaria #17: arranhão profundo no para-lama esquerdo"` (truncado em 180 chars) |
| Operador resolve/ignora | **sem evento** | — | — | — | apenas UPDATE em `hora_avaria.status` |

**Badge em listagem**: moto com ≥1 `hora_avaria` com `status='ABERTA'` ganha badge "⚠ Avariada (N)" na listagem de estoque. Query:

```python
def avarias_abertas_por_chassi(chassis: list[str]) -> dict[str, int]:
    rows = (
        db.session.query(HoraAvaria.numero_chassi, db.func.count(HoraAvaria.id))
        .filter(
            HoraAvaria.numero_chassi.in_(chassis),
            HoraAvaria.status == 'ABERTA',
        )
        .group_by(HoraAvaria.numero_chassi)
        .all()
    )
    return dict(rows)
```

---

## 6. Services e responsabilidades

### 6.1 `app/hora/services/transferencia_service.py` (novo)

```python
def criar_transferencia(
    loja_origem_id: int,
    loja_destino_id: int,
    chassis: list[str],
    usuario: str,
    observacoes: Optional[str] = None,
) -> HoraTransferencia:
    """
    Validações:
    - loja_origem_id != loja_destino_id
    - usuário tem acesso à loja_origem_id (auth_helper)
    - usuário escopado: loja_origem_id == user.loja_hora_id
    - len(chassis) >= 1
    - cada chassi: último evento ∈ EVENTOS_EM_ESTOQUE E loja_id == loja_origem_id
    - cada chassi: não pode estar em outra transf EM_TRANSITO

    Cria: header (status=EM_TRANSITO) + 1 item por chassi + N eventos EM_TRANSITO
         + 1 registro auditoria (EMITIU).
    """

def confirmar_item_destino(
    transferencia_id: int,
    numero_chassi: str,
    usuario: str,
    qr_code_lido: bool,
    foto_s3_key: Optional[str] = None,
    observacao: Optional[str] = None,
) -> HoraTransferenciaItem:
    """
    Idempotente (se já confirmado, no-op).
    Validações:
    - transferência.status == EM_TRANSITO
    - usuário tem acesso à loja_destino
    - chassi pertence à transferência

    UPDATE item: conferido_destino_em, conferido_destino_por, qr_code_lido, foto_s3_key.
    Emite evento TRANSFERIDA.
    Registra auditoria (CONFIRMOU_ITEM).
    Ao final, chama finalizar_se_tudo_confirmado.
    """

def finalizar_se_tudo_confirmado(transferencia_id: int) -> bool:
    """
    Se todos itens têm conferido_destino_em != NULL:
      UPDATE transferencia SET status=CONFIRMADA, confirmada_em=now, confirmada_por=last_user
      Registra auditoria (FINALIZOU).
      Retorna True.
    Caso contrário, retorna False.
    """

def cancelar_transferencia(
    transferencia_id: int,
    motivo: str,
    usuario: str,
) -> HoraTransferencia:
    """
    Validações:
    - status == EM_TRANSITO
    - motivo: length(trim(motivo)) >= 3
    - usuário tem acesso à loja_origem (ou admin)

    UPDATE transferencia: status=CANCELADA, cancelada_em, cancelada_por, motivo_cancelamento.
    Para cada chassi ainda não confirmado no destino: emite evento CANCELADA (loja_id=origem).
    Para itens JÁ confirmados (edge case race): não emite CANCELADA; loga em auditoria.
    Registra auditoria (CANCELOU, detalhe=motivo).
    """
```

### 6.2 `app/hora/services/avaria_service.py` (novo)

```python
def registrar_avaria(
    numero_chassi: str,
    descricao: str,
    fotos: list[tuple[str, Optional[str]]],  # (s3_key, legenda)
    usuario: str,
    loja_id: Optional[int] = None,  # se None: deriva da última loja_id do chassi
) -> HoraAvaria:
    """
    Validações:
    - len(fotos) >= 1
    - len(descricao.strip()) >= 3
    - chassi existe em hora_moto
    - chassi tem último evento em EVENTOS_EM_ESTOQUE (não pode avariar moto vendida)
    - usuário tem acesso à loja_id

    Cria avaria + N fotos na mesma transaction.
    Emite evento AVARIADA.
    """

def adicionar_foto(
    avaria_id: int,
    s3_key: str,
    legenda: Optional[str],
    usuario: str,
) -> HoraAvariaFoto:
    """Adiciona foto em avaria existente (qualquer status)."""

def resolver_avaria(
    avaria_id: int,
    observacao: str,
    usuario: str,
) -> HoraAvaria:
    """UPDATE status=RESOLVIDA, resolvido_em, resolvido_por, resolucao_observacao."""

def ignorar_avaria(
    avaria_id: int,
    observacao: str,
    usuario: str,
) -> HoraAvaria:
    """UPDATE status=IGNORADA + timestamps."""

def avarias_abertas_por_chassi(chassis: list[str]) -> dict[str, int]:
    """Para badge na listagem de estoque. Retorna {chassi: count}."""
```

### 6.3 `app/hora/services/transferencia_audit.py` (novo)

Padrão idêntico ao `recebimento_audit.py`:

```python
def registrar_auditoria(
    transferencia_id: int,
    usuario: str,
    acao: str,
    item_id: Optional[int] = None,
    campo_alterado: Optional[str] = None,
    valor_antes: Optional[str] = None,
    valor_depois: Optional[str] = None,
    detalhe: Optional[str] = None,
) -> HoraTransferenciaAuditoria:
    """Append-only. Nunca UPDATE/DELETE."""
```

### 6.4 Ajustes em services existentes

**`app/hora/services/moto_service.py:65-69`**:
```python
TIPOS_VALIDOS = {
    'RECEBIDA', 'CONFERIDA', 'TRANSFERIDA',
    'EM_TRANSITO', 'CANCELADA',            # NOVOS
    'RESERVADA', 'VENDIDA', 'DEVOLVIDA', 'AVARIADA',
    'FALTANDO_PECA',
}
```

**`app/hora/services/estoque_service.py`**:
```python
EVENTOS_EM_ESTOQUE = (
    'RECEBIDA', 'CONFERIDA', 'TRANSFERIDA',
    'CANCELADA',                # NOVO: moto retornou à origem
    'AVARIADA', 'FALTANDO_PECA',
)
# EM_TRANSITO NÃO entra (moto em limbo)

# Novo helper para consulta categoria "em trânsito"
def listar_em_transito(lojas_permitidas_ids=None) -> list[dict]:
    """Retorna motos com último evento EM_TRANSITO, filtrado por loja_id do evento."""
```

**`app/hora/services/auth_helper.py`** (novo helper):
```python
def loja_origem_permitida_para_transferencia() -> Optional[int]:
    """
    Se user escopado: retorna user.loja_hora_id (origem obrigatória).
    Se admin: retorna None (permite escolher).
    """
```

---

## 7. Rotas e UI

### 7.1 Transferência — `app/hora/routes/transferencias.py` (novo)

| Método | Rota | Função | Tela |
|---|---|---|---|
| GET | `/hora/transferencias` | `transferencias_lista` | lista com filtros |
| GET | `/hora/transferencias/<id>` | `transferencia_detalhe` | detalhe + timeline auditoria |
| GET, POST | `/hora/transferencias/nova` | `transferencia_nova` | formulário emissão |
| GET | `/hora/transferencias/<id>/confirmar` | `transferencia_confirmar_wizard` | wizard destino |
| POST | `/hora/transferencias/<id>/confirmar-item` | `transferencia_confirmar_item` (AJAX) | scan QR + confirma 1 chassi |
| POST | `/hora/transferencias/<id>/cancelar` | `transferencia_cancelar` | cancela (motivo obrigatório) |
| GET | `/hora/transferencias/<id>/auditoria` | `transferencia_auditoria_json` (AJAX) | timeline JSON |

**Templates** (em `app/templates/hora/`):
- `transferencias_lista.html` — tabela, filtros status/loja/período, contadores
- `transferencia_nova.html` — selector loja destino + multi-select chassis com autocomplete (só mostra chassis em estoque da loja origem)
- `transferencia_detalhe.html` — header + tabela de itens (conferidos vs pendentes) + timeline auditoria + botão cancelar (se status=EM_TRANSITO e user=origem)
- `transferencia_confirmar_wizard.html` — wizard A-B-C (padrão `recebimento_wizard.html`): scan QR → foto opcional → observação → confirma

### 7.2 Avaria — `app/hora/routes/avarias.py` (novo)

| Método | Rota | Função | Tela |
|---|---|---|---|
| GET | `/hora/avarias` | `avarias_lista` | lista com filtros |
| GET | `/hora/avarias/<id>` | `avaria_detalhe` | detalhe + galeria fotos |
| GET, POST | `/hora/avarias/nova` | `avaria_nova` | formulário |
| POST | `/hora/avarias/<id>/foto` | `avaria_adicionar_foto` | upload foto extra |
| POST | `/hora/avarias/<id>/resolver` | `avaria_resolver` | resolver |
| POST | `/hora/avarias/<id>/ignorar` | `avaria_ignorar` | ignorar |

**Templates**:
- `avarias_lista.html` — tabela, filtros status/loja/chassi/período
- `avaria_detalhe.html` — descrição, status, fotos (galeria com legenda), botões resolver/ignorar, histórico
- `avaria_nova.html` — autocomplete chassi (restrito a estoque do user), descrição, upload N fotos com legenda por foto (drag-and-drop ou múltiplo)

### 7.3 Menu (`app/templates/base.html`)

Adicionar 2 entries no dropdown "Lojas HORA" (antes de "Dashboard" ou após "Estoque"):

```html
<a class="dropdown-item" href="{{ url_for('hora.transferencias_lista') }}">
  <i class="fas fa-exchange-alt"></i> Transferências
</a>
<a class="dropdown-item" href="{{ url_for('hora.avarias_lista') }}">
  <i class="fas fa-exclamation-triangle"></i> Avarias
</a>
```

### 7.4 Integrações com telas existentes

**`app/templates/hora/estoque_lista.html`**:
- Badge "↔ Em trânsito" em motos com último evento = `EM_TRANSITO` (coluna status)
- Badge "⚠ Avariada (N)" em motos com N avarias abertas
- Filtros: `incluir_em_transito` (default false), `incluir_avariadas` (já existe)

**`app/templates/hora/estoque_chassi_detalhe.html`**:
- Nova seção "Transferências" (lista todas as transf com este chassi)
- Nova seção "Avarias" (lista avarias abertas e resolvidas com fotos)

---

## 8. Regras de autorização

| Ação | Quem pode |
|---|---|
| Emitir transferência | Usuário com acesso à loja origem. Escopado: `loja_origem = user.loja_hora_id`. Admin: qualquer origem. |
| Confirmar item no destino | Usuário com acesso à loja destino. Admin: qualquer destino. |
| Cancelar em trânsito | Usuário com acesso à loja origem. Admin: qualquer. |
| Listar transferências | Filtra por `lojas_permitidas_ids()`: escopado vê só transf onde sua loja é origem ou destino. |
| Registrar avaria | Usuário com acesso à loja da moto. |
| Resolver/ignorar avaria | Mesmo usuário que registrou **ou** admin. (Valida no service.) |
| Listar avarias | Filtra por `lojas_permitidas_ids()`. |

Decorators reutilizados: `@require_lojas` em todas as rotas; admin-only não é necessário nesta fase.

---

## 9. Migrations (regra do projeto — dois artefatos)

**`scripts/migrations/hora_13_transferencia_e_avaria.sql`** — DDL idempotente (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`).

**`scripts/migrations/hora_13_transferencia_e_avaria.py`** — `create_app()` + verificação before/after + `sys.path.insert` (regra feedback 2026-04-22).

**Ordem**:
1. `hora_transferencia` (com CHECKs)
2. `hora_transferencia_item` (FK → transferencia, UNIQUE composto)
3. `hora_transferencia_auditoria` (FK → transferencia/item)
4. `hora_avaria` (CHECKs)
5. `hora_avaria_foto` (FK → avaria)

Sem DROP — migration apenas aditiva (não toca schema existente).

---

## 10. Schemas JSON (`.claude/skills/consultando-sql/schemas/tables/`)

Criar/atualizar:
- `hora_transferencia.json`
- `hora_transferencia_item.json`
- `hora_transferencia_auditoria.json`
- `hora_avaria.json`
- `hora_avaria_foto.json`

(Auto-gerados pelo script do projeto após migration rodar — **confirmar** se o script é manual ou automático.)

---

## 11. S3 storage (fotos)

Reusar padrão de `hora_peca_faltando_foto` e `hora_recebimento_conferencia.foto_s3_key`:

- Bucket: o mesmo já usado pelo módulo HORA (verificar `.claude/references/S3_STORAGE.md`).
- Prefixo: `hora/avarias/{avaria_id}/{uuid}.jpg` (foto avaria), `hora/transferencias/{transf_id}/{item_id}/{uuid}.jpg` (foto confirmação destino).
- Upload antes de INSERT (mesma transaction não garante atomicidade, mas é o padrão do módulo).

---

## 12. Fora de escopo (Fase 2)

- NF de transferência (CNPJs diferentes → operação fiscal) — fora do escopo agora; será parte da Fase 2 financeira/fiscal.
- Evento `CONSERTADA` — não implementado; resolução é apenas mudança de status em `hora_avaria`.
- Integração com frete CarVia para mover motos entre lojas.
- Fotos obrigatórias na confirmação do destino (ficaram opcionais).
- Reconferência em transferência (ex.: destino diz "não é esse chassi") — a divergência é tratada manualmente: cancela + abre nova.

---

## 13. Riscos e trade-offs

| Risco | Mitigação |
|---|---|
| Race condition: 2 usuários confirmam mesmo item simultaneamente | `confirmar_item_destino` é idempotente; UNIQUE em `(transferencia_id, numero_chassi)` impede duplicação |
| Race condition: loja origem cancela enquanto destino confirma | Service recarrega status com `FOR UPDATE` (SELECT FOR UPDATE no header antes de mutar). Se já confirmado, bloqueia cancelamento. |
| Chassi em transferência indefinidamente (esqueceram de confirmar) | Fase 2: job noturno que envia alerta para gestor após X dias. Fora de escopo agora. |
| Upload S3 falha após INSERT: avaria sem fotos | Service faz upload ANTES de INSERT; se upload falha, rollback. |
| Usuário escopado tenta emitir transferência de outra loja via POST manipulado | Service valida `loja_origem == user.loja_hora_id` antes de qualquer gravação. |
| Motivo de cancelamento vazio contorna o CHECK via whitespace | `length(trim(motivo_cancelamento)) >= 3` no CHECK **e** validação adicional no service. |

---

## 14. Checklist de aceitação (pré-entrega)

### Backend
- [ ] 5 tabelas criadas via migration (SQL + Python)
- [ ] 5 models SQLAlchemy em `app/hora/models/`
- [ ] `TIPOS_VALIDOS` e `EVENTOS_EM_ESTOQUE` atualizados
- [ ] 3 services novos (`transferencia_service`, `transferencia_audit`, `avaria_service`)
- [ ] 1 helper novo em `auth_helper.py`
- [ ] Validações completas em cada service (escopo loja, estado chassi, race conditions)

### Frontend
- [ ] 2 arquivos de routes novos (`transferencias.py`, `avarias.py`)
- [ ] Blueprint importa ambos em `routes/__init__.py`
- [ ] 7 templates novos (`transferencias_lista.html`, `transferencia_nova.html`, `transferencia_detalhe.html`, `transferencia_confirmar_wizard.html`, `avarias_lista.html`, `avaria_detalhe.html`, `avaria_nova.html`)
- [ ] 2 itens de menu em `base.html`
- [ ] Badges em `estoque_lista.html` + seções novas em `estoque_chassi_detalhe.html`
- [ ] Validação JS (mín. 1 chassi na transferência, ≥1 foto na avaria, motivo ≥3 chars no cancelamento)

### Integração
- [ ] Schemas JSON atualizados para 5 novas tabelas
- [ ] CLAUDE.md do módulo HORA atualizado (`app/hora/CLAUDE.md`) com nova fase
- [ ] Invariantes preservados: nenhum UPDATE em `hora_moto`; estado via evento append-only
- [ ] Timezone naive Brasil em todos os timestamps
- [ ] S3 uploads antes de INSERT (padrão do módulo)

---

## 15. Referências

- `app/hora/CLAUDE.md` — invariantes do módulo
- `docs/hora/INVARIANTES.md` — contrato de design detalhado
- `app/hora/services/moto_service.py:65-69` — TIPOS_VALIDOS
- `app/hora/services/estoque_service.py` — EVENTOS_EM_ESTOQUE e padrão de query
- `app/hora/services/recebimento_audit.py` — padrão de auditoria append-only
- `app/hora/models/peca.py` — precedente de header + N fotos
- `app/hora/models/devolucao.py` — precedente de header + item + status + workflow
- `.claude/references/S3_STORAGE.md` — padrões S3
- `~/.claude/CLAUDE.md` seção MIGRATIONS — regra de dois artefatos

---

**Próximo passo**: após aprovação deste spec, invocar `superpowers:writing-plans` para gerar plano de implementação faseado (models → migrations → services → routes → templates → testes).
