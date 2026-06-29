"""Descoberta reversa de pedidos TagPlus -> HORA (Fase 3, numero-walk +3).

Objetivo (rede de convergencia, NAO incentivo a criar no TagPlus): puxar para o
HORA os pedidos que nasceram direto no TagPlus, para que o usuario continue
operando so' no HORA. Ver spec `2026-06-29-hora-tagplus-sync-bidirecional-design.md`
secao 5.

Algoritmo (numero-walk +3, decisao do dono):
    base = max(maior tagplus_pedido_numero conhecido, ultimo_pedido_numero_reconciliado)
    a partir de base+1, varre incrementando; reseta ausencias ao achar; para
    apos 3 ausencias SEGUIDAS. Anti-loop: pedido cujo codigo_externo resolve uma
    HoraVenda (nosso push) — ou ja replicado — e' ignorado.

Limitacao conhecida (documentada na spec): gaps reais > 3 fazem a varredura
parar antes (mitigacao futura: varredura por data). Cursor persistido em
hora_tagplus_conta.ultimo_pedido_numero_reconciliado (migration hora_63).

ESTE MODULO cobre a DESCOBERTA. A replicacao (criar HoraVenda INCOMPLETO a
partir do pedido descoberto), a UI de vinculo de chassi e o cron sao a etapa
seguinte (handoff).
"""
from __future__ import annotations

import logging

from app import db
from app.hora.models.venda import HoraVenda
from app.hora.services.tagplus.pedido_service import busca_pedido_por_numero

logger = logging.getLogger(__name__)

LIMITE_AUSENCIAS = 3       # para apos N ausencias seguidas (numero-walk +3)
LIMITE_VARREDURA = 300     # guard anti-loop infinito (max numeros por execucao)


def _maior_numero_conhecido() -> int:
    """Maior tagplus_pedido_numero ja conhecido em hora_venda (0 se nenhum)."""
    maior = db.session.query(db.func.max(HoraVenda.tagplus_pedido_numero)).scalar()
    return int(maior or 0)


def pedido_e_nosso(pedido: dict) -> bool:
    """True se o pedido e' "nosso" (push HORA) OU ja foi replicado (idempotencia).

    Anti-loop: um pedido criado pelo nosso push tem codigo_externo = HoraVenda.id.
    Tambem trata como "nosso" (ignora) qualquer pedido cujo id/numero ja exista
    em alguma HoraVenda — evita replicar 2x se o scheduler rodar de novo.
    """
    codigo_externo = pedido.get('codigo_externo')
    if codigo_externo and str(codigo_externo).strip().isdigit():
        if db.session.get(HoraVenda, int(codigo_externo)) is not None:
            return True
    pedido_id = pedido.get('id')
    if pedido_id and HoraVenda.query.filter_by(tagplus_pedido_id=pedido_id).first():
        return True
    numero = pedido.get('numero')
    if numero and HoraVenda.query.filter_by(tagplus_pedido_numero=numero).first():
        return True
    return False


def _varrer(api, base: int, *, limite_ausencias: int = LIMITE_AUSENCIAS,
            limite_varredura: int = LIMITE_VARREDURA):
    """Logica PURA do numero-walk a partir de base+1 (nao persiste nada).

    Retorna (descobertos, maior_existente):
      - descobertos: lista de pedidos NAO-nossos achados (a replicar).
      - maior_existente: maior numero onde havia pedido (>= base) — vira o cursor.
    """
    cursor = base
    ausencias = 0
    maior_existente = base
    descobertos: list[dict] = []
    varridos = 0
    while ausencias < limite_ausencias and varridos < limite_varredura:
        varridos += 1
        cursor += 1
        pedido = busca_pedido_por_numero(api, cursor)
        if pedido:
            ausencias = 0
            maior_existente = cursor
            if not pedido_e_nosso(pedido):
                descobertos.append(pedido)
        else:
            ausencias += 1
    return descobertos, maior_existente


def numero_walk(api, conta, *, limite_ausencias: int = LIMITE_AUSENCIAS,
                limite_varredura: int = LIMITE_VARREDURA) -> list[dict]:
    """Executa a descoberta reversa e persiste o cursor. Retorna os descobertos.

    base = max(maior numero conhecido no sistema, cursor da conta). Persiste o
    cursor SOMENTE se avancou (nunca regride). Nao replica — devolve os pedidos
    nao-nossos para o caller (cron/replicacao) processar.
    """
    cursor_atual = conta.ultimo_pedido_numero_reconciliado or 0
    base = max(_maior_numero_conhecido(), cursor_atual)
    descobertos, maior = _varrer(
        api, base, limite_ausencias=limite_ausencias, limite_varredura=limite_varredura,
    )
    if maior > cursor_atual:
        conta.ultimo_pedido_numero_reconciliado = maior
        db.session.commit()
    logger.info(
        'numero_walk: base=%s -> cursor=%s, %s descoberto(s) nao-nosso(s)',
        base, maior, len(descobertos),
    )
    return descobertos
