"""
Service de Importação FASE 4: Pedidos e Vendas - Sistema MotoChefe
Data: 15/10/2025

IMPORTANTE:
- Esta fase importa pedidos HISTÓRICOS com chassis já vinculados
- TODAS as funções automáticas são executadas:
  * Atualizar status das motos
  * Gerar títulos financeiros (A RECEBER)
  * Gerar títulos a pagar (PENDENTES)
  * Calcular vencimentos
  * Calcular comissões

ESTRUTURA DO EXCEL:
1. Aba "Pedidos" - Cabeçalho dos pedidos
2. Aba "Itens" - Itens com chassis vinculados
"""
import pandas as pd
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
import traceback

from app import db
from app.motochefe.models.vendas import PedidoVendaMoto, PedidoVendaMotoItem
from app.motochefe.models.cadastro import ClienteMoto, VendedorMoto, EquipeVendasMoto, TransportadoraMoto, EmpresaVendaMoto
from app.motochefe.models.produto import Moto
from app.motochefe.models.financeiro import TituloFinanceiro, TituloAPagar

# Services para funções automáticas
from app.motochefe.services.titulo_service import gerar_titulos_com_fifo_parcelas
from app.motochefe.services.titulo_a_pagar_service import (
    criar_titulo_a_pagar_movimentacao,
    criar_titulo_a_pagar_montagem
)


class ResultadoImportacaoFase4:
    """Classe para armazenar resultado de importação da Fase 4"""
    def __init__(self):
        self.sucesso = False
        self.mensagem = ""
        self.total_pedidos = 0
        self.pedidos_inseridos = 0
        self.pedidos_atualizados = 0
        self.total_itens = 0
        self.itens_inseridos = 0
        self.total_titulos_financeiros = 0
        self.total_titulos_a_pagar = 0
        self.total_comissoes = 0
        self.motos_atualizadas = 0
        self.erros = []
        self.avisos = []

    def to_dict(self):
        return {
            'sucesso': self.sucesso,
            'mensagem': self.mensagem,
            'total_pedidos': self.total_pedidos,
            'pedidos_inseridos': self.pedidos_inseridos,
            'pedidos_atualizados': self.pedidos_atualizados,
            'total_itens': self.total_itens,
            'itens_inseridos': self.itens_inseridos,
            'total_titulos_financeiros': self.total_titulos_financeiros,
            'total_titulos_a_pagar': self.total_titulos_a_pagar,
            'total_comissoes': self.total_comissoes,
            'motos_atualizadas': self.motos_atualizadas,
            'erros': self.erros,
            'avisos': self.avisos
        }


class ImportacaoFase4Service:
    """Service para importação de Pedidos (Fase 4)"""

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def converter_data(valor):
        """Converte valor para date"""
        if pd.isna(valor) or valor is None or valor == '':
            return None

        if isinstance(valor, (date, datetime)):
            return valor if isinstance(valor, date) else valor.date()

        try:
            if isinstance(valor, str):
                for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                    try:
                        return datetime.strptime(valor, fmt).date()
                    except ValueError:
                        continue
            return None
        except Exception:
            return None

    @staticmethod
    def converter_decimal(valor, casas_decimais=2):
        """Converte valor para Decimal"""
        if pd.isna(valor) or valor is None or valor == '':
            return Decimal('0')

        try:
            if isinstance(valor, str):
                valor = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
            return Decimal(str(valor)).quantize(Decimal(f'0.{"0" * casas_decimais}'))
        except Exception:
            return Decimal('0')

    @staticmethod
    def converter_inteiro(valor, padrao=0):
        """Converte valor para inteiro"""
        if pd.isna(valor) or valor is None or valor == '':
            return padrao
        try:
            return int(valor)
        except Exception:
            return padrao

    @staticmethod
    def converter_boolean(valor):
        """Converte valor para boolean"""
        if pd.isna(valor) or valor is None or valor == '':
            return False

        if isinstance(valor, bool):
            return valor

        if isinstance(valor, str):
            return valor.upper() in ['SIM', 'TRUE', 'VERDADEIRO', '1', 'S', 'V', 'YES']

        return bool(valor)

    @staticmethod
    def converter_string(valor):
        """Converte valor para string, tratando NaN do pandas"""
        if pd.isna(valor) or valor is None or valor == '':
            return None

        valor_str = str(valor).strip()

        if valor_str.lower() == 'nan' or valor_str == '':
            return None

        return valor_str

    # ============================================================
    # IMPORTAÇÃO DE PEDIDOS E ITENS
    # ============================================================

    @staticmethod
    def importar_pedidos_completo(df_pedidos, df_itens, usuario='sistema'):
        """
        Importa pedidos com itens (chassis vinculados) e executa TODAS as funções automáticas

        Colunas de df_pedidos esperadas:
        - numero_pedido (obrigatório - PK)
        - cliente_cnpj (obrigatório - busca por CNPJ)
        - vendedor (obrigatório - busca por nome)
        - data_pedido (obrigatório)
        - data_expedicao (opcional)
        - status (APROVADO, PENDENTE, etc - padrão: APROVADO)
        - faturado (boolean - padrão: False)
        - numero_nf (opcional - se faturado)
        - data_nf (opcional - se faturado)
        - empresa_venda (opcional - nome da empresa - se faturado)
        - forma_pagamento (opcional)
        - condicao_pagamento (opcional)
        - prazo_dias (int - padrão: 0)
        - numero_parcelas (int - padrão: 1)
        - transportadora (opcional - nome)
        - tipo_frete (CIF, FOB)
        - observacoes (opcional)

        Colunas de df_itens esperadas:
        - numero_pedido (obrigatório - FK)
        - numero_chassi (obrigatório - FK)
        - preco_venda (obrigatório)
        - montagem_contratada (boolean - padrão: False)
        - valor_montagem (decimal - padrão: 0)
        - fornecedor_montagem (opcional)

        ⚠️ FUNÇÕES AUTOMÁTICAS EXECUTADAS:
        1. Atualizar moto.status (RESERVADA ou VENDIDA)
        2. Gerar títulos financeiros (A RECEBER) com vencimentos
        3. Gerar títulos a pagar (PENDENTES)
        4. Calcular comissões dos vendedores
        """
        resultado = ResultadoImportacaoFase4()
        resultado.total_pedidos = len(df_pedidos)

        try:
            # Dicionário para cache de consultas
            cache_clientes = {}
            cache_vendedores = {}
            cache_transportadoras = {}
            cache_empresas = {}

            for idx_ped, row_ped in df_pedidos.iterrows():
                linha_pedido = idx_ped + 2

                # ========================================
                # 1. LER DADOS DO PEDIDO
                # ========================================

                numero_pedido = ImportacaoFase4Service.converter_string(row_ped.get('numero_pedido'))
                cliente_cnpj = ImportacaoFase4Service.converter_string(row_ped.get('cliente_cnpj'))
                vendedor_nome = ImportacaoFase4Service.converter_string(row_ped.get('vendedor'))

                if not numero_pedido:
                    raise ValueError(f"Linha {linha_pedido} (Pedidos): Número do pedido é obrigatório")
                if not cliente_cnpj:
                    raise ValueError(f"Linha {linha_pedido} (Pedidos): CNPJ do cliente é obrigatório")
                if not vendedor_nome:
                    raise ValueError(f"Linha {linha_pedido} (Pedidos): Vendedor é obrigatório")

                # Buscar cliente (com cache)
                cliente_cnpj_limpo = cliente_cnpj.replace('.', '').replace('/', '').replace('-', '').strip()
                if cliente_cnpj_limpo not in cache_clientes:
                    cliente = ClienteMoto.query.filter_by(cnpj_cliente=cliente_cnpj_limpo, ativo=True).first()
                    if not cliente:
                        raise ValueError(f"Linha {linha_pedido}: Cliente CNPJ '{cliente_cnpj}' não encontrado")
                    cache_clientes[cliente_cnpj_limpo] = cliente
                cliente = cache_clientes[cliente_cnpj_limpo]

                # Buscar vendedor (com cache, case-insensitive)
                vendedor_upper = vendedor_nome.upper()
                if vendedor_upper not in cache_vendedores:
                    vendedor = VendedorMoto.query.filter(
                        func.upper(VendedorMoto.vendedor) == vendedor_upper,
                        VendedorMoto.ativo == True
                    ).first()
                    if not vendedor:
                        raise ValueError(f"Linha {linha_pedido}: Vendedor '{vendedor_nome}' não encontrado")
                    cache_vendedores[vendedor_upper] = vendedor
                vendedor = cache_vendedores[vendedor_upper]

                # Buscar transportadora (opcional, com cache)
                transportadora_id = None
                transportadora_nome = ImportacaoFase4Service.converter_string(row_ped.get('transportadora'))
                if transportadora_nome:
                    transportadora_upper = transportadora_nome.upper()
                    if transportadora_upper not in cache_transportadoras:
                        transportadora = TransportadoraMoto.query.filter(
                            func.upper(TransportadoraMoto.transportadora) == transportadora_upper,
                            TransportadoraMoto.ativo == True
                        ).first()
                        cache_transportadoras[transportadora_upper] = transportadora
                    transportadora = cache_transportadoras[transportadora_upper]
                    if transportadora:
                        transportadora_id = transportadora.id

                # Buscar empresa (opcional, com cache)
                empresa_venda_id = None
                empresa_nome = ImportacaoFase4Service.converter_string(row_ped.get('empresa_venda'))
                if empresa_nome:
                    empresa_upper = empresa_nome.upper()
                    if empresa_upper not in cache_empresas:
                        empresa = EmpresaVendaMoto.query.filter(
                            func.upper(EmpresaVendaMoto.empresa) == empresa_upper,
                            EmpresaVendaMoto.ativo == True
                        ).first()
                        cache_empresas[empresa_upper] = empresa
                    empresa = cache_empresas[empresa_upper]
                    if empresa:
                        empresa_venda_id = empresa.id

                # Datas
                data_pedido = ImportacaoFase4Service.converter_data(row_ped.get('data_pedido'))
                if not data_pedido:
                    data_pedido = date.today()

                data_expedicao = ImportacaoFase4Service.converter_data(row_ped.get('data_expedicao'))
                data_nf = ImportacaoFase4Service.converter_data(row_ped.get('data_nf'))

                # Status e faturamento
                status = ImportacaoFase4Service.converter_string(row_ped.get('status')) or 'APROVADO'
                faturado = ImportacaoFase4Service.converter_boolean(row_ped.get('faturado'))
                numero_nf = ImportacaoFase4Service.converter_string(row_ped.get('numero_nf'))

                # Valores
                prazo_dias = ImportacaoFase4Service.converter_inteiro(row_ped.get('prazo_dias'), 0)
                numero_parcelas = ImportacaoFase4Service.converter_inteiro(row_ped.get('numero_parcelas'), 1)

                # ========================================
                # 2. CRIAR/ATUALIZAR PEDIDO (UPSERT)
                # ========================================

                pedido = PedidoVendaMoto.query.filter_by(numero_pedido=numero_pedido).first()

                if pedido:
                    resultado.pedidos_atualizados += 1
                    pedido.atualizado_por = usuario
                    pedido.atualizado_em = datetime.utcnow()
                else:
                    pedido = PedidoVendaMoto()
                    pedido.numero_pedido = numero_pedido
                    pedido.criado_por = usuario
                    resultado.pedidos_inseridos += 1

                # Preencher campos do pedido
                pedido.cliente_id = cliente.id
                pedido.vendedor_id = vendedor.id
                pedido.equipe_vendas_id = vendedor.equipe_vendas_id
                pedido.data_pedido = data_pedido
                pedido.data_expedicao = data_expedicao
                pedido.status = status
                pedido.ativo = (status == 'APROVADO')  # Só ativa se aprovado
                pedido.faturado = faturado
                pedido.numero_nf = numero_nf
                pedido.data_nf = data_nf
                pedido.empresa_venda_id = empresa_venda_id
                pedido.forma_pagamento = ImportacaoFase4Service.converter_string(row_ped.get('forma_pagamento'))
                pedido.condicao_pagamento = ImportacaoFase4Service.converter_string(row_ped.get('condicao_pagamento'))
                pedido.prazo_dias = prazo_dias
                pedido.numero_parcelas = numero_parcelas
                pedido.transportadora_id = transportadora_id
                pedido.tipo_frete = ImportacaoFase4Service.converter_string(row_ped.get('tipo_frete'))
                pedido.observacoes = ImportacaoFase4Service.converter_string(row_ped.get('observacoes'))

                db.session.add(pedido)
                db.session.flush()  # Gera ID do pedido

                # ========================================
                # 3. PROCESSAR ITENS DO PEDIDO
                # ========================================

                # Filtrar itens deste pedido
                itens_pedido = df_itens[df_itens['numero_pedido'] == numero_pedido]
                resultado.total_itens += len(itens_pedido)

                if len(itens_pedido) == 0:
                    resultado.avisos.append(f"Pedido {numero_pedido}: Sem itens vinculados")

                itens_criados = []
                valor_total_calculado = Decimal('0')

                for idx_item, row_item in itens_pedido.iterrows():
                    linha_item = idx_item + 2

                    numero_chassi = ImportacaoFase4Service.converter_string(row_item.get('numero_chassi'))
                    if not numero_chassi:
                        raise ValueError(f"Linha {linha_item} (Itens): Número do chassi é obrigatório")

                    # Buscar moto
                    moto = Moto.query.filter_by(numero_chassi=numero_chassi, ativo=True).first()
                    if not moto:
                        raise ValueError(f"Linha {linha_item} (Itens): Chassi '{numero_chassi}' não encontrado")

                    # Verificar se item já existe (UPSERT)
                    item = PedidoVendaMotoItem.query.filter_by(
                        pedido_id=pedido.id,
                        numero_chassi=numero_chassi
                    ).first()

                    if not item:
                        item = PedidoVendaMotoItem()
                        item.pedido_id = pedido.id
                        item.numero_chassi = numero_chassi
                        item.criado_por = usuario
                        resultado.itens_inseridos += 1

                    # Preencher campos do item
                    item.preco_venda = ImportacaoFase4Service.converter_decimal(row_item.get('preco_venda'))
                    item.montagem_contratada = ImportacaoFase4Service.converter_boolean(row_item.get('montagem_contratada'))
                    item.valor_montagem = ImportacaoFase4Service.converter_decimal(row_item.get('valor_montagem'))
                    item.fornecedor_montagem = ImportacaoFase4Service.converter_string(row_item.get('fornecedor_montagem'))

                    db.session.add(item)
                    itens_criados.append(item)

                    valor_total_calculado += item.preco_venda + (item.valor_montagem or Decimal('0'))

                    # ✅ ATUALIZAR STATUS DA MOTO
                    if faturado:
                        moto.status = 'VENDIDA'  # Pedido já faturado
                    else:
                        moto.status = 'RESERVADA'  # Pedido não faturado
                    moto.reservado = True
                    resultado.motos_atualizadas += 1

                # Atualizar valor total do pedido
                pedido.valor_total_pedido = valor_total_calculado

                db.session.flush()  # Garante que itens tenham ID

                # ========================================
                # 4. GERAR TÍTULOS FINANCEIROS (A RECEBER)
                # ========================================

                # Montar configuração de parcelas
                parcelas_config = []
                for n_parcela in range(1, numero_parcelas + 1):
                    parcelas_config.append({
                        'numero': n_parcela,
                        'valor': float(valor_total_calculado / numero_parcelas),
                        'prazo_dias': prazo_dias
                    })

                # Gerar títulos usando o service
                titulos_financeiros = gerar_titulos_com_fifo_parcelas(
                    pedido,
                    itens_criados,
                    parcelas_config
                )

                # ✅ CALCULAR data_vencimento
                data_base = data_expedicao or data_pedido
                for titulo in titulos_financeiros:
                    if titulo.prazo_dias is not None:
                        titulo.data_vencimento = data_base + timedelta(days=titulo.prazo_dias)

                resultado.total_titulos_financeiros += len(titulos_financeiros)

                # ========================================
                # 5. GERAR TÍTULOS A PAGAR (PENDENTES)
                # ========================================

                equipe = vendedor.equipe if vendedor else None

                for titulo in titulos_financeiros:
                    if titulo.tipo_titulo == 'MOVIMENTACAO':
                        custo_real = equipe.custo_movimentacao if equipe else Decimal('0')
                        if custo_real > 0:
                            titulo_pagar = criar_titulo_a_pagar_movimentacao(titulo, custo_real)
                            if titulo_pagar:
                                resultado.total_titulos_a_pagar += 1

                    elif titulo.tipo_titulo == 'MONTAGEM':
                        item = next((i for i in itens_criados if i.numero_chassi == titulo.numero_chassi), None)
                        if item and item.montagem_contratada:
                            titulo_pagar = criar_titulo_a_pagar_montagem(titulo, item)
                            if titulo_pagar:
                                resultado.total_titulos_a_pagar += 1

                db.session.flush()

                # ========================================
                # 6. CALCULAR COMISSÕES (FUTURO)
                # ========================================
                # TODO: Implementar calcular_comissoes_pedido(pedido) quando service estiver pronto

            # Commit final
            db.session.commit()
            resultado.sucesso = True
            resultado.mensagem = f"✅ Pedidos importados: {resultado.pedidos_inseridos} novos, {resultado.pedidos_atualizados} atualizados | Itens: {resultado.itens_inseridos} | Títulos Financeiros: {resultado.total_titulos_financeiros} | Títulos a Pagar: {resultado.total_titulos_a_pagar}"

        except Exception as e:
            db.session.rollback()
            resultado.sucesso = False
            resultado.mensagem = f"❌ Erro: {str(e)}"
            resultado.erros.append(str(e))
            resultado.erros.append(traceback.format_exc())

        return resultado

    # ============================================================
    # GERAÇÃO DE TEMPLATES
    # ============================================================

    @staticmethod
    def gerar_template_fase4():
        """Gera arquivo Excel com templates da Fase 4"""
        with pd.ExcelWriter('/tmp/motochefe_fase4_templates.xlsx', engine='openpyxl') as writer:
            # Pedidos
            df_pedidos = pd.DataFrame(columns=[
                'numero_pedido', 'cliente_cnpj', 'vendedor', 'data_pedido', 'data_expedicao',
                'status', 'faturado', 'numero_nf', 'data_nf', 'empresa_venda',
                'forma_pagamento', 'condicao_pagamento', 'prazo_dias', 'numero_parcelas',
                'transportadora', 'tipo_frete', 'observacoes'
            ])
            df_pedidos.to_excel(writer, sheet_name='1_Pedidos', index=False)

            # Itens
            df_itens = pd.DataFrame(columns=[
                'numero_pedido', 'numero_chassi', 'preco_venda',
                'montagem_contratada', 'valor_montagem', 'fornecedor_montagem'
            ])
            df_itens.to_excel(writer, sheet_name='2_Itens', index=False)

        return '/tmp/motochefe_fase4_templates.xlsx'
