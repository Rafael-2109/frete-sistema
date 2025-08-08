"""
Runner simples para validar os 3 casos de abatimento de MovimentacaoPrevista
sem depender do pytest (evita configurações de cobertura/plugins).

Uso:
  source .venv/bin/activate && python scripts/testes/test_faturamento_mov_prevista_runner.py
"""

import os
import sys


def main() -> int:
    # Força banco em memória e modo de teste
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("ENVIRONMENT", "testing")

    from tests.test_faturamento_mov_prevista import (
        test_caso1_nf_encontra_separacao_abate_prevista,
        test_caso2_nf_sem_separacao_nao_abate_prevista,
        test_caso3_nf_ja_tem_sem_separacao_e_depois_encontra_separacao_abate_prevista,
    )

    total = 0
    falhas = 0

    for nome, fn in (
        ("Caso 1 - NF encontra separação (abate)", test_caso1_nf_encontra_separacao_abate_prevista),
        ("Caso 2 - NF sem separação (não abate)", test_caso2_nf_sem_separacao_nao_abate_prevista),
        ("Caso 3 - Já tinha 'Sem Separação' e encontra separação (abate)", test_caso3_nf_ja_tem_sem_separacao_e_depois_encontra_separacao_abate_prevista),
    ):
        total += 1
        try:
            fn()
            print(f"✅ {nome}")
        except AssertionError as e:
            falhas += 1
            print(f"❌ {nome}: {e}")
        except Exception as e:
            falhas += 1
            print(f"❌ {nome} (erro inesperado): {e}")

    print(f"\nResumo: {total - falhas}/{total} casos OK")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())


