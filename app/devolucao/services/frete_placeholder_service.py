"""
Service para criar Fretes placeholder para devoluções órfãs

Quando uma NFD é criada sem que exista um Frete para a NF de venda original
(ex: NF de venda anterior a julho/2024), este service cria um Frete "placeholder"
com valores zerados para permitir a vinculação de DespesaExtra.
"""
from app import db
from app.fretes.models import Frete, DespesaExtra
from app.embarques.models import Embarque
from app.transportadoras.models import Transportadora
from app.devolucao.models import NFDevolucao


def buscar_embarque_devolucao():
    """Busca o embarque fictício para devoluções (numero=0)"""
    return Embarque.query.filter_by(numero=0).first()


def buscar_transportadora_devolucao():
    """Busca a transportadora fictícia 'Devolução' (CNPJ=00000000000000)"""
    return Transportadora.query.filter_by(cnpj='00000000000000').first()


def buscar_frete_por_nf(numero_nf: str):
    """
    Busca Frete existente que contenha a NF de venda.
    Busca no campo numeros_nfs (CSV) do Frete.
    """
    if not numero_nf:
        return None

    # Buscar fretes que contenham a NF
    fretes = Frete.query.filter(
        Frete.numeros_nfs.isnot(None)
    ).all()

    for frete in fretes:
        nfs_frete = [nf.strip() for nf in frete.numeros_nfs.split(',') if nf.strip()]
        if numero_nf in nfs_frete:
            return frete

    return None


def criar_frete_placeholder(nfd: NFDevolucao, numero_nf_venda: str, criado_por: str = 'Sistema') -> Frete:
    """
    Cria Frete placeholder para NFDs órfãs (NF de venda sem Frete)

    Args:
        nfd: NFDevolucao que originou a necessidade do frete
        numero_nf_venda: Número da NF de venda original
        criado_por: Usuário que está criando (default: 'Sistema')

    Returns:
        Frete: Objeto Frete criado (ainda não commitado)

    Raises:
        ValueError: Se embarque ou transportadora fictícios não existirem
    """
    # Buscar Embarque e Transportadora fictícios
    embarque_dev = buscar_embarque_devolucao()
    transp_dev = buscar_transportadora_devolucao()

    if not embarque_dev:
        raise ValueError(
            "Embarque fictício para devoluções não encontrado! "
            "Execute a migração: criar_embarque_devolucao.py"
        )

    if not transp_dev:
        raise ValueError(
            "Transportadora 'Devolução' não encontrada! "
            "Execute a migração: criar_transportadora_devolucao.py"
        )

    # Criar frete placeholder com valores zerados
    frete = Frete(
        embarque_id=embarque_dev.id,
        transportadora_id=transp_dev.id,
        cnpj_cliente=nfd.cnpj_emitente or '00000000000000',
        nome_cliente=nfd.nome_emitente or 'Cliente Devolução',
        tipo_carga='FRACIONADA',
        modalidade='DEVOLUÇÃO',
        uf_destino=nfd.uf_emitente or 'SP',
        cidade_destino=nfd.endereco_emitente or 'N/A',
        peso_total=0,
        valor_total_nfs=0,
        quantidade_nfs=1,
        numeros_nfs=numero_nf_venda,
        valor_cotado=0,
        valor_considerado=0,
        status='PENDENTE',
        criado_por=f'{criado_por} - Devolução NFD {nfd.numero_nfd}'
    )

    db.session.add(frete)
    db.session.flush()  # Obtém o ID sem commitar

    return frete


def obter_ou_criar_frete_para_devolucao(
    nfd: NFDevolucao,
    numero_nf_venda: str,
    criado_por: str = 'Sistema'
) -> tuple:
    """
    Obtém Frete existente ou cria placeholder para devolução.

    Args:
        nfd: NFDevolucao
        numero_nf_venda: Número da NF de venda
        criado_por: Usuário

    Returns:
        tuple: (frete, criado_novo)
            - frete: objeto Frete
            - criado_novo: bool indicando se foi criado novo
    """
    # Tentar encontrar frete existente
    frete = buscar_frete_por_nf(numero_nf_venda)

    if frete:
        return frete, False

    # Criar placeholder
    frete = criar_frete_placeholder(nfd, numero_nf_venda, criado_por)
    return frete, True


def criar_despesa_devolucao(
    frete: Frete,
    nfd: NFDevolucao,
    valor: float,
    criado_por: str
) -> DespesaExtra:
    """
    Cria DespesaExtra do tipo DEVOLUÇÃO vinculada ao Frete e NFD.

    Args:
        frete: Frete ao qual vincular
        nfd: NFDevolucao relacionada
        valor: Valor da despesa
        criado_por: Usuário

    Returns:
        DespesaExtra: Objeto criado (ainda não commitado)
    """
    despesa = DespesaExtra(
        frete_id=frete.id,
        tipo_despesa='DEVOLUÇÃO',
        tipo_documento='PENDENTE',
        numero_documento=f'NFD-{nfd.numero_nfd}',
        valor_despesa=valor or 0,
        setor_responsavel='LOGISTICA',
        motivo_despesa='DEVOLUÇÃO',
        observacoes=f'Devolução ref. NFD {nfd.numero_nfd}',
        criado_por=criado_por,
        nfd_id=nfd.id,
        numero_nfd=nfd.numero_nfd
    )

    db.session.add(despesa)
    db.session.flush()

    return despesa
