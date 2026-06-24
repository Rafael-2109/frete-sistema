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


def _criar_fila(db, protocolo, documento_origem, tipo_origem='lote',
                cnpj='12345678000100', status='processado'):
    from app.portal.models_fila_sendas import FilaAgendamentoSendas
    item = FilaAgendamentoSendas(
        tipo_origem=tipo_origem,
        documento_origem=documento_origem,
        cnpj=cnpj,
        num_pedido=f'PED-{_sfx()}',
        cod_produto=f'PROD-{_sfx()}',
        quantidade=10,
        data_expedicao=date(2026, 4, 19),
        data_agendamento=date(2026, 4, 20),
        protocolo=protocolo,
        status=status,
    )
    db.session.add(item)
    db.session.flush()
    return item


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


class TestFaxinaFila:
    """Faxina automatica (2026-06-24): a cada verificacao, remove itens
    'processado' antigos (>30d) da fila, que so era limpa por acao manual e
    havia acumulado ~13k registros. Itens recentes sao preservados.
    """

    def test_processar_remove_processados_antigos_preserva_recentes(self, db):
        import pandas as pd
        from io import BytesIO
        from datetime import timedelta
        from app.utils.timezone import agora_utc_naive
        from app.portal.models_fila_sendas import FilaAgendamentoSendas
        from app.portal.sendas.service_verificacao_sendas import (
            VerificacaoSendasService,
        )

        prot_antigo = f'PROT-OLD-{_sfx()}'
        prot_novo = f'PROT-NEW-{_sfx()}'
        antigo = _criar_fila(db, protocolo=prot_antigo, documento_origem=f'L-{_sfx()}')
        antigo.processado_em = agora_utc_naive() - timedelta(days=40)
        novo = _criar_fila(db, protocolo=prot_novo, documento_origem=f'L-{_sfx()}')
        novo.processado_em = agora_utc_naive() - timedelta(days=2)
        db.session.flush()

        # Excel minimo valido (colunas obrigatorias) — nenhum protocolo casa
        df = pd.DataFrame([{'ID': 'X', 'Status': 'Agendado', 'Obs. Criação': 'X'}])
        buf = BytesIO()
        df.to_excel(buf, index=False)

        resultado = VerificacaoSendasService().processar_planilha_verificacao(buf.getvalue())
        assert resultado['sucesso'] is True

        restantes = {
            f.protocolo
            for f in FilaAgendamentoSendas.query.filter_by(status='processado').all()
        }
        assert prot_antigo not in restantes  # >30d -> removido pela faxina
        assert prot_novo in restantes        # recente -> preservado

    def test_limpar_processados_retorna_contagem(self, db):
        from datetime import timedelta
        from app.utils.timezone import agora_utc_naive
        from app.portal.models_fila_sendas import FilaAgendamentoSendas

        item = _criar_fila(db, protocolo=f'PROT-CNT-{_sfx()}',
                           documento_origem=f'L-{_sfx()}')
        item.processado_em = agora_utc_naive() - timedelta(days=40)
        db.session.flush()

        removidos = FilaAgendamentoSendas.limpar_processados(dias=30)
        assert removidos >= 1


class TestFilaAgendamentoSendas:
    """Regressao do N+1 + duplicacao na fonte 3 (fila) que travava a
    verificacao (2026-06-24). Antes: o set de dedupe nao era atualizado dentro
    do loop, entao N registros do MESMO protocolo geravam N entradas e N queries
    individuais a Separacao. Com ~13k registros 'processado' acumulados isso
    deixava a tela "processando eternamente".
    """

    def test_fila_um_registro_por_protocolo(self, db):
        from app.portal.sendas.service_verificacao_sendas import (
            VerificacaoSendasService,
        )
        prot = f'PROT-FILA-{_sfx()}'
        lote = f'LOTE-{_sfx()}'
        # Mesmo protocolo em 3 linhas da fila -> deve gerar 1 unica entrada
        _criar_fila(db, protocolo=prot, documento_origem=lote)
        _criar_fila(db, protocolo=prot, documento_origem=lote)
        _criar_fila(db, protocolo=prot, documento_origem=lote)
        db.session.flush()

        protocolos = VerificacaoSendasService()._buscar_protocolos_nao_confirmados()
        encontrados = [p for p in protocolos if p['protocolo'] == prot]
        assert len(encontrados) == 1

    def test_fila_enriquece_com_separacao_em_lote(self, db):
        from app.portal.sendas.service_verificacao_sendas import (
            VerificacaoSendasService,
        )
        from app.separacao.models import Separacao
        prot = f'PROT-ENR-{_sfx()}'
        lote = f'LOTE-ENR-{_sfx()}'
        # Separacao ja faturada (sincronizado_nf=True) NAO entra na fonte 1,
        # mas a fila aponta para o lote -> fonte 3 enriquece via batch.
        sep = Separacao(
            separacao_lote_id=lote,
            num_pedido=f'PED-{_sfx()}',
            cod_uf='SP',
            nome_cidade='CAMPINAS',
            cnpj_cpf='99887766000155',
            raz_social_red='Cliente Fila',
            protocolo=f'OUTRO-{_sfx()}',
            sincronizado_nf=True,
        )
        db.session.add(sep)
        db.session.flush()
        _criar_fila(db, protocolo=prot, documento_origem=lote, cnpj='99887766000155')
        db.session.flush()

        protocolos = VerificacaoSendasService()._buscar_protocolos_nao_confirmados()
        encontrados = [p for p in protocolos if p['protocolo'] == prot]
        assert len(encontrados) == 1
        assert encontrados[0]['raz_social'] == 'Cliente Fila'
        assert encontrados[0]['nome_cidade'] == 'CAMPINAS'
        assert encontrados[0]['cod_uf'] == 'SP'

    def test_fila_nao_duplica_protocolo_da_fonte_separacao(self, db):
        """Protocolo ja presente na fonte 1 (Separacao pendente) nao deve ser
        re-adicionado pela fonte 3 (fila)."""
        from app.portal.sendas.service_verificacao_sendas import (
            VerificacaoSendasService,
        )
        prot = f'PROT-DEDUP-{_sfx()}'
        lote = f'LOTE-DEDUP-{_sfx()}'
        _criar_sep(db, protocolo=prot, numero_nf=None)
        _criar_fila(db, protocolo=prot, documento_origem=lote)
        db.session.flush()

        protocolos = VerificacaoSendasService()._buscar_protocolos_nao_confirmados()
        encontrados = [p for p in protocolos if p['protocolo'] == prot]
        assert len(encontrados) == 1
