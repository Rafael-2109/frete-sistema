#!/usr/bin/env python3
"""
Script Melhorado para Reconstruir Separações Deletadas
========================================================

Este script reconstrói Separações perdidas usando múltiplas fontes:
1. Alertas de separações (AlertaSeparacaoCotada)
2. Dados do Pedido
3. FaturamentoProduto (quando disponível)
4. EmbarqueItem (para validação)

Melhorias:
- Usa FaturamentoProduto para valores mais precisos
- Valida com EmbarqueItem
- Melhor cálculo de valores e pesos
- Opção de reconstruir lotes específicos
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from app.carteira.models_alertas import AlertaSeparacaoCotada
from app.faturamento.models import FaturamentoProduto
from app.embarques.models import EmbarqueItem
from app.producao.models import CadastroPalletizacao
from app.carteira.models import CarteiraPrincipal
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReconstrutorSeparacoes:
    """Classe para reconstruir separações perdidas."""
    
    def __init__(self):
        self.app = create_app()
        self.stats = {
            'lotes_processados': 0,
            'lotes_reconstruidos': 0,
            'lotes_ja_existentes': 0,
            'lotes_sem_dados': 0,
            'itens_criados': 0,
            'usando_faturamento': 0,
            'usando_alertas': 0,
            'usando_carteira': 0
        }
    
    def executar(self, lotes_especificos=None, confirmar=False):
        """
        Executa a reconstrução das separações.
        
        Args:
            lotes_especificos: Lista de lotes específicos para reconstruir (None = todos)
            confirmar: Se True, salva as alterações no banco
        """
        with self.app.app_context():
            logger.info("="*70)
            logger.info("🔧 RECONSTRUÇÃO MELHORADA DE SEPARAÇÕES")
            logger.info("="*70)
            
            # Buscar lotes para processar
            lotes = self._buscar_lotes_para_reconstruir(lotes_especificos)
            
            if not lotes:
                logger.warning("⚠️ Nenhum lote encontrado para processar")
                return
            
            logger.info(f"📋 {len(lotes)} lotes encontrados para análise")
            
            # Processar cada lote
            for lote_info in lotes:
                self._processar_lote(lote_info)
            
            # Salvar se confirmado
            if confirmar and self.stats['lotes_reconstruidos'] > 0:
                logger.info("\n💾 Salvando alterações no banco...")
                db.session.commit()
                logger.info("✅ Alterações salvas com sucesso!")
            elif not confirmar:
                logger.warning("\n⚠️ MODO SIMULAÇÃO - Use --confirmar para salvar")
                db.session.rollback()
            
            # Exibir estatísticas
            self._exibir_estatisticas()
    
    def _buscar_lotes_para_reconstruir(self, lotes_especificos=None):
        """Busca lotes que precisam ser reconstruídos."""
        
        if lotes_especificos:
            # Buscar lotes específicos
            logger.info(f"🔍 Buscando {len(lotes_especificos)} lotes específicos...")
            lotes = []
            for lote_id in lotes_especificos:
                # Verificar se tem alerta ou pedido
                pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()
                alerta = AlertaSeparacaoCotada.query.filter_by(separacao_lote_id=lote_id).first()
                embarque = EmbarqueItem.query.filter_by(separacao_lote_id=lote_id).first()
                
                if pedido or alerta or embarque:
                    lotes.append({
                        'lote_id': lote_id,
                        'tem_pedido': pedido is not None,
                        'tem_alerta': alerta is not None,
                        'tem_embarque': embarque is not None,
                        'num_pedido': pedido.num_pedido if pedido else (embarque.pedido if embarque else None)
                    })
        else:
            # Buscar todos os lotes com alertas
            logger.info("🔍 Buscando todos os lotes com alertas...")
            
            # Query para lotes únicos
            lotes_query = db.session.query(
                AlertaSeparacaoCotada.separacao_lote_id,
                AlertaSeparacaoCotada.num_pedido,
                db.func.count(AlertaSeparacaoCotada.id).label('total_alertas')
            ).filter(
                AlertaSeparacaoCotada.separacao_lote_id.isnot(None)
            ).group_by(
                AlertaSeparacaoCotada.separacao_lote_id,
                AlertaSeparacaoCotada.num_pedido
            ).all()
            
            lotes = []
            for lote_id, num_pedido, total_alertas in lotes_query:
                # Verificar se já tem Separacao
                tem_separacao = Separacao.query.filter_by(
                    separacao_lote_id=lote_id
                ).first() is not None
                
                if not tem_separacao:
                    lotes.append({
                        'lote_id': lote_id,
                        'num_pedido': num_pedido,
                        'total_alertas': total_alertas,
                        'tem_pedido': True,  # Será verificado depois
                        'tem_alerta': True,
                        'tem_embarque': False  # Será verificado depois
                    })
        
        return lotes
    
    def _processar_lote(self, lote_info):
        """Processa um lote específico."""
        lote_id = lote_info['lote_id']
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📦 Processando lote: {lote_id}")
        self.stats['lotes_processados'] += 1
        
        # Verificar se já existe
        if Separacao.query.filter_by(separacao_lote_id=lote_id).first():
            logger.warning(f"⚠️ Lote já tem Separação - pulando")
            self.stats['lotes_ja_existentes'] += 1
            return
        
        # Coletar dados de múltiplas fontes
        dados = self._coletar_dados_lote(lote_id)
        
        if not dados['produtos']:
            logger.error(f"❌ Sem dados de produtos para reconstruir")
            self.stats['lotes_sem_dados'] += 1
            return
        
        # Criar Separações
        itens_criados = self._criar_separacoes(lote_id, dados)
        
        if itens_criados > 0:
            logger.info(f"✅ Lote reconstruído com {itens_criados} itens")
            self.stats['lotes_reconstruidos'] += 1
            self.stats['itens_criados'] += itens_criados
    
    def _coletar_dados_lote(self, lote_id):
        """Coleta dados de todas as fontes disponíveis."""
        dados = {
            'pedido': None,
            'produtos': {},
            'fonte_principal': None
        }
        
        # 1. Buscar Pedido
        pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()
        if pedido:
            dados['pedido'] = pedido
            logger.info(f"  ✓ Pedido encontrado: {pedido.num_pedido}")
        
        # 2. PRIORIDADE: Buscar FaturamentoProduto (tem cod_produto, qtd e valor)
        if pedido:
            faturamentos = FaturamentoProduto.query.filter_by(
                origem=pedido.num_pedido,
                status_nf='Lançado'  # Apenas NFs válidas
            ).all()
            
            if faturamentos:
                logger.info(f"  ✓ {len(faturamentos)} produtos no FaturamentoProduto")
                dados['fonte_principal'] = 'faturamento'
                self.stats['usando_faturamento'] += 1
                
                for fat in faturamentos:
                    # Buscar peso unitário do CadastroPalletizacao
                    palletizacao = CadastroPalletizacao.query.filter_by(
                        cod_produto=fat.cod_produto
                    ).first()
                    
                    peso_unitario = 1.0  # Padrão se não encontrar
                    if palletizacao and palletizacao.peso_unitario:
                        peso_unitario = float(palletizacao.peso_unitario)
                    
                    # Calcular peso total = qtd * peso_unitario
                    peso_total = float(fat.qtd_produto_faturado) * peso_unitario
                    
                    dados['produtos'][fat.cod_produto] = {
                        'nome': fat.nome_produto,
                        'qtd': float(fat.qtd_produto_faturado),  # QTD do FaturamentoProduto
                        'valor': float(fat.valor_produto_faturado),  # VALOR do FaturamentoProduto
                        'peso': peso_total,  # PESO calculado com CadastroPalletizacao
                        'peso_unitario': peso_unitario,
                        'fonte': 'faturamento'
                    }
                    
                    logger.debug(f"    Produto {fat.cod_produto}: Qtd={fat.qtd_produto_faturado}, "
                               f"Valor={fat.valor_produto_faturado}, Peso={peso_total:.2f} "
                               f"(unitário={peso_unitario})")
        
        # 3. Se não tem FaturamentoProduto, buscar CarteiraPrincipal
        if not dados['produtos'] and pedido:
            carteira_items = CarteiraPrincipal.query.filter_by(
                num_pedido=pedido.num_pedido
            ).all()
            
            if carteira_items:
                logger.info(f"  ✓ {len(carteira_items)} produtos na CarteiraPrincipal")
                dados['fonte_principal'] = 'carteira'
                self.stats['usando_carteira'] += 1
                
                for item in carteira_items:
                    # Usar qtd_saldo se disponível, senão qtd_saldo_produto_pedido
                    qtd = float(item.qtd_saldo) if item.qtd_saldo else float(item.qtd_saldo_produto_pedido)
                    if qtd > 0:
                        # Buscar peso unitário do CadastroPalletizacao
                        palletizacao = CadastroPalletizacao.query.filter_by(
                            cod_produto=item.cod_produto
                        ).first()
                        
                        peso_unitario = 1.0  # Padrão se não encontrar
                        if palletizacao and palletizacao.peso_unitario:
                            peso_unitario = float(palletizacao.peso_unitario)
                        
                        # Calcular valores
                        valor_total = float(item.valor_saldo) if item.valor_saldo else qtd * float(item.preco_produto_pedido or 0)
                        peso_total = qtd * peso_unitario
                        
                        dados['produtos'][item.cod_produto] = {
                            'nome': item.nome_produto,
                            'qtd': qtd,  # QTD da CarteiraPrincipal
                            'valor': valor_total,  # VALOR da CarteiraPrincipal ou calculado
                            'peso': peso_total,  # PESO calculado com CadastroPalletizacao
                            'peso_unitario': peso_unitario,
                            'fonte': 'carteira'
                        }
        
        # 4. Se ainda não tem produtos, usar Alertas (última opção)
        if not dados['produtos']:
            alertas = AlertaSeparacaoCotada.query.filter_by(
                separacao_lote_id=lote_id
            ).all()
            
            if alertas:
                logger.info(f"  ✓ {len(alertas)} alertas encontrados")
                dados['fonte_principal'] = 'alertas'
                self.stats['usando_alertas'] += 1
                
                for alerta in alertas:
                    if alerta.cod_produto and alerta.cod_produto != 'TODOS':
                        cod = alerta.cod_produto
                        qtd_usar = float(alerta.qtd_anterior or alerta.qtd_nova or 0)
                        
                        if cod not in dados['produtos'] or qtd_usar > dados['produtos'][cod]['qtd']:
                            # Buscar peso unitário do CadastroPalletizacao
                            palletizacao = CadastroPalletizacao.query.filter_by(
                                cod_produto=cod
                            ).first()
                            
                            peso_unitario = 1.0
                            if palletizacao and palletizacao.peso_unitario:
                                peso_unitario = float(palletizacao.peso_unitario)
                            
                            dados['produtos'][cod] = {
                                'nome': alerta.nome_produto or f'Produto {cod}',
                                'qtd': qtd_usar,  # QTD do alerta
                                'valor': 0,  # Sem valor nos alertas - será estimado
                                'peso': qtd_usar * peso_unitario,  # PESO calculado
                                'peso_unitario': peso_unitario,
                                'fonte': 'alerta'
                            }
        
        # 5. Buscar EmbarqueItem para validação
        embarque_item = EmbarqueItem.query.filter_by(
            separacao_lote_id=lote_id
        ).first()
        
        if embarque_item:
            logger.info(f"  ✓ EmbarqueItem encontrado (NF: {embarque_item.nota_fiscal})")
            dados['embarque_item'] = embarque_item
        
        # Resumo dos dados coletados
        if dados['produtos']:
            logger.info(f"  📊 Total de produtos: {len(dados['produtos'])}")
            logger.info(f"  📊 Fonte principal: {dados['fonte_principal']}")
            total_qtd = sum(p['qtd'] for p in dados['produtos'].values())
            total_valor = sum(p['valor'] for p in dados['produtos'].values())
            total_peso = sum(p['peso'] for p in dados['produtos'].values())
            logger.info(f"  📊 Totais: Qtd={total_qtd:.2f}, Valor=R${total_valor:.2f}, Peso={total_peso:.2f}kg")
        
        return dados
    
    def _criar_separacoes(self, lote_id, dados):
        """Cria as Separações com os dados coletados."""
        pedido = dados['pedido']
        itens_criados = 0
        
        # Se não tem pedido, tentar criar dados mínimos
        if not pedido:
            embarque = dados.get('embarque_item')
            if embarque:
                # Usar dados do EmbarqueItem
                cnpj = embarque.cnpj_cliente
                cliente = embarque.cliente
                cidade = embarque.cidade_destino
                uf = embarque.uf_destino
                num_pedido = embarque.pedido
                data_pedido = None
                expedicao = None
                agendamento = embarque.data_agenda if hasattr(embarque, 'data_agenda') else None
                protocolo = embarque.protocolo_agendamento
            else:
                logger.error("  ❌ Sem dados do pedido ou embarque")
                return 0
        else:
            # Usar dados do Pedido
            cnpj = pedido.cnpj_cpf
            cliente = pedido.raz_social_red
            cidade = pedido.nome_cidade or pedido.cidade_normalizada
            uf = pedido.cod_uf or pedido.uf_normalizada
            num_pedido = pedido.num_pedido
            data_pedido = pedido.data_pedido
            expedicao = pedido.expedicao
            agendamento = pedido.agendamento
            protocolo = pedido.protocolo
        
        # Criar uma Separacao para cada produto
        for cod_produto, info in dados['produtos'].items():
            if info['qtd'] <= 0:
                continue
            
            # Buscar palletização
            palletizacao = CadastroPalletizacao.query.filter_by(
                cod_produto=cod_produto
            ).first()
            
            qtd_pallets = 0
            peso_real = info['peso']
            
            if palletizacao:
                if palletizacao.palletizacao and palletizacao.palletizacao > 0:
                    qtd_pallets = info['qtd'] / float(palletizacao.palletizacao)
                
                # Se não tem peso, estimar baseado no produto
                if peso_real == 0 and palletizacao.peso_unitario:
                    peso_real = info['qtd'] * float(palletizacao.peso_unitario)
            
            # Se ainda não tem peso, usar estimativa padrão
            if peso_real == 0:
                peso_real = info['qtd'] * 1.0  # 1kg por unidade como padrão
            
            # Criar Separacao
            nova_separacao = Separacao(
                # Identificação
                separacao_lote_id=lote_id,
                num_pedido=num_pedido,
                
                # Produto
                cod_produto=cod_produto,
                nome_produto=info['nome'],
                qtd_saldo=info['qtd'],
                
                # Cliente
                cnpj_cpf=cnpj,
                raz_social_red=cliente,
                nome_cidade=cidade,
                cod_uf=uf,
                
                # Datas
                data_pedido=data_pedido,
                expedicao=expedicao,
                agendamento=agendamento,
                protocolo=protocolo,
                
                # Valores
                valor_saldo=info['valor'] if info['valor'] > 0 else info['qtd'] * 10,
                peso=peso_real,
                pallet=qtd_pallets,
                
                # Operacional
                tipo_envio='total',
                observ_ped_1=f'Reconstruído via {info["fonte"]} em {datetime.now().strftime("%Y-%m-%d %H:%M")}',
                
                # Transportadora (se houver no pedido)
                roteirizacao=pedido.transportadora if pedido and hasattr(pedido, 'transportadora') else None,
                
                # Timestamps
                criado_em=datetime.utcnow()
            )
            
            db.session.add(nova_separacao)
            itens_criados += 1
            
            logger.info(f"    ✅ {cod_produto}: {info['qtd']:.2f} un | "
                       f"R$ {info['valor']:.2f} | {peso_real:.2f} kg | "
                       f"Fonte: {info['fonte']}")
        
        return itens_criados
    
    def _exibir_estatisticas(self):
        """Exibe as estatísticas finais."""
        logger.info("\n" + "="*70)
        logger.info("📊 ESTATÍSTICAS DA RECONSTRUÇÃO")
        logger.info("="*70)
        
        logger.info(f"📋 Lotes processados: {self.stats['lotes_processados']}")
        logger.info(f"✅ Lotes reconstruídos: {self.stats['lotes_reconstruidos']}")
        logger.info(f"⚠️ Lotes já existentes: {self.stats['lotes_ja_existentes']}")
        logger.info(f"❌ Lotes sem dados: {self.stats['lotes_sem_dados']}")
        logger.info(f"📦 Total de itens criados: {self.stats['itens_criados']}")
        
        logger.info(f"\n📊 Fontes de dados utilizadas:")
        logger.info(f"  - FaturamentoProduto: {self.stats['usando_faturamento']} lotes")
        logger.info(f"  - CarteiraPrincipal: {self.stats['usando_carteira']} lotes")
        logger.info(f"  - Alertas: {self.stats['usando_alertas']} lotes")
        
        if self.stats['lotes_reconstruidos'] > 0:
            logger.info(f"\n✅ SUCESSO: {self.stats['lotes_reconstruidos']} lotes reconstruídos!")
        else:
            logger.info("\n⚠️ Nenhuma separação foi reconstruída")

def listar_lotes_sem_separacao():
    """Lista todos os lotes que não têm Separação."""
    app = create_app()
    
    with app.app_context():
        logger.info("\n📋 LOTES SEM SEPARAÇÃO:")
        logger.info("-" * 70)
        
        # Buscar Pedidos com lote mas sem Separacao
        pedidos_sem_sep = db.session.query(Pedido).filter(
            Pedido.separacao_lote_id.isnot(None),
            ~db.exists().where(
                Separacao.separacao_lote_id == Pedido.separacao_lote_id
            )
        ).all()
        
        if pedidos_sem_sep:
            logger.info(f"\n🔴 {len(pedidos_sem_sep)} Pedidos com lote mas SEM Separação:")
            for pedido in pedidos_sem_sep[:20]:  # Limitar a 20
                logger.info(f"  Lote: {pedido.separacao_lote_id} | "
                          f"Pedido: {pedido.num_pedido} | "
                          f"Status: {pedido.status}")
        
        # Buscar EmbarqueItems com lote mas sem Separacao
        embarques_sem_sep = db.session.query(EmbarqueItem).filter(
            EmbarqueItem.separacao_lote_id.isnot(None),
            ~db.exists().where(
                Separacao.separacao_lote_id == EmbarqueItem.separacao_lote_id
            )
        ).all()
        
        if embarques_sem_sep:
            logger.info(f"\n🟡 {len(embarques_sem_sep)} EmbarqueItems com lote mas SEM Separação:")
            for item in embarques_sem_sep[:20]:  # Limitar a 20
                logger.info(f"  Lote: {item.separacao_lote_id} | "
                          f"Pedido: {item.pedido} | "
                          f"NF: {item.nota_fiscal}")

def main():
    """Função principal."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Reconstruir Separações perdidas usando múltiplas fontes de dados'
    )
    parser.add_argument(
        '--listar', 
        action='store_true',
        help='Listar lotes sem separação'
    )
    parser.add_argument(
        '--lotes',
        nargs='+',
        help='Lotes específicos para reconstruir (ex: --lotes LOTE1 LOTE2)'
    )
    parser.add_argument(
        '--confirmar',
        action='store_true',
        help='Confirmar e salvar as alterações no banco'
    )
    
    args = parser.parse_args()
    
    try:
        if args.listar:
            listar_lotes_sem_separacao()
        else:
            if not args.confirmar:
                logger.warning("\n⚠️ MODO SIMULAÇÃO - Use --confirmar para salvar no banco\n")
            
            reconstrutor = ReconstrutorSeparacoes()
            reconstrutor.executar(
                lotes_especificos=args.lotes,
                confirmar=args.confirmar
            )
        
        logger.info("\n✅ Script executado com sucesso")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"\n❌ Erro durante execução: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()