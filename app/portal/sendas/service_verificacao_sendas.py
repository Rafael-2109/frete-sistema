"""
Service para verificação de agendamentos do Portal Sendas
Etapa 4 do processo semi-automatizado
Implementação rigorosa conforme especificação docs/NOVO_PROCESSO_SENDAS.md
"""

from app import db
from app.portal.models_fila_sendas import FilaAgendamentoSendas
from app.separacao.models import Separacao
from app.monitoramento.models import AgendamentoEntrega
from datetime import datetime, date, timedelta
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from io import BytesIO

logger = logging.getLogger(__name__)


class VerificacaoSendasService:
    """
    Service para verificar agendamentos através de planilha de retorno do Sendas

    Colunas esperadas na planilha:
    - ID: Protocolo real do Sendas
    - Status: Status do Agendamento (apenas para exibir)
    - Data Efetiva: Data do agendamento aprovado (DateTime -> extrair Date)
    - Obs. Criação: Nosso protocolo (AG_XXXX_DDMMYY_HHMM)
    - Data/Hora Sugerida: Data do agendamento solicitado (DateTime -> extrair Date)
    """

    def processar_planilha_verificacao(self, arquivo_excel: bytes) -> Dict:
        """
        Processa planilha de verificação do Portal Sendas

        Args:
            arquivo_excel: Bytes do arquivo Excel

        Returns:
            Dict com resultados do processamento
        """
        try:
            # Ler Excel
            df = pd.read_excel(BytesIO(arquivo_excel))
            logger.info(f"Planilha lida com {len(df)} linhas")

            # Verificar colunas obrigatórias
            colunas_obrigatorias = ['ID', 'Status', 'Obs. Criação']
            colunas_faltando = [col for col in colunas_obrigatorias if col not in df.columns]

            if colunas_faltando:
                return {
                    'sucesso': False,
                    'erro': f'Colunas obrigatórias faltando: {", ".join(colunas_faltando)}'
                }

            resultados = {
                'sucesso': True,
                'total_linhas': len(df),
                'encontrados': [],
                'nao_encontrados': [],
                'atualizados': [],
                'confirmados': [],
                'com_divergencia': [],
                'erros': []
            }

            # Processar cada linha
            for idx, row in df.iterrows():
                try:
                    resultado_linha = self._processar_linha_verificacao(row, idx + 2)

                    # Categorizar resultado
                    if resultado_linha['erro']:
                        resultados['erros'].append(resultado_linha)
                    elif not resultado_linha['encontrado']:
                        resultados['nao_encontrados'].append(resultado_linha)
                    elif resultado_linha['confirmado']:
                        resultados['confirmados'].append(resultado_linha)
                    elif resultado_linha['atualizado']:
                        resultados['atualizados'].append(resultado_linha)
                    elif resultado_linha['divergencia']:
                        resultados['com_divergencia'].append(resultado_linha)
                    else:
                        resultados['encontrados'].append(resultado_linha)

                except Exception as e:
                    logger.error(f"Erro ao processar linha {idx + 2}: {e}")
                    resultados['erros'].append({
                        'linha': idx + 2,
                        'erro': str(e)
                    })

            db.session.commit()
            return resultados

        except Exception as e:
            logger.error(f"Erro ao processar planilha: {e}")
            db.session.rollback()
            return {
                'sucesso': False,
                'erro': str(e)
            }

    def _processar_linha_verificacao(self, row: pd.Series, numero_linha: int) -> Dict:
        """
        Processa uma linha da planilha de verificação
        Implementa rigorosamente o fluxo A da especificação

        Returns:
            Dict com resultado do processamento da linha
        """
        # Extrair dados da linha
        id_sendas = str(row['ID']).strip() if pd.notna(row['ID']) else ''
        status_sendas = str(row['Status']).strip() if pd.notna(row['Status']) else ''
        obs_criacao = str(row['Obs. Criação']).strip() if pd.notna(row['Obs. Criação']) else ''
        data_efetiva = row.get('Data Efetiva')
        data_hora_sugerida = row.get('Data/Hora Sugerida:')  # Com dois pontos conforme spec

        resultado = {
            'linha': numero_linha,
            'id_sendas': id_sendas,
            'status_sendas': status_sendas,
            'protocolo_nosso': '',
            'encontrado': False,
            'atualizado': False,
            'confirmado': False,
            'divergencia': False,
            'erro': None,
            'mensagem': '',
            'tipo_origem': None,
            'documento_origem': None
        }

        # A - Procurar o "ID" através do protocolo
        protocolo_encontrado = None

        # Tentar encontrar pelo ID primeiro
        if id_sendas:
            # Buscar em FilaAgendamentoSendas onde protocolo = ID
            fila_item = FilaAgendamentoSendas.query.filter_by(protocolo=id_sendas).first()
            if fila_item:
                protocolo_encontrado = id_sendas
                resultado['protocolo_nosso'] = id_sendas
                resultado['tipo_origem'] = fila_item.tipo_origem
                resultado['documento_origem'] = fila_item.documento_origem

        # A.1 - Não encontrando, procurar o protocolo através de "Obs. Criação"
        if not protocolo_encontrado and obs_criacao:
            fila_item = FilaAgendamentoSendas.query.filter_by(protocolo=obs_criacao).first()
            if fila_item:
                protocolo_encontrado = obs_criacao
                resultado['protocolo_nosso'] = obs_criacao
                resultado['tipo_origem'] = fila_item.tipo_origem
                resultado['documento_origem'] = fila_item.documento_origem

                # A.1.1 - Encontrando em "Obs. Criação", gravar o ID no campo de protocolo
                if id_sendas and id_sendas != obs_criacao:
                    # Atualizar protocolo para o ID real do Sendas
                    self._atualizar_protocolo_real(obs_criacao, id_sendas, fila_item.tipo_origem)
                    resultado['atualizado'] = True
                    resultado['mensagem'] = f'Protocolo atualizado: {obs_criacao} → {id_sendas}'

        # A.1.2 - Não encontrando em "Obs. Criação"
        if not protocolo_encontrado:
            resultado['encontrado'] = False
            resultado['mensagem'] = 'Agendamento não encontrado no sistema'
            return resultado

        # Se chegou aqui, encontrou o protocolo
        resultado['encontrado'] = True

        # A.2 - Encontrando, deverá procurar em "Data Efetiva"
        if pd.notna(data_efetiva):
            # A.2.1 - Caso encontre Data Efetiva, gravar e confirmar agendamento
            try:
                data_agendamento = self._extrair_data(data_efetiva)

                # Atualizar baseado no tipo de origem
                if fila_item.tipo_origem in ['lote', 'separacao']:
                    # Fluxos 1 e 2 - Atualizar Separacao
                    self._confirmar_agendamento_separacao(
                        protocolo_encontrado,
                        data_agendamento,
                        fila_item.cnpj
                    )
                    resultado['confirmado'] = True
                    resultado['mensagem'] = f'Agendamento confirmado para {data_agendamento}'

                elif fila_item.tipo_origem == 'nf':
                    # Fluxo 3 - Atualizar AgendamentoEntrega
                    self._confirmar_agendamento_entrega(
                        protocolo_encontrado,
                        data_agendamento
                    )
                    resultado['confirmado'] = True
                    resultado['mensagem'] = f'Agendamento de NF confirmado para {data_agendamento}'

            except Exception as e:
                resultado['erro'] = f'Erro ao processar Data Efetiva: {e}'

        else:
            # A.2.2 - Caso não encontre Data Efetiva, verificar Data/Hora Sugerida
            if pd.notna(data_hora_sugerida):
                try:
                    data_sugerida = self._extrair_data(data_hora_sugerida)

                    # Comparar com data previamente registrada
                    divergencia = self._verificar_divergencia_data(
                        protocolo_encontrado,
                        data_sugerida,
                        fila_item.tipo_origem
                    )

                    if divergencia:
                        resultado['divergencia'] = True
                        resultado['mensagem'] = f'Data sugerida ({data_sugerida}) diverge da solicitada'
                    else:
                        resultado['mensagem'] = 'Agendamento pendente, aguardando confirmação'

                except Exception as e:
                    resultado['erro'] = f'Erro ao processar Data/Hora Sugerida: {e}'
            else:
                resultado['mensagem'] = 'Agendamento sem data de confirmação'

        return resultado

    def _extrair_data(self, valor_data) -> date:
        """
        Extrai Date de um DateTime, considerando diferentes formatos
        """
        if isinstance(valor_data, str):
            # Formato esperado: "DD/MM/YYYY HH:MM:SS" ou "DD/MM/YYYY"
            data_parte = valor_data.split()[0] if ' ' in valor_data else valor_data
            return datetime.strptime(data_parte, '%d/%m/%Y').date()
        else:
            # Se já for datetime do pandas
            return pd.to_datetime(valor_data).date()

    def _atualizar_protocolo_real(self, protocolo_nosso: str, id_sendas: str, tipo_origem: str):
        """
        Atualiza o protocolo para o ID real do Sendas em todos os lugares
        """
        # Atualizar em FilaAgendamentoSendas
        FilaAgendamentoSendas.query.filter_by(protocolo=protocolo_nosso).update({
            'protocolo': id_sendas
        })

        # Atualizar baseado no tipo de origem
        if tipo_origem in ['lote', 'separacao']:
            # Atualizar Separacao
            Separacao.query.filter_by(protocolo=protocolo_nosso).update({
                'protocolo': id_sendas
            })
        elif tipo_origem == 'nf':
            # Atualizar AgendamentoEntrega
            AgendamentoEntrega.query.filter_by(protocolo_agendamento=protocolo_nosso).update({
                'protocolo_agendamento': id_sendas
            })

        logger.info(f"Protocolo atualizado: {protocolo_nosso} → {id_sendas}")

    def _confirmar_agendamento_separacao(self, protocolo: str, data_agendamento: date, cnpj: str):
        """
        Confirma agendamento em Separacao (Fluxos 1 e 2)
        Implementa A.2.1 e A.2.1.1 da especificação
        """
        # Buscar todas as separações com este protocolo
        separacoes = Separacao.query.filter_by(protocolo=protocolo).all()

        for sep in separacoes:
            sep.agendamento = data_agendamento
            sep.agendamento_confirmado = True

            # A.2.1.1 - Para SP, calcular expedição = Data Efetiva - 1 dia útil
            if sep.cod_uf == 'SP':
                sep.expedicao = self._subtrair_dia_util(data_agendamento)
            # A.2.1.2 - Se não é SP, ignorar campo expedição

        logger.info(f"Confirmadas {len(separacoes)} separações com protocolo {protocolo}")

    def _confirmar_agendamento_entrega(self, protocolo: str, data_agendamento: date):
        """
        Confirma agendamento em AgendamentoEntrega (Fluxo 3)
        """
        agendamentos = AgendamentoEntrega.query.filter_by(
            protocolo_agendamento=protocolo
        ).all()

        for agend in agendamentos:
            agend.data_agendada = data_agendamento
            agend.status = 'confirmado'

        logger.info(f"Confirmados {len(agendamentos)} agendamentos de entrega com protocolo {protocolo}")

    def _verificar_divergencia_data(self, protocolo: str, data_sugerida: date, tipo_origem: str) -> bool:
        """
        Verifica se há divergência entre data sugerida e data solicitada
        """
        # Buscar data originalmente solicitada
        fila_item = FilaAgendamentoSendas.query.filter_by(protocolo=protocolo).first()

        if fila_item and fila_item.data_agendamento:
            return fila_item.data_agendamento != data_sugerida

        return False

    def _subtrair_dia_util(self, data: date) -> date:
        """
        Subtrai 1 dia útil da data (pula fim de semana)
        """
        data_anterior = data - timedelta(days=1)

        # Se cair no domingo, volta para sexta
        if data_anterior.weekday() == 6:  # Domingo
            data_anterior = data_anterior - timedelta(days=2)
        # Se cair no sábado, volta para sexta
        elif data_anterior.weekday() == 5:  # Sábado
            data_anterior = data_anterior - timedelta(days=1)

        return data_anterior

    def reenviar_nao_encontrados(self, protocolos: List[str]) -> Dict:
        """
        Marca agendamentos não encontrados para reprocessamento
        Implementa A.1.2.1 da especificação
        """
        try:
            contador = 0

            for protocolo in protocolos:
                # Alterar status de 'exportado' para 'pendente'
                resultado = FilaAgendamentoSendas.query.filter_by(
                    protocolo=protocolo,
                    status='exportado'
                ).update({
                    'status': 'pendente',
                    'processado_em': None
                })

                if resultado > 0:
                    contador += resultado
                    logger.info(f"Protocolo {protocolo} marcado para reprocessamento")

            db.session.commit()

            return {
                'sucesso': True,
                'total_reprocessados': contador,
                'mensagem': f'{contador} agendamentos marcados para reprocessamento'
            }

        except Exception as e:
            logger.error(f"Erro ao reenviar não encontrados: {e}")
            db.session.rollback()
            return {
                'sucesso': False,
                'erro': str(e)
            }

    def atualizar_datas_divergentes(self, atualizacoes: List[Dict]) -> Dict:
        """
        Atualiza datas quando há divergência e usuário confirma
        Implementa A.2.2.1 da especificação
        """
        try:
            contador = 0

            for item in atualizacoes:
                protocolo = item['protocolo']
                data_nova = item['data_nova']
                tipo_origem = item['tipo_origem']

                # Atualizar baseado no tipo
                if tipo_origem in ['lote', 'separacao']:
                    resultado = Separacao.query.filter_by(protocolo=protocolo).update({
                        'agendamento': data_nova
                    })
                elif tipo_origem == 'nf':
                    resultado = AgendamentoEntrega.query.filter_by(
                        protocolo_agendamento=protocolo
                    ).update({
                        'data_agendada': data_nova
                    })

                if resultado > 0:
                    contador += resultado
                    logger.info(f"Data atualizada para protocolo {protocolo}")

            db.session.commit()

            return {
                'sucesso': True,
                'total_atualizados': contador,
                'mensagem': f'{contador} datas atualizadas com sucesso'
            }

        except Exception as e:
            logger.error(f"Erro ao atualizar datas divergentes: {e}")
            db.session.rollback()
            return {
                'sucesso': False,
                'erro': str(e)
            }