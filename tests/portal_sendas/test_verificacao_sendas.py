"""Regressao da otimizacao de `_buscar_protocolos_nao_confirmados` (2026-06-16).

A query antes carregava TODAS as NFs entregues do sistema em memoria (~17k) e
fazia N+1 (`.first()` por protocolo). A versao otimizada faz 1 query de
Separacoes candidatas e consulta APENAS as NFs candidatas. Estes testes garantem
que o COMPORTAMENTO foi preservado:
- protocolo cuja NF ja foi entregue e' EXCLUIDO;
- protocolo com NF pendente (ou sem NF) e' INCLUIDO;
- multiplas linhas do mesmo protocolo geram 1 unica entrada.
"""

from __future__ import annotations

import uuid
from datetime import date


def _sfx() -> str:
    return uuid.uuid4().hex[:6]


def _criar_sep(db, protocolo, numero_nf):
    from app.separacao.models import Separacao
    sep = Separacao(
        separacao_lote_id=f'LOTE-{_sfx()}',
        num_pedido=f'PED-{_sfx()}',
        cod_uf='SP',
        nome_cidade='SAO PAULO',
        cnpj_cpf='12345678000100',
        raz_social_red='Cliente Teste',
        protocolo=protocolo,
        agendamento=date(2026, 4, 20),
        agendamento_confirmado=False,
        sincronizado_nf=False,
        numero_nf=numero_nf,
    )
    db.session.add(sep)
    db.session.flush()
    return sep


def _criar_entrega(db, numero_nf, entregue=False, status_finalizacao=None):
    from app.monitoramento.models import EntregaMonitorada
    em = EntregaMonitorada(
        numero_nf=numero_nf,
        origem='NACOM',
        cliente='Cliente Teste',
        entregue=entregue,
        status_finalizacao=status_finalizacao,
    )
    db.session.add(em)
    db.session.flush()
    return em


class TestBuscarProtocolosNaoConfirmados:

    def test_exclui_nf_entregue_e_inclui_pendente(self, db):
        from app.portal.sendas.service_verificacao_sendas import (
            VerificacaoSendasService,
        )
        prot_entregue = f'PROT-ENT-{_sfx()}'
        prot_pendente = f'PROT-PEND-{_sfx()}'
        nf_ent = f'NF-ENT-{_sfx()}'
        nf_pend = f'NF-PEND-{_sfx()}'

        _criar_sep(db, protocolo=prot_entregue, numero_nf=nf_ent)
        _criar_entrega(db, numero_nf=nf_ent, entregue=True)
        _criar_sep(db, protocolo=prot_pendente, numero_nf=nf_pend)
        _criar_entrega(db, numero_nf=nf_pend, entregue=False)
        db.session.flush()

        protocolos = VerificacaoSendasService()._buscar_protocolos_nao_confirmados()
        nomes = {p['protocolo'] for p in protocolos}

        assert prot_pendente in nomes      # NF pendente -> verificar
        assert prot_entregue not in nomes  # NF entregue -> excluido (FIX BUG 6c)

    def test_exclui_por_status_finalizacao_entregue(self, db):
        from app.portal.sendas.service_verificacao_sendas import (
            VerificacaoSendasService,
        )
        prot = f'PROT-FIN-{_sfx()}'
        nf = f'NF-FIN-{_sfx()}'
        _criar_sep(db, protocolo=prot, numero_nf=nf)
        _criar_entrega(db, numero_nf=nf, entregue=False,
                       status_finalizacao='Entregue')
        db.session.flush()

        protocolos = VerificacaoSendasService()._buscar_protocolos_nao_confirmados()
        assert prot not in {p['protocolo'] for p in protocolos}

    def test_protocolo_sem_nf_incluido(self, db):
        from app.portal.sendas.service_verificacao_sendas import (
            VerificacaoSendasService,
        )
        prot = f'PROT-SEMNF-{_sfx()}'
        _criar_sep(db, protocolo=prot, numero_nf=None)
        db.session.flush()

        protocolos = VerificacaoSendasService()._buscar_protocolos_nao_confirmados()
        assert prot in {p['protocolo'] for p in protocolos}

    def test_um_registro_por_protocolo(self, db):
        from app.portal.sendas.service_verificacao_sendas import (
            VerificacaoSendasService,
        )
        prot = f'PROT-DUP-{_sfx()}'
        nf = f'NF-DUP-{_sfx()}'
        # Mesmo protocolo em 2 linhas (produtos diferentes) -> 1 entrada
        _criar_sep(db, protocolo=prot, numero_nf=nf)
        _criar_sep(db, protocolo=prot, numero_nf=nf)
        db.session.flush()

        protocolos = VerificacaoSendasService()._buscar_protocolos_nao_confirmados()
        encontrados = [p for p in protocolos if p['protocolo'] == prot]
        assert len(encontrados) == 1
