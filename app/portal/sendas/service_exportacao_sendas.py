"""
Service para exportação de planilha para Portal Sendas
Etapa 3 do processo semi-automatizado
"""

from app import db
from app.portal.sendas.models_planilha import PlanilhaModeloSendas
from app.portal.models_fila_sendas import FilaAgendamentoSendas
from app.portal.sendas.models import FilialDeParaSendas
from app.producao.models import CadastroPalletizacao
from datetime import datetime
import pandas as pd
import io
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class ExportacaoSendasService:
    """
    Service para exportar planilha adequada combinando:
    - Dados da planilha modelo (colunas 2-16)
    - Dados da FilaAgendamentoSendas (colunas editáveis)
    """

    # Configuração de veículos conforme especificação
    CAMINHOES = [
        ('Utilitário', 800),
        ('Caminhão VUC 3/4', 2000),
        ('Caminhão 3/4 (2 eixos) 16T', 4000),
        ('Caminhão Truck (6x2) 23T', 8000),
        ('Carreta Simples Toco (3 eixos) 25T', 25000),
        ('Caminhão (4 eixos) 31T', float('inf'))  # Acima de 25000
    ]

    def calcular_veiculo(self, peso_total_kg: float) -> str:
        """
        Calcula o veículo adequado baseado no peso total

        Args:
            peso_total_kg: Peso total em kg

        Returns:
            Nome do veículo adequado
        """
        for nome_veiculo, peso_maximo in self.CAMINHOES:
            if peso_total_kg <= peso_maximo:
                return nome_veiculo

        # Se não encontrar, retorna o maior
        return 'Caminhão (4 eixos) 31T'

    def calcular_peso_produto(self, cod_produto: str, quantidade: float) -> float:
        """
        Calcula o peso total de um produto usando CadastroPalletizacao

        Args:
            cod_produto: Código do produto
            quantidade: Quantidade do produto

        Returns:
            Peso total em kg (quantidade * peso_bruto)
        """
        cadastro = CadastroPalletizacao.query.filter_by(
            cod_produto=cod_produto,
            ativo=True
        ).first()

        if cadastro and cadastro.peso_bruto:
            return float(quantidade) * float(cadastro.peso_bruto)

        # Se não encontrar cadastro, retornar 0 (será somado ao total mas não afetará)
        logger.warning(f"Produto {cod_produto} não encontrado em CadastroPalletizacao")
        return 0

    def exportar_planilha(self, protocolo: str = None) -> Tuple[bool, str, bytes]:
        """
        Exporta planilha para um protocolo específico OU para TODOS os protocolos pendentes

        Args:
            protocolo: Protocolo do agendamento (AG_XXXX_DDMMYY_HHMM) ou None para exportar todos

        Returns:
            Tuple (sucesso, mensagem, bytes_arquivo)
        """
        try:
            # ✅ CORREÇÃO PROBLEMA 4: Permitir exportação de todos os protocolos pendentes
            if protocolo:
                # Buscar apenas itens de um protocolo específico
                itens_fila = FilaAgendamentoSendas.query.filter_by(
                    protocolo=protocolo,
                    status='pendente'
                ).all()
            else:
                # Buscar TODOS os itens pendentes
                itens_fila = FilaAgendamentoSendas.query.filter_by(
                    status='pendente'
                ).order_by(
                    FilaAgendamentoSendas.protocolo,
                    FilaAgendamentoSendas.cnpj,
                    FilaAgendamentoSendas.data_agendamento
                ).all()

            if not itens_fila:
                return False, "Nenhum item pendente encontrado para exportação", None # type: ignore

            logger.info(f"Encontrados {len(itens_fila)} itens na fila para exportar")

            # ✅ CORREÇÃO: Agrupar por protocolo quando exportando múltiplos
            from collections import defaultdict
            itens_por_protocolo = defaultdict(list)

            for item in itens_fila:
                itens_por_protocolo[item.protocolo].append(item)

            # 3. Processar cada protocolo
            linhas_exportacao = []
            numero_demanda = 1  # Começa em 1 e incrementa POR PROTOCOLO

            for protocolo_atual, itens_protocolo in itens_por_protocolo.items():
                logger.info(f"Processando protocolo {protocolo_atual} com {len(itens_protocolo)} itens")

                # ✅ CORREÇÃO PROBLEMA 5: Calcular peso POR PROTOCOLO
                peso_total_protocolo = 0

                # Pegar CNPJ e data do primeiro item do protocolo
                cnpj = itens_protocolo[0].cnpj
                data_agendamento = itens_protocolo[0].data_agendamento

                # 2. Converter CNPJ para filial Sendas
                filial_sendas = FilialDeParaSendas.cnpj_to_filial(cnpj)
                if not filial_sendas:
                    logger.error(f"CNPJ {cnpj} não encontrado no DE-PARA de filiais")
                    continue  # Pular este protocolo e continuar com os outros

                # ✅ VALIDAÇÃO ANTECIPADA: Verificar se a filial TEM dados na planilha modelo
                planilha_existe = PlanilhaModeloSendas.query.filter_by(
                    unidade_destino=filial_sendas
                ).first()

                if not planilha_existe:
                    logger.error(f"Filial {filial_sendas} não tem dados na planilha modelo")
                    return False, f"ERRO: Filial {filial_sendas} não tem dados cadastrados na planilha modelo Sendas. Por favor, solicite ao suporte o cadastro desta filial.", None # type: ignore

                # ✅ CORREÇÃO: Processar cada item DO PROTOCOLO ATUAL
                for item_fila in itens_protocolo:  # ✅ USAR itens_protocolo, não itens_fila!
                    # FilaAgendamentoSendas JÁ TEM os dados corretos da planilha
                    # Buscar item específico usando pedido_cliente e cod_produto da FILA
                    planilha_item_especifico = PlanilhaModeloSendas.query.filter_by(
                        unidade_destino=filial_sendas,
                        codigo_pedido_cliente=item_fila.pedido_cliente,  # Já está com valor completo
                        codigo_produto_cliente=item_fila.cod_produto     # Já está com código Sendas
                    ).first()

                    # Se encontrou o item específico, usar seus dados
                    if planilha_item_especifico:
                        planilha_item = planilha_item_especifico
                    else:
                        # Se não encontrar, pegar qualquer item da filial para dados padrão
                        planilha_item = PlanilhaModeloSendas.query.filter_by(
                            unidade_destino=filial_sendas
                        ).first()

                        if not planilha_item:
                            logger.error(f"ERRO CRÍTICO: Nenhum item encontrado para filial {filial_sendas}")
                            return False, f"ERRO: Filial {filial_sendas} não tem dados na planilha modelo", None # type: ignore

                    # ✅ Criar linha usando dados da FILA (que já tem valores da planilha)
                    linha = {
                        # Coluna 1 - Número sequencial POR AGENDAMENTO
                        'Demanda': numero_demanda,

                        # Colunas 2-16 - Da planilha modelo (preservar dados da filial)
                        'Razão Social - Fornecedor': planilha_item.razao_social_fornecedor,
                        'Nome Fantasia - Fornecedor': planilha_item.nome_fantasia_fornecedor,
                        'Unidade de destino': planilha_item.unidade_destino,
                        'UF Destino': planilha_item.uf_destino,
                        'Fluxo de operação': planilha_item.fluxo_operacao,
                        # ✅ USAR DIRETO DA FILA - JÁ TEM O VALOR CORRETO DA PLANILHA
                        'Código do pedido Cliente': item_fila.pedido_cliente,  # ✅ Já tem valor completo (PC123-001)
                        'Código Produto Cliente': item_fila.cod_produto,       # ✅ Já tem código Sendas
                        'Código Produto SKU Fornecedor': planilha_item_especifico.codigo_produto_sku_fornecedor if planilha_item_especifico and planilha_item_especifico.codigo_produto_sku_fornecedor and str(planilha_item_especifico.codigo_produto_sku_fornecedor).lower() != 'nan' else '',
                        'EAN': planilha_item_especifico.ean if planilha_item_especifico and planilha_item_especifico.ean and str(planilha_item_especifico.ean).lower() != 'nan' else '',
                        'Setor': planilha_item.setor if planilha_item.setor and str(planilha_item.setor).lower() != 'nan' else '',
                        # 'Número do pedido Trizy': planilha_item_especifico.numero_pedido_trizy if planilha_item_especifico and planilha_item_especifico.numero_pedido_trizy and str(planilha_item_especifico.numero_pedido_trizy).lower() != 'nan' else '',  # ⚠️ COMENTADO: Coluna não existe mais no layout do Sendas
                        'Descrição do Item': planilha_item_especifico.descricao_item if planilha_item_especifico and planilha_item_especifico.descricao_item and str(planilha_item_especifico.descricao_item).lower() != 'nan' else '',
                        'Quantidade total': float(planilha_item_especifico.quantidade_total or 0) if planilha_item_especifico and planilha_item_especifico.quantidade_total else 0,
                        'Saldo disponível': float(planilha_item_especifico.saldo_disponivel or 0) if planilha_item_especifico and planilha_item_especifico.saldo_disponivel else 0,
                        'Unidade de medida': planilha_item_especifico.unidade_medida if planilha_item_especifico and planilha_item_especifico.unidade_medida else 'UN',

                        # Colunas 17-24 - Editáveis (dados da FILA)
                        'Quantidade entrega': float(item_fila.quantidade),  # ✅ Quantidade da FILA
                        'Data sugerida de entrega': item_fila.data_agendamento,  # Será formatado no Excel
                        'ID de agendamento (opcional)': '',
                        'Reserva de Slot (opcional)': '',
                        'Característica da carga': 'Paletizada',
                        'Característica do veículo': '',  # Será calculado depois
                        'Transportadora CNPJ (opcional)': '',
                        'Observação/ Fornecedor (opcional)': protocolo_atual  # ✅ Usar protocolo_atual, não variável protocolo
                    }

                    linhas_exportacao.append(linha)

                    # Calcular peso usando CadastroPalletizacao
                    peso_item = self.calcular_peso_produto(
                        item_fila.cod_produto,
                        float(item_fila.quantidade)
                    )
                    peso_total_protocolo += peso_item

                # ✅ CORREÇÃO PROBLEMA 5: Calcular veículo POR PROTOCOLO
                veiculo_protocolo = self.calcular_veiculo(peso_total_protocolo)

                # Atualizar linhas DESTE PROTOCOLO com o veículo calculado
                # Pegar as linhas que acabamos de adicionar (últimas len(itens_protocolo))
                inicio_protocolo = len(linhas_exportacao) - len(itens_protocolo)
                for i in range(inicio_protocolo, len(linhas_exportacao)):
                    linhas_exportacao[i]['Característica do veículo'] = veiculo_protocolo

                # ✅ INCREMENTAR DEMANDA APENAS APÓS PROCESSAR TODOS OS ITENS DO PROTOCOLO
                numero_demanda += 1

            if not linhas_exportacao:
                return False, "Nenhuma linha encontrada na planilha modelo para exportar", None # type: ignore

            # 5. Criar DataFrame e exportar para Excel
            df = pd.DataFrame(linhas_exportacao)

            # Garantir ordem correta das colunas (1-24)
            colunas_ordenadas = [
                'Demanda',
                'Razão Social - Fornecedor',
                'Nome Fantasia - Fornecedor',
                'Unidade de destino',
                'UF Destino',
                'Fluxo de operação',
                'Código do pedido Cliente',
                'Código Produto Cliente',
                'Código Produto SKU Fornecedor',
                'EAN',
                'Setor',
                # 'Número do pedido Trizy',  # ⚠️ COMENTADO: Coluna não existe mais no layout do Sendas
                'Descrição do Item',
                'Quantidade total',
                'Saldo disponível',
                'Unidade de medida',
                'Quantidade entrega',
                'Data sugerida de entrega',
                'ID de agendamento (opcional)',
                'Reserva de Slot (opcional)',
                'Característica da carga',
                'Característica do veículo',
                'Transportadora CNPJ (opcional)',
                'Observação/ Fornecedor (opcional)'
            ]

            df = df[colunas_ordenadas]

            # ✅ CORREÇÃO: Manter como Date mas formatar célula no Excel
            df['Data sugerida de entrega'] = pd.to_datetime(df['Data sugerida de entrega']).dt.date

            # ✅ CORREÇÃO: Substituir TODOS os NaN por string vazia
            df = df.fillna('')

            # Exportar para bytes
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Agendamento')

                # Formatar coluna de data como DD/MM/YYYY
                worksheet = writer.sheets['Agendamento']

                # Encontrar índice da coluna 'Data sugerida de entrega' (coluna 18 = R)
                date_column_letter = 'R'  # Coluna 18
                for row in range(2, worksheet.max_row + 1):  # Começar da linha 2 (pular header)
                    cell = worksheet[f'{date_column_letter}{row}']
                    if cell.value:  # Se tem valor
                        cell.number_format = 'DD/MM/YYYY'  # Formato de data brasileiro

                # Ajustar largura das colunas
                for column in worksheet.columns:
                    max_length = 0
                    column = [cell for cell in column]
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except Exception as e:
                            logger.error(f"Erro ao ajustar largura da coluna: {e}")
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width

            output.seek(0)
            arquivo_bytes = output.read()

            # 6. Marcar TODOS os itens como processados
            for item_fila in itens_fila:
                item_fila.status = 'processado'  # ✅ Mudando para 'processado' após exportação
                item_fila.processado_em = datetime.now()  # Usar datetime.now() ao invés de utcnow()
            db.session.commit()

            # Mensagem detalhada sobre a exportação
            num_protocolos = len(itens_por_protocolo)
            mensagem = f"Planilha exportada com {len(linhas_exportacao)} linhas de {num_protocolos} protocolo(s)"
            logger.info(mensagem)

            return True, mensagem, arquivo_bytes

        except Exception as e:
            logger.error(f"Erro ao exportar planilha: {e}")
            db.session.rollback()
            return False, f"Erro ao exportar: {str(e)}", None # type: ignore

    def listar_exportacoes_disponiveis(self) -> List[Dict]:
        """
        Lista os agendamentos disponíveis para exportação
        Agrupados por protocolo (cada protocolo = 1 agendamento)

        Returns:
            Lista de dicts com informações dos agendamentos
        """
        from sqlalchemy import func

        # Buscar agendamentos pendentes agrupados por protocolo
        resultado = db.session.query(
            FilaAgendamentoSendas.protocolo,
            FilaAgendamentoSendas.cnpj,
            FilaAgendamentoSendas.data_agendamento,
            FilaAgendamentoSendas.tipo_origem,
            FilaAgendamentoSendas.documento_origem,
            func.count(FilaAgendamentoSendas.id).label('total_itens'),
            func.sum(FilaAgendamentoSendas.quantidade).label('quantidade_total')
        ).filter(
            FilaAgendamentoSendas.status == 'pendente'
        ).group_by(
            FilaAgendamentoSendas.protocolo,
            FilaAgendamentoSendas.cnpj,
            FilaAgendamentoSendas.data_agendamento,
            FilaAgendamentoSendas.tipo_origem,
            FilaAgendamentoSendas.documento_origem
        ).all()

        exportacoes = []
        for row in resultado:
            # Buscar nome da filial no DE-PARA
            filial = FilialDeParaSendas.cnpj_to_filial(row.cnpj)

            # Determinar descrição do tipo
            if row.tipo_origem == 'lote':
                tipo_desc = f"Lote (CNPJ: {row.documento_origem})"
            elif row.tipo_origem == 'separacao':
                tipo_desc = f"Separação ({row.documento_origem})"
            elif row.tipo_origem == 'nf':
                tipo_desc = f"NF ({row.documento_origem})"
            else:
                tipo_desc = row.tipo_origem

            exportacoes.append({
                'protocolo': row.protocolo,
                'cnpj': row.cnpj,
                'filial': filial or 'Filial não mapeada',
                'data_agendamento': row.data_agendamento.strftime('%d/%m/%Y'),
                'tipo_origem': tipo_desc,
                'total_itens': row.total_itens,
                'quantidade_total': float(row.quantidade_total or 0)
            })

        return exportacoes

    def reprocessar_exportacao(self, protocolo: str) -> bool:
        """
        Marca itens exportados como pendentes para reprocessamento

        Args:
            protocolo: Protocolo do agendamento

        Returns:
            True se reprocessado com sucesso
        """
        try:
            itens = FilaAgendamentoSendas.query.filter_by(
                protocolo=protocolo,
                status='exportado'
            ).all()

            for item in itens:
                item.status = 'pendente'
                item.processado_em = None

            db.session.commit()
            logger.info(f"Reprocessados {len(itens)} itens do protocolo {protocolo}")
            return True

        except Exception as e:
            logger.error(f"Erro ao reprocessar: {e}")
            db.session.rollback()
            return False