<!-- doc:meta
tipo: how-to
camada: L1
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-26
-->
# CarVia Cotação Pública — Implementation Plan

> **Papel:** plano de implementação task-by-task da feature (remover tipo_carga/modalidade, tela pública `/cotacao`, persistência + listagem). Spec: `docs/superpowers/specs/2026-06-26-carvia-cotacao-publica-design.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remover `tipo_carga`/`modalidade` da Cotação Rápida (PDF e tela), criar uma tela de cotação pública `/cotacao` sem login que persiste cada cotação, e listar essas cotações no fim da Cotação Rápida com login.

**Architecture:** Reusa o motor `CotacaoRapidaService.cotar` e o LLM `extrair_motos_regiao` as-is. A tela pública é um blueprint isolado (`cotacao_publica_bp`, padrão de `portal_cliente.py`) montado na raiz `/cotacao`, registrado no `init_app` do CarVia. O JS das duas telas vira um único arquivo estático parametrizado por `data-*`. Persistência numa tabela nova `carvia_cotacoes_rapidas_publicas` via par migration SQL+Python (padrão CarVia, não Alembic).

**Tech Stack:** Python 3.12, Flask 3.1 + Flask-Login + Flask-WTF (CSRF), SQLAlchemy 2.0, Redis (`redis_cache` singleton), weasyprint (PDF), pytest.

## Global Constraints

- **R1 (CarVia isolado):** não importar de `app/fretes`, `app/carteira`, `app/financeiro`. Imports de outros módulos são LAZY (dentro de funções) — R2.
- **Campos de tabela** vêm dos schemas; modelos novos seguem o padrão de `app/carvia/models/cotacao.py`.
- **Timezone:** datas naive Brasil via `from app.utils.timezone import agora_brasil_naive`.
- **Migration = par DDL `.sql` + aplicador `.py`** em `scripts/migrations/` (idempotente, padrão `carvia_cce.py`). Head Alembic congelado em `7e880edbf40a` — não usar Alembic.
- **Testes:** fixtures `db` e `client` (raiz `tests/conftest.py`); `LOGIN_DISABLED=True` e `WTF_CSRF_ENABLED=False` no app de teste. Login simulado via `patch('flask_login.utils._get_user', return_value=_user())` quando preciso de usuário CarVia.
- **JSON de resposta:** sanitizar via `from app.utils.json_helpers import sanitize_for_json`.
- Não commitar/push sem o usuário pedir.

## Indice
- [Task 1: Migration (tabela carvia_cotacoes_rapidas_publicas)](#task-1-migration)
- [Task 2: Modelo CarviaCotacaoRapidaPublica + export](#task-2-modelo)
- [Task 3: Service registrar/listar cotações públicas](#task-3-service)
- [Task 4: Helper de rate-limit por IP (Redis)](#task-4-rate-limit)
- [Task 5: Extrair helpers comuns de rota](#task-5-helpers-comuns)
- [Task 6: Remover badges do PDF](#task-6-pdf)
- [Task 7: JS compartilhado + remover badges da tela](#task-7-js)
- [Task 8: Blueprint público /cotacao + template + persistência](#task-8-blueprint)
- [Task 9: Seção de cotações públicas na tela com login](#task-9-secao-logada)
- [Task 10: Documentação (CLAUDE.md do CarVia)](#task-10-docs)

---

<a id="task-1-migration"></a>
### Task 1: Migration (tabela `carvia_cotacoes_rapidas_publicas`)

**Files:**
- Create: `scripts/migrations/2026_06_26_criar_carvia_cotacoes_rapidas_publicas.sql`
- Create: `scripts/migrations/2026_06_26_criar_carvia_cotacoes_rapidas_publicas.py`

**Interfaces:**
- Produces: tabela `carvia_cotacoes_rapidas_publicas` no banco (colunas conforme spec Parte 3).

- [ ] **Step 1: Escrever o DDL idempotente**

Create `scripts/migrations/2026_06_26_criar_carvia_cotacoes_rapidas_publicas.sql`:

```sql
-- CarVia — Cotacao Rapida PUBLICA (tela sem login): snapshot persistido (lead).
CREATE TABLE IF NOT EXISTS carvia_cotacoes_rapidas_publicas (
    id                SERIAL PRIMARY KEY,
    solicitante_nome  VARCHAR(160) NOT NULL,
    cnpj_cliente      VARCHAR(20),
    uf_destino        VARCHAR(2) NOT NULL,
    cidade_destino    VARCHAR(120),
    codigo_ibge       VARCHAR(7),
    itens             JSONB NOT NULL,
    opcoes            JSONB NOT NULL,
    valor_total_min   NUMERIC(15, 2),
    qtd_total_motos   INTEGER,
    ip_solicitante    VARCHAR(45),
    user_agent        VARCHAR(255),
    criado_em         TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_carvia_cot_rap_pub_criado_em
    ON carvia_cotacoes_rapidas_publicas (criado_em DESC);
CREATE INDEX IF NOT EXISTS ix_carvia_cot_rap_pub_uf
    ON carvia_cotacoes_rapidas_publicas (uf_destino);
```

- [ ] **Step 2: Escrever o aplicador Python** (padrão `carvia_cce.py`)

Create `scripts/migrations/2026_06_26_criar_carvia_cotacoes_rapidas_publicas.py`:

```python
"""CarVia — cria carvia_cotacoes_rapidas_publicas (Cotacao Rapida da tela publica).

Aplica 2026_06_26_criar_carvia_cotacoes_rapidas_publicas.sql.
Idempotente; safe para re-execucao.
Executar: python scripts/migrations/2026_06_26_criar_carvia_cotacoes_rapidas_publicas.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text

TABELA = 'carvia_cotacoes_rapidas_publicas'


def _tabela_existe(nome):
    return db.session.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
        "WHERE table_name = :t)"
    ), {'t': nome}).scalar()


def run():
    app = create_app()
    with app.app_context():
        print(f'BEFORE: {TABELA}={_tabela_existe(TABELA)}')
        sql_path = os.path.join(
            os.path.dirname(__file__),
            '2026_06_26_criar_carvia_cotacoes_rapidas_publicas.sql',
        )
        with open(sql_path) as f:
            db.session.execute(text(f.read()))
        db.session.commit()
        existe = _tabela_existe(TABELA)
        print(f'AFTER: {TABELA}={existe}')
        if not existe:
            print('ERRO: tabela nao criada.')
            sys.exit(1)
        print('OK: migration concluida.')


if __name__ == '__main__':
    run()
```

- [ ] **Step 3: Aplicar no banco local** (é o banco usado pelos testes)

Run: `source .venv/bin/activate && python scripts/migrations/2026_06_26_criar_carvia_cotacoes_rapidas_publicas.py`
Expected: `AFTER: carvia_cotacoes_rapidas_publicas=True` + `OK: migration concluida.`

- [ ] **Step 4: Commit**

```bash
git add scripts/migrations/2026_06_26_criar_carvia_cotacoes_rapidas_publicas.sql scripts/migrations/2026_06_26_criar_carvia_cotacoes_rapidas_publicas.py
git commit -m "feat(carvia): tabela carvia_cotacoes_rapidas_publicas (cotacao publica)"
```

---

<a id="task-2-modelo"></a>
### Task 2: Modelo `CarviaCotacaoRapidaPublica` + export

**Files:**
- Modify: `app/carvia/models/cotacao.py` (append no fim do arquivo)
- Modify: `app/carvia/models/__init__.py` (import + `__all__`)
- Test: `tests/carvia/test_cotacao_publica.py`

**Interfaces:**
- Produces: `CarviaCotacaoRapidaPublica` (ORM) importável de `app.carvia.models`. Colunas: `id, solicitante_nome, cnpj_cliente, uf_destino, cidade_destino, codigo_ibge, itens, opcoes, valor_total_min, qtd_total_motos, ip_solicitante, user_agent, criado_em`.

- [ ] **Step 1: Escrever o teste do modelo**

Create `tests/carvia/test_cotacao_publica.py`:

```python
"""Cotacao Rapida PUBLICA (tela sem login): modelo, service, rotas, rate-limit."""
from decimal import Decimal


def test_modelo_persiste_e_le(db):
    from app.carvia.models import CarviaCotacaoRapidaPublica
    reg = CarviaCotacaoRapidaPublica(
        solicitante_nome='Fulano',
        uf_destino='RJ',
        cidade_destino='Rio de Janeiro',
        itens=[{'modelo_id': 1, 'quantidade': 2}],
        opcoes=[{'tabela_nome': 'T1', 'valor_total': 100.0}],
        valor_total_min=Decimal('100.00'),
        qtd_total_motos=2,
    )
    db.session.add(reg)
    db.session.commit()
    lido = CarviaCotacaoRapidaPublica.query.get(reg.id)
    assert lido.solicitante_nome == 'Fulano'
    assert lido.itens[0]['quantidade'] == 2
    assert lido.criado_em is not None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `source .venv/bin/activate && pytest tests/carvia/test_cotacao_publica.py::test_modelo_persiste_e_le -v`
Expected: FAIL com `ImportError: cannot import name 'CarviaCotacaoRapidaPublica'`.

- [ ] **Step 3: Adicionar o modelo** ao FIM de `app/carvia/models/cotacao.py`

```python
class CarviaCotacaoRapidaPublica(db.Model):
    """Cotacao Rapida feita na tela PUBLICA (sem login) — snapshot persistido (lead).

    Diferente de CarviaCotacao (fluxo comercial completo): aqui so guardamos o
    que o anonimo cotou (destino + motos + opcoes calculadas) + o nome informado,
    para o time CarVia ver os leads no fim da Cotacao Rapida com login.
    """
    __tablename__ = 'carvia_cotacoes_rapidas_publicas'

    id = db.Column(db.Integer, primary_key=True)
    solicitante_nome = db.Column(db.String(160), nullable=False)
    cnpj_cliente = db.Column(db.String(20), nullable=True)
    uf_destino = db.Column(db.String(2), nullable=False)
    cidade_destino = db.Column(db.String(120), nullable=True)
    codigo_ibge = db.Column(db.String(7), nullable=True)
    itens = db.Column(db.JSON, nullable=False)
    opcoes = db.Column(db.JSON, nullable=False)
    valor_total_min = db.Column(db.Numeric(15, 2), nullable=True)
    qtd_total_motos = db.Column(db.Integer, nullable=True)
    ip_solicitante = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=_agora_brasil_naive_default)

    def __repr__(self):
        return (f'<CarviaCotacaoRapidaPublica {self.id} '
                f'{self.solicitante_nome!r} {self.uf_destino}>')
```

E adicionar, perto do topo de `app/carvia/models/cotacao.py` (após os imports existentes), o default de data (lazy p/ evitar import circular no boot):

```python
def _agora_brasil_naive_default():
    from app.utils.timezone import agora_brasil_naive
    return agora_brasil_naive()
```

- [ ] **Step 4: Exportar em `app/carvia/models/__init__.py`**

No bloco `from app.carvia.models.cotacao import (...)` (linha ~66), adicionar `CarviaCotacaoRapidaPublica` à lista importada. E na lista `__all__` (linha ~132, seção `# Cotacao`), adicionar `'CarviaCotacaoRapidaPublica',`.

- [ ] **Step 5: Rodar e ver passar**

Run: `source .venv/bin/activate && pytest tests/carvia/test_cotacao_publica.py::test_modelo_persiste_e_le -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/carvia/models/cotacao.py app/carvia/models/__init__.py tests/carvia/test_cotacao_publica.py
git commit -m "feat(carvia): modelo CarviaCotacaoRapidaPublica"
```

---

<a id="task-3-service"></a>
### Task 3: Service registrar/listar cotações públicas

**Files:**
- Modify: `app/carvia/services/pricing/cotacao_rapida_service.py`
- Test: `tests/carvia/test_cotacao_publica.py`

**Interfaces:**
- Consumes: `CarviaCotacaoRapidaPublica` (Task 2); formato do retorno de `cotar()` (`{opcoes, itens, regiao{uf_destino,cidade_destino}}`).
- Produces:
  - `CotacaoRapidaService.registrar_cotacao_publica(resultado, *, solicitante_nome, cnpj_cliente=None, codigo_ibge=None, ip=None, user_agent=None) -> CarviaCotacaoRapidaPublica`
  - `CotacaoRapidaService.listar_cotacoes_publicas(limit=20) -> List[dict]` (dicts com `id, criado_em, solicitante_nome, cnpj_cliente, destino, uf_destino, cidade_destino, qtd_total_motos, valor_total_min, opcoes`).

- [ ] **Step 1: Escrever os testes do service**

Append em `tests/carvia/test_cotacao_publica.py`:

```python
def _resultado_fake():
    return {
        'ok': True,
        'opcoes': [
            {'tabela_nome': 'T1', 'valor_total': 250.0, 'modelos': [], 'lead_time': 3},
            {'tabela_nome': 'T2', 'valor_total': 180.0, 'modelos': [], 'lead_time': 5},
        ],
        'itens': [
            {'modelo_id': 1, 'modelo_nome': 'POP', 'categoria_nome': 'A', 'quantidade': 2},
            {'modelo_id': 2, 'modelo_nome': 'JET', 'categoria_nome': 'B', 'quantidade': 1},
        ],
        'regiao': {'uf_destino': 'RJ', 'cidade_destino': 'Rio de Janeiro'},
    }


def test_registrar_cotacao_publica_deriva_campos(db):
    from app.carvia.services.pricing.cotacao_rapida_service import CotacaoRapidaService
    reg = CotacaoRapidaService().registrar_cotacao_publica(
        _resultado_fake(), solicitante_nome='  Maria  ', codigo_ibge='3304557',
        ip='1.2.3.4', user_agent='UA')
    db.session.commit()
    assert reg.id is not None
    assert reg.solicitante_nome == 'Maria'           # strip
    assert reg.uf_destino == 'RJ'
    assert reg.codigo_ibge == '3304557'
    assert float(reg.valor_total_min) == 180.0        # menor das opcoes
    assert reg.qtd_total_motos == 3                   # 2 + 1


def test_listar_cotacoes_publicas_ordem_e_limite(db):
    from app.carvia.services.pricing.cotacao_rapida_service import CotacaoRapidaService
    svc = CotacaoRapidaService()
    for nome in ('A', 'B', 'C'):
        svc.registrar_cotacao_publica(_resultado_fake(), solicitante_nome=nome)
    db.session.commit()
    lista = svc.listar_cotacoes_publicas(limit=2)
    assert len(lista) == 2
    assert lista[0]['solicitante_nome'] == 'C'        # mais recente primeiro
    assert lista[0]['destino'] == 'Rio de Janeiro/RJ'
    assert lista[0]['valor_total_min'] == 180.0
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `source .venv/bin/activate && pytest tests/carvia/test_cotacao_publica.py -k "registrar or listar" -v`
Expected: FAIL com `AttributeError: 'CotacaoRapidaService' object has no attribute 'registrar_cotacao_publica'`.

- [ ] **Step 3: Implementar os métodos** no `CotacaoRapidaService` (após `historico_por_tabela`)

```python
    # ------------------------------------------------------------------ #
    # Persistencia da tela PUBLICA (sem login)
    # ------------------------------------------------------------------ #
    def registrar_cotacao_publica(self, resultado, *, solicitante_nome,
                                  cnpj_cliente=None, codigo_ibge=None,
                                  ip=None, user_agent=None):
        """Grava 1 snapshot da cotacao feita na tela publica. Retorna o registro.

        Chamar so quando `resultado['opcoes']`. NAO faz commit por si — o caller
        decide (a rota faz commit). Deriva valor_total_min/qtd_total_motos.
        """
        from app.carvia.models import CarviaCotacaoRapidaPublica

        opcoes = resultado.get('opcoes') or []
        itens = resultado.get('itens') or []
        regiao = resultado.get('regiao') or {}

        valores = [o.get('valor_total') for o in opcoes if o.get('valor_total') is not None]
        valor_total_min = min(valores) if valores else None
        qtd_total_motos = sum(int(i.get('quantidade') or 0) for i in itens) or None

        registro = CarviaCotacaoRapidaPublica(
            solicitante_nome=(solicitante_nome or '').strip()[:160],
            cnpj_cliente=(cnpj_cliente or None),
            uf_destino=(regiao.get('uf_destino') or '')[:2],
            cidade_destino=(regiao.get('cidade_destino') or None),
            codigo_ibge=(str(codigo_ibge)[:7] if codigo_ibge else None),
            itens=itens,
            opcoes=opcoes,
            valor_total_min=valor_total_min,
            qtd_total_motos=qtd_total_motos,
            ip_solicitante=(ip or None),
            user_agent=((user_agent or '')[:255] or None),
        )
        db.session.add(registro)
        db.session.flush()
        return registro

    def listar_cotacoes_publicas(self, limit: int = 20) -> List[Dict]:
        """Ultimas N cotacoes da tela publica (mais recentes primeiro)."""
        from app.carvia.models import CarviaCotacaoRapidaPublica

        regs = (
            CarviaCotacaoRapidaPublica.query
            .order_by(CarviaCotacaoRapidaPublica.criado_em.desc())
            .limit(limit)
            .all()
        )
        out = []
        for r in regs:
            destino = f"{r.cidade_destino}/{r.uf_destino}" if r.cidade_destino else r.uf_destino
            out.append({
                'id': r.id,
                'criado_em': r.criado_em,
                'solicitante_nome': r.solicitante_nome,
                'cnpj_cliente': r.cnpj_cliente,
                'destino': destino,
                'uf_destino': r.uf_destino,
                'cidade_destino': r.cidade_destino,
                'qtd_total_motos': r.qtd_total_motos,
                'valor_total_min': float(r.valor_total_min) if r.valor_total_min is not None else None,
                'opcoes': r.opcoes or [],
            })
        return out
```

- [ ] **Step 4: Rodar e ver passar**

Run: `source .venv/bin/activate && pytest tests/carvia/test_cotacao_publica.py -k "registrar or listar" -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Commit**

```bash
git add app/carvia/services/pricing/cotacao_rapida_service.py tests/carvia/test_cotacao_publica.py
git commit -m "feat(carvia): service registrar/listar cotacoes publicas"
```

---

<a id="task-4-rate-limit"></a>
### Task 4: Helper de rate-limit por IP (Redis)

**Files:**
- Create: `app/carvia/utils/rate_limit.py`
- Test: `tests/carvia/test_cotacao_publica.py`

**Interfaces:**
- Produces: `permitir(acao: str, ip: str, *, limite: int, janela_seg: int) -> bool` — `True` se ainda dentro do limite na janela; **degrada aberto** (retorna `True`) sem Redis/erro/ip vazio.

- [ ] **Step 1: Escrever os testes**

Append em `tests/carvia/test_cotacao_publica.py`:

```python
from unittest.mock import MagicMock, patch


def test_rate_limit_bloqueia_apos_limite():
    from app.carvia.utils import rate_limit
    fake = MagicMock()
    fake.incr.side_effect = [1, 2, 3]  # 3a chamada excede limite=2
    with patch.object(rate_limit, 'redis_cache') as rc:
        rc.client = fake
        assert rate_limit.permitir('upload', '9.9.9.9', limite=2, janela_seg=3600) is True
        assert rate_limit.permitir('upload', '9.9.9.9', limite=2, janela_seg=3600) is True
        assert rate_limit.permitir('upload', '9.9.9.9', limite=2, janela_seg=3600) is False
    fake.expire.assert_called_once()  # expire so na 1a (incr==1)


def test_rate_limit_degrada_aberto_sem_redis():
    from app.carvia.utils import rate_limit
    with patch.object(rate_limit, 'redis_cache') as rc:
        rc.client = None
        assert rate_limit.permitir('upload', '9.9.9.9', limite=1, janela_seg=60) is True
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `source .venv/bin/activate && pytest tests/carvia/test_cotacao_publica.py -k rate_limit -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.carvia.utils.rate_limit'`.

- [ ] **Step 3: Implementar o helper**

Create `app/carvia/utils/rate_limit.py`:

```python
"""Rate-limit leve por IP via Redis para a Cotacao Publica.

A tela publica expoe o upload LLM (custo API) e o calcular a anonimos. Este
helper limita N requisicoes por IP/janela. Degrada ABERTO: sem Redis, erro ou
IP vazio -> permite (nunca derruba a tela por causa do rate-limit)."""
import logging

from app.utils.redis_cache import redis_cache

logger = logging.getLogger(__name__)


def permitir(acao, ip, *, limite, janela_seg):
    """True se (acao, ip) ainda esta dentro do limite na janela. Degrada aberto."""
    if not ip:
        return True
    try:
        client = redis_cache.client
        if client is None:
            return True
        chave = f"carvia:ratelimit:{acao}:{ip}"
        atual = client.incr(chave)
        if atual == 1:
            client.expire(chave, janela_seg)
        return int(atual) <= limite
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[rate_limit] degradando aberto ({acao}): {e}")
        return True
```

- [ ] **Step 4: Rodar e ver passar**

Run: `source .venv/bin/activate && pytest tests/carvia/test_cotacao_publica.py -k rate_limit -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Commit**

```bash
git add app/carvia/utils/rate_limit.py tests/carvia/test_cotacao_publica.py
git commit -m "feat(carvia): helper rate-limit por IP (Redis, degrada aberto)"
```

---

<a id="task-5-helpers-comuns"></a>
### Task 5: Extrair helpers comuns de rota

**Files:**
- Create: `app/carvia/routes/cotacao_rapida_common.py`
- Modify: `app/carvia/routes/cotacao_rapida_routes.py`

**Interfaces:**
- Produces (módulo comum): `modelos_orm()`, `ufs_destino_disponiveis()`, `resolver_contexto(payload) -> dict` — mesma lógica hoje em `cotacao_rapida_routes.py` (`_modelos_orm`, `_ufs_destino_disponiveis`, `_resolver_contexto`), expostas como funções públicas (sem `_`).

- [ ] **Step 1: Criar o módulo comum** copiando os 3 helpers + a constante `UF_ORIGEM`

Create `app/carvia/routes/cotacao_rapida_common.py` com o conteúdo dos helpers hoje em `cotacao_rapida_routes.py` linhas 22 (`UF_ORIGEM`) e 177-241 (`_modelos_orm`, `_ufs_destino_disponiveis`, `_resolver_contexto`), renomeando para sem underscore:

```python
"""Helpers compartilhados entre a Cotacao Rapida (com login) e a Cotacao Publica.

Normalizacao do payload (itens + regiao + cnpj, resolvendo CEP) e catalogos.
Fonte unica — nao duplicar nas duas familias de rota."""
import logging

logger = logging.getLogger(__name__)

UF_ORIGEM = 'SP'


def modelos_orm():
    """Modelos ativos (ORM) com a categoria carregada — para LLM/normalizacao."""
    from sqlalchemy.orm import joinedload
    from app.carvia.models import CarviaModeloMoto
    return (
        CarviaModeloMoto.query
        .options(joinedload(CarviaModeloMoto.categoria))
        .filter_by(ativo=True)
        .order_by(CarviaModeloMoto.nome.asc())
        .all()
    )


def ufs_destino_disponiveis():
    """UFs de destino que tem alguma tabela CarVia ativa com origem SP."""
    from app import db
    from app.carvia.models import CarviaTabelaFrete
    rows = (
        db.session.query(CarviaTabelaFrete.uf_destino)
        .filter(
            CarviaTabelaFrete.uf_origem == UF_ORIGEM,
            CarviaTabelaFrete.ativo == True,  # noqa: E712
        )
        .distinct()
        .all()
    )
    return sorted({r[0] for r in rows if r[0]})


def resolver_contexto(payload):
    """Normaliza o payload (itens + regiao + cnpj), resolvendo CEP se preciso.

    Retorna `{itens, uf_destino, cidade_destino, codigo_ibge, cnpj_cliente}` ou
    `{erro}`."""
    itens = payload.get('itens') or []
    if not isinstance(itens, list) or not itens:
        return {'erro': 'Informe pelo menos uma moto + quantidade.'}

    uf_destino = (payload.get('uf_destino') or '').strip().upper()
    cidade_destino = (payload.get('cidade_destino') or '').strip() or None
    codigo_ibge = (str(payload.get('codigo_ibge') or '').strip() or None)
    cep = (payload.get('cep') or '').strip()

    if cep and (not uf_destino or not cidade_destino or not codigo_ibge):
        from app.utils.cep_service import resolver_cep
        dados_cep = resolver_cep(cep)
        if dados_cep:
            uf_destino = uf_destino or dados_cep['uf']
            cidade_destino = cidade_destino or dados_cep['cidade']
            codigo_ibge = codigo_ibge or dados_cep.get('codigo_ibge')

    if not uf_destino and not codigo_ibge:
        return {'erro': 'Informe a UF de destino (ou um CEP valido).'}

    return {
        'itens': itens,
        'uf_destino': uf_destino,
        'cidade_destino': cidade_destino,
        'codigo_ibge': codigo_ibge,
        'cnpj_cliente': (payload.get('cnpj_cliente') or '').strip() or None,
    }
```

- [ ] **Step 2: Reapontar `cotacao_rapida_routes.py` para o módulo comum**

Em `app/carvia/routes/cotacao_rapida_routes.py`: remover as definições locais de `UF_ORIGEM`, `_modelos_orm`, `_ufs_destino_disponiveis`, `_resolver_contexto` (linhas 22 e 177-241) e adicionar no topo:

```python
from app.carvia.routes.cotacao_rapida_common import (
    modelos_orm as _modelos_orm,
    ufs_destino_disponiveis as _ufs_destino_disponiveis,
    resolver_contexto as _resolver_contexto,
)
```

(Mantém os nomes `_modelos_orm`/`_ufs_destino_disponiveis`/`_resolver_contexto` usados no corpo das rotas — só passam a vir do módulo comum.)

- [ ] **Step 3: Smoke — a tela com login ainda renderiza**

Append em `tests/carvia/test_cotacao_publica.py`:

```python
def _user_carvia():
    u = MagicMock()
    u.is_authenticated = True
    u.sistema_carvia = True
    u.perfil = 'administrador'
    u.email = 'test@bot'
    return u


def test_cotacao_rapida_com_login_renderiza(db, client):
    with patch('flask_login.utils._get_user', return_value=_user_carvia()):
        assert client.get('/carvia/cotacao-rapida').status_code == 200
```

- [ ] **Step 4: Rodar**

Run: `source .venv/bin/activate && pytest tests/carvia/test_cotacao_publica.py::test_cotacao_rapida_com_login_renderiza -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/carvia/routes/cotacao_rapida_common.py app/carvia/routes/cotacao_rapida_routes.py tests/carvia/test_cotacao_publica.py
git commit -m "refactor(carvia): extrai helpers comuns da cotacao rapida"
```

---

<a id="task-6-pdf"></a>
### Task 6: Remover badges do PDF

**Files:**
- Modify: `app/templates/carvia/cotacao_rapida/imprimir_cotacao.html:81-82`

**Interfaces:**
- Produces: PDF sem `tipo_carga`/`modalidade` (mantém `grupo_cliente`).

- [ ] **Step 1: Remover as 2 linhas dos badges**

Em `imprimir_cotacao.html`, no bloco `<span class="cab">`, apagar exatamente:

```html
        <span class="badge">{{ op.tipo_carga }}</span>
        <span class="badge">{{ op.modalidade }}</span>
```

Mantendo `<span class="nome">{{ op.tabela_nome }}</span>` e o `{% if op.grupo_cliente %}...{% endif %}`.

- [ ] **Step 2: Verificar que o template não referencia mais os campos**

Run: `grep -nE "op\.(tipo_carga|modalidade)" app/templates/carvia/cotacao_rapida/imprimir_cotacao.html`
Expected: nenhuma saída (sem matches).

- [ ] **Step 3: Commit**

```bash
git add app/templates/carvia/cotacao_rapida/imprimir_cotacao.html
git commit -m "feat(carvia): remove tipo_carga/modalidade do PDF da cotacao"
```

---

<a id="task-7-js"></a>
### Task 7: JS compartilhado + remover badges da tela

**Files:**
- Create: `app/static/js/carvia/cotacao_rapida.js`
- Modify: `app/templates/carvia/cotacao_rapida/form.html` (substituir `<script>` inline por nó de config + `<script src>`)

**Interfaces:**
- Consumes: nó `#cr-app` com `data-endpoint-calcular`, `data-endpoint-upload`, `data-endpoint-pdf`, `data-endpoint-cep`, `data-modo`; nó `#cr-modelos-data` (JSON dos modelos); os mesmos ids de campo já usados (`cr-uf`, `cr-cidade`, `cr-cep`, `cr-cnpj`, `cr-cliente-nome`, `cr-motos`, etc.) e, no modo `publico`, `cr-solicitante-nome`.
- Produces: comportamento idêntico ao inline atual, **sem** badges `tipo_carga`/`modalidade`, com validação de nome no modo público.

- [ ] **Step 1: Criar o JS** movendo o IIFE atual (form.html linhas 102-403) para `app/static/js/carvia/cotacao_rapida.js` e aplicando 3 deltas.

**Delta A — ler config do `#cr-app`** (substitui o início do IIFE, onde hoje há `const MODELOS = ...; const csrf = ...;`):

```javascript
(function () {
  const APP = document.getElementById('cr-app');
  const CFG = {
    calcular: APP.dataset.endpointCalcular,
    upload: APP.dataset.endpointUpload,
    pdf: APP.dataset.endpointPdf,
    cep: APP.dataset.endpointCep,        // base; o CEP vai no path
    modo: APP.dataset.modo || 'login',   // 'login' | 'publico'
  };
  const MODELOS = JSON.parse(document.getElementById('cr-modelos-data').textContent || '[]');
  const csrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
  const fmtBRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
  const ultimaCotacao = { inputs: null };
```

Trocar os endpoints hardcoded pelos da CFG:
- `resolverCep()`: `fetch(\`${CFG.cep}/${cep}\`)` (era `/carvia/cotacao-rapida/cep/${cep}`).
- `enviarArquivo()`: `fetch(CFG.upload, {...})` (era `/carvia/cotacao-rapida/upload`).
- `calcular()`: `fetch(CFG.calcular, {...})` (era `/carvia/cotacao-rapida/calcular`).
- `emitirPdf()`: `fetch(CFG.pdf, {...})` (era `/carvia/cotacao-rapida/pdf`).

**Delta B — validação de nome (modo público)** em `montarPayload()` e `calcular()`:

```javascript
  function montarPayload() {
    const payload = {
      itens: coletarMotos(),
      uf_destino: ufSel.value,
      cidade_destino: cidadeInput.value.trim(),
      codigo_ibge: codigoIbgeSel || '',
      cep: document.getElementById('cr-cep').value.trim(),
      cnpj_cliente: document.getElementById('cr-cnpj').value.trim(),
      cliente_nome: document.getElementById('cr-cliente-nome').value.trim(),
    };
    if (CFG.modo === 'publico') {
      const nomeEl = document.getElementById('cr-solicitante-nome');
      payload.solicitante_nome = (nomeEl ? nomeEl.value.trim() : '');
    }
    return payload;
  }
```

E no início de `calcular()`, após montar o payload:

```javascript
    if (CFG.modo === 'publico' && !payload.solicitante_nome) {
      renderErro('Informe seu nome para cotar.');
      return;
    }
```

**Delta C — remover os 2 badges** no `render()` (linhas 313-314 atuais). Trocar o bloco do header da opção por:

```javascript
      html += `<div class="card-header d-flex justify-content-between align-items-center">
        <span><strong>${esc(op.tabela_nome)}</strong>
          ${op.grupo_cliente ? `<span class="badge bg-info ms-1">${esc(op.grupo_cliente)}</span>` : ''}
        </span>
        <span class="fs-5 text-primary fw-bold">${fmtBRL.format(op.valor_total || 0)}</span>
      </div>`;
```

(remove as duas linhas `<span class="badge bg-secondary ...">${esc(op.tipo_carga)}</span>` e `<span class="badge bg-light text-dark ...">${esc(op.modalidade)}</span>`.)

Todo o resto do IIFE é movido **verbatim**.

- [ ] **Step 2: Trocar o inline por config + script no `form.html` (logado)**

Em `app/templates/carvia/cotacao_rapida/form.html`, substituir o bloco `<script type="application/json" id="cr-modelos-data">...</script>` + `<script>(function () {...})();</script>` (linhas 100-404) por:

```html
<script type="application/json" id="cr-modelos-data">{{ modelos | tojson }}</script>
<div id="cr-app"
     data-modo="login"
     data-endpoint-calcular="{{ url_for('carvia.cotacao_rapida_calcular') }}"
     data-endpoint-upload="{{ url_for('carvia.cotacao_rapida_upload') }}"
     data-endpoint-pdf="{{ url_for('carvia.cotacao_rapida_pdf') }}"
     data-endpoint-cep="/carvia/cotacao-rapida/cep"></div>
<script src="{{ 'js/carvia/cotacao_rapida.js'|asset_url }}"></script>
```

- [ ] **Step 3: Smoke — tela com login renderiza e carrega o JS externo**

Append em `tests/carvia/test_cotacao_publica.py`:

```python
def test_form_login_usa_js_externo(db, client):
    with patch('flask_login.utils._get_user', return_value=_user_carvia()):
        html = client.get('/carvia/cotacao-rapida').get_data(as_text=True)
    assert 'js/carvia/cotacao_rapida.js' in html
    assert 'id="cr-app"' in html
```

- [ ] **Step 4: Rodar**

Run: `source .venv/bin/activate && pytest tests/carvia/test_cotacao_publica.py::test_form_login_usa_js_externo -v`
Expected: PASS.

- [ ] **Step 5: Verificar manualmente o JS no navegador** (a tela logada deve calcular/emitir PDF como antes)

Run: `source .venv/bin/activate && python run.py` e abrir `/carvia/cotacao-rapida`, calcular uma cotação e emitir o PDF. Conferir que não há erro no console e que os badges tipo_carga/modalidade sumiram.

- [ ] **Step 6: Commit**

```bash
git add app/static/js/carvia/cotacao_rapida.js app/templates/carvia/cotacao_rapida/form.html tests/carvia/test_cotacao_publica.py
git commit -m "refactor(carvia): JS compartilhado da cotacao + remove badges tipo_carga/modalidade da tela"
```

---

<a id="task-8-blueprint"></a>
### Task 8: Blueprint público `/cotacao` + template + persistência

**Files:**
- Create: `app/carvia/cotacao_publica.py`
- Create: `app/templates/carvia/cotacao_publica/form.html`
- Modify: `app/carvia/__init__.py` (registrar `cotacao_publica_bp` no `init_app`)
- Test: `tests/carvia/test_cotacao_publica.py`

**Interfaces:**
- Consumes: `resolver_contexto`/`modelos_orm`/`ufs_destino_disponiveis` (Task 5); `CotacaoRapidaService.cotar`/`registrar_cotacao_publica` (Task 3); `extrair_motos_regiao` (existente); `rate_limit.permitir` (Task 4); JS compartilhado (Task 7).
- Produces: blueprint `cotacao_publica_bp` (`url_prefix=/cotacao`) com `GET /`, `POST /calcular`, `POST /upload`, `POST /pdf`, `GET /cep/<cep>`.

- [ ] **Step 1: Escrever os testes da rota**

Append em `tests/carvia/test_cotacao_publica.py`:

```python
def test_cotacao_publica_get_sem_login(db, client):
    # Sem patch de usuario: rota publica responde 200 mesmo anonimo.
    assert client.get('/cotacao').status_code == 200


def test_cotacao_publica_calcular_exige_nome(db, client):
    r = client.post('/cotacao/calcular', json={'itens': [{'modelo_id': 1, 'quantidade': 1}],
                                               'uf_destino': 'RJ'})
    assert r.status_code == 400
    assert r.get_json()['ok'] is False


def test_cotacao_publica_calcular_persiste(db, client):
    from app.carvia.models import CarviaCotacaoRapidaPublica
    antes = CarviaCotacaoRapidaPublica.query.count()
    with patch('app.carvia.services.pricing.cotacao_rapida_service.CotacaoRapidaService.cotar',
               return_value=_resultado_fake()):
        r = client.post('/cotacao/calcular', json={
            'itens': [{'modelo_id': 1, 'quantidade': 2}],
            'uf_destino': 'RJ', 'solicitante_nome': 'Joao'})
    assert r.status_code == 200
    assert CarviaCotacaoRapidaPublica.query.count() == antes + 1


def test_cotacao_publica_sem_opcoes_nao_persiste(db, client):
    from app.carvia.models import CarviaCotacaoRapidaPublica
    vazio = {'ok': False, 'opcoes': [], 'itens': [], 'regiao': {'uf_destino': 'RJ', 'cidade_destino': None}}
    antes = CarviaCotacaoRapidaPublica.query.count()
    with patch('app.carvia.services.pricing.cotacao_rapida_service.CotacaoRapidaService.cotar',
               return_value=vazio):
        r = client.post('/cotacao/calcular', json={
            'itens': [{'modelo_id': 1, 'quantidade': 2}],
            'uf_destino': 'RJ', 'solicitante_nome': 'Joao'})
    assert r.status_code == 200
    assert CarviaCotacaoRapidaPublica.query.count() == antes


def test_cotacao_publica_rate_limit_429(db, client):
    with patch('app.carvia.cotacao_publica.permitir', return_value=False):
        r = client.post('/cotacao/calcular', json={
            'itens': [{'modelo_id': 1, 'quantidade': 1}],
            'uf_destino': 'RJ', 'solicitante_nome': 'Joao'})
    assert r.status_code == 429
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `source .venv/bin/activate && pytest tests/carvia/test_cotacao_publica.py -k cotacao_publica -v`
Expected: FAIL (404 nas rotas — blueprint ainda não existe).

- [ ] **Step 3: Implementar o blueprint**

Create `app/carvia/cotacao_publica.py`:

```python
"""Cotacao Rapida PUBLICA (tela SEM login) — blueprint isolado na raiz /cotacao.

Reusa o motor da Cotacao Rapida (CotacaoRapidaService) e o LLM, mas exige nome
do solicitante e PERSISTE cada calculo com opcoes (lead). Rate-limit por IP no
upload/calcular (LLM/custo exposto). Sem @login_required, sem guard sistema_carvia.
"""
import logging

from flask import Blueprint, render_template, request, jsonify, make_response

from app.carvia.utils.rate_limit import permitir
from app.carvia.routes.cotacao_rapida_common import (
    modelos_orm, ufs_destino_disponiveis, resolver_contexto,
)

logger = logging.getLogger(__name__)

cotacao_publica_bp = Blueprint(
    'cotacao_publica', __name__, url_prefix='/cotacao',
    template_folder='../templates/carvia',
)

LIMITE_UPLOAD = 20      # por IP / hora
LIMITE_CALCULAR = 60    # por IP / hora
JANELA = 3600


def _ip():
    fwd = request.headers.get('X-Forwarded-For', '')
    return (fwd.split(',')[0].strip() if fwd else request.remote_addr) or ''


@cotacao_publica_bp.route('')
@cotacao_publica_bp.route('/')
def cotacao_publica():
    from app.carvia.services.pricing.cotacao_rapida_service import CotacaoRapidaService
    return render_template(
        'carvia/cotacao_publica/form.html',
        modelos=CotacaoRapidaService().listar_modelos(),
        ufs_destino=ufs_destino_disponiveis(),
    )


@cotacao_publica_bp.route('/cep/<cep>')
def cotacao_publica_cep(cep):
    from app.utils.cep_service import resolver_cep
    dados = resolver_cep(cep)
    if not dados:
        return jsonify({'ok': False, 'erro': 'cep_nao_encontrado'}), 404
    return jsonify({'ok': True, **dados})


@cotacao_publica_bp.route('/upload', methods=['POST'])
def cotacao_publica_upload():
    if not permitir('upload', _ip(), limite=LIMITE_UPLOAD, janela_seg=JANELA):
        return jsonify({'ok': False, 'erro': 'Muitas requisicoes. Tente mais tarde.'}), 429

    arquivo = request.files.get('arquivo')
    if not arquivo or not arquivo.filename:
        return jsonify({'ok': False, 'erro': 'Nenhum arquivo enviado.'}), 400

    MAX_BYTES = 20 * 1024 * 1024
    if (request.content_length or 0) > MAX_BYTES:
        return jsonify({'ok': False, 'erro': 'Arquivo muito grande (max 20MB).'}), 413
    file_bytes = arquivo.read()
    if len(file_bytes) > MAX_BYTES:
        return jsonify({'ok': False, 'erro': 'Arquivo muito grande (max 20MB).'}), 413

    from app.carvia.services.parsers.cotacao_rapida_llm_service import (
        extrair_motos_regiao, CotacaoRapidaLlmError,
    )
    try:
        resultado = extrair_motos_regiao(
            file_bytes, arquivo.mimetype or '', modelos_orm(), filename=arquivo.filename)
    except CotacaoRapidaLlmError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 422
    except Exception as e:  # noqa: BLE001
        logger.exception('Erro inesperado no upload da Cotacao Publica')
        return jsonify({'ok': False, 'erro': f'Falha ao ler arquivo: {e}'}), 500
    return jsonify({'ok': True, **resultado})


@cotacao_publica_bp.route('/calcular', methods=['POST'])
def cotacao_publica_calcular():
    if not permitir('calcular', _ip(), limite=LIMITE_CALCULAR, janela_seg=JANELA):
        return jsonify({'ok': False, 'erro': 'Muitas requisicoes. Tente mais tarde.'}), 429

    payload = request.get_json(silent=True) or {}
    solicitante_nome = (payload.get('solicitante_nome') or '').strip()
    if not solicitante_nome:
        return jsonify({'ok': False, 'erro': 'Informe seu nome para cotar.'}), 400

    contexto = resolver_contexto(payload)
    if contexto.get('erro'):
        return jsonify({'ok': False, 'erro': contexto['erro']}), 400

    from app import db
    from app.carvia.services.pricing.cotacao_rapida_service import CotacaoRapidaService
    svc = CotacaoRapidaService()
    resultado = svc.cotar(
        itens=contexto['itens'], uf_destino=contexto['uf_destino'],
        cidade_destino=contexto['cidade_destino'], cnpj_cliente=contexto['cnpj_cliente'],
        codigo_ibge=contexto['codigo_ibge'],
    )

    if resultado.get('opcoes'):
        try:
            svc.registrar_cotacao_publica(
                resultado, solicitante_nome=solicitante_nome,
                cnpj_cliente=contexto['cnpj_cliente'], codigo_ibge=contexto['codigo_ibge'],
                ip=_ip(), user_agent=request.headers.get('User-Agent'))
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
            logger.exception('Falha ao persistir cotacao publica (cotacao devolvida mesmo assim)')

    from app.utils.json_helpers import sanitize_for_json
    return jsonify(sanitize_for_json(resultado))


@cotacao_publica_bp.route('/pdf', methods=['POST'])
def cotacao_publica_pdf():
    payload = request.get_json(silent=True) or {}
    contexto = resolver_contexto(payload)
    if contexto.get('erro'):
        return jsonify({'ok': False, 'erro': contexto['erro']}), 400

    from app.carvia.services.pricing.cotacao_rapida_service import CotacaoRapidaService
    resultado = CotacaoRapidaService().cotar(
        itens=contexto['itens'], uf_destino=contexto['uf_destino'],
        cidade_destino=contexto['cidade_destino'], cnpj_cliente=contexto['cnpj_cliente'],
        codigo_ibge=contexto['codigo_ibge'],
    )
    if not resultado.get('opcoes'):
        return jsonify({'ok': False, 'erro': 'Nada a cotar para gerar o PDF.'}), 400

    try:
        from app.utils.timezone import agora_brasil_naive
        cliente_nome = (payload.get('cliente_nome') or payload.get('solicitante_nome') or '').strip() or None
        html = render_template(
            'carvia/cotacao_rapida/imprimir_cotacao.html',
            resultado=resultado, destino=resultado['regiao'],
            cliente_nome=cliente_nome, emitido_em=agora_brasil_naive())
        from weasyprint import HTML
        pdf_bytes = HTML(string=html, base_url=request.host_url).write_pdf()
    except Exception as e:  # noqa: BLE001
        logger.exception('Falha ao gerar PDF da Cotacao Publica')
        return jsonify({'ok': False, 'erro': f'Falha ao gerar PDF: {e}'}), 500

    resp = make_response(pdf_bytes)
    resp.headers['Content-Type'] = 'application/pdf'
    resp.headers['Content-Disposition'] = 'attachment; filename=cotacao_carvia.pdf'
    return resp
```

- [ ] **Step 4: Registrar o blueprint** em `app/carvia/__init__.py` `init_app` (ao lado do `portal_cliente_bp`)

```python
    from app.carvia.cotacao_publica import cotacao_publica_bp
    if 'cotacao_publica' not in app.blueprints:
        app.register_blueprint(cotacao_publica_bp)
```

- [ ] **Step 5: Criar o template público** `app/templates/carvia/cotacao_publica/form.html`

Estende `base.html` (limpo p/ anônimo). Mesma estrutura de 2 colunas do form logado, **com**: (a) campo `cr-solicitante-nome` obrigatório no card de destino; (b) os MESMOS ids dos demais campos (para o JS compartilhado funcionar); (c) o nó `#cr-app` com `data-modo="publico"` e os endpoints `/cotacao/*`. Reusa o `#cr-motos`/`#cr-add-moto`/dropzone igual ao logado. Esqueleto:

```html
{% extends "base.html" %}
{% block content %}
<div class="container py-4" style="max-width: 1100px;">
  <div class="text-center mb-4">
    <h2><i class="fas fa-bolt text-warning"></i> CarVia — Cotação de Frete de Motos</h2>
    <p class="text-muted mb-0">Informe seu nome, o destino e as motos. Cotação na hora.</p>
  </div>

  <div class="row g-3">
    <div class="col-lg-5">
      <div class="card mb-3">
        <div class="card-header"><i class="fas fa-user"></i> Seus dados</div>
        <div class="card-body">
          <label class="form-label mb-1">Seu nome <span class="text-danger">*</span></label>
          <input id="cr-solicitante-nome" class="form-control" placeholder="Nome de quem está cotando" required>
        </div>
      </div>

      {# Card "1. Destino": copiar do form logado (mesmos ids cr-uf, cr-cidade,
         cr-cidades-list, cr-cep, cr-btn-cep, cr-cep-msg, cr-cnpj, cr-cliente-nome). #}
      {# Card "2. Motos": copiar do form logado (cr-dropzone, cr-file, cr-upload-msg,
         cr-motos, cr-add-moto). #}

      <div class="d-grid gap-2">
        <button type="button" class="btn btn-primary btn-lg" id="cr-calcular">
          <i class="fas fa-calculator"></i> Calcular Cotação
        </button>
      </div>
    </div>

    <div class="col-lg-7">
      <div id="cr-resultado">
        <div class="text-center text-muted py-5">
          <i class="fas fa-truck-fast fa-2x mb-2"></i>
          <p>Preencha os dados e clique em <strong>Calcular Cotação</strong>.</p>
        </div>
      </div>
    </div>
  </div>
</div>

<script type="application/json" id="cr-modelos-data">{{ modelos | tojson }}</script>
<div id="cr-app"
     data-modo="publico"
     data-endpoint-calcular="{{ url_for('cotacao_publica.cotacao_publica_calcular') }}"
     data-endpoint-upload="{{ url_for('cotacao_publica.cotacao_publica_upload') }}"
     data-endpoint-pdf="{{ url_for('cotacao_publica.cotacao_publica_pdf') }}"
     data-endpoint-cep="/cotacao/cep"></div>
<script src="{{ 'js/carvia/cotacao_rapida.js'|asset_url }}"></script>
{% endblock %}
```

(Copiar os cards "1. Destino" e "2. Motos" do `form.html` logado **verbatim** — mesmos ids — onde indicado pelos comentários.)

- [ ] **Step 6: Rodar os testes da rota**

Run: `source .venv/bin/activate && pytest tests/carvia/test_cotacao_publica.py -k cotacao_publica -v`
Expected: PASS (5 testes: get sem login, exige nome, persiste, sem-opções não persiste, rate-limit 429).

- [ ] **Step 7: Smoke manual** — abrir `/cotacao` anônimo (logout antes), calcular e emitir PDF.

Run: `source .venv/bin/activate && python run.py` → abrir `/cotacao` em aba anônima; cotar; verificar persistência (a cotação deve aparecer na Task 9).

- [ ] **Step 8: Commit**

```bash
git add app/carvia/cotacao_publica.py app/carvia/__init__.py app/templates/carvia/cotacao_publica/form.html tests/carvia/test_cotacao_publica.py
git commit -m "feat(carvia): tela publica /cotacao (sem login) + persistencia"
```

---

<a id="task-9-secao-logada"></a>
### Task 9: Seção de cotações públicas na tela com login

**Files:**
- Modify: `app/carvia/routes/cotacao_rapida_routes.py` (rota `cotacao_rapida` passa `cotacoes_publicas`)
- Modify: `app/templates/carvia/cotacao_rapida/form.html` (seção no final)
- Test: `tests/carvia/test_cotacao_publica.py`

**Interfaces:**
- Consumes: `CotacaoRapidaService.listar_cotacoes_publicas(20)` (Task 3).

- [ ] **Step 1: Passar `cotacoes_publicas` no render da rota logada**

Em `app/carvia/routes/cotacao_rapida_routes.py`, função `cotacao_rapida()`, alterar o `render_template` para incluir:

```python
        svc = CotacaoRapidaService()
        modelos = svc.listar_modelos()
        ufs = _ufs_destino_disponiveis()
        return render_template(
            'carvia/cotacao_rapida/form.html',
            modelos=modelos,
            ufs_destino=ufs,
            cotacoes_publicas=svc.listar_cotacoes_publicas(20),
        )
```

- [ ] **Step 2: Adicionar a seção no final do `form.html` logado** (antes do `</div>` do `container-fluid`, após a `row g-3`)

```html
  {% if cotacoes_publicas %}
  <hr class="my-4">
  <h5 class="text-muted"><i class="fas fa-globe"></i> Cotações da tela pública (sem login)</h5>
  <div class="table-responsive">
    <table class="table table-sm table-hover align-middle">
      <thead><tr class="text-muted">
        <th>Data</th><th>Solicitante</th><th>Destino</th>
        <th class="text-center">Motos</th><th class="text-end">Menor valor</th>
      </tr></thead>
      <tbody>
        {% for c in cotacoes_publicas %}
        <tr>
          <td>{{ c.criado_em | formatar_data_hora_brasil }}</td>
          <td>{{ c.solicitante_nome }}{% if c.cnpj_cliente %} <small class="text-muted">({{ c.cnpj_cliente }})</small>{% endif %}</td>
          <td>{{ c.destino }}</td>
          <td class="text-center">{{ c.qtd_total_motos or '—' }}</td>
          <td class="text-end">{% if c.valor_total_min is not none %}R$ {{ c.valor_total_min | valor_br }}{% else %}—{% endif %}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}
```

(Se `formatar_data_hora_brasil` não existir como filtro, usar `formatar_data_brasil` — confirmar em `app/utils/template_filters.py` no Step 3.)

- [ ] **Step 3: Confirmar o filtro de data existente**

Run: `grep -nE "formatar_data_hora_brasil|formatar_data_brasil|valor_br" app/utils/template_filters.py`
Expected: ver qual filtro existe; ajustar o template para usar um que exista.

- [ ] **Step 4: Teste — a seção aparece quando há cotação pública**

Append em `tests/carvia/test_cotacao_publica.py`:

```python
def test_secao_cotacoes_publicas_na_tela_logada(db, client):
    from app.carvia.services.pricing.cotacao_rapida_service import CotacaoRapidaService
    CotacaoRapidaService().registrar_cotacao_publica(_resultado_fake(), solicitante_nome='ZéPúblico')
    db.session.commit()
    with patch('flask_login.utils._get_user', return_value=_user_carvia()):
        html = client.get('/carvia/cotacao-rapida').get_data(as_text=True)
    assert 'Cotações da tela pública' in html
    assert 'ZéPúblico' in html
```

- [ ] **Step 5: Rodar**

Run: `source .venv/bin/activate && pytest tests/carvia/test_cotacao_publica.py::test_secao_cotacoes_publicas_na_tela_logada -v`
Expected: PASS.

- [ ] **Step 6: Rodar a suíte completa do arquivo**

Run: `source .venv/bin/activate && pytest tests/carvia/test_cotacao_publica.py -v`
Expected: todos PASS.

- [ ] **Step 7: Commit**

```bash
git add app/carvia/routes/cotacao_rapida_routes.py app/templates/carvia/cotacao_rapida/form.html tests/carvia/test_cotacao_publica.py
git commit -m "feat(carvia): lista cotacoes publicas no fim da cotacao rapida com login"
```

---

<a id="task-10-docs"></a>
### Task 10: Documentação (CLAUDE.md do CarVia)

**Files:**
- Modify: `app/carvia/CLAUDE.md`

**Interfaces:** nenhuma (doc).

- [ ] **Step 1: Registrar a feature** no `app/carvia/CLAUDE.md`

Adicionar uma entrada curta na seção apropriada (Estrutura/Regras) documentando:
- Tela pública `/cotacao` (blueprint isolado `cotacao_publica_bp`, sem login, rate-limit por IP no upload/calcular).
- Tabela `carvia_cotacoes_rapidas_publicas` (snapshot de lead; gravada ao calcular com opções).
- JS compartilhado `static/js/carvia/cotacao_rapida.js` (parametrizado por `#cr-app data-*`, usado pelas 2 telas).
- PDF/tela sem `tipo_carga`/`modalidade`.
- Atualizar a data "Atualizado" no header.

- [ ] **Step 2: Validar o doc no gate** (o pre-commit roda o artefato_lint)

Run: `source .venv/bin/activate && python -m scripts.audits.artefato_lint.checks_struct app/carvia/CLAUDE.md 2>/dev/null || echo "validar via pre-commit no Step 3"`

- [ ] **Step 3: Commit**

```bash
git add app/carvia/CLAUDE.md
git commit -m "docs(carvia): registra cotacao publica /cotacao + tabela + JS compartilhado"
```

---

## Self-Review

**Spec coverage:** Parte 1 → Task 6 (PDF) + Task 7 (tela). Parte 2 → Tasks 4,5,7,8. Parte 3 → Tasks 1,2,3 + persistência na Task 8. Parte 4 → Tasks 3,9. Migration → Task 1. Testes → distribuídos (Tasks 2-9). Docs → Task 10. Sem lacunas.

**Type consistency:** `registrar_cotacao_publica(resultado, *, solicitante_nome, cnpj_cliente, codigo_ibge, ip, user_agent)` e `listar_cotacoes_publicas(limit)` idênticos entre Task 3 (def), Task 8 (chamada) e Task 9 (chamada). Endpoints do JS (`CFG.calcular/upload/pdf/cep`) batem com os `data-*` dos dois templates. `permitir(acao, ip, *, limite, janela_seg)` idêntico entre Task 4 e Task 8.

**Placeholder scan:** os "copiar verbatim" (cards do form, IIFE do JS) referenciam linhas exatas do arquivo-fonte existente — não são TODOs, são instruções de movimentação com origem precisa.
