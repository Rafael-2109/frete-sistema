"""Merge fisico atomico de modelos duplicados.

Resolve a duplicacao historica: 7 grupos detectados em producao
(BOB+BOB AM+SCOOTER ELETRICA BOB; JET+JET AM; X12-10+X12-10 AM; ...).

Operador escolhe canonico + N aliases via tela /hora/modelos/unificar.
Backend executa em UMA transacao:

  1. UPDATE em todas as FKs apontando para o alias -> canonico:
       hora_moto.modelo_id
       hora_pedido_item.modelo_id
       hora_recebimento_conferencia.modelo_id_conferido
       hora_emprestimo_moto.modelo_id
       hora_modelo_alias.modelo_id
       hora_modelo_pendente.resolvido_modelo_id
       hora_modelo (self FK em merged_em_id, caso cadeia)

  2. hora_tabela_preco: mantem somente do canonico. Preco do alias eh
     descartado (com log) — operador foi avisado na UI.

  3. hora_tagplus_produto_map: se canonico ja tem map, transfere
     tagplus_codigo/tagplus_produto_id do alias como HoraModeloAlias
     (preserva como N->1) e DELETA o map do alias (UNIQUE em modelo_id
     impede UPDATE direto). Se canonico nao tem map, faz UPDATE.

  4. Cria HoraModeloAlias para o nome_modelo do alias (preserva nome
     historico do alias como apelido valido do canonico).

  5. Marca alias: ativo=False, merged_em_id=canonico, merged_em=now.

Idempotente parcialmente: re-rodar o mesmo merge falha em (5) se ja
foi mergeado antes (ativo=False e merged_em_id != NULL).

Ver `app/hora/CLAUDE.md` secao "Unificacao de modelos -> merge".
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import text

from app import db
from app.hora.models import (
    HoraModelo,
    HoraModeloAlias,
    HoraTagPlusProdutoMap,
    ALIAS_TIPO_TAGPLUS_PRODUTO_ID,
    ALIAS_TIPO_TAGPLUS_CODIGO,
    ALIAS_TIPO_NOME_LIVRE,
)
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


class MergeError(Exception):
    """Erro de validacao no merge (canonico inexistente, ciclo, etc)."""


def merge_modelos(
    canonico_id: int,
    alias_ids: list[int],
    *,
    operador: Optional[str] = None,
    descartar_precos_aliases: bool = True,
) -> dict:
    """Merge fisico atomico: aliases sao absorvidos no canonico.

    Args:
        canonico_id: id do modelo que sobrevive (recebe todos os FKs).
        alias_ids: lista de ids de modelos a serem absorvidos.
        operador: usuario que disparou (para auditoria).
        descartar_precos_aliases: se True (default), HoraTabelaPreco do
            alias eh deletada. Se False, transfere todas (pode duplicar
            vigencia — operador valida).

    Returns dict com contadores por tabela + lista de alias absorvidos.

    Raises:
        MergeError: validacao falhou.
    """
    if not alias_ids:
        raise MergeError('Nenhum alias informado.')
    if canonico_id in alias_ids:
        raise MergeError('Canonico nao pode estar entre os aliases.')

    canonico = HoraModelo.query.get(canonico_id)
    if not canonico:
        raise MergeError(f'Canonico {canonico_id} nao encontrado.')
    if canonico.merged_em_id is not None:
        raise MergeError(
            f'Canonico {canonico_id} ja foi mergeado em {canonico.merged_em_id}. '
            f'Use o canonico final.'
        )

    aliases = HoraModelo.query.filter(HoraModelo.id.in_(alias_ids)).all()
    if len(aliases) != len(alias_ids):
        encontrados = {m.id for m in aliases}
        faltam = set(alias_ids) - encontrados
        raise MergeError(f'Aliases nao encontrados: {sorted(faltam)}')
    for a in aliases:
        if a.merged_em_id is not None:
            raise MergeError(
                f'Modelo {a.id} ({a.nome_modelo!r}) ja foi mergeado anteriormente.'
            )

    contadores = {
        'aliases_absorvidos': [],
        'hora_moto': 0,
        'hora_pedido_item': 0,
        'hora_recebimento_conferencia': 0,
        'hora_emprestimo_moto': 0,
        'hora_modelo_alias_repontados': 0,
        'hora_modelo_pendente_repontados': 0,
        'hora_modelo_merged_self_repontados': 0,
        'hora_tabela_preco_descartadas': 0,
        'hora_tabela_preco_transferidas': 0,
        'hora_tagplus_produto_map_transferidos': 0,
        'hora_tagplus_produto_map_deletados': 0,
        'aliases_criados': 0,
    }

    # Trabalho real — em transacao gerenciada pelo SQLAlchemy session.
    # Quem chamar (rota) deve fazer commit final, ou commit ja eh feito ao
    # final desta funcao se nao houver erro.

    for alias in aliases:
        _merge_um_alias(canonico, alias, contadores, descartar_precos_aliases, operador)
        contadores['aliases_absorvidos'].append({
            'id': alias.id,
            'nome_modelo': alias.nome_modelo,
        })

    db.session.commit()
    logger.info(
        'Merge concluido: canonico=%s aliases=%s contadores=%s',
        canonico_id, alias_ids, contadores,
    )
    return contadores


def _merge_um_alias(
    canonico: HoraModelo,
    alias: HoraModelo,
    contadores: dict,
    descartar_precos_aliases: bool,
    operador: Optional[str],
) -> None:
    """Absorve 1 alias no canonico (chamado em loop por merge_modelos)."""

    # ----- 1. UPDATE FKs simples (modelo_id apontando para alias) -----

    # hora_moto.modelo_id
    n = db.session.execute(
        text('UPDATE hora_moto SET modelo_id = :c WHERE modelo_id = :a'),
        {'c': canonico.id, 'a': alias.id},
    ).rowcount
    contadores['hora_moto'] += n or 0

    # hora_pedido_item.modelo_id
    n = db.session.execute(
        text('UPDATE hora_pedido_item SET modelo_id = :c WHERE modelo_id = :a'),
        {'c': canonico.id, 'a': alias.id},
    ).rowcount
    contadores['hora_pedido_item'] += n or 0

    # hora_recebimento_conferencia.modelo_id_conferido
    n = db.session.execute(
        text(
            'UPDATE hora_recebimento_conferencia SET modelo_id_conferido = :c '
            'WHERE modelo_id_conferido = :a'
        ),
        {'c': canonico.id, 'a': alias.id},
    ).rowcount
    contadores['hora_recebimento_conferencia'] += n or 0

    # hora_emprestimo_moto.modelo_id
    n = db.session.execute(
        text('UPDATE hora_emprestimo_moto SET modelo_id = :c WHERE modelo_id = :a'),
        {'c': canonico.id, 'a': alias.id},
    ).rowcount
    contadores['hora_emprestimo_moto'] += n or 0

    # ----- 2. hora_modelo_alias: repontar aliases existentes -----
    n = db.session.execute(
        text('UPDATE hora_modelo_alias SET modelo_id = :c WHERE modelo_id = :a'),
        {'c': canonico.id, 'a': alias.id},
    ).rowcount
    contadores['hora_modelo_alias_repontados'] += n or 0

    # ----- 3. hora_modelo_pendente: repontar resolvido_modelo_id -----
    n = db.session.execute(
        text(
            'UPDATE hora_modelo_pendente SET resolvido_modelo_id = :c '
            'WHERE resolvido_modelo_id = :a'
        ),
        {'c': canonico.id, 'a': alias.id},
    ).rowcount
    contadores['hora_modelo_pendente_repontados'] += n or 0

    # ----- 4. hora_modelo.merged_em_id: cadeia (caso outro modelo aponte
    #            para este alias como merged_em_id, repontar para canonico) -----
    n = db.session.execute(
        text(
            'UPDATE hora_modelo SET merged_em_id = :c '
            'WHERE merged_em_id = :a'
        ),
        {'c': canonico.id, 'a': alias.id},
    ).rowcount
    contadores['hora_modelo_merged_self_repontados'] += n or 0

    # ----- 5. hora_tabela_preco -----
    if descartar_precos_aliases:
        n = db.session.execute(
            text('DELETE FROM hora_tabela_preco WHERE modelo_id = :a'),
            {'a': alias.id},
        ).rowcount
        contadores['hora_tabela_preco_descartadas'] += n or 0
    else:
        n = db.session.execute(
            text('UPDATE hora_tabela_preco SET modelo_id = :c WHERE modelo_id = :a'),
            {'c': canonico.id, 'a': alias.id},
        ).rowcount
        contadores['hora_tabela_preco_transferidas'] += n or 0

    # ----- 6. hora_tagplus_produto_map: UNIQUE em modelo_id -----
    map_alias = HoraTagPlusProdutoMap.query.filter_by(modelo_id=alias.id).first()
    if map_alias:
        map_canonico = HoraTagPlusProdutoMap.query.filter_by(
            modelo_id=canonico.id,
        ).first()
        if map_canonico:
            # Canonico ja tem map. Preserva info do alias como
            # HoraModeloAlias (TAGPLUS_CODIGO + TAGPLUS_PRODUTO_ID) e
            # DELETA o map duplicado.
            _criar_alias_se_nao_existe(
                modelo_id=canonico.id,
                nome_alias=map_alias.tagplus_produto_id,
                tipo=ALIAS_TIPO_TAGPLUS_PRODUTO_ID,
                operador=operador,
                observacao=(
                    f'Migrado de hora_tagplus_produto_map do modelo absorvido '
                    f'#{alias.id} ({alias.nome_modelo})'
                ),
                contadores=contadores,
            )
            if map_alias.tagplus_codigo:
                _criar_alias_se_nao_existe(
                    modelo_id=canonico.id,
                    nome_alias=map_alias.tagplus_codigo,
                    tipo=ALIAS_TIPO_TAGPLUS_CODIGO,
                    operador=operador,
                    observacao=(
                        f'Migrado de hora_tagplus_produto_map do modelo '
                        f'absorvido #{alias.id}'
                    ),
                    contadores=contadores,
                )
            db.session.delete(map_alias)
            contadores['hora_tagplus_produto_map_deletados'] += 1
        else:
            # Canonico nao tem map. UPDATE direto.
            map_alias.modelo_id = canonico.id
            contadores['hora_tagplus_produto_map_transferidos'] += 1
            # Tambem cria aliases para o codigo/id (redundancia controlada
            # — facilita resolver ate Fase 5 popular tudo via seed).
            _criar_alias_se_nao_existe(
                modelo_id=canonico.id,
                nome_alias=map_alias.tagplus_produto_id,
                tipo=ALIAS_TIPO_TAGPLUS_PRODUTO_ID,
                operador=operador,
                observacao='Auto-criado em merge a partir do tagplus map transferido',
                contadores=contadores,
            )
            if map_alias.tagplus_codigo:
                _criar_alias_se_nao_existe(
                    modelo_id=canonico.id,
                    nome_alias=map_alias.tagplus_codigo,
                    tipo=ALIAS_TIPO_TAGPLUS_CODIGO,
                    operador=operador,
                    observacao='Auto-criado em merge a partir do tagplus map transferido',
                    contadores=contadores,
                )

    # ----- 7. Preserva nome do alias como HoraModeloAlias NOME_LIVRE -----
    _criar_alias_se_nao_existe(
        modelo_id=canonico.id,
        nome_alias=alias.nome_modelo,
        tipo=ALIAS_TIPO_NOME_LIVRE,
        operador=operador,
        observacao=(
            f'Nome historico do modelo #{alias.id} mergeado em #{canonico.id}'
        ),
        contadores=contadores,
    )

    # ----- 8. Marca alias como inativo + merged_em_id -----
    alias.ativo = False
    alias.merged_em_id = canonico.id
    alias.merged_em = agora_utc_naive()
    alias.merged_por = operador
    db.session.flush()


def _criar_alias_se_nao_existe(
    *,
    modelo_id: int,
    nome_alias: str,
    tipo: str,
    operador: Optional[str],
    observacao: Optional[str],
    contadores: dict,
) -> None:
    """Idempotente: tenta criar; se UNIQUE existir e aponta para outro
    canonico, NAO sobrescreve (evita corromper mapeamentos historicos).
    Se aponta para o mesmo modelo, ignora silenciosamente."""
    if not nome_alias:
        return
    nome_str = str(nome_alias).strip()
    if not nome_str:
        return
    existente = (
        HoraModeloAlias.query
        .filter_by(tipo=tipo, nome_alias=nome_str)
        .first()
    )
    if existente:
        if existente.modelo_id != modelo_id:
            logger.warning(
                'Alias ja existe apontando para outro modelo: '
                'tipo=%s nome=%r modelo_atual=%s solicitado=%s. Mantido.',
                tipo, nome_str, existente.modelo_id, modelo_id,
            )
        return
    db.session.add(HoraModeloAlias(
        modelo_id=modelo_id,
        nome_alias=nome_str,
        tipo=tipo,
        criado_por=operador,
        observacao=observacao,
    ))
    contadores['aliases_criados'] += 1


def preview_merge(canonico_id: int, alias_ids: list[int]) -> dict:
    """Dry-run: retorna o que mudaria sem executar.

    Usado pela tela /hora/modelos/unificar para mostrar ao operador o
    impacto antes de confirmar.
    """
    if canonico_id in alias_ids:
        raise MergeError('Canonico nao pode estar entre os aliases.')

    canonico = HoraModelo.query.get(canonico_id)
    if not canonico:
        raise MergeError(f'Canonico {canonico_id} nao encontrado.')

    aliases = HoraModelo.query.filter(HoraModelo.id.in_(alias_ids)).all()
    if not aliases:
        raise MergeError('Nenhum alias valido.')

    preview = {
        'canonico': {
            'id': canonico.id,
            'nome_modelo': canonico.nome_modelo,
        },
        'aliases': [],
        'totais': {
            'motos': 0, 'pedido_itens': 0,
            'recebimento_conferencias': 0,
            'emprestimos': 0,
            'tabela_preco_descartadas': 0,
            'tagplus_maps_conflito': 0,
        },
    }

    for a in aliases:
        # Conta o que o merge vai tocar (read-only)
        n_moto = db.session.execute(
            text('SELECT COUNT(*) FROM hora_moto WHERE modelo_id = :a'),
            {'a': a.id},
        ).scalar() or 0
        n_pi = db.session.execute(
            text('SELECT COUNT(*) FROM hora_pedido_item WHERE modelo_id = :a'),
            {'a': a.id},
        ).scalar() or 0
        n_rc = db.session.execute(
            text(
                'SELECT COUNT(*) FROM hora_recebimento_conferencia '
                'WHERE modelo_id_conferido = :a'
            ),
            {'a': a.id},
        ).scalar() or 0
        n_em = db.session.execute(
            text('SELECT COUNT(*) FROM hora_emprestimo_moto WHERE modelo_id = :a'),
            {'a': a.id},
        ).scalar() or 0
        n_tp = db.session.execute(
            text('SELECT COUNT(*) FROM hora_tabela_preco WHERE modelo_id = :a'),
            {'a': a.id},
        ).scalar() or 0

        # Conflito tagplus_map: ambos (canonico e alias) tem map?
        canon_map = HoraTagPlusProdutoMap.query.filter_by(modelo_id=canonico.id).first()
        alias_map = HoraTagPlusProdutoMap.query.filter_by(modelo_id=a.id).first()
        conflito_tagplus = bool(canon_map and alias_map)

        preview['aliases'].append({
            'id': a.id,
            'nome_modelo': a.nome_modelo,
            'motos': n_moto,
            'pedido_itens': n_pi,
            'recebimento_conferencias': n_rc,
            'emprestimos': n_em,
            'tabela_preco': n_tp,
            'tagplus_map_conflito': conflito_tagplus,
            'alias_tagplus_codigo': alias_map.tagplus_codigo if alias_map else None,
            'alias_tagplus_id': alias_map.tagplus_produto_id if alias_map else None,
        })
        preview['totais']['motos'] += n_moto
        preview['totais']['pedido_itens'] += n_pi
        preview['totais']['recebimento_conferencias'] += n_rc
        preview['totais']['emprestimos'] += n_em
        preview['totais']['tabela_preco_descartadas'] += n_tp
        if conflito_tagplus:
            preview['totais']['tagplus_maps_conflito'] += 1

    return preview
