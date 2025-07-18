"""
Serviço de Reconciliação - Gestão de Inconsistências
==================================================

Gerencia NFs sem vinculação e separações órfãs
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import and_, or_, not_
from app import db
from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
from app.estoque.models import MovimentacaoEstoque
from app.separacao.models import Separacao
from app.embarques.models import EmbarqueItem

logger = logging.getLogger(__name__)

class ReconciliacaoService:
    """
    Identifica e concilia inconsistências entre NFs e Separações
    """
    
    def buscar_inconsistencias(self) -> Dict[str, List]:
        """
        Busca todas as inconsistências do sistema
        """
        return {
            'nfs_sem_vinculacao': self._buscar_nfs_sem_vinculacao(),
            'separacoes_sem_nf': self._buscar_separacoes_sem_nf(),
            'divergencias_quantidade': self._buscar_divergencias_quantidade()
        }
    
    def _buscar_nfs_sem_vinculacao(self) -> List[Dict]:
        """
        NFs que não conseguiram vincular com nenhuma separação
        """
        # NFs com movimentação "Sem Separação"
        movimentacoes_sem_sep = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.observacao.like('%Sem Separação%')
        ).all()
        
        nfs_sem_vinculacao = []
        numeros_processados = set()
        
        for mov in movimentacoes_sem_sep:
            # Extrair número da NF
            if 'NF' in mov.observacao:
                parts = mov.observacao.split('NF')
                if len(parts) > 1:
                    numero = parts[1].split('-')[0].strip()
                    
                    if numero not in numeros_processados:
                        numeros_processados.add(numero)
                        
                        # Buscar dados da NF
                        nf = RelatorioFaturamentoImportado.query.filter_by(
                            numero_nf=numero
                        ).first()
                        
                        if nf:
                            nfs_sem_vinculacao.append({
                                'numero_nf': nf.numero_nf,
                                'num_pedido': nf.origem,
                                'data_fatura': nf.data_fatura,
                                'nome_cliente': nf.nome_cliente,
                                'valor_total': nf.valor_total,
                                'peso_bruto': nf.peso_bruto
                            })
        
        return nfs_sem_vinculacao
    
    def _buscar_separacoes_sem_nf(self) -> List[Dict]:
        """
        Separações que não têm NF vinculada
        """
        # ✅ CORRETO: Buscar separações sem NF em EmbarqueItem usando separacao_lote_id
        separacoes_sem_nf = db.session.query(Separacao)\
            .outerjoin(EmbarqueItem, 
                      EmbarqueItem.separacao_lote_id == Separacao.separacao_lote_id)\
            .filter(or_(
                EmbarqueItem.nota_fiscal.is_(None),
                EmbarqueItem.id.is_(None)  # Separação sem EmbarqueItem
            ))\
            .all()
        
        resultado = []
        for sep in separacoes_sem_nf:
            resultado.append({
                'lote_id': sep.separacao_lote_id,  # ✅ CORRETO: lote_id não lote_separacao
                'num_pedido': sep.num_pedido,
                'cod_produto': sep.cod_produto,
                'nome_produto': sep.nome_produto,
                'qtd_saldo': sep.qtd_saldo,
                'data_separacao': sep.criado_em,  # ✅ CORRETO: campo criado_em
                'cliente': sep.raz_social_red,  # ✅ ADICIONAR dados do cliente da separação
                'municipio': sep.nome_cidade,  # ✅ CORRETO: nome_cidade no modelo Separacao
                'estado': sep.cod_uf  # ✅ CORRETO: cod_uf no modelo Separacao
            })
        
        return resultado
    
    def _buscar_divergencias_quantidade(self) -> List[Dict]:
        """
        Busca divergências de quantidade entre NF e Separação
        """
        # Buscar da tabela FaturamentoParcialJustificativa
        # Por enquanto retorna vazio - será implementado quando o modelo existir
        return []
    
    def identificar_inconsistencias(self) -> Dict[str, List]:
        """
        Método principal para identificar inconsistências - usado pelos templates
        """
        return self.buscar_inconsistencias()
    
    def conciliar_nf_separacao(self, numero_nf: str, lote_id: str, usuario: str) -> Dict[str, Any]:
        """
        Concilia manualmente uma NF com uma separação
        """
        try:
            # ✅ CORRETO: Verificar se NF existe em FaturamentoProduto (modelo com produtos)
            produtos_nf = FaturamentoProduto.query.filter_by(
                numero_nf=numero_nf
            ).all()
            
            if not produtos_nf:
                return {'sucesso': False, 'erro': 'NF não encontrada no faturamento de produtos'}
            
            # Verificar se separação existe
            separacao = Separacao.query.filter_by(
                separacao_lote_id=lote_id
            ).first()
            
            if not separacao:
                return {'sucesso': False, 'erro': 'Separação não encontrada'}
            
            # Remover movimentação "Sem Separação"
            MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.observacao.like(f'%NF {numero_nf}%Sem Separação%')
            ).delete()
            
            # ✅ CORRETO: Criar nova movimentação vinculada usando dados de FaturamentoProduto
            for produto in produtos_nf:
                movimentacao = MovimentacaoEstoque()
                movimentacao.cod_produto = produto.cod_produto
                movimentacao.nome_produto = produto.nome_produto
                movimentacao.tipo_movimentacao = 'FATURAMENTO'
                movimentacao.local_movimentacao = 'VENDA'
                movimentacao.data_movimentacao = produto.data_fatura  # ✅ CORRETO: data_fatura do FaturamentoProduto
                movimentacao.qtd_movimentacao = -produto.qtd_produto_faturado
                movimentacao.observacao = f"Baixa automática NF {numero_nf} - lote separação {lote_id} (CONCILIADO MANUALMENTE)"
                movimentacao.criado_por = usuario
                db.session.add(movimentacao)
            
            # ✅ USAR separacao_lote_id para atualizar EmbarqueItem
            item = EmbarqueItem.query.filter_by(
                separacao_lote_id=lote_id,
                nota_fiscal=None
            ).first()
            
            if item:
                item.nota_fiscal = numero_nf
            
            db.session.commit()
            
            return {
                'sucesso': True,
                'mensagem': f'NF {numero_nf} vinculada ao lote {lote_id} com sucesso. {len(produtos_nf)} produtos processados.'
            }
            
        except Exception as e:
            db.session.rollback()
            return {'sucesso': False, 'erro': str(e)} 