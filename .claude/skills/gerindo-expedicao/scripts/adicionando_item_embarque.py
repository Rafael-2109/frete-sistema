#!/usr/bin/env python3
"""
Adiciona UM lote Nacom a um Embarque JA EXISTENTE — WRITE
=========================================================

Origem: D8 IMP-2026-06-23-007 (Rafael). `gerar_embarque.py` so cria embarques
NOVOS; nao havia caminho para anexar um EmbarqueItem a um embarque ja existente
— a sessao resolveu via Bash+ORM e o total do embarque INFLOU (1089,35 vs
863,35 kg) porque o incremento aritmetico leu um valor ja atualizado por
`sync_totais_service` concorrente.

CORRECAO ESTRUTURAL: este script NUNCA incrementa total aritmeticamente. Apos
adicionar o item ele chama `sincronizar_totais_embarque(embarque_id)`, que
recalcula peso/valor/pallets por SOMA dos itens ativos (fonte unica) — o mesmo
service que a UI usa. Adicionar 2x o mesmo lote e bloqueado (idempotencia).

ESCOPO = ramo Nacom (lotes `LOTE_*`). Reusa os helpers ja testados de
`gerar_embarque.py` (carregar_pedidos, validar_lotes_nacom, idempotencia,
snapshot de tabela). Itens **CarVia** (`CARVIA-*`) e **Assai** (`ASSAI-*`) sao
RECUSADOS: o CarVia tem maquina de consistencia propria — o ponto canonico e
`app/carvia/services/documentos/embarque_carvia_service.py:reconciliar_embarque_carvia`
(local_cd -> totais -> frete -> entregas), que nao pertence a esta skill Nacom
(CarVia R1 = modulo isolado).

SEGURANCA:
  - dry-run e o DEFAULT. Sem --confirmar mostra item previsto + totais
    (antes/depois por SOMA) e faz rollback.
  - So efetiva com --confirmar.

Uso:
  --embarque-id N     (obrigatorio) id do Embarque ATIVO destino
  --lote LOTE_...     (obrigatorio) separacao_lote_id Nacom a anexar
  --user-id N         (obrigatorio) usuario solicitante (valida em usuarios)
  --confirmar         executa de verdade (sem isto = dry-run)

Exemplo:
  # preview
  python adicionando_item_embarque.py --embarque-id 6026 --lote LOTE_20260623_... --user-id 1
  # efetiva
  python adicionando_item_embarque.py --embarque-id 6026 --lote LOTE_20260623_... --user-id 1 --confirmar
"""

import argparse
import json
import os
import sys

# raiz do projeto (4 niveis acima) + diretorio scripts (p/ reusar gerar_embarque)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gerar_embarque as ge  # noqa: E402 — helpers Nacom ja testados

EXIT_OK = 0
EXIT_FALHA = 1
EXIT_USO = 2
EXIT_DRYRUN = 4


def _totais_itens_ativos(embarque):
    """Soma peso/valor/pallets dos itens ATIVOS (fonte unica — nunca incremento)."""
    peso = valor = pallets = 0.0
    for it in embarque.itens:
        if it.status != 'ativo':
            continue
        peso += it.peso or 0
        valor += it.valor or 0
        pallets += it.pallets or 0
    return round(peso, 2), round(valor, 2), round(pallets, 2)


def _nota_fiscal_do_lote(lote, num_pedido):
    """NF do lote via Separacao (mesma logica de gerar_embarque.executar)."""
    from app.separacao.models import Separacao
    if not (lote and num_pedido):
        return None
    sep = (
        Separacao.query
        .filter_by(separacao_lote_id=lote, num_pedido=num_pedido)
        .filter(Separacao.numero_nf.isnot(None))
        .first()
    )
    return sep.numero_nf if sep else None


def adicionar_item(embarque_id, lote, user_id, confirmar=False):
    """Anexa UM lote Nacom ao embarque. dry-run por padrao."""
    from app.embarques.models import Embarque, EmbarqueItem
    from app.embarques.services.sync_totais_service import sincronizar_totais_embarque
    from app.utils.localizacao import LocalizacaoService
    from app.utils.tabela_frete_manager import TabelaFreteManager
    db = ge._get_db()

    # ---- Guard-rail: so ramo Nacom ----
    ok_nacom, recusados = ge.validar_lotes_nacom([lote])
    if not ok_nacom:
        return EXIT_FALHA, {
            'sucesso': False,
            'erro': f'Lote {lote} e CarVia/Assai — fora do escopo Nacom. '
                    'Itens CARVIA-* usam reconciliar_embarque_carvia '
                    '(embarque_carvia_service); ASSAI-* usam o modulo Motos Assai.',
        }

    # ---- Usuario ----
    usuario = ge.resolver_usuario(user_id)
    if not usuario:
        return EXIT_FALHA, {
            'sucesso': False, 'erro': f'Usuario {user_id} nao encontrado em usuarios',
        }

    # ---- Embarque ----
    embarque = db.session.get(Embarque, embarque_id)
    if not embarque:
        return EXIT_FALHA, {
            'sucesso': False, 'erro': f'Embarque {embarque_id} nao encontrado',
        }
    if embarque.status != 'ativo':
        return EXIT_FALHA, {
            'sucesso': False,
            'erro': f'Embarque {embarque_id} esta {embarque.status} — '
                    'so e possivel anexar item a embarque ATIVO',
        }

    # ---- Idempotencia ----
    ja = ge.lotes_ja_em_embarque_ativo([lote])
    if lote in ja:
        if ja[lote] == embarque.numero:
            return EXIT_OK, {
                'sucesso': True, 'ja_presente': True,
                'mensagem': f'Lote {lote} JA esta no embarque {embarque.numero} — nada a fazer',
            }
        return EXIT_FALHA, {
            'sucesso': False,
            'erro': f'Lote {lote} ja esta alocado no embarque ativo {ja[lote]}. '
                    'Remova de la antes de mover, ou anexe outro lote.',
        }

    # ---- Pedido (VIEW) ----
    pedidos = ge.carregar_pedidos([lote])
    if not pedidos:
        return EXIT_FALHA, {
            'sucesso': False, 'erro': f'Nenhum Pedido encontrado para o lote {lote}',
        }
    pedido = pedidos[0]

    # ---- Tabela conforme tipo do embarque ----
    avisos = []
    tipo = (embarque.tipo_carga or 'FRACIONADA').upper()
    dados_tabela = None
    if tipo == 'FRACIONADA':
        item_ref = ge._item_ref_espelho(embarque_id)
        if item_ref is None:
            return EXIT_FALHA, {
                'sucesso': False,
                'erro': f'Embarque {embarque_id} FRACIONADA sem EmbarqueItem Nacom '
                        'para espelhar a tabela de frete. Frete jamais com tabela '
                        'zerada — use gerar_embarque.py para criar embarque novo.',
            }
        dados_tabela = ge.dados_tabela_de_espelho_item(item_ref)
        avisos.append(
            f'Tabela de frete ESPELHADA do item {item_ref.id} '
            f"(tabela='{dados_tabela.get('nome_tabela') or dados_tabela.get('tabela_nome_tabela')}'). "
            'Confirme que o destino do novo lote usa a MESMA tabela.'
        )
    # DIRETA: tabela ja congelada no header do embarque (item nao grava tabela_*).

    # ---- Dados do item ----
    cidade_fmt, uf_correto = LocalizacaoService.obter_cidade_destino_embarque(pedido)
    nota_fiscal = _nota_fiscal_do_lote(lote, getattr(pedido, 'num_pedido', None))

    item_preview = {
        'separacao_lote_id': lote,
        'cnpj_cliente': getattr(pedido, 'cnpj_cpf', None),
        'cliente': getattr(pedido, 'raz_social_red', None),
        'pedido': getattr(pedido, 'num_pedido', None),
        'nota_fiscal': nota_fiscal,
        'peso': float(pedido.peso_total or 0),
        'valor': float(pedido.valor_saldo_total or 0),
        'pallets': float(pedido.pallet_total or 0),
        'uf_destino': uf_correto,
        'cidade_destino': cidade_fmt,
        'tipo_carga': tipo,
    }

    # ---- Totais por SOMA (nunca incremento) ----
    peso_antes, valor_antes, pallets_antes = _totais_itens_ativos(embarque)
    totais_antes = {'peso': peso_antes, 'valor': valor_antes, 'pallets': pallets_antes}
    totais_previstos = {
        'peso': round(peso_antes + item_preview['peso'], 2),
        'valor': round(valor_antes + item_preview['valor'], 2),
        'pallets': round(pallets_antes + item_preview['pallets'], 2),
    }

    if not confirmar:
        db.session.rollback()
        return EXIT_DRYRUN, {
            'sucesso': True, 'dry_run': True, 'gravado': False,
            'embarque_id': embarque_id, 'embarque_numero': embarque.numero,
            'tipo_carga': tipo,
            'item_previsto': item_preview,
            'totais_antes': totais_antes,
            'totais_previstos_por_soma': totais_previstos,
            'avisos': avisos,
            'mensagem': 'DRY-RUN: nada gravado. Os totais finais serao recalculados '
                        'por sincronizar_totais_embarque (soma dos itens ativos). '
                        'Rode com --confirmar para efetivar.',
        }

    # ---- EXECUTAR ----
    try:
        item = EmbarqueItem(
            embarque_id=embarque.id,
            separacao_lote_id=lote,
            cnpj_cliente=getattr(pedido, 'cnpj_cpf', None),
            cliente=getattr(pedido, 'raz_social_red', None),
            pedido=getattr(pedido, 'num_pedido', None),
            nota_fiscal=nota_fiscal,
            peso=pedido.peso_total or 0,
            valor=pedido.valor_saldo_total or 0,
            pallets=pedido.pallet_total or 0,
            uf_destino=uf_correto,
            cidade_destino=cidade_fmt,
            volumes=None,
        )
        if tipo == 'FRACIONADA' and dados_tabela:
            TabelaFreteManager.atribuir_campos_objeto(item, dados_tabela)
            item.icms_destino = dados_tabela.get('icms_destino', 0)
        db.session.add(item)
        db.session.flush()
        item_id = item.id

        # Vincular o lote a cotacao do embarque (paridade gerar_embarque.executar)
        if embarque.cotacao_id:
            from app.separacao.models import Separacao
            Separacao.atualizar_cotacao(
                separacao_lote_id=lote, cotacao_id=embarque.cotacao_id, nf_cd=False,
            )

        db.session.commit()

        # Recalcular totais por SOMA (fonte unica) — corrige a inflacao do incremento.
        embarque.invalidar_cache_itens()
        sync = sincronizar_totais_embarque(embarque_id)

    except Exception as e:
        db.session.rollback()
        return EXIT_FALHA, {
            'sucesso': False, 'erro': f'{type(e).__name__}: {e}',
        }

    totais_finais = sync.get('totais') if isinstance(sync, dict) else None
    return EXIT_OK, {
        'sucesso': True, 'dry_run': False, 'gravado': True,
        'embarque_id': embarque_id, 'embarque_numero': embarque.numero,
        'item_id': item_id,
        'item': item_preview,
        'totais_antes': totais_antes,
        'totais_finais': totais_finais,
        'sync_totais': {
            'success': sync.get('success') if isinstance(sync, dict) else None,
            'itens_atualizados': sync.get('itens_atualizados') if isinstance(sync, dict) else None,
        },
        'avisos': avisos,
    }


def main():
    parser = argparse.ArgumentParser(
        description='Anexa UM lote Nacom a um Embarque existente (WRITE, dry-run default)',
    )
    parser.add_argument('--embarque-id', type=int, required=True, help='id do Embarque ATIVO')
    parser.add_argument('--lote', type=str, required=True, help='separacao_lote_id Nacom (LOTE_*)')
    parser.add_argument('--user-id', type=int, required=True, help='usuario solicitante (usuarios)')
    parser.add_argument('--confirmar', action='store_true',
                        help='executa de verdade (sem isto = dry-run)')
    args = parser.parse_args()

    with ge.criar_app_context():
        try:
            exit_code, resultado = adicionar_item(
                args.embarque_id, args.lote, args.user_id, confirmar=args.confirmar,
            )
        except Exception as e:
            db = ge._get_db()
            db.session.rollback()
            print(json.dumps({
                'sucesso': False, 'erro': f'{type(e).__name__}: {e}',
            }, ensure_ascii=False, indent=2))
            sys.exit(EXIT_FALHA)

        print(json.dumps(resultado, ensure_ascii=False, indent=2, default=ge.decimal_default))
        sys.exit(exit_code)


if __name__ == '__main__':
    main()
