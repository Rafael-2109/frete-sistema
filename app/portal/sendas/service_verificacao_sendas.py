"""
Service para verificação de agendamentos do Portal Sendas
Etapa 4 do processo semi-automatizado
Implementação rigorosa conforme especificação docs/NOVO_PROCESSO_SENDAS.md
"""

from app import db
from app.portal.models_fila_sendas import FilaAgendamentoSendas
from datetime import datetime, date, timedelta
import pandas as pd
from typing import Dict, List
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
        LÓGICA CORRETA: Busca protocolos do SISTEMA e verifica na PLANILHA

        Args:
            arquivo_excel: Bytes do arquivo Excel

        Returns:
            Dict com resultados do processamento
        """
        try:
            # 1. Ler Excel e criar índice por protocolo
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

            # 2. Criar índice da planilha por protocolo (ID e Obs. Criação)
            planilha_por_protocolo = {}
            for idx, row in df.iterrows():
                id_sendas = str(row['ID']).strip() if pd.notna(row['ID']) else ''
                obs_criacao = str(row['Obs. Criação']).strip() if pd.notna(row['Obs. Criação']) else ''

                # Normalizar Obs. Criação: remover "- " do início que o portal Sendas adiciona
                obs_criacao_normalizado = obs_criacao.lstrip('- ').strip() if obs_criacao else ''

                # Indexar por ID
                if id_sendas and id_sendas != 'nan':
                    if id_sendas not in planilha_por_protocolo:
                        planilha_por_protocolo[id_sendas] = row

                # Indexar por Obs. Criação (normalizado, sem "- ")
                if obs_criacao_normalizado and obs_criacao_normalizado != 'nan':
                    if obs_criacao_normalizado not in planilha_por_protocolo:
                        planilha_por_protocolo[obs_criacao_normalizado] = row

            logger.info(f"Protocolos únicos na planilha: {len(planilha_por_protocolo)}")

            # 3. Buscar todos os protocolos NÃO confirmados do SISTEMA
            protocolos_sistema = self._buscar_protocolos_nao_confirmados()
            logger.info(f"Protocolos não confirmados no sistema: {len(protocolos_sistema)}")

            resultados = {
                'sucesso': True,
                'total_linhas': len(df),
                'total_protocolos_sistema': len(protocolos_sistema),
                'confirmados': [],
                'nao_encontrados': [],
                'com_divergencia': [],
                'atualizados': [],
                'erros': []
            }

            # 4. Para cada protocolo do SISTEMA, verificar na PLANILHA
            for protocolo_info in protocolos_sistema:
                try:
                    protocolo = protocolo_info['protocolo']
                    tipo_origem = protocolo_info['tipo_origem']
                    documento_origem = protocolo_info['documento_origem']

                    # Buscar protocolo na planilha
                    row_planilha = planilha_por_protocolo.get(protocolo)

                    if row_planilha is None:
                        # NÃO ENCONTRADO na planilha
                        # 🆕 FIX BUG 6a: Inclui CNPJ/cliente/cidade/UF nos resultados de nao encontrados
                        resultados['nao_encontrados'].append({
                            'protocolo_nosso': protocolo,
                            'tipo_origem': tipo_origem,
                            'documento_origem': documento_origem,
                            'cnpj': protocolo_info.get('cnpj'),
                            'cliente': protocolo_info.get('cliente'),
                            'raz_social': protocolo_info.get('raz_social') or protocolo_info.get('cliente'),
                            'nome_cidade': protocolo_info.get('nome_cidade'),
                            'cod_uf': protocolo_info.get('cod_uf'),
                            'mensagem': 'Protocolo não encontrado na planilha do Sendas'
                        })
                        continue

                    # Processar o protocolo encontrado
                    resultado = self._processar_protocolo_encontrado(
                        protocolo_info,
                        row_planilha
                    )

                    # Categorizar resultado
                    if resultado.get('confirmado'):
                        resultados['confirmados'].append(resultado)
                    elif resultado.get('divergencia'):
                        resultados['com_divergencia'].append(resultado)
                    elif resultado.get('atualizado'):
                        resultados['atualizados'].append(resultado)

                except Exception as e:
                    logger.error(f"Erro ao processar protocolo {protocolo}: {e}")
                    resultados['erros'].append({
                        'protocolo': protocolo,
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

    def _buscar_protocolos_nao_confirmados(self) -> List[Dict]:
        """
        Busca todos os protocolos não confirmados do SISTEMA
        Retorna lista com informações dos protocolos pendentes de confirmação

        🆕 FIX BUG 6a: Inclui raz_social, nome_cidade e cod_uf em todos os fluxos
            (necessario para exibir Razao Social/Cidade/UF/CNPJ na tabela de verificacao).
        🆕 FIX BUG 6b: status correto da FilaAgendamentoSendas eh 'processado'
            (era 'exportado', que nao existe — modelo so tem pendente/processado/erro).
        🆕 FIX BUG 6c: Filtrar EntregaMonitorada.entregue=False alem de
            status_finalizacao!='Entregue', e para Fluxo 2 (Separacao com numero_nf)
            tambem excluir separacoes cuja NF ja foi entregue.
        """
        protocolos = []

        # 1. Buscar em Separacao (protocolos não confirmados)
        # Como um protocolo pode ter múltiplos produtos, pegar o primeiro de cada protocolo
        from app.separacao.models import Separacao
        from app.monitoramento.models import AgendamentoEntrega, EntregaMonitorada
        from sqlalchemy import distinct

        # Buscar protocolos distintos primeiro
        # IMPORTANTE: Apenas sincronizado_nf=False (não faturados) devem ser verificados
        protocolos_distintos = db.session.query(
            distinct(Separacao.protocolo)
        ).filter(
            Separacao.protocolo.isnot(None),
            Separacao.protocolo != '',
            Separacao.agendamento_confirmado == False,
            Separacao.sincronizado_nf == False  # ✅ CRÍTICO: Apenas não faturados
        ).all()

        # 🆕 FIX BUG 6c: Pre-carregar set de NFs ja entregues para excluir do resultado
        nfs_entregues = set()
        try:
            entregues_rows = db.session.query(EntregaMonitorada.numero_nf).filter(
                db.or_(
                    EntregaMonitorada.entregue == True,
                    EntregaMonitorada.status_finalizacao == 'Entregue'
                )
            ).all()
            nfs_entregues = {row.numero_nf for row in entregues_rows if row.numero_nf}
        except Exception as e:
            logger.warning(f"Falha ao carregar NFs entregues: {e}")

        # Para cada protocolo, buscar os dados do primeiro registro
        for (protocolo_valor,) in protocolos_distintos:
            sep = Separacao.query.filter_by(
                protocolo=protocolo_valor,
                agendamento_confirmado=False,
                sincronizado_nf=False  # ✅ CRÍTICO: Apenas não faturados
            ).first()

            if sep:
                # 🆕 FIX BUG 6c: Se a Separacao tem NF associada e a NF ja foi entregue,
                # nao adicionar (nao precisa mais verificar agenda).
                if sep.numero_nf and sep.numero_nf in nfs_entregues:
                    continue

                protocolos.append({
                    'protocolo': sep.protocolo,
                    'tipo_origem': 'separacao',
                    'documento_origem': sep.separacao_lote_id,
                    'cnpj': sep.cnpj_cpf,
                    'cliente': sep.raz_social_red or sep.cnpj_cpf,
                    # 🆕 FIX BUG 6a: dados de endereco
                    'raz_social': sep.raz_social_red,
                    'nome_cidade': sep.nome_cidade,
                    'cod_uf': sep.cod_uf,
                    'data_agendamento': sep.agendamento,
                })

        # 2. Buscar em AgendamentoEntrega (status != 'confirmado')
        # ✅ FILTRO: Excluir NFs com status_finalizacao='Entregue' OU entregue=True
        agendamentos = db.session.query(
            AgendamentoEntrega.protocolo_agendamento,
            AgendamentoEntrega.entrega_id,
            AgendamentoEntrega.data_agendada,
            EntregaMonitorada.numero_nf,
            EntregaMonitorada.cnpj_cliente,
            EntregaMonitorada.cliente,
            EntregaMonitorada.municipio,
            EntregaMonitorada.uf
        ).join(
            EntregaMonitorada,
            EntregaMonitorada.id == AgendamentoEntrega.entrega_id
        ).filter(
            AgendamentoEntrega.protocolo_agendamento.isnot(None),
            AgendamentoEntrega.protocolo_agendamento != '',
            AgendamentoEntrega.status != 'confirmado',
            EntregaMonitorada.status_finalizacao != 'Entregue',  # ✅ EXCLUIR finalizadas
            EntregaMonitorada.entregue == False                  # 🆕 FIX BUG 6c
        ).all()

        for agend in agendamentos:
            protocolos.append({
                'protocolo': agend.protocolo_agendamento,
                'tipo_origem': 'nf',
                'documento_origem': agend.numero_nf,
                'entrega_id': agend.entrega_id,
                'cnpj': agend.cnpj_cliente,
                'cliente': agend.cliente or agend.cnpj_cliente,
                # 🆕 FIX BUG 6a: dados de endereco
                'raz_social': agend.cliente,
                'nome_cidade': agend.municipio,
                'cod_uf': agend.uf,
                'data_agendamento': agend.data_agendada,
            })

        # 3. Buscar em FilaAgendamentoSendas (status='processado')
        # 🆕 FIX BUG 6b: status correto e 'processado' (modelo so suporta pendente/processado/erro)
        # Como garantia adicional, caso não esteja nas tabelas acima
        fila_items = FilaAgendamentoSendas.query.filter(
            FilaAgendamentoSendas.status == 'processado'
        ).all()

        # Adicionar apenas se não estiver já na lista
        protocolos_existentes = {p['protocolo'] for p in protocolos}
        for fila in fila_items:
            if fila.protocolo not in protocolos_existentes:
                # Buscar cliente/cidade/uf baseado no tipo_origem
                cliente = None
                nome_cidade = None
                cod_uf = None
                if fila.tipo_origem in ['lote', 'separacao'] and fila.documento_origem:
                    # Tentar buscar dados da Separacao
                    sep_info = db.session.query(
                        Separacao.raz_social_red,
                        Separacao.nome_cidade,
                        Separacao.cod_uf
                    ).filter(
                        Separacao.separacao_lote_id == fila.documento_origem
                    ).first()
                    if sep_info:
                        cliente = sep_info.raz_social_red
                        nome_cidade = sep_info.nome_cidade
                        cod_uf = sep_info.cod_uf

                protocolos.append({
                    'protocolo': fila.protocolo,
                    'tipo_origem': fila.tipo_origem,
                    'documento_origem': fila.documento_origem,
                    'cnpj': fila.cnpj,
                    'cliente': cliente or fila.cnpj,
                    # 🆕 FIX BUG 6a: dados de endereco (podem ser None se nao encontrar)
                    'raz_social': cliente,
                    'nome_cidade': nome_cidade,
                    'cod_uf': cod_uf,
                    'data_agendamento': fila.data_agendamento,
                })

        logger.info(f"Total de protocolos não confirmados: {len(protocolos)}")
        return protocolos

    def _processar_protocolo_encontrado(self, protocolo_info: Dict, row_planilha: pd.Series) -> Dict:
        """
        Processa um protocolo encontrado na planilha

        Args:
            protocolo_info: Informações do protocolo do sistema
            row_planilha: Linha da planilha com dados do Sendas

        Returns:
            Dict com resultado do processamento
        """
        # Extrair dados da planilha
        id_sendas = str(row_planilha['ID']).strip() if pd.notna(row_planilha['ID']) else ''
        status_sendas = str(row_planilha['Status']).strip() if pd.notna(row_planilha['Status']) else ''
        obs_criacao = str(row_planilha['Obs. Criação']).strip() if pd.notna(row_planilha['Obs. Criação']) else ''
        # Normalizar Obs. Criação: remover "- " do início que o portal Sendas adiciona
        obs_criacao_normalizado = obs_criacao.lstrip('- ').strip() if obs_criacao else ''
        data_efetiva = row_planilha.get('Data Efetiva')
        data_hora_sugerida = row_planilha.get('Data/Hora Sugerida:')

        # Informações do protocolo do sistema
        protocolo = protocolo_info['protocolo']
        tipo_origem = protocolo_info['tipo_origem']
        documento_origem = protocolo_info['documento_origem']

        resultado = {
            'protocolo_nosso': protocolo,
            'id_sendas': id_sendas,
            'status_sendas': status_sendas,
            'tipo_origem': tipo_origem,
            'documento_origem': documento_origem,
            'cnpj': protocolo_info.get('cnpj'),
            'cliente': protocolo_info.get('cliente'),
            # 🆕 FIX BUG 6a: Propagar dados de endereco para a UI
            'raz_social': protocolo_info.get('raz_social') or protocolo_info.get('cliente'),
            'nome_cidade': protocolo_info.get('nome_cidade'),
            'cod_uf': protocolo_info.get('cod_uf'),
            'confirmado': False,
            'atualizado': False,
            'divergencia': False,
            'mensagem': ''
        }

        # A.1.1 - Se encontrou por Obs. Criação e tem ID diferente, atualizar protocolo
        if id_sendas and id_sendas != protocolo and obs_criacao_normalizado == protocolo:
            self._atualizar_protocolo_real(protocolo, id_sendas, tipo_origem)
            resultado['atualizado'] = True
            resultado['mensagem'] = f'Protocolo atualizado: {protocolo} → {id_sendas}'
            # Atualizar o protocolo para as próximas operações
            protocolo = id_sendas

        # A.2 - Verificar Data Efetiva
        if pd.notna(data_efetiva):
            # A.2.1 - Data Efetiva presente = agendamento confirmado
            try:
                data_agendamento = self._extrair_data(data_efetiva)

                # Confirmar baseado no tipo
                if tipo_origem in ['lote', 'separacao']:
                    self._confirmar_agendamento_separacao(
                        protocolo,
                        data_agendamento,
                        protocolo_info.get('cnpj'),
                        protocolo_info.get('cod_uf')
                    )
                elif tipo_origem == 'nf':
                    self._confirmar_agendamento_entrega(
                        protocolo,
                        data_agendamento,
                        protocolo_info.get('entrega_id')
                    )

                resultado['confirmado'] = True
                resultado['data_confirmada'] = data_agendamento.strftime('%d/%m/%Y')
                resultado['mensagem'] = f'Agendamento confirmado para {data_agendamento}'

            except Exception as e:
                resultado['erro'] = f'Erro ao processar Data Efetiva: {e}'

        else:
            # A.2.2 - Sem Data Efetiva, verificar divergência na Data/Hora Sugerida
            if pd.notna(data_hora_sugerida):
                try:
                    data_que_solicitamos = self._extrair_data(data_hora_sugerida)
                    data_registrada = protocolo_info.get('data_agendamento')

                    if data_registrada and data_que_solicitamos != data_registrada:
                        resultado['divergencia'] = True
                        resultado['data_sugerida'] = data_que_solicitamos.strftime('%d/%m/%Y')
                        resultado['data_solicitada'] = data_registrada.strftime('%d/%m/%Y') if data_registrada else None
                        resultado['mensagem'] = 'Data solicitada diverge da registrada no sistema'
                    else:
                        resultado['mensagem'] = 'Agendamento pendente, aguardando confirmação'

                except Exception as e:
                    resultado['erro'] = f'Erro ao processar Data/Hora Sugerida: {e}'
            else:
                resultado['mensagem'] = 'Agendamento sem data no retorno do Sendas'

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
        from app.separacao.models import Separacao
        from app.monitoramento.models import AgendamentoEntrega

        # Atualizar em FilaAgendamentoSendas
        FilaAgendamentoSendas.query.filter_by(protocolo=protocolo_nosso).update({
            'protocolo': id_sendas
        })

        # Atualizar baseado no tipo de origem
        if tipo_origem in ['lote', 'separacao']:
            # Atualizar Separacao (apenas não faturados)
            Separacao.query.filter_by(
                protocolo=protocolo_nosso,
                sincronizado_nf=False  # ✅ CRÍTICO: Apenas não faturados
            ).update({
                'protocolo': id_sendas
            })
        elif tipo_origem == 'nf':
            # Atualizar AgendamentoEntrega
            AgendamentoEntrega.query.filter_by(protocolo_agendamento=protocolo_nosso).update({
                'protocolo_agendamento': id_sendas
            })

        logger.info(f"Protocolo atualizado: {protocolo_nosso} → {id_sendas}")

    def _confirmar_agendamento_separacao(self, protocolo: str, data_agendamento: date, cnpj: str, cod_uf: str):
        """
        Confirma agendamento em Separacao (Fluxos 1 e 2)
        Implementa A.2.1 e A.2.1.1 da especificação
        """
        from app.separacao.models import Separacao

        # Buscar todas as separações NÃO FATURADAS com este protocolo
        # IMPORTANTE: Apenas atualizar sincronizado_nf=False
        separacoes = Separacao.query.filter_by(
            protocolo=protocolo,
            sincronizado_nf=False  # ✅ CRÍTICO: Apenas não faturados
        ).all()

        for sep in separacoes:
            sep.agendamento = data_agendamento
            sep.agendamento_confirmado = True

            # A.2.1.1 - Para SP, calcular expedição = Data Efetiva - 1 dia útil
            # Usar cod_uf do registro ou do parâmetro
            # ✅ EXCLUIR sub_rota 'D' (entregas diretas) do cálculo de expedição
            uf = sep.cod_uf or cod_uf
            if uf == 'SP' and sep.sub_rota != 'D':
                sep.expedicao = self._subtrair_dia_util(data_agendamento)
            # A.2.1.2 - Se não é SP, ignorar campo expedição

        logger.info(f"Confirmadas {len(separacoes)} separações com protocolo {protocolo}")

    def _confirmar_agendamento_entrega(self, protocolo: str, data_agendamento: date, entrega_id: int = None):
        """
        Confirma agendamento em AgendamentoEntrega (Fluxo 3)
        Atualiza também EntregaMonitorada.reagendar para False
        """
        from app.monitoramento.models import AgendamentoEntrega, EntregaMonitorada

        # Buscar agendamentos com este protocolo
        agendamentos = AgendamentoEntrega.query.filter_by(
            protocolo_agendamento=protocolo
        ).all()

        entregas_atualizadas = set()

        for agend in agendamentos:
            agend.data_agendada = data_agendamento
            agend.status = 'confirmado'
            entregas_atualizadas.add(agend.entrega_id)

        # Atualizar EntregaMonitorada.reagendar para False
        if entregas_atualizadas:
            for entrega_id in entregas_atualizadas:
                entrega = db.session.get(EntregaMonitorada,entrega_id) if entrega_id else None
                if entrega:
                    entrega.reagendar = False
                    # Também atualizar data_agenda se necessário
                    entrega.data_agenda = data_agendamento
                    logger.info(f"EntregaMonitorada {entrega_id} atualizada: reagendar=False, data_agenda={data_agendamento}")

        logger.info(f"Confirmados {len(agendamentos)} agendamentos de entrega com protocolo {protocolo}")


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
        🆕 FIX BUG 6b: status correto eh 'processado' (era 'exportado', que nao existe).
        """
        try:
            contador = 0

            for protocolo in protocolos:
                # Alterar status de 'processado' para 'pendente'
                resultado = FilaAgendamentoSendas.query.filter_by(
                    protocolo=protocolo,
                    status='processado'
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
        from app.separacao.models import Separacao
        from app.monitoramento.models import AgendamentoEntrega

        try:
            contador = 0

            for item in atualizacoes:
                protocolo = item['protocolo']
                data_nova = item['data_nova']
                tipo_origem = item['tipo_origem']

                # Atualizar baseado no tipo
                if tipo_origem in ['lote', 'separacao']:
                    # Atualizar apenas não faturados
                    resultado = Separacao.query.filter_by(
                        protocolo=protocolo,
                        sincronizado_nf=False  # ✅ CRÍTICO: Apenas não faturados
                    ).update({
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