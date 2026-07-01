"""Backfill de dados — correcao dos achados da auditoria do modulo Pessoal (2026-07-01).

Reconcilia dados JA gravados que os fixes de codigo (A1/A2/B1/B2/C1/transferencia/P3)
passam a impedir daqui pra frente. IDEMPOTENTE: as clausulas so casam o que ainda precisa
mudar, entao pode rodar quantas vezes precisar.

Passos:
  A2  compensavel (S/E) marcada excluida SEM compensacao total -> volta ao relatorio (residual visivel)
  B1  compra-principal do Pix-no-Credito des-excluida            -> re-excluir (nao contar 2x)
  C1  duplicatas de re-import Bradesco CC (mesmo Docto)          -> remover a copia do import mais novo
  TR  transferencia entre contas propria sem categoria (Layer 0.7)-> atribuir 'Transferencia entre contas'
  R989 regra degenerada (padrao 'NULL'/'NONE'/'NAN')            -> desativar
  REL RELATIVO com categorias_restritas apontando categoria inexistente -> sanear o JSON

Uso (o codigo dos fixes DEVE estar deployado antes):
    # preview LOCAL (dados de teste):
    python scripts/migrations/pessoal_auditoria_backfill.py --dry-run
    # preview PRODUCAO (read-only, rollback):
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/migrations/pessoal_auditoria_backfill.py --dry-run
    # aplicar em PRODUCAO:
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/migrations/pessoal_auditoria_backfill.py --apply
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402


def _p(msg):
    print(msg, flush=True)


def passo_a2():
    """Compensavel (S/E) excluida indevidamente sem compensacao total -> excluir=FALSE."""
    sel = text("""
        SELECT t.id, t.valor, t.valor_compensado
        FROM pessoal_transacoes t
        JOIN pessoal_categorias c ON c.id = t.categoria_id
        WHERE t.excluir_relatorio = TRUE
          AND c.compensavel_tipo IS NOT NULL
          AND COALESCE(t.valor_compensado, 0) < t.valor
          AND t.eh_pagamento_cartao = FALSE
          AND t.eh_transferencia_propria = FALSE
          AND c.grupo <> 'Desconsiderar'
          AND COALESCE(t.eh_pix_credito, FALSE) = FALSE
    """)
    rows = db.session.execute(sel).fetchall()
    _p(f"[A2] compensavel excluida indevidamente: {len(rows)} tx")
    for r in rows:
        _p(f"     id={r.id} valor={r.valor} compensado={r.valor_compensado} -> excluir_relatorio=FALSE")
    ids = [r.id for r in rows]
    if ids:
        db.session.execute(
            text("UPDATE pessoal_transacoes SET excluir_relatorio=FALSE WHERE id = ANY(:ids)"),
            {"ids": ids},
        )
    return len(ids)


def passo_b1():
    """Compra-principal do Pix-no-Credito des-excluida -> excluir=TRUE (nao duplicar principal)."""
    sel = text("""
        SELECT id, valor, pix_credito_grupo
        FROM pessoal_transacoes
        WHERE tipo = 'debito'
          AND pix_credito_grupo IS NOT NULL
          AND hash_transacao NOT LIKE 'pixjuros-%'
          AND observacao LIKE '%Pix no Credito: original%'
          AND excluir_relatorio = FALSE
    """)
    rows = db.session.execute(sel).fetchall()
    _p(f"[B1] compra-principal Pix-credito des-excluida: {len(rows)} tx (soma R${sum(float(r.valor) for r in rows):.2f})")
    for r in rows:
        _p(f"     id={r.id} valor={r.valor} grupo={r.pix_credito_grupo} -> excluir_relatorio=TRUE")
    ids = [r.id for r in rows]
    if ids:
        db.session.execute(
            text("UPDATE pessoal_transacoes SET excluir_relatorio=TRUE WHERE id = ANY(:ids)"),
            {"ids": ids},
        )
    return len(ids)


# C1: as 10 duplicatas de re-import auditadas MANUALMENTE (mesmo contraparte, so a grafia
# do Pix difere). Cada tupla = (id_a_remover, documento_esperado, valor_esperado). NAO usar
# query generica de GROUP BY: documento nao e unico (docs mapeiam >1 evento distinto), o que
# faria a query apagar transacoes LEGITIMAS. Removemos so a copia do import MAIS NOVO,
# validando gemeo (mesmo conta/doc/data/valor/tipo de OUTRO import) + zero dependencias.
_C1_DUPLICATAS_A_REMOVER = [
    (3882, '1532235', 100.00),
    (3867, '1554213', 25000.00),
    (3986, '1619494', 3000.00),
    (3981, '1630001', 380.00),
    (3982, '1630403', 500.00),
    (3883, '1710113', 500.00),
    (3884, '1858018', 100.00),
    (3871, '1942339', 285.00),
    (3983, '2025194', 200.00),
    (3984, '2025334', 200.00),
]


def passo_c1():
    """Remove as 10 copias de re-import Bradesco CC auditadas (IDs explicitos + guards)."""
    removidos = 0
    total = 0.0
    for tid, doc, val in _C1_DUPLICATAS_A_REMOVER:
        r = db.session.execute(text("""
            SELECT t.id, t.valor, t.documento, t.transferencia_par_id, t.pix_credito_grupo,
                   t.valor_compensado,
                   EXISTS(SELECT 1 FROM pessoal_transacoes x WHERE x.transferencia_par_id=t.id) AS eh_par,
                   EXISTS(SELECT 1 FROM pessoal_importacoes i WHERE i.transacao_pagamento_id=t.id) AS paga_fatura,
                   EXISTS(
                     SELECT 1 FROM pessoal_transacoes g
                     WHERE g.id <> t.id AND g.conta_id=t.conta_id AND g.documento=t.documento
                       AND g.data=t.data AND g.valor=t.valor AND g.tipo=t.tipo
                       AND g.importacao_id <> t.importacao_id
                   ) AS tem_gemeo
            FROM pessoal_transacoes t WHERE t.id=:id
        """), {"id": tid}).fetchone()
        if r is None:
            _p(f"[C1] id={tid} ja removido/ausente — pulo (idempotente)")
            continue
        # Guards de seguranca: documento/valor esperados + tem gemeo de outro import + sem deps
        if str(r.documento) != doc or abs(float(r.valor) - val) > 0.001:
            _p(f"[C1] id={tid} NAO bate documento/valor esperado ({r.documento}/{r.valor} != {doc}/{val}) — PULO")
            continue
        if not r.tem_gemeo:
            _p(f"[C1] id={tid} sem gemeo de outro import — PULO (nao e mais duplicata)")
            continue
        if (r.transferencia_par_id is not None or r.pix_credito_grupo is not None
                or float(r.valor_compensado or 0) != 0 or r.eh_par or r.paga_fatura):
            _p(f"[C1] id={tid} tem dependencia — PULO (nao remover)")
            continue
        _p(f"[C1] DELETE id={tid} doc={doc} valor={r.valor} (copia de re-import)")
        db.session.execute(text("DELETE FROM pessoal_transacoes WHERE id=:id"), {"id": tid})
        removidos += 1
        total += float(r.valor)
    _p(f"[C1] duplicatas removidas: {removidos} (soma R${total:.2f})")
    return removidos


def passo_transferencia():
    """Transferencia entre contas propria (Layer 0.7) sem categoria -> categoria canonica."""
    cat = db.session.execute(text("""
        SELECT id FROM pessoal_categorias
        WHERE grupo='Desconsiderar' AND nome ILIKE 'transfer%entre%contas%' AND ativa=TRUE
        LIMIT 1
    """)).fetchone()
    if not cat:
        _p("[TR] categoria 'Transferencia entre contas' NAO encontrada — pulo (crie a categoria antes)")
        return 0
    cat_id = cat.id
    rows = db.session.execute(text("""
        SELECT id FROM pessoal_transacoes
        WHERE eh_transferencia_propria = TRUE AND categoria_id IS NULL
    """)).fetchall()
    _p(f"[TR] transferencia propria sem categoria: {len(rows)} tx -> categoria_id={cat_id}")
    ids = [r.id for r in rows]
    if ids:
        db.session.execute(
            text("UPDATE pessoal_transacoes SET categoria_id=:c WHERE id = ANY(:ids)"),
            {"c": cat_id, "ids": ids},
        )
    return len(ids)


def passo_regra_degenerada():
    """Regra aprendida com padrao 'NULL'/'NONE'/'NAN' -> desativar."""
    rows = db.session.execute(text("""
        SELECT id, padrao_historico FROM pessoal_regras_categorizacao
        WHERE ativo = TRUE AND upper(padrao_historico) IN ('NULL','NONE','NAN')
    """)).fetchall()
    _p(f"[R989] regras degeneradas ativas: {len(rows)}")
    for r in rows:
        _p(f"     id={r.id} padrao='{r.padrao_historico}' -> ativo=FALSE")
    ids = [r.id for r in rows]
    if ids:
        db.session.execute(
            text("UPDATE pessoal_regras_categorizacao SET ativo=FALSE WHERE id = ANY(:ids)"),
            {"ids": ids},
        )
    return len(ids)


def passo_relativo_orfaos():
    """RELATIVO com categorias_restritas_ids apontando categoria inexistente -> sanear o JSON."""
    existentes = {r.id for r in db.session.execute(text("SELECT id FROM pessoal_categorias")).fetchall()}
    rows = db.session.execute(text("""
        SELECT id, categorias_restritas_ids FROM pessoal_regras_categorizacao
        WHERE tipo_regra='RELATIVO' AND categorias_restritas_ids IS NOT NULL
    """)).fetchall()
    saneadas = 0
    for r in rows:
        try:
            ids_json = json.loads(r.categorias_restritas_ids)
        except (json.JSONDecodeError, TypeError):
            continue
        limpos = [i for i in ids_json if i in existentes]
        if limpos != ids_json:
            saneadas += 1
            novo = json.dumps(limpos) if limpos else None
            orfaos = [i for i in ids_json if i not in existentes]
            _p(f"[REL] regra id={r.id}: remove orfaos {orfaos} -> {limpos or 'NULL (sem sugestao)'}")
            db.session.execute(
                text("UPDATE pessoal_regras_categorizacao SET categorias_restritas_ids=:v WHERE id=:id"),
                {"v": novo, "id": r.id},
            )
    _p(f"[REL] regras RELATIVO saneadas: {saneadas}")
    return saneadas


def main(apply: bool):
    app = create_app()
    with app.app_context():
        _p("=" * 68)
        _p(f"BACKFILL AUDITORIA PESSOAL — {'APPLY (commit)' if apply else 'DRY-RUN (rollback)'}")
        _p(f"DB: {db.engine.url.host}/{db.engine.url.database}")
        _p("=" * 68)
        n = {
            'A2': passo_a2(),
            'B1': passo_b1(),
            'C1': passo_c1(),
            'TR': passo_transferencia(),
            'R989': passo_regra_degenerada(),
            'REL': passo_relativo_orfaos(),
        }
        _p("-" * 68)
        _p(f"RESUMO: {n}")
        if apply:
            db.session.commit()
            _p("APLICADO (commit).")
        else:
            db.session.rollback()
            _p("DRY-RUN (rollback) — rode com --apply para gravar.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--dry-run', action='store_true', help='Preview sem gravar (default)')
    g.add_argument('--apply', action='store_true', help='Grava as alteracoes')
    args = ap.parse_args()
    main(apply=args.apply)
