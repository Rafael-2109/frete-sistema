"""StockInternalTransferService — transferencia entre lotes / locations internas.

Servico ATOMICO e REUTILIZAVEL para ajustar quantidades entre:
- Lotes diferentes (mesmo product+company+location)
- Quant sem lote (lot_id=False) -> lote especifico
- Locations diferentes da mesma company (mesmo lote)

Implementa o padrao oficial do Odoo 16+ via INVENTORY ADJUSTMENT
(stock.quant.action_apply_inventory). Movimenta quantidades sem
renomear lotes — preserva rastreabilidade fiscal e historico.

Por que NAO renomear lote (`stock.lot.write({'name': ...})`)?
- Renomear afeta TODO o lote (todos os quants) — nao permite split parcial
- Viola unique constraint (name, product_id, company_id) se 2 origens
  apontam para o mesmo destino
- Quant sem lot_id (lot_id=False) nao tem nome para renomear

A operacao gera 1 stock.move automatico (via inventory adjustment)
visivel em Inventory > Reporting > Stock Moves com origem
'Physical Inventory'. E auditavel.

Spec: D004/D005 (refator 2026-05-18) — inventario 2026-05.

Reutilizavel para:
- Consolidacao de lotes apos inventario (cenario INVENTARIO_2026_05)
- Correcao de cadastro errado de lote
- Atribuicao de lote a quant sem lote (lot_id=False)
- Split de lote para fracionamento fiscal
- Mover saldo de lote entre locations (FB/Estoque -> FB/Indisponivel)

API v2 (2026-05-24, Skill 2 maturando):
- `transferir_entre_lotes_v2`: delega a `ajustar_quant` 2x (-origem, +destino),
  propagando `delta_esperado` para herdar guard anti-bug CICLAMATO da Skill 1.
- `transferir_entre_locations`: idem para mover quant entre 2 locations (mesmo lote).
- Helpers `resolver_lote_origem/destino`: wildcard de variantes MIGRACAO e
  filtro company_id obrigatorio (G021 lot de empresa errada).

Gotchas-invariante codificados:
- G021: filtro company_id obrigatorio em todo resolve de lote (lot de outra
  empresa => 'Empresas incompativeis')
- G022: 2 lotes MIGRACAO/produto (com e sem cedilha) -> resolver consolida no
  de MAIOR saldo na location alvo, ou cria canonico 'MIGRAÇÃO'
- G027: reserved_quantity vem de saida -> v2 herda `validar_nao_abaixo_reserva`
  da Skill 1 (default True); RESETAR via flag explicito `resetar_reserva`
- G028: consolidar_move_lines -> herdado de ajustar_quant
- G002: lot.name search '=' instavel -> usar 'in' (helper sempre normaliza)
- G_proxy_vazio: 'P-15/05' = literal + tambem cobre quant sem lote (lot_id=False)
- delta_esperado: propagado a CADA chamada de ajustar_quant (regra inviolavel
  11 do roadmap pos-CICLAMATO)
"""
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from app.odoo.estoque.scripts.quant import StockQuantAdjustmentService
from app.odoo.services.stock_lot_service import StockLotService
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)

# Tolerancia de arredondamento (mesma constante da Skill 1 quant.py).
# Banco local guarda 4 casas, Odoo guarda 6; fracoes 1/3, 2/3, 1/6 divergem.
# Re-exportada pelo shim em app/odoo/services/stock_internal_transfer_service.py.
TOL_ARREDONDAMENTO = 0.001

# Variantes do lote MIGRACAO encontradas no Odoo CIEL IT (G022).
# Produtos costumam ter MULTIPLOS stock.lot com diferentes grafias:
#   - 'MIGRAÇÃO'   (canonico, com cedilha)
#   - 'MIGRACAO'   (sem cedilha — criado por piloto 2026-05-18; vide padronizar_migracao.py)
#   - 'MIGRAÇAO'   (cedilha sem til — variante rara)
# Toda busca por lote MIGRACAO precisa cobrir as 3 grafias.
LOTES_MIGRACAO_VARIANTES = ['MIGRAÇÃO', 'MIGRACAO', 'MIGRAÇAO']
LOTE_MIGRACAO_CANONICO = 'MIGRAÇÃO'


def is_migracao(nome: Optional[str]) -> bool:
    """True se o nome de lote bate com QUALQUER variante de MIGRACAO."""
    if not nome:
        return False
    n = nome.strip().upper()
    return n in {v.upper() for v in LOTES_MIGRACAO_VARIANTES}


class StockInternalTransferService:
    """Transferencia atomica de quantidade entre lotes no mesmo location."""

    def __init__(self, odoo=None, lot_svc=None):
        self.odoo = odoo or get_odoo_connection()
        self.lot_svc = lot_svc or StockLotService(odoo=self.odoo)

    # ============================================================
    # Helper: buscar quant especifico
    # ============================================================

    def buscar_quant(
        self,
        product_id: int,
        company_id: int,
        location_id: int,
        lot_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Busca 1 quant por (product, company, location, lot_id).

        lot_id=None busca quant sem lote (lot_id=False no Odoo).
        Se ha multiplos quants compativeis (mesmo lote em sub-locations
        agregadas), retorna o primeiro — caller deve refinar location_id.

        Returns:
            dict {id, quantity, value, lot_id} ou None se nao existe.
        """
        domain: List = [
            ['product_id', '=', product_id],
            ['company_id', '=', company_id],
            ['location_id', '=', location_id],
        ]
        if lot_id is None:
            domain.append(['lot_id', '=', False])
        else:
            domain.append(['lot_id', '=', lot_id])
        quants = self.odoo.search_read(
            'stock.quant', domain,
            ['id', 'quantity', 'value', 'lot_id', 'reserved_quantity'],
            limit=1,
        )
        return quants[0] if quants else None

    def listar_quants(
        self, product_id: int, company_id: int, location_id: int,
    ) -> List[Dict[str, Any]]:
        """Lista todos os quants do produto/company/location.

        Util para auditoria pos-transferencia.
        """
        return self.odoo.search_read(
            'stock.quant',
            [
                ['product_id', '=', product_id],
                ['company_id', '=', company_id],
                ['location_id', '=', location_id],
            ],
            ['id', 'quantity', 'value', 'lot_id', 'reserved_quantity'],
        )

    # ============================================================
    # Operacao atomica: transferir quantidade entre lotes
    # ============================================================

    def transferir_entre_lotes(
        self,
        product_id: int,
        company_id: int,
        location_id: int,
        qty: float,
        lot_id_origem: Optional[int],
        lot_id_destino: int,
    ) -> Dict[str, Any]:
        """Transfere `qty` do `lot_id_origem` para `lot_id_destino` no
        mesmo product/company/location, via inventory adjustment.

        Operacao atomica em 2 passos (cada um e um inventory adjustment
        com action_apply_inventory no Odoo):
            1. Reduzir quant origem em `qty`
            2. Aumentar (ou criar) quant destino em `qty`

        Args:
            product_id: product.product.id.
            company_id: company_id (res.company.id).
            location_id: stock.location.id (origem == destino).
            qty: quantidade a transferir (positiva).
            lot_id_origem: stock.lot.id do lote de origem.
                Use `None` para "quant sem lote" (lot_id=False no Odoo).
            lot_id_destino: stock.lot.id do lote de destino
                (use StockLotService.criar_se_nao_existe para garantir).

        Returns:
            dict com:
                quant_origem_id, quant_origem_qty_antes, quant_origem_qty_apos,
                quant_destino_id, quant_destino_qty_antes, quant_destino_qty_apos,
                qty_transferida, tempo_ms.

        Raises:
            ValueError: qty<=0, lot_ids iguais, falta quant origem.
            RuntimeError: quant origem tem qty < qty solicitada,
                ou reserva impede transferencia.
        """
        if qty <= 0:
            raise ValueError(f'qty deve ser > 0 (recebido {qty})')
        if lot_id_origem == lot_id_destino:
            raise ValueError(
                f'lot_id_origem == lot_id_destino ({lot_id_origem}) — '
                'nao ha o que transferir'
            )

        inicio = time.time()

        # 1. Localizar quant origem
        quant_origem = self.buscar_quant(
            product_id, company_id, location_id, lot_id_origem,
        )
        if not quant_origem:
            raise ValueError(
                f'Quant origem nao encontrado: product_id={product_id} '
                f'company_id={company_id} location_id={location_id} '
                f'lot_id={lot_id_origem}'
            )
        qty_origem_antes = float(quant_origem['quantity'])
        reservada = float(quant_origem.get('reserved_quantity', 0) or 0)

        # Tolerancia 0.001 un para arredondamento (banco local guarda
        # quantity em 4 casas decimais; Odoo guarda em 6 — frações 1/3,
        # 2/3, 1/6 etc divergem). Se qty pedida > qty real por menos
        # que 1 milesimo de unidade, clamp para a qty real disponivel.
        TOL_ARREDONDAMENTO = 0.001
        if qty > qty_origem_antes:
            if qty - qty_origem_antes <= TOL_ARREDONDAMENTO:
                logger.info(
                    f'Clamp qty {qty} → {qty_origem_antes} '
                    f'(diff {qty - qty_origem_antes:.6f} ≤ tolerancia)'
                )
                qty = qty_origem_antes
            else:
                raise RuntimeError(
                    f'Quant origem {quant_origem["id"]} tem {qty_origem_antes} un '
                    f'mas pedido transferir {qty} un'
                )
        # Bloquear se ha reserva que ultrapassaria saldo restante.
        # Saldo apos = qty_origem_antes - qty; deve ser >= reservada.
        if (qty_origem_antes - qty) < reservada:
            raise RuntimeError(
                f'Quant origem {quant_origem["id"]} tem {reservada} un reservadas '
                f'em pickings ativos. Saldo apos transferencia '
                f'({qty_origem_antes - qty}) ficaria < reserva. Cancelar '
                f'pickings ou reduzir qty solicitada.'
            )

        # 2. Localizar (ou preparar criacao de) quant destino
        quant_destino = self.buscar_quant(
            product_id, company_id, location_id, lot_id_destino,
        )
        qty_destino_antes = (
            float(quant_destino['quantity']) if quant_destino else 0.0
        )

        # 3. Reduzir quant origem via inventory adjustment
        nova_qty_origem = qty_origem_antes - qty
        self.odoo.write(
            'stock.quant', [quant_origem['id']],
            {'inventory_quantity': nova_qty_origem},
        )
        self.odoo.execute_kw(
            'stock.quant', 'action_apply_inventory', [[quant_origem['id']]],
        )
        logger.info(
            f'Transferencia: quant_origem {quant_origem["id"]} '
            f'(lot_id={lot_id_origem}) {qty_origem_antes} → '
            f'{nova_qty_origem} (-{qty})'
        )

        # 4. Aumentar (ou criar) quant destino
        nova_qty_destino = qty_destino_antes + qty
        if quant_destino:
            self.odoo.write(
                'stock.quant', [quant_destino['id']],
                {'inventory_quantity': nova_qty_destino},
            )
            self.odoo.execute_kw(
                'stock.quant', 'action_apply_inventory',
                [[quant_destino['id']]],
            )
            quant_destino_id = quant_destino['id']
        else:
            # Criar quant novo. Em Odoo 16, criar com 'inventory_quantity'
            # e depois apply_inventory gera o movimento de entrada.
            quant_destino_id = self.odoo.create('stock.quant', {
                'product_id': product_id,
                'company_id': company_id,
                'location_id': location_id,
                'lot_id': lot_id_destino,
                'inventory_quantity': nova_qty_destino,
            })
            self.odoo.execute_kw(
                'stock.quant', 'action_apply_inventory',
                [[quant_destino_id]],
            )
        logger.info(
            f'Transferencia: quant_destino {quant_destino_id} '
            f'(lot_id={lot_id_destino}) {qty_destino_antes} → '
            f'{nova_qty_destino} (+{qty})'
        )

        return {
            'quant_origem_id': quant_origem['id'],
            'quant_origem_qty_antes': qty_origem_antes,
            'quant_origem_qty_apos': nova_qty_origem,
            'quant_destino_id': quant_destino_id,
            'quant_destino_qty_antes': qty_destino_antes,
            'quant_destino_qty_apos': nova_qty_destino,
            'qty_transferida': qty,
            'lot_id_origem': lot_id_origem,
            'lot_id_destino': lot_id_destino,
            'tempo_ms': int((time.time() - inicio) * 1000),
        }

    # ============================================================
    # Wrapper de alto nivel: garantir lote destino + transferir
    # ============================================================

    def transferir_quantidade_para_lote(
        self,
        product_id: int,
        company_id: int,
        location_id: int,
        qty: float,
        lot_id_origem: Optional[int],
        nome_lote_destino: str,
        expiration_date_destino: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Garante lote destino existe e transfere qty.

        Wrapper conveniente: 1 chamada faz criar_se_nao_existe + transferir.

        Args:
            product_id, company_id, location_id, qty, lot_id_origem:
                como em transferir_entre_lotes.
            nome_lote_destino: nome do lote alvo (ex: '26014'). Criado
                se nao existir.
            expiration_date_destino: validade (opcional) do lote alvo.

        Returns:
            dict como transferir_entre_lotes + chaves extras:
                lote_destino_nome, lote_destino_criado_agora.
        """
        lot_id_destino, criado = self.lot_svc.criar_se_nao_existe(
            nome_lote_destino, product_id, company_id,
            expiration_date=expiration_date_destino,
        )
        res = self.transferir_entre_lotes(
            product_id=product_id,
            company_id=company_id,
            location_id=location_id,
            qty=qty,
            lot_id_origem=lot_id_origem,
            lot_id_destino=lot_id_destino,
        )
        res['lote_destino_nome'] = nome_lote_destino
        res['lote_destino_criado_agora'] = criado
        return res

    # ============================================================
    # Helpers — resolucao de lote MIGRACAO (G021/G022)
    # ============================================================

    def _lotes_migracao_ids(
        self, product_id: int, company_id: int,
    ) -> List[int]:
        """IDs dos stock.lot 'MIGRACAO*' do produto NA empresa-alvo (G021).

        Filtra company_id SEMPRE — sem isso, lots de outra empresa caem na
        lista e estouram 'Empresas incompativeis' na criacao de quant.
        """
        return self.odoo.search('stock.lot', [
            ['name', 'in', LOTES_MIGRACAO_VARIANTES],
            ['product_id', '=', product_id],
            ['company_id', '=', company_id],
        ])

    def _melhor_lote_migracao_na_loc(
        self, product_id: int, company_id: int, location_id: int,
    ) -> Tuple[Optional[int], List[int]]:
        """Retorna (lot_id, todos_ids) do lote MIGRACAO com MAIOR saldo na loc.

        G022: produtos costumam ter 2+ lots MIGRACAO (com/sem cedilha). Escolha
        consciente: o de MAIOR saldo na location_id alvo. Se nenhuma variante
        tem saldo na loc, retorna o primeiro existente. Se nenhuma existe,
        (None, []).
        """
        lids = self._lotes_migracao_ids(product_id, company_id)
        if not lids:
            return None, []
        quants = self.odoo.search_read('stock.quant', [
            ['product_id', '=', product_id],
            ['company_id', '=', company_id],
            ['location_id', '=', location_id],
            ['lot_id', 'in', lids],
        ], ['lot_id', 'quantity'])
        com_saldo = sorted(
            [(q['lot_id'][0], float(q['quantity'])) for q in quants
             if abs(float(q['quantity'])) > 1e-9],
            key=lambda x: -x[1],
        )
        if com_saldo:
            return com_saldo[0][0], lids
        return lids[0], lids

    def resolver_lote_origem(
        self,
        *,
        nome_lote: Optional[str],
        product_id: int,
        company_id: int,
        location_id: int,
    ) -> Tuple[Optional[int], str, Optional[str]]:
        """Resolve lot_id de ORIGEM (G021/G022).

        - MIGRAÇÃO (qq variante): retorna o de maior saldo na location_id.
        - Literal: busca exato (StockLotService trata bug do operador '=').
        - None ou 'P-15/05': retorna (None, 'P-15/05(sem-lote)', None) — o
          caller deve usar lot_id=None na busca do quant (quant sem lote).

        Returns:
            (lot_id|None, label, erro|None).
            erro=None => sucesso (ou proxy vazio); != None => problema (lote
            inexistente, etc).
        """
        if nome_lote is None or (isinstance(nome_lote, str) and nome_lote.strip() in ('', 'P-15/05')):
            return None, 'P-15/05(sem-lote)', None
        if is_migracao(nome_lote):
            lid, _ = self._melhor_lote_migracao_na_loc(
                product_id, company_id, location_id,
            )
            if lid:
                return lid, LOTE_MIGRACAO_CANONICO, None
            return None, LOTE_MIGRACAO_CANONICO, (
                f'lote MIGRACAO* inexistente para product={product_id} '
                f'company={company_id}'
            )
        lid = self.lot_svc.buscar_por_nome(nome_lote, product_id, company_id)
        if lid:
            return lid, nome_lote, None
        return None, nome_lote, (
            f'lote {nome_lote!r} inexistente para product={product_id} '
            f'company={company_id}'
        )

    def resolver_lote_destino(
        self,
        *,
        nome_lote: Optional[str],
        product_id: int,
        company_id: int,
        location_id: int,
        criar_se_faltar: bool = True,
        expiration_date: Optional[str] = None,
    ) -> Tuple[Optional[int], str, bool]:
        """Resolve lot_id de DESTINO (G021/G022).

        - MIGRAÇÃO (qq variante): consolida no de maior saldo na location_id
          (cria canonico 'MIGRAÇÃO' se nenhum existe e criar_se_faltar=True).
        - Literal: criar_se_nao_existe (se criar_se_faltar) ou busca exato.
        - None ou 'P-15/05': retorna (None, 'P-15/05(sem-lote)', False) — o
          caller deve usar lot_id=None ao criar o quant (quant sem lote).

        Returns:
            (lot_id|None, nome_canonico, criado_agora).
        """
        if nome_lote is None or (isinstance(nome_lote, str) and nome_lote.strip() in ('', 'P-15/05')):
            return None, 'P-15/05(sem-lote)', False
        if is_migracao(nome_lote):
            lid, lids = self._melhor_lote_migracao_na_loc(
                product_id, company_id, location_id,
            )
            if lid:
                return lid, LOTE_MIGRACAO_CANONICO, False
            if lids:
                # Existe alguma variante mas sem saldo na loc — usa a primeira
                return lids[0], LOTE_MIGRACAO_CANONICO, False
            if not criar_se_faltar:
                return None, LOTE_MIGRACAO_CANONICO, False
            novo = self.lot_svc.criar(
                LOTE_MIGRACAO_CANONICO, product_id, company_id,
            )
            return novo, LOTE_MIGRACAO_CANONICO, True
        if not criar_se_faltar:
            lid = self.lot_svc.buscar_por_nome(nome_lote, product_id, company_id)
            return lid, nome_lote, False
        lid, criado = self.lot_svc.criar_se_nao_existe(
            nome_lote, product_id, company_id,
            expiration_date=expiration_date,
        )
        return lid, nome_lote, criado

    # ============================================================
    # API v2 — delega a ajustar_quant (Skill 1), propaga delta_esperado
    # ============================================================

    def _quant_svc(self) -> StockQuantAdjustmentService:
        """Lazy-init do StockQuantAdjustmentService (mesma conexao Odoo).

        Evita instanciar 1 por chamada em loops longos.
        """
        if not hasattr(self, '_quant_svc_cache'):
            self._quant_svc_cache = StockQuantAdjustmentService(
                odoo=self.odoo, lot_svc=self.lot_svc,
            )
        return self._quant_svc_cache

    def transferir_entre_lotes_v2(
        self,
        *,
        product_id: int,
        company_id: int,
        location_id: int,
        qty: float,
        lot_id_origem: Optional[int],
        lot_id_destino: int,
        resetar_reserva_origem: bool = False,
        tolerancia_delta: float = 0.001,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Versao v2 de `transferir_entre_lotes` que DELEGA a ajustar_quant 2x.

        Diferencas vs v1:
        - Cada passo (-origem, +destino) propaga `delta_esperado` = +/- qty,
          herdando o guard anti-bug CICLAMATO da Skill 1 (regra inviolavel 11).
        - Retorna a estrutura padrao do `ajustar_quant` para CADA passo
          ('reducao_origem', 'aumento_destino') + sumario.
        - `--resetar-reserva` aplica-se SO a origem (skill 1 unitario por quant).
        - `--dry-run` SIMULA ambos passos sem escrever no Odoo.

        Args:
            product_id, company_id, location_id: identificam o quant
                (mesma location na origem E destino — esta API e para lote-A
                -> lote-B; use `transferir_entre_locations` para lote igual e
                location diferente).
            qty: quantidade a transferir (positiva).
            lot_id_origem: lote de origem (None => quant sem lote).
            lot_id_destino: lote de destino (deve existir; use
                `transferir_quantidade_para_lote_v2` se precisar criar).
            resetar_reserva_origem: passa `resetar_reserva=True` para o passo
                de reducao da origem (limpa reserved_quantity stale ANTES do
                ajuste). Defensivo — preserva picking ativo na maioria dos
                casos; veja G027.
            tolerancia_delta: tolerancia absoluta para o guard delta_esperado
                (default 0.001 — match exato com casas_decimais=6).
            dry_run: simula ambos passos.

        Returns:
            dict {
                'reducao_origem': {...resultado ajustar_quant...},
                'aumento_destino': {...resultado ajustar_quant...},
                'qty_transferida': qty,
                'status': 'EXECUTADO' | 'DRY_RUN_OK' | 'FALHA_REDUCAO' | 'FALHA_AUMENTO',
                'lot_id_origem', 'lot_id_destino', 'tempo_ms',
            }
        """
        if qty <= 0:
            raise ValueError(f'qty deve ser > 0 (recebido {qty})')
        if lot_id_origem == lot_id_destino:
            raise ValueError(
                f'lot_id_origem == lot_id_destino ({lot_id_origem}) — '
                'nao ha o que transferir'
            )

        inicio = time.time()
        svc = self._quant_svc()

        # Passo 1: reduzir origem (delta=-qty, delta_esperado=-qty)
        res_origem = svc.ajustar_quant(
            product_id=product_id,
            company_id=company_id,
            location_id=location_id,
            lot_id=lot_id_origem,
            delta=-qty,
            delta_esperado=-qty,
            tolerancia_delta=tolerancia_delta,
            criar_se_faltar=False,
            validar_nao_negativar=True,
            validar_nao_abaixo_reserva=not resetar_reserva_origem,
            resetar_reserva=resetar_reserva_origem,
            dry_run=dry_run,
        )

        if res_origem['status'] not in ('EXECUTADO', 'DRY_RUN_OK',
                                        'EXECUTADO_AUTO_CORRIGIDO'):
            return {
                'reducao_origem': res_origem,
                'aumento_destino': None,
                'qty_transferida': 0.0,
                'status': 'FALHA_REDUCAO',
                'lot_id_origem': lot_id_origem,
                'lot_id_destino': lot_id_destino,
                'erro': res_origem.get('erro'),
                'tempo_ms': int((time.time() - inicio) * 1000),
            }

        # Passo 2: aumentar destino (delta=+qty, delta_esperado=+qty)
        res_destino = svc.ajustar_quant(
            product_id=product_id,
            company_id=company_id,
            location_id=location_id,
            lot_id=lot_id_destino,
            delta=qty,
            delta_esperado=qty,
            tolerancia_delta=tolerancia_delta,
            criar_se_faltar=True,
            validar_nao_negativar=True,
            validar_nao_abaixo_reserva=True,
            dry_run=dry_run,
        )

        if res_destino['status'] not in ('EXECUTADO', 'DRY_RUN_OK',
                                         'EXECUTADO_AUTO_CORRIGIDO'):
            # FALHA_AUMENTO em modo real = ESTADO PARCIAL (origem ja foi reduzida,
            # destino NAO foi creditado). qty_transferida=0.0 reflete "transfer
            # atomico completo nao ocorreu". qty_reduzida_origem informa o ajuste
            # parcial efetivamente gravado (para auditoria/rollback manual).
            qty_reduzida = (
                abs(res_origem.get('ajuste_aplicado') or 0.0)
                if not dry_run else 0.0
            )
            return {
                'reducao_origem': res_origem,
                'aumento_destino': res_destino,
                'qty_transferida': 0.0,  # CR1#2 (2026-05-24 v2): nada COMPLETO atomicamente
                'qty_reduzida_origem': qty_reduzida,  # debito parcial efetivado (estado partial)
                'status': 'FALHA_AUMENTO',
                'lot_id_origem': lot_id_origem,
                'lot_id_destino': lot_id_destino,
                'erro': res_destino.get('erro'),
                'tempo_ms': int((time.time() - inicio) * 1000),
            }

        return {
            'reducao_origem': res_origem,
            'aumento_destino': res_destino,
            'qty_transferida': qty,
            'status': 'DRY_RUN_OK' if dry_run else 'EXECUTADO',
            'lot_id_origem': lot_id_origem,
            'lot_id_destino': lot_id_destino,
            'tempo_ms': int((time.time() - inicio) * 1000),
        }

    def transferir_entre_locations(
        self,
        *,
        product_id: int,
        company_id: int,
        lot_id: Optional[int],
        qty: float,
        location_id_origem: int,
        location_id_destino: int,
        resetar_reserva_origem: bool = False,
        tolerancia_delta: float = 0.001,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Move `qty` do mesmo lote entre 2 locations da MESMA company.

        Atomo extraido de mover_migracao_para_indisponivel.py (caso real
        FB/Estoque -> FB/Indisponivel mantendo lote MIGRACAO).

        Delega a ajustar_quant 2x: reduz na location_id_origem, aumenta (cria
        se faltar) na location_id_destino. Propaga `delta_esperado`.

        Args:
            product_id, company_id: identificam o produto/empresa.
            lot_id: stock.lot.id (None => quant sem lote, lot_id=False).
            qty: quantidade a mover (positiva).
            location_id_origem, location_id_destino: locations diferentes da
                mesma company.
            resetar_reserva_origem: passa `resetar_reserva=True` para reduzir
                a origem (defensivo — preserva picking ativo na maioria).
            tolerancia_delta: tolerancia absoluta do guard delta_esperado.
            dry_run: simula ambos passos.

        Returns:
            mesma estrutura de `transferir_entre_lotes_v2`, mais
            'location_id_origem' e 'location_id_destino'.
        """
        if qty <= 0:
            raise ValueError(f'qty deve ser > 0 (recebido {qty})')
        if location_id_origem == location_id_destino:
            raise ValueError(
                f'location_id_origem == location_id_destino '
                f'({location_id_origem}) — nao ha o que mover'
            )

        inicio = time.time()
        svc = self._quant_svc()

        # Passo 1: reduzir origem
        res_origem = svc.ajustar_quant(
            product_id=product_id,
            company_id=company_id,
            location_id=location_id_origem,
            lot_id=lot_id,
            delta=-qty,
            delta_esperado=-qty,
            tolerancia_delta=tolerancia_delta,
            criar_se_faltar=False,
            validar_nao_negativar=True,
            validar_nao_abaixo_reserva=not resetar_reserva_origem,
            resetar_reserva=resetar_reserva_origem,
            dry_run=dry_run,
        )

        if res_origem['status'] not in ('EXECUTADO', 'DRY_RUN_OK',
                                        'EXECUTADO_AUTO_CORRIGIDO'):
            return {
                'reducao_origem': res_origem,
                'aumento_destino': None,
                'qty_transferida': 0.0,
                'status': 'FALHA_REDUCAO',
                'location_id_origem': location_id_origem,
                'location_id_destino': location_id_destino,
                'lot_id': lot_id,
                'erro': res_origem.get('erro'),
                'tempo_ms': int((time.time() - inicio) * 1000),
            }

        # Passo 2: aumentar destino
        res_destino = svc.ajustar_quant(
            product_id=product_id,
            company_id=company_id,
            location_id=location_id_destino,
            lot_id=lot_id,
            delta=qty,
            delta_esperado=qty,
            tolerancia_delta=tolerancia_delta,
            criar_se_faltar=True,
            validar_nao_negativar=True,
            validar_nao_abaixo_reserva=True,
            dry_run=dry_run,
        )

        if res_destino['status'] not in ('EXECUTADO', 'DRY_RUN_OK',
                                         'EXECUTADO_AUTO_CORRIGIDO'):
            # FALHA_AUMENTO em modo real = ESTADO PARCIAL (origem ja foi reduzida,
            # destino NAO foi creditado). CR1#2 — vide transferir_entre_lotes_v2.
            qty_reduzida = (
                abs(res_origem.get('ajuste_aplicado') or 0.0)
                if not dry_run else 0.0
            )
            return {
                'reducao_origem': res_origem,
                'aumento_destino': res_destino,
                'qty_transferida': 0.0,
                'qty_reduzida_origem': qty_reduzida,
                'status': 'FALHA_AUMENTO',
                'location_id_origem': location_id_origem,
                'location_id_destino': location_id_destino,
                'lot_id': lot_id,
                'erro': res_destino.get('erro'),
                'tempo_ms': int((time.time() - inicio) * 1000),
            }

        return {
            'reducao_origem': res_origem,
            'aumento_destino': res_destino,
            'qty_transferida': qty,
            'status': 'DRY_RUN_OK' if dry_run else 'EXECUTADO',
            'location_id_origem': location_id_origem,
            'location_id_destino': location_id_destino,
            'lot_id': lot_id,
            'tempo_ms': int((time.time() - inicio) * 1000),
        }

    def transferir_para_indisponivel(
        self,
        *,
        product_id: int,
        company_id: int,
        lot_id_origem: int,
        qty: float,
        location_id_origem: Optional[int] = None,
        nome_lote_destino: str = 'MIGRAÇÃO',
        resetar_reserva_origem: bool = False,
        tolerancia_delta: float = 0.001,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Transfere `qty` para {emp}/Indisponivel CONSOLIDANDO no lote MIGRAÇÃO.

        Invariante GARANTIDA pela skill:
            location_id_destino = LOCAIS_INDISPONIVEL[company_id]
            lot_id_destino      = lot_svc.buscar_por_nome(nome_lote_destino,
                                                          product_id, company_id)
            (criado se faltar em modo real)

        **IMPORTANTE (CR-incidente 2026-05-24 v4)**: stock.lot tem
        product_id — cada produto tem seu PROPRIO lote MIGRACAO (mesmo
        nome, ids diferentes). Por isso a constant
        LOTES_MIGRACAO_POR_COMPANY (em locations.py) NAO eh usavel como
        FK universal — eh apenas um lot_id de exemplo (de UM produto).
        Resolver por produto via lot_svc, sempre.

        Faz sentido para FB e CD (LF=5 historicamente sem MIGRACAO, mas
        nao bloqueamos: passa o nome do lote e deixa o lot_svc decidir).

        Decomposicao: 2 ajustes diretos via `ajustar_quant`:
            Reducao: (loc_origem, lot_id_origem, -qty)
            Aumento: (loc_Indisp, lot_id_destino MIGRACAO, +qty,
                     criar_se_faltar=True)

        Falha reducao: estado inalterado (FALHA_REDUCAO).
        Falha aumento: estado PARCIAL — origem reduzida, destino nao
        creditado (FALHA_AUMENTO).

        Args:
            product_id, company_id: identificam produto/empresa.
            lot_id_origem: stock.lot.id do lote real de origem.
            qty: positiva.
            location_id_origem: default = COMPANY_LOCATIONS[company_id]
                (FB/Estoque=8, CD/Estoque=32).
            nome_lote_destino: nome do lote consolidador (default 'MIGRAÇÃO'
                canonico com cedilha). Resolvido POR PRODUTO via
                lot_svc.buscar_por_nome; criado em modo real se faltar.
            resetar_reserva_origem: passa para reducao.
            tolerancia_delta: tolerancia absoluta dos guards delta_esperado.
            dry_run: simula ambos ajustes; lote destino nao eh criado
                em dry-run (apenas pesquisado).

        Returns:
            dict com:
                reducao_origem: resultado do ajuste origem
                aumento_destino_migracao: resultado do ajuste destino
                qty_transferida: total efetivado
                qty_reduzida_origem: somente em FALHA_AUMENTO real
                status: 'EXECUTADO' | 'DRY_RUN_OK' | 'FALHA_REDUCAO' |
                        'FALHA_AUMENTO' | 'FALHA_LOTE_DESTINO_INEXISTENTE'
                location_id_origem, location_id_destino, lot_id_origem,
                lot_id_destino, lote_destino_nome,
                lote_destino_criado_agora (bool), tempo_ms

        Raises:
            ValueError: company sem LOCAIS_INDISPONIVEL; origem ja em
                Indisp; qty <= 0; lot_svc nao injetado no construtor.
        """
        # Import tardio para evitar dependencia circular at module load.
        # NB: LOTES_MIGRACAO_POR_COMPANY NAO eh importado de proposito
        # (gotcha do incidente 2026-05-24 v4 — lot_id por produto).
        from app.odoo.constants.locations import (
            COMPANY_LOCATIONS, LOCAIS_INDISPONIVEL,
        )

        if qty <= 0:
            raise ValueError(f'qty deve ser > 0 (recebido {qty})')

        if self.lot_svc is None:
            raise ValueError(
                'transferir_para_indisponivel requer lot_svc no construtor '
                '(StockInternalTransferService(odoo, lot_svc=StockLotService(odoo))).'
            )

        # Resolver location destino via constants
        location_id_destino = LOCAIS_INDISPONIVEL.get(company_id)
        if location_id_destino is None:
            raise ValueError(
                f'company_id={company_id} sem entrada em LOCAIS_INDISPONIVEL '
                f'(definidos: {sorted(LOCAIS_INDISPONIVEL)})'
            )

        # Default location_id_origem = principal interno da empresa
        if location_id_origem is None:
            location_id_origem = COMPANY_LOCATIONS.get(company_id)
            if location_id_origem is None:
                raise ValueError(
                    f'company_id={company_id} sem COMPANY_LOCATIONS; informe '
                    f'location_id_origem explicito'
                )

        # Pre-cond: nao pode ser ja no destino
        if location_id_origem == location_id_destino:
            raise ValueError(
                f'location_id_origem == Indisponivel ({location_id_destino}) — '
                'ja esta em Indisponivel; nada a mover'
            )

        # Resolver lote MIGRACAO POR PRODUTO (fix incidente 2026-05-24 v4)
        # Em dry-run: apenas buscar; nao criar (evita poluir Odoo).
        # Em modo real: criar_se_nao_existe.
        lote_destino_criado = False
        if dry_run:
            lot_id_destino = self.lot_svc.buscar_por_nome(
                nome_lote_destino, product_id, company_id,
            )
            if lot_id_destino is None:
                # Em dry-run, sinalizar que precisaria criar
                return {
                    'reducao_origem': None,
                    'aumento_destino_migracao': None,
                    'qty_transferida': 0.0,
                    'status': 'FALHA_LOTE_DESTINO_INEXISTENTE',
                    'location_id_origem': location_id_origem,
                    'location_id_destino': location_id_destino,
                    'lot_id_origem': lot_id_origem,
                    'lot_id_destino': None,
                    'lote_destino_nome': nome_lote_destino,
                    'lote_destino_criado_agora': False,
                    'erro': (
                        f'lote {nome_lote_destino!r} nao existe para '
                        f'product_id={product_id} company_id={company_id}. '
                        'Em modo real seria criado; --confirmar para executar.'
                    ),
                    'tempo_ms': 0,
                }
        else:
            lot_id_destino, lote_destino_criado = self.lot_svc.criar_se_nao_existe(
                nome_lote_destino, product_id, company_id,
            )

        # Pre-cond: lote_origem == lote_destino MIGRACAO (origem ja eh consolidador)
        if lot_id_origem == lot_id_destino:
            raise ValueError(
                f'lot_id_origem == lot_id_destino MIGRACAO ({lot_id_destino}) '
                f'do produto {product_id} — ja consolidado; nada a mover'
            )

        inicio = time.time()
        svc = self._quant_svc()

        # 1 passo direto cross-(loc+lote): delega a `ajustar_quant` 2x.
        # Refatorado em 2026-05-24 v4 (CR-dry-run): a composicao anterior
        # `transferir_entre_locations` + `transferir_entre_lotes_v2` falhava
        # em dry-run porque Passo 2 tentava reduzir lote_origem em Indisp
        # antes do Passo 1 criar o quant la. Solucao: 2 ajustes diretos.

        # Reduzir origem (lote real, loc origem)
        res_origem = svc.ajustar_quant(
            product_id=product_id,
            company_id=company_id,
            location_id=location_id_origem,
            lot_id=lot_id_origem,
            delta=-qty,
            delta_esperado=-qty,
            tolerancia_delta=tolerancia_delta,
            criar_se_faltar=False,
            validar_nao_negativar=True,
            validar_nao_abaixo_reserva=not resetar_reserva_origem,
            resetar_reserva=resetar_reserva_origem,
            dry_run=dry_run,
        )

        if res_origem['status'] not in ('EXECUTADO', 'DRY_RUN_OK',
                                        'EXECUTADO_AUTO_CORRIGIDO'):
            return {
                'reducao_origem': res_origem,
                'aumento_destino_migracao': None,
                'qty_transferida': 0.0,
                'status': 'FALHA_REDUCAO',
                'location_id_origem': location_id_origem,
                'location_id_destino': location_id_destino,
                'lot_id_origem': lot_id_origem,
                'lot_id_destino': lot_id_destino,
                'lote_destino_nome': nome_lote_destino,
                'lote_destino_criado_agora': lote_destino_criado,
                'erro': res_origem.get('erro'),
                'tempo_ms': int((time.time() - inicio) * 1000),
            }

        # Aumentar destino: (loc Indisp, lote MIGRACAO) — criar quant se faltar
        res_destino = svc.ajustar_quant(
            product_id=product_id,
            company_id=company_id,
            location_id=location_id_destino,
            lot_id=lot_id_destino,
            delta=qty,
            delta_esperado=qty,
            tolerancia_delta=tolerancia_delta,
            criar_se_faltar=True,
            validar_nao_negativar=True,
            validar_nao_abaixo_reserva=True,
            dry_run=dry_run,
        )

        if res_destino['status'] not in ('EXECUTADO', 'DRY_RUN_OK',
                                         'EXECUTADO_AUTO_CORRIGIDO'):
            # Estado PARCIAL em modo real: origem reduzida, destino nao creditado.
            qty_reduzida = (
                abs(res_origem.get('ajuste_aplicado') or 0.0)
                if not dry_run else 0.0
            )
            # CR3#5 (2026-05-24 v4): rollback_hint = chamada exata
            # ajustar_quant para reverter origem (operador-acionavel).
            rollback_hint = {
                'action': 'ajustar_quant',
                'product_id': product_id,
                'company_id': company_id,
                'location_id': location_id_origem,
                'lot_id': lot_id_origem,
                'delta': qty_reduzida,
                'delta_esperado': qty_reduzida,
                'criar_se_faltar': True,
                'comentario': (
                    f'Rollback de FALHA_AUMENTO em transferir_para_indisponivel: '
                    f'reverter reducao de {qty_reduzida} un no quant origem.'
                ),
            } if not dry_run and qty_reduzida > 0 else None
            return {
                'reducao_origem': res_origem,
                'aumento_destino_migracao': res_destino,
                'qty_transferida': 0.0,
                'qty_reduzida_origem': qty_reduzida,
                'rollback_hint': rollback_hint,
                'status': 'FALHA_AUMENTO',
                'location_id_origem': location_id_origem,
                'location_id_destino': location_id_destino,
                'lot_id_origem': lot_id_origem,
                'lot_id_destino': lot_id_destino,
                'lote_destino_nome': nome_lote_destino,
                'lote_destino_criado_agora': lote_destino_criado,
                'erro': res_destino.get('erro'),
                'tempo_ms': int((time.time() - inicio) * 1000),
            }

        return {
            'reducao_origem': res_origem,
            'aumento_destino_migracao': res_destino,
            'qty_transferida': qty,
            'status': 'DRY_RUN_OK' if dry_run else 'EXECUTADO',
            'location_id_origem': location_id_origem,
            'location_id_destino': location_id_destino,
            'lot_id_origem': lot_id_origem,
            'lot_id_destino': lot_id_destino,
            'lote_destino_nome': nome_lote_destino,
            'lote_destino_criado_agora': lote_destino_criado,
            'tempo_ms': int((time.time() - inicio) * 1000),
        }

    def transferir_quantidade_para_lote_v2(
        self,
        *,
        product_id: int,
        company_id: int,
        location_id: int,
        qty: float,
        lot_id_origem: Optional[int],
        nome_lote_destino: str,
        expiration_date_destino: Optional[str] = None,
        resetar_reserva_origem: bool = False,
        tolerancia_delta: float = 0.001,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Wrapper v2 — garante lote destino existe e transfere via v2.

        Identico ao `transferir_quantidade_para_lote` (v1) mas usa v2
        internamente, propagando delta_esperado. Resolve lote destino com
        filtro company_id (G021) e variantes MIGRACAO (G022).

        Returns:
            estrutura de `transferir_entre_lotes_v2` + chaves
            'lote_destino_nome' e 'lote_destino_criado_agora'.
        """
        lot_id_destino, nome_canonico, criado = self.resolver_lote_destino(
            nome_lote=nome_lote_destino,
            product_id=product_id,
            company_id=company_id,
            location_id=location_id,
            criar_se_faltar=True,
            expiration_date=expiration_date_destino,
        )
        if lot_id_destino is None:
            # Quant sem lote (P-15/05 proxy) — usa lot_id_destino=None.
            # ajustar_quant aceita; transferir_entre_lotes_v2 NAO (exige int).
            # Para esse caso, caller deveria usar transferir_entre_locations
            # com mesmo lot_id em ambas pontas. Por ora, levantamos.
            raise ValueError(
                f'transferir_quantidade_para_lote_v2 nao suporta destino '
                f'sem lote (nome_lote_destino={nome_lote_destino!r}). '
                f'Use transferir_entre_locations ou ajustar_quant diretamente.'
            )
        res = self.transferir_entre_lotes_v2(
            product_id=product_id,
            company_id=company_id,
            location_id=location_id,
            qty=qty,
            lot_id_origem=lot_id_origem,
            lot_id_destino=lot_id_destino,
            resetar_reserva_origem=resetar_reserva_origem,
            tolerancia_delta=tolerancia_delta,
            dry_run=dry_run,
        )
        res['lote_destino_nome'] = nome_canonico
        res['lote_destino_criado_agora'] = criado
        return res
