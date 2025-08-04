"""
Serviço para atualizar notas fiscais em EmbarqueItem com erro de validação
através da busca em movimentações de estoque
"""
import re
from sqlalchemy import and_
from app import db
from app.estoque.models import MovimentacaoEstoque
from app.embarques.models import EmbarqueItem, Embarque
import logging

logger = logging.getLogger(__name__)


def atualizar_nf_embarque_items_com_erro():
    """
    Atualiza o campo nota_fiscal dos EmbarqueItem que possuem erro_validacao
    através da busca do separacao_lote_id nas observações das movimentações de estoque
    
    Returns:
        dict: Relatório com quantidade de itens atualizados e erros
    """
    relatorio = {
        'total_itens_erro': 0,
        'total_atualizados': 0,
        'total_erros': 0,
        'itens_atualizados': [],
        'erros': []
    }
    
    try:
        # Buscar todos os EmbarqueItem com erro_validacao e status ATIVO
        # Incluindo o join com Embarque para verificar também o status do embarque
        from app.embarques.models import Embarque
        
        embarque_items_erro = db.session.query(EmbarqueItem).join(
            Embarque, EmbarqueItem.embarque_id == Embarque.id
        ).filter(
            and_(
                EmbarqueItem.erro_validacao.isnot(None),
                EmbarqueItem.status == 'ativo',
                Embarque.status == 'ativo'
            )
        ).all()
        
        relatorio['total_itens_erro'] = len(embarque_items_erro)
        logger.info(f"Encontrados {len(embarque_items_erro)} EmbarqueItem com erro_validacao")
        
        for item in embarque_items_erro:
            try:
                # Buscar movimentação de estoque com o lote_id na observação
                # Padrão esperado: "Baixa automática NF {numero_nf} - lote separação {lote_id}"
                pattern = f"lote separação {item.separacao_lote_id}"
                
                movimentacao = MovimentacaoEstoque.query.filter(
                    and_(
                        MovimentacaoEstoque.tipo_movimentacao == 'FATURAMENTO',
                        MovimentacaoEstoque.observacao.like(f'%{pattern}%')
                    )
                ).first()
                
                if movimentacao:
                    # Extrair número da NF da observação usando regex
                    match = re.search(r'NF\s+(\d+)', movimentacao.observacao)
                    
                    if match:
                        numero_nf = match.group(1)
                        
                        # Atualizar o EmbarqueItem
                        item.nota_fiscal = numero_nf
                        item.erro_validacao = None  # Limpar erro já que encontramos a NF
                        
                        relatorio['itens_atualizados'].append({
                            'embarque_item_id': item.id,
                            'separacao_lote_id': item.separacao_lote_id,
                            'nota_fiscal': numero_nf,
                            'num_pedido': item.pedido,
                        })
                        
                        relatorio['total_atualizados'] += 1
                        logger.info(f"Atualizado EmbarqueItem {item.id} com NF {numero_nf}")
                    else:
                        logger.warning(f"Não foi possível extrair NF da observação: {movimentacao.observacao}")
                        relatorio['erros'].append({
                            'embarque_item_id': item.id,
                            'erro': 'NF não encontrada no padrão da observação',
                            'observacao': movimentacao.observacao
                        })
                        relatorio['total_erros'] += 1
                else:
                    logger.warning(f"Movimentação não encontrada para lote {item.separacao_lote_id}")
                    relatorio['erros'].append({
                        'embarque_item_id': item.id,
                        'erro': f'Movimentação não encontrada para lote {item.separacao_lote_id}'
                    })
                    relatorio['total_erros'] += 1
                    
            except Exception as e:
                logger.error(f"Erro ao processar EmbarqueItem {item.id}: {str(e)}")
                relatorio['erros'].append({
                    'embarque_item_id': item.id,
                    'erro': str(e)
                })
                relatorio['total_erros'] += 1
                
        # Commit das alterações
        if relatorio['total_atualizados'] > 0:
            db.session.commit()
            logger.info(f"Commit realizado: {relatorio['total_atualizados']} itens atualizados")
            
    except Exception as e:
        logger.error(f"Erro geral ao atualizar EmbarqueItems: {str(e)}")
        db.session.rollback()
        relatorio['erro_geral'] = str(e)
        
    return relatorio


def buscar_nf_por_lote(separacao_lote_id):
    """
    Busca número da NF para um lote específico nas movimentações de estoque
    
    Args:
        separacao_lote_id: ID do lote de separação
        
    Returns:
        str: Número da NF ou None se não encontrada
    """
    try:
        pattern = f"lote separação {separacao_lote_id}"
        
        movimentacao = MovimentacaoEstoque.query.filter(
            and_(
                MovimentacaoEstoque.tipo_movimentacao == 'FATURAMENTO',
                MovimentacaoEstoque.observacao.like(f'%{pattern}%')
            )
        ).first()
        
        if movimentacao:
            # Extrair número da NF usando regex
            match = re.search(r'NF\s+(\d+)', movimentacao.observacao)
            if match:
                return match.group(1)
                
    except Exception as e:
        logger.error(f"Erro ao buscar NF para lote {separacao_lote_id}: {str(e)}")
        
    return None


def atualizar_nf_embarque_item_especifico(embarque_item_id):
    """
    Atualiza a NF de um EmbarqueItem específico
    
    Args:
        embarque_item_id: ID do EmbarqueItem
        
    Returns:
        dict: Status da atualização
    """
    try:
        from app.embarques.models import Embarque
        
        item = EmbarqueItem.query.get(embarque_item_id)
        
        if not item:
            return {'sucesso': False, 'erro': 'EmbarqueItem não encontrado'}
            
        if not item.erro_validacao:
            return {'sucesso': False, 'erro': 'EmbarqueItem não possui erro_validacao'}
            
        # Verificar se o item e o embarque estão ativos
        if item.status != 'ativo':
            return {'sucesso': False, 'erro': 'EmbarqueItem não está ativo'}
            
        embarque = Embarque.query.get(item.embarque_id)
        if not embarque or embarque.status != 'ativo':
            return {'sucesso': False, 'erro': 'Embarque não está ativo'}
            
        numero_nf = buscar_nf_por_lote(item.separacao_lote_id)
        
        if numero_nf:
            item.nota_fiscal = numero_nf
            item.erro_validacao = None
            db.session.commit()
            
            return {
                'sucesso': True,
                'nota_fiscal': numero_nf,
                'separacao_lote_id': item.separacao_lote_id
            }
        else:
            return {
                'sucesso': False,
                'erro': f'NF não encontrada para lote {item.separacao_lote_id}'
            }
            
    except Exception as e:
        logger.error(f"Erro ao atualizar EmbarqueItem {embarque_item_id}: {str(e)}")
        db.session.rollback()
        return {'sucesso': False, 'erro': str(e)}


def buscar_preview_nf_pendentes():
    """
    Busca preview dos EmbarqueItems com erro_validacao mostrando a NF que será atualizada
    
    Returns:
        list: Lista de dicionários com informações para preview
    """
    preview_items = []
    
    try:
        # Buscar todos os EmbarqueItem com erro_validacao e status ativo
        embarque_items_erro = db.session.query(EmbarqueItem).join(
            Embarque, EmbarqueItem.embarque_id == Embarque.id
        ).filter(
            and_(
                EmbarqueItem.erro_validacao.isnot(None),
                EmbarqueItem.status == 'ativo',
                Embarque.status == 'ativo'
            )
        ).all()
        
        for item in embarque_items_erro:
            # Buscar a NF que seria atualizada
            numero_nf = buscar_nf_por_lote(item.separacao_lote_id)
            
            preview_items.append({
                'embarque_item_id': item.id,
                'embarque_id': item.embarque_id,
                'separacao_lote_id': item.separacao_lote_id,
                'num_pedido': item.pedido,
                'cliente': item.cliente,
                'erro_atual': item.erro_validacao,
                'nota_fiscal_atual': item.nota_fiscal,
                'nota_fiscal_sugerida': numero_nf,
                'encontrou_nf': numero_nf is not None,
                'embarque': {
                    'id': item.embarque.id,
                    'data_embarque': item.embarque.data_embarque.isoformat() if item.embarque.data_embarque else None,
                    'transportadora': item.embarque.transportadora.nome if hasattr(item.embarque.transportadora, 'nome') else str(item.embarque.transportadora)
                }
            })
            
    except Exception as e:
        logger.error(f"Erro ao buscar preview de NFs pendentes: {str(e)}")
        
    return preview_items


def atualizar_nf_embarque_items_selecionados(item_ids):
    """
    Atualiza apenas os EmbarqueItems selecionados
    
    Args:
        item_ids: Lista de IDs dos EmbarqueItems a serem atualizados
        
    Returns:
        dict: Relatório da atualização
    """
    relatorio = {
        'total_selecionados': len(item_ids),
        'total_atualizados': 0,
        'total_erros': 0,
        'itens_atualizados': [],
        'erros': []
    }
    
    try:
        for item_id in item_ids:
            resultado = atualizar_nf_embarque_item_especifico(item_id)
            
            if resultado['sucesso']:
                relatorio['total_atualizados'] += 1
                relatorio['itens_atualizados'].append({
                    'embarque_item_id': item_id,
                    'nota_fiscal': resultado['nota_fiscal']
                })
            else:
                relatorio['total_erros'] += 1
                relatorio['erros'].append({
                    'embarque_item_id': item_id,
                    'erro': resultado['erro']
                })
                
    except Exception as e:
        logger.error(f"Erro ao atualizar items selecionados: {str(e)}")
        relatorio['erro_geral'] = str(e)
        
    return relatorio


if __name__ == "__main__":
    # Teste direto da função
    from app import create_app
    app = create_app()
    
    with app.app_context():
        resultado = atualizar_nf_embarque_items_com_erro()
        print("\n=== RELATÓRIO DE ATUALIZAÇÃO ===")
        print(f"Total itens com erro: {resultado['total_itens_erro']}")
        print(f"Total atualizados: {resultado['total_atualizados']}")
        print(f"Total erros: {resultado['total_erros']}")
        
        if resultado['itens_atualizados']:
            print("\n--- Itens Atualizados ---")
            for item in resultado['itens_atualizados']:
                print(f"  Lote: {item['separacao_lote_id']} -> NF: {item['nota_fiscal']}")
                
        if resultado['erros']:
            print("\n--- Erros ---")
            for erro in resultado['erros']:
                print(f"  Item {erro['embarque_item_id']}: {erro['erro']}")