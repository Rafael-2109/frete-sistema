"""
Rotas de agendamento para o Portal Tenda
Mantém a mesma estrutura de retorno do Atacadão para compatibilidade
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app import db
from app.portal.tenda.models import ProdutoDeParaEAN, LocalEntregaDeParaTenda, AgendamentoTenda
from app.portal.utils.grupo_empresarial import GrupoEmpresarial
from app.separacao.models import Separacao
from app.producao.models import CadastroPalletizacao
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('portal_tenda_agendamento', __name__, url_prefix='/tenda/agendamento')

@bp.route('/status')
@login_required
def status():
    """
    Página para visualizar e gerenciar status de agendamentos no Tenda
    """
    return render_template('portal/tenda/agendamento/status.html')

@bp.route('/preparar/<separacao_lote_id>')
@login_required
def preparar_agendamento(separacao_lote_id):
    """
    Prepara dados de agendamento baseado na Separação
    Converte códigos usando De-Para EAN e identifica local de entrega
    
    MANTÉM A MESMA ESTRUTURA DE RETORNO DO ATACADÃO
    """
    try:
        # Buscar itens da separação
        itens_separacao = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).all()
        
        if not itens_separacao:
            return jsonify({
                'success': False,
                'message': f'Nenhum item encontrado para o lote {separacao_lote_id}'
            }), 404
        
        # Verificar se é cliente Tenda
        primeiro_item = itens_separacao[0]
        if not GrupoEmpresarial.eh_cliente_tenda(primeiro_item.cnpj_cpf):
            return jsonify({
                'success': False,
                'message': 'Este lote não é de um cliente Tenda'
            }), 400
        
        # Buscar local de entrega pelo CNPJ
        local_entrega = LocalEntregaDeParaTenda.obter_local_entrega(primeiro_item.cnpj_cpf)
        if not local_entrega:
            return jsonify({
                'success': False,
                'message': f'Local de entrega não cadastrado para o CNPJ {primeiro_item.cnpj_cpf}'
            }), 400
        
        # Preparar dados para o formulário
        produtos_formulario = []
        produtos_sem_depara = []
        
        for item in itens_separacao:
            # Buscar conversão De-Para EAN
            ean = ProdutoDeParaEAN.obter_ean(
                item.cod_produto,
                item.cnpj_cpf
            )
            
            if ean:
                # Buscar descrição do EAN no De-Para
                depara = ProdutoDeParaEAN.query.filter_by(
                    codigo_nosso=item.cod_produto,
                    ean=ean,
                    ativo=True
                ).first()
                
                # Calcular quantidade convertida
                qtd_convertida = float(item.qtd_saldo or 0)
                if depara and depara.fator_conversao:
                    qtd_convertida = qtd_convertida * float(depara.fator_conversao)
                
                # Buscar palletização
                palletizacao = CadastroPalletizacao.query.filter_by(
                    cod_produto=item.cod_produto
                ).first()
                
                pallets = 0
                if palletizacao and palletizacao.palletizacao:
                    pallets = qtd_convertida / float(palletizacao.palletizacao)
                
                produtos_formulario.append({
                    'codigo_tenda': ean,  # Usando EAN para o portal
                    'descricao_tenda': depara.descricao_ean if depara else '',
                    'codigo_nosso': item.cod_produto,
                    'descricao_nosso': depara.descricao_nosso if depara else '',
                    'quantidade': qtd_convertida,
                    'pallets': round(pallets, 2),
                    'fator_conversao': float(depara.fator_conversao) if depara else 1.0
                })
            else:
                # Produto sem De-Para cadastrado
                produtos_sem_depara.append({
                    'codigo': item.cod_produto,
                    'quantidade': float(item.qtd_saldo or 0)
                })
        
        # Pegar data de agendamento do primeiro item
        data_agendamento = None
        if itens_separacao:
            data_agendamento = itens_separacao[0].agendamento
        
        return jsonify({
            'success': True,
            'lote_id': separacao_lote_id,
            'data_agendamento': data_agendamento.strftime('%d/%m/%Y') if data_agendamento else None,
            'produtos': produtos_formulario,
            'produtos_sem_depara': produtos_sem_depara,
            'total_itens': len(itens_separacao),
            'total_convertidos': len(produtos_formulario),
            # Informações específicas do Tenda
            'local_entrega': local_entrega,
            'cnpj_cliente': primeiro_item.cnpj_cpf,
            'cliente_nome': primeiro_item.raz_social_red
        })
        
    except Exception as e:
        logger.error(f"Erro ao preparar agendamento Tenda: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/gravar_protocolo', methods=['POST'])
@login_required
def gravar_protocolo():
    """
    Grava o protocolo de agendamento na Separação e cria registro no AgendamentoTenda
    Marca agendamento_confirmado como False (aguardando confirmação)
    
    MANTÉM A MESMA ESTRUTURA DE RETORNO DO ATACADÃO
    """
    try:
        data = request.get_json()
        separacao_lote_id = data.get('lote_id')
        protocolo = data.get('protocolo')
        
        # Campos adicionais do Tenda
        pdd_numero = data.get('pdd_numero')
        data_agendamento = data.get('data_agendamento')
        horario_agendamento = data.get('horario_agendamento')
        tipo_veiculo = data.get('tipo_veiculo')
        tipo_carga = data.get('tipo_carga')
        tipo_volume = data.get('tipo_volume')
        quantidade_volume = data.get('quantidade_volume')
        local_entrega_id = data.get('local_entrega_id')
        local_entrega_nome = data.get('local_entrega_nome')
        
        if not separacao_lote_id or not protocolo:
            return jsonify({
                'success': False,
                'message': 'Lote ID e protocolo são obrigatórios'
            }), 400
        
        # Buscar informações do primeiro item para pegar CNPJ
        primeiro_item = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).first()
        
        if not primeiro_item:
            return jsonify({
                'success': False,
                'message': 'Lote não encontrado'
            }), 404
        
        # Criar registro no AgendamentoTenda
        agendamento = AgendamentoTenda(
            separacao_lote_id=separacao_lote_id,
            protocolo=protocolo,
            pdd_numero=pdd_numero,
            data_agendamento=data_agendamento,
            horario_agendamento=horario_agendamento,
            cnpj_cliente=primeiro_item.cnpj_cpf,
            local_entrega_id=local_entrega_id,
            local_entrega_nome=local_entrega_nome,
            tipo_veiculo=tipo_veiculo,
            tipo_carga=tipo_carga,
            tipo_volume=tipo_volume,
            quantidade_volume=quantidade_volume,
            status='aguardando',
            confirmado=False
        )
        db.session.add(agendamento)
        
        # Atualizar todos os itens da separação (compatibilidade com Atacadão)
        itens_atualizados = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).update({
            'protocolo': protocolo,
            'agendamento_confirmado': False,  # Aguardando confirmação
        })
        
        db.session.commit()
        
        logger.info(f"Protocolo {protocolo} gravado para lote {separacao_lote_id} - {itens_atualizados} itens")
        
        return jsonify({
            'success': True,
            'message': f'Protocolo {protocolo} gravado com sucesso',
            'itens_atualizados': itens_atualizados
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao gravar protocolo Tenda: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/confirmar_agendamento', methods=['POST'])
@login_required
def confirmar_agendamento():
    """
    Confirma o agendamento após verificação manual
    Marca agendamento_confirmado como True
    
    MANTÉM A MESMA ESTRUTURA DE RETORNO DO ATACADÃO
    """
    try:
        data = request.get_json()
        separacao_lote_id = data.get('lote_id')
        
        if not separacao_lote_id:
            return jsonify({
                'success': False,
                'message': 'Lote ID é obrigatório'
            }), 400
        
        # Verificar se tem protocolo
        item_exemplo = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).first()
        
        if not item_exemplo or not item_exemplo.protocolo:
            return jsonify({
                'success': False,
                'message': 'Protocolo não encontrado. Realize o agendamento primeiro.'
            }), 400
        
        # Atualizar AgendamentoTenda
        agendamento = AgendamentoTenda.obter_por_lote(separacao_lote_id)
        if agendamento:
            agendamento.status = 'confirmado'
            agendamento.confirmado = True
        
        # Confirmar agendamento na Separação (compatibilidade)
        itens_confirmados = Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).update({
            'agendamento_confirmado': True,
        })
        
        db.session.commit()
        
        logger.info(f"Agendamento confirmado para lote {separacao_lote_id} - {itens_confirmados} itens")
        
        return jsonify({
            'success': True,
            'message': f'Agendamento confirmado com sucesso',
            'protocolo': item_exemplo.protocolo,
            'itens_confirmados': itens_confirmados
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao confirmar agendamento Tenda: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/verificar_depara/<separacao_lote_id>')
@login_required
def verificar_depara(separacao_lote_id):
    """
    Verifica quais produtos da separação têm De-Para EAN cadastrado
    
    MANTÉM A MESMA ESTRUTURA DE RETORNO DO ATACADÃO
    """
    try:
        # Buscar itens únicos da separação
        itens = db.session.query(
            Separacao.cod_produto,
            Separacao.cnpj_cpf
        ).filter_by(
            separacao_lote_id=separacao_lote_id
        ).distinct().all()
        
        produtos_com_depara = []
        produtos_sem_depara = []
        
        for item in itens:
            codigo = item.cod_produto
            cnpj = item.cnpj_cpf
            
            # Verificar se tem De-Para EAN
            ean = ProdutoDeParaEAN.obter_ean(codigo, cnpj)
            
            if ean:
                # Buscar informações completas do De-Para
                depara = ProdutoDeParaEAN.query.filter_by(
                    codigo_nosso=codigo,
                    ean=ean,
                    ativo=True
                ).first()
                
                produtos_com_depara.append({
                    'codigo_nosso': codigo,
                    'codigo_tenda': ean,  # EAN para o portal
                    'descricao_tenda': depara.descricao_ean if depara else ''
                })
            else:
                # Buscar descrição do produto
                produto = CadastroPalletizacao.query.filter_by(
                    cod_produto=codigo
                ).first()
                
                produtos_sem_depara.append({
                    'codigo': codigo,
                    'descricao': produto.nome_produto if produto else 'Produto não encontrado'
                })
        
        # Verificar local de entrega
        local_entrega = None
        if itens:
            local = LocalEntregaDeParaTenda.obter_local_entrega(itens[0].cnpj_cpf)
            if local:
                local_entrega = local
        
        return jsonify({
            'success': True,
            'lote_id': separacao_lote_id,
            'total_produtos': len(itens),
            'com_depara': len(produtos_com_depara),
            'sem_depara': len(produtos_sem_depara),
            'produtos_com_depara': produtos_com_depara,
            'produtos_sem_depara': produtos_sem_depara,
            'local_entrega': local_entrega,
            'local_entrega_cadastrado': local_entrega is not None
        })
        
    except Exception as e:
        logger.error(f"Erro ao verificar De-Para Tenda: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/buscar_pdd', methods=['POST'])
@login_required
def buscar_pdd():
    """
    Busca PDDs (Pedidos de Distribuição) disponíveis para agendamento
    Endpoint específico do Tenda
    """
    try:
        data = request.get_json()
        cnpj_cliente = data.get('cnpj_cliente')
        data_agendamento = data.get('data_agendamento')
        
        # Por enquanto, retornar dados mockados
        # Em produção, isso faria a busca real no portal Tenda
        pdds_disponiveis = [
            {
                'numero': 'PDD001',
                'data': data_agendamento,
                'itens': 10,
                'peso': 1500.0,
                'volume': 25
            }
        ]
        
        return jsonify({
            'success': True,
            'pdds': pdds_disponiveis
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar PDDs: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500