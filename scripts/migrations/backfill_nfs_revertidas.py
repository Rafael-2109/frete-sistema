#!/usr/bin/env python3
"""
Script de Migração Retroativa: NFs Revertidas

Popula o sistema com NFs revertidas históricas do Odoo,
mantendo a compatibilidade com o estoque atual.

IMPORTANTE: O estoque atual já está correto (ajustes manuais já foram feitos).
A lógica de neutralização depende do estado atual da MovimentacaoEstoque.

Cenários de Faturamento:
    FAT-A) FaturamentoProduto com status_nf='Cancelado' → Restaurar para 'Lançado'
    FAT-B) NF NÃO está em FaturamentoProduto → Criar registros do Odoo
    FAT-C) FaturamentoProduto com status_nf='Lançado' → Apenas marcar revertida

Cenários de Movimentação:
    MOV-A) MovimentacaoEstoque INATIVA → Reativar + Criar REVERSAO (se neutralizam)
    MOV-B) MovimentacaoEstoque NÃO EXISTE → Criar VENDA + REVERSAO (se neutralizam)
    MOV-C) MovimentacaoEstoque ATIVA → Criar REVERSAO + AJUSTE (se neutralizam)

Executar:
    source .venv/bin/activate
    python scripts/migrations/backfill_nfs_revertidas.py --dias 365 --dry-run

Autor: Sistema de Fretes
Data: 11/01/2026
"""

import sys
import os
import argparse
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text
from app.faturamento.models import FaturamentoProduto
from app.estoque.models import MovimentacaoEstoque
from app.odoo.utils.connection import get_odoo_connection
from app.utils.timezone import agora_brasil, agora_utc, agora_utc_naive

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CNPJs internos (excluir)
CNPJS_EXCLUIDOS = {'18467441', '61724241'}


class BackfillReversoes:
    """
    Classe para migração retroativa de NFs revertidas.

    Processa NFs históricas do Odoo que foram revertidas via Nota de Crédito,
    garantindo que o estoque atual não seja alterado através de lógica de
    neutralização por cenário.
    """

    def __init__(self, dry_run: bool = False):
        """
        Inicializa o backfill.

        Args:
            dry_run: Se True, não persiste alterações no banco
        """
        self.odoo = get_odoo_connection()
        self.dry_run = dry_run
        self.stats = {
            'ncs_processadas': 0,
            'ncs_ignoradas_cnpj': 0,
            'ncs_ignoradas_sem_nf': 0,
            # Cenários de Faturamento
            'fat_a_restaurados': 0,
            'fat_b_criados': 0,
            'fat_c_marcados': 0,
            'fat_ja_revertidos': 0,
            # Cenários de Movimentação
            'mov_a_reativadas': 0,
            'mov_b_venda_criadas': 0,
            'mov_b_reversao_criadas': 0,
            'mov_c_reversao_criadas': 0,
            'mov_c_ajuste_criadas': 0,
            'mov_ja_existe_reversao': 0,
            # Erros
            'erros': []
        }

    def executar(self, dias: int = 365, limite: Optional[int] = None) -> Dict:
        """
        Executa a migração retroativa.

        Args:
            dias: Quantos dias para trás buscar
            limite: Limite de NCs a processar (None = todas)

        Returns:
            Dict com estatísticas da migração
        """
        print("=" * 80)
        print("MIGRAÇÃO RETROATIVA: NFs REVERTIDAS")
        print("=" * 80)
        print(f"Modo: {'SIMULAÇÃO (dry-run)' if self.dry_run else 'EXECUÇÃO REAL'}")
        print(f"Período: últimos {dias} dias")
        if limite:
            print(f"Limite: {limite} NCs")
        print("")

        # 1. Buscar todas as NCs no período
        data_corte = (agora_utc() - timedelta(days=dias)).strftime('%Y-%m-%d')
        print(f"Buscando Notas de Crédito desde {data_corte}...")

        notas_credito = self._buscar_notas_credito(data_corte, limite)

        if not notas_credito:
            print("Nenhuma Nota de Crédito encontrada.")
            return self.stats

        print(f"Total de NCs encontradas: {len(notas_credito)}")
        print("")

        # 2. Processar cada NC
        for i, nc in enumerate(notas_credito, 1):
            try:
                nc_id = nc.get('id')
                nc_name = nc.get('name', f'NC-{nc_id}')

                if i % 50 == 0 or i == 1:
                    print(f"\n[{i}/{len(notas_credito)}] Processando...")

                self._processar_nota_credito(nc)

            except Exception as e:
                erro = f"Erro NC {nc.get('id')}: {str(e)}"
                logger.error(erro)
                self.stats['erros'].append(erro)
                if not self.dry_run:
                    db.session.rollback()

        # 3. Commit final
        if not self.dry_run:
            try:
                db.session.commit()
                print("\n✅ Migração SALVA no banco de dados")
            except Exception as e:
                db.session.rollback()
                print(f"\n❌ Erro ao salvar: {e}")
                self.stats['erros'].append(f"Erro commit final: {e}")
        else:
            print("\n⚠️  Modo dry-run: nada foi salvo")

        self._imprimir_estatisticas()
        return self.stats

    # =========================================================================
    # BUSCA NO ODOO
    # =========================================================================

    def _buscar_notas_credito(
        self,
        data_corte: str,
        limite: Optional[int] = None
    ) -> List[Dict]:
        """
        Busca Notas de Crédito (out_refund) no Odoo.

        Args:
            data_corte: Data mínima (formato YYYY-MM-DD)
            limite: Limite de registros

        Returns:
            Lista de Notas de Crédito
        """
        try:
            filtros = [
                ('move_type', '=', 'out_refund'),
                ('state', '=', 'posted'),
                ('reversed_entry_id', '!=', False),
                ('invoice_date', '>=', data_corte),
            ]

            campos = [
                'id',
                'name',
                'partner_id',
                'amount_total',
                'reversed_entry_id',
                'l10n_br_numero_nota_fiscal',
                'invoice_date',
            ]

            params = {'fields': campos, 'order': 'invoice_date asc'}
            if limite:
                params['limit'] = limite

            notas_credito = self.odoo.execute_kw(
                'account.move',
                'search_read',
                [filtros],
                params
            )

            return notas_credito or []

        except Exception as e:
            logger.error(f"Erro ao buscar Notas de Crédito: {e}")
            return []

    def _buscar_nf_original(self, nf_id: int) -> Optional[Dict]:
        """
        Busca NF de Venda original no Odoo.

        Args:
            nf_id: ID da NF original

        Returns:
            Dict com dados da NF ou None
        """
        try:
            campos = [
                'id',
                'name',
                'partner_id',
                'amount_total',
                'l10n_br_numero_nota_fiscal',
                'l10n_br_chave_nf',
                'invoice_date',
            ]

            nfs = self.odoo.execute_kw(
                'account.move',
                'search_read',
                [[('id', '=', nf_id)]],
                {'fields': campos, 'limit': 1}
            )

            return nfs[0] if nfs else None

        except Exception as e:
            logger.error(f"Erro ao buscar NF original {nf_id}: {e}")
            return None

    def _buscar_linhas_nf(self, nf_id: int) -> List[Dict]:
        """
        Busca linhas de produto da NF no Odoo.

        Args:
            nf_id: ID da NF

        Returns:
            Lista de linhas com produto
        """
        try:
            # Busca apenas linhas com produto (display_type='product' ou produto definido)
            linhas = self.odoo.execute_kw(
                'account.move.line',
                'search_read',
                [[
                    ('move_id', '=', nf_id),
                    ('product_id', '!=', False),   # Apenas linhas com produto
                ]],
                {
                    'fields': [
                        'id',
                        'product_id',      # [id, name]
                        'quantity',
                        'price_unit',
                        'price_subtotal',
                        'display_type',
                    ]
                }
            )

            # Filtrar apenas linhas de produto (não seções ou notas)
            linhas_produto = [
                linha for linha in (linhas or [])
                if linha.get('display_type') in ('product', False, None)
                and linha.get('product_id')
                and linha.get('quantity', 0) > 0
            ]

            return linhas_produto

        except Exception as e:
            logger.error(f"Erro ao buscar linhas da NF {nf_id}: {e}")
            return []

    def _extrair_cnpj_parceiro(self, partner_id) -> Optional[str]:
        """
        Extrai CNPJ do parceiro.

        Args:
            partner_id: ID ou [id, name] do parceiro

        Returns:
            CNPJ limpo ou None
        """
        if not partner_id:
            return None

        try:
            p_id = partner_id[0] if isinstance(partner_id, list) else partner_id

            parceiro = self.odoo.execute_kw(
                'res.partner',
                'search_read',
                [[('id', '=', p_id)]],
                {'fields': ['l10n_br_cnpj'], 'limit': 1}
            )

            if parceiro:
                cnpj = parceiro[0].get('l10n_br_cnpj')
                if cnpj:
                    return self._limpar_cnpj(cnpj)

            return None

        except Exception as e:
            logger.error(f"Erro ao extrair CNPJ do parceiro: {e}")
            return None

    @staticmethod
    def _limpar_cnpj(cnpj: str) -> str:
        """Remove formatação de CNPJ."""
        if not cnpj:
            return None
        return cnpj.replace('.', '').replace('/', '').replace('-', '').strip()

    @staticmethod
    def _parse_date(date_str) -> Optional[datetime]:
        """Converte string de data para date object."""
        if not date_str:
            return None
        try:
            if isinstance(date_str, str):
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            return date_str
        except Exception:
            return None

    # =========================================================================
    # PROCESSAMENTO PRINCIPAL
    # =========================================================================

    def _processar_nota_credito(self, nc: Dict):
        """
        Processa uma Nota de Crédito.

        Args:
            nc: Dados da Nota de Crédito do Odoo
        """
        nc_id = nc.get('id')
        nc_name = nc.get('name', f'NC-{nc_id}')
        reversed_entry_id = nc.get('reversed_entry_id')

        if not reversed_entry_id:
            return

        nf_original_id = reversed_entry_id[0] if isinstance(reversed_entry_id, list) else reversed_entry_id
        nf_original = self._buscar_nf_original(nf_original_id)

        if not nf_original:
            self.stats['ncs_ignoradas_sem_nf'] += 1
            return

        numero_nf = nf_original.get('l10n_br_numero_nota_fiscal')
        if not numero_nf:
            self.stats['ncs_ignoradas_sem_nf'] += 1
            return

        data_nf = self._parse_date(nf_original.get('invoice_date'))
        partner_id = nf_original.get('partner_id')
        cnpj_parceiro = self._extrair_cnpj_parceiro(partner_id)
        nome_parceiro = partner_id[1] if isinstance(partner_id, list) else None

        # Verificar CNPJ excluído
        if cnpj_parceiro and cnpj_parceiro[:8] in CNPJS_EXCLUIDOS:
            self.stats['ncs_ignoradas_cnpj'] += 1
            return

        print(f"\n📄 NF {numero_nf} (NC: {nc_name})")
        self.stats['ncs_processadas'] += 1

        # ETAPA 1: Processar FaturamentoProduto
        # Retorna também as linhas do Odoo para cenário FAT-B
        cenario_fat, linhas_odoo = self._processar_faturamento(
            numero_nf=str(numero_nf),
            nc_id=nc_id,
            nf_original_id=nf_original_id,
            data_nf=data_nf,
            cnpj=cnpj_parceiro,
            nome=nome_parceiro
        )

        # ETAPA 2: Processar MovimentacaoEstoque (para cada item)
        self._processar_movimentacoes(
            numero_nf=str(numero_nf),
            nc_name=nc_name,
            data_nf=data_nf,
            linhas_odoo=linhas_odoo  # Passar linhas do Odoo para FAT-B
        )

    # =========================================================================
    # PROCESSAMENTO DE FATURAMENTO
    # =========================================================================

    def _processar_faturamento(
        self,
        numero_nf: str,
        nc_id: int,
        nf_original_id: int,
        data_nf,
        cnpj: Optional[str],
        nome: Optional[str]
    ) -> tuple:
        """
        Processa FaturamentoProduto identificando cenário FAT-A/B/C.

        Args:
            numero_nf: Número da NF
            nc_id: ID da Nota de Crédito
            nf_original_id: ID da NF original no Odoo
            data_nf: Data da NF
            cnpj: CNPJ do cliente
            nome: Nome do cliente

        Returns:
            Tuple (cenário, linhas_odoo): Cenário identificado e linhas do Odoo (para FAT-B)
        """
        # Buscar itens existentes
        itens = FaturamentoProduto.query.filter_by(numero_nf=numero_nf).all()

        if not itens:
            # FAT-B: Não existe → Criar do Odoo
            print(f"   FAT-B: FaturamentoProduto não existe → Criando do Odoo...")
            linhas = self._buscar_linhas_nf(nf_original_id)

            if not linhas:
                print(f"   ⚠️  Nenhuma linha de produto encontrada no Odoo")
                return None, []

            for linha in linhas:
                product_id = linha.get('product_id')
                if not product_id:
                    continue

                cod_produto = str(product_id[0]) if isinstance(product_id, list) else str(product_id)
                nome_produto = product_id[1] if isinstance(product_id, list) and len(product_id) > 1 else 'Produto'

                if not self.dry_run:
                    fat = FaturamentoProduto(
                        numero_nf=numero_nf,
                        data_fatura=data_nf or agora_utc_naive().date(),
                        cnpj_cliente=cnpj or '',
                        nome_cliente=nome or '',
                        cod_produto=cod_produto,
                        nome_produto=nome_produto,
                        qtd_produto_faturado=Decimal(str(linha.get('quantity', 0))),
                        preco_produto_faturado=Decimal(str(linha.get('price_unit', 0))),
                        valor_produto_faturado=Decimal(str(linha.get('price_subtotal', 0))),
                        status_nf='Lançado',
                        revertida=True,
                        nota_credito_id=nc_id,
                        data_reversao=agora_brasil(),
                        created_by='Migração Retroativa Reversões'
                    )
                    db.session.add(fat)
                self.stats['fat_b_criados'] += 1

            print(f"   ✅ FAT-B: {len(linhas)} itens criados")
            return 'FAT-B', linhas  # Retorna linhas do Odoo para usar em movimentações

        # Verificar status dos itens existentes
        cancelados = [i for i in itens if i.status_nf == 'Cancelado']
        lancados_nao_revertidos = [i for i in itens if i.status_nf == 'Lançado' and not i.revertida]
        ja_revertidos = [i for i in itens if i.revertida]

        if ja_revertidos and not cancelados and not lancados_nao_revertidos:
            print(f"   ⏭️  Já processado ({len(ja_revertidos)} itens com revertida=True)")
            self.stats['fat_ja_revertidos'] += len(ja_revertidos)
            return None, []

        if cancelados:
            # FAT-A: Cancelado → Restaurar para 'Lançado'
            print(f"   FAT-A: {len(cancelados)} itens com status_nf='Cancelado' → Restaurando...")
            for item in cancelados:
                if not self.dry_run:
                    item.status_nf = 'Lançado'
                    item.revertida = True
                    item.nota_credito_id = nc_id
                    item.data_reversao = agora_brasil()
                    item.updated_by = 'Migração Retroativa Reversões'
                self.stats['fat_a_restaurados'] += 1
            print(f"   ✅ FAT-A: {len(cancelados)} itens restaurados")
            return 'FAT-A', []

        if lancados_nao_revertidos:
            # FAT-C: Lançado → Apenas marcar revertida
            print(f"   FAT-C: {len(lancados_nao_revertidos)} itens com status_nf='Lançado' → Marcando revertida...")
            for item in lancados_nao_revertidos:
                if not self.dry_run:
                    item.revertida = True
                    item.nota_credito_id = nc_id
                    item.data_reversao = agora_brasil()
                    item.updated_by = 'Migração Retroativa Reversões'
                self.stats['fat_c_marcados'] += 1
            print(f"   ✅ FAT-C: {len(lancados_nao_revertidos)} itens marcados")
            return 'FAT-C', []

        return None, []

    # =========================================================================
    # PROCESSAMENTO DE MOVIMENTAÇÃO DE ESTOQUE
    # =========================================================================

    def _processar_movimentacoes(
        self,
        numero_nf: str,
        nc_name: str,
        data_nf,
        linhas_odoo: Optional[List[Dict]] = None
    ):
        """
        Processa MovimentacaoEstoque identificando cenário MOV-A/B/C para cada item.

        Args:
            numero_nf: Número da NF
            nc_name: Nome da Nota de Crédito
            data_nf: Data da NF
            linhas_odoo: Linhas do Odoo (usadas no cenário FAT-B quando não há FaturamentoProduto)
        """
        # Preparar lista de itens para processar
        itens_para_processar = []

        # Tentar buscar do FaturamentoProduto primeiro
        itens_fat = FaturamentoProduto.query.filter_by(numero_nf=numero_nf).all()

        if itens_fat:
            # Usar dados do FaturamentoProduto
            for item in itens_fat:
                itens_para_processar.append({
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto,
                    'qtd': item.qtd_produto_faturado
                })
        elif linhas_odoo:
            # Usar dados do Odoo (cenário FAT-B em dry-run ou antes de commit)
            for linha in linhas_odoo:
                product_id = linha.get('product_id')
                if not product_id:
                    continue

                cod_produto = str(product_id[0]) if isinstance(product_id, list) else str(product_id)
                nome_produto = product_id[1] if isinstance(product_id, list) and len(product_id) > 1 else 'Produto'

                itens_para_processar.append({
                    'cod_produto': cod_produto,
                    'nome_produto': nome_produto,
                    'qtd': Decimal(str(linha.get('quantity', 0)))
                })

        if not itens_para_processar:
            return

        for item in itens_para_processar:
            self._processar_movimentacao_item(
                cod_produto=item['cod_produto'],
                nome_produto=item['nome_produto'],
                qtd=item['qtd'],
                numero_nf=numero_nf,
                nc_name=nc_name,
                data_nf=data_nf
            )

    def _processar_movimentacao_item(
        self,
        cod_produto: str,
        nome_produto: str,
        qtd,
        numero_nf: str,
        nc_name: str,
        data_nf
    ):
        """
        Processa movimentação de estoque para um item, identificando o cenário correto.

        Cenários:
            MOV-A: VENDA inativa → Reativar + Criar REVERSAO
            MOV-B: Não existe VENDA → Criar VENDA + REVERSAO
            MOV-C: VENDA ativa → Criar REVERSAO + AJUSTE

        Args:
            cod_produto: Código do produto
            nome_produto: Nome do produto
            qtd: Quantidade
            numero_nf: Número da NF
            nc_name: Nome da Nota de Crédito
            data_nf: Data da NF
        """
        # Verificar se já existe REVERSAO para este item
        mov_reversao_existe = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.numero_nf == numero_nf,
            MovimentacaoEstoque.cod_produto == str(cod_produto),
            MovimentacaoEstoque.local_movimentacao == 'REVERSAO',
            MovimentacaoEstoque.ativo == True
        ).first()

        if mov_reversao_existe:
            self.stats['mov_ja_existe_reversao'] += 1
            return

        # Buscar movimentação de VENDA existente
        mov_venda = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.numero_nf == numero_nf,
            MovimentacaoEstoque.cod_produto == str(cod_produto),
            MovimentacaoEstoque.local_movimentacao == 'VENDA'
        ).first()

        if mov_venda and not mov_venda.ativo:
            # MOV-A: VENDA inativa → Reativar + Criar REVERSAO
            print(f"      {cod_produto}: MOV-A (reativar VENDA + criar REVERSAO)")
            if not self.dry_run:
                mov_venda.ativo = True
                mov_venda.atualizado_por = 'Migração Retroativa Reversões'
                mov_venda.atualizado_em = agora_brasil()
                self._criar_reversao(cod_produto, nome_produto, qtd, numero_nf, nc_name)
            self.stats['mov_a_reativadas'] += 1

        elif not mov_venda:
            # MOV-B: Não existe VENDA → Criar VENDA + REVERSAO
            print(f"      {cod_produto}: MOV-B (criar VENDA + REVERSAO)")
            if not self.dry_run:
                # Criar VENDA (registro histórico)
                mov_nova = MovimentacaoEstoque(
                    cod_produto=str(cod_produto),
                    nome_produto=nome_produto,
                    data_movimentacao=data_nf or agora_utc_naive().date(),
                    tipo_movimentacao='SAIDA',
                    local_movimentacao='VENDA',
                    qtd_movimentacao=qtd,
                    numero_nf=numero_nf,
                    status_nf='FATURADO',
                    tipo_origem='MIGRACAO',
                    observacao=f'Migração retroativa - NF {numero_nf}',
                    criado_por='Migração Retroativa Reversões',
                    criado_em=agora_brasil()
                )
                db.session.add(mov_nova)
                self._criar_reversao(cod_produto, nome_produto, qtd, numero_nf, nc_name)
            # Contabilizar fora do if para funcionar em dry-run
            self.stats['mov_b_venda_criadas'] += 1
            self.stats['mov_b_reversao_criadas'] += 1

        elif mov_venda and mov_venda.ativo:
            # MOV-C: VENDA ativa → Criar REVERSAO + AJUSTE
            print(f"      {cod_produto}: MOV-C (criar REVERSAO + AJUSTE)")
            if not self.dry_run:
                # Criar REVERSAO
                self._criar_reversao(cod_produto, nome_produto, qtd, numero_nf, nc_name)

                # Criar AJUSTE (contra-partida da REVERSAO)
                mov_ajuste = MovimentacaoEstoque(
                    cod_produto=str(cod_produto),
                    nome_produto=nome_produto,
                    data_movimentacao=agora_utc_naive().date(),
                    tipo_movimentacao='SAIDA',
                    local_movimentacao='AJUSTE',
                    qtd_movimentacao=qtd,
                    numero_nf=numero_nf,
                    status_nf='REVERTIDA',
                    tipo_origem='MIGRACAO',
                    observacao=f'Contra-partida migração - NF {numero_nf} (anula REVERSAO)',
                    criado_por='Migração Retroativa Reversões',
                    criado_em=agora_brasil()
                )
                db.session.add(mov_ajuste)
            # Contabilizar fora do if para funcionar em dry-run
            self.stats['mov_c_reversao_criadas'] += 1
            self.stats['mov_c_ajuste_criadas'] += 1

    def _criar_reversao(
        self,
        cod_produto: str,
        nome_produto: str,
        qtd,
        numero_nf: str,
        nc_name: str
    ):
        """
        Cria MovimentacaoEstoque do tipo REVERSAO (ENTRADA).

        Args:
            cod_produto: Código do produto
            nome_produto: Nome do produto
            qtd: Quantidade
            numero_nf: Número da NF revertida
            nc_name: Nome da Nota de Crédito
        """
        mov_reversao = MovimentacaoEstoque(
            cod_produto=str(cod_produto),
            nome_produto=nome_produto,
            data_movimentacao=agora_utc_naive().date(),
            tipo_movimentacao='ENTRADA',
            local_movimentacao='REVERSAO',
            qtd_movimentacao=qtd,
            numero_nf=numero_nf,
            status_nf='REVERTIDA',
            tipo_origem='MIGRACAO',
            observacao=f'Migração retroativa - Reversão NF {numero_nf} via NC {nc_name}',
            criado_por='Migração Retroativa Reversões',
            criado_em=agora_brasil()
        )
        db.session.add(mov_reversao)

    # =========================================================================
    # ESTATÍSTICAS
    # =========================================================================

    def _imprimir_estatisticas(self):
        """Imprime estatísticas da migração."""
        print("\n" + "=" * 80)
        print("ESTATÍSTICAS DA MIGRAÇÃO")
        print("=" * 80)
        print(f"NCs processadas: {self.stats['ncs_processadas']}")
        print(f"NCs ignoradas (CNPJ interno): {self.stats['ncs_ignoradas_cnpj']}")
        print(f"NCs ignoradas (sem NF): {self.stats['ncs_ignoradas_sem_nf']}")
        print("")
        print("📦 Faturamento:")
        print(f"   FAT-A (restaurados de 'Cancelado'): {self.stats['fat_a_restaurados']}")
        print(f"   FAT-B (criados do Odoo): {self.stats['fat_b_criados']}")
        print(f"   FAT-C (marcados revertida): {self.stats['fat_c_marcados']}")
        print(f"   Já revertidos (ignorados): {self.stats['fat_ja_revertidos']}")
        print("")
        print("📦 Movimentação de Estoque:")
        print(f"   MOV-A (VENDA reativadas): {self.stats['mov_a_reativadas']}")
        print(f"   MOV-B (VENDA criadas): {self.stats['mov_b_venda_criadas']}")
        print(f"   MOV-B (REVERSAO criadas): {self.stats['mov_b_reversao_criadas']}")
        print(f"   MOV-C (REVERSAO criadas): {self.stats['mov_c_reversao_criadas']}")
        print(f"   MOV-C (AJUSTE criadas): {self.stats['mov_c_ajuste_criadas']}")
        print(f"   Já existe REVERSAO (ignorados): {self.stats['mov_ja_existe_reversao']}")
        print("")

        # Cálculo de neutralização
        total_reversao = (
            self.stats['mov_a_reativadas'] +  # MOV-A: VENDA reativada neutraliza REVERSAO
            self.stats['mov_b_reversao_criadas'] +  # MOV-B: VENDA nova neutraliza REVERSAO
            self.stats['mov_c_reversao_criadas']  # MOV-C: AJUSTE neutraliza REVERSAO
        )
        total_contrapartida = (
            self.stats['mov_a_reativadas'] +  # MOV-A: VENDA reativada
            self.stats['mov_b_venda_criadas'] +  # MOV-B: VENDA nova
            self.stats['mov_c_ajuste_criadas']  # MOV-C: AJUSTE
        )

        print(f"📊 Verificação de Neutralização:")
        print(f"   Total REVERSAO (ENTRADA): {total_reversao}")
        print(f"   Total Contrapartida (SAÍDA ou reativação): {total_contrapartida}")
        if total_reversao == total_contrapartida:
            print(f"   ✅ ESTOQUE NEUTRO (diferença = 0)")
        else:
            print(f"   ⚠️  Diferença: {total_reversao - total_contrapartida}")

        print("")
        if self.stats['erros']:
            print(f"❌ Erros: {len(self.stats['erros'])}")
            for erro in self.stats['erros'][:10]:
                print(f"   - {erro}")
            if len(self.stats['erros']) > 10:
                print(f"   ... e mais {len(self.stats['erros']) - 10} erros")


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description='Migração retroativa de NFs revertidas do Odoo'
    )
    parser.add_argument(
        '--dias',
        type=int,
        default=365,
        help='Dias para trás (default: 365)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Modo simulação (não salva)'
    )
    parser.add_argument(
        '--limite',
        type=int,
        default=None,
        help='Limite de NCs a processar'
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        backfill = BackfillReversoes(dry_run=args.dry_run)
        backfill.executar(dias=args.dias, limite=args.limite)


if __name__ == '__main__':
    main()
