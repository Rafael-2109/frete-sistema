"""
Serviço Unificado de Ajuste de Sincronização Odoo
==================================================

Implementação simplificada e funcional das regras de ajuste de
PreSeparacaoItem e Separacao ao sincronizar com o Odoo.

Segue fielmente o documento ajuste_sincronizacao.md
"""

import logging
from decimal import Decimal
from typing import Dict, List, Any
from datetime import datetime, timezone
from app import db
from app.carteira.models import CarteiraPrincipal, PreSeparacaoItem
from app.carteira.models_alertas import AlertaSeparacaoCotada  
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.embarques.models import EmbarqueItem, Embarque

logger = logging.getLogger(__name__)


class AjusteSincronizacaoService:
    """
    Serviço unificado para ajustar separações conforme alterações do Odoo.
    
    Regras principais:
    1. Separação TOTAL: Substituição completa (espelho do pedido)
    2. Separação PARCIAL: Segue hierarquia de ajuste
    """
    
    @classmethod
    def processar_pedido_alterado(cls, num_pedido: str, itens_odoo: List[Dict]) -> Dict[str, Any]:
        """
        Processa um pedido que foi alterado no Odoo.
        
        Args:
            num_pedido: Número do pedido alterado
            itens_odoo: Lista com os itens atualizados do Odoo
            
        Returns:
            Dict com resultado do processamento
        """
        # Garantir sessão limpa
        try:
            db.session.commit()  # Commit qualquer transação pendente
        except Exception as e:
            logger.error(f"Erro ao commitar sessão: {e}")
            db.session.rollback()  # Se falhar, fazer rollback
        
        try:
            logger.info(f"🔄 Processando pedido alterado: {num_pedido}")
            
            resultado = {
                'sucesso': True,
                'num_pedido': num_pedido,
                'tipo_processamento': None,
                'alteracoes_aplicadas': [],
                'alertas_gerados': [],
                'erros': []
            }
            
            # 1. Identificar todos os lotes relacionados ao pedido
            lotes_afetados = cls._identificar_lotes_afetados(num_pedido)
            
            if not lotes_afetados:
                logger.info(f"Pedido {num_pedido} não tem separações ou pré-separações")
                resultado['tipo_processamento'] = 'SEM_SEPARACAO'
                return resultado
            
            logger.info(f"📋 Processando pedido {num_pedido} com {len(lotes_afetados)} lotes:")
            for lote_info in lotes_afetados:
                logger.info(f"   - Lote {lote_info['lote_id']} tipo {lote_info['tipo']}")
            
            # 2. Processar cada lote
            for info_lote in lotes_afetados:
                lote_id = info_lote['lote_id']
                tipo_lote = info_lote['tipo']  # 'SEPARACAO' ou 'PRE_SEPARACAO'
                
                logger.info(f"Processando lote {lote_id} ({tipo_lote})")
                
                # Detectar se é TOTAL ou PARCIAL
                tipo_separacao = cls._detectar_tipo_separacao(num_pedido, lote_id, tipo_lote)
                
                if tipo_separacao == 'TOTAL':
                    # Caso 1: Separação/PreSeparacao TOTAL - Substituir completamente
                    logger.info(f"Processando SUBSTITUIÇÃO TOTAL de {tipo_lote} no lote {lote_id}")
                    resultado_lote = cls._processar_separacao_total(
                        num_pedido, lote_id, tipo_lote, itens_odoo
                    )
                else:
                    # Caso 2: Separação/PreSeparacao PARCIAL - Aplicar hierarquia
                    logger.info(f"Processando ajuste PARCIAL de {tipo_lote} no lote {lote_id}")
                    resultado_lote = cls._processar_separacao_parcial(
                        num_pedido, lote_id, tipo_lote, itens_odoo
                    )
                
                # Acumular resultados
                resultado['alteracoes_aplicadas'].extend(
                    resultado_lote.get('alteracoes', [])
                )
                resultado['alertas_gerados'].extend(
                    resultado_lote.get('alertas', [])
                )
                if resultado_lote.get('erros'):
                    resultado['erros'].extend(resultado_lote['erros'])
            
            # Determinar tipo de processamento geral
            if any('TOTAL' in alt.get('tipo', '') for alt in resultado['alteracoes_aplicadas']):
                resultado['tipo_processamento'] = 'SUBSTITUICAO_TOTAL'
            else:
                resultado['tipo_processamento'] = 'AJUSTE_PARCIAL'
            
            # Commit se tudo deu certo
            if not resultado['erros']:
                db.session.commit()
                logger.info(f"✅ Pedido {num_pedido} processado com sucesso")
            else:
                db.session.rollback()
                resultado['sucesso'] = False
                logger.error(f"❌ Erros ao processar pedido {num_pedido}")
            
            return resultado
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao processar pedido alterado: {e}")
            return {
                'sucesso': False,
                'num_pedido': num_pedido,
                'erros': [str(e)]
            }
    
    @classmethod
    def _identificar_lotes_afetados(cls, num_pedido: str) -> List[Dict]:
        """
        Identifica todos os lotes (PreSeparacao e Separacao) afetados pelo pedido.
        
        IMPORTANTE: 
        - Quando PreSeparacaoItem vira Separacao, MANTÉM o mesmo separacao_lote_id
        - PreSeparacaoItem muda status para 'ENVIADO_SEPARACAO' quando vira Separacao
        - Precisamos processar APENAS Separacao quando existe (tem prioridade)
        - Se existir PreSeparacao com mesmo lote_id da Separacao, ela será processada junto
        """
        lotes = []
        lotes_processados = set()
        
        # PRIMEIRO: Buscar separações com JOIN em Pedido para filtrar status diretamente
        # Só busca separações onde o Pedido tem status ABERTO ou COTADO
        seps = db.session.query(
            Separacao.separacao_lote_id,
            Pedido.status
        ).outerjoin(
            Pedido,
            Separacao.separacao_lote_id == Pedido.separacao_lote_id
        ).filter(
            Separacao.num_pedido == num_pedido,
            Separacao.separacao_lote_id.isnot(None),
            # PROTEÇÃO: Só pegar separações com Pedido em status alterável
            db.or_(
                Pedido.status.in_(['ABERTO', 'COTADO']),
                Pedido.status.is_(None)  # Ou sem Pedido (pode acontecer)
            )
        ).distinct().all()
        
        for lote_id, status_pedido in seps:
            lotes.append({
                'lote_id': lote_id,
                'tipo': 'SEPARACAO'
            })
            lotes_processados.add(lote_id)
            logger.info(f"Encontrada Separacao com lote {lote_id} (status: {status_pedido or 'SEM_PEDIDO'})")
        
        # Log das separações ignoradas por status
        seps_ignoradas = db.session.query(
            Separacao.separacao_lote_id,
            Pedido.status
        ).join(
            Pedido,
            Separacao.separacao_lote_id == Pedido.separacao_lote_id
        ).filter(
            Separacao.num_pedido == num_pedido,
            Separacao.separacao_lote_id.isnot(None),
            ~Pedido.status.in_(['ABERTO', 'COTADO'])
        ).distinct().all()
        
        for lote_id, status in seps_ignoradas:
            logger.warning(f"🛡️ PROTEÇÃO: Ignorando lote {lote_id} - Pedido com status '{status}' não pode ser alterado")
            lotes_processados.add(lote_id)  # Marcar como processado para não processar PreSeparacao também
        
        # SEGUNDO: Buscar pré-separações com JOIN em Pedido
        pre_seps = db.session.query(
            PreSeparacaoItem.separacao_lote_id,
            Pedido.status
        ).outerjoin(
            Pedido,
            PreSeparacaoItem.separacao_lote_id == Pedido.separacao_lote_id
        ).filter(
            PreSeparacaoItem.num_pedido == num_pedido,
            PreSeparacaoItem.separacao_lote_id.isnot(None),
            # PROTEÇÃO: Só pegar pré-separações com Pedido em status alterável
            db.or_(
                Pedido.status.in_(['ABERTO', 'COTADO']),
                Pedido.status.is_(None)  # Ou sem Pedido
            )
        ).distinct().all()
        
        for lote_id, status_pedido in pre_seps:
            if lote_id not in lotes_processados:
                # Só adiciona se não tem Separacao com mesmo lote
                lotes.append({
                    'lote_id': lote_id,
                    'tipo': 'PRE_SEPARACAO'
                })
                logger.info(f"Encontrada PreSeparacaoItem independente com lote {lote_id} (status: {status_pedido or 'SEM_PEDIDO'})")
            else:
                # Já tem Separacao com este lote - será processada junto automaticamente
                logger.info(f"PreSeparacaoItem com lote {lote_id} será processada junto com Separacao")
        
        if not lotes:
            logger.info(f"Pedido {num_pedido} não tem separações nem pré-separações")
        else:
            logger.info(f"Total de {len(lotes)} lotes únicos para processar")
        
        return lotes
    
    @classmethod
    def _detectar_tipo_separacao(cls, num_pedido: str, lote_id: str, tipo_lote: str) -> str:
        """
        Detecta se uma separação/pré-separação é TOTAL ou PARCIAL.
        
        TOTAL = Contém TODOS os itens e quantidades do pedido
        PARCIAL = Contém apenas PARTE dos itens ou quantidades
        """
        try:
            # Usar no_autoflush para evitar problemas de flush prematuro
            with db.session.no_autoflush:
                # Buscar todos os itens do pedido na carteira
                itens_carteira = CarteiraPrincipal.query.filter_by(
                    num_pedido=num_pedido
                ).all()
                
                if not itens_carteira:
                    return 'PARCIAL'
                
                # Calcular totais do pedido
                totais_pedido = {}
                for item in itens_carteira:
                    cod_produto = item.cod_produto
                    qtd = float(item.qtd_saldo_produto_pedido or 0)
                    if cod_produto not in totais_pedido:
                        totais_pedido[cod_produto] = 0
                    totais_pedido[cod_produto] += qtd
                
                # Calcular totais no lote
                totais_lote = {}
                
                if tipo_lote == 'PRE_SEPARACAO':
                    itens_lote = PreSeparacaoItem.query.filter_by(
                        separacao_lote_id=lote_id,
                        num_pedido=num_pedido
                    ).all()
                    
                    for item in itens_lote:
                        cod_produto = item.cod_produto
                        qtd = float(item.qtd_selecionada_usuario or 0)
                        if cod_produto not in totais_lote:
                            totais_lote[cod_produto] = 0
                        totais_lote[cod_produto] += qtd
                else:
                    itens_lote = Separacao.query.filter_by(
                        separacao_lote_id=lote_id,
                        num_pedido=num_pedido
                    ).all()
                    
                    for item in itens_lote:
                        cod_produto = item.cod_produto
                        qtd = float(item.qtd_saldo or 0)
                        if cod_produto not in totais_lote:
                            totais_lote[cod_produto] = 0
                        totais_lote[cod_produto] += qtd
                
                # Comparar: se tem todos os produtos com quantidades totais = TOTAL
                # 1. Verificar se tem todos os produtos
                produtos_pedido = set(totais_pedido.keys())
                produtos_lote = set(totais_lote.keys())
                
                if produtos_pedido != produtos_lote:
                    logger.info(f"Lote {lote_id} é PARCIAL - produtos diferentes")
                    return 'PARCIAL'
                
                # 2. Verificar se as quantidades são totais
                for cod_produto in produtos_pedido:
                    qtd_pedido = totais_pedido[cod_produto]
                    qtd_lote = totais_lote.get(cod_produto, 0)
                    
                    # Tolerância para comparação de float
                    if abs(qtd_pedido - qtd_lote) > 0.01:
                        logger.info(f"Lote {lote_id} é PARCIAL - qtd diferente em {cod_produto}")
                        return 'PARCIAL'
                
                logger.info(f"Lote {lote_id} é TOTAL")
                return 'TOTAL'
            
        except Exception as e:
            logger.error(f"Erro ao detectar tipo de separação: {e}")
            return 'PARCIAL'  # Na dúvida, trata como parcial
    
    @classmethod
    def _processar_separacao_total(cls, num_pedido: str, lote_id: str, 
                                   tipo_lote: str, itens_odoo: List[Dict]) -> Dict:
        """
        Processa separação/pre-separação TOTAL - substituição completa.
        """
        resultado = {
            'alteracoes': [],
            'alertas': [],
            'erros': []
        }
        
        try:
            # Verificar se está COTADO (só Separacao pode estar COTADA)
            is_cotado = cls._verificar_se_cotado(lote_id)
            
            if tipo_lote == 'SEPARACAO':
                # IMPORTANTE: Se COTADO, capturar dados ANTES de substituir
                itens_antigos = {}
                if is_cotado:
                    # Capturar estado atual ANTES de qualquer modificação
                    from app.separacao.models import Separacao
                    separacoes_antigas = Separacao.query.filter_by(
                        separacao_lote_id=lote_id,
                        num_pedido=num_pedido
                    ).all()
                    
                    for sep in separacoes_antigas:
                        itens_antigos[sep.cod_produto] = {
                            'qtd': float(sep.qtd_saldo or 0),
                            'nome': sep.nome_produto
                        }
                    
                    logger.info(f"📸 Capturados {len(itens_antigos)} itens ANTES da substituição (COTADO)")
                
                # Agora substituir Separacao
                logger.info(f"Substituindo Separacao TOTAL {lote_id} (COTADO={is_cotado})")
                cls._substituir_separacao_total(num_pedido, lote_id, itens_odoo)
                resultado['alteracoes'].append({
                    'tipo': 'SUBSTITUICAO_TOTAL_SEPARACAO',
                    'lote_id': lote_id,
                    'num_pedido': num_pedido,
                    'cotado': is_cotado
                })
                
                # IMPORTANTE: Verificar se existe PreSeparacaoItem com mesmo lote_id e substituir também
                pre_sep_existe = PreSeparacaoItem.query.filter_by(
                    separacao_lote_id=lote_id,
                    num_pedido=num_pedido
                ).first()
                
                if pre_sep_existe:
                    logger.info(f"Encontrada PreSeparacaoItem com mesmo lote {lote_id}, substituindo também")
                    cls._substituir_pre_separacao_total(num_pedido, lote_id, itens_odoo)
                    resultado['alteracoes'].append({
                        'tipo': 'SUBSTITUICAO_TOTAL_PRE_SEPARACAO_VINCULADA',
                        'lote_id': lote_id,
                        'num_pedido': num_pedido,
                        'observacao': 'PreSeparacao vinculada à Separacao substituída'
                    })
                
                # Se COTADO, gerar alertas detalhados para cada produto alterado
                if is_cotado:
                    # Usar os itens_antigos já capturados ANTES da substituição
                    logger.info(f"🔍 Comparando {len(itens_antigos)} itens antigos com novos dados")
                    
                    # Criar mapa dos itens NOVOS
                    itens_novos = {}
                    for item in itens_odoo:
                        cod = item['cod_produto']
                        qtd = float(item.get('qtd_saldo_produto_pedido', 0))
                        if qtd > 0:
                            itens_novos[cod] = {
                                'qtd': qtd,
                                'nome': item.get('nome_produto', cod)
                            }
                    
                    # Gerar alertas para cada mudança
                    todos_produtos = set(itens_antigos.keys()) | set(itens_novos.keys())
                    
                    for cod_produto in todos_produtos:
                        qtd_anterior = itens_antigos.get(cod_produto, {}).get('qtd', 0)
                        qtd_nova = itens_novos.get(cod_produto, {}).get('qtd', 0)
                        nome_produto = itens_antigos.get(cod_produto, {}).get('nome') or itens_novos.get(cod_produto, {}).get('nome', cod_produto)
                        
                        if qtd_anterior != qtd_nova:
                            # Determinar tipo de alteração
                            if qtd_anterior > 0 and qtd_nova == 0:
                                tipo_alt = 'REMOCAO'
                                detalhe = f'Produto {nome_produto} removido'
                            elif qtd_anterior == 0 and qtd_nova > 0:
                                tipo_alt = 'ADICAO'
                                detalhe = f'Produto {nome_produto} adicionado'
                            elif qtd_nova > qtd_anterior:
                                tipo_alt = 'AUMENTO'
                                detalhe = f'Produto {nome_produto} aumentado'
                            else:
                                tipo_alt = 'REDUCAO'
                                detalhe = f'Produto {nome_produto} reduzido'
                            
                            # Criar alerta específico para este produto
                            alerta = AlertaSeparacaoCotada.criar_alerta(
                                separacao_lote_id=lote_id,
                                num_pedido=num_pedido,
                                cod_produto=cod_produto,
                                tipo_alteracao=tipo_alt,
                                qtd_anterior=qtd_anterior,
                                qtd_nova=qtd_nova
                            )
                            alerta.nome_produto = nome_produto
                            alerta.tipo_separacao = 'TOTAL'
                            alerta.observacao = detalhe
                            db.session.add(alerta)
                            resultado['alertas'].append(f"{cod_produto}: {tipo_alt}")
                    
                    logger.warning(f"🚨 ALERTA: Separação COTADA {lote_id} foi substituída com {len(resultado['alertas'])} alterações!")
                    
            elif tipo_lote == 'PRE_SEPARACAO':
                # Só processa se não foi processado como SEPARACAO
                logger.info(f"Substituindo PreSeparacaoItem TOTAL {lote_id}")
                cls._substituir_pre_separacao_total(num_pedido, lote_id, itens_odoo)
                resultado['alteracoes'].append({
                    'tipo': 'SUBSTITUICAO_TOTAL_PRE_SEPARACAO',
                    'lote_id': lote_id,
                    'num_pedido': num_pedido
                })
            
            logger.info(f"✅ {tipo_lote} TOTAL {lote_id} substituída com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao processar separação TOTAL: {e}")
            resultado['erros'].append(str(e))
        
        return resultado
    
    @classmethod
    def _processar_separacao_parcial(cls, num_pedido: str, lote_id: str,
                                     tipo_lote: str, itens_odoo: List[Dict]) -> Dict:
        """
        Processa separação PARCIAL - segue hierarquia de ajuste.
        """
        resultado = {
            'alteracoes': [],
            'alertas': [],
            'erros': []
        }
        
        try:
            # Verificar se está COTADO
            is_cotado = cls._verificar_se_cotado(lote_id)
            
            # Se COTADO e tipo_lote é SEPARACAO, capturar estado antes das mudanças
            itens_antigos = {}
            if is_cotado and tipo_lote == 'SEPARACAO':
                from app.separacao.models import Separacao
                separacoes_antigas = Separacao.query.filter_by(
                    separacao_lote_id=lote_id,
                    num_pedido=num_pedido
                ).all()
                
                for sep in separacoes_antigas:
                    itens_antigos[sep.cod_produto] = {
                        'qtd': float(sep.qtd_saldo or 0),
                        'nome': sep.nome_produto
                    }
                
                logger.info(f"📸 Capturados {len(itens_antigos)} itens ANTES do ajuste PARCIAL (COTADO)")
            
            # Calcular diferenças entre Odoo e sistema atual
            diferencas = cls._calcular_diferencas(num_pedido, itens_odoo)
            
            # Processar reduções seguindo hierarquia
            for reducao in diferencas['reducoes']:
                resultado_red = cls._aplicar_reducao_hierarquia(
                    num_pedido, 
                    reducao['cod_produto'],
                    reducao['qtd_reduzir']
                )
                resultado['alteracoes'].append(resultado_red)
                if resultado_red.get('alerta_id'):
                    resultado['alertas'].append(resultado_red['alerta_id'])
            
            # Processar aumentos (sempre vão para saldo livre)
            for aumento in diferencas['aumentos']:
                logger.info(f"Aumento de {aumento['qtd_aumentar']} em {aumento['cod_produto']} - vai para saldo livre")
                resultado['alteracoes'].append({
                    'tipo': 'AUMENTO_SALDO_LIVRE',
                    'cod_produto': aumento['cod_produto'],
                    'quantidade': aumento['qtd_aumentar']
                })
            
            # Processar novos itens (sempre vão para saldo livre)
            for novo in diferencas['novos']:
                logger.info(f"Novo item {novo['cod_produto']} - vai para saldo livre")
                resultado['alteracoes'].append({
                    'tipo': 'NOVO_ITEM_SALDO_LIVRE',
                    'cod_produto': novo['cod_produto'],
                    'quantidade': novo['quantidade']
                })
            
            # Se COTADO e tipo SEPARACAO, gerar alertas para todas as alterações
            if is_cotado and tipo_lote == 'SEPARACAO' and itens_antigos:
                logger.info(f"🚨 Gerando alertas para separação COTADA PARCIAL {lote_id}")
                
                # Criar mapa dos itens NOVOS após as modificações
                from app.separacao.models import Separacao
                itens_novos = {}
                separacoes_novas = Separacao.query.filter_by(
                    separacao_lote_id=lote_id,
                    num_pedido=num_pedido
                ).all()
                
                for sep in separacoes_novas:
                    itens_novos[sep.cod_produto] = {
                        'qtd': float(sep.qtd_saldo or 0),
                        'nome': sep.nome_produto
                    }
                
                # Comparar e gerar alertas
                todos_produtos = set(itens_antigos.keys()) | set(itens_novos.keys())
                
                for cod_produto in todos_produtos:
                    qtd_anterior = itens_antigos.get(cod_produto, {}).get('qtd', 0)
                    qtd_nova = itens_novos.get(cod_produto, {}).get('qtd', 0)
                    nome_produto = itens_antigos.get(cod_produto, {}).get('nome') or itens_novos.get(cod_produto, {}).get('nome', cod_produto)
                    
                    if qtd_anterior != qtd_nova:
                        # Determinar tipo de alteração
                        if qtd_anterior > 0 and qtd_nova == 0:
                            tipo_alt = 'REMOCAO'
                            detalhe = f'Produto {nome_produto} removido (ajuste parcial)'
                        elif qtd_anterior == 0 and qtd_nova > 0:
                            tipo_alt = 'ADICAO'
                            detalhe = f'Produto {nome_produto} adicionado (ajuste parcial)'
                        elif qtd_nova > qtd_anterior:
                            tipo_alt = 'AUMENTO'
                            detalhe = f'Produto {nome_produto} aumentado (ajuste parcial)'
                        else:
                            tipo_alt = 'REDUCAO'
                            detalhe = f'Produto {nome_produto} reduzido (ajuste parcial)'
                        
                        # Criar alerta
                        alerta = AlertaSeparacaoCotada.criar_alerta(
                            separacao_lote_id=lote_id,
                            num_pedido=num_pedido,
                            cod_produto=cod_produto,
                            tipo_alteracao=tipo_alt,
                            qtd_anterior=qtd_anterior,
                            qtd_nova=qtd_nova
                        )
                        alerta.nome_produto = nome_produto
                        alerta.tipo_separacao = 'PARCIAL'
                        alerta.observacao = detalhe
                        db.session.add(alerta)
                        resultado['alertas'].append(f"{cod_produto}: {tipo_alt}")
                
                if resultado['alertas']:
                    logger.warning(f"🚨 ALERTA: Separação COTADA PARCIAL {lote_id} foi alterada com {len(resultado['alertas'])} mudanças!")
            
            logger.info(f"✅ Separação PARCIAL {lote_id} processada com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao processar separação PARCIAL: {e}")
            resultado['erros'].append(str(e))
        
        return resultado
    
    @classmethod
    def _substituir_pre_separacao_total(cls, num_pedido: str, lote_id: str, itens_odoo: List[Dict]):
        """
        Substitui completamente uma pré-separação TOTAL.
        Pega 1 linha existente como modelo, deleta tudo e recria com os novos itens.
        """
        # PROTEÇÃO: Verificar se o Pedido permite alteração
        pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()
        if pedido and pedido.status not in ['ABERTO', 'COTADO']:
            logger.warning(f"🛡️ PROTEÇÃO: Não alterando PreSeparacao {lote_id} - Pedido com status '{pedido.status}'")
            return
            
        # 1. Pegar primeira linha existente como modelo (tem todos os campos preenchidos)
        modelo = PreSeparacaoItem.query.filter_by(
            separacao_lote_id=lote_id,
            num_pedido=num_pedido
        ).first()
        
        if not modelo:
            logger.error(f"Não encontrou modelo de PreSeparacaoItem para lote {lote_id}")
            return
        
        # 2. Guardar os campos do modelo que vamos reutilizar
        campos_modelo = {
            'separacao_lote_id': modelo.separacao_lote_id,
            'cnpj_cliente': modelo.cnpj_cliente,
            'data_expedicao_editada': modelo.data_expedicao_editada,
            'data_agendamento_editada': modelo.data_agendamento_editada,
            'protocolo_editado': modelo.protocolo_editado,
            'observacoes_usuario': modelo.observacoes_usuario,
            'tipo_envio': modelo.tipo_envio,
            'status': modelo.status,
            'criado_por': modelo.criado_por,
            'recomposto': modelo.recomposto,
            'recomposto_por': modelo.recomposto_por,
            'data_recomposicao': modelo.data_recomposicao,
            'versao_carteira_original': modelo.versao_carteira_original,
            'versao_carteira_recomposta': modelo.versao_carteira_recomposta
        }
        
        # 3. Deletar TODOS os itens existentes
        PreSeparacaoItem.query.filter_by(
            separacao_lote_id=lote_id,
            num_pedido=num_pedido
        ).delete()
        
        # 4. Criar novos itens usando o modelo + dados do Odoo
        for item_odoo in itens_odoo:
            qtd = float(item_odoo.get('qtd_saldo_produto_pedido', 0))
            if qtd <= 0:
                continue
            
            # Criar novo item com esqueleto do modelo + dados novos do Odoo
            novo_item = PreSeparacaoItem(
                # Campos do modelo preservados
                separacao_lote_id=campos_modelo['separacao_lote_id'],
                cnpj_cliente=campos_modelo['cnpj_cliente'],
                data_expedicao_editada=campos_modelo['data_expedicao_editada'],
                data_agendamento_editada=campos_modelo['data_agendamento_editada'],
                protocolo_editado=campos_modelo['protocolo_editado'],
                observacoes_usuario=campos_modelo['observacoes_usuario'],
                tipo_envio=campos_modelo['tipo_envio'],
                status=campos_modelo['status'],
                criado_por=campos_modelo['criado_por'],
                recomposto=campos_modelo['recomposto'],
                recomposto_por=campos_modelo['recomposto_por'],
                data_recomposicao=campos_modelo['data_recomposicao'],
                versao_carteira_original=campos_modelo['versao_carteira_original'],
                versao_carteira_recomposta=campos_modelo['versao_carteira_recomposta'],
                
                # Dados do pedido
                num_pedido=num_pedido,
                
                # Dados novos do Odoo
                cod_produto=item_odoo['cod_produto'],
                nome_produto=item_odoo.get('nome_produto', ''),
                qtd_original_carteira=Decimal(str(item_odoo.get('qtd_produto_pedido', 0))),
                qtd_selecionada_usuario=Decimal(str(qtd)),
                qtd_restante_calculada=Decimal('0'),
                
                # Recalcular valores com base na quantidade
                valor_original_item=Decimal(str(qtd * float(item_odoo.get('preco_produto_pedido', 0)))),
                peso_original_item=Decimal(str(qtd * float(item_odoo.get('peso_unitario_produto', 0)))),
                
                # Hash e data de criação
                hash_item_original=None,
                data_criacao=datetime.now(timezone.utc)
            )
            db.session.add(novo_item)
    
    @classmethod
    def _substituir_separacao_total(cls, num_pedido: str, lote_id: str, itens_odoo: List[Dict]):
        """
        Substitui completamente uma separação TOTAL.
        Pega 1 linha existente como modelo, deleta tudo e recria com os novos itens.
        """
        # PROTEÇÃO: Verificar se o Pedido permite alteração
        pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()
        if pedido and pedido.status not in ['ABERTO', 'COTADO']:
            logger.warning(f"🛡️ PROTEÇÃO: Não alterando Separacao {lote_id} - Pedido com status '{pedido.status}'")
            return
            
        # 1. Pegar primeira linha existente como modelo
        modelo = Separacao.query.filter_by(
            separacao_lote_id=lote_id,
            num_pedido=num_pedido
        ).first()
        
        if not modelo:
            logger.error(f"Não encontrou modelo de Separacao para lote {lote_id}")
            return
        
        # 2. Guardar os campos do modelo que vamos reutilizar
        campos_modelo = {
            'separacao_lote_id': modelo.separacao_lote_id,
            'cnpj_cpf': modelo.cnpj_cpf,
            'raz_social_red': modelo.raz_social_red,
            'nome_cidade': modelo.nome_cidade,
            'cod_uf': modelo.cod_uf,
            'data_pedido': modelo.data_pedido,
            'expedicao': modelo.expedicao,
            'agendamento': modelo.agendamento,
            'protocolo': modelo.protocolo,
            'observ_ped_1': modelo.observ_ped_1,
            'roteirizacao': modelo.roteirizacao,
            'rota': modelo.rota,
            'sub_rota': modelo.sub_rota,
            'tipo_envio': modelo.tipo_envio,
            'criado_em': modelo.criado_em
        }
        
        # 3. Deletar TODOS os itens existentes
        Separacao.query.filter_by(
            separacao_lote_id=lote_id,
            num_pedido=num_pedido
        ).delete()
        
        # Importar CadastroPalletizacao uma vez
        from app.producao.models import CadastroPalletizacao
        
        # 4. Criar novos itens usando o modelo + dados do Odoo
        for item_odoo in itens_odoo:
            qtd = float(item_odoo.get('qtd_saldo_produto_pedido', 0))
            if qtd <= 0:
                continue
            
            # Buscar palletização do produto
            palletizacao = CadastroPalletizacao.query.filter_by(
                cod_produto=item_odoo['cod_produto']
            ).first()
            
            # Calcular pallets: qtd / palletizacao
            qtd_pallets = 0
            if palletizacao and palletizacao.palletizacao and palletizacao.palletizacao > 0:
                qtd_pallets = qtd / float(palletizacao.palletizacao)
            
            # Criar novo item com esqueleto do modelo + dados novos do Odoo
            novo_item = Separacao(
                # Campos do modelo preservados
                separacao_lote_id=campos_modelo['separacao_lote_id'],
                cnpj_cpf=campos_modelo['cnpj_cpf'],
                raz_social_red=campos_modelo['raz_social_red'],
                nome_cidade=campos_modelo['nome_cidade'],
                cod_uf=campos_modelo['cod_uf'],
                data_pedido=campos_modelo['data_pedido'],
                expedicao=campos_modelo['expedicao'],
                agendamento=campos_modelo['agendamento'],
                protocolo=campos_modelo['protocolo'],
                observ_ped_1=campos_modelo['observ_ped_1'],
                roteirizacao=campos_modelo['roteirizacao'],
                rota=campos_modelo['rota'],
                sub_rota=campos_modelo['sub_rota'],
                tipo_envio=campos_modelo['tipo_envio'],
                
                # Dados do pedido
                num_pedido=num_pedido,
                
                # Dados novos do Odoo
                cod_produto=item_odoo['cod_produto'],
                nome_produto=item_odoo.get('nome_produto', ''),
                qtd_saldo=qtd,
                
                # Recalcular valores com base na quantidade
                valor_saldo=qtd * float(item_odoo.get('preco_produto_pedido', 0)),
                peso=qtd * float(item_odoo.get('peso_unitario_produto', 0)),
                pallet=qtd_pallets,  # Usando cálculo correto
                
                # Data de criação
                criado_em=datetime.now(timezone.utc)
            )
            db.session.add(novo_item)
    
    @classmethod
    def _calcular_diferencas(cls, num_pedido: str, itens_odoo: List[Dict]) -> Dict:
        """
        Calcula diferenças entre Odoo e sistema atual.
        """
        diferencas = {
            'reducoes': [],
            'aumentos': [],
            'removidos': [],
            'novos': []
        }
        
        # Buscar situação atual no sistema (carteira + separações)
        itens_sistema = {}
        
        # Somar quantidades na carteira
        itens_carteira = CarteiraPrincipal.query.filter_by(
            num_pedido=num_pedido
        ).all()
        
        for item in itens_carteira:
            cod_produto = item.cod_produto
            qtd = float(item.qtd_saldo_produto_pedido or 0)
            if cod_produto not in itens_sistema:
                itens_sistema[cod_produto] = 0
            itens_sistema[cod_produto] += qtd
        
        # Preparar itens do Odoo
        itens_odoo_dict = {}
        for item in itens_odoo:
            cod_produto = item['cod_produto']
            qtd = float(item.get('qtd_saldo_produto_pedido', 0))
            if cod_produto not in itens_odoo_dict:
                itens_odoo_dict[cod_produto] = 0
            itens_odoo_dict[cod_produto] += qtd
        
        # Comparar
        todos_produtos = set(itens_sistema.keys()) | set(itens_odoo_dict.keys())
        
        for cod_produto in todos_produtos:
            qtd_sistema = itens_sistema.get(cod_produto, 0)
            qtd_odoo = itens_odoo_dict.get(cod_produto, 0)
            
            if qtd_odoo < qtd_sistema:
                # Redução ou remoção
                if qtd_odoo == 0:
                    diferencas['removidos'].append({
                        'cod_produto': cod_produto,
                        'qtd_remover': qtd_sistema
                    })
                else:
                    diferencas['reducoes'].append({
                        'cod_produto': cod_produto,
                        'qtd_reduzir': qtd_sistema - qtd_odoo,
                        'qtd_anterior': qtd_sistema,
                        'qtd_nova': qtd_odoo
                    })
            elif qtd_odoo > qtd_sistema:
                # Aumento ou novo
                if qtd_sistema == 0:
                    diferencas['novos'].append({
                        'cod_produto': cod_produto,
                        'quantidade': qtd_odoo
                    })
                else:
                    diferencas['aumentos'].append({
                        'cod_produto': cod_produto,
                        'qtd_aumentar': qtd_odoo - qtd_sistema,
                        'qtd_anterior': qtd_sistema,
                        'qtd_nova': qtd_odoo
                    })
        
        return diferencas
    
    @classmethod
    def _aplicar_reducao_hierarquia(cls, num_pedido: str, cod_produto: str, qtd_reduzir: float) -> Dict:
        """
        Aplica redução seguindo a hierarquia:
        1. Saldo livre
        2. PreSeparacaoItem
        3. Separacao não COTADA
        4. Separacao COTADA
        """
        resultado = {
            'tipo': 'REDUCAO_HIERARQUIA',
            'cod_produto': cod_produto,
            'qtd_solicitada': qtd_reduzir,
            'qtd_aplicada': 0,
            'operacoes': [],
            'alerta_id': None
        }
        
        qtd_restante = qtd_reduzir
        
        # 1. Consumir do saldo livre (CarteiraPrincipal sem lote)
        itens_livres = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.separacao_lote_id.is_(None)
        ).all()
        
        for item in itens_livres:
            if qtd_restante <= 0:
                break
            
            qtd_item = float(item.qtd_saldo_produto_pedido or 0)
            if qtd_item > 0:
                qtd_consumir = min(qtd_item, qtd_restante)
                item.qtd_saldo_produto_pedido = Decimal(str(qtd_item - qtd_consumir))
                qtd_restante -= qtd_consumir
                resultado['operacoes'].append(f"Saldo livre reduzido em {qtd_consumir}")
                resultado['qtd_aplicada'] += qtd_consumir
        
        # 2. Consumir de PreSeparacaoItem
        if qtd_restante > 0:
            pre_seps = PreSeparacaoItem.query.filter(
                PreSeparacaoItem.num_pedido == num_pedido,
                PreSeparacaoItem.cod_produto == cod_produto
            ).order_by(PreSeparacaoItem.data_criacao.desc()).all()
            
            for pre_sep in pre_seps:
                if qtd_restante <= 0:
                    break
                
                qtd_item = float(pre_sep.qtd_selecionada_usuario or 0)
                if qtd_item > 0:
                    qtd_consumir = min(qtd_item, qtd_restante)
                    pre_sep.qtd_selecionada_usuario = Decimal(str(qtd_item - qtd_consumir))
                    qtd_restante -= qtd_consumir
                    resultado['operacoes'].append(f"Pré-separação {pre_sep.separacao_lote_id} reduzida em {qtd_consumir}")
                    resultado['qtd_aplicada'] += qtd_consumir
                    
                    # Se zerou, deletar
                    if pre_sep.qtd_selecionada_usuario <= 0:
                        db.session.delete(pre_sep)
                        resultado['operacoes'].append(f"Pré-separação {pre_sep.separacao_lote_id} removida")
        
        # 3. Consumir de Separacao não COTADA
        if qtd_restante > 0:
            # Buscar separações e verificar status via Pedido
            separacoes = Separacao.query.filter(
                Separacao.num_pedido == num_pedido,
                Separacao.cod_produto == cod_produto
            ).all()
            
            for sep in separacoes:
                if qtd_restante <= 0:
                    break
                
                # PROTEÇÃO: Verificar status do Pedido
                pedido = Pedido.query.filter_by(separacao_lote_id=sep.separacao_lote_id).first()
                if pedido and pedido.status not in ['ABERTO', 'COTADO']:
                    logger.warning(f"🛡️ Ignorando Separacao {sep.separacao_lote_id} - Pedido com status '{pedido.status}'")
                    continue
                
                # Verificar se está COTADO
                is_cotado = cls._verificar_se_cotado(sep.separacao_lote_id)
                
                if not is_cotado:
                    qtd_item = float(sep.qtd_saldo or 0)
                    if qtd_item > 0:
                        qtd_consumir = min(qtd_item, qtd_restante)
                        sep.qtd_saldo = Decimal(str(qtd_item - qtd_consumir))
                        qtd_restante -= qtd_consumir
                        resultado['operacoes'].append(f"Separação {sep.separacao_lote_id} (ABERTO) reduzida em {qtd_consumir}")
                        resultado['qtd_aplicada'] += qtd_consumir
                        
                        # Se zerou, deletar
                        if sep.qtd_saldo <= 0:
                            db.session.delete(sep)
                            resultado['operacoes'].append(f"Separação {sep.separacao_lote_id} removida")
        
        # 4. Consumir de Separacao COTADA (último recurso)
        if qtd_restante > 0:
            separacoes = Separacao.query.filter(
                Separacao.num_pedido == num_pedido,
                Separacao.cod_produto == cod_produto
            ).all()
            
            for sep in separacoes:
                if qtd_restante <= 0:
                    break
                
                # PROTEÇÃO: Verificar status do Pedido
                pedido = Pedido.query.filter_by(separacao_lote_id=sep.separacao_lote_id).first()
                if pedido and pedido.status not in ['ABERTO', 'COTADO']:
                    logger.warning(f"🛡️ Ignorando Separacao COTADA {sep.separacao_lote_id} - Pedido com status '{pedido.status}'")
                    continue
                
                # Verificar se está COTADO
                is_cotado = cls._verificar_se_cotado(sep.separacao_lote_id)
                
                if is_cotado:
                    qtd_item = float(sep.qtd_saldo or 0)
                    if qtd_item > 0:
                        qtd_consumir = min(qtd_item, qtd_restante)
                        sep.qtd_saldo = Decimal(str(qtd_item - qtd_consumir))
                        qtd_restante -= qtd_consumir
                        resultado['operacoes'].append(f"⚠️ Separação {sep.separacao_lote_id} (COTADO) reduzida em {qtd_consumir}")
                        resultado['qtd_aplicada'] += qtd_consumir
                        
                        # Gerar alerta
                        alerta = cls._gerar_alerta_cotado(
                            sep.separacao_lote_id,
                            num_pedido,
                            tipo_alteracao='REDUCAO_PARCIAL',
                            detalhes=f'Produto {cod_produto} reduzido em {qtd_consumir} unidades',
                            cod_produto=cod_produto,
                            qtd_anterior=qtd_item,
                            qtd_nova=qtd_item - qtd_consumir
                        )
                        resultado['alerta_id'] = alerta.id
                        
                        # Se zerou, deletar
                        if sep.qtd_saldo <= 0:
                            db.session.delete(sep)
                            resultado['operacoes'].append(f"Separação {sep.separacao_lote_id} removida")
        
        return resultado
    
    @classmethod
    def _verificar_se_cotado(cls, lote_id: str) -> bool:
        """
        Verifica se uma separação está COTADA verificando:
        1. Status do Pedido
        2. Se está em EmbarqueItem ativo
        """
        # Verificar pelo Pedido
        pedido = Pedido.query.filter_by(
            separacao_lote_id=lote_id
        ).first()
        
        if pedido and pedido.status == 'COTADO':
            return True
        
        # Verificar se está em embarque ativo
        embarque_item = db.session.query(EmbarqueItem).join(
            Embarque,
            EmbarqueItem.embarque_id == Embarque.id
        ).filter(
            EmbarqueItem.separacao_lote_id == lote_id,
            EmbarqueItem.status == 'ativo',
            Embarque.status == 'ativo'
        ).first()
        
        if embarque_item:
            return True
        
        return False
    
    @classmethod
    def _gerar_alerta_cotado(cls, lote_id: str, num_pedido: str, 
                            tipo_alteracao: str, detalhes: str,
                            cod_produto: str = None,
                            qtd_anterior: float = None,
                            qtd_nova: float = None) -> AlertaSeparacaoCotada:
        """
        Gera alerta para separação COTADA alterada.
        """
        # Mapear tipo_alteracao para os valores esperados pela tabela
        tipo_map = {
            'SUBSTITUICAO_TOTAL': 'REMOCAO',  # Substituição total é como remover e adicionar
            'REDUCAO_PARCIAL': 'REDUCAO'
        }
        tipo_alteracao_db = tipo_map.get(tipo_alteracao, tipo_alteracao)
        
        alerta = AlertaSeparacaoCotada(
            separacao_lote_id=lote_id,
            num_pedido=num_pedido,
            cod_produto=cod_produto or 'TODOS',
            tipo_alteracao=tipo_alteracao_db,
            qtd_anterior=qtd_anterior or 0,
            qtd_nova=qtd_nova or 0,
            qtd_diferenca=(qtd_nova or 0) - (qtd_anterior or 0),
            tipo_separacao='TOTAL' if 'TOTAL' in tipo_alteracao else 'PARCIAL',
            observacao=detalhes,
            data_alerta=datetime.now(timezone.utc),
            reimpresso=False  # Campo correto ao invés de 'visualizado'
        )
        db.session.add(alerta)
        db.session.flush()  # Para obter o ID
        
        logger.warning(f"🚨 ALERTA GERADO: {detalhes}")
        
        return alerta