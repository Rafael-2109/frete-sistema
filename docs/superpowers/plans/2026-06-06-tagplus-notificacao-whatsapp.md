<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-06
-->
# TagPlus → WhatsApp (Pedido/NF) — Implementation Plan

> **Papel:** plano de implementação task-by-task (TDD) da notificação WhatsApp de pedido criado / NF emitida no TagPlus, para **grupo único de vendas + DM do vendedor**, com PDF da DANFE anexado na NF. Implementa a spec [2026-06-06-tagplus-notificacao-whatsapp-design.md](../specs/2026-06-06-tagplus-notificacao-whatsapp-design.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ao receber `pedido_criado`/`nfe_criada` do TagPlus (webhook dedicado), enviar mensagem formatada ao grupo único de vendas e à DM do vendedor (quando identificável), com PDF da DANFE anexado na NF — sem tocar no fluxo de faturamento existente.

**Architecture:** Webhook dedicado csrf-exempt valida `X-Hub-Secret`, registra na tabela `tagplus_notificacao_whatsapp` e dispara uma `Thread(daemon=False)` (padrão do WhatsApp bot). A thread busca os detalhes na API TagPlus (`oauth_notas`), formata o texto, resolve o vendedor via `usuarios`, baixa o PDF (NF) e envia via `send_whatsapp` (estendido para anexo base64) ao grupo e à DM. Best-effort: falhas degradam (só-grupo / só-texto) e ficam visíveis numa tela de histórico com reenvio.

**Tech Stack:** Flask blueprint, SQLAlchemy, `requests` (mockado em teste), pytest, gateway OpenClaw (tool `message`), API TagPlus v2 (OAuth2).

---

## Indice

- [Setup de testes](#setup-de-testes-ler-antes-de-começar)
- [File Structure](#file-structure)
- [Task 0: Scaffolding](#task-0-scaffolding-pacote-services--pasta-de-testes)
- [Task 1: Estender send_whatsapp com anexo base64](#task-1-estender-send_whatsapp-com-anexo-base64)
- [Task 2: Model + migration dual](#task-2-model-tagplusnotificacaowhatsapp--migration-dual)
- [Task 3: Formatador de mensagens](#task-3-formatador-de-mensagens)
- [Task 4: Resolver vendedor](#task-4-resolver-vendedor-cadastro-usuarios)
- [Task 5: Service — busca, PDF e envio](#task-5-service--busca-pdf-e-envio-aos-destinos)
- [Task 6: Webhook route + blueprint](#task-6-webhook-route--registro-do-blueprint)
- [Task 7: Tela de histórico + reenvio + menu](#task-7-tela-de-histórico--reenvio--menu)
- [Task 8: Documentação operacional + verificação](#task-8-documentação-operacional--verificação-final)
- [Self-Review](#self-review-preenchido)

---

## Setup de testes (ler antes de começar)

- Rodar da **raiz do worktree**: `cd /home/rafaelnascimento/projetos/frete_tagplus_notif`.
- Testes que tocam DB precisam de `DATABASE_URL` apontando para o Postgres local (o worktree não tem `.env`). Exporte a partir do `.env` da árvore principal:
  ```bash
  export DATABASE_URL="$(grep -E '^DATABASE_URL=' /home/rafaelnascimento/projetos/frete_sistema/.env | head -1 | cut -d= -f2- | tr -d '"'"'"'"'"')"
  ```
- Testes puros (formatador, `send_whatsapp` com mock) **não** precisam de DB.
- Ativar venv: `source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate`.

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `app/utils/whatsapp_notify.py` (modificar) | `send_whatsapp` aceita anexo base64 (`buffer`/`filename`/`mimeType`/`caption`) |
| `app/integracoes/tagplus/models.py` (modificar) | + classe `TagPlusNotificacaoWhatsapp` (vive junto dos models TagPlus já importados — garante registro no metadata) |
| `scripts/migrations/2026_06_06_tagplus_notificacao_whatsapp.py` / `.sql` (criar) | DDL dual idempotente |
| `app/integracoes/tagplus/services/__init__.py` (criar) | novo pacote |
| `app/integracoes/tagplus/services/formatador_notificacao.py` (criar) | `formatar_pedido` / `formatar_nfe` → texto WhatsApp |
| `app/integracoes/tagplus/services/notificacao_whatsapp_service.py` (criar) | orquestração async + resolver vendedor + PDF + envio destinos |
| `app/integracoes/tagplus/webhook_notificacao_routes.py` (criar) | blueprint: webhook + tela histórico + reenviar |
| `app/__init__.py` (modificar) | registrar blueprint `tagplus_notificacao` |
| `app/templates/integracoes/tagplus_notificacoes.html` (criar) | tela histórico/reenvio |
| `app/templates/base.html` (modificar) | link de menu |
| `tests/integracoes/tagplus/...` (criar) | testes pytest |

> **Nota de desvio da spec:** a classe do model fica em `models.py` existente (não em `models_notificacao.py`), porque os models TagPlus já são importados pelo sistema — colocar a classe lá garante que o SQLAlchemy registre a tabela sem novo wiring de import.

---

## Task 0: Scaffolding (pacote services + pasta de testes)

**Files:**
- Create: `app/integracoes/tagplus/services/__init__.py`
- Create: `tests/integracoes/__init__.py`, `tests/integracoes/tagplus/__init__.py`

- [ ] **Step 1: Criar pacote services e pacotes de teste**

```bash
mkdir -p app/integracoes/tagplus/services tests/integracoes/tagplus
printf '"""Services da integração TagPlus."""\n' > app/integracoes/tagplus/services/__init__.py
: > tests/integracoes/__init__.py
: > tests/integracoes/tagplus/__init__.py
```

- [ ] **Step 2: Commit**

```bash
git add app/integracoes/tagplus/services/__init__.py tests/integracoes/__init__.py tests/integracoes/tagplus/__init__.py
git commit -m "chore(tagplus): scaffold pacote services + pasta de testes notificacao"
```

---

## Task 1: Estender `send_whatsapp` com anexo base64

**Files:**
- Modify: `app/utils/whatsapp_notify.py:135` (`send_whatsapp`)
- Test: `tests/integracoes/tagplus/test_send_whatsapp_anexo.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/integracoes/tagplus/test_send_whatsapp_anexo.py
"""Testa o anexo base64 no send_whatsapp (sem rede — mocka requests.post)."""
import json
from unittest.mock import patch, MagicMock

import app.utils.whatsapp_notify as wn


def _fake_resp(ok=True):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = {"ok": ok, "result": {}}
    return r


def test_send_whatsapp_sem_anexo_mantem_args_atuais(monkeypatch):
    monkeypatch.setattr(wn, "_GATEWAY_TOKEN", "tok")
    monkeypatch.setattr(wn, "_ENABLED", True)
    captured = {}

    def fake_post(url, data=None, headers=None, timeout=None):
        captured["body"] = json.loads(data.decode())
        return _fake_resp()

    with patch.object(wn.requests, "post", side_effect=fake_post):
        wn.send_whatsapp("120363@g.us", "Oi", skip_rate_limit=True)

    args = captured["body"]["args"]
    assert args["action"] == "send"
    assert args["channel"] == "whatsapp"
    assert args["target"] == "120363@g.us"
    assert args["message"] == "Oi"
    assert "buffer" not in args  # regressão: sem anexo, sem buffer


def test_send_whatsapp_com_anexo_monta_buffer(monkeypatch):
    monkeypatch.setattr(wn, "_GATEWAY_TOKEN", "tok")
    monkeypatch.setattr(wn, "_ENABLED", True)
    captured = {}

    def fake_post(url, data=None, headers=None, timeout=None):
        captured["body"] = json.loads(data.decode())
        return _fake_resp()

    with patch.object(wn.requests, "post", side_effect=fake_post):
        wn.send_whatsapp(
            "120363@g.us",
            "Segue a NF",
            skip_rate_limit=True,
            anexo_b64="JVBERi0xLjQK",
            anexo_filename="danfe_3706.pdf",
            anexo_mimetype="application/pdf",
        )

    args = captured["body"]["args"]
    assert args["buffer"] == "JVBERi0xLjQK"
    assert args["filename"] == "danfe_3706.pdf"
    assert args["mimeType"] == "application/pdf"
    assert args["caption"] == "Segue a NF"
    assert args["message"] == "Segue a NF"
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `pytest tests/integracoes/tagplus/test_send_whatsapp_anexo.py -v`
Expected: FAIL (`TypeError: send_whatsapp() got an unexpected keyword argument 'anexo_b64'`).

- [ ] **Step 3: Implementar a extensão**

Em `app/utils/whatsapp_notify.py`, alterar a assinatura e o payload de `send_whatsapp`. Substituir a assinatura atual e o bloco do `payload`:

```python
def send_whatsapp(
    target: str,
    text: str,
    *,
    skip_rate_limit: bool = False,
    timeout: float = _HTTP_TIMEOUT,
    anexo_b64: str | None = None,
    anexo_filename: str | None = None,
    anexo_mimetype: str = "application/pdf",
) -> dict:
    """Envia mensagem WhatsApp via gateway OpenClaw.

    Quando ``anexo_b64`` é fornecido, anexa o arquivo (base64) à mensagem via
    o tool ``message`` do gateway (campos ``buffer``/``filename``/``mimeType``/
    ``caption``). Sem ``anexo_b64`` o comportamento é idêntico ao envio só-texto.

    Args:
        target: Número E.164 (DM) ou JID de grupo (``...@g.us``).
        text: Texto da mensagem (vira ``caption`` quando há anexo).
        skip_rate_limit: True desabilita o rate limit local.
        timeout: Timeout HTTP em segundos.
        anexo_b64: Conteúdo do arquivo em base64 (sem o prefixo ``data:``).
        anexo_filename: Nome do arquivo exibido no WhatsApp (ex.: ``danfe_3706.pdf``).
        anexo_mimetype: MIME do anexo (default ``application/pdf``).
    """
```

(O corpo de validação/`_ENABLED`/`_GATEWAY_TOKEN`/rate-limit permanece igual.) Substituir o dict `payload` por:

```python
    msg_args = {
        "action": "send",
        "channel": "whatsapp",
        "target": target_norm,
        "message": text,
    }
    if anexo_b64:
        msg_args["buffer"] = anexo_b64
        msg_args["mimeType"] = anexo_mimetype
        msg_args["caption"] = text
        if anexo_filename:
            msg_args["filename"] = anexo_filename

    payload = {
        "name": "message",
        "args": msg_args,
    }
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `pytest tests/integracoes/tagplus/test_send_whatsapp_anexo.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add app/utils/whatsapp_notify.py tests/integracoes/tagplus/test_send_whatsapp_anexo.py
git commit -m "feat(whatsapp): send_whatsapp aceita anexo base64 (buffer/filename/mimeType/caption)"
```

---

## Task 2: Model `TagPlusNotificacaoWhatsapp` + migration dual

**Files:**
- Modify: `app/integracoes/tagplus/models.py` (adicionar classe no fim)
- Create: `scripts/migrations/2026_06_06_tagplus_notificacao_whatsapp.py`
- Create: `scripts/migrations/2026_06_06_tagplus_notificacao_whatsapp.sql`
- Test: `tests/integracoes/tagplus/test_model_notificacao.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/integracoes/tagplus/test_model_notificacao.py
"""Testa o model TagPlusNotificacaoWhatsapp (dedupe + defaults)."""
import pytest
from app import db
from app.integracoes.tagplus.models import TagPlusNotificacaoWhatsapp


def test_cria_registro_com_defaults(app):
    with app.app_context():
        reg = TagPlusNotificacaoWhatsapp(tipo="NFE", event_type="nfe_criada", tagplus_id="2659")
        db.session.add(reg)
        db.session.commit()
        assert reg.id is not None
        assert reg.status == "PENDENTE"
        assert reg.enviado_grupo is False
        assert reg.tentativas == 0
        db.session.delete(reg)
        db.session.commit()


def test_unique_tipo_id_event(app):
    with app.app_context():
        r1 = TagPlusNotificacaoWhatsapp(tipo="NFE", event_type="nfe_criada", tagplus_id="999")
        db.session.add(r1)
        db.session.commit()
        r2 = TagPlusNotificacaoWhatsapp(tipo="NFE", event_type="nfe_criada", tagplus_id="999")
        db.session.add(r2)
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()
        db.session.delete(r1)
        db.session.commit()
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `export DATABASE_URL=... && pytest tests/integracoes/tagplus/test_model_notificacao.py -v`
Expected: FAIL (`ImportError: cannot import name 'TagPlusNotificacaoWhatsapp'`).

- [ ] **Step 3: Implementar o model**

Adicionar ao fim de `app/integracoes/tagplus/models.py`:

```python
class TagPlusNotificacaoWhatsapp(db.Model):
    """Registro/dedupe/auditoria das notificações WhatsApp de pedido/NF do TagPlus.

    UNIQUE (tipo, tagplus_id, event_type) garante idempotência contra reenvio
    do webhook pelo TagPlus. Flags `enviado_grupo`/`enviado_vendedor` permitem
    reenvio só do destino pendente.
    """
    __tablename__ = 'tagplus_notificacao_whatsapp'

    id = db.Column(db.Integer, primary_key=True)

    tipo = db.Column(db.String(10), nullable=False)         # PEDIDO | NFE
    event_type = db.Column(db.String(30), nullable=False)   # pedido_criado | nfe_criada
    tagplus_id = db.Column(db.String(30), nullable=False)   # id do registro no TagPlus (string)

    numero = db.Column(db.String(30), nullable=True)
    cliente_nome = db.Column(db.String(255), nullable=True)
    valor = db.Column(db.Numeric(15, 2), nullable=True)

    vendedor_nome = db.Column(db.String(120), nullable=True)
    vendedor_user_id = db.Column(db.Integer, nullable=True)  # usuarios.id (sem FK, padrão do projeto)

    enviado_grupo = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    enviado_vendedor = db.Column(db.Boolean, nullable=True)  # NULL = não havia vendedor a notificar

    status = db.Column(db.String(15), nullable=False, default='PENDENTE')  # PENDENTE/PROCESSANDO/ENVIADO/PARCIAL/ERRO/IGNORADO
    erro = db.Column(db.Text, nullable=True)
    tentativas = db.Column(db.Integer, nullable=False, default=0)
    anexou_pdf = db.Column(db.Boolean, nullable=False, default=False, server_default='false')

    enviado_em = db.Column(db.DateTime, nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('tipo', 'tagplus_id', 'event_type', name='uq_tagplus_notif_tipo_id_event'),
        db.Index('idx_tagplus_notif_status', 'status'),
    )

    def __repr__(self):
        return f'<TagPlusNotificacaoWhatsapp {self.tipo} {self.tagplus_id} {self.status}>'
```

- [ ] **Step 4: Criar a migration SQL idempotente**

```sql
-- scripts/migrations/2026_06_06_tagplus_notificacao_whatsapp.sql
-- Idempotente — pode rodar 2x. Cria a tabela de notificações WhatsApp TagPlus.
CREATE TABLE IF NOT EXISTS tagplus_notificacao_whatsapp (
    id               SERIAL PRIMARY KEY,
    tipo             VARCHAR(10)  NOT NULL,
    event_type       VARCHAR(30)  NOT NULL,
    tagplus_id       VARCHAR(30)  NOT NULL,
    numero           VARCHAR(30),
    cliente_nome     VARCHAR(255),
    valor            NUMERIC(15,2),
    vendedor_nome    VARCHAR(120),
    vendedor_user_id INTEGER,
    enviado_grupo    BOOLEAN      NOT NULL DEFAULT FALSE,
    enviado_vendedor BOOLEAN,
    status           VARCHAR(15)  NOT NULL DEFAULT 'PENDENTE',
    erro             TEXT,
    tentativas       INTEGER      NOT NULL DEFAULT 0,
    anexou_pdf       BOOLEAN      NOT NULL DEFAULT FALSE,
    enviado_em       TIMESTAMP,
    criado_em        TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_tagplus_notif_tipo_id_event
    ON tagplus_notificacao_whatsapp (tipo, tagplus_id, event_type);

CREATE INDEX IF NOT EXISTS idx_tagplus_notif_status
    ON tagplus_notificacao_whatsapp (status);
```

- [ ] **Step 5: Criar a migration Python**

```python
# scripts/migrations/2026_06_06_tagplus_notificacao_whatsapp.py
"""Migration: cria tabela tagplus_notificacao_whatsapp (notificações WhatsApp TagPlus).

Idempotente — usa CREATE TABLE/INDEX IF NOT EXISTS.

Uso:
    python scripts/migrations/2026_06_06_tagplus_notificacao_whatsapp.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    """
    CREATE TABLE IF NOT EXISTS tagplus_notificacao_whatsapp (
        id               SERIAL PRIMARY KEY,
        tipo             VARCHAR(10)  NOT NULL,
        event_type       VARCHAR(30)  NOT NULL,
        tagplus_id       VARCHAR(30)  NOT NULL,
        numero           VARCHAR(30),
        cliente_nome     VARCHAR(255),
        valor            NUMERIC(15,2),
        vendedor_nome    VARCHAR(120),
        vendedor_user_id INTEGER,
        enviado_grupo    BOOLEAN      NOT NULL DEFAULT FALSE,
        enviado_vendedor BOOLEAN,
        status           VARCHAR(15)  NOT NULL DEFAULT 'PENDENTE',
        erro             TEXT,
        tentativas       INTEGER      NOT NULL DEFAULT 0,
        anexou_pdf       BOOLEAN      NOT NULL DEFAULT FALSE,
        enviado_em       TIMESTAMP,
        criado_em        TIMESTAMP    NOT NULL DEFAULT NOW()
    );
    """,
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_tagplus_notif_tipo_id_event "
    "ON tagplus_notificacao_whatsapp (tipo, tagplus_id, event_type);",
    "CREATE INDEX IF NOT EXISTS idx_tagplus_notif_status "
    "ON tagplus_notificacao_whatsapp (status);",
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        existe_antes = 'tagplus_notificacao_whatsapp' in inspector.get_table_names()
        print(f'Estado antes: tabela existe? {existe_antes}')
        for ddl in SQL_DDL:
            db.session.execute(text(ddl))
        db.session.commit()
        inspector = inspect(db.engine)
        existe_depois = 'tagplus_notificacao_whatsapp' in inspector.get_table_names()
        cols = {c['name'] for c in inspector.get_columns('tagplus_notificacao_whatsapp')}
        print(f'Estado depois: tabela existe? {existe_depois}')
        print(f'Colunas: {sorted(cols)}')


if __name__ == '__main__':
    main()
```

- [ ] **Step 6: Rodar a migration local + os testes**

```bash
export DATABASE_URL=...   # ver "Setup de testes"
python scripts/migrations/2026_06_06_tagplus_notificacao_whatsapp.py
pytest tests/integracoes/tagplus/test_model_notificacao.py -v
```
Expected: migration imprime `tabela existe? True`; testes PASS (2 passed). Rodar a migration 2x não deve falhar (idempotente).

- [ ] **Step 7: Commit**

```bash
git add app/integracoes/tagplus/models.py scripts/migrations/2026_06_06_tagplus_notificacao_whatsapp.py scripts/migrations/2026_06_06_tagplus_notificacao_whatsapp.sql tests/integracoes/tagplus/test_model_notificacao.py
git commit -m "feat(tagplus): model + migration dual tagplus_notificacao_whatsapp"
```

---

## Task 3: Formatador de mensagens

**Files:**
- Create: `app/integracoes/tagplus/services/formatador_notificacao.py`
- Test: `tests/integracoes/tagplus/test_formatador_notificacao.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/integracoes/tagplus/test_formatador_notificacao.py
"""Testa a formatação WhatsApp de pedido/NF (sem DB, sem rede)."""
from app.integracoes.tagplus.services import formatador_notificacao as fmt

NFE = {
    "numero": 3706, "serie": 1, "valor_nota": 28594.78,
    "data_emissao": "2024-08-15T10:30:00Z",
    "destinatario": {"razao_social": "CESTA BASICA BRASIL COMERCIO"},
    "itens": [
        {"qtd": 44, "valor_unitario": 69.58,
         "produto": {"codigo": "4320147", "descricao": "AZEITONA VERDE FATIADA"}},
    ],
}
PEDIDO = {
    "numero": 555, "valor_total": 1200.50,
    "cliente": {"razao_social": "MERCADO X"},
    "vendedor": {"nome": "João Silva"},
    "data_entrega": "2024-08-20",
    "itens": [
        {"qtd": 2, "valor_unitario": 600.25,
         "produto_servico": {"codigo": "P1", "descricao": "PALMITO"}},
    ],
}


def test_formatar_nfe_contem_campos_principais():
    texto = fmt.formatar_nfe(NFE, vendedor_nome="João Silva")
    assert "3706" in texto
    assert "CESTA BASICA BRASIL" in texto
    assert "João Silva" in texto
    assert "28.594,78" in texto          # R$ BR
    assert "4320147" in texto
    assert "|" not in texto              # R8: sem tabela markdown


def test_formatar_nfe_omite_vendedor_quando_ausente():
    texto = fmt.formatar_nfe(NFE, vendedor_nome=None)
    assert "Vendedor" not in texto


def test_formatar_pedido_contem_vendedor():
    texto = fmt.formatar_pedido(PEDIDO)
    assert "555" in texto
    assert "MERCADO X" in texto
    assert "João Silva" in texto
    assert "1.200,50" in texto


def test_trunca_itens_acima_do_limite():
    nfe = dict(NFE)
    nfe["itens"] = [
        {"qtd": 1, "valor_unitario": 1.0, "produto": {"codigo": str(i), "descricao": f"P{i}"}}
        for i in range(40)
    ]
    texto = fmt.formatar_nfe(nfe, vendedor_nome=None)
    assert "(+10 itens)" in texto      # 40 itens, limite 30
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `pytest tests/integracoes/tagplus/test_formatador_notificacao.py -v`
Expected: FAIL (`ModuleNotFoundError` / `AttributeError`).

- [ ] **Step 3: Implementar o formatador**

```python
# app/integracoes/tagplus/services/formatador_notificacao.py
"""Formata pedido/NF do TagPlus em texto WhatsApp-friendly (regra R8).

Sem tabela markdown, sem headers (##), sem code block. Usa *bold*, emojis e
listas. Valores em R$ no padrão brasileiro.
"""
from __future__ import annotations

from typing import Optional

MAX_ITENS = 30


def _valor_br(v) -> str:
    try:
        n = float(v or 0)
    except (TypeError, ValueError):
        n = 0.0
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _data_br(s) -> str:
    if not s or not isinstance(s, str):
        return ""
    d = s[:10]  # 'YYYY-MM-DD...'
    partes = d.split("-")
    if len(partes) == 3:
        return f"{partes[2]}/{partes[1]}/{partes[0]}"
    return d


def _linhas_itens(itens: list, chave_produto: str) -> list[str]:
    linhas = []
    total = len(itens or [])
    for item in (itens or [])[:MAX_ITENS]:
        prod = item.get(chave_produto) or {}
        cod = prod.get("codigo", "") or item.get("item", "")
        desc = prod.get("descricao", "") or ""
        qtd = item.get("qtd", 0) or 0
        vu = _valor_br(item.get("valor_unitario", 0))
        linhas.append(f"- {cod} {desc} — {qtd} x R$ {vu}")
    if total > MAX_ITENS:
        linhas.append(f"… (+{total - MAX_ITENS} itens)")
    return linhas


def formatar_nfe(nfe: dict, vendedor_nome: Optional[str] = None) -> str:
    numero = nfe.get("numero", "?")
    serie = nfe.get("serie", "?")
    dest = nfe.get("destinatario") or {}
    cliente = dest.get("razao_social", "") or ""
    valor = _valor_br(nfe.get("valor_nota", 0))
    data = _data_br(nfe.get("data_emissao"))

    linhas = [f"🧾 *Nova NF emitida — Nº {numero}/{serie}*"]
    if cliente:
        linhas.append(f"👤 Cliente: {cliente}")
    if vendedor_nome:
        linhas.append(f"🧑‍💼 Vendedor: {vendedor_nome}")
    linhas.append(f"💰 Valor: R$ {valor}")
    if data:
        linhas.append(f"📅 {data}")
    itens = _linhas_itens(nfe.get("itens"), "produto")
    if itens:
        linhas.append("")
        linhas.append("Itens:")
        linhas.extend(itens)
    return "\n".join(linhas)


def formatar_pedido(pedido: dict) -> str:
    numero = pedido.get("numero", "?")
    cliente = (pedido.get("cliente") or {}).get("razao_social", "") or ""
    vendedor = (pedido.get("vendedor") or {}).get("nome", "") or ""
    valor = _valor_br(pedido.get("valor_total", 0))
    entrega = _data_br(pedido.get("data_entrega"))
    obs = (pedido.get("observacoes") or "").strip()

    linhas = [f"🛒 *Novo pedido — Nº {numero}*"]
    if cliente:
        linhas.append(f"👤 Cliente: {cliente}")
    if vendedor:
        linhas.append(f"🧑‍💼 Vendedor: {vendedor}")
    linhas.append(f"💰 Valor: R$ {valor}")
    if entrega:
        linhas.append(f"🚚 Entrega: {entrega}")
    if obs:
        linhas.append(f"📝 {obs[:200]}")
    itens = _linhas_itens(pedido.get("itens"), "produto_servico")
    if itens:
        linhas.append("")
        linhas.append("Itens:")
        linhas.extend(itens)
    return "\n".join(linhas)
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `pytest tests/integracoes/tagplus/test_formatador_notificacao.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add app/integracoes/tagplus/services/formatador_notificacao.py tests/integracoes/tagplus/test_formatador_notificacao.py
git commit -m "feat(tagplus): formatador de mensagem WhatsApp (pedido/NF)"
```

---

## Task 4: Resolver vendedor (cadastro `usuarios`)

**Files:**
- Create: `app/integracoes/tagplus/services/notificacao_whatsapp_service.py` (parcial — só `_resolver_vendedor`)
- Test: `tests/integracoes/tagplus/test_resolver_vendedor.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/integracoes/tagplus/test_resolver_vendedor.py
"""Testa a resolução do vendedor -> Usuario (whatsapp autorizado + ativo)."""
import pytest
from app import db
from app.auth.models import Usuario
from app.integracoes.tagplus.services import notificacao_whatsapp_service as svc


@pytest.fixture
def _cria_vendedor(app):
    with app.app_context():
        u = Usuario(
            nome="João Silva", email="joao.tagplus.test@x.com",
            perfil="vendedor", status="ativo",
            telefone="11999990000", whatsapp_autorizado=True,
            vendedor_vinculado="João Silva",
        )
        u.set_senha("x")  # se o model exigir; senão remover
        db.session.add(u)
        db.session.commit()
        yield u.id
        db.session.delete(db.session.get(Usuario, u.id))
        db.session.commit()


def test_resolve_por_vendedor_vinculado(app, _cria_vendedor):
    with app.app_context():
        u = svc._resolver_vendedor("joão silva")
        assert u is not None
        assert u.telefone == "11999990000"


def test_nao_resolve_sem_whatsapp_autorizado(app):
    with app.app_context():
        u = Usuario(nome="Maria Sem Zap", email="maria.tagplus.test@x.com",
                    perfil="vendedor", status="ativo", telefone="11888880000",
                    whatsapp_autorizado=False, vendedor_vinculado="Maria Sem Zap")
        u.set_senha("x")
        db.session.add(u); db.session.commit()
        try:
            assert svc._resolver_vendedor("Maria Sem Zap") is None
        finally:
            db.session.delete(db.session.get(Usuario, u.id)); db.session.commit()


def test_nao_resolve_nome_inexistente(app):
    with app.app_context():
        assert svc._resolver_vendedor("Fulano Inexistente ZZZ") is None
```

> Nota: confirmar o nome do método de senha do `Usuario` (`set_senha`/`set_password`). Se não houver, criar sem senha (campo `senha_hash` nullable?) — ajustar o fixture conforme o model real.

- [ ] **Step 2: Rodar e verificar que falha**

Run: `export DATABASE_URL=... && pytest tests/integracoes/tagplus/test_resolver_vendedor.py -v`
Expected: FAIL (`AttributeError: module ... has no attribute '_resolver_vendedor'`).

- [ ] **Step 3: Criar o service com `_resolver_vendedor`**

```python
# app/integracoes/tagplus/services/notificacao_whatsapp_service.py
"""Serviço de notificação WhatsApp para pedido/NF do TagPlus.

Processamento assíncrono em Thread(daemon=False), espelhando o padrão do
WhatsApp bot (app/whatsapp/services.py: R1 thread non-daemon, R2 commit retry,
R3 re-fetch, R5 cleanup no finally). Best-effort: falhas degradam e ficam no
registro tagplus_notificacao_whatsapp.
"""
from __future__ import annotations

import base64
import logging
import time
from typing import Optional

from sqlalchemy import func, or_

logger = logging.getLogger(__name__)

DELAYS_BUSCA = [1, 3, 5]


def _resolver_vendedor(nome: Optional[str]):
    """Resolve o nome do vendedor (TagPlus) -> Usuario autorizado no WhatsApp.

    Match case-insensitive por `vendedor_vinculado` OU `nome`, exigindo
    `whatsapp_autorizado=True`, `status='ativo'` e `telefone` preenchido.
    Retorna o Usuario ou None (fallback só-grupo).
    """
    if not nome or not nome.strip():
        return None
    from app.auth.models import Usuario

    alvo = nome.strip().lower()
    return (
        Usuario.query
        .filter(Usuario.whatsapp_autorizado.is_(True))
        .filter(Usuario.status == 'ativo')
        .filter(Usuario.telefone.isnot(None))
        .filter(or_(
            func.lower(Usuario.vendedor_vinculado) == alvo,
            func.lower(Usuario.nome) == alvo,
        ))
        .first()
    )
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `pytest tests/integracoes/tagplus/test_resolver_vendedor.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add app/integracoes/tagplus/services/notificacao_whatsapp_service.py tests/integracoes/tagplus/test_resolver_vendedor.py
git commit -m "feat(tagplus): resolver vendedor -> Usuario autorizado (DM)"
```

---

## Task 5: Service — busca, PDF e envio aos destinos

**Files:**
- Modify: `app/integracoes/tagplus/services/notificacao_whatsapp_service.py`
- Test: `tests/integracoes/tagplus/test_processar_notificacao.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/integracoes/tagplus/test_processar_notificacao.py
"""Testa o processamento de uma notificação NF (com PDF) e os status de destino."""
from unittest.mock import MagicMock, patch

from app import db
from app.integracoes.tagplus.models import TagPlusNotificacaoWhatsapp
from app.integracoes.tagplus.services import notificacao_whatsapp_service as svc

NFE = {
    "numero": 3706, "serie": 1, "valor_nota": 100.0,
    "data_emissao": "2024-08-15", "destinatario": {"razao_social": "CLIENTE Y"},
    "itens": [], "pedido_os_vinculada": {"id": 77},
}
PEDIDO = {"numero": 9, "vendedor": {"nome": "João Silva"}}


def _registro(app, tipo="NFE", event="nfe_criada", tid="3706"):
    reg = TagPlusNotificacaoWhatsapp(tipo=tipo, event_type=event, tagplus_id=tid)
    db.session.add(reg); db.session.commit()
    return reg.id


def test_nf_envia_grupo_e_vendedor_com_pdf(app, monkeypatch):
    with app.app_context():
        rid = _registro(app)
        monkeypatch.setenv("TAGPLUS_NOTIFY_WHATSAPP_GROUP_JID", "120363@g.us")
        enviados = []

        def fake_send(target, text, **kw):
            enviados.append((target, kw.get("anexo_b64") is not None))
            return {"ok": True}

        vendedor = MagicMock(); vendedor.telefone = "11999990000"; vendedor.id = 5
        vendedor.nome = "João Silva"

        with patch.object(svc, "_get_api"), \
             patch.object(svc, "_buscar_nfe_com_retry", return_value=NFE), \
             patch.object(svc, "_buscar_pedido", return_value=PEDIDO), \
             patch.object(svc, "_baixar_danfe_pdf", return_value=b"%PDF-1.4"), \
             patch.object(svc, "_resolver_vendedor", return_value=vendedor), \
             patch("app.integracoes.tagplus.services.notificacao_whatsapp_service.send_whatsapp", side_effect=fake_send):
            svc.processar_notificacao_async(app, rid)

        reg = db.session.get(TagPlusNotificacaoWhatsapp, rid)
        assert reg.status == "ENVIADO"
        assert reg.enviado_grupo is True
        assert reg.enviado_vendedor is True
        assert reg.anexou_pdf is True
        assert len(enviados) == 2          # grupo + vendedor
        assert all(tem_pdf for _, tem_pdf in enviados)
        db.session.delete(reg); db.session.commit()


def test_nf_sem_vendedor_so_grupo(app, monkeypatch):
    with app.app_context():
        rid = _registro(app, tid="3707")
        monkeypatch.setenv("TAGPLUS_NOTIFY_WHATSAPP_GROUP_JID", "120363@g.us")

        with patch.object(svc, "_get_api"), \
             patch.object(svc, "_buscar_nfe_com_retry", return_value=NFE), \
             patch.object(svc, "_buscar_pedido", return_value=None), \
             patch.object(svc, "_baixar_danfe_pdf", return_value=None), \
             patch.object(svc, "_resolver_vendedor", return_value=None), \
             patch("app.integracoes.tagplus.services.notificacao_whatsapp_service.send_whatsapp", return_value={"ok": True}):
            svc.processar_notificacao_async(app, rid)

        reg = db.session.get(TagPlusNotificacaoWhatsapp, rid)
        assert reg.status == "ENVIADO"
        assert reg.enviado_grupo is True
        assert reg.enviado_vendedor is None   # não havia vendedor
        db.session.delete(reg); db.session.commit()
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `export DATABASE_URL=... && pytest tests/integracoes/tagplus/test_processar_notificacao.py -v`
Expected: FAIL (`AttributeError`: funções ainda não existem).

- [ ] **Step 3: Completar o service**

Adicionar ao `app/integracoes/tagplus/services/notificacao_whatsapp_service.py` (após `_resolver_vendedor`):

```python
import os

from app.utils.whatsapp_notify import send_whatsapp, WhatsAppNotifyError
from app.utils.timezone import agora_utc_naive


def _commit_with_retry() -> bool:
    """Commit com retry para SSL drop do Render PostgreSQL (espelha WhatsApp bot)."""
    from app import db
    try:
        db.session.commit()
        return True
    except Exception as exc:
        s = str(exc).lower()
        if 'ssl' in s or 'connection' in s or 'closed' in s:
            logger.warning(f"[TAGPLUS-NOTIF] Conexao perdida no commit: {exc}")
            db.session.rollback(); db.session.close()
            return False
        raise


def _get_api():
    """Cliente OAuth da integração principal (conta 'notas')."""
    from app.integracoes.tagplus.oauth2_v2 import TagPlusOAuth2V2
    return TagPlusOAuth2V2(api_type='notas')


def _buscar_nfe_com_retry(api, tagplus_id: str) -> Optional[dict]:
    for i, delay in enumerate(DELAYS_BUSCA):
        try:
            r = api.make_request('GET', f'/nfes/{tagplus_id}')
            if r is not None and r.status_code == 200:
                return r.json() or None
        except Exception as exc:
            logger.warning(f"[TAGPLUS-NOTIF] GET /nfes/{tagplus_id} erro: {exc}")
        if i < len(DELAYS_BUSCA) - 1:
            time.sleep(delay)
    return None


def _buscar_pedido(api, pedido_id) -> Optional[dict]:
    """GET /pedidos/{id}. 401 = scope read:pedidos ausente -> propaga sinal."""
    try:
        r = api.make_request('GET', f'/pedidos/{pedido_id}')
    except Exception as exc:
        logger.warning(f"[TAGPLUS-NOTIF] GET /pedidos/{pedido_id} erro: {exc}")
        return None
    if r is None:
        return None
    if r.status_code == 401:
        raise PermissionError('scope read:pedidos ausente (GET /pedidos 401)')
    if r.status_code != 200:
        return None
    return r.json() or None


def _buscar_pedido_com_retry(api, pedido_id) -> Optional[dict]:
    for i, delay in enumerate(DELAYS_BUSCA):
        ped = _buscar_pedido(api, pedido_id)
        if ped:
            return ped
        if i < len(DELAYS_BUSCA) - 1:
            time.sleep(delay)
    return None


def _baixar_danfe_pdf(api, tagplus_id: str) -> Optional[bytes]:
    try:
        r = api.make_request('GET', f'/nfes/pdf/recibo_a4/{tagplus_id}')
    except Exception as exc:
        logger.warning(f"[TAGPLUS-NOTIF] PDF DANFE {tagplus_id} erro: {exc}")
        return None
    if r is None or r.status_code != 200:
        return None
    ctype = (r.headers.get('Content-Type') or '').lower()
    if 'pdf' not in ctype and not (r.content[:4] == b'%PDF'):
        logger.warning(f"[TAGPLUS-NOTIF] DANFE {tagplus_id} não é PDF (ctype={ctype})")
        return None
    return r.content


def _enviar_para_destinos(reg, texto, anexo_b64, anexo_filename, vendedor):
    """Envia ao grupo e (se houver) à DM do vendedor. Atualiza flags/status."""
    grupo_jid = os.environ.get('TAGPLUS_NOTIFY_WHATSAPP_GROUP_JID', '').strip()
    if not grupo_jid:
        reg.status = 'ERRO'
        reg.erro = 'TAGPLUS_NOTIFY_WHATSAPP_GROUP_JID não configurado'
        return

    # Grupo
    grupo_ok = False
    try:
        send_whatsapp(grupo_jid, texto, skip_rate_limit=True,
                      anexo_b64=anexo_b64, anexo_filename=anexo_filename)
        grupo_ok = True
    except WhatsAppNotifyError as exc:
        reg.erro = f'Grupo: {exc}'
    reg.enviado_grupo = grupo_ok

    # Vendedor (DM)
    if vendedor is not None and getattr(vendedor, 'telefone', None):
        reg.vendedor_user_id = getattr(vendedor, 'id', None)
        try:
            send_whatsapp(vendedor.telefone, texto, skip_rate_limit=True,
                          anexo_b64=anexo_b64, anexo_filename=anexo_filename)
            reg.enviado_vendedor = True
        except WhatsAppNotifyError as exc:
            reg.enviado_vendedor = False
            reg.erro = ((reg.erro or '') + f' | Vendedor: {exc}').strip(' |')
    else:
        reg.enviado_vendedor = None  # não havia vendedor a notificar

    # Status final
    if not grupo_ok:
        reg.status = 'ERRO'
    elif reg.enviado_vendedor is False:
        reg.status = 'PARCIAL'
    else:
        reg.status = 'ENVIADO'
    reg.enviado_em = agora_utc_naive()


def processar_notificacao_async(app, registro_id: int) -> None:
    """Thread entrypoint: busca dados, formata, resolve vendedor, envia destinos."""
    from app import db
    from app.integracoes.tagplus.models import TagPlusNotificacaoWhatsapp
    from app.integracoes.tagplus.services import formatador_notificacao as fmt

    with app.app_context():
        reg = None
        try:
            reg = db.session.get(TagPlusNotificacaoWhatsapp, registro_id)
            if not reg:
                logger.error(f"[TAGPLUS-NOTIF] Registro {registro_id} não encontrado")
                return
            reg.status = 'PROCESSANDO'
            reg.tentativas = (reg.tentativas or 0) + 1
            _commit_with_retry()

            api = _get_api()
            vendedor_nome = None
            anexo_b64 = None
            anexo_filename = None

            if reg.tipo == 'NFE':
                nfe = _buscar_nfe_com_retry(api, reg.tagplus_id)
                if not nfe:
                    reg.status = 'ERRO'; reg.erro = 'NFe não encontrada na API após retries'
                    _commit_with_retry(); return
                reg.numero = str(nfe.get('numero') or '')
                reg.cliente_nome = (nfe.get('destinatario') or {}).get('razao_social')
                reg.valor = nfe.get('valor_nota')
                # vendedor via pedido vinculado (read:pedidos)
                pedido_vinc = (nfe.get('pedido_os_vinculada') or {}).get('id')
                if pedido_vinc:
                    try:
                        ped = _buscar_pedido(api, pedido_vinc)
                        if ped:
                            vendedor_nome = (ped.get('vendedor') or {}).get('nome')
                    except PermissionError:
                        reg.erro = 'Sem scope read:pedidos: vendedor da NF não resolvido'
                reg.vendedor_nome = vendedor_nome
                texto = fmt.formatar_nfe(nfe, vendedor_nome=vendedor_nome)
                pdf = _baixar_danfe_pdf(api, reg.tagplus_id)
                if pdf:
                    anexo_b64 = base64.b64encode(pdf).decode()
                    anexo_filename = f"danfe_{reg.numero or reg.tagplus_id}.pdf"
                    reg.anexou_pdf = True
                else:
                    reg.erro = ((reg.erro or '') + ' | PDF indisponível, enviado só texto').strip(' |')

            elif reg.tipo == 'PEDIDO':
                try:
                    ped = _buscar_pedido_com_retry(api, reg.tagplus_id)
                except PermissionError:
                    reg.status = 'ERRO'
                    reg.erro = 'Sem scope read:pedidos — reautorizar OAuth (read:pedidos)'
                    _commit_with_retry(); return
                if not ped:
                    reg.status = 'ERRO'; reg.erro = 'Pedido não encontrado na API após retries'
                    _commit_with_retry(); return
                reg.numero = str(ped.get('numero') or '')
                reg.cliente_nome = (ped.get('cliente') or {}).get('razao_social')
                reg.valor = ped.get('valor_total')
                vendedor_nome = (ped.get('vendedor') or {}).get('nome')
                reg.vendedor_nome = vendedor_nome
                texto = fmt.formatar_pedido(ped)
            else:
                reg.status = 'IGNORADO'; reg.erro = f'tipo desconhecido: {reg.tipo}'
                _commit_with_retry(); return

            vendedor = _resolver_vendedor(vendedor_nome)
            _enviar_para_destinos(reg, texto, anexo_b64, anexo_filename, vendedor)

            # re-fetch defensivo (R3) antes do commit final
            reg = db.session.get(TagPlusNotificacaoWhatsapp, registro_id) or reg
            _commit_with_retry()
            logger.info(f"[TAGPLUS-NOTIF] {reg.tipo} {reg.tagplus_id} -> {reg.status}")

        except Exception as exc:
            logger.error(f"[TAGPLUS-NOTIF] Erro registro {registro_id}: {exc}", exc_info=True)
            try:
                r = db.session.get(TagPlusNotificacaoWhatsapp, registro_id)
                if r:
                    r.status = 'ERRO'; r.erro = f'Erro interno: {str(exc)[:300]}'
                    db.session.commit()
            except Exception:
                pass
        finally:
            try:
                db.session.remove()
            except Exception:
                pass


def disparar_thread(app, registro_id: int) -> None:
    """Dispara o processamento em Thread(daemon=False) (R1 do WhatsApp bot)."""
    import threading
    t = threading.Thread(
        target=processar_notificacao_async, args=(app, registro_id), daemon=False,
        name=f"tagplus-notif-{registro_id}",
    )
    t.start()
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `export DATABASE_URL=... && pytest tests/integracoes/tagplus/test_processar_notificacao.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add app/integracoes/tagplus/services/notificacao_whatsapp_service.py tests/integracoes/tagplus/test_processar_notificacao.py
git commit -m "feat(tagplus): service de notificacao (busca, PDF, envio grupo+vendedor)"
```

---

## Task 6: Webhook route + registro do blueprint

**Files:**
- Create: `app/integracoes/tagplus/webhook_notificacao_routes.py`
- Modify: `app/__init__.py:1300-1305`
- Test: `tests/integracoes/tagplus/test_webhook_notificacao.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/integracoes/tagplus/test_webhook_notificacao.py
"""Testa o endpoint de webhook de notificação (dedupe, parsing, assinatura)."""
import json
from unittest.mock import patch

from app import db
from app.integracoes.tagplus.models import TagPlusNotificacaoWhatsapp
from app.integracoes.tagplus.webhook_routes import WEBHOOK_SECRET

URL = "/integracoes/tagplus/webhook/notificacao"


def _payload(event="nfe_criada", tid="3706"):
    return {"event_type": event, "data": [{"id": tid}]}


def test_assinatura_invalida_401(client):
    r = client.post(URL, json=_payload(), headers={"X-Hub-Secret": "errado"})
    assert r.status_code == 401


def test_cria_registro_e_dispara_thread(client, app):
    with patch("app.integracoes.tagplus.webhook_notificacao_routes.disparar_thread") as disp:
        r = client.post(URL, json=_payload(tid="55555"),
                        headers={"X-Hub-Secret": WEBHOOK_SECRET})
    assert r.status_code == 200
    assert disp.called
    with app.app_context():
        reg = TagPlusNotificacaoWhatsapp.query.filter_by(tipo="NFE", tagplus_id="55555").first()
        assert reg is not None
        db.session.delete(reg); db.session.commit()


def test_dedupe_nao_duplica(client, app):
    with patch("app.integracoes.tagplus.webhook_notificacao_routes.disparar_thread"):
        client.post(URL, json=_payload(tid="66666"), headers={"X-Hub-Secret": WEBHOOK_SECRET})
        client.post(URL, json=_payload(tid="66666"), headers={"X-Hub-Secret": WEBHOOK_SECRET})
    with app.app_context():
        regs = TagPlusNotificacaoWhatsapp.query.filter_by(tipo="NFE", tagplus_id="66666").all()
        assert len(regs) == 1
        for r in regs:
            db.session.delete(r)
        db.session.commit()


def test_evento_fora_do_escopo_ignorado(client):
    with patch("app.integracoes.tagplus.webhook_notificacao_routes.disparar_thread") as disp:
        r = client.post(URL, json=_payload(event="produto_criado", tid="1"),
                        headers={"X-Hub-Secret": WEBHOOK_SECRET})
    assert r.status_code == 200
    assert not disp.called
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `export DATABASE_URL=... && pytest tests/integracoes/tagplus/test_webhook_notificacao.py -v`
Expected: FAIL (404 na rota / ImportError).

- [ ] **Step 3: Implementar o blueprint do webhook**

```python
# app/integracoes/tagplus/webhook_notificacao_routes.py
"""Webhook dedicado de NOTIFICAÇÃO WhatsApp (pedido_criado / nfe_criada).

Separado do /webhook/tagplus/nfe (faturamento) — falha aqui não afeta a
importação e vice-versa. Valida X-Hub-Secret (reusa validar_assinatura),
registra em tagplus_notificacao_whatsapp (dedupe) e dispara thread async.
"""
import logging

from flask import Blueprint, request, jsonify
from flask_login import login_required

from app import db, csrf
from app.integracoes.tagplus.models import TagPlusNotificacaoWhatsapp
from app.integracoes.tagplus.webhook_routes import validar_assinatura
from app.integracoes.tagplus.services.notificacao_whatsapp_service import disparar_thread

logger = logging.getLogger(__name__)

tagplus_notificacao = Blueprint('tagplus_notificacao', __name__)

EVENTO_TIPO = {
    'pedido_criado': 'PEDIDO',
    'nfe_criada': 'NFE',
}


@csrf.exempt
@tagplus_notificacao.route('/integracoes/tagplus/webhook/notificacao', methods=['POST'])
def webhook_notificacao():
    ok, motivo = validar_assinatura(request)
    if not ok:
        logger.warning(f"[TAGPLUS-NOTIF] Webhook rejeitado: {motivo}")
        return jsonify({'erro': motivo}), 401

    dados = request.get_json(silent=True) or {}
    event_type = (dados.get('event_type') or '').strip()
    data_arr = dados.get('data') or []
    tagplus_id = str(data_arr[0].get('id')) if data_arr and isinstance(data_arr[0], dict) and data_arr[0].get('id') is not None else None

    tipo = EVENTO_TIPO.get(event_type)
    if not tipo:
        logger.info(f"[TAGPLUS-NOTIF] Evento fora do escopo: '{event_type}' (ignorado)")
        return jsonify({'status': 'ignorado', 'event_type': event_type}), 200

    if not tagplus_id:
        logger.error(f"[TAGPLUS-NOTIF] Webhook sem id em data[]: {dados}")
        return jsonify({'erro': 'id ausente em data[]'}), 400

    # Dedupe
    existente = TagPlusNotificacaoWhatsapp.query.filter_by(
        tipo=tipo, tagplus_id=tagplus_id, event_type=event_type
    ).first()
    if existente:
        logger.info(f"[TAGPLUS-NOTIF] Duplicado {tipo} {tagplus_id} (status={existente.status}) — skip")
        return jsonify({'status': 'duplicado', 'id': existente.id}), 200

    reg = TagPlusNotificacaoWhatsapp(tipo=tipo, event_type=event_type, tagplus_id=tagplus_id)
    db.session.add(reg)
    db.session.commit()

    from flask import current_app
    disparar_thread(current_app._get_current_object(), reg.id)
    return jsonify({'status': 'ok', 'id': reg.id}), 200


@tagplus_notificacao.route('/integracoes/tagplus/notificacoes', methods=['GET'])
@login_required
def notificacoes_lista():
    from flask import render_template
    page = request.args.get('page', 1, type=int)
    pag = (TagPlusNotificacaoWhatsapp.query
           .order_by(TagPlusNotificacaoWhatsapp.criado_em.desc())
           .paginate(page=page, per_page=50, error_out=False))
    return render_template('integracoes/tagplus_notificacoes.html', pag=pag)


@tagplus_notificacao.route('/integracoes/tagplus/notificacoes/<int:reg_id>/reenviar', methods=['POST'])
@login_required
def notificacao_reenviar(reg_id):
    from flask import current_app, redirect, url_for, flash
    reg = TagPlusNotificacaoWhatsapp.query.get_or_404(reg_id)
    reg.status = 'PENDENTE'
    db.session.commit()
    disparar_thread(current_app._get_current_object(), reg.id)
    flash(f'Reenvio disparado para {reg.tipo} {reg.tagplus_id}.', 'info')
    return redirect(url_for('tagplus_notificacao.notificacoes_lista'))
```

- [ ] **Step 4: Registrar o blueprint**

Em `app/__init__.py`, logo após `app.register_blueprint(tagplus_webhook)` (~linha 1304), adicionar:

```python
    from app.integracoes.tagplus.webhook_notificacao_routes import tagplus_notificacao
    app.register_blueprint(tagplus_notificacao)  # webhook dedicado de notificação WhatsApp
```

- [ ] **Step 5: Rodar e verificar que passa**

Run: `export DATABASE_URL=... && pytest tests/integracoes/tagplus/test_webhook_notificacao.py -v`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add app/integracoes/tagplus/webhook_notificacao_routes.py app/__init__.py tests/integracoes/tagplus/test_webhook_notificacao.py
git commit -m "feat(tagplus): webhook dedicado de notificacao WhatsApp + blueprint"
```

---

## Task 7: Tela de histórico + reenvio + menu

**Files:**
- Create: `app/templates/integracoes/tagplus_notificacoes.html`
- Modify: `app/templates/base.html` (link de menu)
- Test: `tests/integracoes/tagplus/test_tela_notificacoes.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/integracoes/tagplus/test_tela_notificacoes.py
"""Smoke da tela de histórico (requer login)."""
def test_lista_exige_login(client):
    r = client.get("/integracoes/tagplus/notificacoes")
    assert r.status_code in (302, 401)  # redireciona pro login
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `export DATABASE_URL=... && pytest tests/integracoes/tagplus/test_tela_notificacoes.py -v`
Expected: pode FALHAR com 404 (template ausente quebra antes do login_required em alguns setups) — confirmar o motivo do fail antes de implementar.

- [ ] **Step 3: Criar o template**

```html
{# app/templates/integracoes/tagplus_notificacoes.html #}
{% extends "base.html" %}
{% block title %}Notificações TagPlus → WhatsApp{% endblock %}
{% block content %}
<div class="container-fluid py-3">
  <h1 class="h4 mb-3">Notificações TagPlus → WhatsApp</h1>
  <div class="table-responsive">
    <table class="table table-sm table-hover align-middle">
      <thead>
        <tr>
          <th>Quando</th><th>Tipo</th><th>Número</th><th>Cliente</th>
          <th>Vendedor</th><th>Grupo</th><th>Vendedor (DM)</th>
          <th>PDF</th><th>Status</th><th>Erro</th><th></th>
        </tr>
      </thead>
      <tbody>
        {% for n in pag.items %}
        <tr>
          <td>{{ n.criado_em.strftime('%d/%m %H:%M') if n.criado_em else '' }}</td>
          <td>{{ n.tipo }}</td>
          <td>{{ n.numero or n.tagplus_id }}</td>
          <td>{{ n.cliente_nome or '' }}</td>
          <td>{{ n.vendedor_nome or '—' }}</td>
          <td>{% if n.enviado_grupo %}<span class="badge bg-success">OK</span>{% else %}<span class="badge bg-secondary">—</span>{% endif %}</td>
          <td>
            {% if n.enviado_vendedor is none %}<span class="badge bg-secondary">n/a</span>
            {% elif n.enviado_vendedor %}<span class="badge bg-success">OK</span>
            {% else %}<span class="badge bg-warning text-dark">falhou</span>{% endif %}
          </td>
          <td>{% if n.anexou_pdf %}📎{% endif %}</td>
          <td>
            {% if n.status == 'ENVIADO' %}<span class="badge bg-success">{{ n.status }}</span>
            {% elif n.status == 'PARCIAL' %}<span class="badge bg-warning text-dark">{{ n.status }}</span>
            {% elif n.status == 'ERRO' %}<span class="badge bg-danger">{{ n.status }}</span>
            {% else %}<span class="badge bg-secondary">{{ n.status }}</span>{% endif %}
          </td>
          <td class="small text-muted">{{ (n.erro or '')[:80] }}</td>
          <td>
            {% if n.status in ['ERRO', 'PARCIAL'] %}
            <form method="post" action="{{ url_for('tagplus_notificacao.notificacao_reenviar', reg_id=n.id) }}" class="d-inline">
              <button class="btn btn-sm btn-outline-primary" type="submit">Reenviar</button>
            </form>
            {% endif %}
          </td>
        </tr>
        {% else %}
        <tr><td colspan="11" class="text-center text-muted py-4">Nenhuma notificação registrada.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% if pag.pages > 1 %}
  <nav><ul class="pagination pagination-sm">
    {% for p in range(1, pag.pages + 1) %}
    <li class="page-item {{ 'active' if p == pag.page }}">
      <a class="page-link" href="?page={{ p }}">{{ p }}</a>
    </li>
    {% endfor %}
  </ul></nav>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 4: Adicionar link no menu**

Em `app/templates/base.html`, no submenu de Integrações/TagPlus (localizar via `grep -n "tagplus\|Integra" app/templates/base.html`; se não houver grupo, adicionar item no menu de integrações/admin existente):

```html
<li><a class="dropdown-item" href="{{ url_for('tagplus_notificacao.notificacoes_lista') }}">
  <i class="fas fa-bell"></i> Notificações TagPlus → WhatsApp
</a></li>
```

- [ ] **Step 5: Rodar e verificar que passa**

Run: `export DATABASE_URL=... && pytest tests/integracoes/tagplus/test_tela_notificacoes.py -v`
Expected: PASS (1 passed — redireciona pro login). Validar manualmente logado que a lista renderiza.

- [ ] **Step 6: Commit**

```bash
git add app/templates/integracoes/tagplus_notificacoes.html app/templates/base.html tests/integracoes/tagplus/test_tela_notificacoes.py
git commit -m "feat(tagplus): tela de historico/reenvio de notificacoes + link no menu"
```

---

## Task 8: Documentação operacional + verificação final

**Files:**
- Modify: `app/integracoes/tagplus/DOCUMENTACAO_API_TAGPLUS.md` ou novo `app/integracoes/tagplus/NOTIFICACAO_WHATSAPP.md`
- Test: rodar a suíte completa do módulo

- [ ] **Step 1: Documentar env vars + cadastro do webhook + como achar o JID**

Criar `app/integracoes/tagplus/NOTIFICACAO_WHATSAPP.md` (com header `doc:meta tipo: how-to`) cobrindo:
- Env vars: `TAGPLUS_NOTIFY_WHATSAPP_GROUP_JID`, `TAGPLUS_NOTIFY_ENABLED`, reuso de `OPENCLAW_GATEWAY_*`.
- Cadastro no painel TagPlus: URL `https://<dominio>/integracoes/tagplus/webhook/notificacao`, `X-Hub-Secret` = mesmo valor de `WEBHOOK_SECRET`, eventos `pedido_criado` + `nfe_criada`.
- Pré-requisito scope `read:pedidos` (pedido + vendedor-na-NF): reautorizar OAuth.
- Pré-requisito vendedores em `usuarios` (telefone + `whatsapp_autorizado=True` + `vendedor_vinculado`).
- Como descobrir o JID do grupo:
  ```bash
  # Enviar uma mensagem no grupo pelo WhatsApp; o conversation_jid aparece nos logs
  # do gateway OpenClaw, ou liste os grupos via gateway:
  cat ~/.openclaw/openclaw.json | jq .gateway.auth.token   # token
  # consultar o gateway local conforme a doc do OpenClaw (memória openclaw_whatsapp_integration)
  ```

- [ ] **Step 2: Rodar a suíte completa do módulo**

Run: `export DATABASE_URL=... && pytest tests/integracoes/tagplus/ -v`
Expected: todos PASS.

- [ ] **Step 3: Verificar imports/registro (smoke do app)**

Run:
```bash
python -c "from app import create_app; a=create_app(); print('rotas:', [r.rule for r in a.url_map.iter_rules() if 'notificacao' in r.rule])"
```
Expected: lista inclui `/integracoes/tagplus/webhook/notificacao`, `/integracoes/tagplus/notificacoes`, `/integracoes/tagplus/notificacoes/<int:reg_id>/reenviar`.

- [ ] **Step 4: Commit**

```bash
git add app/integracoes/tagplus/NOTIFICACAO_WHATSAPP.md
git commit -m "docs(tagplus): guia operacional da notificacao WhatsApp (env, webhook, JID)"
```

---

## Self-Review (preenchido)

**Spec coverage:**
- Webhook dedicado `pedido_criado`/`nfe_criada` → Task 6. ✓
- Grupo + DM vendedor (resolve via `usuarios`, fallback só-grupo) → Tasks 4, 5. ✓
- PDF DANFE anexado (NF, base64) → Tasks 1, 5. ✓
- Status PENDENTE/PROCESSANDO/ENVIADO/PARCIAL/ERRO/IGNORADO + flags → Tasks 2, 5. ✓
- Dedupe (UNIQUE) → Tasks 2, 6. ✓
- Retry de busca `[1,3,5]` → Task 5. ✓
- Tela histórico + reenvio + menu → Task 7. ✓
- Migration dual → Task 2. ✓
- Pré-requisitos (scope, JID, cadastro vendedor, webhook) → Task 8. ✓
- Não tocar `/webhook/tagplus/nfe` → confirmado (nenhuma task modifica o arquivo). ✓

**Gaps conhecidos a confirmar na execução:**
- Nome do método de senha do `Usuario` no fixture (Task 4 Step 1) — confirmar `set_senha` vs `set_password` vs `senha_hash` nullable.
- Local exato do link no `base.html` (Task 7 Step 4) — depende do submenu de integrações existente.
- Estrutura do objeto `vendedor`/`pedido_os_vinculada` é a documentada; validar no 1º webhook real (logar payload).

**Placeholder scan:** nenhum TBD/“implementar depois”; todo passo tem código/comando. ✓

**Type consistency:** funções `_resolver_vendedor`, `_buscar_nfe_com_retry`, `_buscar_pedido`, `_baixar_danfe_pdf`, `_enviar_para_destinos`, `processar_notificacao_async`, `disparar_thread` consistentes entre Tasks 4/5/6 e os testes. `send_whatsapp(..., anexo_b64=, anexo_filename=)` idêntico entre Task 1 e Task 5. ✓
