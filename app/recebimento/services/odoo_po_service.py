"""
Service de Operacoes no Odoo para POs - FASE 2
==============================================

Executa operacoes de SPLIT e CONSOLIDACAO de POs no Odoo
apos validacao 100% match da NF x PO.

## REGRAS DE NEGÓCIO (Atualizado 16/01/2026)

### SPLIT (1 NF + 1 PO com match parcial)
- PO Original (500 un) + NF (400 un)
- Resultado:
  - PO Original: permanece com SALDO (100 un)
  - PO Conciliador (NOVO): criado com 400 un, vinculado à NF

### CONSOLIDAÇÃO (1 NF + N POs com match parcial)
- PO A (500 un produto X) + PO B (500 un produto Y) + NF (400 X + 400 Y)
- Resultado:
  - PO A: permanece com SALDO (100 un X)
  - PO B: permanece com SALDO (100 un Y)
  - PO Conciliador (NOVO): criado com 400 X + 400 Y, vinculado à NF

### REGRA GERAL
SEMPRE criar um PO Conciliador novo que casa 100% com a NF.
Os POs originais permanecem com o saldo restante.

Referencia: .claude/plans/humming-snuggling-brooks.md
"""

import logging
import json
from decimal import Decimal
from typing import Dict, List, Any, Optional
from datetime import datetime

from app import db
from app.recebimento.models import ValidacaoNfPoDfe, MatchNfPoItem, MatchAlocacao
from app.manufatura.models import PedidoCompras
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


def _marcar_dfes_afetados_por_pos(po_ids: list) -> int:
    """
    Marca DFEs que usam POs modificadas para revalidação.

    Chamado após operações que modificam POs (consolidação, ajuste de quantidade, etc.)
    para garantir que DFEs aprovados sejam revalidados na próxima execução do job.

    Args:
        po_ids: Lista de IDs de POs modificados no Odoo

    Returns:
        Número de DFEs marcados para revalidação
    """
    if not po_ids:
        return 0

    try:
        # Buscar alocações que usam essas POs
        alocacoes = MatchAlocacao.query.filter(
            MatchAlocacao.odoo_po_id.in_(po_ids)
        ).all()

        if not alocacoes:
            return 0

        # Agrupar por validação
        validacao_ids = set()
        for aloc in alocacoes:
            if aloc.match_item_id:
                match = MatchNfPoItem.query.get(aloc.match_item_id)
                if match and match.validacao_id:
                    validacao_ids.add(match.validacao_id)

        if not validacao_ids:
            return 0

        # Marcar validações aprovadas para revalidação
        dfes_marcados = 0
        for val_id in validacao_ids:
            validacao = ValidacaoNfPoDfe.query.get(val_id)
            if validacao and validacao.status == 'aprovado':
                if not validacao.po_modificada_apos_validacao:
                    validacao.po_modificada_apos_validacao = True
                    validacao.atualizado_em = datetime.utcnow()
                    dfes_marcados += 1
                    logger.info(
                        f"⚠️ DFE {validacao.odoo_dfe_id} (NF {validacao.numero_nf}) "
                        f"marcado para revalidação - PO modificada via consolidação"
                    )

        if dfes_marcados > 0:
            db.session.commit()

        return dfes_marcados

    except Exception as e:
        logger.error(f"Erro ao marcar DFEs afetados por POs: {e}")
        return 0


class OdooPoService:
    """
    Service para operacoes de PO no Odoo.
    Executa consolidacao e ajustes apos match 100%.
    """

    def simular_consolidacao(
        self,
        validacao_id: int
    ) -> Dict[str, Any]:
        """
        Simula a SPLIT/CONSOLIDACAO sem executar nada no Odoo.
        Retorna preview de todas as acoes que serao executadas.

        ## ATUALIZADO (19/01/2026) - Suporte a Multi-PO Split

        Agora processa MatchAlocacao ao inves de MatchNfPoItem direto.
        Um item da NF pode ter multiplas alocacoes em POs diferentes.

        Args:
            validacao_id: ID da validacao

        Returns:
            Dict com preview das acoes:
            - po_conciliador: Info do PO que sera criado
            - pos_saldo: POs que ficarao com saldo
            - acoes: Lista de acoes detalhadas
            - resumo: Totais
        """
        try:
            validacao = db.session.get(ValidacaoNfPoDfe, validacao_id) if validacao_id else None
            if not validacao:
                raise ValueError(f"Validacao {validacao_id} nao encontrada")

            # Buscar matches
            matches = db.session.query(MatchNfPoItem).filter_by(
                validacao_id=validacao_id,
                status_match='match'
            ).all()

            if not matches:
                return {
                    'sucesso': False,
                    'erro': 'Nenhum match encontrado',
                    'acoes': []
                }

            # Agrupar por PO Original - PROCESSANDO ALOCACOES
            pos_originais = {}
            itens_conciliador = []
            valor_total_conciliador = Decimal('0')

            for match in matches:
                # Buscar alocacoes do match (suporte a multi-PO split)
                alocacoes = db.session.query(MatchAlocacao).filter_by(
                    match_item_id=match.id
                ).order_by(MatchAlocacao.ordem).all()

                if alocacoes:
                    # NOVO: Processar cada alocacao (split multi-PO)
                    for aloc in alocacoes:
                        qtd_alocada = Decimal(str(aloc.qtd_alocada or 0))
                        preco = Decimal(str(aloc.preco_po or match.preco_nf or 0))

                        # Dados para o PO Conciliador
                        item_conciliador = {
                            'match_id': match.id,
                            'alocacao_id': aloc.id,
                            'cod_produto': match.cod_produto_interno,
                            'nome_produto': match.nome_produto,
                            'qtd': float(qtd_alocada),
                            'preco': float(preco),
                            'valor': float(qtd_alocada * preco),
                            'po_origem': aloc.odoo_po_name
                        }
                        itens_conciliador.append(item_conciliador)
                        valor_total_conciliador += qtd_alocada * preco

                        # Agrupar dados do PO Original (ficará como saldo)
                        if aloc.odoo_po_id not in pos_originais:
                            pos_originais[aloc.odoo_po_id] = {
                                'po_id': aloc.odoo_po_id,
                                'po_name': aloc.odoo_po_name,
                                'itens': []
                            }

                        # Buscar qtd_original da linha do PO local
                        qtd_original = Decimal('0')
                        pedido_local = PedidoCompras.query.filter_by(
                            odoo_id=str(aloc.odoo_po_line_id)
                        ).first()
                        if pedido_local:
                            qtd_original = Decimal(str(pedido_local.qtd_produto_pedido or 0))
                        else:
                            # Fallback: usar qtd_alocada como original
                            qtd_original = qtd_alocada

                        qtd_saldo = qtd_original - qtd_alocada

                        pos_originais[aloc.odoo_po_id]['itens'].append({
                            'cod_produto': match.cod_produto_interno,
                            'nome_produto': match.nome_produto,
                            'po_line_id': aloc.odoo_po_line_id,
                            'qtd_original': float(qtd_original),
                            'qtd_usada': float(qtd_alocada),
                            'qtd_saldo': float(qtd_saldo) if qtd_saldo > 0 else 0,
                            'preco': float(preco),
                            'data_po': pedido_local.data_pedido_previsao.strftime('%d/%m/%Y') if pedido_local and pedido_local.data_pedido_previsao else None
                        })

                elif match.odoo_po_id:
                    # FALLBACK: Sem alocacoes, usar dados do match diretamente
                    qtd_nf = Decimal(str(match.qtd_nf or 0))
                    qtd_po = Decimal(str(match.qtd_po or 0))
                    preco = Decimal(str(match.preco_nf or 0))
                    saldo = qtd_po - qtd_nf

                    item_conciliador = {
                        'match_id': match.id,
                        'cod_produto': match.cod_produto_interno,
                        'nome_produto': match.nome_produto,
                        'qtd': float(qtd_nf),
                        'preco': float(preco),
                        'valor': float(qtd_nf * preco),
                        'po_origem': match.odoo_po_name
                    }
                    itens_conciliador.append(item_conciliador)
                    valor_total_conciliador += qtd_nf * preco

                    if match.odoo_po_id not in pos_originais:
                        pos_originais[match.odoo_po_id] = {
                            'po_id': match.odoo_po_id,
                            'po_name': match.odoo_po_name,
                            'itens': []
                        }

                    # Buscar pedido local para a data
                    pedido_fallback = PedidoCompras.query.filter_by(
                        odoo_id=str(match.odoo_po_line_id)
                    ).first()

                    pos_originais[match.odoo_po_id]['itens'].append({
                        'cod_produto': match.cod_produto_interno,
                        'nome_produto': match.nome_produto,
                        'po_line_id': match.odoo_po_line_id,
                        'qtd_original': float(qtd_po),
                        'qtd_usada': float(qtd_nf),
                        'qtd_saldo': float(saldo) if saldo > 0 else 0,
                        'preco': float(preco),
                        'data_po': pedido_fallback.data_pedido_previsao.strftime('%d/%m/%Y') if pedido_fallback and pedido_fallback.data_pedido_previsao else None
                    })

            if not itens_conciliador:
                return {
                    'sucesso': False,
                    'erro': 'Nenhum item para o PO Conciliador',
                    'acoes': []
                }

            # Gerar lista de acoes
            acoes = []

            # Acao 1: Criar PO Conciliador
            acoes.append({
                'tipo': 'criar_conciliador',
                'descricao': f"Criar novo PO Conciliador para NF {validacao.numero_nf or validacao.odoo_dfe_id}",
                'valor_total': float(valor_total_conciliador),
                'qtd_itens': len(itens_conciliador),
                'icone': 'fas fa-plus-square',
                'cor': 'success'
            })

            # Acao 2: Adicionar linhas ao PO Conciliador
            for item in itens_conciliador:
                acoes.append({
                    'tipo': 'adicionar_linha_conciliador',
                    'descricao': f"Adicionar {item['qtd']:.0f} un de {item['nome_produto'] or item['cod_produto']} ao PO Conciliador (de {item['po_origem']})",
                    'produto': item['cod_produto'],
                    'quantidade': item['qtd'],
                    'preco': item['preco'],
                    'icone': 'fas fa-cart-plus',
                    'cor': 'primary'
                })

            # Acao 3: Ajustar quantidades nos POs Originais (ficam como saldo)
            pos_com_saldo = []
            for po_id, po_info in pos_originais.items():
                tem_saldo = False
                for item in po_info['itens']:
                    # Verificar se tem qtd_saldo (formato antigo) ou qtd_alocada (novo formato)
                    if 'qtd_saldo' in item:
                        # FORMATO ANTIGO (fallback)
                        if item['qtd_saldo'] > 0:
                            tem_saldo = True
                            acoes.append({
                                'tipo': 'ajustar_saldo_original',
                                'descricao': f"Reduzir {item['nome_produto'] or item['cod_produto']} em {po_info['po_name']}: {item['qtd_original']:.0f} → {item['qtd_saldo']:.0f} un (SALDO)",
                                'po_id': po_id,
                                'po_name': po_info['po_name'],
                                'qtd_original': item['qtd_original'],
                                'qtd_saldo': item['qtd_saldo'],
                                'icone': 'fas fa-minus-circle',
                                'cor': 'warning'
                            })
                        else:
                            acoes.append({
                                'tipo': 'zerar_linha_original',
                                'descricao': f"Zerar {item['nome_produto'] or item['cod_produto']} em {po_info['po_name']}: {item['qtd_original']:.0f} → 0 un",
                                'po_id': po_id,
                                'po_name': po_info['po_name'],
                                'icone': 'fas fa-times',
                                'cor': 'secondary'
                            })
                    else:
                        # NOVO FORMATO (alocacoes): Mostrar qtd sendo consumida
                        qtd_alocada = item.get('qtd_alocada', 0)
                        acoes.append({
                            'tipo': 'consumir_saldo_original',
                            'descricao': f"Consumir {qtd_alocada:.0f} un de {item['nome_produto'] or item['cod_produto']} de {po_info['po_name']}",
                            'po_id': po_id,
                            'po_name': po_info['po_name'],
                            'po_line_id': item.get('po_line_id'),
                            'qtd_consumida': qtd_alocada,
                            'icone': 'fas fa-minus-circle',
                            'cor': 'warning'
                        })
                        # No novo formato, assumimos que sempre pode haver saldo
                        tem_saldo = True

                if tem_saldo:
                    pos_com_saldo.append({
                        'po_id': po_id,
                        'po_name': po_info['po_name'],
                        'itens': po_info['itens']
                    })

            # Acao 4: Confirmar PO Conciliador
            acoes.append({
                'tipo': 'confirmar_conciliador',
                'descricao': "Confirmar PO Conciliador",
                'icone': 'fas fa-check-circle',
                'cor': 'success'
            })

            # Acao 5: Vincular NF ao PO Conciliador
            acoes.append({
                'tipo': 'vincular_nf',
                'descricao': f"Vincular NF {validacao.numero_nf or validacao.odoo_dfe_id} ao PO Conciliador",
                'dfe_id': validacao.odoo_dfe_id,
                'icone': 'fas fa-link',
                'cor': 'success'
            })

            # Resumo
            resumo = {
                'pos_originais_envolvidos': len(pos_originais),
                'pos_com_saldo': len(pos_com_saldo),
                'itens_no_conciliador': len(itens_conciliador),
                'valor_total_conciliador': float(valor_total_conciliador)
            }

            return {
                'sucesso': True,
                'po_conciliador': {
                    'name': f"NOVO (sera criado)",
                    'itens': itens_conciliador,
                    'valor': float(valor_total_conciliador)
                },
                # Manter compatibilidade com template antigo
                'po_principal': {
                    'id': None,
                    'name': 'PO Conciliador (NOVO)',
                    'valor': float(valor_total_conciliador)
                },
                'pos_saldo': pos_com_saldo,
                'pos_originais': list(pos_originais.values()),
                'acoes': acoes,
                'resumo': resumo,
                # Compatibilidade com template antigo
                'pos_envolvidos': list(pos_originais.values())
            }

        except Exception as e:
            logger.error(f"Erro ao simular consolidacao {validacao_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'sucesso': False,
                'erro': str(e),
                'acoes': []
            }

    def consolidar_pos(
        self,
        validacao_id: int,
        pos_para_consolidar: List[Dict[str, Any]],
        usuario: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executa SPLIT/CONSOLIDACAO de POs no Odoo.

        ## NOVA LÓGICA (16/01/2026)

        SEMPRE cria um PO Conciliador novo que casa 100% com a NF.
        Os POs originais permanecem com o saldo restante.

        FLUXO:
        1. Buscar fornecedor_id no Odoo pelo CNPJ
        2. Criar PO Conciliador (vazio)
        3. Para cada item da NF com match:
           a) Criar linha no PO Conciliador com qtd/preco da NF
           b) Reduzir quantidade no PO Original (fica como saldo)
        4. Confirmar PO Conciliador (se necessário)
        5. Vincular NF ao PO Conciliador

        Args:
            validacao_id: ID da validacao local
            pos_para_consolidar: Lista de POs retornada pela validacao
            usuario: Usuario que executou

        Returns:
            Dict com resultado da consolidacao
        """
        try:
            # Buscar validacao
            validacao = db.session.get(ValidacaoNfPoDfe,validacao_id) if validacao_id else None
            if not validacao:
                raise ValueError(f"Validacao {validacao_id} nao encontrada")

            if validacao.status != 'aprovado':
                raise ValueError(
                    f"Validacao {validacao_id} nao esta aprovada. "
                    f"Status atual: {validacao.status}"
                )

            if not pos_para_consolidar:
                raise ValueError("Nenhum PO para consolidar")

            logger.info(
                f"Iniciando SPLIT/CONSOLIDACAO: validacao {validacao_id}, "
                f"{len(pos_para_consolidar)} POs envolvidos"
            )

            odoo = get_odoo_connection()
            if not odoo.authenticate():
                raise ValueError("Falha na autenticacao com Odoo")

            # =================================================================
            # PASSO 1: Buscar fornecedor_id no Odoo pelo CNPJ
            # =================================================================
            cnpj_fornecedor = validacao.cnpj_fornecedor
            cnpj_limpo = ''.join(c for c in str(cnpj_fornecedor) if c.isdigit())

            # Formatar CNPJ para busca (Odoo armazena formatado)
            def formatar_cnpj(cnpj: str) -> str:
                if len(cnpj) == 14:
                    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
                return cnpj

            cnpj_formatado = formatar_cnpj(cnpj_limpo)
            partner_ids = odoo.search(
                'res.partner',
                [('l10n_br_cnpj', '=', cnpj_formatado)],
                limit=1
            )

            if not partner_ids:
                raise ValueError(f"Fornecedor com CNPJ {cnpj_fornecedor} nao encontrado no Odoo")

            fornecedor_id = partner_ids[0]

            # PO de referencia para copiar configuracoes
            po_referencia_id = pos_para_consolidar[0]['po_id']

            # Validar que PO de referencia existe no Odoo
            po_referencia = odoo.read('purchase.order', [po_referencia_id], ['name', 'state'])
            if not po_referencia:
                raise ValueError(
                    f"PO de referencia {po_referencia_id} nao existe no Odoo. "
                    f"Pode ter sido deletado ou arquivado. "
                    f"Revalide a NF para buscar POs atualizados."
                )
            logger.info(
                f"PO de referencia validado: {po_referencia[0].get('name')} "
                f"(estado: {po_referencia[0].get('state')})"
            )

            # =================================================================
            # PASSO 2: Criar PO Conciliador (vazio)
            # =================================================================
            po_conciliador_info = self._criar_po_conciliador(
                odoo, fornecedor_id, validacao, po_referencia_id
            )

            if not po_conciliador_info:
                raise ValueError("Falha ao criar PO Conciliador")

            po_conciliador_id = po_conciliador_info['po_id']
            po_conciliador_name = po_conciliador_info['po_name']

            logger.info(f"PO Conciliador criado: {po_conciliador_name}")

            # =================================================================
            # PASSO 3: Para cada item da NF com match
            # ATUALIZADO: Processa MatchAlocacao para suporte a multi-PO split
            # =================================================================
            matches = db.session.query(MatchNfPoItem).filter_by(
                validacao_id=validacao_id,
                status_match='match'
            ).all()

            linhas_criadas_conciliador = []
            linhas_ajustadas_originais = []
            pos_com_saldo = set()

            # Cache de linhas ja processadas para evitar duplicidade
            linhas_processadas = {}  # {po_line_id: qtd_total_consumida}

            for match in matches:
                # Buscar alocacoes do match (suporte a multi-PO split)
                alocacoes = db.session.query(MatchAlocacao).filter_by(
                    match_item_id=match.id
                ).order_by(MatchAlocacao.ordem).all()

                if alocacoes:
                    # NOVO FLUXO: Processar cada alocacao (multi-PO split)
                    for aloc in alocacoes:
                        if not aloc.odoo_po_line_id:
                            logger.warning(f"Alocacao {aloc.id} sem po_line_id, pulando")
                            continue

                        qtd_alocada = Decimal(str(aloc.qtd_alocada or 0))
                        preco = float(aloc.preco_po or match.preco_nf or 0)

                        # Buscar product_id da linha original
                        linha_original = odoo.read(
                            'purchase.order.line',
                            [aloc.odoo_po_line_id],
                            ['product_id', 'product_qty', 'qty_received']
                        )

                        if not linha_original or not linha_original[0].get('product_id'):
                            logger.warning(
                                f"Linha {aloc.odoo_po_line_id} sem produto, pulando"
                            )
                            continue

                        product_id = linha_original[0]['product_id'][0]
                        qtd_po_original = Decimal(str(linha_original[0].get('product_qty', 0) or 0))
                        qtd_recebida = Decimal(str(linha_original[0].get('qty_received', 0) or 0))

                        # ---------------------------------------------------------
                        # 3a) Criar linha no PO Conciliador
                        # ---------------------------------------------------------
                        nova_linha_id = self._criar_linha_po_conciliador(
                            odoo,
                            po_conciliador_id,
                            product_id,
                            float(qtd_alocada),
                            preco,
                            aloc.odoo_po_line_id
                        )

                        if nova_linha_id:
                            linhas_criadas_conciliador.append({
                                'linha_id': nova_linha_id,
                                'produto': match.cod_produto_interno,
                                'nome': match.nome_produto,
                                'qtd': float(qtd_alocada),
                                'preco': preco,
                                'po_origem': aloc.odoo_po_name,
                                'alocacao_id': aloc.id
                            })

                        # ---------------------------------------------------------
                        # 3b) Ajustar quantidade no PO Original
                        # Acumular consumo se mesma linha usada por multiplos itens
                        # ---------------------------------------------------------
                        consumo_anterior = linhas_processadas.get(aloc.odoo_po_line_id, Decimal('0'))
                        consumo_total = consumo_anterior + qtd_alocada
                        linhas_processadas[aloc.odoo_po_line_id] = consumo_total

                        # Calcular novo saldo: qtd_original - qtd_recebida - qtd_alocada_total
                        saldo_apos_alocacao = qtd_po_original - qtd_recebida - consumo_total
                        nova_qtd = float(saldo_apos_alocacao) if saldo_apos_alocacao > 0 else 0

                        self._ajustar_quantidade_linha(
                            odoo, aloc.odoo_po_line_id, nova_qtd
                        )

                        linhas_ajustadas_originais.append({
                            'po_id': aloc.odoo_po_id,
                            'po_name': aloc.odoo_po_name,
                            'linha_id': aloc.odoo_po_line_id,
                            'produto': match.cod_produto_interno,
                            'qtd_consumida': float(qtd_alocada),
                            'qtd_saldo': nova_qtd
                        })

                        # Registrar que este PO foi usado
                        if nova_qtd > 0:
                            pos_com_saldo.add((aloc.odoo_po_id, aloc.odoo_po_name))

                elif match.odoo_po_line_id:
                    # FALLBACK: Sem alocacoes, usar dados do match diretamente
                    qtd_nf = Decimal(str(match.qtd_nf or 0))
                    qtd_po = Decimal(str(match.qtd_po or 0))
                    preco_nf = float(match.preco_nf or 0)

                    linha_original = odoo.read(
                        'purchase.order.line',
                        [match.odoo_po_line_id],
                        ['product_id']
                    )

                    if not linha_original or not linha_original[0].get('product_id'):
                        logger.warning(
                            f"Linha {match.odoo_po_line_id} sem produto, pulando"
                        )
                        continue

                    product_id = linha_original[0]['product_id'][0]

                    nova_linha_id = self._criar_linha_po_conciliador(
                        odoo,
                        po_conciliador_id,
                        product_id,
                        float(qtd_nf),
                        preco_nf,
                        match.odoo_po_line_id
                    )

                    if nova_linha_id:
                        linhas_criadas_conciliador.append({
                            'linha_id': nova_linha_id,
                            'produto': match.cod_produto_interno,
                            'nome': match.nome_produto,
                            'qtd': float(qtd_nf),
                            'preco': preco_nf
                        })

                    saldo = qtd_po - qtd_nf
                    nova_qtd_original = float(saldo) if saldo > 0 else 0

                    self._ajustar_quantidade_linha(
                        odoo, match.odoo_po_line_id, nova_qtd_original
                    )

                    linhas_ajustadas_originais.append({
                        'po_id': match.odoo_po_id,
                        'po_name': match.odoo_po_name,
                        'linha_id': match.odoo_po_line_id,
                        'produto': match.cod_produto_interno,
                        'qtd_original': float(qtd_po),
                        'qtd_saldo': nova_qtd_original
                    })

                    if nova_qtd_original > 0:
                        pos_com_saldo.add((match.odoo_po_id, match.odoo_po_name))

            # =================================================================
            # PASSO 4: Confirmar PO Conciliador
            # =================================================================
            try:
                odoo.execute_kw(
                    'purchase.order',
                    'button_confirm',
                    [po_conciliador_id]
                )
                logger.info(f"PO Conciliador {po_conciliador_name} confirmado")
            except Exception as e:
                logger.warning(
                    f"Nao foi possivel confirmar PO Conciliador automaticamente: {e}"
                )

            # =================================================================
            # PASSO 5: Vincular NF ao PO Conciliador
            # =================================================================
            self._vincular_dfe_ao_po(odoo, validacao.odoo_dfe_id, po_conciliador_id)

            # =================================================================
            # Atualizar validacao local
            # =================================================================
            validacao.status = 'consolidado'
            validacao.po_consolidado_id = po_conciliador_id
            validacao.po_consolidado_name = po_conciliador_name
            validacao.pos_saldo_ids = json.dumps([
                {'po_id': po_id, 'po_name': po_name}
                for po_id, po_name in pos_com_saldo
            ])
            validacao.acao_executada = {
                'tipo': 'split_consolidacao',
                'usuario': usuario,
                'data': datetime.utcnow().isoformat(),
                'po_conciliador': {
                    'id': po_conciliador_id,
                    'name': po_conciliador_name,
                    'linhas': linhas_criadas_conciliador
                },
                'pos_originais_ajustados': linhas_ajustadas_originais,
                'pos_com_saldo': [
                    {'po_id': po_id, 'po_name': po_name}
                    for po_id, po_name in pos_com_saldo
                ]
            }
            validacao.consolidado_em = datetime.utcnow()
            validacao.atualizado_em = datetime.utcnow()

            db.session.commit()

            # =================================================================
            # Gap 1 FIX: Marcar DFEs afetados pelas POs modificadas
            # Isso garante que outros DFEs que usavam essas POs sejam revalidados
            # =================================================================
            po_ids_modificados = list(set(
                aloc['po_id'] for aloc in linhas_ajustadas_originais
                if aloc.get('po_id')
            ))
            if po_ids_modificados:
                dfes_marcados = _marcar_dfes_afetados_por_pos(po_ids_modificados)
                if dfes_marcados > 0:
                    logger.info(
                        f"🔄 {dfes_marcados} DFEs marcados para revalidação "
                        f"(POs afetadas pela consolidação)"
                    )

            # =================================================================
            # Gap 4 FIX: Chamar detector imediatamente para reduzir latência
            # Não depender do scheduler (30 min) - detectar mudanças agora
            # =================================================================
            try:
                from app.recebimento.services.po_changes_detector_service import PoChangesDetectorService
                detector = PoChangesDetectorService()
                resultado_deteccao = detector.detectar_e_marcar_revalidacoes(minutos_janela=5)
                if resultado_deteccao.get('dfes_marcados', 0) > 0:
                    logger.info(
                        f"🔍 Detector imediato: {resultado_deteccao['dfes_marcados']} DFEs "
                        f"adicionais marcados para revalidação"
                    )
            except Exception as e_det:
                logger.warning(f"Detector imediato falhou (não crítico): {e_det}")

            logger.info(
                f"SPLIT/CONSOLIDACAO concluida: "
                f"PO Conciliador {po_conciliador_name} criado, "
                f"{len(linhas_criadas_conciliador)} linhas, "
                f"{len(pos_com_saldo)} POs com saldo"
            )

            return {
                'sucesso': True,
                'po_consolidado_id': po_conciliador_id,
                'po_consolidado_name': po_conciliador_name,
                'linhas_criadas': len(linhas_criadas_conciliador),
                'pos_com_saldo': [
                    {'po_id': po_id, 'po_name': po_name}
                    for po_id, po_name in pos_com_saldo
                ]
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao executar SPLIT/CONSOLIDACAO: {e}")
            import traceback
            logger.error(traceback.format_exc())

            # Atualizar validacao com erro
            try:
                validacao = db.session.get(ValidacaoNfPoDfe,validacao_id) if validacao_id else None
                if validacao:
                    validacao.status = 'erro'
                    validacao.erro_mensagem = str(e)
                    db.session.commit()
            except Exception as e:
                pass

            return {
                'sucesso': False,
                'erro': str(e)
            }

    # =========================================================================
    # ODOO OPERATIONS
    # =========================================================================

    def _criar_po_saldo(
        self,
        odoo,
        po_original_id: int,
        linha_original_id: int,
        quantidade_saldo: float
    ) -> Optional[Dict[str, Any]]:
        """
        Cria um novo PO com o saldo restante.

        Args:
            odoo: Conexao Odoo
            po_original_id: ID do PO original
            linha_original_id: ID da linha original
            quantidade_saldo: Quantidade para o PO saldo

        Returns:
            Dict com info do PO saldo ou None se falhou
        """
        try:
            # Ler dados do PO original
            po_original = odoo.read(
                'purchase.order',
                [po_original_id],
                ['partner_id', 'date_order', 'date_planned', 'picking_type_id', 'company_id']
            )

            if not po_original:
                logger.warning(f"PO {po_original_id} nao encontrado para criar saldo")
                return None

            po_data = po_original[0]

            # Ler dados da linha original
            linha_original = odoo.read(
                'purchase.order.line',
                [linha_original_id],
                ['product_id', 'name', 'price_unit', 'product_uom', 'date_planned']
            )

            if not linha_original:
                logger.warning(f"Linha {linha_original_id} nao encontrada")
                return None

            linha_data = linha_original[0]

            # Criar novo PO
            novo_po_data = {
                'partner_id': po_data['partner_id'][0] if po_data.get('partner_id') else False,
                'date_order': po_data.get('date_order'),
                'date_planned': po_data.get('date_planned') or linha_data.get('date_planned'),
                'origin': f'Saldo de {po_original_id}',
                'state': 'draft',  # PO saldo comeca como rascunho
            }

            # Adicionar picking_type_id se existir
            if po_data.get('picking_type_id'):
                novo_po_data['picking_type_id'] = po_data['picking_type_id'][0]

            # Criar PO
            novo_po_id = odoo.create('purchase.order', novo_po_data)

            if not novo_po_id:
                logger.warning("Falha ao criar PO saldo")
                return None

            # Criar linha no novo PO
            nova_linha_data = {
                'order_id': novo_po_id,
                'product_id': linha_data['product_id'][0] if linha_data.get('product_id') else False,
                'name': linha_data.get('name', 'Saldo'),
                'product_qty': quantidade_saldo,
                'price_unit': linha_data.get('price_unit', 0),
                'product_uom': linha_data['product_uom'][0] if linha_data.get('product_uom') else False,
                'date_planned': linha_data.get('date_planned') or po_data.get('date_planned'),
            }

            odoo.create('purchase.order.line', nova_linha_data)

            # Buscar nome do novo PO
            novo_po = odoo.read('purchase.order', [novo_po_id], ['name'])
            novo_po_name = novo_po[0]['name'] if novo_po else str(novo_po_id)

            logger.info(
                f"PO saldo {novo_po_name} criado com {quantidade_saldo} unidades"
            )

            return {
                'po_id': novo_po_id,
                'po_name': novo_po_name,
                'quantidade': quantidade_saldo,
                'po_original_id': po_original_id
            }

        except Exception as e:
            logger.error(f"Erro ao criar PO saldo: {e}")
            return None

    def _criar_po_conciliador(
        self,
        odoo,
        fornecedor_id: int,
        validacao: 'ValidacaoNfPoDfe',
        po_referencia_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Cria PO Conciliador duplicando o PO de referencia via copy() do Odoo.

        Usa o metodo copy() nativo do Odoo que duplica TODOS os campos do PO
        (empresa, condicao pgto, campos fiscais, etc.) e sobrescreve apenas
        os valores especificados em 'default'.

        O PO Conciliador e criado vazio (sem linhas) e as linhas sao
        adicionadas posteriormente via _criar_linha_po_conciliador().

        Args:
            odoo: Conexao Odoo
            fornecedor_id: ID do partner (fornecedor) no Odoo
            validacao: Objeto ValidacaoNfPoDfe com dados da NF
            po_referencia_id: ID de um PO existente para duplicar

        Returns:
            Dict com info do PO conciliador ou None se falhou
        """
        try:
            # Usar copy() nativo do Odoo - duplica o PO inteiro e sobrescreve
            # campos especificados. Isso garante que TODOS os campos obrigatorios
            # (empresa, condicao pgto, fiscal_position, picking_type, etc.)
            # sejam copiados automaticamente.
            novo_po_id = odoo.execute_kw(
                'purchase.order',
                'copy',
                [po_referencia_id],
                {
                    'default': {
                        'partner_id': fornecedor_id,
                        'date_order': validacao.data_nf.isoformat() if validacao.data_nf else datetime.utcnow().isoformat(),
                        'origin': f'Conciliacao NF {validacao.numero_nf or validacao.odoo_dfe_id}',
                        'state': 'draft',
                        'order_line': False,  # Limpar linhas - serao criadas manualmente depois
                    }
                }
            )

            if not novo_po_id:
                logger.error("Falha ao duplicar PO via copy()")
                return None

            logger.info(f"✅ PO Conciliador criado com ID {novo_po_id}")

            # Verificar se copy() criou linhas indesejadas (fallback)
            # Em algumas versoes do Odoo, order_line=False pode nao funcionar
            # NOTA: Essa verificacao e opcional - se falhar, continuamos mesmo assim
            try:
                linhas_existentes = odoo.search(
                    'purchase.order.line',
                    [('order_id', '=', novo_po_id)]  # CORRIGIDO: era [[...]] causando IndexError
                )
                if linhas_existentes:
                    logger.warning(
                        f"copy() criou {len(linhas_existentes)} linhas indesejadas, removendo..."
                    )
                    try:
                        odoo.execute_kw(
                            'purchase.order.line',
                            'unlink',
                            [linhas_existentes]
                        )
                        logger.info(f"Linhas indesejadas removidas do PO Conciliador")
                    except Exception as e_del:
                        logger.warning(
                            f"Nao foi possivel remover linhas indesejadas: {e_del}. "
                            f"Linhas serao sobrescritas pelas novas."
                        )
            except Exception as e_linhas:
                logger.warning(
                    f"Nao foi possivel verificar linhas indesejadas: {e_linhas}. "
                    f"Continuando mesmo assim."
                )

            # Buscar nome do novo PO
            novo_po = odoo.read('purchase.order', [novo_po_id], ['name'])
            novo_po_name = novo_po[0]['name'] if novo_po else str(novo_po_id)

            logger.info(
                f"PO Conciliador {novo_po_name} criado via copy() "
                f"(baseado em PO {po_referencia_id}) para NF {validacao.numero_nf}"
            )

            return {
                'po_id': novo_po_id,
                'po_name': novo_po_name
            }

        except Exception as e:
            logger.error(f"Erro ao criar PO Conciliador via copy(): {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _criar_linha_po_conciliador(
        self,
        odoo,
        po_conciliador_id: int,
        produto_id: int,
        quantidade: float,
        preco_unitario: float,
        linha_referencia_id: int
    ) -> Optional[int]:
        """
        Cria linha no PO Conciliador duplicando a linha de referencia via copy().

        Usa o metodo copy() nativo do Odoo para duplicar a linha original,
        copiando TODOS os campos (CFOP, impostos, UOM, operacao fiscal, etc.)
        e sobrescrevendo apenas order_id, product_qty e price_unit.

        Args:
            odoo: Conexao Odoo
            po_conciliador_id: ID do PO Conciliador
            produto_id: ID do produto no Odoo
            quantidade: Quantidade da NF
            preco_unitario: Preco unitario da NF
            linha_referencia_id: ID de uma linha de PO existente para duplicar

        Returns:
            ID da linha criada ou None se falhou
        """
        try:
            # Duplicar a linha via copy() - copia CFOP, impostos, UOM,
            # operacao fiscal e todos os demais campos automaticamente
            nova_linha_id = odoo.execute_kw(
                'purchase.order.line',
                'copy',
                [linha_referencia_id],
                {
                    'default': {
                        'order_id': po_conciliador_id,
                        'product_id': produto_id,
                        'product_qty': quantidade,
                        'price_unit': preco_unitario,
                    }
                }
            )

            if nova_linha_id:
                logger.debug(
                    f"Linha criada no PO Conciliador via copy(): "
                    f"produto {produto_id}, qtd {quantidade}, preco {preco_unitario}"
                )

            return nova_linha_id

        except Exception as e:
            logger.error(f"Erro ao criar linha no PO Conciliador via copy(): {e}")
            return None

    def _ajustar_quantidade_linha(
        self,
        odoo,
        linha_id: int,
        nova_quantidade: float
    ) -> bool:
        """
        Ajusta a quantidade de uma linha de PO.

        Args:
            odoo: Conexao Odoo
            linha_id: ID da linha
            nova_quantidade: Nova quantidade

        Returns:
            True se ajustou com sucesso
        """
        try:
            odoo.write(
                'purchase.order.line',
                linha_id,
                {'product_qty': nova_quantidade}
            )

            logger.debug(f"Linha {linha_id} ajustada para {nova_quantidade}")
            return True

        except Exception as e:
            logger.error(f"Erro ao ajustar linha {linha_id}: {e}")
            return False

    def _verificar_po_vazio(self, odoo, po_id: int) -> bool:
        """
        Verifica se um PO esta vazio (todas as linhas com qtd 0).

        Args:
            odoo: Conexao Odoo
            po_id: ID do PO

        Returns:
            True se PO esta vazio
        """
        try:
            # Buscar linhas do PO
            line_ids = odoo.search(
                'purchase.order.line',
                [[('order_id', '=', po_id)]]
            )

            if not line_ids:
                return True

            # Verificar quantidades
            lines = odoo.read(
                'purchase.order.line',
                line_ids,
                ['product_qty']
            )

            for line in lines:
                if (line.get('product_qty') or 0) > 0:
                    return False

            return True

        except Exception as e:
            logger.error(f"Erro ao verificar PO {po_id}: {e}")
            return False

    def _cancelar_po(self, odoo, po_id: int) -> bool:
        """
        Cancela um PO no Odoo.

        Args:
            odoo: Conexao Odoo
            po_id: ID do PO

        Returns:
            True se cancelou com sucesso
        """
        try:
            # Chamar button_cancel
            odoo.execute_kw(
                'purchase.order',
                'button_cancel',
                [po_id]
            )

            logger.info(f"PO {po_id} cancelado")
            return True

        except Exception as e:
            logger.error(f"Erro ao cancelar PO {po_id}: {e}")

            # Tentar alternativa: mudar state diretamente
            try:
                odoo.write(
                    'purchase.order',
                    po_id,
                    {'state': 'cancel'}
                )
                return True
            except Exception as e:
                pass

            return False

    def _vincular_dfe_ao_po(
        self,
        odoo,
        dfe_id: int,
        po_id: int
    ) -> bool:
        """
        Vincula um DFE a um PO no Odoo.

        Args:
            odoo: Conexao Odoo
            dfe_id: ID do DFE
            po_id: ID do PO

        Returns:
            True se vinculou com sucesso
        """
        try:
            # Atualizar DFE com referencia ao PO
            # NOTA: O campo exato depende da customizacao do Odoo
            # Tentar dfe_id no PO
            odoo.write(
                'purchase.order',
                po_id,
                {'dfe_id': dfe_id}
            )

            logger.info(f"DFE {dfe_id} vinculado ao PO {po_id}")
            return True

        except Exception as e:
            logger.warning(f"Nao foi possivel vincular DFE {dfe_id} ao PO {po_id}: {e}")
            # Nao falhar a operacao por isso
            return False

    # =========================================================================
    # QUERY METHODS
    # =========================================================================

    def buscar_po(self, po_id: int) -> Optional[Dict[str, Any]]:
        """
        Busca dados de um PO no Odoo.

        Args:
            po_id: ID do PO

        Returns:
            Dict com dados do PO ou None
        """
        try:
            odoo = get_odoo_connection()

            pos = odoo.read(
                'purchase.order',
                [po_id],
                [
                    'id', 'name', 'partner_id', 'date_order', 'date_planned',
                    'state', 'amount_total', 'order_line', 'dfe_id'
                ]
            )

            if not pos:
                return None

            po = pos[0]

            # Buscar linhas
            if po.get('order_line'):
                lines = odoo.read(
                    'purchase.order.line',
                    po['order_line'],
                    [
                        'id', 'product_id', 'name', 'product_qty',
                        'qty_received', 'price_unit', 'date_planned'
                    ]
                )
                po['lines'] = lines
            else:
                po['lines'] = []

            return po

        except Exception as e:
            logger.error(f"Erro ao buscar PO {po_id}: {e}")
            return None

    def buscar_pos_por_fornecedor(
        self,
        cnpj_fornecedor: str,
        apenas_com_saldo: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Busca POs de um fornecedor.

        Args:
            cnpj_fornecedor: CNPJ do fornecedor
            apenas_com_saldo: Se True, retorna apenas POs com saldo disponivel

        Returns:
            Lista de POs
        """
        try:
            odoo = get_odoo_connection()

            # Limpar CNPJ
            cnpj_limpo = ''.join(c for c in str(cnpj_fornecedor) if c.isdigit())

            # Buscar partner
            partner_ids = odoo.search(
                'res.partner',
                [[('l10n_br_cnpj', 'ilike', cnpj_limpo)]],
                limit=1
            )

            if not partner_ids:
                return []

            # Buscar POs
            domain = [
                ('partner_id', '=', partner_ids[0]),
                ('state', 'in', ['purchase', 'done'])
            ]

            po_ids = odoo.search(
                'purchase.order',
                [domain],
                order='date_order desc'
            )

            if not po_ids:
                return []

            pos = odoo.read(
                'purchase.order',
                po_ids,
                ['id', 'name', 'date_order', 'amount_total', 'state', 'order_line']
            )

            if apenas_com_saldo:
                # Filtrar POs com saldo
                pos_filtrados = []
                for po in pos:
                    if po.get('order_line'):
                        lines = odoo.read(
                            'purchase.order.line',
                            po['order_line'],
                            ['product_qty', 'qty_received']
                        )
                        tem_saldo = any(
                            (line.get('product_qty', 0) or 0) > (line.get('qty_received', 0) or 0)
                            for line in lines
                        )
                        if tem_saldo:
                            pos_filtrados.append(po)

                return pos_filtrados

            return pos

        except Exception as e:
            logger.error(f"Erro ao buscar POs do fornecedor {cnpj_fornecedor}: {e}")
            return []

    # =========================================================================
    # ROLLBACK
    # =========================================================================

    def reverter_consolidacao(
        self,
        validacao_id: int,
        usuario: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reverte uma consolidacao executada.

        NOTA: Operacao complexa que tenta desfazer as acoes.
        Pode nao ser 100% reversivel dependendo do estado atual.

        Args:
            validacao_id: ID da validacao
            usuario: Usuario que solicitou reversao

        Returns:
            Dict com resultado
        """
        try:
            validacao = db.session.get(ValidacaoNfPoDfe,validacao_id) if validacao_id else None
            if not validacao:
                raise ValueError(f"Validacao {validacao_id} nao encontrada")

            if validacao.status != 'consolidado':
                raise ValueError(
                    f"Validacao {validacao_id} nao esta consolidada. "
                    f"Status: {validacao.status}"
                )

            if not validacao.acao_executada:
                raise ValueError("Sem informacoes de acao para reverter")

            logger.warning(
                f"Iniciando reversao da consolidacao {validacao_id} "
                f"por usuario {usuario}"
            )

            odoo = get_odoo_connection()

            acao = validacao.acao_executada

            # 1. Cancelar POs saldo criados
            pos_saldo = json.loads(validacao.pos_saldo_ids or '[]')
            for po_saldo in pos_saldo:
                try:
                    self._cancelar_po(odoo, po_saldo['po_id'])
                except Exception as e:
                    pass

            # 2. Restaurar quantidades originais
            for linha_info in acao.get('linhas_ajustadas', []):
                try:
                    odoo.write(
                        'purchase.order.line',
                        linha_info['linha_id'],
                        {'product_qty': linha_info['qtd_original']}
                    )
                except Exception as e:
                    pass

            # 3. Descancelar POs cancelados
            pos_cancelados = json.loads(validacao.pos_cancelados_ids or '[]')
            for po_cancel in pos_cancelados:
                try:
                    odoo.write(
                        'purchase.order',
                        po_cancel['po_id'],
                        {'state': 'purchase'}
                    )
                except Exception as e:
                    pass

            # 4. Remover vinculo DFE -> PO
            try:
                odoo.write(
                    'purchase.order',
                    validacao.po_consolidado_id,
                    {'dfe_id': False}
                )
            except Exception as e:
                pass

            # Atualizar validacao
            # Gap 2 FIX: Marcar para revalidação ao reverter consolidação
            # Isso força o job a reprocessar o DFE na próxima execução
            validacao.status = 'bloqueado'  # Força revalidação (não apenas 'aprovado')
            validacao.po_modificada_apos_validacao = True  # Flag de revalidação
            validacao.po_consolidado_id = None
            validacao.po_consolidado_name = None
            validacao.pos_saldo_ids = None
            validacao.pos_cancelados_ids = None
            validacao.consolidado_em = None
            validacao.atualizado_em = datetime.utcnow()

            db.session.commit()

            logger.info(
                f"⚠️ Reversao da consolidacao {validacao_id} concluida - "
                f"DFE marcado para revalidação"
            )

            return {
                'sucesso': True,
                'mensagem': 'Consolidacao revertida com sucesso',
                'validacao_id': validacao_id
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao reverter consolidacao {validacao_id}: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }
