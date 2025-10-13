"""
Service para gestão de devoluções de motos avariadas
Sistema MotoCHEFE
"""
from app import db
from sqlalchemy import text
from app.motochefe.models import Moto
from decimal import Decimal
from datetime import date


def gerar_proximo_documento_devolucao():
    """
    Gera próximo número de documento de devolução no formato "DEV-###"
    Busca o maior número existente e adiciona 1

    Returns:
        str: Próximo número (ex: "DEV-001", "DEV-002"...)
    """
    # Buscar maior número com máscara "DEV-"
    resultado = db.session.execute(text("""
        SELECT MAX(
            CAST(
                SUBSTRING(documento_devolucao FROM 5) AS INTEGER
            )
        )
        FROM moto
        WHERE documento_devolucao LIKE 'DEV-%'
        AND SUBSTRING(documento_devolucao FROM 5) ~ '^[0-9]+$'
    """)).scalar()

    # Se não encontrou nenhum, começar em 0 (próximo será 1)
    ultimo_numero = resultado if resultado else 0

    # Próximo número com zero padding (3 dígitos)
    proximo = ultimo_numero + 1

    return f"DEV-{proximo:03d}"


def listar_devolucoes_abertas():
    """
    Lista documentos de devolução que ainda têm motos no status AVARIADO
    (ou seja, devoluções que ainda podem receber mais motos)

    Returns:
        list: Lista de dict com {documento_devolucao, qtd_motos, motos}
    """
    # Buscar devoluções existentes com motos DEVOLVIDO ou AVARIADO
    devolucoes = db.session.execute(text("""
        SELECT
            documento_devolucao,
            COUNT(*) as qtd_motos,
            STRING_AGG(numero_chassi, ', ' ORDER BY numero_chassi) as motos
        FROM moto
        WHERE documento_devolucao IS NOT NULL
        AND status IN ('DEVOLVIDO', 'AVARIADO')
        AND ativo = true
        GROUP BY documento_devolucao
        ORDER BY documento_devolucao DESC
    """)).fetchall()

    return [{
        'documento_devolucao': d[0],
        'qtd_motos': d[1],
        'motos': d[2]
    } for d in devolucoes]


def obter_motos_por_documento_devolucao(documento_devolucao):
    """
    Busca todas as motos de um documento de devolução

    Args:
        documento_devolucao (str): Número do documento (ex: "DEV-001")

    Returns:
        list: Lista de objetos Moto
    """
    return Moto.query.filter_by(
        documento_devolucao=documento_devolucao,
        ativo=True
    ).order_by(Moto.numero_chassi).all()


def devolver_moto_individual(chassi, documento_devolucao, observacao_adicional=None, usuario=None):
    """
    Devolve uma moto individual ao fornecedor

    Args:
        chassi (str): Número do chassi
        documento_devolucao (str): Número do documento (DEV-###)
        observacao_adicional (str, optional): Observação adicional
        usuario (str, optional): Nome do usuário que fez a devolução

    Raises:
        Exception: Se moto não estiver avariada ou não existir
    """
    moto = Moto.query.get(chassi)

    if not moto:
        raise Exception(f'Moto {chassi} não encontrada')

    if moto.status != 'AVARIADO':
        raise Exception(f'Moto {chassi} não está avariada (status atual: {moto.status})')

    # Atualizar observação se fornecida
    if observacao_adicional:
        if moto.observacao:
            moto.observacao += f"\n\nDevolução ({documento_devolucao}): {observacao_adicional}"
        else:
            moto.observacao = f"Devolução ({documento_devolucao}): {observacao_adicional}"

    # Atualizar status e documento
    moto.status = 'DEVOLVIDO'
    moto.documento_devolucao = documento_devolucao
    moto.atualizado_por = usuario or 'Sistema'


def devolver_motos_lote(chassis_list, documento_devolucao, observacao_adicional=None, usuario=None):
    """
    Devolve múltiplas motos em lote para o mesmo documento de devolução

    Args:
        chassis_list (list): Lista de números de chassi
        documento_devolucao (str): Número do documento (DEV-###)
        observacao_adicional (str, optional): Observação adicional
        usuario (str, optional): Nome do usuário que fez a devolução

    Returns:
        dict: {sucesso: int, erros: list}
    """
    sucesso = 0
    erros = []

    for chassi in chassis_list:
        try:
            devolver_moto_individual(chassi, documento_devolucao, observacao_adicional, usuario)
            sucesso += 1
        except Exception as e:
            erros.append(f'{chassi}: {str(e)}')

    # Commit apenas se houver pelo menos 1 sucesso
    if sucesso > 0:
        db.session.commit()

    return {
        'sucesso': sucesso,
        'erros': erros
    }


def processar_recebimento_devolucao(documento_devolucao, usuario=None):
    """
    Processa recebimento automático de devolução
    - Cria/busca EmpresaVendaMoto "DevolucaoMoto"
    - Gera TituloFinanceiro a receber (por moto)
    - Efetua recebimento automaticamente
    - Se >1 moto: usa lote (PAI + FILHOS)

    Args:
        documento_devolucao: str - Número do documento (ex: "DEV-001")
        usuario: str

    Returns:
        dict com resultado
    """
    from app.motochefe.models.cadastro import EmpresaVendaMoto
    from app.motochefe.models.operacional import CustosOperacionais
    from app.motochefe.models.financeiro import TituloFinanceiro, MovimentacaoFinanceira
    from app.motochefe.services.empresa_service import atualizar_saldo

    # 1. Garantir empresa DevolucaoMoto existe
    empresa_devolucao = EmpresaVendaMoto.query.filter_by(
        empresa='DevolucaoMoto'
    ).first()

    if not empresa_devolucao:
        empresa_devolucao = EmpresaVendaMoto(
            cnpj_empresa=None,
            empresa='DevolucaoMoto',
            tipo_conta='OPERACIONAL',
            saldo=Decimal('0'),
            baixa_compra_auto=False,
            ativo=True,
            criado_por=usuario or 'SISTEMA'
        )
        db.session.add(empresa_devolucao)
        db.session.flush()

    # 2. Buscar motos do documento
    motos = obter_motos_por_documento_devolucao(documento_devolucao)

    if not motos:
        raise Exception(f'Nenhuma moto encontrada para documento {documento_devolucao}')

    # 3. Buscar custo de devolução
    custos = CustosOperacionais.get_custos_vigentes()
    if not custos or custos.custo_movimentacao_devolucao <= 0:
        raise Exception('Custo de movimentação de devolução não configurado em CustosOperacionais')

    custo_por_moto = custos.custo_movimentacao_devolucao

    # 4. Criar títulos financeiros (um por moto)
    titulos_criados = []
    valor_total = Decimal('0')

    for moto in motos:
        titulo = TituloFinanceiro(
            pedido_id=None,  # Sem pedido
            numero_chassi=moto.numero_chassi,
            tipo_titulo='DEVOLUCAO',
            ordem_pagamento=99,  # Ordem alta (não segue FIFO)
            numero_parcela=1,
            total_parcelas=1,
            valor_parcela=Decimal('0'),
            prazo_dias=0,
            valor_original=custo_por_moto,
            valor_saldo=Decimal('0'),  # Já será quitado
            valor_pago_total=custo_por_moto,
            data_emissao=date.today(),
            empresa_recebedora_id=empresa_devolucao.id,
            data_ultimo_pagamento=date.today(),
            status='PAGO',  # Já criado como PAGO
            criado_por=usuario or 'SISTEMA'
        )
        db.session.add(titulo)
        db.session.flush()
        titulos_criados.append(titulo)
        valor_total += custo_por_moto

    # 5. Criar movimentações financeiras
    if len(motos) == 1:
        # INDIVIDUAL: Uma movimentação
        moto = motos[0]
        titulo = titulos_criados[0]

        movimentacao = MovimentacaoFinanceira(
            tipo='RECEBIMENTO',
            categoria='Devolução Moto',
            valor=custo_por_moto,
            data_movimentacao=date.today(),
            empresa_origem_id=None,
            origem_tipo='Fabricante',
            origem_identificacao=moto.fornecedor,
            empresa_destino_id=empresa_devolucao.id,
            numero_chassi=moto.numero_chassi,
            titulo_financeiro_id=titulo.id,
            numero_documento=documento_devolucao,
            descricao=f'Recebimento Devolução Moto {moto.numero_chassi} - {moto.fornecedor}',
            observacoes=f'Documento: {documento_devolucao}',
            criado_por=usuario or 'SISTEMA'
        )
        db.session.add(movimentacao)
        movimentacoes_criadas = [movimentacao]

    else:
        # LOTE: MovimentacaoFinanceira PAI + FILHOS
        # Agrupar fornecedores
        fornecedores_set = set(m.fornecedor for m in motos if m.fornecedor)
        fornecedores_str = ', '.join(sorted(fornecedores_set)) if fornecedores_set else 'Fornecedor'

        # Criar PAI
        movimentacao_pai = MovimentacaoFinanceira(
            tipo='RECEBIMENTO',
            categoria='Lote Devolução',
            valor=valor_total,
            data_movimentacao=date.today(),
            empresa_origem_id=None,
            origem_tipo='Fabricante',
            origem_identificacao=fornecedores_str if len(fornecedores_set) <= 3 else f'{len(fornecedores_set)} fabricante(s)',
            empresa_destino_id=empresa_devolucao.id,
            numero_documento=documento_devolucao,
            descricao=f'Recebimento Lote Devolução {len(motos)} moto(s) - Doc {documento_devolucao}',
            observacoes=f'Lote com {len(motos)} moto(s): {", ".join([m.numero_chassi for m in motos])}',
            criado_por=usuario or 'SISTEMA'
        )
        db.session.add(movimentacao_pai)
        db.session.flush()

        # Criar FILHOS
        movimentacoes_criadas = []
        for i, moto in enumerate(motos):
            titulo = titulos_criados[i]

            movimentacao_filha = MovimentacaoFinanceira(
                tipo='RECEBIMENTO',
                categoria='Devolução Moto',
                valor=custo_por_moto,
                data_movimentacao=date.today(),
                empresa_origem_id=None,
                origem_tipo='Fabricante',
                origem_identificacao=moto.fornecedor,
                empresa_destino_id=empresa_devolucao.id,
                numero_chassi=moto.numero_chassi,
                titulo_financeiro_id=titulo.id,
                numero_documento=documento_devolucao,
                descricao=f'Devolução Moto {moto.numero_chassi} - {moto.fornecedor}',
                movimentacao_origem_id=movimentacao_pai.id,
                criado_por=usuario or 'SISTEMA'
            )
            db.session.add(movimentacao_filha)
            movimentacoes_criadas.append(movimentacao_filha)

    # 6. Atualizar saldo da empresa DevolucaoMoto
    atualizar_saldo(empresa_devolucao.id, valor_total, 'SOMAR')

    db.session.flush()

    return {
        'empresa_devolucao': empresa_devolucao,
        'titulos_criados': titulos_criados,
        'movimentacoes_criadas': movimentacoes_criadas,
        'valor_total': valor_total,
        'quantidade_motos': len(motos)
    }
