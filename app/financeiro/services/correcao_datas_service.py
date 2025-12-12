"""
Service para Correção de Datas - NFs de Crédito
================================================

Funções:
- diagnosticar(): Busca NFs com problema e salva na tabela
- corrigir(): Executa correção via API Odoo
- exportar_excel(): Gera Excel com histórico

Autor: Sistema de Fretes - Análise CIEL IT
Data: 11/12/2025
"""

from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
import logging

from app import db
from app.financeiro.models_correcao_datas import CorrecaoDataNFCredito
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


class CorrecaoDatasService:
    """Service para diagnóstico e correção de datas de NFs de Crédito"""

    # ID do campo 'date' no Odoo (field_id em mail.tracking.value)
    FIELD_ID_DATE = 4333

    def __init__(self):
        self.odoo = None

    def _conectar_odoo(self) -> bool:
        """Estabelece conexão com Odoo"""
        if self.odoo is None:
            self.odoo = get_odoo_connection()
        return self.odoo.authenticate()

    def diagnosticar(self, data_inicio: date = None, data_fim: date = None) -> Dict:
        """
        Busca NFs de Crédito com problema de data e salva na tabela.

        CRITÉRIOS REFINADOS (problema CIEL IT - julho/2025):
        1. Busca alterações do campo date em julho/2025
        2. Identifica padrão: old_value != invoice_date E new_value == invoice_date
        3. Ou seja: a data foi ALTERADA DE outra data PARA invoice_date (erro do script)

        Args:
            data_inicio: Filtro de data de emissão (início)
            data_fim: Filtro de data de emissão (fim)

        Returns:
            Dict com resultado do diagnóstico
        """
        if not self._conectar_odoo():
            return {'sucesso': False, 'erro': 'Falha na conexão com Odoo'}

        resultado = {
            'sucesso': True,
            'total_analisados': 0,
            'total_com_problema': 0,
            'novos_diagnosticados': 0,
            'ja_existentes': 0,
            'erros': []
        }

        try:
            # 1. Buscar mensagens de alterações feitas pelo "Suporte - CIEL IT" em julho/2025
            logger.info("Buscando mensagens do 'Suporte - CIEL IT' em julho/2025...")

            # Primeiro, buscar o ID do usuário "Suporte - CIEL IT"
            ciel_users = self.odoo.execute_kw(
                'res.partner', 'search_read',
                [[['name', 'ilike', 'CIEL IT']]],
                {'fields': ['id', 'name'], 'limit': 5}
            )

            ciel_user_ids = [u['id'] for u in ciel_users]
            logger.info(f"IDs do Suporte CIEL IT: {ciel_user_ids}")

            if not ciel_user_ids:
                logger.warning("Usuário 'Suporte - CIEL IT' não encontrado")
                return resultado

            # 2. Buscar mensagens do CIEL IT em julho/2025 para account.move
            # IMPORTANTE: Há ~81.000 mensagens, precisamos de limite alto
            messages_ciel = self.odoo.execute_kw(
                'mail.message', 'search_read',
                [[
                    ['author_id', 'in', ciel_user_ids],
                    ['model', '=', 'account.move'],
                    ['create_date', '>=', '2025-07-01 00:00:00'],
                    ['create_date', '<=', '2025-07-31 23:59:59']
                ]],
                {'fields': ['id', 'res_id', 'tracking_value_ids'], 'limit': 100000}
            )

            logger.info(f"Mensagens do CIEL IT em julho/2025: {len(messages_ciel)}")

            # 3. Coletar tracking_value_ids dessas mensagens
            tracking_ids = []
            message_to_move = {}
            for m in messages_ciel:
                tracking_ids.extend(m['tracking_value_ids'])
                message_to_move[m['id']] = m['res_id']

            # 4. Buscar tracking_values do campo date
            tracking_values = self.odoo.execute_kw(
                'mail.tracking.value', 'search_read',
                [[
                    ['id', 'in', tracking_ids],
                    ['field_id', '=', self.FIELD_ID_DATE]
                ]],
                {
                    'fields': ['id', 'old_value_datetime', 'new_value_datetime', 'mail_message_id'],
                    'limit': 100000
                }
            )

            logger.info(f"Alterações de data pelo CIEL IT: {len(tracking_values)}")

            # 5. Criar mapa de tracking por message_id para consulta rápida
            tracking_por_message = {}
            for t in tracking_values:
                if t['mail_message_id']:
                    msg_id = t['mail_message_id'][0]
                    if msg_id not in tracking_por_message:
                        tracking_por_message[msg_id] = []
                    tracking_por_message[msg_id].append(t)

            # Coletar move_ids únicos
            move_ids = list(set(message_to_move.values()))
            logger.info(f"Total de account.move com alterações: {len(move_ids)}")

            # Mapa para guardar a data correta de cada move (old_value do tracking CIEL IT)
            data_correta_por_move = {}

            # 4. Buscar dados das NFs de crédito
            filtro = [
                ['id', 'in', move_ids],
                ['move_type', '=', 'out_refund'],
                ['state', '=', 'posted']
            ]

            if data_inicio:
                filtro.append(['invoice_date', '>=', data_inicio.isoformat()])
            if data_fim:
                filtro.append(['invoice_date', '<=', data_fim.isoformat()])

            moves = self.odoo.execute_kw(
                'account.move', 'search_read',
                [filtro],
                {
                    'fields': [
                        'id', 'name', 'ref', 'invoice_date', 'date',
                        'create_date', 'partner_id'
                    ],
                    'limit': 5000
                }
            )

            # Criar mapa de move_id -> move_data
            moves_por_id = {m['id']: m for m in moves}

            resultado['total_analisados'] = len(moves)

            # 5. Analisar tracking_values para identificar padrão do erro
            # Padrão: old_value != invoice_date E new_value == invoice_date
            nfs_com_problema = set()

            for msg_id, trackings in tracking_por_message.items():
                move_id = message_to_move.get(msg_id)
                if not move_id or move_id not in moves_por_id:
                    continue

                move = moves_por_id[move_id]
                invoice_date = move['invoice_date']

                for t in trackings:
                    old_val = t['old_value_datetime'][:10] if t['old_value_datetime'] else None
                    new_val = t['new_value_datetime'][:10] if t['new_value_datetime'] else None

                    # CRITÉRIOS REFINADOS:
                    # 1. A data foi alterada DE uma data diferente de invoice_date
                    # 2. A data original (old_val) deve ser >= invoice_date
                    #    (não pode ter sido lançada antes da emissão)
                    if old_val and old_val != invoice_date and old_val >= invoice_date:
                        # Encontrou o padrão do erro!
                        # O old_val É a data correta que queremos restaurar
                        nfs_com_problema.add(move_id)
                        data_correta_por_move[move_id] = old_val
                        break

            logger.info(f"NFs com padrão de erro identificado: {len(nfs_com_problema)}")

            # 6. Processar apenas as NFs com problema confirmado
            # Usar no_autoflush para evitar problemas de duplicidade
            move_ids_processados = set()

            with db.session.no_autoflush:
                for move_id in nfs_com_problema:
                    # Evitar processar o mesmo move_id duas vezes nesta sessão
                    if move_id in move_ids_processados:
                        continue
                    move_ids_processados.add(move_id)

                    m = moves_por_id[move_id]

                    resultado['total_com_problema'] += 1

                    # Verificar se já existe na tabela
                    existe = CorrecaoDataNFCredito.query.filter_by(
                        odoo_move_id=m['id']
                    ).first()

                    if existe:
                        resultado['ja_existentes'] += 1
                        continue

                    # Usar a data correta identificada no loop de análise (old_value do tracking CIEL IT)
                    data_original = data_correta_por_move.get(move_id)
                    if not data_original:
                        # Fallback (não deveria acontecer)
                        logger.warning(f"Data correta não encontrada para move {move_id}, usando create_date")
                        create_date = m['create_date'][:10] if m['create_date'] else None
                        data_original = create_date

                    # Buscar data das linhas
                    data_linhas = self._buscar_data_linhas(m['id'])

                    # Extrair número da NF do nome ou ref
                    numero_nf = self._extrair_numero_nf(m['name'], m.get('ref', ''))

                    # Verificar se realmente precisa correção
                    data_correta_dt = datetime.strptime(data_original, '%Y-%m-%d').date()
                    data_lancamento_dt = datetime.strptime(m['date'], '%Y-%m-%d').date()
                    data_linhas_dt = datetime.strptime(data_linhas, '%Y-%m-%d').date() if data_linhas else None

                    header_ok = data_lancamento_dt == data_correta_dt
                    linhas_ok = data_linhas_dt == data_correta_dt if data_linhas_dt else True

                    # Definir status baseado na necessidade de correção
                    if header_ok and linhas_ok:
                        status_inicial = 'ignorado'  # Já está correto
                    else:
                        status_inicial = 'pendente'

                    # Criar registro
                    correcao = CorrecaoDataNFCredito(
                        odoo_move_id=m['id'],
                        nome_documento=m['name'],
                        numero_nf=numero_nf,
                        odoo_partner_id=m['partner_id'][0] if m['partner_id'] else None,
                        nome_parceiro=m['partner_id'][1] if m['partner_id'] else None,
                        data_emissao=datetime.strptime(m['invoice_date'], '%Y-%m-%d').date(),
                        data_lancamento_antes=data_lancamento_dt,
                        data_lancamento_linhas_antes=data_linhas_dt,
                        data_correta=data_correta_dt,
                        status=status_inicial
                    )

                    db.session.add(correcao)
                    resultado['novos_diagnosticados'] += 1

            db.session.commit()
            logger.info(f"Diagnóstico concluído: {resultado}")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro no diagnóstico: {e}")
            resultado['sucesso'] = False
            resultado['erro'] = str(e)

        return resultado

    def _buscar_data_original(self, move_id: int) -> Optional[str]:
        """Busca a data original de um documento via tracking_values"""
        try:
            # Buscar mensagens do documento
            messages = self.odoo.execute_kw(
                'mail.message', 'search_read',
                [[['model', '=', 'account.move'], ['res_id', '=', move_id]]],
                {'fields': ['tracking_value_ids'], 'limit': 100}
            )

            tracking_ids = []
            for msg in messages:
                tracking_ids.extend(msg['tracking_value_ids'])

            if not tracking_ids:
                return None

            # Buscar tracking_values do campo date, ordenado por data
            tracks = self.odoo.execute_kw(
                'mail.tracking.value', 'search_read',
                [[['id', 'in', tracking_ids], ['field_id', '=', self.FIELD_ID_DATE]]],
                {
                    'fields': ['old_value_datetime', 'create_date'],
                    'order': 'create_date asc',
                    'limit': 1
                }
            )

            if tracks and tracks[0]['old_value_datetime']:
                return tracks[0]['old_value_datetime'][:10]

            return None

        except Exception as e:
            logger.warning(f"Erro ao buscar data original do move {move_id}: {e}")
            return None

    def _buscar_data_linhas(self, move_id: int) -> Optional[str]:
        """Busca a data das linhas de um documento"""
        try:
            lines = self.odoo.execute_kw(
                'account.move.line', 'search_read',
                [[['move_id', '=', move_id]]],
                {'fields': ['date'], 'limit': 1}
            )

            if lines:
                return lines[0]['date']
            return None

        except Exception as e:
            logger.warning(f"Erro ao buscar data das linhas do move {move_id}: {e}")
            return None

    def _extrair_numero_nf(self, nome: str, ref: str) -> Optional[str]:
        """Extrai número da NF do nome ou referência"""
        import re
        # Tentar extrair do formato "NF-e: 123456"
        match = re.search(r'NF-?e?:?\s*(\d+)', ref or '')
        if match:
            return match.group(1)
        return None

    def listar_pendentes(
        self,
        mes: str = None,
        documento: str = None,
        page: int = 1,
        per_page: int = 50
    ) -> Tuple[List[Dict], int]:
        """
        Lista NFs pendentes de correção.

        Args:
            mes: Filtro por mês (YYYY-MM)
            documento: Filtro por nome do documento
            page: Página atual
            per_page: Itens por página

        Returns:
            Tuple[Lista de dicts, total de registros]
        """
        query = CorrecaoDataNFCredito.query

        if mes:
            ano, mes_num = mes.split('-')
            query = query.filter(
                db.extract('year', CorrecaoDataNFCredito.data_emissao) == int(ano),
                db.extract('month', CorrecaoDataNFCredito.data_emissao) == int(mes_num)
            )

        if documento:
            query = query.filter(
                CorrecaoDataNFCredito.nome_documento.ilike(f'%{documento}%')
            )

        # Status pendente
        query = query.filter(CorrecaoDataNFCredito.status == 'pendente')

        # Ordenar por data de emissão
        query = query.order_by(CorrecaoDataNFCredito.data_emissao.desc())

        # Paginar
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()

        return [item.to_dict() for item in items], total

    def listar_todos(
        self,
        status: str = None,
        mes: str = None,
        documento: str = None,
        page: int = 1,
        per_page: int = 50
    ) -> Tuple[List[Dict], int]:
        """Lista todos os registros com filtros opcionais"""
        query = CorrecaoDataNFCredito.query

        if status:
            query = query.filter(CorrecaoDataNFCredito.status == status)

        if mes:
            ano, mes_num = mes.split('-')
            query = query.filter(
                db.extract('year', CorrecaoDataNFCredito.data_emissao) == int(ano),
                db.extract('month', CorrecaoDataNFCredito.data_emissao) == int(mes_num)
            )

        if documento:
            query = query.filter(
                CorrecaoDataNFCredito.nome_documento.ilike(f'%{documento}%')
            )

        query = query.order_by(CorrecaoDataNFCredito.data_emissao.desc())

        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()

        return [item.to_dict() for item in items], total

    def corrigir(self, ids: List[int], usuario: str) -> Dict:
        """
        Executa correção dos documentos selecionados via API Odoo.

        Args:
            ids: Lista de IDs da tabela correcao_data_nf_credito
            usuario: Nome do usuário que está executando

        Returns:
            Dict com resultado da correção
        """
        if not self._conectar_odoo():
            return {'sucesso': False, 'erro': 'Falha na conexão com Odoo'}

        resultado = {
            'sucesso': True,
            'total': len(ids),
            'corrigidos': 0,
            'erros': 0,
            'detalhes': []
        }

        for correcao_id in ids:
            correcao = CorrecaoDataNFCredito.query.get(correcao_id)
            if not correcao:
                resultado['erros'] += 1
                resultado['detalhes'].append({
                    'id': correcao_id,
                    'sucesso': False,
                    'erro': 'Registro não encontrado'
                })
                continue

            try:
                # Executar correção via API Odoo
                sucesso = self._corrigir_documento(
                    correcao.odoo_move_id,
                    correcao.data_correta.isoformat()
                )

                if sucesso:
                    # Buscar nova data das linhas
                    data_linhas_depois = self._buscar_data_linhas(correcao.odoo_move_id)

                    correcao.status = 'corrigido'
                    correcao.data_lancamento_depois = correcao.data_correta
                    correcao.data_lancamento_linhas_depois = (
                        datetime.strptime(data_linhas_depois, '%Y-%m-%d').date()
                        if data_linhas_depois else None
                    )
                    correcao.corrigido_em = datetime.utcnow()
                    correcao.corrigido_por = usuario

                    resultado['corrigidos'] += 1
                    resultado['detalhes'].append({
                        'id': correcao_id,
                        'nome': correcao.nome_documento,
                        'sucesso': True
                    })
                else:
                    raise Exception("Falha na API do Odoo")

            except Exception as e:
                correcao.status = 'erro'
                correcao.erro_mensagem = str(e)
                resultado['erros'] += 1
                resultado['detalhes'].append({
                    'id': correcao_id,
                    'nome': correcao.nome_documento,
                    'sucesso': False,
                    'erro': str(e)
                })

            db.session.commit()

        return resultado

    def _corrigir_documento(self, move_id: int, data_correta: str) -> bool:
        """
        Corrige a data de um documento no Odoo.

        Fluxo:
        1. Voltar documento para draft
        2. Atualizar date
        3. Repostar documento
        """
        try:
            # 1. Verificar estado atual
            move = self.odoo.execute_kw(
                'account.move', 'read',
                [[move_id]],
                {'fields': ['state']}
            )

            if not move:
                raise Exception(f"Documento {move_id} não encontrado")

            was_posted = move[0]['state'] == 'posted'

            # 2. Voltar para draft se estava posted
            if was_posted:
                self.odoo.execute_kw('account.move', 'button_draft', [[move_id]])

            # 3. Atualizar a data
            self.odoo.execute_kw(
                'account.move', 'write',
                [[move_id], {'date': data_correta}]
            )

            # 4. Atualizar linhas
            line_ids = self.odoo.execute_kw(
                'account.move.line', 'search',
                [[['move_id', '=', move_id]]]
            )

            if line_ids:
                self.odoo.execute_kw(
                    'account.move.line', 'write',
                    [line_ids, {'date': data_correta}]
                )

            # 5. Repostar se estava posted
            if was_posted:
                self.odoo.execute_kw('account.move', 'action_post', [[move_id]])

            logger.info(f"Documento {move_id} corrigido para data {data_correta}")
            return True

        except Exception as e:
            logger.error(f"Erro ao corrigir documento {move_id}: {e}")
            raise

    def obter_estatisticas(self) -> Dict:
        """Retorna estatísticas do diagnóstico"""
        from sqlalchemy import func

        stats = db.session.query(
            CorrecaoDataNFCredito.status,
            func.count(CorrecaoDataNFCredito.id)
        ).group_by(CorrecaoDataNFCredito.status).all()

        resultado = {
            'total': 0,
            'pendente': 0,
            'corrigido': 0,
            'erro': 0,
            'ignorado': 0
        }

        for status, count in stats:
            resultado[status] = count
            resultado['total'] += count

        return resultado
