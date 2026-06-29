"""Amplia o menu (categorias_restritas) da regra RELATIVO de La Famiglia — modulo Pessoal.

Contexto (item 1a da revisao de 29/06/2026):
    A regra "LA FAMIGLIA" e RELATIVO (nao auto-categoriza, so sugere) mas oferecia
    APENAS [Empresa - Entrada] no menu de sugestao. Como uma entrada La Famiglia pode
    ser receita pura, hibrida (parte entra-e-sai, parte fica) ou so-empresa — decisao
    do usuario POR TRANSACAO — o menu precisa oferecer tambem as categorias de Receita.

    Este script AMPLIA categorias_restritas (uniao, nao-destrutivo) para incluir:
      - Movimentacoes Empresa / Empresa - Entrada   (so-empresa e hibrido; compensa depois)
      - Receitas / Outras Entradas, Pro-labore, Rendimentos   (receita pura)

    NAO converte a regra para PADRAO (forcaria tudo como empresa) e NAO reclassifica
    nenhuma transacao. Idempotente. Resolve categorias por (grupo, nome) — robusto
    entre ambientes (local vs producao, onde os IDs podem diferir).

Uso:
    python scripts/pessoal/ampliar_menu_regra_la_famiglia.py                 # dry-run (local)
    python scripts/pessoal/ampliar_menu_regra_la_famiglia.py --confirmar     # grava (local)
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/pessoal/ampliar_menu_regra_la_famiglia.py
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/pessoal/ampliar_menu_regra_la_famiglia.py --confirmar
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402
from app.pessoal.models import (  # noqa: E402
    PessoalCategoria, PessoalRegraCategorizacao,
)

logger = logging.getLogger(__name__)

# Substring (case-insensitive) no padrao_historico da regra RELATIVO alvo
PADRAO_REGRA = 'LA FAMIGLIA'

# Categorias que devem compor o menu de sugestao (grupo, nome)
MENU_DESEJADO = [
    ('Movimentacoes Empresa', 'Empresa - Entrada'),  # so-empresa e hibrido
    ('Receitas', 'Outras Entradas'),                 # receita pura
    ('Receitas', 'Pro-labore'),
    ('Receitas', 'Rendimentos'),
]


def _resolver_ids() -> tuple[list[int], list[str]]:
    """Resolve (grupo, nome) -> id; retorna (ids_encontrados, faltando)."""
    ids, faltando = [], []
    for grupo, nome in MENU_DESEJADO:
        cat = PessoalCategoria.query.filter_by(grupo=grupo, nome=nome).first()
        if cat:
            ids.append(cat.id)
        else:
            faltando.append(f'{grupo}/{nome}')
    return ids, faltando


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true', help='grava (sem isto, dry-run)')
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        ids_desejados, faltando = _resolver_ids()
        if faltando:
            print(f'AVISO: categorias nao encontradas (serao ignoradas): {faltando}')
        if not ids_desejados:
            print('ERRO: nenhuma categoria do menu desejado foi encontrada. Abortando.')
            sys.exit(1)

        regras = PessoalRegraCategorizacao.query.filter(
            PessoalRegraCategorizacao.padrao_historico.ilike(f'%{PADRAO_REGRA}%'),
            PessoalRegraCategorizacao.tipo_regra == 'RELATIVO',
        ).all()

        print('--- Ampliar menu da regra La Famiglia ---')
        print(f"Modo: {'GRAVADO' if args.confirmar else 'DRY-RUN (use --confirmar para gravar)'}")
        print(f"IDs desejados no menu: {sorted(ids_desejados)}")

        if not regras:
            print(f'Nenhuma regra RELATIVO com padrao contendo "{PADRAO_REGRA}".')
            return

        mudou = 0
        for r in regras:
            atual = set(r.get_categorias_restritas())
            novo = sorted(atual | set(ids_desejados))  # uniao: nunca remove existentes
            marcador = '' if set(novo) == atual else '  <-- ALTERA'
            print(f"Regra id={r.id} '{r.padrao_historico}': {sorted(atual)} -> {novo}{marcador}")
            if set(novo) != atual:
                if args.confirmar:
                    r.set_categorias_restritas(novo)
                mudou += 1

        if args.confirmar and mudou:
            db.session.commit()

        print(f"{'Regras alteradas' if args.confirmar else 'Regras a alterar'}: {mudou}")


if __name__ == '__main__':
    main()
