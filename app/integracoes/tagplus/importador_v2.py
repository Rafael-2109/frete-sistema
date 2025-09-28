"""
Importador TagPlus usando API v2 com OAuth2
"""

import logging
import re
from datetime import datetime
from app import db
from app.carteira.models import CadastroCliente
from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
from app.integracoes.tagplus.oauth2_v2 import TagPlusOAuth2V2
# Usa o ProcessadorFaturamento padrão que já tem score como fallback
from app.faturamento.services.processar_faturamento import ProcessadorFaturamento

logger = logging.getLogger(__name__)

class ImportadorTagPlusV2:
    """Importador que usa API v2 com OAuth2"""
    
    def __init__(self):
        # Cria gerenciadores OAuth2 para cada API
        self.oauth_clientes = TagPlusOAuth2V2(api_type='clientes')
        self.oauth_notas = TagPlusOAuth2V2(api_type='notas')
        
        # Processador de faturamento padrão (já tem score como fallback)
        self.processador_faturamento = ProcessadorFaturamento()
        
        # Estatísticas
        self.stats = {
            'clientes': {'importados': 0, 'atualizados': 0, 'erros': []},
            'nfs': {'importadas': 0, 'itens': 0, 'erros': []},
            'processamento': None
        }
    
    def testar_conexoes(self):
        """Testa conexão com ambas as APIs"""
        resultado = {}
        
        # Testa API de Clientes
        try:
            sucesso, info = self.oauth_clientes.test_connection()
            resultado['clientes'] = {'sucesso': sucesso, 'info': info}
        except Exception as e:
            resultado['clientes'] = {'sucesso': False, 'info': str(e)}
        
        # Testa API de Notas
        try:
            sucesso, info = self.oauth_notas.test_connection()
            resultado['notas'] = {'sucesso': sucesso, 'info': info}
        except Exception as e:
            resultado['notas'] = {'sucesso': False, 'info': str(e)}
        
        return resultado
    
    def importar_clientes(self, limite=None):
        """Importa clientes usando API v2"""
        try:
            logger.info(f"📥 Importando clientes (limite: {limite or 'sem limite'})...")
            
            pagina = 1
            limite_por_pagina = 50
            total_importados = 0
            
            while True:
                # Faz requisição
                response = self.oauth_clientes.make_request(
                    'GET',
                    '/clientes',
                    params={
                        'pagina': pagina,
                        'limite': limite_por_pagina
                    }
                )
                
                if not response:
                    logger.error("Erro ao buscar clientes: sem resposta")
                    break
                
                if response.status_code == 401:
                    logger.error("Token expirado ou inválido. É necessário autorizar novamente.")
                    self.stats['clientes']['erros'].append("Não autorizado - faça login em /tagplus/oauth/")
                    break
                
                if response.status_code != 200:
                    logger.error(f"Erro ao buscar clientes: {response.status_code} - {response.text}")
                    break
                
                data = response.json()
                
                # API v2 retorna dados em formato diferente
                if isinstance(data, dict):
                    clientes = data.get('data', data.get('clientes', []))
                    tem_mais = data.get('has_more', False) or data.get('proxima_pagina')
                else:
                    clientes = data if isinstance(data, list) else []
                    tem_mais = len(clientes) == limite_por_pagina
                
                if not clientes:
                    logger.info("Não há mais clientes para importar")
                    break
                
                # Processa cada cliente
                for cliente_data in clientes:
                    try:
                        self._processar_cliente(cliente_data)
                        total_importados += 1
                        
                        if limite and total_importados >= limite:
                            break
                            
                    except Exception as e:
                        logger.error(f"Erro ao processar cliente: {e}")
                        self.stats['clientes']['erros'].append(str(e))
                
                # Verifica se deve continuar
                if limite and total_importados >= limite:
                    break
                
                if not tem_mais:
                    break
                
                pagina += 1
            
            # Commit
            db.session.commit()
            
            logger.info(f"✅ Importação concluída: {self.stats['clientes']}")
            return self.stats['clientes']
            
        except Exception as e:
            logger.error(f"❌ Erro na importação: {e}")
            db.session.rollback()
            self.stats['clientes']['erros'].append(str(e))
            return self.stats['clientes']
    
    def importar_nfs(self, data_inicio, data_fim, limite=None, verificar_cancelamentos=True, nf_ids=None):
        """Importa NFs usando API v2 e verifica cancelamentos

        Args:
            data_inicio: Data inicial do período
            data_fim: Data final do período
            limite: Número máximo de NFs a importar
            verificar_cancelamentos: Se deve verificar cancelamentos
            nf_ids: Lista de IDs específicos de NFs para importar (opcional)
        """
        try:
            logger.info(f"📥 Importando NFs de {data_inicio} até {data_fim}...")

            pagina = 1
            limite_por_pagina = 50
            total_nfs = 0
            nfs_para_processar = []

            # Primeiro, buscar NFs sem filtro de status para detectar cancelamentos
            if verificar_cancelamentos and not nf_ids:  # Não verificar cancelamentos se importando IDs específicos
                logger.info("🔍 Verificando NFs canceladas no período...")
                self._verificar_e_processar_cancelamentos(data_inicio, data_fim)

            # Se IDs específicos foram fornecidos, buscar cada NF individualmente
            if nf_ids:
                logger.info(f"🎯 Importando {len(nf_ids)} NFs específicas...")
                for nf_id in nf_ids:
                    try:
                        # Buscar detalhes completos da NF
                        nfe_detalhada = self._buscar_nfe_detalhada(nf_id)
                        if nfe_detalhada:
                            # Verificar status
                            status_nf = nfe_detalhada.get('status', '')
                            numero_nf = str(nfe_detalhada.get('numero', ''))

                            if status_nf != 'A':
                                logger.debug(f"NF {numero_nf} com status '{status_nf}' - pulando importação")
                                if numero_nf and status_nf in ['S', '2', '4']:
                                    self._processar_cancelamento_nf_tagplus(numero_nf, status_nf)
                                continue

                            # Processar NF
                            itens_criados = self._processar_nfe(nfe_detalhada)
                            if itens_criados:
                                nfs_para_processar.extend(itens_criados)
                                total_nfs += 1
                        else:
                            logger.warning(f"⚠️ NF ID {nf_id} não encontrada")
                            self.stats['nfs']['erros'].append(f"NF ID {nf_id} não encontrada")

                        if limite and total_nfs >= limite:
                            break

                    except Exception as e:
                        logger.error(f"Erro ao processar NF ID {nf_id}: {e}")
                        self.stats['nfs']['erros'].append(f"NF ID {nf_id}: {str(e)}")
            else:
                # Busca por período (comportamento original)
                while True:
                    # Faz requisição - removido filtro 'status': 'autorizada' para capturar todas
                    response = self.oauth_notas.make_request(
                        'GET',
                        '/nfes',
                        params={
                            'pagina': pagina,
                            'limite': limite_por_pagina,
                            'data_emissao_inicio': data_inicio.strftime('%Y-%m-%d'),
                            'data_emissao_fim': data_fim.strftime('%Y-%m-%d')
                            # Removido status filter para capturar todas as NFs
                        }
                    )
                
                    if not response:
                        logger.error("Erro ao buscar NFs: sem resposta")
                        break
                    
                    if response.status_code == 401:
                        logger.error("Token expirado ou inválido. É necessário autorizar novamente.")
                        self.stats['nfs']['erros'].append("Não autorizado - faça login em /tagplus/oauth/")
                        break
                    
                    if response.status_code != 200:
                        logger.error(f"Erro ao buscar NFs: {response.status_code} - {response.text}")
                        break
                    
                    data = response.json()
                    
                    # API v2 retorna dados em formato diferente
                    if isinstance(data, dict):
                        nfes = data.get('data', data.get('nfes', []))
                        tem_mais = data.get('has_more', False) or data.get('proxima_pagina')
                    else:
                        nfes = data if isinstance(data, list) else []
                        tem_mais = len(nfes) == limite_por_pagina
                    
                    if not nfes:
                        logger.info("Não há mais NFs para importar")
                        break
                    
                    # Processa cada NF
                    for nfe_resumo in nfes:
                        try:
                            # Verificar status da NF
                            status_nf = nfe_resumo.get('status', '')
                            numero_nf = str(nfe_resumo.get('numero', ''))

                            # Processar apenas NFs aprovadas (status="A")
                            if status_nf != 'A':
                                logger.debug(f"NF {numero_nf} com status '{status_nf}' - pulando importação")
                                # Se não é "A", verificar se precisa marcar como cancelada
                                if numero_nf and status_nf in ['S', '2', '4']:
                                    self._processar_cancelamento_nf_tagplus(numero_nf, status_nf)
                                continue

                            # Busca detalhes se necessário
                            nfe_id = nfe_resumo.get('id') or nfe_resumo.get('numero')
                            nfe_detalhada = self._buscar_nfe_detalhada(nfe_id) if nfe_id else nfe_resumo

                            if nfe_detalhada:
                                # Verificar status novamente nos detalhes
                                status_detalhado = nfe_detalhada.get('status', '')
                                if status_detalhado != 'A':
                                    logger.debug(f"NF {numero_nf} status detalhado '{status_detalhado}' - pulando")
                                    if status_detalhado in ['S', '2', '4']:
                                        self._processar_cancelamento_nf_tagplus(numero_nf, status_detalhado)
                                    continue

                                itens_criados = self._processar_nfe(nfe_detalhada)
                                if itens_criados:
                                    nfs_para_processar.extend(itens_criados)
                                    total_nfs += 1

                                if limite and total_nfs >= limite:
                                    break
                                    
                        except Exception as e:
                            logger.error(f"Erro ao processar NF: {e}")
                            self.stats['nfs']['erros'].append(str(e))
                    
                    # Verifica se deve continuar
                    if limite and total_nfs >= limite:
                        break

                    if not tem_mais:
                        break

                    pagina += 1
            
            # Commit das NFs
            db.session.commit()

            # Consolidar para RelatorioFaturamentoImportado antes de processar
            if nfs_para_processar:
                logger.info(f"📋 Consolidando {len(set(item.numero_nf for item in nfs_para_processar))} NFs para RelatorioFaturamentoImportado...")
                self._consolidar_relatorio_faturamento(nfs_para_processar)
                db.session.commit()

            # Processa faturamento
            if nfs_para_processar:
                logger.info(f"📊 Processando {len(nfs_para_processar)} itens...")
                self.stats['processamento'] = self._processar_faturamento(nfs_para_processar)
            
            logger.info(f"✅ Importação concluída: {self.stats['nfs']}")
            return self.stats
            
        except Exception as e:
            logger.error(f"❌ Erro na importação: {e}")
            db.session.rollback()
            self.stats['nfs']['erros'].append(str(e))
            return self.stats
    
    def _processar_cliente(self, dados):
        """Processa um cliente"""
        # Extrai CNPJ/CPF
        cnpj = re.sub(r'\D', '', str(dados.get('cnpj', dados.get('cpf', ''))))
        
        if not cnpj:
            raise ValueError("Cliente sem CNPJ/CPF")
        
        # Verifica se já existe
        cliente = CadastroCliente.query.filter_by(cnpj_cpf=cnpj).first()
        
        if cliente:
            # Atualiza campos vazios
            campos_atualizados = 0
            
            if not cliente.email and dados.get('email'):
                cliente.email = dados.get('email')
                campos_atualizados += 1
            
            if not cliente.telefone_endereco_ent and dados.get('telefone'):
                cliente.telefone_endereco_ent = self._formatar_telefone(dados.get('telefone'))
                campos_atualizados += 1
            
            if campos_atualizados > 0:
                self.stats['clientes']['atualizados'] += 1
                logger.debug(f"Cliente {cnpj} atualizado")
        else:
            # Cria novo cliente
            cliente = CadastroCliente(
                cnpj_cpf=cnpj,
                raz_social=dados.get('razao_social', dados.get('nome', '')),
                raz_social_red=(dados.get('nome_fantasia', '') or dados.get('nome', ''))[:50],
                
                # Endereço
                cep_endereco_ent=dados.get('cep', ''),
                rua_endereco_ent=dados.get('logradouro', ''),
                endereco_ent=dados.get('numero', ''),
                bairro_endereco_ent=dados.get('bairro', ''),
                nome_cidade=dados.get('cidade', ''),
                municipio=dados.get('cidade', ''),
                estado=dados.get('uf', ''),
                cod_uf=dados.get('uf', ''),
                
                # Contato
                telefone_endereco_ent=self._formatar_telefone(dados.get('telefone', '')),
                email=dados.get('email', ''),
                
                # Endereço de entrega
                cnpj_endereco_ent=cnpj,
                empresa_endereco_ent=dados.get('razao_social', dados.get('nome', '')),
                
                # Controle
                origem='TagPlus',
                criado_em=datetime.utcnow()
            )
            
            db.session.add(cliente)
            self.stats['clientes']['importados'] += 1
            logger.debug(f"Cliente {cnpj} criado")
    
    def _buscar_nfe_detalhada(self, nfe_id):
        """Busca detalhes de uma NF"""
        try:
            response = self.oauth_notas.make_request('GET', f'/nfes/{nfe_id}')
            
            if response and response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erro ao buscar NF {nfe_id}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar NF {nfe_id}: {e}")
            return None
    
    def _processar_nfe(self, nfe_data):
        """Processa uma NF e seus itens"""
        numero_nf = str(nfe_data.get('numero', ''))
        
        # Não verifica apenas se a NF existe, pois pode ter múltiplos itens
        # Vamos verificar item por item mais abaixo
        
        # Extrai cliente
        cliente_data = nfe_data.get('cliente', {})
        cnpj_cliente = re.sub(r'\D', '', str(cliente_data.get('cnpj', cliente_data.get('cpf', ''))))
        
        if not cnpj_cliente:
            raise ValueError(f"NF {numero_nf} sem CNPJ")
        
        # Busca ou cria cliente
        cliente = CadastroCliente.query.filter_by(cnpj_cpf=cnpj_cliente).first()
        if not cliente:
            self._processar_cliente(cliente_data)
            db.session.flush()
            cliente = CadastroCliente.query.filter_by(cnpj_cpf=cnpj_cliente).first()
        
        # Processa itens
        itens_criados = []
        for idx, item in enumerate(nfe_data.get('itens', [])):
            try:
                # Verifica se este item específico já existe
                cod_produto = str(item.get('codigo', ''))
                item_existe = FaturamentoProduto.query.filter_by(
                    numero_nf=numero_nf,
                    cod_produto=cod_produto
                ).first()
                
                if item_existe:
                    logger.debug(f"Item {numero_nf}/{cod_produto} já existe, pulando...")
                    continue
                
                faturamento = FaturamentoProduto(
                    numero_nf=numero_nf,
                    data_fatura=self._parse_data(nfe_data.get('data_emissao')),
                    
                    cnpj_cliente=cnpj_cliente,
                    nome_cliente=cliente.raz_social if cliente else '',
                    municipio=cliente.municipio if cliente else '',
                    estado=cliente.estado if cliente else '',
                    vendedor=cliente.vendedor if cliente else '',
                    equipe_vendas=cliente.equipe_vendas if cliente else '',
                    
                    cod_produto=str(item.get('codigo', '')),
                    nome_produto=item.get('descricao', ''),
                    qtd_produto_faturado=float(item.get('quantidade', 0)),
                    preco_produto_faturado=float(item.get('valor_unitario', 0)),
                    valor_produto_faturado=float(item.get('valor_total', 0)),
                    
                    peso_unitario_produto=float(item.get('peso_unitario', 0)),
                    peso_total=float(item.get('peso_total', 0)) or (
                        float(item.get('peso_unitario', 0)) * float(item.get('quantidade', 0))
                    ),
                    
                    # Captura o pedido do campo correto
                    # Prioridade: numero_pedido > numero_pedido_compra (item) > vazio
                    origem=(
                        nfe_data.get('numero_pedido') or
                        item.get('numero_pedido_compra', '') or
                        ''
                    ),
                    status_nf='Lançado',
                    
                    created_by='ImportTagPlus',
                    updated_by='ImportTagPlus'
                )
                
                db.session.add(faturamento)
                itens_criados.append(faturamento)
                self.stats['nfs']['itens'] += 1
                
            except Exception as e:
                logger.error(f"Erro no item da NF {numero_nf}: {e}")
                self.stats['nfs']['erros'].append(f"Item NF {numero_nf}: {str(e)}")
        
        if itens_criados:
            self.stats['nfs']['importadas'] += 1
            logger.debug(f"NF {numero_nf} importada com {len(itens_criados)} itens")
        
        return itens_criados
    
    def _consolidar_relatorio_faturamento(self, itens_faturamento):
        """Consolida NFs no RelatorioFaturamentoImportado para ProcessadorFaturamento encontrar"""
        try:
            # Agrupar por NF
            nfs_consolidadas = {}

            for item in itens_faturamento:
                numero_nf = item.numero_nf

                if numero_nf not in nfs_consolidadas:
                    nfs_consolidadas[numero_nf] = {
                        'numero_nf': numero_nf,
                        'cnpj_cliente': item.cnpj_cliente,
                        'nome_cliente': item.nome_cliente,
                        'data_fatura': item.data_fatura,
                        'municipio': item.municipio,
                        'estado': item.estado,
                        'vendedor': item.vendedor,
                        'equipe_vendas': item.equipe_vendas,
                        'origem': item.origem,  # Pedido capturado do campo correto
                        'valor_total': 0,
                        'peso_bruto': 0
                    }

                # Somar valores
                nfs_consolidadas[numero_nf]['valor_total'] += float(item.valor_produto_faturado or 0)
                nfs_consolidadas[numero_nf]['peso_bruto'] += float(item.peso_total or 0)

            # Salvar no RelatorioFaturamentoImportado
            for numero_nf, dados_nf in nfs_consolidadas.items():
                # Verificar se já existe
                existe = RelatorioFaturamentoImportado.query.filter_by(
                    numero_nf=numero_nf
                ).first()

                if not existe:
                    relatorio = RelatorioFaturamentoImportado(
                        numero_nf=numero_nf,
                        cnpj_cliente=dados_nf['cnpj_cliente'],
                        nome_cliente=dados_nf['nome_cliente'],
                        data_fatura=dados_nf['data_fatura'],
                        municipio=dados_nf['municipio'],
                        estado=dados_nf['estado'],
                        vendedor=dados_nf['vendedor'],
                        equipe_vendas=dados_nf['equipe_vendas'],
                        origem=dados_nf['origem'],
                        valor_total=dados_nf['valor_total'],
                        peso_bruto=dados_nf['peso_bruto'],
                        origem_importacao='tagplus',
                        criado_em=datetime.now()
                    )
                    db.session.add(relatorio)
                    logger.debug(f"Relatório criado para NF {numero_nf}")
                else:
                    # Atualizar valores se necessário
                    existe.valor_total = dados_nf['valor_total']
                    existe.peso_bruto = dados_nf['peso_bruto']
                    existe.origem = dados_nf['origem'] or existe.origem
                    logger.debug(f"Relatório atualizado para NF {numero_nf}")

            db.session.flush()
            logger.info(f"✅ {len(nfs_consolidadas)} NFs consolidadas no RelatorioFaturamentoImportado")

        except Exception as e:
            logger.error(f"Erro ao consolidar relatório: {e}")
            raise

    def _processar_faturamento(self, itens_faturamento):
        """Processa faturamento usando ProcessadorFaturamento padrão"""
        try:
            # Coletar números únicos de NFs para processar
            nfs_unicas = list(set(item.numero_nf for item in itens_faturamento))

            logger.info(f"🎯 Processando {len(nfs_unicas)} NFs com ProcessadorFaturamento padrão...")

            # ProcessadorFaturamento.processar_nfs_importadas processa por NF, não por item
            resultado = self.processador_faturamento.processar_nfs_importadas(
                usuario='ImportTagPlus',
                nfs_especificas=nfs_unicas
            )

            if resultado:
                return {
                    'success': True,
                    'nfs_processadas': resultado.get('processadas', 0),
                    'itens_processados': len(itens_faturamento),
                    'movimentacoes_criadas': resultado.get('movimentacoes_criadas', 0),
                    'com_embarque': resultado.get('com_embarque', 0),
                    'sem_separacao': resultado.get('sem_separacao', 0),
                    'ja_processadas': resultado.get('ja_processadas', 0)
                }
            else:
                return {
                    'success': False,
                    'erro': 'ProcessadorFaturamento retornou None'
                }
            
        except Exception as e:
            logger.error(f"Erro no processamento: {e}")
            db.session.rollback()
            return {'success': False, 'erro': str(e)}
    
    def _formatar_telefone(self, telefone):
        """Formata telefone"""
        if not telefone:
            return ''
        return re.sub(r'[^\d\s\(\)]', '', str(telefone))[:20]
    
    def _parse_data(self, data_str):
        """Converte string para date"""
        if not data_str:
            return datetime.now().date()
        
        data_str = str(data_str).split('T')[0].split(' ')[0]
        
        for formato in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(data_str, formato).date()
            except Exception as e:
                logger.error(f"Erro ao converter data: {e}")
                continue

        return datetime.now().date()

    def _verificar_e_processar_cancelamentos(self, data_inicio, data_fim):
        """
        Verifica NFs existentes no sistema que podem ter sido canceladas no TagPlus
        Compara status atual no TagPlus com status no banco
        """
        try:
            # Buscar APENAS NFs do TagPlus que estão ativas no nosso sistema
            # Filtrar por origem TagPlus para não verificar NFs do Odoo
            nfs_ativas = db.session.query(
                FaturamentoProduto.numero_nf
            ).filter(
                FaturamentoProduto.data_fatura >= data_inicio,
                FaturamentoProduto.data_fatura <= data_fim,
                FaturamentoProduto.status_nf != 'Cancelado',
                FaturamentoProduto.created_by.like('%TagPlus%')  # APENAS NFs do TagPlus
            ).distinct().all()

            if not nfs_ativas:
                return

            logger.info(f"🔍 Verificando status de {len(nfs_ativas)} NFs no TagPlus...")

            nfs_canceladas = 0
            for (numero_nf,) in nfs_ativas:
                try:
                    # Buscar NF no TagPlus
                    response = self.oauth_notas.make_request(
                        'GET',
                        '/nfes',
                        params={'numero': numero_nf}
                    )

                    if response and response.status_code == 200:
                        data = response.json()
                        nfes = data if isinstance(data, list) else data.get('data', [])

                        if nfes:
                            nfe = nfes[0] if isinstance(nfes, list) else nfes
                            status_atual = nfe.get('status', '')

                            # Se não é mais "A", foi cancelada ou invalidada
                            if status_atual != 'A':
                                logger.info(f"🚨 NF {numero_nf} mudou status para '{status_atual}'")
                                if self._processar_cancelamento_nf_tagplus(numero_nf, status_atual):
                                    nfs_canceladas += 1
                        else:
                            # NF não encontrada no TagPlus = possivelmente deletada/cancelada
                            logger.warning(f"⚠️ NF {numero_nf} não encontrada no TagPlus")
                            if self._processar_cancelamento_nf_tagplus(numero_nf, 'DELETADA'):
                                nfs_canceladas += 1

                except Exception as e:
                    logger.error(f"Erro ao verificar NF {numero_nf}: {e}")
                    continue

            if nfs_canceladas > 0:
                logger.info(f"✅ {nfs_canceladas} NFs marcadas como canceladas")
                db.session.commit()

        except Exception as e:
            logger.error(f"Erro na verificação de cancelamentos: {e}")
            db.session.rollback()

    def _processar_cancelamento_nf_tagplus(self, numero_nf: str, status_tagplus: str) -> bool:
        """
        Processa o cancelamento de uma NF do TagPlus
        Segue a mesma lógica do Odoo para manter consistência

        Status TagPlus:
        - A = Aprovada (única válida)
        - S = Cancelada
        - 2 = Denegada
        - 4 = Inutilizada
        - N = Em digitação
        - 0 = Indiferente
        - DELETADA = Não encontrada no TagPlus
        """
        try:
            from app.estoque.models import MovimentacaoEstoque
            from app.separacao.models import Separacao
            from app.embarques.models import EmbarqueItem

            # Mapear status TagPlus para descrição
            status_map = {
                'S': 'Cancelada',
                '2': 'Denegada',
                '4': 'Inutilizada',
                'N': 'Em digitação',
                '0': 'Indiferente',
                'DELETADA': 'Deletada no TagPlus'
            }
            descricao_status = status_map.get(status_tagplus, f'Status {status_tagplus}')

            logger.info(f"🔄 Processando cancelamento da NF {numero_nf} - Status TagPlus: {descricao_status}")

            # 1. Atualizar FaturamentoProduto
            faturamentos_atualizados = db.session.query(FaturamentoProduto).filter(
                FaturamentoProduto.numero_nf == numero_nf,
                FaturamentoProduto.status_nf != 'Cancelado'
            ).update({
                'status_nf': 'Cancelado',
                'updated_at': datetime.now(),
                'updated_by': f'TagPlus - NF {descricao_status}'
            })

            if faturamentos_atualizados > 0:
                logger.info(f"   ✅ {faturamentos_atualizados} registros de faturamento marcados como Cancelado")

            # 2. Atualizar MovimentacaoEstoque
            movs_atualizadas = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.numero_nf == numero_nf,
                MovimentacaoEstoque.ativo == True
            ).update({
                'status_nf': 'CANCELADO',
                'ativo': False,  # Marcar como inativo
                'atualizado_em': datetime.now(),
                'atualizado_por': f'TagPlus - NF {descricao_status}'
            })

            if movs_atualizadas > 0:
                logger.info(f"   ✅ {movs_atualizadas} movimentações de estoque inativadas")

            # 3. Limpar EmbarqueItem
            embarques_limpos = db.session.query(EmbarqueItem).filter(
                EmbarqueItem.nota_fiscal == numero_nf
            ).update({
                'nota_fiscal': None,
                'erro_validacao': f'NF {descricao_status} no TagPlus'
            })

            if embarques_limpos > 0:
                logger.info(f"   ✅ {embarques_limpos} itens de embarque atualizados")

            # 4. Reverter Separacao
            separacoes_atualizadas = db.session.query(Separacao).filter(
                Separacao.numero_nf == numero_nf
            ).update({
                'numero_nf': None,
                'sincronizado_nf': False
            })

            if separacoes_atualizadas > 0:
                logger.info(f"   ✅ {separacoes_atualizadas} separações revertidas")

            # 5. Atualizar saldos na CarteiraPrincipal (se aplicável)
            # Seguindo o padrão do Odoo, buscar pedidos afetados
            pedidos_afetados = {}
            if faturamentos_atualizados > 0:
                faturamentos_cancelados = db.session.query(FaturamentoProduto).filter(
                    FaturamentoProduto.numero_nf == numero_nf
                ).all()

                for fat in faturamentos_cancelados:
                    if fat.origem and fat.cod_produto:
                        if fat.origem not in pedidos_afetados:
                            pedidos_afetados[fat.origem] = set()
                        pedidos_afetados[fat.origem].add(fat.cod_produto)

                # Atualizar saldos (reusando método do Odoo se disponível)
                if pedidos_afetados:
                    from app.odoo.services.faturamento_service import FaturamentoService
                    service = FaturamentoService()
                    resultado_saldos = service._atualizar_saldos_carteira(pedidos_afetados)
                    logger.info(f"   ✅ {resultado_saldos['atualizados']} saldos atualizados na carteira")

            # 6. Log de auditoria
            logger.info(f"✅ CANCELAMENTO COMPLETO: NF {numero_nf} ({descricao_status})")
            logger.info(f"   - Faturamentos cancelados: {faturamentos_atualizados}")
            logger.info(f"   - Movimentações inativadas: {movs_atualizadas}")
            logger.info(f"   - Embarques limpos: {embarques_limpos}")
            logger.info(f"   - Separações revertidas: {separacoes_atualizadas}")
            if pedidos_afetados:
                logger.info(f"   - Saldos atualizados: {len(pedidos_afetados)} pedidos")

            # Commit se houve alterações
            if faturamentos_atualizados > 0 or movs_atualizadas > 0 or embarques_limpos > 0 or separacoes_atualizadas > 0:
                db.session.commit()
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Erro ao processar cancelamento da NF {numero_nf}: {e}")
            db.session.rollback()
            return False