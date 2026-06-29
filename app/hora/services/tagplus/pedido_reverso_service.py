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
import os

from app import db
from app.hora.models.venda import HoraVenda, VENDA_STATUS_INCOMPLETO
from app.hora.services.tagplus.pedido_service import busca_pedido_por_numero

logger = logging.getLogger(__name__)

LIMITE_AUSENCIAS = 3       # para apos N ausencias seguidas (numero-walk +3)
LIMITE_VARREDURA = 300     # guard anti-loop infinito (max numeros por execucao)

# Divergencia registrada por item-modelo do pedido replicado: o pedido TagPlus
# identifica item por MODELO (fungivel), mas HoraVendaItem exige chassi fisico
# (NOT NULL). O operador vincula o chassi na tela de edicao do pedido INCOMPLETO.
TIPO_DIVERGENCIA_AGUARDANDO_CHASSI = 'AGUARDANDO_CHASSI'


def reverso_habilitado() -> bool:
    """Gate da descoberta reversa (cria HoraVenda). Default OFF — evita gerar
    vendas espurias antes de validar o numero-walk em PROD. Espelha a flag de
    push (HORA_TAGPLUS_PUSH_PEDIDO), mas e' INDEPENDENTE: o reverso nao depende
    do to_nfe nem do push para ser ligado."""
    return os.environ.get('HORA_TAGPLUS_REVERSO', '0') in ('1', 'true', 'True')


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


def _resolver_loja_id(departamento_desc):
    """departamento.descricao -> loja_id via HoraTagPlusDepartamentoMap (ou None).

    REGRA FISCAL: emitente e' sempre matriz; a loja FISICA vem do departamento.
    Sem mapeamento -> None (operador define depois, mesma politica do backfill).
    """
    if not departamento_desc:
        return None
    from app.hora.models.tagplus import HoraTagPlusDepartamentoMap
    from app.hora.services.tagplus.pedido_service import normalizar_departamento
    norm = normalizar_departamento(departamento_desc)
    if not norm:
        return None
    mapa = HoraTagPlusDepartamentoMap.query.filter_by(departamento_norm=norm).first()
    return mapa.loja_id if mapa else None


def replicar(pedido: dict):
    """Cria HoraVenda INCOMPLETO (origem TAGPLUS) a partir de um pedido descoberto.

    Idempotente: retorna None se o pedido ja foi replicado ou e' nosso (push).
    Itens-por-modelo viram divergencias AGUARDANDO_CHASSI — HoraVendaItem exige
    chassi (NOT NULL), entao o operador vincula a moto fisica na tela de edicao
    do pedido INCOMPLETO (disparando reserva + evento RESERVADA, fluxo normal).
    Cliente/loja resolvidos do pedido; payload cru guardado no JSONB p/ auditoria.
    """
    from decimal import Decimal

    from app.hora.models.venda import HoraVendaDivergencia
    from app.hora.services.tagplus import pedido_service
    from app.hora.services.tagplus._documento import normalizar_documento
    from app.utils.json_helpers import sanitize_for_json

    if pedido_e_nosso(pedido):
        return None

    cliente = pedido.get('cliente') or {}
    documento, _tipo = normalizar_documento(cliente.get('cpf') or cliente.get('cnpj') or '')
    nome = (cliente.get('razao_social') or cliente.get('nome') or '').strip()[:200]

    dep_desc = pedido_service.extrair_departamento_descricao(pedido)
    loja_id = _resolver_loja_id(dep_desc)

    venda = HoraVenda(
        cpf_cliente=(documento or '00000000000')[:14],
        nome_cliente=nome or 'CLIENTE TAGPLUS',
        valor_total=Decimal(str(pedido.get('valor_total') or 0)),
        status=VENDA_STATUS_INCOMPLETO,
        origem_criacao='TAGPLUS',
        loja_id=loja_id,
        tagplus_pedido_id=pedido.get('id'),
        tagplus_pedido_numero=pedido.get('numero'),
        tagplus_departamento=dep_desc,
        tagplus_pedido_payload=sanitize_for_json(pedido),
    )
    db.session.add(venda)
    db.session.flush()

    for item in (pedido.get('itens') or []):
        ps = item.get('produto_servico') or {}
        if isinstance(ps, dict):
            label = ps.get('descricao') or ps.get('codigo') or str(ps.get('id') or '?')
        else:
            label = str(ps)
        qtd = item.get('qtd') or 1
        db.session.add(HoraVendaDivergencia(
            venda_id=venda.id,
            tipo=TIPO_DIVERGENCIA_AGUARDANDO_CHASSI,
            numero_chassi=None,
            detalhe=(
                f'Pedido TagPlus {pedido.get("numero")}: aguardando vinculo de '
                f'chassi para "{label}" (qtd {qtd}).'
            ),
            valor_esperado=str(label)[:200],
        ))

    db.session.commit()
    logger.info(
        'replicar: HoraVenda %s criada de pedido TP %s/nº%s (loja=%s)',
        venda.id, pedido.get('id'), pedido.get('numero'), loja_id,
    )
    return venda


def descobrir_e_replicar(api, conta, **kw) -> list:
    """Orquestra a Fase 3: numero_walk (descobre) -> replicar cada nao-nosso.

    Tolerante por pedido: falha em 1 replicacao nao aborta as demais. Retorna a
    lista de HoraVenda criadas. Ponto de entrada do cron.
    """
    descobertos = numero_walk(api, conta, **kw)
    replicados = []
    for pedido in descobertos:
        try:
            venda = replicar(pedido)
            if venda is not None:
                replicados.append(venda)
        except Exception as exc:
            logger.exception(
                'replicar pedido TP nº%s falhou (tolerante): %s',
                pedido.get('numero'), exc,
            )
            db.session.rollback()
    return replicados


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
