"""Relatorio HORA 32: detecta duplicacoes de modelo e sugere merge.

Read-only — nao executa merge. Operador usa o relatorio como guia para
abrir /hora/modelos/unificar e resolver caso a caso.

Logica:
  - Agrupa modelos por hora_tagplus_produto_map.tagplus_produto_id.
  - Onde houver 2+ modelos para o mesmo tagplus_id, sugere canonico
    (modelo com mais motos) e lista os outros como aliases candidatos.

Uso:
    python scripts/migrations/hora_32_sugestoes_merge.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)


def _build_sql_detectar(tem_emprestimo: bool) -> str:
    qtd_emp = (
        '(SELECT COUNT(*) FROM hora_emprestimo_moto WHERE modelo_id = m.id)'
        if tem_emprestimo else '0'
    )
    return f"""
SELECT
  pm.tagplus_produto_id,
  pm.tagplus_codigo,
  m.id        AS modelo_id,
  m.nome_modelo,
  m.ativo,
  m.merged_em_id,
  (SELECT COUNT(*) FROM hora_moto WHERE modelo_id = m.id) AS qtd_motos,
  (SELECT COUNT(*) FROM hora_pedido_item WHERE modelo_id = m.id) AS qtd_pedido_itens,
  (SELECT COUNT(*) FROM hora_recebimento_conferencia WHERE modelo_id_conferido = m.id) AS qtd_conferencias,
  {qtd_emp} AS qtd_emprestimos,
  (SELECT COUNT(*) FROM hora_tabela_preco WHERE modelo_id = m.id) AS qtd_tabela_preco
FROM hora_modelo m
INNER JOIN hora_tagplus_produto_map pm ON pm.modelo_id = m.id
WHERE m.merged_em_id IS NULL
ORDER BY pm.tagplus_produto_id, qtd_motos DESC;
"""


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tem_emprestimo = inspector.has_table('hora_emprestimo_moto')
        sql = _build_sql_detectar(tem_emprestimo)
        rows = db.session.execute(text(sql)).fetchall()

        # Agrupa por tagplus_produto_id
        grupos: dict[str, list] = {}
        for r in rows:
            grupos.setdefault(r.tagplus_produto_id, []).append(r)

        duplicados = {tid: lst for tid, lst in grupos.items() if len(lst) > 1}

        print(f'\n=== Detector de duplicacoes (via hora_tagplus_produto_map) ===')
        print(f'Total tagplus_produto_id distintos com mapping: {len(grupos)}')
        print(f'Total grupos com 2+ modelos (DUPLICACOES): {len(duplicados)}')

        if not duplicados:
            print('\nNenhuma duplicacao detectada. Nada a fazer.')
            return

        # Tambem detecta modelos sem tagplus_map mas com nome similar a outros
        # com tagplus_map. Heuristica simples: substring case-insensitive.
        modelos_sem_map = db.session.execute(text("""
            SELECT m.id, m.nome_modelo,
                   (SELECT COUNT(*) FROM hora_moto WHERE modelo_id = m.id) AS qtd_motos
            FROM hora_modelo m
            LEFT JOIN hora_tagplus_produto_map pm ON pm.modelo_id = m.id
            WHERE pm.id IS NULL
              AND m.merged_em_id IS NULL
              AND m.ativo = TRUE
            ORDER BY m.nome_modelo
        """)).fetchall()

        print('\n--- Grupos detectados ---\n')
        for tid, modelos in duplicados.items():
            codigo = modelos[0].tagplus_codigo or '-'
            print(f'TagPlus #{tid} ({codigo}) — {len(modelos)} modelos:')
            canonico = max(modelos, key=lambda r: r.qtd_motos)
            for m in modelos:
                marker = '** CANONICO SUGERIDO **' if m.modelo_id == canonico.modelo_id else 'alias candidato'
                print(
                    f'    [{marker}] id={m.modelo_id:3d} nome={m.nome_modelo!r:30s} '
                    f'motos={m.qtd_motos:4d} pi={m.qtd_pedido_itens:3d} '
                    f'conf={m.qtd_conferencias:3d} emp={m.qtd_emprestimos:3d} '
                    f'tp={m.qtd_tabela_preco}'
                )
            print()

        # Sugestoes de orfaos por similaridade textual
        print('\n--- Modelos sem tagplus_map que talvez devam virar alias ---')
        print('(Heuristica: nome_modelo contem nome de canonico — operador valida)')
        canonicos_nomes = []
        for tid, modelos in duplicados.items():
            canonicos_nomes.extend([m.nome_modelo for m in modelos if m.qtd_motos > 0])
        # tambem inclui canonicos NAO duplicados
        outros_canonicos = db.session.execute(text("""
            SELECT m.nome_modelo FROM hora_modelo m
            INNER JOIN hora_tagplus_produto_map pm ON pm.modelo_id = m.id
            WHERE m.merged_em_id IS NULL AND m.ativo = TRUE
        """)).fetchall()
        canonicos_nomes.extend([r.nome_modelo for r in outros_canonicos])

        for orf in modelos_sem_map:
            nome_norm = orf.nome_modelo.upper()
            matches = [
                c for c in canonicos_nomes
                if c and (c.upper() in nome_norm or nome_norm in c.upper())
                and c.upper() != nome_norm
            ]
            if matches:
                print(
                    f'  id={orf.id:3d} nome={orf.nome_modelo!r:40s} motos={orf.qtd_motos} '
                    f'-> candidatos: {sorted(set(matches))}'
                )

        print('\n--- Como aplicar ---')
        print('1. Acessar /hora/modelos/unificar (requer permissao modelos/aprovar).')
        print('2. Para cada grupo, verificar canonico sugerido e ajustar se necessario.')
        print('3. Clicar "Preview impacto" para ver contadores.')
        print('4. Clicar "Executar merge" para aplicar (irreversivel).')
        print('5. Apos merges, revisar pendencias em /hora/modelos/pendencias.')


if __name__ == '__main__':
    main()
