"""
Teste de Sincronização de Contas a Receber
==========================================

Este script testa a sincronização de dados do Odoo para a tabela contas_a_receber.

Data: 2025-11-27
Autor: Sistema de Fretes
"""

import sys
import os
from datetime import datetime, date, timedelta

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from app.financeiro.services.contas_receber_service import ContasReceberService
from app.financeiro.models import (
    ContasAReceber, ContasAReceberTipo, ContasAReceberAbatimento,
    ContasAReceberSnapshot, LiberacaoAntecipacao
)
from app.monitoramento.models import EntregaMonitorada
from app.faturamento.models import RelatorioFaturamentoImportado
from app.utils.timezone import agora_utc_naive
from sqlalchemy import text
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SincronizacaoContasReceberService:
    """
    Serviço para sincronizar dados do Odoo para a tabela contas_a_receber
    com enriquecimento de dados locais e controle de alterações.
    """

    # Mapeamento de empresa Odoo -> código interno
    EMPRESA_MAP = {
        'NACOM GOYA - FB': 1,
        'NACOM GOYA INDÚSTRIA E COMÉRCIO DE ALIMENTOS LTDA - Filial Brodowski': 1,
        'NACOM GOYA - SC': 2,
        'NACOM GOYA INDÚSTRIA E COMÉRCIO DE ALIMENTOS LTDA - Filial Seberi': 2,
        'NACOM GOYA - CD': 3,
        'NACOM GOYA INDÚSTRIA E COMÉRCIO DE ALIMENTOS LTDA - CD': 3,
    }

    # Campos do Odoo que devem gerar snapshot quando alterados
    CAMPOS_ODOO_AUDITADOS = [
        'valor_original', 'desconto_percentual', 'desconto', 'vencimento',
        'emissao', 'tipo_titulo', 'parcela_paga', 'status_pagamento_odoo',
        'raz_social', 'raz_social_red', 'cnpj', 'uf_cliente'
    ]

    def __init__(self):
        self.odoo_service = ContasReceberService()
        self.estatisticas = {
            'novos': 0,
            'atualizados': 0,
            'erros': 0,
            'snapshots_criados': 0,
            'enriquecidos': 0
        }

    def _mapear_empresa(self, nome_empresa: str) -> int:
        """Mapeia o nome da empresa Odoo para o código interno"""
        for nome, codigo in self.EMPRESA_MAP.items():
            if nome.upper() in nome_empresa.upper() or nome_empresa.upper() in nome.upper():
                return codigo

        # Fallback: tentar identificar pelo nome
        nome_upper = nome_empresa.upper()
        if 'FB' in nome_upper or 'BRODOWSKI' in nome_upper:
            return 1
        elif 'SC' in nome_upper or 'SEBERI' in nome_upper:
            return 2
        elif 'CD' in nome_upper:
            return 3

        logger.warning(f"⚠️ Empresa não mapeada: {nome_empresa}")
        return 0

    def sincronizar(self, data_inicio: date = None, limite: int = None) -> dict:
        """
        Executa a sincronização completa de Contas a Receber.

        Args:
            data_inicio: Data inicial para busca no Odoo (default: D-7)
            limite: Limite de registros para teste (default: None = todos)

        Returns:
            dict com estatísticas da sincronização
        """
        logger.info("=" * 60)
        logger.info("🔄 INICIANDO SINCRONIZAÇÃO DE CONTAS A RECEBER")
        logger.info("=" * 60)

        if data_inicio is None:
            data_inicio = date.today() - timedelta(days=7)

        logger.info(f"📅 Data inicial: {data_inicio}")

        # 1. Extrair dados do Odoo
        logger.info("\n[1/4] Extraindo dados do Odoo...")
        dados_odoo = self.odoo_service.extrair_dados_odoo(data_inicio)
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

        # Resumo
        logger.info("\n" + "=" * 60)
        logger.info("✅ SINCRONIZAÇÃO CONCLUÍDA")
        logger.info("=" * 60)
        logger.info(f"📊 Novos: {self.estatisticas['novos']}")
        logger.info(f"📊 Atualizados: {self.estatisticas['atualizados']}")
        logger.info(f"📊 Enriquecidos: {self.estatisticas['enriquecidos']}")
        logger.info(f"📊 Snapshots: {self.estatisticas['snapshots_criados']}")
        logger.info(f"📊 Erros: {self.estatisticas['erros']}")

        return self.estatisticas

    def _processar_registro(self, row):
        """Processa um registro do Odoo"""

        # Extrair dados do registro
        empresa_nome = row.get('company_id_nome', '')
        empresa = self._mapear_empresa(empresa_nome)
        titulo_nf = str(int(row.get('x_studio_nf_e', 0)))
        parcela = str(row.get('l10n_br_cobranca_parcela', '1') or '1')

        if not titulo_nf or titulo_nf == '0':
            return

        # Buscar registro existente
        conta = ContasAReceber.query.filter_by(
            empresa=empresa,
            titulo_nf=titulo_nf,
            parcela=parcela
        ).first()

        odoo_write_date = agora_utc_naive()

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

        # Calcular valor_titulo inicial
        valor_original = float(row.get('saldo_total', 0) or 0)
        desconto = float(row.get('desconto_concedido', 0) or 0)
        valor_titulo = valor_original - desconto

        # Converter desconto_percentual
        desconto_pct = row.get('desconto_concedido_percentual', 0)
        if desconto_pct:
            desconto_pct = float(desconto_pct) / 100

        conta = ContasAReceber(
            empresa=empresa,
            titulo_nf=titulo_nf,
            parcela=parcela,
            cnpj=row.get('partner_cnpj'),
            raz_social=row.get('partner_id_nome') or row.get('partner_raz_social'),
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
            ultima_sincronizacao=agora_utc_naive(),
            criado_por='Sistema Odoo'
        )

        return conta

    def _atualizar_registro(self, conta: ContasAReceber, row, odoo_write_date: datetime):
        """Atualiza um registro existente com controle de snapshots"""

        alteracoes = []

        # Mapear campos do DataFrame para campos do modelo
        mapeamento = {
            'partner_cnpj': ('cnpj', lambda x: x),
            'partner_id_nome': ('raz_social', lambda x: x or row.get('partner_raz_social')),
            'partner_raz_social_red': ('raz_social_red', lambda x: x),
            'partner_state': ('uf_cliente', lambda x: x),
            'date': ('emissao', lambda x: x),
            'date_maturity': ('vencimento', lambda x: x),
            'saldo_total': ('valor_original', lambda x: float(x or 0)),
            'desconto_concedido_percentual': ('desconto_percentual', lambda x: float(x or 0) / 100 if x else 0),
            'desconto_concedido': ('desconto', lambda x: float(x or 0)),
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

        # Recalcular valor_titulo
        conta.valor_titulo = (conta.valor_original or 0) - (conta.desconto or 0)

        # Atualizar metadados
        conta.odoo_write_date = odoo_write_date
        conta.ultima_sincronizacao = agora_utc_naive()
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
                conta.entrega_monitorada_id = entrega.id
                conta.data_entrega_prevista = entrega.data_entrega_prevista
                conta.data_hora_entrega_realizada = entrega.data_hora_entrega_realizada
                conta.status_finalizacao = entrega.status_finalizacao
                conta.nova_nf = entrega.nova_nf
                conta.reagendar = entrega.reagendar
                conta.data_embarque = entrega.data_embarque
                conta.transportadora = entrega.transportadora
                conta.vendedor = entrega.vendedor
                conta.canhoto_arquivo = entrega.canhoto_arquivo
                conta.nf_cd = entrega.nf_cd

                # Último agendamento
                if entrega.agendamentos:
                    ultimo_ag = sorted(entrega.agendamentos, key=lambda ag: ag.criado_em, reverse=True)[0]
                    conta.ultimo_agendamento_data = ultimo_ag.data_agendada
                    conta.ultimo_agendamento_status = ultimo_ag.status
                    conta.ultimo_agendamento_protocolo = ultimo_ag.protocolo_agendamento

                # Calcular liberação antecipação
                conta.calcular_liberacao_antecipacao()

                self.estatisticas['enriquecidos'] += 1

            # Verificar NF cancelada via FaturamentoProduto
            nf_cancelada = RelatorioFaturamentoImportado.query.filter_by(
                numero_nf=conta.titulo_nf,
                ativo=False
            ).first()

            if nf_cancelada:
                conta.nf_cancelada = True


def main():
    """Função principal de teste"""

    app = create_app()

    with app.app_context():
        print("\n" + "=" * 70)
        print("🧪 TESTE DE SINCRONIZAÇÃO DE CONTAS A RECEBER")
        print("=" * 70)

        # Criar serviço
        service = SincronizacaoContasReceberService()

        # Executar sincronização com limite para teste
        data_inicio = date.today() - timedelta(days=30)  # Últimos 30 dias
        limite = 50  # Limitar a 50 registros para teste

        print(f"\n📅 Período: últimos 30 dias (desde {data_inicio})")
        print(f"📊 Limite: {limite} registros\n")

        estatisticas = service.sincronizar(data_inicio=data_inicio, limite=limite)

        # Verificar resultado
        print("\n" + "=" * 70)
        print("📋 VERIFICAÇÃO FINAL")
        print("=" * 70)

        total = ContasAReceber.query.count()
        print(f"\n📊 Total de registros em contas_a_receber: {total}")

        # Amostra de dados
        amostra = ContasAReceber.query.limit(5).all()
        if amostra:
            print("\n📄 Amostra de registros:")
            for conta in amostra:
                print(f"   - {conta.empresa_nome} | NF {conta.titulo_nf}-{conta.parcela} | {conta.raz_social_red or conta.raz_social} | R$ {conta.valor_titulo:.2f}")

        print("\n✅ Teste concluído!\n")


if __name__ == '__main__':
    main()
