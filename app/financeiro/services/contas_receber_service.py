"""
Serviço de Contas a Receber
============================

Extrai relatório do Odoo (account.move.line), aplica regras de negócio
e enriquece com dados locais de entregas e agendamentos.

Autor: Sistema de Fretes
Data: 2025-11-18
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
import pandas as pd
from app.odoo.utils.connection import get_odoo_connection
from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
from app import db

logger = logging.getLogger(__name__)


class ContasReceberService:
    """
    Serviço para exportação de Contas a Receber do Odoo
    com enriquecimento de dados locais
    """

    # Mapeamento de campos do Odoo
    CAMPOS_ODOO = [
        'company_id',  # Empresa
        'x_studio_tipo_de_documento_fiscal',  # Tipo Doc Fiscal
        'x_studio_nf_e',  # NF-e
        'l10n_br_cobranca_parcela',  # Parcela
        'l10n_br_paga',  # Parcela Paga?
        'partner_id',  # Cliente (retorna [id, nome])
        'date',  # Data
        'date_maturity',  # Vencimento
        'balance',  # Saldo
        'desconto_concedido',  # Desconto Concedido
        'desconto_concedido_percentual',  # Desconto Concedido (%)
        'payment_provider_id',  # Forma de Pagamento
        'x_studio_status_de_pagamento',  # Status de Pagamento
        'amount_residual',  # Saldo residual (valor em aberto)
        'account_type',  # Tipo de conta (asset_receivable, etc)
        'move_type',  # Tipo de movimento (out_invoice, entry, etc)
        'parent_state',  # Estado da fatura (posted, draft, cancel)
    ]

    def __init__(self):
        self.connection = get_odoo_connection()

    def extrair_dados_odoo(
        self,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None
    ) -> List[Dict]:
        """
        Extrai dados do Odoo (account.move.line)

        Args:
            data_inicio: Data inicial para filtro (default: D-1)
            data_fim: Data final para filtro (opcional - se não informado, busca a partir de data_inicio)

        Returns:
            Lista de dicionários com dados do Odoo
        """
        logger.info("🔍 Iniciando extração de dados do Odoo...")

        # Regra 1: Data = D-1 (ou data especificada)
        if data_inicio is None:
            data_inicio = date.today() - timedelta(days=1)

        # Log do período
        if data_fim:
            logger.info(f"📅 Filtrando registros de {data_inicio} até {data_fim}")
        else:
            logger.info(f"📅 Filtrando registros a partir de: {data_inicio}")

        # Autenticar
        if not self.connection.authenticate():
            raise Exception("❌ Falha na autenticação com Odoo")

        # Buscar registros
        # FILTRO CRÍTICO: Apenas CONTAS A RECEBER ativas
        try:
            # Montar domain base
            domain = [
                ['date', '>=', data_inicio.strftime('%Y-%m-%d')],
                ['account_type', '=', 'asset_receivable'],  # Apenas contas a receber
                ['balance', '>', 0],  # Saldo positivo (a receber)
                ['date_maturity', '!=', False],  # Com vencimento preenchido
                ['parent_state', '=', 'posted'],  # Apenas faturas lançadas (não draft/cancel)
            ]

            # Adicionar filtro de data_fim se especificado
            if data_fim:
                domain.append(['date', '<=', data_fim.strftime('%Y-%m-%d')])

            registros = self.connection.search_read(
                'account.move.line',
                domain,
                fields=self.CAMPOS_ODOO,
                limit=None  # Sem limite
            )

            logger.info(f"✅ {len(registros)} registros extraídos do Odoo")

            # Enriquecer com dados dos parceiros (2ª query): UF, CNPJ, Razão Social
            registros = self._enriquecer_dados_parceiros(registros)

            return registros

        except Exception as e:
            logger.error(f"❌ Erro ao extrair dados do Odoo: {e}")
            raise

    def _enriquecer_dados_parceiros(self, registros: List[Dict]) -> List[Dict]:
        """
        Busca dados adicionais dos parceiros através de query em res.partner:
        - state_id (UF)
        - l10n_br_cnpj (CNPJ)
        - trade_name (Nome fantasia / Razão Social Reduzida)
        - name (Razão Social completa - fallback para trade_name)

        Args:
            registros: Lista de registros de account.move.line

        Returns:
            Lista de registros enriquecida com campos de parceiro
        """
        logger.info("🔍 Buscando dados dos parceiros via res.partner...")

        # Extrair IDs únicos de parceiros
        partner_ids = set()
        for reg in registros:
            partner = reg.get('partner_id')
            if partner and isinstance(partner, (list, tuple)) and len(partner) > 0:
                partner_ids.add(partner[0])

        partner_ids = list(partner_ids)

        if not partner_ids:
            logger.warning("⚠️  Nenhum parceiro para buscar dados")
            return registros

        logger.info(f"📊 Buscando dados de {len(partner_ids)} parceiros únicos...")

        # Buscar parceiros com todos os campos necessários em lotes (evitar timeout)
        BATCH_SIZE = 500
        partner_data_map = {}

        for i in range(0, len(partner_ids), BATCH_SIZE):
            batch = partner_ids[i:i + BATCH_SIZE]

            try:
                # Campos do res.partner:
                # - l10n_br_cnpj: CNPJ do parceiro
                # - l10n_br_razao_social: Razão Social completa (campo brasileiro)
                # - name: Nome fantasia / Nome reduzido (usado como raz_social_red)
                # - state_id: UF do parceiro
                partners_data = self.connection.search_read(
                    'res.partner',
                    [['id', 'in', batch]],
                    fields=['id', 'state_id', 'l10n_br_cnpj', 'l10n_br_razao_social', 'name'],
                    limit=None
                )

                for partner in partners_data:
                    partner_id = partner.get('id')

                    # UF - O Odoo retorna [id, 'Nome Estado (BR)'] ou False
                    # Precisamos extrair apenas a sigla de 2 caracteres
                    state_id = partner.get('state_id')  # Retorna [id, 'São Paulo (BR)'] ou False
                    uf = None
                    if state_id and isinstance(state_id, (list, tuple)) and len(state_id) > 1:
                        estado_nome = state_id[1]  # Ex: 'São Paulo (BR)' ou 'SP'
                        # Se já é sigla de 2 caracteres, usar direto
                        if len(estado_nome) == 2:
                            uf = estado_nome.upper()
                        else:
                            # Mapeamento de nomes de estados para siglas
                            estado_map = {
                                'acre': 'AC', 'alagoas': 'AL', 'amapá': 'AP', 'amazonas': 'AM',
                                'bahia': 'BA', 'ceará': 'CE', 'distrito federal': 'DF',
                                'espírito santo': 'ES', 'goiás': 'GO', 'maranhão': 'MA',
                                'mato grosso': 'MT', 'mato grosso do sul': 'MS', 'minas gerais': 'MG',
                                'pará': 'PA', 'paraíba': 'PB', 'paraná': 'PR', 'pernambuco': 'PE',
                                'piauí': 'PI', 'rio de janeiro': 'RJ', 'rio grande do norte': 'RN',
                                'rio grande do sul': 'RS', 'rondônia': 'RO', 'roraima': 'RR',
                                'santa catarina': 'SC', 'são paulo': 'SP', 'sergipe': 'SE', 'tocantins': 'TO'
                            }
                            # Remover ' (BR)' e tentar encontrar no mapa
                            estado_limpo = estado_nome.replace(' (BR)', '').lower().strip()
                            uf = estado_map.get(estado_limpo)
                            if not uf:
                                # Fallback: pegar as 2 primeiras letras
                                uf = estado_nome[:2].upper() if estado_nome else None

                    # CNPJ
                    cnpj = partner.get('l10n_br_cnpj') or None

                    # Razão Social completa (campo l10n_br_razao_social)
                    raz_social = partner.get('l10n_br_razao_social') or partner.get('name', '')

                    # Nome fantasia / Razão Social Reduzida (campo name)
                    name = partner.get('name', '')
                    raz_social_red = name[:100] if name else None

                    partner_data_map[partner_id] = {
                        'uf': uf,
                        'cnpj': cnpj,
                        'raz_social_red': raz_social_red,
                        'raz_social': raz_social
                    }

                logger.info(f"✅ Processado lote {i//BATCH_SIZE + 1}/{(len(partner_ids)-1)//BATCH_SIZE + 1}")

            except Exception as e:
                logger.error(f"⚠️  Erro ao buscar lote de dados de parceiros: {e}")
                continue

        logger.info(f"✅ {len(partner_data_map)} parceiros com dados mapeados")

        # Enriquecer registros com dados dos parceiros
        for reg in registros:
            partner = reg.get('partner_id')
            if partner and isinstance(partner, (list, tuple)) and len(partner) > 0:
                partner_id = partner[0]
                partner_data = partner_data_map.get(partner_id, {})
                reg['partner_state'] = partner_data.get('uf')
                reg['partner_cnpj'] = partner_data.get('cnpj')
                reg['partner_raz_social_red'] = partner_data.get('raz_social_red')
                reg['partner_raz_social'] = partner_data.get('raz_social')
            else:
                reg['partner_state'] = None
                reg['partner_cnpj'] = None
                reg['partner_raz_social_red'] = None
                reg['partner_raz_social'] = None

        logger.info(f"✅ Registros enriquecidos com dados dos parceiros (UF, CNPJ, Razão Social)")

        return registros

    def aplicar_regras_negocio(self, dados: List[Dict]) -> pd.DataFrame:
        """
        Aplica as 11 regras de manipulação nos dados

        Regras:
        1. Data = D-1 (já aplicado na extração)
        2. Remover linhas com NF-e vazio, nulo ou 0
        3. Remover linhas com balance <= 0
        4. Remover linhas com company_id = LA FAMIGLIA-LF
        5. Remover linhas com date_maturity < 02/01/2000
        6. Transformar x_studio_nf_e em integer e ordenar crescente
        7. Transformar date e date_maturity em DATE
        8. Criar coluna "Saldo Total" = balance + desconto_concedido
        9. Remover coluna balance
        10. Remover linhas onde payment_provider_id != "Transferência Bancária CD"
        11. Enriquecer com dados locais (feito em método separado)

        Args:
            dados: Lista de dicionários do Odoo

        Returns:
            DataFrame pandas processado
        """
        logger.info(f"⚙️  Aplicando regras de negócio em {len(dados)} registros...")

        # Converter para DataFrame
        df = pd.DataFrame(dados)

        if df.empty:
            logger.warning("⚠️  Nenhum dado para processar")
            return df

        total_inicial = len(df)
        logger.info(f"📊 Total inicial: {total_inicial} registros")

        # Normalizar campos relacionais (company_id, partner_id, etc.)
        df = self._normalizar_campos_relacionais(df)

        # Regra 2: Remover NF-e vazio, nulo ou 0
        # NOTA: x_studio_nf_e pode ser False (campo não preenchido) OU string com número
        # Vamos manter apenas registros com NF-e preenchida (string não vazia)
        total_antes_regra2 = len(df)

        def tem_nfe_valida(valor):
            """Verifica se NF-e é válida (não vazia/nula)"""
            if pd.isna(valor):
                return False
            if valor == False or valor == '':
                return False
            if str(valor).strip() in ['0', '']:
                return False
            return True

        df = df[df['x_studio_nf_e'].apply(tem_nfe_valida)]
        logger.info(f"✅ Regra 2: {len(df)} registros (removidos {total_antes_regra2 - len(df)} sem NF-e válida)")

        # Regra 3: Remover balance <= 0 (JÁ FILTRADO NA QUERY, mas garantir)
        total_antes = len(df)
        df = df[df['balance'] > 0]
        logger.info(f"✅ Regra 3: {len(df)} registros (removidos {total_antes - len(df)} com saldo <= 0)")

        # NOVA: Remover duplicatas (NF + PARCELA - manter todas as parcelas!)
        # IMPORTANTE: Usar company_id + nf + parcela para permitir mesma NF em empresas diferentes
        total_antes = len(df)
        df = df.drop_duplicates(subset=['company_id_nome', 'x_studio_nf_e', 'l10n_br_cobranca_parcela'], keep='first')
        logger.info(f"✅ Regra Extra: {len(df)} registros (removidos {total_antes - len(df)} duplicatas exatas)")

        # Regra 4: Remover company_id = "LA FAMIGLIA-LF"
        total_antes = len(df)
        df = df[df['company_id_nome'] != 'LA FAMIGLIA-LF']
        logger.info(f"✅ Regra 4: {len(df)} registros (removidos {total_antes - len(df)} da LA FAMIGLIA-LF)")

        # Regra 5: Remover date_maturity inválido (< 02/01/2000 OU vazio)
        # CRÍTICO: Remover linhas com vencimento vazio
        total_antes = len(df)
        df['date_maturity'] = pd.to_datetime(df['date_maturity'], errors='coerce')
        df = df[df['date_maturity'].notna()]  # Remover vazios (CRÍTICO)
        df = df[df['date_maturity'] >= '2000-01-02']  # Remover datas antigas
        logger.info(f"✅ Regra 5: {len(df)} registros (removidos {total_antes - len(df)} com vencimento inválido)")

        if len(df) == 0:
            logger.warning("⚠️  NENHUM registro após Regra 5! Verifique filtros.")

        # Regra 6: Transformar x_studio_nf_e em integer e ordenar
        df['x_studio_nf_e'] = pd.to_numeric(df['x_studio_nf_e'], errors='coerce').fillna(0).astype(int)
        df = df.sort_values('x_studio_nf_e', ascending=True)
        logger.info(f"✅ Regra 6: NF-e convertido para integer e ordenado")

        # Regra 7: Transformar date e date_maturity em DATE
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
        df['date_maturity'] = pd.to_datetime(df['date_maturity'], errors='coerce').dt.date
        logger.info(f"✅ Regra 7: Datas convertidas para formato DATE")

        # Regra 8: Criar coluna "Saldo Total" = balance + desconto_concedido
        df['desconto_concedido'] = pd.to_numeric(df['desconto_concedido'], errors='coerce').fillna(0)
        df['saldo_total'] = df['balance'] + df['desconto_concedido']
        logger.info(f"✅ Regra 8: Coluna 'Saldo Total' criada")

        # Regra 9: Remover coluna balance
        df = df.drop(columns=['balance'])
        logger.info(f"✅ Regra 9: Coluna 'balance' removida")

        # Regra 10: REMOVIDA - Agora aceita todas as formas de pagamento
        # Anteriormente filtrava apenas "Transferência Bancária"
        # Mantido para referência histórica
        logger.info(f"✅ Regra 10: DESATIVADA - Todas as formas de pagamento são aceitas")

        logger.info(f"🎯 Total final após regras: {len(df)} registros ({total_inicial - len(df)} removidos)")

        return df

    def _normalizar_campos_relacionais(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza campos relacionais do Odoo (many2one)

        Odoo retorna campos many2one como [ID, "Nome"]
        Precisamos extrair ID e Nome em colunas separadas
        """
        campos_relacionais = [
            ('company_id', 'Empresa'),
            ('partner_id', 'Parceiro/Cliente'),
            ('payment_provider_id', 'Forma de Pagamento')
        ]

        for campo, label in campos_relacionais:
            if campo in df.columns:
                # Extrair ID
                df[f'{campo}_id'] = df[campo].apply(
                    lambda x: x[0] if isinstance(x, (list, tuple)) and len(x) > 0 else None
                )

                # Extrair Nome
                df[f'{campo}_nome'] = df[campo].apply(
                    lambda x: x[1] if isinstance(x, (list, tuple)) and len(x) > 1 else ''
                )

        return df

    def enriquecer_com_dados_locais(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Regra 11: Enriquece dados com informações locais

        Busca dados de EntregaMonitorada e último AgendamentoEntrega
        usando numero_nf como chave

        Campos adicionados:
        - data_entrega_prevista
        - data_hora_entrega_realizada
        - entregue
        - ultimo_agendamento_data
        - ultimo_agendamento_status
        """
        logger.info("🔗 Enriquecendo com dados locais...")

        if df.empty:
            return df

        # Buscar todas as entregas de uma vez (otimização)
        nfs = df['x_studio_nf_e'].unique().tolist()
        nfs = [str(nf) for nf in nfs if nf and nf != 0]

        if not nfs:
            logger.warning("⚠️  Nenhuma NF válida para enriquecimento")
            return df

        logger.info(f"🔍 Buscando dados de {len(nfs)} NFs no banco local...")

        # Buscar entregas
        entregas = EntregaMonitorada.query.filter(
            EntregaMonitorada.numero_nf.in_(nfs)
        ).all()

        logger.info(f"✅ {len(entregas)} entregas encontradas no banco local")

        # Criar dicionário de entregas por NF
        entregas_dict = {
            str(e.numero_nf): e for e in entregas
        }

        # Aplicar enriquecimento
        def enriquecer_linha(row):
            nf = str(row['x_studio_nf_e'])
            entrega = entregas_dict.get(nf)

            if entrega:
                row['data_entrega_prevista'] = entrega.data_entrega_prevista
                row['data_hora_entrega_realizada'] = entrega.data_hora_entrega_realizada
                row['entregue'] = entrega.entregue

                # Buscar último agendamento
                ultimo_agendamento = entrega.data_agendamento_mais_recente
                if ultimo_agendamento:
                    row['ultimo_agendamento_data'] = ultimo_agendamento

                    # Buscar status do agendamento mais recente
                    agendamentos = sorted(entrega.agendamentos, key=lambda ag: ag.criado_em, reverse=True)
                    if agendamentos:
                        row['ultimo_agendamento_status'] = agendamentos[0].status
                else:
                    row['ultimo_agendamento_data'] = None
                    row['ultimo_agendamento_status'] = None
            else:
                row['data_entrega_prevista'] = None
                row['data_hora_entrega_realizada'] = None
                row['entregue'] = False
                row['ultimo_agendamento_data'] = None
                row['ultimo_agendamento_status'] = None

            return row

        df = df.apply(enriquecer_linha, axis=1)

        logger.info(f"✅ Enriquecimento concluído!")

        return df

    def exportar_excel(self, data_inicio: Optional[date] = None) -> bytes:
        """
        Exporta relatório completo em Excel

        Returns:
            Bytes do arquivo Excel
        """
        logger.info("📊 Iniciando exportação para Excel...")

        # 1. Extrair dados do Odoo
        dados = self.extrair_dados_odoo(data_inicio)

        # 2. Aplicar regras de negócio
        df = self.aplicar_regras_negocio(dados)

        # 3. Enriquecer com dados locais
        df = self.enriquecer_com_dados_locais(df)

        # 4. Renomear colunas para português
        df = self._renomear_colunas_excel(df)

        # 5. Remover colunas desnecessárias (IDs e campos técnicos do Odoo)
        colunas_remover = [
            'id',  # ID da linha (desnecessário)
            'company_id', 'partner_id', 'payment_provider_id',
            'company_id_id', 'partner_id_id', 'payment_provider_id_id',
            'account_type', 'move_type', 'parent_state'  # Campos técnicos usados apenas para filtro
        ]
        df = df.drop(columns=[col for col in colunas_remover if col in df.columns])
        logger.info(f"✅ Colunas desnecessárias removidas")

        # 6. Gerar Excel
        from io import BytesIO
        output = BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Contas a Receber')

            # Obter worksheet
            worksheet = writer.sheets['Contas a Receber']

            # Colunas de data para formatar
            colunas_data = [
                'Data',
                'Data de Vencimento',
                'Data Entrega Prevista',
                'Data/Hora Entrega Realizada',
                'Último Agendamento - Data'
            ]

            # Mapear nomes de colunas para índices (letras)
            header_row = {cell.value: cell.column_letter for cell in worksheet[1]}

            # Ajustar largura e formatar datas
            from openpyxl.styles import numbers

            for column in worksheet.columns:
                column_letter = column[0].column_letter
                column_name = column[0].value

                # Calcular largura
                max_length = 0
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except Exception:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

                # Aplicar formato brasileiro dd/mm/yyyy nas colunas de data
                if column_name in colunas_data:
                    for cell in column[1:]:  # Pular cabeçalho
                        if cell.value:
                            cell.number_format = 'DD/MM/YYYY'

        output.seek(0)
        logger.info(f"✅ Excel gerado com sucesso! ({len(df)} registros)")

        return output.getvalue()

    def exportar_json(self, data_inicio: Optional[date] = None) -> List[Dict]:
        """
        Exporta relatório completo em JSON (para Power Query)

        Returns:
            Lista de dicionários
        """
        logger.info("📊 Iniciando exportação para JSON...")

        # 1. Extrair dados do Odoo
        dados = self.extrair_dados_odoo(data_inicio)

        # 2. Aplicar regras de negócio
        df = self.aplicar_regras_negocio(dados)

        # 3. Enriquecer com dados locais
        df = self.enriquecer_com_dados_locais(df)

        # 4. Renomear colunas
        df = self._renomear_colunas_excel(df)

        # 5. Remover colunas desnecessárias (IDs e campos técnicos do Odoo)
        colunas_remover = [
            'id',  # ID da linha (desnecessário)
            'company_id', 'partner_id', 'payment_provider_id',
            'company_id_id', 'partner_id_id', 'payment_provider_id_id',
            'account_type', 'move_type', 'parent_state'  # Campos técnicos usados apenas para filtro
        ]
        df = df.drop(columns=[col for col in colunas_remover if col in df.columns])

        # 6. Formatar datas para dd/mm/yyyy (formato brasileiro como string)
        colunas_data = [
            'Data',
            'Data de Vencimento',
            'Data Entrega Prevista',
            'Data/Hora Entrega Realizada',
            'Último Agendamento - Data'
        ]

        for col in colunas_data:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) and x is not None else None
                )

        # 7. Converter para JSON
        resultado = df.to_dict('records')

        logger.info(f"✅ JSON gerado com sucesso! ({len(resultado)} registros)")

        return resultado

    def _renomear_colunas_excel(self, df: pd.DataFrame) -> pd.DataFrame:
        """Renomeia colunas para nomes em português amigáveis"""
        mapeamento = {
            'company_id_nome': 'Empresa',
            'x_studio_tipo_de_documento_fiscal': 'Tipo de Documento Fiscal',
            'x_studio_nf_e': 'NF-e',
            'l10n_br_cobranca_parcela': 'Parcela',
            'l10n_br_paga': 'Parcela Paga?',
            'partner_id_nome': 'Parceiro/Razão Social',
            'partner_cnpj': 'Parceiro/CNPJ',
            'partner_raz_social_red': 'Parceiro/Nome Fantasia',
            'partner_state': 'Parceiro/Estado',
            'date': 'Data',
            'date_maturity': 'Data de Vencimento',
            'saldo_total': 'Saldo Total',
            'desconto_concedido': 'Desconto Concedido',
            'desconto_concedido_percentual': 'Desconto Concedido (%)',
            'payment_provider_id_nome': 'Forma de Pagamento',
            'x_studio_status_de_pagamento': 'Status de Pagamento',
            'amount_residual': 'Valor Residual',
            'data_entrega_prevista': 'Data Entrega Prevista',
            'data_hora_entrega_realizada': 'Data/Hora Entrega Realizada',
            'entregue': 'Entregue',
            'ultimo_agendamento_data': 'Último Agendamento - Data',
            'ultimo_agendamento_status': 'Último Agendamento - Status'
        }

        return df.rename(columns=mapeamento)
