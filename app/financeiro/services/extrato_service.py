# -*- coding: utf-8 -*-
"""
Serviço de Importação e Conciliação de Extrato Bancário
=======================================================

Importa linhas de extrato não conciliadas do Odoo e prepara para matching
com títulos a receber.

Fluxo:
1. Importar linhas de extrato não conciliadas (recebimentos) do Odoo
2. Extrair dados do payment_ref (CNPJ, nome, tipo)
3. Buscar linha de crédito correspondente para conciliação
4. Salvar no sistema para processamento posterior

Autor: Sistema de Fretes
Data: 2025-12-11
"""

import re
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

from app import db
from app.financeiro.models import ExtratoLote, ExtratoItem

logger = logging.getLogger(__name__)


# Regex para extrair CNPJ do payment_ref
# Formatos: 05.017.780/0001-04, 05017780000104
REGEX_CNPJ = re.compile(r'(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-.\s]?\d{2})')

# Tipos de transação conhecidos
TIPOS_TRANSACAO = {
    'TED Recebida': 'TED',
    'PIX Recebido': 'PIX',
    'Recebimento de boletos': 'BOLETO',
    'DOC Recebido': 'DOC',
    'Transferência Recebida': 'TRANSFERENCIA',
    'Pagamento Recebido': 'PAGAMENTO',
}


class ExtratoService:
    """
    Serviço para importar e processar extrato bancário do Odoo.
    """

    def __init__(self, connection=None):
        self._connection = connection
        self.estatisticas = {
            'importados': 0,
            'com_cnpj': 0,
            'sem_cnpj': 0,
            'erros': 0
        }

    @property
    def connection(self):
        """Retorna a conexão Odoo, criando se necessário."""
        if self._connection is None:
            from app.odoo.utils.connection import get_odoo_connection
            self._connection = get_odoo_connection()
            if not self._connection.authenticate():
                raise Exception("Falha na autenticação com Odoo")
        return self._connection

    def importar_extrato(
        self,
        journal_code: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        limit: int = 500,
        criado_por: str = 'Sistema'
    ) -> ExtratoLote:
        """
        Importa linhas de extrato não conciliadas do Odoo.

        Args:
            journal_code: Código do journal (GRA1, SIC, BRAD, etc.)
            data_inicio: Data inicial (opcional)
            data_fim: Data final (opcional)
            limit: Limite de linhas a importar
            criado_por: Usuário que criou

        Returns:
            ExtratoLote com os itens importados
        """
        logger.info(f"=" * 60)
        logger.info(f"IMPORTANDO EXTRATO - Journal: {journal_code}")
        logger.info(f"=" * 60)

        # Buscar journal
        journal = self._buscar_journal(journal_code)
        if not journal:
            raise ValueError(f"Journal {journal_code} não encontrado")

        journal_id = journal['id']
        journal_name = journal['name']

        # Criar lote
        nome_lote = f"Importação {journal_code} {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        lote = ExtratoLote(
            nome=nome_lote,
            journal_code=journal_code,
            journal_id=journal_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            status='IMPORTADO',
            criado_por=criado_por
        )
        db.session.add(lote)
        db.session.flush()

        # Buscar linhas não conciliadas
        linhas = self._buscar_linhas_extrato(
            journal_id=journal_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            limit=limit
        )

        logger.info(f"Linhas encontradas: {len(linhas)}")

        # OTIMIZAÇÃO: Buscar todas as linhas de crédito em batch
        move_ids = [
            self._extrair_id(linha.get('move_id'))
            for linha in linhas
            if linha.get('move_id')
        ]
        credit_lines_cache = self._buscar_linhas_credito_batch(move_ids) if move_ids else {}
        logger.info(f"Linhas de crédito carregadas em batch: {len(credit_lines_cache)}")

        valor_total = 0

        for linha in linhas:
            try:
                item = self._processar_linha(
                    lote.id, linha, journal_code, journal_name,
                    credit_lines_cache=credit_lines_cache
                )
                if item:
                    valor_total += item.valor
                    self.estatisticas['importados'] += 1
                    if item.cnpj_pagador:
                        self.estatisticas['com_cnpj'] += 1
                    else:
                        self.estatisticas['sem_cnpj'] += 1
            except Exception as e:
                logger.error(f"Erro ao processar linha {linha.get('id')}: {e}")
                self.estatisticas['erros'] += 1

        # Atualizar estatísticas do lote
        lote.total_linhas = self.estatisticas['importados']
        lote.valor_total = valor_total

        db.session.commit()

        logger.info(f"Importação concluída: {self.estatisticas}")

        return lote

    def _buscar_journal(self, journal_code: str) -> Optional[Dict]:
        """Busca journal pelo código."""
        journals = self.connection.search_read(
            'account.journal',
            [['code', '=', journal_code]],
            fields=['id', 'name', 'code', 'type', 'company_id'],
            limit=1
        )
        return journals[0] if journals else None

    def _buscar_linhas_extrato(
        self,
        journal_id: int,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        limit: int = 500
    ) -> List[Dict]:
        """
        Busca linhas de extrato não conciliadas (recebimentos).

        Critérios:
        - journal_id específico
        - is_reconciled = False
        - amount > 0 (recebimentos)
        """
        domain = [
            ['journal_id', '=', journal_id],
            ['is_reconciled', '=', False],
            ['amount', '>', 0]  # Apenas recebimentos
        ]

        if data_inicio:
            domain.append(['date', '>=', data_inicio.strftime('%Y-%m-%d')])
        if data_fim:
            domain.append(['date', '<=', data_fim.strftime('%Y-%m-%d')])

        fields = [
            'id', 'date', 'payment_ref', 'amount', 'amount_residual',
            'partner_id', 'partner_name', 'account_number',
            'journal_id', 'statement_id', 'move_id',
            'is_reconciled', 'transaction_type', 'company_id'
        ]

        return self.connection.search_read(
            'account.bank.statement.line',
            domain,
            fields=fields,
            limit=limit
        )

    def _processar_linha(
        self,
        lote_id: int,
        linha: Dict,
        journal_code: str,
        journal_name: str,
        credit_lines_cache: Optional[Dict[int, int]] = None
    ) -> Optional[ExtratoItem]:
        """
        Processa uma linha de extrato e cria ExtratoItem.

        Args:
            credit_lines_cache: Cache de move_id -> credit_line_id (OTIMIZAÇÃO)
        """
        statement_line_id = linha['id']

        # Verificar se já foi importada
        existe = ExtratoItem.query.filter_by(statement_line_id=statement_line_id).first()
        if existe:
            logger.debug(f"Linha {statement_line_id} já importada, ignorando")
            return None

        # Extrair dados do payment_ref
        payment_ref = linha.get('payment_ref', '') or ''
        tipo_transacao, nome_pagador, cnpj_pagador = self._extrair_dados_payment_ref(payment_ref)

        # Buscar linha de crédito (usa cache se disponível)
        move_id = self._extrair_id(linha.get('move_id'))
        move_name = self._extrair_nome(linha.get('move_id'))
        credit_line_id = None

        if move_id:
            if credit_lines_cache is not None:
                credit_line_id = credit_lines_cache.get(move_id)
            else:
                credit_line_id = self._buscar_linha_credito(move_id)

        # Converter data
        data_transacao = linha.get('date')
        if isinstance(data_transacao, str):
            data_transacao = datetime.strptime(data_transacao, '%Y-%m-%d').date()

        # Criar item
        item = ExtratoItem(
            lote_id=lote_id,
            statement_line_id=statement_line_id,
            move_id=move_id,
            move_name=move_name,
            credit_line_id=credit_line_id,
            data_transacao=data_transacao,
            valor=linha.get('amount', 0),
            payment_ref=payment_ref,
            tipo_transacao=tipo_transacao,
            nome_pagador=nome_pagador,
            cnpj_pagador=cnpj_pagador,
            journal_id=self._extrair_id(linha.get('journal_id')),
            journal_code=journal_code,
            journal_name=journal_name,
            status_match='PENDENTE',
            status='PENDENTE'
        )

        db.session.add(item)
        return item

    def _extrair_dados_payment_ref(self, payment_ref: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extrai tipo de transação, nome do pagador e CNPJ do payment_ref.

        Formatos comuns:
        - ": TED Recebida - RIO BRANCO ALIMENTOS S A - 05.017.780/0001-04 - Banco: ..."
        - ": PIX Recebido - PREMIER DESPACHOS - 11.849.472/0001-30 - Agência: ..."
        - ": Recebimento de boletos - CAMIL ALIMENTOS S.A. - 64.904.295/0028-23 - ..."

        Returns:
            Tuple (tipo_transacao, nome_pagador, cnpj_formatado)
        """
        if not payment_ref:
            return None, None, None

        tipo_transacao = None
        nome_pagador = None
        cnpj_pagador = None

        # Identificar tipo de transação
        for padrao, tipo in TIPOS_TRANSACAO.items():
            if padrao in payment_ref:
                tipo_transacao = tipo
                break

        # Extrair CNPJ
        match_cnpj = REGEX_CNPJ.search(payment_ref)
        if match_cnpj:
            cnpj_raw = match_cnpj.group(1)
            # Normalizar CNPJ para formato XX.XXX.XXX/XXXX-XX
            cnpj_pagador = self._normalizar_cnpj(cnpj_raw)

        # Extrair nome do pagador
        # Geralmente está entre o tipo de transação e o CNPJ
        # Formato: "tipo - NOME - CNPJ - dados"
        partes = payment_ref.split(' - ')
        if len(partes) >= 2:
            # O nome geralmente é a segunda parte (após o tipo)
            for i, parte in enumerate(partes):
                # Pular parte que contém o tipo de transação
                has_tipo = any(t in parte for t in TIPOS_TRANSACAO.keys())
                if has_tipo:
                    continue
                # Pular parte que contém CNPJ
                if REGEX_CNPJ.search(parte):
                    break
                # Pular partes com "Banco:", "Agência:", etc.
                if ':' in parte:
                    continue
                # Provavelmente é o nome
                nome_pagador = parte.strip()
                break

        return tipo_transacao, nome_pagador, cnpj_pagador

    def _normalizar_cnpj(self, cnpj_raw: str) -> str:
        """Normaliza CNPJ para formato XX.XXX.XXX/XXXX-XX."""
        # Remover tudo exceto dígitos
        digitos = re.sub(r'\D', '', cnpj_raw)

        if len(digitos) != 14:
            return cnpj_raw  # Retorna original se inválido

        # Formatar
        return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:14]}"

    def _buscar_linha_credito(self, move_id: int) -> Optional[int]:
        """
        Busca a linha de crédito (contrapartida) do extrato.

        Quando uma linha de extrato é criada, o Odoo gera:
        - 1 linha de DÉBITO na conta do banco
        - 1 linha de CRÉDITO na conta transitória (para conciliar)

        Retorna o ID da linha de crédito.

        NOTA: Para importações em batch, use _buscar_linhas_credito_batch().
        """
        linhas = self.connection.search_read(
            'account.move.line',
            [
                ['move_id', '=', move_id],
                ['credit', '>', 0]  # Linha de crédito
            ],
            fields=['id', 'account_id', 'credit', 'amount_residual'],
            limit=1
        )
        return linhas[0]['id'] if linhas else None

    def _buscar_linhas_credito_batch(self, move_ids: List[int]) -> Dict[int, int]:
        """
        Busca linhas de crédito para múltiplos moves em uma única query.

        OTIMIZAÇÃO: Elimina o problema de N queries individuais durante importação.

        Args:
            move_ids: Lista de IDs de account.move

        Returns:
            Dict mapeando move_id -> credit_line_id
        """
        if not move_ids:
            return {}

        # Buscar todas as linhas de crédito de uma vez
        linhas = self.connection.search_read(
            'account.move.line',
            [
                ['move_id', 'in', move_ids],
                ['credit', '>', 0]
            ],
            fields=['id', 'move_id']
        )

        # Mapear move_id -> credit_line_id (pega a primeira de cada move)
        resultado = {}
        for linha in linhas:
            move_id = linha['move_id'][0] if isinstance(linha['move_id'], (list, tuple)) else linha['move_id']
            if move_id not in resultado:  # Pegar apenas a primeira
                resultado[move_id] = linha['id']

        return resultado

    def _extrair_id(self, valor) -> Optional[int]:
        """Extrai ID de um campo many2one do Odoo."""
        if not valor:
            return None
        if isinstance(valor, (list, tuple)) and len(valor) > 0:
            return valor[0]
        if isinstance(valor, int):
            return valor
        return None

    def _extrair_nome(self, valor) -> Optional[str]:
        """Extrai nome de um campo many2one do Odoo."""
        if not valor:
            return None
        if isinstance(valor, (list, tuple)) and len(valor) > 1:
            return valor[1]
        return None

    def listar_journals_disponiveis(self) -> List[Dict]:
        """
        Lista journals bancários disponíveis para importação.

        OTIMIZADO: Usa read_group para contar pendentes por journal em uma única query.
        """
        journals = self.connection.search_read(
            'account.journal',
            [['type', 'in', ['bank', 'cash']]],
            fields=['id', 'name', 'code', 'type', 'company_id']
        )

        if not journals:
            return []

        journal_ids = [j['id'] for j in journals]

        # OTIMIZAÇÃO: Contar pendentes de TODOS os journals em uma única query
        pendentes_por_journal = {}
        try:
            grupos = self.connection.execute_kw(
                'account.bank.statement.line',
                'read_group',
                [[
                    ['journal_id', 'in', journal_ids],
                    ['is_reconciled', '=', False],
                    ['amount', '>', 0]
                ]],
                {
                    'fields': ['journal_id'],
                    'groupby': ['journal_id'],
                    'lazy': False
                }
            )
            for g in grupos:
                if g.get('journal_id'):
                    j_id = g['journal_id'][0] if isinstance(g['journal_id'], (list, tuple)) else g['journal_id']
                    # Odoo 17 retorna __count, versões anteriores retornam journal_id_count
                    pendentes_por_journal[j_id] = g.get('__count') or g.get('journal_id_count', 0)
        except Exception as e:
            logger.warning(f"Erro ao usar read_group para journals: {e}")
            # Fallback: buscar todas as linhas e contar em Python
            linhas = self.connection.search_read(
                'account.bank.statement.line',
                [
                    ['journal_id', 'in', journal_ids],
                    ['is_reconciled', '=', False],
                    ['amount', '>', 0]
                ],
                fields=['journal_id']
            )
            for linha in linhas:
                j_id = linha['journal_id'][0] if isinstance(linha['journal_id'], (list, tuple)) else linha['journal_id']
                pendentes_por_journal[j_id] = pendentes_por_journal.get(j_id, 0) + 1

        resultado = []
        for j in journals:
            resultado.append({
                'id': j['id'],
                'code': j['code'],
                'name': j['name'],
                'type': j['type'],
                'company': j['company_id'][1] if j['company_id'] else 'N/A',
                'recebimentos_pendentes': pendentes_por_journal.get(j['id'], 0)
            })

        return resultado

    # =========================================================================
    # MÉTODOS PARA STATEMENTS (NOVOS)
    # =========================================================================

    def listar_statements_disponiveis(self, journal_code: Optional[str] = None) -> List[Dict]:
        """
        Lista statements (extratos) do Odoo com linhas não conciliadas.

        OTIMIZADO: Usa read_group para contar pendentes em uma única query,
        eliminando o problema de N+1 queries.

        Args:
            journal_code: Filtrar por código do journal (opcional)

        Returns:
            Lista de statements com contagem de pendentes
        """
        # Buscar journals
        domain_journal = [['type', 'in', ['bank', 'cash']]]
        if journal_code:
            domain_journal.append(['code', '=', journal_code])

        journals = self.connection.search_read(
            'account.journal',
            domain_journal,
            fields=['id', 'name', 'code', 'company_id']
        )

        journal_map = {j['id']: j for j in journals}
        journal_ids = list(journal_map.keys())

        if not journal_ids:
            return []

        # Buscar statements desses journals
        statements = self.connection.search_read(
            'account.bank.statement',
            [['journal_id', 'in', journal_ids]],
            fields=['id', 'name', 'date', 'journal_id', 'balance_start', 'balance_end_real']
        )

        if not statements:
            return []

        statement_ids = [st['id'] for st in statements]

        # OTIMIZAÇÃO: Contar pendentes de TODOS os statements em uma única query
        # usando read_group ao invés de N queries individuais
        pendentes_por_statement = {}
        try:
            # read_group retorna contagem agrupada por statement_id
            grupos = self.connection.execute_kw(
                'account.bank.statement.line',
                'read_group',
                [[
                    ['statement_id', 'in', statement_ids],
                    ['is_reconciled', '=', False],
                    ['amount', '>', 0]
                ]],
                {
                    'fields': ['statement_id'],
                    'groupby': ['statement_id'],
                    'lazy': False
                }
            )
            for g in grupos:
                if g.get('statement_id'):
                    st_id = g['statement_id'][0] if isinstance(g['statement_id'], (list, tuple)) else g['statement_id']
                    # Odoo 17 retorna __count, versões anteriores retornam statement_id_count
                    pendentes_por_statement[st_id] = g.get('__count') or g.get('statement_id_count', 0)
        except Exception as e:
            logger.warning(f"Erro ao usar read_group, fallback para contagem individual: {e}")
            # Fallback: buscar todas as linhas e contar em Python
            linhas = self.connection.search_read(
                'account.bank.statement.line',
                [
                    ['statement_id', 'in', statement_ids],
                    ['is_reconciled', '=', False],
                    ['amount', '>', 0]
                ],
                fields=['statement_id']
            )
            for linha in linhas:
                st_id = linha['statement_id'][0] if isinstance(linha['statement_id'], (list, tuple)) else linha['statement_id']
                pendentes_por_statement[st_id] = pendentes_por_statement.get(st_id, 0) + 1

        # OTIMIZAÇÃO: Buscar lotes existentes em uma única query
        lotes_existentes = {
            lote.statement_id: lote
            for lote in ExtratoLote.query.filter(
                ExtratoLote.statement_id.in_(statement_ids)
            ).all()
        }

        resultado = []
        for st in statements:
            journal_id = st['journal_id'][0] if st['journal_id'] else None
            journal = journal_map.get(journal_id, {})
            lote_existente = lotes_existentes.get(st['id'])

            resultado.append({
                'statement_id': st['id'],
                'name': st['name'],
                'date': st['date'],
                'journal_id': journal_id,
                'journal_code': journal.get('code'),
                'journal_name': journal.get('name'),
                'company': journal.get('company_id', [None, 'N/A'])[1] if journal.get('company_id') else 'N/A',
                'pendentes_odoo': pendentes_por_statement.get(st['id'], 0),
                'importado': lote_existente is not None,
                'lote_id': lote_existente.id if lote_existente else None,
                'lote_status': lote_existente.status if lote_existente else None
            })

        # Ordenar por data decrescente
        resultado.sort(key=lambda x: x['date'] or '', reverse=True)

        return resultado

    def importar_statement(
        self,
        statement_id: int,
        criado_por: str = 'Sistema'
    ) -> ExtratoLote:
        """
        Importa um statement específico do Odoo.

        Args:
            statement_id: ID do account.bank.statement no Odoo
            criado_por: Usuário que criou

        Returns:
            ExtratoLote criado
        """
        # Verificar se já foi importado
        lote_existente = ExtratoLote.query.filter_by(statement_id=statement_id).first()
        if lote_existente:
            raise ValueError(f"Statement {statement_id} já foi importado (Lote {lote_existente.id})")

        # Buscar dados do statement no Odoo
        statements = self.connection.search_read(
            'account.bank.statement',
            [['id', '=', statement_id]],
            fields=['id', 'name', 'date', 'journal_id'],
            limit=1
        )

        if not statements:
            raise ValueError(f"Statement {statement_id} não encontrado no Odoo")

        st = statements[0]
        journal_id = st['journal_id'][0] if st['journal_id'] else None
        statement_name = st['name']
        statement_date = st['date']

        # Buscar dados do journal
        journal_code = None
        journal_name = None
        if journal_id:
            journals = self.connection.search_read(
                'account.journal',
                [['id', '=', journal_id]],
                fields=['code', 'name'],
                limit=1
            )
            if journals:
                journal_code = journals[0]['code']
                journal_name = journals[0]['name']

        logger.info(f"=" * 60)
        logger.info(f"IMPORTANDO STATEMENT {statement_id}: {statement_name}")
        logger.info(f"=" * 60)

        # Criar lote
        if isinstance(statement_date, str):
            statement_date_obj = datetime.strptime(statement_date, '%Y-%m-%d').date()
        else:
            statement_date_obj = statement_date

        lote = ExtratoLote(
            statement_id=statement_id,
            statement_name=statement_name,
            nome=statement_name,
            journal_code=journal_code,
            journal_id=journal_id,
            data_extrato=statement_date_obj,
            status='IMPORTADO',
            criado_por=criado_por
        )
        db.session.add(lote)
        db.session.flush()

        # Buscar linhas não conciliadas do statement
        linhas = self._buscar_linhas_statement(statement_id)

        logger.info(f"Linhas encontradas: {len(linhas)}")

        # OTIMIZAÇÃO: Buscar todas as linhas de crédito em batch
        move_ids = [
            self._extrair_id(linha.get('move_id'))
            for linha in linhas
            if linha.get('move_id')
        ]
        credit_lines_cache = self._buscar_linhas_credito_batch(move_ids) if move_ids else {}
        logger.info(f"Linhas de crédito carregadas em batch: {len(credit_lines_cache)}")

        valor_total = 0

        for linha in linhas:
            try:
                item = self._processar_linha(
                    lote.id, linha, journal_code, journal_name,
                    credit_lines_cache=credit_lines_cache
                )
                if item:
                    valor_total += item.valor
                    self.estatisticas['importados'] += 1
                    if item.cnpj_pagador:
                        self.estatisticas['com_cnpj'] += 1
                    else:
                        self.estatisticas['sem_cnpj'] += 1
            except Exception as e:
                logger.error(f"Erro ao processar linha {linha.get('id')}: {e}")
                self.estatisticas['erros'] += 1

        # Atualizar estatísticas do lote
        lote.total_linhas = self.estatisticas['importados']
        lote.valor_total = valor_total

        db.session.commit()

        logger.info(f"Importação concluída: {self.estatisticas}")

        return lote

    def _buscar_linhas_statement(self, statement_id: int) -> List[Dict]:
        """
        Busca linhas não conciliadas de um statement específico.
        """
        domain = [
            ['statement_id', '=', statement_id],
            ['is_reconciled', '=', False],
            ['amount', '>', 0]  # Apenas recebimentos
        ]

        fields = [
            'id', 'date', 'payment_ref', 'amount', 'amount_residual',
            'partner_id', 'partner_name', 'account_number',
            'journal_id', 'statement_id', 'move_id',
            'is_reconciled', 'transaction_type', 'company_id'
        ]

        return self.connection.search_read(
            'account.bank.statement.line',
            domain,
            fields=fields
        )


def importar_extrato_comando(journal_code: str, limit: int = 500):
    """
    Comando para importar extrato via CLI.

    Uso:
        source venv/bin/activate
        python -c "from app.financeiro.services.extrato_service import importar_extrato_comando; importar_extrato_comando('GRA1', 100)"
    """
    from app import create_app

    app = create_app()
    with app.app_context():
        service = ExtratoService()
        lote = service.importar_extrato(
            journal_code=journal_code,
            limit=limit
        )
        print(f"\nLote criado: ID={lote.id}, {lote.total_linhas} linhas importadas")
        print(f"Estatísticas: {service.estatisticas}")
