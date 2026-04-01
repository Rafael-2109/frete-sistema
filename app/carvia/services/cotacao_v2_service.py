"""
CotacaoV2Service — Cotacao comercial proativa CarVia
=====================================================

Fluxo: Cliente → Origem/Destino → Material (Carga Geral | Moto) → Pricing → Desconto → Aprovacao

Pricing:
- "Dentro da tabela": CarviaTabelaService.cotar_carvia() — preco de venda CarVia
- "Fora da tabela": CotacaoService.cotar_todas_opcoes() — cotacao via tabelas Nacom

Desconto:
- <= limite global (CarviaConfig): Jessica aprova direto
- > limite global: status PENDENTE_ADMIN, admin aprova/rejeita
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from app import db

logger = logging.getLogger(__name__)


class CotacaoV2Service:
    """Service para cotacoes comerciais CarVia"""

    # ==================== CRUD ====================

    @staticmethod
    def criar_cotacao(
        cliente_id: int,
        endereco_origem_id: int,
        endereco_destino_id: int,
        tipo_material: str,
        criado_por: str,
        **kwargs,
    ) -> Tuple[Optional[object], Optional[str]]:
        """Cria nova cotacao em RASCUNHO. Retorna (cotacao, erro)."""
        from app.carvia.models import (
            CarviaCotacao, CarviaCliente, CarviaClienteEndereco,
        )
        from app.utils.timezone import agora_utc_naive

        # Validacoes
        cliente = db.session.get(CarviaCliente, cliente_id)
        if not cliente:
            return None, 'Cliente nao encontrado.'

        origem = db.session.get(CarviaClienteEndereco, endereco_origem_id)
        if not origem or origem.tipo != 'ORIGEM':
            return None, 'Endereco de origem invalido.'
        # Origem global (cliente_id=None) e valida para qualquer cliente
        if origem.cliente_id is not None and origem.cliente_id != cliente_id:
            return None, 'Endereco de origem nao pertence a este cliente.'

        destino = db.session.get(CarviaClienteEndereco, endereco_destino_id)
        if not destino or destino.tipo != 'DESTINO':
            return None, 'Endereco de destino invalido.'
        if destino.cliente_id != cliente_id:
            return None, 'Endereco de destino nao pertence a este cliente.'

        tipo_material = tipo_material.upper()
        if tipo_material not in ('CARGA_GERAL', 'MOTO'):
            return None, 'Tipo de material deve ser CARGA_GERAL ou MOTO.'

        cotacao = CarviaCotacao(
            numero_cotacao='COT-TEMP',  # atualizado apos flush com COT-{id}
            cliente_id=cliente_id,
            endereco_origem_id=endereco_origem_id,
            endereco_destino_id=endereco_destino_id,
            tipo_material=tipo_material,
            criado_por=criado_por,
            criado_em=agora_utc_naive(),
            atualizado_em=agora_utc_naive(),
            data_cotacao=agora_utc_naive(),
            # Campos opcionais
            peso=kwargs.get('peso'),
            valor_mercadoria=kwargs.get('valor_mercadoria'),
            volumes=kwargs.get('volumes'),
            dimensao_c=kwargs.get('dimensao_c'),
            dimensao_l=kwargs.get('dimensao_l'),
            dimensao_a=kwargs.get('dimensao_a'),
            data_expedicao=kwargs.get('data_expedicao'),
            data_agenda=kwargs.get('data_agenda'),
            observacoes=kwargs.get('observacoes'),
            # Condicao de pagamento e responsavel do frete
            condicao_pagamento=kwargs.get('condicao_pagamento'),
            prazo_dias=kwargs.get('prazo_dias'),
            responsavel_frete=kwargs.get('responsavel_frete'),
            percentual_remetente=kwargs.get('percentual_remetente'),
            percentual_destinatario=kwargs.get('percentual_destinatario'),
        )

        # Calcular peso cubado se dimensoes fornecidas
        if cotacao.dimensao_c and cotacao.dimensao_l and cotacao.dimensao_a:
            m3 = float(cotacao.dimensao_c) * float(cotacao.dimensao_l) * float(cotacao.dimensao_a)
            cotacao.peso_cubado = Decimal(str(m3 * 300))  # fator 300

        db.session.add(cotacao)
        db.session.flush()
        # Atualizar numero_cotacao com COT-{id} apos flush (id disponivel)
        cotacao.numero_cotacao = CarviaCotacao.gerar_numero_cotacao(cotacao.id)
        return cotacao, None

    @staticmethod
    def adicionar_moto(
        cotacao_id: int,
        modelo_moto_id: int,
        quantidade: int,
        valor_unitario: float = None,
    ) -> Tuple[Optional[object], Optional[str]]:
        """Adiciona item de moto a cotacao. Retorna (item, erro)."""
        from app.carvia.models import (
            CarviaCotacao, CarviaCotacaoMoto, CarviaModeloMoto,
        )

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return None, 'Cotacao nao encontrada.'
        if cotacao.status != 'RASCUNHO':
            return None, 'Cotacao nao esta em RASCUNHO.'
        if cotacao.tipo_material != 'MOTO':
            return None, 'Cotacao nao e do tipo MOTO.'

        modelo = db.session.get(CarviaModeloMoto, modelo_moto_id)
        if not modelo:
            return None, 'Modelo de moto nao encontrado.'
        if not modelo.ativo:
            return None, 'Modelo de moto inativo.'
        if modelo.categoria_moto_id is None:
            return None, (
                f'Modelo "{modelo.nome}" sem categoria de moto configurada. '
                'Configure em Config > Modelos Moto.'
            )

        if quantidade < 1:
            return None, 'Quantidade deve ser >= 1.'

        # Calcular peso cubado
        peso_unitario = None
        peso_total = None
        if modelo.comprimento and modelo.largura and modelo.altura:
            # Dimensoes em cm, cubagem_minima em kg
            m3 = float(modelo.comprimento) * float(modelo.largura) * float(modelo.altura)
            cubagem = max(float(modelo.cubagem_minima or 300), 300)
            peso_unitario = Decimal(str(m3 * cubagem / 1_000_000))  # cm^3 → m^3 → peso cubado
            peso_total = peso_unitario * quantidade

        # Valor do produto (declaracao/seguro)
        vlr_unit = Decimal(str(valor_unitario)) if valor_unitario else None
        vlr_total = vlr_unit * quantidade if vlr_unit else None

        item = CarviaCotacaoMoto(
            cotacao_id=cotacao_id,
            modelo_moto_id=modelo_moto_id,
            categoria_moto_id=modelo.categoria_moto_id,
            quantidade=quantidade,
            peso_cubado_unitario=peso_unitario,
            peso_cubado_total=peso_total,
            valor_unitario=vlr_unit,
            valor_total=vlr_total,
        )
        db.session.add(item)
        db.session.flush()

        # Recalcular valor_mercadoria da cotacao (soma dos itens moto)
        if vlr_total:
            todas_motos = cotacao.motos.all()
            soma_valor = sum(float(m.valor_total or 0) for m in todas_motos)
            if soma_valor > 0:
                cotacao.valor_mercadoria = Decimal(str(soma_valor))

        return item, None

    # ==================== PRICING ====================

    @staticmethod
    def calcular_preco(cotacao_id: int) -> Tuple[Optional[Dict], Optional[str]]:
        """Calcula preco da cotacao. Determina dentro/fora tabela e aplica pricing.

        Retorna (resultado, erro). Resultado:
        {
            'dentro_tabela': bool,
            'valor_tabela': float,
            'tabela_carvia_id': int ou None,
            'detalhes_calculo': dict,
            'opcoes_fora_tabela': [...],  # Se fora da tabela
        }
        """
        from app.carvia.models import CarviaCotacao

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return None, 'Cotacao nao encontrada.'

        destino = cotacao.endereco_destino
        if not destino:
            return None, 'Endereco de destino nao definido.'

        # Endereco efetivo: entrega da cotacao (override) > destino cadastrado
        uf_entrega = cotacao.entrega_uf or destino.fisico_uf
        cidade_entrega = cotacao.entrega_cidade or destino.fisico_cidade

        if not uf_entrega:
            return None, 'UF de destino nao definida.'

        # Determinar peso e valor para calculo
        if cotacao.tipo_material == 'MOTO':
            peso = cotacao.peso_total_motos
            valor = float(cotacao.valor_mercadoria or 0)
        else:
            peso = float(cotacao.peso_cubado or cotacao.peso or 0)
            valor = float(cotacao.valor_mercadoria or 0)

        if peso <= 0:
            return None, 'Peso nao definido. Preencha peso ou adicione motos.'

        # DIRETA requer selecao de veiculo
        if cotacao.tipo_carga == 'DIRETA' and not cotacao.veiculo_id:
            return None, 'Selecione um veiculo para carga direta antes de calcular o preco.'

        # Tentar "dentro da tabela" — CarViaCidadeAtendida
        resultado_carvia = CotacaoV2Service._cotar_dentro_tabela(
            cotacao=cotacao,
            destino=destino,
            uf_entrega=uf_entrega,
            cidade_entrega=cidade_entrega,
            peso=peso,
            valor=valor,
        )

        if resultado_carvia:
            # Dentro da tabela CarVia
            cotacao.dentro_tabela = True
            cotacao.valor_tabela = Decimal(str(resultado_carvia['valor']))
            cotacao.tabela_carvia_id = resultado_carvia.get('tabela_carvia_id')
            cotacao.detalhes_calculo = resultado_carvia.get('detalhes')

            # Se era manual e recalculou com tabela, limpar flag manual
            if cotacao.cotacao_manual:
                cotacao.cotacao_manual = False
                cotacao.valor_manual = None

            # Reaplicar desconto com novo valor_tabela (0% se nunca definido)
            desconto = float(cotacao.percentual_desconto or 0)
            valor_desc = float(cotacao.valor_tabela) * (1 - desconto / 100)
            cotacao.valor_descontado = Decimal(str(round(valor_desc, 2)))
            cotacao.valor_final_aprovado = cotacao.valor_descontado

            db.session.flush()
            return {
                'dentro_tabela': True,
                'valor_tabela': float(cotacao.valor_tabela),
                'tabela_carvia_id': cotacao.tabela_carvia_id,
                'detalhes_calculo': cotacao.detalhes_calculo,
            }, None

        # Erro especifico para DIRETA com veiculo selecionado
        if cotacao.tipo_carga == 'DIRETA' and cotacao.veiculo_id:
            veiculo = cotacao.veiculo
            nome_v = veiculo.nome if veiculo else '?'
            return None, (
                f'Veiculo "{nome_v}" nao possui tabela de frete CarVia '
                f'para esta rota. Selecione outro veiculo ou verifique '
                f'a configuracao das tabelas.'
            )

        # Cotacao comercial nao cota fora da tabela CarVia
        return None, 'Cidade nao atendida pela tabela CarVia.'

    @staticmethod
    def _cotar_dentro_tabela(cotacao, destino, peso: float, valor: float,
                             uf_entrega: Optional[str] = None,
                             cidade_entrega: Optional[str] = None) -> Optional[Dict]:
        """Tenta cotar usando tabela CarVia (preco de venda).

        uf_entrega/cidade_entrega: endereco efetivo (cotacao override > destino).
        CNPJ vem sempre do destino cadastrado.
        """
        # Compat: se nao recebeu override, usar destino
        _uf = uf_entrega or (destino.fisico_uf if destino else None)
        _cidade = cidade_entrega or (destino.fisico_cidade if destino else None)

        try:
            from app.carvia.services.carvia_tabela_service import CarviaTabelaService
            svc = CarviaTabelaService()

            origem = cotacao.endereco_origem
            if not origem or not origem.fisico_uf or not _uf:
                return None

            cnpj_cliente = destino.cnpj if destino else None

            # Preparar categorias_moto se aplicavel
            categorias_moto = None
            if cotacao.tipo_material == 'MOTO':
                motos = cotacao.motos.all()
                if motos:
                    # Agrupar por categoria
                    cat_map = {}
                    for m in motos:
                        cid = m.categoria_moto_id
                        if cid not in cat_map:
                            cat_map[cid] = 0
                        cat_map[cid] += m.quantidade
                    categorias_moto = [
                        {'categoria_id': cid, 'quantidade': qtd}
                        for cid, qtd in cat_map.items()
                    ]

            opcoes = svc.cotar_carvia(
                uf_origem=origem.fisico_uf,
                uf_destino=_uf,
                cidade_destino=_cidade,
                peso=peso,
                valor_mercadoria=valor,
                cnpj_cliente=cnpj_cliente,
                tipo_carga=cotacao.tipo_carga,
                categorias_moto=categorias_moto,
            )

            # DIRETA + veiculo selecionado: filtrar por modalidade do veiculo
            if cotacao.tipo_carga == 'DIRETA' and cotacao.veiculo_id and opcoes:
                veiculo = cotacao.veiculo
                if veiculo:
                    nome_v = (veiculo.nome or '').strip().upper()
                    opcoes = [
                        o for o in opcoes
                        if (o.get('modalidade') or '').strip().upper() == nome_v
                    ]

            # cotar_carvia retorna List[Dict] ordenado por valor (menor primeiro)
            if opcoes and len(opcoes) > 0:
                melhor = opcoes[0]
                return {
                    'valor': melhor.get('valor_frete', 0),
                    'tabela_carvia_id': melhor.get('tabela_carvia_id'),
                    'detalhes': melhor.get('detalhes'),
                }
        except Exception as e:
            logger.warning("Erro ao cotar dentro tabela: %s", e)

        return None

    @staticmethod
    def _cotar_fora_tabela(peso: float, valor: float,
                          uf_entrega: Optional[str] = None,
                          cidade_entrega: Optional[str] = None,
                          destino=None) -> List[Dict]:
        """Cota via tabelas Nacom (fora da tabela CarVia). Retorna lista de opcoes.

        uf_entrega/cidade_entrega: endereco efetivo (cotacao override > destino).
        """
        # Compat: se nao recebeu override, usar destino
        _uf = uf_entrega or (destino.fisico_uf if destino else None)
        _cidade = cidade_entrega or (destino.fisico_cidade if destino else None)

        try:
            from app.carvia.services.cotacao_service import CotacaoService
            svc = CotacaoService()

            if not _cidade or not _uf:
                return []

            # cotar_todas_opcoes retorna List[Dict]
            opcoes = svc.cotar_todas_opcoes(
                cidade_destino=_cidade,
                uf_destino=_uf,
                peso=peso,
                valor_mercadoria=valor,
            )

            if opcoes:
                return opcoes
        except Exception as e:
            logger.warning("Erro ao cotar fora tabela: %s", e)

        return []

    # ==================== COTACAO MANUAL ====================

    @staticmethod
    def definir_valor_manual(
        cotacao_id: int,
        valor: float,
        usuario: str,
    ) -> Tuple[bool, Optional[str]]:
        """Define valor manual para cotacao (sem lookup de tabela).

        Cotacao vai para PENDENTE_ADMIN automaticamente.
        Permite cotar mesmo sem cidade atendida ou tabela cadastrada.
        """
        from app.carvia.models import CarviaCotacao
        from app.utils.timezone import agora_utc_naive

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return False, 'Cotacao nao encontrada.'
        if cotacao.status not in ('RASCUNHO', 'PENDENTE_ADMIN'):
            return False, f'Cotacao em status {cotacao.status} nao permite valor manual.'

        if valor <= 0:
            return False, 'Valor deve ser positivo.'

        cotacao.cotacao_manual = True
        cotacao.valor_manual = Decimal(str(valor))
        cotacao.valor_tabela = None
        cotacao.tabela_carvia_id = None
        cotacao.dentro_tabela = None
        cotacao.percentual_desconto = Decimal('0')
        cotacao.valor_descontado = Decimal(str(valor))
        cotacao.valor_final_aprovado = Decimal(str(valor))
        cotacao.detalhes_calculo = {
            'tipo': 'manual',
            'valor_manual': valor,
            'definido_por': usuario,
            'definido_em': str(agora_utc_naive()),
        }
        cotacao.status = 'PENDENTE_ADMIN'

        db.session.flush()
        return True, None

    # ==================== SUGESTAO DE VEICULO ====================

    @staticmethod
    def sugerir_veiculo(peso: float) -> Optional[int]:
        """Sugere o menor veiculo cujo peso_maximo >= peso.

        Retorna veiculo_id ou None se nenhum comporta o peso.
        """
        from app.veiculos.models import Veiculo

        if peso <= 0:
            return None

        veiculo = Veiculo.query.filter(
            Veiculo.peso_maximo >= peso
        ).order_by(
            Veiculo.peso_maximo.asc()
        ).first()

        return veiculo.id if veiculo else None

    # ==================== DESCONTO ====================

    @staticmethod
    def aplicar_desconto(
        cotacao_id: int,
        percentual_desconto: float,
        usuario: str,
    ) -> Tuple[bool, Optional[str]]:
        """Aplica desconto na cotacao. Se > limite, muda para PENDENTE_ADMIN."""
        from app.carvia.models import CarviaCotacao
        from app.carvia.services.config_service import CarviaConfigService

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return False, 'Cotacao nao encontrada.'
        if cotacao.status not in ('RASCUNHO', 'PENDENTE_ADMIN'):
            return False, f'Cotacao em status {cotacao.status} nao permite desconto.'
        if cotacao.cotacao_manual:
            return False, 'Cotacao manual nao permite desconto. Use valor manual diretamente.'
        if cotacao.valor_tabela is None:
            return False, 'Cotacao sem valor de tabela. Calcule o preco primeiro.'

        valor_tabela = float(cotacao.valor_tabela)
        desconto = float(percentual_desconto)

        # Permite desconto negativo (markup = venda acima da tabela)
        if desconto > 100:
            return False, 'Desconto nao pode exceder 100%.'

        valor_desc = valor_tabela * (1 - desconto / 100)

        cotacao.percentual_desconto = Decimal(str(desconto))
        cotacao.valor_descontado = Decimal(str(round(valor_desc, 2)))
        cotacao.valor_final_aprovado = cotacao.valor_descontado

        # Verificar limite — markup (desconto < 0) nao requer aprovacao
        limite = CarviaConfigService.limite_desconto_percentual()
        if desconto > limite:
            cotacao.status = 'PENDENTE_ADMIN'
        else:
            # Markup (acima tabela) ou desconto dentro do limite — livre
            if cotacao.status == 'PENDENTE_ADMIN':
                cotacao.status = 'RASCUNHO'

        db.session.flush()
        return True, None

    # ==================== TRANSICOES DE STATUS ====================

    @staticmethod
    def admin_aprovar(cotacao_id: int, aprovado_por: str) -> Tuple[bool, Optional[str]]:
        """Admin aprova cotacao pendente."""
        from app.carvia.models import CarviaCotacao
        from app.utils.timezone import agora_utc_naive

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return False, 'Cotacao nao encontrada.'
        if cotacao.status != 'PENDENTE_ADMIN':
            return False, f'Cotacao em status {cotacao.status}, esperado PENDENTE_ADMIN.'

        cotacao.status = 'RASCUNHO'  # Volta para Jessica continuar
        cotacao.aprovado_por = aprovado_por
        cotacao.aprovado_em = agora_utc_naive()
        db.session.flush()
        return True, None

    @staticmethod
    def admin_rejeitar(cotacao_id: int) -> Tuple[bool, Optional[str]]:
        """Admin rejeita cotacao pendente."""
        from app.carvia.models import CarviaCotacao

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return False, 'Cotacao nao encontrada.'
        if cotacao.status != 'PENDENTE_ADMIN':
            return False, f'Cotacao em status {cotacao.status}, esperado PENDENTE_ADMIN.'

        cotacao.status = 'RECUSADO'
        db.session.flush()
        return True, None

    @staticmethod
    def marcar_enviado(cotacao_id: int, enviado_por: str) -> Tuple[bool, Optional[str]]:
        """Jessica marca cotacao como enviada ao cliente."""
        from app.carvia.models import CarviaCotacao
        from app.utils.timezone import agora_utc_naive

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return False, 'Cotacao nao encontrada.'
        if cotacao.status != 'RASCUNHO':
            return False, f'Cotacao em status {cotacao.status}, esperado RASCUNHO.'
        if cotacao.valor_final_aprovado is None:
            return False, 'Cotacao sem valor final. Calcule o preco primeiro.'
        if cotacao.data_expedicao is None:
            return False, 'Data de expedicao obrigatoria antes de gravar.'

        # Bloquear se destino provisorio sem CNPJ
        destino = cotacao.endereco_destino
        if destino and destino.provisorio and not destino.cnpj:
            return False, (
                'Destino provisorio sem CNPJ. Preencha o CNPJ do destino antes de gravar.'
            )

        cotacao.status = 'ENVIADO'
        db.session.flush()
        return True, None

    @staticmethod
    def registrar_aprovacao_cliente(cotacao_id: int, aprovado_por: str) -> Tuple[bool, Optional[str]]:
        """Registra aprovacao do cliente."""
        from app.carvia.models import CarviaCotacao
        from app.utils.timezone import agora_utc_naive

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return False, 'Cotacao nao encontrada.'
        if cotacao.status != 'ENVIADO':
            return False, f'Cotacao em status {cotacao.status}, esperado ENVIADO.'

        cotacao.status = 'APROVADO'
        cotacao.aprovado_por = aprovado_por
        cotacao.aprovado_em = agora_utc_naive()
        db.session.flush()
        return True, None

    @staticmethod
    def registrar_recusa_cliente(cotacao_id: int) -> Tuple[bool, Optional[str]]:
        """Registra recusa do cliente."""
        from app.carvia.models import CarviaCotacao

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return False, 'Cotacao nao encontrada.'
        if cotacao.status != 'ENVIADO':
            return False, f'Cotacao em status {cotacao.status}, esperado ENVIADO.'

        cotacao.status = 'RECUSADO'
        db.session.flush()
        return True, None

    @staticmethod
    def registrar_contra_proposta(
        cotacao_id: int,
        novo_valor: float,
    ) -> Tuple[bool, Optional[str]]:
        """Registra contra-proposta do cliente com novo valor.

        Se desconto implícito excede limite, bloqueia para aprovação admin.
        """
        from app.carvia.models import CarviaCotacao
        from app.carvia.services.config_service import CarviaConfigService

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return False, 'Cotacao nao encontrada.'
        if cotacao.status != 'ENVIADO':
            return False, f'Cotacao em status {cotacao.status}, esperado ENVIADO.'

        if novo_valor <= 0:
            return False, 'Valor da contra-proposta deve ser positivo.'

        # Cotacao manual: atualiza valor_manual, re-envia para admin
        if cotacao.cotacao_manual:
            cotacao.valor_manual = Decimal(str(novo_valor))
            cotacao.valor_descontado = Decimal(str(novo_valor))
            cotacao.valor_final_aprovado = Decimal(str(novo_valor))
            cotacao.status = 'PENDENTE_ADMIN'
            db.session.flush()
            return True, None

        # Recalcular desconto com base no novo valor
        valor_tabela = float(cotacao.valor_tabela or 0)
        if valor_tabela > 0:
            desconto = ((valor_tabela - novo_valor) / valor_tabela) * 100
        else:
            desconto = 0

        cotacao.valor_final_aprovado = Decimal(str(novo_valor))
        cotacao.percentual_desconto = Decimal(str(round(desconto, 2)))
        cotacao.valor_descontado = Decimal(str(novo_valor))

        # Verificar limite de desconto — markup (desconto < 0) nao requer admin
        limite = CarviaConfigService.limite_desconto_percentual()
        if desconto > limite:
            cotacao.status = 'PENDENTE_ADMIN'
        else:
            cotacao.status = 'RASCUNHO'

        db.session.flush()
        return True, None

    @staticmethod
    def reabrir(cotacao_id: int, reaberto_por: str) -> Tuple[bool, Optional[str]]:
        """Reabre cotacao APROVADA, voltando para RASCUNHO.

        Bloqueia se houver pedidos EMBARCADO ou em embarque (COTADO).
        """
        from app.carvia.models import CarviaCotacao, CarviaPedido
        from app.utils.timezone import agora_utc_naive

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return False, 'Cotacao nao encontrada.'
        if cotacao.status != 'APROVADO':
            return False, f'Cotacao em status {cotacao.status}, esperado APROVADO.'

        # Verificar se ha pedidos embarcados (irreversivel)
        pedidos_embarcados = CarviaPedido.query.filter(
            CarviaPedido.cotacao_id == cotacao_id,
            CarviaPedido.status == 'EMBARCADO',
        ).count()
        if pedidos_embarcados > 0:
            return False, (
                f'Cotacao possui {pedidos_embarcados} pedido(s) EMBARCADO. '
                'Nao e possivel reabrir.'
            )

        # Verificar se ha pedidos em embarque (cotados)
        from app.embarques.models import EmbarqueItem
        em_embarque = EmbarqueItem.query.filter(
            EmbarqueItem.carvia_cotacao_id == cotacao_id,
            EmbarqueItem.status == 'ativo',
        ).count()
        if em_embarque > 0:
            return False, (
                'Cotacao possui pedido(s) em embarque. '
                'Remova do embarque antes de reabrir.'
            )

        cotacao.status = 'RASCUNHO'
        cotacao.aprovado_por = None
        cotacao.aprovado_em = None
        cotacao.atualizado_em = agora_utc_naive()
        db.session.flush()
        return True, None

    @staticmethod
    def cancelar(cotacao_id: int) -> Tuple[bool, Optional[str]]:
        """Cancela cotacao de qualquer status (exceto CANCELADO).

        Bloqueia se houver pedidos EMBARCADO (irreversivel).
        Cancela pedidos vinculados em cascata e remove EmbarqueItems.
        """
        from app.carvia.models import CarviaCotacao, CarviaPedido

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return False, 'Cotacao nao encontrada.'
        if cotacao.status == 'CANCELADO':
            return False, 'Cotacao ja esta cancelada.'

        # Bloquear se algum pedido EMBARCADO (irreversivel)
        pedidos_embarcados = CarviaPedido.query.filter(
            CarviaPedido.cotacao_id == cotacao_id,
            CarviaPedido.status == 'EMBARCADO',
        ).count()
        if pedidos_embarcados > 0:
            return False, (
                f'Cotacao possui {pedidos_embarcados} pedido(s) EMBARCADO. '
                'Nao e possivel cancelar.'
            )

        # Limpar embarque: provisorio + reais (nao-bloqueante)
        try:
            from app.carvia.services.embarque_carvia_service import EmbarqueCarViaService
            EmbarqueCarViaService.remover_itens_cotacao(cotacao_id)
        except Exception as e:
            logger.warning("Erro ao limpar embarque da cotacao: %s", e)

        # Cascata: cancelar todos pedidos nao-CANCELADO
        pedidos = CarviaPedido.query.filter(
            CarviaPedido.cotacao_id == cotacao_id,
            CarviaPedido.status != 'CANCELADO',
        ).all()
        for pedido in pedidos:
            pedido.status = 'CANCELADO'

        cotacao.status = 'CANCELADO'
        db.session.flush()

        if pedidos:
            logger.info(
                "Cotacao %s cancelada. %d pedido(s) cancelado(s) em cascata.",
                cotacao_id, len(pedidos),
            )

        return True, None

    # ==================== LISTAGEM ====================

    @staticmethod
    def listar_cotacoes(
        status: Optional[str] = None,
        cliente_id: Optional[int] = None,
        alerta: Optional[str] = None,
    ) -> List:
        """Lista cotacoes com filtros opcionais."""
        from app.carvia.models import CarviaCotacao

        query = CarviaCotacao.query

        if status:
            query = query.filter_by(status=status)
        if cliente_id:
            query = query.filter_by(cliente_id=cliente_id)
        if alerta == 'saida_sem_nf':
            query = query.filter_by(alerta_saida_sem_nf=True)

        return query.order_by(CarviaCotacao.criado_em.desc()).all()

    @staticmethod
    def listar_pendentes_admin() -> List:
        """Lista cotacoes aguardando aprovacao do admin."""
        return CotacaoV2Service.listar_cotacoes(status='PENDENTE_ADMIN')
