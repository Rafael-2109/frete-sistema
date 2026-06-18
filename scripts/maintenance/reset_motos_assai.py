"""Reset transacional SEGURO do modulo Motos Assai (B2B Q.P.A.).

Zera os dados TRANSACIONAIS do modulo (motos, eventos, pedidos, compras,
recibos, separacoes, NFs, CCe, divergencias, devolucoes, pos-venda...)
PRESERVANDO os 4 cadastros (assai_cd, assai_loja, assai_modelo,
assai_modelo_alias). Util para limpar dados de teste/homologacao acumulados
e recomecar a operacao do zero.

CONTEXTO (sugestao IMP-2026-06-17-002 / Agent SDK): hoje o reset e' feito por
SQL manual ad-hoc, sem backup e sem guardas — risco alto (ja houve tentativa de
reset em producao sem backup). Este script substitui o SQL manual por uma
operacao repetivel, auditavel e com salvaguardas.

SALVAGUARDAS (defesa em profundidade):
  1. dry-run e' o DEFAULT — sem `--confirmar` nada e' escrito.
  2. Confirmacao tipada: `--token "RESET-MOTOS-ASSAI-<N>"` onde N e' a contagem
     EXATA de registros transacionais; recalculada e comparada no momento da
     execucao (se o banco mudou entre o dry-run e o confirmar, o token nao bate
     e a operacao aborta).
  3. Backup automatico: dump JSON de TODAS as tabelas afetadas + dos espelhos
     ASSAI-SEP-% na `separacao` Nacom ANTES de qualquer escrita.
  4. Pre-flight de tabela NOVA: se existir uma tabela `assai_%` no banco que
     este script nao classifica (nem cadastro, nem transacional conhecida), a
     operacao ABORTA — evita truncar por engano um cadastro novo.
  5. Pre-flight de vinculo: espelhos ASSAI-SEP-% vinculados a NF ou a
     EmbarqueItem BLOQUEIAM o reset (evita orfanar embarque/frete/faturamento).
  6. Limpeza de espelhos reusa `unmirror_assai_separacao` (guarda de NF nativa).
  7. Tudo numa unica transacao; valida que os 4 cadastros ficaram intactos
     antes do commit (senao faz rollback).

NAO toca no S3 — apenas ALERTA sobre prefixos que ficarao orfaos (recibos,
excel Q.P.A., anexos CCe/devolucao/pos-venda). Limpeza de S3 e' operacao
separada e fora do escopo deste script.

NAO e' uma skill do agente web: o agente web e' read-only por design
(text_to_sql so' aceita SELECT/WITH). Reset transacional e' operacao DEV/admin,
executada via Claude Code (4-maos), nunca pela tela web.

Uso:
    # Dry-run (default): inventario + bloqueios + token esperado (NAO escreve)
    python scripts/maintenance/reset_motos_assai.py

    # Executar de verdade (apos validar o dry-run e copiar o token sugerido)
    python scripts/maintenance/reset_motos_assai.py --confirmar \\
        --token "RESET-MOTOS-ASSAI-8512"

    # Backup em diretorio especifico
    python scripts/maintenance/reset_motos_assai.py --confirmar \\
        --token "RESET-MOTOS-ASSAI-8512" --backup-dir /caminho/backup

Saida JSON com: inventario antes, espelhos, bloqueios, backup path,
resultado por tabela e cadastros preservados.
"""
import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402
from app.motos_assai.services.separacao_mirror_service import (  # noqa: E402
    assai_sep_id_de_lote,
    unmirror_assai_separacao,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
log = logging.getLogger('reset_motos_assai')

# Cadastros — NUNCA truncar (assai_modelo_alias -> assai_modelo; ambos cadastro)
CADASTROS_PRESERVAR = {
    'assai_cd',
    'assai_loja',
    'assai_modelo',
    'assai_modelo_alias',
}

# Transacionais — alvo do TRUNCATE. Lista explicita (auditavel). Se uma tabela
# `assai_%` nova aparecer no banco e nao estiver aqui nem em CADASTROS_PRESERVAR,
# o script ABORTA exigindo classificacao manual (salvaguarda 4).
TRANSACIONAIS = {
    'assai_moto',
    'assai_moto_evento',
    'assai_pedido_venda',
    'assai_pedido_venda_loja',
    'assai_pedido_venda_item',
    'assai_compra_motochefe',
    'assai_compra_motochefe_pedido',
    'assai_recibo_motochefe',
    'assai_recibo_item',
    'assai_separacao',
    'assai_separacao_item',
    'assai_separacao_saldo_modelo',
    'assai_nf_qpa',
    'assai_nf_qpa_item',
    'assai_nf_qpa_item_vinculo_historico',
    'assai_cce',
    'assai_carregamento',
    'assai_carregamento_item',
    'assai_divergencia',
    'assai_pedido_excel',
    'assai_devolucao_nfd',
    'assai_devolucao_item',
    'assai_devolucao_anexo',
    'assai_pos_venda_ocorrencia',
    'assai_pos_venda_ocorrencia_anexo',
}

# Prefixos S3 que ficam orfaos apos o reset (apenas ALERTA — nao deletado aqui)
S3_PREFIXOS_ORFAOS = [
    'motos_assai/recebimento/',
    'motos_assai/solicitacoes/',   # excel Q.P.A.
    'motos_assai/cce/',
    'motos_assai/devolucao/',
    'motos_assai/pos_venda/',
]

TOKEN_PREFIX = 'RESET-MOTOS-ASSAI-'


def _tabelas_assai_reais():
    """Tabelas existentes no banco com prefixo assai_."""
    rows = db.session.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name LIKE 'assai\\_%'"
    )).scalars().all()
    return set(rows)


def _count(tabela):
    return db.session.execute(text(f'SELECT COUNT(*) FROM {tabela}')).scalar() or 0


def _inventario(tabelas):
    return {t: _count(t) for t in sorted(tabelas)}


def _espelhos_assai():
    """(total, com_nf, com_embarque, sep_ids) dos espelhos ASSAI-SEP-% na separacao Nacom."""
    total = db.session.execute(text(
        "SELECT COUNT(*) FROM separacao WHERE separacao_lote_id LIKE 'ASSAI-SEP-%'"
    )).scalar() or 0
    com_nf = db.session.execute(text(
        "SELECT COUNT(*) FROM separacao "
        "WHERE separacao_lote_id LIKE 'ASSAI-SEP-%' "
        "AND (numero_nf IS NOT NULL OR sincronizado_nf = TRUE)"
    )).scalar() or 0
    com_embarque = db.session.execute(text(
        "SELECT COUNT(*) FROM embarque_itens WHERE separacao_lote_id LIKE 'ASSAI-SEP-%'"
    )).scalar() or 0
    lotes = db.session.execute(text(
        "SELECT DISTINCT separacao_lote_id FROM separacao "
        "WHERE separacao_lote_id LIKE 'ASSAI-SEP-%'"
    )).scalars().all()
    return total, com_nf, com_embarque, lotes


def _dump_backup(backup_dir, tabelas):
    """Serializa cada tabela + espelhos para JSON. Retorna dict {tabela: n_linhas}."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    contagens = {}
    alvos = sorted(tabelas) + ['__espelhos_separacao_assai']
    for t in alvos:
        if t == '__espelhos_separacao_assai':
            rows = db.session.execute(text(
                "SELECT * FROM separacao WHERE separacao_lote_id LIKE 'ASSAI-SEP-%'"
            )).mappings().all()
        else:
            rows = db.session.execute(text(f'SELECT * FROM {t}')).mappings().all()
        data = [dict(r) for r in rows]
        (backup_dir / f'{t}.json').write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding='utf-8',
        )
        contagens[t] = len(data)
    return contagens


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--confirmar', action='store_true',
                        help='EFETIVA o reset. Sem isso = dry-run (nao escreve).')
    parser.add_argument('--token', type=str, default='',
                        help='Confirmacao tipada "RESET-MOTOS-ASSAI-<N>" (N = total transacional exato).')
    parser.add_argument('--backup-dir', type=str, default='',
                        help='Diretorio do dump JSON. Default: scripts/dumps/motos_assai_reset_<timestamp>.')
    parser.add_argument('--quiet', action='store_true', help='Suprime stdout do boot Flask.')
    args = parser.parse_args()

    if args.quiet:
        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            app = create_app()
    else:
        app = create_app()

    with app.app_context():
        # 1) Descobrir tabelas reais e validar classificacao (salvaguarda 4)
        reais = _tabelas_assai_reais()
        nao_classificadas = reais - CADASTROS_PRESERVAR - TRANSACIONAIS
        if nao_classificadas:
            print(json.dumps({
                'status': 'ABORTADO',
                'motivo': 'tabela(s) assai_ NOVA(s) nao classificada(s) — '
                          'adicione a CADASTROS_PRESERVAR ou TRANSACIONAIS no script antes de rodar',
                'nao_classificadas': sorted(nao_classificadas),
            }, indent=2, ensure_ascii=False))
            sys.exit(2)

        transacionais_exist = sorted(TRANSACIONAIS & reais)
        cadastros_exist = sorted(CADASTROS_PRESERVAR & reais)

        # 2) Inventario + token esperado
        inv_transacional = _inventario(transacionais_exist)
        inv_cadastros = _inventario(cadastros_exist)
        total_transacional = sum(inv_transacional.values())
        token_esperado = f'{TOKEN_PREFIX}{total_transacional}'

        # 3) Espelhos e bloqueios
        esp_total, esp_com_nf, esp_com_embarque, esp_lotes = _espelhos_assai()
        bloqueios = []
        if esp_com_nf > 0:
            bloqueios.append(f'{esp_com_nf} espelho(s) ASSAI-SEP-% com NF preenchida na separacao Nacom')
        if esp_com_embarque > 0:
            bloqueios.append(f'{esp_com_embarque} EmbarqueItem(s) apontando para lote ASSAI-SEP-% (orfanaria embarque/frete)')

        base_output = {
            'modo': 'confirmado' if args.confirmar else 'dry-run',
            'timestamp': datetime.now().isoformat(),
            'token_esperado': token_esperado,
            'inventario_transacional': inv_transacional,
            'total_transacional': total_transacional,
            'cadastros_preservar': inv_cadastros,
            'espelhos_assai_separacao': {
                'total': esp_total,
                'com_nf': esp_com_nf,
                'com_embarque': esp_com_embarque,
                'lotes_distintos': len(esp_lotes),
            },
            'bloqueios': bloqueios,
            's3_prefixos_orfaos_alerta': S3_PREFIXOS_ORFAOS,
        }

        # 4) DRY-RUN: so' reporta
        if not args.confirmar:
            base_output['status'] = 'DRY_RUN'
            base_output['proximo_passo'] = (
                f'Revise. Se OK e sem bloqueios, rode: --confirmar --token "{token_esperado}"'
                if not bloqueios else
                'RESOLVA os bloqueios (cancele NF / desvincule embarque) antes de confirmar.'
            )
            print(json.dumps(base_output, indent=2, ensure_ascii=False))
            return

        # 5) CONFIRMAR — validacoes duras
        if args.token != token_esperado:
            base_output['status'] = 'ABORTADO'
            base_output['motivo'] = (
                f'token invalido. Recebido "{args.token}", esperado "{token_esperado}". '
                'A contagem transacional mudou desde o dry-run, ou o token esta errado.'
            )
            print(json.dumps(base_output, indent=2, ensure_ascii=False))
            sys.exit(3)

        if bloqueios:
            base_output['status'] = 'ABORTADO'
            base_output['motivo'] = 'bloqueios de vinculo presentes — reset cancelado'
            print(json.dumps(base_output, indent=2, ensure_ascii=False))
            sys.exit(4)

        # 6) Backup ANTES de qualquer escrita
        if args.backup_dir:
            backup_dir = Path(args.backup_dir)
        else:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = _THIS.parents[2] / 'scripts' / 'dumps' / f'motos_assai_reset_{ts}'
        log.info('Backup em %s', backup_dir)
        backup_contagens = _dump_backup(backup_dir, transacionais_exist)

        # 7) Reset transacional (uma transacao)
        try:
            # 7a) Limpar espelhos na separacao Nacom (reusa guarda de NF)
            espelhos_removidos = 0
            for lote in esp_lotes:
                sep_id = assai_sep_id_de_lote(lote)
                if sep_id is not None:
                    espelhos_removidos += unmirror_assai_separacao(sep_id)
                else:
                    espelhos_removidos += db.session.execute(text(
                        "DELETE FROM separacao WHERE separacao_lote_id = :lote"
                    ), {'lote': lote}).rowcount
            db.session.flush()

            # 7b) TRUNCATE transacionais (RESTART IDENTITY, SEM CASCADE).
            # Todas as transacionais vao no MESMO comando, entao as FKs internas
            # sao satisfeitas. Omitir CASCADE e' proposital: se uma tabela EXTERNA
            # (fora do conjunto) referenciar uma transacional, o TRUNCATE FALHA em
            # vez de truncar silenciosamente algo inesperado.
            lista = ', '.join(transacionais_exist)
            db.session.execute(text(f'TRUNCATE TABLE {lista} RESTART IDENTITY'))

            # 7c) Validar que cadastros ficaram intactos ANTES do commit
            inv_cadastros_pos = _inventario(cadastros_exist)
            if inv_cadastros_pos != inv_cadastros:
                db.session.rollback()
                base_output['status'] = 'ROLLBACK'
                base_output['motivo'] = 'contagem de cadastros mudou — TRUNCATE afetou cadastro (abortado)'
                base_output['cadastros_antes'] = inv_cadastros
                base_output['cadastros_depois'] = inv_cadastros_pos
                print(json.dumps(base_output, indent=2, ensure_ascii=False))
                sys.exit(5)

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            base_output['status'] = 'ERRO'
            base_output['erro'] = str(e)[:500]
            print(json.dumps(base_output, indent=2, ensure_ascii=False))
            log.exception('Falha no reset — rollback aplicado')
            sys.exit(6)

        # 8) Relatorio pos
        base_output['status'] = 'OK'
        base_output['backup_dir'] = str(backup_dir)
        base_output['backup_contagens'] = backup_contagens
        base_output['espelhos_removidos'] = espelhos_removidos
        base_output['inventario_transacional_pos'] = _inventario(transacionais_exist)
        base_output['cadastros_preservados_pos'] = _inventario(cadastros_exist)
        print(json.dumps(base_output, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
