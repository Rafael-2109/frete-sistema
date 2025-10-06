"""
Serviço de Recuperação de Separações Perdidas
=============================================

Este serviço reconstrói Separações que foram perdidas/deletadas incorretamente.
Usa engenharia reversa: Pedido + FaturamentoProduto → Separacao

Criado: 2025-08-21
Objetivo: Recuperar separações deletadas pela função anterior com bug
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid
from app import db
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.faturamento.models import FaturamentoProduto
from app.producao.models import CadastroPalletizacao
from app.utils.text_utils import truncar_observacao
from app.carteira.models import CarteiraPrincipal

logger = logging.getLogger(__name__)


class RecuperadorSeparacoesPerdidas:
    """
    Serviço para recuperar Separações perdidas através de engenharia reversa
    
    Fluxo:
    1. Busca Pedidos FATURADOS/NF no CD sem separacao_lote_id
    2. Para cada Pedido, busca FaturamentoProduto pela NF
    3. Reconstrói Separação com dados do Pedido + FaturamentoProduto
    4. Calcula pallets usando CadastroPalletizacao
    """
    
    @classmethod
    def executar_recuperacao_completa(cls, modo_simulacao: bool = False) -> Dict[str, Any]:
        """
        Executa recuperação completa de todas as separações perdidas
        
        Args:
            modo_simulacao: Se True, não salva no banco (dry-run)
            
        Returns:
            Dict com estatísticas da recuperação
        """
        logger.info("=" * 70)
        logger.info("🔧 INICIANDO RECUPERAÇÃO DE SEPARAÇÕES PERDIDAS")
        logger.info(f"📅 Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"🔄 Modo: {'SIMULAÇÃO' if modo_simulacao else 'PRODUÇÃO'}")
        logger.info("=" * 70)
        
        resultado = {
            'sucesso': True,
            'pedidos_analisados': 0,
            'pedidos_orfaos': 0,
            'separacoes_criadas': 0,
            'produtos_recuperados': 0,
            'lotes_criados': [],
            'erros': [],
            'detalhes': []
        }
        
        try:
            # 1. Buscar pedidos órfãos (FATURADOS sem separacao_lote_id)
            pedidos_orfaos = cls._buscar_pedidos_orfaos()
            resultado['pedidos_analisados'] = len(pedidos_orfaos)
            
            logger.info(f"📊 Encontrados {len(pedidos_orfaos)} pedidos órfãos para processar")
            
            if not pedidos_orfaos:
                logger.info("✅ Nenhum pedido órfão encontrado - sistema está íntegro!")
                return resultado
            
            # 2. Processar cada pedido órfão
            for pedido in pedidos_orfaos:
                try:
                    logger.info(f"\n{'='*50}")
                    logger.info(f"🔄 Processando Pedido {pedido.num_pedido} - NF: {pedido.nf}")
                    
                    # Verificar se tem NF para buscar produtos
                    if not pedido.nf:
                        logger.warning(f"⚠️ Pedido {pedido.num_pedido} sem NF - pulando")
                        resultado['erros'].append(f"Pedido {pedido.num_pedido} sem NF")
                        continue
                    
                    # Recuperar separação deste pedido
                    resultado_pedido = cls._recuperar_separacao_pedido(pedido, modo_simulacao)
                    
                    if resultado_pedido['sucesso']:
                        resultado['pedidos_orfaos'] += 1
                        resultado['separacoes_criadas'] += resultado_pedido['separacoes_criadas']
                        resultado['produtos_recuperados'] += resultado_pedido['produtos_recuperados']
                        resultado['lotes_criados'].append(resultado_pedido['lote_id'])
                        resultado['detalhes'].append({
                            'pedido': pedido.num_pedido,
                            'nf': pedido.nf,
                            'lote_criado': resultado_pedido['lote_id'],
                            'produtos': resultado_pedido['produtos_recuperados']
                        })
                        
                        logger.info(f"✅ Pedido {pedido.num_pedido} recuperado com sucesso!")
                        logger.info(f"   - Lote criado: {resultado_pedido['lote_id']}")
                        logger.info(f"   - Produtos: {resultado_pedido['produtos_recuperados']}")
                    else:
                        resultado['erros'].append(f"Pedido {pedido.num_pedido}: {resultado_pedido.get('erro', 'Erro desconhecido')}")
                        logger.error(f"❌ Erro ao recuperar pedido {pedido.num_pedido}")
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao processar pedido {pedido.num_pedido}: {e}")
                    resultado['erros'].append(f"Pedido {pedido.num_pedido}: {str(e)}")
                    continue
            
            # 3. Commit ou rollback baseado no modo
            if not modo_simulacao and resultado['separacoes_criadas'] > 0:
                db.session.commit()
                logger.info(f"\n✅ {resultado['separacoes_criadas']} separações salvas no banco")
            elif modo_simulacao:
                db.session.rollback()
                logger.info("\n⚠️ MODO SIMULAÇÃO - Nenhuma alteração foi salva")
            
            # 4. Relatório final
            cls._gerar_relatorio_recuperacao(resultado)
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro na recuperação: {e}")
            resultado['sucesso'] = False
            resultado['erro_geral'] = str(e)
        
        return resultado
    
    @classmethod
    def _buscar_pedidos_orfaos(cls) -> List[Pedido]:
        """
        Busca pedidos FATURADOS ou 'NF no CD' que TÊM separacao_lote_id 
        mas NÃO tem Separacao correspondente (foram deletadas)
        """
        # Buscar pedidos FATURADOS com lote_id
        pedidos_com_lote = Pedido.query.filter(
            db.or_(
                Pedido.status == 'FATURADO',
                Pedido.status == 'NF no CD'
            ),
            Pedido.separacao_lote_id.isnot(None),
            Pedido.separacao_lote_id != '',
            Pedido.nf.isnot(None),  # Precisa ter NF para recuperar
            Pedido.nf != ''
        ).all()
        
        # Filtrar apenas os que NÃO tem Separacao correspondente
        pedidos_orfaos = []
        for pedido in pedidos_com_lote:
            # Verificar se existe Separacao para este lote
            separacao_existe = Separacao.query.filter_by(
                separacao_lote_id=pedido.separacao_lote_id
            ).first()
            
            if not separacao_existe:
                # Pedido tem lote_id mas Separacao foi deletada
                logger.debug(f"Pedido {pedido.num_pedido} tem lote {pedido.separacao_lote_id} mas sem Separacao")
                pedidos_orfaos.append(pedido)
        
        return pedidos_orfaos
    
    @classmethod
    def _recuperar_separacao_pedido(cls, pedido: Pedido, modo_simulacao: bool = False) -> Dict[str, Any]:
        """
        Recupera separação de um pedido específico usando dados da NF
        """
        resultado = {
            'sucesso': False,
            'lote_id': None,
            'separacoes_criadas': 0,
            'produtos_recuperados': 0,
            'erro': None
        }
        
        try:
            # 1. Buscar produtos da NF
            produtos_nf = FaturamentoProduto.query.filter_by(
                numero_nf=pedido.nf,
                origem=pedido.num_pedido
            ).all()
            
            if not produtos_nf:
                # Tentar buscar só pela NF se não encontrou com origem
                produtos_nf = FaturamentoProduto.query.filter_by(
                    numero_nf=pedido.nf
                ).all()
                
                if not produtos_nf:
                    resultado['erro'] = f"Nenhum produto encontrado para NF {pedido.nf}"
                    logger.warning(f"⚠️ Nenhum produto encontrado para NF {pedido.nf}")
                    return resultado
            
            logger.info(f"📦 Encontrados {len(produtos_nf)} produtos na NF {pedido.nf}")
            
            # 2. Usar lote_id existente do Pedido (já que Pedido tem, mas Separacao perdeu)
            lote_id = pedido.separacao_lote_id
            if not lote_id:
                # Se por algum motivo não tem, gerar novo
                lote_id = cls._gerar_lote_id(pedido.num_pedido)
                logger.info(f"🆔 Novo lote_id gerado: {lote_id}")
            else:
                logger.info(f"🔄 Usando lote_id existente do Pedido: {lote_id}")
            
            resultado['lote_id'] = lote_id
            
            # 3. Buscar dados complementares da CarteiraPrincipal (se existir)
            dados_carteira = cls._buscar_dados_carteira(pedido.num_pedido)
            
            # 4. Criar Separação para cada produto
            for produto_nf in produtos_nf:
                try:
                    # Criar nova Separação
                    separacao = Separacao()
                    
                    # Dados do lote e pedido
                    separacao.separacao_lote_id = lote_id
                    separacao.num_pedido = pedido.num_pedido
                    separacao.data_pedido = pedido.data_pedido
                    
                    # Dados do cliente (do Pedido)
                    separacao.cnpj_cpf = pedido.cnpj_cpf
                    separacao.raz_social_red = pedido.raz_social_red
                    separacao.nome_cidade = pedido.nome_cidade or pedido.cidade_normalizada
                    separacao.cod_uf = pedido.cod_uf or pedido.uf_normalizada
                    
                    # Dados do produto (do FaturamentoProduto)
                    separacao.cod_produto = produto_nf.cod_produto
                    separacao.nome_produto = produto_nf.nome_produto
                    separacao.qtd_saldo = float(produto_nf.qtd_produto_faturado or 0)
                    separacao.valor_saldo = float(produto_nf.valor_produto_faturado or 0)
                    separacao.peso = float(produto_nf.peso_total or 0)
                    
                    # Calcular pallets usando CadastroPalletizacao
                    palletizacao = CadastroPalletizacao.query.filter_by(
                        cod_produto=produto_nf.cod_produto
                    ).first()
                    
                    if palletizacao and palletizacao.palletizacao and palletizacao.palletizacao > 0:
                        separacao.pallet = separacao.qtd_saldo / float(palletizacao.palletizacao)
                        logger.debug(f"  Pallets calculados: {separacao.pallet:.2f} (qtd: {separacao.qtd_saldo} / pallet: {palletizacao.palletizacao})")
                    else:
                        separacao.pallet = 0
                        logger.debug(f"  Palletização não encontrada para {produto_nf.cod_produto}")
                    
                    # Dados de agendamento e expedição (do Pedido ou CarteiraPrincipal)
                    separacao.expedicao = pedido.expedicao or (dados_carteira.get('expedicao') if dados_carteira else None)
                    separacao.agendamento = pedido.agendamento or (dados_carteira.get('agendamento') if dados_carteira else None)
                    separacao.protocolo = pedido.protocolo or (dados_carteira.get('protocolo') if dados_carteira else None)
                    
                    # Dados de rota (da CarteiraPrincipal se existir)
                    if dados_carteira:
                        separacao.rota = dados_carteira.get('rota')
                        separacao.sub_rota = dados_carteira.get('sub_rota')
                        separacao.roteirizacao = dados_carteira.get('roteirizacao')
                        separacao.observ_ped_1 = truncar_observacao(dados_carteira.get('observ_ped_1'))
                    
                    # Tipo de envio (sempre total para recuperação)
                    separacao.tipo_envio = 'total'
                    
                    # Marcar como sincronizado com NF (já que veio da NF)
                    separacao.sincronizado_nf = True
                    separacao.numero_nf = pedido.nf
                    separacao.data_sincronizacao = datetime.now()
                    
                    # Adicionar ao banco
                    db.session.add(separacao)
                    resultado['separacoes_criadas'] += 1
                    resultado['produtos_recuperados'] += 1
                    
                    logger.info(f"  ✅ Separação criada: {produto_nf.cod_produto} - Qtd: {separacao.qtd_saldo}")
                    
                except Exception as e:
                    logger.error(f"  ❌ Erro ao criar separação para produto {produto_nf.cod_produto}: {e}")
                    resultado['erro'] = f"Erro no produto {produto_nf.cod_produto}: {str(e)}"
                    continue
            
            # 5. Pedido já tem lote_id, não precisa atualizar
            if resultado['separacoes_criadas'] > 0:
                logger.info(f"✅ {resultado['separacoes_criadas']} Separações recriadas para lote {lote_id}")
                resultado['sucesso'] = True
            
        except Exception as e:
            logger.error(f"❌ Erro ao recuperar separação do pedido {pedido.num_pedido}: {e}")
            resultado['erro'] = str(e)
        
        return resultado
    
    @classmethod
    def _gerar_lote_id(cls, num_pedido: str) -> str:
        """
        Gera um novo lote_id único para a separação recuperada
        """
        # Formato: REC_[PEDIDO]_[TIMESTAMP]_[UUID_CURTO]
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        uuid_curto = str(uuid.uuid4())[:8].upper()
        lote_id = f"REC_{num_pedido}_{timestamp}_{uuid_curto}"
        
        # Garantir unicidade
        while Separacao.query.filter_by(separacao_lote_id=lote_id).first():
            uuid_curto = str(uuid.uuid4())[:8].upper()
            lote_id = f"REC_{num_pedido}_{timestamp}_{uuid_curto}"
        
        return lote_id
    
    @classmethod
    def _buscar_dados_carteira(cls, num_pedido: str) -> Optional[Dict]:
        """
        Busca dados complementares na CarteiraPrincipal
        """
        try:
            # Buscar primeira linha da carteira para este pedido
            item_carteira = CarteiraPrincipal.query.filter_by(
                num_pedido=num_pedido
            ).first()
            
            if item_carteira:
                return {
                    'expedicao': item_carteira.expedicao,
                    'agendamento': item_carteira.agendamento,
                    'protocolo': item_carteira.protocolo,
                    'rota': None,  # CarteiraPrincipal não tem rota
                    'sub_rota': None,
                    'roteirizacao': None,
                    'observ_ped_1': item_carteira.observ_ped_1
                }
        except Exception as e:
            logger.debug(f"Não foi possível buscar dados da carteira: {e}")
        
        return None
    
    @classmethod
    def _gerar_relatorio_recuperacao(cls, resultado: Dict[str, Any]):
        """
        Gera relatório detalhado da recuperação
        """
        logger.info("\n" + "=" * 70)
        logger.info("📊 RELATÓRIO DE RECUPERAÇÃO DE SEPARAÇÕES")
        logger.info("=" * 70)
        logger.info(f"📋 Pedidos analisados: {resultado['pedidos_analisados']}")
        logger.info(f"🔍 Pedidos órfãos encontrados: {resultado['pedidos_orfaos']}")
        logger.info(f"✅ Separações criadas: {resultado['separacoes_criadas']}")
        logger.info(f"📦 Produtos recuperados: {resultado['produtos_recuperados']}")
        
        if resultado['lotes_criados']:
            logger.info(f"\n🆔 LOTES CRIADOS ({len(resultado['lotes_criados'])}):")
            for lote in resultado['lotes_criados'][:10]:  # Mostrar apenas os 10 primeiros
                logger.info(f"  - {lote}")
        
        if resultado['detalhes']:
            logger.info(f"\n📋 DETALHES DAS RECUPERAÇÕES:")
            for detalhe in resultado['detalhes'][:10]:  # Mostrar apenas os 10 primeiros
                logger.info(f"  - Pedido {detalhe['pedido']} (NF: {detalhe['nf']})")
                logger.info(f"    Lote: {detalhe['lote_criado']}")
                logger.info(f"    Produtos: {detalhe['produtos']}")
        
        if resultado['erros']:
            logger.error(f"\n❌ ERROS ENCONTRADOS ({len(resultado['erros'])}):")
            for erro in resultado['erros'][:10]:  # Mostrar apenas os 10 primeiros
                logger.error(f"  - {erro}")
        
        logger.info("=" * 70)
        
        # Resumo final
        if resultado['sucesso'] and resultado['separacoes_criadas'] > 0:
            logger.info(f"✅ RECUPERAÇÃO CONCLUÍDA COM SUCESSO!")
            logger.info(f"   {resultado['separacoes_criadas']} separações foram recuperadas")
            logger.info(f"   {resultado['produtos_recuperados']} produtos foram restaurados")
        elif resultado['sucesso'] and resultado['separacoes_criadas'] == 0:
            logger.info(f"✅ SISTEMA ÍNTEGRO - Nenhuma separação precisou ser recuperada")
        else:
            logger.error(f"❌ RECUPERAÇÃO FALHOU")
            if 'erro_geral' in resultado:
                logger.error(f"   Erro: {resultado['erro_geral']}")
    
    @classmethod
    def verificar_pedido_especifico(cls, num_pedido: str) -> Dict[str, Any]:
        """
        Verifica e recupera um pedido específico
        
        Args:
            num_pedido: Número do pedido para verificar
            
        Returns:
            Dict com status da verificação
        """
        resultado = {
            'pedido': num_pedido,
            'status': None,
            'tem_separacao': False,
            'tem_nf': False,
            'pode_recuperar': False,
            'detalhes': {}
        }
        
        try:
            # Buscar pedido
            pedido = Pedido.query.filter_by(num_pedido=num_pedido).first()
            
            if not pedido:
                resultado['status'] = 'PEDIDO_NAO_ENCONTRADO'
                return resultado
            
            resultado['status'] = pedido.status
            resultado['tem_separacao'] = bool(pedido.separacao_lote_id)
            resultado['tem_nf'] = bool(pedido.nf)
            resultado['detalhes'] = {
                'separacao_lote_id': pedido.separacao_lote_id,
                'nf': pedido.nf,
                'data_pedido': pedido.data_pedido.strftime('%Y-%m-%d') if pedido.data_pedido else None,
                'cliente': pedido.raz_social_red
            }
            
            # Verificar se pode recuperar
            if pedido.status in ['FATURADO', 'NF no CD'] and not pedido.separacao_lote_id and pedido.nf:
                resultado['pode_recuperar'] = True
                
                # Verificar produtos da NF
                produtos_nf = FaturamentoProduto.query.filter_by(
                    numero_nf=pedido.nf,
                    origem=num_pedido
                ).count()
                
                resultado['detalhes']['produtos_na_nf'] = produtos_nf
                
                if produtos_nf == 0:
                    # Tentar buscar só pela NF
                    produtos_nf = FaturamentoProduto.query.filter_by(numero_nf=pedido.nf).count()
                    resultado['detalhes']['produtos_na_nf'] = produtos_nf
                    resultado['detalhes']['obs'] = 'Produtos encontrados apenas pela NF (sem origem)'
            
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao verificar pedido {num_pedido}: {e}")
            resultado['status'] = 'ERRO'
            resultado['detalhes']['erro'] = str(e)
            return resultado


# Função para execução via CLI
def executar_recuperacao_cli(modo_simulacao: bool = False):
    """
    Função para execução via linha de comando
    
    Uso:
        python -c "from app.faturamento.services.recuperar_separacoes_perdidas import executar_recuperacao_cli; executar_recuperacao_cli()"
    """
    from app import create_app
    
    app = create_app()
    with app.app_context():
        resultado = RecuperadorSeparacoesPerdidas.executar_recuperacao_completa(modo_simulacao)
        
        if resultado['sucesso']:
            if resultado['separacoes_criadas'] > 0:
                print(f"✅ Recuperação concluída: {resultado['separacoes_criadas']} separações recuperadas!")
            else:
                print(f"✅ Sistema íntegro - nenhuma separação precisou ser recuperada")
        else:
            print(f"❌ Erro na recuperação: {resultado.get('erro_geral', 'Erro desconhecido')}")
        
        return resultado