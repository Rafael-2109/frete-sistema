<!-- doc:meta
tipo: scratch
camada: L3
sot_de: —
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->

# CarVia — Consistência de Comissões (Ajustes débito/crédito) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Quando o `cte_valor` de um CTe já comissionado muda (ou o CTe/operação é cancelado) depois do fechamento ter sido criado, registrar a diferença de comissão como um ajuste (débito/crédito) abatido no próximo fechamento do mesmo vendedor, sem alterar o fechamento original; e trocar o filtro da tela de criação para apenas "data de corte".

**Architecture:** Nova tabela `carvia_comissao_ajustes` + coluna `vendedor_usuario_id` (FK `usuarios`) e `total_ajustes` em `carvia_comissao_fechamentos`. Lógica nova no `ComissaoService` em métodos **flush-only** testáveis (`sincronizar_ajustes_cte`, `_incorporar_ajustes_pendentes`, `_montar_fechamento`); `criar_fechamento` = `_montar_fechamento` + `commit`. Hooks de disparo em 3 pontos verificados. Vendedor passa a ser um `Usuario` (select). Bloqueio se total ficaria negativo.

**Tech Stack:** Flask 3.1 + Flask-SQLAlchemy 2.0 + Flask-Migrate, PostgreSQL, pytest (fixture `db` em savepoint `begin_nested`), Jinja2 + vanilla JS.

**Spec:** `docs/superpowers/specs/2026-06-15-carvia-comissao-ajustes-design.md`

> **Estado (2026-06-15): ✅ EXECUTADO e integrado na `main`** (238 testes CarVia). Ajustes vs este plano:
> (1) a **migration** NÃO foi feita via Flask-Migrate (`flask db migrate`/`migrations/versions/`) — o
> projeto tem essa cadeia congelada; foi feita como par idempotente
> `scripts/migrations/carvia_comissao_ajustes.{sql,py}` (ver memória `mecanismo-schema-migrations-projeto`).
> Ignorar os passos de `flask db migrate` da Task 1; o resto vale. (2) Acrescentada a edição
> (`editar_comissao`) usando `<select>` de usuário via `vincular_vendedor` (não previsto no plano).

---

## Setup (antes da Task 1)

- [ ] **S1: Worktree isolado.** Use superpowers:using-git-worktrees para criar branch a partir de `origin/main` (ex.: `feat/carvia-comissao-ajustes`). Confirmar com `git branch --show-current` (gotcha conhecido: subagente pode pinar cwd na árvore principal).
- [ ] **S2: Ambiente.** `source .venv/bin/activate`. Garantir `DATABASE_URL` apontando para o Postgres local (não cair em SQLite — o conftest usa o banco do ambiente). Rodar testes SEMPRE a partir da raiz do worktree (hooks PAD).

> **Regras do módulo:** CarVia é isolado (R1) e usa **lazy imports** de services/models nos routes/services (R2). Todo novo import de `ComissaoService`/models dentro de função.

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `app/carvia/models/comissao.py` | + model `CarviaComissaoAjuste`; + colunas `vendedor_usuario_id`/`total_ajustes`; `recalcular_totais()` soma ajustes aplicados |
| `app/carvia/models/__init__.py` | export do novo model |
| `app/carvia/services/financeiro/comissao_service.py` | `sincronizar_ajustes_cte`, `_incorporar_ajustes_pendentes`, `_montar_fechamento`, `vincular_vendedor`; `criar_fechamento`/`buscar_ctes_elegiveis`/`excluir_cte`/`marcar_pago` modificados |
| `app/carvia/routes/operacao_routes.py` | hooks em `editar_cte_valor` e cancelamento direto |
| `app/carvia/services/documentos/operacao_cancel_service.py` | hook no cascade |
| `app/carvia/routes/comissao_routes.py` | criação por `vendedor_usuario_id` + data de corte; API elegíveis; API ajustes pendentes; endpoint `vincular-vendedor` |
| `app/templates/carvia/comissoes/criar.html` | select de vendedor; só data final; painel de ajustes |
| `app/templates/carvia/comissoes/detalhe.html` | seção de ajustes; bloco de vínculo |
| `app/carvia/routes/exportacao_routes.py` | coluna "Total Ajustes" no export |
| `migrations/versions/<rev>_carvia_comissao_ajustes.py` | DDL + backfill |
| `tests/carvia/test_comissao_ajustes.py` | testes do service (novo arquivo) |

---

## Task 1: Model `CarviaComissaoAjuste` + colunas no fechamento + migration

**Files:**
- Modify: `app/carvia/models/comissao.py`
- Modify: `app/carvia/models/__init__.py`
- Create: `migrations/versions/<rev>_carvia_comissao_ajustes.py`
- Test: `tests/carvia/test_comissao_ajustes.py`

- [ ] **Step 1: Adicionar o model e as colunas em `app/carvia/models/comissao.py`**

No fim do arquivo (após `CarviaComissaoFechamentoCte`), adicionar:

```python
class CarviaComissaoAjuste(db.Model):
    """Ajuste (debito/credito) de comissao gerado quando o cte_valor de um CTe
    ja comissionado muda, ou quando o CTe/operacao e cancelado. Abatido no
    proximo fechamento do mesmo vendedor. NAO altera o fechamento de origem."""
    __tablename__ = 'carvia_comissao_ajustes'

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('PENDENTE','APLICADO','CANCELADO')",
            name='ck_comissao_ajuste_status',
        ),
        db.CheckConstraint(
            "motivo IN ('ALTERACAO_VALOR','CANCELAMENTO_CTE')",
            name='ck_comissao_ajuste_motivo',
        ),
        db.Index('ix_comissao_ajuste_vend_status', 'vendedor_usuario_id', 'status'),
    )

    id = db.Column(db.Integer, primary_key=True)
    operacao_id = db.Column(
        db.Integer, db.ForeignKey('carvia_operacoes.id'), nullable=False, index=True,
    )
    fechamento_origem_id = db.Column(
        db.Integer, db.ForeignKey('carvia_comissao_fechamentos.id'),
        nullable=False, index=True,
    )
    vendedor_usuario_id = db.Column(
        db.Integer, db.ForeignKey('usuarios.id'), nullable=True, index=True,
    )
    vendedor_nome = db.Column(db.String(100), nullable=False)
    vendedor_email = db.Column(db.String(150))

    motivo = db.Column(db.String(20), nullable=False)  # ALTERACAO_VALOR | CANCELAMENTO_CTE
    cte_numero = db.Column(db.String(20), nullable=False)
    valor_cte_anterior = db.Column(db.Numeric(15, 2), nullable=False)
    valor_cte_novo = db.Column(db.Numeric(15, 2), nullable=False)
    percentual_snapshot = db.Column(db.Numeric(10, 8), nullable=False)
    delta_comissao = db.Column(db.Numeric(15, 2), nullable=False)  # >0 credito, <0 debito

    status = db.Column(db.String(20), nullable=False, default='PENDENTE', index=True)
    fechamento_aplicado_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_comissao_fechamentos.id', ondelete='SET NULL'),
        nullable=True,
    )

    criado_por = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    aplicado_em = db.Column(db.DateTime)
    observacoes = db.Column(db.Text)

    operacao = db.relationship(
        'CarviaOperacao', lazy='joined', foreign_keys=[operacao_id],
    )

    def __repr__(self):
        return (
            f'<CarviaComissaoAjuste op={self.operacao_id} '
            f'delta={self.delta_comissao} {self.status}>'
        )
```

E em `CarviaComissaoFechamento`, logo após a coluna `total_comissao` (linha ~41), adicionar:

```python
    # Vendedor beneficiario (FK canonica — vendedor_nome/email = snapshot exibicao)
    vendedor_usuario_id = db.Column(
        db.Integer, db.ForeignKey('usuarios.id'), nullable=True, index=True,
    )
    # Soma dos deltas de ajustes APLICADOS a este fechamento (transparencia)
    total_ajustes = db.Column(db.Numeric(15, 2), nullable=False, default=0)
```

- [ ] **Step 2: Export em `app/carvia/models/__init__.py`**

Trocar o bloco Comissao (linhas 85-88):

```python
# Comissao
from app.carvia.models.comissao import (  # noqa: F401
    CarviaComissaoFechamento, CarviaComissaoFechamentoCte, CarviaComissaoAjuste,
)
```

E em `__all__`, na seção Comissao (linha ~135):

```python
    # Comissao
    'CarviaComissaoFechamento', 'CarviaComissaoFechamentoCte', 'CarviaComissaoAjuste',
```

- [ ] **Step 3: Gerar a migration**

Run: `flask db migrate -m "carvia_comissao_ajustes"`
Depois ABRIR o arquivo gerado em `migrations/versions/` e garantir que o `upgrade()` contém EXATAMENTE (autogenerate pode errar ordem/constraints — editar para isto):

```python
def upgrade():
    op.create_table(
        'carvia_comissao_ajustes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('operacao_id', sa.Integer(), nullable=False),
        sa.Column('fechamento_origem_id', sa.Integer(), nullable=False),
        sa.Column('vendedor_usuario_id', sa.Integer(), nullable=True),
        sa.Column('vendedor_nome', sa.String(length=100), nullable=False),
        sa.Column('vendedor_email', sa.String(length=150), nullable=True),
        sa.Column('motivo', sa.String(length=20), nullable=False),
        sa.Column('cte_numero', sa.String(length=20), nullable=False),
        sa.Column('valor_cte_anterior', sa.Numeric(15, 2), nullable=False),
        sa.Column('valor_cte_novo', sa.Numeric(15, 2), nullable=False),
        sa.Column('percentual_snapshot', sa.Numeric(10, 8), nullable=False),
        sa.Column('delta_comissao', sa.Numeric(15, 2), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDENTE'),
        sa.Column('fechamento_aplicado_id', sa.Integer(), nullable=True),
        sa.Column('criado_por', sa.String(length=100), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('aplicado_em', sa.DateTime(), nullable=True),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['operacao_id'], ['carvia_operacoes.id']),
        sa.ForeignKeyConstraint(['fechamento_origem_id'], ['carvia_comissao_fechamentos.id']),
        sa.ForeignKeyConstraint(['vendedor_usuario_id'], ['usuarios.id']),
        sa.ForeignKeyConstraint(['fechamento_aplicado_id'], ['carvia_comissao_fechamentos.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('PENDENTE','APLICADO','CANCELADO')", name='ck_comissao_ajuste_status'),
        sa.CheckConstraint("motivo IN ('ALTERACAO_VALOR','CANCELAMENTO_CTE')", name='ck_comissao_ajuste_motivo'),
    )
    op.create_index('ix_comissao_ajuste_vend_status', 'carvia_comissao_ajustes', ['vendedor_usuario_id', 'status'])
    op.create_index(op.f('ix_carvia_comissao_ajustes_operacao_id'), 'carvia_comissao_ajustes', ['operacao_id'])
    op.create_index(op.f('ix_carvia_comissao_ajustes_fechamento_origem_id'), 'carvia_comissao_ajustes', ['fechamento_origem_id'])
    op.create_index(op.f('ix_carvia_comissao_ajustes_status'), 'carvia_comissao_ajustes', ['status'])

    op.add_column('carvia_comissao_fechamentos', sa.Column('vendedor_usuario_id', sa.Integer(), nullable=True))
    op.add_column('carvia_comissao_fechamentos', sa.Column('total_ajustes', sa.Numeric(15, 2), nullable=False, server_default='0'))
    op.create_foreign_key('fk_comissao_fechamento_vendedor_usuario', 'carvia_comissao_fechamentos', 'usuarios', ['vendedor_usuario_id'], ['id'])
    op.create_index(op.f('ix_carvia_comissao_fechamentos_vendedor_usuario_id'), 'carvia_comissao_fechamentos', ['vendedor_usuario_id'])

    # Backfill por e-mail (idempotente)
    op.execute("""
        UPDATE carvia_comissao_fechamentos f
        SET vendedor_usuario_id = u.id
        FROM usuarios u
        WHERE f.vendedor_email IS NOT NULL
          AND lower(f.vendedor_email) = lower(u.email)
          AND f.vendedor_usuario_id IS NULL
    """)


def downgrade():
    op.drop_index(op.f('ix_carvia_comissao_fechamentos_vendedor_usuario_id'), table_name='carvia_comissao_fechamentos')
    op.drop_constraint('fk_comissao_fechamento_vendedor_usuario', 'carvia_comissao_fechamentos', type_='foreignkey')
    op.drop_column('carvia_comissao_fechamentos', 'total_ajustes')
    op.drop_column('carvia_comissao_fechamentos', 'vendedor_usuario_id')
    op.drop_table('carvia_comissao_ajustes')
```

- [ ] **Step 4: Aplicar a migration no banco local**

Run: `flask db upgrade`
Expected: sem erro; `\d carvia_comissao_ajustes` mostra a tabela.

- [ ] **Step 5: Teste smoke do model (escrever o teste)**

Criar `tests/carvia/test_comissao_ajustes.py`:

```python
"""Testes de ajustes de comissao CarVia (debito/credito) + helpers flush-only.

Services novos sao flush-only (compativel com fixture `db` em savepoint).
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest


def _sfx():
    return uuid.uuid4().hex[:6]


def _chave44(prefixo='3525'):
    return (prefixo + uuid.uuid4().hex).ljust(44, '0')[:44]


def _criar_usuario(db, *, email=None, nome='Jessica Tereza'):
    from app.auth.models import Usuario
    u = Usuario(
        nome=nome,
        email=email or f'vend_{_sfx()}@ex.com',
        senha_hash='x',
        perfil='vendedor',
        status='ativo',
        sistema_carvia=True,
        acesso_comissao_carvia=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _criar_op(db, *, cte_valor='1000.00', status='RASCUNHO', emissao=date(2026, 4, 1)):
    from app.carvia.models import CarviaOperacao
    op = CarviaOperacao(
        cte_numero=f'CTe-{_sfx()}',
        cte_chave_acesso=_chave44(),
        cte_valor=Decimal(cte_valor),
        cte_data_emissao=emissao,
        cnpj_cliente='12345678000100', nome_cliente='Cliente',
        uf_origem='SP', cidade_origem='SP',
        uf_destino='RJ', cidade_destino='RJ',
        status=status, tipo_entrada='IMPORTADO', criado_por='test',
    )
    db.session.add(op)
    db.session.flush()
    return op


def _criar_fechamento(db, usuario, ops, *, percentual=Decimal('0.05'), status='PENDENTE'):
    """Cria fechamento + junctions com snapshots, flush-only (sem service)."""
    from app.carvia.models.comissao import (
        CarviaComissaoFechamento, CarviaComissaoFechamentoCte,
    )
    f = CarviaComissaoFechamento(
        numero_fechamento=f'COM-{_sfx()}',
        vendedor_usuario_id=usuario.id,
        vendedor_nome=usuario.nome, vendedor_email=usuario.email,
        data_inicio=date(2026, 4, 1), data_fim=date(2026, 4, 30),
        percentual=percentual, status=status, criado_por='test',
    )
    db.session.add(f)
    db.session.flush()
    for op in ops:
        valor = Decimal(str(op.cte_valor))
        db.session.add(CarviaComissaoFechamentoCte(
            fechamento_id=f.id, operacao_id=op.id,
            cte_numero=op.cte_numero, cte_data_emissao=op.cte_data_emissao,
            valor_cte_snapshot=valor, percentual_snapshot=percentual,
            valor_comissao=(valor * percentual).quantize(Decimal('0.01')),
            incluido_por='test',
        ))
    db.session.flush()
    f.recalcular_totais()
    return f


def test_model_ajuste_smoke(db):
    from app.carvia.models import CarviaComissaoAjuste, CarviaOperacao  # noqa: F401
    u = _criar_usuario(db)
    op = _criar_op(db)
    f = _criar_fechamento(db, u, [op])
    aj = CarviaComissaoAjuste(
        operacao_id=op.id, fechamento_origem_id=f.id,
        vendedor_usuario_id=u.id, vendedor_nome=u.nome, vendedor_email=u.email,
        motivo='ALTERACAO_VALOR', cte_numero=op.cte_numero,
        valor_cte_anterior=Decimal('1000.00'), valor_cte_novo=Decimal('1200.00'),
        percentual_snapshot=Decimal('0.05'), delta_comissao=Decimal('10.00'),
        criado_por='test',
    )
    db.session.add(aj)
    db.session.flush()
    assert aj.id is not None
    assert aj.status == 'PENDENTE'
```

- [ ] **Step 6: Rodar o teste smoke**

Run: `pytest tests/carvia/test_comissao_ajustes.py::test_model_ajuste_smoke -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add app/carvia/models/comissao.py app/carvia/models/__init__.py migrations/versions/ tests/carvia/test_comissao_ajustes.py
git commit -m "feat(carvia): model CarviaComissaoAjuste + colunas vendedor_usuario_id/total_ajustes + migration"
```

---

## Task 2: `recalcular_totais()` soma ajustes aplicados

**Files:**
- Modify: `app/carvia/models/comissao.py` (`recalcular_totais`, linhas 93-111)
- Test: `tests/carvia/test_comissao_ajustes.py`

- [ ] **Step 1: Escrever o teste**

Adicionar a `tests/carvia/test_comissao_ajustes.py`:

```python
def test_recalcular_totais_inclui_ajustes_aplicados(db):
    from app.carvia.models.comissao import CarviaComissaoAjuste
    u = _criar_usuario(db)
    op = _criar_op(db, cte_valor='1000.00')
    f = _criar_fechamento(db, u, [op])  # comissao CTes = 50.00 (5%)
    assert f.total_comissao == Decimal('50.00')

    # ajuste APLICADO de +10 deve entrar no total
    db.session.add(CarviaComissaoAjuste(
        operacao_id=op.id, fechamento_origem_id=f.id, fechamento_aplicado_id=f.id,
        vendedor_usuario_id=u.id, vendedor_nome=u.nome, vendedor_email=u.email,
        motivo='ALTERACAO_VALOR', cte_numero=op.cte_numero,
        valor_cte_anterior=Decimal('1000.00'), valor_cte_novo=Decimal('1200.00'),
        percentual_snapshot=Decimal('0.05'), delta_comissao=Decimal('10.00'),
        status='APLICADO', criado_por='test',
    ))
    db.session.flush()
    f.recalcular_totais()
    assert f.total_ajustes == Decimal('10.00')
    assert f.total_comissao == Decimal('60.00')
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/carvia/test_comissao_ajustes.py::test_recalcular_totais_inclui_ajustes_aplicados -v`
Expected: FAIL (`total_ajustes`/`total_comissao` ainda não somam ajustes)

- [ ] **Step 3: Implementar `recalcular_totais` modificado**

Substituir o corpo do método em `app/carvia/models/comissao.py`:

```python
    def recalcular_totais(self):
        """Recalcula totais a partir dos CTes ativos + ajustes APLICADOS.

        total_comissao = comissao(CTes ativos) + total_ajustes.
        Caller deve fazer db.session.commit().
        """
        from decimal import Decimal
        ctes_ativos = CarviaComissaoFechamentoCte.query.filter_by(
            fechamento_id=self.id, excluido=False,
        ).all()
        self.qtd_ctes = len(ctes_ativos)
        self.total_bruto = sum(
            (c.valor_cte_snapshot or Decimal('0')) for c in ctes_ativos
        )
        comissao_ctes = sum(
            (c.valor_comissao or Decimal('0')) for c in ctes_ativos
        )

        ajustes_aplicados = CarviaComissaoAjuste.query.filter_by(
            fechamento_aplicado_id=self.id, status='APLICADO',
        ).all()
        self.total_ajustes = sum(
            (a.delta_comissao or Decimal('0')) for a in ajustes_aplicados
        )
        self.total_comissao = comissao_ctes + self.total_ajustes
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/carvia/test_comissao_ajustes.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add app/carvia/models/comissao.py tests/carvia/test_comissao_ajustes.py
git commit -m "feat(carvia): recalcular_totais soma ajustes aplicados"
```

---

## Task 3: `ComissaoService.sincronizar_ajustes_cte` (geração de delta)

**Files:**
- Modify: `app/carvia/services/financeiro/comissao_service.py`
- Test: `tests/carvia/test_comissao_ajustes.py`

- [ ] **Step 1: Escrever os testes**

```python
def test_sincronizar_gera_credito_quando_valor_sobe(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    u = _criar_usuario(db)
    op = _criar_op(db, cte_valor='1000.00')
    f = _criar_fechamento(db, u, [op])
    op.cte_valor = Decimal('1200.00')
    db.session.flush()
    criados = ComissaoService.sincronizar_ajustes_cte(op.id, Decimal('1200.00'), 'ALTERACAO_VALOR', 'test')
    assert len(criados) == 1
    assert criados[0].delta_comissao == Decimal('10.00')  # (1200-1000)*0.05
    assert criados[0].motivo == 'ALTERACAO_VALOR'
    assert criados[0].vendedor_usuario_id == u.id


def test_sincronizar_gera_debito_no_cancelamento(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    u = _criar_usuario(db)
    op = _criar_op(db, cte_valor='1000.00')
    f = _criar_fechamento(db, u, [op])
    criados = ComissaoService.sincronizar_ajustes_cte(op.id, 0, 'CANCELAMENTO_CTE', 'test')
    assert len(criados) == 1
    assert criados[0].delta_comissao == Decimal('-50.00')  # (0-1000)*0.05


def test_sincronizar_base_corrente_em_multiplas_alteracoes(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    u = _criar_usuario(db)
    op = _criar_op(db, cte_valor='1000.00')
    f = _criar_fechamento(db, u, [op])
    ComissaoService.sincronizar_ajustes_cte(op.id, Decimal('1200.00'), 'ALTERACAO_VALOR', 'test')  # +10
    criados2 = ComissaoService.sincronizar_ajustes_cte(op.id, Decimal('900.00'), 'ALTERACAO_VALOR', 'test')  # base 1200 -> -15
    assert criados2[0].valor_cte_anterior == Decimal('1200.00')
    assert criados2[0].delta_comissao == Decimal('-15.00')  # (900-1200)*0.05


def test_sincronizar_delta_zero_nao_cria(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    u = _criar_usuario(db)
    op = _criar_op(db, cte_valor='1000.00')
    f = _criar_fechamento(db, u, [op])
    criados = ComissaoService.sincronizar_ajustes_cte(op.id, Decimal('1000.00'), 'ALTERACAO_VALOR', 'test')
    assert criados == []


def test_sincronizar_ignora_fechamento_cancelado(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    u = _criar_usuario(db)
    op = _criar_op(db, cte_valor='1000.00')
    f = _criar_fechamento(db, u, [op], status='CANCELADO')
    criados = ComissaoService.sincronizar_ajustes_cte(op.id, Decimal('1200.00'), 'ALTERACAO_VALOR', 'test')
    assert criados == []
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/carvia/test_comissao_ajustes.py -k sincronizar -v`
Expected: FAIL (`AttributeError: ... has no attribute 'sincronizar_ajustes_cte'`)

- [ ] **Step 3: Implementar o método** (adicionar em `ComissaoService`, antes de `criar_fechamento`)

```python
    @staticmethod
    def sincronizar_ajustes_cte(operacao_id, novo_valor_efetivo, motivo, usuario):
        """Gera ajustes de comissao (delta) para um CTe cujo valor mudou ou que
        foi cancelado, em TODOS os fechamentos ativos (status != CANCELADO) que
        o contem. FLUSH-ONLY — o caller controla a transacao.

        motivo: 'ALTERACAO_VALOR' (novo_valor=novo cte_valor) ou
                'CANCELAMENTO_CTE' (novo_valor=0).
        Retorna list[CarviaComissaoAjuste] criados (delta != 0).
        """
        from app.carvia.models.comissao import (
            CarviaComissaoFechamento, CarviaComissaoFechamentoCte, CarviaComissaoAjuste,
        )

        novo = Decimal(str(novo_valor_efetivo or 0))

        junctions = db.session.query(CarviaComissaoFechamentoCte).join(
            CarviaComissaoFechamento,
            CarviaComissaoFechamentoCte.fechamento_id == CarviaComissaoFechamento.id,
        ).filter(
            CarviaComissaoFechamentoCte.operacao_id == operacao_id,
            CarviaComissaoFechamentoCte.excluido.is_(False),
            CarviaComissaoFechamento.status != 'CANCELADO',
        ).all()

        criados = []
        for j in junctions:
            fechamento = db.session.get(CarviaComissaoFechamento, j.fechamento_id)

            ultimo = CarviaComissaoAjuste.query.filter(
                CarviaComissaoAjuste.operacao_id == operacao_id,
                CarviaComissaoAjuste.fechamento_origem_id == j.fechamento_id,
                CarviaComissaoAjuste.status != 'CANCELADO',
            ).order_by(CarviaComissaoAjuste.id.desc()).first()
            base = (
                Decimal(str(ultimo.valor_cte_novo)) if ultimo
                else Decimal(str(j.valor_cte_snapshot))
            )

            pct = Decimal(str(j.percentual_snapshot))
            delta = ((novo - base) * pct).quantize(Decimal('0.01'))
            if delta == 0:
                continue

            ajuste = CarviaComissaoAjuste(
                operacao_id=operacao_id,
                fechamento_origem_id=j.fechamento_id,
                vendedor_usuario_id=fechamento.vendedor_usuario_id,
                vendedor_nome=fechamento.vendedor_nome,
                vendedor_email=fechamento.vendedor_email,
                motivo=motivo,
                cte_numero=j.cte_numero,
                valor_cte_anterior=base,
                valor_cte_novo=novo,
                percentual_snapshot=pct,
                delta_comissao=delta,
                status='PENDENTE',
                criado_por=usuario,
            )
            db.session.add(ajuste)
            criados.append(ajuste)

        db.session.flush()
        return criados
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/carvia/test_comissao_ajustes.py -k sincronizar -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/carvia/services/financeiro/comissao_service.py tests/carvia/test_comissao_ajustes.py
git commit -m "feat(carvia): ComissaoService.sincronizar_ajustes_cte (gera delta de comissao)"
```

---

## Task 4: `_incorporar_ajustes_pendentes` (helper flush-only) + guard negativo

**Files:**
- Modify: `app/carvia/services/financeiro/comissao_service.py`
- Test: `tests/carvia/test_comissao_ajustes.py`

- [ ] **Step 1: Escrever os testes**

```python
def test_incorporar_aplica_ajustes_pendentes(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    from app.carvia.models.comissao import CarviaComissaoAjuste
    u = _criar_usuario(db)
    op_velho = _criar_op(db, cte_valor='1000.00')
    f_antigo = _criar_fechamento(db, u, [op_velho])
    ComissaoService.sincronizar_ajustes_cte(op_velho.id, Decimal('1200.00'), 'ALTERACAO_VALOR', 'test')  # +10 PENDENTE

    op_novo = _criar_op(db, cte_valor='2000.00')
    f_novo = _criar_fechamento(db, u, [op_novo])  # comissao CTes = 100.00

    pendentes = ComissaoService._incorporar_ajustes_pendentes(f_novo, 'test')
    assert len(pendentes) == 1
    assert pendentes[0].status == 'APLICADO'
    assert pendentes[0].fechamento_aplicado_id == f_novo.id
    assert f_novo.total_ajustes == Decimal('10.00')
    assert f_novo.total_comissao == Decimal('110.00')


def test_incorporar_guard_total_negativo(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    u = _criar_usuario(db)
    op_velho = _criar_op(db, cte_valor='10000.00')
    f_antigo = _criar_fechamento(db, u, [op_velho])
    ComissaoService.sincronizar_ajustes_cte(op_velho.id, 0, 'CANCELAMENTO_CTE', 'test')  # -500 PENDENTE

    op_novo = _criar_op(db, cte_valor='1000.00')
    f_novo = _criar_fechamento(db, u, [op_novo])  # comissao = 50.00; 50 - 500 < 0

    with pytest.raises(ValueError, match='excedem'):
        ComissaoService._incorporar_ajustes_pendentes(f_novo, 'test')


def test_incorporar_sem_vinculo_nao_aplica(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    u = _criar_usuario(db)
    op = _criar_op(db, cte_valor='1000.00')
    f = _criar_fechamento(db, u, [op])
    f.vendedor_usuario_id = None  # simula fechamento sem vinculo
    db.session.flush()
    pendentes = ComissaoService._incorporar_ajustes_pendentes(f, 'test')
    assert pendentes == []
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/carvia/test_comissao_ajustes.py -k incorporar -v`
Expected: FAIL (`has no attribute '_incorporar_ajustes_pendentes'`)

- [ ] **Step 3: Implementar o helper** (em `ComissaoService`)

```python
    @staticmethod
    def _incorporar_ajustes_pendentes(fechamento, usuario):
        """Incorpora ajustes PENDENTE do vendedor ao fechamento (FLUSH-ONLY).

        Marca cada ajuste APLICADO + fechamento_aplicado_id; recalcula totais.
        Bloqueia (ValueError) se o total final ficaria negativo — caller faz rollback.
        Retorna a lista de ajustes incorporados.
        """
        from app.carvia.models.comissao import CarviaComissaoAjuste

        fechamento.recalcular_totais()  # total_comissao = so CTes (ainda sem ajustes)

        if not fechamento.vendedor_usuario_id:
            return []

        pendentes = CarviaComissaoAjuste.query.filter_by(
            vendedor_usuario_id=fechamento.vendedor_usuario_id,
            status='PENDENTE',
        ).all()
        if not pendentes:
            return []

        soma_delta = sum((a.delta_comissao or Decimal('0')) for a in pendentes)
        total_final = (fechamento.total_comissao or Decimal('0')) + soma_delta
        if total_final < 0:
            raise ValueError(
                f'Debitos pendentes (R$ {-soma_delta:.2f}) excedem a comissao do '
                f'periodo (R$ {fechamento.total_comissao:.2f}). '
                f'Inclua mais CTes ou aguarde o proximo periodo.'
            )

        for a in pendentes:
            a.status = 'APLICADO'
            a.fechamento_aplicado_id = fechamento.id
            a.aplicado_em = agora_utc_naive()

        db.session.flush()
        fechamento.recalcular_totais()  # agora inclui ajustes aplicados
        return pendentes
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/carvia/test_comissao_ajustes.py -k incorporar -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/carvia/services/financeiro/comissao_service.py tests/carvia/test_comissao_ajustes.py
git commit -m "feat(carvia): _incorporar_ajustes_pendentes com guard de total negativo"
```

---

## Task 5: `criar_fechamento` por `vendedor_usuario_id` + `_montar_fechamento` flush-only

**Files:**
- Modify: `app/carvia/services/financeiro/comissao_service.py` (`criar_fechamento`, linhas 171-288)
- Test: `tests/carvia/test_comissao_ajustes.py`

- [ ] **Step 1: Escrever o teste (sobre `_montar_fechamento`, flush-only)**

```python
def test_montar_fechamento_resolve_vendedor_e_incorpora(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    u = _criar_usuario(db, nome='Jessica Tereza')
    op_velho = _criar_op(db, cte_valor='1000.00')
    f_antigo = _criar_fechamento(db, u, [op_velho])
    ComissaoService.sincronizar_ajustes_cte(op_velho.id, Decimal('1200.00'), 'ALTERACAO_VALOR', 'test')  # +10

    op_novo = _criar_op(db, cte_valor='2000.00', emissao=date(2026, 5, 10))
    f = ComissaoService._montar_fechamento(
        vendedor_usuario_id=u.id, data_fim=date(2026, 5, 31),
        operacao_ids=[op_novo.id], criado_por='admin@ex.com',
        percentual=Decimal('0.05'), observacoes=None,
    )
    assert f.vendedor_usuario_id == u.id
    assert f.vendedor_nome == 'Jessica Tereza'   # snapshot do usuario
    assert f.data_inicio == date(2026, 5, 10)    # derivada do CTe mais antigo
    assert f.total_comissao == Decimal('110.00')  # 100 CTes + 10 ajuste
    assert f.total_ajustes == Decimal('10.00')
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/carvia/test_comissao_ajustes.py -k montar_fechamento -v`
Expected: FAIL (`has no attribute '_montar_fechamento'`)

- [ ] **Step 3: Refatorar `criar_fechamento` em `_montar_fechamento` (flush-only) + wrapper**

Substituir o método `criar_fechamento` (linhas 171-288) por:

```python
    @staticmethod
    def _montar_fechamento(
        vendedor_usuario_id, data_fim, operacao_ids, criado_por,
        percentual=None, observacoes=None,
    ):
        """Monta fechamento + junctions + incorpora ajustes + despesa.
        FLUSH-ONLY (nao comita) — testavel sob savepoint.
        """
        from app.carvia.models import CarviaOperacao
        from app.carvia.models.comissao import (
            CarviaComissaoFechamento, CarviaComissaoFechamentoCte,
        )
        from app.auth.models import Usuario

        usuario = db.session.get(Usuario, vendedor_usuario_id)
        if not usuario:
            raise ValueError('Vendedor (usuario) nao encontrado.')
        if not operacao_ids:
            raise ValueError('Selecione ao menos um CTe.')

        if percentual is not None:
            pct = Decimal(str(percentual))
            if pct > 1:
                pct = pct / Decimal('100')
        else:
            pct = ComissaoService.get_percentual_config()

        operacoes = CarviaOperacao.query.filter(
            CarviaOperacao.id.in_(operacao_ids),
        ).all()
        if len(operacoes) != len(operacao_ids):
            encontrados = {o.id for o in operacoes}
            raise ValueError(f'CTes nao encontrados: {set(operacao_ids) - encontrados}')

        for op in operacoes:
            if op.status == 'CANCELADO':
                raise ValueError(f'{op.cte_numero}: CTe cancelado.')
            if not op.cte_valor or op.cte_valor <= 0:
                raise ValueError(f'{op.cte_numero}: sem valor de CTe.')
            if not op.cte_data_emissao:
                raise ValueError(f'{op.cte_numero}: sem data de emissao do CTe.')

        data_inicio = min(op.cte_data_emissao for op in operacoes)  # derivada
        if data_inicio > data_fim:
            data_inicio = data_fim

        fechamento = CarviaComissaoFechamento(
            numero_fechamento=CarviaComissaoFechamento.gerar_numero_fechamento(),
            vendedor_usuario_id=usuario.id,
            vendedor_nome=usuario.nome,
            vendedor_email=usuario.email,
            data_inicio=data_inicio,
            data_fim=data_fim,
            percentual=pct,
            status='PENDENTE',
            observacoes=(observacoes or '').strip() or None,
            criado_por=criado_por,
        )
        db.session.add(fechamento)
        db.session.flush()

        for op in operacoes:
            valor_cte = Decimal(str(op.cte_valor))
            db.session.add(CarviaComissaoFechamentoCte(
                fechamento_id=fechamento.id, operacao_id=op.id,
                cte_numero=op.cte_numero or f'OP-{op.id}',
                cte_data_emissao=op.cte_data_emissao,
                valor_cte_snapshot=valor_cte, percentual_snapshot=pct,
                valor_comissao=(valor_cte * pct).quantize(Decimal('0.01')),
                incluido_por=criado_por,
            ))
        db.session.flush()

        # Incorpora ajustes pendentes do vendedor (pode levantar ValueError)
        ComissaoService._incorporar_ajustes_pendentes(fechamento, criado_por)

        # Despesa vinculada com o total final (ja inclui ajustes)
        ComissaoService._criar_despesa_vinculada(fechamento, criado_por)
        return fechamento

    @staticmethod
    def criar_fechamento(
        vendedor_usuario_id, data_fim, operacao_ids, criado_por,
        percentual=None, observacoes=None,
    ):
        """Cria fechamento de comissao (wrapper que comita)."""
        fechamento = ComissaoService._montar_fechamento(
            vendedor_usuario_id, data_fim, operacao_ids, criado_por,
            percentual=percentual, observacoes=observacoes,
        )
        db.session.commit()
        logger.info(
            "Comissao %s criada: %d CTes, R$ %s comissao por %s",
            fechamento.numero_fechamento, fechamento.qtd_ctes,
            fechamento.total_comissao, criado_por,
        )
        return fechamento
```

> NOTA: a assinatura de `criar_fechamento` mudou (não recebe mais `vendedor_nome`/`vendedor_email`/`data_inicio`). A route é atualizada na Task 9.

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/carvia/test_comissao_ajustes.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add app/carvia/services/financeiro/comissao_service.py tests/carvia/test_comissao_ajustes.py
git commit -m "feat(carvia): criar_fechamento por vendedor_usuario_id + incorporacao de ajustes (montar_fechamento flush-only)"
```

---

## Task 6: `buscar_ctes_elegiveis` por data de corte

**Files:**
- Modify: `app/carvia/services/financeiro/comissao_service.py` (`buscar_ctes_elegiveis`, linhas 119-165)
- Test: `tests/carvia/test_comissao_ajustes.py`

- [ ] **Step 1: Escrever o teste**

```python
def test_buscar_elegiveis_so_data_fim(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    op_dentro = _criar_op(db, cte_valor='100.00', status='CONFIRMADO', emissao=date(2026, 3, 1))
    op_fora = _criar_op(db, cte_valor='100.00', status='CONFIRMADO', emissao=date(2026, 6, 1))
    ids = {o.id for o in ComissaoService.buscar_ctes_elegiveis(date(2026, 4, 30))}
    assert op_dentro.id in ids
    assert op_fora.id not in ids
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/carvia/test_comissao_ajustes.py::test_buscar_elegiveis_so_data_fim -v`
Expected: FAIL (assinatura atual exige `data_inicio` posicional → `TypeError`)

- [ ] **Step 3: Implementar** — substituir assinatura e filtro de data:

```python
    @staticmethod
    def buscar_ctes_elegiveis(data_fim, data_inicio=None, excluir_ja_comissionados=True):
        """Retorna CTes CarVia elegiveis para comissao ate a data de corte.

        Criterios:
        - cte_data_emissao <= data_fim (ou BETWEEN data_inicio..data_fim se data_inicio dado)
        - status != 'CANCELADO'; cte_valor > 0
        - (opcional) nao incluso em fechamento ativo

        Returns: list[CarviaOperacao] ordenado por cte_data_emissao ASC
        """
        from app.carvia.models import CarviaOperacao
        from app.carvia.models.comissao import (
            CarviaComissaoFechamento, CarviaComissaoFechamentoCte,
        )

        filtros = [
            CarviaOperacao.status != 'CANCELADO',
            CarviaOperacao.cte_valor.isnot(None),
            CarviaOperacao.cte_valor > 0,
        ]
        if data_inicio is not None:
            filtros.append(CarviaOperacao.cte_data_emissao.between(data_inicio, data_fim))
        else:
            filtros.append(CarviaOperacao.cte_data_emissao <= data_fim)

        query = db.session.query(CarviaOperacao).filter(*filtros)

        if excluir_ja_comissionados:
            ja_comissionados = db.session.query(
                CarviaComissaoFechamentoCte.operacao_id
            ).join(
                CarviaComissaoFechamento,
                CarviaComissaoFechamentoCte.fechamento_id == CarviaComissaoFechamento.id,
            ).filter(
                CarviaComissaoFechamento.status != 'CANCELADO',
                CarviaComissaoFechamentoCte.excluido.is_(False),
            ).subquery()
            query = query.filter(CarviaOperacao.id.notin_(ja_comissionados))

        return query.order_by(CarviaOperacao.cte_data_emissao.asc()).all()
```

- [ ] **Step 4: Confirmar callers** — Run: `grep -rn "buscar_ctes_elegiveis" app/` — Esperado: só `comissao_routes.py:331` (atualizado na Task 9) e os testes. Se houver outro caller posicional, atualizar.

- [ ] **Step 5: Rodar e ver passar**

Run: `pytest tests/carvia/test_comissao_ajustes.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/carvia/services/financeiro/comissao_service.py tests/carvia/test_comissao_ajustes.py
git commit -m "feat(carvia): buscar_ctes_elegiveis por data de corte (data_inicio opcional)"
```

---

## Task 7: Guards em `excluir_cte`/`marcar_pago` + cancelar ajustes ao excluir CTe

**Files:**
- Modify: `app/carvia/services/financeiro/comissao_service.py` (`excluir_cte` ~374-411, `marcar_pago` ~616-649)
- Test: `tests/carvia/test_comissao_ajustes.py`

- [ ] **Step 1: Escrever o teste**

```python
def test_excluir_cte_cancela_ajustes_pendentes_da_junction(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    from app.carvia.models.comissao import CarviaComissaoAjuste
    u = _criar_usuario(db)
    op = _criar_op(db, cte_valor='1000.00')
    f = _criar_fechamento(db, u, [op])
    ComissaoService.sincronizar_ajustes_cte(op.id, Decimal('1200.00'), 'ALTERACAO_VALOR', 'test')
    # excluir_cte comita; usamos savepoint-safe: chamamos e verificamos estado
    ComissaoService.excluir_cte(f.id, op.id, 'test')
    ajustes = CarviaComissaoAjuste.query.filter_by(
        fechamento_origem_id=f.id, operacao_id=op.id,
    ).all()
    assert all(a.status == 'CANCELADO' for a in ajustes)
```

> Obs.: `excluir_cte` comita (legado). O teste roda; o savepoint externo da fixture cobre a limpeza do schema na maioria dos casos. Se houver vazamento, marcar o teste com `@pytest.mark.commit` e isolar. A lógica crítica de ajustes já está coberta por testes flush-only nas Tasks 3-5.

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/carvia/test_comissao_ajustes.py::test_excluir_cte_cancela_ajustes_pendentes_da_junction -v`
Expected: FAIL (ajustes continuam PENDENTE)

- [ ] **Step 3: Implementar** — em `excluir_cte`, após marcar `junction.excluido = True` e ANTES de `db.session.flush()` (linha ~402), inserir:

```python
        # Cancelar ajustes PENDENTE desta junction — o CTe saiu do fechamento
        from app.carvia.models.comissao import CarviaComissaoAjuste
        CarviaComissaoAjuste.query.filter_by(
            fechamento_origem_id=fechamento_id,
            operacao_id=operacao_id,
            status='PENDENTE',
        ).update({'status': 'CANCELADO'})
```

Após `fechamento.recalcular_totais()` em `excluir_cte` (linha ~404), inserir o guard:

```python
        if (fechamento.total_comissao or 0) < 0:
            raise ValueError('Exclusao deixaria a comissao negativa.')
```

Em `marcar_pago`, após a checagem de `qtd_ctes == 0` (linha ~638), inserir:

```python
        if (fechamento.total_comissao or 0) < 0:
            raise ValueError('Fechamento com comissao negativa — nao pode ser pago.')
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/carvia/test_comissao_ajustes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/carvia/services/financeiro/comissao_service.py tests/carvia/test_comissao_ajustes.py
git commit -m "feat(carvia): cancela ajustes ao excluir CTe + guards de comissao negativa"
```

---

## Task 8: Hooks de disparo (editar_cte_valor, cancelamento direto, cascade)

**Files:**
- Modify: `app/carvia/routes/operacao_routes.py` (`editar_cte_valor` ~1318-1325; cancelamento ~880)
- Modify: `app/carvia/services/documentos/operacao_cancel_service.py` (~304)
- Test: `tests/carvia/test_comissao_ajustes.py`

- [ ] **Step 1: Teste de integração do disparo (chamando o service de cancelamento direto via estado)**

```python
def test_hook_cancelamento_gera_debito_via_sincronizar(db):
    # Garante que apos cancelar (status CANCELADO) + sincronizar(0), ha debito.
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    from app.carvia.models.comissao import CarviaComissaoAjuste
    u = _criar_usuario(db)
    op = _criar_op(db, cte_valor='1000.00')
    f = _criar_fechamento(db, u, [op])
    op.status = 'CANCELADO'
    db.session.flush()
    ComissaoService.sincronizar_ajustes_cte(op.id, 0, 'CANCELAMENTO_CTE', 'test')
    debitos = CarviaComissaoAjuste.query.filter_by(operacao_id=op.id, motivo='CANCELAMENTO_CTE').all()
    assert len(debitos) == 1 and debitos[0].delta_comissao == Decimal('-50.00')
```

(Este teste valida o contrato que os hooks invocam. Os hooks em si são wiring de 3 linhas verificado por inspeção + smoke manual da rota.)

- [ ] **Step 2: Rodar e ver passar** (já passa — valida o contrato)

Run: `pytest tests/carvia/test_comissao_ajustes.py::test_hook_cancelamento_gera_debito_via_sincronizar -v`
Expected: PASS

- [ ] **Step 3: Wiring em `editar_cte_valor`** — em `operacao_routes.py`, no `try` (após `operacao.cte_valor = cte_valor`, linha 1320, antes de `db.session.commit()`):

```python
            operacao.cte_valor = cte_valor

            # Consistencia de comissao: gera ajuste (debito/credito) se o CTe ja
            # foi comissionado em algum fechamento ativo (lazy import — R2).
            from app.carvia.services.financeiro.comissao_service import ComissaoService
            ComissaoService.sincronizar_ajustes_cte(
                operacao_id, cte_valor, 'ALTERACAO_VALOR', current_user.email,
            )

            db.session.commit()
```

- [ ] **Step 4: Wiring no cancelamento direto** — em `operacao_routes.py`, após `operacao.status = 'CANCELADO'` (linha 880), antes de `db.session.commit()`:

```python
            operacao.status = 'CANCELADO'
            from app.carvia.services.financeiro.comissao_service import ComissaoService
            ComissaoService.sincronizar_ajustes_cte(
                operacao_id, 0, 'CANCELAMENTO_CTE', current_user.email,
            )
            db.session.commit()
```

- [ ] **Step 5: Wiring no cascade** — em `operacao_cancel_service.py`, após `op.status = 'CANCELADO'` (linha 304):

```python
                op.status = 'CANCELADO'
                from app.carvia.services.financeiro.comissao_service import ComissaoService
                ComissaoService.sincronizar_ajustes_cte(
                    operacao_id, 0, 'CANCELAMENTO_CTE', usuario,
                )
                resultado['cancelados']['operacao'] = operacao_id
```

> O cascade NÃO comita aqui (commit atômico mais abaixo) — `sincronizar_ajustes_cte` faz `flush`, integrando na transação. A rota `:880` e o cascade são caminhos distintos (sem disparo duplicado); ainda assim `sincronizar` é idempotente (delta 0 não cria).

- [ ] **Step 6: Smoke da suíte CarVia**

Run: `pytest tests/carvia/ -q`
Expected: PASS (sem regressões)

- [ ] **Step 7: Commit**

```bash
git add app/carvia/routes/operacao_routes.py app/carvia/services/documentos/operacao_cancel_service.py tests/carvia/test_comissao_ajustes.py
git commit -m "feat(carvia): disparo de ajuste de comissao em editar_cte_valor e cancelamento (direto+cascade)"
```

---

## Task 9: Rotas de comissão (vendedor select, data de corte, ajustes pendentes, vincular-vendedor)

**Files:**
- Modify: `app/carvia/routes/comissao_routes.py` (`criar_comissao` ~91-169; `api_ctes_elegiveis` ~310-350)
- Modify: `app/carvia/services/financeiro/comissao_service.py` (novo `vincular_vendedor`)

- [ ] **Step 1: `vincular_vendedor` no service** (adicionar em `ComissaoService`)

```python
    @staticmethod
    def vincular_vendedor(fechamento_id, usuario_id, editado_por):
        """Vincula um Usuario a um fechamento (correcao de metadado, qualquer status).
        Atualiza snapshot e faz ajustes orfaos deste fechamento herdarem o vinculo."""
        from app.carvia.models.comissao import (
            CarviaComissaoFechamento, CarviaComissaoAjuste,
        )
        from app.auth.models import Usuario

        fechamento = db.session.get(CarviaComissaoFechamento, fechamento_id)
        if not fechamento:
            raise ValueError('Fechamento nao encontrado.')
        usuario = db.session.get(Usuario, usuario_id) if usuario_id else None
        if not usuario:
            raise ValueError('Usuario nao encontrado.')

        fechamento.vendedor_usuario_id = usuario.id
        fechamento.vendedor_nome = usuario.nome
        fechamento.vendedor_email = usuario.email

        CarviaComissaoAjuste.query.filter_by(
            fechamento_origem_id=fechamento_id, vendedor_usuario_id=None,
        ).update({
            'vendedor_usuario_id': usuario.id,
            'vendedor_nome': usuario.nome,
            'vendedor_email': usuario.email,
        })
        db.session.commit()
        logger.info(
            "Comissao %s vinculada ao usuario #%d por %s",
            fechamento.numero_fechamento, usuario.id, editado_por,
        )
        return fechamento
```

- [ ] **Step 2: `criar_comissao` — POST por `vendedor_usuario_id` + data de corte; GET popula usuários**

Substituir o corpo POST (linhas 110-141) e o `render_template` final. Bloco POST:

```python
        if request.method == 'POST':
            vendedor_usuario_id = request.form.get('vendedor_usuario_id', '').strip()
            data_fim_str = request.form.get('data_fim', '').strip()
            percentual_str = request.form.get('percentual', '').strip()
            observacoes = request.form.get('observacoes', '').strip()
            operacao_ids_raw = request.form.getlist('operacao_ids')

            if not vendedor_usuario_id:
                flash('Selecione o vendedor.', 'warning')
                return redirect(url_for('carvia.criar_comissao'))
            if not data_fim_str:
                flash('Data de corte e obrigatoria.', 'warning')
                return redirect(url_for('carvia.criar_comissao'))
            if not operacao_ids_raw:
                flash('Selecione ao menos um CTe.', 'warning')
                return redirect(url_for('carvia.criar_comissao'))

            try:
                data_fim = date.fromisoformat(data_fim_str)
                percentual = Decimal(percentual_str.replace(',', '.')) if percentual_str else None
                operacao_ids = [int(x) for x in operacao_ids_raw]

                fechamento = ComissaoService.criar_fechamento(
                    vendedor_usuario_id=int(vendedor_usuario_id),
                    data_fim=data_fim,
                    operacao_ids=operacao_ids,
                    criado_por=current_user.email,
                    percentual=percentual,
                    observacoes=observacoes,
                )
                flash(
                    f'Comissao {fechamento.numero_fechamento} criada: '
                    f'{fechamento.qtd_ctes} CTes, R$ {fechamento.total_comissao:,.2f}',
                    'success',
                )
                return redirect(url_for('carvia.detalhe_comissao', comissao_id=fechamento.id))
            except ValueError as ve:
                flash(str(ve), 'warning')
            except Exception as e:
                db.session.rollback()
                logger.error("Erro ao criar comissao: %s", e)
                flash(f'Erro: {e}', 'danger')
```

E o `render_template` final passa a popular a lista de vendedores:

```python
        from app.auth.models import Usuario
        vendedores = Usuario.query.filter_by(
            acesso_comissao_carvia=True, status='ativo',
        ).order_by(Usuario.nome).all()
        return render_template(
            'carvia/comissoes/criar.html',
            pct_display=pct_display, pct_warning=pct_warning,
            vendedores=vendedores,
        )
```

- [ ] **Step 3: `api_ctes_elegiveis` — data_fim obrigatório, data_inicio opcional**

Substituir as linhas 319-331:

```python
        data_fim_str = request.args.get('data_fim', '')
        data_inicio_str = request.args.get('data_inicio', '')
        if not data_fim_str:
            return jsonify({'erro': 'data_fim obrigatorio.'}), 400
        try:
            data_fim = date.fromisoformat(data_fim_str)
            data_inicio = date.fromisoformat(data_inicio_str) if data_inicio_str else None
        except ValueError:
            return jsonify({'erro': 'Formato de data invalido (YYYY-MM-DD).'}), 400

        ctes = ComissaoService.buscar_ctes_elegiveis(data_fim, data_inicio)
```

- [ ] **Step 4: Novo endpoint API ajustes pendentes** (após `api_ctes_elegiveis`)

```python
    @bp.route('/api/comissoes/ajustes-pendentes')  # type: ignore
    @login_required
    def api_ajustes_pendentes():  # type: ignore
        """Ajustes PENDENTE de um vendedor (para preview na criacao)."""
        if not _pode_acessar_comissao():
            return jsonify({'erro': 'Acesso negado.'}), 403
        from app.carvia.models.comissao import CarviaComissaoAjuste
        vid = request.args.get('vendedor_usuario_id', type=int)
        if not vid:
            return jsonify({'sucesso': True, 'qtd': 0, 'total_delta': 0, 'ajustes': []})
        ajustes = CarviaComissaoAjuste.query.filter_by(
            vendedor_usuario_id=vid, status='PENDENTE',
        ).all()
        return jsonify({
            'sucesso': True, 'qtd': len(ajustes),
            'total_delta': float(sum(a.delta_comissao for a in ajustes)) if ajustes else 0,
            'ajustes': [{
                'id': a.id, 'cte_numero': a.cte_numero, 'motivo': a.motivo,
                'delta_comissao': float(a.delta_comissao),
                'fechamento_origem_id': a.fechamento_origem_id,
            } for a in ajustes],
        })
```

- [ ] **Step 5: Novo endpoint vincular-vendedor** (após `api_ajustes_pendentes`)

```python
    @bp.route('/comissoes/<int:comissao_id>/vincular-vendedor', methods=['POST'])  # type: ignore
    @login_required
    def vincular_vendedor_comissao(comissao_id):  # type: ignore
        """Vincula um Usuario a um fechamento sem vinculo (resolucao manual)."""
        if not _pode_acessar_comissao():
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))
        from app.carvia.services.financeiro.comissao_service import ComissaoService
        usuario_id = request.form.get('vendedor_usuario_id', type=int)
        try:
            ComissaoService.vincular_vendedor(comissao_id, usuario_id, current_user.email)
            flash('Vendedor vinculado.', 'success')
        except ValueError as ve:
            flash(str(ve), 'warning')
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao vincular vendedor comissao %d: %s", comissao_id, e)
            flash(f'Erro: {e}', 'danger')
        return redirect(url_for('carvia.detalhe_comissao', comissao_id=comissao_id))
```

- [ ] **Step 6: Smoke import** — Run: `python -c "from app import create_app; create_app()"` — Expected: sem ImportError (blueprint registra).

- [ ] **Step 7: Commit**

```bash
git add app/carvia/routes/comissao_routes.py app/carvia/services/financeiro/comissao_service.py
git commit -m "feat(carvia): rotas de comissao por vendedor_usuario_id + data de corte + ajustes pendentes + vincular-vendedor"
```

---

## Task 10: Templates (criar.html + detalhe.html)

**Files:**
- Modify: `app/templates/carvia/comissoes/criar.html`
- Modify: `app/templates/carvia/comissoes/detalhe.html`

- [ ] **Step 1: `criar.html` — vendedor vira select; remover data inicial e email**

Substituir o bloco de inputs (linhas 29-56) por:

```html
                    <div class="col-md-5">
                        <label for="vendedor_usuario_id" class="form-label">Vendedor *</label>
                        <select class="form-select" id="vendedor_usuario_id" name="vendedor_usuario_id"
                                required onchange="carregarAjustes()">
                            <option value="">Selecione...</option>
                            {% for v in vendedores %}
                            <option value="{{ v.id }}">{{ v.nome }} ({{ v.email }})</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label for="percentual" class="form-label">Percentual (%) *</label>
                        <input type="number" class="form-control" id="percentual" name="percentual"
                               step="any" min="0.0001" max="100" required
                               value="{{ pct_display if pct_display is not none else '' }}"
                               placeholder="Ex: 5.00">
                    </div>
                    <div class="col-md-4">
                        <label for="observacoes" class="form-label">Observacoes</label>
                        <input type="text" class="form-control" id="observacoes" name="observacoes" placeholder="Opcional">
                    </div>
                </div>
                <div class="row g-3 mt-1">
                    <div class="col-md-3">
                        <label for="data_fim" class="form-label">Comissoes ate (data de corte) *</label>
                        <input type="date" class="form-control" id="data_fim" name="data_fim" required>
                    </div>
                    <div class="col-md-2 d-flex align-items-end">
                        <button type="button" class="btn btn-outline-primary w-100" onclick="buscarCtes()">
                            <i class="fas fa-search"></i> Buscar CTes
                        </button>
                    </div>
                    <div class="col-md-7 d-flex align-items-end">
                        <div id="painelAjustes" class="text-muted small"></div>
                    </div>
```

- [ ] **Step 2: `criar.html` — JS: buscar só por data_fim + painel de ajustes**

No bloco `<script>`, substituir `buscarCtes()` (linhas 114-132) e adicionar `carregarAjustes()`:

```javascript
let ajustesTotal = 0;

function buscarCtes() {
    const fim = document.getElementById('data_fim').value;
    if (!fim) { alert('Informe a data de corte.'); return; }
    const url = `/carvia/api/comissoes/ctes-elegiveis?data_fim=${fim}`;
    fetch(url, { headers: { 'X-CSRFToken': csrfToken } })
        .then(r => r.json())
        .then(data => {
            if (data.erro) { alert(data.erro); return; }
            ctesData = data.ctes || [];
            renderCtes();
        })
        .catch(err => alert('Erro: ' + err.message));
}

function carregarAjustes() {
    const vid = document.getElementById('vendedor_usuario_id').value;
    const painel = document.getElementById('painelAjustes');
    ajustesTotal = 0;
    if (!vid) { painel.innerHTML = ''; atualizarResumo(); return; }
    fetch(`/carvia/api/comissoes/ajustes-pendentes?vendedor_usuario_id=${vid}`, { headers: { 'X-CSRFToken': csrfToken } })
        .then(r => r.json())
        .then(data => {
            ajustesTotal = data.total_delta || 0;
            if (data.qtd > 0) {
                const fmt = ajustesTotal.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
                painel.innerHTML = `<i class="fas fa-info-circle"></i> ${data.qtd} ajuste(s) pendente(s) deste vendedor: <strong>${fmt}</strong> (incorporado ao total).`;
            } else { painel.innerHTML = ''; }
            atualizarResumo();
        });
}
```

E em `atualizarResumo()`, após calcular `totalComissao` (linha 193), incorporar os ajustes e bloquear submit se negativo:

```javascript
    const totalComissao = totalBruto * pct / 100 + ajustesTotal;
    const submitBtn = document.querySelector('#cardResumo button[type="submit"]');
    if (submitBtn) submitBtn.disabled = totalComissao < 0;
```

(O `resumoComissao` exibe `totalComissao`, já com ajustes.)

- [ ] **Step 3: `detalhe.html` — seção de ajustes incorporados + vínculo de vendedor**

Adicionar (após a seção de CTes; usar `fechamento`/objeto do contexto — confirmar nome da variável no `detalhe_comissao`). Bloco de vínculo quando sem usuário:

```html
{% if not comissao.vendedor_usuario_id %}
<div class="card mb-3 border-warning">
  <div class="card-header bg-warning-subtle"><strong>Vincular vendedor (usuario)</strong></div>
  <div class="card-body">
    <form method="POST" action="{{ url_for('carvia.vincular_vendedor_comissao', comissao_id=comissao.id) }}" class="row g-2">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="col-md-8">
        <select name="vendedor_usuario_id" class="form-select" required>
          <option value="">Selecione o usuario...</option>
          {% for v in vendedores %}<option value="{{ v.id }}">{{ v.nome }} ({{ v.email }})</option>{% endfor %}
        </select>
      </div>
      <div class="col-md-4"><button class="btn btn-warning w-100">Vincular</button></div>
    </form>
  </div>
</div>
{% endif %}

{% if ajustes %}
<div class="card mb-3">
  <div class="card-header"><strong>Ajustes incorporados</strong>
    <span class="float-end">Total ajustes: <strong>R$ {{ '%.2f'|format(comissao.total_ajustes or 0) }}</strong></span>
  </div>
  <div class="card-body p-0">
    <table class="table mb-0 carvia-table">
      <thead><tr><th>CTe</th><th>Motivo</th><th class="text-end">Delta</th><th>Origem</th></tr></thead>
      <tbody>
        {% for a in ajustes %}
        <tr>
          <td>{{ a.cte_numero }}</td>
          <td>{{ a.motivo }}</td>
          <td class="text-end {{ 'text-success' if a.delta_comissao >= 0 else 'text-danger' }}">R$ {{ '%.2f'|format(a.delta_comissao) }}</td>
          <td>#{{ a.fechamento_origem_id }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endif %}
```

- [ ] **Step 4: Passar `ajustes` e `vendedores` ao `detalhe_comissao`** — em `comissao_routes.py`, na view `detalhe_comissao`, antes do `render_template`, adicionar:

```python
        from app.carvia.models.comissao import CarviaComissaoAjuste
        from app.auth.models import Usuario
        ajustes = CarviaComissaoAjuste.query.filter_by(
            fechamento_aplicado_id=comissao_id,
        ).order_by(CarviaComissaoAjuste.id).all()
        vendedores = Usuario.query.filter_by(
            acesso_comissao_carvia=True, status='ativo',
        ).order_by(Usuario.nome).all()
```

E incluir `ajustes=ajustes, vendedores=vendedores` no `render_template` do detalhe. (Confirmar o nome da variável do fechamento no template — usar o mesmo, ex.: `comissao`.)

- [ ] **Step 5: Smoke visual** — `python run.py`, abrir `/carvia/comissoes/criar`: select de vendedor presente, só data de corte; selecionar vendedor mostra painel de ajustes. Detalhe mostra seção de ajustes.

- [ ] **Step 6: Commit**

```bash
git add app/templates/carvia/comissoes/criar.html app/templates/carvia/comissoes/detalhe.html app/carvia/routes/comissao_routes.py
git commit -m "feat(carvia): UI comissao — select de vendedor, data de corte, painel/seção de ajustes, vínculo manual"
```

---

## Task 11: Export de comissões reflete ajustes

**Files:**
- Modify: `app/carvia/routes/exportacao_routes.py` (`exportar_comissoes`, ~1776-1790)

- [ ] **Step 1: Adicionar coluna "Total Ajustes"** — no dict `fechamentos_data` (após `'Total Comissao'`):

```python
                'Total Ajustes': float(f.total_ajustes or 0),
                'Total Comissao': float(f.total_comissao or 0),  # ja inclui ajustes
```

(`'Total Comissao'` já reflete o total final, pois `recalcular_totais` soma ajustes; a coluna nova dá transparência do componente.)

- [ ] **Step 2: Smoke** — abrir `/carvia/api/exportar/comissoes` (logado com acesso): Excel baixa, coluna "Total Ajustes" presente.

- [ ] **Step 3: Commit**

```bash
git add app/carvia/routes/exportacao_routes.py
git commit -m "feat(carvia): export de comissoes exibe Total Ajustes"
```

---

## Final: suíte + verificação

- [ ] Run: `pytest tests/carvia/ -q` — Expected: PASS.
- [ ] Run: `pytest tests/carvia/test_comissao_ajustes.py -v` — Expected: todos PASS.
- [ ] Conferir checklist do spec §7 (route/API, imports lazy, migration DDL+Python, validações front+back).
- [ ] Finalizar via superpowers:finishing-a-development-branch (PR/merge conforme preferência).

---

## Self-review (preenchido pelo autor do plano)

**Cobertura do spec:** §1 (model+colunas)→T1; recalcular_totais §2.3→T2; sincronizar §2.1→T3; incorporar+guard §2.2/§2.5→T4; criar_fechamento+vendedor §2.2/§Decisão4→T5; data de corte §2.4/§3-filtro→T6; guards excluir/pago + cancelar ajustes §2.5/§6→T7; hooks §3→T8; rotas+vincular §4.1/4.2/4.4→T9; templates §4.1/4.3/4.4→T10; export §8→T11. **Sem gaps.**

**Type consistency:** `sincronizar_ajustes_cte`, `_incorporar_ajustes_pendentes`, `_montar_fechamento`, `criar_fechamento(vendedor_usuario_id, data_fim, operacao_ids, criado_por, percentual, observacoes)`, `buscar_ctes_elegiveis(data_fim, data_inicio=None)`, `vincular_vendedor(fechamento_id, usuario_id, editado_por)` — nomes e assinaturas idênticos entre tarefas. Campos do model conferem com a migration.

**Pontos a confirmar na execução (não bloqueiam o plano):** nome da variável do fechamento no `detalhe.html` (assumido `comissao`); ausência de outros callers posicionais de `buscar_ctes_elegiveis` (grep no T6 Step 4).
