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
import hashlib
import logging

from app import db

logger = logging.getLogger(__name__)
from app.financeiro.models import (
    CnabRetornoLote,
    CnabRetornoItem,
    ContasAReceber,
    ExtratoItem,
    ExtratoLote
)
from app.faturamento.models import FaturamentoProduto
from app.financeiro.services.cnab400_parser_service import Cnab400ParserService


class Cnab400ProcessorService:
    """Processa arquivo CNAB400 e vincula com Contas a Receber"""

    def __init__(self):
        self.parser = Cnab400ParserService()

    def processar_arquivo(
        self,
        arquivo_conteudo: str,
        arquivo_nome: str,
        usuario: str,
        batch_id: str = None
    ) -> CnabRetornoLote:
        """
        Processa arquivo CNAB400 completo.

        Args:
            arquivo_conteudo: Conteúdo do arquivo .ret (encoding latin-1)
            arquivo_nome: Nome do arquivo para registro
            usuario: Nome do usuário que está processando
            batch_id: UUID do batch (para uploads múltiplos via job assíncrono)

        Returns:
            CnabRetornoLote criado com todos os itens processados

        Raises:
            ValueError: Se arquivo inválido ou já importado anteriormente
        """
        # =====================================================
        # CORREÇÃO #3: VERIFICAÇÃO DE DUPLICAÇÃO
        # Evita importar o mesmo arquivo múltiplas vezes
        # =====================================================

        # 1. Calcular hash SHA256 do conteúdo
        hash_arquivo = hashlib.sha256(arquivo_conteudo.encode('latin-1', errors='replace')).hexdigest()

        # 2. Verificar se já existe lote com mesmo hash
        lote_existente_hash = CnabRetornoLote.query.filter(
            CnabRetornoLote.hash_arquivo == hash_arquivo
        ).first()

        if lote_existente_hash:
            raise ValueError(
                f"Arquivo com mesmo conteúdo já foi importado anteriormente. "
                f"Lote #{lote_existente_hash.id} - "
                f"{lote_existente_hash.arquivo_nome} em "
                f"{lote_existente_hash.data_processamento.strftime('%d/%m/%Y %H:%M') if lote_existente_hash.data_processamento else 'N/D'}"
            )

        # 3. Parse do arquivo
        dados = self.parser.parse_arquivo(arquivo_conteudo)

        if not dados['header']:
            raise ValueError("Arquivo inválido: header não encontrado")

        # 4. Verificar se já existe lote com mesmo nome + banco + data
        # (verificação secundária para casos onde hash possa diferir por encoding)
        lote_existente_nome = CnabRetornoLote.query.filter(
            CnabRetornoLote.arquivo_nome == arquivo_nome,
            CnabRetornoLote.banco_codigo == dados['header']['codigo_banco'],
            CnabRetornoLote.data_arquivo == dados['header']['data_arquivo'],
        ).first()

        if lote_existente_nome:
            raise ValueError(
                f"Arquivo '{arquivo_nome}' já foi importado para este banco/data. "
                f"Lote #{lote_existente_nome.id} em "
                f"{lote_existente_nome.data_processamento.strftime('%d/%m/%Y %H:%M') if lote_existente_nome.data_processamento else 'N/D'}"
            )

        # 5. Criar lote (com hash para futuras verificações)
        lote = CnabRetornoLote(
            arquivo_nome=arquivo_nome,
            banco_codigo=dados['header']['codigo_banco'],
            banco_nome=dados['header']['nome_banco'],
            data_arquivo=dados['header']['data_arquivo'],
            total_registros=len(dados['detalhes']),
            processado_por=usuario,
            status='IMPORTADO',
            hash_arquivo=hash_arquivo,  # Hash para verificação de duplicação
            batch_id=batch_id  # UUID do batch para uploads múltiplos
        )
        db.session.add(lote)
        db.session.flush()  # Gera ID do lote

        # 6. Processar cada detalhe
        for detalhe in dados['detalhes']:
            item = self._criar_item(lote, detalhe)
            self._executar_matching(item)

            # CORREÇÃO #5: Também executar match com extrato automaticamente
            # Isso garante que o vínculo CNAB↔Extrato acontece durante a importação
            # NOTA: SEM_MATCH já é tratado dentro de _executar_matching() via
            # _executar_matching_extrato_sem_titulo() - NÃO chamar aqui para
            # evitar sobrescrever o status_match_extrato já definido
            if item.status_match in ('MATCH_ENCONTRADO', 'JA_PAGO'):
                self._executar_matching_extrato(item)

                # SIMPLIFICAÇÃO DO FLUXO (21/01/2026):
                # Baixa automática se título E extrato estão vinculados
                # Isso elimina necessidade de botões manuais na tela
                if item.conta_a_receber_id and item.extrato_item_id:
                    self._executar_baixa_automatica(item, usuario)

        # 7. Atualizar estatísticas do lote
        lote.atualizar_estatisticas()

        # 8. Definir status baseado nos resultados
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
            data_credito=detalhe.get('data_credito'),  # Data do crédito na conta (usada para match)
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
            # CORREÇÃO #7: Mesmo sem título local, tentar vincular com extrato
            # para manter rastreabilidade e permitir conciliação manual
            self._executar_matching_extrato_sem_titulo(item)
            return

        # 5. Verificar se já está pago
        # =====================================================
        # FASE 4: RASTREABILIDADE COMPLETA
        # Mesmo quando título já pago, NÃO retornamos aqui.
        # Continuamos para buscar extrato e criar vínculos para rastreabilidade.
        # O vínculo CNAB ↔ Título ↔ Extrato é REAL independente da ordem de importação.
        # =====================================================
        if titulo.parcela_paga:
            item.status_match = 'JA_PAGO'
            item.conta_a_receber_id = titulo.id
            item.match_score = 100
            item.match_criterio = 'NF_PARCELA_EXATO'
            item.erro_mensagem = 'Título já estava pago anteriormente'
            # NÃO RETORNA - continua para buscar extrato vinculado para rastreabilidade
        else:
            # 6. Match encontrado! (título ainda não pago)
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

    def _buscar_cnpj_cliente(self, item: CnabRetornoItem) -> Optional[str]:
        """
        Busca CNPJ do cliente com fallback.

        CORREÇÃO #11: O CNAB BMP 274 contém CNPJ da empresa, não do cliente.
        Precisamos buscar o CNPJ do cliente de outras fontes.

        Ordem de busca:
        1. ContasAReceber (via conta_a_receber_id) - título vinculado
        2. FaturamentoProduto (via nf_extraida) - fallback por NF

        Args:
            item: CnabRetornoItem para buscar CNPJ do cliente

        Returns:
            CNPJ normalizado (apenas dígitos) ou None
        """
        # FASE 1: Buscar em ContasAReceber (título vinculado) - mais confiável
        if item.conta_a_receber_id:
            titulo = db.session.get(ContasAReceber, item.conta_a_receber_id)
            if titulo and titulo.cnpj:
                return self._normalizar_cnpj(titulo.cnpj)

        # FASE 2: Fallback para FaturamentoProduto (por NF)
        # Útil quando título não existe localmente mas temos a NF
        if item.nf_extraida:
            faturamento = FaturamentoProduto.query.filter(
                FaturamentoProduto.numero_nf == item.nf_extraida,
                FaturamentoProduto.status_nf != 'Cancelado'
            ).first()
            if faturamento and faturamento.cnpj_cliente:
                return self._normalizar_cnpj(faturamento.cnpj_cliente)

        return None

    def _buscar_extrato_correspondente(self, item: CnabRetornoItem) -> Optional[ExtratoItem]:
        """
        Busca linha de extrato que corresponde ao item CNAB.

        CORREÇÃO #10 e #11:
        - Usa data_credito (data do crédito na conta) para match com extrato
        - Busca CNPJ do cliente via título ou FaturamentoProduto (fallback)
        - O CNAB BMP 274 NÃO contém CNPJ do pagador (contém o da empresa)

        Prioridade de Busca:
        1. Extrato que já tem o MESMO título vinculado (mais confiável)
        2. DATA_CREDITO + VALOR + CNPJ do cliente
        3. DATA_CREDITO + VALOR apenas (se único candidato)

        Score de Confiança:
        - 100: Match via título já vinculado
        - 95: Data crédito + Valor + CNPJ do cliente
        - 85: Data crédito + Valor apenas (único candidato)

        Args:
            item: CnabRetornoItem para buscar correspondência

        Returns:
            ExtratoItem encontrado ou None
        """
        # Só busca para liquidações (códigos 06, 10, 17)
        if item.codigo_ocorrencia not in ('06', '10', '17'):
            return None

        # CORREÇÃO #10: Usar data_credito (data do crédito na conta)
        # Fallback para data_ocorrencia se data_credito não estiver disponível
        data_match = item.data_credito or item.data_ocorrencia
        if not data_match:
            return None

        # Tolerância de valor: R$ 0,02
        valor_cnab = float(item.valor_pago or 0)
        tolerancia = 0.02

        # =====================================================
        # FASE 1: Buscar extrato que já tem o MESMO título vinculado
        # Este é o match mais confiável pois o vínculo já existe
        # =====================================================
        if item.conta_a_receber_id:
            extrato = db.session.query(ExtratoItem).join(ExtratoLote).filter(
                ExtratoItem.titulo_receber_id == item.conta_a_receber_id,
                ExtratoItem.status != 'CONCILIADO',
                ExtratoLote.tipo_transacao == 'entrada',
            ).first()
            if extrato:
                return extrato

        # =====================================================
        # FASE 2: DATA_CREDITO + VALOR + CNPJ do CLIENTE
        # CORREÇÃO #11: Busca CNPJ via método com fallback
        # =====================================================
        cnpj_cliente = self._buscar_cnpj_cliente(item)

        # Query base: mesma data de crédito + mesmo valor aproximado + não conciliado
        # CORREÇÃO #12: Excluir extratos já vinculados a outros CNABs
        # Isso previne que 2 CNABs encontrem o mesmo extrato quando há 2 disponíveis
        subquery_vinculados = db.session.query(CnabRetornoItem.extrato_item_id).filter(
            CnabRetornoItem.extrato_item_id.isnot(None),
            CnabRetornoItem.id != item.id  # Permite encontrar extrato que o próprio item já tem
        ).scalar_subquery()

        query = db.session.query(ExtratoItem).join(ExtratoLote).filter(
            ExtratoItem.data_transacao == data_match,
            ExtratoItem.valor.between(valor_cnab - tolerancia, valor_cnab + tolerancia),
            ExtratoItem.status != 'CONCILIADO',
            ExtratoLote.tipo_transacao == 'entrada',
            ~ExtratoItem.id.in_(subquery_vinculados),  # Excluir já vinculados a outros CNABs
        )

        # Se temos CNPJ do cliente (via título), filtrar por ele
        if cnpj_cliente and len(cnpj_cliente) >= 8:
            # CNPJ exato
            extrato = query.filter(
                db.func.regexp_replace(ExtratoItem.cnpj_pagador, '[^0-9]', '', 'g') == cnpj_cliente
            ).first()

            if extrato:
                return extrato

            # CNPJ raiz (8 primeiros dígitos - grupo empresarial)
            raiz_cnpj = cnpj_cliente[:8]
            extrato = query.filter(
                db.func.left(
                    db.func.regexp_replace(ExtratoItem.cnpj_pagador, '[^0-9]', '', 'g'),
                    8
                ) == raiz_cnpj
            ).first()

            if extrato:
                return extrato

        # =====================================================
        # FASE 3: Fallback - apenas DATA + VALOR
        # Só aceita se houver ÚNICO candidato (evita match ambíguo)
        # =====================================================
        candidatos = query.all()
        if len(candidatos) == 1:
            return candidatos[0]
        elif len(candidatos) > 1:
            # Múltiplos candidatos - NÃO vincular para evitar erro
            logger.warning(
                f"CNAB {item.id} NF {item.nf_extraida}/{item.parcela_extraida}: "
                f"{len(candidatos)} extratos candidatos (data={item.data_ocorrencia}, "
                f"valor={valor_cnab}) - match ambíguo, não vinculando"
            )
            return None

        return None

    def _buscar_extrato_correspondente_para_rastreabilidade(
        self,
        item: CnabRetornoItem
    ) -> Optional[ExtratoItem]:
        """
        Busca extrato correspondente para rastreabilidade.
        INCLUI extratos já conciliados pois o vínculo é REAL.

        Esta versão é usada quando o título já foi pago (status_match == 'JA_PAGO').
        Como queremos manter a rastreabilidade completa (CNAB ↔ Título ↔ Extrato),
        precisamos encontrar o extrato mesmo que já tenha sido conciliado anteriormente.

        CORREÇÃO #10 e #11:
        - Usa data_credito (data do crédito na conta) para match
        - Busca CNPJ do cliente via título ou FaturamentoProduto (fallback)

        Prioridade de busca:
        1. Extrato que já tem o mesmo título vinculado (titulo_receber_id)
        2. Extrato com mesmo CNPJ do cliente + Data crédito + Valor
        3. Extrato com Data crédito + Valor (sem CNPJ)

        Args:
            item: CnabRetornoItem para buscar correspondência

        Returns:
            ExtratoItem encontrado ou None
        """
        # Só busca para liquidações (códigos 06, 10, 17)
        if item.codigo_ocorrencia not in ('06', '10', '17'):
            return None

        # CORREÇÃO #10: Usar data_credito (data do crédito na conta)
        # Fallback para data_ocorrencia se data_credito não estiver disponível
        data_match = item.data_credito or item.data_ocorrencia
        if not data_match:
            return None

        # Tolerância de valor: R$ 0,02
        valor_cnab = float(item.valor_pago or 0)
        tolerancia = 0.02

        # Query base: mesma data de crédito + mesmo valor aproximado
        # DIFERENÇA: NÃO filtra por status != 'CONCILIADO'
        # CORREÇÃO #12: Excluir extratos já vinculados a outros CNABs
        subquery_vinculados = db.session.query(CnabRetornoItem.extrato_item_id).filter(
            CnabRetornoItem.extrato_item_id.isnot(None),
            CnabRetornoItem.id != item.id  # Permite encontrar extrato que o próprio item já tem
        ).scalar_subquery()

        query = db.session.query(ExtratoItem).join(ExtratoLote).filter(
            ExtratoItem.data_transacao == data_match,
            ExtratoItem.valor.between(valor_cnab - tolerancia, valor_cnab + tolerancia),
            # SEM: ExtratoItem.status != 'CONCILIADO' - inclui conciliados para rastreabilidade
            ExtratoLote.tipo_transacao == 'entrada',  # Apenas recebimentos
            ~ExtratoItem.id.in_(subquery_vinculados),  # Excluir já vinculados a outros CNABs
        )

        # PRIORIDADE 1: Se título está vinculado, buscar extrato que tem esse título
        # Este é o critério mais confiável pois o vínculo já existe
        if item.conta_a_receber_id:
            extrato = query.filter(
                ExtratoItem.titulo_receber_id == item.conta_a_receber_id
            ).first()
            if extrato:
                return extrato

        # PRIORIDADE 2: Buscar por CNPJ do cliente
        # CORREÇÃO #11: Usa método com fallback (título → FaturamentoProduto)
        cnpj_cliente = self._buscar_cnpj_cliente(item)

        if cnpj_cliente and len(cnpj_cliente) >= 8:
            # CNPJ exato
            extrato = query.filter(
                db.func.regexp_replace(ExtratoItem.cnpj_pagador, '[^0-9]', '', 'g') == cnpj_cliente
            ).first()

            if extrato:
                return extrato

            # CNPJ raiz (8 primeiros dígitos - grupo empresarial)
            raiz_cnpj = cnpj_cliente[:8]
            extrato = query.filter(
                db.func.left(
                    db.func.regexp_replace(ExtratoItem.cnpj_pagador, '[^0-9]', '', 'g'),
                    8
                ) == raiz_cnpj
            ).first()

            if extrato:
                return extrato

        # PRIORIDADE 3: Apenas data de crédito + valor (sem filtro de CNPJ)
        return query.first()

    def _executar_matching_extrato(self, item: CnabRetornoItem) -> None:
        """
        Tenta vincular item CNAB com linha de extrato bancário.

        =====================================================
        FASE 4: RASTREABILIDADE COMPLETA
        Agora aceita tanto MATCH_ENCONTRADO quanto JA_PAGO.
        Para JA_PAGO, busca incluindo extratos já conciliados,
        mantendo a rastreabilidade completa independente da ordem.
        =====================================================

        Pré-requisitos:
        - Item deve ter match com título (MATCH_ENCONTRADO ou JA_PAGO)
        - Item não deve estar processado

        Args:
            item: CnabRetornoItem para processar
        """
        # Só processa se tem match com título (ENCONTRADO ou JA_PAGO)
        # FASE 4: Agora aceita JA_PAGO para manter rastreabilidade
        if item.status_match not in ('MATCH_ENCONTRADO', 'JA_PAGO'):
            item.status_match_extrato = 'NAO_APLICAVEL'
            return

        # Escolher função de busca apropriada baseada no status
        if item.status_match == 'JA_PAGO':
            # Para títulos já pagos, busca INCLUINDO extratos conciliados
            # pois o vínculo é REAL independente de quando foi feita a baixa
            extrato = self._buscar_extrato_correspondente_para_rastreabilidade(item)
        else:
            # Para títulos pendentes, busca apenas extratos não conciliados
            extrato = self._buscar_extrato_correspondente(item)

        if extrato:
            # =====================================================
            # CORREÇÃO #2: VERIFICAR DUPLICATA ANTES DE VINCULAR
            # Impede match 2:1 (2 CNABs → 1 Extrato)
            # =====================================================
            cnab_existente = CnabRetornoItem.query.filter(
                CnabRetornoItem.extrato_item_id == extrato.id,
                CnabRetornoItem.id != item.id
            ).first()

            if cnab_existente:
                # Extrato já vinculado a outro CNAB - NÃO vincular novamente
                item.status_match_extrato = 'ERRO_MATCH_DUPLICADO'
                item.match_criterio_extrato = f'EXTRATO_JA_VINCULADO_CNAB_{cnab_existente.id}'
                logger.warning(
                    f"CNAB {item.id} NF {item.nf_extraida}/{item.parcela_extraida}: "
                    f"Extrato {extrato.id} já vinculado ao CNAB {cnab_existente.id} - match negado"
                )
                return

            # Vinculação encontrada e permitida
            item.extrato_item_id = extrato.id

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

            # =====================================================
            # FASE 4: VINCULAÇÃO BIDIRECIONAL COM TRATAMENTO DE
            # EXTRATOS JÁ CONCILIADOS
            # =====================================================
            if extrato.status == 'CONCILIADO':
                # Extrato já conciliado - apenas vincula para rastreabilidade
                # NÃO altera status do extrato (já está CONCILIADO)
                item.status_match_extrato = 'VINCULADO_RASTREABILIDADE'
                item.match_criterio_extrato = f'EXTRATO_JA_CONCILIADO+{item.match_criterio_extrato}'
                # Não altera extrato.status_match pois já está finalizado
            else:
                # Extrato pendente - vincula e prepara para conciliação
                item.status_match_extrato = 'MATCH_ENCONTRADO'

                # CORREÇÃO #1: VINCULAÇÃO BIDIRECIONAL
                # Atualiza o ExtratoItem para registrar que foi vinculado via CNAB
                extrato.status_match = 'MATCH_ENCONTRADO'
                extrato.match_criterio = f'VIA_CNAB_{item.match_criterio_extrato}'
                extrato.match_score = item.match_score_extrato

                # =====================================================
                # CORREÇÃO #13: COPIAR INFORMAÇÕES DO TÍTULO PARA EXTRATO
                # Quando CNAB tem título vinculado, copiar dados para o extrato
                # para que a tela de extrato mostre o título corretamente.
                # NOTA: Campos do modelo ContasAReceber:
                # - valor_titulo (não 'valor')
                # - vencimento (não 'data_vencimento')
                # - parcela é VARCHAR mas extrato.titulo_parcela é INTEGER
                # =====================================================
                if item.conta_a_receber_id:
                    titulo = db.session.get(ContasAReceber, item.conta_a_receber_id)
                    if titulo:
                        extrato.titulo_receber_id = titulo.id
                        extrato.titulo_nf = titulo.titulo_nf
                        extrato.titulo_parcela = int(titulo.parcela) if titulo.parcela else None
                        extrato.titulo_valor = float(titulo.valor_titulo) if titulo.valor_titulo else None
                        extrato.titulo_vencimento = titulo.vencimento
                        extrato.titulo_cliente = titulo.raz_social
                        extrato.titulo_cnpj = titulo.cnpj
                        logger.info(
                            f"CNAB {item.id}: Título {titulo.id} (NF {titulo.titulo_nf}/{titulo.parcela}) "
                            f"copiado para Extrato {extrato.id}"
                        )
        else:
            # Nenhum extrato encontrado
            item.status_match_extrato = 'SEM_MATCH'

    def _executar_matching_extrato_sem_titulo(self, item: CnabRetornoItem) -> None:
        """
        Tenta vincular CNAB com extrato mesmo quando título não existe localmente.

        CORREÇÃO #7: Usado para manter rastreabilidade quando título não foi
        sincronizado do Odoo mas extrato existe.

        CORREÇÃO #10: Usa data_credito (data do crédito na conta) para match.

        Critérios de match:
        - DATA_CREDITO EXATA (data_credito == data_transacao)
        - VALOR aproximado (±R$0,02)
        - CNPJ do cliente via FaturamentoProduto (fallback - se disponível)
        - Só aceita se houver ÚNICO candidato (evita match ambíguo)

        Score de confiança: 60 (baixo - sem título para validar)

        Args:
            item: CnabRetornoItem para processar
        """
        # Só processa liquidações (códigos 06, 10, 17)
        if item.codigo_ocorrencia not in ('06', '10', '17'):
            item.status_match_extrato = 'NAO_APLICAVEL'
            return

        # CORREÇÃO #10: Usar data_credito (data do crédito na conta)
        # Fallback para data_ocorrencia se data_credito não estiver disponível
        data_match = item.data_credito or item.data_ocorrencia
        if not data_match or not item.valor_pago:
            item.status_match_extrato = 'NAO_APLICAVEL'
            return

        # Tolerância de valor: R$ 0,02
        valor_cnab = float(item.valor_pago)
        tolerancia = 0.02

        # CORREÇÃO #11: Tentar obter CNPJ do cliente via FaturamentoProduto
        cnpj_cliente = self._buscar_cnpj_cliente(item)

        # Buscar extratos por DATA_CREDITO + VALOR
        # CORREÇÃO #12: Excluir extratos já vinculados a outros CNABs
        subquery_vinculados = db.session.query(CnabRetornoItem.extrato_item_id).filter(
            CnabRetornoItem.extrato_item_id.isnot(None),
            CnabRetornoItem.id != item.id
        ).scalar_subquery()

        query = db.session.query(ExtratoItem).join(ExtratoLote).filter(
            ExtratoItem.data_transacao == data_match,
            ExtratoItem.valor.between(valor_cnab - tolerancia, valor_cnab + tolerancia),
            ExtratoItem.status != 'CONCILIADO',
            ExtratoLote.tipo_transacao == 'entrada',  # Apenas recebimentos
            ~ExtratoItem.id.in_(subquery_vinculados),  # Excluir já vinculados
        )

        # Se temos CNPJ do cliente (via FaturamentoProduto), filtrar por ele primeiro
        if cnpj_cliente and len(cnpj_cliente) >= 8:
            candidatos_cnpj = query.filter(
                db.func.regexp_replace(ExtratoItem.cnpj_pagador, '[^0-9]', '', 'g') == cnpj_cliente
            ).all()
            if len(candidatos_cnpj) == 1:
                # Match único com CNPJ - mais confiável
                candidatos = candidatos_cnpj
            else:
                # Fallback: todos os candidatos por data+valor
                candidatos = query.all()
        else:
            candidatos = query.all()

        if len(candidatos) == 1:
            extrato = candidatos[0]

            # =====================================================
            # VERIFICAR DUPLICATA: Extrato já vinculado a outro CNAB?
            # =====================================================
            cnab_existente = CnabRetornoItem.query.filter(
                CnabRetornoItem.extrato_item_id == extrato.id,
                CnabRetornoItem.id != item.id
            ).first()

            if cnab_existente:
                item.status_match_extrato = 'ERRO_MATCH_DUPLICADO'
                item.match_criterio_extrato = f'EXTRATO_JA_VINCULADO_CNAB_{cnab_existente.id}'
                logger.warning(
                    f"CNAB {item.id} NF {item.nf_extraida}/{item.parcela_extraida}: "
                    f"Extrato {extrato.id} já vinculado ao CNAB {cnab_existente.id} - match negado"
                )
                return

            # Vincular com score baixo (sem título para validar)
            item.extrato_item_id = extrato.id
            item.status_match_extrato = 'MATCH_SEM_TITULO'
            item.match_score_extrato = 60  # Score baixo - sem validação de título
            item.match_criterio_extrato = 'DATA+VALOR_SEM_TITULO_LOCAL'

            # Atualizar extrato para indicar que tem match pendente
            extrato.status_match = 'MATCH_CNAB_PENDENTE'
            extrato.match_criterio = 'VIA_CNAB_SEM_TITULO'
            extrato.match_score = 60

            logger.info(
                f"CNAB {item.id} NF {item.nf_extraida}/{item.parcela_extraida}: "
                f"Match com extrato {extrato.id} SEM título local "
                f"(data={item.data_ocorrencia}, valor={valor_cnab}) - requer validação manual"
            )

        elif len(candidatos) > 1:
            # Múltiplos candidatos - NÃO vincular (ambíguo)
            item.status_match_extrato = 'SEM_MATCH'
            item.match_criterio_extrato = f'MATCH_AMBIGUO_{len(candidatos)}_CANDIDATOS'
            logger.warning(
                f"CNAB {item.id} NF {item.nf_extraida}/{item.parcela_extraida}: "
                f"{len(candidatos)} extratos candidatos (data={item.data_ocorrencia}, "
                f"valor={valor_cnab}) - match ambíguo SEM título, não vinculando"
            )
        else:
            # Nenhum extrato encontrado
            item.status_match_extrato = 'SEM_MATCH'
            item.match_criterio_extrato = 'EXTRATO_NAO_ENCONTRADO_SEM_TITULO'

    def _executar_baixa_automatica(self, item: CnabRetornoItem, usuario: str = None) -> bool:
        """
        Executa baixa automática quando CNAB tem título E extrato vinculados.

        SIMPLIFICAÇÃO DO FLUXO (21/01/2026):
        - Baixa automática durante importação CNAB
        - Gera log para auditoria
        - Não requer intervenção manual

        CORREÇÃO 21/01/2026 (Bug extrato sem conciliação Odoo):
        - Ordem corrigida: Odoo PRIMEIRO, status local DEPOIS
        - Se Odoo falhar, NÃO marca como CONCILIADO/processado
        - Permite reprocessamento posterior

        Operações (ORDEM CORRIGIDA):
        1. Carrega título e extrato
        2. Vincular título ao extrato (se necessário)
        3. PRIMEIRO: Reconcilia no Odoo (se disponível)
        4. SÓ SE ODOO OK: Marca título como pago
        5. SÓ SE ODOO OK: Marca extrato como CONCILIADO
        6. SÓ SE ODOO OK: Marca item CNAB como processado
        7. Gera log para auditoria

        Args:
            item: CnabRetornoItem com título e extrato vinculados
            usuario: Nome do usuário/sistema executando

        Returns:
            bool: True se baixa foi executada com sucesso (incluindo Odoo)
        """
        # Validações - só baixa automaticamente se tiver título E extrato
        if not item.conta_a_receber_id or not item.extrato_item_id:
            return False

        if item.processado:
            return False  # Já foi processado

        try:
            # 1. Carregar título e extrato
            titulo = db.session.get(ContasAReceber, item.conta_a_receber_id)
            extrato = db.session.get(ExtratoItem, item.extrato_item_id)

            if not titulo or not extrato:
                logger.warning(
                    f"[BAIXA_AUTO] CNAB {item.id}: Título ou Extrato não encontrado"
                )
                return False

            # 2. Vincular título ao extrato (se não estiver) - isso pode ser feito antes do Odoo
            if not extrato.titulo_receber_id:
                extrato.titulo_receber_id = titulo.id
                extrato.titulo_nf = titulo.titulo_nf
                extrato.titulo_parcela = int(titulo.parcela) if titulo.parcela else None
                extrato.titulo_valor = float(titulo.valor_titulo) if titulo.valor_titulo else None
                extrato.titulo_vencimento = titulo.vencimento
                extrato.titulo_cliente = titulo.raz_social_red or titulo.raz_social
                extrato.titulo_cnpj = titulo.cnpj

            # 3. PRIMEIRO: Reconciliar no Odoo (se disponível)
            odoo_ok = False
            odoo_error = None

            if extrato.statement_line_id:
                # Tem linha de extrato no Odoo - DEVE reconciliar
                try:
                    from app.financeiro.services.extrato_conciliacao_service import ExtratoConciliacaoService
                    conciliador = ExtratoConciliacaoService()
                    result = conciliador.conciliar_item(extrato)
                    odoo_ok = result.get('success', False)

                    if not odoo_ok:
                        odoo_error = result.get('error', 'Reconciliação retornou success=False')
                        logger.warning(
                            f"[BAIXA_AUTO] CNAB {item.id} NF {item.nf_extraida}/{item.parcela_extraida}: "
                            f"Reconciliação Odoo falhou: {odoo_error}"
                        )
                        # NÃO marcar como processado - permitir reprocessamento
                        item.erro_mensagem = f'Odoo falhou: {odoo_error}'
                        return False

                except Exception as e:
                    odoo_error = str(e)
                    logger.error(
                        f"[BAIXA_AUTO] CNAB {item.id} NF {item.nf_extraida}/{item.parcela_extraida}: "
                        f"Erro ao reconciliar Odoo: {e}"
                    )
                    # NÃO marcar como processado - permitir reprocessamento
                    item.erro_mensagem = f'Erro Odoo: {odoo_error}'
                    return False
            else:
                # Sem statement_line_id - extrato não veio do Odoo, OK prosseguir
                odoo_ok = True  # Considera OK pois não precisa reconciliar
                logger.info(
                    f"[BAIXA_AUTO] CNAB {item.id}: Extrato sem statement_line_id - pulando Odoo"
                )

            # 4. SÓ SE ODOO OK: Baixar título (ContasAReceber)
            if not titulo.parcela_paga:
                titulo.parcela_paga = True
                titulo.status_pagamento_odoo = 'PAGO_CNAB_AUTO'

                # Observação para auditoria
                obs_parts = [
                    "[BAIXA_AUTO] Via CNAB400",
                    f"Ocorrência: {item.codigo_ocorrencia}",
                    f"Data Crédito: {item.data_credito.strftime('%d/%m/%Y') if item.data_credito else 'N/D'}",
                ]
                if item.valor_pago:
                    obs_parts.append(f"Valor: R$ {item.valor_pago:,.2f}")
                if item.lote:
                    obs_parts.append(f"Arquivo: {item.lote.arquivo_nome}")

                titulo.observacao = ' | '.join(obs_parts)

            # 5. SÓ SE ODOO OK: Marcar extrato como conciliado
            if extrato.status != 'CONCILIADO':
                extrato.status = 'CONCILIADO'
                extrato.status_match = 'MATCH_ENCONTRADO'
                extrato.match_score = item.match_score_extrato or 100
                extrato.match_criterio = 'BAIXA_AUTO_VIA_CNAB'
                extrato.aprovado = True
                extrato.aprovado_por = usuario or 'SISTEMA_CNAB_AUTO'
                extrato.aprovado_em = datetime.utcnow()
                extrato.processado_em = datetime.utcnow()
                extrato.mensagem = f"[BAIXA_AUTO] Conciliado via CNAB400 - Lote {item.lote_id}"

            # 6. SÓ SE ODOO OK: Marcar item CNAB como processado
            item.processado = True
            item.data_processamento = datetime.utcnow()
            item.erro_mensagem = None  # Limpar erro anterior se houver

            # 7. Log para auditoria
            logger.info(
                f"[BAIXA_AUTO] CNAB {item.id} NF {item.nf_extraida}/{item.parcela_extraida}: "
                f"Título {titulo.id} baixado, Extrato {extrato.id} conciliado, Odoo reconciliado"
            )

            return True

        except Exception as e:
            logger.error(
                f"[BAIXA_AUTO] CNAB {item.id} NF {item.nf_extraida}/{item.parcela_extraida}: "
                f"Erro na baixa automática: {e}"
            )
            item.erro_mensagem = f'Erro baixa automática: {str(e)}'
            return False

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

                    # =====================================================
                    # CORREÇÃO #2: REMOVER CONDIÇÃO IMPOSSÍVEL move_line_id
                    # ContasAReceber NÃO possui campo move_line_id.
                    # O ExtratoConciliacaoService já busca o move_line_id
                    # no Odoo usando NF+Parcela, então basta ter o statement_line_id.
                    # =====================================================
                    # 3. Reconciliar no Odoo (se tiver statement_line_id)
                    if extrato.statement_line_id and titulo:
                        # =====================================================
                        # CORREÇÃO #3: GARANTIR DADOS COMPLETOS ANTES DE RECONCILIAR
                        # O ExtratoConciliacaoService.conciliar_item() requer:
                        # - titulo_receber_id (para buscar título no Odoo)
                        # - titulo_nf + titulo_parcela (para buscar move_line)
                        # - credit_line_id (para fazer a reconciliação)
                        # =====================================================

                        # Garantir que extrato tem título vinculado
                        if not extrato.titulo_receber_id:
                            extrato.titulo_receber_id = item.conta_a_receber_id
                        if not extrato.titulo_nf and titulo:
                            extrato.titulo_nf = titulo.titulo_nf
                        if not extrato.titulo_parcela and titulo:
                            extrato.titulo_parcela = titulo.parcela

                        # Se não tem credit_line_id, tentar buscar no Odoo
                        if not extrato.credit_line_id and extrato.move_id:
                            try:
                                from app.financeiro.services.extrato_service import ExtratoService
                                extrato_svc = ExtratoService()
                                credit_line = extrato_svc._buscar_linha_credito(extrato.move_id)
                                if credit_line:
                                    extrato.credit_line_id = credit_line
                            except Exception as credit_err:
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.warning(f"Não foi possível buscar credit_line_id para extrato {extrato.id}: {credit_err}")

                        try:
                            from app.financeiro.services.extrato_conciliacao_service import ExtratoConciliacaoService
                            import logging
                            logger = logging.getLogger(__name__)

                            # Log de diagnóstico
                            logger.info(
                                f"[CNAB→ODOO] Tentando reconciliar extrato {extrato.id}: "
                                f"statement_line_id={extrato.statement_line_id}, "
                                f"credit_line_id={extrato.credit_line_id}, "
                                f"titulo_receber_id={extrato.titulo_receber_id}, "
                                f"titulo_nf={extrato.titulo_nf}, "
                                f"titulo_parcela={extrato.titulo_parcela}"
                            )

                            conciliador = ExtratoConciliacaoService()
                            # CORREÇÃO: Passar objeto ExtratoItem, não ID
                            odoo_result = conciliador.conciliar_item(extrato)
                            resultado['odoo'] = odoo_result.get('success', False)

                            if not odoo_result.get('success'):
                                logger.warning(f"[CNAB→ODOO] Falha ao reconciliar extrato {extrato.id}: {odoo_result}")
                            else:
                                logger.info(f"[CNAB→ODOO] Extrato {extrato.id} reconciliado com sucesso no Odoo")

                        except ImportError:
                            # Service não disponível
                            pass
                        except Exception as e:
                            # Erro no Odoo não bloqueia a baixa local
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"[CNAB→ODOO] Erro ao reconciliar extrato {extrato.id} no Odoo: {e}")
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

        =====================================================
        FASE 4: RASTREABILIDADE COMPLETA
        Agora também processa itens JA_PAGO para manter rastreabilidade.
        Novo contador 'vinculado_rastreabilidade' para extratos já conciliados.
        =====================================================

        Deve ser chamado APÓS o matching de títulos.

        Args:
            lote: CnabRetornoLote

        Returns:
            Dict com estatísticas: {
                'com_match': N,
                'sem_match': N,
                'nao_aplicavel': N,
                'vinculado_rastreabilidade': N  # NOVO: extratos já conciliados vinculados
            }
        """
        stats = {
            'com_match': 0,
            'sem_match': 0,
            'nao_aplicavel': 0,
            'vinculado_rastreabilidade': 0  # FASE 4: Novo contador
        }

        # FASE 4: Agora também processa itens JA_PAGO para rastreabilidade
        itens = CnabRetornoItem.query.filter(
            CnabRetornoItem.lote_id == lote.id,
            CnabRetornoItem.status_match.in_(['MATCH_ENCONTRADO', 'JA_PAGO']),  # Inclui JA_PAGO
            CnabRetornoItem.processado == False,
        ).all()

        for item in itens:
            self._executar_matching_extrato(item)

            if item.status_match_extrato == 'MATCH_ENCONTRADO':
                stats['com_match'] += 1
            elif item.status_match_extrato == 'VINCULADO_RASTREABILIDADE':
                stats['vinculado_rastreabilidade'] += 1
            elif item.status_match_extrato == 'SEM_MATCH':
                stats['sem_match'] += 1
            else:
                stats['nao_aplicavel'] += 1

        db.session.commit()
        return stats
