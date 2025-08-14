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