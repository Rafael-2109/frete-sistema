"""Backfill do PASSIVO HISTORICO de correcoes do Marcus (user 18) — loop corretivo (Tarefa 1).

CONTEXTO: o sistema antigo nunca incrementava correction_count -> as ~36 correcoes do Marcus
estao com cc=0 e NUNCA serao promovidas pelo batch (0 < threshold 2). Este script e o
backfill one-shot do passivo: funde cada grupo redundante em 1 canonica 'mandatory' (com
frame imperativo + error_signature) e ARQUIVA as copias (is_cold=True), preservando a prescricao.
Daqui pra frente e automatico (batch diario modulo 32 + write-path reincidencia).

SEGURANCA:
- `--dry-run` e o DEFAULT: apenas LISTA o que seria feito (nada e escrito).
- `--confirmar` efetiva (write). IDEMPOTENTE: re-rodar nao duplica (detecta canonica ja
  'mandatory' + copias ja cold -> no-op).
- error_signature so e setado se a coluna existir (hasattr guard — seguro pre-migration 3.1).
- Roda no banco apontado por DATABASE_URL. PROD = rodar no Render Shell (ou com env PROD)
  APOS o GO do Rafael. NUNCA rodar contra dados de teste esperando efeito real.

Uso:
    python scripts/backfill_loop_corretivo_marcus.py                  # DRY-RUN (default)
    python scripts/backfill_loop_corretivo_marcus.py --incluir-baseline   # + cluster F (opcional)
    python scripts/backfill_loop_corretivo_marcus.py --confirmar      # EFETIVA (write)
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db  # noqa: E402
from app.agente.models import AgentMemory  # noqa: E402

USER_ID = 18  # Marcus (web). Ver memoria avaliacao_memoria_agente_2026_06.

# Cada cluster: canonica (id existente a promover) + content imperativo (SEMPRE/NUNCA+WHEN/DO) +
# error_signature + copias (ids a arquivar via is_cold). A canonica herda cc = nº de ocorrencias.
CLUSTERS_CORE = [
    {
        'nome': 'A — escopo/cluster errado (responder sobre outro contexto)',
        'canonica_id': 486,
        'error_signature': 'responder_cluster_ou_escopo_errado',
        'content': (
            "SEMPRE: ao receber um pedido sobre um item/cluster/tarefa especifico, confirmar QUAL "
            "item e responder ESTRITAMENTE sobre ele.\n"
            "NUNCA: reutilizar dados de outro cluster/contexto anterior, nem expandir o escopo "
            "(analises adjacentes) sem o usuario pedir explicitamente.\n"
            "WHEN: usuario pergunta detalhes de um cluster/tarefa especifico (ex: 'tarifas "
            "pendentes', 'TEDs SICOOB tarefa 4', 'apenas ADIANT.DEPOSITANTE').\n"
            "DO: confirmar o escopo exato e buscar SO aquelas linhas; ao desviar, reconhecer "
            "brevemente e voltar ao escopo."
        ),
        'copias_ids': [431, 469, 482, 483, 492, 493, 503],
    },
    {
        'nome': 'B — veto de execucao ("nao fazer X")',
        'canonica_id': 476,
        'error_signature': 'executou_item_vetado',
        'content': (
            "NUNCA: executar ou incluir um padrao/item que o usuario VETOU explicitamente "
            "('nao fazer X', 'nao executar Y'), mesmo que ele diga 'proximo'/'seguir' ou o item "
            "apareca em sequencia natural na lista.\n"
            "SEMPRE: registrar a exclusao e preserva-la atraves de compactacoes de contexto; ao "
            "retomar uma execucao, checar a lista de vetos antes.\n"
            "WHEN: o usuario proibe um padrao/acao durante a sessao (ex: 'nao fazer JUROS (outros)', "
            "'nao executar os 3 debitos cadeia').\n"
            "DO: nunca reintroduzir o item vetado em lotes subsequentes sem nova autorizacao."
        ),
        'copias_ids': [438, 403, 432],
    },
    {
        'nome': 'E — Tenda recebe pelo Bradesco (regra factual)',
        'canonica_id': 809,
        'error_signature': 'tenda_recebe_bradesco_nao_sicoob',
        'content': (
            "SEMPRE: tratar recebimentos da Rede Tenda como entrando pelo BRADESCO.\n"
            "NUNCA: aceitar conciliacao Tenda<->Sicoob — recebimentos da Tenda nunca vem pelo Sicoob.\n"
            "WHEN: aparecer um credito Sicoob vinculado a cliente Tenda.\n"
            "DO: sinalizar como mis-reconciliacao antes de prosseguir."
        ),
        'copias_ids': [],  # 808 e procedural (parceiro ao recriar conciliacao), NAO e a mesma regra
        'cc_min': 2,       # fato corrigido/reforcado -> entra no canal duro
    },
]

# OPCIONAL (--incluir-baseline): consolida o formato do relatorio baseline (heterogeneo).
CLUSTER_BASELINE = {
    'nome': 'F — formato do relatorio baseline (OPCIONAL)',
    'canonica_id': 439,
    'error_signature': 'formato_baseline_errado',
    'content': (
        "SEMPRE: ao gerar/atualizar o baseline de conciliacao, aplicar o formato ACORDADO sem "
        "aguardar correcao: planilha PLANA (sem pivots/abas extras nao solicitadas); coluna de "
        "data COMPLETA dia/mes/ano (nunca so ano-mes); meses em ordem CRONOLOGICA (nao alfabetica) "
        "na aba Resumo; conciliacoes D-1 com TODAS as fontes (extrato_item, lancamento_comprovante, "
        "carvia_conciliacoes) e nomes REAIS do Odoo (write_uid, nunca labels de sync).\n"
        "WHEN: o usuario pedir 'atualizar baseline' / 'relatorio de extratos pendentes'.\n"
        "DO: gerar direto no formato acordado."
    ),
    'copias_ids': [524, 586, 587, 528, 530],
}

# Memorias a NAO promover, com alerta (revisao humana):
ALERTAS = {
    537: "IDENTIDADE FACTUALMENTE ERRADA ('Marcus = UID 42 Rafael de Carvalho Nascimento'). "
         "P5 do diagnostico. NAO promover; recomenda-se ARQUIVAR/CORRIGIR (envenena identidade). "
         "Problema P1 (identidade) e separado do loop.",
    470: "Identidade ('Marcus sou eu') — P1, separado do loop. Nao promover.",
}


def _processar_cluster(c, dry_run):
    canonica = AgentMemory.query.get(c['canonica_id'])
    if canonica is None:
        print(f"  [SKIP] canonica id={c['canonica_id']} nao encontrada — cluster '{c['nome']}' ignorado")
        return
    copias = [AgentMemory.query.get(i) for i in c['copias_ids']]
    copias = [m for m in copias if m is not None]
    cc_alvo = max(len(copias) + 1, c.get('cc_min', 0))

    ja_ok = (canonica.priority == 'mandatory'
             and (canonica.correction_count or 0) >= cc_alvo
             and all((m.is_cold for m in copias)))

    print(f"\n■ Cluster: {c['nome']}")
    print(f"  canonica id={canonica.id} path={canonica.path}")
    print(f"    priority: {canonica.priority} -> mandatory")
    print(f"    correction_count: {canonica.correction_count} -> {cc_alvo}")
    print(f"    error_signature -> '{c['error_signature']}'"
          + ("" if hasattr(canonica, 'error_signature') else " (coluna ausente — sera ignorado)"))
    print(f"    content -> frame imperativo ({len(c['content'])} chars)")
    print(f"  arquivar (is_cold=True): {[m.id for m in copias]}")
    if ja_ok:
        print("  [IDEMPOTENTE] ja aplicado anteriormente — no-op")
        return

    if dry_run:
        print("  [DRY-RUN] nada escrito")
        return

    canonica.priority = 'mandatory'
    canonica.correction_count = cc_alvo
    canonica.content = c['content']
    canonica.importance_score = 0.9
    canonica.is_cold = False
    if hasattr(canonica, 'error_signature'):
        canonica.error_signature = c['error_signature'][:64]
    for m in copias:
        m.is_cold = True
        m.category = 'cold'
        if hasattr(m, 'error_signature') and not m.error_signature:
            m.error_signature = c['error_signature'][:64]
    db.session.commit()
    print("  [OK] aplicado (canonica promovida + copias arquivadas)")


def main():
    ap = argparse.ArgumentParser(description="Backfill do passivo de correcoes do Marcus (loop corretivo)")
    ap.add_argument('--confirmar', action='store_true', help="EFETIVA (write). Default = dry-run.")
    ap.add_argument('--incluir-baseline', action='store_true', help="inclui o cluster F (formato baseline)")
    ap.add_argument('--user-id', type=int, default=USER_ID)
    args = ap.parse_args()
    dry_run = not args.confirmar

    app = create_app()
    with app.app_context():
        modo = "DRY-RUN (nada sera escrito)" if dry_run else "CONFIRMAR (WRITE)"
        print(f"=== BACKFILL LOOP CORRETIVO — user {args.user_id} — MODO: {modo} ===")

        # PRE-FLIGHT: o model AgentMemory ja tem as colunas da Fase 3.1; se o BANCO ainda nao,
        # o commit falharia ("column does not exist"). Exigir a migration 3.1 ANTES (no PROD).
        from sqlalchemy import inspect as _sa_inspect
        cols = {c['name'] for c in _sa_inspect(db.engine).get_columns('agent_memories')}
        faltando = {'error_signature', 'harmful_count', 'helpful_count'} - cols
        if faltando:
            print(f"\n[ABORTADO] colunas da Fase 3.1 ausentes no banco: {sorted(faltando)}.")
            print("  Rode a migration ANTES: "
                  "python scripts/migrations/2026_06_02_agent_memories_error_signature.py")
            sys.exit(2)
        clusters = list(CLUSTERS_CORE)
        if args.incluir_baseline:
            clusters.append(CLUSTER_BASELINE)
        for c in clusters:
            _processar_cluster(c, dry_run)

        print("\n--- ALERTAS (revisao humana, NAO promovidos pelo backfill) ---")
        for mid, msg in ALERTAS.items():
            m = AgentMemory.query.get(mid)
            existe = "existe" if m else "NAO existe"
            print(f"  id={mid} ({existe}): {msg}")

        print("\n=== FIM ===" + ("" if not dry_run else " (rode com --confirmar para efetivar)"))


if __name__ == '__main__':
    main()
