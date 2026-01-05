"""
Service para criação de pedidos de venda no Odoo

Baseado no estudo docs/ESTUDO_CRIAR_PEDIDO_VENDA_ODOO.md

Campos obrigatórios:
- sale.order: partner_id, company_id, l10n_br_compra_indcom, incoterm
- sale.order.line: product_id, product_uom_qty, price_unit, l10n_br_compra_indcom

Cálculo de Impostos:
- Usa Redis Queue (fila 'impostos') para calcular impostos em background
- Jobs processados pelo worker_render.py
- Timeout de 180 segundos por job
- Rastreabilidade via dashboard RQ
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from .models import RegistroPedidoOdoo
from app import db

logger = logging.getLogger(__name__)


@dataclass
class ResultadoCriacaoPedido:
    """Resultado da criação de um pedido no Odoo"""
    sucesso: bool
    order_id: Optional[int] = None
    order_name: Optional[str] = None
    mensagem: str = ""
    erros: List[str] = None # type: ignore

    def __post_init__(self):
        if self.erros is None:
            self.erros = []


class OdooIntegrationService:
    """
    Service para integração com Odoo via XML-RPC

    Usa a conexão existente em app.odoo.utils.connection.get_odoo_connection()

    Uso:
        service = OdooIntegrationService()
        resultado = service.criar_pedido(
            cnpj_cliente='93.209.765/0599-44',
            itens=[
                {'cod_produto': '35642', 'quantidade': 15, 'preco': 199.48},
                ...
            ]
        )
    """

    # Valores fixos para criação de pedido
    COMPANY_ID = 4  # ID da empresa no Odoo
    INCOTERM_CIF = 6  # CIF = Frete por conta do vendedor
    DESTINACAO_USO = 'com'  # Comercialização

    def __init__(self):
        self._connection = None
        self._connected = False

    def _connect(self) -> bool:
        """Estabelece conexão com o Odoo usando sistema existente"""
        if self._connected:
            return True

        try:
            from app.odoo.utils.connection import get_odoo_connection
            self._connection = get_odoo_connection()
            self._connected = True
            return True

        except Exception as e:
            print(f"Erro ao conectar ao Odoo: {e}")
            return False

    def _execute(self, model: str, method: str, *args, **kwargs):
        """Executa método no Odoo usando conexão existente"""
        if not self._connect():
            raise ConnectionError("Não foi possível conectar ao Odoo")

        # Usa o método execute_kw da conexão existente
        return self._connection.execute_kw(
            model, method, list(args), kwargs if kwargs else None
        )

    def buscar_cliente_por_cnpj(self, cnpj: str) -> Optional[int]:
        """
        Busca o ID do cliente pelo CNPJ

        Args:
            cnpj: CNPJ com ou sem formatação

        Returns:
            ID do partner ou None
        """
        # Remove formatação
        cnpj_limpo = ''.join(c for c in cnpj if c.isdigit())

        # Formata para padrão Odoo (com pontos e barras)
        if len(cnpj_limpo) == 14:
            cnpj_formatado = f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}"
        else:
            cnpj_formatado = cnpj

        # Campos possíveis para CNPJ no Odoo
        campos_cnpj = ['l10n_br_cnpj', 'vat']

        # Formatos de CNPJ para tentar
        formatos_cnpj = [cnpj_formatado, cnpj_limpo, cnpj]

        # Tenta cada combinação de campo e formato
        for campo in campos_cnpj:
            for cnpj_busca in formatos_cnpj:
                try:
                    result = self._execute('res.partner', 'search', [
                        (campo, '=', cnpj_busca),
                        ('active', '=', True)
                    ], limit=1)

                    if result:
                        return result[0]
                except Exception:
                    # Campo pode não existir, continua tentando
                    continue

        return None

    def buscar_produto_por_codigo(self, codigo: str) -> Optional[int]:
        """
        Busca o ID do produto pelo código interno (default_code)

        Args:
            codigo: Código do produto Nacom

        Returns:
            ID do product.product ou None
        """
        result = self._execute('product.product', 'search', [
            ('default_code', '=', codigo),
            ('active', '=', True)
        ], limit=1)

        if result:
            return result[0]

        return None

    def criar_pedido(self,
                     cnpj_cliente: str,
                     itens: List[Dict[str, Any]],
                     numero_pedido_cliente: str = None,
                     observacoes: str = None,
                     calcular_impostos: bool = True,
                     payment_provider_id: int = None,
                     picking_policy: str = None) -> ResultadoCriacaoPedido:
        """
        Cria um pedido de venda no Odoo

        Args:
            cnpj_cliente: CNPJ do cliente
            itens: Lista de dicts com cod_produto, quantidade, preco (nosso_codigo)
            numero_pedido_cliente: Número do pedido de compra do cliente (campo "Numero:" do PDF)
            observacoes: Observações do pedido
            calcular_impostos: Se deve calcular impostos após criar
            payment_provider_id: ID da forma de pagamento (30 = Transferência Bancária CD)
            picking_policy: Política de envio ('direct' = O mais rápido possível, 'one' = Quando todos prontos)

        Returns:
            ResultadoCriacaoPedido
        """
        erros = []

        try:
            # 1. Busca cliente
            partner_id = self.buscar_cliente_por_cnpj(cnpj_cliente)
            if not partner_id:
                return ResultadoCriacaoPedido(
                    sucesso=False,
                    mensagem=f"Cliente não encontrado no Odoo: {cnpj_cliente}",
                    erros=[f"CNPJ {cnpj_cliente} não cadastrado no Odoo"]
                )

            # 2. Prepara linhas do pedido
            order_lines = []
            for item in itens:
                cod_produto = item.get('nosso_codigo') or item.get('cod_produto')
                if not cod_produto:
                    erros.append(f"Item sem código de produto: {item}")
                    continue

                # Busca produto
                product_id = self.buscar_produto_por_codigo(cod_produto)
                if not product_id:
                    erros.append(f"Produto não encontrado: {cod_produto}")
                    continue

                quantidade = float(item.get('quantidade', 0))
                preco = float(item.get('preco') or item.get('valor_unitario', 0))

                if quantidade <= 0 or preco <= 0:
                    erros.append(f"Quantidade/preço inválido para {cod_produto}")
                    continue

                # Linha do pedido no formato Odoo (0, 0, {...})
                line_data = {
                    'product_id': product_id,
                    'product_uom_qty': quantidade,
                    'price_unit': preco,
                    'l10n_br_compra_indcom': self.DESTINACAO_USO,
                }

                # Adiciona pedido de compra do cliente na linha também
                if numero_pedido_cliente:
                    line_data['l10n_br_pedido_compra'] = numero_pedido_cliente

                order_lines.append((0, 0, line_data))

            if not order_lines:
                return ResultadoCriacaoPedido(
                    sucesso=False,
                    mensagem="Nenhum item válido para criar pedido",
                    erros=erros
                )

            # 3. Cria o pedido
            order_data = {
                'partner_id': partner_id,
                'company_id': self.COMPANY_ID,
                'l10n_br_compra_indcom': self.DESTINACAO_USO,
                'incoterm': self.INCOTERM_CIF,
                'l10n_br_imposto_auto': True,
                'order_line': order_lines,
            }

            # Número do pedido de compra do cliente (campo "Numero:" do PDF)
            if numero_pedido_cliente:
                order_data['l10n_br_pedido_compra'] = numero_pedido_cliente

            # Forma de pagamento (30 = Transferência Bancária CD)
            if payment_provider_id:
                order_data['payment_provider_id'] = payment_provider_id

            if observacoes:
                order_data['note'] = observacoes

            # Política de envio (direct = O mais rápido possível)
            if picking_policy:
                order_data['picking_policy'] = picking_policy

            order_id = self._execute('sale.order', 'create', order_data)

            if not order_id:
                return ResultadoCriacaoPedido(
                    sucesso=False,
                    mensagem="Falha ao criar pedido no Odoo",
                    erros=erros
                )

            # 4. Busca número do pedido criado
            order_data = self._execute('sale.order', 'read', [order_id], fields=['name'])
            order_name = order_data[0]['name'] if order_data else f"ID:{order_id}"

            # 5. Calcula impostos em BACKGROUND via Redis Queue
            # Usa fila 'impostos' com timeout de 300 segundos (5 minutos)
            job_id = None
            if calcular_impostos:
                try:
                    from app.portal.workers import enqueue_job
                    from app.pedidos.workers.impostos_jobs import calcular_impostos_odoo

                    job = enqueue_job(
                        calcular_impostos_odoo,
                        order_id,
                        order_name,
                        queue_name='impostos',
                        timeout='5m'  # 5 minutos
                    )
                    job_id = job.id
                    logger.info(f"📤 Job {job_id} enfileirado para calcular impostos: {order_name}")
                except Exception as e:
                    # Se falhar ao enfileirar, apenas loga - não bloqueia criação
                    logger.warning(f"⚠️ Erro ao enfileirar cálculo de impostos: {e}")
                    erros.append(f"Aviso: impostos serão calculados manualmente")

            return ResultadoCriacaoPedido(
                sucesso=True,
                order_id=order_id,
                order_name=order_name,
                mensagem=f"Pedido {order_name} criado com sucesso (impostos na fila)",
                erros=erros
            )

        except Exception as e:
            import traceback
            return ResultadoCriacaoPedido(
                sucesso=False,
                mensagem=f"Erro ao criar pedido: {str(e)}",
                erros=erros + [traceback.format_exc()]
            )

    def criar_pedido_e_registrar(self,
        cnpj_cliente: str,
        itens: List[Dict[str, Any]],
        rede: str,
        tipo_documento: str,
        numero_documento: str,
        arquivo_pdf_s3: str,
        usuario: str,
        divergente: bool = False,
        divergencias: List[Dict] = None,
        justificativa: str = None,
        aprovador: str = None,
        numero_pedido_cliente: str = None,
        payment_provider_id: int = None) -> Tuple[ResultadoCriacaoPedido, RegistroPedidoOdoo]: # type: ignore # noqa: E125
        """
        Cria pedido no Odoo e registra no banco local para auditoria

        Args:
            cnpj_cliente: CNPJ do cliente
            itens: Lista de itens
            rede: Nome da rede (ATACADAO, TENDA, ASSAI)
            tipo_documento: PROPOSTA ou PEDIDO
            numero_documento: Número do documento (proposta)
            arquivo_pdf_s3: URL do arquivo no S3
            usuario: Usuário que está inserindo
            divergente: Se teve divergência de preço
            divergencias: Lista de divergências
            justificativa: Justificativa se divergente
            aprovador: Quem aprovou se divergente
            numero_pedido_cliente: Número do pedido do cliente (campo "Numero:" do PDF)
            payment_provider_id: ID da forma de pagamento (30 = Transferência Bancária CD)

        Returns:
            Tupla (ResultadoCriacaoPedido, RegistroPedidoOdoo)
        """
        # Extrai dados do cliente do primeiro item
        primeiro_item = itens[0] if itens else {}
        uf_cliente = primeiro_item.get('uf') or primeiro_item.get('estado')
        nome_cliente = primeiro_item.get('nome_cliente')

        # Cria registro de auditoria
        registro = RegistroPedidoOdoo(
            rede=rede.upper(),
            tipo_documento=tipo_documento.upper(),
            numero_documento=numero_documento,
            arquivo_pdf_s3=arquivo_pdf_s3,
            cnpj_cliente=cnpj_cliente,
            nome_cliente=nome_cliente,
            uf_cliente=uf_cliente,
            status_odoo='PENDENTE',
            dados_documento=itens,
            divergente=divergente,
            divergencias=divergencias,
            justificativa_aprovacao=justificativa,
            inserido_por=usuario,
            aprovado_por=aprovador if divergente else None,
        )

        try:
            # Tenta criar pedido no Odoo
            # Usa numero_pedido_cliente se fornecido, senão usa numero_documento como fallback
            pedido_compra = numero_pedido_cliente or numero_documento

            # Atacadão: política de envio "O mais rápido possível"
            picking_policy = 'direct' if rede.upper() == 'ATACADAO' else None

            resultado = self.criar_pedido(
                cnpj_cliente=cnpj_cliente,
                itens=itens,
                numero_pedido_cliente=pedido_compra,
                payment_provider_id=payment_provider_id,
                picking_policy=picking_policy,
            )

            if resultado.sucesso:
                registro.marcar_sucesso(resultado.order_id, resultado.order_name)
            else:
                registro.marcar_erro(resultado.mensagem)

        except Exception as e:
            registro.marcar_erro(str(e))
            resultado = ResultadoCriacaoPedido(
                sucesso=False,
                mensagem=str(e),
                erros=[str(e)]
            )

        # Salva registro no banco
        try:
            db.session.add(registro)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao salvar registro: {e}")

        return resultado, registro


# Instância singleton para uso global
_odoo_service: Optional[OdooIntegrationService] = None


def get_odoo_service() -> OdooIntegrationService:
    """Retorna instância singleton do serviço Odoo"""
    global _odoo_service
    if _odoo_service is None:
        _odoo_service = OdooIntegrationService()
    return _odoo_service


def criar_pedido_odoo(cnpj_cliente: str,
                      itens: List[Dict[str, Any]],
                      **kwargs) -> ResultadoCriacaoPedido:
    """
    Função utilitária para criar pedido no Odoo

    Args:
        cnpj_cliente: CNPJ do cliente
        itens: Lista de itens
        **kwargs: Argumentos adicionais para criar_pedido

    Returns:
        ResultadoCriacaoPedido
    """
    service = get_odoo_service()
    return service.criar_pedido(cnpj_cliente, itens, **kwargs)
