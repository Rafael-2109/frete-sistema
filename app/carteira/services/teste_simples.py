"""
Teste Simples das Melhorias - Sem Banco
======================================

Valida apenas a lógica do processador sem conectar ao banco
"""

import sys
import os

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

def testar_logica_score():
    """
    Testa a lógica de cálculo de score percentual
    """
    print("🧪 TESTE LÓGICA DE SCORE PERCENTUAL\n")
    
    # Simular dados de NF
    produtos_nf = [
        {'cod_produto': 'A001', 'qtd_produto_faturado': 100},
        {'cod_produto': 'B002', 'qtd_produto_faturado': 50},
        {'cod_produto': 'C003', 'qtd_produto_faturado': 25}
    ]
    
    # Simular separações
    separacoes_lote1 = [
        {'cod_produto': 'A001', 'qtd_saldo': 100},  # Match perfeito
        {'cod_produto': 'B002', 'qtd_saldo': 60},   # 83% match
        {'cod_produto': 'C003', 'qtd_saldo': 30}    # 83% match
    ]
    
    separacoes_lote2 = [
        {'cod_produto': 'A001', 'qtd_saldo': 80},   # 80% match
        {'cod_produto': 'B002', 'qtd_saldo': 50},   # Match perfeito
        {'cod_produto': 'D004', 'qtd_saldo': 20}    # Produto não está na NF
    ]
    
    def calcular_score_lote(produtos_nf, separacoes_lote):
        """Simula a lógica de cálculo de score"""
        score_lote = 0
        produtos_matched = 0
        divergencia = False
        
        for prod_nf in produtos_nf:
            # Buscar separação correspondente
            sep_correspondente = None
            for sep in separacoes_lote:
                if sep['cod_produto'] == prod_nf['cod_produto']:
                    sep_correspondente = sep
                    break
            
            if sep_correspondente:
                produtos_matched += 1
                
                # Calcular percentual
                if sep_correspondente['qtd_saldo'] > 0:
                    percentual = min(
                        prod_nf['qtd_produto_faturado'] / sep_correspondente['qtd_saldo'],
                        sep_correspondente['qtd_saldo'] / prod_nf['qtd_produto_faturado']
                    )
                    
                    if percentual >= 0.95:
                        score_lote += 1.0
                    elif percentual >= 0.80:
                        score_lote += 0.8
                        divergencia = True
                    elif percentual >= 0.50:
                        score_lote += 0.5
                        divergencia = True
                    else:
                        score_lote += 0.2
                        divergencia = True
        
        # Score final
        if len(produtos_nf) > 0:
            score_final = (score_lote / len(produtos_nf)) * (produtos_matched / len(produtos_nf))
        else:
            score_final = 0
        
        return score_final, divergencia, produtos_matched
    
    # Testar lote 1
    print("📊 Teste Lote 1:")
    print(f"Produtos NF: {produtos_nf}")
    print(f"Separações: {separacoes_lote1}")
    
    score1, div1, matched1 = calcular_score_lote(produtos_nf, separacoes_lote1)
    print(f"Score: {score1:.2f} ({score1*100:.1f}%)")
    print(f"Divergência: {div1}")
    print(f"Produtos matched: {matched1}/{len(produtos_nf)}")
    
    # Testar lote 2
    print("\n📊 Teste Lote 2:")
    print(f"Produtos NF: {produtos_nf}")
    print(f"Separações: {separacoes_lote2}")
    
    score2, div2, matched2 = calcular_score_lote(produtos_nf, separacoes_lote2)
    print(f"Score: {score2:.2f} ({score2*100:.1f}%)")
    print(f"Divergência: {div2}")
    print(f"Produtos matched: {matched2}/{len(produtos_nf)}")
    
    # Resultado
    print(f"\n🏆 RESULTADO:")
    if score1 > score2:
        print(f"Lote 1 venceu com {score1*100:.1f}% vs {score2*100:.1f}%")
    else:
        print(f"Lote 2 venceu com {score2*100:.1f}% vs {score1*100:.1f}%")

def testar_deteccao_status():
    """
    Testa a lógica de detecção de status cancelado
    """
    print("\n🧪 TESTE DETECÇÃO DE STATUS CANCELADO\n")
    
    # Simular dados
    nfs_com_movimentacao = {
        'NF001': 'FATURAMENTO',
        'NF002': 'FATURAMENTO',
        'NF003': 'FATURAMENTO'
    }
    
    produtos_status = [
        {'numero_nf': 'NF001', 'status_nf': 'Lançado'},
        {'numero_nf': 'NF002', 'status_nf': 'Cancelado'},  # Mudou para cancelado
        {'numero_nf': 'NF003', 'status_nf': 'Lançado'},
        {'numero_nf': 'NF004', 'status_nf': 'Lançado'}     # Nova NF
    ]
    
    nfs_pendentes = []
    
    for produto in produtos_status:
        numero_nf = produto['numero_nf']
        status = produto['status_nf']
        
        # 1. NF nova (não processada)
        if numero_nf not in nfs_com_movimentacao:
            nfs_pendentes.append(f"{numero_nf} - NOVA")
            continue
        
        # 2. Verificar se mudou para cancelado
        if status == 'Cancelado' and nfs_com_movimentacao.get(numero_nf) == 'FATURAMENTO':
            nfs_pendentes.append(f"{numero_nf} - CANCELADA (mudou status)")
    
    print("📋 NFs que precisam ser processadas:")
    for nf in nfs_pendentes:
        print(f"  - {nf}")

def testar_validacao_vinculacao():
    """
    Testa validação de NF já preenchida em embarque
    """
    print("\n🧪 TESTE VALIDAÇÃO DE VINCULAÇÃO\n")
    
    # Simular NF
    nf = {
        'numero_nf': 'NF123',
        'cnpj_cliente': '12.345.678/0001-90',
        'origem': 'PED456'
    }
    
    # Simular EmbarqueItem existente
    embarque_item = {
        'nota_fiscal': 'NF123',
        'embarque': {
            'cnpj_cliente': '12.345.678/0001-90',  # CNPJ bate
        },
        'num_pedido': 'PED456'  # Pedido bate
    }
    
    print(f"NF: {nf['numero_nf']}")
    print(f"CNPJ NF: {nf['cnpj_cliente']}")
    print(f"Pedido NF: {nf['origem']}")
    print(f"\nEmbarque existente:")
    print(f"CNPJ Embarque: {embarque_item['embarque']['cnpj_cliente']}")
    print(f"Pedido Embarque: {embarque_item['num_pedido']}")
    
    # Validar
    cnpj_bate = embarque_item['embarque']['cnpj_cliente'] == nf['cnpj_cliente']
    pedido_bate = embarque_item['num_pedido'] == nf['origem']
    
    if cnpj_bate and pedido_bate:
        print("\n✅ VINCULAÇÃO VÁLIDA - Processar Caso 1")
    else:
        print("\n❌ INCONSISTÊNCIA DETECTADA")
        print(f"   CNPJ bate: {cnpj_bate}")
        print(f"   Pedido bate: {pedido_bate}")

if __name__ == '__main__':
    testar_logica_score()
    testar_deteccao_status()
    testar_validacao_vinculacao()
    print("\n✅ Todos os testes lógicos concluídos!") 