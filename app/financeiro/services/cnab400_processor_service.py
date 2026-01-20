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
    ContasAReceber
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
