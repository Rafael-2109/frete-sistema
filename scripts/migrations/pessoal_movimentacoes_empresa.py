"""Migration: Grupo 'Movimentacoes Empresa' + 2 categorias compensaveis.

Criado para permitir pareamento intra-day de transferencias entre contas
pessoais e empresas do grupo (La Famiglia, AANP, Sogima, NG Promo, Parnaplast,
Nacom Goya).

Diferente de 'Desconsiderar':
- 'Desconsiderar' = nunca aparece em relatorio (saldo anterior, exclusoes)
- 'Movimentacoes Empresa' = aparece quando ha RESIDUO (compensacao parcial);
  some quando 100% casado (via PessoalCompensacao.valor_compensado >= valor).

Idempotente (ON CONFLICT DO NOTHING).
"""
from app import create_app, db
from sqlalchemy import text


def main():
    app = create_app()
    with app.app_context():
        print('[*] Iniciando migration pessoal_movimentacoes_empresa...')

        db.session.execute(text("""
            INSERT INTO pessoal_categorias (nome, grupo, icone, ativa, compensavel_tipo, criado_em)
            VALUES ('Empresa - Entrada', 'Movimentacoes Empresa', 'fa-arrow-down', TRUE, 'E', NOW())
            ON CONFLICT ON CONSTRAINT uq_pessoal_categorias_grupo_nome DO NOTHING
        """))
        db.session.execute(text("""
            INSERT INTO pessoal_categorias (nome, grupo, icone, ativa, compensavel_tipo, criado_em)
            VALUES ('Empresa - Saida', 'Movimentacoes Empresa', 'fa-arrow-up', TRUE, 'S', NOW())
            ON CONFLICT ON CONSTRAINT uq_pessoal_categorias_grupo_nome DO NOTHING
        """))
        db.session.commit()

        rows = db.session.execute(text("""
            SELECT id, nome, grupo, compensavel_tipo
            FROM pessoal_categorias
            WHERE grupo = 'Movimentacoes Empresa'
            ORDER BY nome
        """)).fetchall()
        for r in rows:
            print(f'  [OK] id={r[0]} {r[1]} (grupo={r[2]}, compensavel={r[3]})')
        print('[OK] Migration concluida.')


if __name__ == '__main__':
    main()
