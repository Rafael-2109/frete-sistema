"""
API para verificação de protocolo no Portal Atacadão
Substitui verificar_posicao.py com funcionalidade expandida
"""

from flask import Blueprint, jsonify, request
from app import db
from app.separacao.models import Separacao
from app.portal.atacadao.playwright_client import AtacadaoPlaywrightClient
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

verificacao_protocolo_bp = Blueprint('verificacao_protocolo', __name__)

class VerificadorProtocoloAtacadao:
    """Verifica protocolo e captura produtos do agendamento"""
    
    def __init__(self):
        self.client = None
    
    def verificar_protocolo_completo(self, protocolo, lote_id=None):
        """
        Verifica protocolo no portal e captura todos os dados
        
        Args:
            protocolo: Número do protocolo
            lote_id: ID do lote de separação (opcional)
            
        Returns:
            dict com informações completas
        """
        try:
            # Importar gerenciador de sessão
            from app.portal.atacadao.login_interativo import garantir_sessao_antes_operacao
            
            # Garantir sessão válida (pode abrir popup para login se necessário)
            if not garantir_sessao_antes_operacao():
                return {
                    'success': False,
                    'message': 'Não foi possível estabelecer sessão com o portal',
                    'requer_login': True
                }
            
            # Iniciar cliente
            self.client = AtacadaoPlaywrightClient(headless=True)
            self.client.iniciar_sessao()
            
            # Verificar login
            if not self.client.verificar_login():
                # Tentar re-login interativo
                from app.portal.atacadao.login_interativo import LoginInterativoAtacadao
                
                login_manager = LoginInterativoAtacadao()
                resultado_login = login_manager.abrir_janela_login_usuario()
                
                if not resultado_login['sucesso']:
                    return {
                        'success': False,
                        'message': 'Sessão expirada. Faça login novamente.',
                        'requer_login': True
                    }
                
                # Reiniciar cliente com nova sessão
                self.client.fechar()
                self.client = AtacadaoPlaywrightClient(headless=True)
                self.client.iniciar_sessao()
            
            # Navegar para página do agendamento
            url_agendamento = f"https://atacadao.hodiebooking.com.br/agendamentos/{protocolo}"
            logger.info(f"Abrindo agendamento: {url_agendamento}")
            
            self.client.page.goto(url_agendamento, timeout=30000, wait_until='networkidle')
            self.client.page.wait_for_timeout(2000)
            
            # Verificar se chegou na página correta
            if "agendamentos" not in self.client.page.url:
                logger.warning(f"Redirecionado para: {self.client.page.url}")
                return {
                    'success': False,
                    'message': 'Protocolo não encontrado ou sem permissão'
                }
            
            resultado = {
                'success': True,
                'protocolo': protocolo,
                'agendamento_confirmado': False,
                'data_aprovada': None,
                'produtos_portal': [],
                'produtos_sistema': [],
                'divergencias': [],
                'status_text': None
            }
            
            # 1. Verificar status do agendamento
            try:
                # Buscar o status na div box-numero-protocolo
                status_element = self.client.page.locator('.box-numero-protocolo .status span').first
                if status_element.count() > 0:
                    status_text = status_element.text_content().strip()
                    resultado['status_text'] = status_text
                    logger.info(f"Status encontrado: {status_text}")
                    
                    # Verificar status negativos primeiro (NÃO atualizar estes)
                    if any(status in status_text for status in ["Cancelado", "No show", "Recusado", "Rejeitado"]):
                        resultado['agendamento_confirmado'] = False
                        logger.warning(f"❌ Agendamento com status negativo: {status_text} - NÃO será atualizado")
                    # Verificar se está confirmado (múltiplos status possíveis)
                    elif any(status in status_text for status in ["Aguardando check-in", "Check-out realizado", "Entregue", "Finalizado"]):
                        resultado['agendamento_confirmado'] = True
                        logger.info(f"✅ Agendamento CONFIRMADO com status: {status_text}")
                    elif "Aguardando aprovação" in status_text:
                        resultado['agendamento_confirmado'] = False
                        logger.info("⏳ Agendamento aguardando aprovação")
                    else:
                        # Status desconhecido - assumir não confirmado mas registrar
                        resultado['agendamento_confirmado'] = False
                        logger.warning(f"⚠️ Status não reconhecido: {status_text}")
                    
                    # 🔄 SEMPRE buscar data (independente do status)
                    try:
                        # Procurar por "Entrega aprovada para" ou "Data de entrega"
                        for label_text in ["Entrega aprovada para", "Data de entrega", "Data agendada"]:
                            data_element = self.client.page.locator(f'label:has-text("{label_text}")').first
                            if data_element.count() > 0:
                                # Pegar o elemento irmão com a data
                                valor_element = data_element.locator('..').locator('span.valor').first
                                if valor_element.count() > 0:
                                    data_text = valor_element.text_content().strip()
                                    # Converter DD/MM/YYYY para YYYY-MM-DD
                                    if data_text and '/' in data_text:
                                        parts = data_text.split('/')
                                        if len(parts) == 3:
                                            resultado['data_aprovada'] = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                                            logger.info(f"📅 Data encontrada ({label_text}): {resultado['data_aprovada']}")
                                            break
                    except Exception as e:
                        logger.warning(f"Erro ao buscar data: {e}")
                        
            except Exception as e:
                logger.warning(f"Erro ao buscar status: {e}")
            
            # 2. Capturar produtos do portal (COM SUPORTE A PAGINAÇÃO)
            try:
                # Aguardar tabela de cargas
                self.client.page.wait_for_selector('.VueTables__table', timeout=5000)
                
                # Função auxiliar para processar produtos da página atual
                def capturar_produtos_pagina():
                    produtos_pagina = []
                    rows = self.client.page.locator('.VueTables__table tbody tr:not(.VueTables__no-results)').all()
                    
                    for row in rows:
                        try:
                            cells = row.locator('td').all()
                            if len(cells) >= 6:
                                # Colunas: Carga | Fornecedor | Pedido | Código | Mercadoria | Quantidade
                                codigo = cells[3].text_content().strip()
                                mercadoria = cells[4].text_content().strip()
                                quantidade = cells[5].text_content().strip()
                                
                                # Converter quantidade
                                quantidade = quantidade.replace(',', '.')
                                try:
                                    quantidade = float(quantidade)
                                except Exception:
                                    quantidade = 0
                                
                                produtos_pagina.append({
                                    'codigo': codigo,
                                    'mercadoria': mercadoria,
                                    'quantidade': quantidade
                                })
                                
                                logger.info(f"Produto capturado: {codigo} - {mercadoria} - Qtd: {quantidade}")
                        except Exception as e:
                            logger.warning(f"Erro ao processar linha da tabela: {e}")
                            continue
                    
                    return produtos_pagina
                
                # Verificar se há paginação
                info_paginacao = self.client._detectar_paginacao()
                
                if not info_paginacao['tem_paginacao']:
                    # Sem paginação, capturar apenas página atual
                    logger.info("📄 Processando página única de produtos")
                    resultado['produtos_portal'] = capturar_produtos_pagina()
                else:
                    # Com paginação, processar todas as páginas
                    logger.info(f"📚 Detectadas {info_paginacao['total_paginas']} páginas de produtos")
                    todos_produtos = []
                    pagina_atual = 1
                    max_paginas = min(info_paginacao['total_paginas'], 10)  # Limitar a 10 páginas
                    
                    while pagina_atual <= max_paginas:
                        logger.info(f"🔄 Processando página {pagina_atual}/{info_paginacao['total_paginas']}")
                        
                        # Capturar produtos da página atual
                        produtos_pagina = capturar_produtos_pagina()
                        todos_produtos.extend(produtos_pagina)
                        logger.info(f"   Capturados {len(produtos_pagina)} produtos nesta página")
                        
                        # Verificar se há próxima página
                        if pagina_atual < info_paginacao['total_paginas']:
                            # Navegar para próxima página
                            if self.client._navegar_proxima_pagina():
                                pagina_atual += 1
                                # Pequena pausa para garantir carregamento
                                self.client.page.wait_for_timeout(500)
                            else:
                                logger.warning("Não foi possível navegar para a próxima página")
                                break
                        else:
                            break
                    
                    resultado['produtos_portal'] = todos_produtos
                    logger.info(f"✅ Total de {len(todos_produtos)} produtos capturados em {pagina_atual} página(s)")
                    
            except Exception as e:
                logger.warning(f"Erro ao buscar produtos: {e}")
            
            # 3. Criar tabela unificada com DE-PARA
            if lote_id:
                # Importar modelos necessários
                from app.portal.atacadao.models import ProdutoDeParaAtacadao
                from app.faturamento.models import FaturamentoProduto
                from app.monitoramento.models import EntregaMonitorada
                
                # Buscar CNPJ do cliente e pedido_cliente
                primeira_sep = Separacao.query.filter_by(separacao_lote_id=lote_id).first()
                cnpj_cliente = primeira_sep.cnpj_cpf if primeira_sep else None
                pedido_cliente = primeira_sep.pedido_cliente if primeira_sep else None
                num_pedido = primeira_sep.num_pedido if primeira_sep else None
                
                # Dicionário unificado de produtos
                produtos_unificados = {}
                
                # 🆕 REFATORAÇÃO: Buscar produtos faturados primeiro
                produtos_faturados = []
                numero_nf_usado = None
                
                # Buscar EntregaMonitorada pelo lote
                entrega_monitorada = EntregaMonitorada.query.filter_by(
                    separacao_lote_id=lote_id
                ).first()
                
                if entrega_monitorada:
                    numero_nf_usado = entrega_monitorada.numero_nf
                    logger.info(f"🔍 EntregaMonitorada encontrada: NF {numero_nf_usado}")
                    
                    # Buscar produtos faturados através da NF
                    produtos_faturados = FaturamentoProduto.query.filter_by(
                        numero_nf=numero_nf_usado,
                        status_nf='Lançado'
                    ).all()
                    
                    logger.info(f"📦 Encontrados {len(produtos_faturados)} produtos faturados na NF {numero_nf_usado}")
                
                # Se não encontrou por EntregaMonitorada, tentar por origem (num_pedido)
                if not produtos_faturados and num_pedido:
                    produtos_faturados = FaturamentoProduto.query.filter_by(
                        origem=num_pedido,
                        status_nf='Lançado'
                    ).all()
                    
                    if produtos_faturados:
                        numero_nf_usado = produtos_faturados[0].numero_nf
                        logger.info(f"📦 Encontrados {len(produtos_faturados)} produtos via pedido {num_pedido}")
                
                # 3.1 Adicionar produtos (priorizar faturados, fallback para separação)
                if produtos_faturados:
                    # 🆕 USAR PRODUTOS FATURADOS
                    logger.info(f"✅ Usando produtos do FaturamentoProduto")
                    for prod_fat in produtos_faturados:
                        if prod_fat.cod_produto not in produtos_unificados:
                            produtos_unificados[prod_fat.cod_produto] = {
                                'codigo_nosso': prod_fat.cod_produto,
                                'descricao_nossa': prod_fat.nome_produto,
                                'qtd_separacao': 0,  # Será qtd_faturada
                                'qtd_agendamento': 0,
                                'diferenca': 0,
                                'tem_divergencia': False,
                                'numero_nf': prod_fat.numero_nf  # 🆕 Rastreabilidade
                            }
                        produtos_unificados[prod_fat.cod_produto]['qtd_separacao'] += float(prod_fat.qtd_produto_faturado or 0)
                else:
                    # FALLBACK: Usar produtos da separação
                    logger.info("⚠️ Sem NF faturada, usando produtos da Separacao")
                    separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()
                    for sep in separacoes:
                        if sep.cod_produto not in produtos_unificados:
                            produtos_unificados[sep.cod_produto] = {
                                'codigo_nosso': sep.cod_produto,
                                'descricao_nossa': sep.nome_produto,
                                'qtd_separacao': 0,
                                'qtd_agendamento': 0,
                                'diferenca': 0,
                                'tem_divergencia': False
                            }
                        produtos_unificados[sep.cod_produto]['qtd_separacao'] += float(sep.qtd_saldo) if sep.qtd_saldo else 0
                
                # 3.2 Adicionar produtos do portal (convertendo códigos)
                produtos_portal_nao_mapeados = []
                
                for prod_portal in resultado['produtos_portal']:
                    codigo_atacadao = prod_portal['codigo']
                    quantidade_portal = prod_portal['quantidade']
                    
                    # Tentar converter código Atacadão para nosso código
                    nosso_codigo = ProdutoDeParaAtacadao.obter_nosso_codigo(codigo_atacadao, cnpj_cliente)
                    
                    if nosso_codigo:
                        # Produto mapeado - adicionar ou atualizar
                        if nosso_codigo not in produtos_unificados:
                            # Produto está no portal mas não na separação
                            # Buscar descrição no DE-PARA
                            depara = ProdutoDeParaAtacadao.query.filter_by(
                                codigo_nosso=nosso_codigo,
                                ativo=True
                            ).first()
                            
                            nome_produto = depara.descricao_nosso if depara else f'Produto {nosso_codigo}'
                            
                            produtos_unificados[nosso_codigo] = {
                                'codigo_nosso': nosso_codigo,
                                'descricao_nossa': nome_produto,
                                'qtd_separacao': 0,
                                'qtd_agendamento': 0,
                                'diferenca': 0,
                                'tem_divergencia': False
                            }
                        
                        produtos_unificados[nosso_codigo]['qtd_agendamento'] += quantidade_portal
                    else:
                        # Produto não mapeado - guardar para avisar
                        produtos_portal_nao_mapeados.append({
                            'codigo_atacadao': codigo_atacadao,
                            'descricao': prod_portal['mercadoria'],
                            'quantidade': quantidade_portal
                        })
                        logger.warning(f"Código Atacadão {codigo_atacadao} sem DE-PARA configurado")
                
                # 3.3 Calcular diferenças e identificar divergências
                for codigo, produto in produtos_unificados.items():
                    produto['diferenca'] = produto['qtd_agendamento'] - produto['qtd_separacao']
                    produto['tem_divergencia'] = abs(produto['diferenca']) > 0.01
                
                # 3.4 Preparar resultado unificado
                resultado['produtos_unificados'] = list(produtos_unificados.values())
                resultado['produtos_nao_mapeados'] = produtos_portal_nao_mapeados
                
                # Manter compatibilidade com código existente
                resultado['produtos_sistema'] = [
                    {
                        'cod_produto': p['codigo_nosso'],
                        'nome_produto': p['descricao_nossa'],
                        'qtd_saldo': p['qtd_separacao']
                    }
                    for p in produtos_unificados.values()
                    if p['qtd_separacao'] > 0
                ]
                
                # 3.5 Contar divergências
                total_divergencias = sum(1 for p in produtos_unificados.values() if p['tem_divergencia'])
                if total_divergencias > 0:
                    resultado['divergencias'].append(f"{total_divergencias} produto(s) com divergência de quantidade")
                
                if produtos_portal_nao_mapeados:
                    resultado['divergencias'].append(f"{len(produtos_portal_nao_mapeados)} produto(s) sem mapeamento DE-PARA")
            
            # Screenshot para debug
            self.client.page.screenshot(path=f"protocolo_{protocolo}.png")
            logger.info(f"Screenshot salvo: protocolo_{protocolo}.png")
            
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao verificar protocolo: {e}")
            return {
                'success': False,
                'message': f'Erro ao verificar protocolo: {str(e)}'
            }
        finally:
            if self.client:
                self.client.fechar()


@verificacao_protocolo_bp.route('/api/verificar-protocolo-portal', methods=['POST'])
def verificar_protocolo_portal():
    """
    API endpoint para verificar protocolo no portal
    """
    try:
        data = request.get_json()
        lote_id = data.get('lote_id')
        protocolo = data.get('protocolo')
        
        if not protocolo:
            return jsonify({
                'success': False,
                'message': 'Protocolo é obrigatório'
            })
        
        logger.info(f"Verificando protocolo {protocolo} para lote {lote_id}")
        
        # Usar a classe verificadora
        verificador = VerificadorProtocoloAtacadao()
        resultado = verificador.verificar_protocolo_completo(protocolo, lote_id)
        
        # 🔄 Atualizar se tiver sucesso e data (MAS não para status negativos)
        status_negativos = ["Cancelado", "No show", "Recusado", "Rejeitado"]
        is_status_negativo = resultado.get('status_text') and any(neg in resultado.get('status_text', '') for neg in status_negativos)
        
        if is_status_negativo:
            logger.warning(f"❌ Status negativo detectado: '{resultado.get('status_text')}' - NÃO será atualizado no banco de dados")
        elif resultado.get('success') and lote_id and resultado.get('data_aprovada'):
            try:
                logger.info(f"🔄 Iniciando atualização de datas - Lote: {lote_id}, Data aprovada: {resultado['data_aprovada']}")
                
                # Atualizar Separacao
                separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()
                logger.info(f"📦 Encontradas {len(separacoes)} separações para atualizar")
                
                for sep in separacoes:
                    data_anterior_sep = sep.agendamento
                    # Atualizar confirmação baseada no resultado do portal
                    if resultado.get('agendamento_confirmado'):
                        sep.agendamento_confirmado = True
                    sep.agendamento = datetime.strptime(resultado['data_aprovada'], '%Y-%m-%d').date()
                    logger.info(f"  - Separação #{sep.id}: data {data_anterior_sep} → {sep.agendamento}, confirmado: {sep.agendamento_confirmado}")
                
                # 🆕 Atualizar AgendamentoEntrega em EntregaMonitorada
                from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
                
                # Buscar EntregaMonitorada pelo lote
                logger.info(f"🔍 Buscando EntregaMonitorada com lote_id: {lote_id}")
                entrega_monitorada = EntregaMonitorada.query.filter_by(
                    separacao_lote_id=lote_id
                ).first()
                
                if entrega_monitorada:
                    logger.info(f"✅ EntregaMonitorada encontrada: #{entrega_monitorada.id}, data_agenda atual: {entrega_monitorada.data_agenda}")
                    
                    # Buscar o último agendamento com este protocolo
                    logger.info(f"🔍 Buscando AgendamentoEntrega com entrega_id={entrega_monitorada.id} e protocolo={protocolo}")
                    agendamento = AgendamentoEntrega.query.filter_by(
                        entrega_id=entrega_monitorada.id,
                        protocolo_agendamento=protocolo
                    ).order_by(AgendamentoEntrega.criado_em.desc()).first()
                    
                    if agendamento:
                        logger.info(f"✅ AgendamentoEntrega encontrado: #{agendamento.id}, status: {agendamento.status}, data_agendada atual: {agendamento.data_agendada}")
                        
                        # Atualizar status para confirmado SE ainda estiver aguardando
                        if agendamento.status == 'aguardando':
                            agendamento.status = 'confirmado'
                            agendamento.confirmado_por = 'Portal Atacadão'
                            agendamento.confirmado_em = datetime.utcnow()
                            agendamento.observacoes_confirmacao = f'Confirmado automaticamente via portal - Status: {resultado.get("status_text", "Aguardando check-in")}'
                            logger.info(f"📝 AgendamentoEntrega #{agendamento.id} - status atualizado para 'confirmado'")
                        else:
                            logger.info(f"ℹ️ AgendamentoEntrega #{agendamento.id} já está com status: {agendamento.status}")
                        
                        # 🔄 SEMPRE atualizar data se houver divergência (independente do status)
                        if resultado.get('data_aprovada'):
                            nova_data = datetime.strptime(resultado['data_aprovada'], '%Y-%m-%d').date()
                            logger.info(f"📅 Nova data do portal: {nova_data}")
                            
                            # Atualizar AgendamentoEntrega.data_agendada
                            if agendamento.data_agendada != nova_data:
                                data_anterior_agendamento = agendamento.data_agendada
                                agendamento.data_agendada = nova_data
                                
                                # Adicionar observação sobre mudança de data
                                if not agendamento.observacoes_confirmacao:
                                    agendamento.observacoes_confirmacao = ''
                                agendamento.observacoes_confirmacao += f' | Data atualizada de {data_anterior_agendamento.strftime("%d/%m/%Y") if data_anterior_agendamento else "N/A"} para {nova_data.strftime("%d/%m/%Y")}'
                                logger.info(f"✅ AgendamentoEntrega #{agendamento.id} - data_agendada atualizada: {data_anterior_agendamento} → {nova_data}")
                            else:
                                logger.info(f"ℹ️ AgendamentoEntrega #{agendamento.id} - data já está correta: {agendamento.data_agendada}")
                            
                            # Atualizar EntregaMonitorada.data_agenda
                            if entrega_monitorada.data_agenda != nova_data:
                                data_anterior_entrega = entrega_monitorada.data_agenda
                                entrega_monitorada.data_agenda = nova_data
                                logger.info(f"✅ EntregaMonitorada #{entrega_monitorada.id} - data_agenda atualizada: {data_anterior_entrega} → {nova_data}")
                            else:
                                logger.info(f"ℹ️ EntregaMonitorada #{entrega_monitorada.id} - data já está correta: {entrega_monitorada.data_agenda}")
                        else:
                            logger.warning(f"⚠️ Sem data_aprovada no resultado do portal")
                    else:
                        logger.warning(f"⚠️ AgendamentoEntrega não encontrado para entrega_id={entrega_monitorada.id} e protocolo={protocolo}")
                        
                        # 🔄 AINDA ASSIM, atualizar EntregaMonitorada se houver data aprovada
                        if resultado.get('data_aprovada'):
                            nova_data = datetime.strptime(resultado['data_aprovada'], '%Y-%m-%d').date()
                            logger.info(f"📅 Atualizando EntregaMonitorada mesmo sem AgendamentoEntrega - nova data: {nova_data}")
                            
                            if entrega_monitorada.data_agenda != nova_data:
                                data_anterior_entrega = entrega_monitorada.data_agenda
                                entrega_monitorada.data_agenda = nova_data
                                logger.info(f"✅ EntregaMonitorada #{entrega_monitorada.id} - data_agenda atualizada (sem agendamento): {data_anterior_entrega} → {nova_data}")
                else:
                    logger.warning(f"⚠️ EntregaMonitorada não encontrada para lote_id: {lote_id}")
                
                db.session.commit()
                logger.info(f"✅ COMMIT realizado - Separações, AgendamentoEntrega e EntregaMonitorada atualizados com sucesso!")
            except Exception as e:
                logger.error(f"Erro ao atualizar separação/agendamento: {e}")
                db.session.rollback()
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Erro na API verificar_protocolo: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao processar requisição: {str(e)}'
        })


@verificacao_protocolo_bp.route('/api/atualizar-status-separacao', methods=['POST'])
def atualizar_status_separacao():
    """
    Atualiza status da separação com dados do portal
    """
    try:
        data = request.get_json()
        lote_id = data.get('lote_id')
        agendamento = data.get('agendamento')
        agendamento_confirmado = data.get('agendamento_confirmado', False)
        
        if not lote_id:
            return jsonify({
                'success': False,
                'message': 'Lote ID é obrigatório'
            })
        
        # Buscar e atualizar separações
        separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()
        if not separacoes:
            return jsonify({
                'success': False,
                'message': 'Separação não encontrada'
            })
        
        for sep in separacoes:
            if agendamento:
                # Converter string para date se necessário
                if isinstance(agendamento, str):
                    sep.agendamento = datetime.strptime(agendamento, '%Y-%m-%d').date()
                else:
                    sep.agendamento = agendamento
            sep.agendamento_confirmado = agendamento_confirmado
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Status atualizado com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao atualizar status: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro ao atualizar status: {str(e)}'
        })


# Função helper para uso direto (compatibilidade com verificar_posicao.py)
def verificar_posicao_agendamento(protocolo):
    """Função helper para verificar posição (compatibilidade)"""
    verificador = VerificadorProtocoloAtacadao()
    return verificador.verificar_protocolo_completo(protocolo)


if __name__ == "__main__":
    # Teste direto
    import sys
    
    if len(sys.argv) > 1:
        protocolo = sys.argv[1]
    else:
        protocolo = input("Digite o número do protocolo: ").strip()
    
    print(f"\n🔍 Verificando protocolo {protocolo}...")
    
    resultado = verificar_posicao_agendamento(protocolo)
    
    if resultado['success']:
        print(f"\n✅ Protocolo: {resultado['protocolo']}")
        print(f"   📊 Status: {resultado.get('status_text', 'Não identificado')}")
        
        if resultado['agendamento_confirmado']:
            print(f"   ✅ Agendamento CONFIRMADO")
            if resultado['data_aprovada']:
                print(f"   📅 Data aprovada: {resultado['data_aprovada']}")
        else:
            print(f"   ⏳ Aguardando aprovação")
        
        if resultado['produtos_portal']:
            print(f"\n   📦 Produtos no portal: {len(resultado['produtos_portal'])}")
            for prod in resultado['produtos_portal']:
                print(f"      - {prod['codigo']}: {prod['mercadoria']} (Qtd: {prod['quantidade']})")
    else:
        print(f"\n❌ {resultado['message']}")