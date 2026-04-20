"""Orquestrador de migrations pendentes de deploy no Render.

Executa, na ordem correta, todas as migrations commitadas apos a ultima
atualizacao do `build.sh` (commit 2715a026, 2026-04-17). Cada sub-script
e idempotente (verifica existencia antes de criar), portanto rodar este
orquestrador multiplas vezes e seguro.

Uso:
    # Render Shell (recomendado apos deploy)
    python scripts/deploy_pending_migrations.py

    # Execucao local/dev
    source .venv/bin/activate
    python scripts/deploy_pending_migrations.py

Comportamento:
- Executa cada migration como subprocess isolado (cada uma instancia seu
  proprio `create_app()` — mesmo padrao do `build.sh`).
- Continua mesmo se uma falhar (nao aborta a fila).
- Imprime sumario final com OK/FAIL/SKIP + duracao.
- Exit code 0 se todas OK; 1 se houver ao menos uma falha.

Ordem importa APENAS para modulo HORA (01 cria schema, 02-07 alteram).
Demais scripts sao independentes entre si, agrupados por commit/sprint
para rastreabilidade.

Referencias de commits:
- 0615bed8 (2026-04-18) — HORA 01-03
- bd6cca42 (2026-04-19) — HORA 04-07 + carvia_fatura_cliente_item_cte_complementar_id
- c2a6a763 (2026-04-19) — pessoal_features_f1_f2_f4
- a40eaf4a (2026-04-19) — CarVia Sprints A+B+D (a4, b2, d2, d6, d10)
- c3e46ca7 (2026-04-19) — CarVia Sprint E (e2, e3, e9)
- df7de2ba (2026-04-19) — CarVia F1 (f1_compensacao)
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = ROOT / "scripts" / "migrations"

# Ordem de execucao — HORA primeiro (01 cria schema, demais dependem).
# Demais grupos sao independentes; ordenados por commit para rastreabilidade.
MIGRATIONS: List[Tuple[str, str]] = [
    # --- HORA (ordem estrita: 01 cria tabelas, 02-07 alteram) ---
    ("HORA 01 — create schema (13 tabelas)", "hora_01_create_schema.py"),
    ("HORA 02 — pedido_item.chassi nullable", "hora_02_pedido_item_chassi_nullable.py"),
    ("HORA 03 — usuario.sistema_lojas flag", "hora_03_usuario_sistema_lojas.py"),
    ("HORA 04 — loja campos ReceitaWS", "hora_04_loja_campos_receita.py"),
    ("HORA 05 — loja latitude/longitude", "hora_05_loja_latlng.py"),
    ("HORA 06 — loja_destino_id (apelido)", "hora_06_loja_destino.py"),
    ("HORA 07 — nf_entrada.qtd_declarada", "hora_07_nf_entrada_qtd_declarada.py"),
    # --- CarVia item (fatura cliente x CTe complementar) ---
    (
        "CarVia — fatura_cliente_item.cte_complementar_id",
        "carvia_fatura_cliente_item_cte_complementar_id.py",
    ),
    # --- Pessoal (CPF/CNPJ + valor min/max) ---
    ("Pessoal — F1/F2/F4 (CPF/CNPJ + valor)", "pessoal_features_f1_f2_f4.py"),
    # --- CarVia Sprints A+B+D (5 scripts independentes) ---
    ("CarVia A4 — enderecos + correcoes", "carvia_a4_enderecos_e_correcoes.py"),
    ("CarVia B2 — unique numeros sequenciais", "carvia_b2_unique_numeros_sequenciais.py"),
    ("CarVia D2 — despesa FKs operacao/frete", "carvia_d2_despesa_fks.py"),
    ("CarVia D6 — fatura_transportadora autoria", "carvia_d6_autoria_status.py"),
    ("CarVia D10 — icms_valor/base_calculo persistidos", "carvia_d10_icms_valor_base.py"),
    # --- CarVia Sprint E (3 scripts) ---
    ("CarVia E2 — extrato_linha.linha_original_id", "carvia_e2_linha_original_id.py"),
    ("CarVia E3 — juros/desconto em conciliacoes", "carvia_e3_juros_desconto.py"),
    ("CarVia E9 — conferencia_historico (nova tabela)", "carvia_e9_conferencia_historico.py"),
    # --- CarVia F1 (compensacao cross-tipo) ---
    ("CarVia F1 — eh_compensacao + motivo", "carvia_f1_compensacao.py"),
]


TIMEOUT_PER_MIGRATION = 600  # 10 minutos — generoso para scripts com backfill


def _executar(script: str) -> Tuple[str, float, str]:
    """Executa uma migration via subprocess isolado.

    Returns:
        (status, duracao_seg, detalhe)
        status in {"OK", "FAIL", "SKIP"}.
    """
    path = MIGRATIONS_DIR / script
    if not path.exists():
        return ("SKIP", 0.0, f"arquivo nao encontrado: {path}")

    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_PER_MIGRATION,
            cwd=str(ROOT),
        )
    except subprocess.TimeoutExpired:
        return ("FAIL", TIMEOUT_PER_MIGRATION, f"timeout apos {TIMEOUT_PER_MIGRATION}s")
    dt = time.monotonic() - t0

    if proc.returncode == 0:
        return ("OK", dt, "")

    # Falha — capturar ultimas linhas de stderr/stdout para diagnostico.
    tail_err = (proc.stderr or "").strip().splitlines()[-8:]
    tail_out = (proc.stdout or "").strip().splitlines()[-3:]
    detalhe = "\n      ".join(["stderr:"] + tail_err + ["stdout:"] + tail_out)
    return ("FAIL", dt, detalhe)


def main() -> int:
    total = len(MIGRATIONS)
    print("=" * 68)
    print(f" DEPLOY PENDING MIGRATIONS — {total} scripts")
    print(f" Ordem: HORA (01-07) -> CarVia item -> Pessoal -> CarVia A+B+D -> E -> F1")
    print("=" * 68)
    print()

    resultados: List[Tuple[str, str, float, str]] = []
    t_inicio = time.monotonic()

    for idx, (nome, script) in enumerate(MIGRATIONS, start=1):
        prefix = f"[{idx:2d}/{total}] {nome:<55}"
        print(f"{prefix} ...", end=" ", flush=True)

        status, dt, detalhe = _executar(script)
        resultados.append((nome, status, dt, detalhe))

        marker = {"OK": "OK  ", "FAIL": "FAIL", "SKIP": "SKIP"}[status]
        print(f"{marker} ({dt:5.1f}s)")
        if detalhe and status != "OK":
            print(f"      {detalhe}")

    t_total = time.monotonic() - t_inicio

    ok = sum(1 for _, s, _, _ in resultados if s == "OK")
    fail = sum(1 for _, s, _, _ in resultados if s == "FAIL")
    skip = sum(1 for _, s, _, _ in resultados if s == "SKIP")

    print()
    print("=" * 68)
    print(f" SUMARIO: {ok} OK / {fail} FAIL / {skip} SKIP  (total {t_total:.1f}s)")
    print("=" * 68)

    if fail:
        print()
        print("FALHAS:")
        for nome, status, _, detalhe in resultados:
            if status == "FAIL":
                print(f"  - {nome}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
