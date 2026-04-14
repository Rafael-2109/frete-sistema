# -*- coding: utf-8 -*-
"""
Historico de Match Extrato <-> Pagador — CarVia
================================================

Log append-only de eventos de conciliacao. A cada CarviaConciliacao criada
para fatura_cliente, registra UMA LINHA com a chave (tokens da descricao
da linha de cima, cnpj do pagador da fatura). Sem UPSERT — cada conciliacao
vira um evento separado. Contagem de ocorrencias e via COUNT(*) GROUP BY
na consulta.

UMA descricao pode fazer match com N CNPJs (e vice-versa). Nao ha UNIQUE.

Na hora de sugerir matches, `pontuar_documentos()` consulta os CNPJs
aprendidos para a descricao da linha e aplica boost multiplicativo (1.4x)
no score dos documentos do mesmo CNPJ.

Escopo: fatura_cliente apenas (CREDITO/recebimento). fatura_transportadora,
despesa, custo_entrega, receita podem ser adicionados no futuro reusando
o mesmo modelo (campo `tipo_documento` ja existe).

Ver R17 em `app/carvia/CLAUDE.md`.
"""

import logging

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.utils.timezone import agora_utc_naive
from app.carvia.services.financeiro.carvia_sugestao_service import _normalizar

logger = logging.getLogger(__name__)


class CarviaHistoricoMatchService:
    """Aprende padroes de match (descricao, cnpj_pagador) a partir de conciliacoes."""

    @staticmethod
    def tokens_chave(descricao):
        """Normaliza a descricao da linha em tokens ordenados.

        API publica — usada por `registrar_aprendizado`, `cnpjs_aprendidos`,
        `cnpjs_aprendidos_batch` e pelo script de backfill.

        Reusa `_normalizar()` do sugestao_service para manter consistencia
        com o scoring de NOME. Retorna string (tokens sort + join " ")
        para persistir como chave VARCHAR de match exato.

        Args:
            descricao: str|None — CarviaExtratoLinha.descricao (linha de cima)

        Returns:
            str: tokens ordenados concatenados com espaco, ou '' se vazio
        """
        tokens_set = _normalizar(descricao or '')
        if not tokens_set:
            return ''
        return ' '.join(sorted(tokens_set))

    @staticmethod
    def registrar_aprendizado(linha, tipo_documento, documento_id,
                               conciliacao_id=None):
        """Grava UM evento de aprendizado apos conciliacao bem-sucedida.

        Append-only: sempre INSERT, nunca UPDATE. UMA descricao pode ter
        N CNPJs associados como eventos distintos.

        **Isolado em SAVEPOINT** (fix B1): o INSERT roda dentro de
        `db.session.begin_nested()`. Se qualquer coisa falhar (IntegrityError,
        DataError, tabela ausente), faz rollback apenas do savepoint — a
        transacao externa do `conciliar()` fica intacta. Sem savepoint, um
        flush falho deixaria a session em estado "deactive" e o commit
        posterior da conciliacao explodiria, perdendo o trabalho do usuario.

        Nao-bloqueante: qualquer erro e logado e retorna False — nao re-raised.

        Args:
            linha: CarviaExtratoLinha — linha bancaria conciliada
            tipo_documento: str — apenas 'fatura_cliente' e processado no escopo atual
            documento_id: int — id do documento conciliado
            conciliacao_id: int|None — ponteiro solto para audit

        Returns:
            bool: True se inseriu, False se skip (sem erro)
        """
        # Escopo atual: fatura_cliente apenas
        if tipo_documento != 'fatura_cliente':
            return False

        from app.carvia.models import (
            CarviaFaturaCliente, CarviaHistoricoMatchExtrato,
        )

        # FIX B1+B2+M8: estrategia defensiva em 3 camadas:
        #
        # 1. Validacao rigorosa dos campos ANTES do add. Rejeita tudo que nao
        #    cabe nas constraints do DDL (VARCHAR(500), VARCHAR(20)). Filtra
        #    de antemao os casos conhecidos de falha — sem esta validacao, o
        #    flush falha e a session vira "pending_rollback" irrecuperavel.
        #
        # 2. `with db.session.begin_nested():` como CONTEXT MANAGER — garante
        #    rollback automatico em QUALQUER exception (SQLAlchemyError OU
        #    erros Python como TypeError, AttributeError). Se usassemos o
        #    padrao manual `sp = begin_nested(); sp.commit()/rollback()`,
        #    um erro nao-SQLAlchemy entre begin e except vazaria o savepoint.
        #
        # 3. NOTA sobre no_autoflush: foi removido porque o SQLAlchemy 2.x
        #    faz flush() INCONDICIONAL ao entrar em begin_nested() (ver
        #    session.py:_take_snapshot linha ~1087 — chama self.session.flush()
        #    direto, NAO self._autoflush(), ignorando o flag). Colocar
        #    begin_nested dentro de `with no_autoflush` era falsa protecao.
        #    O caller (conciliar) ja chama db.session.flush() em linha 408
        #    antes do hook; dirty objects remanescentes sao apenas atualizacoes
        #    de totais NUMERIC validos feitas por _atualizar_totais_*. Esses
        #    flushes passarao sem erro — se falharem, e bug do caller que
        #    o hook nao pode nem deve mascarar.
        try:
            fatura = db.session.get(CarviaFaturaCliente, documento_id)
            if not fatura or not fatura.cnpj_cliente:
                return False

            tokens = CarviaHistoricoMatchService.tokens_chave(linha.descricao)
            if not tokens:
                return False  # linha sem descricao util (so stopwords)

            cnpj = (fatura.cnpj_cliente or '').strip()
            if not cnpj:
                return False

            # Validacao rigorosa de tamanhos (evita StringDataRightTruncation).
            # CNPJ acima de 20 chars sinaliza dado corrompido — skip.
            if len(cnpj) > 20:
                logger.warning(
                    'registrar_aprendizado: cnpj fatura %s > 20 chars (%d) — skip',
                    fatura.id, len(cnpj),
                )
                return False

            # Truncamento defensivo (nao deveria ser necessario dado que
            # _normalizar e descricao do OFX ja sao <= 500, mas e barato).
            descricao_raw = (linha.descricao or '')[:500]
            descricao_tokens = tokens[:500]

            # Context manager garante rollback automatico em QUALQUER exception.
            # Protege contra: tabela ausente (migration nao rodada),
            # constraint nao previsto, connection drop, TypeError, etc.
            with db.session.begin_nested():
                novo = CarviaHistoricoMatchExtrato(
                    descricao_linha_raw=descricao_raw,
                    descricao_tokens=descricao_tokens,
                    cnpj_pagador=cnpj,
                    tipo_documento='fatura_cliente',
                    conciliacao_id=conciliacao_id,
                    registrado_em=agora_utc_naive(),
                )
                db.session.add(novo)
                # flush([novo]) isola o flush apenas do novo objeto.
                db.session.flush([novo])
                # Saida limpa do `with` faz commit do savepoint automaticamente.

            return True

        except SQLAlchemyError as e:
            # Nao-bloqueante: context manager ja fez rollback do savepoint.
            # Log warning e segue.
            logger.warning(
                'registrar_aprendizado falhou (SQLAlchemy): linha=%s doc=%s erro=%s',
                linha.id if linha else '?', documento_id, e,
            )
            return False
        except Exception as e:
            # Defense-in-depth: erros Python (TypeError, AttributeError, etc).
            # Context manager ja fez rollback. Log error (mais severo que warn
            # pois indica bug real, nao falha SQL esperada).
            logger.error(
                'registrar_aprendizado erro inesperado: linha=%s doc=%s erro=%s',
                linha.id if linha else '?', documento_id, e,
                exc_info=True,
            )
            return False

    @staticmethod
    def cnpjs_aprendidos(linha):
        """Retorna dict {cnpj: ocorrencias} via COUNT(*) GROUP BY.

        Chamado por callsites de `pontuar_documentos()` antes do score.
        Retorna dict vazio quando linha nao tem descricao util ou sem matches.

        Para listar_candidatos_extrato que processa N linhas em lote, usar
        `cnpjs_aprendidos_batch` — evita N+1 queries.

        Args:
            linha: CarviaExtratoLinha

        Returns:
            dict[str, int]: {cnpj_pagador: ocorrencias}, vazio se nao aprendeu
        """
        from app.carvia.models import CarviaHistoricoMatchExtrato

        tokens = CarviaHistoricoMatchService.tokens_chave(
            linha.descricao if linha else ''
        )
        if not tokens:
            return {}

        try:
            rows = db.session.query(
                CarviaHistoricoMatchExtrato.cnpj_pagador,
                db.func.count().label('ocorrencias'),
            ).filter(
                CarviaHistoricoMatchExtrato.descricao_tokens == tokens,
                CarviaHistoricoMatchExtrato.tipo_documento == 'fatura_cliente',
            ).group_by(
                CarviaHistoricoMatchExtrato.cnpj_pagador,
            ).all()
        except SQLAlchemyError as e:
            # Nao-bloqueante: se tabela nao existe (migration nao rodada),
            # retorna vazio e sugestao cai para comportamento original.
            logger.warning(
                'cnpjs_aprendidos falhou (tabela ausente?): linha=%s erro=%s',
                linha.id if linha else '?', e,
            )
            return {}

        return {
            row.cnpj_pagador: int(row.ocorrencias)
            for row in rows
            if row.cnpj_pagador
        }

    @staticmethod
    def cnpjs_aprendidos_batch(linhas):
        """Versao em lote de `cnpjs_aprendidos` — colapsa N queries em 1.

        FIX M2: usado por `listar_candidatos_extrato` para evitar N+1
        queries quando processando ate 50 linhas por chamada.

        Faz 1 unica query `IN (...) GROUP BY descricao_tokens, cnpj_pagador`
        e retorna dict indexado por linha.id.

        Args:
            linhas: list[CarviaExtratoLinha]

        Returns:
            dict[int, dict[str, int]]: {linha_id: {cnpj_pagador: ocorrencias}}.
            Linhas sem tokens uteis ou sem matches ficam com dict vazio.
        """
        from app.carvia.models import CarviaHistoricoMatchExtrato

        if not linhas:
            return {}

        # Mapeia linha_id -> tokens e coleta tokens unicos
        tokens_por_linha = {
            linha.id: CarviaHistoricoMatchService.tokens_chave(linha.descricao)
            for linha in linhas
        }
        tokens_unicos = {t for t in tokens_por_linha.values() if t}

        # Resultado default: dict vazio para cada linha
        resultado = {linha.id: {} for linha in linhas}

        if not tokens_unicos:
            return resultado

        try:
            rows = db.session.query(
                CarviaHistoricoMatchExtrato.descricao_tokens,
                CarviaHistoricoMatchExtrato.cnpj_pagador,
                db.func.count().label('ocorrencias'),
            ).filter(
                CarviaHistoricoMatchExtrato.descricao_tokens.in_(tokens_unicos),
                CarviaHistoricoMatchExtrato.tipo_documento == 'fatura_cliente',
            ).group_by(
                CarviaHistoricoMatchExtrato.descricao_tokens,
                CarviaHistoricoMatchExtrato.cnpj_pagador,
            ).all()
        except SQLAlchemyError as e:
            logger.warning(
                'cnpjs_aprendidos_batch falhou (tabela ausente?): %s', e,
            )
            return resultado

        # Agrupa por token: {token: {cnpj: ocorrencias}}
        por_token = {}
        for row in rows:
            if not row.cnpj_pagador:
                continue
            por_token.setdefault(row.descricao_tokens, {})[row.cnpj_pagador] = int(row.ocorrencias)

        # Mapeia para linha_id — FIX M11: copia rasa (dict()) evita que
        # duas linhas com mesma descricao_tokens compartilhem referencia
        # para o mesmo dict. Mesmo se o caller nunca mutar, e defensivo
        # contra bugs latentes futuros.
        for linha_id, tokens in tokens_por_linha.items():
            if tokens and tokens in por_token:
                resultado[linha_id] = dict(por_token[tokens])

        return resultado
