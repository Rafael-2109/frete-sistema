#!/usr/bin/env python3
"""
Script Melhorado para Reconstruir Separações com Valores Corretos
==================================================================

Este script reconstrói Separações com valores corretos usando:
1. JOIN entre Pedido e Separacao via separacao_lote_id
2. Busca NF do Pedido e usa para buscar em FaturamentoProduto
3. Calcula peso usando CadastroPalletizacao
4. Calcula pallets usando palletização

Campos confirmados:
- Pedido: num_pedido, separacao_lote_id, nf, status
- Separacao: separacao_lote_id, cod_produto, qtd_saldo, valor_saldo, peso, pallet
- FaturamentoProduto: numero_nf, cod_produto, qtd_produto_faturado, valor_produto_faturado
- CadastroPalletizacao: cod_produto, peso_bruto, palletizacao
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from app.faturamento.models import FaturamentoProduto
from app.producao.models import CadastroPalletizacao
from app.embarques.models import EmbarqueItem
from datetime import datetime
import logging
from typing import Dict, List, Optional
from decimal import Decimal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReconstrutorSeparacoesValoresCorretos:
    """Reconstrói separações com valores corretos de FaturamentoProduto."""
    
    def __init__(self):
        self.app = create_app()
        self.stats = {
            'lotes_processados': 0,
            'lotes_atualizados': 0,
            'lotes_sem_nf': 0,
            'lotes_sem_faturamento': 0,
            'itens_atualizados': 0,
            'valores_zerados_corrigidos': 0,
            'pesos_calculados': 0,
            'pallets_calculados': 0
        }
    
    def executar(self, lotes_especificos=None, confirmar=False):
        """
        Executa a correção dos valores das separações.
        
        Args:
            lotes_especificos: Lista de lotes específicos para processar (None = todos)
            confirmar: Se True, salva as alterações no banco
        """
        with self.app.app_context():
            logger.info("="*70)
            logger.info("🔧 CORREÇÃO DE VALORES DAS SEPARAÇÕES")
            logger.info("="*70)
            
            # Buscar lotes para processar
            lotes = self._buscar_lotes_para_corrigir(lotes_especificos)
            
            if not lotes:
                logger.warning("⚠️ Nenhum lote encontrado para processar")
                return
            
            logger.info(f"📋 {len(lotes)} lotes encontrados para análise")
            
            # Processar cada lote
            for lote_data in lotes:
                self._processar_lote(lote_data)
            
            # Salvar se confirmado
            if confirmar and self.stats['lotes_atualizados'] > 0:
                logger.info("\n💾 Salvando alterações no banco...")
                db.session.commit()
                logger.info("✅ Alterações salvas com sucesso!")
            elif not confirmar:
                logger.warning("\n⚠️ MODO SIMULAÇÃO - Use --confirmar para salvar")
                db.session.rollback()
            
            # Exibir estatísticas
            self._exibir_estatisticas()
    
    def _buscar_lotes_para_corrigir(self, lotes_especificos=None):
        """
        Busca lotes que precisam de correção usando JOIN.
        """
        # Query com JOIN entre Pedido e Separacao
        query = db.session.query(
            Pedido.separacao_lote_id,
            Pedido.num_pedido,
            Pedido.nf,
            Pedido.status,
            db.func.count(Separacao.id).label('qtd_itens'),
            db.func.sum(Separacao.valor_saldo).label('valor_total'),
            db.func.sum(Separacao.peso).label('peso_total'),
            db.func.sum(Separacao.pallet).label('pallet_total')
        ).join(
            Separacao, 
            Pedido.separacao_lote_id == Separacao.separacao_lote_id
        ).group_by(
            Pedido.separacao_lote_id,
            Pedido.num_pedido,
            Pedido.nf,
            Pedido.status
        )
        
        # Filtrar por lotes específicos se fornecidos
        if lotes_especificos:
            query = query.filter(Pedido.separacao_lote_id.in_(lotes_especificos))
        
        # Filtrar apenas lotes com possíveis problemas (valores zerados ou nulos)
        query = query.having(
            db.or_(
                db.func.sum(Separacao.valor_saldo) == 0,
                db.func.sum(Separacao.valor_saldo).is_(None),
                db.func.sum(Separacao.peso) == 0,
                db.func.sum(Separacao.peso).is_(None),
                db.func.sum(Separacao.pallet) == 0,
                db.func.sum(Separacao.pallet).is_(None)
            )
        )
        
        lotes = query.all()
        
        # Converter para lista de dicionários
        resultado = []
        for lote in lotes:
            resultado.append({
                'separacao_lote_id': lote.separacao_lote_id,
                'num_pedido': lote.num_pedido,
                'nf': lote.nf,
                'status': lote.status,
                'qtd_itens': lote.qtd_itens,
                'valor_total': float(lote.valor_total) if lote.valor_total else 0,
                'peso_total': float(lote.peso_total) if lote.peso_total else 0,
                'pallet_total': float(lote.pallet_total) if lote.pallet_total else 0
            })
        
        return resultado
    
    def _processar_lote(self, lote_data: Dict):
        """
        Processa um lote corrigindo valores.
        """
        lote_id = lote_data['separacao_lote_id']
        num_pedido = lote_data['num_pedido']
        nf = lote_data['nf']
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📦 Processando lote: {lote_id}")
        logger.info(f"   Pedido: {num_pedido} | NF: {nf} | Status: {lote_data['status']}")
        logger.info(f"   Valores atuais - Valor: R$ {lote_data['valor_total']:.2f} | Peso: {lote_data['peso_total']:.3f} | Pallets: {lote_data['pallet_total']:.2f}")
        
        self.stats['lotes_processados'] += 1
        
        # Se não tem NF, tentar buscar do EmbarqueItem
        if not nf:
            embarque_item = EmbarqueItem.query.filter_by(
                separacao_lote_id=lote_id
            ).first()
            
            if embarque_item and embarque_item.nota_fiscal:
                nf = embarque_item.nota_fiscal
                logger.info(f"   ✓ NF encontrada no EmbarqueItem: {nf}")
                
                # Atualizar Pedido com a NF
                pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()
                if pedido:
                    pedido.nf = nf
            else:
                logger.warning(f"   ⚠️ Lote sem NF - não é possível buscar valores")
                self.stats['lotes_sem_nf'] += 1
                return
        
        # Buscar dados do FaturamentoProduto usando NF
        faturamentos = FaturamentoProduto.query.filter_by(
            numero_nf=nf,
            status_nf='Lançado'
        ).all()
        
        if not faturamentos:
            logger.warning(f"   ⚠️ Nenhum produto encontrado no FaturamentoProduto para NF {nf}")
            self.stats['lotes_sem_faturamento'] += 1
            return
        
        logger.info(f"   ✓ {len(faturamentos)} produtos encontrados no FaturamentoProduto")
        
        # Buscar separações do lote
        separacoes = Separacao.query.filter_by(
            separacao_lote_id=lote_id
        ).all()
        
        lote_atualizado = False
        
        # Atualizar cada separação com valores corretos
        for sep in separacoes:
            # Buscar produto correspondente no faturamento
            fat_produto = None
            for fat in faturamentos:
                if str(fat.cod_produto).strip() == str(sep.cod_produto).strip():
                    fat_produto = fat
                    break
            
            if not fat_produto:
                logger.warning(f"   ⚠️ Produto {sep.cod_produto} não encontrado no faturamento")
                continue
            
            # Atualizar quantidade e valor
            qtd_anterior = sep.qtd_saldo
            valor_anterior = sep.valor_saldo
            peso_anterior = sep.peso
            pallet_anterior = sep.pallet
            
            # Valores do faturamento
            sep.qtd_saldo = float(fat_produto.qtd_produto_faturado)
            sep.valor_saldo = float(fat_produto.valor_produto_faturado)
            
            # Buscar peso bruto e palletização do cadastro
            cadastro = CadastroPalletizacao.query.filter_by(
                cod_produto=sep.cod_produto
            ).first()
            
            if cadastro:
                peso_bruto = float(cadastro.peso_bruto) if cadastro.peso_bruto else 0
                palletizacao = float(cadastro.palletizacao) if cadastro.palletizacao else 1
                
                # Calcular peso total
                sep.peso = sep.qtd_saldo * peso_bruto
                
                # Calcular pallets
                if palletizacao > 0:
                    sep.pallet = sep.qtd_saldo / palletizacao
                else:
                    sep.pallet = 0
                
                logger.info(f"   ✓ Produto {sep.cod_produto}:")
                logger.info(f"      Qtd: {qtd_anterior:.3f} → {sep.qtd_saldo:.3f}")
                logger.info(f"      Valor: R$ {valor_anterior:.2f} → R$ {sep.valor_saldo:.2f}")
                logger.info(f"      Peso: {peso_anterior:.3f} → {sep.peso:.3f} (peso_bruto: {peso_bruto:.3f})")
                logger.info(f"      Pallets: {pallet_anterior:.2f} → {sep.pallet:.2f} (palletização: {palletizacao:.0f})")
                
                self.stats['pesos_calculados'] += 1
                self.stats['pallets_calculados'] += 1
            else:
                logger.warning(f"   ⚠️ Cadastro de palletização não encontrado para {sep.cod_produto}")
                # Manter apenas qtd e valor
                logger.info(f"   ✓ Produto {sep.cod_produto} (sem cadastro palletização):")
                logger.info(f"      Qtd: {qtd_anterior:.3f} → {sep.qtd_saldo:.3f}")
                logger.info(f"      Valor: R$ {valor_anterior:.2f} → R$ {sep.valor_saldo:.2f}")
            
            # Contar correções
            if valor_anterior == 0 and sep.valor_saldo > 0:
                self.stats['valores_zerados_corrigidos'] += 1
            
            self.stats['itens_atualizados'] += 1
            lote_atualizado = True
        
        if lote_atualizado:
            self.stats['lotes_atualizados'] += 1
            
            # Calcular novos totais
            novo_valor_total = sum(s.valor_saldo for s in separacoes)
            novo_peso_total = sum(s.peso for s in separacoes)
            novo_pallet_total = sum(s.pallet for s in separacoes)
            
            logger.info(f"   📊 NOVOS TOTAIS DO LOTE:")
            logger.info(f"      Valor: R$ {lote_data['valor_total']:.2f} → R$ {novo_valor_total:.2f}")
            logger.info(f"      Peso: {lote_data['peso_total']:.3f} → {novo_peso_total:.3f}")
            logger.info(f"      Pallets: {lote_data['pallet_total']:.2f} → {novo_pallet_total:.2f}")
    
    def _exibir_estatisticas(self):
        """Exibe estatísticas finais."""
        logger.info("\n" + "="*70)
        logger.info("📊 ESTATÍSTICAS FINAIS")
        logger.info("="*70)
        
        logger.info(f"✓ Lotes processados: {self.stats['lotes_processados']}")
        logger.info(f"✓ Lotes atualizados: {self.stats['lotes_atualizados']}")
        logger.info(f"✓ Lotes sem NF: {self.stats['lotes_sem_nf']}")
        logger.info(f"✓ Lotes sem faturamento: {self.stats['lotes_sem_faturamento']}")
        logger.info(f"✓ Itens atualizados: {self.stats['itens_atualizados']}")
        logger.info(f"✓ Valores zerados corrigidos: {self.stats['valores_zerados_corrigidos']}")
        logger.info(f"✓ Pesos calculados: {self.stats['pesos_calculados']}")
        logger.info(f"✓ Pallets calculados: {self.stats['pallets_calculados']}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Corrigir valores das separações')
    parser.add_argument('--lotes', nargs='+', help='Lotes específicos para processar')
    parser.add_argument('--confirmar', action='store_true', help='Confirmar e salvar alterações')
    
    args = parser.parse_args()
    
    reconstrutor = ReconstrutorSeparacoesValoresCorretos()
    reconstrutor.executar(lotes_especificos=args.lotes, confirmar=args.confirmar)