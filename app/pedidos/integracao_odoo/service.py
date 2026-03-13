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

Resiliência (sale.order create):
- Pattern Fire-and-Poll (P2 do Odoo CLAUDE.md): dispara create com timeout curto,
  polla resultado se der timeout (ação continua no Odoo).
- Batch product lookup (P4): N lookups de produto em 1 query.
- Fonte pattern: app/recebimento/services/recebimento_lf_odoo_service.py:4300
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging
import time

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

    # Fire-and-Poll — parâmetros para sale.order create
    FIRE_TIMEOUT = 90       # Timeout para disparar create (90s)
    POLL_INTERVAL = 10      # Intervalo entre polls (10s)
    MAX_POLL_TIME = 600     # Tempo máximo de polling (10 min)

    def __init__(self):
        self._connection = None
        self._connected = False
        self._product_cache = {}  # Cache batch: default_code → product_id

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

    def _execute(self, model: str, method: str, *args, timeout_override=None, **kwargs):
        """Executa método no Odoo usando conexão existente"""
        if not self._connect():
            raise ConnectionError("Não foi possível conectar ao Odoo")

        # Usa o método execute_kw da conexão existente
        return self._connection.execute_kw(
            model, method, list(args), kwargs if kwargs else None,
            timeout_override=timeout_override
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
        campos_cnpj = ['l10n_br_cnpj']

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
        Busca o ID do produto pelo código interno (default_code).
        Usa cache batch para evitar queries repetidas.

        Args:
            codigo: Código do produto Nacom

        Returns:
            ID do product.product ou None
        """
        # Verifica cache primeiro
        if codigo in self._product_cache:
            return self._product_cache[codigo]

        result = self._execute('product.product', 'search', [
            ('default_code', '=', codigo),
            ('active', '=', True)
        ], limit=1)

        product_id = result[0] if result else None
        self._product_cache[codigo] = product_id
        return product_id

    def buscar_produtos_batch(self, codigos: List[str]) -> Dict[str, int]:
        """
        Busca IDs de múltiplos produtos em 1 query batch (P4: Batch Fan-Out).

        Reduz N queries individuais → 1 query.
        Exemplo: 100 filiais × 10 itens = 1000 queries → 1 query.

        Args:
            codigos: Lista de códigos de produto (default_code)

        Returns:
            Dict {default_code: product_id} para produtos encontrados
        """
        if not codigos:
            return {}

        # Filtra códigos não cacheados
        codigos_buscar = [c for c in codigos if c not in self._product_cache]

        if codigos_buscar:
            try:
                products = self._execute('product.product', 'search_read', [
                    ('default_code', 'in', codigos_buscar),
                    ('active', '=', True)
                ], fields=['id', 'default_code'])

                for p in products:
                    self._product_cache[p['default_code']] = p['id']

                # Marca códigos não encontrados como None no cache
                encontrados = {p['default_code'] for p in products}
                for codigo in codigos_buscar:
                    if codigo not in encontrados:
                        self._product_cache[codigo] = None

                logger.info(
                    f"📦 Batch product lookup: {len(codigos_buscar)} códigos → "
                    f"{len(products)} encontrados"
                )
            except Exception as e:
                logger.warning(f"⚠️ Erro no batch product lookup, fallback individual: {e}")
                # Fallback: busca individual (mais lento mas mais resiliente)
                for codigo in codigos_buscar:
                    self.buscar_produto_por_codigo(codigo)

        return {c: self._product_cache[c] for c in codigos if self._product_cache.get(c)}

    def _fire_and_poll(self, fire_fn, poll_fn, step_name,
                       fire_timeout=None, poll_interval=None, max_poll_time=None):
        """
        Padrão Fire-and-Poll (P2): dispara ação com timeout curto, polla resultado.

        Adaptado de recebimento_lf_odoo_service.py:4300.

        1. fire_fn() com timeout curto — se timeout, OK (ação continua no Odoo)
        2. poll_fn() a cada poll_interval até retornar truthy
        3. Se max_poll_time excedido, raise TimeoutError

        Args:
            fire_fn: callable que dispara a ação (pode dar timeout)
            poll_fn: callable que retorna resultado ou None/False
            step_name: nome do passo (para log)
            fire_timeout: timeout do fire (default FIRE_TIMEOUT)
            poll_interval: intervalo entre polls (default POLL_INTERVAL)
            max_poll_time: tempo máximo de polling (default MAX_POLL_TIME)

        Returns:
            Resultado retornado por fire_fn ou poll_fn

        Raises:
            TimeoutError: se max_poll_time excedido sem resultado
            Exception: erros não relacionados a timeout
        """
        fire_timeout = fire_timeout or self.FIRE_TIMEOUT
        poll_interval = poll_interval or self.POLL_INTERVAL
        max_poll_time = max_poll_time or self.MAX_POLL_TIME

        # 1. FIRE — dispara ação com timeout
        fire_result = None
        needs_polling = False

        try:
            fire_result = fire_fn()
            logger.info(f"  [{step_name}] Ação completou dentro do timeout ({fire_timeout}s)")
        except Exception as e:
            error_str = str(e)
            if 'Timeout' in error_str or 'timeout' in error_str or 'timed out' in error_str:
                logger.info(
                    f"  [{step_name}] Timeout ao disparar ({fire_timeout}s) — "
                    f"esperado, iniciando polling..."
                )
                needs_polling = True
            elif 'cannot marshal None' in error_str:
                logger.info(f"  [{step_name}] Ação completou (retorno None)")
                fire_result = None
            else:
                raise

        # Se fire completou, verificar se resultado já é válido
        if not needs_polling:
            try:
                poll_result = poll_fn()
                if poll_result:
                    return poll_result
            except Exception:
                pass
            if fire_result:
                return fire_result

        # 2. POLL — verificar resultado periodicamente
        elapsed = 0
        poll_count = 0
        while elapsed < max_poll_time:
            time.sleep(poll_interval)
            elapsed += poll_interval
            poll_count += 1

            try:
                poll_result = poll_fn()
                if poll_result:
                    logger.info(
                        f"  [{step_name}] Poll #{poll_count} ({elapsed}s): resultado encontrado"
                    )
                    return poll_result
                else:
                    logger.debug(
                        f"  [{step_name}] Poll #{poll_count} ({elapsed}s): aguardando..."
                    )
            except Exception as e:
                error_str = str(e)
                if any(kw in error_str for kw in ('Timeout', 'timeout', 'timed out',
                                                   'Connection', 'SSL', 'socket')):
                    logger.warning(
                        f"  [{step_name}] Erro de conexão no poll #{poll_count}, "
                        f"reconectando..."
                    )
                    # Força reconexão na próxima chamada
                    self._connected = False
                    self._connection = None
                else:
                    logger.warning(f"  [{step_name}] Erro no poll #{poll_count}: {e}")

        # 3. Timeout de polling — erro
        raise TimeoutError(
            f"[{step_name}] Polling expirou após {max_poll_time}s "
            f"({poll_count} tentativas) sem resultado"
        )

    def criar_pedido(self,
                     cnpj_cliente: str,
                     itens: List[Dict[str, Any]],
                     numero_pedido_cliente: str = None,
                     observacoes: str = None,
                     calcular_impostos: bool = True,
                     payment_provider_id: int = None,
                     picking_policy: str = None) -> ResultadoCriacaoPedido:
        """
        Cria um pedido de venda no Odoo com Fire-and-Poll para resiliência.

        O sale.order create pode demorar >300s em dias de alta demanda.
        Pattern P2 (Fire-and-Poll): dispara create com timeout curto (90s),
        se timeout → polla Odoo para encontrar o pedido criado (ação continua
        server-side).

        Pattern P4 (Batch Fan-Out): busca todos os produtos em 1 query
        em vez de N queries individuais.

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

            # 2. Busca produtos em batch (P4: N queries → 1 query)
            codigos = [
                item.get('nosso_codigo') or item.get('cod_produto')
                for item in itens
                if item.get('nosso_codigo') or item.get('cod_produto')
            ]
            product_map = self.buscar_produtos_batch(codigos)

            # 3. Prepara linhas do pedido
            order_lines = []
            for item in itens:
                cod_produto = item.get('nosso_codigo') or item.get('cod_produto')
                if not cod_produto:
                    erros.append(f"Item sem código de produto: {item}")
                    continue

                product_id = product_map.get(cod_produto)
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

            # 4. Monta dados do pedido
            create_data = {
                'partner_id': partner_id,
                'company_id': self.COMPANY_ID,
                'l10n_br_compra_indcom': self.DESTINACAO_USO,
                'incoterm': self.INCOTERM_CIF,
                'l10n_br_imposto_auto': True,
                'order_line': order_lines,
            }

            if numero_pedido_cliente:
                create_data['l10n_br_pedido_compra'] = numero_pedido_cliente

            if payment_provider_id:
                create_data['payment_provider_id'] = payment_provider_id

            if observacoes:
                create_data['note'] = observacoes

            if picking_policy:
                create_data['picking_policy'] = picking_policy

            # 5. Cria pedido com Fire-and-Poll (P2)
            # Libera conexão DB antes de operação longa (P7)
            db.session.commit()

            pedido_compra_busca = numero_pedido_cliente or ''

            def fire_fn():
                # _execute reconecta automaticamente se necessário
                return self._execute(
                    'sale.order', 'create', create_data,
                    timeout_override=self.FIRE_TIMEOUT
                )

            def poll_fn():
                """Busca pedido recém-criado por partner + pedido_compra."""
                filtros = [
                    ('partner_id', '=', partner_id),
                    ('company_id', '=', self.COMPANY_ID),
                ]
                if pedido_compra_busca:
                    filtros.append(('l10n_br_pedido_compra', '=', pedido_compra_busca))

                try:
                    # _execute reconecta automaticamente após erro de conexão
                    orders = self._execute(
                        'sale.order', 'search_read', [filtros],
                        fields=['id', 'name'], limit=1, order='id desc',
                        timeout_override=30  # Poll com timeout curto
                    )
                    if orders:
                        return orders[0]
                except Exception:
                    pass
                return None

            logger.info(
                f"📝 Criando sale.order para {cnpj_cliente} "
                f"({len(order_lines)} linhas, pedido_compra={pedido_compra_busca})"
            )

            result = self._fire_and_poll(
                fire_fn=fire_fn,
                poll_fn=poll_fn,
                step_name=f"sale.order.create({cnpj_cliente})",
            )

            # Extrai order_id e order_name do resultado
            if isinstance(result, dict):
                # Veio do poll (search_read retorna dict)
                order_id = result['id']
                order_name = result.get('name', f"ID:{order_id}")
            elif isinstance(result, int):
                # Veio do fire (create retorna int)
                order_id = result
                # Busca nome do pedido
                order_read = self._execute('sale.order', 'read', [order_id], fields=['name'])
                order_name = order_read[0]['name'] if order_read else f"ID:{order_id}"
            else:
                return ResultadoCriacaoPedido(
                    sucesso=False,
                    mensagem="Falha ao criar pedido no Odoo (resultado inesperado)",
                    erros=erros
                )

            # 6. Impostos — NÃO calcular aqui (parâmetro calcular_impostos ignorado)
            # O cálculo é feito pelo job inserir_pedidos_lote_job que processa
            # filiais sequencialmente: criar pedido → calcular impostos → próxima.
            # Se calcular aqui ou em RQ separado, N jobs rodam em paralelo no
            # Odoo e derrubam o servidor por acúmulo de RAM.

            return ResultadoCriacaoPedido(
                sucesso=True,
                order_id=order_id,
                order_name=order_name,
                mensagem=f"Pedido {order_name} criado com sucesso",
                erros=erros
            )

        except TimeoutError as e:
            # Fire-and-poll expirou — pedido pode ou não ter sido criado
            logger.error(f"⏱️ Timeout fire-and-poll para {cnpj_cliente}: {e}")
            return ResultadoCriacaoPedido(
                sucesso=False,
                mensagem=f"Timeout ao criar pedido (Odoo sobrecarregado): {str(e)}",
                erros=erros + [str(e)]
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
