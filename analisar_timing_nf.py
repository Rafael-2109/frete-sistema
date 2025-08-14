#!/usr/bin/env python3
"""
Script para verificar o preenchimento de NFs em EmbarqueItems
Identifica por que NFs não são processadas com lote na primeira sincronização
"""

import sys
from datetime import datetime, timedelta
from run import app
from app import db
from app.embarques.models import Embarque, EmbarqueItem
from app.estoque.models import MovimentacaoEstoque
from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
from sqlalchemy import or_

def analisar_problema_timing():
    """Analisa por que algumas NFs não geram MovimentacaoEstoque com lote na primeira vez"""
    
    with app.app_context():
        print("\n" + "="*80)
        print("ANÁLISE DO PROBLEMA DE TIMING NO PROCESSAMENTO DE NFs")
        print("="*80)
        
        # Buscar NFs recentes com movimentação "Sem Separação"
        movs_sem_lote = db.session.query(MovimentacaoEstoque).filter(
            MovimentacaoEstoque.observacao.like("%Sem Separação%"),
            MovimentacaoEstoque.observacao.like("%NF %")
        ).limit(20).all()
        
        print(f"\n📊 Analisando {len(movs_sem_lote)} movimentações 'Sem Separação' recentes")
        print("-"*60)
        
        problemas_encontrados = {
            'embarque_sem_nf': 0,
            'embarque_com_erro': 0,
            'embarque_inexistente': 0,
            'embarque_com_nf_diferente': 0,
            'embarque_cancelado': 0,
            'embarque_ok_mas_nao_processou': 0
        }
        
        for mov in movs_sem_lote[:10]:  # Analisar até 10 casos
            # Extrair número da NF da observação
            obs = mov.observacao
            if "NF " in obs:
                nf_numero = obs.split("NF ")[1].split(" ")[0].replace("-", "").strip()
                
                # Buscar a NF no RelatorioFaturamentoImportado
                nf = RelatorioFaturamentoImportado.query.filter_by(numero_nf=nf_numero).first()
                
                if not nf:
                    print(f"\n❌ NF {nf_numero} não encontrada no relatório")
                    continue
                
                print(f"\n📋 NF: {nf_numero}")
                print(f"   Pedido (origem): {nf.origem}")
                print(f"   Data Fatura: {nf.data_fatura}")
                
                # Verificar se existe EmbarqueItem para este pedido
                # Simular a busca que o ProcessadorFaturamento faria
                embarque_item = (
                    EmbarqueItem.query.join(Embarque, EmbarqueItem.embarque_id == Embarque.id)
                    .filter(
                        EmbarqueItem.pedido == nf.origem,
                        Embarque.status == "ativo",
                        EmbarqueItem.status == "ativo",
                        or_(
                            # NF vazia (ainda não preenchida)
                            EmbarqueItem.nota_fiscal.is_(None),
                            EmbarqueItem.nota_fiscal == '',
                            # Tem erro de validação para resolver
                            EmbarqueItem.erro_validacao.isnot(None)
                        )
                    )
                    .first()
                )
                
                if embarque_item:
                    print(f"   ✅ EmbarqueItem encontrado:")
                    print(f"      - ID: {embarque_item.id}")
                    print(f"      - Lote: {embarque_item.separacao_lote_id}")
                    print(f"      - NF atual: '{embarque_item.nota_fiscal}'")
                    print(f"      - Erro validação: {embarque_item.erro_validacao}")
                    
                    if embarque_item.nota_fiscal and embarque_item.nota_fiscal != nf_numero:
                        print(f"   ⚠️ PROBLEMA: EmbarqueItem já tem NF diferente!")
                        problemas_encontrados['embarque_com_nf_diferente'] += 1
                    elif embarque_item.erro_validacao:
                        print(f"   ⚠️ PROBLEMA: EmbarqueItem com erro de validação")
                        problemas_encontrados['embarque_com_erro'] += 1
                    elif not embarque_item.nota_fiscal:
                        print(f"   🔄 OK: EmbarqueItem sem NF - deveria ter sido processado!")
                        problemas_encontrados['embarque_ok_mas_nao_processou'] += 1
                    else:
                        print(f"   ✅ OK: EmbarqueItem já tem a NF correta")
                        problemas_encontrados['embarque_sem_nf'] += 1
                else:
                    # Buscar TODOS os EmbarqueItems deste pedido
                    todos_embarques = EmbarqueItem.query.filter_by(pedido=nf.origem).all()
                    
                    if todos_embarques:
                        print(f"   ⚠️ Encontrados {len(todos_embarques)} EmbarqueItems para o pedido:")
                        
                        for ei in todos_embarques:
                            embarque = Embarque.query.get(ei.embarque_id)
                            print(f"      - EmbarqueItem ID {ei.id}:")
                            print(f"        Status Embarque: {embarque.status if embarque else 'N/A'}")
                            print(f"        Status Item: {ei.status}")
                            print(f"        NF: '{ei.nota_fiscal}'")
                            print(f"        Erro: {ei.erro_validacao}")
                            
                            if embarque and embarque.status != "ativo":
                                problemas_encontrados['embarque_cancelado'] += 1
                            elif ei.nota_fiscal and ei.nota_fiscal != '' and not ei.erro_validacao:
                                # Tem NF e não tem erro - não precisa processar
                                print(f"        ℹ️ Não processa pois já tem NF e sem erro")
                    else:
                        print(f"   ❌ Nenhum EmbarqueItem encontrado para o pedido")
                        problemas_encontrados['embarque_inexistente'] += 1
        
        # Resumo dos problemas
        print("\n" + "="*60)
        print("RESUMO DOS PROBLEMAS ENCONTRADOS:")
        print("="*60)
        
        for problema, count in problemas_encontrados.items():
            if count > 0:
                print(f"  - {problema}: {count} casos")
        
        # Análise da lógica de busca
        print("\n" + "="*60)
        print("ANÁLISE DA LÓGICA DE BUSCA DE EMBARQUES:")
        print("="*60)
        
        print("\nO método _buscar_embarque_ativo_por_pedido processa APENAS se:")
        print("1. EmbarqueItem.pedido == nf.origem")
        print("2. Embarque.status == 'ativo'")
        print("3. EmbarqueItem.status == 'ativo'")
        print("4. E uma das condições:")
        print("   a) nota_fiscal é None ou vazia")
        print("   b) erro_validacao não é None")
        
        print("\n⚠️ PROBLEMA IDENTIFICADO:")
        print("Se o EmbarqueItem já tem uma NF preenchida E não tem erro,")
        print("ele NÃO será retornado pela busca, mesmo que a NF seja diferente!")
        print("\nIsso pode acontecer quando:")
        print("- Um EmbarqueItem foi preenchido com NF errada manualmente")
        print("- Houve mudança no pedido após o preenchimento")
        print("- A NF foi importada depois do EmbarqueItem ser criado")

if __name__ == "__main__":
    analisar_problema_timing()