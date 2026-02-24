# -*- coding: utf-8 -*-
"""
Serviço de Sincronização de Contas a Pagar
==========================================

Sincroniza dados do Odoo (account.move.line com account_type='liability_payable')
para a tabela contas_a_pagar.

Diferenças em relação ao Contas a Receber:
- account_type = 'liability_payable' (vs 'asset_receivable')
- Valor no campo 'credit' (vs 'debit')
- amount_residual é NEGATIVO quando em aberto
- Fornecedores (partner_type='supplier') vs Clientes

Autor: Sistema de Fretes
Data: 2025-12-13
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

from app import db
from app.financeiro.parcela_utils import parcela_to_str
from app.utils.timezone import agora_utc_naive
from app.financeiro.models import ContasAPagar
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


# CNPJs raiz do grupo Nacom (para excluir transações intercompany)
# FONTE: .claude/references/odoo/IDS_FIXOS.md:18-25
# Padrão alinhado com pedido_compras_service.py:174 e entrada_material_service.py:44
CNPJS_RAIZ_GRUPO_PAGAR = ['61.724.241', '18.467.441']


class SincronizacaoContasAPagarService:
    """
    Serviço para sincronizar dados do Odoo para a tabela contas_a_pagar.
    """

    # Mapeamento de empresa Odoo -> código interno
    # Importado de app.financeiro.constants.EMPRESA_MAP
    from app.financeiro.constants import EMPRESA_MAP

    # Campos a buscar no Odoo (account.move.line)
    CAMPOS_ODOO = [
        'id',
        'name',
        'ref',
        'x_studio_nf_e',           # NF de entrada
        'l10n_br_cobranca_parcela', # Parcela
        'partner_id',              # Fornecedor [id, nome]
        'company_id',              # Empresa [id, nome]
        'move_id',                 # Move [id, nome]
        'date',                    # Data emissão
        'date_maturity',           # Data vencimento
        'credit',                  # Valor original
        'amount_residual',         # Saldo (negativo quando em aberto)
        'l10n_br_paga',            # Parcela paga?
        'reconciled',              # Reconciliado?
        'account_type',            # Tipo de conta
        'parent_state',            # Estado da fatura
        'write_date',              # Data última modificação (para sync incremental)
        'create_date',             # Data criação (para sync incremental)
    ]

    def __init__(self, connection=None):
        self._connection = connection
        self._resetar_estatisticas()

    @property
    def connection(self):
        """Conexão lazy com o Odoo"""
        if self._connection is None:
            self._connection = get_odoo_connection()
        return self._connection

    def _resetar_estatisticas(self):
        """Reseta as estatísticas para uma nova sincronização"""
        self.estatisticas = {
            'novos': 0,
            'atualizados': 0,
            'erros': 0,
            'ignorados': 0,
            'sucesso': False
        }

    def _mapear_empresa(self, nome_empresa: str) -> int:
        """Mapeia o nome da empresa Odoo para o código interno"""
        if not nome_empresa:
            return 0

        for nome, codigo in self.EMPRESA_MAP.items():
            if nome.upper() in nome_empresa.upper() or nome_empresa.upper() in nome.upper():
                return codigo

        nome_upper = nome_empresa.upper()
        if '- FB' in nome_upper or nome_upper.endswith('FB'):
            return 1
        elif '- SC' in nome_upper or nome_upper.endswith('SC'):
            return 2
        elif '- CD' in nome_upper or nome_upper.endswith('CD'):
            return 3

        logger.warning(f"⚠️ Empresa não mapeada: {nome_empresa}")
        return 0

    def sincronizar(
        self,
        data_inicio: date = None,
        data_fim: date = None,
        limite: int = None,
        apenas_em_aberto: bool = True
    ) -> dict:
        """
        Executa a sincronização completa de Contas a Pagar.

        Args:
            data_inicio: Data inicial para busca (date_maturity >=)
            data_fim: Data final para busca (date_maturity <=)
            limite: Limite de registros para teste
            apenas_em_aberto: Se True, busca apenas títulos em aberto

        Returns:
            dict com estatísticas da sincronização
        """
        self._resetar_estatisticas()

        logger.info("=" * 60)
        logger.info("🔄 INICIANDO SINCRONIZAÇÃO DE CONTAS A PAGAR")
        logger.info("=" * 60)

        # Definir período padrão (últimos 90 dias de vencimento)
        if data_inicio is None:
            data_inicio = date.today() - timedelta(days=90)

        if data_fim:
            logger.info(f"📅 Período: {data_inicio} até {data_fim}")
            self.estatisticas['periodo'] = f"{data_inicio} até {data_fim}"
        else:
            logger.info(f"📅 Data inicial: {data_inicio}")
            self.estatisticas['periodo'] = f"A partir de {data_inicio}"

        try:
            # 1. Extrair dados do Odoo
            logger.info("\n[1/3] Extraindo dados do Odoo...")
            dados_odoo = self._extrair_dados_odoo(data_inicio, data_fim, apenas_em_aberto)
            logger.info(f"   ✅ {len(dados_odoo)} registros extraídos")

            if limite:
                dados_odoo = dados_odoo[:limite]
                logger.info(f"   ⚠️ Limitado a {limite} registros para teste")

            # 2. Buscar CNPJs dos fornecedores
            logger.info("\n[2/3] Buscando dados dos fornecedores...")
            partner_ids = list(set(
                r.get('partner_id', [None, None])[0]
                for r in dados_odoo if r.get('partner_id')
            ))
            cnpj_map = self._buscar_cnpjs_fornecedores(partner_ids)
            logger.info(f"   ✅ {len(cnpj_map)} fornecedores encontrados")

            # 3. Pre-carregar registros existentes para batch lookup (evita N+1)
            logger.info("\n[3/4] Pre-carregando registros existentes...")
            odoo_line_ids = [r.get('id') for r in dados_odoo if r.get('id')]
            contas_por_line_id = {}
            contas_por_chave = {}

            # Batch lookup por odoo_line_id (chunks de 500 para evitar SQL IN muito grande)
            for i in range(0, len(odoo_line_ids), 500):
                chunk = odoo_line_ids[i:i+500]
                for c in ContasAPagar.query.filter(ContasAPagar.odoo_line_id.in_(chunk)).all():
                    if c.odoo_line_id:
                        contas_por_line_id[c.odoo_line_id] = c

            # Batch lookup por chave composta (empresa, titulo_nf, parcela)
            # Determinar empresas presentes nos dados
            empresas_presentes = set()
            for r in dados_odoo:
                emp_nome = r.get('company_id', [None, ''])[1] or ''
                emp = self._mapear_empresa(emp_nome)
                if emp != 0:
                    empresas_presentes.add(emp)

            for emp in empresas_presentes:
                for c in ContasAPagar.query.filter(ContasAPagar.empresa == emp).all():
                    chave = (c.empresa, c.titulo_nf, c.parcela)
                    contas_por_chave[chave] = c

            logger.info(f"   ✅ {len(contas_por_line_id)} por line_id, {len(contas_por_chave)} por chave composta")

            # 4. Processar cada registro
            logger.info("\n[4/4] Processando registros...")

            for idx, row in enumerate(dados_odoo):
                try:
                    self._processar_registro(row, cnpj_map, contas_por_line_id, contas_por_chave)
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"   ❌ Erro no registro {idx}: {e}")
                    self.estatisticas['erros'] += 1
                    continue

            db.session.commit()
            self.estatisticas['sucesso'] = True

        except Exception as e:
            logger.error(f"❌ Erro na sincronização: {e}")
            self.estatisticas['erro'] = str(e)
            db.session.rollback()

        # Resumo
        logger.info("\n" + "=" * 60)
        logger.info("✅ SINCRONIZAÇÃO CONCLUÍDA" if self.estatisticas['sucesso'] else "❌ SINCRONIZAÇÃO COM ERROS")
        logger.info("=" * 60)
        logger.info(f"📊 Novos: {self.estatisticas['novos']}")
        logger.info(f"📊 Atualizados: {self.estatisticas['atualizados']}")
        logger.info(f"📊 Ignorados: {self.estatisticas['ignorados']}")
        logger.info(f"📊 Erros: {self.estatisticas['erros']}")

        return self.estatisticas

    def sincronizar_manual(self, dias: int = 90) -> dict:
        """
        Sincronização manual via botão.

        Args:
            dias: Quantidade de dias retroativos de vencimento

        Returns:
            dict com estatísticas
        """
        data_inicio = date.today() - timedelta(days=dias)
        logger.info(f"🔄 Sincronização Manual - Vencimentos desde {data_inicio}")
        return self.sincronizar(data_inicio=data_inicio)

    def sincronizar_incremental(self, minutos_janela: int = 120) -> dict:
        """
        Sincronização incremental para o scheduler.

        Usa write_date/create_date como filtro de janela (padrão dos outros services).
        Captura títulos recém-modificados — incluindo pagos — resolvendo o problema
        de títulos que saíam do filtro amount_residual < 0 após pagamento.

        Args:
            minutos_janela: Minutos de janela para busca (default: 120)

        Returns:
            dict com estatísticas
        """
        data_limite = (agora_utc_naive() - timedelta(minutes=minutos_janela)).strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"🔄 Sincronização Incremental (write_date) - Janela: {minutos_janela} min, desde {data_limite}")

        try:
            resultado = self._sincronizar_por_write_date(data_limite)
            return {
                'sucesso': resultado.get('sucesso', False),
                'novos': resultado.get('novos', 0),
                'atualizados': resultado.get('atualizados', 0),
                'erros': resultado.get('erros', 0),
                'erro': resultado.get('erro')
            }
        except Exception as e:
            logger.error(f"❌ Erro na sincronização incremental: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }

    def _sincronizar_por_write_date(self, data_limite: str) -> dict:
        """
        Sincroniza títulos a pagar modificados/criados após data_limite.

        Diferença do sincronizar() original:
        - Filtra por write_date/create_date em vez de date_maturity
        - SEM filtro amount_residual < 0 — captura pagos E em aberto
        - Reutiliza _processar_registro() para criar/atualizar

        Args:
            data_limite: Data limite no formato 'YYYY-MM-DD HH:MM:SS'

        Returns:
            dict com estatísticas
        """
        self._resetar_estatisticas()

        logger.info("=" * 60)
        logger.info("🔄 SYNC CONTAS A PAGAR (write_date)")
        logger.info(f"📅 Títulos modificados desde: {data_limite}")
        logger.info("=" * 60)

        try:
            # 1. Extrair dados do Odoo — sem filtro de amount_residual
            logger.info("\n[1/4] Extraindo dados do Odoo (write_date)...")
            filtros = [
                ['account_type', '=', 'liability_payable'],
                ['parent_state', '=', 'posted'],
                '|',
                ['create_date', '>=', data_limite],
                ['write_date', '>=', data_limite],
            ]

            dados_odoo = []
            offset = 0
            PAGE_SIZE = 2000
            while True:
                page = self.connection.search_read(
                    'account.move.line',
                    filtros,
                    self.CAMPOS_ODOO,
                    limit=PAGE_SIZE,
                    offset=offset
                ) or []
                if not page:
                    break
                dados_odoo.extend(page)
                offset += PAGE_SIZE
                logger.info(f"   📄 Página {offset // PAGE_SIZE}: +{len(page)} registros (total: {len(dados_odoo)})")
            logger.info(f"   ✅ {len(dados_odoo)} registros extraídos")

            if not dados_odoo:
                self.estatisticas['sucesso'] = True
                return self.estatisticas

            # 2. Buscar CNPJs dos fornecedores
            logger.info("\n[2/4] Buscando dados dos fornecedores...")
            partner_ids = list(set(
                r.get('partner_id', [None, None])[0]
                for r in dados_odoo if r.get('partner_id')
            ))
            cnpj_map = self._buscar_cnpjs_fornecedores(partner_ids)
            logger.info(f"   ✅ {len(cnpj_map)} fornecedores encontrados")

            # 3. Pre-carregar registros existentes para batch lookup
            logger.info("\n[3/4] Pre-carregando registros existentes...")
            odoo_line_ids = [r.get('id') for r in dados_odoo if r.get('id')]
            contas_por_line_id = {}
            contas_por_chave = {}

            for i in range(0, len(odoo_line_ids), 500):
                chunk = odoo_line_ids[i:i+500]
                for c in ContasAPagar.query.filter(ContasAPagar.odoo_line_id.in_(chunk)).all():
                    if c.odoo_line_id:
                        contas_por_line_id[c.odoo_line_id] = c

            empresas_presentes = set()
            for r in dados_odoo:
                emp_nome = r.get('company_id', [None, ''])[1] or ''
                emp = self._mapear_empresa(emp_nome)
                if emp != 0:
                    empresas_presentes.add(emp)

            for emp in empresas_presentes:
                for c in ContasAPagar.query.filter(ContasAPagar.empresa == emp).all():
                    chave = (c.empresa, c.titulo_nf, c.parcela)
                    contas_por_chave[chave] = c

            logger.info(f"   ✅ {len(contas_por_line_id)} por line_id, {len(contas_por_chave)} por chave composta")

            # 4. Processar cada registro
            logger.info("\n[4/4] Processando registros...")
            for idx, row in enumerate(dados_odoo):
                try:
                    self._processar_registro(row, cnpj_map, contas_por_line_id, contas_por_chave)
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"   ❌ Erro no registro {idx}: {e}")
                    self.estatisticas['erros'] += 1
                    continue

            db.session.commit()
            self.estatisticas['sucesso'] = True

        except Exception as e:
            logger.error(f"❌ Erro na sincronização write_date: {e}")
            self.estatisticas['erro'] = str(e)
            db.session.rollback()

        # Resumo
        logger.info("\n" + "=" * 60)
        logger.info("✅ SYNC WRITE_DATE CONCLUÍDA" if self.estatisticas['sucesso'] else "❌ SYNC WRITE_DATE COM ERROS")
        logger.info("=" * 60)
        logger.info(f"📊 Novos: {self.estatisticas['novos']}")
        logger.info(f"📊 Atualizados: {self.estatisticas['atualizados']}")
        logger.info(f"📊 Ignorados: {self.estatisticas['ignorados']}")
        logger.info(f"📊 Erros: {self.estatisticas['erros']}")

        return self.estatisticas

    def _extrair_dados_odoo(
        self,
        data_inicio: date,
        data_fim: date = None,
        apenas_em_aberto: bool = True
    ) -> List[Dict]:
        """
        Extrai títulos a pagar do Odoo.

        Filtros:
        - account_type = 'liability_payable'
        - parent_state = 'posted' (apenas faturas confirmadas)
        - date_maturity >= data_inicio
        - Se apenas_em_aberto: amount_residual < 0
        """
        filtros = [
            ['account_type', '=', 'liability_payable'],
            ['parent_state', '=', 'posted'],
            ['date_maturity', '>=', data_inicio.strftime('%Y-%m-%d')],
        ]

        if data_fim:
            filtros.append(['date_maturity', '<=', data_fim.strftime('%Y-%m-%d')])

        if apenas_em_aberto:
            # amount_residual < 0 significa em aberto para liability_payable
            filtros.append(['amount_residual', '<', 0])

        logger.info(f"   Filtros: {filtros}")

        dados = []
        offset = 0
        PAGE_SIZE = 2000
        while True:
            page = self.connection.search_read(
                'account.move.line',
                filtros,
                self.CAMPOS_ODOO,
                limit=PAGE_SIZE,
                offset=offset
            ) or []
            if not page:
                break
            dados.extend(page)
            offset += PAGE_SIZE
            logger.info(f"   📄 Página {offset // PAGE_SIZE}: +{len(page)} registros (total: {len(dados)})")

        return dados

    def _buscar_cnpjs_fornecedores(self, partner_ids: List[int]) -> Dict[int, Dict]:
        """
        Busca CNPJs e dados dos fornecedores.

        Returns:
            Dict[partner_id, {cnpj, name, raz_social, raz_social_red}]
        """
        if not partner_ids:
            return {}

        # Remover None
        partner_ids = [p for p in partner_ids if p]

        dados = self.connection.search_read(
            'res.partner',
            [['id', 'in', partner_ids]],
            ['id', 'name', 'l10n_br_cnpj', 'l10n_br_razao_social'],
            limit=len(partner_ids)
        )

        result = {}
        for p in (dados or []):
            cnpj = p.get('l10n_br_cnpj') or ''
            name = p.get('name', '')
            raz_social = p.get('l10n_br_razao_social') or name
            result[p['id']] = {
                'cnpj': cnpj,
                'name': name,
                'raz_social': raz_social,
                'raz_social_red': (name or '')[:100],
            }

        return result

    def _processar_registro(
        self,
        row: Dict,
        cnpj_map: Dict[int, Dict],
        contas_por_line_id: Dict = None,
        contas_por_chave: Dict = None
    ):
        """Processa um registro do Odoo. Usa dicts pre-carregados para lookup O(1)."""

        # Extrair dados básicos
        odoo_line_id = row.get('id')
        empresa_nome = row.get('company_id', [None, ''])[1] or ''
        empresa = self._mapear_empresa(empresa_nome)

        # Ignorar empresas não mapeadas
        if empresa == 0:
            self.estatisticas['ignorados'] += 1
            return

        # NF e parcela
        titulo_nf = str(row.get('x_studio_nf_e') or '').strip()
        parcela = parcela_to_str(row.get('l10n_br_cobranca_parcela')) or '1'

        if not titulo_nf:
            self.estatisticas['ignorados'] += 1
            return

        # Fornecedor
        partner_id = row.get('partner_id', [None, None])[0]
        partner_name = row.get('partner_id', [None, ''])[1] or ''
        partner_data = cnpj_map.get(partner_id, {})
        cnpj = partner_data.get('cnpj', '')

        # Ignorar transações intercompany (parceiro pertence ao grupo Nacom)
        # Alinhado com Regra 4 do receber (contas_receber_service.py:314)
        if cnpj and any(cnpj.startswith(raiz) for raiz in CNPJS_RAIZ_GRUPO_PAGAR):
            self.estatisticas['ignorados'] += 1
            return

        # Move
        move_id = row.get('move_id', [None, None])[0]
        move_name = row.get('move_id', [None, ''])[1] or ''

        # Valores
        valor_original = float(row.get('credit') or 0)

        # Ignorar devoluções de compra (credit = 0 → não é conta a pagar)
        # Devoluções têm credit=0, debit>0 em liability_payable (fornecedor nos deve)
        # Sync principal exclui via amount_residual < 0 (linha 416), mas incremental não
        if valor_original == 0:
            self.estatisticas['ignorados'] += 1
            return

        amount_residual = float(row.get('amount_residual') or 0)
        valor_residual = abs(amount_residual)  # Converter para positivo

        # Datas
        emissao = row.get('date')
        vencimento = row.get('date_maturity')

        # Status — 3 sinais para parcela_paga (alinhado com Receber)
        # Sinal 1: flag explícita l10n_br
        # Sinal 2: reconciliado no Odoo
        # Sinal 3: amount_residual >= 0 (para payables, negativo = em aberto — Gotcha O3)
        paga_l10n = bool(row.get('l10n_br_paga'))
        reconciliado = bool(row.get('reconciled'))
        parcela_paga = paga_l10n or reconciliado or amount_residual >= 0

        # Buscar registro existente: batch dict O(1) com fallback para query
        conta = None
        if contas_por_line_id is not None:
            conta = contas_por_line_id.get(odoo_line_id)
        else:
            conta = ContasAPagar.query.filter_by(odoo_line_id=odoo_line_id).first()

        if not conta:
            if contas_por_chave is not None:
                conta = contas_por_chave.get((empresa, titulo_nf, parcela))
            else:
                conta = ContasAPagar.query.filter_by(
                    empresa=empresa,
                    titulo_nf=titulo_nf,
                    parcela=parcela
                ).first()

        if conta:
            # Atualizar registro existente
            conta.odoo_line_id = odoo_line_id
            conta.odoo_move_id = move_id
            conta.odoo_move_name = move_name
            conta.partner_id = partner_id
            conta.cnpj = cnpj
            conta.raz_social = partner_data.get('raz_social', partner_name)
            conta.raz_social_red = partner_data.get('raz_social_red')
            conta.emissao = emissao
            conta.vencimento = vencimento
            conta.valor_original = valor_original
            conta.valor_residual = valor_residual
            conta.parcela_paga = parcela_paga
            conta.reconciliado = reconciliado
            conta.odoo_write_date = agora_utc_naive()
            conta.ultima_sincronizacao = agora_utc_naive()
            conta.atualizado_por = 'Sistema Odoo'

            # Atualizar status_sistema se pago
            if parcela_paga and conta.status_sistema == 'PENDENTE':
                conta.status_sistema = 'PAGO'

            # FIX G3: Fallback metodo_baixa='ODOO_DIRETO' quando sync marca como pago
            if parcela_paga and not conta.metodo_baixa:
                conta.metodo_baixa = 'ODOO_DIRETO'

            self.estatisticas['atualizados'] += 1
        else:
            # Criar novo registro
            conta = ContasAPagar(
                empresa=empresa,
                titulo_nf=titulo_nf,
                parcela=parcela,
                odoo_line_id=odoo_line_id,
                odoo_move_id=move_id,
                odoo_move_name=move_name,
                partner_id=partner_id,
                cnpj=cnpj,
                raz_social=partner_data.get('raz_social', partner_name),
                raz_social_red=partner_data.get('raz_social_red'),
                emissao=emissao,
                vencimento=vencimento,
                valor_original=valor_original,
                valor_residual=valor_residual,
                parcela_paga=parcela_paga,
                reconciliado=reconciliado,
                status_sistema='PAGO' if parcela_paga else 'PENDENTE',
                metodo_baixa='ODOO_DIRETO' if parcela_paga else None,
                odoo_write_date=agora_utc_naive(),
                ultima_sincronizacao=agora_utc_naive(),
                criado_por='Sistema Odoo'
            )
            db.session.add(conta)
            # Atualizar dicts para evitar duplicatas no mesmo batch
            if contas_por_line_id is not None and odoo_line_id:
                contas_por_line_id[odoo_line_id] = conta
            if contas_por_chave is not None:
                contas_por_chave[(empresa, titulo_nf, parcela)] = conta
            self.estatisticas['novos'] += 1
