"""Limpa divergencias MODELO_DIFERENTE falsas (modelo conferido == canonico da NF).

Bug 2026-05-16 — `_redefinir_divergencias` tinha fallback textual que marcava
MODELO_DIFERENTE quando NF trazia texto livre nao resolvivel ('MOTO ELETR.
X12-10') e operador conferia o canonico correto ('X12-10'). Como a FK
`item_nf.moto.modelo_id` ja apontava para o canonico correto (resolvido no
import via get_or_create_moto), o match estava equivocado.

Esta migration:
  1. Para cada HoraConferenciaDivergencia tipo='MODELO_DIFERENTE':
     - resolve modelo conferido canonico (_seguir_canonico)
     - resolve modelo NF canonico via `item_nf.moto.modelo` (FK ja canonica),
       fallback resolver_modelo(texto NF) para legacy.
     - se ambos resolverem para o MESMO canonico: DELETA a divergencia
  2. Recalcula `tipo_divergencia` snapshot das conferencias afetadas.
  3. Recalcula status do recebimento (CONCLUIDO se nenhuma divergencia sobrar).

NAO cria aliases automaticos. Casos onde NF nao resolve canonico ficam para
operador resolver via /hora/modelos/pendencias (item 12 CLAUDE.md HORA).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from app.hora.models import (
    HoraConferenciaDivergencia,
    HoraModelo,
    HoraNfEntradaItem,
    HoraRecebimento,
    HoraRecebimentoConferencia,
    ALIAS_TIPO_NOME_NF,
)
from app.hora.services.modelo_resolver_service import (
    resolver_modelo,
    _seguir_canonico,
)


def main() -> None:
    app = create_app()
    with app.app_context():
        print('\n=== hora_42 fix divergencias MODELO_DIFERENTE falsas ===\n')

        # 1. Diagnostico (antes)
        total_antes = (
            HoraConferenciaDivergencia.query
            .filter_by(tipo='MODELO_DIFERENTE')
            .count()
        )
        print(f'Total divergencias MODELO_DIFERENTE antes: {total_antes}')

        if total_antes == 0:
            print('Nenhuma divergencia para analisar. Saindo.')
            return

        divs = (
            HoraConferenciaDivergencia.query
            .filter_by(tipo='MODELO_DIFERENTE')
            .all()
        )

        falsos_positivos: list[int] = []
        recebimentos_afetados: set[int] = set()
        conferencias_afetadas: set[int] = set()

        for div in divs:
            conf: HoraRecebimentoConferencia | None = (
                HoraRecebimentoConferencia.query.get(div.conferencia_id)
            )
            if not conf:
                continue
            rec = HoraRecebimento.query.get(conf.recebimento_id)
            if not rec:
                continue

            modelo_conf = (
                HoraModelo.query.get(conf.modelo_id_conferido)
                if conf.modelo_id_conferido else None
            )
            modelo_conf_canonico = _seguir_canonico(modelo_conf) if modelo_conf else None

            item_nf = HoraNfEntradaItem.query.filter_by(
                nf_id=rec.nf_id, numero_chassi=conf.numero_chassi,
            ).first()
            if not item_nf:
                # Sem item NF — divergencia provavel e CHASSI_EXTRA, nao MODELO. Skip.
                continue

            # FONTE DE VERDADE: FK item_nf.moto.modelo (canonico via
            # _seguir_canonico). NF JA RESOLVE canonico no import via
            # nf_entrada_service.criar_nf_com_itens -> get_or_create_moto.
            # So cai no fallback de resolver pelo texto se moto/modelo nulos
            # ou se aponta para sentinela DESCONHECIDO.
            modelo_nf_canonico = None
            if item_nf.moto and item_nf.moto.modelo:
                modelo_nf_canonico = _seguir_canonico(item_nf.moto.modelo)
                if modelo_nf_canonico and modelo_nf_canonico.nome_modelo == 'DESCONHECIDO':
                    modelo_nf_canonico = None
            if modelo_nf_canonico is None and item_nf.modelo_texto_original:
                modelo_nf_canonico = (
                    resolver_modelo(item_nf.modelo_texto_original, tipo=ALIAS_TIPO_NOME_NF)
                    or resolver_modelo(item_nf.modelo_texto_original)
                )

            if not modelo_conf_canonico:
                # Operador nao conferiu modelo — nao consideramos falso positivo.
                continue

            # Falso positivo: ambos resolvem MESMO canonico (texto diferente
            # mas mesma identidade). Deleta a divergencia.
            if modelo_nf_canonico and modelo_conf_canonico.id == modelo_nf_canonico.id:
                falsos_positivos.append(div.id)
                conferencias_afetadas.add(conf.id)
                recebimentos_afetados.add(rec.id)
                print(
                    f'  [MATCH-CANONICO] div={div.id} conf={conf.id} chassi={conf.numero_chassi} '
                    f'NF=\"{item_nf.modelo_texto_original}\" -> canonico {modelo_conf_canonico.nome_modelo!r}'
                )
                continue

            # NF nao resolve canonico — NAO deleta. Esses casos viram pendencia
            # em /hora/modelos/pendencias para operador decidir. (Decisao
            # usuario 2026-05-16: nao criar alias auto na migration.)
            if not modelo_nf_canonico:
                print(
                    f'  [PENDENTE] div={div.id} conf={conf.id} chassi={conf.numero_chassi} '
                    f'NF=\"{item_nf.modelo_texto_original}\" nao resolve canonico — '
                    f'mantida divergencia, operador resolve via /hora/modelos/pendencias'
                )

        if not falsos_positivos:
            print('\nNenhum falso positivo encontrado. Saindo sem alterar nada.')
            db.session.rollback()
            return

        print(
            f'\nFalsos positivos identificados: {len(falsos_positivos)} '
            f'/ {total_antes} divergencias MODELO_DIFERENTE'
        )
        print(f'Conferencias afetadas: {len(conferencias_afetadas)}')
        print(f'Recebimentos afetados: {len(recebimentos_afetados)}')

        # Deletar divergencias falsas
        deletadas = (
            HoraConferenciaDivergencia.query
            .filter(HoraConferenciaDivergencia.id.in_(falsos_positivos))
            .delete(synchronize_session=False)
        )
        db.session.flush()
        print(f'\nDivergencias MODELO_DIFERENTE deletadas: {deletadas}')

        # Recalcular tipo_divergencia snapshot e status do recebimento
        prioridade = ('CHASSI_EXTRA', 'MOTO_FALTANDO', 'MODELO_DIFERENTE', 'COR_DIFERENTE', 'AVARIA_FISICA')
        for conf_id in conferencias_afetadas:
            conf = HoraRecebimentoConferencia.query.get(conf_id)
            if not conf:
                continue
            divs_restantes = list(conf.divergencias)
            novo_snapshot = None
            if divs_restantes:
                tipos_restantes = {d.tipo for d in divs_restantes}
                for t in prioridade:
                    if t in tipos_restantes:
                        novo_snapshot = t
                        break
            conf.tipo_divergencia = novo_snapshot
            if not divs_restantes:
                conf.detalhe_divergencia = None

        db.session.flush()

        # Recalcular status do recebimento
        from app.utils.timezone import agora_utc_naive
        for rec_id in recebimentos_afetados:
            rec = HoraRecebimento.query.get(rec_id)
            if not rec:
                continue
            confs_ativas = [c for c in rec.conferencias if not c.substituida]
            houve = any(
                c.divergencias or c.tipo_divergencia for c in confs_ativas
            )
            if rec.status == 'COM_DIVERGENCIA' and not houve:
                rec.status = 'CONCLUIDO'
                if not rec.finalizado_em:
                    rec.finalizado_em = agora_utc_naive()
                print(f'  Recebimento {rec_id} reclassificado COM_DIVERGENCIA -> CONCLUIDO')

        db.session.commit()
        print('\n=== Migration concluida. ===\n')


if __name__ == '__main__':
    main()
