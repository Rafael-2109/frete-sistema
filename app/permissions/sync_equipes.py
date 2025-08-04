"""
Funções para sincronização de equipes de vendas
"""
import logging
from app import db
from app.permissions.models import EquipeVendas
from app.faturamento.models import RelatorioFaturamentoImportado

logger = logging.getLogger(__name__)


def sincronizar_equipe_por_nome(equipe_nome: str, criado_por_id: int = None) -> EquipeVendas:
    """
    Busca ou cria uma equipe de vendas pelo nome.
    Usado para sincronizar equipes do faturamento com a tabela equipe_vendas.
    
    Args:
        equipe_nome: Nome da equipe
        criado_por_id: ID do usuário que está criando (opcional)
        
    Returns:
        EquipeVendas: Objeto da equipe (existente ou criada)
    """
    if not equipe_nome:
        return None
        
    # Buscar equipe existente
    equipe = EquipeVendas.query.filter_by(nome=equipe_nome).first()
    
    if equipe:
        return equipe
    
    # Criar nova equipe
    codigo = equipe_nome.upper().replace(' ', '_')[:50]
    
    # Garantir código único
    codigo_base = codigo
    contador = 1
    while EquipeVendas.query.filter_by(codigo=codigo).first():
        codigo = f"{codigo_base}_{contador}"
        contador += 1
    
    equipe = EquipeVendas(
        codigo=codigo,
        nome=equipe_nome,
        descricao=f"Equipe sincronizada do faturamento",
        ativo=True,
        criado_por=criado_por_id
    )
    
    db.session.add(equipe)
    db.session.flush()  # Para obter o ID sem fazer commit
    
    logger.info(f"Equipe criada: {equipe_nome} (código: {codigo})")
    
    return equipe


def obter_mapa_equipes_temporarias():
    """
    Cria um mapa de IDs temporários para nomes de equipes.
    Usado para converter os IDs temporários da API para nomes reais.
    
    Returns:
        dict: Mapa {id_temporario: nome_equipe}
    """
    # Buscar equipes únicas do faturamento - ordenar por nome para consistência
    equipes_faturamento = db.session.query(
        RelatorioFaturamentoImportado.equipe_vendas
    ).filter(
        RelatorioFaturamentoImportado.equipe_vendas.isnot(None),
        RelatorioFaturamentoImportado.equipe_vendas != ''
    ).distinct().order_by(
        RelatorioFaturamentoImportado.equipe_vendas
    ).all()
    
    # Criar mapa de índice temporário para nome
    equipes_map = {}
    for idx, (equipe,) in enumerate(equipes_faturamento):
        if equipe:
            equipes_map[idx + 1] = equipe  # O ID temporário é idx + 1
            
    return equipes_map


def sincronizar_todas_equipes_faturamento(criado_por_id: int = None):
    """
    Sincroniza todas as equipes do RelatorioFaturamentoImportado
    para a tabela equipe_vendas.
    
    Args:
        criado_por_id: ID do usuário que está criando (opcional)
        
    Returns:
        dict: Estatísticas da sincronização
    """
    try:
        logger.info("Iniciando sincronização de equipes de vendas...")
        
        # Buscar equipes únicas do faturamento
        equipes_faturamento = db.session.query(
            RelatorioFaturamentoImportado.equipe_vendas
        ).filter(
            RelatorioFaturamentoImportado.equipe_vendas.isnot(None),
            RelatorioFaturamentoImportado.equipe_vendas != ''
        ).distinct().order_by(
            RelatorioFaturamentoImportado.equipe_vendas
        ).all()
        
        equipes_criadas = 0
        equipes_existentes = 0
        
        for (equipe_nome,) in equipes_faturamento:
            if not equipe_nome:
                continue
                
            # Verificar se já existe
            equipe_existente = EquipeVendas.query.filter_by(nome=equipe_nome).first()
            
            if equipe_existente:
                equipes_existentes += 1
            else:
                # Criar nova equipe
                sincronizar_equipe_por_nome(equipe_nome, criado_por_id)
                equipes_criadas += 1
        
        # Commit apenas no final
        if equipes_criadas > 0:
            db.session.commit()
            
        logger.info(f"Sincronização concluída: {equipes_criadas} criadas, {equipes_existentes} já existentes")
        
        return {
            'total': len(equipes_faturamento),
            'criadas': equipes_criadas,
            'existentes': equipes_existentes,
            'sucesso': True
        }
        
    except Exception as e:
        logger.error(f"Erro ao sincronizar equipes: {e}")
        db.session.rollback()
        return {
            'sucesso': False,
            'erro': str(e)
        }