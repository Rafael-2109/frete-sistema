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

from app.utils.timezone import agora_utc_naive
from app.faturamento.models import RelatorioFaturamentoImportado, FaturamentoProduto
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.utils.faturamento_mapper import FaturamentoMapper
from app.embarques.models import EmbarqueItem
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
        # Usar conexão direta otimizada (safe_connection removida por causar lentidão)
        self.connection = get_odoo_connection()

    
    def _processar_dados_faturamento_com_multiplas_queries(self, dados_odoo_brutos: List[Dict]) -> List[Dict]:
        """
        🚀 MÉTODO REALMENTE OTIMIZADO - 5 queries + JOIN em memória
        
        ESTRATÉGIA (igual à carteira):
        1. Coletar todos os IDs necessários
        2. Fazer 5 queries em lote  
        3. JOIN em memória
        
        ✅ NOVA VALIDAÇÃO: Filtra linhas vazias automaticamente
        """
        try:
            logger.info("🚀 Processando faturamento com método REALMENTE otimizado...")
            
            if not dados_odoo_brutos:
                return []
            
            # 🔍 FILTRAR LINHAS VÁLIDAS PRIMEIRO
            logger.info(f"📊 Filtrando {len(dados_odoo_brutos)} linhas brutas...")
            dados_validos = []
            linhas_descartadas = 0
            
            for linha in dados_odoo_brutos:
                # ✅ VALIDAÇÃO OBRIGATÓRIA: Linha deve ter product_id válido
                if not linha.get('product_id') or not isinstance(linha.get('product_id'), list):
                    linhas_descartadas += 1
                    continue
                    
                # ✅ VALIDAÇÃO: Deve ter move_id válido
                if not linha.get('move_id') or not isinstance(linha.get('move_id'), list):
                    linhas_descartadas += 1
                    continue
                    
                # ✅ VALIDAÇÃO: Deve ter quantidade maior que 0
                quantidade = linha.get('quantity', 0)
                if not quantidade or quantidade <= 0:
                    linhas_descartadas += 1
                    continue
                
                dados_validos.append(linha)
            
            logger.info(f"📈 Resultado filtragem: {len(dados_validos)} válidas, {linhas_descartadas} descartadas")
            
            if not dados_validos:
                logger.warning("⚠️ Nenhuma linha válida encontrada após filtragem")
                return []
            
            # 1️⃣ COLETAR TODOS OS IDs NECESSÁRIOS
            move_ids = set()
            partner_ids = set()
            product_ids = set()
            
            for linha in dados_validos:
                if linha.get('move_id'):
                    move_ids.add(linha['move_id'][0])
                if linha.get('partner_id'):
                    partner_ids.add(linha['partner_id'][0])
                if linha.get('product_id'):
                    product_ids.add(linha['product_id'][0])
            
            logger.info(f"📊 Coletados: {len(move_ids)} faturas, {len(partner_ids)} clientes, {len(product_ids)} produtos")
            
            # 2️⃣ BUSCAR TODAS AS FATURAS (1 query)
            campos_fatura = [
                'id', 'name', 'invoice_origin', 'state', 'invoice_user_id', 'invoice_incoterm_id',
                'l10n_br_numero_nota_fiscal', 'date', 'l10n_br_cnpj', 'invoice_partner_display_name',
                'team_id'  # Campo da equipe de vendas
            ]
            
            logger.info("🔍 Query 1/6: Buscando faturas...")
            faturas = self.connection.search_read(
                'account.move',
                [('id', 'in', list(move_ids))],
                campos_fatura
            )
            
            # 3️⃣ BUSCAR TODOS OS CLIENTES (1 query)
            campos_cliente = [
                'id', 'name', 'l10n_br_cnpj', 'l10n_br_municipio_id', 'state_id', 'user_id'
            ]
            
            logger.info(f"🔍 Query 2/6: Buscando {len(partner_ids)} clientes...")
            clientes = self.connection.search_read(
                'res.partner',
                [('id', 'in', list(partner_ids))],
                campos_cliente
            )
            
            # 4️⃣ BUSCAR TODOS OS PRODUTOS (1 query)
            campos_produto = ['id', 'name', 'code', 'weight', 'product_tmpl_id']  # Adicionar template_id
            
            logger.info(f"🔍 Query 3/6: Buscando {len(product_ids)} produtos...")
            produtos = self.connection.search_read(
                'product.product',
                [('id', 'in', list(product_ids))],
                campos_produto
            )
            
            # 5️⃣ BUSCAR TODOS OS TEMPLATES DOS PRODUTOS (1 query)
            template_ids = set()
            for produto in produtos:
                if produto.get('product_tmpl_id'):
                    template_ids.add(produto['product_tmpl_id'][0])
            
            templates = []
            if template_ids:
                campos_template = ['id', 'name', 'default_code', 'gross_weight']
                
                logger.info(f"🔍 Query 4/6: Buscando {len(template_ids)} templates...")
                templates = self.connection.search_read(
                    'product.template',
                    [('id', 'in', list(template_ids))],
                    campos_template
                )
            
            # 6️⃣ BUSCAR MUNICÍPIOS DOS CLIENTES (1 query)
            municipio_ids = set()
            for cliente in clientes:
                if cliente.get('l10n_br_municipio_id'):
                    municipio_ids.add(cliente['l10n_br_municipio_id'][0])
            
            municipios = []
            if municipio_ids:
                logger.info(f"🔍 Query 5/6: Buscando {len(municipio_ids)} municípios...")
                municipios = self.connection.search_read(
                    'l10n_br_ciel_it_account.res.municipio',
                    [('id', 'in', list(municipio_ids))],
                    ['id', 'name', 'state_id']
                )
            
            # 7️⃣ BUSCAR USUÁRIOS/VENDEDORES MELHORADO (1 query)
            user_ids = set()
            
            # Coletar IDs de vendedores de múltiplas fontes
            for fatura in faturas:
                # Primeira opção: invoice_user_id da fatura
                if fatura.get('invoice_user_id'):
                    user_ids.add(fatura['invoice_user_id'][0])
            
            # Segunda opção: user_id do cliente (res.partner)
            for cliente in clientes:
                if cliente.get('user_id'):
                    user_ids.add(cliente['user_id'][0])
            
            usuarios = []
            if user_ids:
                logger.info(f"🔍 Query 6/6: Buscando {len(user_ids)} vendedores...")
                usuarios = self.connection.search_read(
                    'res.users',
                    [('id', 'in', list(user_ids))],
                    ['id', 'name']
                )
            
            # 8️⃣ CRIAR CACHES PARA JOIN EM MEMÓRIA
            cache_faturas = {f['id']: f for f in faturas}
            cache_clientes = {c['id']: c for c in clientes}
            cache_produtos = {p['id']: p for p in produtos}
            cache_templates = {t['id']: t for t in templates}
            cache_municipios = {m['id']: m for m in municipios}
            cache_usuarios = {u['id']: u for u in usuarios}
            
            logger.info("🧠 Caches criados, fazendo JOIN em memória...")
            
            # 9️⃣ PROCESSAR DADOS COM JOIN EM MEMÓRIA
            dados_processados = []
            
            for linha in dados_validos:  # ✅ Usar dados_validos ao invés de dados_odoo_brutos
                try:
                    item_mapeado = self._mapear_item_faturamento_otimizado(
                        linha, cache_faturas, cache_clientes, cache_produtos,
                        cache_templates, cache_municipios, cache_usuarios
                    )
                    
                    # ✅ VALIDAÇÃO FINAL: Item deve ter campos essenciais
                    origem = item_mapeado.get('origem', '')
                    if not item_mapeado.get('cod_produto') or not item_mapeado.get('numero_nf') or not origem or origem == 'false':
                        logger.debug(f"Item descartado na validação final: {item_mapeado.get('cod_produto')} / {item_mapeado.get('numero_nf')} / origem: {origem}")
                        continue
                    
                    dados_processados.append(item_mapeado)
                    
                except Exception as e:
                    logger.warning(f"Erro ao mapear item faturamento {linha.get('id')}: {e}")
                    continue
            
            total_queries = 6  # Agora são 6 queries
            logger.info(f"✅ OTIMIZAÇÃO FATURAMENTO COMPLETA:")
            logger.info(f"   📊 {len(dados_processados)} itens processados")
            logger.info(f"   ⚡ {total_queries} queries executadas (vs {len(dados_odoo_brutos)*17} do método antigo)")
            logger.info(f"   🚀 {(len(dados_odoo_brutos)*17)//total_queries}x mais rápido")
            
            return dados_processados
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento faturamento otimizado: {e}")
            return []
    
    def _processar_cancelamento_nf(self, numero_nf: str) -> bool:
        """
        Processa o cancelamento de uma NF de forma atômica

        IMPORTANTE: Este método é para NFs CANCELADAS (state='cancel' no Odoo).
        NFs REVERTIDAS (com Nota de Crédito) são processadas pelo ReversaoService
        e NÃO devem passar por aqui.

        Args:
            numero_nf: Número da NF a ser cancelada

        Returns:
            bool: True se processamento foi bem sucedido
        """
        try:
            logger = logging.getLogger(__name__)
            logger.info(f"🔄 Processando cancelamento da NF {numero_nf}")

            from app.estoque.models import MovimentacaoEstoque
            from app.separacao.models import Separacao

            # SALVAGUARDA: Verificar se NF já foi revertida (não deve ser "cancelada")
            # NFs revertidas são tratadas pelo ReversaoService com lógica diferente
            fat_revertida = FaturamentoProduto.query.filter_by(
                numero_nf=numero_nf,
                revertida=True
            ).first()

            if fat_revertida:
                logger.warning(f"⚠️ NF {numero_nf} já foi REVERTIDA via Nota de Crédito. "
                             f"Cancelamento ignorado (usar ReversaoService para reversões).")
                return False

            # 1. Atualizar FaturamentoProduto - IMPORTANTE!
            faturamentos_atualizados = db.session.query(FaturamentoProduto).filter(
                FaturamentoProduto.numero_nf == numero_nf,
                FaturamentoProduto.status_nf != 'Cancelado'  # Apenas não cancelados
            ).update({
                'status_nf': 'Cancelado',
                'updated_at': agora_utc_naive(),
                'updated_by': 'Sistema - NF Cancelada no Odoo'
            })
            
            if faturamentos_atualizados > 0:
                logger.info(f"   ✅ {faturamentos_atualizados} registros de faturamento marcados como Cancelado")
            
            # 2. Atualizar MovimentacaoEstoque
            movs_atualizadas = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.numero_nf == numero_nf,
                MovimentacaoEstoque.ativo == True  # Buscar apenas ativos
            ).update({
                'status_nf': 'CANCELADO',
                'ativo': False,  # IMPORTANTE: Marcar como inativo para excluir do estoque
                'atualizado_em': agora_utc_naive(),
                'atualizado_por': 'Sistema - NF Cancelada no Odoo'
            })
            
            if movs_atualizadas > 0:
                logger.info(f"   ✅ {movs_atualizadas} movimentações de estoque marcadas como CANCELADO e inativas")
            
            # 3. Limpar EmbarqueItem (remover número da NF)
            embarques_limpos = db.session.query(EmbarqueItem).filter(
                EmbarqueItem.nota_fiscal == numero_nf
            ).update({
                'nota_fiscal': None,
                'erro_validacao': 'NF cancelada no Odoo'
            })
            
            if embarques_limpos > 0:
                logger.info(f"   ✅ {embarques_limpos} itens de embarque atualizados")
            
            # 4. Atualizar Separacao (reverter sincronização)
            separacoes_atualizadas = db.session.query(Separacao).filter(
                Separacao.numero_nf == numero_nf
            ).update({
                'numero_nf': None,
                'sincronizado_nf': False
            })
            
            if separacoes_atualizadas > 0:
                logger.info(f"   ✅ {separacoes_atualizadas} separações revertidas para não sincronizado")
            
            # 5. Atualizar saldos na CarteiraPrincipal
            pedidos_afetados = {}
            if faturamentos_atualizados > 0:
                # Buscar pedidos/produtos afetados pelo cancelamento
                faturamentos_cancelados = db.session.query(FaturamentoProduto).filter(
                    FaturamentoProduto.numero_nf == numero_nf
                ).all()

                for fat in faturamentos_cancelados:
                    if fat.origem and fat.cod_produto:
                        if fat.origem not in pedidos_afetados:
                            pedidos_afetados[fat.origem] = set()
                        pedidos_afetados[fat.origem].add(fat.cod_produto)

                # Atualizar saldos na carteira
                if pedidos_afetados:
                    resultado_saldos = self._atualizar_saldos_carteira(pedidos_afetados)
                    logger.info(f"   ✅ {resultado_saldos['atualizados']} saldos atualizados na carteira")

            # 6. Log de auditoria detalhado
            logger.info(f"✅ CANCELAMENTO COMPLETO: NF {numero_nf}")
            logger.info(f"   - Faturamentos cancelados: {faturamentos_atualizados}")
            logger.info(f"   - Movimentações inativadas: {movs_atualizadas}")
            logger.info(f"   - Embarques limpos: {embarques_limpos}")
            logger.info(f"   - Separações revertidas: {separacoes_atualizadas}")
            if pedidos_afetados:
                logger.info(f"   - Saldos da carteira atualizados: {len(pedidos_afetados)} pedidos")

            # Commit apenas se houve alterações
            if faturamentos_atualizados > 0 or movs_atualizadas > 0 or embarques_limpos > 0 or separacoes_atualizadas > 0:
                db.session.commit()

            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar cancelamento da NF {numero_nf}: {e}")
            db.session.rollback()
            return False
    
    def _atualizar_saldos_carteira(self, pedidos_produtos_afetados: Dict[str, set]) -> Dict[str, Any]:
        """
        Atualiza qtd_saldo_produto_pedido na CarteiraPrincipal após mudanças no faturamento

        IMPORTANTE: Este método garante que o saldo na carteira sempre reflita a realidade
        do faturamento, evitando inconsistências quando pedidos antigos são faturados.

        Args:
            pedidos_produtos_afetados: Dict com chave=num_pedido, valor=set(cod_produtos)

        Returns:
            Dict com estatísticas da atualização
        """
        try:
            from sqlalchemy import func

            contador_atualizados = 0
            contador_erros = 0
            erros = []

            logger.info(f"📊 Atualizando saldos da carteira para {len(pedidos_produtos_afetados)} pedidos")

            for num_pedido, produtos in pedidos_produtos_afetados.items():
                for cod_produto in produtos:
                    try:
                        # Calcular quantidade total faturada para este pedido/produto
                        qtd_faturada = db.session.query(
                            func.sum(FaturamentoProduto.qtd_produto_faturado)
                        ).filter(
                            FaturamentoProduto.origem == num_pedido,
                            FaturamentoProduto.cod_produto == cod_produto,
                            FaturamentoProduto.status_nf != 'Cancelado'
                        ).scalar() or 0

                        qtd_faturada = float(qtd_faturada)

                        # Atualizar todos os registros na CarteiraPrincipal para este pedido/produto
                        # Usando SQL direto para melhor performance e evitar problemas de ORM
                        from sqlalchemy import text

                        sql_update = text("""
                            UPDATE carteira_principal
                            SET qtd_saldo_produto_pedido = qtd_produto_pedido - :qtd_faturada,
                                updated_at = NOW(),
                                updated_by = 'FaturamentoService'
                            WHERE num_pedido = :num_pedido
                              AND cod_produto = :cod_produto
                        """)

                        resultado = db.session.execute(
                            sql_update,
                            {
                                'qtd_faturada': qtd_faturada,
                                'num_pedido': num_pedido,
                                'cod_produto': cod_produto
                            }
                        )

                        registros_atualizados = resultado.rowcount
                        contador_atualizados += registros_atualizados

                        if registros_atualizados > 0:
                            logger.debug(f"   ✅ Atualizado saldo: Pedido {num_pedido}, Produto {cod_produto}, Faturado: {qtd_faturada}")

                    except Exception as e:
                        contador_erros += 1
                        erro_msg = f"Erro ao atualizar saldo do pedido {num_pedido}, produto {cod_produto}: {e}"
                        logger.error(f"   ❌ {erro_msg}")
                        erros.append(erro_msg)
                        continue

            if contador_atualizados > 0:
                logger.info(f"✅ Saldos da carteira atualizados: {contador_atualizados} registros")

            if contador_erros > 0:
                logger.warning(f"⚠️ {contador_erros} erros ao atualizar saldos")

            return {
                'sucesso': True,
                'atualizados': contador_atualizados,
                'erros': contador_erros,
                'detalhes_erros': erros[:10]  # Limitar detalhes de erros
            }

        except Exception as e:
            logger.error(f"❌ Erro crítico ao atualizar saldos da carteira: {e}")
            return {
                'sucesso': False,
                'atualizados': 0,
                'erros': 1,
                'detalhes_erros': [str(e)]
            }

    def _mapear_status(self, status_odoo: Optional[str]) -> str:
        """
        Mapeia status do Odoo para status do sistema
        Mantém consistência com valores esperados no banco
        """
        if not status_odoo:
            return 'Lançado'
        
        status_map = {
            'draft': 'Provisório',
            'posted': 'Lançado',
            'cancel': 'Cancelado',  # Usar 'Cancelado' com inicial maiúscula conforme modelo
            'sale': 'Lançado',
            'done': 'Lançado',
            'sent': 'Lançado'
        }
        
        return status_map.get(status_odoo.lower(), 'Lançado')
    
    def _parse_date(self, date_input) -> Optional[datetime]:
        """
        Converte string de data ou datetime para datetime
        Trata ambos os casos: string e datetime já processado
        """
        if not date_input:
            return None
        
        # Se já é datetime, retornar diretamente
        if isinstance(date_input, datetime):
            return date_input
        
        # Se é string, processar
        if isinstance(date_input, str):
            try:
                # Formato do Odoo: 2025-07-14 20:19:52
                dt = datetime.strptime(date_input, '%Y-%m-%d %H:%M:%S')
                return dt
            except ValueError:
                try:
                    # Formato de data apenas: 2025-07-14
                    dt = datetime.strptime(date_input, '%Y-%m-%d')
                    return dt
                except ValueError:
                    self.logger.warning(f"Formato de data inválido: {date_input}")
                    return None
        
        # Tipo inesperado
        self.logger.warning(f"Tipo de data inesperado: {type(date_input)} - {date_input}")
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
                        'nome_cliente': dado.get('nome_cliente'),  # Campo correto
                        'cnpj_cliente': dado.get('cnpj_cliente'),  # Campo correto
                        'data_fatura': dado.get('data_fatura'),   # Campo correto
                        'valor_total': 0,
                        'origem': dado.get('origem'),             # Campo correto
                        'incoterm': dado.get('incoterm'),         # Campo correto
                        'vendedor': dado.get('vendedor'),         # Campo correto
                        'equipe_vendas': dado.get('equipe_vendas'),  # ✅ NOVO CAMPO
                        'municipio': dado.get('municipio'),       # Campo correto
                        'estado': dado.get('estado'),             # ✅ ADICIONAR ESTADO
                        'status': dado.get('status_nf'),          # Campo correto: status_nf
                        'peso_total': 0
                    }
                
                # Adicionar valor do item ao total - usar campo correto
                valor_item = dado.get('valor_produto_faturado') or 0  # Campo correto
                nfs_consolidadas[nf_key]['valor_total'] += valor_item
                
                # Somar peso total da NF
                peso_item = (dado.get('peso_unitario_produto') or 0) * (dado.get('qtd_produto_faturado') or 0)
                if 'peso_total' not in nfs_consolidadas[nf_key]:
                    nfs_consolidadas[nf_key]['peso_total'] = 0
                nfs_consolidadas[nf_key]['peso_total'] += peso_item
                
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
                        relatorio.equipe_vendas = dados_nf['equipe_vendas']  # ✅ NOVO CAMPO
                        relatorio.municipio = dados_nf['municipio']
                        relatorio.estado = dados_nf['estado']      # ✅ ADICIONAR ESTADO
                        relatorio.status_faturamento = dados_nf['status']
                        relatorio.peso_bruto = dados_nf['peso_total']

                        db.session.add(relatorio)
                        total_relatorio_importado += 1
                    else:
                        # Atualizar registro existente
                        existe.valor_total = dados_nf['valor_total']
                        existe.peso_bruto = dados_nf['peso_total']
                        existe.status_faturamento = dados_nf['status']
                        existe.equipe_vendas = dados_nf['equipe_vendas']  # ✅ NOVO CAMPO
                
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
    
    def sincronizar_faturamento_incremental(self, primeira_execucao=False, minutos_status=1560) -> Dict[str, Any]:
        """
        🚀 SINCRONIZAÇÃO INCREMENTAL OTIMIZADA + INTEGRAÇÃO COMPLETA

        Agora usa write_date para busca incremental mantendo todas funcionalidades

        Estratégia do usuário:
        - NF não existe → INSERT
        - NF já existe → UPDATE apenas status

        ✅ INCLUI: Sincronização completa de entregas, embarques e fretes
        """
        # Audit Supply Chain: contexto para triggers PostgreSQL
        _audit_session_id = None
        try:
            from app.supply_chain.services.context_middleware import set_audit_context, gerar_session_id
            _audit_session_id = gerar_session_id('SYNC_FATURAMENTO')
            set_audit_context(usuario='Sistema - Sync Odoo', origem='SYNC_ODOO', session_id=_audit_session_id)
        except Exception:
            pass

        try:
            import time
            from app import db

            start_time = time.time()

            # ⚡ Buscar dados do Odoo com MODO INCREMENTAL usando write_date
            resultado = self.obter_faturamento_otimizado(
                usar_filtro_postado=True,
                limite=0,  # Usará limite interno de 20000 registros para evitar timeout
                modo_incremental=True,  # ✅ ATIVAR MODO INCREMENTAL COM WRITE_DATE
                minutos_status=minutos_status  # ✅ PASSAR JANELA PARA STATUS
            )
            
            if not resultado['sucesso']:
                return {
                    'sucesso': False,
                    'erro': resultado.get('erro', 'Erro na consulta do Odoo'),
                    'estatisticas': {}
                }
            
            dados_faturamento = resultado.get('dados', [])
            
            if not dados_faturamento:
                logger.info("📊 Nenhuma alteração encontrada no período (normal em finais de semana)")
                return {
                    'sucesso': True,
                    'registros_novos': 0,
                    'registros_atualizados': 0,
                    'estatisticas': {},
                    'movimentacoes_estoque': {},
                    'sincronizacoes': {},
                    'tempo_execucao': time.time() - start_time,
                    'mensagem': 'Nenhuma alteração no período'
                }
            
            logger.info(f"📊 Processando {len(dados_faturamento)} registros do Odoo...")
            
            # Sanitizar dados antes de processar
            logger.info("🧹 Sanitizando dados de faturamento...")
            dados_faturamento = self._sanitizar_dados_faturamento(dados_faturamento)
            
            # 📊 ESTATÍSTICAS
            contador_novos = 0
            contador_atualizados = 0
            contador_erros = 0
            erros = []

            # 📋 LISTAS PARA SINCRONIZAÇÃO POSTERIOR
            nfs_novas = []  # NFs que foram inseridas
            nfs_atualizadas = []  # NFs que foram atualizadas
            nfs_reprocessar = []  # NFs que precisam ser reprocessadas (novas ou status mudou para não-cancelado)
            cnpjs_processados = set()  # CNPJs únicos para lançamento de fretes

            # 🚀 OTIMIZAÇÃO: Listas para bulk insert
            produtos_para_verificar = set()  # Produtos que precisam ser verificados
            registros_para_bulk_insert = []  # Lista para bulk insert
            
            # 🔍 CRIAR ÍNDICE DE REGISTROS EXISTENTES (OTIMIZADO)
            logger.info("🔍 Carregando índice de registros existentes...")
            registros_existentes = {}

            # 🚀 OTIMIZAÇÃO: Em modo incremental, carregar apenas registros recentes
            query = db.session.query(
                FaturamentoProduto.numero_nf,
                FaturamentoProduto.cod_produto,
                FaturamentoProduto.id,
                FaturamentoProduto.status_nf
            )

            # 🔴 CORREÇÃO: Verificar registros baseado na janela de tempo real
            # Para janelas grandes (histórico), verificar tudo para evitar duplicatas
            # Para janelas pequenas (scheduler), manter otimização
            if not primeira_execucao:
                from datetime import datetime, timedelta
                minutos_verificacao = int(minutos_status * 1.1)  # margem segurança
                data_limite = agora_utc_naive() - timedelta(minutes=minutos_verificacao)
                query = query.filter(FaturamentoProduto.created_at >= data_limite)
                logger.info(
                    f"🔎 Verificando existentes desde {data_limite.strftime('%Y-%m-%d %H:%M')} "
                    f"(janela={minutos_status}m +10%)"
                )

            # Usar yield_per para economizar memória em queries grandes
            contador_registros = 0
            for registro in query.yield_per(1000):
                chave = f"{registro.numero_nf}|{registro.cod_produto}"
                registros_existentes[chave] = {
                    'id': registro.id,
                    'status_atual': registro.status_nf
                }
                contador_registros += 1

            logger.info(f"📋 Índice criado com {contador_registros} registros existentes")
            
            # 🔄 PROCESSAR CADA ITEM DO ODOO
            for item_mapeado in dados_faturamento:
                try:
                    numero_nf = item_mapeado.get('numero_nf', '').strip()
                    cod_produto = item_mapeado.get('cod_produto', '').strip()
                    status_odoo = item_mapeado.get('status_nf', 'Lançado')
                    status_odoo_raw = item_mapeado.get('status_odoo_raw', '')  # Status bruto do Odoo
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
                            
                            # 🚨 Se mudou para CANCELADO, processar imediatamente
                            # Comparação case-insensitive para garantir detecção
                            status_atual_upper = registro_info['status_atual'].upper() if registro_info['status_atual'] else ''
                            if status_odoo_raw == 'cancel' and status_atual_upper != 'CANCELADO':
                                logger.info(f"🚨 Processando CANCELAMENTO da NF {numero_nf} (Odoo state='cancel')")
                                self._processar_cancelamento_nf(numero_nf)
                            # 🔄 Se mudou DE cancelado PARA ativo, precisa reprocessar
                            elif status_atual_upper == 'CANCELADO' and status_odoo.upper() != 'CANCELADO':
                                nfs_reprocessar.append(numero_nf)
                                logger.info(f"🔄 NF {numero_nf} voltou de CANCELADO para {status_odoo}, marcada para reprocessamento")
                        # Se status igual, não faz nada (otimização)
                        
                    else:
                        # ➕ REGISTRO NÃO EXISTE → INSERT
                        # Remover campo status_odoo_raw que não existe no modelo
                        item_para_inserir = item_mapeado.copy()
                        if 'status_odoo_raw' in item_para_inserir:
                            del item_para_inserir['status_odoo_raw']
                        
                        # 🚀 OTIMIZAÇÃO: Adicionar produto ao conjunto para verificação em batch
                        cod_produto = item_para_inserir.get('cod_produto')
                        if cod_produto:
                            produtos_para_verificar.add(cod_produto)
                        
                        # 🚀 OTIMIZAÇÃO: Preparar para bulk insert
                        item_para_inserir['created_by'] = 'Sistema Odoo'
                        item_para_inserir['status_nf'] = status_odoo
                        registros_para_bulk_insert.append(item_para_inserir)

                        contador_novos += 1
                        nfs_novas.append(numero_nf)
                        if status_odoo_raw != 'cancel':
                            nfs_reprocessar.append(numero_nf)  # NFs novas precisam ser processadas (exceto canceladas)
                        else:
                            logger.info(f"🚫 NF {numero_nf} importada já cancelada — pulando processamento de estoque")
                        logger.debug(f"➕ Preparado para INSERT: NF {numero_nf} produto {cod_produto}")
                    
                except Exception as e:
                    contador_erros += 1
                    erro_msg = f"Erro NF {item_mapeado.get('numero_nf', 'N/A')}: {e}"
                    logger.error(erro_msg)
                    erros.append(erro_msg)
                    continue
            
            # 🚀 OTIMIZAÇÃO: Verificar e criar produtos em batch antes do bulk insert
            if produtos_para_verificar:
                from app.producao.models import CadastroPalletizacao

                logger.info(f"🔍 Verificando {len(produtos_para_verificar)} produtos no CadastroPalletizacao...")

                # Buscar produtos existentes em uma única query
                produtos_existentes = {
                    p.cod_produto
                    for p in CadastroPalletizacao.query.filter(
                        CadastroPalletizacao.cod_produto.in_(produtos_para_verificar)
                    ).all()
                }

                # Criar produtos que não existem
                produtos_novos = []
                for cod_produto in produtos_para_verificar:
                    if cod_produto not in produtos_existentes:
                        # Buscar nome do produto nos registros para bulk insert
                        nome_produto = cod_produto
                        for registro in registros_para_bulk_insert:
                            if registro.get('cod_produto') == cod_produto:
                                nome_produto = registro.get('nome_produto', cod_produto)
                                break

                        produtos_novos.append({
                            'cod_produto': cod_produto,
                            'nome_produto': nome_produto,
                            'palletizacao': 1.0,
                            'peso_bruto': 1.0
                        })

                if produtos_novos:
                    db.session.bulk_insert_mappings(CadastroPalletizacao, produtos_novos)
                    logger.info(f"✅ {len(produtos_novos)} produtos criados em batch no CadastroPalletizacao")

            # 🚀 OTIMIZAÇÃO: Bulk insert para novos registros
            pedidos_produtos_para_atualizar = {}
            if registros_para_bulk_insert:
                logger.info(f"🚀 Executando bulk insert de {len(registros_para_bulk_insert)} registros...")
                db.session.bulk_insert_mappings(FaturamentoProduto, registros_para_bulk_insert)
                logger.info(f"✅ Bulk insert concluído com sucesso")

                # Coletar pedidos/produtos para atualização de saldo
                for registro in registros_para_bulk_insert:
                    num_pedido = registro.get('origem')
                    cod_produto = registro.get('cod_produto')
                    if num_pedido and cod_produto:
                        if num_pedido not in pedidos_produtos_para_atualizar:
                            pedidos_produtos_para_atualizar[num_pedido] = set()
                        pedidos_produtos_para_atualizar[num_pedido].add(cod_produto)

            # Coletar pedidos/produtos atualizados (mudança de status)
            for numero_nf in nfs_atualizadas:
                # Buscar produtos desta NF para atualizar saldos
                produtos_nf = db.session.query(FaturamentoProduto).filter_by(numero_nf=numero_nf).all()
                for produto in produtos_nf:
                    if produto.origem and produto.cod_produto:
                        if produto.origem not in pedidos_produtos_para_atualizar:
                            pedidos_produtos_para_atualizar[produto.origem] = set()
                        pedidos_produtos_para_atualizar[produto.origem].add(produto.cod_produto)

            # 🔄 ATUALIZAR SALDOS NA CARTEIRA
            saldos_atualizados = 0
            if pedidos_produtos_para_atualizar:
                logger.info(f"📊 Atualizando saldos da carteira para {len(pedidos_produtos_para_atualizar)} pedidos...")
                resultado_saldos = self._atualizar_saldos_carteira(pedidos_produtos_para_atualizar)
                saldos_atualizados = resultado_saldos.get('atualizados', 0)
                if saldos_atualizados > 0:
                    logger.info(f"✅ {saldos_atualizados} saldos atualizados na carteira")

            # 💾 COMMIT das alterações principais
            db.session.commit()
            logger.info(f"✅ Sincronização principal concluída: {contador_novos} novos, {contador_atualizados} atualizados, {saldos_atualizados} saldos atualizados")
            
            # ============================================
            # 🚨 PROCESSAMENTO DE NFs CANCELADAS
            # ============================================
            # NFs recém-canceladas já foram processadas durante a sincronização incremental
            # Este bloco agora é apenas para garantir consistência em casos especiais
            
            logger.info("🔍 Verificando consistência de NFs CANCELADAS...")
            
            # Nota: O processamento principal de cancelamentos agora ocorre em tempo real
            # durante a sincronização incremental através de _processar_cancelamento_nf()
            
            # ============================================
            # 🔄 CONSOLIDAÇÃO PARA RELATORIOFATURAMENTOIMPORTADO
            # ============================================
            # IMPORTANTE: Consolidar ANTES de processar movimentações!
            # ProcessadorFaturamento busca NFs em RelatorioFaturamentoImportado

            # 🚀 OTIMIZAÇÃO: Pular consolidação completa em modo incremental regular
            relatorios_consolidados = 0
            if primeira_execucao or contador_novos > 100:  # Consolidar apenas se primeira execução ou muitas NFs novas
                logger.info("🔄 Iniciando consolidação COMPLETA para RelatorioFaturamentoImportado...")
                try:
                    resultado_consolidacao = self._consolidar_faturamento(dados_faturamento)
                    relatorios_consolidados = resultado_consolidacao.get('total_relatorio_importado', 0)
                    logger.info(f"✅ Consolidação concluída: {relatorios_consolidados} relatórios processados")
                except Exception as e:
                    logger.error(f"❌ Erro na consolidação: {e}")
                    erros.append(f"Erro na consolidação RelatorioFaturamentoImportado: {e}")
            elif nfs_novas:
                # Consolidar apenas NFs novas
                logger.info(f"🚀 Modo incremental: consolidando apenas {len(set(nfs_novas))} NFs novas...")
                try:
                    # Filtrar apenas dados das NFs novas
                    dados_nfs_novas = [d for d in dados_faturamento if d.get('numero_nf') in set(nfs_novas)]
                    if dados_nfs_novas:
                        resultado_consolidacao = self._consolidar_faturamento(dados_nfs_novas)
                        relatorios_consolidados = resultado_consolidacao.get('total_relatorio_importado', 0)
                        logger.info(f"✅ Consolidação incremental concluída: {relatorios_consolidados} relatórios")
                except Exception as e:
                    logger.error(f"❌ Erro na consolidação incremental: {e}")
                    erros.append(f"Erro na consolidação incremental: {e}")
            else:
                logger.info("📊 Modo incremental: pulando consolidação (sem NFs novas)")

            # ============================================
            # SAFETY NET: Verificar NFs orfas do sync atual
            # ============================================
            # Se a consolidacao falhou ou pulou NFs, reparar ANTES do ProcessadorFaturamento
            if nfs_novas:
                try:
                    from app.faturamento.models import RelatorioFaturamentoImportado as _RFI
                    nfs_novas_set = set(nfs_novas)
                    nfs_em_relatorio = set(
                        row[0] for row in db.session.query(_RFI.numero_nf)
                        .filter(_RFI.numero_nf.in_(list(nfs_novas_set)))
                        .all()
                    )
                    nfs_orfas = nfs_novas_set - nfs_em_relatorio
                    if nfs_orfas:
                        logger.warning(
                            f"⚠️ Safety net: {len(nfs_orfas)} NFs orfas detectadas "
                            f"(em FaturamentoProduto mas nao em RelatorioFaturamentoImportado): "
                            f"{sorted(nfs_orfas)[:10]}"
                        )
                        from app.odoo.services.importacao_fallback_service import ImportacaoFallbackService
                        resultado_reparacao = ImportacaoFallbackService().reparar_orfaos_faturamento(
                            nfs_especificas=list(nfs_orfas)
                        )
                        if resultado_reparacao.get('orfas_reparadas', 0) > 0:
                            logger.info(
                                f"✅ Safety net: {resultado_reparacao['orfas_reparadas']} NFs orfas reparadas"
                            )
                except Exception as e:
                    logger.error(f"⚠️ Erro no safety net de NFs orfas (nao bloqueante): {e}")

            # ============================================
            # 🚨 PROCESSAMENTO DE MOVIMENTAÇÕES DE ESTOQUE
            # ============================================
            # AGORA que RelatorioFaturamentoImportado está populado,
            # ProcessadorFaturamento pode encontrar as NFs
            
            # 🏭 PROCESSAR NFs para gerar movimentações de estoque
            logger.info("🏭 Iniciando processamento de movimentações de estoque...")
            stats_estoque = {'processadas': 0, 'movimentacoes_criadas': 0, 'erros_processamento': []}
            
            try:
                from app.faturamento.services.processar_faturamento import ProcessadorFaturamento
                
                processador = ProcessadorFaturamento()
                
                # 🚀 FLUXO INTELIGENTE: 
                # Se tem NFs novas/reativadas específicas → processa só elas
                # Senão → processa TUDO que precisa (novas + incompletas antigas)
                nfs_para_processar = list(set(nfs_reprocessar))  # NFs novas + reativadas, sem duplicatas
                
                if nfs_para_processar:
                    # Caso 1: Temos NFs específicas da sincronização atual
                    logger.info(f"📊 Processando {len(nfs_para_processar)} NFs específicas da sincronização")
                    logger.debug(f"   - {len(set(nfs_novas))} NFs novas")
                    logger.debug(f"   - {len(set(nfs_reprocessar) - set(nfs_novas))} NFs reativadas")
                    
                    resultado_processamento = processador.processar_nfs_importadas(
                        usuario='Sincronização Odoo',
                        nfs_especificas=nfs_para_processar  # Passa lista específica
                    )
                else:
                    # Caso 2: Não tem NFs novas, mas pode ter incompletas antigas
                    logger.info("🔄 Executando fluxo completo (busca automática de pendentes)")
                    resultado_processamento = processador.processar_fluxo_completo()
                
                if resultado_processamento:
                    stats_estoque['processadas'] = resultado_processamento.get('processadas', 0)
                    stats_estoque['ja_processadas'] = resultado_processamento.get('ja_processadas', 0)
                    stats_estoque['canceladas'] = resultado_processamento.get('canceladas', 0)
                    stats_estoque['sem_separacao'] = resultado_processamento.get('sem_separacao', 0)
                    stats_estoque['com_embarque'] = resultado_processamento.get('com_embarque', 0)
                    stats_estoque['movimentacoes_criadas'] = resultado_processamento.get('movimentacoes_criadas', 0)
                    stats_estoque['embarque_items_atualizados'] = resultado_processamento.get('embarque_items_atualizados', 0)
                    stats_estoque['erros_processamento'] = resultado_processamento.get('erros', [])
                    
                    logger.info(f"""✅ Processamento de estoque concluído:
                    - NFs processadas: {stats_estoque['processadas']}
                    - Já processadas: {stats_estoque['ja_processadas']} 
                    - Canceladas: {stats_estoque['canceladas']}
                    - Com embarque: {stats_estoque['com_embarque']}
                    - Sem separação: {stats_estoque['sem_separacao']}
                    - Movimentações criadas: {stats_estoque['movimentacoes_criadas']}
                    - Embarques atualizados: {stats_estoque['embarque_items_atualizados']}
                    """)
                    
                    if stats_estoque['erros_processamento']:
                        logger.warning(f"⚠️ {len(stats_estoque['erros_processamento'])} erros no processamento de estoque")
                else:
                    logger.warning("⚠️ ProcessadorFaturamento retornou None")
                    
            except ImportError as e:
                erro_msg = f"Módulo ProcessadorFaturamento não disponível: {e}"
                logger.error(f"❌ {erro_msg}")
                stats_estoque['erros_processamento'].append(erro_msg)
            except Exception as e:
                erro_msg = f"Erro no processamento de movimentações de estoque: {e}"
                logger.error(f"❌ {erro_msg}")
                stats_estoque['erros_processamento'].append(erro_msg)
            
            
            # ============================================
            # 🔄 SINCRONIZAÇÕES INTEGRADAS (4 MÉTODOS)
            # ============================================
            
            # Estatísticas das sincronizações
            stats_sincronizacao = {
                'entregas_sincronizadas': 0,
                'embarques_revalidados': 0,
                'nfs_embarques_sincronizadas': 0,
                'fretes_lancados': 0,
                'relatorios_consolidados': relatorios_consolidados,
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
                'saldos_carteira_atualizados': saldos_atualizados,  # 🆕 SALDOS ATUALIZADOS
                # 🆕 ESTATÍSTICAS DE CANCELAMENTOS
                'cancelamentos': {
                    'nfs_canceladas': 0,  # Agora processadas em tempo real via _processar_cancelamento_nf
                    'movimentacoes_removidas': 0  # Contabilizadas durante processamento incremental
                },
                # 🆕 ESTATÍSTICAS DAS SINCRONIZAÇÕES
                'sincronizacoes': stats_sincronizacao
            }
            
            logger.info(f"   ✅ SINCRONIZAÇÃO INCREMENTAL COMPLETA CONCLUÍDA:")
            logger.info(f"   ➕ {contador_novos} novos registros inseridos")
            logger.info(f"   ✏️ {contador_atualizados} registros atualizados")
            logger.info(f"   📊 {saldos_atualizados} saldos da carteira atualizados")
            logger.info(f"   📋 {stats_sincronizacao['relatorios_consolidados']} relatórios consolidados")
            logger.info(f"   🔄 {stats_sincronizacao['entregas_sincronizadas']} entregas sincronizadas")
            logger.info(f"   📦 {stats_sincronizacao['embarques_revalidados']} embarques re-validados")
            logger.info(f"   🚚 {stats_sincronizacao['nfs_embarques_sincronizadas']} NFs de embarques sincronizadas")
            logger.info(f"   💰 {stats_sincronizacao['fretes_lancados']} fretes lançados automaticamente")
            logger.info(f"   ⏱️ Tempo execução: {tempo_execucao:.2f}s")
            logger.info(f"   ❌ {contador_erros} erros principais + {len(stats_sincronizacao['erros_sincronizacao'])} erros de sincronização")
            
            # Audit Supply Chain: enriquecer eventos com projecao D0
            if _audit_session_id:
                try:
                    from app.supply_chain.services.enrichment_service import enriquecer_projecao
                    enriquecer_projecao(_audit_session_id)
                except Exception:
                    pass

            return {
                'sucesso': True,
                'estatisticas': estatisticas,
                'registros_novos': contador_novos,
                'registros_atualizados': contador_atualizados,
                'registros_processados': total_processados,
                'tempo_execucao': tempo_execucao,
                'erros': erros + stats_sincronizacao['erros_sincronizacao'] + stats_estoque['erros_processamento'],
                'sincronizacoes': stats_sincronizacao,
                'movimentacoes_estoque': stats_estoque,
                'mensagem': f'🚀 Sincronização incremental completa: {contador_novos} novos, {contador_atualizados} atualizados, {stats_estoque["movimentacoes_criadas"]} movimentações de estoque, {stats_sincronizacao["relatorios_consolidados"]} relatórios consolidados + {stats_sincronizacao["fretes_lancados"]} fretes em {tempo_execucao:.2f}s'
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

    def _processar_sincronizacao_faturamento(self, dados_faturamento: List[Dict]) -> Dict[str, Any]:
        """
        🔄 PROCESSA SINCRONIZAÇÃO DE DADOS DE FATURAMENTO

        Método extraído para reutilização entre sincronização completa e incremental

        Args:
            dados_faturamento: Lista de dados já processados do Odoo

        Returns:
            Dict com estatísticas da sincronização
        """
        try:
            import time
            from app import db

            start_time = time.time()

            if not dados_faturamento:
                return {
                    'sucesso': True,
                    'faturas_processadas': 0,
                    'itens_atualizados': 0,
                    'itens_novos': 0,
                    'mensagem': 'Nenhum dado para processar'
                }

            logger.info(f"📊 Processando {len(dados_faturamento)} registros...")

            # Sanitizar dados antes de processar
            logger.info("🧹 Sanitizando dados de faturamento...")
            dados_faturamento = self._sanitizar_dados_faturamento(dados_faturamento)

            # 📊 ESTATÍSTICAS
            contador_novos = 0
            contador_atualizados = 0
            contador_erros = 0
            erros = []
            nfs_processadas = set()

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

                    # Validar dados essenciais
                    if not numero_nf or not cod_produto:
                        contador_erros += 1
                        erros.append(f"Item sem NF/produto: NF={numero_nf}, Produto={cod_produto}")
                        continue

                    # Adicionar NF ao conjunto de processadas
                    nfs_processadas.add(numero_nf)

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
                            logger.debug(f"✏️ Atualizado status: NF={numero_nf}, Produto={cod_produto}, Status={status_odoo}")
                    else:
                        # ✅ REGISTRO NÃO EXISTE → INSERT
                        novo_registro = FaturamentoProduto(**item_mapeado)
                        db.session.add(novo_registro)
                        contador_novos += 1
                        logger.debug(f"✅ Novo registro: NF={numero_nf}, Produto={cod_produto}")

                except Exception as e:
                    contador_erros += 1
                    erros.append(f"Erro ao processar NF {numero_nf}: {e}")
                    logger.error(f"❌ Erro ao processar item: {e}")
                    continue

            # 💾 COMMIT FINAL
            if contador_novos > 0 or contador_atualizados > 0:
                db.session.commit()
                logger.info(f"💾 Commit realizado: {contador_novos} novos, {contador_atualizados} atualizados")

            tempo_execucao = time.time() - start_time

            # 📊 RETORNAR ESTATÍSTICAS
            return {
                'sucesso': True,
                'faturas_processadas': len(nfs_processadas),
                'itens_novos': contador_novos,
                'itens_atualizados': contador_atualizados,
                'total_processados': contador_novos + contador_atualizados,
                'erros': contador_erros,
                'tempo_execucao': tempo_execucao,
                'detalhes_erros': erros[:10] if erros else []  # Limitar erros retornados
            }

        except Exception as e:
            logger.error(f"❌ Erro no processamento: {e}")
            import traceback
            traceback.print_exc()
            return {
                'sucesso': False,
                'erro': str(e),
                'faturas_processadas': 0,
                'itens_atualizados': 0,
                'itens_novos': 0
            }

    def obter_faturamento_otimizado(self, usar_filtro_postado=True, limite=0, modo_incremental=False, minutos_status=1560):
        """
        🚀 MÉTODO REALMENTE OTIMIZADO - 5 queries + JOIN em memória
        Com filtro obrigatório implementado

        Args:
            usar_filtro_postado: Filtrar apenas faturas postadas
            limite: Limite de registros
            modo_incremental: Se True, busca apenas registros modificados recentemente
            minutos_status: Janela de tempo em minutos para busca incremental
        """
        try:
            logger.info(f"🚀 Busca faturamento otimizada: filtro_postado={usar_filtro_postado}, limite={limite}, incremental={modo_incremental}")

            # Conectar ao Odoo
            if not self.connection:
                return {
                    'sucesso': False,
                    'erro': 'Conexão com Odoo não disponível',
                    'dados': []
                }

            # 🔄 MODO INCREMENTAL - Estratégia simplificada
            if modo_incremental:
                from datetime import datetime, timedelta
                import pytz

                # Usar UTC para garantir compatibilidade com Odoo
                tz_utc = pytz.UTC
                agora_utc = datetime.now(tz_utc)

                # 📊 ESTRATÉGIA SIMPLIFICADA
                # Buscar NFs criadas no período para verificar status
                # (podem ter sido canceladas ou alteradas)

                logger.info("🔄 MODO INCREMENTAL ATIVO - BUSCA POR CREATE_DATE")

                # BUSCA ÚNICA: NFs criadas no período de minutos_status
                data_corte = agora_utc - timedelta(minutes=minutos_status)
                data_corte_str = data_corte.strftime('%Y-%m-%d %H:%M:%S')

                domain = []
                # Buscar NFs criadas no período definido (podem ser novas ou canceladas)
                domain.append(('move_id.create_date', '>=', data_corte_str))

                # Não filtrar por estado para pegar canceladas também
                domain.extend([
                    '|',
                    '|',
                    '|',
                    '|',
                    ('move_id.l10n_br_tipo_pedido', '=', 'venda'),
                    ('move_id.l10n_br_tipo_pedido', '=', 'bonificacao'),
                    ('move_id.l10n_br_tipo_pedido', '=', 'industrializacao'),
                    ('move_id.l10n_br_tipo_pedido', '=', 'exportacao'),
                    ('move_id.l10n_br_tipo_pedido', '=', 'venda-industrializacao')
                ])

                horas_status = minutos_status / 60
                logger.info(f"   📌 Buscando NFs criadas desde: {data_corte_str} UTC (últimas {horas_status:.1f} horas)")
                logger.info(f"   📌 Hora atual UTC: {agora_utc.strftime('%Y-%m-%d %H:%M:%S')}")

                campos_basicos = [
                    'id', 'move_id', 'partner_id', 'product_id',
                    'quantity', 'price_unit', 'price_total', 'date', 'l10n_br_total_nfe'
                ]

                # Executar busca única
                logger.info(f"   🔍 Executando busca de NFs das últimas {horas_status:.1f} horas...")
                dados_odoo_brutos = self.connection.search_read(
                    'account.move.line', domain, campos_basicos, limit=20000
                )
                logger.info(f"      ✅ {len(dados_odoo_brutos)} linhas encontradas")

                # Processar dados usando método otimizado
                if dados_odoo_brutos:
                    dados_processados = self._processar_dados_faturamento_com_multiplas_queries(dados_odoo_brutos)
                else:
                    dados_processados = []

                return {
                    'sucesso': True,
                    'dados': dados_processados,
                    'total_registros': len(dados_processados),
                    'estatisticas': {
                        'total_linhas_odoo': len(dados_odoo_brutos),
                        'janela_horas': horas_status,
                        'queries_executadas': 7,  # 1 busca principal + 6 queries de JOIN
                    },
                    'mensagem': f'⚡ {len(dados_processados)} registros processados (NFs das últimas {horas_status:.1f} horas)'
                }

            # ⚠️ MODO NÃO-INCREMENTAL (busca normal)
            domain = []

            if usar_filtro_postado:
                domain.extend([
                    ('move_id.state', '=', 'posted'),  # Faturas postadas
                    '|',  # Operador OR em domain Odoo
                    '|',
                    '|',
                    '|',
                    ('move_id.l10n_br_tipo_pedido', '=', 'venda'),
                    ('move_id.l10n_br_tipo_pedido', '=', 'bonificacao'),
                    ('move_id.l10n_br_tipo_pedido', '=', 'industrializacao'),
                    ('move_id.l10n_br_tipo_pedido', '=', 'exportacao'),
                    ('move_id.l10n_br_tipo_pedido', '=', 'venda-industrializacao')
                ])
            else:
                domain.extend([
                    '|',  # Operador OR em domain Odoo
                    '|',
                    '|',
                    '|',
                    ('move_id.l10n_br_tipo_pedido', '=', 'venda'),
                    ('move_id.l10n_br_tipo_pedido', '=', 'bonificacao'),
                    ('move_id.l10n_br_tipo_pedido', '=', 'industrializacao'),
                    ('move_id.l10n_br_tipo_pedido', '=', 'exportacao'),
                    ('move_id.l10n_br_tipo_pedido', '=', 'venda-industrializacao')
                ])
            
            campos_basicos = [
                'id', 'move_id', 'partner_id', 'product_id', 
                'quantity', 'price_unit', 'price_total', 'date', 'l10n_br_total_nfe'
            ]
            
            logger.info("📋 Buscando linhas de faturamento...")
            
            # 🚀 SISTEMA DE LOTES INTELIGENTE para evitar timeouts
            if limite and limite > 0:
                # Dashboard/consulta rápida - limite baixo
                dados_odoo_brutos = self.connection.search_read(
                    'account.move.line', domain, campos_basicos, limit=limite * 2
                )
            else:
                # ⚡ SINCRONIZAÇÃO LIMITADA para evitar timeouts
                logger.info("🔄 Usando sincronização limitada...")
                max_records = 20000  # Máximo 20000 registros (aumentado para pegar todas as NFs)
                
                dados_odoo_brutos = self.connection.search_read(
                    'account.move.line',
                    domain,
                    campos_basicos,
                    limit=max_records
                )
                
                logger.info(f"📊 Total carregado: {len(dados_odoo_brutos)} registros (limitado para performance)")
            
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
                    'queries_executadas': 6,  # Agora são 6 queries
                    'total_linhas': len(dados_processados),
                    'linhas_brutas': len(dados_odoo_brutos)
                },
                'mensagem': f'⚡ {len(dados_processados)} registros faturamento (método realmente otimizado com 6 queries)'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    # ============================================
    # 🛠️ MÉTODOS AUXILIARES E DE PROCESSAMENTO
    # ============================================
    
    def _mapear_item_faturamento_otimizado(self, linha, cache_faturas, cache_clientes, cache_produtos, cache_templates, cache_municipios, cache_usuarios):
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
            
            # Template do produto
            template_id = produto.get('product_tmpl_id', [None])[0] if produto.get('product_tmpl_id') else None
            template = cache_templates.get(template_id, {})
            
            # Município do cliente
            municipio_id = cliente.get('l10n_br_municipio_id', [None])[0] if cliente.get('l10n_br_municipio_id') else None
            municipio = cache_municipios.get(municipio_id, {})
            
            # Função auxiliar para extrair valores de relações Many2one
            def extrair_relacao(campo, indice=1):
                if isinstance(campo, list) and len(campo) > indice:
                    return campo[indice]
                return ''
            
            # Extrair município e estado do formato "Cidade (UF)"
            municipio_nome = ''
            estado_uf = ''
            
            # Primeiro tentar do município do Odoo
            if municipio:
                nome_municipio = municipio.get('name', '')
                if nome_municipio:
                    # Se o município tem formato "Cidade (UF)", extrair
                    if '(' in nome_municipio and ')' in nome_municipio:
                        partes = nome_municipio.split('(')
                        municipio_nome = partes[0].strip()
                        if len(partes) > 1:
                            estado_uf = partes[1].replace(')', '').strip()
                    else:
                        municipio_nome = nome_municipio
                        
                        # Buscar estado via state_id do município
                        if municipio.get('state_id'):
                            state_name = municipio['state_id'][1] if isinstance(municipio['state_id'], list) else str(municipio['state_id'])
                            # Mapear nome do estado para sigla
                            estado_uf = self._extrair_sigla_estado(state_name)
            
            # Se ainda não tem município, tentar pegar do cliente diretamente
            if not municipio_nome and cliente.get('l10n_br_municipio_id'):
                municipio_nome = extrair_relacao(cliente.get('l10n_br_municipio_id'), 1)
            
            # Vendedor - MELHORADO: usar múltiplas fontes
            vendedor_nome = ''
            
            # Primeira opção: buscar no cache de usuários
            user_id = fatura.get('invoice_user_id', [None])[0] if fatura.get('invoice_user_id') else None
            if user_id and user_id in cache_usuarios:
                vendedor_nome = cache_usuarios[user_id].get('name', '')
            
            # Segunda opção: user_id do cliente (res.partner)
            if not vendedor_nome:
                cliente_user_id = cliente.get('user_id', [None])[0] if cliente.get('user_id') else None
                if cliente_user_id and cliente_user_id in cache_usuarios:
                    vendedor_nome = cache_usuarios[cliente_user_id].get('name', '')
            
            # Terceira opção: extrair direto da relação se ainda não achou
            if not vendedor_nome and fatura.get('invoice_user_id'):
                vendedor_nome = extrair_relacao(fatura.get('invoice_user_id'), 1)
            
            # Quarta opção: user_id do cliente como relação
            if not vendedor_nome and cliente.get('user_id'):
                vendedor_nome = extrair_relacao(cliente.get('user_id'), 1)
            
            # UF - MELHORADO: múltiplas fontes e validação
            if not estado_uf:
                # Tentar do state_id do cliente
                if cliente.get('state_id'):
                    state_info = cliente['state_id']
                    if isinstance(state_info, list) and len(state_info) > 1:
                        estado_nome = state_info[1]  # Nome do estado
                        # Converter nome para UF
                        if estado_nome:
                            estado_uf = self._converter_estado_para_uf(estado_nome)
                    elif isinstance(state_info, str):
                        estado_uf = state_info[:2].upper()
                
                # Validar se UF é válida (2 caracteres, apenas letras)
                if estado_uf and (len(estado_uf) != 2 or not estado_uf.isalpha()):
                    estado_uf = ''
            
            # Incoterm - buscar do cache ou relação e extrair código entre colchetes
            incoterm_codigo = ''
            if fatura.get('invoice_incoterm_id'):
                incoterm_texto = extrair_relacao(fatura.get('invoice_incoterm_id'), 1)
                if incoterm_texto and '[' in incoterm_texto and ']' in incoterm_texto:
                    # Extrair apenas o código entre colchetes: [CIF] → CIF
                    inicio = incoterm_texto.find('[')
                    fim = incoterm_texto.find(']')
                    if inicio >= 0 and fim > inicio:
                        incoterm_codigo = incoterm_texto[inicio+1:fim]
                else:
                    # Se não tem colchetes, usar o texto completo mas truncar
                    incoterm_codigo = incoterm_texto[:20] if incoterm_texto else ''
            
            # Mapear TODOS os campos de faturamento
            item_mapeado = {
                # 📄 DADOS DA NOTA FISCAL
                'numero_nf': fatura.get('l10n_br_numero_nota_fiscal'),
                'data_fatura': self._parse_date(fatura.get('date')),  # Usar date da fatura via cache
                'origem': fatura.get('invoice_origin', ''),
                'status_nf': self._mapear_status(fatura.get('state', '')),
                'status_odoo_raw': fatura.get('state', ''),  # Status bruto do Odoo para detectar cancelamentos
                
                # 👥 DADOS DO CLIENTE
                'cnpj_cliente': fatura.get('l10n_br_cnpj') or cliente.get('l10n_br_cnpj', ''),
                'nome_cliente': fatura.get('invoice_partner_display_name') or cliente.get('name', ''),
                'municipio': municipio_nome,
                'estado': estado_uf,
                
                # 🏢 DADOS COMERCIAIS
                'vendedor': vendedor_nome,
                'equipe_vendas': extrair_relacao(fatura.get('team_id', ''), 1) if fatura.get('team_id') else '',
                'incoterm': incoterm_codigo,
                
                # 📦 DADOS DO PRODUTO
                'cod_produto': template.get('default_code', ''),  # Do template
                'nome_produto': template.get('name', ''),  # Do template
                'peso_unitario_produto': template.get('gross_weight', 0),  # Do template
                
                # 📊 QUANTIDADES E VALORES
                'qtd_produto_faturado': linha.get('quantity', 0),
                'valor_produto_faturado': linha.get('l10n_br_total_nfe') or linha.get('price_total', 0),
                'preco_produto_faturado': linha.get('price_unit', 0),
                
                # 📏 CAMPOS CALCULADOS
                'peso_total': self._calcular_peso_total(linha.get('quantity', 0), template.get('gross_weight', 0)),
                
                # Metadados
                'created_at': agora_utc_naive(),
                'updated_at': agora_utc_naive(),
                'created_by': 'Sistema Odoo REALMENTE Otimizado'
            }
            
            return item_mapeado
            
        except Exception as e:
            logger.error(f"Erro no mapeamento faturamento otimizado do item: {e}")
            return {}
    
    def _sanitizar_dados_faturamento(self, dados_faturamento: List[Dict]) -> List[Dict]:
        """
        Sanitiza e corrige dados de faturamento antes da inserção.
        Garante que campos não excedam os limites do banco.

        Delega para utilitário compartilhado (reutilizado por ImportacaoFallbackService).
        """
        from app.odoo.utils.sanitizacao_faturamento import sanitizar_dados_faturamento
        return sanitizar_dados_faturamento(dados_faturamento)
    
    def _calcular_peso_total(self, quantidade: float, peso_unitario: float) -> float:
        """
        Calcula peso total do produto
        """
        try:
            return float(quantidade) * float(peso_unitario)
        except (ValueError, TypeError):
            return 0.0
    
    def _extrair_sigla_estado(self, nome_estado: str) -> str:
        """
        Extrai sigla do estado a partir do nome completo
        """
        if not nome_estado:
            return ''
        
        # Mapeamento de estados brasileiros
        estados_map = {
            'São Paulo': 'SP',
            'Rio de Janeiro': 'RJ',
            'Minas Gerais': 'MG',
            'Espírito Santo': 'ES',
            'Bahia': 'BA',
            'Paraná': 'PR',
            'Santa Catarina': 'SC',
            'Rio Grande do Sul': 'RS',
            'Goiás': 'GO',
            'Mato Grosso': 'MT',
            'Mato Grosso do Sul': 'MS',
            'Distrito Federal': 'DF',
            'Ceará': 'CE',
            'Pernambuco': 'PE',
            'Alagoas': 'AL',
            'Sergipe': 'SE',
            'Paraíba': 'PB',
            'Rio Grande do Norte': 'RN',
            'Piauí': 'PI',
            'Maranhão': 'MA',
            'Pará': 'PA',
            'Amapá': 'AP',
            'Amazonas': 'AM',
            'Roraima': 'RR',
            'Acre': 'AC',
            'Rondônia': 'RO',
            'Tocantins': 'TO'
        }
        
        # Buscar no mapeamento
        estado_limpo = nome_estado.strip()
        
        # Se já é uma sigla de 2 caracteres, retornar
        if len(estado_limpo) == 2 and estado_limpo.isupper():
            return estado_limpo
        
        # Buscar no mapeamento
        for nome, sigla in estados_map.items():
            if nome.lower() in estado_limpo.lower():
                return sigla
        
        # Casos específicos conhecidos do Odoo
        casos_especiais = {
            'Sã': 'SP',  # São Paulo truncado
            'RJ': 'RJ',  # Rio de Janeiro já correto
            'MG': 'MG',  # Minas Gerais já correto
        }
        
        if estado_limpo in casos_especiais:
            return casos_especiais[estado_limpo]
        
        # Se não encontrou, tentar pegar as primeiras 2 letras maiúsculas
        return estado_limpo[:2].upper() if estado_limpo else ''

    def _converter_estado_para_uf(self, estado_nome: str) -> str:
        """
        Converte o nome do estado para a sigla do UF.
        """
        estados_brasileiros = {
            'ACRE': 'AC', 'ALAGOAS': 'AL', 'AMAPA': 'AP', 'AMAZONAS': 'AM', 'BAHIA': 'BA', 'CEARA': 'CE',
            'DISTRITO FEDERAL': 'DF', 'ESPIRITO SANTO': 'ES', 'GOIAS': 'GO', 'MARANHAO': 'MA', 'MINAS GERAIS': 'MG',
            'MATO GROSSO DO SUL': 'MS', 'MATO GROSSO': 'MT', 'PARA': 'PA', 'PARAIBA': 'PB', 'PERNAMBUCO': 'PE',
            'PIAUI': 'PI', 'PARANA': 'PR', 'RIO DE JANEIRO': 'RJ', 'RIO GRANDE DO NORTE': 'RN', 'RIO GRANDE DO SUL': 'RS',
            'RONDONIA': 'RO', 'RORAIMA': 'RR', 'SANTA CATARINA': 'SC', 'SAO PAULO': 'SP', 'SERGIPE': 'SE', 'TOCANTINS': 'TO'
        }
        return estados_brasileiros.get(estado_nome.upper(), '')

    def processar_nfs_canceladas_existentes(self) -> Dict[str, Any]:
        """
        Processa todas as NFs que estão canceladas no Odoo mas não foram marcadas corretamente no banco.
        Este método é útil para corrigir NFs que foram importadas antes da correção do bug de cancelamento.
        
        Returns:
            Dict com estatísticas do processamento
        """
        try:
            logger.info("🔍 Buscando NFs canceladas no Odoo que precisam ser corrigidas...")
            
            # 1. Buscar TODAS as NFs canceladas no Odoo
            if not self.connection:
                return {
                    'sucesso': False,
                    'erro': 'Conexão com Odoo não disponível'
                }
            
            # Buscar faturas canceladas
            faturas_canceladas = self.connection.search_read(
                'account.move',
                [
                    ('state', '=', 'cancel'),
                    ('l10n_br_numero_nota_fiscal', '!=', False),
                    '|',
                    '|',
                    '|',
                    '|',
                    ('l10n_br_tipo_pedido', '=', 'venda'),
                    ('l10n_br_tipo_pedido', '=', 'bonificacao'),
                    ('l10n_br_tipo_pedido', '=', 'industrializacao'),
                    ('l10n_br_tipo_pedido', '=', 'exportacao'),
                    ('l10n_br_tipo_pedido', '=', 'venda-industrializacao')
                ],
                ['id', 'l10n_br_numero_nota_fiscal', 'state', 'date', 'partner_id'],
                limit=1000  # Limitar para evitar timeout
            )
            
            logger.info(f"📊 Encontradas {len(faturas_canceladas)} NFs canceladas no Odoo")
            
            if not faturas_canceladas:
                return {
                    'sucesso': True,
                    'mensagem': 'Nenhuma NF cancelada encontrada no Odoo',
                    'total_odoo': 0,
                    'total_corrigidas': 0
                }
            
            # 2. Para cada NF cancelada, verificar e corrigir no banco
            contador_corrigidas = 0
            contador_ja_corretas = 0
            contador_nao_existentes = 0
            erros = []
            
            for fatura in faturas_canceladas:
                numero_nf = fatura.get('l10n_br_numero_nota_fiscal')
                if not numero_nf:
                    continue
                
                try:
                    # Verificar se existe FaturamentoProduto com status diferente de 'Cancelado'
                    faturamentos = FaturamentoProduto.query.filter(
                        FaturamentoProduto.numero_nf == numero_nf,
                        FaturamentoProduto.status_nf != 'Cancelado'
                    ).first()
                    
                    if faturamentos:
                        # NF existe e não está cancelada - CORRIGIR!
                        logger.info(f"🔄 Corrigindo NF {numero_nf} que está cancelada no Odoo...")
                        resultado = self._processar_cancelamento_nf(numero_nf)
                        
                        if resultado:
                            contador_corrigidas += 1
                            logger.info(f"   ✅ NF {numero_nf} corrigida com sucesso")
                        else:
                            erros.append(f"Erro ao corrigir NF {numero_nf}")
                    else:
                        # Verificar se existe mas já está cancelada
                        fat_cancelado = FaturamentoProduto.query.filter_by(
                            numero_nf=numero_nf,
                            status_nf='Cancelado'
                        ).first()
                        
                        if fat_cancelado:
                            contador_ja_corretas += 1
                            logger.debug(f"   ✓ NF {numero_nf} já está correta (Cancelado)")
                        else:
                            contador_nao_existentes += 1
                            logger.debug(f"   ⚠️ NF {numero_nf} não existe no banco")
                    
                except Exception as e:
                    erro_msg = f"Erro ao processar NF {numero_nf}: {e}"
                    logger.error(erro_msg)
                    erros.append(erro_msg)
            
            # 3. Estatísticas finais
            logger.info(f"""
            ✅ CORREÇÃO DE NFs CANCELADAS CONCLUÍDA:
               - Total no Odoo: {len(faturas_canceladas)}
               - Corrigidas: {contador_corrigidas}
               - Já corretas: {contador_ja_corretas}
               - Não existentes: {contador_nao_existentes}
               - Erros: {len(erros)}
            """)
            
            return {
                'sucesso': True,
                'total_odoo': len(faturas_canceladas),
                'total_corrigidas': contador_corrigidas,
                'ja_corretas': contador_ja_corretas,
                'nao_existentes': contador_nao_existentes,
                'erros': erros,
                'mensagem': f'Processadas {contador_corrigidas} NFs canceladas de {len(faturas_canceladas)} encontradas'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar NFs canceladas existentes: {e}")
            return {
                'sucesso': False,
                'erro': str(e),
                'total_corrigidas': 0
            }
    
