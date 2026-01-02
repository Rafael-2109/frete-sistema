"""
TEMPLATE: Service de Lançamento no Odoo
========================================

Copie este template e adapte para sua entidade.
Substitua 'Xxx' pelo nome da sua entidade (ex: Frete, DespesaExtra, etc.)

Arquivos de referência:
- app/fretes/services/lancamento_odoo_service.py (implementação base)
- app/fretes/services/lancamento_despesa_odoo_service.py (exemplo de extensão)
"""

import json
import time
from datetime import date
from typing import Dict, Optional, Any

from flask import current_app

from app import db
from app.fretes.models import (
    # Importar seu modelo aqui
    # Xxx,
    LancamentoFreteOdooAuditoria
)
from app.fretes.services.lancamento_odoo_service import LancamentoOdooService


class LancamentoXxxOdooService(LancamentoOdooService):
    """
    Service para lançar [Xxx] no Odoo.
    Herda de LancamentoOdooService e reutiliza constantes e métodos base.
    """

    def _registrar_auditoria_xxx(
        self,
        xxx_id: int,
        cte_id: Optional[int],
        chave_cte: str,
        etapa: int,
        etapa_descricao: str,
        modelo_odoo: str,
        acao: str,
        status: str,
        mensagem: Optional[str] = None,
        metodo_odoo: Optional[str] = None,
        dados_antes: Optional[Dict] = None,
        dados_depois: Optional[Dict] = None,
        campos_alterados: Optional[list] = None,
        tempo_execucao_ms: Optional[int] = None,
        dfe_id: Optional[int] = None,
        purchase_order_id: Optional[int] = None,
        invoice_id: Optional[int] = None
    ) -> LancamentoFreteOdooAuditoria:
        """
        Registra etapa na auditoria.
        Adapte o campo xxx_id conforme seu modelo.
        """
        try:
            auditoria = LancamentoFreteOdooAuditoria(
                frete_id=None,  # Ajustar conforme necessidade
                # xxx_id=xxx_id,  # Adicionar campo no modelo de auditoria se necessário
                cte_id=cte_id,
                chave_cte=chave_cte,
                dfe_id=dfe_id,
                purchase_order_id=purchase_order_id,
                invoice_id=invoice_id,
                etapa=etapa,
                etapa_descricao=etapa_descricao,
                modelo_odoo=modelo_odoo,
                metodo_odoo=metodo_odoo,
                acao=acao,
                dados_antes=json.dumps(dados_antes, default=str) if dados_antes else None,
                dados_depois=json.dumps(dados_depois, default=str) if dados_depois else None,
                campos_alterados=','.join(campos_alterados) if campos_alterados else None,
                status=status,
                mensagem=mensagem,
                tempo_execucao_ms=tempo_execucao_ms,
                executado_por=self.usuario_nome,
                ip_usuario=self.usuario_ip
            )

            db.session.add(auditoria)
            db.session.flush()
            self.auditoria_logs.append(auditoria.to_dict())

            return auditoria

        except Exception as e:
            current_app.logger.error(f"Erro ao registrar auditoria: {e}")
            raise

    def _rollback_xxx_odoo(self, xxx_id: int, etapas_concluidas: int) -> bool:
        """
        Faz rollback dos campos Odoo em caso de erro.
        """
        try:
            # xxx = Xxx.query.get(xxx_id)
            # if not xxx:
            #     return False

            # if xxx.status != 'LANCADO_ODOO' or etapas_concluidas < 16:
            #     xxx.odoo_dfe_id = None
            #     xxx.odoo_purchase_order_id = None
            #     xxx.odoo_invoice_id = None
            #     xxx.lancado_odoo_em = None
            #     xxx.lancado_odoo_por = None
            #     xxx.status = 'STATUS_ANTERIOR'  # Definir status de retorno
            #     db.session.commit()
            #     return True

            return False

        except Exception as e:
            current_app.logger.error(f"Erro ao executar rollback: {e}")
            db.session.rollback()
            return False

    def lancar_xxx_odoo(
        self,
        xxx_id: int,
        data_vencimento: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Executa lançamento completo no Odoo.

        Args:
            xxx_id: ID do registro no sistema local
            data_vencimento: Data de vencimento (opcional)

        Returns:
            Dict com resultado do lançamento
        """
        from app.odoo.utils.connection import get_odoo_connection

        inicio_total = time.time()
        current_app.logger.info("=" * 80)
        current_app.logger.info(f"INICIANDO LANCAMENTO ODOO - Xxx #{xxx_id}")
        current_app.logger.info("=" * 80)

        resultado = {
            'sucesso': False,
            'mensagem': '',
            'dfe_id': None,
            'purchase_order_id': None,
            'invoice_id': None,
            'etapas_concluidas': 0,
            'auditoria': [],
            'erro': None
        }

        try:
            # ================================================
            # VALIDAÇÕES INICIAIS
            # ================================================
            # xxx = Xxx.query.get(xxx_id)
            # if not xxx:
            #     raise ValueError(f"Xxx #{xxx_id} não encontrado")

            # Validar CTe vinculado
            # if not xxx.cte_id:
            #     raise ValueError("CTe não vinculado")

            # Validar status
            # if xxx.status != 'STATUS_PERMITIDO':
            #     raise ValueError(f"Status '{xxx.status}' não permite lançamento")

            # Buscar CTe
            # cte = ConhecimentoTransporte.query.get(xxx.cte_id)
            # cte_chave = cte.chave_acesso
            # cte_id = cte.id

            # Usar vencimento do registro se não informado
            # if not data_vencimento:
            #     data_vencimento = xxx.vencimento

            # Converter para string
            # data_vencimento_str = data_vencimento.strftime('%Y-%m-%d')

            # ================================================
            # CONECTAR NO ODOO
            # ================================================
            self.odoo = get_odoo_connection()
            if not self.odoo.authenticate():
                raise Exception("Falha na autenticação com Odoo")

            # ================================================
            # ETAPA 1: Buscar DFe pela chave
            # ================================================
            # Implementar etapas 1-16 seguindo o padrão documentado
            # Ver SKILL.md para detalhes de cada etapa

            # ================================================
            # ETAPA 16: Atualizar registro local
            # ================================================
            # xxx.odoo_dfe_id = dfe_id
            # xxx.odoo_purchase_order_id = po_id
            # xxx.odoo_invoice_id = invoice_id
            # xxx.lancado_odoo_em = agora_brasil()
            # xxx.lancado_odoo_por = self.usuario_nome
            # xxx.status = 'LANCADO_ODOO'
            # db.session.commit()

            resultado['etapas_concluidas'] = 16
            resultado['sucesso'] = True
            resultado['mensagem'] = f'Xxx #{xxx_id} lançado com sucesso no Odoo'
            resultado['auditoria'] = self.auditoria_logs

            return resultado

        except Exception as e:
            current_app.logger.error(f"Erro no lançamento: {str(e)}")
            resultado['erro'] = str(e)
            resultado['mensagem'] = f'Erro no lançamento: {str(e)}'
            resultado['auditoria'] = self.auditoria_logs
            resultado['rollback_executado'] = self._rollback_xxx_odoo(
                xxx_id, resultado['etapas_concluidas']
            )
            return resultado
