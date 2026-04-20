# CarVia: Migracao de conferencia de Sub para Frete (Escopo C)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) ou superpowers:executing-plans. Steps usam checkbox (`- [ ]`) para tracking.
>
> Este plano e **auto-contido** — cada task tem codigo literal com linhas exatas. Subagentes podem executar individualmente sem contexto externo alem deste arquivo.

**Goal:** Fazer CarviaFrete ser o eixo UNICO de conferencia (paridade total com Frete Nacom), removendo TODOS os campos de conferencia de CarviaSubcontrato e refatorando servicos, rotas, templates e modelos relacionados.

**Architecture:** Sub vira "documento CTe puro" (cte_numero, cte_valor, valor_cotado, valor_acertado, tabela_frete_id, frete_id). Frete ganha todos os campos de conferencia (status_conferencia, conferido_por/em, valor_considerado, valor_pago, detalhes_conferencia, requer_aprovacao). Tabela `carvia_aprovacoes_subcontrato` vira `carvia_aprovacoes_frete` com FK `frete_id`. Tabela `carvia_conta_corrente_transportadoras` ganha `frete_id` (drop `subcontrato_id`). ConferenciaService, AprovacaoFreteService (renomeado), ContaCorrenteService, aprovacao_routes, fatura_routes e templates migram para ler/escrever no Frete.

**Tech Stack:** Flask + SQLAlchemy + PostgreSQL. Migrations via `scripts/migrations/*.{py,sql}`.

---

## Phase 1 — Reversao de mudancas parciais da sessao anterior

### Task 1.1: Remover 3 metodos dinamicos de CarviaSubcontrato

**Files:**
- Modify: `app/carvia/models/documentos.py` (remover linhas 713-802)

- [ ] **Step 1: Ler o contexto ao redor do bloco a remover**

Confirmar que o bloco alvo existe. Run:
```bash
sed -n '710,810p' app/carvia/models/documentos.py
```
Expected: ver comentario `# Metodos dinamicos de divergencia (paridade Frete Nacom)` seguido dos 3 metodos `diferenca_considerado_pago`, `classificacao_valor_pago_considerado`, `requer_aprovacao_por_valor`, terminando antes de `def __repr__`.

- [ ] **Step 2: Aplicar a edicao**

Use Edit tool com old_string:
```python
    # ------------------------------------------------------------------
    # Metodos dinamicos de divergencia (paridade Frete Nacom)
    # Ref: app/fretes/models.py::Frete linhas 115-174
    # ------------------------------------------------------------------
    def diferenca_considerado_pago(self):
        """Diferenca valor_pago - valor_considerado (para conta corrente).
        Paridade Frete.diferenca_considerado_pago() linha 115.
        """
        if self.valor_pago is not None and self.valor_considerado is not None:
            return float(self.valor_pago) - float(self.valor_considerado)
        return 0

    def classificacao_valor_pago_considerado(self):
        """Classifica a relacao entre valor pago e considerado.
        Paridade Frete.classificacao_valor_pago_considerado() linha 121.
        """
        if self.valor_pago is None or self.valor_considerado is None:
            return ""
        vp = float(self.valor_pago)
        vc = float(self.valor_considerado)
        if vp < vc:
            return "Valor abaixo da tabela"
        elif vp > vc:
            return "Transportadora deve para o Nacom"
        return "Valores iguais"

    def requer_aprovacao_por_valor(self):
        """Verifica se requer aprovacao baseado em diferencas > R$ 5,00.

        Regras (espelho de Frete.requer_aprovacao_por_valor linhas 145-174):
        - Regra A: |valor_considerado - valor_pago| > R$ 5,00
        - Regra B: |valor_considerado - valor_cotado| > R$ 5,00

        Returns:
            tuple(bool, list[str]): (requer, motivos)
        """
        requer = False
        motivos = []

        # Regra A: considerado vs pago
        if self.valor_considerado is not None and self.valor_pago is not None:
            vc = float(self.valor_considerado)
            vp = float(self.valor_pago)
            diff = abs(vc - vp)
            if diff > 5.00:
                requer = True
                if vp > vc:
                    motivos.append(
                        f"Valor Pago (R$ {vp:.2f}) superior ao "
                        f"Considerado (R$ {vc:.2f}) em R$ {diff:.2f}"
                    )
                else:
                    motivos.append(
                        f"Valor Considerado (R$ {vc:.2f}) superior ao "
                        f"Pago (R$ {vp:.2f}) em R$ {diff:.2f}"
                    )

        # Regra B: considerado vs cotado
        if self.valor_considerado is not None and self.valor_cotado is not None:
            vc = float(self.valor_considerado)
            vco = float(self.valor_cotado)
            diff = abs(vc - vco)
            if diff > 5.00:
                requer = True
                if vc > vco:
                    motivos.append(
                        f"Valor Considerado (R$ {vc:.2f}) superior ao "
                        f"Cotado (R$ {vco:.2f}) em R$ {diff:.2f}"
                    )
                else:
                    motivos.append(
                        f"Valor Cotado (R$ {vco:.2f}) superior ao "
                        f"Considerado (R$ {vc:.2f}) em R$ {diff:.2f}"
                    )

        return requer, motivos

    def __repr__(self):
```

new_string:
```python
    def __repr__(self):
```

- [ ] **Step 3: Verificar compile**

```bash
python -m py_compile app/carvia/models/documentos.py
```
Expected: sem output (success).

- [ ] **Step 4: Commit**

```bash
git add app/carvia/models/documentos.py
git commit -m "refactor(carvia): reverter metodos dinamicos de Sub (serao em Frete)"
```

---

### Task 1.2: Reverter sync frete→sub em editar_frete_carvia

**Files:**
- Modify: `app/carvia/routes/frete_routes.py:332-348`

- [ ] **Step 1: Aplicar Edit**

old_string:
```python
                # Sincronizar CarviaFrete → CarviaSubcontrato
                if sub:
                    if frete.valor_cte:
                        sub.cte_valor = frete.valor_cte
                        sub.valor_acertado = frete.valor_cte
                    if frete.valor_considerado:
                        sub.valor_considerado = frete.valor_considerado
                    # Sincronizar valor_pago tambem (paridade Nacom).
                    # Garante que os 2 caminhos de preenchimento (form de editar
                    # Frete e endpoint registrar_pagamento_subcontrato) resultem
                    # no mesmo estado. Corrige bug latente onde valor_pago era
                    # persistido so em CarviaFrete.
                    if frete.valor_pago is not None:
                        from app.utils.timezone import agora_utc_naive as _agora
                        sub.valor_pago = frete.valor_pago
                        sub.valor_pago_em = _agora()
                        sub.valor_pago_por = current_user.email
```

new_string:
```python
                # Sincronizar CarviaFrete → CarviaSubcontrato (somente CTe)
                # Phase C: valor_considerado/valor_pago foram migrados para
                # Frete como fonte unica — nao sincronizamos mais para Sub.
                if sub and frete.valor_cte:
                    sub.cte_valor = frete.valor_cte
                    sub.valor_acertado = frete.valor_cte
```

- [ ] **Step 2: Verificar compile**

```bash
python -m py_compile app/carvia/routes/frete_routes.py
```

- [ ] **Step 3: Commit**

```bash
git add app/carvia/routes/frete_routes.py
git commit -m "refactor(carvia): remove sync valor_considerado/pago frete->sub"
```

---

### Task 1.3: Reverter parametro valor_pago em ConferenciaService.registrar_conferencia

**Files:**
- Modify: `app/carvia/services/documentos/conferencia_service.py:219-222, 290-297`

NOTA: esta task apenas reverte as pequenas mudancas anteriores. O service inteiro sera refatorado na Phase 8 (migrar para operar em Frete).

- [ ] **Step 1: Reverter assinatura**

old_string:
```python
    def registrar_conferencia(self, subcontrato_id: int, valor_considerado: float,
                               status: str, usuario: str,
                               observacoes: str = None,
                               valor_pago: float = None) -> Dict:
        """
        Registra conferencia de um subcontrato.

        REFATOR D4 (.claude/plans/wobbly-tumbling-treasure.md):
        Quando o conferente decide DIVERGENTE, o status_conferencia NAO vai
        direto para 'DIVERGENTE'. Em vez disso, uma CarviaAprovacaoSubcontrato
        PENDENTE e criada via AprovacaoSubcontratoService, e o sub fica com
        status_conferencia='PENDENTE' + requer_aprovacao=True ate o aprovador
        decidir. APROVADO continua sendo gravado direto.

        Quando APROVADO: tambem se verifica se a diferenca considerado-cotado
        esta dentro da tolerancia — se nao estiver, abre tratativa mesmo com
        intencao de APROVAR (evita lancamentos em CC sem aprovacao explicita).

        Paridade Nacom (Frete.valor_pago): Quando `valor_pago` e informado,
        grava junto com `valor_considerado` e dispara a Regra C do
        AprovacaoSubcontratoService (|pago - considerado| > R$5).

        Args:
            subcontrato_id: ID do CarviaSubcontrato
            valor_considerado: Valor registrado pelo conferente
            status: APROVADO ou DIVERGENTE (decisao inicial do conferente)
            usuario: Email do conferente
            observacoes: Texto opcional
            valor_pago: Valor efetivamente pago (opcional — paridade Nacom)

        Returns:
            Dict com sucesso, status_conferencia (pode diferir do solicitado
            se virou tratativa), fatura_atualizada, fatura_status,
            tratativa_aberta (bool), aprovacao_id (se tratativa).
        """
```

new_string:
```python
    def registrar_conferencia(self, subcontrato_id: int, valor_considerado: float,
                               status: str, usuario: str,
                               observacoes: str = None) -> Dict:
        """
        Registra conferencia de um subcontrato.

        REFATOR D4 (.claude/plans/wobbly-tumbling-treasure.md):
        Quando o conferente decide DIVERGENTE, o status_conferencia NAO vai
        direto para 'DIVERGENTE'. Em vez disso, uma CarviaAprovacaoSubcontrato
        PENDENTE e criada via AprovacaoSubcontratoService, e o sub fica com
        status_conferencia='PENDENTE' + requer_aprovacao=True ate o aprovador
        decidir. APROVADO continua sendo gravado direto.

        Quando APROVADO: tambem se verifica se a diferenca considerado-cotado
        esta dentro da tolerancia — se nao estiver, abre tratativa mesmo com
        intencao de APROVAR (evita lancamentos em CC sem aprovacao explicita).

        NOTA (2026-04-14): este service sera refatorado na Phase 8 deste plano
        para operar em CarviaFrete. Esta reversao e temporaria.

        Args:
            subcontrato_id: ID do CarviaSubcontrato
            valor_considerado: Valor registrado pelo conferente
            status: APROVADO ou DIVERGENTE (decisao inicial do conferente)
            usuario: Email do conferente
            observacoes: Texto opcional

        Returns:
            Dict com sucesso, status_conferencia (pode diferir do solicitado
            se virou tratativa), fatura_atualizada, fatura_status,
            tratativa_aberta (bool), aprovacao_id (se tratativa).
        """
```

- [ ] **Step 2: Remover persistencia em sub.valor_pago**

old_string:
```python
            sub.valor_considerado = valor_considerado
            sub.conferido_por = usuario
            sub.conferido_em = agora_utc_naive()
            sub.detalhes_conferencia = snapshot

            # Paridade Nacom: grava valor_pago junto (opcional).
            # Flush no mesmo commit da conferencia — necessario para que a
            # Regra C do AprovacaoSubcontratoService (|pago - considerado| > R$5)
            # seja acionada corretamente abaixo.
            if valor_pago is not None:
                sub.valor_pago = valor_pago
                sub.valor_pago_em = agora_utc_naive()
                sub.valor_pago_por = usuario

            if observacoes:
```

new_string:
```python
            sub.valor_considerado = valor_considerado
            sub.conferido_por = usuario
            sub.conferido_em = agora_utc_naive()
            sub.detalhes_conferencia = snapshot

            if observacoes:
```

- [ ] **Step 3: Verificar compile**

```bash
python -m py_compile app/carvia/services/documentos/conferencia_service.py
```

- [ ] **Step 4: Commit**

```bash
git add app/carvia/services/documentos/conferencia_service.py
git commit -m "refactor(carvia): reverter parametro valor_pago em ConferenciaService"
```

---

### Task 1.4: Deletar backfill script obsoleto

**Files:**
- Delete: `scripts/migrations/backfill_carvia_sub_valor_pago.py`

- [ ] **Step 1: Deletar arquivo**

```bash
rm scripts/migrations/backfill_carvia_sub_valor_pago.py
```

- [ ] **Step 2: Commit**

```bash
git add -u scripts/migrations/backfill_carvia_sub_valor_pago.py
git commit -m "chore(carvia): remove backfill sub.valor_pago (obsoleto)"
```

---

## Phase 2 — Adicionar campos e metodos de conferencia em CarviaFrete

### Task 2.1: Adicionar 5 campos de conferencia em CarviaFrete

**Files:**
- Modify: `app/carvia/models/frete.py` (apos linha 103, antes de `criado_em`)

- [ ] **Step 1: Aplicar Edit**

old_string:
```python
    # --- Status: PENDENTE -> CONFERIDO -> FATURADO ---
    status = db.Column(db.String(20), default='PENDENTE', index=True)

    # --- Auditoria ---
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
```

new_string:
```python
    # --- Status: PENDENTE -> CONFERIDO -> FATURADO ---
    status = db.Column(db.String(20), default='PENDENTE', index=True)

    # --- Conferencia (paridade Nacom Frete + FaturaFrete.status_conferencia) ---
    # Migrado de CarviaSubcontrato em 2026-04-14 (Frete = CTe analisado).
    status_conferencia = db.Column(
        db.String(20), nullable=False, default='PENDENTE', index=True
    )  # PENDENTE | APROVADO | DIVERGENTE
    conferido_por = db.Column(db.String(100), nullable=True)
    conferido_em = db.Column(db.DateTime, nullable=True)
    detalhes_conferencia = db.Column(db.JSON, nullable=True)
    # Flag de tratativa: True quando existe CarviaAprovacaoFrete PENDENTE
    requer_aprovacao = db.Column(db.Boolean, nullable=False, default=False)

    # --- Auditoria ---
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
```

- [ ] **Step 2: Verificar compile**

```bash
python -m py_compile app/carvia/models/frete.py
```

- [ ] **Step 3: Commit**

```bash
git add app/carvia/models/frete.py
git commit -m "feat(carvia): CarviaFrete ganha 5 campos de conferencia"
```

---

### Task 2.2: Adicionar 3 metodos dinamicos em CarviaFrete

**Files:**
- Modify: `app/carvia/models/frete.py` (apos `margem_percentual` property, antes de `__repr__`)

- [ ] **Step 1: Aplicar Edit**

old_string:
```python
    @property
    def margem_percentual(self):
        """Margem percentual = (margem / venda) * 100."""
        if self.valor_venda and self.valor_venda > 0 and self.margem is not None:
            return (self.margem / self.valor_venda) * 100
        return None

    def __repr__(self):
        return (
            f'<CarviaFrete {self.id} emb={self.embarque_id} '
            f'{self.cnpj_emitente}->{self.cnpj_destino} ({self.status})>'
        )
```

new_string:
```python
    @property
    def margem_percentual(self):
        """Margem percentual = (margem / venda) * 100."""
        if self.valor_venda and self.valor_venda > 0 and self.margem is not None:
            return (self.margem / self.valor_venda) * 100
        return None

    # ------------------------------------------------------------------
    # Metodos dinamicos de divergencia (paridade Frete Nacom)
    # Ref: app/fretes/models.py::Frete linhas 115-174
    # ------------------------------------------------------------------
    def diferenca_considerado_pago(self):
        """Diferenca valor_pago - valor_considerado (para conta corrente)."""
        if self.valor_pago is not None and self.valor_considerado is not None:
            return float(self.valor_pago) - float(self.valor_considerado)
        return 0

    def classificacao_valor_pago_considerado(self):
        """Classifica a relacao entre valor pago e considerado."""
        if self.valor_pago is None or self.valor_considerado is None:
            return ""
        vp = float(self.valor_pago)
        vc = float(self.valor_considerado)
        if vp < vc:
            return "Valor abaixo da tabela"
        elif vp > vc:
            return "Transportadora deve para o Nacom"
        return "Valores iguais"

    def requer_aprovacao_por_valor(self):
        """Verifica se requer aprovacao baseado em diferencas > R$ 5,00.

        Regras (paridade Frete Nacom linhas 145-174):
        - Regra A: |valor_considerado - valor_pago| > R$ 5,00
        - Regra B: |valor_considerado - valor_cotado| > R$ 5,00

        Returns:
            tuple(bool, list[str]): (requer, motivos)
        """
        requer = False
        motivos = []

        if self.valor_considerado is not None and self.valor_pago is not None:
            vc = float(self.valor_considerado)
            vp = float(self.valor_pago)
            diff = abs(vc - vp)
            if diff > 5.00:
                requer = True
                if vp > vc:
                    motivos.append(
                        f"Valor Pago (R$ {vp:.2f}) superior ao "
                        f"Considerado (R$ {vc:.2f}) em R$ {diff:.2f}"
                    )
                else:
                    motivos.append(
                        f"Valor Considerado (R$ {vc:.2f}) superior ao "
                        f"Pago (R$ {vp:.2f}) em R$ {diff:.2f}"
                    )

        if self.valor_considerado is not None and self.valor_cotado is not None:
            vc = float(self.valor_considerado)
            vco = float(self.valor_cotado)
            diff = abs(vc - vco)
            if diff > 5.00:
                requer = True
                if vc > vco:
                    motivos.append(
                        f"Valor Considerado (R$ {vc:.2f}) superior ao "
                        f"Cotado (R$ {vco:.2f}) em R$ {diff:.2f}"
                    )
                else:
                    motivos.append(
                        f"Valor Cotado (R$ {vco:.2f}) superior ao "
                        f"Considerado (R$ {vc:.2f}) em R$ {diff:.2f}"
                    )

        return requer, motivos

    def __repr__(self):
        return (
            f'<CarviaFrete {self.id} emb={self.embarque_id} '
            f'{self.cnpj_emitente}->{self.cnpj_destino} ({self.status})>'
        )
```

- [ ] **Step 2: Verificar compile**

```bash
python -m py_compile app/carvia/models/frete.py
```

- [ ] **Step 3: Commit**

```bash
git add app/carvia/models/frete.py
git commit -m "feat(carvia): metodos dinamicos de divergencia em CarviaFrete"
```

---

## Phase 3 — Migration: add campos em carvia_fretes + backfill

### Task 3.1: Criar arquivo SQL idempotente

**Files:**
- Create: `scripts/migrations/carvia_frete_conferencia_fields.sql`

- [ ] **Step 1: Criar arquivo**

Use Write tool com path `scripts/migrations/carvia_frete_conferencia_fields.sql` e conteudo:

```sql
-- Migration: Add campos de conferencia em carvia_fretes (Escopo C refactor)
-- Data: 2026-04-14
-- Ref: docs/superpowers/plans/2026-04-14-carvia-frete-conferencia-migration.md

-- 1. Adicionar 5 colunas idempotente
ALTER TABLE carvia_fretes
  ADD COLUMN IF NOT EXISTS status_conferencia VARCHAR(20) NOT NULL DEFAULT 'PENDENTE';

ALTER TABLE carvia_fretes
  ADD COLUMN IF NOT EXISTS conferido_por VARCHAR(100);

ALTER TABLE carvia_fretes
  ADD COLUMN IF NOT EXISTS conferido_em TIMESTAMP;

ALTER TABLE carvia_fretes
  ADD COLUMN IF NOT EXISTS detalhes_conferencia JSON;

ALTER TABLE carvia_fretes
  ADD COLUMN IF NOT EXISTS requer_aprovacao BOOLEAN NOT NULL DEFAULT FALSE;

-- 2. Index para status_conferencia
CREATE INDEX IF NOT EXISTS idx_carvia_fretes_status_conferencia
  ON carvia_fretes (status_conferencia);

-- 3. Backfill: consolidar status_conferencia dos subs para frete pai
-- Logica:
--   Se algum sub DIVERGENTE → frete DIVERGENTE
--   Se TODOS subs APROVADO → frete APROVADO
--   Senao → frete PENDENTE (default)
WITH consolidacao AS (
  SELECT
    s.frete_id,
    COUNT(*) AS total,
    SUM(CASE WHEN s.status_conferencia = 'APROVADO' THEN 1 ELSE 0 END) AS aprovados,
    SUM(CASE WHEN s.status_conferencia = 'DIVERGENTE' THEN 1 ELSE 0 END) AS divergentes,
    MAX(s.conferido_por) AS conferido_por_any,
    MAX(s.conferido_em) AS conferido_em_max,
    BOOL_OR(s.requer_aprovacao) AS algum_requer_aprovacao
  FROM carvia_subcontratos s
  WHERE s.frete_id IS NOT NULL
  GROUP BY s.frete_id
)
UPDATE carvia_fretes f
SET
  status_conferencia = CASE
    WHEN c.divergentes > 0 THEN 'DIVERGENTE'
    WHEN c.aprovados = c.total THEN 'APROVADO'
    ELSE 'PENDENTE'
  END,
  conferido_por = CASE WHEN c.aprovados = c.total THEN c.conferido_por_any ELSE NULL END,
  conferido_em  = CASE WHEN c.aprovados = c.total THEN c.conferido_em_max ELSE NULL END,
  requer_aprovacao = COALESCE(c.algum_requer_aprovacao, FALSE)
FROM consolidacao c
WHERE f.id = c.frete_id
  AND f.status_conferencia = 'PENDENTE';

-- 4. Backfill valor_considerado (agrega sum dos subs)
UPDATE carvia_fretes f
SET valor_considerado = COALESCE(f.valor_considerado, subtotal.soma)
FROM (
  SELECT frete_id, SUM(valor_considerado) AS soma
  FROM carvia_subcontratos
  WHERE frete_id IS NOT NULL AND valor_considerado IS NOT NULL
  GROUP BY frete_id
) subtotal
WHERE f.id = subtotal.frete_id
  AND f.valor_considerado IS NULL;

-- 5. Backfill valor_pago (agrega sum dos subs)
UPDATE carvia_fretes f
SET valor_pago = COALESCE(f.valor_pago, subtotal.soma)
FROM (
  SELECT frete_id, SUM(valor_pago) AS soma
  FROM carvia_subcontratos
  WHERE frete_id IS NOT NULL AND valor_pago IS NOT NULL
  GROUP BY frete_id
) subtotal
WHERE f.id = subtotal.frete_id
  AND f.valor_pago IS NULL;
```

- [ ] **Step 2: Commit**

```bash
git add scripts/migrations/carvia_frete_conferencia_fields.sql
git commit -m "feat(carvia): SQL add conferencia fields em carvia_fretes"
```

---

### Task 3.2: Criar Python runner

**Files:**
- Create: `scripts/migrations/carvia_frete_conferencia_fields.py`

- [ ] **Step 1: Criar arquivo**

Use Write tool com path `scripts/migrations/carvia_frete_conferencia_fields.py` e conteudo:

```python
"""Migration: Add campos de conferencia em carvia_fretes + backfill.

Data: 2026-04-14
Ref: docs/superpowers/plans/2026-04-14-carvia-frete-conferencia-migration.md
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run_migration():
    from app.carvia.models import CarviaFrete, CarviaSubcontrato

    print("=" * 70)
    print("MIGRATION: CarviaFrete ganha campos de conferencia")
    print("=" * 70)

    # ANTES
    total_fretes = CarviaFrete.query.count()
    total_subs = CarviaSubcontrato.query.count()
    subs_aprovados = CarviaSubcontrato.query.filter_by(
        status_conferencia='APROVADO'
    ).count()
    subs_divergentes = CarviaSubcontrato.query.filter_by(
        status_conferencia='DIVERGENTE'
    ).count()

    print(f"Total fretes: {total_fretes}")
    print(f"Total subs: {total_subs}")
    print(f"  Subs APROVADO: {subs_aprovados}")
    print(f"  Subs DIVERGENTE: {subs_divergentes}")
    print()

    # DDL
    sql_ddl = [
        """ALTER TABLE carvia_fretes
           ADD COLUMN IF NOT EXISTS status_conferencia VARCHAR(20)
           NOT NULL DEFAULT 'PENDENTE'""",
        """ALTER TABLE carvia_fretes
           ADD COLUMN IF NOT EXISTS conferido_por VARCHAR(100)""",
        """ALTER TABLE carvia_fretes
           ADD COLUMN IF NOT EXISTS conferido_em TIMESTAMP""",
        """ALTER TABLE carvia_fretes
           ADD COLUMN IF NOT EXISTS detalhes_conferencia JSON""",
        """ALTER TABLE carvia_fretes
           ADD COLUMN IF NOT EXISTS requer_aprovacao BOOLEAN
           NOT NULL DEFAULT FALSE""",
        """CREATE INDEX IF NOT EXISTS idx_carvia_fretes_status_conferencia
           ON carvia_fretes (status_conferencia)""",
    ]
    for sql in sql_ddl:
        print(f"Executando: {sql[:60]}...")
        db.session.execute(text(sql))
    db.session.commit()
    print("DDL concluido.")
    print()

    # Backfill 1: consolidar status_conferencia
    print("Backfill 1: consolidar status_conferencia sub → frete")
    result = db.session.execute(text("""
        WITH consolidacao AS (
          SELECT
            s.frete_id,
            COUNT(*) AS total,
            SUM(CASE WHEN s.status_conferencia = 'APROVADO' THEN 1 ELSE 0 END) AS aprovados,
            SUM(CASE WHEN s.status_conferencia = 'DIVERGENTE' THEN 1 ELSE 0 END) AS divergentes,
            MAX(s.conferido_por) AS conferido_por_any,
            MAX(s.conferido_em) AS conferido_em_max,
            BOOL_OR(s.requer_aprovacao) AS algum_requer_aprovacao
          FROM carvia_subcontratos s
          WHERE s.frete_id IS NOT NULL
          GROUP BY s.frete_id
        )
        UPDATE carvia_fretes f
        SET
          status_conferencia = CASE
            WHEN c.divergentes > 0 THEN 'DIVERGENTE'
            WHEN c.aprovados = c.total THEN 'APROVADO'
            ELSE 'PENDENTE'
          END,
          conferido_por = CASE WHEN c.aprovados = c.total THEN c.conferido_por_any ELSE NULL END,
          conferido_em  = CASE WHEN c.aprovados = c.total THEN c.conferido_em_max ELSE NULL END,
          requer_aprovacao = COALESCE(c.algum_requer_aprovacao, FALSE)
        FROM consolidacao c
        WHERE f.id = c.frete_id
          AND f.status_conferencia = 'PENDENTE'
    """))
    print(f"  Fretes atualizados: {result.rowcount}")

    # Backfill 2: valor_considerado agregado
    print("Backfill 2: valor_considerado agregado")
    result = db.session.execute(text("""
        UPDATE carvia_fretes f
        SET valor_considerado = COALESCE(f.valor_considerado, subtotal.soma)
        FROM (
          SELECT frete_id, SUM(valor_considerado) AS soma
          FROM carvia_subcontratos
          WHERE frete_id IS NOT NULL AND valor_considerado IS NOT NULL
          GROUP BY frete_id
        ) subtotal
        WHERE f.id = subtotal.frete_id
          AND f.valor_considerado IS NULL
    """))
    print(f"  Fretes atualizados: {result.rowcount}")

    # Backfill 3: valor_pago agregado
    print("Backfill 3: valor_pago agregado")
    result = db.session.execute(text("""
        UPDATE carvia_fretes f
        SET valor_pago = COALESCE(f.valor_pago, subtotal.soma)
        FROM (
          SELECT frete_id, SUM(valor_pago) AS soma
          FROM carvia_subcontratos
          WHERE frete_id IS NOT NULL AND valor_pago IS NOT NULL
          GROUP BY frete_id
        ) subtotal
        WHERE f.id = subtotal.frete_id
          AND f.valor_pago IS NULL
    """))
    print(f"  Fretes atualizados: {result.rowcount}")

    db.session.commit()
    print()

    # DEPOIS
    fretes_aprovados = CarviaFrete.query.filter_by(
        status_conferencia='APROVADO'
    ).count()
    fretes_divergentes = CarviaFrete.query.filter_by(
        status_conferencia='DIVERGENTE'
    ).count()
    print("=" * 70)
    print("RESULTADO")
    print("=" * 70)
    print(f"Fretes APROVADO: {fretes_aprovados}")
    print(f"Fretes DIVERGENTE: {fretes_divergentes}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        run_migration()
```

- [ ] **Step 2: Compile**

```bash
python -m py_compile scripts/migrations/carvia_frete_conferencia_fields.py
```

- [ ] **Step 3: Commit (SEM executar)**

```bash
git add scripts/migrations/carvia_frete_conferencia_fields.py
git commit -m "feat(carvia): Python runner migration campos conferencia frete"
```

> **IMPORTANTE**: NAO executar a migration ainda. Sera executada no final, apos todo o codigo estar migrado. Veja Phase 15.

---

## Phase 4 — Rename tabela aprovacoes (subcontrato → frete)

### Task 4.1: Criar SQL de rename tabela + FK

**Files:**
- Create: `scripts/migrations/carvia_aprovacoes_rename_frete.sql`

- [ ] **Step 1: Criar arquivo**

Use Write tool com path `scripts/migrations/carvia_aprovacoes_rename_frete.sql` e conteudo:

```sql
-- Migration: Rename carvia_aprovacoes_subcontrato → carvia_aprovacoes_frete
-- Trocar FK subcontrato_id → frete_id. Data: 2026-04-14

-- 1. Adicionar frete_id nullable
ALTER TABLE carvia_aprovacoes_subcontrato
  ADD COLUMN IF NOT EXISTS frete_id INTEGER REFERENCES carvia_fretes(id);

-- 2. Backfill frete_id via sub.frete_id
UPDATE carvia_aprovacoes_subcontrato aps
SET frete_id = s.frete_id
FROM carvia_subcontratos s
WHERE aps.subcontrato_id = s.id
  AND aps.frete_id IS NULL
  AND s.frete_id IS NOT NULL;

-- 3. Checar orfaos (registros sem frete_id apos backfill)
DO $$
DECLARE
  orfaos INT;
BEGIN
  SELECT COUNT(*) INTO orfaos
  FROM carvia_aprovacoes_subcontrato
  WHERE frete_id IS NULL;
  IF orfaos > 0 THEN
    RAISE NOTICE 'AVISO: % aprovacoes orfas — requer investigacao', orfaos;
  END IF;
END $$;

-- 4. Index em frete_id
CREATE INDEX IF NOT EXISTS idx_carvia_aprovacoes_frete_id
  ON carvia_aprovacoes_subcontrato (frete_id);

-- 5. Renomear tabela
ALTER TABLE IF EXISTS carvia_aprovacoes_subcontrato
  RENAME TO carvia_aprovacoes_frete;

-- 6. DROP coluna subcontrato_id (apos rename)
ALTER TABLE carvia_aprovacoes_frete
  DROP COLUMN IF EXISTS subcontrato_id;

-- 7. NOT NULL em frete_id (ultimo passo — requer que nao haja orfaos)
-- Comentado para permitir revisao manual dos orfaos se houver:
-- ALTER TABLE carvia_aprovacoes_frete
--   ALTER COLUMN frete_id SET NOT NULL;
```

- [ ] **Step 2: Commit**

```bash
git add scripts/migrations/carvia_aprovacoes_rename_frete.sql
git commit -m "feat(carvia): SQL rename aprovacoes subcontrato → frete"
```

---

### Task 4.2: Criar Python runner rename

**Files:**
- Create: `scripts/migrations/carvia_aprovacoes_rename_frete.py`

- [ ] **Step 1: Criar arquivo**

Use Write tool com path `scripts/migrations/carvia_aprovacoes_rename_frete.py` e conteudo:

```python
"""Migration: Rename carvia_aprovacoes_subcontrato → carvia_aprovacoes_frete.

Data: 2026-04-14
Ref: docs/superpowers/plans/2026-04-14-carvia-frete-conferencia-migration.md
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run_migration():
    print("=" * 70)
    print("MIGRATION: Rename aprovacoes_subcontrato → aprovacoes_frete")
    print("=" * 70)

    total = db.session.execute(text(
        "SELECT COUNT(*) FROM carvia_aprovacoes_subcontrato"
    )).scalar()
    print(f"Total aprovacoes: {total}")
    print()

    print("Step 1: ADD COLUMN frete_id (nullable)")
    db.session.execute(text("""
        ALTER TABLE carvia_aprovacoes_subcontrato
          ADD COLUMN IF NOT EXISTS frete_id INTEGER
          REFERENCES carvia_fretes(id)
    """))
    db.session.commit()

    print("Step 2: Backfill frete_id via sub.frete_id")
    result = db.session.execute(text("""
        UPDATE carvia_aprovacoes_subcontrato aps
        SET frete_id = s.frete_id
        FROM carvia_subcontratos s
        WHERE aps.subcontrato_id = s.id
          AND aps.frete_id IS NULL
          AND s.frete_id IS NOT NULL
    """))
    print(f"  Backfill: {result.rowcount} linhas atualizadas")
    db.session.commit()

    orfaos = db.session.execute(text(
        "SELECT COUNT(*) FROM carvia_aprovacoes_subcontrato WHERE frete_id IS NULL"
    )).scalar()
    if orfaos > 0:
        print(f"ERRO: {orfaos} aprovacoes orfas — investigar manualmente")
        print("Abortar migration.")
        return 1
    print("  Sem orfaos, prosseguindo.")

    print("Step 3: NOT NULL em frete_id + index")
    db.session.execute(text("""
        ALTER TABLE carvia_aprovacoes_subcontrato
          ALTER COLUMN frete_id SET NOT NULL
    """))
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_carvia_aprovacoes_frete_id
          ON carvia_aprovacoes_subcontrato (frete_id)
    """))
    db.session.commit()

    print("Step 4: RENAME TABLE")
    db.session.execute(text("""
        ALTER TABLE IF EXISTS carvia_aprovacoes_subcontrato
          RENAME TO carvia_aprovacoes_frete
    """))
    db.session.commit()

    print("Step 5: DROP COLUMN subcontrato_id")
    db.session.execute(text("""
        ALTER TABLE carvia_aprovacoes_frete
          DROP COLUMN IF EXISTS subcontrato_id
    """))
    db.session.commit()

    total_final = db.session.execute(text(
        "SELECT COUNT(*) FROM carvia_aprovacoes_frete"
    )).scalar()
    print()
    print("=" * 70)
    print("RESULTADO")
    print("=" * 70)
    print(f"carvia_aprovacoes_frete: {total_final} registros")
    return 0


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        sys.exit(run_migration())
```

- [ ] **Step 2: Compile**

```bash
python -m py_compile scripts/migrations/carvia_aprovacoes_rename_frete.py
```

- [ ] **Step 3: Commit (SEM executar)**

```bash
git add scripts/migrations/carvia_aprovacoes_rename_frete.py
git commit -m "feat(carvia): Python runner rename aprovacoes tabela"
```

---

### Task 4.3: Atualizar modelo CarviaAprovacaoFrete

**Files:**
- Modify: `app/carvia/models/aprovacao.py` (substituir arquivo inteiro)

- [ ] **Step 1: Substituir arquivo**

Use Write tool com path `app/carvia/models/aprovacao.py` e conteudo:

```python
"""Modelo de Aprovacao de CarviaFrete.

Tabela satelite de carvia_fretes que registra o historico de tratativas
de aprovacao quando a divergencia entre valor_considerado/valor_pago e o
valor_cotado ultrapassa a tolerancia (R$ 5,00 — TOLERANCIA_APROVACAO em
AprovacaoFreteService).

Paridade app/fretes/models.py:AprovacaoFrete (Nacom), com as seguintes
diferencas:
- Snapshot dos 3 valores no momento da solicitacao (auditoria forte)
- 1:N (e nao 1:0..1) — frete pode ter multiplas aprovacoes ao longo do tempo
  (ex: PENDENTE -> REJEITADO -> nova solicitacao apos correcao do valor_pago)
- Status do frete.status_conferencia permanece PENDENTE durante a tratativa
  (e definido APROVADO ou DIVERGENTE so apos o aprovador decidir)

Ref: docs/superpowers/plans/2026-04-14-carvia-frete-conferencia-migration.md
"""

from app import db
from app.utils.timezone import agora_utc_naive


STATUS_APROVACAO = ('PENDENTE', 'APROVADO', 'REJEITADO')


class CarviaAprovacaoFrete(db.Model):
    """Tratativa de aprovacao de divergencia em CarviaFrete."""

    __tablename__ = 'carvia_aprovacoes_frete'

    id = db.Column(db.Integer, primary_key=True)
    frete_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_fretes.id'),
        nullable=False,
        index=True,
    )

    # PENDENTE | APROVADO | REJEITADO
    status = db.Column(db.String(20), nullable=False, default='PENDENTE', index=True)

    # Solicitacao
    solicitado_por = db.Column(db.String(100), nullable=False)
    solicitado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    motivo_solicitacao = db.Column(db.Text, nullable=True)

    # Snapshot dos valores no momento da solicitacao (auditoria)
    valor_cotado_snap = db.Column(db.Numeric(15, 2), nullable=True)
    valor_considerado_snap = db.Column(db.Numeric(15, 2), nullable=True)
    valor_pago_snap = db.Column(db.Numeric(15, 2), nullable=True)
    diferenca_snap = db.Column(db.Numeric(15, 2), nullable=True)

    # Decisao do aprovador
    aprovador = db.Column(db.String(100), nullable=True)
    aprovado_em = db.Column(db.DateTime, nullable=True)
    observacoes_aprovacao = db.Column(db.Text, nullable=True)
    lancar_diferenca = db.Column(db.Boolean, nullable=True, default=False)

    # Auditoria
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    @property
    def pendente(self):
        return self.status == 'PENDENTE'

    @property
    def finalizada(self):
        return self.status in ('APROVADO', 'REJEITADO')

    def __repr__(self):
        return (
            f'<CarviaAprovacaoFrete {self.id} '
            f'frete={self.frete_id} status={self.status}>'
        )
```

- [ ] **Step 2: Compile**

```bash
python -m py_compile app/carvia/models/aprovacao.py
```

- [ ] **Step 3: Commit**

```bash
git add app/carvia/models/aprovacao.py
git commit -m "refactor(carvia): CarviaAprovacaoSubcontrato → CarviaAprovacaoFrete"
```

---

### Task 4.4: Atualizar __init__.py de models

**Files:**
- Modify: `app/carvia/models/__init__.py:85-86 e linha 126`

- [ ] **Step 1: Trocar import**

old_string:
```python
from .aprovacao import (
    CarviaAprovacaoSubcontrato, STATUS_APROVACAO,
)
```

new_string:
```python
from .aprovacao import (
    CarviaAprovacaoFrete, STATUS_APROVACAO,
)
```

- [ ] **Step 2: Trocar re-export**

old_string:
```python
    'CarviaAprovacaoSubcontrato', 'STATUS_APROVACAO',
```

new_string:
```python
    'CarviaAprovacaoFrete', 'STATUS_APROVACAO',
```

- [ ] **Step 3: Compile**

```bash
python -m py_compile app/carvia/models/__init__.py
```

- [ ] **Step 4: Commit**

```bash
git add app/carvia/models/__init__.py
git commit -m "refactor(carvia): __init__.py export CarviaAprovacaoFrete"
```

---

### Task 4.5: Remover relacionamento `aprovacoes` de CarviaSubcontrato + adicionar em CarviaFrete

**Files:**
- Modify: `app/carvia/models/documentos.py:681-687` (remover)
- Modify: `app/carvia/models/frete.py` (adicionar apos `ctes_complementares`)

- [ ] **Step 1: Remover de documentos.py**

old_string:
```python
    # 1:N com aprovacoes (historico de tratativas)
    aprovacoes = db.relationship(
        'CarviaAprovacaoSubcontrato',
        backref='subcontrato',
        foreign_keys='CarviaAprovacaoSubcontrato.subcontrato_id',
        order_by='CarviaAprovacaoSubcontrato.solicitado_em.desc()',
        lazy='dynamic',
    )
```

new_string: (vazio — remover o bloco inteiro incluindo linha em branco antes)

Usar Edit com `replace_all: false` — o string e unico no arquivo.

- [ ] **Step 2: Adicionar em frete.py**

old_string:
```python
    ctes_complementares = db.relationship(
        'CarviaCteComplementar',
        backref='frete',
        foreign_keys='CarviaCteComplementar.frete_id',
        lazy='dynamic',
    )

    __table_args__ = (
```

new_string:
```python
    ctes_complementares = db.relationship(
        'CarviaCteComplementar',
        backref='frete',
        foreign_keys='CarviaCteComplementar.frete_id',
        lazy='dynamic',
    )
    # 1:N com aprovacoes (historico de tratativas — paridade Nacom)
    aprovacoes = db.relationship(
        'CarviaAprovacaoFrete',
        backref='frete',
        foreign_keys='CarviaAprovacaoFrete.frete_id',
        order_by='CarviaAprovacaoFrete.solicitado_em.desc()',
        lazy='dynamic',
    )

    __table_args__ = (
```

- [ ] **Step 3: Compile**

```bash
python -m py_compile app/carvia/models/documentos.py app/carvia/models/frete.py
```

- [ ] **Step 4: Commit**

```bash
git add app/carvia/models/documentos.py app/carvia/models/frete.py
git commit -m "refactor(carvia): move rel aprovacoes Sub->Frete"
```

---

## Phase 5 — Adicionar `frete_id` em CarviaContaCorrenteTransportadora

### Task 5.1: SQL add frete_id + backfill

**Files:**
- Create: `scripts/migrations/carvia_cc_frete_id.sql`

- [ ] **Step 1: Criar arquivo**

Use Write tool com path `scripts/migrations/carvia_cc_frete_id.sql` e conteudo:

```sql
-- Migration: Add frete_id em carvia_conta_corrente_transportadoras
-- Data: 2026-04-14

-- 1. Add column nullable
ALTER TABLE carvia_conta_corrente_transportadoras
  ADD COLUMN IF NOT EXISTS frete_id INTEGER REFERENCES carvia_fretes(id);

-- 2. Backfill via subcontrato
UPDATE carvia_conta_corrente_transportadoras cc
SET frete_id = s.frete_id
FROM carvia_subcontratos s
WHERE cc.subcontrato_id = s.id
  AND cc.frete_id IS NULL
  AND s.frete_id IS NOT NULL;

-- 3. Checar orfaos
DO $$
DECLARE orfaos INT;
BEGIN
  SELECT COUNT(*) INTO orfaos
  FROM carvia_conta_corrente_transportadoras
  WHERE frete_id IS NULL;
  IF orfaos > 0 THEN
    RAISE NOTICE 'AVISO: % movimentacoes CC orfas', orfaos;
  END IF;
END $$;

-- 4. Index
CREATE INDEX IF NOT EXISTS idx_carvia_cc_frete_id
  ON carvia_conta_corrente_transportadoras (frete_id);

-- 5. Drop subcontrato_id (apos codigo migrado)
-- Comentado: executar MANUALMENTE apos deploy do codigo
-- ALTER TABLE carvia_conta_corrente_transportadoras
--   DROP COLUMN IF EXISTS subcontrato_id;
```

- [ ] **Step 2: Commit**

```bash
git add scripts/migrations/carvia_cc_frete_id.sql
git commit -m "feat(carvia): SQL add frete_id em conta_corrente"
```

---

### Task 5.2: Python runner

**Files:**
- Create: `scripts/migrations/carvia_cc_frete_id.py`

- [ ] **Step 1: Criar arquivo**

Use Write tool com path `scripts/migrations/carvia_cc_frete_id.py` e conteudo:

```python
"""Migration: Add frete_id em carvia_conta_corrente_transportadoras + backfill.

Data: 2026-04-14
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run_migration():
    print("=" * 70)
    print("MIGRATION: Add frete_id em CC + backfill")
    print("=" * 70)

    total = db.session.execute(text(
        "SELECT COUNT(*) FROM carvia_conta_corrente_transportadoras"
    )).scalar()
    print(f"Total movimentacoes CC: {total}")
    print()

    print("Step 1: ADD COLUMN frete_id")
    db.session.execute(text("""
        ALTER TABLE carvia_conta_corrente_transportadoras
          ADD COLUMN IF NOT EXISTS frete_id INTEGER REFERENCES carvia_fretes(id)
    """))
    db.session.commit()

    print("Step 2: Backfill")
    result = db.session.execute(text("""
        UPDATE carvia_conta_corrente_transportadoras cc
        SET frete_id = s.frete_id
        FROM carvia_subcontratos s
        WHERE cc.subcontrato_id = s.id
          AND cc.frete_id IS NULL
          AND s.frete_id IS NOT NULL
    """))
    print(f"  Backfill: {result.rowcount}")
    db.session.commit()

    orfaos = db.session.execute(text(
        "SELECT COUNT(*) FROM carvia_conta_corrente_transportadoras WHERE frete_id IS NULL"
    )).scalar()
    if orfaos > 0:
        print(f"AVISO: {orfaos} movimentacoes sem frete_id")

    print("Step 3: Index")
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_carvia_cc_frete_id
          ON carvia_conta_corrente_transportadoras (frete_id)
    """))
    db.session.commit()

    print()
    print("RESULTADO: frete_id adicionado. DROP subcontrato_id deve ser feito")
    print("manualmente apos deploy do codigo migrado (Phase 14).")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        run_migration()
```

- [ ] **Step 2: Compile + Commit**

```bash
python -m py_compile scripts/migrations/carvia_cc_frete_id.py
git add scripts/migrations/carvia_cc_frete_id.py
git commit -m "feat(carvia): Python runner add frete_id em CC"
```

---

### Task 5.3: Atualizar modelo CarviaContaCorrenteTransportadora

**Files:**
- Modify: `app/carvia/models/conta_corrente.py:47-59` (add frete_id; deprecar subcontrato_id)

- [ ] **Step 1: Adicionar frete_id no modelo**

old_string:
```python
    subcontrato_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_subcontratos.id'),
        nullable=False,
        index=True,
    )

    fatura_transportadora_id = db.Column(
```

new_string:
```python
    # DEPRECATED: manter ate drop migration final.
    # Fonte canonica agora e frete_id (paridade Nacom).
    subcontrato_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_subcontratos.id'),
        nullable=True,  # afrouxado para permitir novos registros sem sub
        index=True,
    )
    frete_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_fretes.id'),
        nullable=True,
        index=True,
    )

    fatura_transportadora_id = db.Column(
```

- [ ] **Step 2: Adicionar relationship `frete`**

old_string:
```python
    subcontrato = db.relationship('CarviaSubcontrato', foreign_keys=[subcontrato_id])
    fatura_transportadora = db.relationship(
```

new_string:
```python
    subcontrato = db.relationship('CarviaSubcontrato', foreign_keys=[subcontrato_id])
    frete = db.relationship('CarviaFrete', foreign_keys=[frete_id])
    fatura_transportadora = db.relationship(
```

- [ ] **Step 3: Compile**

```bash
python -m py_compile app/carvia/models/conta_corrente.py
```

- [ ] **Step 4: Commit**

```bash
git add app/carvia/models/conta_corrente.py
git commit -m "refactor(carvia): CC ganha FK frete_id (sub_id deprecado)"
```

---

## Phase 6 — Refactor AprovacaoFreteService (rename + operar em Frete)

### Task 6.1: Renomear arquivo do service

**Files:**
- Rename: `app/carvia/services/documentos/aprovacao_subcontrato_service.py` → `aprovacao_frete_service.py`

- [ ] **Step 1: Git move**

```bash
git mv app/carvia/services/documentos/aprovacao_subcontrato_service.py \
       app/carvia/services/documentos/aprovacao_frete_service.py
```

- [ ] **Step 2: Commit preliminar**

```bash
git commit -m "refactor(carvia): rename aprovacao_subcontrato_service.py → aprovacao_frete_service.py"
```

---

### Task 6.2: Reescrever service completo

**Files:**
- Rewrite: `app/carvia/services/documentos/aprovacao_frete_service.py`

- [ ] **Step 1: Substituir conteudo completo**

Use Write tool com path `app/carvia/services/documentos/aprovacao_frete_service.py` e conteudo:

```python
"""AprovacaoFreteService — fluxo de tratativa de divergencia em CarviaFrete.

Porta para o CarVia o conceito de "Em Tratativa" do modulo Nacom
(`app/fretes/`). Quando a divergencia ultrapassa a tolerancia, uma
solicitacao de aprovacao e criada em `carvia_aprovacoes_frete`.

Paridade Nacom Frete.requer_aprovacao_por_valor (app/fretes/models.py:145-174):
- Regra A: |valor_considerado - valor_cotado| > R$5
- Regra B: |valor_pago - valor_cotado| > R$5
- Regra C: |valor_pago - valor_considerado| > R$5  (a mais importante)

Ref: docs/superpowers/plans/2026-04-14-carvia-frete-conferencia-migration.md
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional

from app import db
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


TOLERANCIA_APROVACAO = Decimal('5.00')


class AprovacaoFreteService:
    """Servico de gerenciamento de tratativas de CarviaFrete."""

    # =================================================================
    # Verificacao automatica e solicitacao
    # =================================================================
    def verificar_e_solicitar_se_necessario(
        self, frete_id: int, usuario: str
    ) -> Dict:
        """Avalia se frete requer tratativa e cria solicitacao se sim.

        Aplicado quando:
        - Conferente registra conferencia via ConferenciaService
        - Operador atualiza valor_pago via form editar_frete_carvia

        Regras (espelho do Nacom):
        - Regra A: |valor_considerado - valor_cotado| > TOLERANCIA
        - Regra B: |valor_pago - valor_cotado| > TOLERANCIA
        - Regra C: |valor_pago - valor_considerado| > TOLERANCIA
        """
        from app.carvia.models import CarviaFrete

        frete = db.session.get(CarviaFrete, frete_id)
        if not frete:
            return {'sucesso': False, 'erro': 'Frete nao encontrado'}

        if frete.status == 'CANCELADO':
            return {'sucesso': False, 'erro': 'Frete cancelado — sem tratativa'}

        valor_cotado = Decimal(str(frete.valor_cotado or 0))
        valor_considerado = (
            Decimal(str(frete.valor_considerado))
            if frete.valor_considerado is not None else None
        )
        valor_pago = (
            Decimal(str(frete.valor_pago))
            if frete.valor_pago is not None else None
        )

        motivos = []
        diff_relevante = Decimal('0')

        if valor_considerado is not None:
            diff_a = abs(valor_considerado - valor_cotado)
            if diff_a > TOLERANCIA_APROVACAO:
                motivos.append(
                    f'Diferenca de R$ {diff_a:.2f} entre valor considerado '
                    f'(R$ {valor_considerado:.2f}) e cotado (R$ {valor_cotado:.2f})'
                )
                diff_relevante = max(diff_relevante, diff_a)

        if valor_pago is not None:
            diff_b = abs(valor_pago - valor_cotado)
            if diff_b > TOLERANCIA_APROVACAO:
                motivos.append(
                    f'Diferenca de R$ {diff_b:.2f} entre valor pago '
                    f'(R$ {valor_pago:.2f}) e cotado (R$ {valor_cotado:.2f})'
                )
                diff_relevante = max(diff_relevante, diff_b)

        # Regra C: pago vs considerado (paridade Nacom)
        if valor_considerado is not None and valor_pago is not None:
            diff_c = abs(valor_pago - valor_considerado)
            if diff_c > TOLERANCIA_APROVACAO:
                if valor_pago > valor_considerado:
                    motivos.append(
                        f'Valor Pago (R$ {valor_pago:.2f}) superior ao '
                        f'Considerado (R$ {valor_considerado:.2f}) em R$ {diff_c:.2f}'
                    )
                else:
                    motivos.append(
                        f'Valor Considerado (R$ {valor_considerado:.2f}) superior ao '
                        f'Pago (R$ {valor_pago:.2f}) em R$ {diff_c:.2f}'
                    )
                diff_relevante = max(diff_relevante, diff_c)

        if not motivos:
            return {
                'sucesso': True,
                'tratativa_aberta': False,
                'motivo': 'dentro da tolerancia',
            }

        return self.solicitar_aprovacao(
            frete_id=frete_id,
            motivo=' | '.join(motivos),
            usuario=usuario,
            valor_cotado=valor_cotado,
            valor_considerado=valor_considerado,
            valor_pago=valor_pago,
            diferenca=diff_relevante,
        )

    # =================================================================
    # Solicitacao (idempotente)
    # =================================================================
    def solicitar_aprovacao(
        self,
        frete_id: int,
        motivo: str,
        usuario: str,
        valor_cotado: Optional[Decimal] = None,
        valor_considerado: Optional[Decimal] = None,
        valor_pago: Optional[Decimal] = None,
        diferenca: Optional[Decimal] = None,
    ) -> Dict:
        """Cria aprovacao PENDENTE. Idempotente — se ja existe, retorna."""
        from app.carvia.models import CarviaAprovacaoFrete, CarviaFrete

        frete = db.session.get(CarviaFrete, frete_id)
        if not frete:
            return {'sucesso': False, 'erro': 'Frete nao encontrado'}

        # Snapshot atual se nao fornecido
        if valor_cotado is None and frete.valor_cotado is not None:
            valor_cotado = Decimal(str(frete.valor_cotado))
        if valor_considerado is None and frete.valor_considerado is not None:
            valor_considerado = Decimal(str(frete.valor_considerado))
        if valor_pago is None and frete.valor_pago is not None:
            valor_pago = Decimal(str(frete.valor_pago))

        # Idempotencia
        existente = CarviaAprovacaoFrete.query.filter_by(
            frete_id=frete_id,
            status='PENDENTE',
        ).with_for_update().first()

        if existente:
            logger.info(
                f"Aprovacao PENDENTE ja existe | frete={frete_id} | "
                f"aprovacao={existente.id}"
            )
            return {
                'sucesso': True,
                'tratativa_aberta': True,
                'aprovacao_id': existente.id,
                'motivo': 'Aprovacao PENDENTE ja existente',
            }

        aprovacao = CarviaAprovacaoFrete(
            frete_id=frete_id,
            status='PENDENTE',
            solicitado_por=usuario,
            solicitado_em=agora_utc_naive(),
            motivo_solicitacao=motivo,
            valor_cotado_snap=valor_cotado,
            valor_considerado_snap=valor_considerado,
            valor_pago_snap=valor_pago,
            diferenca_snap=diferenca,
        )
        db.session.add(aprovacao)
        db.session.flush()

        frete.requer_aprovacao = True

        logger.info(
            f"Aprovacao criada | frete={frete_id} | aprovacao={aprovacao.id} | "
            f"diff={diferenca}"
        )

        return {
            'sucesso': True,
            'tratativa_aberta': True,
            'aprovacao_id': aprovacao.id,
            'motivo': motivo,
        }

    # =================================================================
    # Decisao: APROVAR
    # =================================================================
    def aprovar(
        self,
        aprovacao_id: int,
        lancar_diferenca: bool,
        observacoes: str,
        usuario: str,
    ) -> Dict:
        """Processa decisao APROVADO em uma aprovacao PENDENTE."""
        from app.carvia.models import CarviaAprovacaoFrete, CarviaFrete

        aprovacao = CarviaAprovacaoFrete.query.filter_by(
            id=aprovacao_id
        ).with_for_update().first()

        if not aprovacao:
            return {'sucesso': False, 'erro': 'Aprovacao nao encontrada'}

        if aprovacao.status != 'PENDENTE':
            return {
                'sucesso': False,
                'erro': f'Aprovacao ja finalizada (status={aprovacao.status})',
            }

        try:
            aprovacao.status = 'APROVADO'
            aprovacao.aprovador = usuario
            aprovacao.aprovado_em = agora_utc_naive()
            aprovacao.observacoes_aprovacao = observacoes
            aprovacao.lancar_diferenca = lancar_diferenca

            frete = db.session.get(CarviaFrete, aprovacao.frete_id)
            if frete:
                frete.status_conferencia = 'APROVADO'
                frete.requer_aprovacao = False
                frete.conferido_por = usuario
                frete.conferido_em = agora_utc_naive()

                # Opt-in: lancar em CC se usuario marcou checkbox
                if lancar_diferenca:
                    from app.carvia.services.financeiro.conta_corrente_service import (
                        ContaCorrenteService,
                    )
                    cc_result = ContaCorrenteService.lancar_movimentacao(
                        frete_id=frete.id,
                        descricao=f'Aprovacao #{aprovacao.id}: {aprovacao.motivo_solicitacao[:100]}',
                        usuario=usuario,
                        fatura_transportadora_id=frete.fatura_transportadora_id,
                        observacoes=observacoes,
                    )
                    if not cc_result.get('sucesso'):
                        logger.warning(
                            f"Lancamento CC falhou para aprovacao {aprovacao_id}: "
                            f"{cc_result.get('erro')}"
                        )

            db.session.commit()

            logger.info(
                f"Aprovacao APROVADO | aprovacao={aprovacao_id} | "
                f"frete={aprovacao.frete_id} | lancar_diff={lancar_diferenca}"
            )

            return {
                'sucesso': True,
                'decisao': 'APROVADO',
                'frete_status': frete.status_conferencia if frete else None,
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao aprovar {aprovacao_id}: {e}")
            return {'sucesso': False, 'erro': str(e)}

    # =================================================================
    # Decisao: REJEITAR
    # =================================================================
    def rejeitar(
        self,
        aprovacao_id: int,
        observacoes: str,
        usuario: str,
    ) -> Dict:
        """Processa decisao REJEITADO em uma aprovacao PENDENTE."""
        from app.carvia.models import CarviaAprovacaoFrete, CarviaFrete

        aprovacao = CarviaAprovacaoFrete.query.filter_by(
            id=aprovacao_id
        ).with_for_update().first()

        if not aprovacao:
            return {'sucesso': False, 'erro': 'Aprovacao nao encontrada'}

        if aprovacao.status != 'PENDENTE':
            return {
                'sucesso': False,
                'erro': f'Aprovacao ja finalizada (status={aprovacao.status})',
            }

        try:
            aprovacao.status = 'REJEITADO'
            aprovacao.aprovador = usuario
            aprovacao.aprovado_em = agora_utc_naive()
            aprovacao.observacoes_aprovacao = observacoes
            aprovacao.lancar_diferenca = False

            frete = db.session.get(CarviaFrete, aprovacao.frete_id)
            if frete:
                frete.status_conferencia = 'DIVERGENTE'
                frete.requer_aprovacao = False
                frete.conferido_por = usuario
                frete.conferido_em = agora_utc_naive()

            db.session.commit()

            logger.info(
                f"Aprovacao REJEITADO | aprovacao={aprovacao_id} | "
                f"frete={aprovacao.frete_id}"
            )

            return {
                'sucesso': True,
                'decisao': 'REJEITADO',
                'frete_status': frete.status_conferencia if frete else None,
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao rejeitar {aprovacao_id}: {e}")
            return {'sucesso': False, 'erro': str(e)}

    # =================================================================
    # Listagem de PENDENTES
    # =================================================================
    def listar_pendentes(
        self,
        transportadora: Optional[str] = None,
        cte_numero: Optional[str] = None,
        nf_numero: Optional[str] = None,
    ) -> List:
        """Lista tratativas PENDENTE com filtros opcionais.

        Retorna lista de tuplas (aprovacao, frete) para uso em templates.
        """
        from app.carvia.models import CarviaAprovacaoFrete, CarviaFrete

        query = (
            db.session.query(CarviaAprovacaoFrete, CarviaFrete)
            .join(CarviaFrete, CarviaAprovacaoFrete.frete_id == CarviaFrete.id)
            .filter(CarviaAprovacaoFrete.status == 'PENDENTE')
        )

        if transportadora:
            from app.transportadoras.models import Transportadora
            query = query.join(
                Transportadora,
                CarviaFrete.transportadora_id == Transportadora.id,
            ).filter(Transportadora.razao_social.ilike(f'%{transportadora}%'))

        # cte_numero e nf_numero dependem de joins com Sub (que carrega CTe).
        # Mantido opcional — se necessario, iterar frete.subcontratos.
        if cte_numero:
            from app.carvia.models import CarviaSubcontrato
            query = query.join(
                CarviaSubcontrato,
                CarviaSubcontrato.frete_id == CarviaFrete.id,
            ).filter(CarviaSubcontrato.cte_numero.ilike(f'%{cte_numero}%'))

        if nf_numero:
            query = query.filter(CarviaFrete.numeros_nfs.ilike(f'%{nf_numero}%'))

        return query.order_by(
            CarviaAprovacaoFrete.solicitado_em.desc()
        ).all()

    # =================================================================
    # Contagem PENDENTE (para badge em menu)
    # =================================================================
    def contar_pendentes(self) -> int:
        """Retorna quantidade de tratativas PENDENTE."""
        from app.carvia.models import CarviaAprovacaoFrete
        return CarviaAprovacaoFrete.query.filter_by(status='PENDENTE').count()

    # =================================================================
    # Rejeicao em lote (hook de desanexar sub/cancelar)
    # =================================================================
    def rejeitar_pendentes_de_frete(
        self, frete_id: int, motivo: str, usuario: str
    ) -> int:
        """Rejeita silenciosamente todas aprovacoes PENDENTE de um frete.

        Usado em hooks de cancelamento (frete.status='CANCELADO',
        desanexar subcontrato). NAO commita — chamador deve commitar.
        Retorna qtd de rejeicoes aplicadas.
        """
        from app.carvia.models import CarviaAprovacaoFrete, CarviaFrete

        pendentes = CarviaAprovacaoFrete.query.filter_by(
            frete_id=frete_id,
            status='PENDENTE',
        ).all()

        count = 0
        for ap in pendentes:
            ap.status = 'REJEITADO'
            ap.aprovador = usuario
            ap.aprovado_em = agora_utc_naive()
            ap.observacoes_aprovacao = f'Auto-rejeitado: {motivo}'
            ap.lancar_diferenca = False
            count += 1

        if count > 0:
            frete = db.session.get(CarviaFrete, frete_id)
            if frete:
                frete.requer_aprovacao = False

        return count
```

- [ ] **Step 2: Compile**

```bash
python -m py_compile app/carvia/services/documentos/aprovacao_frete_service.py
```

- [ ] **Step 3: Commit**

```bash
git add app/carvia/services/documentos/aprovacao_frete_service.py
git commit -m "refactor(carvia): AprovacaoFreteService opera em Frete (7 metodos)"
```

---

## Phase 7 — Refactor ContaCorrenteService

### Task 7.1: deve_lancar(frete)

**Files:**
- Modify: `app/carvia/services/financeiro/conta_corrente_service.py:47-77`

- [ ] **Step 1: Edit assinatura e leituras**

old_string:
```python
    @staticmethod
    def deve_lancar(sub) -> tuple:
        """Avalia se sub deve lancar movimentacao na CC automaticamente.

        Regras (espelham Nacom `Frete.deve_lancar_conta_corrente`,
        models.py:168-189):
        - Sem `valor_pago` ou sem `valor_considerado`: nao lanca (sem dados)
        - diff dentro da tolerancia (R$ 5,00): lanca direto
        - diff > tolerancia: requer aprovacao explicita (lancar_diferenca=True)

        Returns:
            (bool, str) — pode lancar, motivo
        """
        from app.carvia.services.documentos.aprovacao_subcontrato_service import (
            TOLERANCIA_APROVACAO,
        )

        if sub.valor_pago is None or sub.valor_considerado is None:
            return False, 'valor_pago ou valor_considerado nao informado'

        valor_pago = Decimal(str(sub.valor_pago))
        valor_considerado = Decimal(str(sub.valor_considerado))
        diff = abs(valor_pago - valor_considerado)
```

new_string:
```python
    @staticmethod
    def deve_lancar(frete) -> tuple:
        """Avalia se frete deve lancar movimentacao na CC automaticamente.

        Regras (espelho Nacom `Frete.deve_lancar_conta_corrente`):
        - Sem `valor_pago` ou sem `valor_considerado`: nao lanca
        - diff dentro da tolerancia (R$ 5,00): lanca direto
        - diff > tolerancia: requer aprovacao explicita (lancar_diferenca=True)

        Args:
            frete: CarviaFrete (unidade de analise — paridade Nacom)

        Returns:
            (bool, str) — pode lancar, motivo
        """
        from app.carvia.services.documentos.aprovacao_frete_service import (
            TOLERANCIA_APROVACAO,
        )

        if frete.valor_pago is None or frete.valor_considerado is None:
            return False, 'valor_pago ou valor_considerado nao informado'

        valor_pago = Decimal(str(frete.valor_pago))
        valor_considerado = Decimal(str(frete.valor_considerado))
        diff = abs(valor_pago - valor_considerado)
```

- [ ] **Step 2: Compile**

```bash
python -m py_compile app/carvia/services/financeiro/conta_corrente_service.py
```

- [ ] **Step 3: Commit**

```bash
git add app/carvia/services/financeiro/conta_corrente_service.py
git commit -m "refactor(carvia): ContaCorrente.deve_lancar recebe Frete"
```

---

### Task 7.2: lancar_movimentacao(frete_id)

**Files:**
- Modify: `app/carvia/services/financeiro/conta_corrente_service.py:83-165`

- [ ] **Step 1: Edit assinatura e corpo**

old_string:
```python
    @staticmethod
    def lancar_movimentacao(
        sub_id: int,
        descricao: str,
        usuario: str,
        fatura_transportadora_id: Optional[int] = None,
        observacoes: Optional[str] = None,
    ) -> Dict:
        """Cria uma movimentacao na CC com base na diferenca atual do sub.

        Calcula tipo (DEBITO/CREDITO) pelo sinal de
        `valor_pago - valor_considerado`. NAO commita — chamador deve commitar.
        """
        from app.carvia.models import (
            CarviaContaCorrenteTransportadora,
            CarviaSubcontrato,
        )

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub:
            return {'sucesso': False, 'erro': 'Subcontrato nao encontrado'}

        if sub.valor_pago is None or sub.valor_considerado is None:
            return {
                'sucesso': False,
                'erro': 'Sub precisa ter valor_pago e valor_considerado para gerar CC',
            }

        valor_pago = Decimal(str(sub.valor_pago))
        valor_considerado = Decimal(str(sub.valor_considerado))
        diff_assinada = valor_pago - valor_considerado
        diff_abs = abs(diff_assinada)
```

new_string:
```python
    @staticmethod
    def lancar_movimentacao(
        frete_id: int,
        descricao: str,
        usuario: str,
        fatura_transportadora_id: Optional[int] = None,
        observacoes: Optional[str] = None,
    ) -> Dict:
        """Cria uma movimentacao na CC com base na diferenca do frete.

        Calcula tipo (DEBITO/CREDITO) pelo sinal de
        `valor_pago - valor_considerado`. NAO commita — chamador deve commitar.

        Args:
            frete_id: ID do CarviaFrete (paridade Nacom Frete.id)
        """
        from app.carvia.models import (
            CarviaContaCorrenteTransportadora,
            CarviaFrete,
        )

        frete = db.session.get(CarviaFrete, frete_id)
        if not frete:
            return {'sucesso': False, 'erro': 'Frete nao encontrado'}

        if frete.valor_pago is None or frete.valor_considerado is None:
            return {
                'sucesso': False,
                'erro': 'Frete precisa ter valor_pago e valor_considerado para gerar CC',
            }

        valor_pago = Decimal(str(frete.valor_pago))
        valor_considerado = Decimal(str(frete.valor_considerado))
        diff_assinada = valor_pago - valor_considerado
        diff_abs = abs(diff_assinada)
```

- [ ] **Step 2: Edit criacao da movimentacao**

old_string:
```python
        try:
            mov = CarviaContaCorrenteTransportadora(
                transportadora_id=sub.transportadora_id,
                subcontrato_id=sub.id,
                fatura_transportadora_id=(
                    fatura_transportadora_id or sub.fatura_transportadora_id
                ),
                tipo_movimentacao=tipo,
                valor_diferenca=diff_abs,
                valor_debito=valor_debito,
                valor_credito=valor_credito,
                descricao=descricao,
                observacoes=observacoes,
                status='ATIVO',
                criado_em=agora_utc_naive(),
                criado_por=usuario,
            )
            db.session.add(mov)
            db.session.flush()  # popula mov.id

            logger.info(
                f'CC mov criada | sub={sub_id} | tipo={tipo} | '
                f'valor={diff_abs} | mov_id={mov.id}'
            )
```

new_string:
```python
        try:
            mov = CarviaContaCorrenteTransportadora(
                transportadora_id=frete.transportadora_id,
                frete_id=frete.id,
                subcontrato_id=None,  # deprecated — fonte e frete_id
                fatura_transportadora_id=(
                    fatura_transportadora_id or frete.fatura_transportadora_id
                ),
                tipo_movimentacao=tipo,
                valor_diferenca=diff_abs,
                valor_debito=valor_debito,
                valor_credito=valor_credito,
                descricao=descricao,
                observacoes=observacoes,
                status='ATIVO',
                criado_em=agora_utc_naive(),
                criado_por=usuario,
            )
            db.session.add(mov)
            db.session.flush()

            logger.info(
                f'CC mov criada | frete={frete_id} | tipo={tipo} | '
                f'valor={diff_abs} | mov_id={mov.id}'
            )
```

- [ ] **Step 3: Compile**

```bash
python -m py_compile app/carvia/services/financeiro/conta_corrente_service.py
```

- [ ] **Step 4: Commit**

```bash
git add app/carvia/services/financeiro/conta_corrente_service.py
git commit -m "refactor(carvia): ContaCorrente.lancar_movimentacao opera em Frete"
```

---

### Task 7.3: cancelar_movimentacoes(frete_id)

**Files:**
- Modify: `app/carvia/services/financeiro/conta_corrente_service.py:171-198`

- [ ] **Step 1: Edit**

old_string:
```python
    @staticmethod
    def cancelar_movimentacoes(sub_id: int, motivo: str, usuario: str) -> int:
```

new_string:
```python
    @staticmethod
    def cancelar_movimentacoes(frete_id: int, motivo: str, usuario: str) -> int:
```

- [ ] **Step 2: Edit corpo — trocar filter**

old_string:
```python
        movs = CarviaContaCorrenteTransportadora.query.filter_by(
            subcontrato_id=sub_id,
            status='ATIVO',
        ).all()
```

new_string:
```python
        movs = CarviaContaCorrenteTransportadora.query.filter_by(
            frete_id=frete_id,
            status='ATIVO',
        ).all()
```

NOTA: se o Edit falhar porque o contexto nao bate, abrir o arquivo e copiar bloco exato das linhas 180-182. Ajustar conforme estrutura real.

- [ ] **Step 3: Compile + commit**

```bash
python -m py_compile app/carvia/services/financeiro/conta_corrente_service.py
git add app/carvia/services/financeiro/conta_corrente_service.py
git commit -m "refactor(carvia): ContaCorrente.cancelar_movimentacoes usa frete_id"
```

---

### Task 7.4: listar_extrato — trocar sub_valor_* para frete_valor_*

**Files:**
- Modify: `app/carvia/services/financeiro/conta_corrente_service.py:340-414`

- [ ] **Step 1: Ler o metodo para localizar bloco exato**

```bash
sed -n '340,420p' app/carvia/services/financeiro/conta_corrente_service.py
```

- [ ] **Step 2: Edit linhas 403-405**

Baseado no finding, o dict tem:
```python
'sub_valor_cotado': float(sub.valor_cotado or 0) if sub else None,
'sub_valor_considerado': float(sub.valor_considerado or 0) if sub else None,
'sub_valor_pago': float(sub.valor_pago or 0) if sub else None,
```

Trocar para (ler valores do frete via mov.frete, com fallback):
```python
'frete_valor_cotado': float(frete.valor_cotado or 0) if frete else None,
'frete_valor_considerado': float(frete.valor_considerado or 0) if frete else None,
'frete_valor_pago': float(frete.valor_pago or 0) if frete else None,
```

IMPORTANTE: o JOIN atual (linhas 358-361) provavelmente faz join com `CarviaSubcontrato`. Precisa mudar para join com `CarviaFrete`. Ler contexto antes de Edit. Ajustar:
- JOIN: `.outerjoin(CarviaFrete, CarviaContaCorrenteTransportadora.frete_id == CarviaFrete.id)`
- Itera os resultados: `for mov, frete in results:`

EXECUTAR SUB-TASK: ler linhas 340-420, identificar join e dict construction, aplicar edits. Para preservar bite-sized, neste task e aceitavel multiplas edits sequenciais no mesmo arquivo.

- [ ] **Step 3: Compile + commit**

```bash
python -m py_compile app/carvia/services/financeiro/conta_corrente_service.py
git add app/carvia/services/financeiro/conta_corrente_service.py
git commit -m "refactor(carvia): listar_extrato le campos do Frete"
```

---

## Phase 8 — Refactor ConferenciaService para operar em Frete

### Task 8.1: Substituir registrar_conferencia inteiro

**Files:**
- Modify: `app/carvia/services/documentos/conferencia_service.py:219-355`

- [ ] **Step 1: Ler o bloco atual inteiro**

```bash
sed -n '215,360p' app/carvia/services/documentos/conferencia_service.py
```

- [ ] **Step 2: Substituir bloco com Edit**

old_string: (copiar todo o bloco da funcao `def registrar_conferencia` ate o fechamento, incluindo imports locais no inicio)

new_string:
```python
    def registrar_conferencia(self, frete_id: int, valor_considerado: float,
                               status: str, usuario: str,
                               observacoes: str = None,
                               valor_pago: float = None) -> Dict:
        """
        Registra conferencia de um CarviaFrete (unidade de analise — paridade Nacom).

        Paridade Nacom: equivalente a editar_frete com valor_considerado/pago
        (app/fretes/routes.py:editar_frete linhas ~750-900).

        REFATOR D4 (.claude/plans/wobbly-tumbling-treasure.md):
        Quando o conferente decide DIVERGENTE, uma CarviaAprovacaoFrete
        PENDENTE e criada via AprovacaoFreteService, e o frete fica com
        status_conferencia='PENDENTE' + requer_aprovacao=True ate o aprovador
        decidir. APROVADO continua sendo gravado direto (se dentro da tolerancia).

        Args:
            frete_id: ID do CarviaFrete
            valor_considerado: Valor registrado pelo conferente
            status: APROVADO ou DIVERGENTE (decisao inicial)
            usuario: Email do conferente
            observacoes: Texto opcional
            valor_pago: Valor efetivamente pago (opcional)

        Returns:
            Dict com sucesso, status_conferencia, fatura_atualizada,
            fatura_status, tratativa_aberta, aprovacao_id.
        """
        from app.carvia.models import CarviaFrete
        from app.utils.timezone import agora_utc_naive

        if status not in ('APROVADO', 'DIVERGENTE'):
            return {'sucesso': False, 'erro': 'Status deve ser APROVADO ou DIVERGENTE'}

        frete = db.session.get(CarviaFrete, frete_id)
        if not frete:
            return {'sucesso': False, 'erro': 'Frete nao encontrado'}

        if frete.status == 'CANCELADO':
            return {'sucesso': False, 'erro': 'Frete cancelado — sem conferencia'}

        try:
            # Snapshot dos calculos (opcional — usar primary sub como proxy)
            snapshot = None
            primary_sub = frete.subcontratos.first()
            if primary_sub:
                try:
                    resultado = self.calcular_opcoes_conferencia(primary_sub.id)
                    if resultado.get('sucesso'):
                        snapshot = {
                            'opcoes': resultado.get('opcoes', []),
                            'operacao_info': resultado.get('operacao_info'),
                            'conferido_em': str(agora_utc_naive()),
                        }
                except Exception as e:
                    logger.warning(f"Erro ao gerar snapshot frete {frete_id}: {e}")

            frete.valor_considerado = valor_considerado
            if valor_pago is not None:
                frete.valor_pago = valor_pago
            frete.conferido_por = usuario
            frete.conferido_em = agora_utc_naive()
            frete.detalhes_conferencia = snapshot

            if observacoes:
                frete.observacoes = (frete.observacoes or '') + f'\n[Conferencia] {observacoes}'

            # REFATOR D4: roteamento entre APROVADO direto ou abrir tratativa
            from app.carvia.services.documentos.aprovacao_frete_service import (
                AprovacaoFreteService,
            )
            aprov_svc = AprovacaoFreteService()

            tratativa_aberta = False
            aprovacao_id = None

            if status == 'DIVERGENTE':
                frete.status_conferencia = 'PENDENTE'
                resultado_trat = aprov_svc.verificar_e_solicitar_se_necessario(
                    frete_id=frete_id, usuario=usuario,
                )
                if resultado_trat.get('sucesso') and resultado_trat.get('tratativa_aberta'):
                    tratativa_aberta = True
                    aprovacao_id = resultado_trat.get('aprovacao_id')
                else:
                    frete.status_conferencia = 'DIVERGENTE'
            else:  # APROVADO
                resultado_trat = aprov_svc.verificar_e_solicitar_se_necessario(
                    frete_id=frete_id, usuario=usuario,
                )
                if resultado_trat.get('sucesso') and resultado_trat.get('tratativa_aberta'):
                    frete.status_conferencia = 'PENDENTE'
                    tratativa_aberta = True
                    aprovacao_id = resultado_trat.get('aprovacao_id')
                else:
                    frete.status_conferencia = 'APROVADO'

            # Cascade para fatura
            fatura_atualizada = False
            fatura_status = None
            if frete.fatura_transportadora_id:
                fatura_atualizada, fatura_status = self._verificar_fatura_completa(
                    frete.fatura_transportadora_id, usuario,
                )

            db.session.commit()

            logger.info(
                f"Conferencia registrada | frete_id={frete_id} | "
                f"considerado={valor_considerado} | pago={valor_pago} | "
                f"solicitado={status} | final={frete.status_conferencia} | "
                f"tratativa={tratativa_aberta} | usuario={usuario}"
            )

            return {
                'sucesso': True,
                'status_conferencia': frete.status_conferencia,
                'valor_considerado': float(valor_considerado),
                'valor_pago': float(valor_pago) if valor_pago is not None else None,
                'fatura_atualizada': fatura_atualizada,
                'fatura_status': fatura_status,
                'tratativa_aberta': tratativa_aberta,
                'aprovacao_id': aprovacao_id,
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao registrar conferencia frete {frete_id}: {e}")
            return {'sucesso': False, 'erro': str(e)}
```

- [ ] **Step 3: Compile + commit**

```bash
python -m py_compile app/carvia/services/documentos/conferencia_service.py
git add app/carvia/services/documentos/conferencia_service.py
git commit -m "refactor(carvia): ConferenciaService.registrar_conferencia opera em Frete"
```

---

### Task 8.2: Substituir _verificar_fatura_completa

**Files:**
- Modify: `app/carvia/services/documentos/conferencia_service.py:357-415`

- [ ] **Step 1: Substituir metodo**

old_string: (ler linhas 357-415 e copiar o bloco inteiro, do `def _verificar_fatura_completa` ate o fechamento)

new_string:
```python
    def _verificar_fatura_completa(self, fatura_id: int, usuario: str):
        """Verifica se todos fretes da fatura foram conferidos.

        Paridade Nacom: itera CarviaFrete (nao Sub).

        Returns:
            Tuple (fatura_atualizada: bool, novo_status: str)
        """
        from app.carvia.models import CarviaFaturaTransportadora, CarviaFrete
        from app.utils.timezone import agora_utc_naive

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            return False, None

        fretes = CarviaFrete.query.filter(
            CarviaFrete.fatura_transportadora_id == fatura_id,
            CarviaFrete.status != 'CANCELADO',
        ).all()

        if not fretes:
            return False, fatura.status_conferencia

        contagem = {'APROVADO': 0, 'DIVERGENTE': 0, 'PENDENTE': 0}
        for f in fretes:
            sc = f.status_conferencia or 'PENDENTE'
            contagem[sc] = contagem.get(sc, 0) + 1

        total = len(fretes)
        status_anterior = fatura.status_conferencia

        if contagem['APROVADO'] == total:
            fatura.status_conferencia = 'CONFERIDO'
            fatura.conferido_por = usuario
            fatura.conferido_em = agora_utc_naive()
            for f in fretes:
                if f.status == 'FATURADO':
                    f.status = 'CONFERIDO'
        elif contagem['DIVERGENTE'] > 0:
            fatura.status_conferencia = 'DIVERGENTE'
            fatura.conferido_por = usuario
            fatura.conferido_em = agora_utc_naive()
        elif contagem['APROVADO'] > 0:
            fatura.status_conferencia = 'EM_CONFERENCIA'

        novo_status = fatura.status_conferencia
        atualizado = novo_status != status_anterior

        if atualizado:
            logger.info(
                f"Fatura #{fatura_id}: {status_anterior} → {novo_status} | "
                f"aprovados={contagem['APROVADO']}/{total} "
                f"divergentes={contagem['DIVERGENTE']}/{total}"
            )

        return atualizado, novo_status
```

- [ ] **Step 2: Compile + commit**

```bash
python -m py_compile app/carvia/services/documentos/conferencia_service.py
git add app/carvia/services/documentos/conferencia_service.py
git commit -m "refactor(carvia): _verificar_fatura_completa itera Frete"
```

---

### Task 8.3: Substituir resumo_conferencia_fatura

**Files:**
- Modify: `app/carvia/services/documentos/conferencia_service.py:417-482`

- [ ] **Step 1: Substituir metodo**

old_string: (ler linhas 417-482 e copiar o bloco inteiro)

new_string:
```python
    def resumo_conferencia_fatura(self, fatura_id: int) -> Dict:
        """Retorna resumo da conferencia de uma fatura.

        Paridade Nacom: itera CarviaFrete (unidade de analise).

        Returns:
            Dict com total, aprovados, divergentes, pendentes,
            soma_cte_valor, soma_considerado, soma_valor_pago,
            soma_custos_entrega, valor_conferido_total, valor_pago_total.
        """
        from app.carvia.models import CarviaFrete, CarviaCustoEntrega

        fretes = CarviaFrete.query.filter(
            CarviaFrete.fatura_transportadora_id == fatura_id,
            CarviaFrete.status != 'CANCELADO',
        ).all()

        total = len(fretes)
        aprovados = sum(1 for f in fretes if f.status_conferencia == 'APROVADO')
        divergentes = sum(1 for f in fretes if f.status_conferencia == 'DIVERGENTE')
        pendentes = total - aprovados - divergentes

        soma_cte_valor = sum(float(f.valor_cte or 0) for f in fretes)
        soma_considerado = sum(float(f.valor_considerado or 0) for f in fretes)
        soma_valor_pago = sum(float(f.valor_pago or 0) for f in fretes)

        ces = CarviaCustoEntrega.query.filter(
            CarviaCustoEntrega.fatura_transportadora_id == fatura_id,
            CarviaCustoEntrega.status != 'CANCELADO',
        ).all()
        soma_custos_entrega = sum(float(ce.valor or 0) for ce in ces)
        total_ces = len(ces)
        valor_conferido_total = soma_considerado + soma_custos_entrega
        valor_pago_total = soma_valor_pago + soma_custos_entrega

        return {
            'total': total,
            'aprovados': aprovados,
            'divergentes': divergentes,
            'pendentes': pendentes,
            'soma_cte_valor': round(soma_cte_valor, 2),
            'soma_considerado': round(soma_considerado, 2),
            'soma_valor_pago': round(soma_valor_pago, 2),
            'soma_custos_entrega': round(soma_custos_entrega, 2),
            'total_ces': total_ces,
            'valor_conferido_total': round(valor_conferido_total, 2),
            'valor_pago_total': round(valor_pago_total, 2),
            'diferenca': round(soma_cte_valor - soma_considerado, 2) if total else None,
            'percentual_conferido': round((aprovados + divergentes) / total * 100) if total else 0,
        }
```

- [ ] **Step 2: Compile + commit**

```bash
python -m py_compile app/carvia/services/documentos/conferencia_service.py
git add app/carvia/services/documentos/conferencia_service.py
git commit -m "refactor(carvia): resumo_conferencia_fatura itera Frete"
```

---

## Phase 9 — Refactor aprovacao_routes.py

### Task 9.1: Atualizar imports (header do arquivo)

**Files:**
- Modify: `app/carvia/routes/aprovacao_routes.py:1-40` (imports)

- [ ] **Step 1: Edit imports**

old_string:
```python
from app.carvia.models import (
    CarviaAprovacaoSubcontrato,
    CarviaSubcontrato,
    CarviaOperacao,
    CarviaFaturaTransportadora,
)
from app.carvia.services.documentos.aprovacao_subcontrato_service import (
    AprovacaoSubcontratoService,
    TOLERANCIA_APROVACAO,
)
```

new_string:
```python
from app.carvia.models import (
    CarviaAprovacaoFrete,
    CarviaFrete,
    CarviaSubcontrato,
    CarviaOperacao,
    CarviaFaturaTransportadora,
)
from app.carvia.services.documentos.aprovacao_frete_service import (
    AprovacaoFreteService,
    TOLERANCIA_APROVACAO,
)
```

- [ ] **Step 2: Compile**

```bash
python -m py_compile app/carvia/routes/aprovacao_routes.py
```
NOTA: Pyright pode reclamar de funcoes indefinidas abaixo — ignorar por enquanto, serao atualizadas nas proximas tasks.

- [ ] **Step 3: Commit (sem testar — stub atualizado)**

```bash
git add app/carvia/routes/aprovacao_routes.py
git commit -m "refactor(carvia): aprovacao_routes imports para Frete"
```

---

### Task 9.2: Atualizar listar_aprovacoes_subcontrato → listar_aprovacoes_frete

**Files:**
- Modify: `app/carvia/routes/aprovacao_routes.py:35-82`

- [ ] **Step 1: Edit funcao completa**

old_string: (ler linhas 35-82 completas do arquivo atual e copiar)

Use Read para ver o conteudo exato antes.

new_string: substituir assinatura `def listar_aprovacoes_subcontrato():` por `def listar_aprovacoes_frete():`. Substituir chamadas:
- `AprovacaoSubcontratoService().listar_pendentes()` → `AprovacaoFreteService().listar_pendentes()`
- Resultado: service agora retorna `(aprovacao, frete)` tuples (nao mais `(aprovacao, sub)`)
- No loop: trocar `sub.transportadora` por `frete.transportadora`
- `sub.cte_numero` nao existe no frete — resolver via `frete.subcontratos.first().cte_numero` se necessario

Tambem: mudar rota `@bp.route('/subcontratos/aprovacoes')` para `@bp.route('/aprovacoes-frete')` OU manter URL e so renomear funcao Python (escolha: **manter URL** para nao quebrar bookmarks).

EXECUTAR SUB-TASK: ler codigo completo, substituir mantendo rota publica igual (`/subcontratos/aprovacoes` — ou criar alias novo). A responsabilidade do agente e preservar a rota atual enquanto migra o codigo interno para Frete.

- [ ] **Step 2: Compile**

```bash
python -m py_compile app/carvia/routes/aprovacao_routes.py
```

- [ ] **Step 3: Commit**

```bash
git add app/carvia/routes/aprovacao_routes.py
git commit -m "refactor(carvia): listar_aprovacoes opera em Frete"
```

---

### Task 9.3: Atualizar processar_aprovacao_subcontrato → processar_aprovacao_frete

**Files:**
- Modify: `app/carvia/routes/aprovacao_routes.py:87-178`

- [ ] **Step 1: Ler a funcao atual completa**

```bash
sed -n '85,180p' app/carvia/routes/aprovacao_routes.py
```

- [ ] **Step 2: Substituir blocos:**

- Renomear funcao Python: `def processar_aprovacao_subcontrato` → `def processar_aprovacao_frete`
- Substituir `aprovacao = db.session.get(CarviaAprovacaoSubcontrato, aprovacao_id)` → `aprovacao = db.session.get(CarviaAprovacaoFrete, aprovacao_id)`
- Substituir `sub = db.session.get(CarviaSubcontrato, aprovacao.subcontrato_id)` → `frete = db.session.get(CarviaFrete, aprovacao.frete_id)`
- Substituir `sub.valor_cotado` → `frete.valor_cotado`
- Substituir `sub.valor_considerado` → `frete.valor_considerado`
- Substituir `sub.valor_pago` → `frete.valor_pago`
- Substituir `sub.transportadora` → `frete.transportadora`
- Substituir `sub.operacao` → `frete.subcontratos.first().operacao if frete.subcontratos.count() else None`
- No render_template: passar `frete=frete` em vez de `sub=sub`

- [ ] **Step 3: Compile**

```bash
python -m py_compile app/carvia/routes/aprovacao_routes.py
```

- [ ] **Step 4: Commit**

```bash
git add app/carvia/routes/aprovacao_routes.py
git commit -m "refactor(carvia): processar_aprovacao opera em Frete"
```

---

### Task 9.4: Atualizar aprovar_subcontrato e rejeitar_subcontrato

**Files:**
- Modify: `app/carvia/routes/aprovacao_routes.py:183-268`

- [ ] **Step 1: Edit aprovar_subcontrato → aprovar_frete**

Renomear funcao Python e trocar service:
- `AprovacaoSubcontratoService()` → `AprovacaoFreteService()`
- Assinatura do metodo `aprovar` permanece igual (recebe `aprovacao_id, lancar_diferenca, observacoes, usuario`)
- Retornar mesmo tipo de resposta

- [ ] **Step 2: Edit rejeitar_subcontrato → rejeitar_frete**

Mesma coisa para rejeitar.

- [ ] **Step 3: Compile + commit**

```bash
python -m py_compile app/carvia/routes/aprovacao_routes.py
git add app/carvia/routes/aprovacao_routes.py
git commit -m "refactor(carvia): aprovar/rejeitar operam em Frete"
```

---

### Task 9.5: Atualizar solicitar_aprovacao_subcontrato_manual

**Files:**
- Modify: `app/carvia/routes/aprovacao_routes.py:276-299`

- [ ] **Step 1: Edit funcao**

- Renomear: `def solicitar_aprovacao_subcontrato_manual(sub_id)` → `def solicitar_aprovacao_frete_manual(frete_id)`
- Parametro de rota: `/subcontratos/<int:sub_id>/solicitar-aprovacao` → manter URL ou criar `/fretes/<int:frete_id>/solicitar-aprovacao`. Decisao: **criar nova URL** e **manter old URL como deprecated** (301 redirect para nova). Nao essencial.
- `svc.solicitar_aprovacao(sub_id=sub_id, motivo, usuario)` → `svc.solicitar_aprovacao(frete_id=frete_id, motivo, usuario)`

Simplificacao: como o fluxo manual e pouco usado, aceita-se so renomear a funcao interna sem mudar a URL publica. Caller JS decide.

- [ ] **Step 2: Compile + commit**

```bash
python -m py_compile app/carvia/routes/aprovacao_routes.py
git add app/carvia/routes/aprovacao_routes.py
git commit -m "refactor(carvia): solicitar_aprovacao_manual opera em Frete"
```

---

## Phase 10 — Refactor fatura_routes callers

### Task 10.1: Linha 1614 — trocar import lazy + chamada

**Files:**
- Modify: `app/carvia/routes/fatura_routes.py:1606-1625`

- [ ] **Step 1: Edit**

old_string:
```python
        from app.carvia.services.documentos.aprovacao_subcontrato_service import (
            AprovacaoSubcontratoService,
        )
        AprovacaoSubcontratoService().rejeitar_pendentes_de_sub(
            sub_id=sub.id, motivo='...',
            usuario=current_user.email
        )
```

NOTA: o codigo atual pode ter parametros ligeiramente diferentes. Ler linhas 1606-1625 primeiro e copiar contexto exato.

new_string (adaptado):
```python
        from app.carvia.services.documentos.aprovacao_frete_service import (
            AprovacaoFreteService,
        )
        if sub.frete_id:
            AprovacaoFreteService().rejeitar_pendentes_de_frete(
                frete_id=sub.frete_id, motivo='Sub desanexado da fatura',
                usuario=current_user.email,
            )
```

- [ ] **Step 2: Compile + commit**

```bash
python -m py_compile app/carvia/routes/fatura_routes.py
git add app/carvia/routes/fatura_routes.py
git commit -m "refactor(carvia): fatura_routes rejeita aprovacoes do frete"
```

---

### Task 10.2: Linhas 2175-2204 — check requer_aprovacao

**Files:**
- Modify: `app/carvia/routes/fatura_routes.py:2175-2204`

NOTA: no refactor anterior (conferir_fatura_transportadora) ja transformei `subs_em_tratativa` para ler `s.requer_aprovacao` via getattr. Agora essa logica pode ler direto de `frete.requer_aprovacao`.

- [ ] **Step 1: Ler contexto**

```bash
sed -n '2160,2220p' app/carvia/routes/fatura_routes.py
```

- [ ] **Step 2: Edit — trocar `subs_em_tratativa` por `fretes_em_tratativa`**

O loop iter sobre fretes. Trocar:
```python
subs_em_tratativa = [
    s for s in subs_do_frete
    if getattr(s, 'requer_aprovacao', False)
]
```

por:
```python
fretes_em_tratativa = [
    f for f in fretes if getattr(f, 'requer_aprovacao', False)
]
```

E ajustar uso mais abaixo (flash messages, etc.).

NOTA: esta logica esta dentro de `aprovar_conferencia_fatura_transportadora`. Ler contexto para entender onde aplicar.

- [ ] **Step 3: Compile + commit**

```bash
python -m py_compile app/carvia/routes/fatura_routes.py
git add app/carvia/routes/fatura_routes.py
git commit -m "refactor(carvia): fatura_routes le requer_aprovacao do frete"
```

---

## Phase 11 — Remover endpoint registrar_pagamento_subcontrato

### Task 11.1: Grep final por callers JS

**Files:**
- None (investigacao apenas)

- [ ] **Step 1: Buscar referencias em JS, HTML e Python**

```bash
grep -rn "registrar-pagamento\|registrar_pagamento_subcontrato" app/ --include="*.py" --include="*.html" --include="*.js"
```

Resultado esperado (baseado em inventario previo): 2 referencias em comentarios + 1 endpoint. **Nenhum caller ativo**.

Se houver callers JS/HTML inesperados, adicionar tasks 11.Y para remove-los antes do Step 2 abaixo.

---

### Task 11.2: Deletar endpoint inteiro

**Files:**
- Modify: `app/carvia/routes/subcontrato_routes.py:642-712` (remover funcao completa)

- [ ] **Step 1: Edit remover bloco**

old_string: copiar linhas 642-712 do arquivo (do comentario/decorator `@bp.route('/subcontratos/<int:sub_id>/registrar-pagamento'...)` ate o final da funcao, incluindo linha em branco apos).

Use Read para pegar o bloco exato primeiro. Entao Edit para substituir por string vazia.

- [ ] **Step 2: Compile**

```bash
python -m py_compile app/carvia/routes/subcontrato_routes.py
```

- [ ] **Step 3: Commit**

```bash
git add app/carvia/routes/subcontrato_routes.py
git commit -m "refactor(carvia): remove endpoint registrar_pagamento_subcontrato"
```

---

## Phase 12 — Admin service cleanup

### Task 12.1: Remover resets obsoletos

**Files:**
- Modify: `app/carvia/services/admin/admin_service.py:614-625` (remover 4 linhas)

- [ ] **Step 1: Ler contexto**

```bash
sed -n '610,635p' app/carvia/services/admin/admin_service.py
```

- [ ] **Step 2: Edit**

old_string: (copiar bloco exato de ~618-624 que contem)
```python
        sub.valor_pago = None
        sub.valor_pago_em = None
        sub.valor_pago_por = None
        sub.requer_aprovacao = False
```

new_string: (vazio — remover essas 4 linhas)

Tambem buscar se ha reset de `sub.valor_considerado`, `sub.status_conferencia`, `sub.conferido_por`, `sub.conferido_em`, `sub.detalhes_conferencia` nas proximidades — remover todas.

- [ ] **Step 3: Compile + commit**

```bash
python -m py_compile app/carvia/services/admin/admin_service.py
git add app/carvia/services/admin/admin_service.py
git commit -m "refactor(carvia): admin remove resets obsoletos de Sub"
```

---

## Phase 13 — Templates

### Task 13.1: aprovacoes/processar.html — dict keys

**Files:**
- Modify: `app/templates/carvia/aprovacoes/processar.html` (linhas 98, 102, 107, 137, 141, 146, 177)

O template usa dict keys `caso_a.valor_cotado`, `caso_a.valor_considerado`, `caso_a.diferenca`, `caso_b.valor_cotado`, `caso_b.valor_pago`, `caso_b.diferenca`, `diff_pago_considerado.valor`. Estes sao dict keys, nao atributos diretos de model — vem da rota.

**Verificacao**: apos refactor em Task 9.3, o dict vem da rota construido a partir de `frete.valor_*`. As chaves permanecem (`caso_a.valor_cotado`, etc.), entao **o template NAO precisa mudar conteudo**.

Porem, substituir labels user-facing de "Subcontrato" para "Frete" nas secoes aplicaveis. Exemplo:
- `<h3>Aprovar Subcontrato</h3>` → `<h3>Aprovar Frete</h3>`
- `Cte Subcontratado` → `Frete` (onde apropriado)

- [ ] **Step 1: Grep labels**

```bash
grep -n "Subcontrato\|subcontrato\|sub\." app/templates/carvia/aprovacoes/processar.html
```

- [ ] **Step 2: Trocar labels visuais** (manter dict keys intactos)

Para cada match: decidir se e label user-facing (trocar) ou acesso a variavel/atributo (verificar se a rota passa frete agora).

- [ ] **Step 3: Commit**

```bash
git add app/templates/carvia/aprovacoes/processar.html
git commit -m "refactor(carvia): template processar.html labels Frete"
```

---

### Task 13.2: aprovacoes/listar.html — PERMANECE

**Files:**
- Modify: `app/templates/carvia/aprovacoes/listar.html` (linhas 116-121 permanecem)

Os snapshots `ap.valor_cotado_snap`, `ap.valor_considerado_snap`, `ap.valor_pago_snap`, `ap.diferenca_snap` sao campos do model `CarviaAprovacaoFrete` (ex-CarviaAprovacaoSubcontrato). Como renomeamos so a classe, os campos tem o mesmo nome. **NAO precisa mudar essas linhas**.

Porem: o loop `for linha in linhas` usa `linha.sub.XXX` ou similar — depende do que a rota passa. Apos Task 9.2, a rota passa `(aprovacao, frete)` tuples. Ajustar o loop.

- [ ] **Step 1: Ler o template**

```bash
sed -n '1,50p' app/templates/carvia/aprovacoes/listar.html
sed -n '100,160p' app/templates/carvia/aprovacoes/listar.html
```

- [ ] **Step 2: Trocar `linha.sub` por `linha.frete`** (ou adaptar conforme dict retornado pela rota)

- [ ] **Step 3: Commit**

```bash
git add app/templates/carvia/aprovacoes/listar.html
git commit -m "refactor(carvia): template listar aprovacoes le frete"
```

---

### Task 13.3: conta_corrente/extrato.html — renomear sub_valor_*

**Files:**
- Modify: `app/templates/carvia/conta_corrente/extrato.html:162-163`

- [ ] **Step 1: Edit**

old_string:
```html
                            <td class="text-end"><small>{{ m.sub_valor_considerado|valor_br if m.sub_valor_considerado is not none else '-' }}</small></td>
                            <td class="text-end"><small>{{ m.sub_valor_pago|valor_br if m.sub_valor_pago is not none else '-' }}</small></td>
```

new_string:
```html
                            <td class="text-end"><small>{{ m.frete_valor_considerado|valor_br if m.frete_valor_considerado is not none else '-' }}</small></td>
                            <td class="text-end"><small>{{ m.frete_valor_pago|valor_br if m.frete_valor_pago is not none else '-' }}</small></td>
```

NOTA: task 7.4 ja atualizou o dict retornado pela rota para usar `frete_valor_*`. Esta troca e o complemento.

- [ ] **Step 2: Commit**

```bash
git add app/templates/carvia/conta_corrente/extrato.html
git commit -m "refactor(carvia): extrato CC usa frete_valor_*"
```

---

### Task 13.4: subcontratos/detalhe.html — remover UI deprecada

**Files:**
- Modify: `app/templates/carvia/subcontratos/detalhe.html:106, 333-334, 514`

- [ ] **Step 1: Remover linha 106 (valor_considerado do sub)**

old_string:
```html
{{ sub.valor_considerado|valor_br if sub.valor_considerado else '-' }}
```

Decidir: substituir por `{{ sub.frete.valor_considerado|valor_br if sub.frete and sub.frete.valor_considerado else '-' }}` OU remover a linha.

Recomendacao: **substituir por via frete** para preservar info na UI.

- [ ] **Step 2: Linhas 333-334 (status_conferencia via fatura)**

Ler contexto:
```bash
sed -n '325,345p' app/templates/carvia/subcontratos/detalhe.html
```

Trocar `sub.fatura_transportadora.status_conferencia` — este usa a fatura nao o sub, entao permanece. Apenas verificar que continua funcionando.

- [ ] **Step 3: Linha 514 (texto obsoleto)**

old_string:
```
'Reset de valor_pago/valor_pago_em/valor_pago_por/requer_aprovacao'
```

Remover ou atualizar para refletir que reset agora e em frete (se aplicavel).

- [ ] **Step 4: Commit**

```bash
git add app/templates/carvia/subcontratos/detalhe.html
git commit -m "refactor(carvia): subcontratos/detalhe.html remove UI conferencia"
```

---

## Phase 14 — Migration final: DROP campos de Sub

### Task 14.1: SQL drop idempotente

**Files:**
- Create: `scripts/migrations/carvia_drop_sub_conferencia_fields.sql`

- [ ] **Step 1: Criar arquivo**

Use Write tool com path `scripts/migrations/carvia_drop_sub_conferencia_fields.sql` e conteudo:

```sql
-- Migration: DROP campos de conferencia em carvia_subcontratos
-- DEVE ser executada APOS todas as migrations do plano e deploy do codigo.
-- Data: 2026-04-14

ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS valor_pago;
ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS valor_pago_em;
ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS valor_pago_por;
ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS valor_considerado;
ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS status_conferencia;
ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS conferido_por;
ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS conferido_em;
ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS detalhes_conferencia;
ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS requer_aprovacao;

-- Drop tambem subcontrato_id em carvia_conta_corrente_transportadoras
-- (foi deprecado ao adicionar frete_id na Phase 5)
ALTER TABLE carvia_conta_corrente_transportadoras DROP COLUMN IF EXISTS subcontrato_id;
ALTER TABLE carvia_conta_corrente_transportadoras DROP COLUMN IF EXISTS compensacao_subcontrato_id;
```

- [ ] **Step 2: Commit**

```bash
git add scripts/migrations/carvia_drop_sub_conferencia_fields.sql
git commit -m "feat(carvia): SQL drop campos conferencia Sub (migration final)"
```

---

### Task 14.2: Python runner drop

**Files:**
- Create: `scripts/migrations/carvia_drop_sub_conferencia_fields.py`

- [ ] **Step 1: Criar arquivo**

Use Write tool com path `scripts/migrations/carvia_drop_sub_conferencia_fields.py` e conteudo:

```python
"""Migration: DROP campos de conferencia em carvia_subcontratos.

DEVE ser executada APOS todas as migrations do plano e deploy do codigo.
Idempotente via IF EXISTS.

Data: 2026-04-14
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


CAMPOS_SUB = [
    'valor_pago', 'valor_pago_em', 'valor_pago_por',
    'valor_considerado',
    'status_conferencia', 'conferido_por', 'conferido_em',
    'detalhes_conferencia', 'requer_aprovacao',
]

CAMPOS_CC = [
    'subcontrato_id',
    'compensacao_subcontrato_id',
]


def run_migration():
    print("=" * 70)
    print("MIGRATION: DROP campos obsoletos")
    print("=" * 70)

    print("1. Drop campos em carvia_subcontratos")
    for campo in CAMPOS_SUB:
        sql = f"ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS {campo}"
        print(f"  {sql}")
        db.session.execute(text(sql))

    print("2. Drop campos em carvia_conta_corrente_transportadoras")
    for campo in CAMPOS_CC:
        sql = f"ALTER TABLE carvia_conta_corrente_transportadoras DROP COLUMN IF EXISTS {campo}"
        print(f"  {sql}")
        db.session.execute(text(sql))

    db.session.commit()
    print()
    print("DROP concluido.")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        run_migration()
```

- [ ] **Step 2: Compile + commit**

```bash
python -m py_compile scripts/migrations/carvia_drop_sub_conferencia_fields.py
git add scripts/migrations/carvia_drop_sub_conferencia_fields.py
git commit -m "feat(carvia): Python runner drop campos conferencia Sub"
```

---

### Task 14.3: Remover campos do modelo CarviaSubcontrato

**Files:**
- Modify: `app/carvia/models/documentos.py:645-659` (remover 14 linhas)

- [ ] **Step 1: Edit remover bloco**

old_string:
```python
    # Conferencia individual (CTe vs TabelaFrete)
    valor_considerado = db.Column(db.Numeric(15, 2), nullable=True)
    status_conferencia = db.Column(db.String(20), nullable=False, default='PENDENTE')
    conferido_por = db.Column(db.String(100), nullable=True)
    conferido_em = db.Column(db.DateTime, nullable=True)
    detalhes_conferencia = db.Column(db.JSON, nullable=True)

    # Pagamento (manual, igual padrao Nacom Frete.valor_pago)
    # Independente do pagamento da fatura (status_pagamento da FT) — granularidade por sub
    valor_pago = db.Column(db.Numeric(15, 2), nullable=True)
    valor_pago_em = db.Column(db.DateTime, nullable=True)
    valor_pago_por = db.Column(db.String(100), nullable=True)

    # Flag de tratativa: True quando existe CarviaAprovacaoSubcontrato PENDENTE
    requer_aprovacao = db.Column(db.Boolean, nullable=False, default=False)
```

new_string: (vazio — ou comentario indicando que campos migraram)
```python
    # NOTA: campos de conferencia migrados para CarviaFrete em 2026-04-14
    # (ver docs/superpowers/plans/2026-04-14-carvia-frete-conferencia-migration.md)
```

- [ ] **Step 2: Compile**

```bash
python -m py_compile app/carvia/models/documentos.py
```

- [ ] **Step 3: Remover campos de `conta_corrente.py` tambem**

old_string: (bloco de `subcontrato_id` deprecated e `compensacao_subcontrato_id`)

new_string: remover os campos completamente.

- [ ] **Step 4: Compile + commit**

```bash
python -m py_compile app/carvia/models/documentos.py app/carvia/models/conta_corrente.py
git add app/carvia/models/documentos.py app/carvia/models/conta_corrente.py
git commit -m "refactor(carvia): remove campos obsoletos de Sub e CC do modelo"
```

---

## Phase 15 — Executar migrations em ordem + Self-audit final

### Task 15.1: Executar migrations na ordem correta

**Files:**
- Execute in order: (em ambiente local/staging, NAO em producao direto)

- [ ] **Step 1: Ativar venv**

```bash
source .venv/bin/activate
```

- [ ] **Step 2: Executar na ordem**

```bash
python scripts/migrations/carvia_frete_conferencia_fields.py
python scripts/migrations/carvia_aprovacoes_rename_frete.py
python scripts/migrations/carvia_cc_frete_id.py
# DROP deve ser ULTIMO
python scripts/migrations/carvia_drop_sub_conferencia_fields.py
```

- [ ] **Step 3: Verificar que nao ha erro**

Output esperado em cada: "RESULTADO" com contadores finais.

---

### Task 15.2: Compile geral de todos os arquivos modificados

- [ ] **Step 1: Compilar tudo**

```bash
find app/carvia -name "*.py" -exec python -m py_compile {} + 2>&1 | tail -20
python -m py_compile scripts/migrations/carvia_frete_conferencia_fields.py \
                     scripts/migrations/carvia_aprovacoes_rename_frete.py \
                     scripts/migrations/carvia_cc_frete_id.py \
                     scripts/migrations/carvia_drop_sub_conferencia_fields.py
```

Expected: sem erros.

---

### Task 15.3: Grep residual

- [ ] **Step 1: Grep por campos removidos em codigo**

```bash
grep -rn "sub\.valor_pago\|sub\.valor_considerado\|sub\.status_conferencia\|sub\.conferido_por\|sub\.conferido_em\|sub\.requer_aprovacao\|sub\.detalhes_conferencia\|sub\.valor_pago_em\|sub\.valor_pago_por" app/carvia/ app/templates/carvia/ --include="*.py" --include="*.html"
```

Expected: 0 matches.

- [ ] **Step 2: Grep por nomes antigos de classes/services**

```bash
grep -rn "CarviaAprovacaoSubcontrato\|aprovacao_subcontrato_service\|AprovacaoSubcontratoService\|carvia_aprovacoes_subcontrato" app/ --include="*.py" --include="*.html"
```

Expected: 0 matches (excluindo commit messages / historicos).

- [ ] **Step 3: Grep por endpoint removido**

```bash
grep -rn "registrar_pagamento_subcontrato\|registrar-pagamento" app/ --include="*.py" --include="*.html" --include="*.js"
```

Expected: 0 matches.

---

### Task 15.4: Teste manual end-to-end

- [ ] **Step 1: Iniciar dev server**

```bash
python run.py
```

- [ ] **Step 2: Smoke test de 4 telas**

1. Abrir `/carvia/fretes/<id>/editar` → preencher valor_cte/considerado/pago → salvar
2. Abrir `/carvia/faturas-transportadora/<id>/conferir` → verificar card "Total Pago" + coluna "Valor Pago"
3. Abrir `/carvia/subcontratos/aprovacoes` (ou rota renomeada) → verificar lista de tratativas
4. Abrir `/carvia/conta-corrente/<transportadora_id>/extrato` → verificar coluna "Valor Pago"

Expected: nenhum 500 Internal Server Error. Dados de conferencia consistentes com Frete.

- [ ] **Step 3: Commit final**

```bash
git log --oneline | head -50
```

Listar e confirmar que todos commits estao presentes em ordem.

---

## Self-Review Checklist

- [x] Todos os 9 campos de conferencia migrados de Sub para Frete
- [x] Tabela `carvia_aprovacoes_subcontrato` renomeada para `carvia_aprovacoes_frete`
- [x] FK `subcontrato_id` trocada para `frete_id` em ambas tabelas (aprovacoes e conta_corrente)
- [x] `AprovacaoSubcontratoService` renomeado para `AprovacaoFreteService`
- [x] Regra C (|pago - considerado| > R$5) implementada
- [x] ConferenciaService opera em Frete
- [x] ContaCorrenteService opera em Frete
- [x] aprovacao_routes processa Frete
- [x] Endpoint registrar_pagamento_subcontrato removido
- [x] Admin service resets obsoletos removidos
- [x] Templates atualizados (processar, listar, extrato CC, subcontratos/detalhe)
- [x] Migrations idempotentes (IF EXISTS, IF NOT EXISTS)
- [x] Ordem de execucao correta (add campos → rename → add FK → drop campos)
- [x] Compile geral sem erros
- [x] Grep residual sem matches

---

**FIM DO PLANO**
