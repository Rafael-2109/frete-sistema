"""
Service para Empresas - Sistema MotoCHEFE
Gerencia empresas recebedoras/pagadoras e MargemSogima
"""
from app import db
from app.motochefe.models.cadastro import EmpresaVendaMoto


def garantir_margem_sogima():
    """
    Garante que empresa MargemSogima existe
    Executado na inicialização ou quando necessário
    Retorna a empresa MargemSogima
    """
    margem = EmpresaVendaMoto.query.filter_by(
        tipo_conta='MARGEM_SOGIMA'
    ).first()

    if not margem:
        # Detectar tipo de banco para compatibilidade
        # PostgreSQL: usar NULL
        # SQLite: usar '' (string vazia) porque não suporta ALTER COLUMN DROP NOT NULL
        from sqlalchemy import inspect
        engine_name = db.engine.name

        cnpj_value = None if engine_name == 'postgresql' else ''

        margem = EmpresaVendaMoto(
            cnpj_empresa=cnpj_value,  # NULL (PostgreSQL) ou '' (SQLite)
            empresa='MargemSogima',
            tipo_conta='MARGEM_SOGIMA',
            baixa_compra_auto=False,
            saldo=0,
            ativo=True,
            criado_por='SISTEMA'
        )
        db.session.add(margem)
        db.session.commit()

    return margem


def validar_saldo(empresa_id, valor_necessario):
    """
    Valida se empresa tem saldo suficiente
    Retorna (bool, mensagem)
    """
    empresa = db.session.get(EmpresaVendaMoto,empresa_id) if empresa_id else None

    if not empresa:
        return False, 'Empresa não encontrada'

    # Sistema permite saldo negativo (confirmado pelo usuário)
    # Então sempre retorna True, mas avisa se ficará negativo
    if empresa.saldo < valor_necessario:
        saldo_apos = empresa.saldo - valor_necessario
        return True, f'Atenção: Saldo ficará negativo (R$ {saldo_apos})'

    return True, 'Saldo suficiente'


def atualizar_saldo(empresa_id, valor, operacao='SOMAR'):
    """
    Atualiza saldo da empresa
    operacao: 'SOMAR' ou 'SUBTRAIR'
    """
    empresa = db.session.get(EmpresaVendaMoto,empresa_id) if empresa_id else None

    if not empresa:
        raise Exception(f'Empresa ID {empresa_id} não encontrada')

    if operacao == 'SOMAR':
        empresa.saldo += valor
    elif operacao == 'SUBTRAIR':
        empresa.saldo -= valor
    else:
        raise Exception(f'Operação inválida: {operacao}')

    db.session.flush()
    return empresa.saldo
