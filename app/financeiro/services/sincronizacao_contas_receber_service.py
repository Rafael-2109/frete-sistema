"""
Serviço de Sincronização de Contas a Receber
=============================================

Sincroniza dados do Odoo para a tabela contas_a_receber
com enriquecimento de dados locais e controle de alterações.

Autor: Sistema de Fretes
Data: 2025-11-27
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, Optional

from app import db
from app.financeiro.services.contas_receber_service import ContasReceberService
from app.financeiro.models import (
    ContasAReceber, ContasAReceberSnapshot, LiberacaoAntecipacao,
    CnabRetornoItem
)
from app.monitoramento.models import EntregaMonitorada

logger = logging.getLogger(__name__)


class SincronizacaoContasReceberService:
    """
    Serviço para sincronizar dados do Odoo para a tabela contas_a_receber
    com enriquecimento de dados locais e controle de alterações.
    """

    # Mapeamento de empresa Odoo -> código interno
    # 1 = FB (Fábrica), 2 = SC (Santa Catarina), 3 = CD (Centro de Distribuição)
    EMPRESA_MAP = {
        'NACOM GOYA - FB': 1,
        'NACOM GOYA - SC': 2,
        'NACOM GOYA - CD': 3,
    }

    # Campos do Odoo que devem gerar snapshot quando alterados
    CAMPOS_ODOO_AUDITADOS = [
        'valor_original', 'desconto_percentual', 'desconto', 'vencimento',
        'emissao', 'tipo_titulo', 'parcela_paga', 'status_pagamento_odoo',
        'raz_social', 'raz_social_red', 'cnpj', 'uf_cliente'
    ]

    def __init__(self):
        self.odoo_service = ContasReceberService()
        self._resetar_estatisticas()

    def _resetar_estatisticas(self):
        """Reseta as estatísticas para uma nova sincronização"""
        self.estatisticas = {
            'novos': 0,
            'atualizados': 0,
            'erros': 0,
            'snapshots_criados': 0,
            'enriquecidos': 0,
            'sucesso': False
        }

    def _mapear_empresa(self, nome_empresa: str) -> int:
        """Mapeia o nome da empresa Odoo para o código interno"""
        if not nome_empresa:
            return 0

        # Match direto
        for nome, codigo in self.EMPRESA_MAP.items():
            if nome.upper() in nome_empresa.upper() or nome_empresa.upper() in nome.upper():
                return codigo

        # Fallback: tentar identificar pelo sufixo
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
        limite: int = None
    ) -> dict:
        """
        Executa a sincronização completa de Contas a Receber.

        Args:
            data_inicio: Data inicial para busca no Odoo (default: D-7)
            data_fim: Data final para busca no Odoo (opcional)
            limite: Limite de registros para teste (default: None = todos)

        Returns:
            dict com estatísticas da sincronização
        """
        self._resetar_estatisticas()

        logger.info("=" * 60)
        logger.info("🔄 INICIANDO SINCRONIZAÇÃO DE CONTAS A RECEBER")
        logger.info("=" * 60)

        if data_inicio is None:
            data_inicio = date.today() - timedelta(days=7)

        if data_fim:
            logger.info(f"📅 Período: {data_inicio} até {data_fim}")
            self.estatisticas['periodo'] = f"{data_inicio} até {data_fim}"
        else:
            logger.info(f"📅 Data inicial: {data_inicio}")
            self.estatisticas['periodo'] = f"A partir de {data_inicio}"

        try:
            # 1. Extrair dados do Odoo
            logger.info("\n[1/4] Extraindo dados do Odoo...")
            dados_odoo = self.odoo_service.extrair_dados_odoo(data_inicio, data_fim)
            logger.info(f"   ✅ {len(dados_odoo)} registros extraídos")

            # 2. Aplicar regras de negócio
            logger.info("\n[2/4] Aplicando regras de negócio...")
            df = self.odoo_service.aplicar_regras_negocio(dados_odoo)
            logger.info(f"   ✅ {len(df)} registros após filtros")

            # Aplicar limite se especificado
            if limite:
                df = df.head(limite)
                logger.info(f"   ⚠️ Limitado a {limite} registros para teste")

            # 3. Processar cada registro
            logger.info("\n[3/4] Processando registros...")

            for idx, row in df.iterrows():
                try:
                    self._processar_registro(row)
                except Exception as e:
                    logger.error(f"   ❌ Erro no registro {idx}: {e}")
                    self.estatisticas['erros'] += 1
                    continue

            db.session.commit()

            # 4. Enriquecer com dados locais
            logger.info("\n[4/4] Enriquecendo com dados locais...")
            self._enriquecer_dados_locais()
            db.session.commit()

            # 5. Reprocessar CNABs sem match (SIMPLIFICAÇÃO FLUXO 21/01/2026)
            logger.info("\n[5/5] Reprocessando CNABs sem match...")
            cnabs_reprocessados = self._reprocessar_cnabs_sem_match()
            self.estatisticas['cnabs_reprocessados'] = cnabs_reprocessados
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
        logger.info(f"📊 Enriquecidos: {self.estatisticas['enriquecidos']}")
        logger.info(f"📊 Snapshots: {self.estatisticas['snapshots_criados']}")
        logger.info(f"📊 CNABs reprocessados: {self.estatisticas.get('cnabs_reprocessados', 0)}")
        logger.info(f"❌ Erros: {self.estatisticas['erros']}")

        return self.estatisticas

    def sincronizar_incremental(self, minutos_janela: int = 120) -> dict:
        """
        Sincronização incremental para uso no scheduler.
        Busca registros com write_date dentro da janela especificada.

        Args:
            minutos_janela: Janela de tempo em minutos (default: 120 = 2 horas)

        Returns:
            dict com estatísticas da sincronização
        """
        # Calcular data início baseada na janela (convertendo minutos para dias)
        dias = minutos_janela / (60 * 24)  # Converte minutos para fração de dias
        data_inicio = date.today() - timedelta(days=max(1, int(dias) + 1))

        logger.info(f"🔄 Sincronização Incremental - Janela: {minutos_janela} minutos (desde {data_inicio})")

        return self.sincronizar(data_inicio=data_inicio)

    def sincronizar_manual(self, dias: int = 7) -> dict:
        """
        Sincronização manual para uso via botão/rota.
        Busca registros dos últimos N dias.

        Args:
            dias: Quantidade de dias retroativos (default: 7)

        Returns:
            dict com estatísticas da sincronização
        """
        data_inicio = date.today() - timedelta(days=dias)

        logger.info(f"🔄 Sincronização Manual - Últimos {dias} dias (desde {data_inicio})")

        return self.sincronizar(data_inicio=data_inicio)

    def _processar_registro(self, row):
        """Processa um registro do Odoo"""

        # Extrair dados do registro
        empresa_nome = row.get('company_id_nome', '')
        empresa = self._mapear_empresa(empresa_nome)
        titulo_nf = str(int(row.get('x_studio_nf_e', 0)))
        parcela = str(row.get('l10n_br_cobranca_parcela', '1') or '1')

        if not titulo_nf or titulo_nf == '0':
            return

        # Ignorar empresas não mapeadas (empresa=0)
        if empresa == 0:
            return

        # Buscar registro existente
        conta = ContasAReceber.query.filter_by(
            empresa=empresa,
            titulo_nf=titulo_nf,
            parcela=parcela
        ).first()

        odoo_write_date = datetime.utcnow()

        if conta:
            # Atualizar registro existente
            self._atualizar_registro(conta, row, odoo_write_date)
            self.estatisticas['atualizados'] += 1
        else:
            # Criar novo registro
            conta = self._criar_registro(row, empresa, titulo_nf, parcela, odoo_write_date)
            db.session.add(conta)
            self.estatisticas['novos'] += 1

    def _criar_registro(self, row, empresa: int, titulo_nf: str, parcela: str,
                        odoo_write_date: datetime) -> ContasAReceber:
        """Cria um novo registro de ContasAReceber"""

        # =======================================================================
        # CORREÇÃO BUG DESCONTO DUPLO NO ODOO (2025-12-15)
        # =======================================================================
        # O Odoo aplica o desconto 2 vezes: VALOR * (1-desc) * (1-desc)
        #
        # O que vem do Odoo:
        # - saldo_total = balance + desconto_concedido = valor com desconto 1x
        # - desconto_concedido = calculado sobre valor já com desconto (incorreto)
        # - desconto_percentual = percentual correto (ex: 5%)
        #
        # O que precisamos:
        # - valor_titulo = saldo_total (valor que o cliente vai pagar, desconto 1x)
        # - valor_original = saldo_total / (1 - desconto_pct) (valor da NF sem desconto)
        # - desconto = valor_original - valor_titulo (recalculado corretamente)
        # =======================================================================

        # Converter desconto_percentual primeiro (precisamos para calcular valor_original)
        desconto_pct = row.get('desconto_concedido_percentual', 0)
        if desconto_pct:
            desconto_pct = float(desconto_pct) / 100

        # valor_titulo = saldo_total (valor com desconto correto 1x - valor a pagar)
        valor_titulo = float(row.get('saldo_total', 0) or 0)

        # valor_original = valor_titulo / (1 - desconto_pct), se houver desconto
        if desconto_pct and desconto_pct > 0 and desconto_pct < 1:
            valor_original = valor_titulo / (1 - desconto_pct)
        else:
            valor_original = valor_titulo

        # desconto = diferença entre original e título (recalculado corretamente)
        desconto = valor_original - valor_titulo

        conta = ContasAReceber(
            empresa=empresa,
            titulo_nf=titulo_nf,
            parcela=parcela,
            cnpj=row.get('partner_cnpj'),
            raz_social=row.get('partner_raz_social') or row.get('partner_id_nome'),
            raz_social_red=row.get('partner_raz_social_red'),
            uf_cliente=row.get('partner_state'),
            emissao=row.get('date'),
            vencimento=row.get('date_maturity'),
            valor_original=valor_original,
            desconto_percentual=desconto_pct,
            desconto=desconto,
            valor_titulo=valor_titulo,
            tipo_titulo=row.get('payment_provider_id_nome'),
            parcela_paga=bool(row.get('l10n_br_paga')),
            status_pagamento_odoo=row.get('x_studio_status_de_pagamento'),
            odoo_write_date=odoo_write_date,
            ultima_sincronizacao=datetime.utcnow(),
            criado_por='Sistema Odoo'
        )

        return conta

    def _atualizar_registro(self, conta: ContasAReceber, row, odoo_write_date: datetime):
        """Atualiza um registro existente com controle de snapshots"""

        alteracoes = []

        # =======================================================================
        # CORREÇÃO BUG DESCONTO DUPLO NO ODOO (2025-12-15)
        # =======================================================================
        # Primeiro calcular os valores financeiros corretamente
        # (mesma lógica do _criar_registro)
        # =======================================================================

        desconto_pct = row.get('desconto_concedido_percentual', 0)
        if desconto_pct:
            desconto_pct = float(desconto_pct) / 100

        # saldo_total do Odoo = valor com desconto correto 1x = nosso valor_titulo
        saldo_total_odoo = float(row.get('saldo_total', 0) or 0)

        # Calcular valor_original e desconto corretamente
        if desconto_pct and desconto_pct > 0 and desconto_pct < 1:
            valor_original_calc = saldo_total_odoo / (1 - desconto_pct)
        else:
            valor_original_calc = saldo_total_odoo

        desconto_calc = valor_original_calc - saldo_total_odoo
        valor_titulo_calc = saldo_total_odoo

        # Mapear campos do DataFrame para campos do modelo
        # NOTA: Removemos saldo_total, desconto_concedido do mapeamento automático
        # pois precisam de cálculo especial (bug desconto duplo)
        mapeamento = {
            'partner_cnpj': ('cnpj', lambda x: x),
            'partner_raz_social': ('raz_social', lambda x: x or row.get('partner_id_nome')),
            'partner_raz_social_red': ('raz_social_red', lambda x: x),
            'partner_state': ('uf_cliente', lambda x: x),
            'date': ('emissao', lambda x: x),
            'date_maturity': ('vencimento', lambda x: x),
            'payment_provider_id_nome': ('tipo_titulo', lambda x: x),
            'l10n_br_paga': ('parcela_paga', lambda x: bool(x)),
            'x_studio_status_de_pagamento': ('status_pagamento_odoo', lambda x: x),
        }

        for campo_df, (campo_modelo, converter) in mapeamento.items():
            valor_novo = converter(row.get(campo_df))
            valor_atual = getattr(conta, campo_modelo)

            # Verificar se houve alteração
            if self._valores_diferentes(valor_atual, valor_novo):
                if campo_modelo in self.CAMPOS_ODOO_AUDITADOS:
                    # Criar snapshot
                    ContasAReceberSnapshot.registrar_alteracao(
                        conta=conta,
                        campo=campo_modelo,
                        valor_anterior=valor_atual,
                        valor_novo=valor_novo,
                        usuario='Sistema Odoo',
                        odoo_write_date=odoo_write_date
                    )
                    self.estatisticas['snapshots_criados'] += 1

                setattr(conta, campo_modelo, valor_novo)
                alteracoes.append(campo_modelo)

        # Atualizar campos financeiros calculados (com snapshot se alterado)
        campos_financeiros = [
            ('valor_original', valor_original_calc),
            ('desconto_percentual', desconto_pct),
            ('desconto', desconto_calc),
            ('valor_titulo', valor_titulo_calc),
        ]

        for campo, valor_novo in campos_financeiros:
            valor_atual = getattr(conta, campo)
            if self._valores_diferentes(valor_atual, valor_novo):
                if campo in self.CAMPOS_ODOO_AUDITADOS:
                    ContasAReceberSnapshot.registrar_alteracao(
                        conta=conta,
                        campo=campo,
                        valor_anterior=valor_atual,
                        valor_novo=valor_novo,
                        usuario='Sistema Odoo',
                        odoo_write_date=odoo_write_date
                    )
                    self.estatisticas['snapshots_criados'] += 1

                setattr(conta, campo, valor_novo)
                alteracoes.append(campo)

        # Atualizar metadados
        conta.odoo_write_date = odoo_write_date
        conta.ultima_sincronizacao = datetime.utcnow()
        conta.atualizado_por = 'Sistema Odoo'

        if alteracoes:
            logger.debug(f"   📝 {conta.titulo_nf}-{conta.parcela}: {', '.join(alteracoes)}")

    def _valores_diferentes(self, valor1, valor2) -> bool:
        """Verifica se dois valores são diferentes, tratando tipos especiais"""
        if valor1 is None and valor2 is None:
            return False
        if valor1 is None or valor2 is None:
            return True

        # Comparar floats com tolerância
        if isinstance(valor1, float) and isinstance(valor2, float):
            return abs(valor1 - valor2) > 0.01

        # Comparar datas
        if isinstance(valor1, (date, datetime)) and isinstance(valor2, (date, datetime)):
            return valor1 != valor2

        return str(valor1) != str(valor2)

    def _enriquecer_dados_locais(self):
        """Enriquece registros com dados de EntregaMonitorada e FaturamentoProduto"""

        # Buscar contas sem entrega_monitorada_id
        contas_para_enriquecer = ContasAReceber.query.filter(
            ContasAReceber.entrega_monitorada_id.is_(None)
        ).all()

        logger.info(f"   📊 {len(contas_para_enriquecer)} contas para enriquecer")

        for conta in contas_para_enriquecer:
            # Buscar EntregaMonitorada
            entrega = EntregaMonitorada.query.filter_by(
                numero_nf=conta.titulo_nf
            ).first()

            if entrega:
                # Apenas vincula o relacionamento - dados são obtidos dinamicamente
                conta.entrega_monitorada_id = entrega.id

                # Calcular liberação antecipação (usa dados do relacionamento)
                conta.calcular_liberacao_antecipacao()

                self.estatisticas['enriquecidos'] += 1

            # nf_cancelada é obtido dinamicamente via property no modelo
            # (busca em FaturamentoProduto.status_nf = 'Cancelado')

    def _reprocessar_cnabs_sem_match(self) -> int:
        """
        Reprocessa CNABs que estavam sem match após sincronização de títulos.

        SIMPLIFICAÇÃO DO FLUXO CNAB (21/01/2026):
        Quando títulos são sincronizados do Odoo, CNABs que estavam
        com status_match = 'SEM_MATCH' são reprocessados automaticamente.
        Se encontrar título agora, faz o match e baixa automática.

        Returns:
            int: Quantidade de CNABs reprocessados com sucesso
        """
        # Importar o processor aqui para evitar import circular
        from app.financeiro.services.cnab400_processor_service import Cnab400ProcessorService

        # Buscar CNABs pendentes (sem match e não processados)
        cnabs_pendentes = CnabRetornoItem.query.filter(
            CnabRetornoItem.status_match == 'SEM_MATCH',
            CnabRetornoItem.processado == False
        ).all()

        if not cnabs_pendentes:
            logger.info("   ℹ️ Nenhum CNAB pendente para reprocessar")
            return 0

        logger.info(f"   📋 {len(cnabs_pendentes)} CNABs pendentes encontrados")

        processor = Cnab400ProcessorService()
        reprocessados = 0
        baixados = 0

        for item in cnabs_pendentes:
            try:
                # Tentar fazer match com título agora
                status_anterior = item.status_match
                processor._executar_matching(item)

                if item.status_match == 'MATCH_ENCONTRADO':
                    reprocessados += 1
                    logger.info(
                        f"   ✓ CNAB {item.id} NF {item.nf_extraida}/{item.parcela_extraida}: "
                        f"{status_anterior} → {item.status_match}"
                    )

                    # Tentar vincular com extrato
                    processor._executar_matching_extrato(item)

                    # Se tem título E extrato, fazer baixa automática
                    if item.conta_a_receber_id and item.extrato_item_id:
                        if processor._executar_baixa_automatica(item, 'SISTEMA_SYNC_AUTO'):
                            baixados += 1
                            logger.info(
                                f"   ✓ [BAIXA_AUTO] CNAB {item.id} baixado automaticamente"
                            )

            except Exception as e:
                logger.warning(
                    f"   ⚠️ CNAB {item.id}: Erro no reprocessamento: {e}"
                )
                continue

        if reprocessados > 0:
            logger.info(
                f"   ✅ {reprocessados} CNABs reprocessados, {baixados} baixados automaticamente"
            )

        return reprocessados
