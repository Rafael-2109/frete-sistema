#!/usr/bin/env python3
"""
Script Melhorado para Reconstruir Separações Deletadas com Fallback Robusto
===========================================================================

Este script reconstrói Separações perdidas usando múltiplas fontes e fallbacks:
1. Alertas de separações (AlertaSeparacaoCotada) 
2. Dados do Pedido (usando separacao_lote_id como fallback)
3. FaturamentoProduto (quando disponível)
4. EmbarqueItem (para validação e recuperação de separacao_lote_id)

Melhorias implementadas:
- Fallback via Pedido quando Separacao foi completamente apagada
- Validação de produtos e quantidades entre fontes
- Recuperação de separacao_lote_id perdido em EmbarqueItem via NF
- Reconstrução mantendo separacao_lote_id original
- Logs detalhados de todas as operações
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
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReconstrutorSeparacoes:
    """Classe para reconstruir separações perdidas com fallback robusto."""
    
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
            'usando_carteira': 0,
            'separacoes_validadas': 0,
            'separacoes_divergentes': 0,
            'embarques_atualizados': 0,
            'lotes_recuperados_via_pedido': 0,
            'lotes_recuperados_via_nf': 0
        }
    
    def executar(self, lotes_especificos=None, confirmar=False):
        """
        Executa a reconstrução das separações com fallback robusto.
        
        Args:
            lotes_especificos: Lista de lotes específicos para reconstruir (None = todos)
            confirmar: Se True, salva as alterações no banco
        """
        with self.app.app_context():
            logger.info("="*70)
            logger.info("🔧 RECONSTRUÇÃO MELHORADA DE SEPARAÇÕES COM FALLBACK ROBUSTO")
            logger.info("="*70)
            
            # Buscar lotes para processar (incluindo fallback)
            lotes = self._buscar_lotes_com_fallback(lotes_especificos)
            
            if not lotes:
                logger.warning("⚠️ Nenhum lote encontrado para processar")
                return
            
            logger.info(f"📋 {len(lotes)} lotes encontrados para análise")
            
            # Processar cada lote
            for lote_info in lotes:
                self._processar_lote_com_validacao(lote_info)
            
            # Atualizar EmbarqueItems sem separacao_lote_id
            self._atualizar_embarque_items_sem_lote()
            
            # Salvar se confirmado
            if confirmar and (self.stats['lotes_reconstruidos'] > 0 or self.stats['embarques_atualizados'] > 0):
                logger.info("\n💾 Salvando alterações no banco...")
                db.session.commit()
                logger.info("✅ Alterações salvas com sucesso!")
            elif not confirmar:
                logger.warning("\n⚠️ MODO SIMULAÇÃO - Use --confirmar para salvar")
                db.session.rollback()
            
            # Exibir estatísticas
            self._exibir_estatisticas()
    
    def _buscar_lotes_com_fallback(self, lotes_especificos=None) -> List[Dict]:
        """
        Busca lotes que precisam ser reconstruídos, incluindo fallback via Pedido.
        """
        lotes_para_processar = []
        lotes_processados = set()
        
        if lotes_especificos:
            # Processar lotes específicos
            for lote_id in lotes_especificos:
                if lote_id not in lotes_processados:
                    info = self._analisar_lote(lote_id)
                    if info:
                        lotes_para_processar.append(info)
                        lotes_processados.add(lote_id)
        else:
            # 1. Buscar todos os lotes em Alertas
            logger.info("🔍 Buscando lotes em Alertas...")
            alertas_lotes = db.session.query(
                AlertaSeparacaoCotada.separacao_lote_id
            ).filter(
                AlertaSeparacaoCotada.separacao_lote_id.isnot(None)
            ).distinct().all()
            
            for (lote_id,) in alertas_lotes:
                if lote_id not in lotes_processados:
                    info = self._analisar_lote(lote_id)
                    if info:
                        lotes_para_processar.append(info)
                        lotes_processados.add(lote_id)
            
            # 2. Buscar Pedidos com separacao_lote_id mas sem Separacao (FALLBACK)
            logger.info("🔍 Buscando Pedidos órfãos (sem Separação correspondente)...")
            pedidos_orfaos = db.session.query(Pedido).filter(
                Pedido.separacao_lote_id.isnot(None),
                ~db.exists().where(
                    Separacao.separacao_lote_id == Pedido.separacao_lote_id
                )
            ).all()
            
            for pedido in pedidos_orfaos:
                if pedido.separacao_lote_id not in lotes_processados:
                    logger.info(f"  📌 Pedido órfão encontrado: {pedido.num_pedido} (Lote: {pedido.separacao_lote_id})")
                    self.stats['lotes_recuperados_via_pedido'] += 1
                    
                    info = self._analisar_lote(pedido.separacao_lote_id, pedido_fallback=pedido)
                    if info:
                        lotes_para_processar.append(info)
                        lotes_processados.add(pedido.separacao_lote_id)
            
            # 3. Buscar EmbarqueItems órfãos (sem separacao_lote_id mas com NF)
            logger.info("🔍 Buscando EmbarqueItems sem lote (via NF)...")
            embarques_sem_lote = db.session.query(EmbarqueItem).filter(
                (EmbarqueItem.separacao_lote_id.is_(None)) | (EmbarqueItem.separacao_lote_id == ''),
                EmbarqueItem.nota_fiscal.isnot(None),
                EmbarqueItem.nota_fiscal != ''
            ).all()
            
            for embarque in embarques_sem_lote:
                # Buscar Pedido pela NF
                pedido = Pedido.query.filter_by(nf=embarque.nota_fiscal).first()
                if pedido and pedido.separacao_lote_id and pedido.separacao_lote_id not in lotes_processados:
                    logger.info(f"  📌 EmbarqueItem órfão encontrado via NF {embarque.nota_fiscal} → Lote: {pedido.separacao_lote_id}")
                    self.stats['lotes_recuperados_via_nf'] += 1
                    
                    info = self._analisar_lote(pedido.separacao_lote_id, pedido_fallback=pedido)
                    if info:
                        info['embarque_para_atualizar'] = embarque.id
                        lotes_para_processar.append(info)
                        lotes_processados.add(pedido.separacao_lote_id)
        
        return lotes_para_processar
    
    def _analisar_lote(self, lote_id: str, pedido_fallback: Optional[Pedido] = None) -> Optional[Dict]:
        """
        Analisa um lote específico e retorna informações sobre ele.
        """
        info = {
            'lote_id': lote_id,
            'tem_separacao': False,
            'separacao_divergente': False,
            'tem_pedido': False,
            'tem_alerta': False,
            'tem_embarque': False,
            'num_pedido': None,
            'pedido_obj': pedido_fallback,
            'produtos_esperados': {},
            'produtos_atuais': {},
            'fonte': None
        }
        
        # Verificar se tem Separacao
        separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()
        if separacoes:
            info['tem_separacao'] = True
            for sep in separacoes:
                info['produtos_atuais'][sep.cod_produto] = {
                    'qtd': float(sep.qtd_saldo or 0),
                    'valor': float(sep.valor_saldo or 0),
                    'peso': float(sep.peso or 0)
                }
        
        # Buscar Pedido
        pedido = pedido_fallback or Pedido.query.filter_by(separacao_lote_id=lote_id).first()
        if pedido:
            info['tem_pedido'] = True
            info['num_pedido'] = pedido.num_pedido
            info['pedido_obj'] = pedido
        
        # Buscar Alertas (produtos esperados)
        alertas = AlertaSeparacaoCotada.query.filter_by(separacao_lote_id=lote_id).all()
        if alertas:
            info['tem_alerta'] = True
            info['fonte'] = 'alertas'
            
            for alerta in alertas:
                if alerta.cod_produto and alerta.cod_produto != 'TODOS':
                    # Usar qtd_nova se disponível, senão qtd_anterior
                    qtd = float(alerta.qtd_nova or alerta.qtd_anterior or 0)
                    if qtd > 0:
                        if alerta.cod_produto not in info['produtos_esperados']:
                            info['produtos_esperados'][alerta.cod_produto] = {
                                'qtd': qtd,
                                'nome': alerta.nome_produto,
                                'fonte': 'alerta'
                            }
                        else:
                            # Manter a maior quantidade
                            if qtd > info['produtos_esperados'][alerta.cod_produto]['qtd']:
                                info['produtos_esperados'][alerta.cod_produto]['qtd'] = qtd
        
        # Se não tem alertas mas tem pedido, buscar produtos da CarteiraPrincipal
        if not info['produtos_esperados'] and pedido:
            carteira_items = CarteiraPrincipal.query.filter_by(
                num_pedido=pedido.num_pedido,
                separacao_lote_id=lote_id
            ).all()
            
            if not carteira_items:
                # Tentar sem separacao_lote_id
                carteira_items = CarteiraPrincipal.query.filter_by(
                    num_pedido=pedido.num_pedido
                ).all()
            
            if carteira_items:
                info['fonte'] = 'carteira'
                for item in carteira_items:
                    qtd = float(item.qtd_saldo if item.qtd_saldo else item.qtd_saldo_produto_pedido)
                    if qtd > 0:
                        info['produtos_esperados'][item.cod_produto] = {
                            'qtd': qtd,
                            'nome': item.nome_produto,
                            'fonte': 'carteira'
                        }
        
        # Buscar EmbarqueItem
        embarque = EmbarqueItem.query.filter_by(separacao_lote_id=lote_id).first()
        if embarque:
            info['tem_embarque'] = True
        
        # Validar divergências
        if info['tem_separacao'] and info['produtos_esperados']:
            info['separacao_divergente'] = self._verificar_divergencia(
                info['produtos_atuais'],
                info['produtos_esperados']
            )
        
        # Decidir se precisa processar
        if not info['tem_separacao'] or info['separacao_divergente']:
            return info
        elif not info['produtos_esperados']:
            # Sem dados para validar mas tem separação
            return None
        
        return None
    
    def _verificar_divergencia(self, produtos_atuais: Dict, produtos_esperados: Dict) -> bool:
        """
        Verifica se há divergência entre produtos atuais e esperados.
        """
        # Verificar se todos os produtos esperados existem
        for cod_produto, esperado in produtos_esperados.items():
            if cod_produto not in produtos_atuais:
                logger.warning(f"    ⚠️ Produto {cod_produto} faltando na Separação")
                return True
            
            atual = produtos_atuais[cod_produto]
            # Tolerância de 1% para diferenças de arredondamento
            if abs(atual['qtd'] - esperado['qtd']) > esperado['qtd'] * 0.01:
                logger.warning(f"    ⚠️ Divergência em {cod_produto}: "
                             f"Atual={atual['qtd']:.2f}, Esperado={esperado['qtd']:.2f}")
                return True
        
        # Verificar produtos extras
        for cod_produto in produtos_atuais:
            if cod_produto not in produtos_esperados:
                logger.warning(f"    ⚠️ Produto {cod_produto} extra na Separação (não esperado)")
                # Não considerar como divergência se for quantidade pequena
                if produtos_atuais[cod_produto]['qtd'] > 1:
                    return True
        
        return False
    
    def _processar_lote_com_validacao(self, lote_info: Dict):
        """
        Processa um lote com validação completa.
        """
        lote_id = lote_info['lote_id']
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📦 Processando lote: {lote_id}")
        self.stats['lotes_processados'] += 1
        
        # Status do lote
        if lote_info['tem_separacao']:
            if lote_info['separacao_divergente']:
                logger.warning(f"⚠️ Lote com Separação DIVERGENTE - será reconstruído")
                self.stats['separacoes_divergentes'] += 1
                # Deletar separações divergentes
                Separacao.query.filter_by(separacao_lote_id=lote_id).delete()
                db.session.flush()
            else:
                logger.info(f"✅ Lote já tem Separação válida - pulando")
                self.stats['separacoes_validadas'] += 1
                self.stats['lotes_ja_existentes'] += 1
                return
        else:
            logger.warning(f"🔴 Lote SEM Separação - será reconstruído")
        
        # Coletar dados completos
        dados = self._coletar_dados_completos(lote_id, lote_info)
        
        if not dados['produtos']:
            logger.error(f"❌ Sem dados de produtos para reconstruir")
            self.stats['lotes_sem_dados'] += 1
            return
        
        # Criar Separações
        itens_criados = self._criar_separacoes_validadas(lote_id, dados)
        
        if itens_criados > 0:
            logger.info(f"✅ Lote reconstruído com {itens_criados} itens")
            self.stats['lotes_reconstruidos'] += 1
            self.stats['itens_criados'] += itens_criados
            
            # Atualizar EmbarqueItem se necessário
            if lote_info.get('embarque_para_atualizar'):
                embarque = EmbarqueItem.query.get(lote_info['embarque_para_atualizar'])
                if embarque:
                    embarque.separacao_lote_id = lote_id
                    logger.info(f"  ✅ EmbarqueItem atualizado com lote {lote_id}")
                    self.stats['embarques_atualizados'] += 1
    
    def _coletar_dados_completos(self, lote_id: str, lote_info: Dict) -> Dict:
        """
        Coleta dados de todas as fontes disponíveis com priorização.
        """
        dados = {
            'pedido': lote_info.get('pedido_obj'),
            'produtos': {},
            'fonte_principal': None
        }
        
        pedido = dados['pedido']
        
        # 1. PRIORIDADE 1: FaturamentoProduto (mais confiável)
        if pedido:
            faturamentos = FaturamentoProduto.query.filter_by(
                origem=pedido.num_pedido,
                status_nf='Lançado'
            ).all()
            
            if faturamentos:
                logger.info(f"  ✓ {len(faturamentos)} produtos no FaturamentoProduto")
                dados['fonte_principal'] = 'faturamento'
                self.stats['usando_faturamento'] += 1
                
                for fat in faturamentos:
                    peso_bruto = self._obter_peso_bruto(fat.cod_produto)
                    peso_total = float(fat.qtd_produto_faturado) * peso_bruto
                    
                    dados['produtos'][fat.cod_produto] = {
                        'nome': fat.nome_produto,
                        'qtd': float(fat.qtd_produto_faturado),
                        'valor': float(fat.valor_produto_faturado),
                        'peso': peso_total,
                        'peso_bruto': peso_bruto,
                        'fonte': 'faturamento'
                    }
        
        # 2. PRIORIDADE 2: Produtos esperados (Alertas ou Carteira)
        if not dados['produtos'] and lote_info.get('produtos_esperados'):
            logger.info(f"  ✓ Usando {len(lote_info['produtos_esperados'])} produtos de {lote_info.get('fonte', 'fonte desconhecida')}")
            dados['fonte_principal'] = lote_info.get('fonte', 'alertas')
            
            if dados['fonte_principal'] == 'alertas':
                self.stats['usando_alertas'] += 1
            else:
                self.stats['usando_carteira'] += 1
            
            for cod_produto, info in lote_info['produtos_esperados'].items():
                peso_bruto = self._obter_peso_bruto(cod_produto)
                
                # Tentar obter valor da CarteiraPrincipal
                valor = 0
                if pedido:
                    carteira_item = CarteiraPrincipal.query.filter_by(
                        num_pedido=pedido.num_pedido,
                        cod_produto=cod_produto
                    ).first()
                    if carteira_item:
                        valor = float(carteira_item.valor_saldo or 0)
                        if valor == 0 and carteira_item.preco_produto_pedido:
                            valor = info['qtd'] * float(carteira_item.preco_produto_pedido)
                
                dados['produtos'][cod_produto] = {
                    'nome': info.get('nome', f'Produto {cod_produto}'),
                    'qtd': info['qtd'],
                    'valor': valor,
                    'peso': info['qtd'] * peso_bruto,
                    'peso_bruto': peso_bruto,
                    'fonte': info.get('fonte', 'alerta')
                }
        
        # 3. FALLBACK: CarteiraPrincipal diretamente
        if not dados['produtos'] and pedido:
            carteira_items = CarteiraPrincipal.query.filter_by(
                num_pedido=pedido.num_pedido
            ).all()
            
            if carteira_items:
                logger.info(f"  ✓ {len(carteira_items)} produtos na CarteiraPrincipal (fallback)")
                dados['fonte_principal'] = 'carteira'
                self.stats['usando_carteira'] += 1
                
                for item in carteira_items:
                    qtd = float(item.qtd_saldo if item.qtd_saldo else item.qtd_saldo_produto_pedido)
                    if qtd > 0:
                        peso_bruto = self._obter_peso_bruto(item.cod_produto)
                        valor_total = float(item.valor_saldo or 0)
                        if valor_total == 0 and item.preco_produto_pedido:
                            valor_total = qtd * float(item.preco_produto_pedido)
                        
                        dados['produtos'][item.cod_produto] = {
                            'nome': item.nome_produto,
                            'qtd': qtd,
                            'valor': valor_total,
                            'peso': qtd * peso_bruto,
                            'peso_bruto': peso_bruto,
                            'fonte': 'carteira'
                        }
        
        # Resumo dos dados
        if dados['produtos']:
            self._exibir_resumo_dados(dados)
        
        return dados
    
    def _obter_peso_bruto(self, cod_produto: str) -> float:
        """
        Obtém o peso bruto do produto do CadastroPalletizacao.
        """
        palletizacao = CadastroPalletizacao.query.filter_by(
            cod_produto=cod_produto
        ).first()
        
        if palletizacao and palletizacao.peso_bruto:
            return float(palletizacao.peso_bruto)
        return 1.0  # Padrão
    
    def _exibir_resumo_dados(self, dados: Dict):
        """
        Exibe resumo dos dados coletados.
        """
        logger.info(f"  📊 Total de produtos: {len(dados['produtos'])}")
        logger.info(f"  📊 Fonte principal: {dados['fonte_principal']}")
        
        total_qtd = sum(p['qtd'] for p in dados['produtos'].values())
        total_valor = sum(p['valor'] for p in dados['produtos'].values())
        total_peso = sum(p['peso'] for p in dados['produtos'].values())
        
        logger.info(f"  📊 Totais: Qtd={total_qtd:.2f}, Valor=R${total_valor:.2f}, Peso={total_peso:.2f}kg")
    
    def _criar_separacoes_validadas(self, lote_id: str, dados: Dict) -> int:
        """
        Cria as Separações com validação completa.
        """
        pedido = dados['pedido']
        itens_criados = 0
        
        if not pedido:
            logger.error("  ❌ Sem dados do pedido para criar Separação")
            return 0
        
        # Dados do pedido
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
            if palletizacao and palletizacao.palletizacao and palletizacao.palletizacao > 0:
                qtd_pallets = info['qtd'] / float(palletizacao.palletizacao)
            
            # Criar Separacao
            nova_separacao = Separacao(
                # Identificação - MANTÉM O LOTE ORIGINAL
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
                peso=info['peso'],
                pallet=qtd_pallets,
                
                # Operacional
                tipo_envio='total',
                observ_ped_1=f'Reconstruído via {info["fonte"]} em {datetime.now().strftime("%Y-%m-%d %H:%M")}',
                
                # Transportadora
                roteirizacao=pedido.transportadora if hasattr(pedido, 'transportadora') and pedido.transportadora else None,
                
                # Timestamps
                criado_em=datetime.utcnow()
            )
            
            db.session.add(nova_separacao)
            itens_criados += 1
            
            logger.info(f"    ✅ {cod_produto}: {info['qtd']:.2f} un | "
                       f"R$ {info['valor']:.2f} | {info['peso']:.2f} kg | "
                       f"Fonte: {info['fonte']}")
        
        return itens_criados
    
    def _atualizar_embarque_items_sem_lote(self):
        """
        Atualiza EmbarqueItems que perderam o separacao_lote_id usando NF como referência.
        """
        logger.info("\n📋 Atualizando EmbarqueItems sem separacao_lote_id...")
        
        # Buscar EmbarqueItems sem lote mas com NF
        embarques_sem_lote = db.session.query(EmbarqueItem).filter(
            (EmbarqueItem.separacao_lote_id.is_(None)) | (EmbarqueItem.separacao_lote_id == ''),
            EmbarqueItem.nota_fiscal.isnot(None),
            EmbarqueItem.nota_fiscal != ''
        ).all()
        
        if not embarques_sem_lote:
            logger.info("  ✓ Todos os EmbarqueItems têm separacao_lote_id")
            return
        
        logger.info(f"  🔍 {len(embarques_sem_lote)} EmbarqueItems sem lote encontrados")
        
        for embarque in embarques_sem_lote:
            # Buscar Pedido pela NF
            pedido = Pedido.query.filter_by(nf=embarque.nota_fiscal).first()
            
            if pedido and pedido.separacao_lote_id:
                # Verificar se existe Separacao para este lote
                separacao_existe = Separacao.query.filter_by(
                    separacao_lote_id=pedido.separacao_lote_id
                ).first() is not None
                
                if separacao_existe:
                    embarque.separacao_lote_id = pedido.separacao_lote_id
                    logger.info(f"    ✅ EmbarqueItem ID {embarque.id} atualizado: "
                              f"NF {embarque.nota_fiscal} → Lote {pedido.separacao_lote_id}")
                    self.stats['embarques_atualizados'] += 1
                else:
                    logger.warning(f"    ⚠️ EmbarqueItem ID {embarque.id}: "
                                 f"Lote {pedido.separacao_lote_id} não tem Separação")
            else:
                # Tentar buscar pelo número do pedido
                if embarque.pedido:
                    pedido_alt = Pedido.query.filter_by(num_pedido=embarque.pedido).first()
                    if pedido_alt and pedido_alt.separacao_lote_id:
                        separacao_existe = Separacao.query.filter_by(
                            separacao_lote_id=pedido_alt.separacao_lote_id
                        ).first() is not None
                        
                        if separacao_existe:
                            embarque.separacao_lote_id = pedido_alt.separacao_lote_id
                            logger.info(f"    ✅ EmbarqueItem ID {embarque.id} atualizado via pedido: "
                                      f"Pedido {embarque.pedido} → Lote {pedido_alt.separacao_lote_id}")
                            self.stats['embarques_atualizados'] += 1
    
    def _exibir_estatisticas(self):
        """Exibe as estatísticas finais detalhadas."""
        logger.info("\n" + "="*70)
        logger.info("📊 ESTATÍSTICAS DA RECONSTRUÇÃO COM FALLBACK")
        logger.info("="*70)
        
        logger.info(f"\n📋 PROCESSAMENTO:")
        logger.info(f"  • Lotes processados: {self.stats['lotes_processados']}")
        logger.info(f"  • Lotes reconstruídos: {self.stats['lotes_reconstruidos']}")
        logger.info(f"  • Lotes já existentes: {self.stats['lotes_ja_existentes']}")
        logger.info(f"  • Lotes sem dados: {self.stats['lotes_sem_dados']}")
        
        logger.info(f"\n✅ VALIDAÇÕES:")
        logger.info(f"  • Separações validadas: {self.stats['separacoes_validadas']}")
        logger.info(f"  • Separações divergentes: {self.stats['separacoes_divergentes']}")
        
        logger.info(f"\n🔄 RECUPERAÇÕES VIA FALLBACK:")
        logger.info(f"  • Lotes recuperados via Pedido: {self.stats['lotes_recuperados_via_pedido']}")
        logger.info(f"  • Lotes recuperados via NF: {self.stats['lotes_recuperados_via_nf']}")
        logger.info(f"  • EmbarqueItems atualizados: {self.stats['embarques_atualizados']}")
        
        logger.info(f"\n📦 ITENS CRIADOS:")
        logger.info(f"  • Total de itens: {self.stats['itens_criados']}")
        
        logger.info(f"\n📊 FONTES DE DADOS:")
        logger.info(f"  • FaturamentoProduto: {self.stats['usando_faturamento']} lotes")
        logger.info(f"  • CarteiraPrincipal: {self.stats['usando_carteira']} lotes")
        logger.info(f"  • Alertas: {self.stats['usando_alertas']} lotes")
        
        if self.stats['lotes_reconstruidos'] > 0 or self.stats['embarques_atualizados'] > 0:
            logger.info(f"\n✅ SUCESSO: {self.stats['lotes_reconstruidos']} lotes reconstruídos, "
                       f"{self.stats['embarques_atualizados']} embarques atualizados!")
        else:
            logger.info("\n⚠️ Nenhuma alteração foi necessária")

def listar_lotes_problematicos():
    """Lista todos os lotes com problemas."""
    app = create_app()
    
    with app.app_context():
        logger.info("\n" + "="*70)
        logger.info("📋 ANÁLISE DE LOTES PROBLEMÁTICOS")
        logger.info("="*70)
        
        # 1. Pedidos com lote mas sem Separacao
        pedidos_sem_sep = db.session.query(Pedido).filter(
            Pedido.separacao_lote_id.isnot(None),
            ~db.exists().where(
                Separacao.separacao_lote_id == Pedido.separacao_lote_id
            )
        ).all()
        
        if pedidos_sem_sep:
            logger.info(f"\n🔴 {len(pedidos_sem_sep)} Pedidos com lote mas SEM Separação:")
            for pedido in pedidos_sem_sep[:10]:
                logger.info(f"  • Lote: {pedido.separacao_lote_id} | "
                          f"Pedido: {pedido.num_pedido} | "
                          f"Status: {pedido.status} | "
                          f"NF: {pedido.nf or 'Sem NF'}")
        
        # 2. EmbarqueItems sem separacao_lote_id
        embarques_sem_lote = db.session.query(EmbarqueItem).filter(
            (EmbarqueItem.separacao_lote_id.is_(None)) | (EmbarqueItem.separacao_lote_id == '')
        ).all()
        
        if embarques_sem_lote:
            logger.info(f"\n🟡 {len(embarques_sem_lote)} EmbarqueItems SEM separacao_lote_id:")
            for item in embarques_sem_lote[:10]:
                logger.info(f"  • ID: {item.id} | "
                          f"Pedido: {item.pedido} | "
                          f"NF: {item.nota_fiscal} | "
                          f"Cliente: {item.cliente}")
        
        # 3. Separações órfãs (sem Pedido correspondente)
        separacoes_orfas = db.session.query(Separacao).filter(
            ~db.exists().where(
                Pedido.separacao_lote_id == Separacao.separacao_lote_id
            )
        ).all()
        
        if separacoes_orfas:
            logger.info(f"\n🟠 {len(separacoes_orfas)} Separações órfãs (sem Pedido):")
            lotes_unicos = set()
            for sep in separacoes_orfas:
                lotes_unicos.add(sep.separacao_lote_id)
            for lote in list(lotes_unicos)[:10]:
                logger.info(f"  • Lote órfão: {lote}")
        
        # 4. Alertas com lote sem Separação
        alertas_sem_sep = db.session.query(
            AlertaSeparacaoCotada.separacao_lote_id,
            db.func.count(AlertaSeparacaoCotada.id).label('total')
        ).filter(
            AlertaSeparacaoCotada.separacao_lote_id.isnot(None),
            ~db.exists().where(
                Separacao.separacao_lote_id == AlertaSeparacaoCotada.separacao_lote_id
            )
        ).group_by(AlertaSeparacaoCotada.separacao_lote_id).all()
        
        if alertas_sem_sep:
            logger.info(f"\n🔵 {len(alertas_sem_sep)} lotes com Alertas mas SEM Separação:")
            for lote_id, total in alertas_sem_sep[:10]:
                logger.info(f"  • Lote: {lote_id} | {total} alertas")
        
        # Resumo
        total_problemas = (
            len(pedidos_sem_sep) + 
            len(embarques_sem_lote) + 
            len(separacoes_orfas) + 
            len(alertas_sem_sep)
        )
        
        if total_problemas > 0:
            logger.info(f"\n⚠️ TOTAL DE PROBLEMAS ENCONTRADOS: {total_problemas}")
            logger.info("Use --confirmar para corrigir automaticamente")
        else:
            logger.info("\n✅ Nenhum problema encontrado!")

def main():
    """Função principal."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Reconstruir Separações com fallback robusto via Pedido e NF'
    )
    parser.add_argument(
        '--listar', 
        action='store_true',
        help='Listar lotes problemáticos'
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
            listar_lotes_problematicos()
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


'''INFO:app.claude_ai.auto_command_processor:🤖 Auto Command Processor inicializado
13:40:43 | INFO     | app.claude_ai.auto_command_processor | 🤖 Auto Command Processor inicializado
INFO:app:🤖 Processador automático de comandos inicializado
13:40:43 | INFO     | app | 🤖 Processador automático de comandos inicializado
INFO:app.claude_ai.claude_code_generator:🚀 Claude Code Generator inicializado: /opt/render/project/src/app
13:40:43 | INFO     | app.claude_ai.claude_code_generator | 🚀 Claude Code Generator inicializado: /opt/render/project/src/app
INFO:app:🚀 Gerador de código Claude AI inicializado
13:40:43 | INFO     | app | 🚀 Gerador de código Claude AI inicializado
INFO:app.estoque.triggers_sql_corrigido:✅ Triggers SQL corrigidos ativados com sucesso
13:40:43 | INFO     | app.estoque.triggers_sql_corrigido | ✅ Triggers SQL corrigidos ativados com sucesso
INFO:app:✅ Triggers SQL corrigidos do EstoqueTempoReal registrados com sucesso
13:40:43 | INFO     | app | ✅ Triggers SQL corrigidos do EstoqueTempoReal registrados com sucesso
INFO:app:✅ API de Estoque Tempo Real registrada
13:40:43 | INFO     | app | ✅ API de Estoque Tempo Real registrada
INFO:apscheduler.scheduler:Adding job tentatively -- it will be properly scheduled when the scheduler starts
13:40:43 | INFO     | apscheduler.scheduler | Adding job tentatively -- it will be properly scheduled when the scheduler starts
INFO:apscheduler.scheduler:Added job "create_app.<locals>.<lambda>" to job store "default"
13:40:43 | INFO     | apscheduler.scheduler | Added job "create_app.<locals>.<lambda>" to job store "default"
INFO:apscheduler.scheduler:Scheduler started
13:40:43 | INFO     | apscheduler.scheduler | Scheduler started
INFO:app:✅ Job de Fallback de Estoque configurado (60 segundos)
13:40:43 | INFO     | app | ✅ Job de Fallback de Estoque configurado (60 segundos)
INFO:__main__:======================================================================
13:40:43 | INFO     | __main__ | ======================================================================
INFO:__main__:🔧 RECONSTRUÇÃO MELHORADA DE SEPARAÇÕES COM FALLBACK ROBUSTO
13:40:43 | INFO     | __main__ | 🔧 RECONSTRUÇÃO MELHORADA DE SEPARAÇÕES COM FALLBACK ROBUSTO
INFO:__main__:======================================================================
13:40:43 | INFO     | __main__ | ======================================================================
INFO:__main__:🔍 Buscando lotes em Alertas...
13:40:43 | INFO     | __main__ | 🔍 Buscando lotes em Alertas...
WARNING:__main__:    ⚠️ Produto 4100161 faltando na Separação
13:40:43 | WARNING  | __main__ |     ⚠️ Produto 4100161 faltando na Separação
WARNING:__main__:    ⚠️ Produto 4360147 faltando na Separação
13:40:43 | WARNING  | __main__ |     ⚠️ Produto 4360147 faltando na Separação
WARNING:__main__:    ⚠️ Produto 4510162 faltando na Separação
13:40:43 | WARNING  | __main__ |     ⚠️ Produto 4510162 faltando na Separação
WARNING:__main__:    ⚠️ Produto 4870146 faltando na Separação
13:40:43 | WARNING  | __main__ |     ⚠️ Produto 4870146 faltando na Separação
WARNING:__main__:    ⚠️ Produto 4210165 faltando na Separação
13:40:43 | WARNING  | __main__ |     ⚠️ Produto 4210165 faltando na Separação
WARNING:__main__:    ⚠️ Produto 4360162 faltando na Separação
13:40:43 | WARNING  | __main__ |     ⚠️ Produto 4360162 faltando na Separação
WARNING:__main__:    ⚠️ Produto 4080156 faltando na Separação
13:40:43 | WARNING  | __main__ |     ⚠️ Produto 4080156 faltando na Separação
WARNING:__main__:    ⚠️ Produto 4080156 faltando na Separação
13:40:43 | WARNING  | __main__ |     ⚠️ Produto 4080156 faltando na Separação
WARNING:__main__:    ⚠️ Produto 4080156 faltando na Separação
13:40:43 | WARNING  | __main__ |     ⚠️ Produto 4080156 faltando na Separação
WARNING:__main__:    ⚠️ Produto 4070162 faltando na Separação
13:40:43 | WARNING  | __main__ |     ⚠️ Produto 4070162 faltando na Separação
WARNING:__main__:    ⚠️ Produto 4050176 faltando na Separação
13:40:43 | WARNING  | __main__ |     ⚠️ Produto 4050176 faltando na Separação
WARNING:__main__:    ⚠️ Produto 4050176 faltando na Separação
13:40:43 | WARNING  | __main__ |     ⚠️ Produto 4050176 faltando na Separação
WARNING:__main__:    ⚠️ Produto 4070162 faltando na Separação
13:40:43 | WARNING  | __main__ |     ⚠️ Produto 4070162 faltando na Separação
WARNING:__main__:    ⚠️ Produto 4320147 faltando na Separação
13:40:43 | WARNING  | __main__ |     ⚠️ Produto 4320147 faltando na Separação
INFO:__main__:🔍 Buscando Pedidos órfãos (sem Separação correspondente)...
13:40:43 | INFO     | __main__ | 🔍 Buscando Pedidos órfãos (sem Separação correspondente)...
INFO:__main__:  📌 Pedido órfão encontrado: VCD2521224 (Lote: LOTE_20250808_034538_384)
13:40:43 | INFO     | __main__ |   📌 Pedido órfão encontrado: VCD2521224 (Lote: LOTE_20250808_034538_384)
INFO:__main__:  📌 Pedido órfão encontrado: VCD2521491 (Lote: LOTE_20250808_194054_398)
13:40:43 | INFO     | __main__ |   📌 Pedido órfão encontrado: VCD2521491 (Lote: LOTE_20250808_194054_398)
INFO:__main__:  📌 Pedido órfão encontrado: VCD2521086 (Lote: LOTE_20250811_140846_758)
13:40:43 | INFO     | __main__ |   📌 Pedido órfão encontrado: VCD2521086 (Lote: LOTE_20250811_140846_758)
INFO:__main__:  📌 Pedido órfão encontrado: VCD2521073 (Lote: LOTE_20250811_140907_061)
13:40:43 | INFO     | __main__ |   📌 Pedido órfão encontrado: VCD2521073 (Lote: LOTE_20250811_140907_061)
INFO:__main__:  📌 Pedido órfão encontrado: VCD2521077 (Lote: LOTE_20250811_140923_592)
13:40:43 | INFO     | __main__ |   📌 Pedido órfão encontrado: VCD2521077 (Lote: LOTE_20250811_140923_592)
INFO:__main__:  📌 Pedido órfão encontrado: VCD2521114 (Lote: LOTE_20250811_140931_636)
13:40:43 | INFO     | __main__ |   📌 Pedido órfão encontrado: VCD2521114 (Lote: LOTE_20250811_140931_636)
INFO:__main__:  📌 Pedido órfão encontrado: VCD2521080 (Lote: LOTE_20250811_140957_676)
13:40:43 | INFO     | __main__ |   📌 Pedido órfão encontrado: VCD2521080 (Lote: LOTE_20250811_140957_676)
INFO:__main__:  📌 Pedido órfão encontrado: VCD2521105 (Lote: LOTE_20250811_141005_038)
13:40:43 | INFO     | __main__ |   📌 Pedido órfão encontrado: VCD2521105 (Lote: LOTE_20250811_141005_038)
INFO:__main__:  📌 Pedido órfão encontrado: VCD2520309 (Lote: LOTE_23B29D1B)
13:40:43 | INFO     | __main__ |   📌 Pedido órfão encontrado: VCD2520309 (Lote: LOTE_23B29D1B)
INFO:__main__:  📌 Pedido órfão encontrado: VCD2520214 (Lote: LOTE_5BB46EE6)
13:40:43 | INFO     | __main__ |   📌 Pedido órfão encontrado: VCD2520214 (Lote: LOTE_5BB46EE6)
INFO:__main__:  📌 Pedido órfão encontrado: VCD2520562 (Lote: LOTE_AEA24966)
13:40:43 | INFO     | __main__ |   📌 Pedido órfão encontrado: VCD2520562 (Lote: LOTE_AEA24966)
INFO:__main__:  📌 Pedido órfão encontrado: VCD2520411 (Lote: LOTE_C4D3F191)
13:40:43 | INFO     | __main__ |   📌 Pedido órfão encontrado: VCD2520411 (Lote: LOTE_C4D3F191)
INFO:__main__:  📌 Pedido órfão encontrado: VCD2520355 (Lote: LOTE_F7E2EB60)
13:40:43 | INFO     | __main__ |   📌 Pedido órfão encontrado: VCD2520355 (Lote: LOTE_F7E2EB60)
INFO:__main__:🔍 Buscando EmbarqueItems sem lote (via NF)...
13:40:43 | INFO     | __main__ | 🔍 Buscando EmbarqueItems sem lote (via NF)...
INFO:__main__:📋 38 lotes encontrados para análise
13:40:43 | INFO     | __main__ | 📋 38 lotes encontrados para análise
INFO:__main__:
============================================================
13:40:43 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250807_142223_692
13:40:43 | INFO     | __main__ | 📦 Processando lote: LOTE_20250807_142223_692
WARNING:__main__:⚠️ Lote com Separação DIVERGENTE - será reconstruído
13:40:43 | WARNING  | __main__ | ⚠️ Lote com Separação DIVERGENTE - será reconstruído
INFO:__main__:  ✓ Usando 15 produtos de alertas
13:40:43 | INFO     | __main__ |   ✓ Usando 15 produtos de alertas
INFO:__main__:  📊 Total de produtos: 15
13:40:43 | INFO     | __main__ |   📊 Total de produtos: 15
INFO:__main__:  📊 Fonte principal: alertas
13:40:43 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=954.00, Valor=R$4096.00, Peso=19547.84kg
13:40:43 | INFO     | __main__ |   📊 Totais: Qtd=954.00, Valor=R$4096.00, Peso=19547.84kg
INFO:__main__:    ✅ 4100161: 20.00 un | R$ 0.00 | 268.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4100161: 20.00 un | R$ 0.00 | 268.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4230162: 10.00 un | R$ 0.00 | 210.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4230162: 10.00 un | R$ 0.00 | 210.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4520161: 20.00 un | R$ 0.00 | 268.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4520161: 20.00 un | R$ 0.00 | 268.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4360162: 20.00 un | R$ 0.00 | 420.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4360162: 20.00 un | R$ 0.00 | 420.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4510161: 20.00 un | R$ 0.00 | 268.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4510161: 20.00 un | R$ 0.00 | 268.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4040162: 8.00 un | R$ 0.00 | 168.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4040162: 8.00 un | R$ 0.00 | 168.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4310164: 350.00 un | R$ 0.00 | 7350.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4310164: 350.00 un | R$ 0.00 | 7350.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4350162: 20.00 un | R$ 0.00 | 420.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4350162: 20.00 un | R$ 0.00 | 420.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4320162: 360.00 un | R$ 0.00 | 7560.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4320162: 360.00 un | R$ 0.00 | 7560.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4210165: 10.00 un | R$ 0.00 | 210.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4210165: 10.00 un | R$ 0.00 | 210.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4070162: 20.00 un | R$ 0.00 | 420.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4070162: 20.00 un | R$ 0.00 | 420.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4520162: 10.00 un | R$ 0.00 | 210.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4520162: 10.00 un | R$ 0.00 | 210.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4050162: 60.00 un | R$ 0.00 | 1260.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4050162: 60.00 un | R$ 0.00 | 1260.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4080162: 10.00 un | R$ 0.00 | 210.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4080162: 10.00 un | R$ 0.00 | 210.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4759699: 16.00 un | R$ 4096.00 | 305.84 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4759699: 16.00 un | R$ 4096.00 | 305.84 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 15 itens
13:40:43 | INFO     | __main__ | ✅ Lote reconstruído com 15 itens
INFO:__main__:
============================================================
13:40:43 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250808_034121_469
13:40:43 | INFO     | __main__ | 📦 Processando lote: LOTE_20250808_034121_469
WARNING:__main__:⚠️ Lote com Separação DIVERGENTE - será reconstruído
13:40:43 | WARNING  | __main__ | ⚠️ Lote com Separação DIVERGENTE - será reconstruído
INFO:__main__:  ✓ Usando 4 produtos de alertas
13:40:43 | INFO     | __main__ |   ✓ Usando 4 produtos de alertas
INFO:__main__:  📊 Total de produtos: 4
13:40:43 | INFO     | __main__ |   📊 Total de produtos: 4
INFO:__main__:  📊 Fonte principal: alertas
13:40:43 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=25.00, Valor=R$0.00, Peso=143.08kg
13:40:43 | INFO     | __main__ |   📊 Totais: Qtd=25.00, Valor=R$0.00, Peso=143.08kg
INFO:__main__:    ✅ 4360147: 5.00 un | R$ 0.00 | 27.30 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4360147: 5.00 un | R$ 0.00 | 27.30 kg | Fonte: alerta
INFO:__main__:    ✅ 4510173: 4.00 un | R$ 0.00 | 27.76 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4510173: 4.00 un | R$ 0.00 | 27.76 kg | Fonte: alerta
INFO:__main__:    ✅ 4510145: 6.00 un | R$ 0.00 | 33.42 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4510145: 6.00 un | R$ 0.00 | 33.42 kg | Fonte: alerta
INFO:__main__:    ✅ 4320147: 10.00 un | R$ 0.00 | 54.60 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4320147: 10.00 un | R$ 0.00 | 54.60 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 4 itens
13:40:43 | INFO     | __main__ | ✅ Lote reconstruído com 4 itens
INFO:__main__:
============================================================
13:40:43 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250808_195315_979
13:40:43 | INFO     | __main__ | 📦 Processando lote: LOTE_20250808_195315_979
WARNING:__main__:⚠️ Lote com Separação DIVERGENTE - será reconstruído
13:40:43 | WARNING  | __main__ | ⚠️ Lote com Separação DIVERGENTE - será reconstruído
INFO:__main__:  ✓ Usando 2 produtos de alertas
13:40:43 | INFO     | __main__ |   ✓ Usando 2 produtos de alertas
INFO:__main__:  📊 Total de produtos: 2
13:40:43 | INFO     | __main__ |   📊 Total de produtos: 2
INFO:__main__:  📊 Fonte principal: alertas
13:40:43 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=6.00, Valor=R$0.00, Peso=126.00kg
13:40:43 | INFO     | __main__ |   📊 Totais: Qtd=6.00, Valor=R$0.00, Peso=126.00kg
INFO:__main__:    ✅ 4510162: 2.00 un | R$ 0.00 | 42.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4510162: 2.00 un | R$ 0.00 | 42.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4230162: 4.00 un | R$ 0.00 | 84.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4230162: 4.00 un | R$ 0.00 | 84.00 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 2 itens
13:40:43 | INFO     | __main__ | ✅ Lote reconstruído com 2 itens
INFO:__main__:
============================================================
13:40:43 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250811_134048_814
13:40:43 | INFO     | __main__ | 📦 Processando lote: LOTE_20250811_134048_814
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:43 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
INFO:__main__:  ✓ Usando 7 produtos de alertas
13:40:43 | INFO     | __main__ |   ✓ Usando 7 produtos de alertas
INFO:__main__:  📊 Total de produtos: 7
13:40:43 | INFO     | __main__ |   📊 Total de produtos: 7
INFO:__main__:  📊 Fonte principal: alertas
13:40:43 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=21.00, Valor=R$0.00, Peso=254.02kg
13:40:43 | INFO     | __main__ |   📊 Totais: Qtd=21.00, Valor=R$0.00, Peso=254.02kg
INFO:__main__:    ✅ 4520145: 2.00 un | R$ 0.00 | 11.14 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4520145: 2.00 un | R$ 0.00 | 11.14 kg | Fonte: alerta
INFO:__main__:    ✅ 4310145: 2.00 un | R$ 0.00 | 11.14 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4310145: 2.00 un | R$ 0.00 | 11.14 kg | Fonte: alerta
INFO:__main__:    ✅ 4510145: 2.00 un | R$ 0.00 | 11.14 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4510145: 2.00 un | R$ 0.00 | 11.14 kg | Fonte: alerta
INFO:__main__:    ✅ 4320156: 1.00 un | R$ 0.00 | 10.20 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4320156: 1.00 un | R$ 0.00 | 10.20 kg | Fonte: alerta
INFO:__main__:    ✅ 4759698: 6.00 un | R$ 0.00 | 57.60 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4759698: 6.00 un | R$ 0.00 | 57.60 kg | Fonte: alerta
INFO:__main__:    ✅ 4510161: 2.00 un | R$ 0.00 | 26.80 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4510161: 2.00 un | R$ 0.00 | 26.80 kg | Fonte: alerta
INFO:__main__:    ✅ 4310164: 6.00 un | R$ 0.00 | 126.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4310164: 6.00 un | R$ 0.00 | 126.00 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 7 itens
13:40:43 | INFO     | __main__ | ✅ Lote reconstruído com 7 itens
INFO:__main__:
============================================================
13:40:43 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250811_142606_640
13:40:43 | INFO     | __main__ | 📦 Processando lote: LOTE_20250811_142606_640
WARNING:__main__:⚠️ Lote com Separação DIVERGENTE - será reconstruído
13:40:43 | WARNING  | __main__ | ⚠️ Lote com Separação DIVERGENTE - será reconstruído
INFO:__main__:  ✓ Usando 8 produtos de alertas
13:40:43 | INFO     | __main__ |   ✓ Usando 8 produtos de alertas
INFO:__main__:  📊 Total de produtos: 8
13:40:43 | INFO     | __main__ |   📊 Total de produtos: 8
INFO:__main__:  📊 Fonte principal: alertas
13:40:43 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=170.00, Valor=R$0.00, Peso=549.29kg
13:40:43 | INFO     | __main__ |   📊 Totais: Qtd=170.00, Valor=R$0.00, Peso=549.29kg
INFO:__main__:    ✅ 4870146: 35.00 un | R$ 0.00 | 71.75 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4870146: 35.00 un | R$ 0.00 | 71.75 kg | Fonte: alerta
INFO:__main__:    ✅ 4840176: 30.00 un | R$ 0.00 | 80.40 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4840176: 30.00 un | R$ 0.00 | 80.40 kg | Fonte: alerta
INFO:__main__:    ✅ 4870112: 10.00 un | R$ 0.00 | 140.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4870112: 10.00 un | R$ 0.00 | 140.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4810146: 25.00 un | R$ 0.00 | 51.25 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4810146: 25.00 un | R$ 0.00 | 51.25 kg | Fonte: alerta
INFO:__main__:    ✅ 4880176: 20.00 un | R$ 0.00 | 53.60 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4880176: 20.00 un | R$ 0.00 | 53.60 kg | Fonte: alerta
INFO:__main__:    ✅ 4860146: 35.00 un | R$ 0.00 | 71.75 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4860146: 35.00 un | R$ 0.00 | 71.75 kg | Fonte: alerta
INFO:__main__:    ✅ 4080178: 1.00 un | R$ 0.00 | 12.50 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4080178: 1.00 un | R$ 0.00 | 12.50 kg | Fonte: alerta
INFO:__main__:    ✅ 4210186: 14.00 un | R$ 0.00 | 68.04 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4210186: 14.00 un | R$ 0.00 | 68.04 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 8 itens
13:40:43 | INFO     | __main__ | ✅ Lote reconstruído com 8 itens
INFO:__main__:
============================================================
13:40:43 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250811_150804_744
13:40:43 | INFO     | __main__ | 📦 Processando lote: LOTE_20250811_150804_744
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:43 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
INFO:__main__:  ✓ Usando 2 produtos de alertas
13:40:43 | INFO     | __main__ |   ✓ Usando 2 produtos de alertas
INFO:__main__:  📊 Total de produtos: 2
13:40:43 | INFO     | __main__ |   📊 Total de produtos: 2
INFO:__main__:  📊 Fonte principal: alertas
13:40:43 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=250.00, Valor=R$0.00, Peso=4303.00kg
13:40:43 | INFO     | __main__ |   📊 Totais: Qtd=250.00, Valor=R$0.00, Peso=4303.00kg
ERROR:__main__:  ❌ Sem dados do pedido para criar Separação
13:40:43 | ERROR    | __main__ |   ❌ Sem dados do pedido para criar Separação
INFO:__main__:
============================================================
13:40:43 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250811_173356_765
13:40:43 | INFO     | __main__ | 📦 Processando lote: LOTE_20250811_173356_765
WARNING:__main__:⚠️ Lote com Separação DIVERGENTE - será reconstruído
13:40:43 | WARNING  | __main__ | ⚠️ Lote com Separação DIVERGENTE - será reconstruído
INFO:__main__:  ✓ Usando 6 produtos de alertas
13:40:43 | INFO     | __main__ |   ✓ Usando 6 produtos de alertas
INFO:__main__:  📊 Total de produtos: 6
13:40:43 | INFO     | __main__ |   📊 Total de produtos: 6
INFO:__main__:  📊 Fonte principal: alertas
13:40:43 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=208.00, Valor=R$0.00, Peso=4155.20kg
13:40:43 | INFO     | __main__ |   📊 Totais: Qtd=208.00, Valor=R$0.00, Peso=4155.20kg
INFO:__main__:    ✅ 4210165: 20.00 un | R$ 0.00 | 420.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4210165: 20.00 un | R$ 0.00 | 420.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4320162: 50.00 un | R$ 0.00 | 1050.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4320162: 50.00 un | R$ 0.00 | 1050.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4360162: 50.00 un | R$ 0.00 | 1050.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4360162: 50.00 un | R$ 0.00 | 1050.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4310164: 60.00 un | R$ 0.00 | 1260.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4310164: 60.00 un | R$ 0.00 | 1260.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4520161: 14.00 un | R$ 0.00 | 187.60 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4520161: 14.00 un | R$ 0.00 | 187.60 kg | Fonte: alerta
INFO:__main__:    ✅ 4510161: 14.00 un | R$ 0.00 | 187.60 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4510161: 14.00 un | R$ 0.00 | 187.60 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 6 itens
13:40:43 | INFO     | __main__ | ✅ Lote reconstruído com 6 itens
INFO:__main__:
============================================================
13:40:43 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250811_173441_549
13:40:43 | INFO     | __main__ | 📦 Processando lote: LOTE_20250811_173441_549
WARNING:__main__:⚠️ Lote com Separação DIVERGENTE - será reconstruído
13:40:43 | WARNING  | __main__ | ⚠️ Lote com Separação DIVERGENTE - será reconstruído
INFO:__main__:  ✓ Usando 2 produtos de alertas
13:40:43 | INFO     | __main__ |   ✓ Usando 2 produtos de alertas
INFO:__main__:  📊 Total de produtos: 2
13:40:43 | INFO     | __main__ |   📊 Total de produtos: 2
INFO:__main__:  📊 Fonte principal: alertas
13:40:43 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=25.00, Valor=R$0.00, Peso=525.00kg
13:40:43 | INFO     | __main__ |   📊 Totais: Qtd=25.00, Valor=R$0.00, Peso=525.00kg
INFO:__main__:    ✅ 4360162: 15.00 un | R$ 0.00 | 315.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4360162: 15.00 un | R$ 0.00 | 315.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4320162: 10.00 un | R$ 0.00 | 210.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4320162: 10.00 un | R$ 0.00 | 210.00 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 2 itens
13:40:43 | INFO     | __main__ | ✅ Lote reconstruído com 2 itens
INFO:__main__:
============================================================
13:40:43 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250812_184659_960
13:40:43 | INFO     | __main__ | 📦 Processando lote: LOTE_20250812_184659_960
WARNING:__main__:⚠️ Lote com Separação DIVERGENTE - será reconstruído
13:40:43 | WARNING  | __main__ | ⚠️ Lote com Separação DIVERGENTE - será reconstruído
INFO:__main__:  ✓ Usando 13 produtos de alertas
13:40:43 | INFO     | __main__ |   ✓ Usando 13 produtos de alertas
INFO:__main__:  📊 Total de produtos: 13
13:40:43 | INFO     | __main__ |   📊 Total de produtos: 13
INFO:__main__:  📊 Fonte principal: alertas
13:40:43 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=139.00, Valor=R$0.00, Peso=1135.13kg
13:40:43 | INFO     | __main__ |   📊 Totais: Qtd=139.00, Valor=R$0.00, Peso=1135.13kg
INFO:__main__:    ✅ 4080156: 5.00 un | R$ 0.00 | 51.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4080156: 5.00 un | R$ 0.00 | 51.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4520171: 5.00 un | R$ 0.00 | 42.90 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4520171: 5.00 un | R$ 0.00 | 42.90 kg | Fonte: alerta
INFO:__main__:    ✅ 4510156: 5.00 un | R$ 0.00 | 51.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4510156: 5.00 un | R$ 0.00 | 51.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4759099: 5.00 un | R$ 0.00 | 95.57 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4759099: 5.00 un | R$ 0.00 | 95.57 kg | Fonte: alerta
INFO:__main__:    ✅ 4080178: 5.00 un | R$ 0.00 | 62.50 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4080178: 5.00 un | R$ 0.00 | 62.50 kg | Fonte: alerta
INFO:__main__:    ✅ 4510171: 3.00 un | R$ 0.00 | 25.74 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4510171: 3.00 un | R$ 0.00 | 25.74 kg | Fonte: alerta
INFO:__main__:    ✅ 4759098: 30.00 un | R$ 0.00 | 288.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4759098: 30.00 un | R$ 0.00 | 288.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4310177: 3.00 un | R$ 0.00 | 47.27 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4310177: 3.00 un | R$ 0.00 | 47.27 kg | Fonte: alerta
INFO:__main__:    ✅ 4510145: 5.00 un | R$ 0.00 | 27.85 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4510145: 5.00 un | R$ 0.00 | 27.85 kg | Fonte: alerta
INFO:__main__:    ✅ 4320147: 60.00 un | R$ 0.00 | 327.60 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4320147: 60.00 un | R$ 0.00 | 327.60 kg | Fonte: alerta
INFO:__main__:    ✅ 4520161: 3.00 un | R$ 0.00 | 40.20 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4520161: 3.00 un | R$ 0.00 | 40.20 kg | Fonte: alerta
INFO:__main__:    ✅ 4070176: 5.00 un | R$ 0.00 | 36.50 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4070176: 5.00 un | R$ 0.00 | 36.50 kg | Fonte: alerta
INFO:__main__:    ✅ 4080154: 5.00 un | R$ 0.00 | 39.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4080154: 5.00 un | R$ 0.00 | 39.00 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 13 itens
13:40:43 | INFO     | __main__ | ✅ Lote reconstruído com 13 itens
INFO:__main__:
============================================================
13:40:43 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250812_184759_586
13:40:43 | INFO     | __main__ | 📦 Processando lote: LOTE_20250812_184759_586
WARNING:__main__:⚠️ Lote com Separação DIVERGENTE - será reconstruído
13:40:43 | WARNING  | __main__ | ⚠️ Lote com Separação DIVERGENTE - será reconstruído
INFO:__main__:  ✓ Usando 11 produtos de alertas
13:40:43 | INFO     | __main__ |   ✓ Usando 11 produtos de alertas
INFO:__main__:  📊 Total de produtos: 11
13:40:43 | INFO     | __main__ |   📊 Total de produtos: 11
INFO:__main__:  📊 Fonte principal: alertas
13:40:43 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=88.00, Valor=R$0.00, Peso=905.41kg
13:40:43 | INFO     | __main__ |   📊 Totais: Qtd=88.00, Valor=R$0.00, Peso=905.41kg
INFO:__main__:    ✅ 4080156: 2.00 un | R$ 0.00 | 20.40 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4080156: 2.00 un | R$ 0.00 | 20.40 kg | Fonte: alerta
INFO:__main__:    ✅ 4520171: 5.00 un | R$ 0.00 | 42.90 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4520171: 5.00 un | R$ 0.00 | 42.90 kg | Fonte: alerta
INFO:__main__:    ✅ 4070162: 2.00 un | R$ 0.00 | 42.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4070162: 2.00 un | R$ 0.00 | 42.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4759099: 5.00 un | R$ 0.00 | 95.57 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4759099: 5.00 un | R$ 0.00 | 95.57 kg | Fonte: alerta
INFO:__main__:    ✅ 4080178: 5.00 un | R$ 0.00 | 62.50 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4080178: 5.00 un | R$ 0.00 | 62.50 kg | Fonte: alerta
INFO:__main__:    ✅ 4759098: 50.00 un | R$ 0.00 | 480.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4759098: 50.00 un | R$ 0.00 | 480.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4360147: 5.00 un | R$ 0.00 | 27.30 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4360147: 5.00 un | R$ 0.00 | 27.30 kg | Fonte: alerta
INFO:__main__:    ✅ 4310176: 3.00 un | R$ 0.00 | 22.44 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4310176: 3.00 un | R$ 0.00 | 22.44 kg | Fonte: alerta
INFO:__main__:    ✅ 4520161: 5.00 un | R$ 0.00 | 67.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4520161: 5.00 un | R$ 0.00 | 67.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4070176: 3.00 un | R$ 0.00 | 21.90 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4070176: 3.00 un | R$ 0.00 | 21.90 kg | Fonte: alerta
INFO:__main__:    ✅ 4080154: 3.00 un | R$ 0.00 | 23.40 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4080154: 3.00 un | R$ 0.00 | 23.40 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 11 itens
13:40:43 | INFO     | __main__ | ✅ Lote reconstruído com 11 itens
INFO:__main__:
============================================================
13:40:43 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250812_184911_710
13:40:43 | INFO     | __main__ | 📦 Processando lote: LOTE_20250812_184911_710
WARNING:__main__:⚠️ Lote com Separação DIVERGENTE - será reconstruído
13:40:43 | WARNING  | __main__ | ⚠️ Lote com Separação DIVERGENTE - será reconstruído
INFO:__main__:  ✓ Usando 9 produtos de alertas
13:40:43 | INFO     | __main__ |   ✓ Usando 9 produtos de alertas
INFO:__main__:  📊 Total de produtos: 9
13:40:43 | INFO     | __main__ |   📊 Total de produtos: 9
INFO:__main__:  📊 Fonte principal: alertas
13:40:43 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=89.00, Valor=R$0.00, Peso=989.57kg
13:40:43 | INFO     | __main__ |   📊 Totais: Qtd=89.00, Valor=R$0.00, Peso=989.57kg
INFO:__main__:    ✅ 4080156: 2.00 un | R$ 0.00 | 20.40 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4080156: 2.00 un | R$ 0.00 | 20.40 kg | Fonte: alerta
INFO:__main__:    ✅ 4759099: 10.00 un | R$ 0.00 | 191.15 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4759099: 10.00 un | R$ 0.00 | 191.15 kg | Fonte: alerta
INFO:__main__:    ✅ 4510171: 3.00 un | R$ 0.00 | 25.74 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4510171: 3.00 un | R$ 0.00 | 25.74 kg | Fonte: alerta
INFO:__main__:    ✅ 4759098: 50.00 un | R$ 0.00 | 480.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4759098: 50.00 un | R$ 0.00 | 480.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4310177: 5.00 un | R$ 0.00 | 78.78 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4310177: 5.00 un | R$ 0.00 | 78.78 kg | Fonte: alerta
INFO:__main__:    ✅ 4360156: 3.00 un | R$ 0.00 | 30.60 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4360156: 3.00 un | R$ 0.00 | 30.60 kg | Fonte: alerta
INFO:__main__:    ✅ 4320156: 10.00 un | R$ 0.00 | 102.00 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4320156: 10.00 un | R$ 0.00 | 102.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4080178: 3.00 un | R$ 0.00 | 37.50 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4080178: 3.00 un | R$ 0.00 | 37.50 kg | Fonte: alerta
INFO:__main__:    ✅ 4080154: 3.00 un | R$ 0.00 | 23.40 kg | Fonte: alerta
13:40:43 | INFO     | __main__ |     ✅ 4080154: 3.00 un | R$ 0.00 | 23.40 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 9 itens
13:40:43 | INFO     | __main__ | ✅ Lote reconstruído com 9 itens
INFO:__main__:
============================================================
13:40:43 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250812_185019_514
13:40:43 | INFO     | __main__ | 📦 Processando lote: LOTE_20250812_185019_514
WARNING:__main__:⚠️ Lote com Separação DIVERGENTE - será reconstruído
13:40:43 | WARNING  | __main__ | ⚠️ Lote com Separação DIVERGENTE - será reconstruído
INFO:__main__:  ✓ Usando 11 produtos de alertas
13:40:43 | INFO     | __main__ |   ✓ Usando 11 produtos de alertas
INFO:__main__:  📊 Total de produtos: 11
13:40:44 | INFO     | __main__ |   📊 Total de produtos: 11
INFO:__main__:  📊 Fonte principal: alertas
13:40:44 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=238.00, Valor=R$0.00, Peso=2296.83kg
13:40:44 | INFO     | __main__ |   📊 Totais: Qtd=238.00, Valor=R$0.00, Peso=2296.83kg
INFO:__main__:    ✅ 4070162: 2.00 un | R$ 0.00 | 42.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4070162: 2.00 un | R$ 0.00 | 42.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4759099: 10.00 un | R$ 0.00 | 191.15 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4759099: 10.00 un | R$ 0.00 | 191.15 kg | Fonte: alerta
INFO:__main__:    ✅ 4759098: 150.00 un | R$ 0.00 | 1440.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4759098: 150.00 un | R$ 0.00 | 1440.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4310177: 5.00 un | R$ 0.00 | 78.78 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4310177: 5.00 un | R$ 0.00 | 78.78 kg | Fonte: alerta
INFO:__main__:    ✅ 4360147: 10.00 un | R$ 0.00 | 54.60 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4360147: 10.00 un | R$ 0.00 | 54.60 kg | Fonte: alerta
INFO:__main__:    ✅ 4320156: 10.00 un | R$ 0.00 | 102.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4320156: 10.00 un | R$ 0.00 | 102.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4320147: 30.00 un | R$ 0.00 | 163.80 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4320147: 30.00 un | R$ 0.00 | 163.80 kg | Fonte: alerta
INFO:__main__:    ✅ 4520161: 10.00 un | R$ 0.00 | 134.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4520161: 10.00 un | R$ 0.00 | 134.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4070176: 5.00 un | R$ 0.00 | 36.50 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4070176: 5.00 un | R$ 0.00 | 36.50 kg | Fonte: alerta
INFO:__main__:    ✅ 4080154: 3.00 un | R$ 0.00 | 23.40 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4080154: 3.00 un | R$ 0.00 | 23.40 kg | Fonte: alerta
INFO:__main__:    ✅ 4080156: 3.00 un | R$ 0.00 | 30.60 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4080156: 3.00 un | R$ 0.00 | 30.60 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 11 itens
13:40:44 | INFO     | __main__ | ✅ Lote reconstruído com 11 itens
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250812_185129_320
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250812_185129_320
WARNING:__main__:⚠️ Lote com Separação DIVERGENTE - será reconstruído
13:40:44 | WARNING  | __main__ | ⚠️ Lote com Separação DIVERGENTE - será reconstruído
INFO:__main__:  ✓ Usando 1 produtos de alertas
13:40:44 | INFO     | __main__ |   ✓ Usando 1 produtos de alertas
INFO:__main__:  📊 Total de produtos: 1
13:40:44 | INFO     | __main__ |   📊 Total de produtos: 1
INFO:__main__:  📊 Fonte principal: alertas
13:40:44 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=5.00, Valor=R$0.00, Peso=36.50kg
13:40:44 | INFO     | __main__ |   📊 Totais: Qtd=5.00, Valor=R$0.00, Peso=36.50kg
INFO:__main__:    ✅ 4050176: 5.00 un | R$ 0.00 | 36.50 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4050176: 5.00 un | R$ 0.00 | 36.50 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 1 itens
13:40:44 | INFO     | __main__ | ✅ Lote reconstruído com 1 itens
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250812_185205_416
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250812_185205_416
WARNING:__main__:⚠️ Lote com Separação DIVERGENTE - será reconstruído
13:40:44 | WARNING  | __main__ | ⚠️ Lote com Separação DIVERGENTE - será reconstruído
INFO:__main__:  ✓ Usando 1 produtos de alertas
13:40:44 | INFO     | __main__ |   ✓ Usando 1 produtos de alertas
INFO:__main__:  📊 Total de produtos: 1
13:40:44 | INFO     | __main__ |   📊 Total de produtos: 1
INFO:__main__:  📊 Fonte principal: alertas
13:40:44 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=5.00, Valor=R$0.00, Peso=36.50kg
13:40:44 | INFO     | __main__ |   📊 Totais: Qtd=5.00, Valor=R$0.00, Peso=36.50kg
INFO:__main__:    ✅ 4050176: 5.00 un | R$ 0.00 | 36.50 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4050176: 5.00 un | R$ 0.00 | 36.50 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 1 itens
13:40:44 | INFO     | __main__ | ✅ Lote reconstruído com 1 itens
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250813_141257_053
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250813_141257_053
WARNING:__main__:⚠️ Lote com Separação DIVERGENTE - será reconstruído
13:40:44 | WARNING  | __main__ | ⚠️ Lote com Separação DIVERGENTE - será reconstruído
INFO:__main__:  ✓ Usando 5 produtos de alertas
13:40:44 | INFO     | __main__ |   ✓ Usando 5 produtos de alertas
INFO:__main__:  📊 Total de produtos: 5
13:40:44 | INFO     | __main__ |   📊 Total de produtos: 5
INFO:__main__:  📊 Fonte principal: alertas
13:40:44 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=31.00, Valor=R$3145.56, Peso=575.00kg
13:40:44 | INFO     | __main__ |   📊 Totais: Qtd=31.00, Valor=R$3145.56, Peso=575.00kg
INFO:__main__:    ✅ 4070162: 5.00 un | R$ 0.00 | 105.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4070162: 5.00 un | R$ 0.00 | 105.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4360162: 5.00 un | R$ 0.00 | 105.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4360162: 5.00 un | R$ 0.00 | 105.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4320162: 11.00 un | R$ 3145.56 | 231.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4320162: 11.00 un | R$ 3145.56 | 231.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4100161: 4.00 un | R$ 0.00 | 53.60 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4100161: 4.00 un | R$ 0.00 | 53.60 kg | Fonte: alerta
INFO:__main__:    ✅ 4510161: 6.00 un | R$ 0.00 | 80.40 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4510161: 6.00 un | R$ 0.00 | 80.40 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 5 itens
13:40:44 | INFO     | __main__ | ✅ Lote reconstruído com 5 itens
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250813_142907_855
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250813_142907_855
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
INFO:__main__:  ✓ Usando 2 produtos de alertas
13:40:44 | INFO     | __main__ |   ✓ Usando 2 produtos de alertas
INFO:__main__:  📊 Total de produtos: 2
13:40:44 | INFO     | __main__ |   📊 Total de produtos: 2
INFO:__main__:  📊 Fonte principal: alertas
13:40:44 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=16.00, Valor=R$0.00, Peso=336.00kg
13:40:44 | INFO     | __main__ |   📊 Totais: Qtd=16.00, Valor=R$0.00, Peso=336.00kg
INFO:__main__:    ✅ 4360162: 8.00 un | R$ 0.00 | 168.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4360162: 8.00 un | R$ 0.00 | 168.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4510162: 8.00 un | R$ 0.00 | 168.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4510162: 8.00 un | R$ 0.00 | 168.00 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 2 itens
13:40:44 | INFO     | __main__ | ✅ Lote reconstruído com 2 itens
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250813_152713_870
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250813_152713_870
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
INFO:__main__:  ✓ Usando 4 produtos de alertas
13:40:44 | INFO     | __main__ |   ✓ Usando 4 produtos de alertas
INFO:__main__:  📊 Total de produtos: 4
13:40:44 | INFO     | __main__ |   📊 Total de produtos: 4
INFO:__main__:  📊 Fonte principal: alertas
13:40:44 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=12.00, Valor=R$0.00, Peso=138.40kg
13:40:44 | INFO     | __main__ |   📊 Totais: Qtd=12.00, Valor=R$0.00, Peso=138.40kg
INFO:__main__:    ✅ 4030156: 2.00 un | R$ 0.00 | 20.40 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4030156: 2.00 un | R$ 0.00 | 20.40 kg | Fonte: alerta
INFO:__main__:    ✅ 4050156: 2.00 un | R$ 0.00 | 20.40 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4050156: 2.00 un | R$ 0.00 | 20.40 kg | Fonte: alerta
INFO:__main__:    ✅ 4520156: 3.00 un | R$ 0.00 | 30.60 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4520156: 3.00 un | R$ 0.00 | 30.60 kg | Fonte: alerta
INFO:__main__:    ✅ 4100161: 5.00 un | R$ 0.00 | 67.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4100161: 5.00 un | R$ 0.00 | 67.00 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 4 itens
13:40:44 | INFO     | __main__ | ✅ Lote reconstruído com 4 itens
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250813_152720_166
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250813_152720_166
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
INFO:__main__:  ✓ Usando 6 produtos de alertas
13:40:44 | INFO     | __main__ |   ✓ Usando 6 produtos de alertas
INFO:__main__:  📊 Total de produtos: 6
13:40:44 | INFO     | __main__ |   📊 Total de produtos: 6
INFO:__main__:  📊 Fonte principal: alertas
13:40:44 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=54.00, Valor=R$0.00, Peso=356.05kg
13:40:44 | INFO     | __main__ |   📊 Totais: Qtd=54.00, Valor=R$0.00, Peso=356.05kg
INFO:__main__:    ✅ 4360147: 12.00 un | R$ 0.00 | 65.52 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4360147: 12.00 un | R$ 0.00 | 65.52 kg | Fonte: alerta
INFO:__main__:    ✅ 4320147: 18.00 un | R$ 0.00 | 98.28 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4320147: 18.00 un | R$ 0.00 | 98.28 kg | Fonte: alerta
INFO:__main__:    ✅ 4310177: 5.00 un | R$ 0.00 | 78.78 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4310177: 5.00 un | R$ 0.00 | 78.78 kg | Fonte: alerta
INFO:__main__:    ✅ 4510145: 4.00 un | R$ 0.00 | 22.28 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4510145: 4.00 un | R$ 0.00 | 22.28 kg | Fonte: alerta
INFO:__main__:    ✅ 4520145: 11.00 un | R$ 0.00 | 61.27 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4520145: 11.00 un | R$ 0.00 | 61.27 kg | Fonte: alerta
INFO:__main__:    ✅ 4310176: 4.00 un | R$ 0.00 | 29.92 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4310176: 4.00 un | R$ 0.00 | 29.92 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 6 itens
13:40:44 | INFO     | __main__ | ✅ Lote reconstruído com 6 itens
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250813_152730_414
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250813_152730_414
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
INFO:__main__:  ✓ Usando 2 produtos de alertas
13:40:44 | INFO     | __main__ |   ✓ Usando 2 produtos de alertas
INFO:__main__:  📊 Total de produtos: 2
13:40:44 | INFO     | __main__ |   📊 Total de produtos: 2
INFO:__main__:  📊 Fonte principal: alertas
13:40:44 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=11.00, Valor=R$0.00, Peso=163.02kg
13:40:44 | INFO     | __main__ |   📊 Totais: Qtd=11.00, Valor=R$0.00, Peso=163.02kg
INFO:__main__:    ✅ 4360147: 1.00 un | R$ 0.00 | 5.46 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4360147: 1.00 un | R$ 0.00 | 5.46 kg | Fonte: alerta
INFO:__main__:    ✅ 4310177: 10.00 un | R$ 0.00 | 157.56 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4310177: 10.00 un | R$ 0.00 | 157.56 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 2 itens
13:40:44 | INFO     | __main__ | ✅ Lote reconstruído com 2 itens
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250813_152849_761
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250813_152849_761
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
INFO:__main__:  ✓ Usando 2 produtos de alertas
13:40:44 | INFO     | __main__ |   ✓ Usando 2 produtos de alertas
INFO:__main__:  📊 Total de produtos: 2
13:40:44 | INFO     | __main__ |   📊 Total de produtos: 2
INFO:__main__:  📊 Fonte principal: alertas
13:40:44 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=13.00, Valor=R$0.00, Peso=101.87kg
13:40:44 | INFO     | __main__ |   📊 Totais: Qtd=13.00, Valor=R$0.00, Peso=101.87kg
INFO:__main__:    ✅ 4320147: 10.00 un | R$ 0.00 | 54.60 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4320147: 10.00 un | R$ 0.00 | 54.60 kg | Fonte: alerta
INFO:__main__:    ✅ 4310177: 3.00 un | R$ 0.00 | 47.27 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4310177: 3.00 un | R$ 0.00 | 47.27 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 2 itens
13:40:44 | INFO     | __main__ | ✅ Lote reconstruído com 2 itens
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250813_190828_437
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250813_190828_437
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
INFO:__main__:  ✓ Usando 7 produtos de alertas
13:40:44 | INFO     | __main__ |   ✓ Usando 7 produtos de alertas
INFO:__main__:  📊 Total de produtos: 7
13:40:44 | INFO     | __main__ |   📊 Total de produtos: 7
INFO:__main__:  📊 Fonte principal: alertas
13:40:44 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=18.00, Valor=R$0.00, Peso=298.00kg
13:40:44 | INFO     | __main__ |   📊 Totais: Qtd=18.00, Valor=R$0.00, Peso=298.00kg
INFO:__main__:    ✅ 4320162: 5.00 un | R$ 0.00 | 105.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4320162: 5.00 un | R$ 0.00 | 105.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4510156: 2.00 un | R$ 0.00 | 20.40 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4510156: 2.00 un | R$ 0.00 | 20.40 kg | Fonte: alerta
INFO:__main__:    ✅ 4210165: 2.00 un | R$ 0.00 | 42.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4210165: 2.00 un | R$ 0.00 | 42.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4520156: 2.00 un | R$ 0.00 | 20.40 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4520156: 2.00 un | R$ 0.00 | 20.40 kg | Fonte: alerta
INFO:__main__:    ✅ 4100161: 2.00 un | R$ 0.00 | 26.80 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4100161: 2.00 un | R$ 0.00 | 26.80 kg | Fonte: alerta
INFO:__main__:    ✅ 4230162: 3.00 un | R$ 0.00 | 63.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4230162: 3.00 un | R$ 0.00 | 63.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4030156: 2.00 un | R$ 0.00 | 20.40 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4030156: 2.00 un | R$ 0.00 | 20.40 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 7 itens
13:40:44 | INFO     | __main__ | ✅ Lote reconstruído com 7 itens
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250813_190932_048
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250813_190932_048
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
INFO:__main__:  ✓ Usando 5 produtos de alertas
13:40:44 | INFO     | __main__ |   ✓ Usando 5 produtos de alertas
INFO:__main__:  📊 Total de produtos: 5
13:40:44 | INFO     | __main__ |   📊 Total de produtos: 5
INFO:__main__:  📊 Fonte principal: alertas
13:40:44 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=50.00, Valor=R$0.00, Peso=433.22kg
13:40:44 | INFO     | __main__ |   📊 Totais: Qtd=50.00, Valor=R$0.00, Peso=433.22kg
INFO:__main__:    ✅ 4070176: 6.00 un | R$ 0.00 | 43.80 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4070176: 6.00 un | R$ 0.00 | 43.80 kg | Fonte: alerta
INFO:__main__:    ✅ 4310152: 7.00 un | R$ 0.00 | 42.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4310152: 7.00 un | R$ 0.00 | 42.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4510145: 15.00 un | R$ 0.00 | 83.55 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4510145: 15.00 un | R$ 0.00 | 83.55 kg | Fonte: alerta
INFO:__main__:    ✅ 4310176: 10.00 un | R$ 0.00 | 74.80 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4310176: 10.00 un | R$ 0.00 | 74.80 kg | Fonte: alerta
INFO:__main__:    ✅ 4310177: 12.00 un | R$ 0.00 | 189.07 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4310177: 12.00 un | R$ 0.00 | 189.07 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 5 itens
13:40:44 | INFO     | __main__ | ✅ Lote reconstruído com 5 itens
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250813_190939_561
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250813_190939_561
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
INFO:__main__:  ✓ Usando 2 produtos de alertas
13:40:44 | INFO     | __main__ |   ✓ Usando 2 produtos de alertas
INFO:__main__:  📊 Total de produtos: 2
13:40:44 | INFO     | __main__ |   📊 Total de produtos: 2
INFO:__main__:  📊 Fonte principal: alertas
13:40:44 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=5.00, Valor=R$0.00, Peso=83.40kg
13:40:44 | INFO     | __main__ |   📊 Totais: Qtd=5.00, Valor=R$0.00, Peso=83.40kg
INFO:__main__:    ✅ 4210165: 3.00 un | R$ 0.00 | 63.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4210165: 3.00 un | R$ 0.00 | 63.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4030156: 2.00 un | R$ 0.00 | 20.40 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4030156: 2.00 un | R$ 0.00 | 20.40 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 2 itens
13:40:44 | INFO     | __main__ | ✅ Lote reconstruído com 2 itens
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250813_192614_966
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250813_192614_966
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
INFO:__main__:  ✓ Usando 3 produtos de alertas
13:40:44 | INFO     | __main__ |   ✓ Usando 3 produtos de alertas
INFO:__main__:  📊 Total de produtos: 3
13:40:44 | INFO     | __main__ |   📊 Total de produtos: 3
INFO:__main__:  📊 Fonte principal: alertas
13:40:44 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=6.00, Valor=R$0.00, Peso=104.40kg
13:40:44 | INFO     | __main__ |   📊 Totais: Qtd=6.00, Valor=R$0.00, Peso=104.40kg
INFO:__main__:    ✅ 4510156: 2.00 un | R$ 0.00 | 20.40 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4510156: 2.00 un | R$ 0.00 | 20.40 kg | Fonte: alerta
INFO:__main__:    ✅ 4320162: 2.00 un | R$ 0.00 | 42.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4320162: 2.00 un | R$ 0.00 | 42.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4310162: 2.00 un | R$ 0.00 | 42.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4310162: 2.00 un | R$ 0.00 | 42.00 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 3 itens
13:40:44 | INFO     | __main__ | ✅ Lote reconstruído com 3 itens
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_BF50340F
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_BF50340F
WARNING:__main__:⚠️ Lote com Separação DIVERGENTE - será reconstruído
13:40:44 | WARNING  | __main__ | ⚠️ Lote com Separação DIVERGENTE - será reconstruído
INFO:__main__:  ✓ Usando 9 produtos de alertas
13:40:44 | INFO     | __main__ |   ✓ Usando 9 produtos de alertas
INFO:__main__:  📊 Total de produtos: 9
13:40:44 | INFO     | __main__ |   📊 Total de produtos: 9
INFO:__main__:  📊 Fonte principal: alertas
13:40:44 | INFO     | __main__ |   📊 Fonte principal: alertas
INFO:__main__:  📊 Totais: Qtd=804.00, Valor=R$0.00, Peso=5074.88kg
13:40:44 | INFO     | __main__ |   📊 Totais: Qtd=804.00, Valor=R$0.00, Peso=5074.88kg
INFO:__main__:    ✅ 4320147: 112.00 un | R$ 0.00 | 611.52 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4320147: 112.00 un | R$ 0.00 | 611.52 kg | Fonte: alerta
INFO:__main__:    ✅ 4310148: 112.00 un | R$ 0.00 | 657.44 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4310148: 112.00 un | R$ 0.00 | 657.44 kg | Fonte: alerta
INFO:__main__:    ✅ 4310146: 112.00 un | R$ 0.00 | 657.44 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4310146: 112.00 un | R$ 0.00 | 657.44 kg | Fonte: alerta
INFO:__main__:    ✅ 4350150: 112.00 un | R$ 0.00 | 672.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4350150: 112.00 un | R$ 0.00 | 672.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4320154: 80.00 un | R$ 0.00 | 624.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4320154: 80.00 un | R$ 0.00 | 624.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4310141: 112.00 un | R$ 0.00 | 585.76 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4310141: 112.00 un | R$ 0.00 | 585.76 kg | Fonte: alerta
INFO:__main__:    ✅ 4360147: 32.00 un | R$ 0.00 | 174.72 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4360147: 32.00 un | R$ 0.00 | 174.72 kg | Fonte: alerta
INFO:__main__:    ✅ 4360162: 20.00 un | R$ 0.00 | 420.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4360162: 20.00 un | R$ 0.00 | 420.00 kg | Fonte: alerta
INFO:__main__:    ✅ 4310152: 112.00 un | R$ 0.00 | 672.00 kg | Fonte: alerta
13:40:44 | INFO     | __main__ |     ✅ 4310152: 112.00 un | R$ 0.00 | 672.00 kg | Fonte: alerta
INFO:__main__:✅ Lote reconstruído com 9 itens
13:40:44 | INFO     | __main__ | ✅ Lote reconstruído com 9 itens
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250808_034538_384
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250808_034538_384
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
ERROR:__main__:❌ Sem dados de produtos para reconstruir
13:40:44 | ERROR    | __main__ | ❌ Sem dados de produtos para reconstruir
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250808_194054_398
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250808_194054_398
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
ERROR:__main__:❌ Sem dados de produtos para reconstruir
13:40:44 | ERROR    | __main__ | ❌ Sem dados de produtos para reconstruir
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250811_140846_758
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250811_140846_758
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
ERROR:__main__:❌ Sem dados de produtos para reconstruir
13:40:44 | ERROR    | __main__ | ❌ Sem dados de produtos para reconstruir
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250811_140907_061
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250811_140907_061
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
ERROR:__main__:❌ Sem dados de produtos para reconstruir
13:40:44 | ERROR    | __main__ | ❌ Sem dados de produtos para reconstruir
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250811_140923_592
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250811_140923_592
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
ERROR:__main__:❌ Sem dados de produtos para reconstruir
13:40:44 | ERROR    | __main__ | ❌ Sem dados de produtos para reconstruir
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250811_140931_636
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250811_140931_636
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
ERROR:__main__:❌ Sem dados de produtos para reconstruir
13:40:44 | ERROR    | __main__ | ❌ Sem dados de produtos para reconstruir
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250811_140957_676
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250811_140957_676
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
ERROR:__main__:❌ Sem dados de produtos para reconstruir
13:40:44 | ERROR    | __main__ | ❌ Sem dados de produtos para reconstruir
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_20250811_141005_038
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_20250811_141005_038
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
ERROR:__main__:❌ Sem dados de produtos para reconstruir
13:40:44 | ERROR    | __main__ | ❌ Sem dados de produtos para reconstruir
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_23B29D1B
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_23B29D1B
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
ERROR:__main__:❌ Sem dados de produtos para reconstruir
13:40:44 | ERROR    | __main__ | ❌ Sem dados de produtos para reconstruir
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_5BB46EE6
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_5BB46EE6
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
ERROR:__main__:❌ Sem dados de produtos para reconstruir
13:40:44 | ERROR    | __main__ | ❌ Sem dados de produtos para reconstruir
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_AEA24966
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_AEA24966
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
ERROR:__main__:❌ Sem dados de produtos para reconstruir
13:40:44 | ERROR    | __main__ | ❌ Sem dados de produtos para reconstruir
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_C4D3F191
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_C4D3F191
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
ERROR:__main__:❌ Sem dados de produtos para reconstruir
13:40:44 | ERROR    | __main__ | ❌ Sem dados de produtos para reconstruir
INFO:__main__:
============================================================
13:40:44 | INFO     | __main__ | 
============================================================
INFO:__main__:📦 Processando lote: LOTE_F7E2EB60
13:40:44 | INFO     | __main__ | 📦 Processando lote: LOTE_F7E2EB60
WARNING:__main__:🔴 Lote SEM Separação - será reconstruído
13:40:44 | WARNING  | __main__ | 🔴 Lote SEM Separação - será reconstruído
ERROR:__main__:❌ Sem dados de produtos para reconstruir
13:40:44 | ERROR    | __main__ | ❌ Sem dados de produtos para reconstruir
INFO:__main__:
📋 Atualizando EmbarqueItems sem separacao_lote_id...
13:40:44 | INFO     | __main__ | 
📋 Atualizando EmbarqueItems sem separacao_lote_id...
INFO:__main__:  ✓ Todos os EmbarqueItems têm separacao_lote_id
13:40:44 | INFO     | __main__ |   ✓ Todos os EmbarqueItems têm separacao_lote_id
INFO:__main__:
💾 Salvando alterações no banco...
13:40:44 | INFO     | __main__ | 
💾 Salvando alterações no banco...
INFO:__main__:✅ Alterações salvas com sucesso!
13:40:44 | INFO     | __main__ | ✅ Alterações salvas com sucesso!
INFO:__main__:
======================================================================
13:40:44 | INFO     | __main__ | 
======================================================================
INFO:__main__:📊 ESTATÍSTICAS DA RECONSTRUÇÃO COM FALLBACK
13:40:44 | INFO     | __main__ | 📊 ESTATÍSTICAS DA RECONSTRUÇÃO COM FALLBACK
INFO:__main__:======================================================================
13:40:44 | INFO     | __main__ | ======================================================================
INFO:__main__:
📋 PROCESSAMENTO:
13:40:44 | INFO     | __main__ | 
📋 PROCESSAMENTO:
INFO:__main__:  • Lotes processados: 38
13:40:44 | INFO     | __main__ |   • Lotes processados: 38
INFO:__main__:  • Lotes reconstruídos: 24
13:40:44 | INFO     | __main__ |   • Lotes reconstruídos: 24
INFO:__main__:  • Lotes já existentes: 0
13:40:44 | INFO     | __main__ |   • Lotes já existentes: 0
INFO:__main__:  • Lotes sem dados: 13
13:40:44 | INFO     | __main__ |   • Lotes sem dados: 13
INFO:__main__:
✅ VALIDAÇÕES:
13:40:44 | INFO     | __main__ | 
✅ VALIDAÇÕES:
INFO:__main__:  • Separações validadas: 0
13:40:44 | INFO     | __main__ |   • Separações validadas: 0
INFO:__main__:  • Separações divergentes: 14
13:40:44 | INFO     | __main__ |   • Separações divergentes: 14
INFO:__main__:
🔄 RECUPERAÇÕES VIA FALLBACK:
13:40:44 | INFO     | __main__ | 
🔄 RECUPERAÇÕES VIA FALLBACK:
INFO:__main__:  • Lotes recuperados via Pedido: 13
13:40:44 | INFO     | __main__ |   • Lotes recuperados via Pedido: 13
INFO:__main__:  • Lotes recuperados via NF: 0
13:40:44 | INFO     | __main__ |   • Lotes recuperados via NF: 0
INFO:__main__:  • EmbarqueItems atualizados: 0
13:40:44 | INFO     | __main__ |   • EmbarqueItems atualizados: 0
INFO:__main__:
📦 ITENS CRIADOS:
13:40:44 | INFO     | __main__ | 
📦 ITENS CRIADOS:
INFO:__main__:  • Total de itens: 137
13:40:44 | INFO     | __main__ |   • Total de itens: 137
INFO:__main__:
📊 FONTES DE DADOS:
13:40:44 | INFO     | __main__ | 
📊 FONTES DE DADOS:
INFO:__main__:  • FaturamentoProduto: 0 lotes
13:40:44 | INFO     | __main__ |   • FaturamentoProduto: 0 lotes
INFO:__main__:  • CarteiraPrincipal: 0 lotes
13:40:44 | INFO     | __main__ |   • CarteiraPrincipal: 0 lotes
INFO:__main__:  • Alertas: 25 lotes
13:40:44 | INFO     | __main__ |   • Alertas: 25 lotes
INFO:__main__:
✅ SUCESSO: 24 lotes reconstruídos, 0 embarques atualizados!
13:40:44 | INFO     | __main__ | 
✅ SUCESSO: 24 lotes reconstruídos, 0 embarques atualizados!
INFO:__main__:
✅ Script executado com sucesso
13:40:44 | INFO     | __main__ | 
✅ Script executado com sucesso
INFO:apscheduler.scheduler:Scheduler has been shut down
13:40:44 | INFO     | apscheduler.scheduler | Scheduler has been shut down
render@srv-d13m38vfte5s738t6p60-6bcf86c75b-q59bn:~/project/src$ '''