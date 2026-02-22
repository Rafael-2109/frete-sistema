"""
Fix: Corrigir nf_devolucao_linha onde qtd_por_caixa=1 (tratadas como caixa 1:1)
mas o preço da NFD indica claramente UNIDADE individual.

Contexto:
    26 linhas de diversos produtos Campo Belo foram auto-resolvidas via DEPARA/DEPARA_GRUPO
    com qtd_por_caixa=1 (tratadas como caixa 1:1). Porém o preço unitário da NFD é
    compatível com preço de UNIDADE individual, não de CAIXA.

    Fórmula de validação:
        mediana_caixa = mediana(faturamento_produto.preco_produto_faturado)
        preco_unidade_est = mediana_caixa / N (do padrão NxM no nome_produto)
        ratio_como_unidade = valor_unitario / preco_unidade_est
        ratio_como_caixa = mediana_caixa / valor_unitario
        → Se ratio_UN < 1.5 e ratio_CX > 2.5 → É UNIDADE (não caixa)

    Critérios aplicados (conservadores):
        - Produto com >= 5 vendas no faturamento
        - Padrão NxM > 1 no nome do cadastro
        - ratio_UN < 1.5 (preço NFD próximo do estimado por unidade)
        - ratio_CX > 2.5 (preço NFD claramente abaixo da caixa)

    5 linhas corretamente CAIXA excluídas:
        8268 (CXA1, ratio_cx=0.98), 8283 (CXA1, ratio_cx=1.04),
        8285 (CXA1, ratio_cx=1.01), 8287 (CXA1, ratio_cx=1.01),
        8288 (CXA1, ratio_cx=0.87)

Correção:
    - qtd_por_caixa = N (fator do padrão NxM)
    - quantidade_convertida = quantidade / N
    - peso_bruto = quantidade_convertida * peso_bruto_produto
    - metodo_resolucao += '+PRECO'

Executar:
    source .venv/bin/activate
    python scripts/migrations/fix_nfd_linha_caixa_preco_unidade.py          # dry-run
    python scripts/migrations/fix_nfd_linha_caixa_preco_unidade.py --apply  # executa
"""

import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# 26 linhas anômalas identificadas via query no Render (2026-02-21)
# Fonte: faturamento_produto (mediana), cadastro_palletizacao (NxM, peso_bruto)
# Todas com veredicto=UNIDADE pela fórmula de preço
CORRECOES = [
    # ndl_id, cod_produto, un, qtd, fator_n, peso_prod, metodo_atual, ratio_un, ratio_cx
    {'ndl_id': 8267,  'cod_produto': '4320162', 'quantidade': 2.0,   'fator_n': 6,  'peso_prod': 21.0,  'metodo_atual': 'DEPARA'},
    {'ndl_id': 8274,  'cod_produto': '4320156', 'quantidade': 300.0, 'fator_n': 6,  'peso_prod': 10.2,  'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8275,  'cod_produto': '4310156', 'quantidade': 18.0,  'fator_n': 6,  'peso_prod': 10.2,  'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8276,  'cod_produto': '4310164', 'quantidade': 192.0, 'fator_n': 6,  'peso_prod': 21.0,  'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8277,  'cod_produto': '4520156', 'quantidade': 42.0,  'fator_n': 6,  'peso_prod': 10.2,  'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8278,  'cod_produto': '4080154', 'quantidade': 960.0, 'fator_n': 12, 'peso_prod': 7.8,   'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8281,  'cod_produto': '4520161', 'quantidade': 16.0,  'fator_n': 6,  'peso_prod': 13.4,  'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8284,  'cod_produto': '4030156', 'quantidade': 3.0,   'fator_n': 6,  'peso_prod': 10.2,  'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8286,  'cod_produto': '4080162', 'quantidade': 6.0,   'fator_n': 6,  'peso_prod': 21.0,  'metodo_atual': 'DEPARA'},
    {'ndl_id': 8290,  'cod_produto': '4310164', 'quantidade': 2.0,   'fator_n': 6,  'peso_prod': 21.0,  'metodo_atual': 'DEPARA'},
    {'ndl_id': 8291,  'cod_produto': '4070162', 'quantidade': 4.0,   'fator_n': 6,  'peso_prod': 21.0,  'metodo_atual': 'DEPARA'},
    {'ndl_id': 8292,  'cod_produto': '4310148', 'quantidade': 26.0,  'fator_n': 30, 'peso_prod': 5.87,  'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8296,  'cod_produto': '4310141', 'quantidade': 108.0, 'fator_n': 36, 'peso_prod': 5.23,  'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8297,  'cod_produto': '4520161', 'quantidade': 6.0,   'fator_n': 6,  'peso_prod': 13.4,  'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8298,  'cod_produto': '4320154', 'quantidade': 12.0,  'fator_n': 12, 'peso_prod': 7.8,   'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8299,  'cod_produto': '4360147', 'quantidade': 18.0,  'fator_n': 18, 'peso_prod': 5.46,  'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8300,  'cod_produto': '4510145', 'quantidade': 60.0,  'fator_n': 30, 'peso_prod': 5.57,  'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8301,  'cod_produto': '4310162', 'quantidade': 10.0,  'fator_n': 6,  'peso_prod': 21.0,  'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8302,  'cod_produto': '4320162', 'quantidade': 1.0,   'fator_n': 6,  'peso_prod': 21.0,  'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8303,  'cod_produto': '4320147', 'quantidade': 54.0,  'fator_n': 18, 'peso_prod': 5.46,  'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8304,  'cod_produto': '4310152', 'quantidade': 83.0,  'fator_n': 18, 'peso_prod': 6.0,   'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8305,  'cod_produto': '4350150', 'quantidade': 54.0,  'fator_n': 18, 'peso_prod': 6.0,   'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8306,  'cod_produto': '4840176', 'quantidade': 12.0,  'fator_n': 12, 'peso_prod': 2.68,  'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8307,  'cod_produto': '4080162', 'quantidade': 7.0,   'fator_n': 6,  'peso_prod': 21.0,  'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8308,  'cod_produto': '4030162', 'quantidade': 35.0,  'fator_n': 6,  'peso_prod': 21.0,  'metodo_atual': 'DEPARA_GRUPO'},
    {'ndl_id': 8311,  'cod_produto': '4510145', 'quantidade': 36.0,  'fator_n': 30, 'peso_prod': 5.57,  'metodo_atual': 'DEPARA_GRUPO'},
]


def run(dry_run: bool = True):
    from app import create_app, db
    from sqlalchemy import text

    app = create_app()
    with app.app_context():
        logger.info("=" * 70)
        logger.info("FIX: nf_devolucao_linha — CAIXA → UNIDADE (validação por preço)")
        logger.info(f"Modo: {'DRY-RUN' if dry_run else 'APLICAR'}")
        logger.info(f"Linhas a corrigir: {len(CORRECOES)}")
        logger.info("=" * 70)

        # 1. Verificar estado atual (before) — só linhas que ainda têm qtd_por_caixa=1
        ids = [c['ndl_id'] for c in CORRECOES]
        rows = db.session.execute(text("""
            SELECT id, codigo_produto_interno, unidade_medida, quantidade,
                   quantidade_convertida, qtd_por_caixa, metodo_resolucao, peso_bruto
            FROM nf_devolucao_linha
            WHERE id = ANY(:ids)
              AND qtd_por_caixa = 1
            ORDER BY id
        """), {'ids': ids}).fetchall()

        if not rows:
            logger.info("Nenhuma linha pendente de correção (já aplicado ou IDs mudaram)")
            return

        ids_encontrados = {r[0] for r in rows}
        correcoes_aplicaveis = [c for c in CORRECOES if c['ndl_id'] in ids_encontrados]

        logger.info(f"\nLinhas encontradas com qtd_por_caixa=1: {len(rows)}")
        if len(rows) < len(CORRECOES):
            ids_ausentes = set(ids) - ids_encontrados
            logger.info(f"IDs já corrigidos ou ausentes: {ids_ausentes}")

        logger.info(f"\n{'='*70}")
        logger.info("ESTADO ATUAL (before):")
        logger.info(f"{'='*70}")
        for r in rows:
            logger.info(
                f"  ndl.id={r[0]} | cod={r[1]} | un={r[2]} | qtd={r[3]} | "
                f"qtd_conv={r[4]} | qtd_cx={r[5]} | metodo={r[6]} | peso={r[7]}"
            )

        # 2. Calcular correções
        logger.info(f"\n{'='*70}")
        logger.info("CORREÇÕES PLANEJADAS:")
        logger.info(f"{'='*70}")

        updates = []
        for c in correcoes_aplicaveis:
            nova_conv = round(c['quantidade'] / c['fator_n'], 3)
            novo_peso = round(nova_conv * c['peso_prod'], 2)
            novo_metodo = c['metodo_atual'] + '+PRECO'

            updates.append({
                'id': c['ndl_id'],
                'qtd_por_caixa': c['fator_n'],
                'quantidade_convertida': nova_conv,
                'peso_bruto': novo_peso,
                'metodo_resolucao': novo_metodo,
            })

            logger.info(
                f"  ndl.id={c['ndl_id']} | {c['cod_produto']} | "
                f"qtd_cx: 1 → {c['fator_n']} | "
                f"qtd_conv: {c['quantidade']} → {nova_conv} | "
                f"peso: → {novo_peso} | "
                f"metodo: {c['metodo_atual']} → {novo_metodo}"
            )

        if dry_run:
            logger.info(f"\n{'='*70}")
            logger.info(f"DRY-RUN: {len(updates)} linhas seriam corrigidas")
            logger.info(f"{'='*70}")
            logger.info("Para aplicar: python scripts/migrations/fix_nfd_linha_caixa_preco_unidade.py --apply")
            return

        # 3. Aplicar correções
        logger.info(f"\n{'='*70}")
        logger.info("APLICANDO CORREÇÕES...")
        logger.info(f"{'='*70}")

        for upd in updates:
            db.session.execute(text("""
                UPDATE nf_devolucao_linha
                SET qtd_por_caixa = :qtd_por_caixa,
                    quantidade_convertida = :quantidade_convertida,
                    peso_bruto = :peso_bruto,
                    metodo_resolucao = :metodo_resolucao,
                    atualizado_em = NOW()
                WHERE id = :id
                  AND qtd_por_caixa = 1
            """), upd)

        db.session.commit()
        logger.info(f"\n✅ {len(updates)} linhas corrigidas com sucesso")

        # 4. Verificar estado final (after)
        rows_after = db.session.execute(text("""
            SELECT id, codigo_produto_interno, unidade_medida, quantidade,
                   quantidade_convertida, qtd_por_caixa, metodo_resolucao, peso_bruto
            FROM nf_devolucao_linha
            WHERE id = ANY(:ids)
            ORDER BY id
        """), {'ids': [c['ndl_id'] for c in correcoes_aplicaveis]}).fetchall()

        logger.info(f"\n{'='*70}")
        logger.info("ESTADO FINAL (after):")
        logger.info(f"{'='*70}")
        for r in rows_after:
            logger.info(
                f"  ndl.id={r[0]} | cod={r[1]} | un={r[2]} | qtd={r[3]} | "
                f"qtd_conv={r[4]} | qtd_cx={r[5]} | metodo={r[6]} | peso={r[7]}"
            )


if __name__ == '__main__':
    apply = '--apply' in sys.argv
    run(dry_run=not apply)
