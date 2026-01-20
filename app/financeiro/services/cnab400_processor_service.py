"""
Service para processamento de arquivos CNAB400.

Este service é responsável por:
1. Processar arquivos .ret (retorno bancário)
2. Criar registros no banco (CnabRetornoLote, CnabRetornoItem)
3. Executar matching com ContasAReceber via NF/Parcela
4. Executar baixa de títulos

Estratégia de Matching:
- Extrai NF e Parcela do campo "Seu Número" (posição 117-126)
- Busca exata em ContasAReceber(empresa, titulo_nf, parcela)
- Score 100 = match exato (0 ou 1 resultado, nunca múltiplos)

Uso:
    processor = Cnab400ProcessorService()
    lote = processor.processar_arquivo(conteudo, nome_arquivo, usuario)
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import re

from app import db
from app.financeiro.models import (
    CnabRetornoLote,
    CnabRetornoItem,
    ContasAReceber,
    ExtratoItem,
    ExtratoLote
)
from app.financeiro.services.cnab400_parser_service import Cnab400ParserService


class Cnab400ProcessorService:
    """Processa arquivo CNAB400 e vincula com Contas a Receber"""

    def __init__(self):
        self.parser = Cnab400ParserService()

    def processar_arquivo(
        self,
        arquivo_conteudo: str,
        arquivo_nome: str,
        usuario: str
    ) -> CnabRetornoLote:
        """
        Processa arquivo CNAB400 completo.

        Args:
            arquivo_conteudo: Conteúdo do arquivo .ret (encoding latin-1)
            arquivo_nome: Nome do arquivo para registro
            usuario: Nome do usuário que está processando

        Returns:
            CnabRetornoLote criado com todos os itens processados
        """
        # 1. Parse do arquivo
        dados = self.parser.parse_arquivo(arquivo_conteudo)

        if not dados['header']:
            raise ValueError("Arquivo inválido: header não encontrado")

        # 2. Criar lote
        lote = CnabRetornoLote(
            arquivo_nome=arquivo_nome,
            banco_codigo=dados['header']['codigo_banco'],
            banco_nome=dados['header']['nome_banco'],
            data_arquivo=dados['header']['data_arquivo'],
            total_registros=len(dados['detalhes']),
            processado_por=usuario,
            status='IMPORTADO'
        )
        db.session.add(lote)
        db.session.flush()  # Gera ID do lote

        # 3. Processar cada detalhe
        for detalhe in dados['detalhes']:
            item = self._criar_item(lote, detalhe)
            self._executar_matching(item)

        # 4. Atualizar estatísticas do lote
        lote.atualizar_estatisticas()

        # 5. Definir status baseado nos resultados
        if lote.registros_sem_match > 0:
            lote.status = 'AGUARDANDO_REVISAO'
        else:
            lote.status = 'APROVADO'

        db.session.commit()
        return lote

    def _criar_item(self, lote: CnabRetornoLote, detalhe: Dict[str, Any]) -> CnabRetornoItem:
        """
        Cria item do CNAB a partir dos dados parseados.

        Args:
            lote: Lote pai
            detalhe: Dicionário com dados do registro detalhe

        Returns:
            CnabRetornoItem criado
        """
        # Extrai NF e Parcela do Seu Número
        nf, parcela = self.parser.extrair_nf_parcela(detalhe.get('seu_numero', ''))

        item = CnabRetornoItem(
            lote_id=lote.id,
            tipo_registro=detalhe.get('tipo_registro'),
            nosso_numero=detalhe.get('nosso_numero'),
            seu_numero=detalhe.get('seu_numero'),
            cnpj_pagador=detalhe.get('cnpj_pagador'),
            codigo_ocorrencia=detalhe.get('codigo_ocorrencia'),
            descricao_ocorrencia=detalhe.get('descricao_ocorrencia'),
            data_ocorrencia=detalhe.get('data_ocorrencia'),
            valor_titulo=detalhe.get('valor_titulo'),
            valor_pago=detalhe.get('valor_pago'),
            valor_juros=detalhe.get('valor_juros'),
            valor_desconto=detalhe.get('valor_desconto'),
            valor_abatimento=detalhe.get('valor_abatimento'),
            data_vencimento=detalhe.get('data_vencimento'),
            nf_extraida=nf,
            parcela_extraida=parcela,
            linha_original=detalhe.get('linha_original'),
            numero_linha=detalhe.get('numero_linha'),
            status_match='PENDENTE'
        )
        db.session.add(item)
        return item

    def _executar_matching(self, item: CnabRetornoItem) -> None:
        """
        Executa matching do item com ContasAReceber via NF/Parcela.

        Estratégia:
        1. Só processa liquidações (código 06) e baixas (10, 17)
        2. Extrai NF e Parcela do campo "Seu Número"
        3. Busca exata em ContasAReceber(empresa, titulo_nf, parcela)
        4. Verifica se título já está pago

        Args:
            item: CnabRetornoItem para processar
        """
        # Códigos de ocorrência que indicam pagamento/liquidação
        CODIGOS_LIQUIDACAO = ('06', '17')  # Liquidação Normal, Liquidação após Baixa
        CODIGOS_BAIXA = ('09', '10')       # Baixado automaticamente, Baixado conf. Instruções

        # 1. Verificar se é ocorrência que requer matching
        if item.codigo_ocorrencia not in CODIGOS_LIQUIDACAO + CODIGOS_BAIXA:
            item.status_match = 'NAO_APLICAVEL'
            return

        # 2. Verificar se conseguiu extrair NF/Parcela
        if not item.nf_extraida or not item.parcela_extraida:
            item.status_match = 'FORMATO_INVALIDO'
            item.erro_mensagem = f'Não foi possível extrair NF/Parcela de: {item.seu_numero}'
            return

        # 3. Buscar título exato
        # Tenta empresa 1 (NACOM GOYA = FB) primeiro
        titulo = self._buscar_titulo(item.nf_extraida, item.parcela_extraida, empresa=1)

        # Se não encontrar, tenta outras empresas
        if not titulo:
            for empresa_id in [2, 3, 4, 5]:  # SC, CD, etc.
                titulo = self._buscar_titulo(item.nf_extraida, item.parcela_extraida, empresa=empresa_id)
                if titulo:
                    break

        # 4. Avaliar resultado
        if not titulo:
            item.status_match = 'SEM_MATCH'
            item.erro_mensagem = f'Título não encontrado: NF {item.nf_extraida} Parcela {item.parcela_extraida}'
            return

        # 5. Verificar se já está pago
        if titulo.parcela_paga:
            item.status_match = 'JA_PAGO'
            item.conta_a_receber_id = titulo.id
            item.erro_mensagem = 'Título já estava pago anteriormente'
            return

        # 6. Match encontrado!
        item.status_match = 'MATCH_ENCONTRADO'
        item.conta_a_receber_id = titulo.id
        item.match_score = 100
        item.match_criterio = 'NF_PARCELA_EXATO'

        # 7. Validação adicional: verificar se valor confere
        if titulo.valor_titulo and item.valor_titulo:
            valor_sistema = float(titulo.valor_titulo or 0)
            valor_cnab = float(item.valor_titulo or 0)
            diff_valor = abs(valor_sistema - valor_cnab)
            if diff_valor > 0.01:
                item.erro_mensagem = (
                    f'ALERTA: Valor diverge. '
                    f'Sistema: R$ {valor_sistema:,.2f}, '
                    f'CNAB: R$ {valor_cnab:,.2f}'
                )

    def _buscar_titulo(
        self,
        nf: str,
        parcela: str,
        empresa: int
    ) -> Optional[ContasAReceber]:
        """
        Busca título exato por NF, Parcela e Empresa.

        Args:
            nf: Número da NF
            parcela: Número da parcela
            empresa: ID da empresa (1=FB, 2=SC, 3=CD, etc.)

        Returns:
            ContasAReceber ou None se não encontrar
        """
        return ContasAReceber.query.filter(
            ContasAReceber.empresa == empresa,
            ContasAReceber.titulo_nf == nf,
            ContasAReceber.parcela == parcela,
        ).first()

    def baixar_titulo(self, item: CnabRetornoItem) -> bool:
        """
        Executa baixa do título vinculado ao item.

        Args:
            item: CnabRetornoItem com match encontrado

        Returns:
            True se baixa executada com sucesso, False caso contrário
        """
        if not item.conta_a_receber_id:
            item.erro_mensagem = 'Item não possui título vinculado'
            return False

        if item.processado:
            item.erro_mensagem = 'Item já foi processado anteriormente'
            return False

        titulo = item.conta_a_receber

        if not titulo:
            item.erro_mensagem = 'Título vinculado não encontrado'
            item.status_match = 'ERRO'
            return False

        if titulo.parcela_paga:
            item.erro_mensagem = 'Título já estava pago'
            item.status_match = 'JA_PAGO'
            return False

        try:
            # Atualizar título
            titulo.parcela_paga = True
            titulo.status_pagamento_odoo = 'PAGO_CNAB'

            # Construir observação
            obs_parts = [
                f"Baixa via CNAB400",
                f"Ocorrência: {item.codigo_ocorrencia} ({item.descricao_ocorrencia})",
                f"Data: {item.data_ocorrencia.strftime('%d/%m/%Y') if item.data_ocorrencia else 'N/D'}",
                f"Valor Pago: R$ {item.valor_pago:,.2f}" if item.valor_pago else None,
                f"Arquivo: {item.lote.arquivo_nome}" if item.lote else None,
            ]
            titulo.observacao = ' | '.join(filter(None, obs_parts))

            # Marcar item como processado
            item.processado = True
            item.data_processamento = datetime.utcnow()
            item.status_match = 'PROCESSADO'

            db.session.commit()
            return True

        except Exception as e:
            db.session.rollback()
            item.erro_mensagem = f'Erro ao baixar título: {str(e)}'
            item.status_match = 'ERRO'
            return False

    def baixar_lote(self, lote: CnabRetornoLote) -> Dict[str, int]:
        """
        Executa baixa de todos os itens com match encontrado do lote.

        Args:
            lote: CnabRetornoLote a processar

        Returns:
            Dicionário com estatísticas: {'sucesso': N, 'erros': N, 'ignorados': N}
        """
        stats = {'sucesso': 0, 'erros': 0, 'ignorados': 0}

        lote.status = 'PROCESSANDO'
        db.session.commit()

        # Buscar itens elegíveis para baixa
        itens = CnabRetornoItem.query.filter(
            CnabRetornoItem.lote_id == lote.id,
            CnabRetornoItem.status_match == 'MATCH_ENCONTRADO',
            CnabRetornoItem.processado == False,
        ).all()

        for item in itens:
            try:
                if self.baixar_titulo(item):
                    stats['sucesso'] += 1
                else:
                    stats['erros'] += 1
            except Exception as e:
                item.erro_mensagem = str(e)
                item.status_match = 'ERRO'
                stats['erros'] += 1

        # Atualizar estatísticas do lote
        lote.atualizar_estatisticas()

        # Definir status final
        if stats['erros'] == 0:
            lote.status = 'CONCLUIDO'
        elif stats['sucesso'] > 0:
            lote.status = 'PARCIAL'
        else:
            lote.status = 'ERRO'

        db.session.commit()
        return stats

    def reprocessar_matching(self, lote: CnabRetornoLote) -> Dict[str, int]:
        """
        Reprocessa matching de todos os itens pendentes ou sem match.

        Útil quando novos títulos foram importados após o upload do CNAB.

        Args:
            lote: CnabRetornoLote a reprocessar

        Returns:
            Dicionário com estatísticas
        """
        stats = {'novos_matches': 0, 'ainda_sem_match': 0}

        itens = CnabRetornoItem.query.filter(
            CnabRetornoItem.lote_id == lote.id,
            CnabRetornoItem.status_match.in_(['SEM_MATCH', 'FORMATO_INVALIDO']),
            CnabRetornoItem.processado == False,
        ).all()

        for item in itens:
            status_anterior = item.status_match
            self._executar_matching(item)

            if item.status_match == 'MATCH_ENCONTRADO':
                stats['novos_matches'] += 1
            else:
                stats['ainda_sem_match'] += 1

        # Atualizar estatísticas do lote
        lote.atualizar_estatisticas()

        if lote.registros_sem_match == 0:
            lote.status = 'APROVADO'

        db.session.commit()
        return stats

    def obter_itens_sem_match(self, lote_id: int) -> List[CnabRetornoItem]:
        """
        Retorna itens sem match para análise manual.

        Args:
            lote_id: ID do lote

        Returns:
            Lista de CnabRetornoItem com status SEM_MATCH
        """
        return CnabRetornoItem.query.filter(
            CnabRetornoItem.lote_id == lote_id,
            CnabRetornoItem.status_match.in_(['SEM_MATCH', 'FORMATO_INVALIDO']),
        ).order_by(CnabRetornoItem.numero_linha).all()

    def obter_estatisticas_lote(self, lote: CnabRetornoLote) -> Dict[str, Any]:
        """
        Retorna estatísticas detalhadas do lote.

        Args:
            lote: CnabRetornoLote

        Returns:
            Dicionário com estatísticas
        """
        itens = lote.itens.all()

        # Agrupar por código de ocorrência
        por_ocorrencia = {}
        for item in itens:
            codigo = item.codigo_ocorrencia
            if codigo not in por_ocorrencia:
                por_ocorrencia[codigo] = {
                    'codigo': codigo,
                    'descricao': item.descricao_ocorrencia,
                    'quantidade': 0,
                    'valor_total': 0
                }
            por_ocorrencia[codigo]['quantidade'] += 1
            por_ocorrencia[codigo]['valor_total'] += float(item.valor_pago or item.valor_titulo or 0)

        # Agrupar por status de match
        por_status = {}
        for item in itens:
            status = item.status_match
            if status not in por_status:
                por_status[status] = 0
            por_status[status] += 1

        return {
            'lote': lote.to_dict(),
            'por_ocorrencia': list(por_ocorrencia.values()),
            'por_status': por_status,
            'total_itens': len(itens),
            'valor_total': sum(float(i.valor_pago or i.valor_titulo or 0) for i in itens),
        }

    # =========================================================================
    # FASE 2: INTEGRAÇÃO COM EXTRATO BANCÁRIO
    # =========================================================================

    def _normalizar_cnpj(self, cnpj: str) -> str:
        """
        Remove formatação do CNPJ, retornando apenas dígitos.

        Args:
            cnpj: CNPJ com ou sem formatação

        Returns:
            CNPJ apenas com dígitos (14 caracteres)
        """
        if not cnpj:
            return ''
        return ''.join(filter(str.isdigit, str(cnpj)))

    def _buscar_extrato_correspondente(self, item: CnabRetornoItem) -> Optional[ExtratoItem]:
        """
        Busca linha de extrato que corresponde ao item CNAB.

        Critérios de Match (em ordem de prioridade):
        1. Data ocorrência = Data transação
        2. Valor pago ≈ Valor (tolerância ±R$0.02)
        3. CNPJ pagador (se disponível em ambos)

        Score de Confiança:
        - 100: Data + Valor + CNPJ exato
        - 95: Data + Valor + CNPJ raiz (8 primeiros dígitos)
        - 85: Data + Valor (sem CNPJ ou CNPJ não disponível)

        Args:
            item: CnabRetornoItem para buscar correspondência

        Returns:
            ExtratoItem encontrado ou None
        """
        # Só busca para liquidações (códigos 06, 10, 17)
        if item.codigo_ocorrencia not in ('06', '10', '17'):
            return None

        # Verifica se há data de ocorrência
        if not item.data_ocorrencia:
            return None

        # Tolerância de valor: R$ 0,02
        valor_cnab = float(item.valor_pago or 0)
        tolerancia = 0.02

        # Query base: mesma data + mesmo valor aproximado + não conciliado
        query = db.session.query(ExtratoItem).join(ExtratoLote).filter(
            ExtratoItem.data_transacao == item.data_ocorrencia,
            ExtratoItem.valor.between(valor_cnab - tolerancia, valor_cnab + tolerancia),
            ExtratoItem.status != 'CONCILIADO',
            ExtratoLote.tipo_transacao == 'entrada',  # Apenas recebimentos
        )

        # Filtrar por CNPJ se disponível
        cnpj_cnab = self._normalizar_cnpj(item.cnpj_pagador)

        if cnpj_cnab and len(cnpj_cnab) >= 8:
            # Primeiro: CNPJ exato
            extrato = query.filter(
                db.func.regexp_replace(ExtratoItem.cnpj_pagador, '[^0-9]', '', 'g') == cnpj_cnab
            ).first()

            if extrato:
                return extrato

            # Segundo: CNPJ raiz (8 primeiros dígitos - grupo empresarial)
            raiz_cnpj = cnpj_cnab[:8]
            extrato = query.filter(
                db.func.left(
                    db.func.regexp_replace(ExtratoItem.cnpj_pagador, '[^0-9]', '', 'g'),
                    8
                ) == raiz_cnpj
            ).first()

            if extrato:
                return extrato

        # Terceiro: Apenas data + valor (sem filtro de CNPJ)
        return query.first()

    def _executar_matching_extrato(self, item: CnabRetornoItem) -> None:
        """
        Tenta vincular item CNAB com linha de extrato bancário.

        Pré-requisitos:
        - Item deve ter match com título (status_match == 'MATCH_ENCONTRADO')
        - Item não deve estar processado

        Args:
            item: CnabRetornoItem para processar
        """
        # Só processa se já tem match com título
        if item.status_match != 'MATCH_ENCONTRADO':
            item.status_match_extrato = 'NAO_APLICAVEL'
            return

        # Buscar extrato correspondente
        extrato = self._buscar_extrato_correspondente(item)

        if extrato:
            # Vinculação encontrada
            item.extrato_item_id = extrato.id
            item.status_match_extrato = 'MATCH_ENCONTRADO'

            # Calcular score baseado no critério de match
            cnpj_cnab = self._normalizar_cnpj(item.cnpj_pagador)
            cnpj_extrato = self._normalizar_cnpj(extrato.cnpj_pagador)

            if cnpj_cnab and cnpj_extrato:
                if cnpj_cnab == cnpj_extrato:
                    item.match_score_extrato = 100
                    item.match_criterio_extrato = 'DATA+VALOR+CNPJ_EXATO'
                elif len(cnpj_cnab) >= 8 and len(cnpj_extrato) >= 8 and cnpj_cnab[:8] == cnpj_extrato[:8]:
                    item.match_score_extrato = 95
                    item.match_criterio_extrato = 'DATA+VALOR+CNPJ_RAIZ'
                else:
                    item.match_score_extrato = 85
                    item.match_criterio_extrato = 'DATA+VALOR_CNPJ_DIVERGENTE'
            else:
                item.match_score_extrato = 85
                item.match_criterio_extrato = 'DATA+VALOR_SEM_CNPJ'
        else:
            # Nenhum extrato encontrado
            item.status_match_extrato = 'SEM_MATCH'

    def baixar_titulo_e_extrato(self, item: CnabRetornoItem, usuario: str = None) -> Dict[str, Any]:
        """
        Executa baixa unificada: Título + Extrato + Odoo.

        Operações realizadas:
        1. Marca título como pago (ContasAReceber.parcela_paga = True)
        2. Concilia linha do extrato (ExtratoItem.status = 'CONCILIADO')
        3. (Opcional) Cria reconciliação no Odoo via ExtratoConciliacaoService

        Args:
            item: CnabRetornoItem com match encontrado
            usuario: Nome do usuário executando a operação

        Returns:
            Dict com resultado: {
                'success': bool,
                'titulo': bool,  # Se baixou título
                'extrato': bool,  # Se conciliou extrato
                'odoo': bool,  # Se reconciliou no Odoo
                'mensagem': str
            }
        """
        resultado = {
            'success': False,
            'titulo': False,
            'extrato': False,
            'odoo': False,
            'mensagem': ''
        }

        # Validações iniciais
        if item.processado:
            resultado['mensagem'] = 'Item já foi processado anteriormente'
            return resultado

        if not item.conta_a_receber_id:
            resultado['mensagem'] = 'Item não possui título vinculado'
            return resultado

        try:
            # 1. Baixar título (ContasAReceber)
            titulo = item.conta_a_receber
            if titulo and not titulo.parcela_paga:
                titulo.parcela_paga = True
                titulo.status_pagamento_odoo = 'PAGO_CNAB'

                # Construir observação detalhada
                obs_parts = [
                    "Baixa via CNAB400",
                    f"Ocorrência: {item.codigo_ocorrencia} ({item.descricao_ocorrencia})",
                    f"Data: {item.data_ocorrencia.strftime('%d/%m/%Y') if item.data_ocorrencia else 'N/D'}",
                ]
                if item.valor_pago:
                    obs_parts.append(f"Valor Pago: R$ {item.valor_pago:,.2f}")
                if item.lote:
                    obs_parts.append(f"Arquivo: {item.lote.arquivo_nome}")

                titulo.observacao = ' | '.join(obs_parts)
                resultado['titulo'] = True

            # 2. Conciliar extrato (se vinculado)
            if item.extrato_item_id:
                extrato = item.extrato_item

                if extrato:
                    # Vincular título ao extrato (se não estiver)
                    if not extrato.titulo_receber_id and item.conta_a_receber_id:
                        extrato.titulo_receber_id = item.conta_a_receber_id
                        extrato.titulo_nf = titulo.titulo_nf if titulo else None
                        extrato.titulo_parcela = titulo.parcela if titulo else None
                        extrato.titulo_valor = float(titulo.valor_titulo) if titulo and titulo.valor_titulo else None
                        extrato.titulo_cliente = titulo.raz_social_red or titulo.raz_social if titulo else None
                        extrato.titulo_cnpj = titulo.cnpj if titulo else None

                    # Atualizar status do extrato
                    extrato.status = 'CONCILIADO'
                    extrato.status_match = 'MATCH_ENCONTRADO'
                    extrato.match_score = item.match_score_extrato
                    extrato.match_criterio = f'VIA_CNAB+{item.match_criterio_extrato or "MANUAL"}'
                    extrato.aprovado = True
                    extrato.aprovado_por = usuario or 'CNAB_AUTO'
                    extrato.aprovado_em = datetime.utcnow()
                    extrato.processado_em = datetime.utcnow()
                    extrato.mensagem = f"Conciliado via CNAB400 - Lote {item.lote_id}"

                    resultado['extrato'] = True

                    # 3. Reconciliar no Odoo (se tiver IDs necessários)
                    if extrato.statement_line_id and titulo and getattr(titulo, 'move_line_id', None):
                        try:
                            from app.financeiro.services.extrato_conciliacao_service import ExtratoConciliacaoService
                            conciliador = ExtratoConciliacaoService()
                            odoo_result = conciliador.conciliar_item(extrato.id, usuario=usuario)
                            resultado['odoo'] = odoo_result.get('success', False)
                        except ImportError:
                            # Service não disponível
                            pass
                        except Exception as e:
                            # Erro no Odoo não bloqueia a baixa local
                            item.erro_mensagem = f"Erro Odoo (não crítico): {str(e)}"

            # 4. Marcar CNAB como processado
            item.processado = True
            item.data_processamento = datetime.utcnow()
            item.status_match = 'PROCESSADO'

            if resultado['extrato']:
                item.status_match_extrato = 'CONCILIADO'

            db.session.commit()

            resultado['success'] = True
            resultado['mensagem'] = 'Baixa executada com sucesso'

            return resultado

        except Exception as e:
            db.session.rollback()
            resultado['mensagem'] = f'Erro ao executar baixa: {str(e)}'
            item.erro_mensagem = resultado['mensagem']
            item.status_match = 'ERRO'
            return resultado

    def baixar_lote_unificado(self, lote: CnabRetornoLote, usuario: str = None) -> Dict[str, Any]:
        """
        Executa baixa unificada de todos os itens elegíveis do lote.

        Esta versão estendida:
        1. Baixa títulos de ContasAReceber
        2. Concilia linhas de ExtratoItem (se vinculadas)
        3. Reconcilia no Odoo (se disponível)

        Args:
            lote: CnabRetornoLote a processar
            usuario: Nome do usuário executando a operação

        Returns:
            Dict com estatísticas: {
                'total': N,
                'sucesso': N,
                'erros': N,
                'titulos_baixados': N,
                'extratos_conciliados': N,
                'odoo_reconciliados': N
            }
        """
        stats = {
            'total': 0,
            'sucesso': 0,
            'erros': 0,
            'titulos_baixados': 0,
            'extratos_conciliados': 0,
            'odoo_reconciliados': 0
        }

        lote.status = 'PROCESSANDO'
        db.session.commit()

        # Buscar itens elegíveis para baixa
        itens = CnabRetornoItem.query.filter(
            CnabRetornoItem.lote_id == lote.id,
            CnabRetornoItem.status_match == 'MATCH_ENCONTRADO',
            CnabRetornoItem.processado == False,
        ).all()

        stats['total'] = len(itens)

        for item in itens:
            try:
                resultado = self.baixar_titulo_e_extrato(item, usuario)

                if resultado['success']:
                    stats['sucesso'] += 1
                    if resultado['titulo']:
                        stats['titulos_baixados'] += 1
                    if resultado['extrato']:
                        stats['extratos_conciliados'] += 1
                    if resultado['odoo']:
                        stats['odoo_reconciliados'] += 1
                else:
                    stats['erros'] += 1
                    item.erro_mensagem = resultado.get('mensagem', 'Erro desconhecido')

            except Exception as e:
                item.erro_mensagem = str(e)
                item.status_match = 'ERRO'
                stats['erros'] += 1

        # Atualizar estatísticas do lote
        lote.atualizar_estatisticas()

        # Definir status final
        if stats['erros'] == 0 and stats['sucesso'] > 0:
            lote.status = 'CONCLUIDO'
        elif stats['sucesso'] > 0:
            lote.status = 'PARCIAL'
        elif stats['total'] == 0:
            lote.status = 'APROVADO'  # Nenhum item para processar
        else:
            lote.status = 'ERRO'

        db.session.commit()
        return stats

    def executar_matching_extrato_lote(self, lote: CnabRetornoLote) -> Dict[str, int]:
        """
        Executa matching com extrato para todos os itens do lote que têm título vinculado.

        Deve ser chamado APÓS o matching de títulos.

        Args:
            lote: CnabRetornoLote

        Returns:
            Dict com estatísticas: {'com_match': N, 'sem_match': N, 'nao_aplicavel': N}
        """
        stats = {'com_match': 0, 'sem_match': 0, 'nao_aplicavel': 0}

        itens = CnabRetornoItem.query.filter(
            CnabRetornoItem.lote_id == lote.id,
            CnabRetornoItem.status_match == 'MATCH_ENCONTRADO',
            CnabRetornoItem.processado == False,
        ).all()

        for item in itens:
            self._executar_matching_extrato(item)

            if item.status_match_extrato == 'MATCH_ENCONTRADO':
                stats['com_match'] += 1
            elif item.status_match_extrato == 'SEM_MATCH':
                stats['sem_match'] += 1
            else:
                stats['nao_aplicavel'] += 1

        db.session.commit()
        return stats
