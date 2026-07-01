# Alertas de Faturamento por CNPJ — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ao faturar (NF nova via sync Odoo) para um CNPJ cadastrado e ativo, disparar UM aviso agrupado por cliente — por e-mail (lista do CNPJ, todos em cópia) e no Teams (canal fixo via webhook) — configurável por um card novo na Central Fiscal.

**Architecture:** Feature dona do módulo Faturamento (3 models + serviço + blueprint/telas), com um atalho (card) na Central Fiscal (módulo Recebimento) e UM gancho (SYNC 5) no fim de `importar_faturamento_odoo`. O entrypoint do serviço NUNCA levanta exceção (garante que o disparo nunca derrube o faturamento). Idempotência por `UNIQUE(numero_nf, canal)`.

**Tech Stack:** Flask 3.1 + Flask-SQLAlchemy 2.0, Jinja2, `app.notificacoes.email_sender` (SMTP/SES/SendGrid), `requests` (webhook Teams), pytest + Postgres local.

## Global Constraints

- **Branch**: trabalhar em `feature/alertas-faturamento-cnpj` (já criada a partir da `main`). NUNCA commitar na `main`. NUNCA versionar `.claude/` local ou `CLAUDE.md` pessoal.
- **Timezone**: usar `from app.utils.timezone import agora_utc_naive` para todo timestamp (naive Brasil). NUNCA `datetime.now()`/`utcnow()`.
- **Campos de tabela**: os únicos campos de `RelatorioFaturamentoImportado` usados são os reais do model (`numero_nf`, `data_fatura`, `cnpj_cliente`, `nome_cliente`, `valor_total`, `municipio`, `estado`, `ativo`) — ver `app/faturamento/models.py:4-26`.
- **Migration**: SEMPRE par `.sql` (DDL) + `.py` (runner idempotente), padrão `scripts/migrations/motos_assai_34_estoque_pecas_pendencia.py`. `CREATE TABLE IF NOT EXISTS`.
- **Testes**: Postgres local (fixtures em `tests/conftest.py`: `app`, `db`, `client`). `LOGIN_DISABLED=True` → rotas `@login_required` acessíveis pelo `client` sem login. Isolamento por savepoint (rollback no teardown).
- **Nunca derrubar o faturamento**: `processar_alertas_faturamento` engole toda exceção e retorna um dict-resumo.
- **CNPJ**: sempre normalizado (só dígitos) na gravação E na comparação.

**Spec:** `docs/superpowers/specs/2026-07-01-alertas-faturamento-cnpj-design.md` (decisões D1–D8).

---

## File Structure

- Create: `app/faturamento/services/alerta_faturamento_service.py` — lógica de disparo (pura + envio).
- Create: `app/faturamento/routes_alertas.py` — blueprint `alertas_faturamento_bp` (CRUD + config + teste).
- Create: `app/templates/faturamento/alertas/index.html` — tela única (config Teams + tabela CNPJs + form novo).
- Create: `scripts/migrations/2026_07_01_alertas_faturamento_cnpj.sql` e `.py` — 3 tabelas.
- Create: `tests/faturamento/__init__.py`, `tests/faturamento/test_alerta_models.py`, `tests/faturamento/test_alerta_service.py`, `tests/faturamento/test_alerta_rotas.py`.
- Modify: `app/faturamento/models.py` — +3 models.
- Modify: `app/__init__.py:31,1004` — importar/registrar o blueprint.
- Modify: `app/odoo/services/faturamento_service.py` — SYNC 5 (hook).
- Modify: `app/templates/recebimento/central_fiscal.html` — card novo.
- Modify: `app/faturamento/CLAUDE.md` — documentar SYNC 5 + models + blueprint.

---

### Task 1: Camada de dados — migration + 3 models

**Files:**
- Create: `scripts/migrations/2026_07_01_alertas_faturamento_cnpj.sql`
- Create: `scripts/migrations/2026_07_01_alertas_faturamento_cnpj.py`
- Modify: `app/faturamento/models.py` (append no fim)
- Test: `tests/faturamento/__init__.py`, `tests/faturamento/test_alerta_models.py`

**Interfaces:**
- Produces: models `AlertaFaturamentoCnpj` (campos `id, cnpj, nome_cliente, emails, ativo, criado_em, criado_por, atualizado_em`; método `lista_emails() -> list[str]`), `AlertaFaturamentoConfig` (`id, teams_webhook_url, teams_ativo, email_ativo, atualizado_em, atualizado_por`; classmethod `get_config() -> AlertaFaturamentoConfig`), `AlertaFaturamentoEnviado` (`id, numero_nf, cnpj, canal, status, detalhe, enviado_em`; `UNIQUE(numero_nf, canal)`).

- [ ] **Step 1: Escrever o SQL da migration**

Create `scripts/migrations/2026_07_01_alertas_faturamento_cnpj.sql`:

```sql
-- Alertas de Faturamento por CNPJ (e-mail + Teams)
-- Spec: docs/superpowers/specs/2026-07-01-alertas-faturamento-cnpj-design.md

CREATE TABLE IF NOT EXISTS alerta_faturamento_cnpj (
    id SERIAL PRIMARY KEY,
    cnpj VARCHAR(20) NOT NULL UNIQUE,
    nome_cliente VARCHAR(255),
    emails TEXT NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alerta_faturamento_config (
    id SERIAL PRIMARY KEY,
    teams_webhook_url VARCHAR(500),
    teams_ativo BOOLEAN NOT NULL DEFAULT FALSE,
    email_ativo BOOLEAN NOT NULL DEFAULT TRUE,
    atualizado_em TIMESTAMP,
    atualizado_por VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS alerta_faturamento_enviado (
    id SERIAL PRIMARY KEY,
    numero_nf VARCHAR(20) NOT NULL,
    cnpj VARCHAR(20),
    canal VARCHAR(10) NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'ok',
    detalhe TEXT,
    enviado_em TIMESTAMP,
    CONSTRAINT uq_alerta_fat_enviado_nf_canal UNIQUE (numero_nf, canal)
);

CREATE INDEX IF NOT EXISTS ix_alerta_faturamento_enviado_numero_nf ON alerta_faturamento_enviado (numero_nf);
CREATE INDEX IF NOT EXISTS ix_alerta_faturamento_enviado_cnpj ON alerta_faturamento_enviado (cnpj);
```

- [ ] **Step 2: Escrever o runner Python da migration**

Create `scripts/migrations/2026_07_01_alertas_faturamento_cnpj.py`:

```python
"""Migration: Alertas de Faturamento por CNPJ (e-mail + Teams).

Cria 3 tabelas: alerta_faturamento_cnpj, alerta_faturamento_config,
alerta_faturamento_enviado. Idempotente (CREATE TABLE/INDEX IF NOT EXISTS).
Semeia 1 linha de config (get-or-create).

Spec: docs/superpowers/specs/2026-07-01-alertas-faturamento-cnpj-design.md
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402

SQL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '2026_07_01_alertas_faturamento_cnpj.sql',
)


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH, 'r', encoding='utf-8') as f:
            db.session.execute(text(f.read()))
        # Semear config única
        existe = db.session.execute(
            text("SELECT COUNT(*) FROM alerta_faturamento_config")
        ).scalar()
        if not existe:
            db.session.execute(text(
                "INSERT INTO alerta_faturamento_config "
                "(teams_ativo, email_ativo) VALUES (FALSE, TRUE)"
            ))
        db.session.commit()
        print("OK: 3 tabelas de alertas de faturamento criadas/verificadas.")


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Aplicar a migration no Postgres local**

Run: `source .venv/bin/activate && python scripts/migrations/2026_07_01_alertas_faturamento_cnpj.py`
Expected: `OK: 3 tabelas de alertas de faturamento criadas/verificadas.`

- [ ] **Step 4: Adicionar os 3 models**

Append em `app/faturamento/models.py` (o import de `db`/`agora_utc_naive` já existe no topo do arquivo):

```python
class AlertaFaturamentoCnpj(db.Model):
    """CNPJ monitorado: ao faturar para ele, dispara alerta para os e-mails."""
    __tablename__ = 'alerta_faturamento_cnpj'

    id = db.Column(db.Integer, primary_key=True)
    cnpj = db.Column(db.String(20), nullable=False, unique=True, index=True)
    nome_cliente = db.Column(db.String(255), nullable=True)
    emails = db.Column(db.Text, nullable=False)  # lista separada por ; ou ,
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)

    def lista_emails(self):
        import re
        return [e.strip() for e in re.split(r'[;,\n]', self.emails or '') if e.strip()]

    def __repr__(self):
        return f"<AlertaFaturamentoCnpj {self.cnpj} ativo={self.ativo}>"


class AlertaFaturamentoConfig(db.Model):
    """Configuração global (1 linha): canal fixo do Teams + liga/desliga."""
    __tablename__ = 'alerta_faturamento_config'

    id = db.Column(db.Integer, primary_key=True)
    teams_webhook_url = db.Column(db.String(500), nullable=True)
    teams_ativo = db.Column(db.Boolean, default=False, nullable=False)
    email_ativo = db.Column(db.Boolean, default=True, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)
    atualizado_por = db.Column(db.String(100), nullable=True)

    @classmethod
    def get_config(cls):
        cfg = cls.query.first()
        if cfg is None:
            cfg = cls()
            db.session.add(cfg)
            db.session.commit()
        return cfg


class AlertaFaturamentoEnviado(db.Model):
    """Log/idempotência: 1 linha por (numero_nf, canal). Evita reenvio."""
    __tablename__ = 'alerta_faturamento_enviado'

    id = db.Column(db.Integer, primary_key=True)
    numero_nf = db.Column(db.String(20), nullable=False, index=True)
    cnpj = db.Column(db.String(20), nullable=True, index=True)
    canal = db.Column(db.String(10), nullable=False)  # 'email' | 'teams'
    status = db.Column(db.String(10), nullable=False, default='ok')  # 'ok' | 'erro'
    detalhe = db.Column(db.Text, nullable=True)
    enviado_em = db.Column(db.DateTime, default=agora_utc_naive)

    __table_args__ = (
        db.UniqueConstraint('numero_nf', 'canal', name='uq_alerta_fat_enviado_nf_canal'),
    )

    def __repr__(self):
        return f"<AlertaFaturamentoEnviado NF {self.numero_nf} {self.canal} {self.status}>"
```

- [ ] **Step 5: Escrever os testes dos models**

Create `tests/faturamento/__init__.py` (arquivo vazio).

Create `tests/faturamento/test_alerta_models.py`:

```python
import pytest
from app import db
from app.faturamento.models import (
    AlertaFaturamentoCnpj,
    AlertaFaturamentoConfig,
    AlertaFaturamentoEnviado,
)


def test_lista_emails_separadores(db):
    reg = AlertaFaturamentoCnpj(cnpj='12345678000199', emails='a@x.com; b@x.com , c@x.com')
    assert reg.lista_emails() == ['a@x.com', 'b@x.com', 'c@x.com']


def test_get_config_cria_linha_unica(db):
    cfg = AlertaFaturamentoConfig.get_config()
    assert cfg.id is not None
    assert cfg.email_ativo is True
    assert cfg.teams_ativo is False
    # segunda chamada não cria outra
    cfg2 = AlertaFaturamentoConfig.get_config()
    assert cfg2.id == cfg.id


def test_unique_nf_canal(db):
    db.session.add(AlertaFaturamentoEnviado(numero_nf='NF1', canal='email', status='ok'))
    db.session.commit()
    db.session.add(AlertaFaturamentoEnviado(numero_nf='NF1', canal='email', status='ok'))
    with pytest.raises(Exception):
        db.session.commit()
    db.session.rollback()
```

- [ ] **Step 6: Rodar os testes (devem passar)**

Run: `source .venv/bin/activate && pytest tests/faturamento/test_alerta_models.py -v`
Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add scripts/migrations/2026_07_01_alertas_faturamento_cnpj.sql scripts/migrations/2026_07_01_alertas_faturamento_cnpj.py app/faturamento/models.py tests/faturamento/__init__.py tests/faturamento/test_alerta_models.py
git commit -m "feat(faturamento): tabelas e models dos alertas de faturamento por CNPJ

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Serviço — helpers puros (agrupar, filtrar, formatar)

**Files:**
- Create: `app/faturamento/services/alerta_faturamento_service.py`
- Test: `tests/faturamento/test_alerta_service.py`

**Interfaces:**
- Consumes: models da Task 1.
- Produces: `normalizar_cnpj(cnpj) -> str`; `agrupar_por_cnpj(cabecalhos) -> dict[str, list]`; `filtrar_nao_enviadas(cabecalhos, canal) -> list`; `montar_linhas(cabecalhos) -> tuple[list[dict], str]` (dict com `numero_nf,data,valor,cidade`; str = total formatado); `montar_dados_email(linhas, total) -> dict`; `montar_texto_teams(nome, cnpj, linhas, total) -> str`.

- [ ] **Step 1: Escrever os testes dos helpers**

Create `tests/faturamento/test_alerta_service.py`:

```python
from datetime import date
from app import db
from app.faturamento.models import RelatorioFaturamentoImportado, AlertaFaturamentoEnviado
import app.faturamento.services.alerta_faturamento_service as svc


def _cab(nf, cnpj='12345678000199', valor=100.0, mun='São Paulo', uf='SP'):
    return RelatorioFaturamentoImportado(
        numero_nf=nf, cnpj_cliente=cnpj, nome_cliente='Cliente X',
        valor_total=valor, data_fatura=date(2026, 7, 1), municipio=mun, estado=uf, ativo=True,
    )


def test_normalizar_cnpj():
    assert svc.normalizar_cnpj('12.345.678/0001-99') == '12345678000199'
    assert svc.normalizar_cnpj(None) == ''


def test_agrupar_por_cnpj_ignora_mascara():
    a = _cab('NF1', cnpj='12.345.678/0001-99')
    b = _cab('NF2', cnpj='12345678000199')
    grupos = svc.agrupar_por_cnpj([a, b])
    assert set(grupos.keys()) == {'12345678000199'}
    assert len(grupos['12345678000199']) == 2


def test_montar_linhas_total(db):
    linhas, total = svc.montar_linhas([_cab('NF1', valor=100.0), _cab('NF2', valor=50.5)])
    assert total == 'R$ 150,50'
    assert linhas[0]['numero_nf'] == 'NF1'
    assert linhas[0]['cidade'] == 'São Paulo/SP'
    assert linhas[0]['valor'] == 'R$ 100,00'


def test_filtrar_nao_enviadas_exclui_ok(db):
    db.session.add(_cab('NF1')); db.session.add(_cab('NF2'))
    db.session.add(AlertaFaturamentoEnviado(numero_nf='NF1', canal='email', status='ok'))
    db.session.commit()
    cabs = RelatorioFaturamentoImportado.query.filter(
        RelatorioFaturamentoImportado.numero_nf.in_(['NF1', 'NF2'])).all()
    pend = svc.filtrar_nao_enviadas(cabs, 'email')
    assert {c.numero_nf for c in pend} == {'NF2'}


def test_filtrar_nao_enviadas_erro_reenvia(db):
    db.session.add(_cab('NF3'))
    db.session.add(AlertaFaturamentoEnviado(numero_nf='NF3', canal='email', status='erro'))
    db.session.commit()
    cabs = RelatorioFaturamentoImportado.query.filter_by(numero_nf='NF3').all()
    pend = svc.filtrar_nao_enviadas(cabs, 'email')
    assert {c.numero_nf for c in pend} == {'NF3'}  # erro não bloqueia retry


def test_montar_texto_teams():
    linhas, total = svc.montar_linhas([_cab('NF1', valor=100.0)])
    txt = svc.montar_texto_teams('Cliente X', '12345678000199', linhas, total)
    assert 'Cliente X' in txt and 'NF1' in txt and 'R$ 100,00' in txt and total in txt
```

- [ ] **Step 2: Rodar os testes (devem falhar por módulo inexistente)**

Run: `source .venv/bin/activate && pytest tests/faturamento/test_alerta_service.py -v`
Expected: FAIL (ModuleNotFoundError: alerta_faturamento_service).

- [ ] **Step 3: Escrever os helpers**

Create `app/faturamento/services/alerta_faturamento_service.py`:

```python
"""Alertas de faturamento por CNPJ (e-mail + Teams).

Ao faturar (NF nova via sync Odoo) para um CNPJ cadastrado e ativo, dispara UM
aviso por cliente (agrupando as NFs novas) por e-mail (lista do CNPJ, todos em
cópia) e no Teams (canal fixo via webhook). Idempotente por (numero_nf, canal).

`processar_alertas_faturamento` NUNCA levanta exceção (garantia p/ o hook da
sync Odoo — nunca derruba o faturamento).
"""
import re
import logging

import requests

from app import db
from app.utils.timezone import agora_utc_naive
from app.faturamento.models import (
    RelatorioFaturamentoImportado,
    AlertaFaturamentoCnpj,
    AlertaFaturamentoConfig,
    AlertaFaturamentoEnviado,
)
from app.notificacoes.email_sender import email_sender, EmailTemplates, EmailConfig

logger = logging.getLogger(__name__)

TEAMS_TIMEOUT = 15


def normalizar_cnpj(cnpj):
    return re.sub(r'\D', '', cnpj or '')


def _fmt_moeda(valor):
    v = float(valor or 0)
    return ('R$ ' + f'{v:,.2f}').replace(',', 'X').replace('.', ',').replace('X', '.')


def _fmt_data(d):
    return d.strftime('%d/%m/%Y') if d else '-'


def agrupar_por_cnpj(cabecalhos):
    grupos = {}
    for nf in cabecalhos:
        grupos.setdefault(normalizar_cnpj(nf.cnpj_cliente), []).append(nf)
    return grupos


def filtrar_nao_enviadas(cabecalhos, canal):
    numeros = [n.numero_nf for n in cabecalhos]
    if not numeros:
        return []
    ja_ok = {
        r.numero_nf for r in AlertaFaturamentoEnviado.query.filter(
            AlertaFaturamentoEnviado.canal == canal,
            AlertaFaturamentoEnviado.status == 'ok',
            AlertaFaturamentoEnviado.numero_nf.in_(numeros),
        ).all()
    }
    return [n for n in cabecalhos if n.numero_nf not in ja_ok]


def montar_linhas(cabecalhos):
    linhas, total = [], 0.0
    for nf in sorted(cabecalhos, key=lambda n: n.numero_nf):
        total += float(nf.valor_total or 0)
        cidade = f"{nf.municipio}/{nf.estado}" if nf.municipio else (nf.estado or '')
        linhas.append({
            'numero_nf': nf.numero_nf,
            'data': _fmt_data(nf.data_fatura),
            'valor': _fmt_moeda(nf.valor_total),
            'cidade': cidade,
        })
    return linhas, _fmt_moeda(total)


def montar_dados_email(linhas, total):
    dados = {f"NF {l['numero_nf']}": f"{l['data']} · {l['valor']} · {l['cidade']}" for l in linhas}
    dados['Total'] = total
    return dados


def montar_texto_teams(nome, cnpj, linhas, total):
    corpo = "\n".join(
        f"- NF {l['numero_nf']} · {l['data']} · {l['valor']} · {l['cidade']}" for l in linhas
    )
    return f"**Faturamento — {nome or cnpj}** (CNPJ {cnpj})\n{corpo}\n**Total: {total}**"
```

- [ ] **Step 4: Rodar os testes (devem passar)**

Run: `source .venv/bin/activate && pytest tests/faturamento/test_alerta_service.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add app/faturamento/services/alerta_faturamento_service.py tests/faturamento/test_alerta_service.py
git commit -m "feat(faturamento): helpers dos alertas (agrupar/filtrar/formatar)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Serviço — envio, log e orquestração (never-raise)

**Files:**
- Modify: `app/faturamento/services/alerta_faturamento_service.py` (append)
- Test: `tests/faturamento/test_alerta_service.py` (append)

**Interfaces:**
- Consumes: helpers da Task 2.
- Produces: `registrar_envio(numero_nf, cnpj, canal, ok, detalhe=None) -> None` (upsert por NF+canal); `enviar_email(cnpj_cfg, nome, cnpj, linhas, total) -> dict` (`{'success': bool, 'error'|'message_id': ...}`); `enviar_teams(config, texto) -> dict`; `processar_alertas_faturamento(nfs_novas) -> dict` (NUNCA levanta; retorna `{'cnpjs','emails_ok','teams_ok','erros'}`); `enviar_teste(cnpj_cfg, config) -> dict`.

- [ ] **Step 1: Escrever os testes de orquestração (com mocks)**

Append em `tests/faturamento/test_alerta_service.py`:

```python
class _FakeSender:
    def __init__(self): self.calls = []
    def send(self, **kw):
        self.calls.append(kw)
        return {'success': True, 'message_id': 'x', 'error': None}


def _cadastrar(db, cnpj='12345678000199', emails='a@x.com; b@x.com', ativo=True):
    from app.faturamento.models import AlertaFaturamentoCnpj
    reg = AlertaFaturamentoCnpj(cnpj=svc.normalizar_cnpj(cnpj), emails=emails,
                                nome_cliente='Cliente X', ativo=ativo)
    db.session.add(reg); db.session.commit()
    return reg


def test_processar_envia_email_agrupado(db, monkeypatch):
    _cadastrar(db)
    db.session.add(_cab('NF1', valor=100.0)); db.session.add(_cab('NF2', valor=50.0))
    db.session.commit()
    fake = _FakeSender()
    monkeypatch.setattr(svc, 'email_sender', fake)
    monkeypatch.setattr(svc.EmailConfig, 'is_configured', classmethod(lambda cls: True))
    cfg = AlertaFaturamentoConfig.get_config(); cfg.teams_ativo = False; db.session.commit()

    resumo = svc.processar_alertas_faturamento(['NF1', 'NF2'])

    assert resumo['emails_ok'] == 1           # 1 e-mail agrupado
    assert len(fake.calls) == 1
    assert fake.calls[0]['to'] == 'a@x.com'
    assert fake.calls[0]['cc'] == ['b@x.com']  # demais em cópia (D8)
    enviados = AlertaFaturamentoEnviado.query.filter_by(canal='email', status='ok').count()
    assert enviados == 2                        # 1 registro por NF


def test_processar_nao_reenvia(db, monkeypatch):
    _cadastrar(db)
    db.session.add(_cab('NF1', valor=100.0)); db.session.commit()
    fake = _FakeSender()
    monkeypatch.setattr(svc, 'email_sender', fake)
    monkeypatch.setattr(svc.EmailConfig, 'is_configured', classmethod(lambda cls: True))
    cfg = AlertaFaturamentoConfig.get_config(); cfg.teams_ativo = False; db.session.commit()

    svc.processar_alertas_faturamento(['NF1'])
    svc.processar_alertas_faturamento(['NF1'])   # 2ª rodada
    assert len(fake.calls) == 1                  # não reenviou


def test_processar_ignora_cnpj_nao_cadastrado(db, monkeypatch):
    db.session.add(_cab('NF9', cnpj='99999999000199')); db.session.commit()
    fake = _FakeSender(); monkeypatch.setattr(svc, 'email_sender', fake)
    monkeypatch.setattr(svc.EmailConfig, 'is_configured', classmethod(lambda cls: True))
    resumo = svc.processar_alertas_faturamento(['NF9'])
    assert resumo['cnpjs'] == 0 and len(fake.calls) == 0


def test_processar_teams_ok(db, monkeypatch):
    _cadastrar(db)
    db.session.add(_cab('NFT', valor=10.0)); db.session.commit()
    cfg = AlertaFaturamentoConfig.get_config()
    cfg.teams_ativo = True; cfg.teams_webhook_url = 'https://hook.example/x'
    cfg.email_ativo = False; db.session.commit()
    posts = []
    class _Resp: status_code = 200
    monkeypatch.setattr(svc.requests, 'post', lambda url, **kw: (posts.append((url, kw)), _Resp())[1])
    resumo = svc.processar_alertas_faturamento(['NFT'])
    assert resumo['teams_ok'] == 1 and len(posts) == 1
    assert posts[0][0] == 'https://hook.example/x'
    assert 'NFT' in posts[0][1]['json']['text']


def test_processar_nunca_levanta(db, monkeypatch):
    _cadastrar(db)
    db.session.add(_cab('NFX')); db.session.commit()
    monkeypatch.setattr(svc, 'agrupar_por_cnpj',
                        lambda c: (_ for _ in ()).throw(RuntimeError('boom')))
    resumo = svc.processar_alertas_faturamento(['NFX'])
    assert any('boom' in e for e in resumo['erros'])  # capturou, não levantou


def test_processar_vazio_noop(db):
    assert svc.processar_alertas_faturamento([]) == {'cnpjs': 0, 'emails_ok': 0, 'teams_ok': 0, 'erros': []}
```

- [ ] **Step 2: Rodar (devem falhar por funções inexistentes)**

Run: `source .venv/bin/activate && pytest tests/faturamento/test_alerta_service.py -k processar -v`
Expected: FAIL (AttributeError: processar_alertas_faturamento).

- [ ] **Step 3: Implementar envio + orquestração**

Append em `app/faturamento/services/alerta_faturamento_service.py`:

```python
def registrar_envio(numero_nf, cnpj, canal, ok, detalhe=None):
    """Upsert por (numero_nf, canal): evita violar o UNIQUE ao reprocessar erro."""
    reg = AlertaFaturamentoEnviado.query.filter_by(numero_nf=numero_nf, canal=canal).first()
    if reg is None:
        reg = AlertaFaturamentoEnviado(numero_nf=numero_nf, canal=canal)
        db.session.add(reg)
    reg.cnpj = cnpj
    reg.status = 'ok' if ok else 'erro'
    reg.detalhe = (detalhe or '')[:2000]
    reg.enviado_em = agora_utc_naive()


def enviar_email(cnpj_cfg, nome, cnpj, linhas, total):
    if not EmailConfig.is_configured():
        return {'success': False, 'error': 'E-mail não configurado (EMAIL_*)'}
    emails = cnpj_cfg.lista_emails()
    if not emails:
        return {'success': False, 'error': 'CNPJ sem e-mails cadastrados'}
    return email_sender.send(
        to=emails[0],
        cc=emails[1:] or None,
        subject=f"Faturamento — {nome or cnpj}",
        body_html=EmailTemplates.info(
            titulo=f"Faturamento — {nome or cnpj} (CNPJ {cnpj})",
            mensagem="Foram faturadas as seguintes notas para este cliente:",
            dados=montar_dados_email(linhas, total),
        ),
    )


def enviar_teams(config, texto):
    if not (config.teams_ativo and config.teams_webhook_url):
        return {'success': False, 'error': 'Teams desativado ou sem URL'}
    try:
        resp = requests.post(config.teams_webhook_url, json={'text': texto}, timeout=TEAMS_TIMEOUT)
        if 200 <= resp.status_code < 300:
            return {'success': True}
        return {'success': False, 'error': f'HTTP {resp.status_code}'}
    except requests.RequestException as e:
        return {'success': False, 'error': str(e)}


def _processar_canal(nfs, cnpj, nome, canal, envia_fn):
    """Filtra pendentes do canal, envia 1x agrupado, registra por NF. Retorna (ok, erro)."""
    pend = filtrar_nao_enviadas(nfs, canal)
    if not pend:
        return None, None
    linhas, total = montar_linhas(pend)
    if canal == 'email':
        r = envia_fn(nome, cnpj, linhas, total)
    else:
        r = envia_fn(montar_texto_teams(nome, cnpj, linhas, total))
    ok = bool(r.get('success'))
    for nf in pend:
        registrar_envio(nf.numero_nf, cnpj, canal, ok, r.get('error') or r.get('message_id'))
    return ok, (None if ok else r.get('error'))


def processar_alertas_faturamento(nfs_novas):
    """Entrypoint do hook. NUNCA levanta exceção."""
    resumo = {'cnpjs': 0, 'emails_ok': 0, 'teams_ok': 0, 'erros': []}
    try:
        if not nfs_novas:
            return resumo
        cabecalhos = RelatorioFaturamentoImportado.query.filter(
            RelatorioFaturamentoImportado.numero_nf.in_(list(nfs_novas)),
            RelatorioFaturamentoImportado.ativo.is_(True),
        ).all()
        if not cabecalhos:
            return resumo
        config = AlertaFaturamentoConfig.get_config()
        for cnpj, nfs in agrupar_por_cnpj(cabecalhos).items():
            try:
                cnpj_cfg = AlertaFaturamentoCnpj.query.filter_by(cnpj=cnpj, ativo=True).first()
                if not cnpj_cfg:
                    continue
                resumo['cnpjs'] += 1
                nome = cnpj_cfg.nome_cliente or (nfs[0].nome_cliente if nfs else None)
                if config.email_ativo:
                    ok, erro = _processar_canal(
                        nfs, cnpj, nome, 'email',
                        lambda n, c, l, t: enviar_email(cnpj_cfg, n, c, l, t))
                    if ok:
                        resumo['emails_ok'] += 1
                    elif erro:
                        resumo['erros'].append(f"email {cnpj}: {erro}")
                if config.teams_ativo:
                    ok, erro = _processar_canal(
                        nfs, cnpj, nome, 'teams',
                        lambda texto: enviar_teams(config, texto))
                    if ok:
                        resumo['teams_ok'] += 1
                    elif erro:
                        resumo['erros'].append(f"teams {cnpj}: {erro}")
                db.session.commit()
            except Exception as e:  # isola por CNPJ
                db.session.rollback()
                logger.error(f"Alerta faturamento CNPJ {cnpj} falhou: {e}", exc_info=True)
                resumo['erros'].append(f"{cnpj}: {e}")
        return resumo
    except Exception as e:  # nunca propaga p/ a sync
        logger.error(f"processar_alertas_faturamento falhou: {e}", exc_info=True)
        try:
            db.session.rollback()
        except Exception:
            pass
        resumo['erros'].append(str(e))
        return resumo


def enviar_teste(cnpj_cfg, config):
    """Dispara um aviso de TESTE (linha fictícia) para o CNPJ. NÃO grava log."""
    linhas = [{'numero_nf': 'TESTE', 'data': _fmt_data(agora_utc_naive().date()),
               'valor': _fmt_moeda(0), 'cidade': ''}]
    total = _fmt_moeda(0)
    nome = cnpj_cfg.nome_cliente or cnpj_cfg.cnpj
    r_email = enviar_email(cnpj_cfg, nome, cnpj_cfg.cnpj, linhas, total) if config.email_ativo else {'success': None}
    r_teams = enviar_teams(config, montar_texto_teams(nome, cnpj_cfg.cnpj, linhas, total)) if config.teams_ativo else {'success': None}
    return {'email': r_email, 'teams': r_teams}
```

- [ ] **Step 4: Rodar TODOS os testes do serviço (devem passar)**

Run: `source .venv/bin/activate && pytest tests/faturamento/test_alerta_service.py -v`
Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add app/faturamento/services/alerta_faturamento_service.py tests/faturamento/test_alerta_service.py
git commit -m "feat(faturamento): envio e orquestracao dos alertas (never-raise + idempotente)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Gancho na sync Odoo (SYNC 5)

**Files:**
- Modify: `app/odoo/services/faturamento_service.py` (bloco após SYNC 4, antes de `# ⏱️ CALCULAR PERFORMANCE REAL`)

**Interfaces:**
- Consumes: `processar_alertas_faturamento(nfs_novas)` (Task 3) e a variável local `nfs_novas` já existente na função `importar_faturamento_odoo`.

- [ ] **Step 1: Inserir o hook**

Em `app/odoo/services/faturamento_service.py`, logo após o bloco `# 🚀 SINCRONIZAÇÃO 4: Lançamento automático de fretes` (que termina no `except ImportError as e:` de fretes) e ANTES de `# ⏱️ CALCULAR PERFORMANCE REAL`, inserir:

```python
            # 🚀 SINCRONIZAÇÃO 5: Alertas de faturamento por CNPJ (e-mail + Teams)
            try:
                from app.faturamento.services.alerta_faturamento_service import processar_alertas_faturamento
                if nfs_novas:
                    resumo_alertas = processar_alertas_faturamento(nfs_novas)
                    stats_sincronizacao['alertas_faturamento'] = resumo_alertas
                    logger.info(f"🔔 Alertas de faturamento: {resumo_alertas}")
            except Exception as e:
                logger.error(f"Alertas de faturamento falharam (ignorado): {e}", exc_info=True)
```

- [ ] **Step 2: Verificar a inserção**

Run: `grep -n "SINCRONIZAÇÃO 5\|processar_alertas_faturamento" app/odoo/services/faturamento_service.py`
Expected: 2+ linhas (comentário + chamada) dentro de `importar_faturamento_odoo`.

- [ ] **Step 3: Rodar a suíte de faturamento (nada quebrou)**

Run: `source .venv/bin/activate && pytest tests/faturamento -v`
Expected: todos passam (models + service). A garantia never-raise já é coberta por `test_processar_nunca_levanta`.

- [ ] **Step 4: Commit**

```bash
git add app/odoo/services/faturamento_service.py
git commit -m "feat(odoo): SYNC 5 dispara alertas de faturamento por CNPJ (isolado)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: UI — blueprint, telas e card na Central Fiscal

**Files:**
- Create: `app/faturamento/routes_alertas.py`
- Create: `app/templates/faturamento/alertas/index.html`
- Modify: `app/__init__.py:31` (import) e `:1004` (register)
- Modify: `app/templates/recebimento/central_fiscal.html` (card novo)
- Test: `tests/faturamento/test_alerta_rotas.py`

**Interfaces:**
- Consumes: models (Task 1), `normalizar_cnpj`, `enviar_teste` (Task 2/3).
- Produces: blueprint `alertas_faturamento_bp` (prefix `/faturamento/alertas`) com rotas nomeadas `alertas_faturamento.index|novo|editar|remover|config|testar`.

- [ ] **Step 1: Escrever o blueprint**

Create `app/faturamento/routes_alertas.py`:

```python
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db
from app.faturamento.models import AlertaFaturamentoCnpj, AlertaFaturamentoConfig
from app.faturamento.services.alerta_faturamento_service import normalizar_cnpj, enviar_teste

logger = logging.getLogger(__name__)

alertas_faturamento_bp = Blueprint(
    'alertas_faturamento', __name__, url_prefix='/faturamento/alertas'
)


def _quem():
    return getattr(current_user, 'nome', None) or getattr(current_user, 'email', None)


@alertas_faturamento_bp.route('/')
@login_required
def index():
    cnpjs = AlertaFaturamentoCnpj.query.order_by(
        AlertaFaturamentoCnpj.ativo.desc(), AlertaFaturamentoCnpj.nome_cliente
    ).all()
    config = AlertaFaturamentoConfig.get_config()
    return render_template('faturamento/alertas/index.html', cnpjs=cnpjs, config=config)


@alertas_faturamento_bp.route('/novo', methods=['POST'])
@login_required
def novo():
    cnpj = normalizar_cnpj(request.form.get('cnpj'))
    emails = (request.form.get('emails') or '').strip()
    nome = (request.form.get('nome_cliente') or '').strip() or None
    if not cnpj or not emails:
        flash('Informe o CNPJ e ao menos um e-mail.', 'warning')
        return redirect(url_for('alertas_faturamento.index'))
    if AlertaFaturamentoCnpj.query.filter_by(cnpj=cnpj).first():
        flash('CNPJ já cadastrado.', 'warning')
        return redirect(url_for('alertas_faturamento.index'))
    db.session.add(AlertaFaturamentoCnpj(cnpj=cnpj, emails=emails, nome_cliente=nome, criado_por=_quem()))
    db.session.commit()
    flash('CNPJ cadastrado.', 'success')
    return redirect(url_for('alertas_faturamento.index'))


@alertas_faturamento_bp.route('/<int:id>/editar', methods=['POST'])
@login_required
def editar(id):
    reg = db.session.get(AlertaFaturamentoCnpj, id)
    if not reg:
        flash('Registro não encontrado.', 'warning')
        return redirect(url_for('alertas_faturamento.index'))
    reg.emails = (request.form.get('emails') or reg.emails).strip()
    reg.nome_cliente = (request.form.get('nome_cliente') or '').strip() or None
    reg.ativo = request.form.get('ativo') == 'on'
    db.session.commit()
    flash('Cadastro atualizado.', 'success')
    return redirect(url_for('alertas_faturamento.index'))


@alertas_faturamento_bp.route('/<int:id>/remover', methods=['POST'])
@login_required
def remover(id):
    reg = db.session.get(AlertaFaturamentoCnpj, id)
    if reg:
        db.session.delete(reg)
        db.session.commit()
        flash('CNPJ removido.', 'success')
    return redirect(url_for('alertas_faturamento.index'))


@alertas_faturamento_bp.route('/config', methods=['POST'])
@login_required
def config():
    cfg = AlertaFaturamentoConfig.get_config()
    cfg.teams_webhook_url = (request.form.get('teams_webhook_url') or '').strip() or None
    cfg.teams_ativo = request.form.get('teams_ativo') == 'on'
    cfg.email_ativo = request.form.get('email_ativo') == 'on'
    cfg.atualizado_por = _quem()
    db.session.commit()
    flash('Configuração salva.', 'success')
    return redirect(url_for('alertas_faturamento.index'))


@alertas_faturamento_bp.route('/<int:id>/testar', methods=['POST'])
@login_required
def testar(id):
    reg = db.session.get(AlertaFaturamentoCnpj, id)
    if not reg:
        flash('Registro não encontrado.', 'warning')
        return redirect(url_for('alertas_faturamento.index'))
    r = enviar_teste(reg, AlertaFaturamentoConfig.get_config())
    flash(f"Teste enviado — e-mail: {r['email'].get('success')}, teams: {r['teams'].get('success')}", 'info')
    return redirect(url_for('alertas_faturamento.index'))
```

- [ ] **Step 2: Escrever a tela**

Create `app/templates/faturamento/alertas/index.html`:

```html
{% extends "base.html" %}
{% block title %}Alertas de Faturamento{% endblock %}
{% block content %}
<div class="fin-container premium-page">
  <header class="fin-header">
    <div class="fin-header__content">
      <h1 class="fin-header__title"><i class="fas fa-bell"></i> Alertas de Faturamento</h1>
      <p class="fin-header__subtitle">Ao faturar para um CNPJ cadastrado, avisa por e-mail e no Teams.</p>
    </div>
    <div class="fin-header__actions">
      <a href="{{ url_for('recebimento_views.central_fiscal') }}" class="btn btn-outline-light btn-sm">
        <i class="fas fa-arrow-left"></i> Voltar
      </a>
    </div>
  </header>

  {% with msgs = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in msgs %}<div class="alert alert-{{ cat }}">{{ msg }}</div>{% endfor %}
  {% endwith %}

  <!-- Configuração global -->
  <div class="fin-section-card">
    <h3 class="fin-section-card__title">Configuração</h3>
    <form method="post" action="{{ url_for('alertas_faturamento.config') }}" class="row g-2">
      <div class="col-12">
        <label class="form-label">Endereço do canal do Teams (webhook)</label>
        <input type="url" name="teams_webhook_url" class="form-control"
               value="{{ config.teams_webhook_url or '' }}" placeholder="https://...">
      </div>
      <div class="col-auto form-check">
        <input class="form-check-input" type="checkbox" name="email_ativo" id="email_ativo"
               {% if config.email_ativo %}checked{% endif %}>
        <label class="form-check-label" for="email_ativo">Enviar e-mail</label>
      </div>
      <div class="col-auto form-check">
        <input class="form-check-input" type="checkbox" name="teams_ativo" id="teams_ativo"
               {% if config.teams_ativo %}checked{% endif %}>
        <label class="form-check-label" for="teams_ativo">Enviar Teams</label>
      </div>
      <div class="col-12"><button class="btn btn-primary btn-sm">Salvar configuração</button></div>
    </form>
  </div>

  <!-- Novo CNPJ -->
  <div class="fin-section-card">
    <h3 class="fin-section-card__title">Adicionar CNPJ</h3>
    <form method="post" action="{{ url_for('alertas_faturamento.novo') }}" class="row g-2">
      <div class="col-md-3"><input name="cnpj" class="form-control" placeholder="CNPJ" required></div>
      <div class="col-md-3"><input name="nome_cliente" class="form-control" placeholder="Nome (opcional)"></div>
      <div class="col-md-4"><input name="emails" class="form-control" placeholder="e-mails (separados por ; ou ,)" required></div>
      <div class="col-md-2"><button class="btn btn-success w-100">Adicionar</button></div>
    </form>
  </div>

  <!-- Lista -->
  <div class="fin-section-card">
    <h3 class="fin-section-card__title">CNPJs monitorados</h3>
    <table class="table table-sm align-middle">
      <thead><tr><th>CNPJ</th><th>Nome</th><th>E-mails</th><th>Ativo</th><th>Ações</th></tr></thead>
      <tbody>
      {% for c in cnpjs %}
        <tr>
          <form method="post" action="{{ url_for('alertas_faturamento.editar', id=c.id) }}">
            <td>{{ c.cnpj }}</td>
            <td><input name="nome_cliente" class="form-control form-control-sm" value="{{ c.nome_cliente or '' }}"></td>
            <td><input name="emails" class="form-control form-control-sm" value="{{ c.emails }}"></td>
            <td><input type="checkbox" name="ativo" {% if c.ativo %}checked{% endif %}></td>
            <td class="text-nowrap">
              <button class="btn btn-sm btn-outline-primary">Salvar</button>
          </form>
              <form method="post" action="{{ url_for('alertas_faturamento.testar', id=c.id) }}" style="display:inline">
                <button class="btn btn-sm btn-outline-info">Testar</button>
              </form>
              <form method="post" action="{{ url_for('alertas_faturamento.remover', id=c.id) }}" style="display:inline"
                    onsubmit="return confirm('Remover este CNPJ?')">
                <button class="btn btn-sm btn-outline-danger">Remover</button>
              </form>
            </td>
        </tr>
      {% else %}
        <tr><td colspan="5" class="text-muted">Nenhum CNPJ cadastrado.</td></tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 3: Registrar o blueprint**

Em `app/__init__.py`, na linha do import (junto a `from app.faturamento.routes import faturamento_bp`, ~linha 31):

```python
    from app.faturamento.routes_alertas import alertas_faturamento_bp
```

E junto ao registro (após `app.register_blueprint(atualizar_nf_bp)`, ~linha 1005):

```python
    app.register_blueprint(alertas_faturamento_bp)
```

- [ ] **Step 4: Adicionar o card na Central Fiscal**

Em `app/templates/recebimento/central_fiscal.html`, inserir ANTES do fechamento `</div>` do `.fiscal-dashboard-grid` (logo após o card "RELATORIOS"):

```html
        <!-- ALERTAS DE FATURAMENTO -->
        <div class="fin-section-card">
            <div class="fin-section-card__header">
                <div class="fin-section-card__icon fin-section-card__icon--amber">
                    <i class="fas fa-bell"></i>
                </div>
                <div>
                    <h3 class="fin-section-card__title">Alertas de Faturamento</h3>
                    <p class="fin-section-card__desc">Avisa por e-mail/Teams ao faturar para CNPJs cadastrados</p>
                </div>
            </div>
            <div class="fin-section-links">
                <a href="{{ url_for('alertas_faturamento.index') }}" class="fin-section-link">
                    <div class="fin-section-link__icon"><i class="fas fa-envelope text-warning"></i></div>
                    <div class="fin-section-link__text">
                        <div class="fin-section-link__title">Configurar Alertas</div>
                        <div class="fin-section-link__subtitle">CNPJs, e-mails e canal do Teams</div>
                    </div>
                </a>
            </div>
        </div>
```

- [ ] **Step 5: Escrever os testes de rota**

Create `tests/faturamento/test_alerta_rotas.py`:

```python
from app import db
from app.faturamento.models import AlertaFaturamentoCnpj, AlertaFaturamentoConfig


def test_index_200(client):
    assert client.get('/faturamento/alertas/').status_code == 200


def test_novo_normaliza_cnpj(client, db):
    resp = client.post('/faturamento/alertas/novo', data={
        'cnpj': '12.345.678/0001-99', 'nome_cliente': 'ACME', 'emails': 'x@a.com'})
    assert resp.status_code in (302, 200)
    reg = AlertaFaturamentoCnpj.query.filter_by(cnpj='12345678000199').first()
    assert reg is not None and reg.nome_cliente == 'ACME'


def test_novo_sem_email_rejeita(client, db):
    client.post('/faturamento/alertas/novo', data={'cnpj': '11111111000111', 'emails': ''})
    assert AlertaFaturamentoCnpj.query.filter_by(cnpj='11111111000111').first() is None


def test_editar_e_remover(client, db):
    reg = AlertaFaturamentoCnpj(cnpj='22222222000122', emails='a@a.com', ativo=True)
    db.session.add(reg); db.session.commit(); rid = reg.id
    client.post(f'/faturamento/alertas/{rid}/editar', data={'emails': 'b@b.com', 'nome_cliente': 'X'})
    assert db.session.get(AlertaFaturamentoCnpj, rid).emails == 'b@b.com'
    assert db.session.get(AlertaFaturamentoCnpj, rid).ativo is False  # checkbox ausente = off
    client.post(f'/faturamento/alertas/{rid}/remover')
    assert db.session.get(AlertaFaturamentoCnpj, rid) is None


def test_config_salva(client, db):
    client.post('/faturamento/alertas/config', data={
        'teams_webhook_url': 'https://hook.example/y', 'teams_ativo': 'on', 'email_ativo': 'on'})
    cfg = AlertaFaturamentoConfig.get_config()
    assert cfg.teams_webhook_url == 'https://hook.example/y' and cfg.teams_ativo is True
```

- [ ] **Step 6: Rodar os testes de rota (devem passar)**

Run: `source .venv/bin/activate && pytest tests/faturamento/test_alerta_rotas.py -v`
Expected: 5 passed.

- [ ] **Step 7: Commit**

```bash
git add app/faturamento/routes_alertas.py app/templates/faturamento/alertas/index.html app/__init__.py app/templates/recebimento/central_fiscal.html tests/faturamento/test_alerta_rotas.py
git commit -m "feat(faturamento): tela de alertas na Central Fiscal (CRUD + config + teste)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Documentação + schemas

**Files:**
- Create (via gerador): `.claude/skills/consultando-sql/schemas/tables/alerta_faturamento_cnpj.json`, `..._config.json`, `..._enviado.json`
- Modify: `app/faturamento/CLAUDE.md`

- [ ] **Step 1: Gerar os schemas JSON das 3 tabelas novas**

Run: `source .venv/bin/activate && python .claude/skills/consultando-sql/scripts/generate_schemas.py`
Expected: cria os 3 JSONs em `.claude/skills/consultando-sql/schemas/tables/` (pode atualizar `catalog.json`/`relationships.json`).

- [ ] **Step 2: Documentar no CLAUDE.md do faturamento**

Em `app/faturamento/CLAUDE.md`, na seção "Fluxo (Odoo → 4 sincronizacoes)", trocar o título para incluir a SYNC 5 e adicionar a frase:

```markdown
**(5)** `processar_alertas_faturamento(nfs_novas)` (`services/alerta_faturamento_service.py`) — para cada NF NOVA cujo `cnpj_cliente` está cadastrado e ativo em `alerta_faturamento_cnpj`, dispara UM aviso agrupado por cliente (e-mail via `app/notificacoes/email_sender` + Teams via webhook `alerta_faturamento_config`). Idempotente por `UNIQUE(numero_nf, canal)` em `alerta_faturamento_enviado`. NUNCA levanta exceção (não derruba a sync). Cadastro/config na Central Fiscal (`alertas_faturamento_bp`, `/faturamento/alertas`).
```

E na tabela "Models", adicionar 3 linhas:

```markdown
| `AlertaFaturamentoCnpj` | `alerta_faturamento_cnpj` | CNPJ monitorado + lista de e-mails (`;`/`,`). `cnpj` normalizado (só dígitos), UNIQUE |
| `AlertaFaturamentoConfig` | `alerta_faturamento_config` | 1 linha (`get_config`): webhook Teams + flags `teams_ativo`/`email_ativo` |
| `AlertaFaturamentoEnviado` | `alerta_faturamento_enviado` | Log/idempotência. `UNIQUE(numero_nf, canal)`; upsert em retry de erro |
```

- [ ] **Step 3: Rodar a suíte completa da feature**

Run: `source .venv/bin/activate && pytest tests/faturamento -v`
Expected: models (3) + service (12) + rotas (5) = 20 passed.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/consultando-sql/schemas/tables/alerta_faturamento_cnpj.json .claude/skills/consultando-sql/schemas/tables/alerta_faturamento_config.json .claude/skills/consultando-sql/schemas/tables/alerta_faturamento_enviado.json .claude/skills/consultando-sql/schemas/catalog.json .claude/skills/consultando-sql/schemas/relationships.json app/faturamento/CLAUDE.md
git commit -m "docs(faturamento): documenta SYNC 5 + schemas das tabelas de alertas

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

> Nota: os arquivos sob `.claude/` de schema SÃO versionados no repo (fazem parte do projeto, não são config pessoal). NÃO commitar `CLAUDE.md` pessoal (raiz `~/.claude`) nem outros arquivos de `.claude/` locais fora dos schemas.

---

## Self-Review (feito)

**1. Spec coverage:**
- D1 e-mail+Teams → Task 3 (`enviar_email`/`enviar_teams`). ✅
- D2 canal fixo → `AlertaFaturamentoConfig.teams_webhook_url` (Task 1/3/5). ✅
- D3 aviso agrupado por CNPJ → `agrupar_por_cnpj` + `_processar_canal` (1 envio/CNPJ). ✅
- D4 config na Central Fiscal → Task 5 (card + tela). ✅
- D5 gatilho `nfs_novas` → Task 4. ✅
- D6 não repetir → `filtrar_nao_enviadas` + UNIQUE + upsert (Task 1/3). ✅
- D7 never-raise → `processar_alertas_faturamento` try/except total (Task 3, `test_processar_nunca_levanta`). ✅
- D8 e-mail único com cópia → `enviar_email` (`to=1º`, `cc=demais`), `test_processar_envia_email_agrupado`. ✅
- Idempotência/segurança (§9), migration par (§10), testes (§11), docs (§12) → Tasks 1/3/5/6. ✅

**2. Placeholder scan:** nenhum TBD/TODO; todo passo com código/comando reais. ✅

**3. Type consistency:** `processar_alertas_faturamento(nfs_novas)`, `enviar_email(cnpj_cfg, nome, cnpj, linhas, total)`, `enviar_teams(config, texto)`, `registrar_envio(numero_nf, cnpj, canal, ok, detalhe)`, `montar_linhas -> (linhas, total)`, `lista_emails()`, `get_config()` — nomes idênticos entre definição (Task 2/3) e uso (Task 4/5). ✅
