"""
CarviaFreteService — Orquestrador central de fretes CarVia
============================================================

Cria APENAS CarviaFrete na portaria. CarviaOperacao (CTe CarVia) e
CarviaSubcontrato (CTe Subcontrato) sao criados MANUALMENTE pelo usuario
quando lanca cada CTe. CarviaFrete e o eixo central.

Gatilho:
  1. Portaria deu saida + embarque tem itens CarVia com NF → gera CarviaFrete
  2. NF anexada apos portaria → atualiza CarviaFrete existente

Agregacao: EmbarqueItems com mesmo (cnpj_emitente + cnpj_destino) no embarque.

Calculo automatico ao criar CarviaFrete:
  valor_cotado (CUSTO):  DIRETA = rateio; FRACIONADA = tabela do item
  valor_venda  (VENDA):  tabela CarVia via CarviaTabelaService

Ref: app/carvia/INTEGRACAO_EMBARQUE.md
"""

import logging
from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Optional

from app import db

logger = logging.getLogger(__name__)


class CarviaFreteService:
    """Orquestrador central: cria CarviaFrete (eixo central) na portaria."""

    @staticmethod
    def lancar_frete_carvia(embarque_id: int, usuario: str) -> List[int]:
        """Gera fretes CarVia para um embarque (orquestrador unico).

        Para cada grupo (cnpj_emitente, cnpj_destino), cria:
          1. CarviaOperacao (CTe CarVia — preco VENDA)
          2. CarviaOperacaoNf (junctions com NFs)
          3. CarviaSubcontrato (preco CUSTO)
          4. CarviaFrete com operacao_id + subcontrato_id JA populados

        Chamado por:
          - portaria/routes.py: apos saida da portaria
          - embarque_carvia_service.py: quando NF e anexada apos portaria

        Returns:
            Lista de IDs dos CarviaFrete criados/atualizados.
        """
        try:
            return CarviaFreteService._processar(embarque_id, usuario)
        except Exception as e:
            # PostgreSQL: se houve erro SQL anterior na mesma transacao,
            # a session fica em estado "aborted" e qualquer query falha
            # com InFailedSqlTransaction. Rollback aqui destrava a session
            # para que hooks seguintes e o commit final da rota nao falhem
            # em cascata. (fix PYTHON-FLASK-MF)
            try:
                db.session.rollback()
            except Exception:
                pass

            # InFailedSqlTransaction indica que outro hook anterior falhou
            # silenciosamente sem rollback — nao e bug do CarVia. Logar
            # como warning para nao inundar Sentry com errors handled.
            msg_erro = str(e)
            if (
                'InFailedSqlTransaction' in msg_erro
                or 'current transaction is aborted' in msg_erro
            ):
                logger.warning(
                    "Frete CarVia nao gerado para embarque %s — transaction "
                    "abortada por erro SQL anterior no mesmo request: %s",
                    embarque_id, e,
                )
            else:
                logger.error(
                    "Erro ao lancar frete CarVia para embarque %s: %s",
                    embarque_id, e, exc_info=True,
                )
            return []

    # ------------------------------------------------------------------
    # Processamento principal
    # ------------------------------------------------------------------

    @staticmethod
    def _processar(embarque_id: int, usuario: str) -> List[int]:
        """Logica interna de processamento."""
        from app.embarques.models import Embarque, EmbarqueItem
        from app.carvia.models import CarviaFrete

        embarque = db.session.get(Embarque, embarque_id)
        if not embarque:
            return []

        # Validacao: embarque precisa de transportadora
        if not embarque.transportadora_id:
            logger.warning("Embarque %s sem transportadora vinculada", embarque_id)
            return []

        # Buscar itens CarVia ativos com NF preenchida (nao provisorios)
        itens_carvia = EmbarqueItem.query.filter(
            EmbarqueItem.embarque_id == embarque_id,
            EmbarqueItem.status == 'ativo',
            EmbarqueItem.separacao_lote_id.ilike('CARVIA-%'),
            EmbarqueItem.provisorio == False,  # noqa: E712 — so itens reais
            EmbarqueItem.nota_fiscal.isnot(None),
            EmbarqueItem.nota_fiscal != '',
        ).all()

        if not itens_carvia:
            return []

        # Agregar por (cnpj_emitente, cnpj_destino)
        grupos = defaultdict(list)
        for item in itens_carvia:
            cnpj_emit = CarviaFreteService._resolver_cnpj_emitente(item)
            cnpj_dest = item.cnpj_cliente or ''
            chave = (cnpj_emit.strip(), cnpj_dest.strip())
            grupos[chave].append(item)

        fretes_resultado = []
        itens_com_frete = []  # Apenas itens cujo frete foi criado/atualizado com sucesso

        # --------------------------------------------------------------
        # Fase B3 (2026-05-11): Cancelar fretes orfaos do embarque cujo
        # cnpj_destino nao bate com nenhum grupo atual.
        # Consequencia da Fase B2: quando NF importada tem CNPJ destino
        # diferente, item.cnpj_cliente e atualizado. O frete antigo (com
        # cnpj antigo) fica orfao — antes ficava pendurado e bloqueava
        # cancelamento da NF. Agora cancelamos automaticamente quando
        # ainda esta em PENDENTE; se ja avancou (CONFERIDO/FATURADO),
        # mantemos e logamos warning para o operador intervir.
        # Normaliza CNPJs (so digitos) para evitar falsos orfaos por
        # diferenca de formatacao entre frete antigo (legado) e itens.
        # --------------------------------------------------------------
        from app.utils.cnpj_utils import normalizar_cnpj as _norm_cnpj_b3
        chaves_atuais_norm = {
            (_norm_cnpj_b3(e), _norm_cnpj_b3(d)) for e, d in grupos.keys()
        }
        cnpjs_destinos_norm = {
            _norm_cnpj_b3(chave[1]) for chave in grupos.keys()
        }
        fretes_existentes_emb = CarviaFrete.query.filter(
            CarviaFrete.embarque_id == embarque_id,
            CarviaFrete.status != 'CANCELADO',
        ).all()
        for fr in fretes_existentes_emb:
            fr_emit_norm = _norm_cnpj_b3(fr.cnpj_emitente or '')
            fr_dest_norm = _norm_cnpj_b3(fr.cnpj_destino or '')
            chave_fr = (fr_emit_norm, fr_dest_norm)
            if chave_fr in chaves_atuais_norm:
                continue  # ainda relevante
            if fr_dest_norm in cnpjs_destinos_norm:
                continue  # ha grupo com mesmo cnpj_destino (emitente diferente)
            if fr.status in ('CONFERIDO', 'FATURADO'):
                logger.warning(
                    "Fase B3: frete #%s embarque %s cnpj_destino=%s ficou orfao "
                    "(itens atualizaram CNPJ para %s) mas status=%s — "
                    "nao cancelando. Operador deve revisar manualmente.",
                    fr.id, embarque_id, fr.cnpj_destino,
                    sorted(cnpjs_destinos_norm), fr.status,
                )
                continue
            # Caso de borda Fase B3-G6: frete orfao com filhos ja criados
            # (CarviaOperacao/CarviaSubcontrato vinculados). Nao cancelar
            # silenciosamente para nao deixar filhos pendurados — sinalizar
            # e deixar para revisao manual.
            if fr.operacao_id or fr.subcontrato_id:
                logger.warning(
                    "Fase B3: frete #%s orfao mas tem operacao_id=%s / "
                    "subcontrato_id=%s — NAO cancelando automaticamente. "
                    "Operador deve cancelar manualmente apos avaliar filhos.",
                    fr.id, fr.operacao_id, fr.subcontrato_id,
                )
                continue
            logger.info(
                "Fase B3: frete #%s embarque %s cnpj_destino=%s "
                "(emitente=%s) sem itens atuais — cancelando para "
                "permitir frete novo com cnpj atualizado.",
                fr.id, embarque_id, fr.cnpj_destino, fr.cnpj_emitente,
            )
            fr.status = 'CANCELADO'

        # Mapa cotacao_id → valor_final_aprovado (preco VENDA)
        cotacao_valores = CarviaFreteService._carregar_cotacao_valores(itens_carvia)
        # Mapa cotacao_id → dados comerciais (condicao pagamento, responsavel frete)
        cotacao_dados = CarviaFreteService._carregar_cotacao_dados(itens_carvia)

        for (cnpj_emitente, cnpj_destino), itens_grupo in grupos.items():
            # Dedup: checar frete existente PRIMEIRO
            existente = CarviaFrete.query.filter_by(
                embarque_id=embarque_id,
                cnpj_emitente=cnpj_emitente,
                cnpj_destino=cnpj_destino,
            ).first()

            if existente:
                if existente.status == 'CANCELADO':
                    # Deletar frete cancelado e recriar do zero
                    CarviaFreteService._limpar_frete_cancelado(existente)
                    # NAO dar continue — cair no _criar_frete_completo abaixo
                else:
                    # W11 (Sprint 3) + Fase B3 (2026-05-11):
                    # Antes bloqueava QUALQUER NF nova em frete existente.
                    # Agora:
                    #   - status PENDENTE:    substitui CSV in-place
                    #                         (recalcula peso/valor/qtd)
                    #   - status CONFERIDO+:  mantem bloqueio (toca conferencia)
                    nfs_no_frete = set(
                        (existente.numeros_nfs or '').split(',')
                    )
                    nfs_no_frete.discard('')
                    nfs_atuais = {
                        item.nota_fiscal for item in itens_grupo
                        if item.nota_fiscal
                    }
                    nfs_novas = nfs_atuais - nfs_no_frete
                    nfs_removidas = nfs_no_frete - nfs_atuais

                    if existente.status == 'PENDENTE' and (nfs_novas or nfs_removidas):
                        # Substituir CSV + recalcular totais a partir dos itens
                        # FIX peso_cubado (2026-05-21): max(bruto, cubado) (R3)
                        # com cubado resolvido da fonte de verdade quando o
                        # snapshot esta vazio. Ver _peso_frete_item.
                        peso_total = sum(
                            CarviaFreteService._peso_frete_item(it)
                            for it in itens_grupo
                        )
                        valor_total = sum(float(it.valor or 0) for it in itens_grupo)
                        nfs_csv = ','.join(sorted(nfs_atuais))
                        logger.info(
                            "Fase B3 W11: frete #%s PENDENTE - substituindo NFs "
                            "in-place: '%s' -> '%s' (+%s -%s) peso=%.2f valor=%.2f",
                            existente.id, existente.numeros_nfs, nfs_csv,
                            sorted(nfs_novas), sorted(nfs_removidas),
                            peso_total, valor_total,
                        )
                        existente.numeros_nfs = nfs_csv
                        existente.quantidade_nfs = len(nfs_atuais)
                        existente.peso_total = peso_total
                        existente.valor_total_nfs = valor_total
                    elif nfs_novas:
                        # Status avancado: manter bloqueio do W11 original
                        logger.warning(
                            "W11: BLOQUEADO NF tardia para frete #%s "
                            "(emitente=%s, destino=%s, status=%s). "
                            "NFs novas: %s. Cancele o frete (depois de "
                            "destravar a conferencia) e recrie.",
                            existente.id, cnpj_emitente, cnpj_destino,
                            existente.status, sorted(nfs_novas),
                        )
                        try:
                            from flask import g
                            if not hasattr(g, 'carvia_w11_bloqueios'):
                                g.carvia_w11_bloqueios = []
                            g.carvia_w11_bloqueios.append({
                                'frete_id': existente.id,
                                'cnpj_emitente': cnpj_emitente,
                                'cnpj_destino': cnpj_destino,
                                'nfs_bloqueadas': sorted(nfs_novas),
                                'status_frete': existente.status,
                            })
                        except Exception:
                            # Fora de request context — OK, so log
                            pass
                    else:
                        # Nenhuma NF nova nem removida — frete ja reflete.
                        logger.debug(
                            "Frete #%s: todas as NFs ja presentes, skip.",
                            existente.id,
                        )
                    # Marcar pedidos como EMBARCADO em todos os casos
                    # (frete existe e itens fisicamente sairam).
                    itens_com_frete.extend(itens_grupo)
                    fretes_resultado.append(existente.id)
                    continue

            # Criar operacao + subcontrato + frete (sequencia atomica)
            cot_id_grupo = next(
                (i.carvia_cotacao_id for i in itens_grupo if i.carvia_cotacao_id),
                None
            )
            valor_venda_cotacao = cotacao_valores.get(cot_id_grupo)
            dados_comerciais = cotacao_dados.get(cot_id_grupo)

            frete_id = CarviaFreteService._criar_frete_completo(
                embarque=embarque,
                cnpj_emitente=cnpj_emitente,
                cnpj_destino=cnpj_destino,
                itens=itens_grupo,
                usuario=usuario,
                valor_venda_cotacao=valor_venda_cotacao,
                cotacao_dados_comerciais=dados_comerciais,
            )
            if frete_id:
                fretes_resultado.append(frete_id)
                itens_com_frete.extend(itens_grupo)

        # Marcar APENAS pedidos de fretes com sucesso como EMBARCADO
        if itens_com_frete:
            CarviaFreteService._marcar_pedidos_embarcado(itens_com_frete, usuario)
            db.session.flush()
            logger.info(
                "Embarque %s: %d frete(s) CarVia gerado(s)/atualizado(s): %s",
                embarque_id, len(fretes_resultado), fretes_resultado
            )

        return fretes_resultado

    # ------------------------------------------------------------------
    # Criacao: APENAS CarviaFrete (eixo central)
    # CarviaOperacao e CarviaSubcontrato sao criados manualmente pelo usuario
    # ------------------------------------------------------------------

    @staticmethod
    def _criar_frete_completo(
        embarque,
        cnpj_emitente: str,
        cnpj_destino: str,
        itens: list,
        usuario: str,
        valor_venda_cotacao: float = None,
        cotacao_dados_comerciais: dict = None,
    ) -> Optional[int]:
        """Cria APENAS CarviaFrete com valores calculados.

        CarviaOperacao (CTe CarVia) e CarviaSubcontrato (CTe Subcontrato)
        NAO sao criados aqui — serao criados manualmente quando o usuario
        lancar cada CTe. CarviaFrete e o eixo central.
        """
        from app.carvia.models import CarviaFrete
        from app.utils.timezone import agora_utc_naive

        try:
            # --- Agregar totais do grupo ---
            # FIX peso_cubado (2026-05-21): usar max(bruto, cubado) (regra R3),
            # resolvendo o cubado da FONTE DE VERDADE (CarviaCotacaoMoto) quando
            # o snapshot do item esta vazio. Varios fluxos de criacao de
            # EmbarqueItem nao propagam peso_cubado, fazendo o frete cair no
            # peso bruto. Ver _peso_frete_item.
            peso_total = sum(
                CarviaFreteService._peso_frete_item(item) for item in itens
            )
            valor_total_nfs = sum(float(item.valor or 0) for item in itens)
            nfs = [item.nota_fiscal for item in itens if item.nota_fiscal]
            uf_destino = itens[0].uf_destino or ''
            cidade_destino = itens[0].cidade_destino or ''
            nome_destino = itens[0].cliente or ''
            nome_emitente = CarviaFreteService._resolver_nome_emitente(cnpj_emitente)

            # --- Calcular valor_venda (preco VENDA — tabela CarVia) ---
            if valor_venda_cotacao is not None:
                valor_venda_final = valor_venda_cotacao
            else:
                valor_venda_final = CarviaFreteService._calcular_venda(
                    uf_destino=uf_destino,
                    cidade_destino=cidade_destino,
                    peso=peso_total,
                    valor_mercadoria=valor_total_nfs,
                    cnpj_cliente=cnpj_destino,
                )

            # --- Calcular valor_cotado (preco CUSTO — tabela Nacom) ---
            valor_custo = CarviaFreteService._calcular_custo(
                embarque=embarque,
                itens=itens,
                peso_total=peso_total,
                valor_total=valor_total_nfs,
                operacao_id=None,  # sem CarviaOperacao na auto-criacao
            )

            # --- Criar CarviaFrete (eixo central, sem operacao/sub) ---
            frete = CarviaFrete(
                embarque_id=embarque.id,
                transportadora_id=embarque.transportadora_id,
                cnpj_emitente=cnpj_emitente,
                nome_emitente=nome_emitente,
                cnpj_destino=cnpj_destino,
                nome_destino=nome_destino,
                uf_destino=uf_destino,
                cidade_destino=cidade_destino,
                tipo_carga=embarque.tipo_carga or 'DIRETA',
                peso_total=peso_total,
                valor_total_nfs=valor_total_nfs,
                quantidade_nfs=len(nfs),
                numeros_nfs=','.join(nfs),
                valor_cotado=float(valor_custo) if valor_custo else 0,
                valor_considerado=float(valor_custo) if valor_custo else 0,
                valor_venda=float(valor_venda_final) if valor_venda_final else None,
                # operacao_id: NULL — criado quando usuario lancar CTe CarVia
                # subcontrato_id: NULL — criado quando usuario lancar CTe Subcontrato
                # fatura_cliente_id: preenchido retroativamente ao criar fatura
                # fatura_transportadora_id: preenchido retroativamente ao lancar CTe
                status='PENDENTE',
                criado_em=agora_utc_naive(),
                criado_por=usuario,
            )

            # Propagar condicao de pagamento e responsavel do frete da cotacao
            if cotacao_dados_comerciais:
                frete.condicao_pagamento = cotacao_dados_comerciais.get('condicao_pagamento')
                frete.prazo_dias = cotacao_dados_comerciais.get('prazo_dias')
                frete.responsavel_frete = cotacao_dados_comerciais.get('responsavel_frete')
                frete.percentual_remetente = cotacao_dados_comerciais.get('percentual_remetente')
                frete.percentual_destinatario = cotacao_dados_comerciais.get('percentual_destinatario')

            # Copiar snapshot tabela de frete
            CarviaFreteService._copiar_snapshot_tabela(frete, embarque, itens)

            db.session.add(frete)
            db.session.flush()

            # Vincular CarviaOperacao + FaturaCliente existentes pelas NFs
            CarviaFreteService._vincular_operacao_existente(frete, nfs)

            logger.info(
                "CarviaFrete criado: embarque=%s, emit=%s→dest=%s, "
                "custo=%s, venda=%s, %d NFs, op=%s, fat_cli=%s",
                embarque.id, cnpj_emitente, cnpj_destino,
                valor_custo, valor_venda_final, len(nfs),
                frete.operacao_id, frete.fatura_cliente_id,
            )

            return frete.id

        except Exception as e:
            logger.error(
                "Erro ao criar frete para grupo (%s, %s): %s",
                cnpj_emitente, cnpj_destino, e, exc_info=True
            )
            return None

    # ------------------------------------------------------------------
    # Limpeza de frete cancelado (para re-criacao)
    # ------------------------------------------------------------------

    @staticmethod
    def _limpar_frete_cancelado(frete) -> None:
        """Deleta CarviaFrete CANCELADO e filhos cancelados para liberar unique constraint.

        Chamado quando embarque e revinculado na portaria e o frete anterior
        foi cancelado. Deleta tudo para permitir re-criacao limpa.
        """
        from app.carvia.models import (
            CarviaOperacao, CarviaOperacaoNf, CarviaSubcontrato,
        )

        try:
            # Deletar subcontratos cancelados (via frete_id — novo path N:1)
            for sub in frete.subcontratos.all():
                if sub.status == 'CANCELADO' and not sub.fatura_transportadora_id:
                    db.session.delete(sub)

            # Fallback: subcontrato via deprecated FK (subcontrato_id)
            if frete.subcontrato_id:
                sub = db.session.get(CarviaSubcontrato, frete.subcontrato_id)
                if sub and sub.status == 'CANCELADO' and not sub.fatura_transportadora_id:
                    if not sub.frete_id:  # so deleta se nao ja deletado acima
                        db.session.delete(sub)

            # Deletar operacao cancelada (se nao faturada) + junctions
            if frete.operacao_id:
                op = db.session.get(CarviaOperacao, frete.operacao_id)
                if op and op.status == 'CANCELADO' and not op.fatura_cliente_id:
                    # Deletar junctions primeiro
                    CarviaOperacaoNf.query.filter_by(operacao_id=op.id).delete()
                    db.session.delete(op)

            # Deletar o frete cancelado
            db.session.delete(frete)
            db.session.flush()  # Libera unique constraint para re-criacao

            logger.info(
                "CarviaFrete #%s CANCELADO deletado para re-criacao "
                "(embarque=%s, emit=%s, dest=%s)",
                frete.id, frete.embarque_id,
                frete.cnpj_emitente, frete.cnpj_destino,
            )

        except Exception as e:
            logger.error("Erro ao limpar frete cancelado #%s: %s", frete.id, e)

    # ------------------------------------------------------------------
    # Atualizacao de frete existente (NF tardia) — REMOVIDO
    #
    # W11 (Sprint 3): NF tardia e agora PROIBIDA. O metodo
    # _atualizar_frete_existente foi removido porque nao e mais chamado
    # (review Sprint 3 L2: nao manter dead code). Se for preciso alterar
    # um frete existente, cancele e recrie explicitamente.
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Resolucao de peso para calculo do frete (cubado vs bruto)
    # ------------------------------------------------------------------

    @staticmethod
    def _peso_cubado_resolvido(item) -> float:
        """Resolve o peso cubado de um EmbarqueItem CarVia.

        Prioriza o snapshot (`item.peso_cubado`). Quando ausente — varios
        fluxos de criacao de EmbarqueItem nao propagam a cubagem (ver
        cotacao/routes.py e carvia/models/cotacao.py), fazendo o frete
        cair silenciosamente no peso bruto — resolve da FONTE DE VERDADE:

          1. item.peso_cubado, se > 0
          2. Item real (com NF): cubado proporcional aos veiculos DA NF,
             via EmbarqueCarViaService.calcular_cubado_por_modelos. Se nao
             resolver por modelos, retorna 0 (usa bruto) para NAO
             superestimar em cenarios multi-NF.
          3. Provisorio (sem NF): soma peso_cubado_total dos
             CarviaCotacaoMoto da cotacao (representa o saldo inteiro).
          4. 0.0 (sem cubagem -> caller usa peso bruto).

        Imports lazy (regra R2 do modulo CarVia).
        """
        cubado_snapshot = float(item.peso_cubado or 0)
        if cubado_snapshot > 0:
            return cubado_snapshot

        cot_id = getattr(item, 'carvia_cotacao_id', None)
        if not cot_id:
            return 0.0

        from app.carvia.services.documentos.embarque_carvia_service import (
            EmbarqueCarViaService,
        )

        nf_num = (item.nota_fiscal or '').strip() if item.nota_fiscal else ''

        # 2. Item real (com NF): cubado dos veiculos DA NF
        if nf_num:
            try:
                from app.carvia.models import CarviaNf
                nf = CarviaNf.query.filter_by(
                    numero_nf=nf_num, status='ATIVA',
                ).order_by(CarviaNf.id.desc()).first()
                if nf:
                    modelos = [v.modelo for v in nf.veiculos.all() if v.modelo]
                    if modelos:
                        cubado = EmbarqueCarViaService.calcular_cubado_por_modelos(
                            cot_id, modelos,
                        )
                        if cubado and cubado > 0:
                            logger.info(
                                "peso_cubado ausente no item (lote=%s NF=%s) — "
                                "resolvido via veiculos da NF: %.2f kg",
                                item.separacao_lote_id, nf_num, cubado,
                            )
                            return float(cubado)
                logger.warning(
                    "peso_cubado ausente no item real (lote=%s NF=%s) e nao "
                    "resolvido por modelos — frete usara peso bruto.",
                    item.separacao_lote_id, nf_num,
                )
            except Exception as e:
                logger.warning(
                    "Falha ao resolver cubado via NF %s: %s", nf_num, e,
                )
            return 0.0

        # 3. Provisorio (sem NF): total da cotacao
        try:
            from app.carvia.models import CarviaCotacaoMoto
            from sqlalchemy import func as _func
            total = float(
                db.session.query(
                    _func.coalesce(
                        _func.sum(CarviaCotacaoMoto.peso_cubado_total), 0
                    )
                ).filter(CarviaCotacaoMoto.cotacao_id == cot_id).scalar() or 0
            )
            if total > 0:
                logger.info(
                    "peso_cubado ausente no provisorio (lote=%s) — resolvido "
                    "via cotacao %s: %.2f kg",
                    item.separacao_lote_id, cot_id, total,
                )
                return total
        except Exception as e:
            logger.warning(
                "Falha ao resolver cubado via cotacao %s: %s", cot_id, e,
            )

        return 0.0

    @staticmethod
    def _peso_frete_item(item) -> float:
        """Peso a usar no calculo do frete: max(bruto, cubado) — regra R3.

        O cubado vem de `_peso_cubado_resolvido` (fonte de verdade, nao
        apenas o snapshot do item). Para motos o cubado domina; para carga
        sem cubagem cai no peso bruto.
        """
        bruto = float(item.peso or 0)
        cubado = CarviaFreteService._peso_cubado_resolvido(item)
        return max(bruto, cubado)

    # ------------------------------------------------------------------
    # Calculos de custo e venda
    # ------------------------------------------------------------------

    @staticmethod
    def _calcular_custo(
        embarque, itens, peso_total, valor_total, operacao_id: int = None,
    ) -> Optional[float]:
        """Calcula custo do frete subcontratado.

        DIRETA: rateio proporcional — frete_total_embarque * (peso_grupo / peso_embarque)
        FRACIONADA: calculo individual via CotacaoService.cotar_subcontrato()
        Fallback: CotacaoService para ambos se rateio nao disponivel.
        """
        # Tentar rateio para DIRETA
        if embarque.tipo_carga == 'DIRETA':
            resultado = CarviaFreteService._calcular_custo_rateio(
                embarque, peso_total, valor_total
            )
            if resultado is not None:
                return resultado

        # FRACIONADA ou fallback DIRETA: calculo via CotacaoService
        if operacao_id and embarque.transportadora_id:
            resultado = CarviaFreteService._calcular_custo_cotacao(
                operacao_id, embarque.transportadora_id
            )
            if resultado is not None:
                return resultado

        # Fallback final: calculo direto pela tabela do item (com fallback p/ embarque)
        if itens:
            return CarviaFreteService._calcular_custo_tabela_item(
                itens, peso_total, valor_total, embarque=embarque,
            )

        return None

    @staticmethod
    def _calcular_custo_rateio(embarque, peso_grupo, valor_grupo) -> Optional[float]:
        """Rateio DIRETA: frete_total_embarque * (peso_grupo / peso_embarque).

        Fix 2026-05-05: CalculadoraFrete retorna Decimal em valor_com_icms.
        Converter explicitamente para float antes de multiplicar pela
        proporcao (float) — caso contrario TypeError silencioso engole o
        calculo e valor_cotado fica zerado para todos os fretes DIRETA.
        """
        try:
            from app.utils.calculadora_frete import CalculadoraFrete
            from app.utils.tabela_frete_manager import TabelaFreteManager
            from app.embarques.models import EmbarqueItem

            tabela_dados = TabelaFreteManager.preparar_dados_tabela(embarque)
            if not tabela_dados.get('nome_tabela'):
                return None

            # FIX peso_cubado (2026-05-21): denominador do rateio coerente com
            # o numerador (peso_grupo = max(bruto, cubado) por item). Soma
            # _peso_frete_item dos itens CarVia do embarque, resolvendo o
            # cubado da fonte de verdade quando o snapshot esta vazio.
            # `embarque.peso_total` reflete peso FISICO e subestima o frete
            # em ate ~10x para motos.
            itens_emb_carvia = EmbarqueItem.query.filter(
                EmbarqueItem.embarque_id == embarque.id,
                EmbarqueItem.status == 'ativo',
                EmbarqueItem.separacao_lote_id.ilike('CARVIA-%'),
            ).all()
            peso_cubado_embarque = sum(
                CarviaFreteService._peso_frete_item(it) for it in itens_emb_carvia
            )
            # Fallback: se nenhum item tem cubado nem bruto, usar agregado fisico
            peso_embarque_real = peso_cubado_embarque or float(embarque.peso_total or 0)
            valor_embarque_real = float(embarque.valor_total or 0)

            # Fallback: se embarque sem peso/valor agregado, usar do grupo
            peso_calc = peso_embarque_real or float(peso_grupo or 0)
            valor_calc = valor_embarque_real or float(valor_grupo or 0)
            # Sem valor nao da pra cotar
            if not valor_calc:
                return None
            # Se peso=0 em ambos (raro, mas acontece em embarques que ainda
            # nao tiveram peso calculado), usar peso minimo positivo para
            # nao bloquear o calculo do frete minimo da tabela
            if not peso_calc:
                peso_calc = 1.0

            calc = CalculadoraFrete()
            resultado = calc.calcular_frete_unificado(
                peso=peso_calc,
                valor_mercadoria=valor_calc,
                tabela_dados=tabela_dados,
                cidade=None,
            )
            if not resultado or 'valor_com_icms' not in resultado:
                return None

            # CalculadoraFrete retorna Decimal — converter para float
            frete_total = float(resultado['valor_com_icms'])
            if frete_total <= 0:
                return None

            # Proporcao de peso: se embarque sem peso agregado, calculo
            # ficou para o grupo inteiro (proporcao=1)
            if peso_embarque_real > 0 and peso_grupo:
                proporcao = float(peso_grupo) / peso_embarque_real
            else:
                proporcao = 1.0

            return round(frete_total * proporcao, 2)

        except Exception as e:
            logger.warning("Erro ao calcular rateio DIRETA: %s", e, exc_info=True)

        return None

    @staticmethod
    def _calcular_custo_cotacao(operacao_id: int, transportadora_id: int) -> Optional[float]:
        """Calcula custo via CotacaoService.cotar_subcontrato() (FRACIONADA ou fallback)."""
        try:
            from app.carvia.services.pricing.cotacao_service import CotacaoService
            svc = CotacaoService()
            resultado = svc.cotar_subcontrato(
                operacao_id=operacao_id,
                transportadora_id=transportadora_id,
            )
            if resultado and resultado.get('sucesso'):
                return resultado.get('valor_cotado', 0)
        except Exception as e:
            logger.warning("Erro ao cotar custo via CotacaoService: %s", e)
        return None

    @staticmethod
    def _calcular_custo_tabela_item(itens, peso_total, valor_total, embarque=None) -> Optional[float]:
        """Fallback: calcula custo pela tabela do primeiro item do grupo.

        Fix 2026-05-05: itens CarVia tipicamente tem `tabela_nome_tabela=NULL`
        (apenas o Embarque tem snapshot de tabela em DIRETA). Quando o item
        nao tem tabela, fazer fallback para a tabela do embarque para garantir
        que valor_cotado seja preenchido.
        """
        try:
            from app.utils.calculadora_frete import CalculadoraFrete
            from app.utils.tabela_frete_manager import TabelaFreteManager

            item = itens[0]
            tabela_dados = TabelaFreteManager.preparar_dados_tabela(item)

            # Fallback: usar tabela do embarque se item nao tem
            if not tabela_dados.get('nome_tabela') and embarque is not None:
                tabela_dados = TabelaFreteManager.preparar_dados_tabela(embarque)

            if not tabela_dados.get('nome_tabela'):
                return None
            if not peso_total or not valor_total:
                return None

            calc = CalculadoraFrete()
            resultado = calc.calcular_frete_unificado(
                peso=float(peso_total),
                valor_mercadoria=float(valor_total),
                tabela_dados=tabela_dados,
                cidade=None,
            )
            if resultado and 'valor_com_icms' in resultado:
                return round(float(resultado['valor_com_icms']), 2)

        except Exception as e:
            logger.warning("Erro ao calcular custo por tabela do item: %s", e, exc_info=True)

        return None

    @staticmethod
    def _calcular_venda(uf_destino, cidade_destino, peso, valor_mercadoria, cnpj_cliente) -> Optional[float]:
        """Calcula preco de venda pela tabela CarVia."""
        try:
            from app.carvia.services.pricing.carvia_tabela_service import CarviaTabelaService
            svc = CarviaTabelaService()

            opcoes = svc.cotar_carvia(
                uf_origem='SP',
                uf_destino=uf_destino,
                cidade_destino=cidade_destino,
                peso=peso,
                valor_mercadoria=valor_mercadoria,
                cnpj_cliente=cnpj_cliente,
            )

            if opcoes and len(opcoes) > 0:
                return opcoes[0].get('valor_frete', 0)

        except Exception as e:
            logger.warning("Erro ao calcular venda frete CarVia: %s", e)

        return None

    # ------------------------------------------------------------------
    # Vinculacao com entidades existentes
    # ------------------------------------------------------------------

    @staticmethod
    def _vincular_operacao_existente(frete, nfs_numeros: list) -> None:
        """Busca CarviaOperacao existente pelas NFs e vincula ao frete.

        Quando as NFs do frete ja possuem um CTe CarVia (CarviaOperacao)
        vinculado via CarviaOperacaoNf, preenche:
          - frete.operacao_id
          - frete.fatura_cliente_id (se operacao ja tiver fatura)
          - frete.valor_venda (atualiza com cte_valor da operacao, se disponivel)
        """
        if not nfs_numeros:
            return

        try:
            from app.carvia.models import CarviaNf, CarviaOperacaoNf, CarviaOperacao

            # 1. Buscar IDs das CarviaNf ativas por numero
            nf_ids = [
                nf_id for (nf_id,) in
                db.session.query(CarviaNf.id).filter(
                    CarviaNf.numero_nf.in_(nfs_numeros),
                    CarviaNf.status == 'ATIVA',
                ).all()
            ]
            if not nf_ids:
                return

            # 2. Buscar CarviaOperacao vinculadas a essas NFs (via junction)
            #    Priorizar pela que cobre MAIS NFs do frete (nao apenas a mais recente)
            from sqlalchemy import func

            op_scores = (
                db.session.query(
                    CarviaOperacaoNf.operacao_id,
                    func.count(CarviaOperacaoNf.nf_id).label('cnt'),
                )
                .filter(CarviaOperacaoNf.nf_id.in_(nf_ids))
                .group_by(CarviaOperacaoNf.operacao_id)
                .order_by(
                    func.count(CarviaOperacaoNf.nf_id).desc(),  # maior cobertura
                    CarviaOperacaoNf.operacao_id.desc(),         # desempate: mais recente
                )
                .all()
            )
            if not op_scores:
                return

            # 3. Buscar a primeira operacao ativa (nao cancelada)
            operacao = None
            for op_id, _cnt in op_scores:
                candidata = db.session.get(CarviaOperacao, op_id)
                if candidata and candidata.status != 'CANCELADO':
                    operacao = candidata
                    break

            if not operacao:
                return

            # 4. Vincular operacao ao frete
            frete.operacao_id = operacao.id

            # Atualizar valor_venda com cte_valor da operacao se disponivel
            if operacao.cte_valor and not frete.valor_venda:
                frete.valor_venda = float(operacao.cte_valor)

            # 5. Propagar fatura_cliente_id se operacao ja tiver fatura
            if operacao.fatura_cliente_id:
                frete.fatura_cliente_id = operacao.fatura_cliente_id

            logger.info(
                "CarviaFrete #%s vinculado a operacao existente %s "
                "(fatura_cliente_id=%s) via NFs %s",
                frete.id, operacao.cte_numero,
                operacao.fatura_cliente_id, nfs_numeros,
            )

        except Exception as e:
            logger.warning(
                "Erro ao vincular operacao existente para frete #%s: %s",
                frete.id, e,
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _carregar_cotacao_valores(itens_carvia: list) -> Dict[int, float]:
        """Carrega mapa cotacao_id → valor_final_aprovado para preco de VENDA."""
        from app.carvia.models import CarviaCotacao
        valores = {}
        for item in itens_carvia:
            cot_id = item.carvia_cotacao_id
            if cot_id and cot_id not in valores:
                cot = db.session.get(CarviaCotacao, cot_id)
                if cot and cot.valor_final_aprovado:
                    valores[cot_id] = float(cot.valor_final_aprovado)
        return valores

    @staticmethod
    def _carregar_cotacao_dados(itens_carvia: list) -> Dict[int, dict]:
        """Carrega mapa cotacao_id → dados comerciais para propagacao downstream."""
        from app.carvia.models import CarviaCotacao
        dados = {}
        for item in itens_carvia:
            cot_id = item.carvia_cotacao_id
            if cot_id and cot_id not in dados:
                cot = db.session.get(CarviaCotacao, cot_id)
                if cot:
                    dados[cot_id] = {
                        'condicao_pagamento': cot.condicao_pagamento,
                        'prazo_dias': cot.prazo_dias,
                        'responsavel_frete': cot.responsavel_frete,
                        'percentual_remetente': float(cot.percentual_remetente) if cot.percentual_remetente is not None else None,
                        'percentual_destinatario': float(cot.percentual_destinatario) if cot.percentual_destinatario is not None else None,
                    }
        return dados

    @staticmethod
    def _marcar_pedidos_embarcado(itens_carvia: list, usuario: str):
        """Promove pedidos CarVia para FATURADO apos frete gerado na portaria.

        Fluxo CarVia (P12 revisado, 2026-04-24):
            ABERTO -> COTADO -> FATURADO
            (EMBARCADO deixou de ser status. O fato fisico da saida da
            portaria aparece via property `badge_embarcado` derivada de
            `Embarque.data_embarque` + `ControlePortaria.hora_saida` —
            ortogonal ao ciclo fiscal do pedido.)

        Este metodo e chamado pelo hook da portaria. Se o pedido ja nao
        estiver FATURADO (ex: NF anexada apenas no momento da saida),
        garante transicao ABERTO/COTADO -> FATURADO.
        """
        from app.carvia.models import CarviaPedido, CarviaPedidoItem, CarviaNf

        # Coletar NFs dos itens CarVia
        nfs = {item.nota_fiscal for item in itens_carvia if item.nota_fiscal}
        if not nfs:
            return

        # Filtrar para NFs que EXISTEM em CarviaNf com status='ATIVA'.
        # Sem isso (auto-revisao code-review 2026-04-24), poderiamos promover
        # CarviaPedido para FATURADO usando numero_nf livre sem NF fiscal
        # real no sistema, causando inconsistencia.
        nfs_ativas_set = {
            str(nf.numero_nf) for nf in CarviaNf.query.filter(
                CarviaNf.numero_nf.in_([str(n) for n in nfs]),
                CarviaNf.status == 'ATIVA',
            ).all()
        }
        if not nfs_ativas_set:
            return

        # Buscar pedidos com NFs ATIVAS (excluir cancelados e ja FATURADO)
        pedidos_itens = CarviaPedidoItem.query.join(
            CarviaPedido,
            CarviaPedidoItem.pedido_id == CarviaPedido.id
        ).filter(
            CarviaPedidoItem.numero_nf.in_(nfs_ativas_set),
            CarviaPedido.status.notin_(['FATURADO', 'CANCELADO']),
        ).all()

        pedidos_atualizados = set()
        for pi in pedidos_itens:
            if pi.pedido_id in pedidos_atualizados:
                continue
            pedido = db.session.get(CarviaPedido, pi.pedido_id)
            if not pedido or pedido.status in ('FATURADO', 'CANCELADO'):
                continue

            logger.info(
                'CarviaPedido %s %s -> FATURADO (saida portaria, NF %s ATIVA)',
                pedido.numero_pedido, pedido.status, pi.numero_nf,
            )
            pedido.status = 'FATURADO'
            pedidos_atualizados.add(pi.pedido_id)

    @staticmethod
    def _resolver_cnpj_emitente(item) -> str:
        """Resolve CNPJ emitente da NF a partir do EmbarqueItem.

        Para CarVia, o emitente NAO e a Nacom — e o terceiro que emitiu a NF.
        Tenta buscar na CarviaNf pelo numero_nf.
        """
        if not item.nota_fiscal:
            return ''

        try:
            from app.carvia.models import CarviaNf
            nf = CarviaNf.query.filter_by(
                numero_nf=item.nota_fiscal,
                status='ATIVA',
            ).first()
            if nf and nf.cnpj_emitente:
                return nf.cnpj_emitente
        except Exception:
            pass

        # Fallback: buscar cnpj_emitente via CarviaPedidoItem → CarviaPedido → CarviaCotacao
        # Se CarviaNf nao existe (NF ainda nao importada), tentar via cotacao
        try:
            from app.carvia.models import CarviaPedidoItem, CarviaCotacao
            ped_item = CarviaPedidoItem.query.filter_by(
                numero_nf=item.nota_fiscal,
            ).first()
            if ped_item:
                pedido = ped_item.pedido
                if pedido and pedido.cotacao_id:
                    cotacao = db.session.get(CarviaCotacao, pedido.cotacao_id)
                    if cotacao and cotacao.cnpj_origem:
                        return cotacao.cnpj_origem
        except Exception:
            pass

        # Ultimo fallback: vazio (evita usar cnpj_destino como cnpj_emitente)
        logger.warning(
            "Nao foi possivel resolver cnpj_emitente para NF %s — "
            "CarviaNf nao existe e cotacao nao tem cnpj_origem",
            item.nota_fiscal
        )
        return ''

    @staticmethod
    def _resolver_nome_emitente(cnpj_emitente: str) -> str:
        """Resolve nome do emitente pelo CNPJ."""
        if not cnpj_emitente:
            return ''
        try:
            from app.carvia.models import CarviaNf
            nf = CarviaNf.query.filter_by(
                cnpj_emitente=cnpj_emitente,
                status='ATIVA',
            ).first()
            if nf and nf.nome_emitente:
                return nf.nome_emitente
        except Exception:
            pass
        return ''

    @staticmethod
    def _copiar_snapshot_tabela(frete, embarque, itens):
        """Copia snapshot da tabela de frete para o CarviaFrete.

        DIRETA: copia do Embarque.
        FRACIONADA: copia do primeiro EmbarqueItem do grupo.
        """
        fonte = embarque if embarque.tipo_carga == 'DIRETA' else (itens[0] if itens else embarque)

        campos = [
            'tabela_nome_tabela', 'tabela_valor_kg', 'tabela_percentual_valor',
            'tabela_frete_minimo_valor', 'tabela_frete_minimo_peso', 'tabela_icms',
            'tabela_percentual_gris', 'tabela_pedagio_por_100kg', 'tabela_valor_tas',
            'tabela_percentual_adv', 'tabela_percentual_rca', 'tabela_valor_despacho',
            'tabela_valor_cte', 'tabela_icms_incluso', 'tabela_gris_minimo',
            'tabela_adv_minimo', 'tabela_icms_proprio',
        ]

        for campo in campos:
            valor = getattr(fonte, campo, None)
            if valor is not None:
                setattr(frete, campo, valor)

        # icms_destino separado
        frete.tabela_icms_destino = getattr(fonte, 'icms_destino', None)
