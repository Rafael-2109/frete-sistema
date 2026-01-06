"""
Servico de sincronizacao de movimentacoes de pallet com Odoo

Este servico importa:
1. NFs de remessa de pallet (l10n_br_tipo_pedido = 'vasilhame') -> tipo_movimentacao = 'REMESSA'
2. NFs de venda de pallet (cod_produto = '208000012') -> tipo_movimentacao = 'SAIDA'
3. NFs de retorno/entrada de pallet -> tipo_movimentacao = 'ENTRADA'
"""
import logging
from datetime import datetime, date, timedelta
from app import db
from app.estoque.models import MovimentacaoEstoque

logger = logging.getLogger(__name__)

# Constantes
COD_PRODUTO_PALLET = '208000012'
NOME_PRODUTO_PALLET = 'PALLET'
# Prazo de cobranca agora e calculado dinamicamente em app/pallet/utils.py
# SP/RED = 7 dias, outros = 30 dias


class PalletSyncService:
    """Servico para sincronizar movimentacoes de pallet do Odoo"""

    def __init__(self, odoo_client=None):
        """
        Inicializa o servico com cliente Odoo

        Args:
            odoo_client: Cliente XML-RPC do Odoo configurado (opcional)
                         Se nao informado, cria conexao automaticamente
        """
        if odoo_client:
            self.odoo = odoo_client
        else:
            from app.odoo.utils.connection import get_odoo_connection
            self.odoo = get_odoo_connection()

    def sincronizar_remessas(self, dias_retroativos=30):
        """
        Importa NFs de remessa de pallet (l10n_br_tipo_pedido = 'vasilhame')

        Args:
            dias_retroativos: Quantos dias para tras buscar

        Returns:
            dict: Resumo da sincronizacao
        """
        logger.info(f"🔄 Iniciando sincronizacao de remessas de pallet (ultimos {dias_retroativos} dias)")

        data_corte = (datetime.now() - timedelta(days=dias_retroativos)).strftime('%Y-%m-%d')

        resumo = {
            'processados': 0,
            'novos': 0,
            'ja_existentes': 0,
            'erros': 0,
            'detalhes': []
        }

        try:
            # Buscar NFs de vasilhame no Odoo
            domain = [
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted'),
                ('l10n_br_tipo_pedido', '=', 'vasilhame'),
                ('invoice_date', '>=', data_corte)
            ]

            campos = [
                'id', 'name', 'invoice_date', 'partner_id',
                'l10n_br_numero_nota_fiscal', 'l10n_br_tipo_pedido',
                'amount_total', 'invoice_line_ids'
            ]

            nfs = self.odoo.search_read('account.move', domain, campos)
            logger.info(f"   📦 Encontradas {len(nfs)} NFs de vasilhame")

            for nf in nfs:
                try:
                    resumo['processados'] += 1
                    numero_nf = str(nf.get('l10n_br_numero_nota_fiscal', ''))

                    if not numero_nf:
                        logger.warning(f"   ⚠️ NF sem numero: {nf.get('name')}")
                        continue

                    # Verificar se ja existe
                    existente = MovimentacaoEstoque.query.filter(
                        MovimentacaoEstoque.numero_nf == numero_nf,
                        MovimentacaoEstoque.local_movimentacao == 'PALLET',
                        MovimentacaoEstoque.tipo_movimentacao == 'REMESSA',
                        MovimentacaoEstoque.ativo == True
                    ).first()

                    if existente:
                        resumo['ja_existentes'] += 1
                        continue

                    # Buscar linhas da NF para obter quantidade
                    linha_ids = nf.get('invoice_line_ids', [])
                    quantidade_total = 0

                    if linha_ids:
                        linhas = self.odoo.search_read(
                            'account.move.line',
                            [('id', 'in', linha_ids), ('product_id', '!=', False)],
                            ['quantity', 'product_id']
                        )
                        for linha in linhas:
                            quantidade_total += linha.get('quantity', 0)

                    if quantidade_total == 0:
                        quantidade_total = 1  # Fallback

                    # Dados do parceiro (destinatario)
                    partner = nf.get('partner_id', [])
                    partner_id = partner[0] if isinstance(partner, (list, tuple)) else partner
                    partner_nome = partner[1] if isinstance(partner, (list, tuple)) and len(partner) > 1 else ''

                    # Buscar CNPJ do parceiro
                    cnpj_destinatario = ''
                    tipo_destinatario = 'CLIENTE'

                    if partner_id:
                        partner_data = self.odoo.search_read(
                            'res.partner',
                            [('id', '=', partner_id)],
                            ['l10n_br_cnpj', 'name', 'company_type']
                        )
                        if partner_data:
                            cnpj_destinatario = partner_data[0].get('l10n_br_cnpj', '') or ''
                            # Remover formatacao do CNPJ
                            cnpj_destinatario = cnpj_destinatario.replace('.', '').replace('-', '').replace('/', '')

                    # Determinar tipo de destinatario (TRANSPORTADORA ou CLIENTE)
                    # Prioridade: Transportadora > ContatoAgendamento
                    # Match por raiz do CNPJ (8 primeiros digitos)
                    from app.pallet.utils import buscar_tipo_destinatario
                    tipo_destinatario, _, _ = buscar_tipo_destinatario(cnpj_destinatario)

                    # Data da NF
                    data_nf = nf.get('invoice_date')
                    if isinstance(data_nf, str):
                        data_nf = datetime.strptime(data_nf, '%Y-%m-%d').date()
                    elif not data_nf:
                        data_nf = date.today()

                    # Criar movimentacao
                    movimento = MovimentacaoEstoque(
                        cod_produto=COD_PRODUTO_PALLET,
                        nome_produto=NOME_PRODUTO_PALLET,
                        data_movimentacao=data_nf,
                        tipo_movimentacao='REMESSA',  # Tipo especifico para remessa de pallet
                        local_movimentacao='PALLET',
                        qtd_movimentacao=int(quantidade_total),
                        numero_nf=numero_nf,
                        tipo_origem='ODOO',
                        status_nf='FATURADO',
                        tipo_destinatario=tipo_destinatario,
                        cnpj_destinatario=cnpj_destinatario,
                        nome_destinatario=partner_nome,
                        baixado=False,
                        observacao=f'Remessa de pallet - NF {numero_nf}',
                        criado_por='SYNC_ODOO'
                    )

                    db.session.add(movimento)
                    db.session.commit()

                    resumo['novos'] += 1
                    resumo['detalhes'].append({
                        'nf': numero_nf,
                        'destinatario': partner_nome,
                        'quantidade': int(quantidade_total),
                        'tipo': tipo_destinatario
                    })

                    logger.info(f"   ✅ NF {numero_nf}: {int(quantidade_total)} pallets -> {partner_nome}")

                except Exception as e:
                    resumo['erros'] += 1
                    logger.error(f"   ❌ Erro ao processar NF: {e}")
                    db.session.rollback()
                    continue

            logger.info(f"✅ Sincronizacao concluida: {resumo['novos']} novos, {resumo['ja_existentes']} existentes, {resumo['erros']} erros")

        except Exception as e:
            logger.error(f"❌ Erro na sincronizacao de remessas: {e}")
            resumo['erro_geral'] = str(e)

        return resumo

    def sincronizar_vendas_pallet(self, dias_retroativos=30):
        """
        Importa NFs de venda de pallet (cod_produto = '208000012')

        Args:
            dias_retroativos: Quantos dias para tras buscar

        Returns:
            dict: Resumo da sincronizacao
        """
        logger.info(f"🔄 Iniciando sincronizacao de vendas de pallet (ultimos {dias_retroativos} dias)")

        data_corte = (datetime.now() - timedelta(days=dias_retroativos)).strftime('%Y-%m-%d')

        resumo = {
            'processados': 0,
            'novos': 0,
            'ja_existentes': 0,
            'erros': 0,
            'detalhes': []
        }

        try:
            # Buscar produto PALLET no Odoo
            produtos = self.odoo.search_read(
                'product.product',
                [('default_code', '=', COD_PRODUTO_PALLET)],
                ['id', 'name']
            )

            if not produtos:
                logger.warning(f"   ⚠️ Produto {COD_PRODUTO_PALLET} nao encontrado no Odoo")
                return resumo

            produto_id = produtos[0]['id']
            logger.info(f"   📦 Produto PALLET encontrado: ID {produto_id}")

            # Buscar linhas de NF com esse produto
            domain = [
                ('product_id', '=', produto_id),
                ('move_id.move_type', 'in', ['out_invoice']),
                ('move_id.state', '=', 'posted'),
                ('move_id.invoice_date', '>=', data_corte)
            ]

            campos = [
                'id', 'move_id', 'product_id', 'quantity', 'price_total', 'partner_id'
            ]

            linhas = self.odoo.search_read('account.move.line', domain, campos)
            logger.info(f"   📦 Encontradas {len(linhas)} linhas de venda de pallet")

            for linha in linhas:
                try:
                    resumo['processados'] += 1

                    # Dados da NF pai
                    move_data = linha.get('move_id', [])
                    move_id = move_data[0] if isinstance(move_data, (list, tuple)) else move_data

                    # Buscar numero da NF
                    nf_data = self.odoo.search_read(
                        'account.move',
                        [('id', '=', move_id)],
                        ['l10n_br_numero_nota_fiscal', 'invoice_date', 'partner_id']
                    )

                    if not nf_data:
                        continue

                    numero_nf = str(nf_data[0].get('l10n_br_numero_nota_fiscal', ''))
                    if not numero_nf:
                        continue

                    # Verificar se ja existe
                    existente = MovimentacaoEstoque.query.filter(
                        MovimentacaoEstoque.numero_nf == numero_nf,
                        MovimentacaoEstoque.local_movimentacao == 'PALLET',
                        MovimentacaoEstoque.tipo_movimentacao == 'SAIDA',
                        MovimentacaoEstoque.ativo == True
                    ).first()

                    if existente:
                        resumo['ja_existentes'] += 1
                        continue

                    # Dados do parceiro
                    partner = nf_data[0].get('partner_id', [])
                    partner_id = partner[0] if isinstance(partner, (list, tuple)) else partner
                    partner_nome = partner[1] if isinstance(partner, (list, tuple)) and len(partner) > 1 else ''

                    # Buscar CNPJ
                    cnpj = ''
                    if partner_id:
                        partner_data = self.odoo.search_read(
                            'res.partner',
                            [('id', '=', partner_id)],
                            ['l10n_br_cnpj']
                        )
                        if partner_data:
                            cnpj = partner_data[0].get('l10n_br_cnpj', '') or ''
                            cnpj = cnpj.replace('.', '').replace('-', '').replace('/', '')

                    # Data da NF
                    data_nf = nf_data[0].get('invoice_date')
                    if isinstance(data_nf, str):
                        data_nf = datetime.strptime(data_nf, '%Y-%m-%d').date()
                    elif not data_nf:
                        data_nf = date.today()

                    quantidade = int(linha.get('quantity', 0))
                    valor = float(linha.get('price_total', 0))

                    # Criar movimentacao de SAIDA (venda)
                    movimento = MovimentacaoEstoque(
                        cod_produto=COD_PRODUTO_PALLET,
                        nome_produto=NOME_PRODUTO_PALLET,
                        data_movimentacao=data_nf,
                        tipo_movimentacao='SAIDA',  # Venda de pallet
                        local_movimentacao='PALLET',
                        qtd_movimentacao=quantidade,
                        numero_nf=numero_nf,
                        tipo_origem='ODOO',
                        status_nf='FATURADO',
                        tipo_destinatario='CLIENTE',
                        cnpj_destinatario=cnpj,
                        nome_destinatario=partner_nome,
                        baixado=False,  # Precisa vincular manualmente a uma remessa
                        observacao=f'Venda de pallet - NF {numero_nf} - R$ {valor:.2f}',
                        criado_por='SYNC_ODOO'
                    )

                    db.session.add(movimento)
                    db.session.commit()

                    resumo['novos'] += 1
                    resumo['detalhes'].append({
                        'nf': numero_nf,
                        'comprador': partner_nome,
                        'quantidade': quantidade,
                        'valor': valor
                    })

                    logger.info(f"   ✅ Venda NF {numero_nf}: {quantidade} pallets -> {partner_nome} (R$ {valor:.2f})")

                except Exception as e:
                    resumo['erros'] += 1
                    logger.error(f"   ❌ Erro ao processar linha: {e}")
                    db.session.rollback()
                    continue

            logger.info(f"✅ Sincronizacao de vendas concluida: {resumo['novos']} novos, {resumo['ja_existentes']} existentes")

        except Exception as e:
            logger.error(f"❌ Erro na sincronizacao de vendas: {e}")
            resumo['erro_geral'] = str(e)

        return resumo

    def sincronizar_devolucoes(self, dias_retroativos=30):
        """
        Importa NFs de devolucao de pallet (NFs de entrada que referenciam remessas de pallet)

        Devolucoes ocorrem quando:
        - Cliente emite NF de devolucao referenciando NF de remessa
        - NF de entrada do tipo refund que referencia NF de vasilhame

        Args:
            dias_retroativos: Quantos dias para tras buscar

        Returns:
            dict: Resumo da sincronizacao
        """
        logger.info(f"🔄 Iniciando sincronizacao de devolucoes de pallet (ultimos {dias_retroativos} dias)")

        data_corte = (datetime.now() - timedelta(days=dias_retroativos)).strftime('%Y-%m-%d')

        resumo = {
            'processados': 0,
            'novos': 0,
            'ja_existentes': 0,
            'baixas_realizadas': 0,
            'erros': 0,
            'detalhes': []
        }

        try:
            # Buscar NFs de devolucao/reembolso (entrada) no Odoo
            # Devolucoes de cliente sao out_refund (NF de saida negativa)
            domain = [
                ('move_type', '=', 'out_refund'),
                ('state', '=', 'posted'),
                ('l10n_br_tipo_pedido', '=', 'vasilhame'),
                ('invoice_date', '>=', data_corte)
            ]

            campos = [
                'id', 'name', 'invoice_date', 'partner_id',
                'l10n_br_numero_nota_fiscal', 'l10n_br_tipo_pedido',
                'amount_total', 'invoice_line_ids', 'reversed_entry_id'
            ]

            nfs = self.odoo.search_read('account.move', domain, campos)
            logger.info(f"   📦 Encontradas {len(nfs)} NFs de devolucao de vasilhame")

            for nf in nfs:
                try:
                    resumo['processados'] += 1
                    numero_nf = str(nf.get('l10n_br_numero_nota_fiscal', ''))

                    if not numero_nf:
                        logger.warning(f"   ⚠️ NF de devolucao sem numero: {nf.get('name')}")
                        continue

                    # Verificar se ja existe como DEVOLUCAO
                    existente = MovimentacaoEstoque.query.filter(
                        MovimentacaoEstoque.numero_nf == numero_nf,
                        MovimentacaoEstoque.local_movimentacao == 'PALLET',
                        MovimentacaoEstoque.tipo_movimentacao == 'DEVOLUCAO',
                        MovimentacaoEstoque.ativo == True
                    ).first()

                    if existente:
                        resumo['ja_existentes'] += 1
                        continue

                    # Buscar linhas da NF para obter quantidade
                    linha_ids = nf.get('invoice_line_ids', [])
                    quantidade_total = 0

                    if linha_ids:
                        linhas = self.odoo.search_read(
                            'account.move.line',
                            [('id', 'in', linha_ids), ('product_id', '!=', False)],
                            ['quantity', 'product_id']
                        )
                        for linha in linhas:
                            quantidade_total += abs(linha.get('quantity', 0))

                    if quantidade_total == 0:
                        quantidade_total = 1  # Fallback

                    # Dados do parceiro
                    partner = nf.get('partner_id', [])
                    partner_id = partner[0] if isinstance(partner, (list, tuple)) else partner
                    partner_nome = partner[1] if isinstance(partner, (list, tuple)) and len(partner) > 1 else ''

                    # Buscar CNPJ do parceiro
                    cnpj_destinatario = ''
                    if partner_id:
                        partner_data = self.odoo.search_read(
                            'res.partner',
                            [('id', '=', partner_id)],
                            ['l10n_br_cnpj', 'name']
                        )
                        if partner_data:
                            cnpj_destinatario = partner_data[0].get('l10n_br_cnpj', '') or ''
                            cnpj_destinatario = cnpj_destinatario.replace('.', '').replace('-', '').replace('/', '')

                    # Buscar NF de remessa original (se houver referencia)
                    nf_remessa_origem = None
                    reversed_entry = nf.get('reversed_entry_id', [])
                    if reversed_entry:
                        reversed_id = reversed_entry[0] if isinstance(reversed_entry, (list, tuple)) else reversed_entry
                        nf_original = self.odoo.search_read(
                            'account.move',
                            [('id', '=', reversed_id)],
                            ['l10n_br_numero_nota_fiscal']
                        )
                        if nf_original:
                            nf_remessa_origem = str(nf_original[0].get('l10n_br_numero_nota_fiscal', ''))

                    # Data da NF
                    data_nf = nf.get('invoice_date')
                    if isinstance(data_nf, str):
                        data_nf = datetime.strptime(data_nf, '%Y-%m-%d').date()
                    elif not data_nf:
                        data_nf = date.today()

                    # Criar movimentacao de DEVOLUCAO
                    movimento = MovimentacaoEstoque(
                        cod_produto=COD_PRODUTO_PALLET,
                        nome_produto=NOME_PRODUTO_PALLET,
                        data_movimentacao=data_nf,
                        tipo_movimentacao='DEVOLUCAO',
                        local_movimentacao='PALLET',
                        qtd_movimentacao=int(quantidade_total),
                        numero_nf=numero_nf,
                        tipo_origem='ODOO',
                        status_nf='FATURADO',
                        tipo_destinatario='CLIENTE',
                        cnpj_destinatario=cnpj_destinatario,
                        nome_destinatario=partner_nome,
                        nf_remessa_origem=nf_remessa_origem,
                        baixado=True,  # Devolucao ja esta baixada por natureza
                        observacao=f'Devolucao de pallet - NF {numero_nf}' + (f' (ref: {nf_remessa_origem})' if nf_remessa_origem else ''),
                        criado_por='SYNC_ODOO'
                    )

                    db.session.add(movimento)

                    # Tentar baixar a remessa original se encontrada
                    if nf_remessa_origem:
                        remessa = MovimentacaoEstoque.query.filter(
                            MovimentacaoEstoque.numero_nf == nf_remessa_origem,
                            MovimentacaoEstoque.tipo_movimentacao == 'REMESSA',
                            MovimentacaoEstoque.local_movimentacao == 'PALLET',
                            MovimentacaoEstoque.baixado == False,
                            MovimentacaoEstoque.ativo == True
                        ).first()
                        if remessa:
                            remessa.baixado = True
                            remessa.baixado_em = datetime.utcnow()
                            remessa.baixado_por = 'SYNC_ODOO'
                            remessa.movimento_baixado_id = movimento.id
                            remessa.observacao = (remessa.observacao or '') + f'\n[BAIXA] Devolucao NF {numero_nf}'
                            resumo['baixas_realizadas'] += 1

                    db.session.commit()

                    resumo['novos'] += 1
                    resumo['detalhes'].append({
                        'nf': numero_nf,
                        'origem': partner_nome,
                        'quantidade': int(quantidade_total),
                        'nf_remessa_origem': nf_remessa_origem
                    })

                    logger.info(f"   ✅ Devolucao NF {numero_nf}: {int(quantidade_total)} pallets <- {partner_nome}")

                except Exception as e:
                    resumo['erros'] += 1
                    logger.error(f"   ❌ Erro ao processar devolucao: {e}")
                    db.session.rollback()
                    continue

            logger.info(f"✅ Sincronizacao de devolucoes concluida: {resumo['novos']} novas, {resumo['baixas_realizadas']} baixas")

        except Exception as e:
            logger.error(f"❌ Erro na sincronizacao de devolucoes: {e}")
            resumo['erro_geral'] = str(e)

        return resumo

    def sincronizar_recusas(self, dias_retroativos=30):
        """
        Importa NFs de remessa de pallet que foram recusadas/canceladas

        Recusas ocorrem quando:
        - NF foi emitida mas cliente recusou (evento SEFAZ)
        - NF foi cancelada dentro do prazo de 24h

        Args:
            dias_retroativos: Quantos dias para tras buscar

        Returns:
            dict: Resumo da sincronizacao
        """
        logger.info(f"🔄 Iniciando sincronizacao de recusas de pallet (ultimos {dias_retroativos} dias)")

        data_corte = (datetime.now() - timedelta(days=dias_retroativos)).strftime('%Y-%m-%d')

        resumo = {
            'processados': 0,
            'novos': 0,
            'ja_atualizados': 0,
            'baixas_realizadas': 0,
            'erros': 0,
            'detalhes': []
        }

        try:
            # Buscar NFs de vasilhame canceladas no Odoo
            domain = [
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'cancel'),
                ('l10n_br_tipo_pedido', '=', 'vasilhame'),
                ('invoice_date', '>=', data_corte)
            ]

            campos = [
                'id', 'name', 'invoice_date', 'partner_id',
                'l10n_br_numero_nota_fiscal', 'l10n_br_tipo_pedido',
                'invoice_line_ids'
            ]

            nfs = self.odoo.search_read('account.move', domain, campos)
            logger.info(f"   📦 Encontradas {len(nfs)} NFs de vasilhame canceladas")

            for nf in nfs:
                try:
                    resumo['processados'] += 1
                    numero_nf = str(nf.get('l10n_br_numero_nota_fiscal', ''))

                    if not numero_nf:
                        continue

                    # Verificar se existe como REMESSA e atualizar status
                    remessa = MovimentacaoEstoque.query.filter(
                        MovimentacaoEstoque.numero_nf == numero_nf,
                        MovimentacaoEstoque.local_movimentacao == 'PALLET',
                        MovimentacaoEstoque.tipo_movimentacao == 'REMESSA',
                        MovimentacaoEstoque.ativo == True
                    ).first()

                    if remessa:
                        if remessa.status_nf == 'CANCELADO' and remessa.baixado:
                            resumo['ja_atualizados'] += 1
                            continue

                        # Atualizar status para CANCELADO e baixar
                        remessa.status_nf = 'CANCELADO'
                        remessa.baixado = True
                        remessa.baixado_em = datetime.utcnow()
                        remessa.baixado_por = 'SYNC_ODOO'
                        remessa.observacao = (remessa.observacao or '') + '\n[CANCELAMENTO] NF cancelada no Odoo'

                        db.session.commit()

                        resumo['novos'] += 1
                        resumo['baixas_realizadas'] += 1
                        resumo['detalhes'].append({
                            'nf': numero_nf,
                            'acao': 'CANCELAMENTO',
                            'quantidade': int(remessa.qtd_movimentacao)
                        })

                        logger.info(f"   ✅ NF {numero_nf} marcada como CANCELADA e baixada")
                    else:
                        # NF cancelada nao existe no sistema - criar registro de RECUSA
                        # para manter historico
                        existente = MovimentacaoEstoque.query.filter(
                            MovimentacaoEstoque.numero_nf == numero_nf,
                            MovimentacaoEstoque.local_movimentacao == 'PALLET',
                            MovimentacaoEstoque.tipo_movimentacao == 'RECUSA',
                            MovimentacaoEstoque.ativo == True
                        ).first()

                        if existente:
                            resumo['ja_atualizados'] += 1
                            continue

                        # Buscar quantidade das linhas
                        linha_ids = nf.get('invoice_line_ids', [])
                        quantidade_total = 0
                        if linha_ids:
                            linhas = self.odoo.search_read(
                                'account.move.line',
                                [('id', 'in', linha_ids), ('product_id', '!=', False)],
                                ['quantity']
                            )
                            for linha in linhas:
                                quantidade_total += linha.get('quantity', 0)
                        if quantidade_total == 0:
                            quantidade_total = 1

                        # Dados do parceiro
                        partner = nf.get('partner_id', [])
                        partner_nome = partner[1] if isinstance(partner, (list, tuple)) and len(partner) > 1 else ''

                        # Data da NF
                        data_nf = nf.get('invoice_date')
                        if isinstance(data_nf, str):
                            data_nf = datetime.strptime(data_nf, '%Y-%m-%d').date()
                        elif not data_nf:
                            data_nf = date.today()

                        # Criar registro de RECUSA (para historico)
                        movimento = MovimentacaoEstoque(
                            cod_produto=COD_PRODUTO_PALLET,
                            nome_produto=NOME_PRODUTO_PALLET,
                            data_movimentacao=data_nf,
                            tipo_movimentacao='RECUSA',
                            local_movimentacao='PALLET',
                            qtd_movimentacao=int(quantidade_total),
                            numero_nf=numero_nf,
                            tipo_origem='ODOO',
                            status_nf='CANCELADO',
                            nome_destinatario=partner_nome,
                            baixado=True,  # Recusa ja esta baixada por natureza
                            observacao=f'NF de pallet recusada/cancelada - {numero_nf}',
                            criado_por='SYNC_ODOO'
                        )

                        db.session.add(movimento)
                        db.session.commit()

                        resumo['novos'] += 1
                        resumo['detalhes'].append({
                            'nf': numero_nf,
                            'acao': 'RECUSA_REGISTRADA',
                            'quantidade': int(quantidade_total)
                        })

                        logger.info(f"   ✅ Recusa NF {numero_nf} registrada")

                except Exception as e:
                    resumo['erros'] += 1
                    logger.error(f"   ❌ Erro ao processar recusa: {e}")
                    db.session.rollback()
                    continue

            logger.info(f"✅ Sincronizacao de recusas concluida: {resumo['novos']} novos, {resumo['baixas_realizadas']} baixas")

        except Exception as e:
            logger.error(f"❌ Erro na sincronizacao de recusas: {e}")
            resumo['erro_geral'] = str(e)

        return resumo

    def sincronizar_tudo(self, dias_retroativos=30):
        """
        Sincroniza remessas, vendas, devolucoes e recusas de pallet

        Args:
            dias_retroativos: Quantos dias para tras buscar

        Returns:
            dict: Resumo consolidado
        """
        logger.info("=" * 60)
        logger.info("🚀 INICIANDO SINCRONIZACAO COMPLETA DE PALLET")
        logger.info("=" * 60)

        resumo_remessas = self.sincronizar_remessas(dias_retroativos)
        resumo_vendas = self.sincronizar_vendas_pallet(dias_retroativos)
        resumo_devolucoes = self.sincronizar_devolucoes(dias_retroativos)
        resumo_recusas = self.sincronizar_recusas(dias_retroativos)

        return {
            'remessas': resumo_remessas,
            'vendas': resumo_vendas,
            'devolucoes': resumo_devolucoes,
            'recusas': resumo_recusas,
            'total_novos': (
                resumo_remessas.get('novos', 0) +
                resumo_vendas.get('novos', 0) +
                resumo_devolucoes.get('novos', 0) +
                resumo_recusas.get('novos', 0)
            ),
            'total_baixas': (
                resumo_devolucoes.get('baixas_realizadas', 0) +
                resumo_recusas.get('baixas_realizadas', 0)
            )
        }
