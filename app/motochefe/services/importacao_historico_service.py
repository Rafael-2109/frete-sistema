"""
Service de Importação de Dados Históricos - Sistema MotoCHEFE
FASES 5, 6 e 7: Comissões, Montagens e Movimentações históricas

IMPORTANTE:
- Usa OPÇÃO A: Altera valor_original dos títulos VENDA (dedução direta)
- Válido APENAS para importação histórica (pedidos já concluídos)
- Cria MovimentacaoFinanceira PAI/FILHO para lotes PAGOS
- Atualiza saldos de empresas retroativamente
"""
import pandas as pd
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from app.utils.timezone import agora_utc_naive
from sqlalchemy import func
import traceback
from io import BytesIO

from app import db
from app.motochefe.models.vendas import PedidoVendaMoto, PedidoVendaMotoItem
from app.motochefe.models.financeiro import TituloFinanceiro, TituloAPagar, ComissaoVendedor, MovimentacaoFinanceira
from app.motochefe.models.cadastro import EmpresaVendaMoto, VendedorMoto
from app.motochefe.services.empresa_service import atualizar_saldo, garantir_margem_sogima


# ============================================================
# HELPERS
# ============================================================

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


def converter_string(valor):
    """Converte valor para string, tratando NaN do pandas"""
    if pd.isna(valor) or valor is None or valor == '':
        return None

    valor_str = str(valor).strip()

    if valor_str.lower() == 'nan' or valor_str == '':
        return None

    return valor_str


def buscar_empresa(nome_empresa):
    """Busca empresa por nome (case-insensitive)"""
    if not nome_empresa:
        raise ValueError("Nome da empresa é obrigatório")

    empresa = EmpresaVendaMoto.query.filter(
        func.upper(EmpresaVendaMoto.empresa) == nome_empresa.upper(),
        EmpresaVendaMoto.ativo == True
    ).first()

    if not empresa:
        raise ValueError(f"Empresa '{nome_empresa}' não encontrada ou inativa")

    return empresa


# ============================================================
# FASE 5: COMISSÕES HISTÓRICAS
# ============================================================

class ResultadoImportacaoComissoes:
    """Classe para armazenar resultado da importação de comissões"""
    def __init__(self):
        self.sucesso = False
        self.mensagem = ""
        self.total_linhas = 0
        self.comissoes_criadas = 0
        self.comissoes_pagas = 0
        self.comissoes_pendentes = 0
        self.movimentacoes_pai_criadas = 0
        self.movimentacoes_filhas_criadas = 0
        self.valor_total_pago = Decimal('0')
        self.erros = []
        self.avisos = []


def importar_comissoes_historico(df_comissoes, usuario='IMPORTACAO_HISTORICO'):
    """
    FASE 5: Importa comissões históricas do Excel

    Colunas esperadas:
    - numero_pedido (obrigatório)
    - numero_chassi (obrigatório)
    - vendedor (obrigatório) - Nome do vendedor
    - valor_comissao (obrigatório)
    - status_pagamento ('PAGO' ou 'PENDENTE')
    - data_pagamento (obrigatório se status='PAGO')
    - empresa_pagadora (obrigatório se status='PAGO')

    Regras:
    - Pode haver MÚLTIPLAS comissões por chassi (diferentes vendedores)
    - Pode haver APENAS 1 comissão por vendedor+chassi (valida duplicidade)

    Lógica:
    1. Valida vendedor existe
    2. Valida duplicidade (vendedor + chassi)
    3. Cria ComissaoVendedor para cada linha
    4. Agrupa linhas PAGAS por (empresa_pagadora + data_pagamento)
    5. Para cada grupo: Cria MovimentacaoFinanceira PAI + FILHOS
    6. Atualiza saldos das empresas
    """
    resultado = ResultadoImportacaoComissoes()
    resultado.total_linhas = len(df_comissoes)

    try:
        comissoes_todas = []
        vendedores_chassi_processados = set()  # Controle de duplicidade

        # 1. PROCESSAR TODAS AS LINHAS
        for idx, row in df_comissoes.iterrows():
            linha = idx + 2

            # Validar campos obrigatórios
            numero_pedido = converter_string(row.get('numero_pedido'))
            numero_chassi = converter_string(row.get('numero_chassi'))
            vendedor_nome = converter_string(row.get('vendedor'))
            valor_comissao = converter_decimal(row.get('valor_comissao'))
            status_pagamento = converter_string(row.get('status_pagamento')) or 'PENDENTE'

            if not numero_pedido:
                raise ValueError(f"Linha {linha}: numero_pedido é obrigatório")
            if not numero_chassi:
                raise ValueError(f"Linha {linha}: numero_chassi é obrigatório")
            if not vendedor_nome:
                raise ValueError(f"Linha {linha}: vendedor é obrigatório")
            # Permite comissões negativas (estornos/ajustes) e zero (sem comissão)
            # Removida validação: if valor_comissao <= 0

            # Validar status
            if status_pagamento not in ['PAGO', 'PENDENTE']:
                raise ValueError(f"Linha {linha}: status_pagamento deve ser 'PAGO' ou 'PENDENTE'")

            # Se PAGO, validar data e empresa
            data_pagamento = None
            empresa_pagadora = None
            if status_pagamento == 'PAGO':
                data_pagamento = converter_data(row.get('data_pagamento'))
                empresa_pagadora_nome = converter_string(row.get('empresa_pagadora'))

                if not data_pagamento:
                    raise ValueError(f"Linha {linha}: data_pagamento é obrigatória quando status='PAGO'")
                if not empresa_pagadora_nome:
                    raise ValueError(f"Linha {linha}: empresa_pagadora é obrigatória quando status='PAGO'")

                empresa_pagadora = buscar_empresa(empresa_pagadora_nome)

            # Buscar pedido
            pedido = PedidoVendaMoto.query.filter_by(numero_pedido=numero_pedido).first()
            if not pedido:
                raise ValueError(f"Linha {linha}: Pedido '{numero_pedido}' não encontrado")

            # Buscar item (para validar chassi - case insensitive)
            item = PedidoVendaMotoItem.query.filter(
                PedidoVendaMotoItem.pedido_id == pedido.id,
                func.upper(PedidoVendaMotoItem.numero_chassi) == numero_chassi.upper()
            ).first()
            if not item:
                raise ValueError(f"Linha {linha}: Chassi '{numero_chassi}' não encontrado no pedido '{numero_pedido}'")

            # Buscar vendedor
            vendedor = VendedorMoto.query.filter(
                func.upper(VendedorMoto.vendedor) == vendedor_nome.upper(),
                VendedorMoto.ativo == True
            ).first()
            if not vendedor:
                raise ValueError(f"Linha {linha}: Vendedor '{vendedor_nome}' não encontrado ou inativo")

            # Validar duplicidade no BANCO (evitar re-importação)
            comissao_existente = ComissaoVendedor.query.filter(
                ComissaoVendedor.pedido_id == pedido.id,
                func.upper(ComissaoVendedor.numero_chassi) == item.numero_chassi.upper(),
                ComissaoVendedor.vendedor_id == vendedor.id
            ).first()

            if comissao_existente:
                resultado.avisos.append(
                    f"Linha {linha}: Comissão já existe para vendedor '{vendedor_nome}' e chassi '{numero_chassi}' - Pulando"
                )
                continue

            # Validar duplicidade na MESMA EXECUÇÃO (vendedor + chassi)
            chave_duplicidade = (vendedor.id, numero_chassi)
            if chave_duplicidade in vendedores_chassi_processados:
                raise ValueError(
                    f"Linha {linha}: Duplicidade detectada - Vendedor '{vendedor_nome}' "
                    f"já possui comissão para o chassi '{numero_chassi}'"
                )
            vendedores_chassi_processados.add(chave_duplicidade)

            # Criar ComissaoVendedor (usa chassi do item encontrado para manter formato do banco)
            comissao = ComissaoVendedor(
                pedido_id=pedido.id,
                numero_chassi=item.numero_chassi,
                vendedor_id=vendedor.id,

                # Valores históricos (não calcula fixa + excedente)
                valor_comissao_fixa=Decimal('0'),
                valor_excedente=Decimal('0'),
                valor_total_comissao=valor_comissao,
                qtd_vendedores_equipe=1,
                valor_rateado=valor_comissao,

                status=status_pagamento,
                data_pagamento=data_pagamento,
                empresa_pagadora_id=empresa_pagadora.id if empresa_pagadora else None,
                # lote_pagamento_id será preenchido depois (se PAGO)

                criado_em=agora_utc_naive(),
                atualizado_em=agora_utc_naive()
            )
            db.session.add(comissao)
            db.session.flush()

            resultado.comissoes_criadas += 1
            if status_pagamento == 'PAGO':
                resultado.comissoes_pagas += 1
            else:
                resultado.comissoes_pendentes += 1

            comissoes_todas.append({
                'comissao': comissao,
                'status': status_pagamento,
                'data_pagamento': data_pagamento,
                'empresa_pagadora': empresa_pagadora,
                'linha': linha
            })

        # 2. AGRUPAR COMISSÕES PAGAS POR (empresa + data)
        comissoes_pagas = [c for c in comissoes_todas if c['status'] == 'PAGO']

        if comissoes_pagas:
            # Agrupar manualmente
            grupos = {}
            for item in comissoes_pagas:
                chave = (item['empresa_pagadora'].id, item['data_pagamento'])
                if chave not in grupos:
                    grupos[chave] = {
                        'empresa': item['empresa_pagadora'],
                        'data': item['data_pagamento'],
                        'comissoes': []
                    }
                grupos[chave]['comissoes'].append(item['comissao'])

            # 3. CRIAR LOTES (PAI + FILHOS)
            for chave, grupo_data in grupos.items():
                empresa = grupo_data['empresa']
                data_pag = grupo_data['data']
                comissoes_lote = grupo_data['comissoes']

                valor_total_lote = sum(c.valor_rateado for c in comissoes_lote)

                # ✅ VALIDAR SE JÁ EXISTE LOTE PARA ESSA EMPRESA+DATA (evitar duplicação em múltiplas importações)
                lote_existente = MovimentacaoFinanceira.query.filter(
                    MovimentacaoFinanceira.categoria == 'Lote Comissão',
                    MovimentacaoFinanceira.tipo == 'PAGAMENTO',
                    MovimentacaoFinanceira.empresa_origem_id == empresa.id,
                    MovimentacaoFinanceira.data_movimentacao == data_pag,
                    MovimentacaoFinanceira.movimentacao_origem_id == None,
                    MovimentacaoFinanceira.criado_por == usuario  # Apenas lotes desta importação
                ).first()

                if lote_existente:
                    # Usar lote existente (importação duplicada - comissões já pularam pela validação)
                    movimentacao_pai = lote_existente
                    resultado.avisos.append(
                        f"Lote para {empresa.empresa} em {data_pag} já existe (ID={lote_existente.id}) - Usando lote existente"
                    )
                else:
                    # Criar novo lote PAI
                    vendedores_set = set([c.vendedor.vendedor for c in comissoes_lote if c.vendedor])
                    vendedores_str = ', '.join(sorted(vendedores_set)) if len(vendedores_set) <= 3 else f'{len(vendedores_set)} vendedor(es)'

                    movimentacao_pai = MovimentacaoFinanceira(
                        tipo='PAGAMENTO',
                        categoria='Lote Comissão',
                        valor=valor_total_lote,
                        data_movimentacao=data_pag,

                        empresa_origem_id=empresa.id,
                        empresa_destino_id=None,
                        destino_tipo='Vendedor',
                        destino_identificacao=vendedores_str,

                        descricao=f'Importação Histórico - Lote {len(comissoes_lote)} comissão(ões)',
                        observacoes=f'Fase 5 - Importação de comissões históricas - {len(comissoes_lote)} comissão(ões)',
                        criado_por=usuario
                    )
                    db.session.add(movimentacao_pai)
                    db.session.flush()

                    resultado.movimentacoes_pai_criadas += 1

                # Criar MovimentacaoFinanceira FILHAS
                for comissao in comissoes_lote:
                    # ✅ VALIDAR SE JÁ EXISTE MOVIMENTAÇÃO PARA ESSA COMISSÃO (evitar duplicação)
                    mov_existente = MovimentacaoFinanceira.query.filter_by(
                        comissao_vendedor_id=comissao.id,
                        categoria='Comissão',
                        tipo='PAGAMENTO'
                    ).first()

                    if mov_existente:
                        # Movimentação já existe (importação duplicada)
                        # Apenas garantir que está vinculada ao lote correto
                        if mov_existente.movimentacao_origem_id != movimentacao_pai.id:
                            mov_existente.movimentacao_origem_id = movimentacao_pai.id
                    else:
                        # Criar nova movimentação filha
                        movimentacao_filha = MovimentacaoFinanceira(
                            tipo='PAGAMENTO',
                            categoria='Comissão',
                            valor=comissao.valor_rateado,
                            data_movimentacao=data_pag,

                            empresa_origem_id=empresa.id,
                            empresa_destino_id=None,
                            destino_tipo='Vendedor',
                            destino_identificacao=comissao.vendedor.vendedor if comissao.vendedor else 'Vendedor',

                            pedido_id=comissao.pedido_id,
                            numero_chassi=comissao.numero_chassi,
                            comissao_vendedor_id=comissao.id,

                            descricao=f'Comissão Histórico - Pedido {comissao.pedido.numero_pedido}',
                            movimentacao_origem_id=movimentacao_pai.id,  # ← FILHO aponta PAI
                            criado_por=usuario
                        )
                        db.session.add(movimentacao_filha)
                        resultado.movimentacoes_filhas_criadas += 1

                    # Vincular comissão ao lote
                    comissao.lote_pagamento_id = movimentacao_pai.id

                # ❌ NÃO atualiza saldo do lote PAI - apenas as comissões filhas já atualizaram
                # O lote é apenas agrupamento visual, o saldo já foi subtraído pelas comissões individuais
                # resultado.valor_total_pago += valor_total_lote  # ← Comentado para não duplicar

        db.session.commit()
        resultado.sucesso = True
        resultado.mensagem = (
            f"✅ Comissões importadas: {resultado.comissoes_criadas} total "
            f"({resultado.comissoes_pagas} pagas, {resultado.comissoes_pendentes} pendentes) | "
            f"Lotes criados: {resultado.movimentacoes_pai_criadas} | "
            f"Valor total pago: R$ {resultado.valor_total_pago}"
        )

    except Exception as e:
        db.session.rollback()
        resultado.sucesso = False
        resultado.mensagem = f"❌ Erro: {str(e)}"
        resultado.erros.append(str(e))
        resultado.erros.append(traceback.format_exc())

    return resultado


# ============================================================
# FASE 6: MONTAGENS HISTÓRICAS
# ============================================================

class ResultadoImportacaoMontagens:
    """Classe para armazenar resultado da importação de montagens"""
    def __init__(self):
        self.sucesso = False
        self.mensagem = ""
        self.total_linhas = 0
        self.itens_atualizados = 0
        self.titulos_receber_criados = 0
        self.titulos_pagar_criados = 0
        self.movimentacoes_recebimento = 0
        self.movimentacoes_pagamento = 0
        self.valor_total_recebido = Decimal('0')
        self.valor_total_pago = Decimal('0')
        self.valor_total_deduzido_venda = Decimal('0')
        self.erros = []
        self.avisos = []


def importar_montagens_historico(df_montagens, usuario='IMPORTACAO_HISTORICO'):
    """
    FASE 6: Importa montagens históricas do Excel

    Colunas esperadas:
    - numero_pedido (obrigatório)
    - numero_chassi (obrigatório)
    - fornecedor_montagem (obrigatório)
    - valor_cliente (obrigatório) - Quanto CLIENTE pagou
    - valor_custo (obrigatório) - Quanto EMPRESA pagou ao fornecedor
    - status_recebimento ('PAGO' ou 'PENDENTE')
    - data_recebimento (obrigatório se status_recebimento='PAGO')
    - empresa_recebedora (obrigatório se status_recebimento='PAGO')
    - status_pagamento ('PAGO' ou 'PENDENTE')
    - data_pagamento (obrigatório se status_pagamento='PAGO')
    - empresa_pagadora (obrigatório se status_pagamento='PAGO')

    Lógica:
    1. Atualiza PedidoVendaMotoItem (marca montagem_contratada=True)
    2. Cria TituloFinanceiro MONTAGEM (A Receber)
    3. DEDUZ valor do TituloFinanceiro VENDA (OPÇÃO A)
    4. Cria TituloAPagar MONTAGEM (A Pagar)
    5. SE status_recebimento='PAGO': Cria MovimentacaoFinanceira RECEBIMENTO
    6. SE status_pagamento='PAGO': Cria MovimentacaoFinanceira PAGAMENTO
    """
    resultado = ResultadoImportacaoMontagens()
    resultado.total_linhas = len(df_montagens)

    try:
        for idx, row in df_montagens.iterrows():
            linha = idx + 2

            # Validar campos obrigatórios
            numero_pedido = converter_string(row.get('numero_pedido'))
            numero_chassi = converter_string(row.get('numero_chassi'))
            fornecedor_montagem = converter_string(row.get('fornecedor_montagem'))
            valor_cliente = converter_decimal(row.get('valor_cliente'))
            valor_custo = converter_decimal(row.get('valor_custo'))
            status_recebimento = converter_string(row.get('status_recebimento')) or 'PENDENTE'
            status_pagamento = converter_string(row.get('status_pagamento')) or 'PENDENTE'

            if not numero_pedido:
                raise ValueError(f"Linha {linha}: numero_pedido é obrigatório")
            if not numero_chassi:
                raise ValueError(f"Linha {linha}: numero_chassi é obrigatório")
            if not fornecedor_montagem:
                raise ValueError(f"Linha {linha}: fornecedor_montagem é obrigatório")
            if valor_cliente < 0:
                raise ValueError(f"Linha {linha}: valor_cliente deve ser >= 0")
            if valor_custo < 0:
                raise ValueError(f"Linha {linha}: valor_custo deve ser >= 0")

            # Validar status
            if status_recebimento not in ['PAGO', 'PENDENTE']:
                raise ValueError(f"Linha {linha}: status_recebimento deve ser 'PAGO' ou 'PENDENTE'")
            if status_pagamento not in ['PAGO', 'PENDENTE']:
                raise ValueError(f"Linha {linha}: status_pagamento deve ser 'PAGO' ou 'PENDENTE'")

            # Buscar pedido e item
            pedido = PedidoVendaMoto.query.filter_by(numero_pedido=numero_pedido).first()
            if not pedido:
                raise ValueError(f"Linha {linha}: Pedido '{numero_pedido}' não encontrado")

            # Buscar item (para validar chassi - case insensitive)
            item = PedidoVendaMotoItem.query.filter(
                PedidoVendaMotoItem.pedido_id == pedido.id,
                func.upper(PedidoVendaMotoItem.numero_chassi) == numero_chassi.upper()
            ).first()
            if not item:
                raise ValueError(f"Linha {linha}: Chassi '{numero_chassi}' não encontrado no pedido '{numero_pedido}'")

            # 1. VERIFICAR SE JÁ EXISTE TITULO MONTAGEM (evitar duplicação)
            titulo_existente = TituloFinanceiro.query.filter(
                TituloFinanceiro.pedido_id == pedido.id,
                func.upper(TituloFinanceiro.numero_chassi) == item.numero_chassi.upper(),
                TituloFinanceiro.tipo_titulo == 'MONTAGEM'
            ).first()

            if titulo_existente:
                resultado.avisos.append(
                    f"Linha {linha}: Título MONTAGEM já existe para chassi '{numero_chassi}' - Pulando importação"
                )
                continue

            # 2. ATUALIZAR ITEM (marcar montagem)
            item.montagem_contratada = True
            item.valor_montagem = valor_cliente
            item.fornecedor_montagem = fornecedor_montagem
            resultado.itens_atualizados += 1

            # 3. CRIAR TITULO A RECEBER (Montagem - usa chassi do item para manter formato do banco)
            titulo_montagem_receber = TituloFinanceiro(
                pedido_id=pedido.id,
                numero_chassi=item.numero_chassi,
                tipo_titulo='MONTAGEM',
                ordem_pagamento=2,
                numero_parcela=1,
                total_parcelas=1,
                valor_parcela=Decimal('0'),
                prazo_dias=0,

                valor_original=valor_cliente,
                valor_saldo=Decimal('0') if status_recebimento == 'PAGO' else valor_cliente,
                valor_pago_total=valor_cliente if status_recebimento == 'PAGO' else Decimal('0'),

                data_emissao=pedido.data_pedido,
                data_vencimento=pedido.data_expedicao if pedido.data_expedicao else None,
                data_ultimo_pagamento=converter_data(row.get('data_recebimento')) if status_recebimento == 'PAGO' else None,

                status='PAGO' if status_recebimento == 'PAGO' else 'ABERTO',
                criado_por=usuario
            )
            db.session.add(titulo_montagem_receber)
            db.session.flush()
            resultado.titulos_receber_criados += 1

            # 3. DEDUZIR DO TITULO VENDA (OPÇÃO A - busca case insensitive)
            titulo_venda = TituloFinanceiro.query.filter(
                TituloFinanceiro.pedido_id == pedido.id,
                func.upper(TituloFinanceiro.numero_chassi) == numero_chassi.upper(),
                TituloFinanceiro.tipo_titulo == 'VENDA'
            ).first()

            if titulo_venda:
                titulo_venda.valor_original -= valor_cliente
                titulo_venda.valor_saldo -= valor_cliente
                resultado.valor_total_deduzido_venda += valor_cliente
            else:
                resultado.avisos.append(
                    f"Linha {linha}: Título VENDA não encontrado para chassi '{numero_chassi}'. "
                    f"Dedução não aplicada."
                )

            # 4. CRIAR TITULO A PAGAR (Montagem - usa chassi do item)
            titulo_montagem_pagar = TituloAPagar(
                tipo='MONTAGEM',
                titulo_financeiro_id=titulo_montagem_receber.id,
                pedido_id=pedido.id,
                numero_chassi=item.numero_chassi,

                empresa_destino_id=None,
                fornecedor_montagem=fornecedor_montagem,

                valor_original=valor_custo,
                valor_pago=valor_custo if status_pagamento == 'PAGO' else Decimal('0'),
                valor_saldo=Decimal('0') if status_pagamento == 'PAGO' else valor_custo,

                data_criacao=pedido.data_pedido,
                data_liberacao=pedido.data_pedido,  # Já libera (histórico)
                data_pagamento=converter_data(row.get('data_pagamento')) if status_pagamento == 'PAGO' else None,

                status='PAGO' if status_pagamento == 'PAGO' else 'ABERTO',
                criado_por=usuario
            )
            db.session.add(titulo_montagem_pagar)
            db.session.flush()
            resultado.titulos_pagar_criados += 1

            # 5. PROCESSAR RECEBIMENTO (se PAGO)
            if status_recebimento == 'PAGO':
                data_recebimento = converter_data(row.get('data_recebimento'))
                empresa_recebedora_nome = converter_string(row.get('empresa_recebedora'))

                if not data_recebimento:
                    raise ValueError(f"Linha {linha}: data_recebimento é obrigatória quando status_recebimento='PAGO'")
                if not empresa_recebedora_nome:
                    raise ValueError(f"Linha {linha}: empresa_recebedora é obrigatória quando status_recebimento='PAGO'")

                empresa_receb = buscar_empresa(empresa_recebedora_nome)

                # Criar MovimentacaoFinanceira RECEBIMENTO (sem PAI para histórico individual)
                mov_receb = MovimentacaoFinanceira(
                    tipo='RECEBIMENTO',
                    categoria='Título Montagem',
                    valor=valor_cliente,
                    data_movimentacao=data_recebimento,

                    empresa_origem_id=None,
                    origem_tipo='Cliente',
                    origem_identificacao=pedido.cliente.cliente if pedido.cliente else 'Cliente',

                    empresa_destino_id=empresa_receb.id,

                    pedido_id=pedido.id,
                    numero_chassi=item.numero_chassi,
                    titulo_financeiro_id=titulo_montagem_receber.id,

                    descricao=f'Recebimento Histórico Montagem - Pedido {pedido.numero_pedido}',
                    observacoes='Importação Histórica - Fase 6',
                    criado_por=usuario
                )
                db.session.add(mov_receb)
                resultado.movimentacoes_recebimento += 1

                titulo_montagem_receber.empresa_recebedora_id = empresa_receb.id

                # Atualizar saldo
                atualizar_saldo(empresa_receb.id, valor_cliente, 'SOMAR')
                resultado.valor_total_recebido += valor_cliente

            # 6. PROCESSAR PAGAMENTO (se PAGO)
            if status_pagamento == 'PAGO':
                data_pagamento = converter_data(row.get('data_pagamento'))
                empresa_pagadora_nome = converter_string(row.get('empresa_pagadora'))

                if not data_pagamento:
                    raise ValueError(f"Linha {linha}: data_pagamento é obrigatória quando status_pagamento='PAGO'")
                if not empresa_pagadora_nome:
                    raise ValueError(f"Linha {linha}: empresa_pagadora é obrigatória quando status_pagamento='PAGO'")

                empresa_pag = buscar_empresa(empresa_pagadora_nome)

                # Criar MovimentacaoFinanceira PAGAMENTO (sem PAI)
                mov_pag = MovimentacaoFinanceira(
                    tipo='PAGAMENTO',
                    categoria='Montagem',
                    valor=valor_custo,
                    data_movimentacao=data_pagamento,

                    empresa_origem_id=empresa_pag.id,

                    empresa_destino_id=None,
                    destino_tipo='Equipe Montagem',
                    destino_identificacao=fornecedor_montagem,

                    pedido_id=pedido.id,
                    numero_chassi=item.numero_chassi,

                    descricao=f'Pagamento Histórico Montagem - Pedido {pedido.numero_pedido}',
                    observacoes='Importação Histórica - Fase 6',
                    criado_por=usuario
                )
                db.session.add(mov_pag)
                resultado.movimentacoes_pagamento += 1

                # Atualizar item
                item.montagem_paga = True
                item.data_pagamento_montagem = data_pagamento
                item.empresa_pagadora_montagem_id = empresa_pag.id
                # lote_pagamento_montagem_id fica NULL (sem lote para histórico individual)

                # Atualizar saldo
                atualizar_saldo(empresa_pag.id, valor_custo, 'SUBTRAIR')
                resultado.valor_total_pago += valor_custo

        db.session.commit()
        resultado.sucesso = True
        resultado.mensagem = (
            f"✅ Montagens importadas: {resultado.itens_atualizados} itens | "
            f"Títulos: {resultado.titulos_receber_criados} A Receber, {resultado.titulos_pagar_criados} A Pagar | "
            f"Movimentações: {resultado.movimentacoes_recebimento} recebimentos, {resultado.movimentacoes_pagamento} pagamentos | "
            f"Deduzido de VENDA: R$ {resultado.valor_total_deduzido_venda}"
        )

    except Exception as e:
        db.session.rollback()
        resultado.sucesso = False
        resultado.mensagem = f"❌ Erro: {str(e)}"
        resultado.erros.append(str(e))
        resultado.erros.append(traceback.format_exc())

    return resultado


# ============================================================
# FASE 7: MOVIMENTAÇÕES HISTÓRICAS
# ============================================================

class ResultadoImportacaoMovimentacoes:
    """Classe para armazenar resultado da importação de movimentações"""
    def __init__(self):
        self.sucesso = False
        self.mensagem = ""
        self.total_linhas = 0
        self.titulos_receber_criados = 0
        self.titulos_pagar_criados = 0
        self.movimentacoes_recebimento = 0
        self.movimentacoes_pagamento = 0
        self.valor_total_recebido = Decimal('0')
        self.valor_total_pago = Decimal('0')
        self.valor_total_deduzido_venda = Decimal('0')
        self.erros = []
        self.avisos = []


def importar_movimentacoes_historico(df_movimentacoes, usuario='IMPORTACAO_HISTORICO'):
    """
    FASE 7: Importa movimentações históricas do Excel

    Colunas esperadas:
    - numero_pedido (obrigatório)
    - numero_chassi (obrigatório)
    - valor_cliente (obrigatório) - Quanto CLIENTE pagou
    - valor_custo (obrigatório) - Quanto EMPRESA pagou MargemSogima
    - status_recebimento ('PAGO' ou 'PENDENTE')
    - data_recebimento (obrigatório se status_recebimento='PAGO')
    - empresa_recebedora (obrigatório se status_recebimento='PAGO')
    - status_pagamento ('PAGO' ou 'PENDENTE')
    - data_pagamento (obrigatório se status_pagamento='PAGO')
    - empresa_pagadora (obrigatório se status_pagamento='PAGO')

    Lógica: Idêntica à Fase 6, mudando apenas tipo_titulo='MOVIMENTACAO'
    """
    resultado = ResultadoImportacaoMovimentacoes()
    resultado.total_linhas = len(df_movimentacoes)

    try:
        # Garantir que MargemSogima existe
        margem_sogima = garantir_margem_sogima()

        for idx, row in df_movimentacoes.iterrows():
            linha = idx + 2

            # Validar campos obrigatórios
            numero_pedido = converter_string(row.get('numero_pedido'))
            numero_chassi = converter_string(row.get('numero_chassi'))
            valor_cliente = converter_decimal(row.get('valor_cliente'))
            valor_custo = converter_decimal(row.get('valor_custo'))
            status_recebimento = converter_string(row.get('status_recebimento')) or 'PENDENTE'
            status_pagamento = converter_string(row.get('status_pagamento')) or 'PENDENTE'

            if not numero_pedido:
                raise ValueError(f"Linha {linha}: numero_pedido é obrigatório")
            if not numero_chassi:
                raise ValueError(f"Linha {linha}: numero_chassi é obrigatório")
            if valor_cliente < 0:
                raise ValueError(f"Linha {linha}: valor_cliente deve ser >= 0")
            if valor_custo < 0:
                raise ValueError(f"Linha {linha}: valor_custo deve ser >= 0")

            # Validar status
            if status_recebimento not in ['PAGO', 'PENDENTE']:
                raise ValueError(f"Linha {linha}: status_recebimento deve ser 'PAGO' ou 'PENDENTE'")
            if status_pagamento not in ['PAGO', 'PENDENTE']:
                raise ValueError(f"Linha {linha}: status_pagamento deve ser 'PAGO' ou 'PENDENTE'")

            # Buscar pedido e item
            pedido = PedidoVendaMoto.query.filter_by(numero_pedido=numero_pedido).first()
            if not pedido:
                raise ValueError(f"Linha {linha}: Pedido '{numero_pedido}' não encontrado")

            # Buscar item (para validar chassi - case insensitive)
            item = PedidoVendaMotoItem.query.filter(
                PedidoVendaMotoItem.pedido_id == pedido.id,
                func.upper(PedidoVendaMotoItem.numero_chassi) == numero_chassi.upper()
            ).first()
            if not item:
                raise ValueError(f"Linha {linha}: Chassi '{numero_chassi}' não encontrado no pedido '{numero_pedido}'")

            # 1. VERIFICAR SE JÁ EXISTE TITULO MOVIMENTACAO (evitar duplicação)
            titulo_existente = TituloFinanceiro.query.filter(
                TituloFinanceiro.pedido_id == pedido.id,
                func.upper(TituloFinanceiro.numero_chassi) == item.numero_chassi.upper(),
                TituloFinanceiro.tipo_titulo == 'MOVIMENTACAO'
            ).first()

            if titulo_existente:
                resultado.avisos.append(
                    f"Linha {linha}: Título MOVIMENTACAO já existe para chassi '{numero_chassi}' - Pulando importação"
                )
                continue

            # 2. CRIAR TITULO A RECEBER (Movimentação - usa chassi do item)
            titulo_movimentacao_receber = TituloFinanceiro(
                pedido_id=pedido.id,
                numero_chassi=item.numero_chassi,
                tipo_titulo='MOVIMENTACAO',
                ordem_pagamento=1,
                numero_parcela=1,
                total_parcelas=1,
                valor_parcela=Decimal('0'),
                prazo_dias=0,

                valor_original=valor_cliente,
                valor_saldo=Decimal('0') if status_recebimento == 'PAGO' else valor_cliente,
                valor_pago_total=valor_cliente if status_recebimento == 'PAGO' else Decimal('0'),

                data_emissao=pedido.data_pedido,
                data_vencimento=pedido.data_expedicao if pedido.data_expedicao else None,
                data_ultimo_pagamento=converter_data(row.get('data_recebimento')) if status_recebimento == 'PAGO' else None,

                status='PAGO' if status_recebimento == 'PAGO' else 'ABERTO',
                criado_por=usuario
            )
            db.session.add(titulo_movimentacao_receber)
            db.session.flush()
            resultado.titulos_receber_criados += 1

            # 2. DEDUZIR DO TITULO VENDA (OPÇÃO A - busca case insensitive)
            titulo_venda = TituloFinanceiro.query.filter(
                TituloFinanceiro.pedido_id == pedido.id,
                func.upper(TituloFinanceiro.numero_chassi) == numero_chassi.upper(),
                TituloFinanceiro.tipo_titulo == 'VENDA'
            ).first()

            if titulo_venda:
                titulo_venda.valor_original -= valor_cliente
                titulo_venda.valor_saldo -= valor_cliente
                resultado.valor_total_deduzido_venda += valor_cliente
            else:
                resultado.avisos.append(
                    f"Linha {linha}: Título VENDA não encontrado para chassi '{numero_chassi}'. "
                    f"Dedução não aplicada."
                )

            # 3. CRIAR TITULO A PAGAR (Movimentação → MargemSogima - usa chassi do item)
            titulo_movimentacao_pagar = TituloAPagar(
                tipo='MOVIMENTACAO',
                titulo_financeiro_id=titulo_movimentacao_receber.id,
                pedido_id=pedido.id,
                numero_chassi=item.numero_chassi,

                empresa_destino_id=margem_sogima.id,
                fornecedor_montagem=None,

                valor_original=valor_custo,
                valor_pago=valor_custo if status_pagamento == 'PAGO' else Decimal('0'),
                valor_saldo=Decimal('0') if status_pagamento == 'PAGO' else valor_custo,

                data_criacao=pedido.data_pedido,
                data_liberacao=pedido.data_pedido,  # Já libera (histórico)
                data_pagamento=converter_data(row.get('data_pagamento')) if status_pagamento == 'PAGO' else None,

                status='PAGO' if status_pagamento == 'PAGO' else 'ABERTO',
                criado_por=usuario
            )
            db.session.add(titulo_movimentacao_pagar)
            db.session.flush()
            resultado.titulos_pagar_criados += 1

            # 4. PROCESSAR RECEBIMENTO (se PAGO)
            if status_recebimento == 'PAGO':
                data_recebimento = converter_data(row.get('data_recebimento'))
                empresa_recebedora_nome = converter_string(row.get('empresa_recebedora'))

                if not data_recebimento:
                    raise ValueError(f"Linha {linha}: data_recebimento é obrigatória quando status_recebimento='PAGO'")
                if not empresa_recebedora_nome:
                    raise ValueError(f"Linha {linha}: empresa_recebedora é obrigatória quando status_recebimento='PAGO'")

                empresa_receb = buscar_empresa(empresa_recebedora_nome)

                # Criar MovimentacaoFinanceira RECEBIMENTO
                mov_receb = MovimentacaoFinanceira(
                    tipo='RECEBIMENTO',
                    categoria='Título Movimentação',
                    valor=valor_cliente,
                    data_movimentacao=data_recebimento,

                    empresa_origem_id=None,
                    origem_tipo='Cliente',
                    origem_identificacao=pedido.cliente.cliente if pedido.cliente else 'Cliente',

                    empresa_destino_id=empresa_receb.id,

                    pedido_id=pedido.id,
                    numero_chassi=item.numero_chassi,
                    titulo_financeiro_id=titulo_movimentacao_receber.id,

                    descricao=f'Recebimento Histórico Movimentação - Pedido {pedido.numero_pedido}',
                    observacoes='Importação Histórica - Fase 7',
                    criado_por=usuario
                )
                db.session.add(mov_receb)
                resultado.movimentacoes_recebimento += 1

                titulo_movimentacao_receber.empresa_recebedora_id = empresa_receb.id

                # Atualizar saldo
                atualizar_saldo(empresa_receb.id, valor_cliente, 'SOMAR')
                resultado.valor_total_recebido += valor_cliente

            # 5. PROCESSAR PAGAMENTO (se PAGO)
            if status_pagamento == 'PAGO':
                data_pagamento = converter_data(row.get('data_pagamento'))
                empresa_pagadora_nome = converter_string(row.get('empresa_pagadora'))

                if not data_pagamento:
                    raise ValueError(f"Linha {linha}: data_pagamento é obrigatória quando status_pagamento='PAGO'")
                if not empresa_pagadora_nome:
                    raise ValueError(f"Linha {linha}: empresa_pagadora é obrigatória quando status_pagamento='PAGO'")

                empresa_pag = buscar_empresa(empresa_pagadora_nome)

                # Criar MovimentacaoFinanceira PAGAMENTO
                mov_pag = MovimentacaoFinanceira(
                    tipo='PAGAMENTO',
                    categoria='Movimentação',
                    valor=valor_custo,
                    data_movimentacao=data_pagamento,

                    empresa_origem_id=empresa_pag.id,
                    empresa_destino_id=margem_sogima.id,

                    pedido_id=pedido.id,
                    numero_chassi=item.numero_chassi,

                    descricao=f'Pagamento Histórico Movimentação - Pedido {pedido.numero_pedido}',
                    observacoes='Importação Histórica - Fase 7',
                    criado_por=usuario
                )
                db.session.add(mov_pag)
                resultado.movimentacoes_pagamento += 1

                # Atualizar saldos (origem e destino)
                atualizar_saldo(empresa_pag.id, valor_custo, 'SUBTRAIR')
                atualizar_saldo(margem_sogima.id, valor_custo, 'SOMAR')
                resultado.valor_total_pago += valor_custo

        db.session.commit()
        resultado.sucesso = True
        resultado.mensagem = (
            f"✅ Movimentações importadas: {resultado.total_linhas} linhas | "
            f"Títulos: {resultado.titulos_receber_criados} A Receber, {resultado.titulos_pagar_criados} A Pagar | "
            f"Movimentações: {resultado.movimentacoes_recebimento} recebimentos, {resultado.movimentacoes_pagamento} pagamentos | "
            f"Deduzido de VENDA: R$ {resultado.valor_total_deduzido_venda}"
        )

    except Exception as e:
        db.session.rollback()
        resultado.sucesso = False
        resultado.mensagem = f"❌ Erro: {str(e)}"
        resultado.erros.append(str(e))
        resultado.erros.append(traceback.format_exc())

    return resultado


# ============================================================
# GERADOR DE TEMPLATE EXCEL
# ============================================================

def gerar_template_historico_excel():
    """
    Gera arquivo Excel template para importação histórica
    Retorna BytesIO para download via Flask

    Returns:
        BytesIO - Arquivo Excel em memória
    """
    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # ========================================
        # ABA 1: COMISSÕES
        # ========================================
        df_comissoes = pd.DataFrame(columns=[
            'numero_pedido',
            'numero_chassi',
            'valor_comissao',
            'status_pagamento',
            'data_pagamento',
            'empresa_pagadora'
        ])

        # Linha de exemplo
        df_comissoes.loc[0] = [
            'MC-001',           # numero_pedido
            'ABC123XYZ456',     # numero_chassi
            300.00,             # valor_comissao
            'PAGO',             # status_pagamento (PAGO ou PENDENTE)
            '2024-01-15',       # data_pagamento (obrigatório se PAGO)
            'Sogima LTDA'       # empresa_pagadora (obrigatório se PAGO)
        ]

        df_comissoes.loc[1] = [
            'MC-002',
            'DEF789GHI012',
            250.00,
            'PENDENTE',
            None,               # data_pagamento (NULL se PENDENTE)
            None                # empresa_pagadora (NULL se PENDENTE)
        ]

        df_comissoes.to_excel(writer, sheet_name='Comissoes', index=False)

        # ========================================
        # ABA 2: MONTAGENS
        # ========================================
        df_montagens = pd.DataFrame(columns=[
            'numero_pedido',
            'numero_chassi',
            'fornecedor_montagem',
            'valor_cliente',
            'valor_custo',
            'status_recebimento',
            'data_recebimento',
            'empresa_recebedora',
            'status_pagamento',
            'data_pagamento',
            'empresa_pagadora'
        ])

        # Linha de exemplo
        df_montagens.loc[0] = [
            'MC-001',           # numero_pedido
            'ABC123XYZ456',     # numero_chassi
            'Equipe Montagem X',  # fornecedor_montagem
            100.00,             # valor_cliente (quanto cliente pagou)
            80.00,              # valor_custo (quanto empresa pagou)
            'PAGO',             # status_recebimento (PAGO ou PENDENTE)
            '2024-01-10',       # data_recebimento (obrigatório se status_recebimento=PAGO)
            'Sogima LTDA',      # empresa_recebedora (obrigatório se status_recebimento=PAGO)
            'PAGO',             # status_pagamento (PAGO ou PENDENTE)
            '2024-01-15',       # data_pagamento (obrigatório se status_pagamento=PAGO)
            'Sogima LTDA'       # empresa_pagadora (obrigatório se status_pagamento=PAGO)
        ]

        df_montagens.loc[1] = [
            'MC-002',
            'DEF789GHI012',
            'Equipe Montagem Y',
            150.00,
            120.00,
            'PAGO',
            '2024-01-12',
            'Sogima LTDA',
            'PENDENTE',         # Recebeu do cliente mas ainda não pagou fornecedor
            None,
            None
        ]

        df_montagens.to_excel(writer, sheet_name='Montagens', index=False)

        # ========================================
        # ABA 3: MOVIMENTAÇÕES
        # ========================================
        df_movimentacoes = pd.DataFrame(columns=[
            'numero_pedido',
            'numero_chassi',
            'valor_cliente',
            'valor_custo',
            'status_recebimento',
            'data_recebimento',
            'empresa_recebedora',
            'status_pagamento',
            'data_pagamento',
            'empresa_pagadora'
        ])

        # Linha de exemplo
        df_movimentacoes.loc[0] = [
            'MC-001',           # numero_pedido
            'ABC123XYZ456',     # numero_chassi
            50.00,              # valor_cliente (quanto cliente pagou)
            50.00,              # valor_custo (quanto empresa pagou MargemSogima)
            'PAGO',             # status_recebimento (PAGO ou PENDENTE)
            '2024-01-10',       # data_recebimento (obrigatório se status_recebimento=PAGO)
            'Sogima LTDA',      # empresa_recebedora (obrigatório se status_recebimento=PAGO)
            'PAGO',             # status_pagamento (PAGO ou PENDENTE)
            '2024-01-15',       # data_pagamento (obrigatório se status_pagamento=PAGO)
            'Sogima LTDA'       # empresa_pagadora (obrigatório se status_pagamento=PAGO)
        ]

        df_movimentacoes.loc[1] = [
            'MC-002',
            'DEF789GHI012',
            0.00,               # Cliente não pagou movimentação (empresa absorveu custo)
            50.00,              # Mas empresa pagou MargemSogima
            'PAGO',             # Título R$ 0 fica PAGO automaticamente
            '2024-01-12',
            'Sogima LTDA',
            'PAGO',
            '2024-01-15',
            'Sogima LTDA'
        ]

        df_movimentacoes.to_excel(writer, sheet_name='Movimentacoes', index=False)

        # ========================================
        # ABA 4: INSTRUÇÕES
        # ========================================
        df_instrucoes = pd.DataFrame({
            'INSTRUÇÕES DE USO': [
                '',
                '1. PREPARAÇÃO:',
                '   - Certifique-se de que os pedidos já foram importados (Fase 4)',
                '   - Certifique-se de que as empresas existem no sistema',
                '',
                '2. PREENCHIMENTO:',
                '   - numero_pedido: DEVE existir no sistema',
                '   - numero_chassi: DEVE existir no pedido',
                '   - Datas: Formato DD/MM/YYYY ou YYYY-MM-DD',
                '   - Valores: Números com 2 casas decimais (use . ou ,)',
                '   - status_pagamento/status_recebimento: Apenas "PAGO" ou "PENDENTE"',
                '',
                '3. CAMPOS CONDICIONAIS:',
                '   - Se status = "PAGO": data e empresa são OBRIGATÓRIOS',
                '   - Se status = "PENDENTE": data e empresa devem ficar VAZIOS (NULL)',
                '',
                '4. IMPORTANTE:',
                '   - FASE 6 (Montagens): valor_cliente pode ser R$ 0 (sem montagem)',
                '   - FASE 7 (Movimentações): valor_cliente pode ser R$ 0 (empresa absorveu)',
                '   - Valor deduzido de VENDA = valor_cliente (montagem + movimentação)',
                '   - Em caso de ERRO em qualquer fase: ROLLBACK TOTAL',
                '',
                '5. ORDEM DE EXECUÇÃO:',
                '   - O sistema executa: Fase 5 → Fase 6 → Fase 7',
                '   - Se qualquer fase falhar, NADA é importado',
                '',
                '6. VALIDAÇÕES:',
                '   - Após importação, valide:',
                '     * Saldos de empresas estão corretos',
                '     * Títulos VENDA foram deduzidos corretamente',
                '     * MovimentacaoFinanceira PAI/FILHOS criadas para lotes',
                '',
                '7. DEDUÇÕES:',
                '   - Título VENDA original = R$ 10.000',
                '   - Montagem cliente paga = R$ 100',
                '   - Movimentação cliente paga = R$ 50',
                '   - Título VENDA final = R$ 9.850 (10.000 - 100 - 50)',
                ''
            ]
        })

        df_instrucoes.to_excel(writer, sheet_name='LEIA_ME', index=False)

    output.seek(0)
    return output
