"""Resolver de modelo: N nomes -> 1 modelo canonico.

Substitui o antigo `cadastro_service.buscar_ou_criar_modelo` que criava
HoraModelo silenciosamente para qualquer nome novo, gerando duplicacao
(ex: BOB, BOB AM, SCOOTER ELETRICA BOB viraram 3 modelos).

Fluxo novo:
  1. resolver_modelo(nome, tipo) consulta hora_modelo_alias.
  2. Se nao achar, fallback para hora_modelo.nome_modelo (compat).
  3. Se ainda nao achar, resolver_ou_pendenciar cria/incrementa entrada
     em hora_modelo_pendente. Sistema NAO cria modelo silenciosamente.
  4. Operador resolve via tela /hora/modelos/pendencias:
       - Vincular: cria HoraModeloAlias para o nome -> modelo existente.
       - Criar novo: cria HoraModelo + HoraModeloAlias.
       - Ignorar: marca pendencia, nao gera modelo.

Ver `app/hora/CLAUDE.md` secao "Unificacao de modelos".
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import func

from app import db
from app.hora.models import (
    HoraModelo,
    HoraModeloAlias,
    HoraModeloPendente,
    ALIAS_TIPO_TAGPLUS_PRODUTO_ID,
    ALIAS_TIPO_TAGPLUS_CODIGO,
    ALIAS_TIPO_NOME_NF,
    ALIAS_TIPO_NOME_PEDIDO,
    ALIAS_TIPO_NOME_LIVRE,
    ALIAS_TIPOS_VALIDOS,
    PENDENTE_ORIGENS_VALIDAS,
    PENDENTE_STATUS_PENDENTE,
)
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


class ModeloPendenteError(Exception):
    """Levantada quando modelo nao e resolvido na ingestao.

    Carrega `pendencia` (HoraModeloPendente) para o chamador decidir como
    tratar:
      - TagPlus backfill / NF DANFE: captura, registra divergencia, segue
        com modelo_id=NULL (HoraMoto NAO eh criada).
      - Pedido manual: rota retorna 4xx com link para /hora/modelos/pendencias.
    """

    def __init__(self, pendencia: HoraModeloPendente, mensagem: Optional[str] = None):
        self.pendencia = pendencia
        super().__init__(
            mensagem
            or (
                f'Modelo {pendencia.nome_observado!r} nao reconhecido '
                f'(origem={pendencia.origem}). Pendencia #{pendencia.id} '
                f'aguardando decisao em /hora/modelos/pendencias.'
            )
        )


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _normalizar(valor: Optional[str]) -> Optional[str]:
    """Strip + uppercase para casamento case-insensitive consistente."""
    if valor is None:
        return None
    s = str(valor).strip()
    return s.upper() if s else None


def _seguir_canonico(modelo: Optional[HoraModelo]) -> Optional[HoraModelo]:
    """Se o modelo achado foi mergeado em outro, retorna o canonico.

    Permite que aliases historicos apontando para um modelo absorvido
    ainda funcionem — segue a cadeia ate o canonico ativo.
    """
    if modelo is None:
        return None

    visitados: set[int] = set()
    atual = modelo
    while atual.merged_em_id is not None and atual.id not in visitados:
        visitados.add(atual.id)
        proximo = HoraModelo.query.get(atual.merged_em_id)
        if proximo is None:
            break
        atual = proximo
    return atual


# ---------------------------------------------------------------------------
# Resolver (consulta apenas)
# ---------------------------------------------------------------------------

def resolver_modelo(
    nome: Optional[str],
    *,
    tipo: Optional[str] = None,
    tipos: Optional[tuple[str, ...]] = None,
) -> Optional[HoraModelo]:
    """Procura modelo via aliases. Retorna None se nao encontrar.

    Args:
        nome: string a buscar (e.g. 'BOB AM', 'MT-BOB', '10').
        tipo: se passado, restringe busca a esse tipo de alias.
        tipos: se passado, restringe a esses tipos (OR).
        Se nem `tipo` nem `tipos`: busca em qualquer tipo (todos).

    Ordem:
      1. hora_modelo_alias com tipos especificados (case-insensitive).
      2. Fallback: hora_modelo.nome_modelo == nome (compat com modelos
         que ainda nao foram seedados como aliases).

    O retorno SEMPRE eh o modelo canonico (segue cadeia merged_em_id).
    """
    nome_norm = _normalizar(nome)
    if not nome_norm:
        return None

    tipos_busca: tuple[str, ...]
    if tipo:
        tipos_busca = (tipo,)
    elif tipos:
        tipos_busca = tuple(tipos)
    else:
        tipos_busca = ALIAS_TIPOS_VALIDOS

    # 1. Busca em hora_modelo_alias (case-insensitive via UPPER)
    alias = (
        HoraModeloAlias.query
        .filter(HoraModeloAlias.tipo.in_(tipos_busca))
        .filter(func.upper(HoraModeloAlias.nome_alias) == nome_norm)
        .first()
    )
    if alias and alias.modelo:
        return _seguir_canonico(alias.modelo)

    # 2. Fallback: nome_modelo direto (compat)
    modelo = (
        HoraModelo.query
        .filter(func.upper(HoraModelo.nome_modelo) == nome_norm)
        .first()
    )
    return _seguir_canonico(modelo)


def resolver_via_tagplus(
    *,
    tagplus_codigo: Optional[str] = None,
    tagplus_produto_id: Optional[str] = None,
) -> Optional[HoraModelo]:
    """Atalho TagPlus: tenta tagplus_codigo > tagplus_produto_id > legado.

    O legado eh hora_tagplus_produto_map, que ainda mapeia diretamente
    modelo<->codigo TagPlus. Mantemos compat — uma migration Fase 5
    populara hora_modelo_alias a partir desse legado.
    """
    if tagplus_codigo:
        m = resolver_modelo(tagplus_codigo, tipo=ALIAS_TIPO_TAGPLUS_CODIGO)
        if m:
            return m
    if tagplus_produto_id:
        m = resolver_modelo(str(tagplus_produto_id), tipo=ALIAS_TIPO_TAGPLUS_PRODUTO_ID)
        if m:
            return m

    # Legado: hora_tagplus_produto_map
    from app.hora.models import HoraTagPlusProdutoMap
    if tagplus_codigo:
        leg = (
            HoraTagPlusProdutoMap.query
            .filter(HoraTagPlusProdutoMap.tagplus_codigo == tagplus_codigo.strip())
            .first()
        )
        if leg and leg.modelo:
            return _seguir_canonico(leg.modelo)
    if tagplus_produto_id:
        leg = (
            HoraTagPlusProdutoMap.query
            .filter(HoraTagPlusProdutoMap.tagplus_produto_id == str(tagplus_produto_id).strip())
            .first()
        )
        if leg and leg.modelo:
            return _seguir_canonico(leg.modelo)
    return None


# ---------------------------------------------------------------------------
# Resolver-ou-pendenciar (cria pendencia se nao achar)
# ---------------------------------------------------------------------------

def resolver_ou_pendenciar(
    nome: Optional[str],
    *,
    origem: str,
    origem_id: Optional[int] = None,
    tipo_alias: Optional[str] = None,
    tagplus_codigo: Optional[str] = None,
    tagplus_produto_id: Optional[str] = None,
    commit: bool = False,
) -> tuple[Optional[HoraModelo], Optional[HoraModeloPendente]]:
    """Resolve modelo. Se nao achar, cria/incrementa pendencia.

    Args:
        nome: nome a buscar/pendenciar. Pode ser None se houver tagplus_*.
        origem: PENDENTE_ORIGEM_* (qual fluxo disparou).
        origem_id: id da entidade que disparou (venda_id, nf_id, ...).
        tipo_alias: se passado, restringe busca a esse tipo. Se None,
            tenta na ordem TAGPLUS_CODIGO > TAGPLUS_PRODUTO_ID > nome
            textual em qualquer tipo.
        tagplus_codigo / tagplus_produto_id: usados em
            resolver_via_tagplus + persistidos na pendencia para auditoria.
        commit: se True, faz db.session.commit() ao final. Default False
            (chamador controla transacao).

    Returns:
        (modelo, None) se resolveu — uso normal.
        (None, pendente) se nao resolveu — chamador trata.

    Idempotente em pendencia: (nome_observado, origem) eh UNIQUE.
        Mesmo nome+origem incrementa qtd_ocorrencias e atualiza ultimo_visto.
    """
    if origem not in PENDENTE_ORIGENS_VALIDAS:
        raise ValueError(
            f'origem invalida: {origem!r}. Validos: {PENDENTE_ORIGENS_VALIDAS}'
        )

    # 1. Tenta TagPlus primeiro se houver pistas
    if tagplus_codigo or tagplus_produto_id:
        modelo = resolver_via_tagplus(
            tagplus_codigo=tagplus_codigo,
            tagplus_produto_id=tagplus_produto_id,
        )
        if modelo:
            return (modelo, None)

    # 2. Tenta nome textual
    nome_norm = _normalizar(nome)
    if nome_norm:
        modelo = resolver_modelo(
            nome_norm,
            tipo=tipo_alias,
        )
        if modelo:
            return (modelo, None)

    # 3. Nao resolveu — cria/incrementa pendencia
    if not nome_norm and not (tagplus_codigo or tagplus_produto_id):
        # Nada para pendenciar. Retorna (None, None).
        return (None, None)

    # Chave da pendencia: prefere nome se houver, senao usa codigo
    chave_nome = nome_norm or tagplus_codigo or f'tagplus_id:{tagplus_produto_id}'

    pendente = (
        HoraModeloPendente.query
        .filter_by(nome_observado=chave_nome, origem=origem)
        .first()
    )
    if pendente is None:
        pendente = HoraModeloPendente(
            nome_observado=chave_nome[:200],
            origem=origem,
            origem_id=origem_id,
            tagplus_codigo=(tagplus_codigo or None),
            tagplus_produto_id=(str(tagplus_produto_id) if tagplus_produto_id else None),
            qtd_ocorrencias=1,
            status=PENDENTE_STATUS_PENDENTE,
        )
        db.session.add(pendente)
        db.session.flush()
        logger.info(
            'Pendencia criada: nome=%r origem=%s id=%s',
            chave_nome, origem, pendente.id,
        )
    else:
        pendente.qtd_ocorrencias = (pendente.qtd_ocorrencias or 0) + 1
        pendente.ultimo_visto = agora_utc_naive()
        # Atualiza tagplus_* se vier preenchido agora (vinha None antes).
        if tagplus_codigo and not pendente.tagplus_codigo:
            pendente.tagplus_codigo = tagplus_codigo
        if tagplus_produto_id and not pendente.tagplus_produto_id:
            pendente.tagplus_produto_id = str(tagplus_produto_id)
        # Atualiza origem_id se nao tinha (rastreio do mais recente)
        if origem_id and not pendente.origem_id:
            pendente.origem_id = origem_id
        db.session.flush()

    if commit:
        db.session.commit()

    return (None, pendente)


# ---------------------------------------------------------------------------
# Helpers de resolucao (usados pela tela /hora/modelos/pendencias)
# ---------------------------------------------------------------------------

def vincular_pendencia_a_modelo(
    pendencia_id: int,
    modelo_id: int,
    *,
    operador: Optional[str] = None,
    tipo_alias: Optional[str] = None,
) -> dict:
    """Resolve pendencia vinculando a modelo existente. Cria HoraModeloAlias.

    Retroatividade: chama propagar_resolucao para corrigir registros que
    ficaram com modelo_id=NULL ou HoraMoto nao criada.

    Returns dict com `pendencia`, `alias_criado`, `retroativos` (resumo).
    """
    from app.hora.models import PENDENTE_STATUS_VINCULADO

    pendencia = HoraModeloPendente.query.get(pendencia_id)
    if not pendencia:
        raise ValueError(f'Pendencia {pendencia_id} nao encontrada')
    if pendencia.status != PENDENTE_STATUS_PENDENTE:
        raise ValueError(
            f'Pendencia ja resolvida (status={pendencia.status}).'
        )

    modelo = HoraModelo.query.get(modelo_id)
    if not modelo:
        raise ValueError(f'Modelo {modelo_id} nao encontrado')
    modelo = _seguir_canonico(modelo) or modelo  # nunca vincula em alias merged

    # Tipo de alias deduzido da origem se nao passado
    if not tipo_alias:
        tipo_alias = _tipo_alias_para_origem(pendencia.origem)

    # Cria alias (idempotente — UNIQUE pode falhar se ja existe)
    existente = (
        HoraModeloAlias.query
        .filter_by(tipo=tipo_alias, nome_alias=pendencia.nome_observado)
        .first()
    )
    alias_criado = False
    if existente:
        if existente.modelo_id != modelo.id:
            raise ValueError(
                f'Alias {pendencia.nome_observado!r} (tipo={tipo_alias}) ja '
                f'aponta para outro modelo (id={existente.modelo_id}). '
                f'Conflito de unicidade.'
            )
    else:
        alias = HoraModeloAlias(
            modelo_id=modelo.id,
            nome_alias=pendencia.nome_observado,
            tipo=tipo_alias,
            criado_por=operador,
            observacao=f'Resolvida pendencia #{pendencia.id}',
        )
        db.session.add(alias)
        alias_criado = True

    pendencia.status = PENDENTE_STATUS_VINCULADO
    pendencia.resolvido_modelo_id = modelo.id
    pendencia.resolvido_em = agora_utc_naive()
    pendencia.resolvido_por = operador
    db.session.flush()

    # Retroatividade
    from app.hora.services.modelo_retroatividade_service import propagar_resolucao
    retroativos = propagar_resolucao(
        nome_observado=pendencia.nome_observado,
        modelo_canonico_id=modelo.id,
        operador=operador,
    )

    db.session.commit()
    return {
        'pendencia_id': pendencia.id,
        'modelo_id': modelo.id,
        'modelo_nome': modelo.nome_modelo,
        'alias_criado': alias_criado,
        'retroativos': retroativos,
    }


def criar_modelo_de_pendencia(
    pendencia_id: int,
    nome_modelo: str,
    *,
    potencia_motor: Optional[str] = None,
    descricao: Optional[str] = None,
    operador: Optional[str] = None,
) -> dict:
    """Resolve pendencia criando NOVO modelo + alias do nome observado.

    Retorna dict com modelo_id, alias_criado, retroativos.
    """
    from app.hora.models import PENDENTE_STATUS_NOVO_MODELO
    from app.hora.services import cadastro_service

    pendencia = HoraModeloPendente.query.get(pendencia_id)
    if not pendencia:
        raise ValueError(f'Pendencia {pendencia_id} nao encontrada')
    if pendencia.status != PENDENTE_STATUS_PENDENTE:
        raise ValueError(
            f'Pendencia ja resolvida (status={pendencia.status}).'
        )

    nome_norm = (nome_modelo or '').strip()
    if not nome_norm:
        raise ValueError('nome_modelo obrigatorio')

    # Cria modelo (cadastro_service valida unicidade de nome_modelo)
    modelo = cadastro_service.criar_modelo(
        nome_modelo=nome_norm,
        potencia_motor=potencia_motor,
        descricao=descricao,
    )

    # Vincula pendencia ao modelo recem-criado (cria alias se nome difere)
    tipo_alias = _tipo_alias_para_origem(pendencia.origem)
    if pendencia.nome_observado.strip().upper() != nome_norm.upper():
        db.session.add(HoraModeloAlias(
            modelo_id=modelo.id,
            nome_alias=pendencia.nome_observado,
            tipo=tipo_alias,
            criado_por=operador,
            observacao=f'Pendencia #{pendencia.id} resolvida criando modelo novo',
        ))

    # Sempre adiciona o proprio nome_modelo como alias NOME_LIVRE (preserva
    # padrao do seed — nome canonico tambem e alias valido).
    db.session.add(HoraModeloAlias(
        modelo_id=modelo.id,
        nome_alias=nome_norm,
        tipo=ALIAS_TIPO_NOME_LIVRE,
        criado_por=operador,
        observacao='Auto-alias do nome_modelo canonico',
    ))

    pendencia.status = PENDENTE_STATUS_NOVO_MODELO
    pendencia.resolvido_modelo_id = modelo.id
    pendencia.resolvido_em = agora_utc_naive()
    pendencia.resolvido_por = operador
    db.session.flush()

    # Retroatividade
    from app.hora.services.modelo_retroatividade_service import propagar_resolucao
    retroativos = propagar_resolucao(
        nome_observado=pendencia.nome_observado,
        modelo_canonico_id=modelo.id,
        operador=operador,
    )

    db.session.commit()
    return {
        'pendencia_id': pendencia.id,
        'modelo_id': modelo.id,
        'modelo_nome': modelo.nome_modelo,
        'modelo_criado': True,
        'retroativos': retroativos,
    }


def ignorar_pendencia(
    pendencia_id: int,
    *,
    operador: Optional[str] = None,
    motivo: Optional[str] = None,
) -> HoraModeloPendente:
    """Marca pendencia como IGNORADA (nao gera modelo/alias).

    Util quando o nome observado eh erro de digitacao em ingestao avulsa
    e nao deve nem virar modelo nem alias. Itens com esse nome continuam
    com modelo_id=NULL (operador resolve manualmente).
    """
    from app.hora.models import PENDENTE_STATUS_IGNORADO

    pendencia = HoraModeloPendente.query.get(pendencia_id)
    if not pendencia:
        raise ValueError(f'Pendencia {pendencia_id} nao encontrada')
    if pendencia.status != PENDENTE_STATUS_PENDENTE:
        raise ValueError(
            f'Pendencia ja resolvida (status={pendencia.status}).'
        )

    pendencia.status = PENDENTE_STATUS_IGNORADO
    pendencia.resolvido_em = agora_utc_naive()
    pendencia.resolvido_por = operador
    if motivo:
        existente = pendencia.observacao or ''
        prefix = '\n' if existente else ''
        pendencia.observacao = f'{existente}{prefix}IGNORADA: {motivo}'[:2000]
    db.session.commit()
    return pendencia


# ---------------------------------------------------------------------------
# Helper interno
# ---------------------------------------------------------------------------

def _tipo_alias_para_origem(origem: str) -> str:
    """Mapeia origem da pendencia -> tipo de alias a criar.

    NF/DANFE/recebimento -> NOME_NF
    Pedido manual -> NOME_PEDIDO
    TagPlus backfill -> TAGPLUS_CODIGO (mais provavel)
    Outros -> NOME_LIVRE
    """
    from app.hora.models import (
        PENDENTE_ORIGEM_TAGPLUS_BACKFILL,
        PENDENTE_ORIGEM_NF_ENTRADA,
        PENDENTE_ORIGEM_PEDIDO_MANUAL,
        PENDENTE_ORIGEM_DANFE_PDF,
        PENDENTE_ORIGEM_RECEBIMENTO,
    )
    mapa = {
        PENDENTE_ORIGEM_TAGPLUS_BACKFILL: ALIAS_TIPO_TAGPLUS_CODIGO,
        PENDENTE_ORIGEM_NF_ENTRADA: ALIAS_TIPO_NOME_NF,
        PENDENTE_ORIGEM_DANFE_PDF: ALIAS_TIPO_NOME_NF,
        PENDENTE_ORIGEM_PEDIDO_MANUAL: ALIAS_TIPO_NOME_PEDIDO,
        PENDENTE_ORIGEM_RECEBIMENTO: ALIAS_TIPO_NOME_NF,
    }
    return mapa.get(origem, ALIAS_TIPO_NOME_LIVRE)
