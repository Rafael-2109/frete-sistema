"""
Service para Recebimento LF (La Famiglia -> Nacom Goya)
========================================================

Responsabilidades:
- Buscar DFes da LF disponiveis no Odoo (NFs de retorno de industrializacao)
- Buscar detalhes de um DFe: linhas separadas por CFOP (manual vs auto)
- Copiar lotes do faturamento da LF para produtos CFOP=1902
- Salvar recebimento local + enqueue job RQ (fire-and-forget)
- Listar recebimentos com status
- Retry de recebimentos com erro

Contexto:
- LF (company_id=5) envia insumos para FB (company_id=1) industrializar
- FB recebe NF de retorno da LF (DFe aparece na company_id=1)
- CFOP=1902: retorno de insumos/embalagens (lotes copiados automaticamente)
- CFOP!=1902: produto acabado (lotes preenchidos pelo usuario)
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from app import db
from app.utils.timezone import agora_utc_naive, agora_utc
from app.utils.database_retry import commit_with_retry
from app.recebimento.models import RecebimentoLf, RecebimentoLfLote
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.utils.dfe_utils import situacao_nf_valida

logger = logging.getLogger(__name__)


class RecebimentoLfService:
    """Service para operacoes de Recebimento LF."""

    # IDs fixos (conforme IDS_FIXOS.md)
    CNPJ_LF = '18.467.441/0001-63'  # Formato Odoo (com pontuacao)
    COMPANY_FB = 1
    COMPANY_LF = 5

    # Campos do DFe para busca
    CAMPOS_DFE = [
        'id', 'l10n_br_status', 'l10n_br_situacao_dfe',
        'nfe_infnfe_ide_nnf', 'nfe_infnfe_ide_serie',
        'nfe_infnfe_ide_dhemi', 'nfe_infnfe_emit_cnpj',
        'nfe_infnfe_emit_xnome', 'nfe_infnfe_dest_cnpj',
        'nfe_infnfe_total_icmstot_vnf',
        'protnfe_infnfe_chnfe', 'l10n_br_tipo_pedido',
        'l10n_br_data_entrada', 'purchase_id',
    ]

    # Campos das linhas do DFe
    CAMPOS_DFE_LINE = [
        'id', 'dfe_id', 'det_prod_cfop', 'det_prod_cprod',
        'det_prod_xprod', 'det_prod_qcom', 'det_prod_ucom',
        'det_prod_vuncom', 'det_prod_vprod', 'product_id',
    ]

    def buscar_dfes_lf_disponiveis(self, minutos=60, data_inicio=None, data_fim=None):
        """
        Busca DFes no Odoo emitidos pela LA FAMIGLIA (LF) para NACOM GOYA (FB).

        Filtros:
        - nfe_infnfe_emit_cnpj = CNPJ_LF
        - company_id = COMPANY_FB (FB recebe)
        - l10n_br_situacao_dfe != 'CANCELADA'/'INUTILIZADA' (filtro Python, nao Odoo)
        - Janela temporal: data_inicio/data_fim OU ultimos N minutos
        - Nao ja processado localmente

        Aceita qualquer l10n_br_status (01-04), pois o sistema avanca automaticamente.

        Args:
            minutos: Janela temporal em minutos (default 60). Ignorado se data_inicio/data_fim.
            data_inicio: Data inicio do range (string ISO YYYY-MM-DD). Opcional.
            data_fim: Data fim do range (string ISO YYYY-MM-DD). Opcional.

        Returns:
            Dict com lista de DFes e total
        """
        try:
            odoo = get_odoo_connection()

            # Buscar DFes da LF no Odoo
            filtro = [
                ['nfe_infnfe_emit_cnpj', '=', self.CNPJ_LF],
                ['company_id', '=', self.COMPANY_FB],
                # NAO filtrar l10n_br_situacao_dfe no domain Odoo:
                # - Campo vazio em ~99% dos DFes (ref: dfe_utils.py:31)
                # - Odoo 'not in' exclui registros NULL → zero resultados
                # - Filtragem feita em Python abaixo via situacao_nf_valida()
            ]

            # Filtro temporal: range de datas OU ultimos N minutos
            if data_inicio and data_fim:
                # Sincronizar: busca por data de emissao da NF (negocio)
                filtro.append(['nfe_infnfe_ide_dhemi', '>=', f'{data_inicio} 00:00:00'])
                filtro.append(['nfe_infnfe_ide_dhemi', '<=', f'{data_fim} 23:59:59'])
                logger.info(f"Buscando DFes LF no range {data_inicio} a {data_fim}")
            else:
                # Atualizar: busca por data de modificacao no Odoo (operacional)
                # Usa write_date (nao nfe_infnfe_ide_dhemi) — padrao do codebase
                # Ref: dfe_utils.py:189, validacao_fiscal_job.py:171
                # CORREÇÃO TIMEZONE: Odoo write_date é UTC → usar agora_utc()
                data_limite = (agora_utc() - timedelta(minutes=minutos)).strftime('%Y-%m-%d %H:%M:%S')
                filtro.append(['write_date', '>=', data_limite])
                logger.info(f"Buscando DFes LF dos ultimos {minutos} minutos (desde {data_limite})")

            dfes_odoo = odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe', 'search_read',
                [filtro],
                {
                    'fields': self.CAMPOS_DFE,
                    'order': 'nfe_infnfe_ide_dhemi desc',
                    'limit': 100,
                }
            )

            if not dfes_odoo:
                return {'dfes': [], 'total': 0}

            # Filtrar situacao invalida em Python (CANCELADA/INUTILIZADA)
            # Ref: dfe_utils.py:39 — trata None/vazio como valido
            dfes_odoo = [d for d in dfes_odoo if situacao_nf_valida(d.get('l10n_br_situacao_dfe'))]

            if not dfes_odoo:
                return {'dfes': [], 'total': 0}

            # Filtrar DFes ja processados localmente
            dfe_ids_processados = set()
            recebimentos_existentes = RecebimentoLf.query.filter(
                RecebimentoLf.status.in_(['pendente', 'processando', 'processado'])
            ).all()
            for r in recebimentos_existentes:
                dfe_ids_processados.add(r.odoo_dfe_id)

            # Filtrar DFes que ja tem PO vinculado (purchase_id preenchido E status >= 06)
            # Esses ja foram processados por outro meio
            dfes_disponiveis = []
            for dfe in dfes_odoo:
                dfe_id = dfe['id']

                # Pular se ja processado localmente
                if dfe_id in dfe_ids_processados:
                    continue

                # Pular se ja tem PO e status >= 06 (concluido)
                if dfe.get('purchase_id') and dfe.get('l10n_br_status') in ('06', '07'):
                    continue

                dfes_disponiveis.append({
                    'id': dfe['id'],
                    'numero_nf': dfe.get('nfe_infnfe_ide_nnf', ''),
                    'serie': dfe.get('nfe_infnfe_ide_serie', ''),
                    'data_emissao': dfe.get('nfe_infnfe_ide_dhemi', ''),
                    'emitente_cnpj': dfe.get('nfe_infnfe_emit_cnpj', ''),
                    'emitente_nome': dfe.get('nfe_infnfe_emit_xnome', ''),
                    'valor_total': dfe.get('nfe_infnfe_total_icmstot_vnf', 0),
                    'chave_nfe': dfe.get('protnfe_infnfe_chnfe', ''),
                    'status_dfe': dfe.get('l10n_br_status', ''),
                    'tipo_pedido': dfe.get('l10n_br_tipo_pedido', ''),
                    'tem_po': bool(dfe.get('purchase_id')),
                })

            return {
                'dfes': dfes_disponiveis,
                'total': len(dfes_disponiveis),
            }

        except Exception as e:
            logger.error(f"Erro ao buscar DFes LF: {e}")
            raise

    def buscar_detalhes_dfe(self, dfe_id):
        """
        Busca detalhes de um DFe + suas linhas, separando por CFOP.

        Para CFOP=1902: busca lotes do faturamento da LF no Odoo.
        Para CFOP!=1902: retorna para preenchimento manual pelo usuario.

        Args:
            dfe_id: ID do DFe no Odoo

        Returns:
            Dict com info_dfe, linhas_manuais (CFOP!=1902), linhas_auto (CFOP=1902)
        """
        try:
            odoo = get_odoo_connection()

            # 1. Buscar DFe
            dfe = odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe', 'search_read',
                [[['id', '=', dfe_id]]],
                {'fields': self.CAMPOS_DFE, 'limit': 1}
            )

            if not dfe:
                raise ValueError(f"DFe {dfe_id} nao encontrado no Odoo")

            dfe = dfe[0]

            # 2. Buscar linhas do DFe (GOTCHA: lines_ids NAO existe no dfe,
            #    buscar via l10n_br_ciel_it_account.dfe.line com filtro dfe_id)
            linhas = odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe.line', 'search_read',
                [[['dfe_id', '=', dfe_id]]],
                {'fields': self.CAMPOS_DFE_LINE}
            )

            # 3. Separar por CFOP
            # CFOP 5902 (emissor) = 1902 (receptor): retorno de insumos/embalagens
            # O DFe contem o CFOP do emissor (LF), por isso checamos 5902
            CFOPS_RETORNO = ('5902', '1902')
            linhas_manuais = []  # CFOP != 5902/1902 (produto acabado)
            linhas_auto = []     # CFOP = 5902/1902 (insumos — lotes auto)

            for linha in linhas:
                cfop = str(linha.get('det_prod_cfop', '')).strip()
                product_id = linha['product_id'][0] if linha.get('product_id') else None

                item = {
                    'dfe_line_id': linha['id'],
                    'cfop': cfop,
                    'cod_produto': linha.get('det_prod_cprod', ''),
                    'nome_produto': linha.get('det_prod_xprod', ''),
                    'quantidade': Decimal(str(linha.get('det_prod_qcom', 0) or 0)),
                    'unidade': linha.get('det_prod_ucom', ''),
                    'valor_unitario': Decimal(str(linha.get('det_prod_vuncom', 0) or 0)),
                    'valor_total': Decimal(str(linha.get('det_prod_vprod', 0) or 0)),
                    'product_id': product_id,
                }

                if cfop in CFOPS_RETORNO:
                    linhas_auto.append(item)
                else:
                    linhas_manuais.append(item)

            # 4. Para linhas_auto (CFOP 5902/1902): lote = numero da NF
            # Componentes/insumos nao tem lote proprio no picking da LF;
            # convencao: usar numero da NF como identificador de lote
            numero_nf = dfe.get('nfe_infnfe_ide_nnf', '')
            for item in linhas_auto:
                item['lote_nome'] = numero_nf
                item['data_validade'] = None
                item['lote_origem'] = 'numero_nf'

            # 5. Montar retorno
            info_dfe = {
                'id': dfe['id'],
                'numero_nf': dfe.get('nfe_infnfe_ide_nnf', ''),
                'serie': dfe.get('nfe_infnfe_ide_serie', ''),
                'data_emissao': dfe.get('nfe_infnfe_ide_dhemi', ''),
                'emitente_cnpj': dfe.get('nfe_infnfe_emit_cnpj', ''),
                'emitente_nome': dfe.get('nfe_infnfe_emit_xnome', ''),
                'valor_total': dfe.get('nfe_infnfe_total_icmstot_vnf', 0),
                'chave_nfe': dfe.get('protnfe_infnfe_chnfe', ''),
                'status_dfe': dfe.get('l10n_br_status', ''),
            }

            return {
                'info_dfe': info_dfe,
                'linhas_manuais': linhas_manuais,
                'linhas_auto': linhas_auto,
                'total_linhas': len(linhas),
                'total_manuais': len(linhas_manuais),
                'total_auto': len(linhas_auto),
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes DFe {dfe_id}: {e}")
            raise

    def _buscar_lotes_faturamento_lf(self, odoo, numero_nf):
        """
        Busca lotes do faturamento da LF no Odoo.

        A NF emitida pela LF (company_id=5) contem as move lines com lote
        no picking de saida. Buscamos via account.move (fatura de venda da LF)
        e depois stock.move.line (picking de saida associado).

        Args:
            odoo: Conexao Odoo ativa
            numero_nf: Numero da NF emitida pela LF

        Returns:
            Dict[product_id] -> {lote_nome, quantidade, data_validade}
        """
        try:
            # 1. Buscar account.move da LF pelo numero da NF
            invoices = odoo.execute_kw(
                'account.move', 'search_read',
                [[
                    ['company_id', '=', self.COMPANY_LF],
                    ['l10n_br_numero_nota_fiscal', '=', numero_nf],
                    ['move_type', 'in', ['out_invoice', 'out_refund']],
                ]],
                {
                    'fields': ['id', 'name', 'invoice_line_ids', 'stock_move_id'],
                    'limit': 5,
                }
            )

            if not invoices:
                logger.warning(f"Nenhuma fatura da LF encontrada para NF {numero_nf}")
                return {}

            # 2. Para cada invoice, buscar as move lines do picking de saida
            #    (stock.picking ligado ao sale.order da LF)
            lotes_por_produto = {}

            for invoice in invoices:
                # Buscar stock.picking associado (via origin da invoice ou sale_id)
                # Alternativa: buscar stock.move.line com reference ao invoice
                invoice_id = invoice['id']

                # Buscar delivery (stock.picking) via invoice -> sale.order -> picking
                # Ou buscar diretamente as move lines com lot_id
                pickings = odoo.execute_kw(
                    'stock.picking', 'search_read',
                    [[
                        ['company_id', '=', self.COMPANY_LF],
                        ['picking_type_code', '=', 'outgoing'],
                        ['state', '=', 'done'],
                        ['origin', 'ilike', numero_nf],
                    ]],
                    {
                        'fields': ['id', 'name', 'move_line_ids'],
                        'limit': 5,
                    }
                )

                if not pickings:
                    # Fallback: buscar pickings recentes (ultimos 30 dias)
                    # CORREÇÃO TIMEZONE: Odoo date_done é UTC → usar agora_utc()
                    data_limite = (agora_utc() - timedelta(days=30)).strftime('%Y-%m-%d')
                    pickings = odoo.execute_kw(
                        'stock.picking', 'search_read',
                        [[
                            ['company_id', '=', self.COMPANY_LF],
                            ['picking_type_code', '=', 'outgoing'],
                            ['state', '=', 'done'],
                            ['date_done', '>=', data_limite],
                        ]],
                        {
                            'fields': ['id', 'name', 'move_line_ids'],
                            'limit': 5,
                            'order': 'date_done desc',
                        }
                    )

                for picking in pickings:
                    if not picking.get('move_line_ids'):
                        continue

                    # Buscar move lines com lot_id
                    move_lines = odoo.execute_kw(
                        'stock.move.line', 'search_read',
                        [[
                            ['picking_id', '=', picking['id']],
                            ['lot_id', '!=', False],
                        ]],
                        {
                            'fields': ['id', 'product_id', 'lot_id', 'quantity',
                                       'lot_name'],
                        }
                    )

                    # Coletar move_lines com lot_id para batch
                    lot_ids_to_fetch = []
                    for ml in move_lines:
                        if ml.get('lot_id'):
                            lid = ml['lot_id'][0] if isinstance(ml['lot_id'], (list, tuple)) else ml['lot_id']
                            lot_ids_to_fetch.append(lid)

                    # Batch read de stock.lot
                    lots_data = {}
                    if lot_ids_to_fetch:
                        try:
                            lots = odoo.execute_kw(
                                'stock.lot', 'read',
                                [list(set(lot_ids_to_fetch))],
                                {'fields': ['id', 'name', 'expiration_date']}
                            )
                            lots_data = {l['id']: l for l in lots}
                        except Exception as e_lot:
                            logger.warning(f"Erro ao buscar lotes batch: {e_lot}")

                    for ml in move_lines:
                        pid = ml['product_id'][0] if ml.get('product_id') else None
                        if not pid:
                            continue

                        lot_name = ''
                        data_validade = None
                        if ml.get('lot_id'):
                            lot_id = ml['lot_id'][0] if isinstance(ml['lot_id'], (list, tuple)) else ml['lot_id']
                            lot_name = ml['lot_id'][1] if isinstance(ml['lot_id'], (list, tuple)) else ''

                            # Usar dados do batch
                            if lot_id in lots_data:
                                lot_name = lots_data[lot_id].get('name', lot_name)
                                data_validade = lots_data[lot_id].get('expiration_date')

                        if pid not in lotes_por_produto:
                            lotes_por_produto[pid] = {
                                'lote_nome': lot_name,
                                'quantidade': float(ml.get('quantity', 0)),
                                'data_validade': data_validade,
                            }
                        else:
                            existing = lotes_por_produto[pid]
                            existing['quantidade'] += float(ml.get('quantity', 0))

            return lotes_por_produto

        except Exception as e:
            logger.error(f"Erro ao buscar lotes do faturamento LF (NF {numero_nf}): {e}")
            return {}

    def salvar_recebimento(self, dados, usuario='sistema'):
        """
        Salva RecebimentoLf + lotes localmente e enfileira job RQ.

        Args:
            dados: Dict com:
                - dfe_id, numero_nf, chave_nfe, cnpj_emitente
                - lotes_manuais: [{product_id, product_name, dfe_line_id,
                                  cfop, lote_nome, quantidade, data_validade}]
                - lotes_auto: [{product_id, product_name, dfe_line_id,
                               cfop, lote_nome, quantidade, data_validade}]
            usuario: Nome do usuario

        Returns:
            RecebimentoLf salvo com job_id
        """
        try:
            # Verificar se DFe ja esta em processamento
            existente = RecebimentoLf.query.filter(
                RecebimentoLf.odoo_dfe_id == dados['dfe_id'],
                RecebimentoLf.status.in_(['pendente', 'processando'])
            ).first()

            if existente:
                raise ValueError(
                    f"DFe {dados['dfe_id']} ja possui recebimento em andamento "
                    f"(ID={existente.id}, status={existente.status})"
                )

            # Criar RecebimentoLf
            recebimento = RecebimentoLf(
                odoo_dfe_id=dados['dfe_id'],
                numero_nf=dados.get('numero_nf'),
                chave_nfe=dados.get('chave_nfe'),
                cnpj_emitente=dados.get('cnpj_emitente', self.CNPJ_LF),
                company_id=self.COMPANY_FB,
                status='pendente',
                usuario=usuario,
            )
            db.session.add(recebimento)
            db.session.flush()  # Obter ID

            # Salvar lotes manuais (CFOP!=1902)
            for lote_data in dados.get('lotes_manuais', []):
                lote = RecebimentoLfLote(
                    recebimento_lf_id=recebimento.id,
                    odoo_product_id=lote_data['product_id'],
                    odoo_product_name=lote_data.get('product_name', ''),
                    odoo_dfe_line_id=lote_data.get('dfe_line_id'),
                    cfop=lote_data.get('cfop', ''),
                    tipo='manual',
                    lote_nome=lote_data.get('lote_nome', ''),
                    quantidade=lote_data['quantidade'],
                    data_validade=self._parse_data(lote_data.get('data_validade')),
                    produto_tracking=lote_data.get('produto_tracking', 'lot'),
                )
                db.session.add(lote)

            # Salvar lotes auto (CFOP=1902)
            for lote_data in dados.get('lotes_auto', []):
                lote = RecebimentoLfLote(
                    recebimento_lf_id=recebimento.id,
                    odoo_product_id=lote_data['product_id'],
                    odoo_product_name=lote_data.get('product_name', ''),
                    odoo_dfe_line_id=lote_data.get('dfe_line_id'),
                    cfop=lote_data.get('cfop', '5902'),
                    tipo='auto',
                    lote_nome=lote_data.get('lote_nome', ''),
                    quantidade=lote_data['quantidade'],
                    data_validade=self._parse_data(lote_data.get('data_validade')),
                    produto_tracking=lote_data.get('produto_tracking', 'lot'),
                )
                db.session.add(lote)

            commit_with_retry(db.session)

            # Enfileirar job RQ (fire-and-forget) com retry automatico
            try:
                from app.recebimento.workers.recebimento_lf_jobs import processar_recebimento_lf_job
                from app.portal.workers import enqueue_job
                from rq import Retry

                retry_config = Retry(max=3, interval=[30, 120, 480])

                job = enqueue_job(
                    processar_recebimento_lf_job,
                    recebimento.id,
                    usuario,
                    queue_name='recebimento',
                    timeout='45m',
                    retry=retry_config,
                )
                recebimento.job_id = job.id
                commit_with_retry(db.session)
                logger.info(f"Job RQ enfileirado: {job.id} para recebimento LF {recebimento.id}")
            except Exception as e_job:
                logger.warning(
                    f"Nao foi possivel enfileirar job RQ: {e_job}. "
                    f"Recebimento LF {recebimento.id} fica 'pendente' para retry manual."
                )

            logger.info(
                f"Recebimento LF {recebimento.id} salvo para DFe {recebimento.odoo_dfe_id} "
                f"(NF {recebimento.numero_nf})"
            )

            return recebimento

        except ValueError:
            raise
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao salvar recebimento LF: {e}")
            raise

    def listar_recebimentos(self, status=None, limit=50):
        """
        Lista recebimentos LF com filtros.

        Args:
            status: Filtrar por status (pendente, processando, processado, erro)
            limit: Limite de resultados

        Returns:
            Lista de dicts serializados
        """
        try:
            query = RecebimentoLf.query

            if status:
                query = query.filter(RecebimentoLf.status == status)

            query = query.order_by(RecebimentoLf.criado_em.desc())
            query = query.limit(limit)

            recebimentos = query.all()
            return [r.to_dict() for r in recebimentos]

        except Exception as e:
            logger.error(f"Erro ao listar recebimentos LF: {e}")
            raise

    def retry_recebimento(self, recebimento_id):
        """
        Retry de recebimento LF com erro.

        Args:
            recebimento_id: ID do RecebimentoLf

        Returns:
            RecebimentoLf re-enfileirado
        """
        try:
            recebimento = RecebimentoLf.query.get(recebimento_id)
            if not recebimento:
                raise ValueError(f"Recebimento LF {recebimento_id} nao encontrado")

            if recebimento.status != 'erro':
                raise ValueError(
                    f"Recebimento LF {recebimento_id} nao esta com erro "
                    f"(status={recebimento.status})"
                )

            if recebimento.tentativas >= recebimento.max_tentativas:
                raise ValueError(
                    f"Recebimento LF {recebimento_id} atingiu maximo de tentativas "
                    f"({recebimento.max_tentativas})"
                )

            # Re-enfileirar
            recebimento.status = 'pendente'
            recebimento.erro_mensagem = None
            commit_with_retry(db.session)

            from app.recebimento.workers.recebimento_lf_jobs import processar_recebimento_lf_job
            from app.portal.workers import enqueue_job
            from rq import Retry

            retry_config = Retry(max=3, interval=[30, 120, 480])

            job = enqueue_job(
                processar_recebimento_lf_job,
                recebimento.id,
                recebimento.usuario,
                queue_name='recebimento',
                timeout='45m',
                retry=retry_config,
            )
            recebimento.job_id = job.id
            commit_with_retry(db.session)

            logger.info(f"Retry: Job RQ {job.id} para recebimento LF {recebimento.id}")
            return recebimento

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Erro ao retry recebimento LF {recebimento_id}: {e}")
            raise

    def retry_transfer(self, recebimento_id):
        """
        Retry apenas da fase de transferencia FB -> CD (etapas 19-26).

        Requisitos:
        - Recebimento deve estar com status='processado' (FB OK)
        - transfer_status deve ser 'erro'

        Args:
            recebimento_id: ID do RecebimentoLf

        Returns:
            RecebimentoLf re-enfileirado
        """
        try:
            recebimento = RecebimentoLf.query.get(recebimento_id)
            if not recebimento:
                raise ValueError(f"Recebimento LF {recebimento_id} nao encontrado")

            if recebimento.status != 'processado':
                raise ValueError(
                    f"Recebimento LF {recebimento_id} nao esta processado "
                    f"(status={recebimento.status}). "
                    "Retry transfer so e possivel apos FB concluir."
                )

            if recebimento.transfer_status not in ('erro', None, 'pendente'):
                raise ValueError(
                    f"Transfer status atual: {recebimento.transfer_status}. "
                    "Retry so e possivel quando transfer_status='erro'."
                )

            # Reset transfer
            recebimento.transfer_status = 'pendente'
            recebimento.transfer_erro_mensagem = None
            # Reset etapa para 18 (antes da fase 6)
            if recebimento.etapa_atual >= 19:
                recebimento.etapa_atual = 18
            commit_with_retry(db.session)

            from app.recebimento.workers.recebimento_lf_jobs import processar_transfer_fb_cd_job
            from app.portal.workers import enqueue_job
            from rq import Retry

            retry_config = Retry(max=2, interval=[30, 120])

            job = enqueue_job(
                processar_transfer_fb_cd_job,
                recebimento.id,
                queue_name='recebimento',
                timeout='45m',
                retry=retry_config,
            )
            recebimento.job_id = job.id
            commit_with_retry(db.session)

            logger.info(
                f"Retry transfer: Job RQ {job.id} para recebimento LF {recebimento.id}"
            )
            return recebimento

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Erro ao retry transfer {recebimento_id}: {e}")
            raise

    def _parse_data(self, data_str):
        """
        Parse de data no formato DD/MM/YYYY ou YYYY-MM-DD para date.

        Args:
            data_str: String de data ou None

        Returns:
            date ou None
        """
        if not data_str:
            return None

        from datetime import date

        if isinstance(data_str, date):
            return data_str

        for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
            try:
                return datetime.strptime(str(data_str), fmt).date()
            except ValueError:
                continue

        logger.warning(f"Formato de data nao reconhecido: {data_str}")
        return None
