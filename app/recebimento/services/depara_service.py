"""
Service de De-Para Produto/Fornecedor - FASE 2
===============================================

Gerencia o mapeamento entre codigos de produtos do fornecedor e codigos internos.

Funcionalidades:
1. CRUD de mapeamentos De-Para
2. Conversao de codigos (fornecedor -> interno)
3. Conversao de unidades de medida (UM)
4. Sincronizacao bidirecional com Odoo (product.supplierinfo)

Campos de Conversao:
- cod_produto_fornecedor -> cod_produto_interno
- um_fornecedor -> um_interna (com fator_conversao)
  Ex: 1 ML (Milhar) = 1000 UNITS

UoMs conhecidas que indicam MILHAR:
- ML, MI, MIL = 1000 unidades

Referencia: .claude/references/CONVERSAO_UOM_ODOO.md
"""

import logging
from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import datetime

from app import db
from app.recebimento.models import ProdutoFornecedorDepara
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


# UoMs que indicam MILHAR (fator 1000)
UOMS_MILHAR = ['ML', 'MI', 'MIL']

# Fator padrao para Milhar
FATOR_MILHAR = Decimal('1000.0000')


class DeparaService:
    """
    Service para gerenciamento de De-Para Produto/Fornecedor.
    Converte codigos e unidades de medida do fornecedor para internos.
    """

    # =========================================================================
    # CRUD OPERATIONS
    # =========================================================================

    def listar(
        self,
        cnpj_fornecedor: Optional[str] = None,
        cod_produto_fornecedor: Optional[str] = None,
        cod_produto_interno: Optional[str] = None,
        ativo: Optional[bool] = True,
        sincronizado_odoo: Optional[bool] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Lista mapeamentos De-Para com filtros.

        Args:
            cnpj_fornecedor: Filtrar por CNPJ
            cod_produto_fornecedor: Filtrar por codigo do fornecedor
            cod_produto_interno: Filtrar por codigo interno
            ativo: Filtrar por status ativo (default: True)
            sincronizado_odoo: Filtrar por status de sincronizacao
            page: Pagina atual
            per_page: Itens por pagina

        Returns:
            Dict com items, total, pages
        """
        try:
            query = ProdutoFornecedorDepara.query

            if cnpj_fornecedor:
                # Limpar CNPJ (remover pontuacao)
                cnpj_limpo = self._limpar_cnpj(cnpj_fornecedor)
                query = query.filter(
                    ProdutoFornecedorDepara.cnpj_fornecedor.ilike(f'%{cnpj_limpo}%')
                )

            if cod_produto_fornecedor:
                query = query.filter(
                    ProdutoFornecedorDepara.cod_produto_fornecedor.ilike(
                        f'%{cod_produto_fornecedor}%'
                    )
                )

            if cod_produto_interno:
                query = query.filter(
                    ProdutoFornecedorDepara.cod_produto_interno.ilike(
                        f'%{cod_produto_interno}%'
                    )
                )

            if ativo is not None:
                query = query.filter(ProdutoFornecedorDepara.ativo == ativo)

            if sincronizado_odoo is not None:
                query = query.filter(
                    ProdutoFornecedorDepara.sincronizado_odoo == sincronizado_odoo
                )

            # Ordenar por fornecedor e codigo
            query = query.order_by(
                ProdutoFornecedorDepara.cnpj_fornecedor,
                ProdutoFornecedorDepara.cod_produto_fornecedor
            )

            # Paginar
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)

            return {
                'items': [self._to_dict(item) for item in pagination.items],
                'total': pagination.total,
                'pages': pagination.pages,
                'page': page,
                'per_page': per_page
            }

        except Exception as e:
            logger.error(f"Erro ao listar De-Para: {e}")
            raise

    def buscar_por_id(self, depara_id: int) -> Optional[Dict[str, Any]]:
        """
        Busca De-Para por ID.

        Args:
            depara_id: ID do registro

        Returns:
            Dict com dados ou None
        """
        try:
            item = ProdutoFornecedorDepara.query.get(depara_id)
            return self._to_dict(item) if item else None

        except Exception as e:
            logger.error(f"Erro ao buscar De-Para {depara_id}: {e}")
            raise

    def criar(
        self,
        cnpj_fornecedor: str,
        cod_produto_fornecedor: str,
        cod_produto_interno: str,
        razao_fornecedor: Optional[str] = None,
        descricao_produto_fornecedor: Optional[str] = None,
        nome_produto_interno: Optional[str] = None,
        odoo_product_id: Optional[int] = None,
        um_fornecedor: Optional[str] = None,
        um_interna: str = 'UNITS',
        fator_conversao: Decimal = Decimal('1.0000'),
        criado_por: Optional[str] = None,
        auto_sync_odoo: bool = True
    ) -> Dict[str, Any]:
        """
        Cria novo mapeamento De-Para.

        Args:
            cnpj_fornecedor: CNPJ do fornecedor
            cod_produto_fornecedor: Codigo do produto no fornecedor
            cod_produto_interno: Codigo interno (default_code)
            razao_fornecedor: Razao social do fornecedor
            descricao_produto_fornecedor: Descricao do produto na NF
            nome_produto_interno: Nome do produto interno
            odoo_product_id: ID do produto no Odoo
            um_fornecedor: Unidade de medida do fornecedor (ex: ML)
            um_interna: Unidade de medida interna (default: UNITS)
            fator_conversao: Fator de conversao de UM
            criado_por: Usuario que criou
            auto_sync_odoo: Se True, sincroniza automaticamente com Odoo (default: True)

        Returns:
            Dict com dados do registro criado

        Raises:
            ValueError: Se ja existir mapeamento para este fornecedor/produto
        """
        try:
            # Limpar CNPJ
            cnpj_limpo = self._limpar_cnpj(cnpj_fornecedor)

            # Verificar se ja existe
            existente = ProdutoFornecedorDepara.query.filter_by(
                cnpj_fornecedor=cnpj_limpo,
                cod_produto_fornecedor=cod_produto_fornecedor
            ).first()

            if existente:
                raise ValueError(
                    f"Ja existe De-Para para fornecedor {cnpj_limpo} "
                    f"e produto {cod_produto_fornecedor}"
                )

            # Detectar fator de conversao automaticamente se UM for Milhar
            if um_fornecedor and um_fornecedor.upper() in UOMS_MILHAR:
                fator_conversao = FATOR_MILHAR
                logger.info(
                    f"Fator de conversao detectado automaticamente: "
                    f"{um_fornecedor} = {fator_conversao} unidades"
                )

            # Criar registro
            novo = ProdutoFornecedorDepara(
                cnpj_fornecedor=cnpj_limpo,
                razao_fornecedor=razao_fornecedor,
                cod_produto_fornecedor=cod_produto_fornecedor,
                descricao_produto_fornecedor=descricao_produto_fornecedor,
                cod_produto_interno=cod_produto_interno,
                nome_produto_interno=nome_produto_interno,
                odoo_product_id=odoo_product_id,
                um_fornecedor=um_fornecedor,
                um_interna=um_interna,
                fator_conversao=fator_conversao,
                ativo=True,
                sincronizado_odoo=False,
                criado_por=criado_por,
                criado_em=datetime.utcnow()
            )

            db.session.add(novo)
            db.session.commit()

            logger.info(
                f"De-Para criado: {cnpj_limpo}/{cod_produto_fornecedor} -> "
                f"{cod_produto_interno}"
            )

            resultado = self._to_dict(novo)

            # AUTO SYNC: Sincronizar automaticamente com Odoo se tiver odoo_product_id
            if auto_sync_odoo and odoo_product_id:
                try:
                    sync_result = self.sincronizar_para_odoo(novo.id)
                    resultado['odoo_sync'] = sync_result
                    logger.info(f"De-Para {novo.id} sincronizado automaticamente com Odoo")
                except Exception as sync_error:
                    logger.warning(
                        f"Nao foi possivel sincronizar De-Para {novo.id} com Odoo: {sync_error}"
                    )
                    resultado['odoo_sync'] = {'sucesso': False, 'erro': str(sync_error)}

            return resultado

        except ValueError:
            raise
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar De-Para: {e}")
            raise

    def atualizar(
        self,
        depara_id: int,
        cod_produto_interno: Optional[str] = None,
        nome_produto_interno: Optional[str] = None,
        odoo_product_id: Optional[int] = None,
        um_fornecedor: Optional[str] = None,
        um_interna: Optional[str] = None,
        fator_conversao: Optional[Decimal] = None,
        ativo: Optional[bool] = None,
        atualizado_por: Optional[str] = None,
        auto_sync_odoo: bool = True
    ) -> Dict[str, Any]:
        """
        Atualiza mapeamento De-Para existente.

        Args:
            depara_id: ID do registro
            cod_produto_interno: Novo codigo interno
            nome_produto_interno: Novo nome do produto
            odoo_product_id: Novo ID do produto Odoo
            um_fornecedor: Nova UM do fornecedor
            um_interna: Nova UM interna
            fator_conversao: Novo fator de conversao
            ativo: Novo status
            atualizado_por: Usuario que atualizou
            auto_sync_odoo: Se True, sincroniza automaticamente com Odoo (default: True)

        Returns:
            Dict com dados atualizados

        Raises:
            ValueError: Se registro nao existir
        """
        try:
            item = ProdutoFornecedorDepara.query.get(depara_id)

            if not item:
                raise ValueError(f"De-Para {depara_id} nao encontrado")

            # Atualizar campos se fornecidos
            if cod_produto_interno is not None:
                item.cod_produto_interno = cod_produto_interno

            if nome_produto_interno is not None:
                item.nome_produto_interno = nome_produto_interno

            if odoo_product_id is not None:
                item.odoo_product_id = odoo_product_id

            if um_fornecedor is not None:
                item.um_fornecedor = um_fornecedor
                # Auto-detectar fator se Milhar
                if um_fornecedor.upper() in UOMS_MILHAR and fator_conversao is None:
                    item.fator_conversao = FATOR_MILHAR

            if um_interna is not None:
                item.um_interna = um_interna

            if fator_conversao is not None:
                item.fator_conversao = fator_conversao

            if ativo is not None:
                item.ativo = ativo

            # Marcar como nao sincronizado (mudou localmente)
            item.sincronizado_odoo = False
            item.atualizado_por = atualizado_por
            item.atualizado_em = datetime.utcnow()

            db.session.commit()

            logger.info(f"De-Para {depara_id} atualizado")

            resultado = self._to_dict(item)

            # AUTO SYNC: Sincronizar automaticamente com Odoo se tiver odoo_product_id
            if auto_sync_odoo and item.odoo_product_id:
                try:
                    sync_result = self.sincronizar_para_odoo(depara_id)
                    resultado['odoo_sync'] = sync_result
                    logger.info(f"De-Para {depara_id} sincronizado automaticamente com Odoo")
                except Exception as sync_error:
                    logger.warning(
                        f"Nao foi possivel sincronizar De-Para {depara_id} com Odoo: {sync_error}"
                    )
                    resultado['odoo_sync'] = {'sucesso': False, 'erro': str(sync_error)}

            return resultado

        except ValueError:
            raise
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar De-Para {depara_id}: {e}")
            raise

    def excluir(self, depara_id: int) -> bool:
        """
        Exclui mapeamento De-Para (soft delete - marca como inativo).

        Args:
            depara_id: ID do registro

        Returns:
            True se excluido com sucesso

        Raises:
            ValueError: Se registro nao existir
        """
        try:
            item = ProdutoFornecedorDepara.query.get(depara_id)

            if not item:
                raise ValueError(f"De-Para {depara_id} nao encontrado")

            # Soft delete
            item.ativo = False
            item.atualizado_em = datetime.utcnow()

            db.session.commit()

            logger.info(f"De-Para {depara_id} desativado")

            return True

        except ValueError:
            raise
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao excluir De-Para {depara_id}: {e}")
            raise

    # =========================================================================
    # CONVERSION OPERATIONS
    # =========================================================================

    def converter(
        self,
        cnpj_fornecedor: str,
        cod_produto_fornecedor: str
    ) -> Optional[Dict[str, Any]]:
        """
        Converte codigo de produto do fornecedor para codigo interno.

        Args:
            cnpj_fornecedor: CNPJ do fornecedor
            cod_produto_fornecedor: Codigo do produto no fornecedor

        Returns:
            Dict com:
                - cod_produto_interno: Codigo interno
                - odoo_product_id: ID do produto no Odoo
                - um_fornecedor: UM do fornecedor
                - um_interna: UM interna
                - fator_conversao: Fator de conversao
            Ou None se nao encontrar mapeamento
        """
        try:
            cnpj_limpo = self._limpar_cnpj(cnpj_fornecedor)

            item = ProdutoFornecedorDepara.query.filter_by(
                cnpj_fornecedor=cnpj_limpo,
                cod_produto_fornecedor=cod_produto_fornecedor,
                ativo=True
            ).first()

            if not item:
                logger.debug(
                    f"De-Para nao encontrado: {cnpj_limpo}/{cod_produto_fornecedor}"
                )
                return None

            return {
                'cod_produto_interno': item.cod_produto_interno,
                'nome_produto_interno': item.nome_produto_interno,
                'odoo_product_id': item.odoo_product_id,
                'um_fornecedor': item.um_fornecedor,
                'um_interna': item.um_interna,
                'fator_conversao': float(item.fator_conversao) if item.fator_conversao else 1.0
            }

        except Exception as e:
            logger.error(
                f"Erro ao converter De-Para {cnpj_fornecedor}/{cod_produto_fornecedor}: {e}"
            )
            return None

    def converter_quantidade(
        self,
        quantidade: Decimal,
        fator_conversao: Decimal
    ) -> Decimal:
        """
        Converte quantidade usando fator de conversao.

        Exemplo: 60 ML * 1000 = 60.000 UNITS

        Args:
            quantidade: Quantidade original
            fator_conversao: Fator de conversao

        Returns:
            Quantidade convertida
        """
        return Decimal(str(quantidade)) * Decimal(str(fator_conversao))

    def converter_preco(
        self,
        preco: Decimal,
        fator_conversao: Decimal
    ) -> Decimal:
        """
        Converte preco usando fator de conversao.

        Exemplo: R$ 41,00 por ML / 1000 = R$ 0,041 por UNIT

        Args:
            preco: Preco original (por UM do fornecedor)
            fator_conversao: Fator de conversao

        Returns:
            Preco convertido (por UM interna)
        """
        if fator_conversao == 0:
            return Decimal(str(preco))

        return Decimal(str(preco)) / Decimal(str(fator_conversao))

    def verificar_depara_existe(
        self,
        cnpj_fornecedor: str,
        cod_produto_fornecedor: str
    ) -> bool:
        """
        Verifica se existe De-Para para o fornecedor/produto.

        Args:
            cnpj_fornecedor: CNPJ do fornecedor
            cod_produto_fornecedor: Codigo do produto no fornecedor

        Returns:
            True se existe, False caso contrario
        """
        try:
            cnpj_limpo = self._limpar_cnpj(cnpj_fornecedor)

            existe = ProdutoFornecedorDepara.query.filter_by(
                cnpj_fornecedor=cnpj_limpo,
                cod_produto_fornecedor=cod_produto_fornecedor,
                ativo=True
            ).first()

            return existe is not None

        except Exception as e:
            logger.error(f"Erro ao verificar De-Para: {e}")
            return False

    # =========================================================================
    # ODOO SYNC OPERATIONS
    # =========================================================================

    def sincronizar_para_odoo(self, depara_id: int) -> Dict[str, Any]:
        """
        Sincroniza um De-Para local para o Odoo (product.supplierinfo).

        Args:
            depara_id: ID do De-Para local

        Returns:
            Dict com resultado da sincronizacao
        """
        try:
            item = ProdutoFornecedorDepara.query.get(depara_id)

            if not item:
                raise ValueError(f"De-Para {depara_id} nao encontrado")

            if not item.odoo_product_id:
                raise ValueError(
                    f"De-Para {depara_id} nao tem odoo_product_id. "
                    f"Vincule ao produto Odoo primeiro."
                )

            odoo = get_odoo_connection()

            # Buscar fornecedor no Odoo pelo CNPJ (formatado ou limpo)
            # Primeiro tenta com CNPJ formatado (XX.XXX.XXX/XXXX-XX)
            cnpj_formatado = self._formatar_cnpj(item.cnpj_fornecedor)
            partner_ids = odoo.search(
                'res.partner',
                [('l10n_br_cnpj', '=', cnpj_formatado)]
            )

            # Se nao encontrar, tenta com ILIKE no CNPJ formatado parcial
            if not partner_ids:
                # Extrai apenas a raiz do CNPJ formatado (XX.XXX.XXX)
                cnpj_raiz = cnpj_formatado[:10] if len(cnpj_formatado) >= 10 else cnpj_formatado
                partner_ids = odoo.search(
                    'res.partner',
                    [('l10n_br_cnpj', 'ilike', cnpj_raiz)]
                )

            if not partner_ids:
                raise ValueError(
                    f"Fornecedor com CNPJ {item.cnpj_fornecedor} nao encontrado no Odoo"
                )

            partner_id = partner_ids[0]

            # Verificar se ja existe supplierinfo para este MESMO product_code
            # ESTRATEGIA DE BUSCA (em ordem de prioridade):
            # 1. partner_id + product_code (mais especifico - ignora product_id pois pode ser null)
            # 2. supplierinfo_id salvo localmente (fallback)

            # Busca principal: partner_id + product_code
            # NAO incluir product_id na busca porque no Odoo pode estar null/False
            supplierinfo_ids = odoo.search(
                'product.supplierinfo',
                [
                    ('partner_id', '=', partner_id),
                    ('product_code', '=', item.cod_produto_fornecedor)
                ]
            )

            # Se nao encontrou, verifica se tem supplierinfo_id salvo localmente
            if not supplierinfo_ids and item.odoo_supplierinfo_id:
                # Verificar se o supplierinfo salvo ainda existe e pertence a este De-Para
                existing = odoo.read('product.supplierinfo', [item.odoo_supplierinfo_id],
                                     ['id', 'product_code'])
                if existing and existing[0].get('product_code') == item.cod_produto_fornecedor:
                    supplierinfo_ids = [item.odoo_supplierinfo_id]

            # Dados para criar/atualizar
            supplierinfo_data = {
                'partner_id': partner_id,
                'product_id': item.odoo_product_id,
                'product_code': item.cod_produto_fornecedor,
            }

            # Adicionar fator_un se definido (campo customizado do Odoo BR)
            if item.fator_conversao and float(item.fator_conversao) != 1.0:
                supplierinfo_data['fator_un'] = float(item.fator_conversao)

            # Adicionar descricao do produto do fornecedor se definida
            if item.descricao_produto_fornecedor:
                supplierinfo_data['product_name'] = item.descricao_produto_fornecedor

            if supplierinfo_ids:
                # Atualizar existente
                odoo.write(
                    'product.supplierinfo',
                    [supplierinfo_ids[0]],  # write espera lista de IDs
                    supplierinfo_data
                )
                item.odoo_supplierinfo_id = supplierinfo_ids[0]
                logger.info(
                    f"Supplierinfo {supplierinfo_ids[0]} atualizado para De-Para {depara_id}"
                )
            else:
                # Criar novo
                new_id = odoo.create(
                    'product.supplierinfo',
                    supplierinfo_data
                )
                item.odoo_supplierinfo_id = new_id
                logger.info(
                    f"Supplierinfo {new_id} criado para De-Para {depara_id}"
                )

            # Marcar como sincronizado
            item.sincronizado_odoo = True
            item.atualizado_em = datetime.utcnow()

            db.session.commit()

            return {
                'sucesso': True,
                'depara_id': depara_id,
                'odoo_supplierinfo_id': item.odoo_supplierinfo_id,
                'acao': 'atualizado' if supplierinfo_ids else 'criado'
            }

        except ValueError:
            raise
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao sincronizar De-Para {depara_id} para Odoo: {e}")
            raise

    def importar_do_odoo(
        self,
        cnpj_fornecedor: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Importa mapeamentos do Odoo (product.supplierinfo) para o local.

        Args:
            cnpj_fornecedor: Filtrar por CNPJ (opcional)
            limit: Limite de registros

        Returns:
            Dict com estatisticas da importacao
        """
        try:
            odoo = get_odoo_connection()

            # Montar filtro - Aceita product_id OU product_tmpl_id
            # A maioria dos supplierinfos usa product_tmpl_id (template), não product_id (variante)
            domain = [
                ('product_code', '!=', False),  # Deve ter codigo do fornecedor
                '|',  # OR
                ('product_id', '!=', False),      # Tem variante vinculada
                ('product_tmpl_id', '!=', False)  # Ou tem template vinculado
            ]

            if cnpj_fornecedor:
                cnpj_limpo = self._limpar_cnpj(cnpj_fornecedor)
                # Buscar partner_id pelo CNPJ (primeiro l10n_br_cnpj)
                partner_ids = odoo.search(
                    'res.partner',
                    [('l10n_br_cnpj', 'ilike', cnpj_limpo)]
                )
                if partner_ids:
                    domain.append(('partner_id', 'in', partner_ids))
                else:
                    return {
                        'importados': 0,
                        'atualizados': 0,
                        'erros': 0,
                        'mensagem': f'Fornecedor {cnpj_limpo} nao encontrado no Odoo'
                    }

            # Buscar supplierinfos
            supplierinfo_ids = odoo.search(
                'product.supplierinfo',
                domain,
                limit=limit
            )

            if not supplierinfo_ids:
                return {
                    'importados': 0,
                    'atualizados': 0,
                    'erros': 0,
                    'mensagem': 'Nenhum supplierinfo encontrado no Odoo'
                }

            # Ler dados - incluir product_tmpl_id, product_name e fator_un
            supplierinfos = odoo.read(
                'product.supplierinfo',
                supplierinfo_ids,
                [
                    'id', 'partner_id', 'product_id', 'product_tmpl_id',
                    'product_code', 'product_name', 'product_uom', 'fator_un', 'price'
                ]
            )

            # Buscar CNPJs dos partners
            # IMPORTANTE: No Odoo BR, o CNPJ está no campo l10n_br_cnpj
            partner_ids_list = list(set([s['partner_id'][0] for s in supplierinfos if s.get('partner_id')]))
            partners = {}
            if partner_ids_list:
                partners_data = odoo.read(
                    'res.partner',
                    partner_ids_list,
                    ['id', 'l10n_br_cnpj', 'name']
                )
                partners = {p['id']: p for p in partners_data}

            # Buscar codigos dos produtos (variantes)
            product_ids_list = list(set([s['product_id'][0] for s in supplierinfos if s.get('product_id') and s['product_id']]))
            products = {}
            if product_ids_list:
                products_data = odoo.read(
                    'product.product',
                    product_ids_list,
                    ['id', 'default_code', 'name', 'product_tmpl_id']
                )
                products = {p['id']: p for p in products_data}

            # Buscar templates (para supplierinfos que usam product_tmpl_id)
            tmpl_ids_list = list(set([
                s['product_tmpl_id'][0] for s in supplierinfos
                if s.get('product_tmpl_id') and s['product_tmpl_id'] and (not s.get('product_id') or not s['product_id'])
            ]))
            templates = {}
            if tmpl_ids_list:
                templates_data = odoo.read(
                    'product.template',
                    tmpl_ids_list,
                    ['id', 'default_code', 'name']
                )
                templates = {t['id']: t for t in templates_data}

                # Buscar primeira variante de cada template para obter product_id
                for tmpl_id in tmpl_ids_list:
                    variant_ids = odoo.search(
                        'product.product',
                        [('product_tmpl_id', '=', tmpl_id)],
                        limit=1
                    )
                    if variant_ids:
                        variant_data = odoo.read(
                            'product.product',
                            variant_ids,
                            ['id', 'default_code', 'name']
                        )
                        if variant_data:
                            templates[tmpl_id]['product_id'] = variant_data[0]['id']
                            # Usar default_code da variante se template não tiver
                            if not templates[tmpl_id].get('default_code') and variant_data[0].get('default_code'):
                                templates[tmpl_id]['default_code'] = variant_data[0]['default_code']

            # Importar cada um
            importados = 0
            atualizados = 0
            erros = 0

            for si in supplierinfos:
                try:
                    partner_id = si.get('partner_id', [None, None])[0] if si.get('partner_id') else None
                    product_id = si.get('product_id', [None, None])[0] if si.get('product_id') else None
                    tmpl_id = si.get('product_tmpl_id', [None, None])[0] if si.get('product_tmpl_id') else None

                    if not partner_id:
                        continue

                    # Precisa ter product_id OU product_tmpl_id
                    if not product_id and not tmpl_id:
                        continue

                    partner = partners.get(partner_id, {})

                    # Obter dados do produto (variante ou template)
                    if product_id and product_id in products:
                        product = products[product_id]
                        odoo_product_id = product_id
                    elif tmpl_id and tmpl_id in templates:
                        product = templates[tmpl_id]
                        # Usar product_id da variante se disponível
                        odoo_product_id = product.get('product_id', None)
                    else:
                        continue

                    # Buscar CNPJ: primeiro tenta l10n_br_cnpj (BR)
                    cnpj_raw = partner.get('l10n_br_cnpj') or ''
                    cnpj = self._limpar_cnpj(cnpj_raw) if cnpj_raw else ''
                    if not cnpj:
                        continue

                    # Ignorar CNPJs do grupo interno (não são fornecedores externos)
                    # 18.467.441 = Nacom Goya, 61.724.241 = Grupo relacionado
                    CNPJS_GRUPO_INTERNO = ['18467441', '61724241']
                    cnpj_raiz = cnpj[:8] if len(cnpj) >= 8 else cnpj
                    if cnpj_raiz in CNPJS_GRUPO_INTERNO:
                        continue

                    cod_fornecedor = si.get('product_code', '')
                    cod_interno = product.get('default_code', '')

                    if not cod_fornecedor or not cod_interno:
                        continue

                    # Verificar se ja existe
                    existente = ProdutoFornecedorDepara.query.filter_by(
                        cnpj_fornecedor=cnpj,
                        cod_produto_fornecedor=cod_fornecedor
                    ).first()

                    # Extrair fator_un do Odoo (campo fator_un)
                    fator_odoo = si.get('fator_un') or 1.0
                    if fator_odoo and fator_odoo > 0:
                        fator_conversao = Decimal(str(fator_odoo))
                    else:
                        fator_conversao = Decimal('1.0')

                    # Extrair UM do fornecedor (product_uom é many2one: [id, nome])
                    product_uom = si.get('product_uom')
                    um_fornecedor = None
                    if product_uom and isinstance(product_uom, (list, tuple)) and len(product_uom) >= 2:
                        um_fornecedor = product_uom[1]  # Ex: [182, "PL"] → "PL"
                    elif product_uom and isinstance(product_uom, str):
                        um_fornecedor = product_uom

                    # Nome do produto no fornecedor (product_name do supplierinfo)
                    descricao_fornecedor = si.get('product_name') or ''

                    if existente:
                        # Atualizar
                        existente.cod_produto_interno = cod_interno
                        existente.nome_produto_interno = product.get('name', '')
                        existente.descricao_produto_fornecedor = descricao_fornecedor
                        existente.odoo_product_id = odoo_product_id
                        existente.odoo_supplierinfo_id = si['id']
                        existente.fator_conversao = fator_conversao
                        existente.um_fornecedor = um_fornecedor
                        existente.sincronizado_odoo = True
                        existente.atualizado_em = datetime.utcnow()
                        atualizados += 1
                    else:
                        # Criar
                        novo = ProdutoFornecedorDepara(
                            cnpj_fornecedor=cnpj,
                            razao_fornecedor=partner.get('name', ''),
                            cod_produto_fornecedor=cod_fornecedor,
                            descricao_produto_fornecedor=descricao_fornecedor,
                            cod_produto_interno=cod_interno,
                            nome_produto_interno=product.get('name', ''),
                            odoo_product_id=odoo_product_id,
                            odoo_supplierinfo_id=si['id'],
                            um_fornecedor=um_fornecedor,
                            fator_conversao=fator_conversao,
                            sincronizado_odoo=True,
                            ativo=True,
                            criado_em=datetime.utcnow()
                        )
                        db.session.add(novo)
                        importados += 1

                except Exception as e:
                    logger.warning(f"Erro ao importar supplierinfo {si.get('id')}: {e}")
                    erros += 1

            db.session.commit()

            logger.info(
                f"Importacao Odoo concluida: {importados} importados, "
                f"{atualizados} atualizados, {erros} erros"
            )

            return {
                'importados': importados,
                'atualizados': atualizados,
                'erros': erros,
                'total_processados': importados + atualizados + erros
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao importar do Odoo: {e}")
            raise

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _limpar_cnpj(self, cnpj: str) -> str:
        """Remove pontuacao do CNPJ/CPF."""
        if not cnpj:
            return ''
        return ''.join(c for c in str(cnpj) if c.isdigit())

    def _formatar_cnpj(self, cnpj: str) -> str:
        """
        Formata CNPJ para o padrao XX.XXX.XXX/XXXX-XX.
        Necessario para buscar no Odoo que armazena formatado.
        """
        cnpj_limpo = self._limpar_cnpj(cnpj)
        if len(cnpj_limpo) != 14:
            return cnpj_limpo  # Retorna como esta se nao for CNPJ valido
        return f'{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}'

    def _to_dict(self, item: ProdutoFornecedorDepara) -> Dict[str, Any]:
        """Converte model para dict."""
        if not item:
            return {}

        return {
            'id': item.id,
            'cnpj_fornecedor': item.cnpj_fornecedor,
            'razao_fornecedor': item.razao_fornecedor,
            'cod_produto_fornecedor': item.cod_produto_fornecedor,
            'descricao_produto_fornecedor': item.descricao_produto_fornecedor,
            'cod_produto_interno': item.cod_produto_interno,
            'nome_produto_interno': item.nome_produto_interno,
            'odoo_product_id': item.odoo_product_id,
            'um_fornecedor': item.um_fornecedor,
            'um_interna': item.um_interna,
            'fator_conversao': float(item.fator_conversao) if item.fator_conversao else 1.0,
            'ativo': item.ativo,
            'sincronizado_odoo': item.sincronizado_odoo,
            'odoo_supplierinfo_id': item.odoo_supplierinfo_id,
            'criado_por': item.criado_por,
            'criado_em': item.criado_em.isoformat() if item.criado_em else None,
            'atualizado_por': item.atualizado_por,
            'atualizado_em': item.atualizado_em.isoformat() if item.atualizado_em else None
        }

    def buscar_produto_odoo(
        self,
        cod_produto_interno: str,
        busca_flexivel: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Busca produto no Odoo pelo codigo interno (default_code).

        Estrategia de busca:
        1. Busca EXATA pelo default_code
        2. Se nao achar e busca_flexivel=True:
           - Busca ILIKE (case insensitive, parcial)
           - Busca em product.template se nao achar em product.product

        Args:
            cod_produto_interno: Codigo interno do produto
            busca_flexivel: Se True, faz busca parcial se exata falhar

        Returns:
            Dict com id, default_code, name ou None
        """
        try:
            odoo = get_odoo_connection()
            cod_limpo = cod_produto_interno.strip()

            # 1. Busca EXATA em product.product
            product_ids = odoo.search(
                'product.product',
                [('default_code', '=', cod_limpo)],
                limit=1
            )

            if product_ids:
                products = odoo.read(
                    'product.product',
                    product_ids,
                    ['id', 'default_code', 'name', 'product_tmpl_id']
                )
                if products:
                    return products[0]

            # Se busca flexivel esta desabilitada, para aqui
            if not busca_flexivel:
                return None

            # 2. Busca ILIKE em product.product (parcial, case insensitive)
            product_ids = odoo.search(
                'product.product',
                [('default_code', 'ilike', cod_limpo)],
                limit=5
            )

            if product_ids:
                products = odoo.read(
                    'product.product',
                    product_ids,
                    ['id', 'default_code', 'name', 'product_tmpl_id']
                )
                if products:
                    # Se encontrou exatamente 1, retorna
                    if len(products) == 1:
                        return products[0]
                    # Se encontrou varios, tenta match mais proximo
                    for p in products:
                        if p.get('default_code', '').upper() == cod_limpo.upper():
                            return p
                    # Retorna o primeiro se nenhum match exato
                    return products[0]

            # 3. Busca em product.template
            tmpl_ids = odoo.search(
                'product.template',
                [('default_code', 'ilike', cod_limpo)],
                limit=1
            )

            if tmpl_ids:
                templates = odoo.read(
                    'product.template',
                    tmpl_ids,
                    ['id', 'default_code', 'name']
                )
                if templates:
                    tmpl = templates[0]
                    # Buscar variante (product.product) do template
                    variant_ids = odoo.search(
                        'product.product',
                        [('product_tmpl_id', '=', tmpl['id'])],
                        limit=1
                    )
                    if variant_ids:
                        variants = odoo.read(
                            'product.product',
                            variant_ids,
                            ['id', 'default_code', 'name']
                        )
                        if variants:
                            return variants[0]
                    # Se nao tem variante, retorna o template com id negativo
                    # para indicar que e um template
                    return {
                        'id': tmpl['id'],
                        'default_code': tmpl.get('default_code'),
                        'name': tmpl.get('name'),
                        'is_template': True
                    }

            return None

        except Exception as e:
            logger.error(f"Erro ao buscar produto Odoo {cod_produto_interno}: {e}")
            return None

    def sugerir_fator_conversao(self, um_fornecedor: str) -> Decimal:
        """
        Sugere fator de conversao com base na UM do fornecedor.

        Args:
            um_fornecedor: Unidade de medida do fornecedor

        Returns:
            Fator de conversao sugerido
        """
        if not um_fornecedor:
            return Decimal('1.0000')

        um_upper = um_fornecedor.upper().strip()

        if um_upper in UOMS_MILHAR:
            return FATOR_MILHAR

        # Outras UMs conhecidas podem ser adicionadas aqui
        # Por enquanto, retorna 1 como padrao
        return Decimal('1.0000')

    # =========================================================================
    # IMPORT EXCEL OPERATIONS
    # =========================================================================

    def importar_lote_excel(
        self,
        dados: list,
        usuario: str,
        auto_sync_odoo: bool = True
    ) -> Dict[str, Any]:
        """
        Importa multiplos De-Para de uma lista de dicionarios (vindo do Excel).

        Para cada item:
        1. Valida campos obrigatorios
        2. Busca produto no Odoo (default_code) para obter odoo_product_id
        3. Cria ou atualiza De-Para local
        4. Sincroniza com Odoo (product.supplierinfo)

        Args:
            dados: Lista de dicts com campos do De-Para
            usuario: Nome do usuario que esta importando
            auto_sync_odoo: Se True, sincroniza automaticamente com Odoo

        Returns:
            Dict com estatisticas:
            - total_processados: numero total de linhas processadas
            - criados: numero de De-Para criados
            - atualizados: numero de De-Para atualizados
            - erros: lista com detalhes dos erros
        """
        resultado = {
            'total_processados': 0,
            'criados': 0,
            'atualizados': 0,
            'sincronizados': 0,
            'erros': []
        }

        campos_obrigatorios = ['cnpj_fornecedor', 'cod_produto_fornecedor', 'cod_produto_interno']

        for idx, linha in enumerate(dados, start=1):
            resultado['total_processados'] += 1

            try:
                # Validar campos obrigatorios
                campos_faltando = [c for c in campos_obrigatorios if not linha.get(c)]
                if campos_faltando:
                    resultado['erros'].append({
                        'linha': idx,
                        'erro': f"Campos obrigatorios faltando: {', '.join(campos_faltando)}",
                        'dados': linha
                    })
                    continue

                cnpj = self._limpar_cnpj(str(linha['cnpj_fornecedor']))
                cod_fornecedor = str(linha['cod_produto_fornecedor']).strip()
                cod_interno = str(linha['cod_produto_interno']).strip()

                # Buscar produto no Odoo para obter odoo_product_id
                produto_odoo = self.buscar_produto_odoo(cod_interno, busca_flexivel=True)
                odoo_product_id = None
                nome_produto_interno = None

                if produto_odoo:
                    odoo_product_id = produto_odoo.get('id')
                    nome_produto_interno = produto_odoo.get('name')
                else:
                    resultado['erros'].append({
                        'linha': idx,
                        'erro': f"Produto interno '{cod_interno}' nao encontrado no Odoo",
                        'dados': linha,
                        'warning': True  # Nao impede criacao local
                    })

                # Extrair campos opcionais
                descricao_fornecedor = linha.get('descricao_produto_fornecedor', '') or ''
                um_fornecedor = linha.get('um_fornecedor', '') or None
                fator_conversao = linha.get('fator_conversao')

                # Converter fator para Decimal
                if fator_conversao:
                    try:
                        fator_conversao = Decimal(str(fator_conversao))
                    except Exception as e:
                        logger.error(f"Erro ao converter fator de conversao: {e}")
                        fator_conversao = Decimal('1.0')
                else:
                    fator_conversao = Decimal('1.0')

                # Verificar se ja existe
                existente = ProdutoFornecedorDepara.query.filter_by(
                    cnpj_fornecedor=cnpj,
                    cod_produto_fornecedor=cod_fornecedor
                ).first()

                if existente:
                    # Atualizar existente
                    existente.cod_produto_interno = cod_interno
                    existente.nome_produto_interno = nome_produto_interno or existente.nome_produto_interno
                    existente.descricao_produto_fornecedor = descricao_fornecedor or existente.descricao_produto_fornecedor
                    existente.um_fornecedor = um_fornecedor or existente.um_fornecedor
                    existente.fator_conversao = fator_conversao
                    existente.odoo_product_id = odoo_product_id or existente.odoo_product_id
                    existente.sincronizado_odoo = False  # Marca para re-sync
                    existente.atualizado_por = usuario
                    existente.atualizado_em = datetime.utcnow()
                    existente.ativo = True  # Reativa se estava inativo

                    db.session.flush()
                    resultado['atualizados'] += 1
                    depara_id = existente.id
                else:
                    # Criar novo
                    novo = ProdutoFornecedorDepara(
                        cnpj_fornecedor=cnpj,
                        razao_fornecedor=linha.get('razao_fornecedor', ''),
                        cod_produto_fornecedor=cod_fornecedor,
                        descricao_produto_fornecedor=descricao_fornecedor,
                        cod_produto_interno=cod_interno,
                        nome_produto_interno=nome_produto_interno,
                        odoo_product_id=odoo_product_id,
                        um_fornecedor=um_fornecedor,
                        um_interna='UNITS',
                        fator_conversao=fator_conversao,
                        ativo=True,
                        sincronizado_odoo=False,
                        criado_por=usuario,
                        criado_em=datetime.utcnow()
                    )
                    db.session.add(novo)
                    db.session.flush()
                    resultado['criados'] += 1
                    depara_id = novo.id

                # Sincronizar com Odoo se solicitado e se tiver odoo_product_id
                if auto_sync_odoo and odoo_product_id:
                    try:
                        self.sincronizar_para_odoo(depara_id)
                        resultado['sincronizados'] += 1
                    except Exception as sync_error:
                        resultado['erros'].append({
                            'linha': idx,
                            'erro': f"Sync Odoo falhou: {str(sync_error)}",
                            'dados': linha,
                            'warning': True,
                            'depara_id': depara_id
                        })

            except Exception as e:
                db.session.rollback()
                resultado['erros'].append({
                    'linha': idx,
                    'erro': str(e),
                    'dados': linha
                })
                logger.error(f"Erro ao importar linha {idx}: {e}")

        # Commit final
        try:
            db.session.commit()
            logger.info(
                f"Importacao Excel concluida: {resultado['criados']} criados, "
                f"{resultado['atualizados']} atualizados, {len(resultado['erros'])} erros"
            )
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao commitar importacao: {e}")
            raise

        return resultado
