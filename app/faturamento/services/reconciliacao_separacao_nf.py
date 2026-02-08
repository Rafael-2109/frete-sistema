"""
Serviço de Reconciliação Separação x NF
========================================

Este serviço garante a consistência entre Separações e NFs faturadas.
Pode ser executado periodicamente ou sob demanda.

Criado: 2025-08-21
Objetivo: Manter integridade dos dados após mudanças do sistema
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from decimal import Decimal
from app import db
from app.utils.timezone import agora_utc_naive
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
from app.producao.models import CadastroPalletizacao

logger = logging.getLogger(__name__)


class ReconciliacaoSeparacaoNF:
    """
    Serviço para reconciliar Separações com NFs faturadas
    
    Principais funções:
    1. Verificar separações sem sincronização
    2. Encontrar NFs correspondentes
    3. Sincronizar quantidades
    4. Gerar relatório de discrepâncias
    """
    
    @classmethod
    def executar_reconciliacao_completa(cls, dias_retroativos: int = 30) -> Dict[str, Any]:
        """
        Executa reconciliação completa de todas as separações
        
        Args:
            dias_retroativos: Quantos dias para trás verificar
            
        Returns:
            Dict com estatísticas da reconciliação
        """
        logger.info(f"🔄 INICIANDO RECONCILIAÇÃO COMPLETA - Últimos {dias_retroativos} dias")
        
        resultado = {
            'sucesso': True,
            'separacoes_analisadas': 0,
            'separacoes_sincronizadas': 0,
            'separacoes_com_discrepancia': 0,
            'separacoes_sem_nf': 0,
            'erros': [],
            'discrepancias': []
        }
        
        try:
            # Data limite para análise
            data_limite = datetime.now() - timedelta(days=dias_retroativos)
            
            # 1. Buscar separações não sincronizadas ou com possível discrepância
            separacoes_para_verificar = cls._buscar_separacoes_para_reconciliar(data_limite)
            resultado['separacoes_analisadas'] = len(separacoes_para_verificar)
            
            logger.info(f"📊 Encontradas {len(separacoes_para_verificar)} separações para analisar")
            
            # 2. Processar cada separação
            for lote_id, pedido_info in separacoes_para_verificar.items():
                try:
                    resultado_lote = cls._reconciliar_lote(
                        lote_id=lote_id,
                        num_pedido=pedido_info['num_pedido'],
                        numero_nf=pedido_info['numero_nf']
                    )
                    
                    if resultado_lote['sincronizado']:
                        resultado['separacoes_sincronizadas'] += 1
                    
                    if resultado_lote['discrepancias']:
                        resultado['separacoes_com_discrepancia'] += 1
                        resultado['discrepancias'].extend(resultado_lote['discrepancias'])
                    
                    if not resultado_lote['nf_encontrada']:
                        resultado['separacoes_sem_nf'] += 1
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao reconciliar lote {lote_id}: {e}")
                    resultado['erros'].append(f"Lote {lote_id}: {str(e)}")
                    continue
            
            # 3. Commit das alterações
            if resultado['separacoes_sincronizadas'] > 0:
                db.session.commit()
                logger.info(f"✅ {resultado['separacoes_sincronizadas']} separações sincronizadas com sucesso")
            
            # 4. Relatório final
            cls._gerar_relatorio_reconciliacao(resultado)
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro na reconciliação completa: {e}")
            resultado['sucesso'] = False
            resultado['erro_geral'] = str(e)
        
        return resultado
    
    @classmethod
    def _buscar_separacoes_para_reconciliar(cls, data_limite: datetime) -> Dict[str, Dict]:
        """
        Busca separações que precisam ser reconciliadas
        
        Critérios:
        1. Não sincronizadas (sincronizado_nf = False)
        2. Pedidos com status FATURADO mas separação não sincronizada
        3. Separações criadas após a data limite
        """
        separacoes_dict = {}
        
        # Query: Separações com Pedidos FATURADOS ou com NF
        query = db.session.query(
            Separacao.separacao_lote_id,
            Separacao.num_pedido,
            Pedido.nf,
            Pedido.status,
            db.func.count(Separacao.id).label('total_itens'),
            db.func.sum(Separacao.qtd_saldo).label('qtd_total')
        ).outerjoin(
            Pedido,
            Separacao.separacao_lote_id == Pedido.separacao_lote_id
        ).filter(
            Separacao.criado_em >= data_limite,
            db.or_(
                Separacao.sincronizado_nf == False,
                Separacao.sincronizado_nf.is_(None),
                db.and_(
                    Pedido.status == 'FATURADO',
                    Separacao.sincronizado_nf == False
                )
            )
        ).group_by(
            Separacao.separacao_lote_id,
            Separacao.num_pedido,
            Pedido.nf,
            Pedido.status
        ).all()
        
        for row in query:
            lote_id, num_pedido, numero_nf, status, total_itens, qtd_total = row
            
            # Adicionar ao dicionário se tem NF ou está FATURADO
            if numero_nf or status == 'FATURADO':
                separacoes_dict[lote_id] = {
                    'num_pedido': num_pedido,
                    'numero_nf': numero_nf,
                    'status': status,
                    'total_itens': total_itens,
                    'qtd_total': float(qtd_total) if qtd_total else 0
                }
        
        return separacoes_dict
    
    @classmethod
    def _reconciliar_lote(cls, lote_id: str, num_pedido: str, numero_nf: Optional[str]) -> Dict[str, Any]:
        """
        Reconcilia um lote específico de separação com sua NF
        """
        resultado = {
            'sincronizado': False,
            'nf_encontrada': False,
            'discrepancias': []
        }
        
        # Se não tem NF, tentar encontrar
        if not numero_nf:
            # Buscar NF pelo pedido
            faturamento = FaturamentoProduto.query.filter_by(origem=num_pedido).first()
            if faturamento:
                numero_nf = faturamento.numero_nf
                resultado['nf_encontrada'] = True
                logger.info(f"📋 NF {numero_nf} encontrada para pedido {num_pedido}")
        else:
            resultado['nf_encontrada'] = True
        
        if not numero_nf:
            logger.warning(f"⚠️ Nenhuma NF encontrada para lote {lote_id} / pedido {num_pedido}")
            return resultado
        
        # Buscar produtos da NF
        produtos_nf = FaturamentoProduto.query.filter_by(
            numero_nf=numero_nf,
            origem=num_pedido
        ).all()
        
        if not produtos_nf:
            logger.warning(f"⚠️ Nenhum produto encontrado na NF {numero_nf} para pedido {num_pedido}")
            return resultado
        
        # Buscar separações do lote
        separacoes = Separacao.query.filter_by(
            separacao_lote_id=lote_id,
            num_pedido=num_pedido
        ).all()
        
        if not separacoes:
            logger.warning(f"⚠️ Nenhuma separação encontrada para lote {lote_id}")
            return resultado
        
        # Criar dicionário de produtos da NF
        produtos_nf_dict = {}
        for prod in produtos_nf:
            if prod.cod_produto not in produtos_nf_dict:
                produtos_nf_dict[prod.cod_produto] = {
                    'qtd': 0,
                    'valor': 0,
                    'peso': 0
                }
            produtos_nf_dict[prod.cod_produto]['qtd'] += float(prod.qtd_produto_faturado or 0)
            produtos_nf_dict[prod.cod_produto]['valor'] += float(prod.valor_produto_faturado or 0)
            produtos_nf_dict[prod.cod_produto]['peso'] += float(prod.peso_total or 0)
        
        # Reconciliar cada separação
        for sep in separacoes:
            if sep.cod_produto in produtos_nf_dict:
                dados_nf = produtos_nf_dict[sep.cod_produto]
                
                # Verificar discrepância
                qtd_atual = float(sep.qtd_saldo or 0)
                qtd_nf = dados_nf['qtd']
                
                if abs(qtd_atual - qtd_nf) > 0.01:  # Tolerância para float
                    resultado['discrepancias'].append({
                        'lote_id': lote_id,
                        'produto': sep.cod_produto,
                        'qtd_separacao': qtd_atual,
                        'qtd_nf': qtd_nf,
                        'diferenca': qtd_nf - qtd_atual
                    })
                    
                    # Sincronizar com valor da NF
                    logger.info(f"🔄 Sincronizando {sep.cod_produto}: {qtd_atual} → {qtd_nf}")
                    sep.qtd_saldo = qtd_nf
                    sep.valor_saldo = dados_nf['valor']
                    sep.peso = dados_nf['peso']
                    
                    # Calcular pallets
                    palletizacao = CadastroPalletizacao.query.filter_by(
                        cod_produto=sep.cod_produto
                    ).first()
                    if palletizacao and palletizacao.palletizacao > 0:
                        sep.pallet = qtd_nf / float(palletizacao.palletizacao)
                
                # Marcar como sincronizado
                if not sep.sincronizado_nf:
                    sep.sincronizado_nf = True
                    sep.numero_nf = numero_nf
                    sep.data_sincronizacao = agora_utc_naive()
                    resultado['sincronizado'] = True
            else:
                # Produto não está na NF - verificar se precisa zerar
                if sep.qtd_saldo > 0 and not sep.zerado_por_sync:
                    logger.warning(f"⚠️ Produto {sep.cod_produto} não consta na NF - marcando para revisão")
                    resultado['discrepancias'].append({
                        'lote_id': lote_id,
                        'produto': sep.cod_produto,
                        'qtd_separacao': float(sep.qtd_saldo),
                        'qtd_nf': 0,
                        'diferenca': -float(sep.qtd_saldo),
                        'acao': 'PRODUTO_NAO_FATURADO'
                    })
        
        return resultado
    
    @classmethod
    def _gerar_relatorio_reconciliacao(cls, resultado: Dict[str, Any]):
        """
        Gera relatório detalhado da reconciliação
        """
        logger.info("=" * 60)
        logger.info("📊 RELATÓRIO DE RECONCILIAÇÃO SEPARAÇÃO x NF")
        logger.info("=" * 60)
        logger.info(f"📋 Separações analisadas: {resultado['separacoes_analisadas']}")
        logger.info(f"✅ Sincronizadas: {resultado['separacoes_sincronizadas']}")
        logger.info(f"⚠️ Com discrepância: {resultado['separacoes_com_discrepancia']}")
        logger.info(f"❌ Sem NF: {resultado['separacoes_sem_nf']}")
        
        if resultado['discrepancias']:
            logger.info("\n📊 PRINCIPAIS DISCREPÂNCIAS:")
            for disc in resultado['discrepancias'][:10]:  # Mostrar apenas as 10 primeiras
                logger.info(f"  - Lote {disc['lote_id']}, Produto {disc['produto']}: "
                          f"Sep={disc['qtd_separacao']}, NF={disc['qtd_nf']}, "
                          f"Diff={disc['diferenca']}")
        
        if resultado['erros']:
            logger.error("\n❌ ERROS ENCONTRADOS:")
            for erro in resultado['erros'][:5]:  # Mostrar apenas os 5 primeiros
                logger.error(f"  - {erro}")
        
        logger.info("=" * 60)
    
    @classmethod
    def verificar_integridade_lote(cls, lote_id: str) -> Dict[str, Any]:
        """
        Verifica a integridade de um lote específico
        
        Args:
            lote_id: ID do lote para verificar
            
        Returns:
            Dict com status da integridade
        """
        resultado = {
            'lote_id': lote_id,
            'integro': True,
            'problemas': []
        }
        
        try:
            # Buscar Pedido
            pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()
            if not pedido:
                resultado['integro'] = False
                resultado['problemas'].append('Pedido não encontrado')
                return resultado
            
            # Buscar Separações
            separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()
            if not separacoes:
                resultado['integro'] = False
                resultado['problemas'].append('Nenhuma separação encontrada')
                return resultado
            
            # Se tem NF, verificar sincronização
            if pedido.nf:
                # Verificar se existe FaturamentoProduto
                faturamentos = FaturamentoProduto.query.filter_by(
                    numero_nf=pedido.nf,
                    origem=pedido.num_pedido
                ).all()
                
                if not faturamentos:
                    resultado['integro'] = False
                    resultado['problemas'].append(f'NF {pedido.nf} não encontrada em FaturamentoProduto')
                
                # Verificar se separações estão sincronizadas
                for sep in separacoes:
                    if not sep.sincronizado_nf:
                        resultado['integro'] = False
                        resultado['problemas'].append(f'Separação {sep.cod_produto} não sincronizada')
                        break
            
            # Se status é FATURADO, deve ter NF
            if pedido.status == 'FATURADO' and not pedido.nf:
                resultado['integro'] = False
                resultado['problemas'].append('Pedido FATURADO sem NF')
            
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao verificar integridade do lote {lote_id}: {e}")
            resultado['integro'] = False
            resultado['problemas'].append(f'Erro: {str(e)}')
            return resultado


# Função para execução via CLI ou agendamento
def executar_reconciliacao_cli(dias: int = 30):
    """
    Função para execução via linha de comando ou agendamento
    
    Uso:
        python -c "from app.faturamento.services.reconciliacao_separacao_nf import executar_reconciliacao_cli; executar_reconciliacao_cli(30)"
    """
    from app import create_app
    
    app = create_app()
    with app.app_context():
        resultado = ReconciliacaoSeparacaoNF.executar_reconciliacao_completa(dias)
        
        if resultado['sucesso']:
            print(f"✅ Reconciliação concluída com sucesso!")
            print(f"   - {resultado['separacoes_sincronizadas']} separações sincronizadas")
            print(f"   - {resultado['separacoes_com_discrepancia']} com discrepâncias corrigidas")
        else:
            print(f"❌ Erro na reconciliação: {resultado.get('erro_geral', 'Erro desconhecido')}")
        
        return resultado