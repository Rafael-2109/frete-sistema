"""Propaga cidade/UF de um CarviaClienteEndereco (tipo DESTINO) para os
registros CarVia EM ABERTO vinculados, mais EmbarqueItem/EntregaMonitorada
(via helper R1-safe). Disparado ao editar o endereço (cliente_service).

Vínculos (ver docs/superpowers/specs/2026-06-23-carvia-propagacao-endereco-cce-design.md):
- CarviaCotacao: FK endereco_destino_id; atualiza override entrega_cidade/uf
  SÓ se já preenchidos (senão a FK já reflete o endereço novo).
- CarviaNf / CarviaOperacao: match por CNPJ (sem FK), status ATIVA / RASCUNHO.
- EmbarqueItem / EntregaMonitorada: via helper app/utils (R1).

NÃO commita (caller commita). Só escreve onde o valor difere.
"""
import logging

from app import db

logger = logging.getLogger(__name__)


class CarviaPropagacaoEnderecoService:

    @staticmethod
    def propagar(endereco_id):
        from app.carvia.models import (
            CarviaClienteEndereco, CarviaCotacao, CarviaNf, CarviaOperacao,
        )
        res = {'cotacoes': 0, 'nfs': 0, 'operacoes': 0,
               'embarque_itens': 0, 'entregas': 0}

        end = db.session.get(CarviaClienteEndereco, endereco_id)
        if not end or end.tipo != 'DESTINO':
            return res

        cidade = end.fisico_cidade
        uf = end.fisico_uf
        cnpj = end.cnpj

        # 1. Cotações (FK precisa) — override entrega_* só se já preenchido
        cot_ids = []
        cotacoes = CarviaCotacao.query.filter(
            CarviaCotacao.endereco_destino_id == endereco_id,
            CarviaCotacao.status.notin_(['RECUSADO', 'CANCELADO']),
        ).all()
        for cot in cotacoes:
            cot_ids.append(cot.id)
            mudou = False
            if cot.entrega_cidade and cot.entrega_cidade != cidade:
                cot.entrega_cidade = cidade
                mudou = True
            if cot.entrega_uf and cot.entrega_uf != uf:
                cot.entrega_uf = uf
                mudou = True
            if mudou:
                res['cotacoes'] += 1

        numeros_nf = []
        if cnpj:
            # 2. NFs ATIVAS do CNPJ
            for nf in CarviaNf.query.filter(
                CarviaNf.cnpj_destinatario == cnpj,
                CarviaNf.status == 'ATIVA',
            ).all():
                if nf.numero_nf:
                    numeros_nf.append(nf.numero_nf)
                mudou = False
                if nf.cidade_destinatario != cidade:
                    nf.cidade_destinatario = cidade
                    mudou = True
                if nf.uf_destinatario != uf:
                    nf.uf_destinatario = uf
                    mudou = True
                if mudou:
                    res['nfs'] += 1

            # 3. Operações (CTe) RASCUNHO do CNPJ
            for op in CarviaOperacao.query.filter(
                CarviaOperacao.cnpj_cliente == cnpj,
                CarviaOperacao.status == 'RASCUNHO',
            ).all():
                mudou = False
                if op.cidade_destino != cidade:
                    op.cidade_destino = cidade
                    mudou = True
                if op.uf_destino != uf:
                    op.uf_destino = uf
                    mudou = True
                if mudou:
                    res['operacoes'] += 1

        # 4/5. EmbarqueItem + EntregaMonitorada (helper R1-safe, lazy import)
        from app.utils.propagacao_endereco_carvia import propagar_cidade_uf_carvia
        externos = propagar_cidade_uf_carvia(numeros_nf, cot_ids, cidade, uf)
        res['embarque_itens'] = externos['embarque_itens']
        res['entregas'] = externos['entregas']

        db.session.flush()
        logger.info("Propagacao endereco #%s: %s", endereco_id, res)
        return res
