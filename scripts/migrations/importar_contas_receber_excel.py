"""
Script de Importação de Contas a Receber via Excel (Por Chave)
===============================================================

Este script importa registros específicos do Odoo baseado em um Excel
com as chaves: Empresa (1, 2 ou 3) + Titulo_NF + Parcela.

Gera um Excel de erros para os registros não encontrados no Odoo.

Data: 2025-11-27
Autor: Sistema de Fretes

Formato do Excel de entrada:
- Coluna A: Empresa (1=FB, 2=SC, 3=CD)
- Coluna B: Titulo_NF (número da NF)
- Coluna C: Parcela (número da parcela)

Uso:
    python scripts/migrations/importar_contas_receber_excel.py <caminho_do_excel.xlsx>

Exemplo:
    python scripts/migrations/importar_contas_receber_excel.py uploads/contas_receber_importar.xlsx
"""

import sys
import os
from datetime import datetime, date

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pandas as pd
from app import create_app, db
from app.financeiro.services.contas_receber_service import ContasReceberService
from app.financeiro.services.sincronizacao_contas_receber_service import SincronizacaoContasReceberService
from app.financeiro.models import ContasAReceber
from app.monitoramento.models import EntregaMonitorada
from app.faturamento.models import RelatorioFaturamentoImportado
from app.utils.timezone import agora_utc_naive
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImportadorContasReceberExcel:
    """
    Importador de Contas a Receber via Excel.
    Busca registros específicos no Odoo e gera relatório de erros.
    """

    # Mapeamento de empresa Odoo -> código interno
    # 1 = FB (Fábrica), 2 = SC (Santa Catarina), 3 = CD (Centro de Distribuição)
    EMPRESA_MAP = {
        1: 'NACOM GOYA - FB',
        2: 'NACOM GOYA - SC',
        3: 'NACOM GOYA - CD',
    }

    EMPRESA_MAP_REVERSO = {
        'NACOM GOYA - FB': 1,
        'NACOM GOYA - SC': 2,
        'NACOM GOYA - CD': 3,
    }

    def __init__(self):
        self.odoo_service = ContasReceberService()
        self.sync_service = SincronizacaoContasReceberService()
        self.estatisticas = {
            'total_excel': 0,
            'encontrados': 0,
            'novos': 0,
            'atualizados': 0,
            'nao_encontrados': 0,
            'erros': []
        }

    def importar(self, caminho_excel: str, caminho_saida_erros: str = None) -> dict:
        """
        Importa registros do Excel, busca no Odoo e sincroniza.

        Args:
            caminho_excel: Caminho do arquivo Excel de entrada
            caminho_saida_erros: Caminho para salvar Excel de erros (opcional)

        Returns:
            dict com estatísticas da importação
        """
        print("\n" + "=" * 70)
        print("📊 IMPORTAÇÃO DE CONTAS A RECEBER VIA EXCEL")
        print("=" * 70)

        # 1. Ler Excel de entrada
        print(f"\n[1/4] Lendo Excel: {caminho_excel}")
        try:
            df_entrada = pd.read_excel(caminho_excel, header=None)
            # Nomear colunas
            df_entrada.columns = ['empresa', 'titulo_nf', 'parcela'][:len(df_entrada.columns)]

            # Garantir que temos as 3 colunas
            if len(df_entrada.columns) < 3:
                raise ValueError("Excel deve ter 3 colunas: Empresa, Titulo_NF, Parcela")

            self.estatisticas['total_excel'] = len(df_entrada)
            print(f"   ✅ {len(df_entrada)} registros lidos do Excel")
        except Exception as e:
            print(f"   ❌ Erro ao ler Excel: {e}")
            return self.estatisticas

        # 2. Buscar dados do Odoo (desde 24/11/2025 para ter todos disponíveis)
        print("\n[2/4] Buscando dados do Odoo desde 24/11/2025...")
        try:
            data_inicio = date(2025, 11, 24)
            dados_odoo = self.odoo_service.extrair_dados_odoo(data_inicio)
            df_odoo = self.odoo_service.aplicar_regras_negocio(dados_odoo)
            print(f"   ✅ {len(df_odoo)} registros disponíveis no Odoo")
        except Exception as e:
            print(f"   ❌ Erro ao buscar dados do Odoo: {e}")
            return self.estatisticas

        # 3. Criar índice para busca rápida no Odoo
        # Chave: (empresa_codigo, titulo_nf, parcela)
        print("\n[3/4] Processando registros...")

        odoo_index = {}
        for idx, row in df_odoo.iterrows():
            empresa_nome = row.get('company_id_nome', '')
            empresa_codigo = self._mapear_empresa_nome_para_codigo(empresa_nome)
            titulo_nf = str(int(row.get('x_studio_nf_e', 0)))
            parcela = str(row.get('l10n_br_cobranca_parcela', '1') or '1')

            if empresa_codigo > 0 and titulo_nf != '0':
                chave = (empresa_codigo, titulo_nf, parcela)
                odoo_index[chave] = row

        print(f"   📊 {len(odoo_index)} registros indexados do Odoo")

        # 4. Processar cada linha do Excel
        erros = []

        for idx, row in df_entrada.iterrows():
            try:
                empresa = int(row['empresa'])
                titulo_nf = str(int(row['titulo_nf']))
                parcela = str(row['parcela']) if pd.notna(row['parcela']) else '1'

                # Validar empresa
                if empresa not in [1, 2, 3]:
                    erros.append({
                        'linha': idx + 1,
                        'empresa': empresa,
                        'titulo_nf': titulo_nf,
                        'parcela': parcela,
                        'erro': f'Empresa inválida: {empresa}. Use 1 (FB), 2 (SC) ou 3 (CD)'
                    })
                    continue

                # Buscar no índice do Odoo
                chave = (empresa, titulo_nf, parcela)
                registro_odoo = odoo_index.get(chave)

                if registro_odoo is None:
                    erros.append({
                        'linha': idx + 1,
                        'empresa': empresa,
                        'titulo_nf': titulo_nf,
                        'parcela': parcela,
                        'erro': 'Não encontrado no Odoo (desde 24/11/2025)'
                    })
                    self.estatisticas['nao_encontrados'] += 1
                    continue

                # Encontrado! Processar registro
                self.estatisticas['encontrados'] += 1
                self._processar_registro(registro_odoo, empresa, titulo_nf, parcela)

            except Exception as e:
                erros.append({
                    'linha': idx + 1,
                    'empresa': row.get('empresa', ''),
                    'titulo_nf': row.get('titulo_nf', ''),
                    'parcela': row.get('parcela', ''),
                    'erro': str(e)
                })

        db.session.commit()

        # Enriquecer com dados locais
        print("\n[4/4] Enriquecendo com dados locais...")
        self._enriquecer_dados_locais()
        db.session.commit()

        self.estatisticas['erros'] = erros

        # Gerar Excel de erros se houver
        if erros:
            if caminho_saida_erros is None:
                caminho_saida_erros = caminho_excel.replace('.xlsx', '_ERROS.xlsx')

            df_erros = pd.DataFrame(erros)
            df_erros.to_excel(caminho_saida_erros, index=False)
            print(f"\n⚠️  {len(erros)} erros salvos em: {caminho_saida_erros}")

        # Resumo
        print("\n" + "=" * 70)
        print("📋 RESUMO DA IMPORTAÇÃO")
        print("=" * 70)
        print(f"   📊 Total no Excel: {self.estatisticas['total_excel']}")
        print(f"   ✅ Encontrados no Odoo: {self.estatisticas['encontrados']}")
        print(f"   🆕 Novos registros: {self.estatisticas['novos']}")
        print(f"   🔄 Atualizados: {self.estatisticas['atualizados']}")
        print(f"   ❌ Não encontrados: {self.estatisticas['nao_encontrados']}")
        print(f"   ⚠️  Erros: {len(erros)}")

        return self.estatisticas

    def _mapear_empresa_nome_para_codigo(self, nome_empresa: str) -> int:
        """Mapeia o nome da empresa Odoo para o código interno"""
        if not nome_empresa:
            return 0

        for nome, codigo in self.EMPRESA_MAP_REVERSO.items():
            if nome.upper() in nome_empresa.upper() or nome_empresa.upper() in nome.upper():
                return codigo

        nome_upper = nome_empresa.upper()
        if '- FB' in nome_upper or nome_upper.endswith('FB'):
            return 1
        elif '- SC' in nome_upper or nome_upper.endswith('SC'):
            return 2
        elif '- CD' in nome_upper or nome_upper.endswith('CD'):
            return 3

        return 0

    def _processar_registro(self, row, empresa: int, titulo_nf: str, parcela: str):
        """Processa um registro encontrado no Odoo"""

        # Buscar registro existente no banco
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

        valor_original = float(row.get('saldo_total', 0) or 0)
        desconto = float(row.get('desconto_concedido', 0) or 0)
        valor_titulo = valor_original - desconto

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
            criado_por='Importação Excel'
        )

        return conta

    def _atualizar_registro(self, conta: ContasAReceber, row, odoo_write_date: datetime):
        """Atualiza um registro existente"""

        conta.cnpj = row.get('partner_cnpj') or conta.cnpj
        conta.raz_social = row.get('partner_id_nome') or row.get('partner_raz_social') or conta.raz_social
        conta.raz_social_red = row.get('partner_raz_social_red') or conta.raz_social_red
        conta.uf_cliente = row.get('partner_state') or conta.uf_cliente
        conta.emissao = row.get('date') or conta.emissao
        conta.vencimento = row.get('date_maturity') or conta.vencimento

        valor_original = float(row.get('saldo_total', 0) or 0)
        desconto = float(row.get('desconto_concedido', 0) or 0)

        conta.valor_original = valor_original
        conta.desconto = desconto
        conta.valor_titulo = valor_original - desconto

        desconto_pct = row.get('desconto_concedido_percentual', 0)
        if desconto_pct:
            conta.desconto_percentual = float(desconto_pct) / 100

        conta.tipo_titulo = row.get('payment_provider_id_nome') or conta.tipo_titulo
        conta.parcela_paga = bool(row.get('l10n_br_paga'))
        conta.status_pagamento_odoo = row.get('x_studio_status_de_pagamento') or conta.status_pagamento_odoo

        conta.odoo_write_date = odoo_write_date
        conta.ultima_sincronizacao = agora_utc_naive()
        conta.atualizado_por = 'Importação Excel'

    def _enriquecer_dados_locais(self):
        """Enriquece registros com dados de EntregaMonitorada"""

        contas_para_enriquecer = ContasAReceber.query.filter(
            ContasAReceber.entrega_monitorada_id.is_(None)
        ).all()

        enriquecidos = 0
        for conta in contas_para_enriquecer:
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

                if entrega.agendamentos:
                    ultimo_ag = sorted(entrega.agendamentos, key=lambda ag: ag.criado_em, reverse=True)[0]
                    conta.ultimo_agendamento_data = ultimo_ag.data_agendada
                    conta.ultimo_agendamento_status = ultimo_ag.status
                    conta.ultimo_agendamento_protocolo = ultimo_ag.protocolo_agendamento

                conta.calcular_liberacao_antecipacao()
                enriquecidos += 1

            # Verificar NF cancelada
            nf_cancelada = RelatorioFaturamentoImportado.query.filter_by(
                numero_nf=conta.titulo_nf,
                ativo=False
            ).first()

            if nf_cancelada:
                conta.nf_cancelada = True

        print(f"   ✅ {enriquecidos} registros enriquecidos com dados locais")


def main():
    """Função principal"""
    if len(sys.argv) < 2:
        print("\n❌ Uso: python importar_contas_receber_excel.py <caminho_do_excel.xlsx>")
        print("\nFormato do Excel:")
        print("  - Coluna A: Empresa (1=FB, 2=SC, 3=CD)")
        print("  - Coluna B: Titulo_NF (número da NF)")
        print("  - Coluna C: Parcela (número da parcela)")
        print("\nExemplo:")
        print("  python importar_contas_receber_excel.py uploads/contas_receber.xlsx")
        sys.exit(1)

    caminho_excel = sys.argv[1]

    if not os.path.exists(caminho_excel):
        print(f"\n❌ Arquivo não encontrado: {caminho_excel}")
        sys.exit(1)

    app = create_app()

    with app.app_context():
        importador = ImportadorContasReceberExcel()
        importador.importar(caminho_excel)

        print("\n✅ Importação concluída!\n")


if __name__ == '__main__':
    main()
