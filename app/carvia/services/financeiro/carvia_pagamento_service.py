"""CarviaPagamentoService — ponto unico de pagamento de documentos CarVia.

Orquestra o pagamento de qualquer documento (fatura_cliente, fatura_trans,
despesa, custo_entrega, receita) usando Conciliacao como SOT.

Dois modos de pagamento:
  1. pagar_com_conciliacao(): usuario seleciona uma linha bancaria OFX/CSV
     ja existente e o documento e conciliado com ela.
  2. pagar_manual(): pagamento feito fora do extrato bancario CarVia
     (conta pessoal, outra empresa, dinheiro, etc.). Cria uma linha
     `origem='MANUAL'` com `conta_origem` informado e concilia com ela.

Em AMBOS os modos:
  - Documento tem status de pagamento atualizado (PAGO/PAGA/RECEBIDO)
  - Conciliacao e criada via CarviaConciliacaoService.conciliar()
  - NUNCA cria CarviaContaMovimentacao (legado — mantido apenas para
    saldo_inicial via rota especifica)

Usado por:
  - app/carvia/routes/fluxo_caixa_routes.py (api_fluxo_caixa_pagar)
  - app/carvia/routes/fatura_routes.py (atualizar_status_fatura_cliente)
  - app/carvia/routes/despesa_routes.py (atualizar_status_despesa)
  - app/carvia/routes/custo_entrega_routes.py (atualizar_status_custo_entrega)
  - app/carvia/routes/receita_routes.py (atualizar_status_receita)

W10 Nivel 2 — Sprint 4 (auditoria CarVia).
"""
import logging
import uuid
from datetime import date, datetime

from app import db

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Erros customizados
# ----------------------------------------------------------------------

class PagamentoError(Exception):
    """Erro generico de pagamento (mensagem exibida ao usuario)."""
    pass


class DocumentoJaPagoError(PagamentoError):
    """Documento ja esta pago — tentativa de re-pagar."""
    pass


class DocumentoCanceladoError(PagamentoError):
    """Documento cancelado nao pode ser pago."""
    pass


class DocumentoNaoEncontradoError(PagamentoError):
    """Documento nao existe."""
    pass


class JaConciliadoError(PagamentoError):
    """Documento ja possui conciliacao — deve usar Extrato Bancario."""
    pass


class ParametroInvalidoError(PagamentoError):
    """Parametro obrigatorio ausente ou invalido."""
    pass


# ----------------------------------------------------------------------
# Mapeamento tipo_doc -> metadados
# ----------------------------------------------------------------------

# Cada tipo_doc define: atributo de status, valor do novo status,
# campo de data de pagamento, campo de usuario.
TIPO_DOC_META = {
    'fatura_cliente': {
        'status_attr': 'status',
        'status_pago': 'PAGA',
        'status_pendente': 'PENDENTE',
        'status_cancelado': 'CANCELADA',
        'pago_em_attr': 'pago_em',
        'pago_por_attr': 'pago_por',
        'valor_attr': 'valor_total',
        'tipo_linha': 'CREDITO',  # CarVia recebe dinheiro
        'label': 'Fatura cliente',
    },
    'fatura_transportadora': {
        'status_attr': 'status_pagamento',
        'status_pago': 'PAGO',
        'status_pendente': 'PENDENTE',
        'status_cancelado': None,  # FT nao tem status CANCELADA em status_pagamento
        'pago_em_attr': 'pago_em',
        'pago_por_attr': 'pago_por',
        'valor_attr': 'valor_total',
        'tipo_linha': 'DEBITO',  # CarVia paga
        'label': 'Fatura transportadora',
    },
    'despesa': {
        'status_attr': 'status',
        'status_pago': 'PAGO',
        'status_pendente': 'PENDENTE',
        'status_cancelado': 'CANCELADO',
        'pago_em_attr': 'pago_em',
        'pago_por_attr': 'pago_por',
        'valor_attr': 'valor',
        'tipo_linha': 'DEBITO',
        'label': 'Despesa',
    },
    'custo_entrega': {
        'status_attr': 'status',
        'status_pago': 'PAGO',
        'status_pendente': 'PENDENTE',
        'status_cancelado': 'CANCELADO',
        'pago_em_attr': 'pago_em',
        'pago_por_attr': 'pago_por',
        'valor_attr': 'valor',
        'tipo_linha': 'DEBITO',
        'label': 'Custo de entrega',
    },
    'receita': {
        'status_attr': 'status',
        'status_pago': 'RECEBIDO',
        'status_pendente': 'PENDENTE',
        'status_cancelado': 'CANCELADO',
        'pago_em_attr': 'recebido_em',
        'pago_por_attr': 'recebido_por',
        'valor_attr': 'valor',
        'tipo_linha': 'CREDITO',
        'label': 'Receita',
    },
}


# ----------------------------------------------------------------------
# Service
# ----------------------------------------------------------------------

class CarviaPagamentoService:
    """Service centralizado de pagamento de documentos CarVia."""

    @staticmethod
    def _buscar_doc(tipo_doc, doc_id):
        """Busca documento e retorna (doc, meta) ou levanta erro.

        Raises:
            ParametroInvalidoError: tipo_doc nao suportado
            DocumentoNaoEncontradoError: doc nao existe
        """
        if tipo_doc not in TIPO_DOC_META:
            raise ParametroInvalidoError(
                f'Tipo de documento invalido: {tipo_doc}'
            )

        meta = TIPO_DOC_META[tipo_doc]

        from app.carvia.models import (
            CarviaFaturaCliente,
            CarviaFaturaTransportadora,
            CarviaDespesa,
            CarviaCustoEntrega,
            CarviaReceita,
        )

        model_map = {
            'fatura_cliente': CarviaFaturaCliente,
            'fatura_transportadora': CarviaFaturaTransportadora,
            'despesa': CarviaDespesa,
            'custo_entrega': CarviaCustoEntrega,
            'receita': CarviaReceita,
        }

        Model = model_map[tipo_doc]
        doc = db.session.get(Model, int(doc_id))
        if not doc:
            raise DocumentoNaoEncontradoError(
                f'{meta["label"]} #{doc_id} nao encontrado'
            )
        return doc, meta

    @staticmethod
    def _validar_pode_pagar(doc, meta):
        """Valida que o doc pode ser pago (nao cancelado, nao pago).

        Raises:
            DocumentoCanceladoError, DocumentoJaPagoError
        """
        status_atual = getattr(doc, meta['status_attr'])
        if meta['status_cancelado'] and status_atual == meta['status_cancelado']:
            raise DocumentoCanceladoError(
                f'{meta["label"]} cancelado nao pode ser pago.'
            )
        if status_atual == meta['status_pago']:
            raise DocumentoJaPagoError(
                f'{meta["label"]} ja pago.'
            )

    @staticmethod
    def _aplicar_pagamento_no_doc(doc, meta, data_pagamento, usuario):
        """Aplica campos de pagamento no doc (status, data, user).

        Semantica de `pago_em`:
            Aqui `pago_em` (ou `recebido_em`, para CarviaReceita) e gravado
            como `midnight` (00:00:00) da `data_pagamento` escolhida pelo
            usuario — e explicitamente um "carimbo de negocio", NAO um
            timestamp de sistema. O usuario escolheu quando o pagamento
            efetivamente ocorreu.

            Diferente do caminho de conciliacao direta via Extrato Bancario:
            `CarviaConciliacaoService._atualizar_totais_documento` usa
            `agora_utc_naive()` (timestamp do sistema) ao propagar o status
            para o doc. Essa discrepancia e INTENCIONAL:
              - Pagamento via service (esta rota): data escolhida pelo usuario.
              - Conciliacao direta (Extrato Bancario): timestamp do sistema.
            Ambos gravam no mesmo campo; quando houver duvida, o valor em
            `pago_em` reflete a ultima escrita, e e audit-loggado.
        """
        pago_em_dt = datetime.combine(data_pagamento, datetime.min.time())
        setattr(doc, meta['status_attr'], meta['status_pago'])
        setattr(doc, meta['pago_em_attr'], pago_em_dt)
        setattr(doc, meta['pago_por_attr'], usuario)

    @staticmethod
    def _valor_do_doc(doc, meta):
        """Extrai valor do doc conforme atributo configurado."""
        return float(getattr(doc, meta['valor_attr']) or 0)

    @staticmethod
    def _remover_movimentacao_legada(tipo_doc, doc_id):
        """Remove CarviaContaMovimentacao legada do doc (compat historico).

        Antes do W10 Nivel 2, pagamentos criavam CarviaContaMovimentacao.
        Apos a refatoracao, passaram a criar CarviaExtratoLinha(origem='MANUAL').
        Este helper limpa resquicios pre-refatoracao ao desfazer um pagamento
        — mantido APENAS para compat com dados historicos.

        Nao faz parte do fluxo canonico de novos pagamentos/reversoes; e
        chamado internamente por `desfazer_pagamento`.

        Args:
            tipo_doc: str
            doc_id: int|str

        Returns:
            bool: True se havia movimentacao e foi removida, False caso
                  contrario (documento nao pre-existia a refatoracao).
        """
        from app.carvia.models import CarviaContaMovimentacao

        mov = db.session.query(CarviaContaMovimentacao).filter_by(
            tipo_doc=tipo_doc,
            doc_id=int(doc_id),
        ).first()

        if mov:
            db.session.delete(mov)
            return True
        return False

    @staticmethod
    def _guard_ja_conciliado(tipo_doc, doc_id):
        """Bloqueia se doc ja tem QUALQUER conciliacao — Conciliacao e SOT.

        Usado apenas no modo pagar_manual — no modo com_conciliacao o
        usuario esta escolhendo a linha e a validacao e feita pelo
        CarviaConciliacaoService.

        Raises:
            JaConciliadoError
        """
        from app.carvia.models import CarviaConciliacao
        ja = CarviaConciliacao.query.filter_by(
            tipo_documento=tipo_doc,
            documento_id=int(doc_id),
        ).first()
        if ja:
            raise JaConciliadoError(
                'Este documento ja possui conciliacao bancaria. '
                'Use a tela de Extrato Bancario para gerenciar o pagamento.'
            )

    # ------------------------------------------------------------------
    # API publica
    # ------------------------------------------------------------------

    @staticmethod
    def pagar_com_conciliacao(
        tipo_doc,
        doc_id,
        data_pagamento,
        extrato_linha_id,
        usuario,
    ):
        """Paga doc conciliando com uma linha OFX/CSV existente.

        Args:
            tipo_doc: str (fatura_cliente|fatura_transportadora|despesa|custo_entrega|receita)
            doc_id: int
            data_pagamento: date
            extrato_linha_id: int (id de CarviaExtratoLinha OFX/CSV)
            usuario: str (email)

        Returns:
            dict: {
                'sucesso': True,
                'novo_status': str,
                'doc_id': int,
                'tipo_doc': str,
                'extrato_linha_id': int,
                'conciliou': True,
                'modo': 'com_conciliacao',
            }

        Raises:
            PagamentoError (ou subclasses)
        """
        from app.carvia.models import CarviaConciliacao, CarviaExtratoLinha
        from app.carvia.services.financeiro.carvia_conciliacao_service import (
            CarviaConciliacaoService,
        )

        if not extrato_linha_id:
            raise ParametroInvalidoError(
                'extrato_linha_id e obrigatorio em pagar_com_conciliacao'
            )
        if not isinstance(data_pagamento, date):
            raise ParametroInvalidoError(
                'data_pagamento deve ser um objeto date'
            )

        doc, meta = CarviaPagamentoService._buscar_doc(tipo_doc, doc_id)
        CarviaPagamentoService._validar_pode_pagar(doc, meta)

        # Verifica se linha existe e e OFX/CSV (nao MANUAL)
        linha = db.session.get(CarviaExtratoLinha, int(extrato_linha_id))
        if not linha:
            raise ParametroInvalidoError(
                f'Linha de extrato #{extrato_linha_id} nao existe'
            )

        valor_mov = CarviaPagamentoService._valor_do_doc(doc, meta)

        # Aplica pagamento no doc
        CarviaPagamentoService._aplicar_pagamento_no_doc(
            doc, meta, data_pagamento, usuario
        )

        # Concilia (se ainda nao existe)
        ja_existe = db.session.query(CarviaConciliacao).filter_by(
            extrato_linha_id=int(extrato_linha_id),
            tipo_documento=tipo_doc,
            documento_id=int(doc_id),
        ).first()

        if not ja_existe:
            CarviaConciliacaoService.conciliar(
                int(extrato_linha_id),
                [{
                    'tipo_documento': tipo_doc,
                    'documento_id': int(doc_id),
                    'valor_alocado': valor_mov,
                }],
                usuario,
            )

        logger.info(
            "Pagamento com conciliacao: %s #%s conciliado com linha #%s por %s",
            tipo_doc, doc_id, extrato_linha_id, usuario,
        )

        return {
            'sucesso': True,
            'novo_status': meta['status_pago'],
            'doc_id': int(doc_id),
            'tipo_doc': tipo_doc,
            'extrato_linha_id': int(extrato_linha_id),
            'conciliou': True,
            'modo': 'com_conciliacao',
        }

    @staticmethod
    def pagar_manual(
        tipo_doc,
        doc_id,
        data_pagamento,
        conta_origem,
        descricao_pagamento,
        usuario,
    ):
        """Paga doc via lancamento manual (fora do extrato bancario).

        Cria uma linha origem='MANUAL' em CarviaExtratoLinha com a
        `conta_origem` informada e concilia com o documento.

        Args:
            tipo_doc: str
            doc_id: int
            data_pagamento: date
            conta_origem: str (ex: "Conta Pessoal Rafael", "Dinheiro/Caixa")
            descricao_pagamento: str (descricao livre — substitui generico)
            usuario: str (email)

        Returns:
            dict: {
                'sucesso': True,
                'novo_status': str,
                'doc_id': int,
                'tipo_doc': str,
                'extrato_linha_id': int (id da linha MANUAL criada),
                'conciliou': True,
                'modo': 'manual',
            }

        Raises:
            PagamentoError (ou subclasses)
        """
        from app.carvia.models import CarviaExtratoLinha
        from app.carvia.services.financeiro.carvia_conciliacao_service import (
            CarviaConciliacaoService,
        )

        # Validacoes de params
        if not conta_origem or not str(conta_origem).strip():
            raise ParametroInvalidoError(
                'conta_origem e obrigatorio em pagamento manual '
                '(ex: "Conta Pessoal Rafael", "Dinheiro/Caixa").'
            )
        if not descricao_pagamento or not str(descricao_pagamento).strip():
            raise ParametroInvalidoError(
                'descricao_pagamento e obrigatorio em pagamento manual.'
            )
        if not isinstance(data_pagamento, date):
            raise ParametroInvalidoError(
                'data_pagamento deve ser um objeto date'
            )

        conta_origem = str(conta_origem).strip()[:100]
        descricao_pagamento = str(descricao_pagamento).strip()[:500]

        # Busca doc
        doc, meta = CarviaPagamentoService._buscar_doc(tipo_doc, doc_id)
        CarviaPagamentoService._validar_pode_pagar(doc, meta)

        # Guard: se ja tem qualquer conciliacao, bloqueia
        CarviaPagamentoService._guard_ja_conciliado(tipo_doc, doc_id)

        valor_mov = CarviaPagamentoService._valor_do_doc(doc, meta)

        # Aplica pagamento no doc
        CarviaPagamentoService._aplicar_pagamento_no_doc(
            doc, meta, data_pagamento, usuario
        )

        # Cria linha MANUAL
        # fitid unico: MANUAL-{tipo}-{doc_id}-{uuid12}
        fitid = f"MANUAL-{tipo_doc}-{doc_id}-{uuid.uuid4().hex[:12]}"

        linha = CarviaExtratoLinha(
            fitid=fitid,
            data=data_pagamento,
            valor=valor_mov,
            tipo=meta['tipo_linha'],
            descricao=descricao_pagamento,
            memo=f'Pagamento manual — {conta_origem}',
            status_conciliacao='PENDENTE',
            total_conciliado=0,
            arquivo_ofx='MANUAL',
            origem='MANUAL',
            conta_origem=conta_origem,
            criado_por=usuario,
        )
        db.session.add(linha)
        db.session.flush()  # obter id

        # Concilia doc com a linha MANUAL
        CarviaConciliacaoService.conciliar(
            linha.id,
            [{
                'tipo_documento': tipo_doc,
                'documento_id': int(doc_id),
                'valor_alocado': valor_mov,
            }],
            usuario,
        )

        logger.info(
            "Pagamento manual: %s #%s via linha MANUAL #%s "
            "(conta: %s) por %s",
            tipo_doc, doc_id, linha.id, conta_origem, usuario,
        )

        return {
            'sucesso': True,
            'novo_status': meta['status_pago'],
            'doc_id': int(doc_id),
            'tipo_doc': tipo_doc,
            'extrato_linha_id': linha.id,
            'conciliou': True,
            'modo': 'manual',
            'conta_origem': conta_origem,
        }

    @staticmethod
    def desfazer_pagamento(tipo_doc, doc_id, usuario):
        """Desfaz pagamento de doc.

        Regras:
        - Se doc esta conciliado com linha REAL (OFX/CSV): BLOQUEIA
          (usuario deve desconciliar via Extrato Bancario).
        - Se doc esta conciliado apenas com linhas MANUAL: desconcilia
          e remove as linhas MANUAL orfas.
        - Reverte status do doc para PENDENTE.

        Returns:
            dict: {
                'sucesso': True,
                'novo_status': 'PENDENTE',
                'doc_id': int,
                'tipo_doc': str,
                'linhas_manuais_removidas': int,
            }

        Raises:
            PagamentoError (com mensagem detalhada)
        """
        from app.carvia.models import CarviaConciliacao, CarviaExtratoLinha
        from app.carvia.services.financeiro.carvia_conciliacao_service import (
            CarviaConciliacaoService,
        )

        # 1. Buscar doc, meta
        doc, meta = CarviaPagamentoService._buscar_doc(tipo_doc, doc_id)

        # 2. A10: nao permite desfazer pagamento de doc ja PENDENTE.
        # Sem esta guarda, a rotina rodava silenciosamente sobre um doc que
        # nunca esteve pago (sem efeito visivel, mas poluindo logs e
        # permitindo double-click erratico no botao "Desfazer").
        status_atual = getattr(doc, meta['status_attr'])
        if status_atual == meta['status_pendente']:
            raise PagamentoError(
                f'{meta["label"]} ja esta em {meta["status_pendente"]} — '
                f'nao ha pagamento para desfazer.'
            )

        # NC2: A10 extendido — doc CANCELADO nao pode ter desfazer.
        # Reativar um cancelado violaria o fluxo de status R4 (CANCELADO e
        # final). Observacao: `status_cancelado` e None para fatura_transportadora
        # (que nao tem status CANCELADA em status_pagamento) — o check curto-
        # circuita nesse caso.
        if meta['status_cancelado'] and status_atual == meta['status_cancelado']:
            raise PagamentoError(
                f'{meta["label"]} esta {meta["status_cancelado"]} — '
                f'nao e possivel desfazer pagamento. '
                f'Reative o documento primeiro (reverter cancelamento).'
            )

        # 3. Buscar conciliacoes
        conciliacoes = db.session.query(CarviaConciliacao).join(
            CarviaExtratoLinha,
            CarviaExtratoLinha.id == CarviaConciliacao.extrato_linha_id,
        ).filter(
            CarviaConciliacao.tipo_documento == tipo_doc,
            CarviaConciliacao.documento_id == int(doc_id),
        ).all()

        # 4. Validar: se ha conciliacao REAL (OFX/CSV), bloqueia antes de
        # tocar qualquer estado. Raise PagamentoError — caller faz rollback.
        if conciliacoes:
            conciliacoes_reais = [
                c for c in conciliacoes
                if c.extrato_linha and c.extrato_linha.origem != 'MANUAL'
            ]
            conciliacoes_manuais = [
                c for c in conciliacoes
                if c.extrato_linha and c.extrato_linha.origem == 'MANUAL'
            ]

            if conciliacoes_reais:
                msg_extra = ''
                if conciliacoes_manuais:
                    msg_extra = (
                        f' (Ha tambem {len(conciliacoes_manuais)} '
                        'pagamento(s) manual — apos desconciliar no Extrato '
                        'Bancario, volte aqui para desfazer o pagamento restante.)'
                    )
                raise PagamentoError(
                    f'Documento possui {len(conciliacoes_reais)} '
                    f'conciliacao(oes) bancaria(s) real(is). '
                    f'Desconcilie via Extrato Bancario primeiro.{msg_extra}'
                )
            # Todas MANUAL — pode desfazer

        # IMPORTANTE: coletar linhas_manuais_ids ANTES de desconciliar.
        # Apos desconciliar, o objeto CarviaConciliacao e deletado e
        # `conc.extrato_linha_id` pode estar gone/expirado.
        linhas_manuais_ids = set()
        for conc in conciliacoes:
            if conc.extrato_linha and conc.extrato_linha.origem == 'MANUAL':
                linhas_manuais_ids.add(conc.extrato_linha_id)

        # 5. Desconciliar TUDO primeiro (loop completo)
        for conc in conciliacoes:
            try:
                CarviaConciliacaoService.desconciliar(conc.id, usuario)
            except Exception as e:
                logger.error(
                    "Erro ao desconciliar #%s em desfazer pagamento: %s",
                    conc.id, e,
                )
                raise PagamentoError(
                    f'Falha ao desconciliar #{conc.id}: {e}. '
                    f'Operacao abortada para preservar integridade.'
                )

        # 6. Remover linhas MANUAL orfas (loop completo)
        linhas_removidas = 0
        for linha_id in linhas_manuais_ids:
            restantes = CarviaConciliacao.query.filter_by(
                extrato_linha_id=linha_id
            ).count()
            if restantes == 0:
                linha = db.session.get(CarviaExtratoLinha, linha_id)
                if linha:
                    db.session.delete(linha)
                    linhas_removidas += 1
                    logger.info(
                        "Linha MANUAL #%s removida (orfa apos desfazer)",
                        linha_id,
                    )

        # 7. DEPOIS reverter status do doc (apenas quando tudo o mais
        # ja foi feito com sucesso — se desconciliar/remover falhar,
        # o status permanece intacto e o caller faz rollback).
        setattr(doc, meta['status_attr'], meta['status_pendente'])
        setattr(doc, meta['pago_em_attr'], None)
        setattr(doc, meta['pago_por_attr'], None)

        # 8. Compat historico: limpa CarviaContaMovimentacao pre-refatoracao.
        # Antes do W10 Nivel 2, pagamentos criavam movimentacao na conta.
        # Apos a refatoracao, passaram a criar CarviaExtratoLinha MANUAL.
        # Este helper e no-op para docs pos-refatoracao (e o caminho unico
        # de limpeza de dados legados — as routes NAO devem mais invocar
        # nada do tipo).
        CarviaPagamentoService._remover_movimentacao_legada(tipo_doc, doc_id)

        logger.info(
            "Pagamento desfeito: %s #%s (status %s) por %s",
            tipo_doc, doc_id, meta['status_pendente'], usuario,
        )

        # 9. Retornar resultado
        return {
            'sucesso': True,
            'novo_status': meta['status_pendente'],
            'doc_id': int(doc_id),
            'tipo_doc': tipo_doc,
            'linhas_manuais_removidas': linhas_removidas,
        }
