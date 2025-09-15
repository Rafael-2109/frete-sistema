"""
Rotas para gerenciar a fila de agendamentos Sendas (REFATORADO)
Versão limpa e otimizada com lógica correta
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.portal.models_fila_sendas import FilaAgendamentoSendas
from app.carteira.models import CarteiraPrincipal
from app.producao.models import CadastroPalletizacao
from app.separacao.models import Separacao
from app.monitoramento.models import EntregaMonitorada
from app.faturamento.models import FaturamentoProduto
from app.portal.sendas.utils_protocolo import gerar_protocolo_sendas
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

fila_sendas_bp = Blueprint('fila_sendas', __name__, url_prefix='/portal/sendas/fila')


def calcular_data_expedicao_sp(data_agendamento):
    """
    Calcula D-1 útil para SP considerando fins de semana
    """
    if isinstance(data_agendamento, str):
        data_agendamento = datetime.strptime(data_agendamento, '%Y-%m-%d').date()

    # Calcular D-1
    data_exp = data_agendamento - timedelta(days=1)

    # Se cair no domingo, volta para sexta
    if data_exp.weekday() == 6:  # Domingo
        data_exp = data_exp - timedelta(days=2)
    # Se cair no sábado, volta para sexta
    elif data_exp.weekday() == 5:  # Sábado
        data_exp = data_exp - timedelta(days=1)

    return data_exp


def buscar_pedido_cliente_com_fallback(num_pedido):
    """
    Busca pedido_cliente com fallback para Odoo
    Retorna None se não encontrar
    """
    if not num_pedido:
        return None

    try:
        # Primeiro tentar na Separacao
        separacao = Separacao.query.filter_by(num_pedido=num_pedido).first()
        if separacao and separacao.pedido_cliente:
            logger.info(f"pedido_cliente encontrado na Separacao: {separacao.pedido_cliente}")
            return separacao.pedido_cliente

        # Fallback: buscar no Odoo
        logger.info(f"Buscando pedido_cliente no Odoo para pedido {num_pedido}")
        from app.odoo.utils.pedido_cliente_utils import buscar_pedido_cliente_odoo
        pedido_cliente = buscar_pedido_cliente_odoo(num_pedido)

        if pedido_cliente:
            logger.info(f"✅ pedido_cliente encontrado no Odoo: {pedido_cliente}")
            # Atualizar a Separacao para futuras consultas
            if separacao:
                separacao.pedido_cliente = pedido_cliente
                db.session.commit()
                logger.info(f"✅ Separacao atualizada com pedido_cliente do Odoo")
        else:
            logger.warning(f"pedido_cliente não encontrado no Odoo para pedido {num_pedido}")

        return pedido_cliente

    except Exception as e:
        logger.error(f"Erro ao buscar pedido_cliente: {e}")
        return None


@fila_sendas_bp.route('/adicionar', methods=['POST'])
@login_required
def adicionar_na_fila():
    """
    Adiciona item na fila de agendamento Sendas

    Aceita origem de:
    - Separação (carteira agrupada)
    - NF (listar_entregas)
    """
    try:
        data = request.get_json()

        tipo_origem = data.get('tipo_origem')  # 'separacao' ou 'nf'
        documento_origem = data.get('documento_origem')  # lote_id ou numero_nf
        data_expedicao = data.get('data_expedicao')
        data_agendamento = data.get('data_agendamento')

        if not all([tipo_origem, documento_origem, data_agendamento]):
            return jsonify({
                'success': False,
                'message': 'Dados obrigatórios faltando'
            }), 400

        # Converter datas se vierem como string
        if isinstance(data_expedicao, str):
            data_expedicao = datetime.strptime(data_expedicao, '%Y-%m-%d').date()
        if isinstance(data_agendamento, str):
            data_agendamento = datetime.strptime(data_agendamento, '%Y-%m-%d').date()

        itens_adicionados = []

        # ============================================================
        # TIPO ORIGEM: SEPARAÇÃO
        # ============================================================
        if tipo_origem == 'separacao':
            # Buscar itens da separação
            itens_sep = Separacao.query.filter_by(
                separacao_lote_id=documento_origem,
                sincronizado_nf=False
            ).all()

            if not itens_sep:
                return jsonify({
                    'success': False,
                    'message': 'Separação não encontrada ou já sincronizada'
                }), 404

            # Buscar pedido_cliente UMA VEZ para o lote (assumindo mesmo pedido)
            pedido_cliente = None
            cnpj_lote = None
            if itens_sep:
                primeiro_item = itens_sep[0]
                cnpj_lote = primeiro_item.cnpj_cpf  # Capturar CNPJ para protocolo
                if primeiro_item.pedido_cliente:
                    pedido_cliente = primeiro_item.pedido_cliente
                elif primeiro_item.num_pedido:
                    pedido_cliente = buscar_pedido_cliente_com_fallback(primeiro_item.num_pedido)

            # GERAR PROTOCOLO ÚNICO PARA O LOTE (novo padrão)
            if cnpj_lote and data_agendamento:
                protocolo = gerar_protocolo_sendas(cnpj_lote, data_agendamento)

                # ATUALIZAR TODAS AS SEPARAÇÕES DO LOTE COM O PROTOCOLO
                # Importante: zerar datas para validação posterior
                logger.info(f"📝 Atualizando Separações do lote {documento_origem} com protocolo {protocolo}")
                resultado_update = Separacao.query.filter_by(
                    separacao_lote_id=documento_origem
                ).update({
                    'protocolo': protocolo,
                    'agendamento': None,  # Zerar para preencher apenas no retorno
                    'expedicao': None     # Zerar para validação
                })
                db.session.commit()
                logger.info(f"✅ {resultado_update} Separações atualizadas com protocolo")

            # Processar cada item da separação
            for item in itens_sep:
                # Nome do produto
                nome_produto = item.nome_produto
                if not nome_produto and item.cod_produto:
                    # Buscar na CadastroPalletizacao
                    palletizacao = CadastroPalletizacao.query.filter_by(
                        cod_produto=item.cod_produto
                    ).first()
                    if palletizacao:
                        nome_produto = palletizacao.nome_produto

                # UF vem direto da Separação
                uf_destino = item.cod_uf

                # Data de expedição: apenas para SP (D-1 útil)
                data_exp_final = data_expedicao or item.expedicao
                if uf_destino == 'SP' and not data_exp_final and data_agendamento:
                    data_exp_final = calcular_data_expedicao_sp(data_agendamento)

                # Adicionar na fila COM O PROTOCOLO JÁ GERADO
                fila_item = FilaAgendamentoSendas.adicionar(
                    tipo_origem='separacao',
                    documento_origem=documento_origem,
                    cnpj=item.cnpj_cpf,
                    num_pedido=item.num_pedido,
                    cod_produto=item.cod_produto,
                    nome_produto=nome_produto,
                    quantidade=float(item.qtd_saldo or 0),
                    data_expedicao=data_exp_final,
                    data_agendamento=data_agendamento,
                    pedido_cliente=pedido_cliente,  # Usar o pedido_cliente único
                    protocolo=protocolo  # Passar o protocolo já gerado
                )
                itens_adicionados.append(fila_item.id)

            logger.info(f"✅ {len(itens_adicionados)} itens de Separação adicionados à fila")

        # ============================================================
        # TIPO ORIGEM: NF
        # ============================================================
        elif tipo_origem == 'nf':
            # Buscar entrega monitorada (para validação)
            entrega = EntregaMonitorada.query.filter_by(
                numero_nf=documento_origem
            ).first()

            if not entrega:
                return jsonify({
                    'success': False,
                    'message': 'NF não encontrada no monitoramento'
                }), 404

            # FONTE PRIMÁRIA: FaturamentoProduto
            produtos_faturados = FaturamentoProduto.query.filter_by(
                numero_nf=documento_origem
            ).all()

            if produtos_faturados:
                # Buscar pedido_cliente UMA VEZ para a NF
                pedido_cliente = None
                num_pedido = None

                # Pegar o número do pedido do primeiro produto
                if produtos_faturados[0].origem:
                    num_pedido = produtos_faturados[0].origem
                    pedido_cliente = buscar_pedido_cliente_com_fallback(num_pedido)

                # GERAR PROTOCOLO ÚNICO PARA A NF INTEIRA
                cnpj_nf = produtos_faturados[0].cnpj_cliente or entrega.cnpj_cliente
                protocolo_nf = gerar_protocolo_sendas(cnpj_nf, data_agendamento)
                logger.info(f"📝 NF {documento_origem}: protocolo único {protocolo_nf}")

                # Processar produtos do FaturamentoProduto
                for produto in produtos_faturados:
                    # UF vem do FaturamentoProduto
                    uf_destino = produto.estado

                    # Data de expedição: apenas para SP (D-1 útil)
                    data_exp_final = data_expedicao
                    if uf_destino == 'SP' and not data_exp_final and data_agendamento:
                        data_exp_final = calcular_data_expedicao_sp(data_agendamento)

                    # Adicionar na fila COM PROTOCOLO ÚNICO DA NF
                    fila_item = FilaAgendamentoSendas.adicionar(
                        tipo_origem='nf',
                        documento_origem=documento_origem,
                        cnpj=produto.cnpj_cliente or entrega.cnpj_cliente,
                        num_pedido=produto.origem or '',
                        cod_produto=produto.cod_produto,
                        nome_produto=produto.nome_produto,
                        quantidade=float(produto.qtd_produto_faturado or 0),
                        data_expedicao=data_exp_final,
                        data_agendamento=data_agendamento,
                        pedido_cliente=pedido_cliente,  # Usar o pedido_cliente único
                        protocolo=protocolo_nf  # Protocolo único para toda a NF
                    )
                    itens_adicionados.append(fila_item.id)

                logger.info(f"✅ {len(itens_adicionados)} produtos de FaturamentoProduto adicionados à fila")

            else:
                # FALLBACK: Buscar na Separação
                logger.info(f"NF {documento_origem} não encontrada em FaturamentoProduto, tentando Separação")

                itens_sep = Separacao.query.filter_by(
                    numero_nf=documento_origem
                ).all()

                if not itens_sep:
                    return jsonify({
                        'success': False,
                        'message': f'Produtos da NF {documento_origem} não encontrados'
                    }), 404

                # Buscar pedido_cliente UMA VEZ
                pedido_cliente = None
                if itens_sep:
                    primeiro_item = itens_sep[0]
                    if primeiro_item.pedido_cliente:
                        pedido_cliente = primeiro_item.pedido_cliente
                    elif primeiro_item.num_pedido:
                        pedido_cliente = buscar_pedido_cliente_com_fallback(primeiro_item.num_pedido)

                # GERAR PROTOCOLO ÚNICO PARA A NF INTEIRA
                cnpj_nf = entrega.cnpj_cliente
                protocolo_nf = gerar_protocolo_sendas(cnpj_nf, data_agendamento)
                logger.info(f"📝 NF {documento_origem} (fallback): protocolo único {protocolo_nf}")

                # Processar itens da Separação
                for item in itens_sep:
                    # Nome do produto
                    nome_produto = None
                    if item.num_pedido and item.cod_produto:
                        carteira_item = CarteiraPrincipal.query.filter_by(
                            num_pedido=item.num_pedido,
                            cod_produto=item.cod_produto
                        ).first()
                        if carteira_item:
                            nome_produto = carteira_item.nome_produto

                    # UF vem da Separação
                    uf_destino = item.cod_uf

                    # Data de expedição: apenas para SP (D-1 útil)
                    data_exp_final = data_expedicao or item.expedicao
                    if uf_destino == 'SP' and not data_exp_final and data_agendamento:
                        data_exp_final = calcular_data_expedicao_sp(data_agendamento)

                    # Adicionar na fila COM PROTOCOLO ÚNICO DA NF
                    fila_item = FilaAgendamentoSendas.adicionar(
                        tipo_origem='nf',
                        documento_origem=documento_origem,
                        cnpj=entrega.cnpj_cliente,
                        num_pedido=item.num_pedido,
                        cod_produto=item.cod_produto,
                        nome_produto=nome_produto,
                        quantidade=float(item.qtd_saldo or 0),
                        data_expedicao=data_exp_final,
                        data_agendamento=data_agendamento,
                        pedido_cliente=pedido_cliente,  # Usar o pedido_cliente único
                        protocolo=protocolo_nf  # Protocolo único para toda a NF
                    )
                    itens_adicionados.append(fila_item.id)

                logger.info(f"✅ {len(itens_adicionados)} itens de Separação (fallback) adicionados à fila")

        else:
            return jsonify({
                'success': False,
                'message': 'Tipo de origem inválido'
            }), 400

        # Contar pendentes
        pendentes = FilaAgendamentoSendas.contar_pendentes()

        return jsonify({
            'success': True,
            'message': f'{len(itens_adicionados)} itens adicionados à fila',
            'itens_adicionados': len(itens_adicionados),
            'pendentes_total': sum(pendentes.values()),
            'pendentes_por_cnpj': pendentes
        })

    except Exception as e:
        logger.error(f"Erro ao adicionar na fila: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# Manter as outras rotas como estão (status, processar, limpar)
@fila_sendas_bp.route('/status', methods=['GET'])
@login_required
def status_fila():
    """
    Retorna status da fila de agendamentos
    """
    try:
        pendentes = FilaAgendamentoSendas.contar_pendentes()

        # Buscar detalhes se solicitado
        incluir_detalhes = request.args.get('detalhes', 'false').lower() == 'true'
        detalhes = []

        if incluir_detalhes:
            grupos = FilaAgendamentoSendas.obter_para_processar()
            for chave, grupo in grupos.items():
                detalhes.append({
                    'cnpj': grupo['cnpj'],
                    'data_agendamento': grupo['data_agendamento'].isoformat(),
                    'total_itens': len(grupo['itens']),
                    'protocolo': grupo['protocolo']
                })

        return jsonify({
            'success': True,
            'pendentes_total': sum(pendentes.values()),
            'pendentes_por_cnpj': pendentes,
            'detalhes': detalhes if incluir_detalhes else None
        })

    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@fila_sendas_bp.route('/processar', methods=['POST'])
@login_required
def processar_fila():
    """
    Processa a fila enviando para o worker de agendamento em lote
    """
    try:
        from app.portal.workers import enqueue_job
        from app.portal.workers.sendas_jobs import processar_agendamento_sendas
        from app.portal.models import PortalIntegracao
        from app.utils.lote_utils import gerar_lote_id

        grupos = FilaAgendamentoSendas.obter_para_processar()

        if not grupos:
            return jsonify({
                'success': True,
                'message': 'Nenhum item na fila para processar',
                'total_processado': 0
            })

        # CORREÇÃO: Enviar DADOS COMPLETOS da fila, não apenas CNPJ/data
        dados_para_processar = []
        cnpjs_processados = set()
        total_peso_geral = 0

        for chave, grupo in grupos.items():
            cnpj = grupo['cnpj']
            data_agendamento = grupo['data_agendamento']
            protocolo = grupo['protocolo']
            itens = grupo['itens']  # Lista de objetos FilaAgendamentoSendas com TODOS os dados!

            # Evitar duplicatas
            chave_unica = f"{cnpj}_{data_agendamento}"
            if chave_unica not in cnpjs_processados:
                # Converter itens da fila para dicionário com TODOS os dados necessários
                itens_dict = []
                peso_grupo = 0

                for item in itens:
                    # Calcular peso do item (necessário para tipo_caminhao)
                    peso_item = 0
                    if item.cod_produto:
                        pallet_info = CadastroPalletizacao.query.filter_by(
                            cod_produto=item.cod_produto
                        ).first()
                        if pallet_info and pallet_info.peso_bruto:
                            peso_item = float(item.quantidade) * float(pallet_info.peso_bruto)

                    peso_grupo += peso_item

                    itens_dict.append({
                        'id': item.id,
                        'num_pedido': item.num_pedido,
                        'pedido_cliente': item.pedido_cliente,  # CRÍTICO: Já tem o pedido_cliente do Odoo!
                        'cod_produto': item.cod_produto,  # CRÍTICO: Para DE-PARA com código Sendas
                        'nome_produto': item.nome_produto,
                        'quantidade': float(item.quantidade),  # CRÍTICO: Quantidade a agendar
                        'peso': peso_item,  # CRÍTICO: Para tipo_caminhao
                        'data_expedicao': item.data_expedicao.isoformat() if item.data_expedicao else None,
                        'tipo_origem': item.tipo_origem,
                        'documento_origem': item.documento_origem
                    })

                total_peso_geral += peso_grupo

                dados_para_processar.append({
                    'cnpj': cnpj,
                    'data_agendamento': data_agendamento.isoformat() if hasattr(data_agendamento, 'isoformat') else str(data_agendamento),
                    'protocolo': protocolo,  # Já tem o protocolo gerado!
                    'peso_total': peso_grupo,
                    'itens': itens_dict  # ENVIANDO TODOS OS DADOS DA FILA!
                })
                cnpjs_processados.add(chave_unica)

        # Criar registro de integração
        lote_id = gerar_lote_id()

        # Preparar dados para JSONB (com informações completas)
        lista_cnpjs_json = []
        for item in dados_para_processar:
            lista_cnpjs_json.append({
                'cnpj': item['cnpj'],
                'data_agendamento': item['data_agendamento'],
                'protocolo': item.get('protocolo'),
                'peso_total': item.get('peso_total'),
                'total_itens': len(item['itens'])
            })

        integracao = PortalIntegracao(
            portal='sendas',
            lote_id=lote_id,
            tipo_lote='agendamento_fila',
            status='aguardando',
            dados_enviados={
                'cnpjs': lista_cnpjs_json,
                'total': len(lista_cnpjs_json),
                'origem': 'fila_agendamento',
                'usuario': current_user.nome if current_user else 'Sistema'
            }
        )
        db.session.add(integracao)
        db.session.commit()

        # Enfileirar job no Redis Queue
        try:
            job = enqueue_job(
                processar_agendamento_sendas,
                integracao.id,
                dados_para_processar,  # ENVIANDO DADOS COMPLETOS DA FILA!
                current_user.nome if current_user else 'Sistema',
                queue_name='sendas',
                timeout='15m'
            )

            # Salvar job_id na integração
            integracao.job_id = job.id
            db.session.commit()

            # Marcar itens da fila como processados
            for chave, grupo in grupos.items():
                FilaAgendamentoSendas.marcar_processados(
                    grupo['cnpj'],
                    grupo['data_agendamento']
                )

            logger.info(f"✅ Fila processada - Job {job.id} criado com {len(dados_para_processar)} grupos")

            return jsonify({
                'success': True,
                'message': f'{len(dados_para_processar)} grupos enviados para processamento',
                'job_id': job.id,
                'total_processado': len(dados_para_processar)
            })

        except Exception as queue_error:
            logger.error(f"❌ Erro ao enfileirar job: {queue_error}")
            integracao.status = 'erro'
            integracao.resposta_portal = {'erro': str(queue_error)}
            db.session.commit()

            return jsonify({
                'success': False,
                'message': f'Erro ao processar fila: {str(queue_error)}',
                'total_processado': 0
            }), 500

    except Exception as e:
        logger.error(f"Erro ao processar fila: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@fila_sendas_bp.route('/limpar', methods=['POST'])
@login_required
def limpar_fila():
    """
    Limpa itens processados antigos
    """
    try:
        dias = request.get_json().get('dias', 7)
        FilaAgendamentoSendas.limpar_processados(dias)

        return jsonify({
            'success': True,
            'message': f'Itens processados há mais de {dias} dias removidos'
        })

    except Exception as e:
        logger.error(f"Erro ao limpar fila: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500