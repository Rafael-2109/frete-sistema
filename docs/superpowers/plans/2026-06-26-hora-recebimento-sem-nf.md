<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-26
-->
# HORA — Recebimento por filial sem NF (NF provisória) — Implementation Plan

> **Papel:** plano de implementação task-by-task do recebimento de motos selecionando só a loja (NF provisória + snapshot dos pedidos pendentes + anexar NF real depois).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** permitir criar um recebimento informando apenas a loja; a moto entra em estoque pela conferência cega; a NF real é anexada depois e promove a NF provisória a real.

**Architecture:** `hora_nf_entrada.tipo ∈ {PROVISORIA, REAL}` mantém `hora_recebimento.nf_id` NOT NULL (zero efeito-dominó). O gabarito da conferência é um snapshot congelado dos pedidos pendentes da filial em `hora_recebimento_esperado`. Conferência é SOT; a NF real, ao ser anexada, é gravada por cima e reprocessa divergências via `reprocessar_recebimentos_para_nf` (já existe).

**Tech Stack:** Flask 3.1 + SQLAlchemy 2.0 + Jinja2/Bootstrap 5; PostgreSQL; pytest (`tests/hora/`).

**Spec:** `docs/superpowers/specs/2026-06-26-hora-recebimento-sem-nf-design.md`.

## Global Constraints

- **Invariante HORA:** `hora_moto` é insert-once; estado via `hora_moto_evento` (nunca `UPDATE hora_moto.status`). Exceção SOT já existente: `_aplicar_correcao_moto_se_divergir` (cor/modelo).
- **Migrations duais** (regra `~/.claude/CLAUDE.md`): par `.sql` idempotente + `.py` espelho. Próxima = `hora_57`.
- **Testes:** PostgreSQL real, fixture `db` (SAVEPOINT) + `loja_factory`/`pedido_compra_factory`/`modelo_moto`. Services commitam fora do savepoint → **uuid em tudo unique** + `_db.session.expire_all()` após chamar service que commitou.
- **Rotas:** `@require_hora_perm('recebimentos', <acao>)`; `usuario_tem_acesso_a_loja(loja_id)`.

---

## Indice

- [File Structure](#file-structure)
- [Convenções do módulo (ler antes)](#convenções-do-módulo-ler-antes)
- [Task 1: Migration hora_57](#task-1-migration-hora_57)
- [Task 2: Modelos — tipo/provisoria + HoraRecebimentoEsperado](#task-2-modelos--tipoprovisoria--horarecebimentoesperado)
- [Task 3: criar_recebimento_sem_nf + snapshot](#task-3-criar_recebimento_sem_nf--snapshot)
- [Task 4: branches provisória na conferência/finalização](#task-4-branches-provisória-na-conferênciafinalização)
- [Task 5: anexar_nf_real_ao_recebimento](#task-5-anexar_nf_real_ao_recebimento)
- [Task 6: proteção de chassi provisório (R2)](#task-6-proteção-de-chassi-provisório-r2)
- [Task 7: rotas](#task-7-rotas)
- [Task 8: templates](#task-8-templates)
- [Task 9: isolamento fiscal + guard assert (R1)](#task-9-isolamento-fiscal--guard-assert-r1)
- [Task 10: docs](#task-10-docs)
- [Self-review](#self-review)

## File Structure

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `scripts/migrations/hora_57_recebimento_sem_nf.{sql,py}` | Criar | coluna `tipo` + tabela `hora_recebimento_esperado` |
| `app/hora/models/compra.py` | Modificar | `tipo` + property `provisoria` em `HoraNfEntrada` |
| `app/hora/models/recebimento.py` | Modificar | classe `HoraRecebimentoEsperado` |
| `app/hora/models/__init__.py` | Modificar | exportar `HoraRecebimentoEsperado` |
| `app/hora/services/recebimento_service.py` | Modificar | `criar_recebimento_sem_nf`, `_gabarito_provisorio`, branches, `anexar_nf_real_ao_recebimento` |
| `app/hora/services/chassi_protecao_service.py` | Modificar | cobrir conferência de recebimento |
| `app/hora/routes/recebimentos.py` | Modificar | `recebimentos_novo` sem NF + `recebimentos_anexar_nf` |
| `app/templates/hora/recebimento_novo.html` + wizard/lista/detalhe | Modificar | UI provisória |
| `tests/hora/test_recebimento_sem_nf.py` | Criar | cobertura TDD |
| `app/hora/CLAUDE.md` + `docs/hora/INVARIANTES.md` | Modificar | documentar |

## Convenções do módulo (ler antes)

- **Imports de teste** (`tests/hora/test_recebimento_reprocessamento.py:15-30`): `from app import db as _db`; `from app.hora.models import (...)`; `from app.hora.services import nf_entrada_service, recebimento_service`; `from app.hora.services.moto_service import registrar_evento, status_atual`.
- **Helpers de teste a copiar** (já existentes nos testes de recebimento): `_chassi(prefix)`, `_criar_modelo()`. Para pedido use a fixture `pedido_compra_factory(chassis)` (`tests/hora/conftest.py:101-134`).
- **Snapshot query** já existe: `matching_service.STATUS_CANDIDATOS` + `HoraPedido.query.filter(loja_destino_id==, status.in_(STATUS_CANDIDATOS))`.

---

### Task 1: Migration hora_57

**Files:**
- Create: `scripts/migrations/hora_57_recebimento_sem_nf.sql`
- Create: `scripts/migrations/hora_57_recebimento_sem_nf.py`

**Interfaces:**
- Produces: coluna `hora_nf_entrada.tipo`; tabela `hora_recebimento_esperado`.

- [ ] **Step 1: Escrever o `.sql`**

```sql
-- Migration HORA 57: Recebimento por filial sem NF (NF provisória).
-- Adiciona hora_nf_entrada.tipo {PROVISORIA,REAL} (default REAL p/ NFs existentes)
-- e a tabela de snapshot congelado hora_recebimento_esperado.
-- Idempotente — pode rodar 2x (IF NOT EXISTS).

ALTER TABLE hora_nf_entrada
    ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) NOT NULL DEFAULT 'REAL';

CREATE TABLE IF NOT EXISTS hora_recebimento_esperado (
    id                            SERIAL PRIMARY KEY,
    recebimento_id                INTEGER NOT NULL REFERENCES hora_recebimento (id),
    pedido_id                     INTEGER REFERENCES hora_pedido (id),
    pedido_item_id                INTEGER REFERENCES hora_pedido_item (id),
    modelo_id                     INTEGER REFERENCES hora_modelo (id),
    cor                           VARCHAR(50),
    chassi_esperado               VARCHAR(30),
    preco_esperado                NUMERIC(15, 2),
    consumido_por_conferencia_id  INTEGER REFERENCES hora_recebimento_conferencia (id),
    criado_em                     TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_hora_rec_esperado_rec ON hora_recebimento_esperado (recebimento_id);
CREATE INDEX IF NOT EXISTS ix_hora_rec_esperado_rec_modelo ON hora_recebimento_esperado (recebimento_id, modelo_id);
CREATE INDEX IF NOT EXISTS ix_hora_rec_esperado_rec_chassi ON hora_recebimento_esperado (recebimento_id, chassi_esperado);
```

- [ ] **Step 2: Escrever o `.py`** (template `hora_48`/`hora_53`)

```python
"""Migration HORA 57: Recebimento por filial sem NF (NF provisória).

Adiciona hora_nf_entrada.tipo {PROVISORIA,REAL} e cria hora_recebimento_esperado
(snapshot congelado dos pedidos pendentes da filial usado como gabarito).

Idempotente — pode rodar 2x (IF NOT EXISTS).

Uso:
    python scripts/migrations/hora_57_recebimento_sem_nf.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    "ALTER TABLE hora_nf_entrada ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) NOT NULL DEFAULT 'REAL'",
    """
    CREATE TABLE IF NOT EXISTS hora_recebimento_esperado (
        id                            SERIAL PRIMARY KEY,
        recebimento_id                INTEGER NOT NULL REFERENCES hora_recebimento (id),
        pedido_id                     INTEGER REFERENCES hora_pedido (id),
        pedido_item_id                INTEGER REFERENCES hora_pedido_item (id),
        modelo_id                     INTEGER REFERENCES hora_modelo (id),
        cor                           VARCHAR(50),
        chassi_esperado               VARCHAR(30),
        preco_esperado                NUMERIC(15, 2),
        consumido_por_conferencia_id  INTEGER REFERENCES hora_recebimento_conferencia (id),
        criado_em                     TIMESTAMP NOT NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_hora_rec_esperado_rec ON hora_recebimento_esperado (recebimento_id)",
    "CREATE INDEX IF NOT EXISTS ix_hora_rec_esperado_rec_modelo ON hora_recebimento_esperado (recebimento_id, modelo_id)",
    "CREATE INDEX IF NOT EXISTS ix_hora_rec_esperado_rec_chassi ON hora_recebimento_esperado (recebimento_id, chassi_esperado)",
]


def _colunas(tabela: str) -> list:
    return [c['name'] for c in inspect(db.engine).get_columns(tabela)]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        insp = inspect(db.engine)
        print('Estado antes:')
        print(f"  hora_nf_entrada.tipo existe? {'tipo' in _colunas('hora_nf_entrada')}")
        print(f"  hora_recebimento_esperado existe? {'hora_recebimento_esperado' in insp.get_table_names()}")

        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))

        insp = inspect(db.engine)
        ok_col = 'tipo' in _colunas('hora_nf_entrada')
        ok_tab = 'hora_recebimento_esperado' in insp.get_table_names()
        print('\nEstado depois:')
        print(f'  hora_nf_entrada.tipo existe? {ok_col}')
        print(f'  hora_recebimento_esperado existe? {ok_tab}')
        if not (ok_col and ok_tab):
            print('\nERRO: migration HORA 57 incompleta.')
            sys.exit(1)
        print('\nMigration HORA 57 concluida com sucesso.')


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Rodar a migration**

Run: `source .venv/bin/activate && python scripts/migrations/hora_57_recebimento_sem_nf.py`
Expected: "Migration HORA 57 concluida com sucesso."

- [ ] **Step 4: Commit**

```bash
git add scripts/migrations/hora_57_recebimento_sem_nf.sql scripts/migrations/hora_57_recebimento_sem_nf.py
git commit -m "feat(hora): migration hora_57 — tipo NF provisoria + hora_recebimento_esperado"
```

---

### Task 2: Modelos — tipo/provisoria + HoraRecebimentoEsperado

**Files:**
- Modify: `app/hora/models/compra.py` (classe `HoraNfEntrada`)
- Modify: `app/hora/models/recebimento.py`
- Modify: `app/hora/models/__init__.py`
- Test: `tests/hora/test_recebimento_sem_nf.py`

**Interfaces:**
- Produces: `HoraNfEntrada.tipo`, `HoraNfEntrada.provisoria` (property); `HoraRecebimentoEsperado`.

- [ ] **Step 1: Teste do modelo**

```python
# tests/hora/test_recebimento_sem_nf.py
import uuid
from datetime import date as _date
from app import db as _db
from app.hora.models import (
    HoraNfEntrada, HoraRecebimento, HoraRecebimentoEsperado, HoraMoto,
)
from app.hora.services import recebimento_service
from app.hora.services.moto_service import status_atual
from app.utils.timezone import agora_utc_naive


def _chassi(prefix: str) -> str:
    return f'{prefix}{uuid.uuid4().hex.upper()}'[:25].ljust(25, '0')


def test_nf_provisoria_property(db, loja_factory):
    loja = loja_factory()
    nf = HoraNfEntrada(
        chave_44='PROV' + uuid.uuid4().hex, numero_nf='PROV-1',
        cnpj_emitente='', cnpj_destinatario=loja.cnpj,
        loja_destino_id=loja.id, data_emissao=_date.today(),
        valor_total=0, tipo='PROVISORIA', criado_em=agora_utc_naive(),
    )
    _db.session.add(nf); _db.session.flush()
    assert nf.provisoria is True
    nf.tipo = 'REAL'
    assert nf.provisoria is False
```

- [ ] **Step 2: Rodar — falha** (`tipo`/`provisoria`/`HoraRecebimentoEsperado` inexistentes)

Run: `pytest tests/hora/test_recebimento_sem_nf.py::test_nf_provisoria_property -v`
Expected: FAIL (`AttributeError`/`ImportError`).

- [ ] **Step 3: Implementar no modelo**

Em `app/hora/models/compra.py`, classe `HoraNfEntrada`, após `criado_em`:
```python
    tipo = db.Column(db.String(20), nullable=False, server_default='REAL', default='REAL')
    # {'PROVISORIA','REAL'}. PROVISORIA = recebimento criado só com a loja
    # (gabarito vem de hora_recebimento_esperado). Promovida a REAL ao anexar a NF.

    @property
    def provisoria(self) -> bool:
        return self.tipo == 'PROVISORIA'
```

Em `app/hora/models/recebimento.py`, nova classe ao final:
```python
class HoraRecebimentoEsperado(db.Model):
    """Snapshot congelado de um item esperado da filial no momento do recebimento.

    Gabarito do recebimento PROVISORIO (sem NF): copia dos itens pendentes dos
    pedidos de compra ABERTO/PARCIAL da loja. `chassi_esperado` é NULL quando o
    pedido ainda não tinha chassi (pedido pré-NF). `consumido_por_conferencia_id`
    marca qual conferência casou este slot (chassi exato ou modelo fungível).
    """
    __tablename__ = 'hora_recebimento_esperado'

    id = db.Column(db.Integer, primary_key=True)
    recebimento_id = db.Column(db.Integer, db.ForeignKey('hora_recebimento.id'), nullable=False, index=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('hora_pedido.id'), nullable=True)
    pedido_item_id = db.Column(db.Integer, db.ForeignKey('hora_pedido_item.id'), nullable=True)
    modelo_id = db.Column(db.Integer, db.ForeignKey('hora_modelo.id'), nullable=True)
    cor = db.Column(db.String(50), nullable=True)
    chassi_esperado = db.Column(db.String(30), nullable=True)
    preco_esperado = db.Column(db.Numeric(15, 2), nullable=True)
    consumido_por_conferencia_id = db.Column(
        db.Integer, db.ForeignKey('hora_recebimento_conferencia.id'), nullable=True,
    )
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    recebimento = db.relationship('HoraRecebimento', backref='esperados')

    def __repr__(self):
        return f'<HoraRecebimentoEsperado rec={self.recebimento_id} modelo={self.modelo_id} chassi={self.chassi_esperado}>'
```

Em `app/hora/models/__init__.py`: adicionar `HoraRecebimentoEsperado` ao import de `recebimento` e ao `__all__`.

- [ ] **Step 4: Rodar — passa**

Run: `pytest tests/hora/test_recebimento_sem_nf.py::test_nf_provisoria_property -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/hora/models/ tests/hora/test_recebimento_sem_nf.py
git commit -m "feat(hora): modelo NF.tipo/provisoria + HoraRecebimentoEsperado"
```

---

### Task 3: criar_recebimento_sem_nf + snapshot

**Files:**
- Modify: `app/hora/services/recebimento_service.py`
- Test: `tests/hora/test_recebimento_sem_nf.py`

**Interfaces:**
- Consumes: `matching_service.STATUS_CANDIDATOS`; `iniciar_recebimento`.
- Produces: `criar_recebimento_sem_nf(loja_id, operador) -> HoraRecebimento`.

- [ ] **Step 1: Teste**

```python
def test_criar_recebimento_sem_nf_materializa_snapshot(db, loja_factory, pedido_compra_factory):
    from app.hora.models import HoraPedido
    chassi_a = _chassi('AAA')
    pedido = pedido_compra_factory([chassi_a])          # status ABERTO, loja = loja_origem
    loja_id = pedido.loja_destino_id

    rec = recebimento_service.criar_recebimento_sem_nf(loja_id=loja_id, operador='tester')
    _db.session.expire_all()

    nf = HoraNfEntrada.query.get(rec.nf_id)
    assert nf.provisoria is True
    esperados = HoraRecebimentoEsperado.query.filter_by(recebimento_id=rec.id).all()
    assert len(esperados) == 1
    assert esperados[0].chassi_esperado == chassi_a
    assert esperados[0].pedido_id == pedido.id
```

- [ ] **Step 2: Rodar — falha** (`criar_recebimento_sem_nf` inexistente)

Run: `pytest tests/hora/test_recebimento_sem_nf.py::test_criar_recebimento_sem_nf_materializa_snapshot -v`
Expected: FAIL (`AttributeError`).

- [ ] **Step 3: Implementar** (em `recebimento_service.py`)

```python
def criar_recebimento_sem_nf(loja_id: int, operador: Optional[str] = None) -> HoraRecebimento:
    """Cria um recebimento informando só a loja (sem NF).

    Cria uma NF PROVISORIA (container — mantém nf_id NOT NULL) e materializa o
    snapshot congelado dos pedidos pendentes da filial em hora_recebimento_esperado.
    """
    from app.hora.models import (
        HoraNfEntrada, HoraLoja, HoraPedido, HoraRecebimentoEsperado,
    )
    from app.hora.services.matching_service import STATUS_CANDIDATOS, _chassis_ja_faturados_no_pedido

    loja = HoraLoja.query.get(loja_id)
    if not loja:
        raise ValueError(f'Loja {loja_id} nao encontrada')

    nf = HoraNfEntrada(
        chave_44='PROV' + uuid.uuid4().hex,
        numero_nf='PROV',
        cnpj_emitente='',
        cnpj_destinatario=loja.cnpj,
        loja_destino_id=loja.id,
        data_emissao=agora_utc_naive().date(),
        valor_total=0,
        tipo='PROVISORIA',
    )
    db.session.add(nf)
    db.session.flush()
    nf.numero_nf = f'PROV-{nf.id}'

    rec = iniciar_recebimento(nf_id=nf.id, loja_id=loja.id, operador=operador)

    pedidos = (
        HoraPedido.query
        .filter(HoraPedido.loja_destino_id == loja.id,
                HoraPedido.status.in_(STATUS_CANDIDATOS))
        .all()
    )
    for pedido in pedidos:
        faturados = _chassis_ja_faturados_no_pedido(pedido.id)
        for item in pedido.itens:
            if item.is_peca:
                continue
            if item.numero_chassi and item.numero_chassi in faturados:
                continue
            db.session.add(HoraRecebimentoEsperado(
                recebimento_id=rec.id,
                pedido_id=pedido.id,
                pedido_item_id=item.id,
                modelo_id=item.modelo_id,
                cor=item.cor,
                chassi_esperado=item.numero_chassi,
                preco_esperado=item.preco_compra_esperado,
            ))
    db.session.commit()
    return rec
```

(Garantir `import uuid` no topo do módulo — adicionar se ausente.)

- [ ] **Step 4: Rodar — passa**

Run: `pytest tests/hora/test_recebimento_sem_nf.py::test_criar_recebimento_sem_nf_materializa_snapshot -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/hora/services/recebimento_service.py tests/hora/test_recebimento_sem_nf.py
git commit -m "feat(hora): criar_recebimento_sem_nf + snapshot dos pedidos pendentes da filial"
```

---

### Task 4: branches provisória na conferência/finalização

**Files:**
- Modify: `app/hora/services/recebimento_service.py` (`_garantir_moto`, `_redefinir_divergencias`, `finalizar_recebimento`, novo `_gabarito_provisorio`)
- Test: `tests/hora/test_recebimento_sem_nf.py`

**Interfaces:**
- Consumes: `criar_recebimento_sem_nf`, `definir_qtd_declarada`, `registrar_conferencia_cega`, `finalizar_recebimento`.
- Produces: `_gabarito_provisorio(rec, chassi, modelo_id)`; comportamento provisório das 3 funções.

- [ ] **Step 1: Teste — conferir casando snapshot, chassi-extra, sem MOTO_FALTANDO**

```python
def test_conferencia_provisoria_casa_modelo_e_chassi_extra(db, loja_factory, pedido_compra_factory, modelo_moto):
    chassi_ped = _chassi('PED')           # item do pedido COM chassi
    pedido = pedido_compra_factory([chassi_ped])
    loja_id = pedido.loja_destino_id
    rec = recebimento_service.criar_recebimento_sem_nf(loja_id=loja_id, operador='tester')
    recebimento_service.definir_qtd_declarada(recebimento_id=rec.id, qtd=2, usuario='tester')

    # (a) chassi do snapshot -> RECEBIDA/CONFERIDA, sem CHASSI_EXTRA
    recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi_ped,
        modelo_id_conferido=modelo_moto.id, cor_conferida='PRETA',
        avaria_fisica=False, qr_code_lido=True, operador='tester',
    )
    # (b) chassi fora do snapshot -> CHASSI_EXTRA, sem bloquear
    chassi_extra = _chassi('EXT')
    recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi_extra,
        modelo_id_conferido=modelo_moto.id, cor_conferida='PRETA',
        avaria_fisica=False, qr_code_lido=True, operador='tester',
    )
    _db.session.expire_all()
    assert status_atual(chassi_ped) in ('RECEBIDA', 'CONFERIDA')
    assert HoraMoto.query.get(chassi_ped) is not None
    conf_extra = next(c for c in rec.conferencias if c.numero_chassi == chassi_extra)
    assert any(d.tipo == 'CHASSI_EXTRA' for d in conf_extra.divergencias)

    rec = recebimento_service.finalizar_recebimento(recebimento_id=rec.id, operador='tester')
    _db.session.expire_all()
    # D8: provisorio NAO gera MOTO_FALTANDO
    faltando = [c for c in rec.conferencias if c.tipo_divergencia == 'MOTO_FALTANDO']
    assert faltando == []
```

- [ ] **Step 2: Rodar — falha** (sem snapshot, tudo vira CHASSI_EXTRA e `_garantir_moto` usa sentinela; finalizar tenta `rec.nf.itens_considerados` vazio)

Run: `pytest tests/hora/test_recebimento_sem_nf.py::test_conferencia_provisoria_casa_modelo_e_chassi_extra -v`
Expected: FAIL.

- [ ] **Step 3: Implementar branches**

`_gabarito_provisorio` (novo):
```python
def _gabarito_provisorio(rec, chassi: str, modelo_id_conf: Optional[int]):
    """Casa um chassi conferido contra o snapshot (hora_recebimento_esperado).

    Retorna o HoraRecebimentoEsperado consumido ou None. NAO toca HoraPedidoItem
    (D6 — quem atribui chassi ao pedido e a NF real).
    """
    from app.hora.models import HoraRecebimentoEsperado
    chassi = (chassi or '').strip().upper()
    base = HoraRecebimentoEsperado.query.filter_by(recebimento_id=rec.id, consumido_por_conferencia_id=None)
    exato = base.filter(HoraRecebimentoEsperado.chassi_esperado == chassi).first()
    if exato:
        return exato
    if modelo_id_conf:
        return base.filter(HoraRecebimentoEsperado.chassi_esperado.is_(None),
                           HoraRecebimentoEsperado.modelo_id == modelo_id_conf).first()
    return None
```

`_garantir_moto` (`:1701`) — antes do branch `if item_nf:`, tratar provisório:
```python
def _garantir_moto(chassi, item_nf, operador, *, modelo_id_conf=None, cor_conf=None):
    if HoraMoto.query.get(chassi):
        return
    from app.hora.services.moto_service import get_or_create_moto
    from app.hora.models import PENDENTE_ORIGEM_RECEBIMENTO, HoraModelo
    if item_nf:
        ...  # bloco existente inalterado
        return
    if modelo_id_conf:   # recebimento provisorio: usa o que o operador declarou
        modelo = HoraModelo.query.get(modelo_id_conf)
        get_or_create_moto(
            numero_chassi=chassi,
            modelo_nome=modelo.nome_modelo if modelo else None,
            cor=(cor_conf or 'NAO_INFORMADA'),
            criado_por=operador, origem_pendencia=PENDENTE_ORIGEM_RECEBIMENTO,
            fallback_sentinela=True,
        )
        return
    ...  # bloco CHASSI_EXTRA_DESCONHECIDO existente (fallback)
```
E em `registrar_conferencia_cega` (`:357-360`), passar `modelo_id_conf`/`cor_conf` ao `_garantir_moto` quando `rec.nf.provisoria`.

`_redefinir_divergencias` (`:1766`) — no topo, antes de buscar `item_nf`:
```python
    if rec.nf.provisoria:
        for d in list(conf.divergencias):
            db.session.delete(d)
        db.session.flush()
        slot = _gabarito_provisorio(rec, conf.numero_chassi, conf.modelo_id_conferido)
        snapshot = None
        if slot is None:
            db.session.add(HoraConferenciaDivergencia(
                conferencia_id=conf.id, tipo='CHASSI_EXTRA', detalhe='Fora dos pedidos pendentes da filial'))
            snapshot = 'CHASSI_EXTRA'
        else:
            slot.consumido_por_conferencia_id = conf.id
        if conf.avaria_fisica:
            db.session.add(HoraConferenciaDivergencia(
                conferencia_id=conf.id, tipo='AVARIA_FISICA', detalhe='Marcado pelo operador no wizard'))
            snapshot = snapshot or 'AVARIA_FISICA'
        conf.tipo_divergencia = snapshot
        conf.detalhe_divergencia = None
        db.session.flush()
        return
```

`finalizar_recebimento` (`:506`) — após carregar `rec` e descartar parciais, guardar o bloco MOTO_FALTANDO:
```python
    if rec.nf.provisoria:
        chassis_nf = set()          # D8: sem gabarito fechado -> sem faltantes
    else:
        ignorar_norm = {...}        # bloco existente
        chassis_nf = {...}
```
(O resto — cálculo de `houve_divergencia` e status — segue igual; com `chassis_nf` vazio não há faltantes.)

- [ ] **Step 4: Rodar — passa**

Run: `pytest tests/hora/test_recebimento_sem_nf.py::test_conferencia_provisoria_casa_modelo_e_chassi_extra -v`
Expected: PASS.

- [ ] **Step 5: Regressão recebimento normal**

Run: `pytest tests/hora/test_recebimento_reprocessamento.py tests/hora/test_recebimento_automatico_blindagem.py -v`
Expected: PASS (NF real continua derivando MOTO_FALTANDO/CHASSI_EXTRA como antes).

- [ ] **Step 6: Commit**

```bash
git add app/hora/services/recebimento_service.py tests/hora/test_recebimento_sem_nf.py
git commit -m "feat(hora): conferencia provisoria casa snapshot; sem MOTO_FALTANDO no fechamento"
```

---

### Task 5: anexar_nf_real_ao_recebimento

**Files:**
- Modify: `app/hora/services/recebimento_service.py`
- Test: `tests/hora/test_recebimento_sem_nf.py`

**Interfaces:**
- Consumes: parser DANFE `parse_danfe_to_hora_payload`; `get_or_create_moto`; `reprocessar_recebimentos_para_nf`; `matching_service.atualizar_status_pedido_por_faturamento`.
- Produces: `anexar_nf_real_ao_recebimento(recebimento_id, pdf_bytes, operador, payload=None) -> HoraNfEntrada`.

> **Nota de teste:** parsear PDF real é caro; teste a **promoção** injetando o payload via o parâmetro opcional `payload=` (default `None` → parseia `pdf_bytes`). Assim o teste passa um dict e não depende de PDF.

- [ ] **Step 1: Teste**

```python
def test_anexar_nf_real_promove_e_reprocessa(db, loja_factory, pedido_compra_factory, modelo_moto):
    chassi = _chassi('REAL')
    pedido = pedido_compra_factory([chassi])
    loja_id = pedido.loja_destino_id
    rec = recebimento_service.criar_recebimento_sem_nf(loja_id=loja_id, operador='tester')
    recebimento_service.definir_qtd_declarada(recebimento_id=rec.id, qtd=1, usuario='tester')
    recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi,
        modelo_id_conferido=modelo_moto.id, cor_conferida='PRETA',
        avaria_fisica=False, qr_code_lido=True, operador='tester')
    recebimento_service.finalizar_recebimento(recebimento_id=rec.id, operador='tester')

    payload = {
        'nf': {'chave_44': uuid.uuid4().hex.zfill(44), 'numero_nf': '12345',
               'cnpj_emitente': '12345678000199', 'cnpj_destinatario': '00000000000000',
               'data_emissao': _date.today(), 'valor_total': 5000},
        'itens': [{'numero_chassi': chassi, 'preco_real': 5000,
                   'modelo_texto_original': modelo_moto.nome_modelo, 'cor_texto_original': 'PRETA'}],
    }
    nf = recebimento_service.anexar_nf_real_ao_recebimento(
        recebimento_id=rec.id, pdf_bytes=b'', operador='tester', payload=payload)
    _db.session.expire_all()
    assert nf.tipo == 'REAL'
    assert nf.numero_nf == '12345'
    from app.hora.models import HoraNfEntradaItem
    assert HoraNfEntradaItem.query.filter_by(nf_id=nf.id, numero_chassi=chassi).count() == 1
```

- [ ] **Step 2: Rodar — falha**

Run: `pytest tests/hora/test_recebimento_sem_nf.py::test_anexar_nf_real_promove_e_reprocessa -v`
Expected: FAIL (`AttributeError`).

- [ ] **Step 3: Implementar**

```python
def anexar_nf_real_ao_recebimento(recebimento_id, pdf_bytes, operador=None, payload=None) -> HoraNfEntrada:
    """Grava a NF real por cima da provisoria do recebimento (PROVISORIA -> REAL)."""
    from app.hora.models import HoraNfEntrada, HoraNfEntradaItem, PENDENTE_ORIGEM_NF_ENTRADA
    from app.hora.services.moto_service import get_or_create_moto
    rec = HoraRecebimento.query.get(recebimento_id)
    if not rec:
        raise ValueError(f'Recebimento {recebimento_id} nao encontrado')
    nf = rec.nf
    if not nf.provisoria:
        raise ValueError('Recebimento ja tem NF real anexada')

    if payload is None:
        from app.hora.services.nf_entrada_service import parse_danfe_to_hora_payload
        payload = parse_danfe_to_hora_payload(pdf_bytes)
    nf_data, itens_data = payload['nf'], payload['itens']

    dup = HoraNfEntrada.query.filter(
        HoraNfEntrada.chave_44 == nf_data['chave_44'], HoraNfEntrada.id != nf.id).first()
    if dup:
        raise ValueError(f"NF {nf_data['chave_44']} ja importada (id={dup.id})")

    nf.tipo = 'REAL'
    nf.chave_44 = nf_data['chave_44']
    nf.numero_nf = nf_data['numero_nf']
    nf.cnpj_emitente = nf_data.get('cnpj_emitente') or ''
    nf.nome_emitente = nf_data.get('nome_emitente')
    nf.data_emissao = nf_data.get('data_emissao') or nf.data_emissao
    nf.valor_total = nf_data.get('valor_total') or 0
    nf.parseada_em = agora_utc_naive()
    db.session.flush()

    for item in itens_data:
        moto = get_or_create_moto(
            numero_chassi=item['numero_chassi'],
            modelo_nome=item.get('modelo_texto_original'),
            cor=item.get('cor_texto_original') or 'NAO_INFORMADA',
            criado_por=operador, origem_pendencia=PENDENTE_ORIGEM_NF_ENTRADA,
            origem_id=nf.id, fallback_sentinela=True,
        )
        db.session.add(HoraNfEntradaItem(
            nf_id=nf.id, numero_chassi=moto.numero_chassi, preco_real=item['preco_real'],
            modelo_texto_original=item.get('modelo_texto_original'),
            cor_texto_original=item.get('cor_texto_original'),
        ))
    db.session.commit()

    reprocessar_recebimentos_para_nf(nf.id)        # reavalia divergencias conferido x NF real
    if nf.pedido_id:
        from app.hora.services.matching_service import atualizar_status_pedido_por_faturamento
        atualizar_status_pedido_por_faturamento(nf.pedido_id)
    return nf
```

- [ ] **Step 4: Rodar — passa**

Run: `pytest tests/hora/test_recebimento_sem_nf.py::test_anexar_nf_real_promove_e_reprocessa -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/hora/services/recebimento_service.py tests/hora/test_recebimento_sem_nf.py
git commit -m "feat(hora): anexar_nf_real_ao_recebimento — promove provisoria e reprocessa"
```

---

### Task 6: proteção de chassi provisório (R2)

**Files:**
- Modify: `app/hora/services/chassi_protecao_service.py`
- Test: `tests/hora/test_chassi_protecao.py` (já existe — adicionar caso)

- [ ] **Step 1: Teste** — moto só com conferência de recebimento ativa é protegida.

```python
def test_chassi_protegido_por_conferencia_recebimento(db, loja_factory, pedido_compra_factory, modelo_moto):
    from app.hora.services.chassi_protecao_service import chassi_protegido
    from app.hora.services import recebimento_service
    import uuid as _uuid
    chassi = ('CONF' + _uuid.uuid4().hex.upper())[:25].ljust(25, '0')
    pedido = pedido_compra_factory([chassi])
    rec = recebimento_service.criar_recebimento_sem_nf(loja_id=pedido.loja_destino_id, operador='t')
    recebimento_service.definir_qtd_declarada(recebimento_id=rec.id, qtd=1, usuario='t')
    recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi, modelo_id_conferido=modelo_moto.id,
        cor_conferida='PRETA', avaria_fisica=False, qr_code_lido=True, operador='t')
    from app import db as _db
    _db.session.expire_all()
    assert chassi_protegido(chassi) is True
```

- [ ] **Step 2: Rodar — falha** (hoje só protege pedido-com-chassi/NF-item).

Run: `pytest tests/hora/test_chassi_protecao.py::test_chassi_protegido_por_conferencia_recebimento -v`
Expected: FAIL.

- [ ] **Step 3: Implementar** — em `chassi_protegido`, adicionar à condição:
```python
    from app.hora.models import HoraRecebimentoConferencia
    tem_conferencia = db.session.query(HoraRecebimentoConferencia.id).filter_by(
        numero_chassi=chassi, substituida=False).first() is not None
    return tem_pedido or tem_nf or tem_conferencia
```

- [ ] **Step 4: Rodar — passa**

Run: `pytest tests/hora/test_chassi_protecao.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/hora/services/chassi_protecao_service.py tests/hora/test_chassi_protecao.py
git commit -m "fix(hora): proteger chassi com conferencia de recebimento ativa (R2)"
```

---

### Task 7: rotas

**Files:**
- Modify: `app/hora/routes/recebimentos.py`

- [ ] **Step 1: `recebimentos_novo`** — POST sem NF, GET sem autocomplete:
```python
    if request.method == 'POST':
        try:
            loja_id = int(request.form['loja_id'])
            if not usuario_tem_acesso_a_loja(loja_id):
                flash('Acesso negado a essa loja.', 'danger')
                return redirect(url_for('hora.recebimentos_novo'))
            rec = recebimento_service.criar_recebimento_sem_nf(loja_id=loja_id, operador=_op_name())
            return redirect(url_for('hora.recebimentos_qtd', recebimento_id=rec.id))
        except (ValueError, KeyError) as exc:
            flash(f'Erro: {exc}', 'danger')
```

- [ ] **Step 2: nova rota `recebimentos_anexar_nf`**:
```python
@hora_bp.route('/recebimentos/<int:recebimento_id>/anexar-nf', methods=['POST'])
@require_hora_perm('recebimentos', 'editar')
def recebimentos_anexar_nf(recebimento_id: int):
    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if not usuario_tem_acesso_a_loja(rec.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.recebimentos_lista'))
    arquivo = request.files.get('pdf')
    if not arquivo:
        flash('Envie o PDF da NF.', 'danger')
        return redirect(url_for('hora.recebimentos_detalhe', recebimento_id=rec.id))
    try:
        recebimento_service.anexar_nf_real_ao_recebimento(
            recebimento_id=rec.id, pdf_bytes=arquivo.read(), operador=_op_name())
        flash('NF real anexada e recebimento reprocessado.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.recebimentos_detalhe', recebimento_id=rec.id))
```

- [ ] **Step 3: `recebimentos_wizard`** — proteger `rec.nf.itens` quando provisória (`:193-199`):
```python
    cores = set()
    if rec.nf.provisoria:
        for e in rec.esperados:
            if e.cor:
                cores.add(e.cor.strip().upper())
    else:
        for i in rec.nf.itens:
            if i.cor_texto_original:
                cores.add(i.cor_texto_original.strip().upper())
        if rec.nf.pedido_id and rec.nf.pedido:
            for pi in rec.nf.pedido.itens:
                if pi.cor:
                    cores.add(pi.cor.strip().upper())
```

- [ ] **Step 4: Smoke** — subir app e abrir a tela de novo recebimento.

Run: `source .venv/bin/activate && python -c "from app import create_app; c=create_app().test_client(); print(c.get('/hora/recebimentos/novo').status_code)"`
Expected: sem exceção de import/rota (status 200/302/401 conforme auth).

- [ ] **Step 5: Commit**

```bash
git add app/hora/routes/recebimentos.py
git commit -m "feat(hora): rota recebimento sem NF + anexar NF real; wizard guarda provisoria"
```

---

### Task 8: templates

**Files:**
- Modify: `recebimento_novo.html`, `recebimento_wizard.html`, `recebimentos_lista.html`, `recebimento_detalhe.html`

- [ ] **Step 1: `recebimento_novo.html`** — remover o bloco `#nf-upload-area` (linhas 6-27) e o `<script>` de validação de NF (49-80). Manter só o select de loja + submit. Trocar o texto do botão para "Iniciar recebimento".

- [ ] **Step 2: `recebimentos_lista.html:61`** — badge provisória:
```jinja
<td>{% if r.nf.provisoria %}<span class="badge bg-warning text-dark">Provisória</span>{% else %}{{ r.nf.numero_nf }}{% endif %}</td>
```

- [ ] **Step 3: `recebimento_detalhe.html:56-60`** — KPI NF sem link quando provisória:
```jinja
    <div>
      {% if recebimento.nf.provisoria %}
        <span class="badge bg-warning text-dark">Provisória</span>
      {% elif pode_ver_resumo_completo %}
        <a href="{{ url_for('hora.nfs_detalhe', nf_id=recebimento.nf_id) }}">{{ recebimento.nf.numero_nf }}</a>
      {% else %}
        {{ recebimento.nf.numero_nf }}
      {% endif %}
    </div>
```
E esconder KPI "Esperado NF" (71-76) quando `recebimento.nf.provisoria`. Adicionar bloco "Anexar NF real" (form POST `recebimentos_anexar_nf`, `enctype=multipart/form-data`, input file `pdf`) visível só quando provisória.

- [ ] **Step 4: `recebimento_wizard.html:235`** — título do modal com badge provisória.

- [ ] **Step 5: Verificação visual** — `/run` o app, abrir a tela de novo recebimento e um recebimento provisório; confirmar badge + form de anexar.

- [ ] **Step 6: Commit**

```bash
git add app/templates/hora/recebimento_novo.html app/templates/hora/recebimento_wizard.html app/templates/hora/recebimentos_lista.html app/templates/hora/recebimento_detalhe.html
git commit -m "feat(hora): UI recebimento sem NF (badge provisoria + anexar NF real)"
```

---

### Task 9: isolamento fiscal + guard assert (R1)

**Files:**
- Modify: `app/hora/services/autocomplete_service.py` e/ou onde se some valor de NF de entrada; `app/hora/services/nf_entrada_service.py:255` (`assert_item_moto_consistente`)
- Test: `tests/hora/test_recebimento_sem_nf.py`

- [ ] **Step 1: Teste** — NF provisória não aparece em listagens de NF importável nem soma valor.

```python
def test_nf_provisoria_isolada_de_listas_de_nf(db, loja_factory, pedido_compra_factory):
    from app.hora.services import autocomplete_service
    pedido = pedido_compra_factory([_chassi('ISO')])
    rec = recebimento_service.criar_recebimento_sem_nf(loja_id=pedido.loja_destino_id, operador='t')
    _db.session.expire_all()
    # autocomplete de NFs (sem_recebimento) nunca traz provisoria (ela ja tem recebimento)
    res = autocomplete_service.nfs_entrada('PROV', lojas_permitidas_ids=None, sem_recebimento=True)
    assert all(not (r['numero_nf'] or '').startswith('PROV') for r in res)
```

- [ ] **Step 2: Rodar** — confirmar comportamento (já protegido por `~recebimentos.any()`; o teste documenta a invariante).

Run: `pytest tests/hora/test_recebimento_sem_nf.py::test_nf_provisoria_isolada_de_listas_de_nf -v`
Expected: PASS (ou ajustar `nfs_entrada` para filtrar `HoraNfEntrada.tipo == 'REAL'` se algum caminho não-filtrado existir).

- [ ] **Step 3: Guard R1** — em `assert_item_moto_consistente`, ignorar chassis cuja única âncora é conferência provisória (documentar que moto provisória é legítima sem item de NF). Adicionar early-return/skip para esses chassis e teste cobrindo que `importar_danfe`/desconsiderar não falha sobre moto provisória.

- [ ] **Step 4: Auditar somas de valor fiscal** — `grep -rn "valor_total" app/hora/` e garantir que relatórios de valor de estoque/NF filtrem `tipo == 'REAL'`. Ajustar onde necessário (com teste).

- [ ] **Step 5: Commit**

```bash
git add app/hora/services/ tests/hora/test_recebimento_sem_nf.py
git commit -m "fix(hora): isolar NF provisoria do fiscal + guard assert_item_moto_consistente (R1)"
```

---

### Task 10: docs

**Files:**
- Modify: `app/hora/CLAUDE.md` (nova seção numerada, padrão das anteriores)
- Modify: `docs/hora/INVARIANTES.md` (NF provisória + exceção)
- Modify: `docs/superpowers/specs/INDEX.md` e `docs/superpowers/plans/INDEX.md` (registro bidirecional)

- [ ] **Step 1:** Adicionar seção "Recebimento por filial sem NF (NF provisória) — 2026-06-26" em `app/hora/CLAUDE.md` resumindo: campo `tipo`, snapshot `hora_recebimento_esperado`, fluxo anexar NF real, decisões D1-D9.
- [ ] **Step 2:** Registrar o spec e o plano nos dois arquivos INDEX (uma linha no padrão do índice: bullet com título, link relativo e gancho de 1 linha).
- [ ] **Step 3:** `python scripts/audits/doc_audit.py --enforce-touched` → sem erro.
- [ ] **Step 4: Commit**

```bash
git add app/hora/CLAUDE.md docs/hora/INVARIANTES.md docs/superpowers/specs/INDEX.md docs/superpowers/plans/INDEX.md
git commit -m "docs(hora): recebimento sem NF (NF provisoria) — CLAUDE.md + invariantes + indices"
```

---

## Self-review

**Spec coverage:** D1 (snapshot)→T3; D2 (tipo)→T1/T2; D3 (tabela esperado)→T1/T2; D4 (anexar dentro)→T5/T7; D5 (conferência SOT)→T4 (não sobrescreve) + T5 (reprocessa); D6 (não atribui chassi)→T4 (`_gabarito_provisorio` lógico); D7 (chassi-extra aceita)→T4; D8 (sem MOTO_FALTANDO)→T4; D9 (status fiscal só com NF real)→T5. Riscos: R1→T9, R2→T6, R3→T5 (dedup), R4→T1 (índices).

**Placeholder scan:** Tasks 9 (auditar somas de valor / guard assert) e 8 (HTML) descrevem ação sem código completo em alguns steps — refinar ao executar lendo o arquivo-alvo; demais tasks têm código real.

**Type consistency:** `criar_recebimento_sem_nf(loja_id, operador)`, `anexar_nf_real_ao_recebimento(recebimento_id, pdf_bytes, operador, payload=None)`, `_gabarito_provisorio(rec, chassi, modelo_id_conf)`, `HoraRecebimentoEsperado.consumido_por_conferencia_id` — consistentes entre tasks.
