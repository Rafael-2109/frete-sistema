"""
Migration: CHECK constraints no modulo de Custeio
Sprint 2 - C12 (auditoria 2026-05-10)

Aplica CHECK constraints idempotentes (DROP IF EXISTS + ADD) para garantir
integridade de valores enumerados em tipo_custo_selecionado, tipo_produto,
status, mes/ano, percentuais e coerencia de vigencias.

ANTES de aplicar: valida que nao ha violacoes em prod.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db


CHECKS_VALIDACAO = [
    ("tipo_custo_selecionado fora dos validos",
     "SELECT COUNT(*) FROM custo_considerado WHERE tipo_custo_selecionado NOT IN ('MEDIO_MES','ULTIMO_CUSTO','MEDIO_ESTOQUE','BOM','MANUAL','PRODUCAO')"),
    ("tipo_produto considerado fora dos validos",
     "SELECT COUNT(*) FROM custo_considerado WHERE tipo_produto NOT IN ('COMPRADO','INTERMEDIARIO','ACABADO')"),
    ("tipo_produto mensal fora dos validos",
     "SELECT COUNT(*) FROM custo_mensal WHERE tipo_produto NOT IN ('COMPRADO','INTERMEDIARIO','ACABADO')"),
    ("status mensal fora dos validos",
     "SELECT COUNT(*) FROM custo_mensal WHERE status NOT IN ('ABERTO','FECHADO')"),
    ("mes/ano custo_mensal invalidos",
     "SELECT COUNT(*) FROM custo_mensal WHERE NOT (mes BETWEEN 1 AND 12 AND ano >= 2020)"),
    ("percentual_frete fora 0-100",
     "SELECT COUNT(*) FROM custo_frete WHERE NOT (percentual_frete >= 0 AND percentual_frete <= 100)"),
    ("comissao_percentual fora 0-30",
     "SELECT COUNT(*) FROM regra_comissao WHERE NOT (comissao_percentual >= 0 AND comissao_percentual <= 30)"),
    ("vigencia_fim < vigencia_inicio em custo_frete",
     "SELECT COUNT(*) FROM custo_frete WHERE vigencia_fim IS NOT NULL AND vigencia_fim <= vigencia_inicio"),
    ("vigencia_fim < vigencia_inicio em regra_comissao",
     "SELECT COUNT(*) FROM regra_comissao WHERE vigencia_fim IS NOT NULL AND vigencia_fim < vigencia_inicio"),
]

CONSTRAINTS_DDL = [
    ("custo_considerado", "chk_tipo_custo_selecionado",
     "CHECK (tipo_custo_selecionado IN ('MEDIO_MES','ULTIMO_CUSTO','MEDIO_ESTOQUE','BOM','MANUAL','PRODUCAO'))"),
    ("custo_considerado", "chk_tipo_produto_considerado",
     "CHECK (tipo_produto IN ('COMPRADO','INTERMEDIARIO','ACABADO'))"),
    ("custo_mensal", "chk_tipo_produto_mensal",
     "CHECK (tipo_produto IN ('COMPRADO','INTERMEDIARIO','ACABADO'))"),
    ("custo_mensal", "chk_status_mensal",
     "CHECK (status IN ('ABERTO','FECHADO'))"),
    ("custo_mensal", "chk_mes_ano_validos",
     "CHECK (mes BETWEEN 1 AND 12 AND ano >= 2020)"),
    ("custo_frete", "chk_percentual_frete",
     "CHECK (percentual_frete >= 0 AND percentual_frete <= 100)"),
    ("regra_comissao", "chk_comissao_percentual",
     "CHECK (comissao_percentual >= 0 AND comissao_percentual <= 30)"),
    ("custo_frete", "chk_vigencia_coerente_frete",
     "CHECK (vigencia_fim IS NULL OR vigencia_fim > vigencia_inicio)"),
    ("regra_comissao", "chk_vigencia_coerente_comissao",
     "CHECK (vigencia_fim IS NULL OR vigencia_fim >= vigencia_inicio)"),
]


def run():
    app = create_app()
    with app.app_context():
        # 1. Validacao
        print("Validando dados antes de aplicar CHECK constraints...")
        violacoes_total = 0
        for nome, query in CHECKS_VALIDACAO:
            count = db.session.execute(db.text(query)).scalar() or 0
            status = "OK" if count == 0 else f"FALHA ({count} violacoes)"
            print(f"  [{status}] {nome}")
            violacoes_total += int(count)

        if violacoes_total > 0:
            print(f"\nERRO: {violacoes_total} violacoes encontradas. Resolver antes de aplicar.")
            sys.exit(1)

        # 2. Aplicar
        print("\nAplicando CHECK constraints...")
        for tabela, nome, ddl in CONSTRAINTS_DDL:
            db.session.execute(db.text(f"ALTER TABLE {tabela} DROP CONSTRAINT IF EXISTS {nome}"))
            db.session.execute(db.text(f"ALTER TABLE {tabela} ADD CONSTRAINT {nome} {ddl}"))
            print(f"  OK {tabela}.{nome}")

        db.session.commit()
        print("\nTodas as CHECK constraints aplicadas com sucesso.")


if __name__ == '__main__':
    run()
