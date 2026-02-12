"""
Service para Importação de Entradas de Materiais do Odoo
=========================================================

OBJETIVO:
    Importar recebimentos de materiais (stock.picking + stock.move) do Odoo
    e registrar em MovimentacaoEstoque

REGRAS:
    1. Apenas stock.picking com state='done' (recebidos)
    2. Apenas picking_type_id.code='incoming' (entradas)
    3. Excluir fornecedores do grupo (CNPJ iniciando com 61.724.241 e 18.467.441)
    4. Vincular com PedidoCompras via purchase_id
    5. Registrar em MovimentacaoEstoque tipo=ENTRADA, local=COMPRA

AUTOR: Sistema de Fretes
DATA: 11/11/2025
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from app import db
from app.utils.timezone import agora_utc_naive
from app.estoque.models import MovimentacaoEstoque
from app.manufatura.models import PedidoCompras
from app.producao.models import CadastroPalletizacao
from app.odoo.utils.connection import get_odoo_connection
from app.utils.file_storage import get_file_storage
from io import BytesIO
import base64

logger = logging.getLogger(__name__)


class EntradaMaterialService:
    """
    Service para importação de entradas de materiais do Odoo
    """

    # CNPJs de empresas do grupo (estoque consolidado - não importar)
    CNPJS_GRUPO = ['61.724.241', '18.467.441']

    def __init__(self):
        """Inicializa conexão com Odoo"""
        self.odoo = get_odoo_connection()

    def _eh_fornecedor_grupo(self, cnpj: str) -> bool:
        """
        Verifica se o CNPJ é de uma empresa do grupo

        Args:
            cnpj: CNPJ do fornecedor

        Returns:
            True se for empresa do grupo
        """
        if not cnpj:
            return False

        # Remove formatação
        cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '').strip()

        # Verifica se começa com algum CNPJ do grupo
        for cnpj_grupo in self.CNPJS_GRUPO:
            cnpj_grupo_limpo = cnpj_grupo.replace('.', '')
            if cnpj_limpo.startswith(cnpj_grupo_limpo):
                logger.info(f"⚠️  CNPJ {cnpj} é empresa do grupo - PULANDO")
                return True

        return False

    def importar_entradas(
        self,
        dias_retroativos: int = 7,
        limite: Optional[int] = None
    ) -> Dict:
        """
        Importa entradas de materiais do Odoo

        Args:
            dias_retroativos: Quantos dias para trás buscar (padrão: 7)
            limite: Limite de registros (None = todos)

        Returns:
            Dict com estatísticas da importação
        """
        logger.info("=" * 80)
        logger.info("🚚 INICIANDO IMPORTAÇÃO DE ENTRADAS DE MATERIAIS")
        logger.info("=" * 80)

        resultado = {
            'sucesso': False,
            'entradas_processadas': 0,
            'entradas_novas': 0,
            'entradas_atualizadas': 0,
            'entradas_ignoradas': 0,
            'erros': []
        }

        try:
            # 1. Buscar recebimentos do Odoo
            data_inicio = (agora_utc_naive() - timedelta(days=dias_retroativos)).strftime('%Y-%m-%d')

            logger.info(f"📅 Buscando recebimentos desde {data_inicio}")

            pickings = self._buscar_recebimentos_odoo(data_inicio, limite)

            if not pickings:
                logger.warning("⚠️  Nenhum recebimento encontrado no Odoo")
                resultado['sucesso'] = True
                return resultado

            # 1.1 Filtrar pickings com /DEV/ no nome
            pickings_originais = len(pickings)
            pickings = [p for p in pickings if '/DEV/' not in p.get('name', '')]
            dev_ignorados = pickings_originais - len(pickings)

            if dev_ignorados > 0:
                logger.info(f"⏭️  Ignorados {dev_ignorados} pickings com /DEV/ no nome")
                resultado['entradas_ignoradas'] += dev_ignorados

            if not pickings:
                logger.warning("⚠️  Todos os recebimentos foram filtrados (/DEV/)")
                resultado['sucesso'] = True
                return resultado

            logger.info(f"📦 Total de recebimentos a processar: {len(pickings)}")

            # 2. PRÉ-CARREGAR DADOS EM BATCH (otimização crítica)
            logger.info("🚀 Pré-carregando dados em batch...")
            cache = self._precarregar_dados_batch(pickings)
            logger.info(f"   ✅ Cache preparado: {len(cache['cnpjs'])} CNPJs, "
                       f"{len(cache['codigos'])} códigos, "
                       f"{len(cache['cadastros'])} cadastros, "
                       f"{len(cache['pedidos'])} pedidos")

            # 3. Processar cada recebimento
            for picking in pickings:
                try:
                    picking_id = picking.get('id')
                    picking_name = picking.get('name')

                    logger.info(f"\n📋 Processando recebimento: {picking_name} (ID: {picking_id})")

                    # 3.1 Verificar fornecedor usando CACHE
                    partner = picking.get('partner_id')
                    if not partner or len(partner) < 2:
                        logger.warning(f"⚠️  Recebimento {picking_name} sem fornecedor - PULANDO")
                        resultado['entradas_ignoradas'] += 1
                        continue

                    partner_id = partner[0]
                    cnpj_fornecedor = cache['cnpjs'].get(partner_id)

                    if self._eh_fornecedor_grupo(cnpj_fornecedor):
                        logger.info(f"   ⏭️  Fornecedor do grupo - PULANDO")
                        resultado['entradas_ignoradas'] += 1
                        continue

                    # 3.2 Buscar movimentos do picking (do cache)
                    movimentos = cache['movimentos_por_picking'].get(picking_id, [])

                    if not movimentos:
                        logger.warning(f"⚠️  Recebimento {picking_name} sem movimentos - PULANDO")
                        resultado['entradas_ignoradas'] += 1
                        continue

                    logger.info(f"   📦 Movimentos encontrados: {len(movimentos)}")

                    # 3.3 Processar cada movimento usando CACHE
                    for movimento in movimentos:
                        try:
                            estatisticas = self._processar_movimento(
                                picking=picking,
                                movimento=movimento,
                                cnpj_fornecedor=cnpj_fornecedor,
                                cache=cache  # ✅ Passar cache
                            )

                            resultado['entradas_processadas'] += 1
                            if estatisticas.get('novo'):
                                resultado['entradas_novas'] += 1
                            else:
                                resultado['entradas_atualizadas'] += 1

                        except Exception as e:
                            erro_msg = f"Erro ao processar movimento {movimento.get('id')}: {str(e)}"
                            logger.error(f"❌ {erro_msg}")
                            resultado['erros'].append(erro_msg)

                except Exception as e:
                    erro_msg = f"Erro ao processar recebimento {picking.get('name')}: {str(e)}"
                    logger.error(f"❌ {erro_msg}")
                    resultado['erros'].append(erro_msg)

            # 3. Commit final
            db.session.commit()

            resultado['sucesso'] = True
            logger.info("=" * 80)
            logger.info("✅ IMPORTAÇÃO DE ENTRADAS CONCLUÍDA")
            logger.info(f"   📊 Processadas: {resultado['entradas_processadas']}")
            logger.info(f"   ✨ Novas: {resultado['entradas_novas']}")
            logger.info(f"   🔄 Atualizadas: {resultado['entradas_atualizadas']}")
            logger.info(f"   ⏭️  Ignoradas: {resultado['entradas_ignoradas']}")
            logger.info(f"   ❌ Erros: {len(resultado['erros'])}")
            logger.info("=" * 80)

            return resultado

        except Exception as e:
            db.session.rollback()
            erro_msg = f"Erro fatal na importação de entradas: {str(e)}"
            logger.error(f"❌ {erro_msg}")
            resultado['erros'].append(erro_msg)
            resultado['sucesso'] = False
            return resultado

    def _precarregar_dados_batch(self, pickings: List[Dict]) -> Dict:
        """
        Pré-carrega todos os dados necessários em batch para otimizar performance

        Args:
            pickings: Lista de pickings do Odoo

        Returns:
            Dict com caches de CNPJs, códigos, cadastros e pedidos
        """
        cache = {
            'cnpjs': {},
            'codigos': {},
            'cadastros': {},
            'pedidos': {},
            'movimentos_por_picking': {},
            'dfe_por_pedido': {}  # ✅ DFe ID por pedido de compra
        }

        try:
            # 1. Coletar IDs necessários
            picking_ids = [p['id'] for p in pickings]
            partner_ids = set()
            purchase_ids = set()

            for picking in pickings:
                if picking.get('partner_id'):
                    partner_ids.add(picking['partner_id'][0])
                if picking.get('purchase_id'):
                    purchase_ids.add(str(picking['purchase_id'][0]))

            # 2. Buscar TODOS os movimentos de UMA VEZ (batch completo - 94% mais rápido)
            logger.info(f"   📦 Buscando movimentos de {len(picking_ids)} pickings...")
            movimentos_todos = self.odoo.execute_kw(
                'stock.move',
                'search_read',
                [[['picking_id', 'in', picking_ids]]],
                {'fields': [
                    'id', 'picking_id', 'product_id', 'product_uom_qty',
                    'quantity', 'product_uom', 'date', 'state', 'origin',
                    'purchase_line_id'
                ]}
            )

            # Organizar movimentos por picking
            for mov in movimentos_todos:
                picking_id = mov.get('picking_id')
                if picking_id and isinstance(picking_id, (list, tuple)):
                    picking_id = picking_id[0]

                if picking_id not in cache['movimentos_por_picking']:
                    cache['movimentos_por_picking'][picking_id] = []
                cache['movimentos_por_picking'][picking_id].append(mov)

            # Coletar product_ids
            product_ids = set()
            for mov in movimentos_todos:
                if mov.get('product_id'):
                    product_ids.add(mov['product_id'][0])

            # 3. Buscar CNPJs em BATCH
            if partner_ids:
                logger.info(f"   👥 Buscando {len(partner_ids)} CNPJs em batch...")
                partners = self.odoo.execute_kw(
                    'res.partner',
                    'read',
                    [list(partner_ids)],
                    {'fields': ['l10n_br_cnpj']}
                )
                cache['cnpjs'] = {p['id']: p.get('l10n_br_cnpj') for p in partners}

            # 4. Buscar códigos de produto em BATCH
            if product_ids:
                logger.info(f"   📦 Buscando {len(product_ids)} códigos de produto em batch...")
                produtos = self.odoo.execute_kw(
                    'product.product',
                    'read',
                    [list(product_ids)],
                    {'fields': ['default_code']}
                )
                cache['codigos'] = {p['id']: p.get('default_code') for p in produtos}

            # 5. Buscar cadastros de palletização em BATCH
            codigos_validos = [c for c in cache['codigos'].values() if c]
            if codigos_validos:
                logger.info(f"   📋 Buscando {len(codigos_validos)} cadastros em batch...")
                cadastros = CadastroPalletizacao.query.filter(
                    CadastroPalletizacao.cod_produto.in_(codigos_validos),
                    CadastroPalletizacao.produto_comprado == True
                ).all()
                cache['cadastros'] = {c.cod_produto: c for c in cadastros}

            # 6. Buscar pedidos de compra locais em BATCH
            if purchase_ids:
                logger.info(f"   📝 Buscando {len(purchase_ids)} pedidos locais em batch...")
                pedidos = PedidoCompras.query.filter(
                    PedidoCompras.odoo_id.in_(list(purchase_ids))
                ).all()
                cache['pedidos'] = {p.odoo_id: p for p in pedidos}

            # 7. Buscar dfe_id dos pedidos de compra do Odoo em BATCH
            if purchase_ids:
                logger.info(f"   📄 Buscando dfe_id de {len(purchase_ids)} pedidos em batch...")
                pedidos_odoo = self.odoo.execute_kw(
                    'purchase.order',
                    'read',
                    [list(purchase_ids)],
                    {'fields': ['id', 'dfe_id']}
                )
                cache['dfe_por_pedido'] = {
                    str(p['id']): p.get('dfe_id') for p in pedidos_odoo if p.get('dfe_id')
                }

            return cache

        except Exception as e:
            logger.error(f"❌ Erro ao pré-carregar dados em batch: {e}")
            # Retornar cache vazio em caso de erro (fallback)
            return cache

    def _buscar_recebimentos_odoo(
        self,
        data_inicio: str,
        limite: Optional[int]
    ) -> List[Dict]:
        """
        Busca recebimentos no Odoo

        Args:
            data_inicio: Data mínima (YYYY-MM-DD)
            limite: Limite de registros

        Returns:
            Lista de recebimentos
        """
        try:
            filtros = [
                ['picking_type_code', '=', 'incoming'],  # Apenas recebimentos
                ['state', '=', 'done'],                  # Apenas concluídos
                ['date_done', '>=', data_inicio]         # Data >= início
            ]

            campos = [
                'id',
                'name',
                'state',
                'date_done',
                'scheduled_date',
                'origin',
                'partner_id',
                'purchase_id',
                'location_dest_id',
                'move_ids_without_package'
            ]

            params = {'fields': campos}
            if limite:
                params['limit'] = limite

            pickings = self.odoo.execute_kw(
                'stock.picking',
                'search_read',
                [filtros],
                params
            )

            return pickings or []

        except Exception as e:
            logger.error(f"❌ Erro ao buscar recebimentos do Odoo: {e}")
            return []

    def _processar_dfe_e_salvar_arquivos(
        self,
        pedido_local: PedidoCompras,
        dfe_info: tuple,
        cnpj_fornecedor: str
    ) -> bool:
        """
        Processa DFe e salva PDF/XML no S3/local

        Args:
            pedido_local: Instância do PedidoCompras
            dfe_info: Tupla [dfe_id, nome] do Odoo
            cnpj_fornecedor: CNPJ do fornecedor (para organizar pasta)

        Returns:
            bool: True se processado com sucesso
        """
        if not dfe_info or len(dfe_info) < 1:
            return False

        dfe_id = dfe_info[0] if isinstance(dfe_info, (list, tuple)) else dfe_info

        # Verificar se já processou este DFe
        if pedido_local.dfe_id == str(dfe_id) and pedido_local.nf_pdf_path:
            logger.debug(f"   ⏭️  DFe {dfe_id} já processado anteriormente")
            return True

        try:
            logger.info(f"   📄 Processando DFe ID: {dfe_id}")

            # Buscar dados completos do DFe
            dfe_data = self.odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe',
                'read',
                [[dfe_id]],
                {'fields': [
                    'l10n_br_pdf_dfe', 'l10n_br_xml_dfe',
                    'l10n_br_pdf_dfe_fname', 'l10n_br_xml_dfe_fname',
                    'protnfe_infnfe_chnfe', 'nfe_infnfe_ide_nnf',
                    'nfe_infnfe_ide_serie', 'nfe_infnfe_ide_dhemi',
                    'nfe_infnfe_total_icmstot_vnf'
                ]}
            )

            if not dfe_data or len(dfe_data) == 0:
                logger.warning(f"   ⚠️  DFe {dfe_id} não encontrado")
                return False

            dfe = dfe_data[0]

            # Extrair metadados
            chave_acesso = dfe.get('protnfe_infnfe_chnfe')
            numero_nf = dfe.get('nfe_infnfe_ide_nnf')
            serie_nf = dfe.get('nfe_infnfe_ide_serie')
            data_emissao = dfe.get('nfe_infnfe_ide_dhemi')
            valor_total = dfe.get('nfe_infnfe_total_icmstot_vnf')

            # Preparar FileStorage
            file_storage = get_file_storage()

            # Limpar CNPJ para nome de pasta
            cnpj_limpo = cnpj_fornecedor.replace('.', '').replace('/', '').replace('-', '') if cnpj_fornecedor else 'sem_cnpj'

            # Data para organizar em pastas
            data_hoje = agora_utc_naive()
            pasta_base = f"nfs_entrada/{data_hoje.year}/{data_hoje.month:02d}/{cnpj_limpo}"

            pdf_path = None
            xml_path = None

            # 1. Salvar PDF
            pdf_base64 = dfe.get('l10n_br_pdf_dfe')
            pdf_fname = dfe.get('l10n_br_pdf_dfe_fname') or f"{chave_acesso or dfe_id}.pdf"

            if pdf_base64:
                try:
                    pdf_bytes = base64.b64decode(pdf_base64)

                    # Criar BytesIO com nome de arquivo
                    pdf_file = BytesIO(pdf_bytes)
                    pdf_file.name = pdf_fname

                    # Salvar via FileStorage
                    pdf_path = file_storage.save_file(
                        file=pdf_file,
                        folder=pasta_base,
                        filename=pdf_fname,
                        allowed_extensions=['pdf']
                    )

                    if pdf_path:
                        logger.info(f"   ✅ PDF salvo: {pdf_path}")
                    else:
                        logger.warning(f"   ⚠️  Erro ao salvar PDF")

                except Exception as e:
                    logger.error(f"   ❌ Erro ao processar PDF: {e}")

            # 2. Salvar XML
            xml_base64 = dfe.get('l10n_br_xml_dfe')
            xml_fname = dfe.get('l10n_br_xml_dfe_fname') or f"{chave_acesso or dfe_id}.xml"

            if xml_base64:
                try:
                    xml_bytes = base64.b64decode(xml_base64)

                    # Criar BytesIO com nome de arquivo
                    xml_file = BytesIO(xml_bytes)
                    xml_file.name = xml_fname

                    # Salvar via FileStorage
                    xml_path = file_storage.save_file(
                        file=xml_file,
                        folder=pasta_base,
                        filename=xml_fname,
                        allowed_extensions=['xml']
                    )

                    if xml_path:
                        logger.info(f"   ✅ XML salvo: {xml_path}")
                    else:
                        logger.warning(f"   ⚠️  Erro ao salvar XML")

                except Exception as e:
                    logger.error(f"   ❌ Erro ao processar XML: {e}")

            # 3. Atualizar PedidoCompras
            pedido_local.dfe_id = str(dfe_id)
            pedido_local.nf_pdf_path = pdf_path
            pedido_local.nf_xml_path = xml_path
            pedido_local.nf_chave_acesso = chave_acesso
            pedido_local.nf_numero = numero_nf
            pedido_local.nf_serie = serie_nf

            if data_emissao:
                try:
                    if isinstance(data_emissao, str):
                        pedido_local.nf_data_emissao = datetime.strptime(data_emissao, '%Y-%m-%d').date()
                    else:
                        pedido_local.nf_data_emissao = data_emissao
                except Exception:
                    pass

            if valor_total:
                pedido_local.nf_valor_total = Decimal(str(valor_total))

            pedido_local.atualizado_em = agora_utc_naive()

            logger.info(f"   ✅ PedidoCompras atualizado com dados da NF")

            return True

        except Exception as e:
            logger.error(f"   ❌ Erro ao processar DFe {dfe_id}: {e}")
            return False

    def _processar_movimento(
        self,
        picking: Dict,
        movimento: Dict,
        cnpj_fornecedor: str,
        cache: Dict
    ) -> Dict:
        """
        Processa um movimento e cria/atualiza MovimentacaoEstoque

        Args:
            picking: Dados do picking
            movimento: Dados do movimento
            cnpj_fornecedor: CNPJ do fornecedor

        Returns:
            Dict com estatísticas
        """
        # 1. Extrair dados do movimento
        move_id = str(movimento.get('id'))
        picking_id = str(picking.get('id'))
        picking_name = picking.get('name')

        product = movimento.get('product_id')
        if not product or len(product) < 2:
            logger.warning(f"⚠️  Movimento {move_id} sem produto - PULANDO")
            return {'novo': False}

        product_id, product_name = product[0], product[1]

        # Buscar default_code do CACHE
        cod_produto = cache['codigos'].get(product_id)
        if not cod_produto:
            logger.warning(f"⚠️  Produto {product_id} sem código - PULANDO")
            return {'novo': False}

        # 2. Verificar se produto é comprado usando CACHE
        produto_cadastro = cache['cadastros'].get(str(cod_produto))

        if not produto_cadastro:
            logger.debug(f"   ⏭️  Produto {cod_produto} não é comprado - PULANDO")
            return {'novo': False}

        # 3. Quantidade recebida (usar 'quantity' = quantidade realizada)
        qtd_recebida = Decimal(str(movimento.get('quantity', 0)))  # ✅ Campo correto
        if qtd_recebida <= 0:
            logger.warning(f"⚠️  Movimento {move_id} com quantidade zero - PULANDO")
            return {'novo': False}

        # 4. Data do recebimento
        date_done_str = picking.get('date_done')
        if date_done_str:
            date_done = datetime.fromisoformat(date_done_str.replace('Z', '+00:00')).date()
        else:
            date_done = agora_utc_naive().date()

        # 5. Vincular com pedido local usando CACHE
        purchase_id_odoo = picking.get('purchase_id')
        pedido_local = None

        if purchase_id_odoo and len(purchase_id_odoo) >= 1:
            purchase_odoo_id = str(purchase_id_odoo[0])
            pedido_local = cache['pedidos'].get(purchase_odoo_id)

            # 5.1 Processar DFe e salvar PDF/XML (se houver)
            if pedido_local:
                dfe_info = cache['dfe_por_pedido'].get(purchase_odoo_id)
                if dfe_info:
                    self._processar_dfe_e_salvar_arquivos(
                        pedido_local=pedido_local,
                        dfe_info=dfe_info,
                        cnpj_fornecedor=cnpj_fornecedor
                    )

        # 6. Verificar se já existe
        movimentacao_existe = MovimentacaoEstoque.query.filter_by(
            odoo_move_id=move_id
        ).first()

        if movimentacao_existe:
            # Atualizar
            logger.info(f"   🔄 Atualizando movimentação existente: {cod_produto}")
            movimentacao_existe.qtd_movimentacao = qtd_recebida
            movimentacao_existe.data_movimentacao = date_done
            movimentacao_existe.atualizado_em = agora_utc_naive()
            movimentacao_existe.atualizado_por = 'Sistema Odoo'

            return {'novo': False}

        # 7. Extrair purchase_line_id (apenas o ID numérico)
        purchase_line_id_value = None
        purchase_line_data = movimento.get('purchase_line_id')

        if purchase_line_data:
            # Odoo retorna tupla [ID, Nome]
            if isinstance(purchase_line_data, (list, tuple)) and len(purchase_line_data) > 0:
                purchase_line_id_value = str(purchase_line_data[0])  # Apenas o ID
            else:
                purchase_line_id_value = str(purchase_line_data)

        # 8. Determinar local_movimentacao baseado no tipo de pedido
        # Retorno de vasilhame -> local_movimentacao = 'RETORNO'
        local_mov = 'COMPRA'  # Default
        if pedido_local and hasattr(pedido_local, 'tipo_pedido') and pedido_local.tipo_pedido:
            if 'retorno' in pedido_local.tipo_pedido.lower() and 'vasilhame' in pedido_local.tipo_pedido.lower():
                local_mov = 'RETORNO'
                logger.info(f"   📦 Retorno de vasilhame detectado - local_movimentacao=RETORNO")

        # 9. Criar nova movimentação
        logger.info(f"   ✨ Criando nova movimentação: {cod_produto} - {qtd_recebida}")

        movimentacao = MovimentacaoEstoque(
            # Produto
            cod_produto=str(cod_produto),
            nome_produto=product_name,

            # Movimentação
            data_movimentacao=date_done,
            tipo_movimentacao='ENTRADA',
            local_movimentacao=local_mov,
            qtd_movimentacao=qtd_recebida,

            # Rastreabilidade
            num_pedido=picking.get('origin') or picking_name,
            tipo_origem='ODOO',

            # Odoo - Rastreabilidade
            odoo_picking_id=picking_id,
            odoo_move_id=move_id,
            purchase_line_id=purchase_line_id_value,
            pedido_compras_id=pedido_local.id if pedido_local else None,

            # Observação
            observacao=f"Recebimento {picking_name} - Fornecedor CNPJ: {cnpj_fornecedor or 'N/A'}",

            # Auditoria
            criado_por='Sistema Odoo',
            ativo=True
        )

        db.session.add(movimentacao)
        db.session.flush()  # Para obter o ID da movimentação

        # 10. Baixa automática de remessa de pallet (se for retorno de vasilhame + produto pallet)
        COD_PRODUTO_PALLET = '208000012'
        if local_mov == 'RETORNO' and str(cod_produto) == COD_PRODUTO_PALLET:
            try:
                from app.pallet.utils import normalizar_cnpj
                cnpj_norm = normalizar_cnpj(cnpj_fornecedor) if cnpj_fornecedor else ''

                # Buscar remessa pendente do mesmo CNPJ (pela raiz - 8 primeiros digitos)
                if cnpj_norm and len(cnpj_norm) >= 8:
                    raiz = cnpj_norm[:8]
                    remessa = MovimentacaoEstoque.query.filter(
                        MovimentacaoEstoque.cod_produto == COD_PRODUTO_PALLET,
                        MovimentacaoEstoque.local_movimentacao == 'PALLET',
                        MovimentacaoEstoque.tipo_movimentacao == 'REMESSA',
                        MovimentacaoEstoque.baixado == False,
                        MovimentacaoEstoque.ativo == True
                    ).all()

                    # Filtrar pela raiz do CNPJ
                    for rem in remessa:
                        rem_raiz = normalizar_cnpj(rem.cnpj_destinatario)[:8] if rem.cnpj_destinatario else ''
                        if rem_raiz == raiz:
                            rem.baixado = True
                            rem.baixado_em = agora_utc_naive()
                            rem.baixado_por = 'Sistema Odoo (Retorno Automatico)'
                            rem.movimento_baixado_id = movimentacao.id
                            logger.info(f"   ✅ Remessa NF {rem.numero_nf} baixada automaticamente pelo retorno")
                            break
            except Exception as e:
                logger.warning(f"   ⚠️ Erro ao baixar remessa automaticamente: {e}")

        return {'novo': True}
