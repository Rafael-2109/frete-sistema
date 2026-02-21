"""
Service de Query Unificada para Gestao de Pallets V3

Consolida dados de 6 tabelas (nf_remessa, creditos, solucoes, documentos,
nf_solucoes, cadastro_palletizacao) em uma unica view centrada na NF de Remessa.

Metodos principais:
- listar_paginado(filtros, page, per_page) -> dict com tabela paginada
- obter_kpis() -> dict com 6 KPIs + alertas
- obter_completo(nf_id) -> dict com drill-down completo para offcanvas

Todos os metodos retornam dicts puros (JSON-serializaveis), nao objetos ORM.
"""
import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from app import db
from app.pallet.models import (
    PalletNFRemessa, PalletCredito, PalletDocumento,
    PalletNFSolucao
)

logger = logging.getLogger(__name__)


class UnifiedQueryService:
    """Service para queries unificadas da tela V3 de pallets."""

    # =========================================================================
    # KPIs
    # =========================================================================

    @staticmethod
    def obter_kpis() -> dict:
        """
        Retorna os 6 KPIs do topo + alertas.

        Returns:
            dict: {
                'em_terceiros': int,
                'saldo_pendente': int,
                'creditos_abertos': int,
                'vencendo_7d': int,
                'sugestoes_pendentes': int,
                'docs_nao_recebidos': int,
                'alertas': [...]
            }
        """
        hoje = date.today()
        limite_7d = hoje + timedelta(days=7)

        # KPI 1: Total pallets em terceiros (soma saldos pendentes/parciais)
        em_terceiros = db.session.query(
            func.coalesce(func.sum(PalletCredito.qtd_saldo), 0)
        ).filter(
            PalletCredito.ativo == True,
            PalletCredito.status.in_(['PENDENTE', 'PARCIAL'])
        ).scalar() or 0

        # KPI 2: Saldo pendente (mesmo valor, mas separado para clareza semantica)
        saldo_pendente = int(em_terceiros)

        # KPI 3: Creditos abertos (count)
        creditos_abertos = PalletCredito.query.filter(
            PalletCredito.ativo == True,
            PalletCredito.status.in_(['PENDENTE', 'PARCIAL'])
        ).count()

        # KPI 4: Vencendo em < 7 dias
        vencendo_7d = PalletCredito.query.filter(
            PalletCredito.ativo == True,
            PalletCredito.status.in_(['PENDENTE', 'PARCIAL']),
            PalletCredito.data_vencimento.isnot(None),
            PalletCredito.data_vencimento <= limite_7d
        ).count()

        # KPI 5: Sugestoes pendentes (SUGESTAO nao confirmada/rejeitada)
        sugestoes_pendentes = PalletNFSolucao.query.filter(
            PalletNFSolucao.ativo == True,
            PalletNFSolucao.vinculacao == 'SUGESTAO',
            PalletNFSolucao.confirmado == False,
            PalletNFSolucao.rejeitado == False
        ).count()

        # KPI 6: Docs nao recebidos
        docs_nao_recebidos = PalletDocumento.query.filter(
            PalletDocumento.ativo == True,
            PalletDocumento.recebido == False
        ).count()

        # Alertas
        alertas = []

        # Creditos vencidos
        creditos_vencidos = PalletCredito.query.filter(
            PalletCredito.ativo == True,
            PalletCredito.status.in_(['PENDENTE', 'PARCIAL']),
            PalletCredito.data_vencimento.isnot(None),
            PalletCredito.data_vencimento < hoje
        ).count()
        if creditos_vencidos > 0:
            alertas.append({
                'tipo': 'danger',
                'icone': 'fas fa-exclamation-triangle',
                'texto': f'{creditos_vencidos} credito(s) vencido(s)',
                'filtro': {'vencido': 'true'}
            })

        if sugestoes_pendentes > 0:
            alertas.append({
                'tipo': 'info',
                'icone': 'fas fa-lightbulb',
                'texto': f'{sugestoes_pendentes} sugestao(oes) DFe pendente(s)',
                'filtro': {'aba': 'sugestoes'}
            })

        if docs_nao_recebidos > 0:
            alertas.append({
                'tipo': 'warning',
                'icone': 'fas fa-file-alt',
                'texto': f'{docs_nao_recebidos} documento(s) nao recebido(s)',
                'filtro': {'docs_pendentes': 'true'}
            })

        return {
            'em_terceiros': int(em_terceiros),
            'saldo_pendente': saldo_pendente,
            'creditos_abertos': creditos_abertos,
            'vencendo_7d': vencendo_7d,
            'sugestoes_pendentes': sugestoes_pendentes,
            'docs_nao_recebidos': docs_nao_recebidos,
            'alertas': alertas
        }

    # =========================================================================
    # TABELA PAGINADA
    # =========================================================================

    @staticmethod
    def listar_paginado(
        filtros: dict,
        page: int = 1,
        per_page: int = 50,
        ordenar_por: str = 'data_emissao',
        ordem: str = 'desc'
    ) -> dict:
        """
        Lista NFs de remessa com dados agregados de 6 tabelas.

        Args:
            filtros: dict com chaves opcionais:
                - busca: texto livre (NF, CNPJ, nome)
                - status_nf: ATIVA, RESOLVIDA, CANCELADA
                - status_credito: PENDENTE, PARCIAL, RESOLVIDO
                - empresa: CD, FB, SC
                - tipo_destinatario: TRANSPORTADORA, CLIENTE
                - cnpj: CNPJ/nome responsavel
                - data_de: data inicio (YYYY-MM-DD)
                - data_ate: data fim (YYYY-MM-DD)
                - uf: UF responsavel
                - cidade: cidade responsavel
                - aba: visao_geral, vencendo, sugestoes, historico
                - vencido: 'true' para filtrar vencidos
                - docs_pendentes: 'true' para filtrar com docs pendentes
            page: pagina atual
            per_page: itens por pagina
            ordenar_por: campo de ordenacao
            ordem: 'asc' ou 'desc'

        Returns:
            dict: {
                'itens': [...],
                'total': int,
                'pagina': int,
                'por_pagina': int,
                'paginas': int,
                'tem_anterior': bool,
                'tem_proximo': bool
            }
        """
        hoje = date.today()

        # Query principal com eager loading
        query = PalletNFRemessa.query.options(
            joinedload(PalletNFRemessa.creditos).joinedload(PalletCredito.documentos),
            joinedload(PalletNFRemessa.creditos).joinedload(PalletCredito.solucoes),
            joinedload(PalletNFRemessa.solucoes_nf)
        ).filter(
            PalletNFRemessa.ativo == True
        )

        # ==========================================
        # PRE-FILTROS POR ABA
        # ==========================================
        aba = filtros.get('aba', 'visao_geral')

        if aba == 'visao_geral':
            # NFs ativas com credito pendente/parcial
            query = query.filter(PalletNFRemessa.status == 'ATIVA')

        elif aba == 'vencendo':
            # NFs com credito vencendo em < 7 dias
            limite_7d = hoje + timedelta(days=7)
            subq_vencendo = db.session.query(
                PalletCredito.nf_remessa_id
            ).filter(
                PalletCredito.ativo == True,
                PalletCredito.status.in_(['PENDENTE', 'PARCIAL']),
                PalletCredito.data_vencimento.isnot(None),
                PalletCredito.data_vencimento <= limite_7d
            ).subquery()
            query = query.filter(PalletNFRemessa.id.in_(
                db.session.query(subq_vencendo.c.nf_remessa_id)
            ))

        elif aba == 'sugestoes':
            # NFs com sugestoes pendentes
            subq_sugestoes = db.session.query(
                PalletNFSolucao.nf_remessa_id
            ).filter(
                PalletNFSolucao.ativo == True,
                PalletNFSolucao.vinculacao == 'SUGESTAO',
                PalletNFSolucao.confirmado == False,
                PalletNFSolucao.rejeitado == False
            ).subquery()
            query = query.filter(PalletNFRemessa.id.in_(
                db.session.query(subq_sugestoes.c.nf_remessa_id)
            ))

        elif aba == 'historico':
            # Todos (incluindo resolvidos e cancelados) — sem filtro de status
            pass

        # ==========================================
        # FILTROS CUSTOMIZADOS
        # ==========================================

        # Busca textual
        busca = filtros.get('busca', '').strip()
        if busca:
            busca_limpa = busca.replace('.', '').replace('-', '').replace('/', '')
            query = query.filter(
                or_(
                    PalletNFRemessa.numero_nf.ilike(f'%{busca}%'),
                    PalletNFRemessa.cnpj_destinatario.ilike(f'%{busca_limpa}%'),
                    PalletNFRemessa.nome_destinatario.ilike(f'%{busca}%')
                )
            )

        # Status NF
        status_nf = filtros.get('status_nf', '').strip()
        if status_nf:
            query = query.filter(PalletNFRemessa.status == status_nf)

        # Empresa
        empresa = filtros.get('empresa', '').strip()
        if empresa:
            query = query.filter(PalletNFRemessa.empresa == empresa)

        # Tipo destinatario
        tipo_dest = filtros.get('tipo_destinatario', '').strip()
        if tipo_dest:
            query = query.filter(PalletNFRemessa.tipo_destinatario == tipo_dest)

        # CNPJ / Nome responsavel (busca no credito)
        cnpj = filtros.get('cnpj', '').strip()
        if cnpj:
            cnpj_limpo = cnpj.replace('.', '').replace('-', '').replace('/', '')
            subq_cnpj = db.session.query(
                PalletCredito.nf_remessa_id
            ).filter(
                PalletCredito.ativo == True,
                or_(
                    PalletCredito.cnpj_responsavel.ilike(f'%{cnpj_limpo}%'),
                    PalletCredito.nome_responsavel.ilike(f'%{cnpj}%')
                )
            ).subquery()
            query = query.filter(PalletNFRemessa.id.in_(
                db.session.query(subq_cnpj.c.nf_remessa_id)
            ))

        # Data
        data_de = filtros.get('data_de', '').strip()
        if data_de:
            try:
                from datetime import datetime
                dt = datetime.strptime(data_de, '%Y-%m-%d')
                query = query.filter(PalletNFRemessa.data_emissao >= dt)
            except ValueError:
                pass

        data_ate = filtros.get('data_ate', '').strip()
        if data_ate:
            try:
                from datetime import datetime
                dt = datetime.strptime(data_ate, '%Y-%m-%d')
                query = query.filter(PalletNFRemessa.data_emissao <= dt)
            except ValueError:
                pass

        # UF
        uf = filtros.get('uf', '').strip()
        if uf:
            subq_uf = db.session.query(
                PalletCredito.nf_remessa_id
            ).filter(
                PalletCredito.ativo == True,
                PalletCredito.uf_responsavel == uf
            ).subquery()
            query = query.filter(PalletNFRemessa.id.in_(
                db.session.query(subq_uf.c.nf_remessa_id)
            ))

        # Cidade
        cidade = filtros.get('cidade', '').strip()
        if cidade:
            subq_cidade = db.session.query(
                PalletCredito.nf_remessa_id
            ).filter(
                PalletCredito.ativo == True,
                PalletCredito.cidade_responsavel.ilike(f'%{cidade}%')
            ).subquery()
            query = query.filter(PalletNFRemessa.id.in_(
                db.session.query(subq_cidade.c.nf_remessa_id)
            ))

        # Status credito
        status_credito = filtros.get('status_credito', '').strip()
        if status_credito:
            subq_sc = db.session.query(
                PalletCredito.nf_remessa_id
            ).filter(
                PalletCredito.ativo == True,
                PalletCredito.status == status_credito
            ).subquery()
            query = query.filter(PalletNFRemessa.id.in_(
                db.session.query(subq_sc.c.nf_remessa_id)
            ))

        # Filtro especial: vencidos
        if filtros.get('vencido') == 'true':
            subq_vencido = db.session.query(
                PalletCredito.nf_remessa_id
            ).filter(
                PalletCredito.ativo == True,
                PalletCredito.status.in_(['PENDENTE', 'PARCIAL']),
                PalletCredito.data_vencimento.isnot(None),
                PalletCredito.data_vencimento < hoje
            ).subquery()
            query = query.filter(PalletNFRemessa.id.in_(
                db.session.query(subq_vencido.c.nf_remessa_id)
            ))

        # ==========================================
        # ORDENACAO
        # ==========================================
        ordem_map = {
            'data_emissao': PalletNFRemessa.data_emissao,
            'numero_nf': PalletNFRemessa.numero_nf,
            'empresa': PalletNFRemessa.empresa,
            'quantidade': PalletNFRemessa.quantidade,
            'status': PalletNFRemessa.status,
        }
        col = ordem_map.get(ordenar_por, PalletNFRemessa.data_emissao)
        if ordem == 'asc':
            query = query.order_by(col.asc())
        else:
            query = query.order_by(col.desc())

        # ==========================================
        # PAGINACAO
        # ==========================================
        paginacao = query.paginate(page=page, per_page=per_page, error_out=False)

        # Serializar itens com dados agregados
        itens = []
        for nf in paginacao.items:
            itens.append(UnifiedQueryService._serializar_linha(nf, hoje))

        return {
            'itens': itens,
            'total': paginacao.total,
            'pagina': paginacao.page,
            'por_pagina': paginacao.per_page,
            'paginas': paginacao.pages,
            'tem_anterior': paginacao.has_prev,
            'tem_proximo': paginacao.has_next
        }

    # =========================================================================
    # DRILL-DOWN (OFFCANVAS)
    # =========================================================================

    @staticmethod
    def obter_completo(nf_id: int) -> Optional[dict]:
        """
        Retorna dados completos de uma NF para o painel lateral.

        Args:
            nf_id: ID da NF de remessa

        Returns:
            dict completo ou None se nao encontrada
        """
        nf = PalletNFRemessa.query.options(
            joinedload(PalletNFRemessa.creditos).joinedload(PalletCredito.documentos),
            joinedload(PalletNFRemessa.creditos).joinedload(PalletCredito.solucoes),
            joinedload(PalletNFRemessa.solucoes_nf),
            joinedload(PalletNFRemessa.embarque)
        ).filter(
            PalletNFRemessa.id == nf_id,
            PalletNFRemessa.ativo == True
        ).first()

        if not nf:
            return None

        hoje = date.today()

        # Cabecalho
        resultado = {
            'nf': nf.to_dict(),
            'embarque': None,
        }

        # Embarque
        if nf.embarque:
            resultado['embarque'] = {
                'id': nf.embarque.id,
                'numero': getattr(nf.embarque, 'numero_embarque', None),
                'data': getattr(nf.embarque, 'data_embarque', None),
            }
            if resultado['embarque']['data']:
                resultado['embarque']['data'] = resultado['embarque']['data'].isoformat()

        # Creditos (Dominio A)
        creditos = []
        for c in nf.creditos:
            if not c.ativo:
                continue
            credito_dict = c.to_dict()
            credito_dict['vencido'] = c.vencido
            credito_dict['prestes_a_vencer'] = c.prestes_a_vencer
            credito_dict['dias_para_vencer'] = c.dias_para_vencer

            # Documentos do credito
            docs = []
            for d in c.documentos:
                if d.ativo:
                    docs.append(d.to_dict())
            credito_dict['documentos'] = docs

            # Solucoes do credito (Dominio A)
            sols = []
            for s in c.solucoes:
                if s.ativo:
                    sols.append(s.to_dict())
            credito_dict['solucoes'] = sols

            creditos.append(credito_dict)

        resultado['creditos'] = creditos

        # Solucoes NF (Dominio B)
        solucoes_nf = []
        sugestoes_pendentes = []
        for s in nf.solucoes_nf:
            if not s.ativo:
                continue
            sol_dict = s.to_dict()

            if s.pendente_confirmacao:
                sugestoes_pendentes.append(sol_dict)
            else:
                solucoes_nf.append(sol_dict)

        resultado['solucoes_nf'] = solucoes_nf
        resultado['sugestoes_pendentes'] = sugestoes_pendentes

        # Resumo agregado
        qtd_original = sum(c.get('qtd_original', 0) for c in creditos)
        qtd_saldo = sum(c.get('qtd_saldo', 0) for c in creditos)
        qtd_resolvida_a = qtd_original - qtd_saldo

        resultado['resumo'] = {
            'dom_a': {
                'qtd_original': qtd_original,
                'qtd_resolvida': qtd_resolvida_a,
                'qtd_pendente': qtd_saldo,
                'percentual': round((qtd_resolvida_a / qtd_original * 100), 1) if qtd_original > 0 else 0
            },
            'dom_b': {
                'qtd_total': nf.quantidade,
                'qtd_resolvida': nf.qtd_resolvida or 0,
                'qtd_pendente': nf.qtd_pendente,
                'percentual': round(((nf.qtd_resolvida or 0) / nf.quantidade * 100), 1) if nf.quantidade > 0 else 0
            },
            'total_documentos': sum(len(c.get('documentos', [])) for c in creditos),
            'docs_recebidos': sum(
                1 for c in creditos
                for d in c.get('documentos', [])
                if d.get('recebido')
            ),
        }

        return resultado

    # =========================================================================
    # LINHA INDIVIDUAL (para partial update)
    # =========================================================================

    @staticmethod
    def obter_linha(nf_id: int) -> Optional[dict]:
        """
        Retorna dados de uma unica linha da tabela (para partial update apos acao).

        Args:
            nf_id: ID da NF de remessa

        Returns:
            dict da linha ou None
        """
        nf = PalletNFRemessa.query.options(
            joinedload(PalletNFRemessa.creditos).joinedload(PalletCredito.documentos),
            joinedload(PalletNFRemessa.creditos).joinedload(PalletCredito.solucoes),
            joinedload(PalletNFRemessa.solucoes_nf)
        ).filter(
            PalletNFRemessa.id == nf_id,
            PalletNFRemessa.ativo == True
        ).first()

        if not nf:
            return None

        return UnifiedQueryService._serializar_linha(nf, date.today())

    # =========================================================================
    # FILTROS DINAMICOS
    # =========================================================================

    @staticmethod
    def listar_ufs() -> list:
        """Lista UFs distintas de creditos ativos."""
        ufs = db.session.query(
            PalletCredito.uf_responsavel
        ).filter(
            PalletCredito.ativo == True,
            PalletCredito.uf_responsavel.isnot(None),
            PalletCredito.uf_responsavel != ''
        ).distinct().order_by(PalletCredito.uf_responsavel).all()
        return [u[0] for u in ufs]

    @staticmethod
    def listar_cidades_por_uf(uf: str) -> list:
        """Lista cidades distintas de uma UF."""
        cidades = db.session.query(
            PalletCredito.cidade_responsavel
        ).filter(
            PalletCredito.ativo == True,
            PalletCredito.uf_responsavel == uf,
            PalletCredito.cidade_responsavel.isnot(None),
            PalletCredito.cidade_responsavel != ''
        ).distinct().order_by(PalletCredito.cidade_responsavel).all()
        return [c[0] for c in cidades]

    @staticmethod
    def buscar_responsaveis(termo: str, limite: int = 10) -> list:
        """Autocomplete de responsaveis."""
        if not termo or len(termo) < 2:
            return []

        termo_limpo = termo.replace('.', '').replace('-', '').replace('/', '')

        resultados = db.session.query(
            PalletCredito.cnpj_responsavel,
            PalletCredito.nome_responsavel
        ).filter(
            PalletCredito.ativo == True,
            or_(
                PalletCredito.cnpj_responsavel.ilike(f'%{termo_limpo}%'),
                PalletCredito.nome_responsavel.ilike(f'%{termo}%')
            )
        ).distinct().limit(limite).all()

        return [
            {'cnpj': r[0], 'nome': r[1]}
            for r in resultados
        ]

    # =========================================================================
    # CONTADORES POR ABA
    # =========================================================================

    @staticmethod
    def contar_por_aba() -> dict:
        """Retorna contagem de itens por aba."""
        hoje = date.today()
        limite_7d = hoje + timedelta(days=7)

        # Visao geral: NFs ativas
        visao_geral = PalletNFRemessa.query.filter(
            PalletNFRemessa.ativo == True,
            PalletNFRemessa.status == 'ATIVA'
        ).count()

        # Vencendo: creditos com vencimento < 7 dias (distinct nf_remessa_id)
        vencendo = db.session.query(
            func.count(func.distinct(PalletCredito.nf_remessa_id))
        ).filter(
            PalletCredito.ativo == True,
            PalletCredito.status.in_(['PENDENTE', 'PARCIAL']),
            PalletCredito.data_vencimento.isnot(None),
            PalletCredito.data_vencimento <= limite_7d
        ).scalar() or 0

        # Sugestoes: NFs com sugestoes pendentes
        sugestoes = db.session.query(
            func.count(func.distinct(PalletNFSolucao.nf_remessa_id))
        ).filter(
            PalletNFSolucao.ativo == True,
            PalletNFSolucao.vinculacao == 'SUGESTAO',
            PalletNFSolucao.confirmado == False,
            PalletNFSolucao.rejeitado == False
        ).scalar() or 0

        # Historico: todos
        historico = PalletNFRemessa.query.filter(
            PalletNFRemessa.ativo == True
        ).count()

        return {
            'visao_geral': visao_geral,
            'vencendo': vencendo,
            'sugestoes': sugestoes,
            'historico': historico
        }

    # =========================================================================
    # HELPERS PRIVADOS
    # =========================================================================

    @staticmethod
    def _serializar_linha(nf: PalletNFRemessa, hoje: date) -> dict:
        """
        Serializa uma NF de remessa com dados agregados para a tabela.

        Args:
            nf: instancia PalletNFRemessa com eager loads
            hoje: data de referencia

        Returns:
            dict com dados da linha
        """
        # Calcular dados do Dominio A (creditos + solucoes)
        qtd_original = 0
        qtd_saldo = 0
        qtd_baixa = 0
        qtd_venda = 0
        qtd_recebimento = 0
        qtd_substituicao = 0
        data_vencimento = None
        vencido = False
        prestes_a_vencer = False
        total_docs = 0
        docs_recebidos = 0
        credito_id = None
        credito_status = None

        for credito in nf.creditos:
            if not credito.ativo:
                continue

            # Pegar o primeiro credito valido para referencia
            if credito_id is None:
                credito_id = credito.id
                credito_status = credito.status

            qtd_original += credito.qtd_original or 0
            qtd_saldo += credito.qtd_saldo or 0

            # Vencimento (pegar o mais proximo)
            if credito.data_vencimento:
                if data_vencimento is None or credito.data_vencimento < data_vencimento:
                    data_vencimento = credito.data_vencimento
                    vencido = credito.vencido
                    prestes_a_vencer = credito.prestes_a_vencer

            # Solucoes por tipo
            for sol in credito.solucoes:
                if not sol.ativo:
                    continue
                if sol.tipo == 'BAIXA':
                    qtd_baixa += sol.quantidade or 0
                elif sol.tipo == 'VENDA':
                    qtd_venda += sol.quantidade or 0
                elif sol.tipo == 'RECEBIMENTO':
                    qtd_recebimento += sol.quantidade or 0
                elif sol.tipo == 'SUBSTITUICAO':
                    qtd_substituicao += sol.quantidade or 0

            # Documentos
            for doc in credito.documentos:
                if not doc.ativo:
                    continue
                total_docs += 1
                if doc.recebido:
                    docs_recebidos += 1

        qtd_resolvida_a = qtd_original - qtd_saldo
        pct_dom_a = round((qtd_resolvida_a / qtd_original * 100), 1) if qtd_original > 0 else 0

        # Calcular dados do Dominio B (solucoes NF)
        qtd_resolvida_b = nf.qtd_resolvida or 0
        pct_dom_b = round((qtd_resolvida_b / nf.quantidade * 100), 1) if nf.quantidade > 0 else 0

        # Sugestoes pendentes para esta NF
        sugestoes = 0
        for sol in nf.solucoes_nf:
            if sol.ativo and sol.vinculacao == 'SUGESTAO' and not sol.confirmado and not sol.rejeitado:
                sugestoes += 1

        return {
            'id': nf.id,
            'numero_nf': nf.numero_nf,
            'serie': nf.serie,
            'data_emissao': nf.data_emissao.strftime('%d/%m/%Y') if nf.data_emissao else '',
            'data_emissao_iso': nf.data_emissao.isoformat() if nf.data_emissao else '',
            'empresa': nf.empresa,
            'tipo_destinatario': nf.tipo_destinatario,
            'cnpj_destinatario': nf.cnpj_destinatario,
            'nome_destinatario': nf.nome_destinatario or '',
            'quantidade': nf.quantidade,
            'status': nf.status,

            # Dominio A
            'credito_id': credito_id,
            'credito_status': credito_status,
            'qtd_saldo': qtd_saldo,
            'dom_a_pct': pct_dom_a,
            'dom_a_resolvida': qtd_resolvida_a,
            'dom_a_original': qtd_original,
            'dom_a_breakdown': {
                'baixa': qtd_baixa,
                'venda': qtd_venda,
                'recebimento': qtd_recebimento,
                'substituicao': qtd_substituicao
            },

            # Dominio B
            'dom_b_pct': pct_dom_b,
            'dom_b_resolvida': qtd_resolvida_b,
            'dom_b_total': nf.quantidade,

            # Vencimento
            'data_vencimento': data_vencimento.strftime('%d/%m/%Y') if data_vencimento else '',
            'data_vencimento_iso': data_vencimento.isoformat() if data_vencimento else '',
            'vencido': vencido,
            'prestes_a_vencer': prestes_a_vencer,

            # Documentos
            'total_docs': total_docs,
            'docs_recebidos': docs_recebidos,

            # Sugestoes
            'sugestoes_pendentes': sugestoes,

            # Odoo
            'odoo_account_move_id': nf.odoo_account_move_id,
            'odoo_picking_id': nf.odoo_picking_id,
        }
