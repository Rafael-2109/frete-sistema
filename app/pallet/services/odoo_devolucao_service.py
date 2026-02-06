"""
Servico de Vinculacao de Devolucao de Pallet no Odoo
=====================================================

Gerencia o fluxo completo de vinculacao de devolucoes de pallet no Odoo:
1. Criar Purchase Order (PO) para o DFe de devolucao
2. Vincular DFe <-> PO bidirecional
3. Confirmar PO (gera picking de recebimento automaticamente)
4. Redistribuir moves do picking para vincular 1:1 as remessas originais
5. Validar picking (recebimento fisico)
6. Popular campos customizados (x_studio_return_picking_ids)

Abordagem: Opcao B — 1 picking devolucao -> N moves, cada move 1:1 com remessa
via origin_returned_move_id.

Referencia de teste: scripts/pallet/teste_vinculacao_devolucao.py (validado com ATACADAO 183)

Autor: Sistema de Fretes
Data: 2026-02-06
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


# ==============================================================================
# CONSTANTES (de emissao_nf_pallet.py e IDS_FIXOS.md)
# ==============================================================================

PRODUTO_PALLET = {
    'product_id': 28108,
    'product_code': '208000012',
    'product_name': '[208000012] PALLET',
    'price_unit': 35.00,
    'product_uom': 1,  # Units
}

# Picking types de RECEBIMENTO (NAO de expedicao!)
# Mapa: company_id -> picking_type_id
PICKING_TYPES_RECEBIMENTO = {
    1: 1,    # FB -> Recebimento (FB)
    3: 8,    # SC -> Recebimento (SC)
    4: 13,   # CD -> Recebimento (CD)
    5: 16,   # LF -> Recebimento (LF)
}

# Fiscal positions de REMESSA VASILHAME
# Mapa: company_id -> fiscal_position_id
FISCAL_POSITIONS = {
    1: 17,   # FB
    3: 37,   # SC
    4: 46,   # CD
}

# Condicao de pagamento A VISTA
PAYMENT_TERM_ID = 2800

# Mapa: company_id -> sigla empresa
COMPANY_SIGLAS = {
    1: 'FB',
    3: 'SC',
    4: 'CD',
    5: 'LF',
}


class OdooDevolucaoService:
    """
    Service para vincular devolucoes de pallet no Odoo.

    Fluxo completo:
        DFe (finnfe=4) -> Criar PO -> Confirmar PO -> Picking gerado
        -> Redistribuir moves (1:1 com remessas) -> Validar picking
        -> Popular x_studio_return_picking_ids nas remessas

    Uso:
        service = OdooDevolucaoService()
        resultado = service.processar_devolucao_completa(
            dfe_id=12345,
            company_id=4,
            quantidade_total=416,
            vinculacoes=[
                {'odoo_picking_remessa_id': 100, 'quantidade': 26},
                {'odoo_picking_remessa_id': 101, 'quantidade': 28},
            ]
        )
    """

    def __init__(self, odoo_client=None):
        """
        Inicializa o service com cliente Odoo opcional.

        Args:
            odoo_client: Cliente XML-RPC do Odoo configurado (opcional).
                         Se nao informado, cria conexao automaticamente quando necessario.
        """
        self._odoo_client = odoo_client

    @property
    def odoo(self):
        """Lazy loading do cliente Odoo."""
        if self._odoo_client is None:
            from app.odoo.utils.connection import get_odoo_connection
            self._odoo_client = get_odoo_connection()
        return self._odoo_client

    # =========================================================================
    # METODO 1: CRIAR PO DE DEVOLUCAO
    # =========================================================================

    def criar_po_devolucao_pallet(
        self,
        dfe_id: int,
        company_id: int,
        quantidade_total: int
    ) -> Dict[str, Any]:
        """
        Cria Purchase Order para DFe de devolucao de pallet.

        Fluxo:
        1. Buscar dados do DFe (partner_id, data)
        2. Verificar se DFe ja tem PO vinculado
        3. Criar PO via create() com produto PALLET
        4. Vincular DFe <-> PO bidirecional
        5. Confirmar PO (button_confirm) -> gera picking
        6. Buscar picking gerado

        Args:
            dfe_id: ID do DFe no Odoo (l10n_br_ciel_it_account.dfe)
            company_id: ID da empresa que recebe (1=FB, 3=SC, 4=CD)
            quantidade_total: Quantidade total de pallets da devolucao

        Returns:
            Dict com po_id, po_name, picking_id, picking_name

        Raises:
            ValueError: Se company_id nao configurado ou DFe nao encontrado
            Exception: Se erro na criacao do PO ou confirmacao
        """
        sigla = COMPANY_SIGLAS.get(company_id, '?')
        logger.info(
            f"📦 Criando PO de devolucao de pallet: DFe={dfe_id}, "
            f"empresa={sigla} (company_id={company_id}), qty={quantidade_total}"
        )

        # Validar empresa
        picking_type_id = PICKING_TYPES_RECEBIMENTO.get(company_id)
        if not picking_type_id:
            raise ValueError(
                f"Company {company_id} nao configurada para recebimento de pallet. "
                f"Empresas validas: {list(PICKING_TYPES_RECEBIMENTO.keys())}"
            )

        fiscal_position_id = FISCAL_POSITIONS.get(company_id)

        # 1. Buscar dados do DFe
        dfe_data = self.odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            [['id', '=', dfe_id]],
            ['partner_id', 'nfe_infnfe_ide_dhemi', 'purchase_id',
             'nfe_infnfe_ide_nnf', 'nfe_infnfe_emit_cnpj']
        )

        if not dfe_data:
            raise ValueError(f"DFe {dfe_id} nao encontrado no Odoo")

        dfe = dfe_data[0]
        partner_id = dfe['partner_id'][0] if dfe.get('partner_id') else None
        data_emissao = dfe.get('nfe_infnfe_ide_dhemi', '')
        numero_nf = dfe.get('nfe_infnfe_ide_nnf', '')
        cnpj_emitente = dfe.get('nfe_infnfe_emit_cnpj', '')

        if not partner_id:
            raise ValueError(f"DFe {dfe_id} nao tem partner_id (emitente)")

        # 2. Verificar se DFe ja tem PO vinculado
        if dfe.get('purchase_id') and dfe['purchase_id']:
            existing_po_id = dfe['purchase_id'][0]
            logger.info(f"⚡ DFe {dfe_id} ja tem PO vinculado: {existing_po_id}")
            return self._buscar_po_e_picking_existente(existing_po_id)

        # 3. Criar PO
        logger.info(f"📝 Criando PO para partner_id={partner_id} ({cnpj_emitente})")

        # Data do pedido (usar data de emissao ou hoje)
        date_order = data_emissao[:10] if data_emissao and len(data_emissao) >= 10 else False

        po_vals = {
            'partner_id': partner_id,
            'company_id': company_id,
            'picking_type_id': picking_type_id,
            'payment_term_id': PAYMENT_TERM_ID,
            'origin': f'Devolucao Pallet NF {numero_nf} (DFe {dfe_id})',
            'order_line': [(0, 0, {
                'product_id': PRODUTO_PALLET['product_id'],
                'product_qty': float(quantidade_total),
                'price_unit': PRODUTO_PALLET['price_unit'],
                'product_uom': PRODUTO_PALLET['product_uom'],
                'name': f"[{PRODUTO_PALLET['product_code']}] PALLET - Devolucao NF {numero_nf}",
            })],
        }

        if fiscal_position_id:
            po_vals['fiscal_position_id'] = fiscal_position_id

        if date_order:
            po_vals['date_order'] = date_order

        po_id = self.odoo.create('purchase.order', po_vals)
        logger.info(f"✅ PO criado: id={po_id}")

        # Buscar nome do PO
        po_info = self.odoo.read('purchase.order', [po_id], ['name'])
        po_name = po_info[0]['name'] if po_info else f'PO-{po_id}'

        # 4. Vincular DFe <-> PO bidirecional
        logger.info(f"🔗 Vinculando DFe {dfe_id} <-> PO {po_id}")

        self.odoo.write('purchase.order', [po_id], {'dfe_id': dfe_id})
        self.odoo.write('l10n_br_ciel_it_account.dfe', [dfe_id], {
            'purchase_id': po_id,
            'purchase_fiscal_id': po_id,
        })

        # 5. Confirmar PO (button_confirm -> gera picking)
        logger.info(f"📋 Confirmando PO {po_name}...")

        self.odoo.execute_kw(
            'purchase.order',
            'button_confirm',
            [[po_id]],
            timeout_override=120  # PO confirmation pode demorar
        )
        logger.info(f"✅ PO {po_name} confirmado (state=purchase)")

        # 6. Buscar picking gerado
        picking_ids = self.odoo.search(
            'stock.picking',
            [['origin', 'ilike', po_name], ['company_id', '=', company_id]],
            limit=5
        )

        if not picking_ids:
            # Fallback: buscar via purchase_id nas PO lines -> moves
            logger.warning(f"⚠️ Picking nao encontrado por origin. Tentando via move_ids...")
            po_lines = self.odoo.search_read(
                'purchase.order.line',
                [['order_id', '=', po_id]],
                ['move_ids']
            )
            for line in po_lines:
                if line.get('move_ids'):
                    moves = self.odoo.read('stock.move', line['move_ids'][:1], ['picking_id'])
                    if moves and moves[0].get('picking_id'):
                        picking_ids = [moves[0]['picking_id'][0]]
                        break

        if not picking_ids:
            logger.error(f"❌ Nenhum picking encontrado para PO {po_name}")
            return {
                'sucesso': True,
                'po_id': po_id,
                'po_name': po_name,
                'picking_id': None,
                'picking_name': None,
                'aviso': 'PO criado mas picking nao encontrado automaticamente',
            }

        picking_id = picking_ids[0]
        picking_info = self.odoo.read('stock.picking', [picking_id], ['name', 'state'])
        picking_name = picking_info[0]['name'] if picking_info else f'PICK-{picking_id}'
        picking_state = picking_info[0].get('state', '?') if picking_info else '?'

        logger.info(f"✅ Picking encontrado: {picking_name} (id={picking_id}, state={picking_state})")

        return {
            'sucesso': True,
            'po_id': po_id,
            'po_name': po_name,
            'picking_id': picking_id,
            'picking_name': picking_name,
            'picking_state': picking_state,
        }

    def _buscar_po_e_picking_existente(self, po_id: int) -> Dict[str, Any]:
        """Busca PO e picking ja existentes."""
        po_info = self.odoo.read('purchase.order', [po_id], ['name', 'state'])
        po_name = po_info[0]['name'] if po_info else f'PO-{po_id}'

        # Buscar picking
        picking_ids = self.odoo.search(
            'stock.picking',
            [['origin', 'ilike', po_name]],
            limit=5
        )

        picking_id = None
        picking_name = None
        picking_state = None

        if picking_ids:
            picking_id = picking_ids[0]
            picking_info = self.odoo.read('stock.picking', [picking_id], ['name', 'state'])
            if picking_info:
                picking_name = picking_info[0]['name']
                picking_state = picking_info[0].get('state', '?')

        return {
            'sucesso': True,
            'po_id': po_id,
            'po_name': po_name,
            'picking_id': picking_id,
            'picking_name': picking_name,
            'picking_state': picking_state,
            'ja_existia': True,
        }

    # =========================================================================
    # METODO 2: VINCULAR MOVES AS REMESSAS
    # =========================================================================

    def vincular_moves_remessas(
        self,
        picking_devolucao_id: int,
        vinculacoes: List[Dict]
    ) -> Dict[str, Any]:
        """
        Redistribui moves do picking de devolucao para vincular 1:1 as remessas.

        Para cada remessa no breakdown:
        - Primeiro move: write no move existente (ajustar qty + origin_returned_move_id)
        - Demais moves: create novos moves com state='done'

        Referencia: scripts/pallet/teste_vinculacao_devolucao.py linhas 173-309

        Args:
            picking_devolucao_id: ID do picking de recebimento (gerado pelo PO)
            vinculacoes: Lista de dicts com:
                - odoo_picking_remessa_id: ID do picking de remessa (saida)
                - quantidade: Quantidade de pallets a vincular a essa remessa

        Returns:
            Dict com moves_criados, total_vinculado, erros
        """
        logger.info(
            f"🔗 Vinculando moves do picking {picking_devolucao_id} "
            f"a {len(vinculacoes)} remessas"
        )

        # 1. Buscar move(s) existente(s) do picking de devolucao
        moves_devolucao = self.odoo.search_read(
            'stock.move',
            [['picking_id', '=', picking_devolucao_id],
             ['product_id', '=', PRODUTO_PALLET['product_id']]],
            ['id', 'product_id', 'product_uom', 'name', 'state',
             'location_id', 'location_dest_id', 'company_id',
             'picking_id', 'picking_type_id', 'date', 'origin']
        )

        if not moves_devolucao:
            raise ValueError(
                f"Nenhum move de PALLET encontrado no picking {picking_devolucao_id}"
            )

        move_template = moves_devolucao[0]
        move_template_id = move_template['id']

        # 2. Buscar moves das remessas
        remessa_picking_ids = [v['odoo_picking_remessa_id'] for v in vinculacoes
                               if v.get('odoo_picking_remessa_id')]

        moves_remessas_raw = []
        if remessa_picking_ids:
            moves_remessas_raw = self.odoo.search_read(
                'stock.move',
                [['picking_id', 'in', remessa_picking_ids],
                 ['product_id', '=', PRODUTO_PALLET['product_id']]],
                ['id', 'picking_id']
            )

        # Mapear picking_id -> move_id da remessa
        moves_por_picking = {}
        for m in moves_remessas_raw:
            pid = m['picking_id'][0] if m.get('picking_id') else None
            if pid:
                moves_por_picking[pid] = m['id']

        # 3. Executar vinculacao
        moves_criados = []
        erros = []
        remessa_names_vinculadas = []

        for i, vinc in enumerate(vinculacoes):
            remessa_picking_id = vinc.get('odoo_picking_remessa_id')
            quantidade = vinc['quantidade']

            # Buscar move_id da remessa
            remessa_move_id = moves_por_picking.get(remessa_picking_id)

            if not remessa_move_id and remessa_picking_id:
                logger.warning(
                    f"⚠️ Move nao encontrado para remessa picking {remessa_picking_id}, "
                    f"pulando vinculacao Odoo"
                )
                erros.append({
                    'remessa_picking_id': remessa_picking_id,
                    'erro': 'Move nao encontrado na remessa',
                })
                continue

            try:
                if i == 0:
                    # Primeiro: write no move existente
                    write_vals = {
                        'product_uom_qty': float(quantidade),
                        'quantity': float(quantidade),
                    }

                    if remessa_move_id:
                        write_vals['origin_returned_move_id'] = remessa_move_id
                        write_vals['move_orig_ids'] = [(4, remessa_move_id)]

                    self.odoo.write('stock.move', [move_template_id], write_vals)
                    moves_criados.append(move_template_id)

                    logger.info(
                        f"  ✅ Move {move_template_id} atualizado: "
                        f"qty={quantidade}, remessa_move={remessa_move_id}"
                    )
                else:
                    # Demais: create novo move
                    new_move_vals = {
                        'name': move_template.get('name', 'PALLET'),
                        'product_id': move_template['product_id'][0],
                        'product_uom': move_template['product_uom'][0],
                        'product_uom_qty': float(quantidade),
                        'quantity': float(quantidade),
                        'location_id': move_template['location_id'][0],
                        'location_dest_id': move_template['location_dest_id'][0],
                        'picking_id': picking_devolucao_id,
                        'company_id': (
                            move_template['company_id'][0]
                            if move_template.get('company_id') else False
                        ),
                        'state': 'done',
                        'origin': move_template.get('origin', ''),
                        'date': move_template.get('date', False),
                    }

                    # picking_type_id pode ser False/[] em alguns moves
                    if move_template.get('picking_type_id'):
                        new_move_vals['picking_type_id'] = (
                            move_template['picking_type_id'][0]
                            if isinstance(move_template['picking_type_id'], list)
                            else move_template['picking_type_id']
                        )

                    if remessa_move_id:
                        new_move_vals['origin_returned_move_id'] = remessa_move_id
                        new_move_vals['move_orig_ids'] = [(4, remessa_move_id)]

                    new_id = self.odoo.create('stock.move', new_move_vals)
                    moves_criados.append(new_id)

                    logger.info(
                        f"  ✅ Move {new_id} criado: "
                        f"qty={quantidade}, remessa_move={remessa_move_id}"
                    )

                # Buscar nome do picking da remessa para log
                if remessa_picking_id:
                    remessa_names_vinculadas.append(str(remessa_picking_id))

            except Exception as e:
                logger.error(
                    f"  ❌ Erro vinculando remessa {remessa_picking_id}: {e}"
                )
                erros.append({
                    'remessa_picking_id': remessa_picking_id,
                    'erro': str(e),
                })
                continue

        # 4. Atualizar picking de devolucao
        if vinculacoes and vinculacoes[0].get('odoo_picking_remessa_id'):
            try:
                primeiro_remessa_id = vinculacoes[0]['odoo_picking_remessa_id']

                # Buscar nomes das remessas para o campo origin
                remessa_infos = self.odoo.read(
                    'stock.picking',
                    [v['odoo_picking_remessa_id'] for v in vinculacoes
                     if v.get('odoo_picking_remessa_id')][:10],
                    ['name']
                )
                remessa_names = [r['name'] for r in remessa_infos if r.get('name')]
                origin_text = (
                    f"Devolucao de {', '.join(remessa_names[:5])}"
                    f"{'...' if len(remessa_names) > 5 else ''}"
                )

                self.odoo.write('stock.picking', [picking_devolucao_id], {
                    'return_id': primeiro_remessa_id,
                    'is_return_picking': True,
                    'origin': origin_text,
                })
                logger.info(
                    f"  ✅ Picking {picking_devolucao_id} atualizado: "
                    f"return_id={primeiro_remessa_id}, is_return_picking=True"
                )
            except Exception as e:
                logger.warning(f"  ⚠️ Erro atualizando picking: {e}")
                erros.append({'picking_update': str(e)})

        # 5. Popular x_studio_return_picking_ids nas remessas
        self._popular_campo_customizado_remessas(
            picking_devolucao_id, vinculacoes
        )

        total_vinculado = sum(v['quantidade'] for v in vinculacoes)
        logger.info(
            f"📦 Vinculacao concluida: {len(moves_criados)} moves, "
            f"{total_vinculado} pallets, {len(erros)} erros"
        )

        return {
            'sucesso': len(erros) == 0,
            'moves_criados': moves_criados,
            'total_vinculado': total_vinculado,
            'erros': erros,
        }

    def _popular_campo_customizado_remessas(
        self,
        picking_devolucao_id: int,
        vinculacoes: List[Dict]
    ):
        """
        Popula x_studio_return_picking_ids (many2many, field_id=72862)
        em cada picking de remessa com o picking de devolucao.
        """
        for vinc in vinculacoes:
            remessa_picking_id = vinc.get('odoo_picking_remessa_id')
            if not remessa_picking_id:
                continue

            try:
                self.odoo.write(
                    'stock.picking',
                    [remessa_picking_id],
                    {
                        'x_studio_return_picking_ids': [(4, picking_devolucao_id)],
                    }
                )
                logger.debug(
                    f"  ✅ x_studio_return_picking_ids atualizado "
                    f"em remessa {remessa_picking_id}"
                )
            except Exception as e:
                logger.warning(
                    f"  ⚠️ Erro populando x_studio_return_picking_ids "
                    f"na remessa {remessa_picking_id}: {e}"
                )

    # =========================================================================
    # METODO 3: VALIDAR PICKING
    # =========================================================================

    def validar_picking(self, picking_id: int) -> Dict[str, Any]:
        """
        Executa o recebimento fisico do picking (button_validate).

        1. Verificar estado do picking
        2. Preencher qty_done nos move_lines
        3. Executar button_validate

        Args:
            picking_id: ID do stock.picking

        Returns:
            Dict com sucesso, state, aviso
        """
        logger.info(f"📋 Validando picking {picking_id}...")

        # Verificar estado atual
        picking = self.odoo.read('stock.picking', [picking_id], ['name', 'state'])
        if not picking:
            raise ValueError(f"Picking {picking_id} nao encontrado")

        state = picking[0].get('state', '')
        name = picking[0].get('name', '')

        if state == 'done':
            logger.info(f"  ⚡ Picking {name} ja esta done")
            return {'sucesso': True, 'state': 'done', 'aviso': 'Picking ja validado'}

        if state == 'cancel':
            raise ValueError(f"Picking {name} esta cancelado, nao pode ser validado")

        # Preencher qty_done nos move_lines
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['picking_id', '=', picking_id]],
            ['id', 'quantity', 'move_id']
        )

        # Para cada move_line, buscar qty esperada do move
        for ml in move_lines:
            move_id = ml['move_id'][0] if ml.get('move_id') else None
            if move_id:
                move_data = self.odoo.read('stock.move', [move_id], ['product_uom_qty'])
                if move_data:
                    qty = move_data[0].get('product_uom_qty', 0)
                    self.odoo.write('stock.move.line', [ml['id']], {
                        'quantity': qty,
                    })

        # Validar picking
        try:
            self.odoo.execute_kw(
                'stock.picking',
                'button_validate',
                [[picking_id]],
                timeout_override=120
            )
            logger.info(f"  ✅ Picking {name} validado com sucesso")
        except Exception as e:
            error_str = str(e)
            # "cannot marshal None" = operacao executou mas retornou None
            if 'cannot marshal None' not in error_str:
                raise

        # Verificar estado final
        picking_final = self.odoo.read('stock.picking', [picking_id], ['state'])
        state_final = picking_final[0].get('state', '?') if picking_final else '?'

        return {
            'sucesso': state_final == 'done',
            'state': state_final,
        }

    # =========================================================================
    # METODO 4: ORQUESTRADOR COMPLETO
    # =========================================================================

    def processar_devolucao_completa(
        self,
        dfe_id: int,
        company_id: int,
        quantidade_total: int,
        vinculacoes: List[Dict]
    ) -> Dict[str, Any]:
        """
        Orquestra o fluxo completo de vinculacao de devolucao no Odoo.

        Ordem:
        1. Criar PO -> Confirmar -> Picking gerado
        2. Redistribuir moves do picking (1:1 com remessas)
        3. Validar picking (recebimento fisico)

        Args:
            dfe_id: ID do DFe no Odoo
            company_id: ID da empresa (1=FB, 3=SC, 4=CD)
            quantidade_total: Quantidade total de pallets
            vinculacoes: Lista de dicts com:
                - odoo_picking_remessa_id: ID do picking de remessa
                - quantidade: Quantidade a vincular

        Returns:
            Dict completo com resultado de cada etapa
        """
        sigla = COMPANY_SIGLAS.get(company_id, '?')
        logger.info(
            f"🚀 Processando devolucao completa: DFe={dfe_id}, "
            f"empresa={sigla}, qty={quantidade_total}, "
            f"vinculacoes={len(vinculacoes)}"
        )

        resultado = {
            'sucesso': False,
            'etapa_1_po': None,
            'etapa_2_moves': None,
            'etapa_3_validacao': None,
        }

        # ETAPA 1: Criar PO + Picking
        try:
            po_result = self.criar_po_devolucao_pallet(
                dfe_id=dfe_id,
                company_id=company_id,
                quantidade_total=quantidade_total,
            )
            resultado['etapa_1_po'] = po_result

            if not po_result.get('picking_id'):
                logger.error("❌ Picking nao gerado apos criacao do PO")
                resultado['erro'] = 'Picking nao gerado pelo PO'
                return resultado

        except Exception as e:
            logger.error(f"❌ Erro na etapa 1 (PO): {e}")
            resultado['erro'] = f'Erro criando PO: {e}'
            return resultado

        picking_id = po_result['picking_id']

        # ETAPA 2: Vincular moves as remessas
        # So vincular se ha remessas com picking_id no Odoo
        vinculacoes_com_picking = [
            v for v in vinculacoes if v.get('odoo_picking_remessa_id')
        ]

        if vinculacoes_com_picking:
            try:
                moves_result = self.vincular_moves_remessas(
                    picking_devolucao_id=picking_id,
                    vinculacoes=vinculacoes_com_picking,
                )
                resultado['etapa_2_moves'] = moves_result
            except Exception as e:
                logger.error(f"❌ Erro na etapa 2 (moves): {e}")
                resultado['etapa_2_moves'] = {
                    'sucesso': False,
                    'erro': str(e),
                }
                # Continua para etapa 3 — PO ja existe
        else:
            logger.info("⚠️ Nenhuma remessa com picking_id — skip etapa 2")
            resultado['etapa_2_moves'] = {
                'sucesso': True,
                'aviso': 'Nenhuma remessa com odoo_picking_id para vincular',
            }

        # ETAPA 3: Validar picking
        try:
            validacao_result = self.validar_picking(picking_id)
            resultado['etapa_3_validacao'] = validacao_result
        except Exception as e:
            logger.error(f"❌ Erro na etapa 3 (validacao): {e}")
            resultado['etapa_3_validacao'] = {
                'sucesso': False,
                'erro': str(e),
            }

        # Resultado final
        resultado['sucesso'] = True  # PO foi criado com sucesso
        resultado['po_id'] = po_result.get('po_id')
        resultado['po_name'] = po_result.get('po_name')
        resultado['picking_id'] = picking_id
        resultado['picking_name'] = po_result.get('picking_name')

        logger.info(
            f"✅ Devolucao processada: PO={po_result.get('po_name')}, "
            f"Picking={po_result.get('picking_name')}"
        )

        return resultado
