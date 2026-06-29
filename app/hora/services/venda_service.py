"""Service de HoraVenda — pedido de venda ao consumidor final.

Maquina de estado (status):
    COTACAO    -> CONFIRMADO  (confirmar_venda)
    CONFIRMADO -> FATURADO    (webhook TagPlus nfe_aprovada)
    *          -> CANCELADO   (cancelar_venda; FATURADO so apos NFe cancelada)
    DANFE legado -> FATURADO direto (importar_nf_saida_pdf).

Estoque:
    COTACAO/CONFIRMADO/FATURADO reservam o chassi (saem do estoque disponivel).
    CANCELADO devolve via evento DEVOLVIDA.

Lock pessimista:
    criar_venda_manual + editar_item_pedido + adicionar_item_pedido fazem
    SELECT FOR UPDATE no chassi para impedir reserva concorrente.

Auditoria:
    Toda transicao registra HoraVendaAuditoria via venda_audit.registrar_auditoria.
"""
from __future__ import annotations

import io
from datetime import date, datetime, time
from decimal import Decimal
from typing import Iterable, List, Optional, Union

from flask import current_app

from app import db
from app.hora.models import (
    HoraLoja,
    HoraMoto,
    HoraMotoEvento,
    HoraPeca,
    HoraTabelaPreco,
    HoraVenda,
    HoraVendaDivergencia,
    HoraVendaItem,
    HoraVendaItemPeca,
    HoraVendaPagamento,
    VENDA_STATUS_CANCELADO,
    VENDA_STATUS_CONFIRMADO,
    VENDA_STATUS_COTACAO,
    VENDA_STATUS_FATURADO,
    VENDA_STATUS_INCOMPLETO,
    VENDA_ORIGEM_LEAD_VALIDOS,
    VENDA_ORIGEM_LEAD_OUTROS,
)
from app.hora.models.tagplus import (
    HoraTagPlusNfeEmissao,
    NFE_STATUS_APROVADA,
    NFE_STATUS_CANCELAMENTO_SOLICITADO,
    NFE_STATUS_EM_ENVIO,
    NFE_STATUS_ENVIADA_SEFAZ,
)
from app.hora.services import venda_audit
from app.hora.services.estoque_service import EVENTOS_EM_ESTOQUE
from app.hora.services.moto_service import (
    devolver_ao_estoque,
    get_or_create_moto,
    registrar_evento,
)
from app.hora.services.parsers import parse_danfe_to_hora_payload
from app.utils.file_storage import FileStorage
from app.utils.timezone import agora_utc_naive, agora_brasil


# --------------------------------------------------------------------------
# Tipos de divergencia (espelhado em hora_17_nf_saida.sql)
# --------------------------------------------------------------------------
TIPOS_DIVERGENCIA_VENDA = (
    'CHASSI_NAO_CADASTRADO',
    'CHASSI_INDISPONIVEL',
    'LOJA_DIVERGENTE',
    'CNPJ_DESCONHECIDO',
    'TABELA_PRECO_AUSENTE',
    'PRECO_ACIMA_TABELA',
    # Adicionado migration hora_29: nome do produto na origem (TagPlus,
    # NF, pedido) nao bate em nenhum HoraModeloAlias — pendencia foi
    # criada em hora_modelo_pendente. Item da venda fica sem HoraMoto
    # ate operador resolver em /hora/modelos/pendencias.
    'MODELO_PENDENTE',
)

# Estados de NFe que bloqueiam edicao/cancelamento livre da venda.
_NFE_EM_VOO = (NFE_STATUS_EM_ENVIO, NFE_STATUS_ENVIADA_SEFAZ, NFE_STATUS_CANCELAMENTO_SOLICITADO)

# --------------------------------------------------------------------------
# Frete CIF (migration hora_38)
# --------------------------------------------------------------------------
# Valores validos de tipo_frete_calc (ver app/hora/models/venda.py).
TIPOS_FRETE_CALC = ('INCLUSO', 'ADICIONAR')


def _normalizar_frete(
    modalidade_frete: Optional[str],
    valor_frete,
    tipo_frete_calc: Optional[str],
):
    """Normaliza e valida (valor_frete, tipo_frete_calc) contra modalidade.

    Regras:
        - tipo_frete_calc deve estar em TIPOS_FRETE_CALC ou ser None.
        - Se tipo_frete_calc preenchido, modalidade DEVE ser '0' (CIF).
        - valor_frete >= 0; aceita Decimal/str/int. Vazio/None -> None.

    Retorna:
        (valor_frete_dec_or_none, tipo_frete_calc_or_none)
    """
    tipo_norm = (tipo_frete_calc or '').strip().upper() or None
    if tipo_norm and tipo_norm not in TIPOS_FRETE_CALC:
        raise ValueError(
            f'tipo_frete_calc invalido: {tipo_frete_calc!r} '
            f"(esperado {TIPOS_FRETE_CALC} ou vazio)"
        )

    if isinstance(valor_frete, str):
        s = valor_frete.strip()
        if not s:
            valor_dec = None
        else:
            # Aceita formato BR (1.234,56) ou US (1234.56).
            if ',' in s:
                s = s.replace('.', '').replace(',', '.')
            try:
                valor_dec = Decimal(s)
            except Exception as exc:
                raise ValueError(f'valor_frete invalido: {valor_frete!r}') from exc
    elif valor_frete is None:
        valor_dec = None
    else:
        try:
            valor_dec = Decimal(str(valor_frete))
        except Exception as exc:
            raise ValueError(f'valor_frete invalido: {valor_frete!r}') from exc

    if valor_dec is not None and valor_dec < 0:
        raise ValueError(f'valor_frete deve ser >= 0 (recebido: {valor_dec})')

    # Coerencia: tipo_frete_calc so faz sentido com modalidade CIF ('0').
    # Se modalidade != '0', SILENCIOSAMENTE descarta tipo + valor (UI ja
    # esconde os controles via JS; este return None,None cobre o cenario
    # de operador trocar CIF->FOB no mesmo submit que ainda traz dados de
    # frete antigos no payload). Levantar ValueError aqui daria erro
    # confuso ao operador (intent claro era trocar para FOB, nao validar
    # frete). Defesa em profundidade contra POST automatizado/JS desligado.
    if tipo_norm and (modalidade_frete or '').strip() != '0':
        return None, None

    # Se nao informou tipo, valor_frete tambem nao faz sentido — zera.
    if not tipo_norm:
        valor_dec = None

    return valor_dec, tipo_norm


def _para_datetime(valor) -> Optional[datetime]:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, date):
        return datetime.combine(valor, time.min)
    return None


class NfSaidaJaImportada(Exception):
    """NF com mesma chave_44 já existe em HoraVenda."""


class ChassiIndisponivelError(ValueError):
    """Chassi nao esta disponivel para reserva (ja reservado / vendido / fora de estoque)."""


class TransicaoInvalidaError(ValueError):
    """Transicao de status nao permitida."""


# --------------------------------------------------------------------------
# Helpers internos
# --------------------------------------------------------------------------

def _salvar_pdf_storage(
    pdf_bytes: bytes, chave_44: str, nome_arquivo_origem: Optional[str]
) -> Optional[str]:
    try:
        buf = io.BytesIO(pdf_bytes)
        buf.name = (nome_arquivo_origem or f'venda_{chave_44}.pdf')
        s3_key = FileStorage().save_file(
            buf, folder='hora/vendas', filename=f'{chave_44}.pdf',
            allowed_extensions=['pdf'],
        )
        return s3_key
    except Exception as exc:
        current_app.logger.warning(
            f'hora: falha ao persistir PDF da NF de saida chave={chave_44}: {exc}'
        )
        return None


def _registrar_divergencia(
    venda_id: int,
    tipo: str,
    numero_chassi: Optional[str] = None,
    detalhe: Optional[str] = None,
    valor_esperado: Optional[str] = None,
    valor_conferido: Optional[str] = None,
) -> HoraVendaDivergencia:
    """UPSERT idempotente em HoraVendaDivergencia.

    A tabela tem UNIQUE (venda_id, tipo, numero_chassi). Em re-execucoes do
    backfill TagPlus, INSERT puro violava `uq_hora_venda_divergencia_tipo_chassi`
    e cada NF re-importada falhava (50s perdidos no retry de SSL drop antes
    de marcar erro). Agora reutilizamos a divergencia existente — se algo
    mudou no detalhe/valores, atualizamos; se ja foi resolvida, mantemos
    como esta (operador ja decidiu).
    """
    if tipo not in TIPOS_DIVERGENCIA_VENDA:
        raise ValueError(f'tipo de divergencia invalido: {tipo}')

    # Procura divergencia existente (chassi NULL precisa de filtro `IS NULL`).
    query = HoraVendaDivergencia.query.filter_by(venda_id=venda_id, tipo=tipo)
    if numero_chassi is None:
        query = query.filter(HoraVendaDivergencia.numero_chassi.is_(None))
    else:
        query = query.filter(HoraVendaDivergencia.numero_chassi == numero_chassi)
    div = query.first()

    if div is not None:
        # Atualiza apenas se ainda esta aberta (preserva resolucoes do operador).
        if div.aberta:
            if detalhe is not None and div.detalhe != detalhe:
                div.detalhe = detalhe
            if valor_esperado is not None and div.valor_esperado != valor_esperado:
                div.valor_esperado = valor_esperado
            if valor_conferido is not None and div.valor_conferido != valor_conferido:
                div.valor_conferido = valor_conferido
            db.session.flush()
        return div

    div = HoraVendaDivergencia(
        venda_id=venda_id,
        tipo=tipo,
        numero_chassi=numero_chassi,
        detalhe=detalhe,
        valor_esperado=valor_esperado,
        valor_conferido=valor_conferido,
    )
    db.session.add(div)
    db.session.flush()
    return div


def _ultimo_evento(chassi: str) -> Optional[HoraMotoEvento]:
    return (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi)
        .order_by(HoraMotoEvento.timestamp.desc())
        .first()
    )


def _buscar_preco_vigente(modelo_id: int, na_data) -> Optional[HoraTabelaPreco]:
    from sqlalchemy import or_
    return (
        HoraTabelaPreco.query
        .filter(
            HoraTabelaPreco.modelo_id == modelo_id,
            HoraTabelaPreco.ativo.is_(True),
            HoraTabelaPreco.vigencia_inicio <= na_data,
            or_(
                HoraTabelaPreco.vigencia_fim.is_(None),
                HoraTabelaPreco.vigencia_fim >= na_data,
            ),
        )
        .order_by(HoraTabelaPreco.vigencia_inicio.desc())
        .first()
    )


def _resolver_loja_por_cnpj(cnpj_emitente: Optional[str]) -> Optional[HoraLoja]:
    if not cnpj_emitente:
        return None
    digitos = ''.join(c for c in cnpj_emitente if c.isdigit())
    if not digitos:
        return None
    return HoraLoja.query.filter_by(cnpj=digitos, ativa=True).first()


def _resolver_loja_por_departamento(
    tagplus_departamento: Optional[str],
) -> Optional[HoraLoja]:
    """Loja fisica via de-para `hora_tagplus_departamento_map` (tagplus_departamento).

    Retorna None se nao ha departamento, se nao existe mapa, ou se o mapa ainda
    nao tem `loja_id` atribuido (departamento observado mas pendente de mapeamento
    na tela /hora/tagplus/departamento-map).
    """
    if not tagplus_departamento:
        return None
    from app.hora.models import HoraTagPlusDepartamentoMap
    from app.hora.services.tagplus.pedido_service import normalizar_departamento
    norm = normalizar_departamento(tagplus_departamento)
    if not norm:
        return None
    mapa = HoraTagPlusDepartamentoMap.query.filter_by(departamento_norm=norm).first()
    if mapa is None or mapa.loja_id is None:
        return None
    return HoraLoja.query.get(mapa.loja_id)


def _resolver_loja_real_venda(
    cnpj_emitente: Optional[str],
    tagplus_departamento: Optional[str] = None,
) -> Optional[HoraLoja]:
    """Loja FISICA da venda — NUNCA a matriz (emitente fiscal != loja de venda).

    Toda NFe da HORA sai com o CNPJ da matriz (invariante CLAUDE.md secao 7), entao
    o CNPJ emitente NAO pode ser usado para atribuir a loja de venda. Ordem:
      1. de-para de departamento (loja fisica real do pedido TagPlus);
      2. CNPJ emitente SE a loja resolvida NAO for a matriz (futuro: emissao por
         CNPJ proprio da filial);
      3. None — loja a definir (caller registra divergencia; correcao posterior via
         `definir_loja_venda` ou re-aplicacao do de-para de departamento).
    """
    loja = _resolver_loja_por_departamento(tagplus_departamento)
    if loja is not None:
        return loja
    loja = _resolver_loja_por_cnpj(cnpj_emitente)
    if loja is not None and not loja.is_matriz:
        return loja
    return None


def _assert_sem_avaria_aberta(chassi_norm: str) -> None:
    """Avaria ABERTA torna a moto NAO-VENDAVEL: continua em estoque (visivel), mas
    nao pode ser reservada/vendida ate a ultima avaria ser resolvida ou ignorada.

    Fonte de verdade da vendabilidade: HoraAvaria status='ABERTA' (via
    avaria_service.avarias_abertas_por_chassi) — NAO o tipo do ultimo evento, pois
    AVARIADA permanece em EVENTOS_EM_ESTOQUE (a moto segue contando no estoque).
    Import lazy: avaria_service importa estoque_service no topo; mantemos lazy p/
    evitar qualquer ciclo de import.
    """
    from app.hora.services import avaria_service
    if avaria_service.avarias_abertas_por_chassi([chassi_norm]).get(chassi_norm, 0) > 0:
        raise ChassiIndisponivelError(
            f'Chassi {chassi_norm} tem avaria aberta — resolva em /hora/avarias '
            f'antes de vender'
        )


def _lock_chassi_e_validar_disponivel(chassi: str) -> tuple[HoraMoto, HoraMotoEvento]:
    """SELECT ... FOR UPDATE no HoraMoto + valida disponibilidade.

    Retorna (moto, ultimo_evento). Levanta ChassiIndisponivelError se nao
    estiver em EVENTOS_EM_ESTOQUE ou se tiver avaria ABERTA (nao-vendavel).
    """
    chassi_norm = (chassi or '').strip().upper()
    if not chassi_norm:
        raise ValueError('Chassi obrigatorio')

    moto = (
        db.session.query(HoraMoto)
        .filter(HoraMoto.numero_chassi == chassi_norm)
        .with_for_update()
        .first()
    )
    if not moto:
        raise ChassiIndisponivelError(f'Chassi {chassi_norm} nao cadastrado')

    ult = _ultimo_evento(chassi_norm)
    if ult is None or ult.tipo not in EVENTOS_EM_ESTOQUE:
        ult_tipo = ult.tipo if ult else 'sem eventos'
        raise ChassiIndisponivelError(
            f'Chassi {chassi_norm} nao esta disponivel para reserva '
            f'(ultimo evento: {ult_tipo})'
        )
    _assert_sem_avaria_aberta(chassi_norm)
    return moto, ult


def _emissao_nfe(venda_id: int) -> Optional[HoraTagPlusNfeEmissao]:
    return HoraTagPlusNfeEmissao.query.filter_by(venda_id=venda_id).first()


def _buscar_preco_modelo(
    modelo_id: int, forma_pagamento_hora: Optional[str], na_data,
) -> tuple[Optional[Decimal], str, Optional[int]]:
    """Resolve preço de tabela do modelo conforme forma de pagamento.

    Retorna `(preco, fonte, tabela_preco_id)`:
      preco: Decimal ou None se nao houver tabela alguma para o modelo.
      fonte: 'MODELO_A_VISTA' | 'MODELO_A_PRAZO' | 'TABELA_LEGADA' | 'AUSENTE'.
      tabela_preco_id: id da HoraTabelaPreco usada (so quando fonte='TABELA_LEGADA').

    Prioridade:
      1. HoraModelo.preco_a_vista / preco_a_prazo conforme tipo da forma de
         pagamento (HoraTagPlusFormaPagamentoMap.tipo_pagamento).
      2. Se forma desconhecida ou tipo nao classificado, prefere preco_a_vista
         (default mais comum); fallback para preco_a_prazo.
      3. Ultimo recurso: HoraTabelaPreco vigente em na_data (legado).
    """
    from app.hora.models import HoraModelo
    from app.hora.models.tagplus import (
        HoraTagPlusFormaPagamentoMap,
        TIPO_PAGAMENTO_A_VISTA,
        TIPO_PAGAMENTO_A_PRAZO,
    )

    modelo = HoraModelo.query.get(modelo_id) if modelo_id else None
    if modelo is None:
        return None, 'AUSENTE', None

    tipo = None
    if forma_pagamento_hora:
        forma_norm = forma_pagamento_hora.strip().upper()
        if forma_norm and forma_norm != 'NAO_INFORMADO':
            mapa = HoraTagPlusFormaPagamentoMap.query.filter_by(
                forma_pagamento_hora=forma_norm,
            ).first()
            if mapa is not None:
                tipo = mapa.tipo_pagamento

    if tipo == TIPO_PAGAMENTO_A_VISTA and modelo.preco_a_vista is not None:
        return Decimal(str(modelo.preco_a_vista)), 'MODELO_A_VISTA', None
    if tipo == TIPO_PAGAMENTO_A_PRAZO and modelo.preco_a_prazo is not None:
        return Decimal(str(modelo.preco_a_prazo)), 'MODELO_A_PRAZO', None

    # Fallback intra-modelo: prefere a vista, depois a prazo.
    if modelo.preco_a_vista is not None:
        return Decimal(str(modelo.preco_a_vista)), 'MODELO_A_VISTA', None
    if modelo.preco_a_prazo is not None:
        return Decimal(str(modelo.preco_a_prazo)), 'MODELO_A_PRAZO', None

    # Ultimo fallback: HoraTabelaPreco legado.
    tabela = _buscar_preco_vigente(modelo_id, na_data)
    if tabela is not None:
        return Decimal(str(tabela.preco_tabela)), 'TABELA_LEGADA', tabela.id

    return None, 'AUSENTE', None


def buscar_preco_para_pedido(
    modelo_id: int,
    forma_pagamento_hora: Optional[str] = None,
    na_data=None,
) -> dict:
    """API publica para o JS do pedido de venda manual.

    Retorna dict com preço sugerido e qual a fonte:
      {
        'preco': Decimal | None,
        'fonte': 'MODELO_A_VISTA' | 'MODELO_A_PRAZO' | 'TABELA_LEGADA' | 'AUSENTE',
        'tipo_pagamento': 'A_VISTA' | 'A_PRAZO' | None,
        'preco_a_vista': Decimal | None,   # campo direto do modelo (informativo).
        'preco_a_prazo': Decimal | None,
      }
    """
    from app.hora.models import HoraModelo
    from app.hora.models.tagplus import HoraTagPlusFormaPagamentoMap

    if na_data is None:
        na_data = date.today()

    preco, fonte, _tab_id = _buscar_preco_modelo(
        modelo_id, forma_pagamento_hora, na_data,
    )

    tipo = None
    if forma_pagamento_hora:
        forma_norm = forma_pagamento_hora.strip().upper()
        if forma_norm and forma_norm != 'NAO_INFORMADO':
            mapa = HoraTagPlusFormaPagamentoMap.query.filter_by(
                forma_pagamento_hora=forma_norm,
            ).first()
            if mapa is not None:
                tipo = mapa.tipo_pagamento

    modelo = HoraModelo.query.get(modelo_id) if modelo_id else None
    return {
        'preco': preco,
        'fonte': fonte,
        'tipo_pagamento': tipo,
        'preco_a_vista': modelo.preco_a_vista if modelo else None,
        'preco_a_prazo': modelo.preco_a_prazo if modelo else None,
    }


def _resolver_preco_tabela(
    modelo_id: int,
    na_data,
    valor_final: Decimal,
    forma_pagamento_hora: Optional[str] = None,
) -> tuple[Decimal, Decimal, Decimal, Optional[int], Optional[str]]:
    """Retorna (preco_tabela_ref, desconto_rs, desconto_pct, tabela_preco_id, divergencia_tipo).

    `desconto_pct` e Decimal(5,2) — coerente com hora_venda_item.desconto_percentual.
    `divergencia_tipo` (se preenchido) deve ser registrado pelo chamador com
    detalhe apropriado (vence aqui o calculo, nao o registro).

    Assinatura atualizada (migration hora_33): agora aceita `forma_pagamento_hora`
    para escolher entre preco_a_vista / preco_a_prazo do modelo. Callers legacy
    (DANFE import) podem omitir; nesse caso usa fallback prefere-A_VISTA.
    """
    preco_ref, _fonte, tabela_id = _buscar_preco_modelo(
        modelo_id, forma_pagamento_hora, na_data,
    )
    if preco_ref is None:
        return (
            Decimal(str(valor_final)),
            Decimal('0.00'),
            Decimal('0.00'),
            None,
            'TABELA_PRECO_AUSENTE',
        )
    desconto = preco_ref - Decimal(str(valor_final))
    if desconto < 0:
        # Preço final acima da tabela — registra como divergencia, item nao
        # ganha desconto negativo (preserva auditoria).
        return (
            Decimal(str(valor_final)),
            Decimal('0.00'),
            Decimal('0.00'),
            None,
            'PRECO_ACIMA_TABELA',
        )
    if preco_ref > 0:
        pct = (desconto / preco_ref) * Decimal('100')
        pct = pct.quantize(Decimal('0.01'))
    else:
        pct = Decimal('0.00')
    return preco_ref, desconto, pct, tabela_id, None


def validar_desconto_tabela(modelo_id, valor_final, forma_pagamento_hora=None, na_data=None):
    """Publico (Onda F): valida um preco final proposto contra a tabela do modelo.

    Delega a _resolver_preco_tabela (interno) e devolve um dict limpo no lugar
    da 5-tupla, para a skill READ consultando-venda-loja consumir sem acoplar a
    funcao privada.

    Args:
        modelo_id: id do HoraModelo.
        valor_final: preco final proposto (Decimal/str/number).
        forma_pagamento_hora: 'A_VISTA' | 'A_PRAZO' | None.
        na_data: date de referencia da vigencia; default = hoje (Brasil).

    Returns:
        dict {modelo_id, preco_referencia, desconto_rs, desconto_pct, tabela_id, divergencia}
    """
    if na_data is None:
        na_data = agora_brasil().date()
    preco_ref, desconto_rs, desconto_pct, tabela_id, divergencia = _resolver_preco_tabela(
        modelo_id, na_data, Decimal(str(valor_final)), forma_pagamento_hora
    )
    return {
        "modelo_id": modelo_id,
        "preco_referencia": preco_ref,
        "desconto_rs": desconto_rs,
        "desconto_pct": desconto_pct,
        "tabela_id": tabela_id,
        "divergencia": divergencia,
    }


# --------------------------------------------------------------------------
# Helpers de pagamento (multi-formas — migration hora_34)
# --------------------------------------------------------------------------

def _normalizar_pagamentos(pagamentos: Optional[List[dict]]) -> List[dict]:
    """Sanitiza lista de pagamentos vindas do form/API.

    Cada item de entrada deve ter as chaves:
        forma_pagamento_hora: str (obrigatorio)
        valor: Decimal | str (obrigatorio, > 0)
        numero_parcelas: int (default 1)
        aut_id: str | None (opcional)

    Retorna lista normalizada (forma upper, valor Decimal, parcelas int >= 1,
    aut_id stripped). Pagamentos com `valor <= 0` ou `forma` vazia sao
    descartados silenciosamente.
    """
    if not pagamentos:
        return []
    out: List[dict] = []
    for p in pagamentos:
        forma = (p.get('forma_pagamento_hora') or '').strip().upper()
        if not forma:
            continue
        try:
            valor = Decimal(str(p.get('valor') or '0'))
        except Exception:
            continue
        if valor <= 0:
            continue
        try:
            parcelas = int(p.get('numero_parcelas') or 1)
        except (TypeError, ValueError):
            parcelas = 1
        if parcelas < 1 or parcelas > 60:
            parcelas = 1
        aut = (p.get('aut_id') or '').strip() or None
        out.append({
            'forma_pagamento_hora': forma[:20],
            'valor': valor,
            'numero_parcelas': parcelas,
            'aut_id': aut[:50] if aut else None,
        })
    return out


def _classificar_formas_para_preco(pagamentos: List[dict]) -> Optional[str]:
    """Retorna nome da forma representativa para resolver preco do modelo.

    Regra (decisao do dono em 2026-05-07): se QUALQUER pagamento e A_PRAZO,
    o preco do modelo deve ser A_PRAZO. Senao, A_VISTA. Esta funcao escolhe
    uma forma "vencedora" para passar ao `_buscar_preco_modelo` existente.

    Retorna:
        - Nome de uma forma A_PRAZO se houver alguma na lista.
        - Senao, nome de uma forma A_VISTA se houver.
        - Senao, primeiro nome bruto (caller cai em fallback de tabela legada).
        - None se lista vazia.
    """
    from app.hora.models.tagplus import (
        HoraTagPlusFormaPagamentoMap,
        TIPO_PAGAMENTO_A_PRAZO,
        TIPO_PAGAMENTO_A_VISTA,
    )
    if not pagamentos:
        return None
    nomes = [p['forma_pagamento_hora'] for p in pagamentos]
    mapas = (
        HoraTagPlusFormaPagamentoMap.query
        .filter(HoraTagPlusFormaPagamentoMap.forma_pagamento_hora.in_(nomes))
        .all()
    )
    mapas_por_nome = {m.forma_pagamento_hora: m for m in mapas}
    for nome in nomes:
        m = mapas_por_nome.get(nome)
        if m and m.tipo_pagamento == TIPO_PAGAMENTO_A_PRAZO:
            return nome
    for nome in nomes:
        m = mapas_por_nome.get(nome)
        if m and m.tipo_pagamento == TIPO_PAGAMENTO_A_VISTA:
            return nome
    return nomes[0]


def _avaliar_status_pagamento(
    pagamentos: List[dict],
    valor_total: Decimal,
) -> tuple[str, List[str]]:
    """Decide se a venda nasce COTACAO ou INCOMPLETO baseado nos pagamentos.

    Criterios para INCOMPLETO (qualquer um dispara):
      - lista de pagamentos vazia.
      - soma dos valores != valor_total (tolerancia R$ 0,01 para arred).
      - alguma forma exige_aut_id=True com aut_id vazio/None.

    Returns:
        (status, motivos): status = VENDA_STATUS_COTACAO ou VENDA_STATUS_INCOMPLETO.
        motivos: lista de strings explicativas (vazio se status=COTACAO).
    """
    motivos: List[str] = []
    if not pagamentos:
        motivos.append('Nenhuma forma de pagamento informada.')
        return VENDA_STATUS_INCOMPLETO, motivos

    soma = sum((p['valor'] for p in pagamentos), Decimal('0'))
    diff = (soma - Decimal(str(valor_total))).copy_abs()
    if diff > Decimal('0.01'):
        motivos.append(
            f'Soma das formas de pagamento (R$ {soma}) difere do valor total '
            f'(R$ {valor_total}).'
        )

    # Aut/ID: checar formas com exige_aut_id=True.
    from app.hora.models.tagplus import HoraTagPlusFormaPagamentoMap
    nomes = [p['forma_pagamento_hora'] for p in pagamentos]
    mapas = (
        HoraTagPlusFormaPagamentoMap.query
        .filter(HoraTagPlusFormaPagamentoMap.forma_pagamento_hora.in_(nomes))
        .all()
    )
    mapas_por_nome = {m.forma_pagamento_hora: m for m in mapas}
    for p in pagamentos:
        m = mapas_por_nome.get(p['forma_pagamento_hora'])
        if m and m.exige_aut_id and not p.get('aut_id'):
            motivos.append(
                f'Forma {p["forma_pagamento_hora"]} exige AUT/ID — preencher '
                f'numero de autorizacao.'
            )

    if motivos:
        return VENDA_STATUS_INCOMPLETO, motivos
    return VENDA_STATUS_COTACAO, []


def motivos_incompleto_venda(venda) -> List[str]:
    """Motivos REAIS de a venda estar INCOMPLETA (para exibir na tela).

    Recalcula via `_avaliar_status_pagamento` sobre os pagamentos ja persistidos,
    para que o badge mostre a causa exata — soma das formas divergente E/OU
    AUT/ID faltando em forma que exige — em vez de uma mensagem fixa generica
    (que enganava quando a soma batia mas faltava o AUT). Retorna [] se a venda
    nao estiver em INCOMPLETO.
    """
    if getattr(venda, 'status', None) != VENDA_STATUS_INCOMPLETO:
        return []
    pagamentos = [
        {
            'forma_pagamento_hora': p.forma_pagamento_hora,
            'valor': Decimal(str(p.valor or 0)),
            'aut_id': p.aut_id,
        }
        for p in (venda.pagamentos or [])
    ]
    _status, motivos = _avaliar_status_pagamento(
        pagamentos, Decimal(str(venda.valor_total or 0)),
    )
    return motivos


# --------------------------------------------------------------------------
# Fluxo de criacao manual: COTACAO/INCOMPLETO + lock pessimista + RESERVADA
# --------------------------------------------------------------------------

def _normalizar_origem_lead(origem_lead, origem_lead_obs):
    """Normaliza/valida a origem do lead (roadmap #6 — como conheceu a loja).

    Retorna `(origem_norm, obs_norm)`:
    - origem_norm: None se vazio, senao um valor de VENDA_ORIGEM_LEAD_VALIDOS.
    - obs_norm: texto livre (<=255) APENAS quando origem == OUTROS; caso
      contrario None (o texto livre so se aplica a "Outros").

    Levanta ValueError se a origem for invalida ou se OUTROS vier sem obs.
    O service aceita origem vazia (None) para nao quebrar import DANFE /
    backfill / vendas legadas — a obrigatoriedade do SELECT e do form manual
    (rota + frontend).
    """
    origem = (origem_lead or '').strip().upper() or None
    obs = (origem_lead_obs or '').strip() or None
    if origem is None:
        return None, None
    if origem not in VENDA_ORIGEM_LEAD_VALIDOS:
        raise ValueError(
            f'origem_lead invalida: {origem_lead!r} '
            f'(esperado um de {sorted(VENDA_ORIGEM_LEAD_VALIDOS)})'
        )
    if origem == VENDA_ORIGEM_LEAD_OUTROS:
        if not obs:
            raise ValueError(
                'Informe a observacao da origem quando selecionar "Outros".'
            )
        return origem, obs[:255]
    return origem, None


def criar_venda_manual(
    cpf_cliente: str,
    nome_cliente: str,
    inscricao_estadual: Optional[str] = None,
    cep: Optional[str] = None,
    endereco_logradouro: Optional[str] = None,
    endereco_numero: Optional[str] = None,
    endereco_complemento: Optional[str] = None,
    endereco_bairro: Optional[str] = None,
    endereco_cidade: Optional[str] = None,
    endereco_uf: Optional[str] = None,
    numero_chassi: Optional[str] = None,
    valor_final: Optional[Decimal] = None,
    forma_pagamento: Optional[str] = None,
    telefone_cliente: Optional[str] = None,
    telefone_lead: Optional[str] = None,
    email_cliente: Optional[str] = None,
    vendedor: Optional[str] = None,
    observacoes: Optional[str] = None,
    modalidade_frete: str = '0',
    numero_parcelas: int = 1,
    intervalo_parcelas_dias: int = 30,
    criado_por: Optional[str] = None,
    criado_por_id: Optional[int] = None,
    loja_id_override: Optional[int] = None,
    pagamentos: Optional[List[dict]] = None,
    consumidor_final: Optional[bool] = None,
    valor_frete=None,
    tipo_frete_calc: Optional[str] = None,
    itens: Optional[List[dict]] = None,
    origem_lead: Optional[str] = None,
    origem_lead_obs: Optional[str] = None,
    brindes: Optional[List[dict]] = None,
) -> HoraVenda:
    """Cria pedido de venda manual em status COTACAO ou INCOMPLETO.

    Aceita N motos via `itens=[{numero_chassi, valor_final}, ...]` (FU-3) ou,
    retrocompat, 1 moto via `numero_chassi`/`valor_final` singulares. O
    `valor_total` da venda e a SOMA dos `valor_final` de todos os itens.

    1. Valida CPF, nome, e a lista de itens (N chassis, valor>0, sem repetidos).
    2. SELECT FOR UPDATE em CADA chassi (impede 2 operadores reservando o mesmo).
    3. Resolve loja_id da venda (override do form ou loja do 1o chassi).
    4. Multi-formas (migration hora_34): aceita `pagamentos: List[dict]` com
       N formas. Compat: se nao informado mas `forma_pagamento` sim, gera
       1 pagamento sintetico com valor=valor_total.
    5. Resolve preco do modelo: se QUALQUER forma e A_PRAZO -> preco a prazo.
    6. Decide status final via `_avaliar_status_pagamento`:
       - COTACAO se pagamentos validos (soma == valor_total + AUT/ID OK).
       - INCOMPLETO senao (vendedor pode editar e completar depois).
    7. Cria HoraVenda + N HoraVendaItem + N HoraVendaPagamento.
    8. Emite evento RESERVADA por chassi mesmo em INCOMPLETO (chassi reservado).
    9. Auditoria: CRIOU.

    Args:
        numero_chassi/valor_final: legacy (1 moto). Ignorados se `itens` for
            fornecido. Sem `itens` e sem ambos -> ValueError.
        itens: lista de dicts {numero_chassi, valor_final} (N motos). Chassi
            normalizado p/ uppercase; repetido (apos normalizar) -> ValueError;
            valor_final<=0 -> ValueError.
        forma_pagamento: legacy. Quando `pagamentos` nao fornecido, gera 1
            pagamento sintetico com essa forma e valor=valor_total. Se ambos
            None, status final sera INCOMPLETO (sem forma).
        pagamentos: lista de dicts com keys forma_pagamento_hora, valor,
            numero_parcelas, aut_id. Soma deve igualar valor_total para sair
            INCOMPLETO. Pagamentos invalidos (valor<=0 ou forma vazia) sao
            descartados.
    """
    # Aceita CPF (11) ou CNPJ (14) — coluna `cpf_cliente` eh String(14) e
    # comporta ambos. Ver app/hora/services/tagplus/_documento.py.
    from app.hora.services.tagplus._documento import (
        inferir_consumidor_final,
        normalizar_documento,
    )
    cpf_norm, _tipo_doc = normalizar_documento(cpf_cliente)
    if not _tipo_doc:
        raise ValueError(
            f'Documento invalido: {cpf_cliente!r} '
            f'(esperado CPF com 11 digitos ou CNPJ com 14 digitos)'
        )

    nome_norm = (nome_cliente or '').strip()
    if not nome_norm:
        raise ValueError('Nome do cliente obrigatorio')

    # Normaliza para lista de itens (FU-3). Legado: numero_chassi/valor_final
    # singulares -> 1 item. Novo: itens=[{numero_chassi, valor_final}, ...].
    if itens is None:
        if numero_chassi is None or valor_final is None:
            raise ValueError('Informe itens=[...] ou numero_chassi/valor_final.')
        itens = [{'numero_chassi': numero_chassi, 'valor_final': valor_final}]
    itens_norm = []
    vistos: set = set()
    for it in itens:
        # Normaliza para a forma canonica (uppercase) ANTES de dedup —
        # `_lock_chassi_e_validar_disponivel` tambem normaliza p/ uppercase,
        # entao ['mi123','MI123'] sao o MESMO chassi (a tabela nao tem UNIQUE).
        ch = (it.get('numero_chassi') or '').strip().upper()
        if not ch:
            raise ValueError('Item sem chassi.')
        if ch in vistos:
            raise ValueError(f'Chassi repetido no pedido: {ch}')
        vistos.add(ch)
        vf = it.get('valor_final')
        if vf is None or Decimal(str(vf)) <= 0:
            raise ValueError(f'Valor final do chassi {ch} deve ser maior que zero')
        itens_norm.append({'numero_chassi': ch, 'valor_final': Decimal(str(vf))})
    if not itens_norm:
        raise ValueError('Pedido precisa de ao menos 1 item.')

    # valor_total = soma dos itens (sera atualizado apos flush dos itens).
    valor_total_dec = sum((it['valor_final'] for it in itens_norm), Decimal('0'))

    # Compat: se `pagamentos` nao foi fornecido mas `forma_pagamento` sim,
    # cria pagamento sintetico (1 forma com valor=valor_total). Se nem um
    # nem outro, lista fica vazia -> status final sera INCOMPLETO.
    pagamentos_norm = _normalizar_pagamentos(pagamentos)
    if not pagamentos_norm and forma_pagamento:
        forma_legacy = (forma_pagamento or '').strip().upper()
        if forma_legacy and forma_legacy != 'NAO_INFORMADO':
            pagamentos_norm = [{
                'forma_pagamento_hora': forma_legacy[:20],
                'valor': valor_total_dec,
                'numero_parcelas': max(1, int(numero_parcelas or 1)),
                'aut_id': None,
            }]

    # Forma representativa para resolucao de preco (qualquer A_PRAZO -> A_PRAZO).
    forma_para_preco = _classificar_formas_para_preco(pagamentos_norm)

    # forma_pagamento legacy (cache em HoraVenda): MISTO se >1 forma distinta;
    # senao, a unica forma; senao, 'NAO_INFORMADO'.
    formas_distintas = {p['forma_pagamento_hora'] for p in pagamentos_norm}
    if len(formas_distintas) >= 2:
        forma_norm = 'MISTO'
    elif len(formas_distintas) == 1:
        forma_norm = next(iter(formas_distintas))
    else:
        forma_norm = 'NAO_INFORMADO'

    mod_frete = (modalidade_frete or '0').strip()
    # Lojas HORA so emitem com modalidade 0 (CIF) ou 1 (FOB) — restricao
    # aplicada em 2026-05-07. Pedidos legados DANFE com modalidades 2,3,4,9
    # ficam preservados no banco mas nao podem ser GERADOS por este path.
    if mod_frete not in ('0', '1'):
        raise ValueError(
            f'modalidade_frete invalida: {modalidade_frete!r} '
            f"(esperado '0' CIF ou '1' FOB)"
        )
    valor_frete_dec, tipo_frete_norm = _normalizar_frete(
        modalidade_frete=mod_frete,
        valor_frete=valor_frete,
        tipo_frete_calc=tipo_frete_calc,
    )
    n_parcelas = int(numero_parcelas or 1)
    if n_parcelas < 1 or n_parcelas > 60:
        raise ValueError(
            f'numero_parcelas fora do intervalo 1..60: {numero_parcelas!r}'
        )
    intervalo = int(intervalo_parcelas_dias or 30)
    if intervalo < 1 or intervalo > 90:
        raise ValueError(
            f'intervalo_parcelas_dias fora do intervalo 1..90: {intervalo_parcelas_dias!r}'
        )

    # Lock + validacao de disponibilidade para TODOS os chassis (fase de
    # validacao): feito antes de criar HoraVenda para falhar cedo.
    # Guarda (moto, ult_evento) por chassi para reuse no loop de itens abaixo.
    chassis_validados: dict = {}
    for it in itens_norm:
        moto, ult = _lock_chassi_e_validar_disponivel(it['numero_chassi'])
        if not ult.loja_id:
            raise ValueError(
                f'Chassi {moto.numero_chassi} sem loja definida no ultimo evento — '
                f'investigar inconsistencia em hora_moto_evento.'
            )
        chassis_validados[moto.numero_chassi] = (moto, ult)

    # Loja oficial da venda: override do form (se fornecido) OU loja do
    # primeiro chassi (criterio arbitrario para N itens — operador deve
    # usar loja_id_override em pedidos multi-item).
    primeiro_chassi_norm = next(iter(chassis_validados))
    loja_id_chassi_primeiro = chassis_validados[primeiro_chassi_norm][1].loja_id
    loja_id = (
        int(loja_id_override) if loja_id_override is not None
        else int(loja_id_chassi_primeiro)
    )

    cep_norm = ''.join(c for c in (cep or '') if c.isdigit()) or None
    if cep_norm and len(cep_norm) != 8:
        raise ValueError(f'CEP invalido: {cep!r} (esperado 8 digitos)')
    cep_formatado = f'{cep_norm[:5]}-{cep_norm[5:]}' if cep_norm else None
    uf_norm = (endereco_uf or '').strip().upper() or None
    if uf_norm and len(uf_norm) != 2:
        raise ValueError(f'UF invalido: {endereco_uf!r} (esperado 2 letras)')

    data_venda = date.today()

    # Status final: COTACAO se pagamentos consistentes com valor_total, senao INCOMPLETO.
    # Avaliado DEPOIS de calcular valor_total (soma dos itens).
    status_final, motivos_incompleto = _avaliar_status_pagamento(
        pagamentos_norm, valor_total_dec,
    )

    origem_lead_norm, origem_lead_obs_norm = _normalizar_origem_lead(
        origem_lead, origem_lead_obs,
    )

    venda = HoraVenda(
        loja_id=loja_id,
        cpf_cliente=cpf_norm,
        nome_cliente=nome_norm[:200],
        inscricao_estadual=(inscricao_estadual or '').strip()[:20] or None,
        telefone_cliente=(telefone_cliente or '').strip()[:20] or None,
        telefone_lead=(telefone_lead or '').strip()[:20] or None,
        email_cliente=(email_cliente or '').strip()[:120] or None,
        data_venda=data_venda,
        forma_pagamento=forma_norm[:20],
        valor_total=valor_total_dec,
        nf_saida_numero=None,
        nf_saida_chave_44=None,
        nf_saida_emitida_em=None,
        arquivo_pdf_s3_key=None,
        parser_usado=None,
        parseada_em=None,
        cnpj_emitente=None,
        status=status_final,
        vendedor=(vendedor or '').strip()[:100] or None,
        observacoes=(observacoes or '').strip() or None,
        cep=cep_formatado,
        endereco_logradouro=(endereco_logradouro or '').strip()[:255] or None,
        endereco_numero=(endereco_numero or '').strip()[:20] or None,
        endereco_complemento=(endereco_complemento or '').strip()[:100] or None,
        endereco_bairro=(endereco_bairro or '').strip()[:100] or None,
        endereco_cidade=(endereco_cidade or '').strip()[:100] or None,
        endereco_uf=uf_norm,
        origem_criacao='MANUAL',
        modalidade_frete=mod_frete,
        valor_frete=valor_frete_dec,
        tipo_frete_calc=tipo_frete_norm,
        numero_parcelas=n_parcelas,
        intervalo_parcelas_dias=intervalo,
        # consumidor_final: se nao explicito, infere via tipo de documento
        # (CPF=True / CNPJ=False). Operador pode sobrescrever na tela de
        # detalhe enquanto pedido estiver em COTACAO ou CONFIRMADO.
        consumidor_final=(
            bool(consumidor_final) if consumidor_final is not None
            else inferir_consumidor_final(cpf_norm)
        ),
        criado_por_id=criado_por_id,
        origem_lead=origem_lead_norm,
        origem_lead_obs=origem_lead_obs_norm,
    )
    db.session.add(venda)
    db.session.flush()

    # Loop de itens: cria HoraVendaItem + evento RESERVADA por chassi.
    chassi_norms_criados: list[str] = []
    for it in itens_norm:
        # `numero_chassi` em itens_norm ja esta na forma canonica (uppercase),
        # coerente com as chaves de chassis_validados.
        chassi_norm = it['numero_chassi']
        valor_item_dec = it['valor_final']
        moto, ult = chassis_validados[chassi_norm]

        (
            preco_tabela_ref, desconto, desconto_pct,
            tabela_preco_id, divergencia_tipo,
        ) = _resolver_preco_tabela(
            moto.modelo_id, data_venda, valor_item_dec,
            forma_pagamento_hora=forma_para_preco,
        )

        venda_item = HoraVendaItem(
            venda_id=venda.id,
            numero_chassi=chassi_norm,
            tabela_preco_id=tabela_preco_id,
            preco_tabela_referencia=preco_tabela_ref,
            desconto_aplicado=desconto,
            desconto_percentual=desconto_pct,
            preco_final=valor_item_dec,
        )
        db.session.add(venda_item)
        db.session.flush()

        if divergencia_tipo:
            if divergencia_tipo == 'PRECO_ACIMA_TABELA':
                _registrar_divergencia(
                    venda_id=venda.id, tipo=divergencia_tipo,
                    numero_chassi=chassi_norm,
                    detalhe=(
                        f'Preco final R${valor_item_dec} > tabela vigente. '
                        'Item gravado sem desconto negativo.'
                    ),
                    valor_conferido=str(valor_item_dec),
                )
            else:
                _registrar_divergencia(
                    venda_id=venda.id, tipo=divergencia_tipo,
                    numero_chassi=chassi_norm,
                    detalhe=f'Sem HoraTabelaPreco vigente para modelo {moto.modelo_id}.',
                    valor_conferido=str(valor_item_dec),
                )

        # Evento RESERVADA: tira chassi do estoque disponivel — emitido mesmo em
        # INCOMPLETO (a reserva e' valida; a venda e' que ainda esta a completar).
        registrar_evento(
            numero_chassi=chassi_norm,
            tipo='RESERVADA',
            origem_tabela='hora_venda_item',
            origem_id=venda_item.id,
            loja_id=loja_id,
            operador=criado_por,
            detalhe=f'Pedido #{venda.id} ({status_final}) para {nome_norm} CPF {cpf_norm}',
        )
        chassi_norms_criados.append(chassi_norm)

    # Persistencia das N formas de pagamento (multi-formas).
    for p in pagamentos_norm:
        db.session.add(HoraVendaPagamento(
            venda_id=venda.id,
            forma_pagamento_hora=p['forma_pagamento_hora'],
            valor=p['valor'],
            numero_parcelas=p['numero_parcelas'],
            aut_id=p['aut_id'],
        ))
    if pagamentos_norm:
        db.session.flush()

    # Brindes do orcamento (#4a): peca prometida ja na criacao. Criados na MESMA
    # transacao (flush-only, sem commit proprio) — valem mesmo se o pedido nascer
    # INCOMPLETO. Linha invalida (peca inexistente / qtd<=0) aborta a criacao toda.
    for b in (brindes or []):
        _criar_brinde_flush_only(
            venda, peca_id=b['peca_id'], qtd=b['qtd'], usuario=criado_por,
        )

    detalhe_audit = (
        f'Pedido manual ({status_final}) chassis={",".join(chassi_norms_criados)} '
        f'cliente={nome_norm} valor_total={valor_total_dec}'
    )
    if motivos_incompleto:
        detalhe_audit += f' INCOMPLETO: {"; ".join(motivos_incompleto)}'
    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=criado_por or '',
        acao='CRIOU',
        detalhe=detalhe_audit,
    )

    db.session.commit()

    # Push pos-commit do pedido p/ TagPlus (Fase 2b — atras da flag
    # HORA_TAGPLUS_PUSH_PEDIDO, tolerante a falha: NUNCA trava a venda local).
    from app.hora.services.tagplus import pedido_sync_service
    pedido_sync_service.push_criar_pedido(venda)

    return venda


# --------------------------------------------------------------------------
# Confirmacao: COTACAO -> CONFIRMADO
# --------------------------------------------------------------------------

def confirmar_venda(venda_id: int, usuario: Optional[str] = None) -> HoraVenda:
    """Transiciona pedido de COTACAO para CONFIRMADO.

    Mantem evento RESERVADA (chassi continua reservado). Registra auditoria.
    """
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    if venda.status == VENDA_STATUS_INCOMPLETO:
        raise TransicaoInvalidaError(
            f'Pedido {venda_id} esta INCOMPLETO — complete formas de pagamento '
            f'(soma == valor total + AUT/ID quando exigido) antes de confirmar.'
        )
    if venda.status != VENDA_STATUS_COTACAO:
        raise TransicaoInvalidaError(
            f'Pedido {venda_id} esta em {venda.status}; so COTACAO pode ser confirmado.'
        )
    if venda.tem_divergencia_aberta:
        # Politica: divergencias podem ser confirmadas, mas operador deve ter
        # marcado-as como resolvidas antes (sao avisos, nao bloqueios).
        # Nao bloqueamos aqui — alinhado com fluxo permissivo do import DANFE.
        pass

    # #28 Fatia 2 + #5b: desconto acima do teto, frete (>0) e brinde BLOQUEIAM a
    # confirmacao ate aprovacao gerencial (perm aprovacoes/aprovar). Cria 1
    # solicitacao PENDENTE por gatilho e aborta.
    from app.hora.services import aprovacao_desconto_service
    pendencia = aprovacao_desconto_service.garantir_aprovacao_para_confirmar(venda, usuario)
    if pendencia:
        db.session.commit()  # persiste a(s) solicitacao(oes) PENDENTE (flush -> commit)
        raise TransicaoInvalidaError(
            f'Pendente de aprovacao do gerente antes de confirmar — {pendencia}'
        )

    # Avaria ABERTA bloqueia a confirmacao (decisao do dono 2026-06-28: bloqueio
    # na reserva + na confirmacao). Cobre o gap de moto reservada e SO DEPOIS
    # avariada. Fonte de verdade: HoraAvaria status='ABERTA'.
    chassis_pedido = [it.numero_chassi for it in venda.itens if it.numero_chassi]
    if chassis_pedido:
        from app.hora.services import avaria_service
        avariados = sorted(
            c for c, n in avaria_service.avarias_abertas_por_chassi(chassis_pedido).items() if n > 0
        )
        if avariados:
            raise TransicaoInvalidaError(
                'Nao e possivel confirmar: chassi(s) com avaria aberta — '
                + ', '.join(avariados)
                + '. Resolva em /hora/avarias antes de confirmar.'
            )

    venda.status = VENDA_STATUS_CONFIRMADO
    venda.confirmado_em = agora_utc_naive()
    venda.confirmado_por = usuario or 'desconhecido'

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='CONFIRMOU',
        detalhe=f'Pedido confirmado ({len(venda.itens)} chassi(s)).',
    )

    db.session.commit()

    try:
        from app.hora.services.tagplus.notificacao_whatsapp import enfileirar_notificacao
        enfileirar_notificacao('PEDIDO', venda.id)
    except Exception:
        import logging as _logging
        _logging.getLogger(__name__).exception(
            'Falha ao enfileirar notificacao WhatsApp pedido (venda=%s)', venda.id,
        )

    # Espelha a confirmacao no pedido TagPlus (PATCH status=B) — Fase 2b, flag, tolerante.
    from app.hora.services.tagplus import pedido_sync_service
    pedido_sync_service.push_atualizar_status(venda)

    return venda


def editar_pagamentos(
    venda_id: int,
    pagamentos: List[dict],
    usuario: Optional[str] = None,
) -> HoraVenda:
    """Substitui as formas de pagamento de uma venda e re-avalia status.

    Permitido em status INCOMPLETO ou COTACAO (vendedor completando ou
    ajustando antes de confirmar). Bloqueado em CONFIRMADO/FATURADO/CANCELADO.

    Mecanica:
      1. Apaga HoraVendaPagamento existentes da venda.
      2. Cria os novos a partir de `pagamentos` (normalizados).
      3. Re-avalia status via _avaliar_status_pagamento (INCOMPLETO ou COTACAO).
      4. Atualiza HoraVenda.forma_pagamento legacy (MISTO se >1 forma).
      5. Auditoria EDITOU_HEADER.

    Args:
        pagamentos: lista [{forma_pagamento_hora, valor, numero_parcelas, aut_id}].
    """
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    if venda.status not in (VENDA_STATUS_INCOMPLETO, VENDA_STATUS_COTACAO):
        raise TransicaoInvalidaError(
            f'Pedido {venda_id} esta em {venda.status}; pagamentos so podem ser '
            f'editados em INCOMPLETO ou COTACAO.'
        )

    novo_status, _motivos = _aplicar_pagamentos(venda, pagamentos, usuario)
    venda.status = novo_status

    db.session.commit()
    return venda


def _aplicar_pagamentos(
    venda: HoraVenda,
    pagamentos: List[dict],
    usuario: Optional[str] = None,
) -> tuple[str, List[str]]:
    """Helper FLUSH-ONLY: aplica os pagamentos a uma venda (sem commit).

    Apaga os HoraVendaPagamento existentes, recria a partir de `pagamentos`
    (normalizados), recalcula o cache `forma_pagamento` legacy e registra a
    auditoria EDITOU_HEADER. NAO faz commit, NAO seta `venda.status` e NAO
    valida o guard de status permitido — isso fica a cargo do caller (wrapper
    publico `editar_pagamentos` ou orquestrador `salvar_pedido_completo`).

    Returns:
        (novo_status, motivos): avaliacao de status conforme os pagamentos
        aplicados. O caller decide se/quando seta `venda.status`.
    """
    pagamentos_norm = _normalizar_pagamentos(pagamentos)
    valor_total_dec = Decimal(str(venda.valor_total))

    novo_status, motivos = _avaliar_status_pagamento(pagamentos_norm, valor_total_dec)

    # Apaga pagamentos atuais e recria.
    HoraVendaPagamento.query.filter_by(venda_id=venda.id).delete()
    db.session.flush()
    for p in pagamentos_norm:
        db.session.add(HoraVendaPagamento(
            venda_id=venda.id,
            forma_pagamento_hora=p['forma_pagamento_hora'],
            valor=p['valor'],
            numero_parcelas=p['numero_parcelas'],
            aut_id=p['aut_id'],
        ))

    # forma_pagamento legacy (cache).
    formas_distintas = {p['forma_pagamento_hora'] for p in pagamentos_norm}
    if len(formas_distintas) >= 2:
        venda.forma_pagamento = 'MISTO'
    elif len(formas_distintas) == 1:
        venda.forma_pagamento = next(iter(formas_distintas))[:20]
    else:
        venda.forma_pagamento = 'NAO_INFORMADO'

    status_antes = venda.status
    detalhe = (
        f'Pagamentos editados: {len(pagamentos_norm)} forma(s). '
        f'Status {status_antes}->{novo_status}.'
    )
    if motivos:
        detalhe += ' Motivos INCOMPLETO: ' + '; '.join(motivos)
    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='EDITOU_HEADER',
        campo_alterado='pagamentos',
        detalhe=detalhe,
    )

    return novo_status, motivos


def voltar_para_cotacao(venda_id: int, usuario: Optional[str] = None) -> HoraVenda:
    """Reverte CONFIRMADO -> COTACAO para permitir edicao de itens.

    Bloqueado se houver emissao TagPlus em estado em-voo ou aprovada — nesses
    casos cancele a NFe primeiro. Registra auditoria.
    """
    from app.hora.models.tagplus import HoraTagPlusNfeEmissao

    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    if venda.status != VENDA_STATUS_CONFIRMADO:
        raise TransicaoInvalidaError(
            f'Pedido {venda_id} esta em {venda.status}; so CONFIRMADO pode voltar para COTACAO.'
        )

    emissao = HoraTagPlusNfeEmissao.query.filter_by(venda_id=venda.id).first()
    estados_bloqueio = (
        'EM_ENVIO', 'ENVIADA_SEFAZ', 'APROVADA',
        'CANCELAMENTO_SOLICITADO',
    )
    if emissao and emissao.status in estados_bloqueio:
        raise TransicaoInvalidaError(
            f'Pedido tem emissao NFe em status {emissao.status}; '
            f'cancele a NFe na SEFAZ antes de voltar para cotacao.'
        )

    venda.status = VENDA_STATUS_COTACAO
    venda.confirmado_em = None
    venda.confirmado_por = None

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='VOLTOU_PARA_COTACAO',
        detalhe='Pedido revertido CONFIRMADO -> COTACAO para edicao.',
    )

    db.session.commit()
    return venda


# --------------------------------------------------------------------------
# Edicao do header (vendedor, contato, endereco, observacoes, forma_pagamento)
# --------------------------------------------------------------------------

# Campos editaveis em cada status. FATURADO so permite observacoes.
# INCOMPLETO usa o mesmo conjunto de COTACAO — pedido em INCOMPLETO precisa
# ser livremente editavel para o vendedor corrigir cliente/endereco/etc.
# antes de promover via editar_pagamentos.
_CAMPOS_COTACAO_FULL = {
    'vendedor', 'forma_pagamento', 'telefone_cliente', 'telefone_lead',
    'email_cliente',
    'observacoes', 'nome_cliente', 'cpf_cliente', 'inscricao_estadual',
    'cep', 'endereco_logradouro', 'endereco_numero', 'endereco_complemento',
    'endereco_bairro', 'endereco_cidade', 'endereco_uf',
    'modalidade_frete', 'numero_parcelas', 'intervalo_parcelas_dias',
    'consumidor_final',
    # Frete CIF (migration hora_38) — UI mostra apenas com modalidade='0'.
    'valor_frete', 'tipo_frete_calc',
    # Origem do lead (roadmap #6) — editavel enquanto em COTACAO/INCOMPLETO.
    'origem_lead', 'origem_lead_obs',
}
_CAMPOS_EDITAVEIS_HEADER = {
    VENDA_STATUS_INCOMPLETO: _CAMPOS_COTACAO_FULL,
    VENDA_STATUS_COTACAO: _CAMPOS_COTACAO_FULL,
    VENDA_STATUS_CONFIRMADO: {
        'vendedor', 'forma_pagamento', 'telefone_cliente', 'telefone_lead',
        'email_cliente',
        'observacoes',
        'cep', 'endereco_logradouro', 'endereco_numero', 'endereco_complemento',
        'endereco_bairro', 'endereco_cidade', 'endereco_uf',
        'modalidade_frete', 'numero_parcelas', 'intervalo_parcelas_dias',
        # consumidor_final permanece editavel ate FATURADO porque influencia
        # diretamente o payload da NFe ainda nao enviada.
        'consumidor_final',
        # Frete CIF — auditoria/calculo de comissao depende; permitido em
        # CONFIRMADO porque ainda nao foi gerado o registro fiscal.
        'valor_frete', 'tipo_frete_calc',
    },
    VENDA_STATUS_FATURADO: {'observacoes'},
    VENDA_STATUS_CANCELADO: set(),
}


def _validar_campo_editavel(venda: HoraVenda, campo: str) -> None:
    permitidos = _CAMPOS_EDITAVEIS_HEADER.get(venda.status, set())
    if campo not in permitidos:
        raise TransicaoInvalidaError(
            f'Campo {campo!r} nao pode ser editado em pedido {venda.status}. '
            f'Campos permitidos: {sorted(permitidos) or "(nenhum)"}'
        )
    # Defesa adicional: se ha NFe em-voo, bloqueia edicao livre.
    emissao = _emissao_nfe(venda.id)
    if emissao and emissao.status in _NFE_EM_VOO and campo != 'observacoes':
        raise TransicaoInvalidaError(
            f'NFe em estado {emissao.status} — apenas observacoes editaveis.'
        )


def editar_venda(
    venda_id: int,
    vendedor: Optional[str] = None,
    forma_pagamento: Optional[str] = None,
    telefone_cliente: Optional[str] = None,
    email_cliente: Optional[str] = None,
    observacoes: Optional[str] = None,
    nome_cliente: Optional[str] = None,
    cpf_cliente: Optional[str] = None,
    inscricao_estadual: Optional[str] = None,
    cep: Optional[str] = None,
    endereco_logradouro: Optional[str] = None,
    endereco_numero: Optional[str] = None,
    endereco_complemento: Optional[str] = None,
    endereco_bairro: Optional[str] = None,
    endereco_cidade: Optional[str] = None,
    endereco_uf: Optional[str] = None,
    modalidade_frete: Optional[str] = None,
    numero_parcelas: Optional[int] = None,
    intervalo_parcelas_dias: Optional[int] = None,
    consumidor_final: Optional[bool] = None,
    valor_frete=None,
    tipo_frete_calc: Optional[str] = None,
    usuario: Optional[str] = None,
) -> HoraVenda:
    """Edita campos do header conforme regra por status.

    - COTACAO: tudo (incluindo cliente/endereco e consumidor_final).
    - CONFIRMADO: contato/endereco/operacionais + consumidor_final (sem mexer
      em CPF/nome — sao do payload TagPlus).
    - FATURADO: so observacoes.
    - CANCELADO: nada (raise).
    """
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')

    dados = {
        'vendedor': vendedor,
        'forma_pagamento': forma_pagamento,
        'telefone_cliente': telefone_cliente,
        'email_cliente': email_cliente,
        'observacoes': observacoes,
        'nome_cliente': nome_cliente,
        'cpf_cliente': cpf_cliente,
        'inscricao_estadual': inscricao_estadual,
        'cep': cep,
        'endereco_logradouro': endereco_logradouro,
        'endereco_numero': endereco_numero,
        'endereco_complemento': endereco_complemento,
        'endereco_bairro': endereco_bairro,
        'endereco_cidade': endereco_cidade,
        'endereco_uf': endereco_uf,
        'modalidade_frete': modalidade_frete,
        'numero_parcelas': numero_parcelas,
        'intervalo_parcelas_dias': intervalo_parcelas_dias,
        'consumidor_final': consumidor_final,
        'valor_frete': valor_frete,
        'tipo_frete_calc': tipo_frete_calc,
    }
    _aplicar_header(venda, dados, usuario)

    db.session.commit()
    return venda


def _aplicar_header(
    venda: HoraVenda,
    dados: dict,
    usuario: Optional[str] = None,
) -> HoraVenda:
    """Helper FLUSH-ONLY: aplica os campos do header a uma venda (sem commit).

    Recebe a venda ja buscada e um `dados` dict (mesmas chaves que os kwargs de
    `editar_venda`: vendedor, forma_pagamento, ..., valor_frete, tipo_frete_calc).
    Para cada campo nao-None: normaliza, valida pela matriz `_CAMPOS_EDITAVEIS_HEADER`
    (via `_validar_campo_editavel`, que tambem aplica a defesa NFe-em-voo), faz
    setattr e registra auditoria EDITOU_HEADER. NAO faz commit — fica a cargo do
    caller (wrapper publico `editar_venda` ou orquestrador `salvar_pedido_completo`).

    Regras por status (mesmas de antes):
    - COTACAO/INCOMPLETO: tudo (incluindo cliente/endereco e consumidor_final).
    - CONFIRMADO: contato/endereco/operacionais + consumidor_final.
    - FATURADO: so observacoes.
    - CANCELADO: nada (raise).
    """
    if venda.status == VENDA_STATUS_CANCELADO:
        raise TransicaoInvalidaError('Pedido cancelado nao pode ser editado.')

    vendedor = dados.get('vendedor')
    forma_pagamento = dados.get('forma_pagamento')
    telefone_cliente = dados.get('telefone_cliente')
    telefone_lead = dados.get('telefone_lead')
    email_cliente = dados.get('email_cliente')
    observacoes = dados.get('observacoes')
    nome_cliente = dados.get('nome_cliente')
    cpf_cliente = dados.get('cpf_cliente')
    cep = dados.get('cep')
    endereco_logradouro = dados.get('endereco_logradouro')
    endereco_numero = dados.get('endereco_numero')
    endereco_complemento = dados.get('endereco_complemento')
    endereco_bairro = dados.get('endereco_bairro')
    endereco_cidade = dados.get('endereco_cidade')
    endereco_uf = dados.get('endereco_uf')
    modalidade_frete = dados.get('modalidade_frete')
    numero_parcelas = dados.get('numero_parcelas')
    intervalo_parcelas_dias = dados.get('intervalo_parcelas_dias')
    consumidor_final = dados.get('consumidor_final')
    valor_frete = dados.get('valor_frete')
    tipo_frete_calc = dados.get('tipo_frete_calc')
    origem_lead = dados.get('origem_lead')
    origem_lead_obs = dados.get('origem_lead_obs')
    inscricao_estadual = dados.get('inscricao_estadual')

    def _atualizar(campo: str, novo_valor):
        antes = getattr(venda, campo)
        if novo_valor == antes:
            return
        _validar_campo_editavel(venda, campo)
        setattr(venda, campo, novo_valor)
        venda_audit.registrar_auditoria(
            venda_id=venda.id, usuario=usuario or '',
            acao='EDITOU_HEADER',
            campo_alterado=campo,
            valor_antes=antes,
            valor_depois=novo_valor,
        )

    if vendedor is not None:
        _atualizar('vendedor', (vendedor.strip()[:100] or None))
    if forma_pagamento is not None:
        fp_norm = (forma_pagamento or '').strip().upper() or 'NAO_INFORMADO'
        _atualizar('forma_pagamento', fp_norm[:20])
    if telefone_cliente is not None:
        _atualizar('telefone_cliente', telefone_cliente.strip()[:20] or None)
    if telefone_lead is not None:
        _atualizar('telefone_lead', telefone_lead.strip()[:20] or None)
    if email_cliente is not None:
        _atualizar('email_cliente', email_cliente.strip()[:120] or None)
    if observacoes is not None:
        _atualizar('observacoes', observacoes.strip() or None)
    if nome_cliente is not None:
        _atualizar('nome_cliente', nome_cliente.strip()[:200] or venda.nome_cliente)
    if cpf_cliente is not None:
        # Aceita CPF (11) ou CNPJ (14). String vazia mantem valor anterior.
        from app.hora.services.tagplus._documento import normalizar_documento
        cpf_norm, _tipo_doc = normalizar_documento(cpf_cliente)
        if cpf_norm and not _tipo_doc:
            raise ValueError(
                f'Documento invalido: {cpf_cliente!r} '
                f'(esperado CPF com 11 digitos ou CNPJ com 14 digitos)'
            )
        _atualizar('cpf_cliente', cpf_norm or venda.cpf_cliente)
    if inscricao_estadual is not None:
        # Registro/exibicao (nao vai para a NFe). Texto livre curto: numero da
        # IE ou "ISENTO". Vazio limpa o campo.
        _atualizar('inscricao_estadual', inscricao_estadual.strip()[:20] or None)
    if cep is not None:
        cep_norm = ''.join(c for c in cep if c.isdigit()) or None
        if cep_norm and len(cep_norm) != 8:
            raise ValueError(f'CEP invalido: {cep!r}')
        _atualizar('cep', f'{cep_norm[:5]}-{cep_norm[5:]}' if cep_norm else None)
    if endereco_logradouro is not None:
        _atualizar('endereco_logradouro', endereco_logradouro.strip()[:255] or None)
    if endereco_numero is not None:
        _atualizar('endereco_numero', endereco_numero.strip()[:20] or None)
    if endereco_complemento is not None:
        _atualizar('endereco_complemento', endereco_complemento.strip()[:100] or None)
    if endereco_bairro is not None:
        _atualizar('endereco_bairro', endereco_bairro.strip()[:100] or None)
    if endereco_cidade is not None:
        _atualizar('endereco_cidade', endereco_cidade.strip()[:100] or None)
    if endereco_uf is not None:
        uf_norm = endereco_uf.strip().upper() or None
        if uf_norm and len(uf_norm) != 2:
            raise ValueError(f'UF invalido: {endereco_uf!r}')
        _atualizar('endereco_uf', uf_norm)
    if modalidade_frete is not None:
        mod_norm = (modalidade_frete or '').strip()
        # Restricao 2026-05-07: edicao so aceita 0 (CIF) ou 1 (FOB).
        # Vendas legadas com 2,3,4,9 mantem o valor no banco se o operador
        # nao mexer no campo (pois `if modalidade_frete is not None` so
        # entra quando o form envia o campo); ao salvar uma edicao com
        # qualquer outro valor, a request e rejeitada.
        if mod_norm not in ('0', '1'):
            raise ValueError(
                f'modalidade_frete invalida: {modalidade_frete!r} '
                f"(esperado '0' CIF ou '1' FOB)"
            )
        _atualizar('modalidade_frete', mod_norm)
    if numero_parcelas is not None:
        try:
            n = int(numero_parcelas)
        except (TypeError, ValueError):
            raise ValueError(f'numero_parcelas invalido: {numero_parcelas!r}')
        if n < 1 or n > 60:
            raise ValueError(
                f'numero_parcelas fora do intervalo 1..60: {n}'
            )
        _atualizar('numero_parcelas', n)
    if intervalo_parcelas_dias is not None:
        try:
            d = int(intervalo_parcelas_dias)
        except (TypeError, ValueError):
            raise ValueError(
                f'intervalo_parcelas_dias invalido: {intervalo_parcelas_dias!r}'
            )
        if d < 1 or d > 90:
            raise ValueError(
                f'intervalo_parcelas_dias fora do intervalo 1..90: {d}'
            )
        _atualizar('intervalo_parcelas_dias', d)
    if consumidor_final is not None:
        _atualizar('consumidor_final', bool(consumidor_final))

    # Frete CIF (hora_38): edita os 2 campos como bloco coerente. Se um
    # dos dois e fornecido, normaliza ambos contra a modalidade efetiva
    # (a vigente apos um eventual _atualizar('modalidade_frete', ...) acima).
    if valor_frete is not None or tipo_frete_calc is not None:
        modalidade_efetiva = venda.modalidade_frete
        valor_dec_norm, tipo_norm = _normalizar_frete(
            modalidade_frete=modalidade_efetiva,
            valor_frete=valor_frete if valor_frete is not None else venda.valor_frete,
            tipo_frete_calc=(
                tipo_frete_calc if tipo_frete_calc is not None else venda.tipo_frete_calc
            ),
        )
        _atualizar('valor_frete', valor_dec_norm)
        _atualizar('tipo_frete_calc', tipo_norm)

    # Origem do lead (roadmap #6): os 2 campos sao acoplados (OUTROS exige obs).
    # Resolve juntos para validar a regra; usa o valor atual como fallback
    # quando so um dos campos vem no form.
    if origem_lead is not None or origem_lead_obs is not None:
        origem_in = origem_lead if origem_lead is not None else venda.origem_lead
        obs_in = (
            origem_lead_obs if origem_lead_obs is not None else venda.origem_lead_obs
        )
        origem_norm, obs_norm = _normalizar_origem_lead(origem_in, obs_in)
        _atualizar('origem_lead', origem_norm)
        _atualizar('origem_lead_obs', obs_norm)

    return venda


def _aplicar_itens(
    venda: HoraVenda,
    itens: List[dict],
    usuario: Optional[str] = None,
    forma_para_preco: Optional[str] = None,
) -> HoraVenda:
    """Helper FLUSH-ONLY: reconcilia (diff) os itens-moto de uma venda (sem commit).

    Recebe a venda ja buscada e a lista DESEJADA de itens; cada dict tem as
    chaves:
        item_id: int | None  (None = linha nova; preenchido = item existente)
        numero_chassi: str    (so usado em linha nova; troca de chassi de item
                               existente e IGNORADA — a rota nunca troca chassi)
        valor_final: Decimal  (preco final desejado)

    Algoritmo de diff (reusa os MESMOS padroes de adicionar/remover/editar_item):
      - Guard "nao remove o ultimo": se o resultado final teria 0 itens
        (lista vazia ou todos removidos) -> ValueError ANTES de mutar (sem
        estado parcial).
      - Remove (DEVOLVIDA + delete) cada item existente cujo id nao esta na lista.
      - Para item existente: se valor_final mudou, re-resolve preco da tabela
        (sem troca de chassi).
      - Para linha nova (item_id None): lock pessimista no chassi, valida loja,
        cria HoraVendaItem + flush + evento RESERVADA.

    NAO faz commit, NAO seta venda.status nem recalcula valor_total — isso fica
    a cargo do caller (orquestrador salvar_pedido_completo).

    `forma_para_preco`: forma representativa A_VISTA/A_PRAZO usada para resolver o
    preco de tabela dos itens. Quando None, usa o cache `venda.forma_pagamento`
    (compat). O caller passa a forma representativa dos pagamentos SUBMETIDOS
    (nao a forma_pagamento antiga do header) para evitar o "desconto-fantasma":
    item precificado com a forma antiga enquanto o operador trocou para outra
    (ex.: cache 'MISTO' resolvia A_VISTA, mas o pagamento e A_PRAZO).
    """
    forma_preco = (
        forma_para_preco if forma_para_preco is not None else venda.forma_pagamento
    )
    existentes = {it.id: it for it in venda.itens}
    ids_submetidos = {i['item_id'] for i in itens if i.get('item_id')}

    # Guard "nao remove o ultimo": calcula a contagem final ANTES de mutar.
    # remanescentes = itens existentes que continuam + linhas novas.
    n_remanescentes = sum(1 for iid in existentes if iid in ids_submetidos)
    n_novos = sum(1 for i in itens if not i.get('item_id'))
    if (n_remanescentes + n_novos) < 1:
        raise ValueError('Pedido precisa de ao menos 1 item.')

    # 1) Remover: item existente cujo id NAO esta na lista submetida.
    for iid, item in list(existentes.items()):
        if iid in ids_submetidos:
            continue
        devolver_ao_estoque(
            numero_chassi=item.numero_chassi,
            origem_tabela='hora_venda_item',
            origem_id=item.id,
            loja_id=venda.loja_id,
            operador=usuario,
            detalhe=f'Item removido do pedido #{venda.id} (salvar pedido)',
        )
        venda_audit.registrar_auditoria(
            venda_id=venda.id, usuario=usuario or '',
            acao='REMOVEU_ITEM', item_id=item.id,
            detalhe=f'chassi={item.numero_chassi} valor={item.preco_final}',
        )
        db.session.delete(item)
    db.session.flush()

    # 2) Atualizar existentes + criar novos.
    for entrada in itens:
        item_id = entrada.get('item_id')
        # Defesa em profundidade: item_id preenchido que NAO pertence a esta venda
        # e payload invalido (o front so envia item_id de itens reais). Sem este
        # guard, cairia no ramo "linha nova" e tentaria lockar o chassi.
        if item_id and item_id not in existentes:
            raise ValueError(f'item_id {item_id} nao pertence ao pedido #{venda.id}.')
        # Valida o valor cedo: sem isto, Decimal(str(None)) levanta InvalidOperation
        # (NAO subclasse de ValueError) e a rota retornaria HTTP 500 em vez de flash.
        if entrada.get('valor_final') is None:
            raise ValueError('Item sem valor final.')
        if item_id and item_id in existentes:
            # Item existente: so re-resolve preco se o valor_final mudou.
            # Sem troca de chassi (a rota nao troca chassi de item existente).
            item = existentes[item_id]
            valor_alvo = Decimal(str(entrada.get('valor_final')))
            valor_atual = Decimal(str(item.preco_final))
            if valor_alvo <= 0:
                raise ValueError('Valor final deve ser maior que zero')
            if valor_alvo != valor_atual:
                moto = HoraMoto.query.get(item.numero_chassi)
                if moto:
                    preco_ref, desconto, desconto_pct, tabela_id, _ = _resolver_preco_tabela(
                        moto.modelo_id, venda.data_venda, valor_alvo,
                        forma_pagamento_hora=forma_preco,
                    )
                    item.tabela_preco_id = tabela_id
                    item.preco_tabela_referencia = preco_ref
                    item.desconto_aplicado = desconto
                    item.desconto_percentual = desconto_pct
                item.preco_final = valor_alvo
                venda_audit.registrar_auditoria(
                    venda_id=venda.id, usuario=usuario or '',
                    acao='EDITOU_ITEM', item_id=item.id,
                    campo_alterado='preco_final',
                    valor_antes=valor_atual, valor_depois=valor_alvo,
                )
        else:
            # Linha nova: lock + validacao de loja + RESERVADA (igual adicionar_item_pedido).
            valor_final_dec = Decimal(str(entrada.get('valor_final')))
            if valor_final_dec <= 0:
                raise ValueError('Valor final deve ser maior que zero')
            moto, ult = _lock_chassi_e_validar_disponivel(entrada.get('numero_chassi') or '')
            chassi_norm = moto.numero_chassi
            if ult.loja_id and venda.loja_id and ult.loja_id != venda.loja_id:
                raise ValueError(
                    f'Chassi {chassi_norm} esta na loja {ult.loja_id}, mas pedido e da '
                    f'loja {venda.loja_id} — adicione um chassi da mesma loja.'
                )
            preco_ref, desconto, desconto_pct, tabela_id, _ = _resolver_preco_tabela(
                moto.modelo_id, venda.data_venda, valor_final_dec,
                forma_pagamento_hora=forma_preco,
            )
            item = HoraVendaItem(
                venda_id=venda.id,
                numero_chassi=chassi_norm,
                tabela_preco_id=tabela_id,
                preco_tabela_referencia=preco_ref,
                desconto_aplicado=desconto,
                desconto_percentual=desconto_pct,
                preco_final=valor_final_dec,
            )
            db.session.add(item)
            db.session.flush()
            registrar_evento(
                numero_chassi=chassi_norm,
                tipo='RESERVADA',
                origem_tabela='hora_venda_item',
                origem_id=item.id,
                loja_id=venda.loja_id or ult.loja_id,
                operador=usuario,
                detalhe=f'Pedido #{venda.id} item adicionado (salvar pedido)',
            )
            venda_audit.registrar_auditoria(
                venda_id=venda.id, usuario=usuario or '',
                acao='ADICIONOU_ITEM', item_id=item.id,
                detalhe=f'chassi={chassi_norm} valor={valor_final_dec}',
            )

    db.session.flush()
    return venda


def salvar_pedido_completo(
    venda_id: int,
    header: dict,
    itens: List[dict],
    pagamentos: List[dict],
    usuario: Optional[str] = None,
) -> HoraVenda:
    """Orquestrador FU-5: reconcilia header + itens + pagamentos numa UNICA transacao.

    Compoe os helpers flush-only `_aplicar_header`, `_aplicar_itens` e
    `_aplicar_pagamentos` e faz o UNICO commit ao final. Itens e pagamentos so
    sao reconciliados em INCOMPLETO/COTACAO; em CONFIRMADO+ apenas o header e
    aplicado (matriz `_CAMPOS_EDITAVEIS_HEADER`) e o status fica intacto (nao
    derruba CONFIRMADO/FATURADO).

    - Header: sempre aplicado (validado pela matriz por status).
    - Itens: reconciliados (diff) em INCOMPLETO ou COTACAO (decisao 2026-06-25:
      o operador pode trocar/remover/adicionar moto enquanto o pedido nao foi
      confirmado — antes era so COTACAO, o que travava pedidos INCOMPLETOS).
    - Pagamentos + valor_total + status: recalculados em INCOMPLETO/COTACAO.
    """
    venda = HoraVenda.query.get(venda_id)
    if venda is None:
        raise ValueError('Venda nao encontrada.')

    _aplicar_header(venda, header or {}, usuario)
    status_inicial = venda.status

    if status_inicial in (VENDA_STATUS_INCOMPLETO, VENDA_STATUS_COTACAO):
        # Forma representativa dos pagamentos SUBMETIDOS (qualquer A_PRAZO -> a
        # prazo) para precificar os itens de forma coerente com a tela, em vez
        # da forma_pagamento antiga do cache (evita desconto-fantasma). Considera
        # as formas SELECIONADAS independentemente do valor ja digitado — uma
        # forma a prazo com valor ainda em branco precifica a prazo (o JS faz o
        # mesmo: le o tipo do <select>, nao o valor); _normalizar_pagamentos
        # descartaria a linha de valor<=0 e cairia no fallback A_VISTA.
        forma_para_preco = _classificar_formas_para_preco([
            {'forma_pagamento_hora': (p.get('forma_pagamento_hora') or '').strip().upper()}
            for p in (pagamentos or [])
            if (p.get('forma_pagamento_hora') or '').strip()
        ])
        _aplicar_itens(
            venda, itens or [], usuario, forma_para_preco=forma_para_preco,
        )
        # _aplicar_itens fez delete()/add() via db.session (NAO mutou a colecao
        # venda.itens em memoria) + flush. Expira a colecao para o sum() abaixo
        # refletir o estado real do banco (sem o item removido, com o novo).
        db.session.expire(venda, ['itens'])

        # valor_total recalculado a partir dos itens ANTES de aplicar os
        # pagamentos — _aplicar_pagamentos avalia o status contra venda.valor_total,
        # entao o total precisa estar correto primeiro.
        venda.valor_total = sum((it.preco_final for it in venda.itens), Decimal('0'))
        novo_status, _motivos = _aplicar_pagamentos(venda, pagamentos or [], usuario)
        venda.status = novo_status

    db.session.commit()

    # Push pos-commit (idempotente: no-op se ja tem tagplus_pedido_id) — cobre
    # vendas criadas antes da flag ligar. Fase 2b, atras da flag, tolerante.
    from app.hora.services.tagplus import pedido_sync_service
    pedido_sync_service.push_criar_pedido(venda)

    return venda


# --------------------------------------------------------------------------
# Edicao de itens — so em COTACAO
# --------------------------------------------------------------------------

def _exigir_cotacao(venda: HoraVenda, acao: str) -> None:
    if venda.status != VENDA_STATUS_COTACAO:
        raise TransicaoInvalidaError(
            f'{acao} so e permitido em pedido COTACAO (atual: {venda.status}).'
        )


def _exigir_cotacao_ou_incompleto(venda: HoraVenda, acao: str) -> None:
    """Mesma janela de edicao dos ITENS (pedido nasce INCOMPLETO sem pagamento/AUT).

    CONFIRMADO/FATURADO ficam de fora de proposito: o brinde dispara aprovacao
    gerencial avaliada na confirmacao (#5b), entao mexer no brinde depois de
    confirmar furaria esse gate.
    """
    if venda.status not in (VENDA_STATUS_COTACAO, VENDA_STATUS_INCOMPLETO):
        raise TransicaoInvalidaError(
            f'{acao} so e permitido em pedido INCOMPLETO ou COTACAO '
            f'(atual: {venda.status}).'
        )


def adicionar_item_pedido(
    venda_id: int,
    numero_chassi: str,
    valor_final: Decimal,
    usuario: Optional[str] = None,
) -> HoraVendaItem:
    """Adiciona item ao pedido em COTACAO. Lock pessimista no chassi."""
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    _exigir_cotacao(venda, 'Adicionar item')

    if valor_final is None or Decimal(valor_final) <= 0:
        raise ValueError('Valor final deve ser maior que zero')

    moto, ult = _lock_chassi_e_validar_disponivel(numero_chassi)
    chassi_norm = moto.numero_chassi
    if ult.loja_id and venda.loja_id and ult.loja_id != venda.loja_id:
        raise ValueError(
            f'Chassi {chassi_norm} esta na loja {ult.loja_id}, mas pedido e da '
            f'loja {venda.loja_id} — adicione um chassi da mesma loja.'
        )

    valor_final_dec = Decimal(str(valor_final))
    preco_ref, desconto, desconto_pct, tabela_id, _ = _resolver_preco_tabela(
        moto.modelo_id, venda.data_venda, valor_final_dec,
        forma_pagamento_hora=venda.forma_pagamento,
    )

    item = HoraVendaItem(
        venda_id=venda.id,
        numero_chassi=chassi_norm,
        tabela_preco_id=tabela_id,
        preco_tabela_referencia=preco_ref,
        desconto_aplicado=desconto,
        desconto_percentual=desconto_pct,
        preco_final=valor_final_dec,
    )
    db.session.add(item)
    db.session.flush()

    registrar_evento(
        numero_chassi=chassi_norm,
        tipo='RESERVADA',
        origem_tabela='hora_venda_item',
        origem_id=item.id,
        loja_id=venda.loja_id or ult.loja_id,
        operador=usuario,
        detalhe=f'Pedido #{venda.id} item adicionado',
    )

    # Atualiza valor_total (header).
    venda.valor_total = Decimal(str(venda.valor_total)) + valor_final_dec

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='ADICIONOU_ITEM', item_id=item.id,
        detalhe=f'chassi={chassi_norm} valor={valor_final_dec}',
    )

    db.session.commit()
    return item


def remover_item_pedido(
    venda_id: int,
    item_id: int,
    usuario: Optional[str] = None,
) -> HoraVenda:
    """Remove item do pedido em COTACAO. Emite evento DEVOLVIDA no chassi."""
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    _exigir_cotacao(venda, 'Remover item')

    item = HoraVendaItem.query.get(item_id)
    if not item or item.venda_id != venda.id:
        raise ValueError(f'Item {item_id} nao pertence ao pedido {venda_id}')

    if len(venda.itens) <= 1:
        raise ValueError('Pedido deve ter ao menos 1 item — cancele o pedido em vez de remover o ultimo item.')

    chassi = item.numero_chassi
    valor_removido = Decimal(str(item.preco_final))

    # Devolve chassi ao estoque (re-emite o estado-em-estoque anterior).
    devolver_ao_estoque(
        numero_chassi=chassi,
        origem_tabela='hora_venda_item',
        origem_id=item.id,
        loja_id=venda.loja_id,
        operador=usuario,
        detalhe=f'Item removido do pedido #{venda.id} (COTACAO)',
    )

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='REMOVEU_ITEM', item_id=item.id,
        detalhe=f'chassi={chassi} valor={valor_removido}',
    )

    db.session.delete(item)
    venda.valor_total = Decimal(str(venda.valor_total)) - valor_removido

    db.session.commit()
    return venda


def editar_item_pedido(
    venda_id: int,
    item_id: int,
    novo_chassi: Optional[str] = None,
    novo_valor: Optional[Decimal] = None,
    usuario: Optional[str] = None,
) -> HoraVendaItem:
    """Edita item: troca chassi e/ou ajusta preco. So em COTACAO.

    Trocar chassi: emite DEVOLVIDA no antigo + RESERVADA no novo (com lock).
    """
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    _exigir_cotacao(venda, 'Editar item')

    item = HoraVendaItem.query.get(item_id)
    if not item or item.venda_id != venda.id:
        raise ValueError(f'Item {item_id} nao pertence ao pedido {venda_id}')

    chassi_atual = item.numero_chassi
    valor_atual = Decimal(str(item.preco_final))

    chassi_alvo = (novo_chassi or '').strip().upper() or None
    valor_alvo = Decimal(str(novo_valor)) if novo_valor is not None else None

    if not chassi_alvo and valor_alvo is None:
        return item  # nada a fazer

    if valor_alvo is not None and valor_alvo <= 0:
        raise ValueError('Valor final deve ser maior que zero')

    # Troca de chassi.
    if chassi_alvo and chassi_alvo != chassi_atual:
        moto, ult = _lock_chassi_e_validar_disponivel(chassi_alvo)
        if ult.loja_id and venda.loja_id and ult.loja_id != venda.loja_id:
            raise ValueError(
                f'Chassi {chassi_alvo} esta na loja {ult.loja_id}; pedido e da '
                f'loja {venda.loja_id}.'
            )
        # Devolve antigo ao estoque (re-emite o estado-em-estoque anterior).
        devolver_ao_estoque(
            numero_chassi=chassi_atual,
            origem_tabela='hora_venda_item',
            origem_id=item.id,
            loja_id=venda.loja_id,
            operador=usuario,
            detalhe=f'Substituido por {chassi_alvo} no pedido #{venda.id}',
        )
        # Reserva novo.
        registrar_evento(
            numero_chassi=chassi_alvo,
            tipo='RESERVADA',
            origem_tabela='hora_venda_item',
            origem_id=item.id,
            loja_id=venda.loja_id or ult.loja_id,
            operador=usuario,
            detalhe=f'Substituido a partir de {chassi_atual} no pedido #{venda.id}',
        )
        venda_audit.registrar_auditoria(
            venda_id=venda.id, usuario=usuario or '',
            acao='EDITOU_ITEM', item_id=item.id,
            campo_alterado='numero_chassi',
            valor_antes=chassi_atual, valor_depois=chassi_alvo,
        )
        item.numero_chassi = chassi_alvo
        # Re-resolve preco_tabela com modelo do novo chassi.
        preco_ref, desconto, desconto_pct, tabela_id, _ = _resolver_preco_tabela(
            moto.modelo_id, venda.data_venda, valor_alvo or valor_atual,
            forma_pagamento_hora=venda.forma_pagamento,
        )
        item.tabela_preco_id = tabela_id
        item.preco_tabela_referencia = preco_ref
        item.desconto_aplicado = desconto
        item.desconto_percentual = desconto_pct

    # Mudanca de valor.
    if valor_alvo is not None and valor_alvo != valor_atual:
        # Re-resolve preco_tabela apenas para ajustar desconto (mesmo modelo).
        moto = HoraMoto.query.get(item.numero_chassi)
        if moto:
            preco_ref, desconto, desconto_pct, tabela_id, _ = _resolver_preco_tabela(
                moto.modelo_id, venda.data_venda, valor_alvo,
                forma_pagamento_hora=venda.forma_pagamento,
            )
            item.tabela_preco_id = tabela_id
            item.preco_tabela_referencia = preco_ref
            item.desconto_aplicado = desconto
            item.desconto_percentual = desconto_pct
        item.preco_final = valor_alvo
        venda.valor_total = Decimal(str(venda.valor_total)) - valor_atual + valor_alvo
        venda_audit.registrar_auditoria(
            venda_id=venda.id, usuario=usuario or '',
            acao='EDITOU_ITEM', item_id=item.id,
            campo_alterado='preco_final',
            valor_antes=valor_atual, valor_depois=valor_alvo,
        )

    db.session.commit()
    return item


# --------------------------------------------------------------------------
# Cancelamento de pedido
# --------------------------------------------------------------------------

def cancelar_venda(
    venda_id: int,
    motivo: str,
    usuario: Optional[str] = None,
) -> HoraVenda:
    """Cancela pedido. Reage ao status atual e ao estado da NFe.

    Regras de bloqueio:
      - Se NFe em estado em-voo (EM_ENVIO / ENVIADA_SEFAZ /
        CANCELAMENTO_SOLICITADO): aguardar resolucao, nao aceita.
      - Se NFe APROVADA: exige que ja tenha sido cancelada na SEFAZ
        (status CANCELADA). Operador deve cancelar a NFe primeiro
        (rota /vendas/<id>/nfe/cancelar), aguardar webhook nfe_cancelada,
        e so depois cancelar o pedido.
      - Se status ja CANCELADO: idempotente.

    Efeito:
      - status -> CANCELADO, marcadores cancelado_em/por/motivo preenchidos.
      - Para cada chassi do pedido: emite DEVOLVIDA (devolve ao estoque
        disponivel).
      - Auditoria: CANCELOU.
    """
    motivo_limpo = (motivo or '').strip()
    if len(motivo_limpo) < 3:
        raise ValueError('Motivo obrigatorio (min 3 chars)')

    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    if venda.status == VENDA_STATUS_CANCELADO:
        return venda

    emissao = _emissao_nfe(venda.id)
    if emissao:
        if emissao.status in _NFE_EM_VOO:
            raise TransicaoInvalidaError(
                f'NFe em estado {emissao.status} — aguarde resolucao SEFAZ '
                'antes de cancelar o pedido.'
            )
        if emissao.status == NFE_STATUS_APROVADA:
            raise TransicaoInvalidaError(
                'NFe esta APROVADA — cancele a NFe primeiro (janela 24h SEFAZ) '
                'e aguarde a confirmacao SEFAZ antes de cancelar o pedido.'
            )
        # NFe em REJEITADA_LOCAL/SEFAZ/ERRO_INFRA/CANCELADA: pode cancelar pedido livre.

    venda.status = VENDA_STATUS_CANCELADO
    venda.cancelado_em = agora_utc_naive()
    venda.cancelado_por = usuario or 'desconhecido'
    venda.cancelamento_motivo = motivo_limpo[:500]

    for item in venda.itens:
        devolver_ao_estoque(
            numero_chassi=item.numero_chassi,
            origem_tabela='hora_venda',
            origem_id=venda.id,
            loja_id=venda.loja_id,
            operador=usuario,
            detalhe=f'Pedido #{venda.id} cancelado: {motivo_limpo[:180]}',
        )

    # Devolve pecas ao estoque (DEVOLUCAO_VENDA).
    if venda.itens_peca:
        from app.hora.services import peca_estoque_service
        for ip in venda.itens_peca:
            peca_estoque_service.registrar_movimento(
                peca_id=ip.peca_id, loja_id=venda.loja_id,
                tipo='DEVOLUCAO_VENDA', qtd=Decimal(str(ip.qtd)),
                ref_tabela='hora_venda_item_peca', ref_id=ip.id,
                motivo=f'Pedido #{venda.id} cancelado',
                operador=usuario,
            )

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='CANCELOU',
        detalhe=motivo_limpo[:500],
    )

    db.session.commit()

    # Espelha o cancelamento no pedido TagPlus (PATCH status=C) — Fase 2b, flag, tolerante.
    from app.hora.services.tagplus import pedido_sync_service
    pedido_sync_service.push_cancelar(venda)

    return venda


# --------------------------------------------------------------------------
# Itens PECA em pedido de venda
# --------------------------------------------------------------------------

def adicionar_item_peca(
    venda_id: int,
    peca_id: int,
    qtd,
    valor_unitario_final,
    usuario: Optional[str] = None,
) -> HoraVendaItemPeca:
    """Adiciona peca em pedido COTACAO. Emite SAIDA_VENDA na loja do pedido.

    Validacoes:
    - status precisa ser COTACAO
    - peca_id existe
    - qtd > 0 e valor_unitario_final > 0
    - venda.loja_id definido
    - saldo na loja suficiente
    """
    from app.hora.services import peca_estoque_service

    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    _exigir_cotacao(venda, 'Adicionar peca')

    peca = HoraPeca.query.get(peca_id)
    if not peca:
        raise ValueError(f'Peca {peca_id} nao existe')
    qtd_dec = Decimal(str(qtd or 0))
    if qtd_dec <= 0:
        raise ValueError('qtd deve ser positiva')
    valor_uni = Decimal(str(valor_unitario_final or 0))
    if valor_uni <= 0:
        raise ValueError('valor_unitario_final deve ser positivo')

    if not venda.loja_id:
        raise ValueError('Venda sem loja_id - defina loja antes de adicionar pecas')
    saldo_atual = peca_estoque_service.saldo(peca.id, venda.loja_id)
    if saldo_atual < qtd_dec:
        raise ValueError(
            f'Saldo insuficiente: loja {venda.loja_id} tem {saldo_atual} {peca.unidade}, '
            f'pedido exige {qtd_dec}'
        )

    preco_ref = Decimal(str(peca.preco_venda_padrao))
    desconto_uni = max(Decimal('0'), preco_ref - valor_uni)
    preco_final_total = qtd_dec * valor_uni
    custo_uni = Decimal(str(peca.custo or 0))  # snapshot do custo p/ margem (hora_59)

    item = HoraVendaItemPeca(
        venda_id=venda.id, peca_id=peca.id, qtd=qtd_dec,
        preco_unitario_referencia=preco_ref,
        desconto_aplicado=desconto_uni,
        preco_final=preco_final_total,
        custo_unitario=custo_uni,
    )
    db.session.add(item)
    db.session.flush()

    peca_estoque_service.registrar_movimento(
        peca_id=peca.id, loja_id=venda.loja_id,
        tipo='SAIDA_VENDA', qtd=-qtd_dec,
        ref_tabela='hora_venda_item_peca', ref_id=item.id,
        motivo=f'Pedido #{venda.id}', operador=usuario,
    )

    venda.valor_total = Decimal(str(venda.valor_total)) + preco_final_total
    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='ADICIONOU_ITEM_PECA',
        detalhe=f'peca={peca.codigo_interno} qtd={qtd_dec} total={preco_final_total}',
    )
    db.session.commit()
    return item


def remover_item_peca(venda_id: int, item_id: int, usuario: Optional[str] = None) -> None:
    """Remove peca de pedido COTACAO. Emite DEVOLUCAO_VENDA (devolve estoque)."""
    from app.hora.services import peca_estoque_service

    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    _exigir_cotacao(venda, 'Remover peca')

    item = HoraVendaItemPeca.query.get(item_id)
    if not item or item.venda_id != venda.id:
        raise ValueError(f'Item peca {item_id} nao pertence ao pedido {venda_id}')

    peca_estoque_service.registrar_movimento(
        peca_id=item.peca_id, loja_id=venda.loja_id,
        tipo='DEVOLUCAO_VENDA', qtd=Decimal(str(item.qtd)),
        ref_tabela='hora_venda_item_peca', ref_id=item.id,
        motivo=f'Item peca removido do pedido #{venda.id}',
        operador=usuario,
    )

    venda.valor_total = Decimal(str(venda.valor_total)) - Decimal(str(item.preco_final))
    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='REMOVEU_ITEM_PECA',
        detalhe=f'peca={item.peca.codigo_interno} qtd={item.qtd}',
    )
    db.session.delete(item)
    db.session.commit()


# --------------------------------------------------------------------------
# Brindes (#36) — peca dada de brinde: custo na margem, NAO cobrado, NAO
# abate estoque (custo = peca.custo snapshot — hora_59; antes preco_venda_padrao).
# --------------------------------------------------------------------------

def _criar_brinde_flush_only(venda: HoraVenda, peca_id: int, qtd,
                             usuario: Optional[str] = None):
    """Cria um HoraVendaBrinde (add + flush + auditoria) SEM commit e SEM o
    guard de status. Reuso por `adicionar_brinde` (rota pos-save, que envolve
    com `_exigir_cotacao` + commit) e por `criar_venda_manual` (#4a — cria os
    brindes do orcamento na MESMA transacao do pedido, antes do commit unico,
    permitindo prometer brinde ja na cotacao mesmo quando nasce INCOMPLETO).
    """
    from app.hora.models import HoraVendaBrinde
    peca = HoraPeca.query.get(peca_id)
    if not peca:
        raise ValueError(f'Peca {peca_id} nao existe')
    qtd_dec = Decimal(str(qtd or 0))
    if qtd_dec <= 0:
        raise ValueError('qtd deve ser positiva')
    # Custo real da peca (hora_59) — antes usava preco_venda_padrao como proxy.
    custo_uni = Decimal(str(peca.custo or 0))
    brinde = HoraVendaBrinde(
        venda_id=venda.id, peca_id=peca.id, qtd=qtd_dec,
        custo_unitario=custo_uni, custo_total=qtd_dec * custo_uni,
        criado_por=(usuario or '').strip()[:100] or None,
    )
    db.session.add(brinde)
    db.session.flush()
    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '', acao='ADICIONOU_BRINDE',
        detalhe=f'peca={peca.codigo_interno} qtd={qtd_dec} custo={brinde.custo_total}',
    )
    return brinde


def adicionar_brinde(venda_id: int, peca_id: int, qtd,
                     usuario: Optional[str] = None):
    """Adiciona um brinde (peca) ao pedido em COTACAO.

    Custo = peca.custo (snapshot — hora_59). NAO entra no valor cobrado
    (valor_total) e NAO abate estoque — apenas reduz a margem da venda
    (venda_preview_service).
    """
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    _exigir_cotacao_ou_incompleto(venda, 'Adicionar brinde')
    brinde = _criar_brinde_flush_only(venda, peca_id, qtd, usuario)
    db.session.commit()
    return brinde


def remover_brinde(venda_id: int, brinde_id: int, usuario: Optional[str] = None) -> None:
    """Remove um brinde do pedido em INCOMPLETO ou COTACAO."""
    from app.hora.models import HoraVendaBrinde
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    _exigir_cotacao_ou_incompleto(venda, 'Remover brinde')
    brinde = HoraVendaBrinde.query.get(brinde_id)
    if not brinde or brinde.venda_id != venda.id:
        raise ValueError(f'Brinde {brinde_id} nao pertence ao pedido {venda_id}')
    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '', acao='REMOVEU_BRINDE',
        detalhe=f'peca_id={brinde.peca_id} qtd={brinde.qtd}',
    )
    db.session.delete(brinde)
    db.session.commit()


# --------------------------------------------------------------------------
# Descarte de NF de teste (pos janela 24h SEFAZ)
# --------------------------------------------------------------------------

def descartar_venda_teste(
    venda_id: int,
    motivo: str,
    usuario: Optional[str] = None,
) -> HoraVenda:
    """Descarta venda de teste cuja NFe estourou janela 24h SEFAZ.

    Diferenca de cancelar_venda: NAO checa se NFe foi cancelada na SEFAZ.
    A NFe permanece valida na SEFAZ; apenas marca o pedido como CANCELADO
    no sistema interno e libera os chassis para o estoque. Uso restrito a
    limpar NFs de teste poluindo o sistema.

    Bloqueios mantidos:
      - Motivo obrigatorio (min 3 chars).
      - Venda deve existir.
      - NFe em estado em-voo (EM_ENVIO/ENVIADA_SEFAZ/CANCELAMENTO_SOLICITADO):
        ainda bloqueia (race condition real).
      - Idempotente se ja CANCELADO.

    Efeito (identico a cancelar_venda):
      - status -> CANCELADO; cancelado_em/por preenchidos.
      - cancelamento_motivo persistido com prefixo "[DESCARTE TESTE] ".
      - DEVOLVIDA em todos os chassis (libera estoque).
      - Auditoria: acao DESCARTOU_TESTE (distinta de CANCELOU).
    """
    motivo_limpo = (motivo or '').strip()
    if len(motivo_limpo) < 3:
        raise ValueError('Motivo obrigatorio (min 3 chars)')

    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    if venda.status == VENDA_STATUS_CANCELADO:
        return venda

    emissao = _emissao_nfe(venda.id)
    if emissao and emissao.status in _NFE_EM_VOO:
        raise TransicaoInvalidaError(
            f'NFe em estado {emissao.status} — aguarde resolucao SEFAZ '
            'antes de descartar o pedido.'
        )

    motivo_persistido = f'[DESCARTE TESTE] {motivo_limpo}'[:500]
    venda.status = VENDA_STATUS_CANCELADO
    venda.cancelado_em = agora_utc_naive()
    venda.cancelado_por = usuario or 'desconhecido'
    venda.cancelamento_motivo = motivo_persistido

    for item in venda.itens:
        devolver_ao_estoque(
            numero_chassi=item.numero_chassi,
            origem_tabela='hora_venda',
            origem_id=venda.id,
            loja_id=venda.loja_id,
            operador=usuario,
            detalhe=f'Pedido #{venda.id} descartado (NF teste): {motivo_limpo[:160]}',
        )

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='DESCARTOU_TESTE',
        detalhe=motivo_limpo[:500],
    )

    db.session.commit()
    return venda


# --------------------------------------------------------------------------
# Definir loja (CNPJ_DESCONHECIDO)
# --------------------------------------------------------------------------

def definir_loja_venda(
    venda_id: int,
    loja_id: int,
    usuario: Optional[str] = None,
) -> HoraVenda:
    """Define ou TROCA a loja fisica do pedido.

    Caso de uso primario: como NFe da Lojas HORA sai sempre com CNPJ da
    matriz (regra fiscal — invariante 2026-04-27 em CLAUDE.md), o
    backfill resolve `loja_id` pelo CNPJ emitente e cai sempre na matriz.
    Operador precisa indicar a loja fisica real onde a venda aconteceu.

    Comportamento:
      - Se loja_id atual == novo loja_id: no-op (idempotente).
      - Se atual e NULL ou diferente: atualiza + emite VENDIDA com a nova
        loja_id (auditoria de movimentacao). Resolve divergencia
        CNPJ_DESCONHECIDO se houver.
    """
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')

    loja = HoraLoja.query.get(loja_id)
    if not loja:
        raise ValueError(f'Loja {loja_id} nao encontrada')

    loja_anterior_id = venda.loja_id
    if loja_anterior_id == loja_id:
        return venda

    venda.loja_id = loja_id

    if loja_anterior_id is None:
        detalhe_evt = (
            f'Loja definida retroativamente no pedido #{venda.id} '
            '(evento anterior com loja_id=NULL).'
        )
    else:
        loja_ant = HoraLoja.query.get(loja_anterior_id)
        rotulo_ant = loja_ant.rotulo_display if loja_ant else f'#{loja_anterior_id}'
        detalhe_evt = (
            f'Loja trocada de {rotulo_ant} para {loja.rotulo_display} '
            f'no pedido #{venda.id}.'
        )

    for item in venda.itens:
        registrar_evento(
            numero_chassi=item.numero_chassi,
            tipo='VENDIDA',
            origem_tabela='hora_venda_item',
            origem_id=item.id,
            loja_id=loja_id,
            operador=usuario,
            detalhe=detalhe_evt,
        )

    div = (
        HoraVendaDivergencia.query
        .filter_by(venda_id=venda.id, tipo='CNPJ_DESCONHECIDO')
        .first()
    )
    if div and div.resolvida_em is None:
        div.resolvida_em = agora_utc_naive()
        div.resolvida_por = usuario

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='DEFINIU_LOJA',
        valor_antes=str(loja_anterior_id) if loja_anterior_id else None,
        valor_depois=str(loja_id),
        detalhe=(
            f'Loja {"definida" if loja_anterior_id is None else "trocada"}: '
            f'{loja.rotulo_display}'
        ),
    )

    db.session.commit()
    return venda


def resolver_divergencia(
    divergencia_id: int,
    usuario: Optional[str] = None,
) -> HoraVendaDivergencia:
    div = HoraVendaDivergencia.query.get(divergencia_id)
    if not div:
        raise ValueError(f'Divergencia {divergencia_id} nao encontrada')
    if div.resolvida_em is not None:
        return div
    div.resolvida_em = agora_utc_naive()
    div.resolvida_por = usuario

    venda_audit.registrar_auditoria(
        venda_id=div.venda_id, usuario=usuario or '',
        acao='RESOLVEU_DIVERGENCIA',
        detalhe=f'tipo={div.tipo} chassi={div.numero_chassi or "-"}',
    )
    db.session.commit()
    return div


# --------------------------------------------------------------------------
# Import DANFE legado: nasce em FATURADO direto
# --------------------------------------------------------------------------

def importar_nf_saida_pdf(
    pdf_bytes: bytes,
    nome_arquivo_origem: Optional[str] = None,
    criado_por: Optional[str] = None,
) -> HoraVenda:
    """Parseia DANFE de saida e cria pedido FATURADO (NF ja existe)."""
    payload = parse_danfe_to_hora_payload(
        pdf_bytes=pdf_bytes,
        nome_arquivo_origem=nome_arquivo_origem,
    )
    nf_data = payload['nf']
    itens_data = payload['itens']

    chave_44 = nf_data['chave_44']

    existente = HoraVenda.query.filter_by(nf_saida_chave_44=chave_44).first()
    if existente:
        raise NfSaidaJaImportada(
            f'NF de saida com chave {chave_44} ja importada (venda_id={existente.id})'
        )

    # `cpf_destinatario` no payload do parser comporta CPF (11) ou CNPJ (14)
    # — ver app/hora/services/parsers/danfe_adapter.py.
    cpf_cliente = nf_data.get('cpf_destinatario')
    nome_cliente = nf_data.get('nome_destinatario')
    if not cpf_cliente:
        raise ValueError(
            'NF de saida sem CPF/CNPJ do destinatario.'
        )
    if not nome_cliente:
        raise ValueError('NF de saida sem nome do destinatario.')

    cnpj_emitente = nf_data.get('cnpj_emitente')
    # DANFE nao carrega departamento -> loja real so via CNPJ NAO-matriz; senao
    # NULL (loja a definir). NUNCA atribuir a venda a matriz (emitente fiscal).
    loja_venda = _resolver_loja_real_venda(cnpj_emitente, None)

    s3_key = _salvar_pdf_storage(
        pdf_bytes=pdf_bytes, chave_44=chave_44,
        nome_arquivo_origem=nome_arquivo_origem,
    )

    data_emissao = nf_data['data_emissao']
    valor_total_nf = Decimal(str(nf_data['valor_total']))
    venda = HoraVenda(
        loja_id=loja_venda.id if loja_venda else None,
        cpf_cliente=cpf_cliente[:14],
        nome_cliente=nome_cliente[:200],
        data_venda=data_emissao,
        forma_pagamento='NAO_INFORMADO',
        valor_total=valor_total_nf,
        nf_saida_numero=nf_data['numero_nf'][:20],
        nf_saida_chave_44=chave_44,
        nf_saida_emitida_em=_para_datetime(data_emissao),
        arquivo_pdf_s3_key=s3_key,
        parser_usado=nf_data.get('parser_usado', 'danfe_pdf_parser_v1'),
        parseada_em=agora_utc_naive(),
        cnpj_emitente=cnpj_emitente,
        status=VENDA_STATUS_FATURADO,
        faturado_em=_para_datetime(data_emissao) or agora_utc_naive(),
        vendedor=None,
        origem_criacao='DANFE',
    )
    db.session.add(venda)
    db.session.flush()

    if loja_venda is None:
        _registrar_divergencia(
            venda_id=venda.id, tipo='CNPJ_DESCONHECIDO',
            detalhe=(
                'Loja de venda nao definida: emitente da NF e a matriz (ou CNPJ '
                'nao cadastrado). Defina a loja fisica na tela de detalhe.'
            ),
            valor_conferido=cnpj_emitente,
        )

    _criar_itens_e_eventos(
        venda=venda,
        itens_data=itens_data,
        loja_emitente_id=loja_venda.id if loja_venda else None,
        data_venda=data_emissao,
        operador=criado_por,
    )

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=criado_por or '',
        acao='CRIOU',
        detalhe=(
            f'Import DANFE legado (FATURADO direto) NF {venda.nf_saida_numero} '
            f'chave {chave_44}'
        ),
    )

    db.session.commit()
    return venda


def _resolver_modelo_id_por_codigo(codigo_produto: Optional[str]) -> Optional[int]:
    """Resolve modelo_id deterministicamente via tagplus_codigo.

    Migration hora_29: usa resolver_via_tagplus (que cobre HoraModeloAlias
    com tipo TAGPLUS_CODIGO + fallback legado em hora_tagplus_produto_map).
    """
    if not codigo_produto:
        return None
    cod = codigo_produto.strip()
    if not cod:
        return None
    from app.hora.services.modelo_resolver_service import resolver_via_tagplus
    modelo = resolver_via_tagplus(tagplus_codigo=cod)
    return modelo.id if modelo else None


def _criar_itens_e_eventos(
    venda: HoraVenda,
    itens_data: List[dict],
    loja_emitente_id: Optional[int],
    data_venda,
    operador: Optional[str],
) -> None:
    """Cria HoraVendaItem + evento VENDIDA + divergencias por chassi (DANFE legado)."""
    for item in itens_data:
        chassi = item['numero_chassi']
        preco_final = Decimal(str(item['preco_real']))
        codigo_produto = item.get('codigo_produto')

        moto_existia = HoraMoto.query.get(chassi) is not None

        # Caminho 1 (DETERMINISTICO): codigo TagPlus -> modelo_id via mapa.
        # Caminho 2 (FALLBACK): nome textual extraido do PDF — pode criar
        # 'BICICLETA ELETRICA' generico, registrar divergencia.
        modelo_id_resolvido = _resolver_modelo_id_por_codigo(codigo_produto)
        if modelo_id_resolvido and not moto_existia:
            # Cria moto vinculada direto ao modelo correto.
            moto = HoraMoto(
                numero_chassi=chassi,
                modelo_id=modelo_id_resolvido,
                cor=(item.get('cor_texto_original') or 'NAO_INFORMADA').strip().upper(),
                numero_motor=item.get('numero_motor') or None,
                ano_modelo=item.get('ano_modelo'),
                criado_por=operador,
            )
            db.session.add(moto)
            db.session.flush()
        else:
            # Migration hora_29: get_or_create_moto pode levantar
            # ModeloPendenteError. Capturamos e SKIPAMOS o item — operador
            # resolve via /hora/modelos/pendencias e re-importa NF (UNIQUE
            # em chave_44 detecta + atualiza).
            from app.hora.services.modelo_resolver_service import ModeloPendenteError
            from app.hora.models import PENDENTE_ORIGEM_DANFE_PDF
            try:
                moto = get_or_create_moto(
                    numero_chassi=chassi,
                    modelo_nome=item.get('modelo_texto_original'),
                    cor=item.get('cor_texto_original') or 'NAO_INFORMADA',
                    numero_motor=item.get('numero_motor'),
                    ano_modelo=item.get('ano_modelo'),
                    criado_por=operador,
                    origem_pendencia=PENDENTE_ORIGEM_DANFE_PDF,
                    origem_id=venda.id,
                    tagplus_codigo=codigo_produto,
                )
            except ModeloPendenteError as exc:
                _registrar_divergencia(
                    venda_id=venda.id, tipo='MODELO_PENDENTE',
                    numero_chassi=chassi,
                    detalhe=(
                        f'Modelo {(item.get("modelo_texto_original") or codigo_produto)!r} '
                        f'nao reconhecido. Pendencia #{exc.pendencia.id} aguardando '
                        f'decisao em /hora/modelos/pendencias. Re-importe a NF apos '
                        f'resolver.'
                    ),
                    valor_conferido=(
                        item.get('modelo_texto_original') or codigo_produto or ''
                    )[:255],
                )
                continue
            # Se chegou ate aqui sem modelo_id resolvido E havia codigo no PDF,
            # operador esqueceu de mapear -> registra divergencia.
            if codigo_produto and not modelo_id_resolvido and not moto_existia:
                _registrar_divergencia(
                    venda_id=venda.id, tipo='TABELA_PRECO_AUSENTE',
                    numero_chassi=chassi,
                    detalhe=(
                        f'Codigo TagPlus {codigo_produto!r} nao mapeado em '
                        f'hora_tagplus_produto_map. Modelo criado por nome '
                        f'textual (pode ser duplicata). Mapear em '
                        f'/hora/modelos/{moto.modelo_id}/editar.'
                    ),
                    valor_conferido=codigo_produto,
                )
        if not moto_existia:
            _registrar_divergencia(
                venda_id=venda.id, tipo='CHASSI_NAO_CADASTRADO',
                numero_chassi=chassi,
                detalhe='Chassi nao existia em hora_moto (criado a partir da NF).',
            )

        ult = _ultimo_evento(chassi)
        if ult is None:
            if moto_existia:
                _registrar_divergencia(
                    venda_id=venda.id, tipo='CHASSI_INDISPONIVEL',
                    numero_chassi=chassi,
                    detalhe='Chassi existia em hora_moto mas sem nenhum evento.',
                )
        else:
            if ult.tipo not in EVENTOS_EM_ESTOQUE:
                _registrar_divergencia(
                    venda_id=venda.id, tipo='CHASSI_INDISPONIVEL',
                    numero_chassi=chassi,
                    detalhe=(
                        f'Ultimo evento do chassi era {ult.tipo} '
                        f'(em {ult.timestamp.strftime("%d/%m/%Y %H:%M")})'
                    ),
                    valor_conferido=ult.tipo,
                )
            if (
                loja_emitente_id is not None
                and ult.loja_id is not None
                and ult.loja_id != loja_emitente_id
            ):
                _registrar_divergencia(
                    venda_id=venda.id, tipo='LOJA_DIVERGENTE',
                    numero_chassi=chassi,
                    detalhe=(
                        f'Chassi estava na loja_id={ult.loja_id} '
                        f'mas NF foi emitida pela loja_id={loja_emitente_id}.'
                    ),
                    valor_esperado=str(loja_emitente_id),
                    valor_conferido=str(ult.loja_id),
                )

        preco_ref, desconto, desconto_pct, tabela_id, divergencia_tipo = _resolver_preco_tabela(
            moto.modelo_id, data_venda, preco_final,
            forma_pagamento_hora=venda.forma_pagamento,
        )
        if divergencia_tipo:
            _registrar_divergencia(
                venda_id=venda.id, tipo=divergencia_tipo,
                numero_chassi=chassi,
                detalhe=(
                    f'Sem tabela vigente OU preco acima da tabela. '
                    f'preco_final=R${preco_final}'
                ),
                valor_esperado=str(preco_ref),
                valor_conferido=str(preco_final),
            )

        venda_item = HoraVendaItem(
            venda_id=venda.id,
            numero_chassi=chassi,
            tabela_preco_id=tabela_id,
            preco_tabela_referencia=preco_ref,
            desconto_aplicado=desconto,
            desconto_percentual=desconto_pct,
            preco_final=preco_final,
        )
        db.session.add(venda_item)
        db.session.flush()

        # DANFE legado: vai direto para VENDIDA + NF_EMITIDA (faturado).
        registrar_evento(
            numero_chassi=chassi,
            tipo='VENDIDA',
            origem_tabela='hora_venda_item',
            origem_id=venda_item.id,
            loja_id=loja_emitente_id,
            operador=operador,
            detalhe=(
                f'Pedido FATURADO (DANFE legado) #{venda.id} '
                f'NF {venda.nf_saida_numero} para {venda.nome_cliente}'
            ),
        )


# --------------------------------------------------------------------------
# Listagem
# --------------------------------------------------------------------------

def listar_vendas(
    limit: int = 200,
    lojas_permitidas_ids: Optional[Iterable[int]] = None,
    status: Optional[str] = None,
) -> List[HoraVenda]:
    """Lista pedidos com filtro por lojas permitidas e status (sem paginacao)."""
    query = _query_vendas(lojas_permitidas_ids=lojas_permitidas_ids, status=status)
    if query is None:
        return []
    return query.limit(limit).all()


def _query_vendas(
    lojas_permitidas_ids: Optional[Iterable[int]] = None,
    status: Optional[Union[str, Iterable[str]]] = None,
    *,
    busca: Optional[str] = None,
    loja_id: Optional[int] = None,
    data_inicio=None,
    data_fim=None,
    chassi: Optional[str] = None,
    eager_itens: bool = False,
    filtro_vendedor: Optional[dict] = None,
):
    """Constroi query base de vendas com filtros — usado por listar e paginar.

    busca: substring que casa em nf_saida_numero, nome_cliente ou cpf_cliente.
    loja_id: id especifico de loja_id (precisa estar dentro de lojas_permitidas).
    data_inicio/data_fim: faixa em data_venda.
    chassi: substring (case-insensitive) que casa em HoraVendaItem.numero_chassi.
        Usa EXISTS para evitar duplicacao de linhas no resultado.
    eager_itens: quando True, faz `selectinload` em itens+moto+modelo para
        permitir exibicao inline na listagem sem N+1. NAO ativar quando o
        caller nao precisa dos itens (custa 3 SELECT IN extras —
        listar_vendas/exportacao geralmente nao precisa).
    """
    from sqlalchemy import or_
    from sqlalchemy.orm import selectinload

    opts = []
    if eager_itens:
        opts.append(
            selectinload(HoraVenda.itens)
            .selectinload(HoraVendaItem.moto)
            .selectinload(HoraMoto.modelo),
        )
        # Roadmap #1: badge de qtd de pecas na listagem — evita N+1.
        opts.append(selectinload(HoraVenda.itens_peca))

    query = HoraVenda.query
    if opts:
        query = query.options(*opts)
    query = query.order_by(
        HoraVenda.data_venda.desc(), HoraVenda.id.desc()
    )
    if status:
        # Aceita str (1 status) OU iteravel de status (multi-selecao da tela).
        # Retrocompativel com chamadas legadas que passam string.
        if isinstance(status, str):
            query = query.filter(HoraVenda.status == status)
        else:
            status_list = [s for s in status if s]
            if status_list:
                query = query.filter(HoraVenda.status.in_(status_list))
    if filtro_vendedor is not None:
        # Criterio 'vendedor': ignora escopo de loja; pedidos do proprio usuario.
        nomes = [n for n in (filtro_vendedor.get('nomes') or []) if n]
        uid = filtro_vendedor.get('user_id')
        conds = []
        if nomes:
            conds.append(HoraVenda.vendedor.in_(nomes))
        if uid is not None:
            conds.append(HoraVenda.criado_por_id == uid)
        if not conds:
            return None  # sem criterio resolvivel -> nada a mostrar
        query = query.filter(or_(*conds))
    elif lojas_permitidas_ids is not None:
        ids_list = list(lojas_permitidas_ids)
        if not ids_list:
            return None
        query = query.filter(HoraVenda.loja_id.in_(ids_list))

    if busca:
        b = busca.strip()
        digits = ''.join(c for c in b if c.isdigit())
        cond = or_(
            HoraVenda.nf_saida_numero.ilike(f'%{b}%'),
            HoraVenda.nome_cliente.ilike(f'%{b}%'),
        )
        if digits:
            cond = or_(cond, HoraVenda.cpf_cliente.ilike(f'%{digits}%'))
        query = query.filter(cond)
    if loja_id:
        query = query.filter(HoraVenda.loja_id == loja_id)
    if data_inicio:
        query = query.filter(HoraVenda.data_venda >= data_inicio)
    if data_fim:
        query = query.filter(HoraVenda.data_venda <= data_fim)
    if chassi:
        ch = chassi.strip().upper()
        if ch:
            # EXISTS evita duplicar HoraVenda quando chassi casa multiplos
            # itens (raro mas possivel em pedido com itens trocados via
            # editar_item_pedido). Mantem ordering estavel.
            sub = (
                db.session.query(HoraVendaItem.id)
                .filter(HoraVendaItem.venda_id == HoraVenda.id)
                .filter(HoraVendaItem.numero_chassi.ilike(f'%{ch}%'))
            )
            query = query.filter(sub.exists())
    return query


def paginar_vendas(
    page: int = 1,
    per_page: int = 50,
    lojas_permitidas_ids: Optional[Iterable[int]] = None,
    status: Optional[Union[str, Iterable[str]]] = None,
    *,
    busca: Optional[str] = None,
    loja_id: Optional[int] = None,
    data_inicio=None,
    data_fim=None,
    chassi: Optional[str] = None,
    filtro_vendedor: Optional[dict] = None,
):
    """Pagina vendas com filtros. Retorna `Pagination` (Flask-SQLAlchemy)
    ou None quando o usuario nao tem nenhuma loja permitida (lista vazia).
    """
    page = max(1, int(page or 1))
    per_page = max(1, min(int(per_page or 50), 200))
    query = _query_vendas(
        lojas_permitidas_ids=lojas_permitidas_ids,
        status=status,
        busca=busca,
        loja_id=loja_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        chassi=chassi,
        eager_itens=True,  # listagem mostra itens (chassi+modelo+cor) inline.
        filtro_vendedor=filtro_vendedor,
    )
    if query is None:
        return None
    return query.paginate(page=page, per_page=per_page, error_out=False)


__all__ = [
    'NfSaidaJaImportada',
    'ChassiIndisponivelError',
    'TransicaoInvalidaError',
    'criar_venda_manual',
    'confirmar_venda',
    'editar_venda',
    'editar_pagamentos',
    'adicionar_item_pedido',
    'remover_item_pedido',
    'editar_item_pedido',
    'cancelar_venda',
    'descartar_venda_teste',
    'definir_loja_venda',
    'resolver_divergencia',
    'importar_nf_saida_pdf',
    'listar_vendas',
]
