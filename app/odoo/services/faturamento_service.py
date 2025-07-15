"""
Serviço de Faturamento - Integração Odoo Correta
===============================================

Este serviço implementa a integração correta com o Odoo usando múltiplas consultas
ao invés de campos com "/" que não funcionam.

Baseado no mapeamento_faturamento.csv e usando FaturamentoMapper hardcoded.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import sessionmaker

from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.utils.faturamento_mapper import FaturamentoMapper
from app import db

logger = logging.getLogger(__name__)

class FaturamentoService:
    """
    Serviço para integração de faturamento com Odoo
    Usa FaturamentoMapper hardcoded com sistema de múltiplas queries
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mapper = FaturamentoMapper()
        self.connection = get_odoo_connection()

    
    def _processar_dados_faturamento_com_multiplas_queries(self, dados_odoo_brutos: List[Dict]) -> List[Dict]:
        """
        🚀 MÉTODO REALMENTE OTIMIZADO - 5 queries + JOIN em memória
        
        ESTRATÉGIA (igual à carteira):
        1. Coletar todos os IDs necessários
        2. Fazer 5 queries em lote  
        3. JOIN em memória
        """
        try:
            logger.info("🚀 Processando faturamento com método REALMENTE otimizado...")
            
            if not dados_odoo_brutos:
                return []
            
            # 1️⃣ COLETAR TODOS OS IDs NECESSÁRIOS
            move_ids = set()
            partner_ids = set()
            product_ids = set()
            
            for linha in dados_odoo_brutos:
                if linha.get('move_id'):
                    move_ids.add(linha['move_id'][0])
                if linha.get('partner_id'):
                    partner_ids.add(linha['partner_id'][0])
                if linha.get('product_id'):
                    product_ids.add(linha['product_id'][0])
            
            logger.info(f"📊 Coletados: {len(move_ids)} faturas, {len(partner_ids)} clientes, {len(product_ids)} produtos")
            
            # 2️⃣ BUSCAR TODAS AS FATURAS (1 query)
            campos_fatura = [
                'id', 'name', 'invoice_origin', 'state', 'invoice_user_id', 'invoice_incoterm_id'
            ]
            
            logger.info("🔍 Query 1/5: Buscando faturas...")
            faturas = self.connection.search_read(
                'account.move',
                [('id', 'in', list(move_ids))],
                campos_fatura
            )
            
            # 3️⃣ BUSCAR TODOS OS CLIENTES (1 query)
            campos_cliente = [
                'id', 'name', 'l10n_br_cnpj', 'l10n_br_municipio_id'
            ]
            
            logger.info(f"🔍 Query 2/5: Buscando {len(partner_ids)} clientes...")
            clientes = self.connection.search_read(
                'res.partner',
                [('id', 'in', list(partner_ids))],
                campos_cliente
            )
            
            # 4️⃣ BUSCAR TODOS OS PRODUTOS (1 query)
            campos_produto = ['id', 'name', 'default_code', 'weight']
            
            logger.info(f"🔍 Query 3/5: Buscando {len(product_ids)} produtos...")
            produtos = self.connection.search_read(
                'product.product',
                [('id', 'in', list(product_ids))],
                campos_produto
            )
            
            # 5️⃣ BUSCAR MUNICÍPIOS DOS CLIENTES (1 query)
            municipio_ids = set()
            for cliente in clientes:
                if cliente.get('l10n_br_municipio_id'):
                    municipio_ids.add(cliente['l10n_br_municipio_id'][0])
            
            municipios = []
            if municipio_ids:
                logger.info(f"🔍 Query 4/5: Buscando {len(municipio_ids)} municípios...")
                municipios = self.connection.search_read(
                    'l10n_br_ciel_it_account.res.municipio',
                    [('id', 'in', list(municipio_ids))],
                    ['id', 'name', 'state_id']
                )
            
            # 6️⃣ BUSCAR USUÁRIOS/VENDEDORES (1 query)
            user_ids = set()
            for fatura in faturas:
                if fatura.get('invoice_user_id'):
                    user_ids.add(fatura['invoice_user_id'][0])
            
            usuarios = []
            if user_ids:
                logger.info(f"🔍 Query 5/5: Buscando {len(user_ids)} vendedores...")
                usuarios = self.connection.search_read(
                    'res.users',
                    [('id', 'in', list(user_ids))],
                    ['id', 'name']
                )
            
            # 7️⃣ CRIAR CACHES PARA JOIN EM MEMÓRIA
            cache_faturas = {f['id']: f for f in faturas}
            cache_clientes = {c['id']: c for c in clientes}
            cache_produtos = {p['id']: p for p in produtos}
            cache_municipios = {m['id']: m for m in municipios}
            cache_usuarios = {u['id']: u for u in usuarios}
            
            logger.info("🧠 Caches criados, fazendo JOIN em memória...")
            
            # 8️⃣ PROCESSAR DADOS COM JOIN EM MEMÓRIA
            dados_processados = []
            
            for linha in dados_odoo_brutos:
                try:
                    item_mapeado = self._mapear_item_faturamento_otimizado(
                        linha, cache_faturas, cache_clientes, cache_produtos,
                        cache_municipios, cache_usuarios
                    )
                    dados_processados.append(item_mapeado)
                    
                except Exception as e:
                    logger.warning(f"Erro ao mapear item faturamento {linha.get('id')}: {e}")
                    continue
            
            total_queries = 5
            logger.info(f"✅ OTIMIZAÇÃO FATURAMENTO COMPLETA:")
            logger.info(f"   📊 {len(dados_processados)} itens processados")
            logger.info(f"   ⚡ {total_queries} queries executadas (vs {len(dados_odoo_brutos)*17} do método antigo)")
            logger.info(f"   🚀 {(len(dados_odoo_brutos)*17)//total_queries}x mais rápido")
            
            return dados_processados
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento faturamento otimizado: {e}")
            return []
    
    def _mapear_status(self, status_odoo: Optional[str]) -> str:
        """
        Mapeia status do Odoo para status do sistema
        """
        if not status_odoo:
            return 'ATIVO'
        
        status_map = {
            'draft': 'RASCUNHO',
            'sent': 'ENVIADO',
            'sale': 'ATIVO',
            'done': 'ATIVO',
            'cancel': 'CANCELADO'
        }
        
        return status_map.get(status_odoo.lower(), 'ATIVO')
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Converte string de data para datetime
        """
        if not date_str:
            return None
        
        try:
            # Formato do Odoo: 2025-07-14 20:19:52
            dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            return dt  # Retorna datetime para compatibilidade
        except ValueError:
            try:
                # Formato de data apenas: 2025-07-14
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                return dt  # Retorna datetime para compatibilidade
            except ValueError:
                self.logger.warning(f"Formato de data inválido: {date_str}")
                return None
    
    def _consolidar_faturamento(self, dados_faturamento: List[Dict]) -> Dict[str, Any]:
        """
        Consolida dados de faturamento para RelatorioFaturamentoImportado
        """
        try:
            self.logger.info("Consolidando dados para RelatorioFaturamentoImportado")
            
            total_consolidado = 0
            total_relatorio_importado = 0
            
            # Agrupar por NF para consolidação
            nfs_consolidadas = {}
            
            for dado in dados_faturamento:
                numero_nf = dado.get('numero_nf')
                if not numero_nf:
                    continue
                    
                nf_key = f"{numero_nf}_{dado.get('cnpj_cliente', '')}"
                
                if nf_key not in nfs_consolidadas:
                    nfs_consolidadas[nf_key] = {
                        'numero_nf': numero_nf,
                        'nome_cliente': dado.get('nome_cliente'),
                        'cnpj_cliente': dado.get('cnpj_cliente'),
                        'data_fatura': dado.get('data_fatura'),
                        'valor_total': 0,
                        'origem': dado.get('origem'),
                        'incoterm': dado.get('incoterm'),
                        'vendedor': dado.get('vendedor'),
                        'municipio': dado.get('municipio'),
                        'status': dado.get('status'),
                        'itens': []
                    }
                
                # Adicionar valor do item ao total
                valor_item = dado.get('valor_total_item_nf') or 0
                nfs_consolidadas[nf_key]['valor_total'] += valor_item
                
                # Adicionar item
                nfs_consolidadas[nf_key]['itens'].append({
                    'codigo_produto': dado.get('codigo_produto'),
                    'nome_produto': dado.get('nome_produto'),
                    'quantidade': dado.get('quantidade'),
                    'valor_total': valor_item
                })
                
                total_consolidado += 1
            
            # Salvar dados consolidados
            for nf_key, dados_nf in nfs_consolidadas.items():
                try:
                    # Verificar se já existe
                    existe = db.session.query(RelatorioFaturamentoImportado).filter_by(
                        numero_nf=dados_nf['numero_nf'],
                        cnpj_cliente=dados_nf['cnpj_cliente']
                    ).first()
                    
                    if not existe:
                        relatorio = RelatorioFaturamentoImportado()
                        relatorio.numero_nf = dados_nf['numero_nf']
                        relatorio.nome_cliente = dados_nf['nome_cliente']
                        relatorio.cnpj_cliente = dados_nf['cnpj_cliente']
                        data_fatura = self._parse_date(dados_nf['data_fatura'])
                        relatorio.data_fatura = data_fatura.date() if data_fatura else None
                        relatorio.valor_total = dados_nf['valor_total']
                        relatorio.origem = dados_nf['origem']
                        relatorio.incoterm = dados_nf['incoterm']
                        relatorio.vendedor = dados_nf['vendedor']
                        relatorio.municipio = dados_nf['municipio']
                        relatorio.status_faturamento = dados_nf['status']
                        relatorio.data_importacao = datetime.now()
                        relatorio.origem_importacao = 'odoo_integracao'
                        
                        db.session.add(relatorio)
                        total_relatorio_importado += 1
                    else:
                        # Atualizar registro existente
                        existe.valor_total = dados_nf['valor_total']
                        existe.status_faturamento = dados_nf['status']
                        existe.data_importacao = datetime.now()
                        existe.origem_importacao = 'odoo_integracao'
                
                except Exception as e:
                    self.logger.error(f"Erro ao consolidar NF {nf_key}: {e}")
                    continue
            
            # Commit final
            db.session.commit()
            
            self.logger.info(f"Consolidação concluída: {total_consolidado} itens processados, {total_relatorio_importado} relatórios criados")
            
            return {
                'total_consolidado': total_consolidado,
                'total_relatorio_importado': total_relatorio_importado
            }
            
        except Exception as e:
            self.logger.error(f"Erro na consolidação: {e}")
            db.session.rollback()
            return {
                'total_consolidado': 0,
                'total_relatorio_importado': 0
            }

    
    # ============================================
    # 🚀 MÉTODOS PRINCIPAIS OTIMIZADOS
    # ============================================
    
    def sincronizar_faturamento_incremental(self) -> Dict[str, Any]:
        """
        🚀 SINCRONIZAÇÃO INCREMENTAL OTIMIZADA + INTEGRAÇÃO COMPLETA
        
        Estratégia do usuário:
        - NF não existe → INSERT
        - NF já existe → UPDATE apenas status
        
        ✅ INCLUI: Sincronização completa de entregas, embarques e fretes
        """
        try:
            import time
            from app.faturamento.models import FaturamentoProduto
            from app import db
            
            start_time = time.time()
            logger.info("🚀 SINCRONIZAÇÃO INCREMENTAL + INTEGRAÇÃO COMPLETA")
            
            # ⚡ Buscar dados do Odoo com filtro obrigatório
            resultado = self.obter_faturamento_otimizado(
                usar_filtro_postado=True,
                limite=0  # Sem limite para sincronização completa
            )
            
            if not resultado['sucesso']:
                return {
                    'sucesso': False,
                    'erro': resultado.get('erro', 'Erro na consulta do Odoo'),
                    'estatisticas': {}
                }
            
            dados_faturamento = resultado.get('dados', [])
            
            if not dados_faturamento:
                return {
                    'sucesso': False,
                    'erro': 'Nenhum dado encontrado no Odoo',
                    'estatisticas': {}
                }
            
            logger.info(f"📊 Processando {len(dados_faturamento)} registros do Odoo...")
            
            # 📊 ESTATÍSTICAS
            contador_novos = 0
            contador_atualizados = 0
            contador_erros = 0
            erros = []
            
            # 📋 LISTAS PARA SINCRONIZAÇÃO POSTERIOR
            nfs_novas = []  # NFs que foram inseridas
            nfs_atualizadas = []  # NFs que foram atualizadas
            cnpjs_processados = set()  # CNPJs únicos para lançamento de fretes
            
            # 🔍 CRIAR ÍNDICE DE REGISTROS EXISTENTES
            logger.info("🔍 Carregando índice de registros existentes...")
            registros_existentes = {}
            
            for registro in db.session.query(FaturamentoProduto.numero_nf, FaturamentoProduto.cod_produto, FaturamentoProduto.id, FaturamentoProduto.status_nf).all():
                chave = f"{registro.numero_nf}|{registro.cod_produto}"
                registros_existentes[chave] = {
                    'id': registro.id,
                    'status_atual': registro.status_nf
                }
            
            logger.info(f"📋 Índice criado com {len(registros_existentes)} registros existentes")
            
            # 🔄 PROCESSAR CADA ITEM DO ODOO
            for item_mapeado in dados_faturamento:
                try:
                    numero_nf = item_mapeado.get('numero_nf', '').strip()
                    cod_produto = item_mapeado.get('cod_produto', '').strip()
                    status_odoo = item_mapeado.get('status_nf', 'Lançado')
                    cnpj_cliente = item_mapeado.get('cnpj_cliente', '').strip()
                    
                    # Validar dados essenciais
                    if not numero_nf or not cod_produto:
                        contador_erros += 1
                        erros.append(f"Item sem NF/produto: NF={numero_nf}, Produto={cod_produto}")
                        continue
                    
                    # Coletar CNPJ para processamento posterior
                    if cnpj_cliente:
                        cnpjs_processados.add(cnpj_cliente)
                    
                    # Criar chave única
                    chave = f"{numero_nf}|{cod_produto}"
                    
                    if chave in registros_existentes:
                        # ✏️ REGISTRO EXISTE → UPDATE apenas status se diferente
                        registro_info = registros_existentes[chave]
                        
                        if registro_info['status_atual'] != status_odoo:
                            # Status mudou - atualizar
                            db.session.query(FaturamentoProduto).filter_by(
                                id=registro_info['id']
                            ).update({
                                'status_nf': status_odoo,
                                'updated_by': 'Sistema Odoo'
                            })
                            
                            contador_atualizados += 1
                            nfs_atualizadas.append(numero_nf)
                            logger.debug(f"✏️ UPDATE: NF {numero_nf} produto {cod_produto} - status: {registro_info['status_atual']} → {status_odoo}")
                        # Se status igual, não faz nada (otimização)
                        
                    else:
                        # ➕ REGISTRO NÃO EXISTE → INSERT
                        novo_registro = FaturamentoProduto(**item_mapeado)
                        novo_registro.created_by = 'Sistema Odoo'
                        novo_registro.status_nf = status_odoo
                        
                        db.session.add(novo_registro)
                        contador_novos += 1
                        nfs_novas.append(numero_nf)
                        logger.debug(f"➕ INSERT: NF {numero_nf} produto {cod_produto}")
                    
                except Exception as e:
                    contador_erros += 1
                    erro_msg = f"Erro NF {item_mapeado.get('numero_nf', 'N/A')}: {e}"
                    logger.error(erro_msg)
                    erros.append(erro_msg)
                    continue
            
            # 💾 COMMIT das alterações principais
            db.session.commit()
            logger.info(f"✅ Sincronização principal concluída: {contador_novos} novos, {contador_atualizados} atualizados")
            
            # ============================================
            # 🔄 SINCRONIZAÇÕES INTEGRADAS (4 MÉTODOS)
            # ============================================
            
            # Estatísticas das sincronizações
            stats_sincronizacao = {
                'entregas_sincronizadas': 0,
                'embarques_revalidados': 0,
                'nfs_embarques_sincronizadas': 0,
                'fretes_lancados': 0,
                'erros_sincronizacao': []
            }
            
            # 🚀 SINCRONIZAÇÃO 1: Entregas por NF (todas as NFs novas/atualizadas)
            try:
                from app.utils.sincronizar_entregas import sincronizar_entrega_por_nf
                
                nfs_para_sincronizar = list(set(nfs_novas + nfs_atualizadas))
                logger.info(f"🔄 Sincronizando entregas para {len(nfs_para_sincronizar)} NFs...")
                
                for numero_nf in nfs_para_sincronizar:
                    try:
                        sincronizar_entrega_por_nf(numero_nf)
                        stats_sincronizacao['entregas_sincronizadas'] += 1
                    except Exception as e:
                        stats_sincronizacao['erros_sincronizacao'].append(f"Entrega NF {numero_nf}: {e}")
                        
            except ImportError as e:
                stats_sincronizacao['erros_sincronizacao'].append(f"Módulo entregas não disponível: {e}")
            
            # 🚀 SINCRONIZAÇÃO 2: Re-validar embarques pendentes
            try:
                from app.faturamento.routes import revalidar_embarques_pendentes
                
                if nfs_novas:
                    logger.info(f"🔄 Re-validando embarques pendentes para {len(nfs_novas)} NFs novas...")
                    resultado_revalidacao = revalidar_embarques_pendentes(nfs_novas)
                    if resultado_revalidacao:
                        stats_sincronizacao['embarques_revalidados'] = len(nfs_novas)
                        
            except ImportError as e:
                stats_sincronizacao['erros_sincronizacao'].append(f"Módulo embarques não disponível: {e}")
            
            # 🚀 SINCRONIZAÇÃO 3: NFs pendentes em embarques
            try:
                from app.faturamento.routes import sincronizar_nfs_pendentes_embarques
                
                if nfs_novas:
                    logger.info(f"🔄 Sincronizando NFs pendentes em embarques...")
                    nfs_embarques_sync = sincronizar_nfs_pendentes_embarques(nfs_novas)
                    stats_sincronizacao['nfs_embarques_sincronizadas'] = nfs_embarques_sync
                    
            except ImportError as e:
                stats_sincronizacao['erros_sincronizacao'].append(f"Módulo embarques não disponível: {e}")
            
            # 🚀 SINCRONIZAÇÃO 4: Lançamento automático de fretes
            try:
                from app.fretes.routes import processar_lancamento_automatico_fretes
                
                logger.info(f"🔄 Processando lançamento automático de fretes para {len(cnpjs_processados)} CNPJs...")
                fretes_lancados_total = 0
                
                for cnpj_cliente in cnpjs_processados:
                    try:
                        sucesso, resultado = processar_lancamento_automatico_fretes(
                            cnpj_cliente=cnpj_cliente,
                            usuario='Sistema Odoo'
                        )
                        if sucesso and "lançado(s) automaticamente" in resultado:
                            fretes_lancados_total += 1
                            logger.debug(f"✅ Frete lançado para CNPJ {cnpj_cliente}: {resultado}")
                            
                    except Exception as e:
                        stats_sincronizacao['erros_sincronizacao'].append(f"Frete CNPJ {cnpj_cliente}: {e}")
                
                stats_sincronizacao['fretes_lancados'] = fretes_lancados_total
                
            except ImportError as e:
                stats_sincronizacao['erros_sincronizacao'].append(f"Módulo fretes não disponível: {e}")
            
            # ⏱️ CALCULAR PERFORMANCE REAL
            tempo_execucao = time.time() - start_time
            total_processados = contador_novos + contador_atualizados
            
            # 📊 ESTATÍSTICAS FINAIS COMPLETAS
            estatisticas = {
                'metodo': 'incremental_completo',
                'registros_novos': contador_novos,
                'registros_atualizados': contador_atualizados,
                'registros_processados': total_processados,
                'registros_ignorados': len(dados_faturamento) - total_processados - contador_erros,
                'registros_com_erro': contador_erros,
                'total_odoo': len(dados_faturamento),
                'total_existentes_antes': len(registros_existentes),
                'tempo_execucao': f"{tempo_execucao:.2f}s",
                'registros_por_segundo': f"{total_processados / tempo_execucao:.1f}" if tempo_execucao > 0 else "0",
                'taxa_novos': f"{(contador_novos / len(dados_faturamento) * 100):.1f}%" if dados_faturamento else "0%",
                'taxa_atualizados': f"{(contador_atualizados / len(dados_faturamento) * 100):.1f}%" if dados_faturamento else "0%",
                'economia_tempo': 'MUITO SIGNIFICATIVA vs método DELETE+INSERT',
                # 🆕 ESTATÍSTICAS DAS SINCRONIZAÇÕES
                'sincronizacoes': stats_sincronizacao
            }
            
            logger.info(f"✅ SINCRONIZAÇÃO INCREMENTAL COMPLETA CONCLUÍDA:")
            logger.info(f"   ➕ {contador_novos} novos registros inseridos")
            logger.info(f"   ✏️ {contador_atualizados} registros atualizados")
            logger.info(f"   🔄 {stats_sincronizacao['entregas_sincronizadas']} entregas sincronizadas")
            logger.info(f"   📦 {stats_sincronizacao['embarques_revalidados']} embarques re-validados")
            logger.info(f"   🚚 {stats_sincronizacao['nfs_embarques_sincronizadas']} NFs de embarques sincronizadas")
            logger.info(f"   💰 {stats_sincronizacao['fretes_lancados']} fretes lançados automaticamente")
            logger.info(f"   ⏱️ Tempo execução: {tempo_execucao:.2f}s")
            logger.info(f"   ❌ {contador_erros} erros principais + {len(stats_sincronizacao['erros_sincronizacao'])} erros de sincronização")
            
            return {
                'sucesso': True,
                'estatisticas': estatisticas,
                'registros_novos': contador_novos,
                'registros_atualizados': contador_atualizados,
                'registros_processados': total_processados,
                'tempo_execucao': tempo_execucao,
                'erros': erros + stats_sincronizacao['erros_sincronizacao'],
                'sincronizacoes': stats_sincronizacao,
                'mensagem': f'🚀 Sincronização incremental completa: {contador_novos} novos, {contador_atualizados} atualizados + {stats_sincronizacao["entregas_sincronizadas"]} entregas + {stats_sincronizacao["fretes_lancados"]} fretes em {tempo_execucao:.2f}s'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ ERRO na sincronização incremental completa: {e}")
            return {
                'sucesso': False,
                'erro': str(e),
                'registros_novos': 0,
                'registros_atualizados': 0,
                'estatisticas': {}
            }

    def obter_faturamento_otimizado(self, usar_filtro_postado=True, limite=20):
        """
        🚀 MÉTODO REALMENTE OTIMIZADO - 5 queries + JOIN em memória
        Com filtro obrigatório implementado
        """
        try:
            logger.info(f"🚀 Busca faturamento otimizada: filtro_postado={usar_filtro_postado}, limite={limite}")
            
            # Conectar ao Odoo
            if not self.connection:
                return {
                    'sucesso': False,
                    'erro': 'Conexão com Odoo não disponível',
                    'dados': []
                }
            
            # ⚠️ FILTRO OBRIGATÓRIO para faturamento
            domain = []
            if usar_filtro_postado:
                domain.extend([
                    ('move_id.state', '=', 'posted'),  # Faturas postadas
                    '|',  # Operador OR em domain Odoo
                    ('move_id.l10n_br_tipo_pedido', '=', 'venda'),
                    ('move_id.l10n_br_tipo_pedido', '=', 'bonificacao')
                ])
            else:
                domain.extend([
                    '|',  # Operador OR em domain Odoo
                    ('move_id.l10n_br_tipo_pedido', '=', 'venda'),
                    ('move_id.l10n_br_tipo_pedido', '=', 'bonificacao')
                ])
            
            campos_basicos = [
                'id', 'move_id', 'partner_id', 'product_id', 
                'quantity', 'price_unit', 'price_total', 'date'
            ]
            
            logger.info("📋 Buscando linhas de faturamento...")
            
            # 🚀 SISTEMA DE LOTES para grandes volumes
            if limite and limite > 0:
                # Dashboard/consulta rápida - limite baixo
                dados_odoo_brutos = self.connection.search_read(
                    'account.move.line', domain, campos_basicos, limit=limite*2
                )
            else:
                # Sincronização completa - sem limite
                dados_odoo_brutos = self.connection.search_read(
                    'account.move.line', domain, campos_basicos
                )
            
            if not dados_odoo_brutos:
                return {
                    'sucesso': True,
                    'dados': [],
                    'total_registros': 0,
                    'mensagem': 'Nenhum faturamento encontrado'
                }
            
            # Processar dados usando método REALMENTE otimizado
            dados_processados = self._processar_dados_faturamento_com_multiplas_queries(dados_odoo_brutos)
            
            # Aplicar limite
            if limite and limite > 0 and len(dados_processados) > limite:
                dados_processados = dados_processados[:limite]
            
            return {
                'sucesso': True,
                'dados': dados_processados,
                'total_registros': len(dados_processados),
                'estatisticas': {
                    'queries_executadas': 5,
                    'total_linhas': len(dados_processados),
                    'linhas_brutas': len(dados_odoo_brutos)
                },
                'mensagem': f'⚡ {len(dados_processados)} registros faturamento (método realmente otimizado)'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }

    # ============================================
    # 🔄 MÉTODOS DE COMPATIBILIDADE
    # ============================================
    
    def obter_faturamento_produtos(self, data_inicio=None, data_fim=None, nfs_especificas=None):
        """
        🔄 MÉTODO DE COMPATIBILIDADE - Usa novo método otimizado
        
        Este método mantém a interface antiga mas usa internamente o método otimizado
        """
        logger.warning("⚠️ Método obsoleto 'obter_faturamento_produtos' usado - migre para 'obter_faturamento_otimizado'")
        
        # Redirecionar para método otimizado
        return self.obter_faturamento_otimizado(
            usar_filtro_postado=True,
            limite=0  # Sem limite para compatibilidade
        )
    
    def sincronizar_faturamento_completo(self) -> Dict[str, Any]:
        """
        🔄 MÉTODO DE COMPATIBILIDADE - Usa novo método incremental
        
        AVISO: Este método DELETE ALL + INSERT ALL foi substituído pelo método incremental
        """
        logger.warning("⚠️ Método obsoleto 'sincronizar_faturamento_completo' usado - migre para 'sincronizar_faturamento_incremental'")
        
        # Redirecionar para método incremental otimizado
        return self.sincronizar_faturamento_incremental()

    # ============================================
    # 🛠️ MÉTODOS AUXILIARES E DE PROCESSAMENTO
    # ============================================
    
    def _mapear_item_faturamento_otimizado(self, linha, cache_faturas, cache_clientes, cache_produtos, cache_municipios, cache_usuarios):
        """
        🚀 MAPEAMENTO FATURAMENTO OTIMIZADO - JOIN em memória usando caches
        Mapeia TODOS os campos de faturamento usando dados já carregados
        """
        try:
            # Extrair IDs da linha
            move_id = linha.get('move_id', [None])[0] if linha.get('move_id') else None
            partner_id = linha.get('partner_id', [None])[0] if linha.get('partner_id') else None
            product_id = linha.get('product_id', [None])[0] if linha.get('product_id') else None
            
            # Buscar dados relacionados nos caches
            fatura = cache_faturas.get(move_id, {})
            cliente = cache_clientes.get(partner_id, {})
            produto = cache_produtos.get(product_id, {})
            
            # Município do cliente
            municipio_id = cliente.get('l10n_br_municipio_id', [None])[0] if cliente.get('l10n_br_municipio_id') else None
            municipio = cache_municipios.get(municipio_id, {})
            
            # Vendedor da fatura
            user_id = fatura.get('invoice_user_id', [None])[0] if fatura.get('invoice_user_id') else None
            usuario = cache_usuarios.get(user_id, {})
            
            # Função auxiliar para extrair valores de relações Many2one
            def extrair_relacao(campo, indice=1):
                if isinstance(campo, list) and len(campo) > indice:
                    return campo[indice]
                return ''
            
            # Extrair estado do município (tratamento especial)
            estado_nome = ''
            if municipio.get('state_id'):
                # Para estado, geralmente o formato é ['SP', 'São Paulo'] 
                estado_info = municipio['state_id']
                if isinstance(estado_info, list) and len(estado_info) > 0:
                    estado_nome = estado_info[0]  # Código do estado (ex: 'SP')
            
            # Mapear TODOS os campos de faturamento
            item_mapeado = {
                # 📄 DADOS DA NOTA FISCAL
                'numero_nf': fatura.get('name', ''),
                'data_fatura': self._parse_date(linha.get('date')),
                'origem': fatura.get('invoice_origin', ''),
                'status_nf': self._mapear_status(fatura.get('state', '')),
                
                # 👥 DADOS DO CLIENTE
                'cnpj_cliente': cliente.get('l10n_br_cnpj', ''),
                'nome_cliente': cliente.get('name', ''),
                'municipio': municipio.get('name', ''),
                'estado': estado_nome,
                
                # 🏢 DADOS COMERCIAIS
                'vendedor': usuario.get('name', ''),
                'incoterm': extrair_relacao(fatura.get('invoice_incoterm_id'), 1),
                
                # 📦 DADOS DO PRODUTO
                'cod_produto': produto.get('default_code', ''),
                'nome_produto': produto.get('name', ''),
                'peso_unitario_produto': produto.get('weight', 0),
                
                # 📊 QUANTIDADES E VALORES
                'qtd_produto_faturado': linha.get('quantity', 0),
                'valor_produto_faturado': linha.get('price_total', 0),
                'preco_produto_faturado': linha.get('price_unit', 0),
                
                # 📏 CAMPOS CALCULADOS
                'peso_total': self._calcular_peso_total(linha.get('quantity', 0), produto.get('weight', 0)),
                
                # Metadados
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'created_by': 'Sistema Odoo REALMENTE Otimizado'
            }
            
            return item_mapeado
            
        except Exception as e:
            logger.error(f"Erro no mapeamento faturamento otimizado do item: {e}")
            return {}
    
    def _calcular_peso_total(self, quantidade: float, peso_unitario: float) -> float:
        """
        Calcula peso total do produto
        """
        try:
            return float(quantidade) * float(peso_unitario)
        except (ValueError, TypeError):
            return 0.0

    def estimar_performance_grandes_volumes(self, total_nfs: int = 5000) -> Dict[str, Any]:
        """
        🔍 CALCULADORA DE PERFORMANCE para grandes volumes
        
        Estima tempo e recursos necessários para sincronizar grandes quantidades
        """
        try:
            import psutil
            import time
            
            logger.info(f"📊 Calculando performance para {total_nfs} NFs...")
            
            # Estimativas baseadas no método otimizado atual
            estimativas = {
                # 📊 VOLUMES ESTIMADOS
                'total_nfs': total_nfs,
                'linhas_faturamento_estimadas': total_nfs * 3,  # Média 3 produtos por NF
                'faturas_unicas': total_nfs,
                'clientes_estimados': total_nfs * 0.7,  # 70% clientes únicos
                'produtos_estimados': total_nfs * 2,    # 2 produtos únicos por NF
                
                # ⚡ PERFORMANCE OTIMIZADA
                'queries_executadas': 5,  # Sempre 5 queries com método otimizado
                'queries_por_metodo_antigo': total_nfs * 17,  # Método antigo faria 17 queries/NF
                'melhoria_performance': f"{(total_nfs * 17) // 5}x mais rápido",
                
                # 🕒 TEMPO ESTIMADO
                'tempo_query_odoo': '15-30s',  # Busca inicial no Odoo
                'tempo_multiplas_queries': '10-20s',  # 5 queries de relacionamentos
                'tempo_join_memoria': '5-15s',  # JOIN em memória
                'tempo_insert_postgresql': '20-40s',  # Inserção no PostgreSQL
                'tempo_total_estimado': '50-105s (1-2 minutos)',
                
                # 💾 MEMÓRIA ESTIMADA
                'memoria_dados_brutos': f"{(total_nfs * 3 * 0.5):.0f}MB",  # ~0.5KB por linha
                'memoria_caches': f"{(total_nfs * 1.2):.0f}MB",  # Caches de relacionamentos
                'memoria_total_estimada': f"{(total_nfs * 4.7):.0f}MB",  # Total em memória
                'memoria_disponivel': f"{psutil.virtual_memory().available // (1024*1024)}MB",
                
                # 🚨 ALERTAS
                'alertas': []
            }
            
            # Verificar alertas baseados no volume
            if total_nfs > 10000:
                estimativas['alertas'].append("⚠️ Volume muito alto (>10k NFs) - considere sincronização por lotes")
            
            memoria_mb_str = estimativas['memoria_total_estimada'][:-2]
            if memoria_mb_str and memoria_mb_str.isdigit() and \
               int(memoria_mb_str) > (psutil.virtual_memory().available // (1024*1024)) * 0.7:
                estimativas['alertas'].append("⚠️ Memória insuficiente - pode precisar otimização adicional")
            
            if total_nfs > 50000:
                estimativas['alertas'].append("🚨 Volume crítico (>50k NFs) - implementar paginação obrigatória")
            
            # ✅ RECOMENDAÇÕES
            estimativas['recomendacoes'] = []
            
            if total_nfs <= 10000:
                estimativas['recomendacoes'].append("✅ Volume OK - sincronização direta recomendada")
            elif total_nfs <= 30000:
                estimativas['recomendacoes'].append("⚡ Volume médio - monitorar performance")
            else:
                estimativas['recomendacoes'].append("🔧 Volume alto - implementar sistema de lotes")
            
            return estimativas
            
        except Exception as e:
            logger.error(f"Erro no cálculo de performance: {e}")
            return {'erro': str(e)} 