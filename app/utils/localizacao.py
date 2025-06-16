"""
Módulo unificado de localização e normalização de cidades.
Centraliza todas as funções de busca e normalização para eliminar redundâncias.
"""

from sqlalchemy import func
from app import db
from app.localidades.models import Cidade
from app.utils.string_utils import remover_acentos
import logging

logger = logging.getLogger(__name__)


class LocalizacaoService:
    """
    Serviço centralizado para localização e normalização de cidades.
    ✅ CORRIGIDO: Removido cache para evitar problemas de sessão SQLAlchemy.
    """
    
    @staticmethod
    def normalizar_nome_cidade_com_regras(nome, rota=None):
        """
        Normaliza o nome da cidade seguindo as regras de negócio:
        1. Se rota FOB -> None (será tratado separadamente)
        2. Se rota RED -> GUARULHOS/SP
        3. Se cidade SP -> SAO PAULO
        4. Se cidade RJ -> RIO DE JANEIRO
        5. Outros casos -> Remove acentos e converte para maiúsculo
        """
        if not nome:
            return None
            
        # Remove espaços extras e converte para maiúsculo
        nome = nome.strip().upper()
        
        # Verifica rota primeiro
        if rota:
            rota = rota.strip().upper()
            if rota == 'FOB':
                return None  # FOB será tratado separadamente
            if rota == 'RED':
                return 'Guarulhos'
        
        # Casos especiais de cidade
        if nome in ['SP', 'SAO PAULO', 'SÃO PAULO', 'S PAULO', 'S. PAULO']:
            return 'São Paulo'  # ✅ CORRIGIDO: Mantém o acento
        if nome in ['RJ', 'RIO DE JANEIRO', 'R JANEIRO', 'R. JANEIRO']:
            return 'Rio de Janeiro'  # ✅ CORRIGIDO: Mantém o acento
        
        # Para outros casos, remove acentos e retorna em maiúsculo
        return remover_acentos(nome)
    
    @staticmethod
    def normalizar_uf_com_regras(uf, cidade=None, rota=None):
        """
        Normaliza o UF considerando regras especiais:
        1. Se rota for RED, sempre retorna SP independente de cidade/UF
        2. Se cidade for SP, retorna SP
        3. Se cidade for RJ, retorna RJ
        4. Caso contrário, usa o UF informado
        """
        # Se for RED, é SP e pronto - nem olha cidade/UF
        if rota and rota.upper().strip() == "RED":
            return "SP"

        # Se cidade for SP, considera SP
        if cidade and cidade.upper().strip() == "SP":
            return "SP"

        # Se cidade for RJ, considera RJ
        if cidade and cidade.upper().strip() == "RJ":
            return "RJ"

        # Para outros casos, usa o UF informado
        if uf:
            return uf.upper().strip()

        return None
    
    @staticmethod
    def buscar_cidade_por_ibge(codigo_ibge):
        """
        Busca cidade por código IBGE (método mais confiável e rápido).
        ✅ CORRIGIDO: Garante que o objeto sempre esteja vinculado à sessão atual.
        """
        if not codigo_ibge:
            return None
            
        codigo_ibge = str(codigo_ibge).strip()
        
        # ✅ CORREÇÃO: Não usa cache para evitar problemas de sessão
        # O cache pode retornar objetos órfãos de sessões anteriores
        
        # Busca sempre no banco com a sessão atual
        cidade = Cidade.query.filter_by(codigo_ibge=codigo_ibge).first()
        
        # Se encontrou a cidade, garante que está na sessão atual
        if cidade:
            try:
                # ✅ GARANTE SESSÃO ATIVA: Força carregamento na sessão atual
                cidade = db.session.merge(cidade)
                
                # Teste de acesso aos atributos para garantir que funciona
                _ = cidade.nome
                _ = cidade.uf
                _ = cidade.icms
                _ = cidade.codigo_ibge
                
                logger.debug(f"✅ Cidade IBGE {codigo_ibge} carregada: {cidade.nome}/{cidade.uf}")
                
            except Exception as e:
                logger.warning(f"Erro ao processar cidade IBGE {codigo_ibge}: {e}")
                # Se falhou, tenta buscar novamente diretamente
                try:
                    cidade = db.session.query(Cidade).filter_by(codigo_ibge=codigo_ibge).first()
                    if cidade:
                        _ = cidade.nome  # Teste de acesso
                        logger.debug(f"✅ Cidade IBGE {codigo_ibge} recarregada: {cidade.nome}/{cidade.uf}")
                    else:
                        logger.warning(f"❌ Cidade IBGE {codigo_ibge} não encontrada na segunda tentativa")
                except Exception as e2:
                    logger.error(f"❌ Erro crítico ao buscar cidade IBGE {codigo_ibge}: {e2}")
                    cidade = None
        
        return cidade
    
    @staticmethod
    def buscar_cidade_por_nome(nome, uf):
        """
        Busca cidade por nome e UF (fallback quando não tem código IBGE).
        ✅ CORRIGIDO: Evita problemas de sessão SQLAlchemy.
        """
        if not nome or not uf:
            return None
            
        # Normaliza parâmetros
        nome_normalizado = remover_acentos(nome.strip()).upper()
        uf_normalizado = uf.strip().upper()
        
        # ✅ CORREÇÃO: Busca diretamente no banco sem cache
        try:
            # Busca todas as cidades do UF na sessão atual
            cidades_uf = db.session.query(Cidade).filter(
                func.upper(Cidade.uf) == uf_normalizado
            ).all()
            
            # Compara nomes normalizados
            for cidade in cidades_uf:
                try:
                    # ✅ GARANTE SESSÃO ATIVA: Já está na sessão atual da query
                    nome_db = cidade.nome
                    cidade_nome_normalizado = remover_acentos(nome_db.strip()).upper()
                    
                    if cidade_nome_normalizado == nome_normalizado:
                        # Testa acesso a todos os atributos para garantir que funciona
                        _ = cidade.uf
                        _ = cidade.icms
                        _ = cidade.codigo_ibge
                        
                        logger.debug(f"✅ Cidade encontrada por nome: {cidade.nome}/{cidade.uf}")
                        return cidade
                        
                except Exception as e:
                    logger.warning(f"Erro ao acessar dados da cidade {getattr(cidade, 'id', 'N/A')}: {e}")
                    continue
            
            logger.debug(f"❌ Cidade não encontrada: {nome_normalizado}/{uf_normalizado}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar cidade por nome {nome_normalizado}/{uf_normalizado}: {e}")
            return None
    
    @staticmethod
    def buscar_cidade_especial_fob():
        """
        Busca cidade especial FOB.
        ✅ CORRIGIDO: Garante sessão ativa.
        """
        try:
            # ✅ BUSCA DIRETA NA SESSÃO ATUAL
            cidade = db.session.query(Cidade).filter(func.upper(Cidade.nome) == 'FOB').first()
            
            if cidade:
                # Testa acesso aos atributos para garantir que funciona
                _ = cidade.nome
                _ = cidade.uf
                _ = cidade.icms
                _ = cidade.codigo_ibge
                
                logger.debug(f"✅ Cidade FOB encontrada: {cidade.nome}/{cidade.uf}")
                return cidade
            else:
                logger.debug("❌ Cidade FOB não encontrada")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao buscar cidade FOB: {e}")
            return None
    
    @staticmethod
    def buscar_cidade_unificada(pedido=None, nome=None, uf=None, codigo_ibge=None, rota=None):
        """
        Função unificada para busca de cidades.
        Implementa toda a lógica de prioridade e fallback.
        
        PRIORIDADE:
        1. Código IBGE (mais confiável)
        2. Busca por nome normalizado
        3. Casos especiais (FOB)
        """
        
        # Se recebeu um pedido, extrai os dados dele
        if pedido:
            nome = getattr(pedido, 'cidade_normalizada', None) or getattr(pedido, 'nome_cidade', None)
            uf = getattr(pedido, 'uf_normalizada', None) or getattr(pedido, 'cod_uf', None)
            codigo_ibge = getattr(pedido, 'codigo_ibge', None)
            rota = getattr(pedido, 'rota', None)
        
        logger.debug(f"Buscando cidade: nome={nome}, uf={uf}, ibge={codigo_ibge}, rota={rota}")
        
        # ESTRATÉGIA 1: Busca por código IBGE (mais confiável)
        if codigo_ibge:
            cidade = LocalizacaoService.buscar_cidade_por_ibge(codigo_ibge)
            if cidade:
                try:
                    nome_cidade = cidade.nome  # Carrega o nome dentro da sessão
                    logger.debug(f"✅ Cidade encontrada por IBGE: {nome_cidade}")
                except Exception as e:
                    logger.debug(f"✅ Cidade encontrada por IBGE (IBGE: {codigo_ibge})")
                return cidade
        
        # ESTRATÉGIA 2: Casos especiais
        if rota and rota.upper() == 'FOB':
            cidade = LocalizacaoService.buscar_cidade_especial_fob()
            if cidade:
                try:
                    nome_cidade = cidade.nome  # Carrega o nome dentro da sessão
                    logger.debug(f"✅ Cidade FOB encontrada: {nome_cidade}")
                except Exception as e:
                    logger.debug(f"✅ Cidade FOB encontrada")
                return cidade
        
        # ESTRATÉGIA 3: Normaliza cidade e UF com regras de negócio
        if nome and uf:
            nome_normalizado = LocalizacaoService.normalizar_nome_cidade_com_regras(nome, rota)
            uf_normalizado = LocalizacaoService.normalizar_uf_com_regras(uf, nome, rota)
            
            if nome_normalizado and uf_normalizado:
                cidade = LocalizacaoService.buscar_cidade_por_nome(nome_normalizado, uf_normalizado)
                if cidade:
                    try:
                        nome_cidade = cidade.nome  # Carrega o nome dentro da sessão
                        logger.debug(f"✅ Cidade encontrada por nome: {nome_cidade}")
                    except Exception as e:
                        logger.debug(f"✅ Cidade encontrada por nome normalizado")
                    return cidade
        
        logger.debug(f"❌ Cidade não encontrada")
        return None
    
    @staticmethod
    def normalizar_dados_pedido(pedido):
        """
        Normaliza os dados de localização de um pedido.
        Aplica todas as regras de negócio e tenta encontrar o código IBGE.
        """
        if not pedido:
            return False
            
        try:
            # Extrai dados originais
            nome_original = getattr(pedido, 'nome_cidade', None)
            uf_original = getattr(pedido, 'cod_uf', None)
            rota = getattr(pedido, 'rota', None)
            
            logger.debug(f"Normalizando pedido {getattr(pedido, 'num_pedido', 'N/A')}: {nome_original}/{uf_original} (rota: {rota})")
            
            # Aplica regras de normalização
            if rota and rota.upper() == 'FOB':
                # Para FOB, mantém dados originais
                pedido.cidade_normalizada = nome_original
                pedido.uf_normalizada = uf_original
            elif rota and rota.upper() == 'RED':
                # Para RED, força GUARULHOS/SP
                pedido.cidade_normalizada = 'Guarulhos'
                pedido.uf_normalizada = 'SP'
            else:
                # Para outros casos, aplica normalização
                pedido.cidade_normalizada = LocalizacaoService.normalizar_nome_cidade_com_regras(nome_original, rota)
                pedido.uf_normalizada = LocalizacaoService.normalizar_uf_com_regras(uf_original, nome_original, rota)
            
            # Tenta encontrar e salvar o código IBGE se ainda não tem
            if not getattr(pedido, 'codigo_ibge', None):
                cidade = LocalizacaoService.buscar_cidade_unificada(
                    nome=pedido.cidade_normalizada,
                    uf=pedido.uf_normalizada,
                    rota=rota
                )
                
                if cidade:
                    try:
                        # ✅ CARREGA DADOS DA CIDADE IMEDIATAMENTE PARA EVITAR PROBLEMAS DE SESSÃO
                        codigo_ibge = cidade.codigo_ibge
                        if codigo_ibge:
                            pedido.codigo_ibge = codigo_ibge
                            logger.debug(f"✅ Código IBGE {codigo_ibge} salvo no pedido")
                    except Exception as e:
                        logger.warning(f"Erro ao acessar código IBGE da cidade: {e}")
                        # Tenta recarregar a cidade na sessão atual
                        try:
                            cidade_recarregada = db.session.merge(cidade)
                            if cidade_recarregada and cidade_recarregada.codigo_ibge:
                                pedido.codigo_ibge = cidade_recarregada.codigo_ibge
                                logger.debug(f"✅ Código IBGE {cidade_recarregada.codigo_ibge} salvo após recarregar")
                        except Exception as e2:
                            logger.warning(f"Erro ao recarregar cidade: {e2}")
            
            logger.debug(f"Dados normalizados: {pedido.cidade_normalizada}/{pedido.uf_normalizada} (IBGE: {getattr(pedido, 'codigo_ibge', 'N/A')})")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao normalizar dados do pedido: {str(e)}")
            return False
    
    @staticmethod
    def obter_icms_cidade(pedido=None, nome=None, uf=None, codigo_ibge=None, rota=None):
        """
        Obtém o ICMS da cidade usando a busca unificada.
        Retorna 0 se não encontrar a cidade.
        """
        cidade = LocalizacaoService.buscar_cidade_unificada(
            pedido=pedido,
            nome=nome,
            uf=uf,
            codigo_ibge=codigo_ibge,
            rota=rota
        )
        
        if cidade:
            try:
                return cidade.icms or 0
            except Exception as e:
                logger.warning(f"Erro ao acessar ICMS da cidade: {e}")
                # Tenta recarregar a cidade
                try:
                    cidade_recarregada = db.session.merge(cidade)
                    if cidade_recarregada:
                        return cidade_recarregada.icms or 0
                except Exception as e2:
                    logger.warning(f"Erro ao recarregar cidade para ICMS: {e2}")
        return 0
    
    @staticmethod
    def atualizar_todos_codigos_ibge():
        """
        Atualiza os códigos IBGE de todos os pedidos que não têm.
        Função para execução em massa.
        """
        from app.pedidos.models import Pedido
        
        # Busca pedidos sem código IBGE
        pedidos_sem_ibge = Pedido.query.filter(
            (Pedido.codigo_ibge.is_(None)) | (Pedido.codigo_ibge == ''),
            Pedido.cidade_normalizada.isnot(None)
        ).all()
        
        logger.info(f"Encontrados {len(pedidos_sem_ibge)} pedidos sem código IBGE")
        
        contador_atualizados = 0
        contador_nao_encontrados = 0
        
        for pedido in pedidos_sem_ibge:
            # Usa a busca unificada
            cidade = LocalizacaoService.buscar_cidade_unificada(pedido=pedido)
            
            if cidade and cidade.codigo_ibge:
                pedido.codigo_ibge = cidade.codigo_ibge
                contador_atualizados += 1
                
                if contador_atualizados % 100 == 0:
                    db.session.commit()
                    logger.info(f"Atualizados {contador_atualizados} pedidos...")
            else:
                contador_nao_encontrados += 1
                logger.warning(f"Cidade não encontrada para pedido {pedido.num_pedido}: {pedido.cidade_normalizada}/{pedido.uf_normalizada}")
        
        # Commit final
        db.session.commit()
        
        logger.info(f"Processo concluído:")
        logger.info(f"- Pedidos atualizados: {contador_atualizados}")
        logger.info(f"- Pedidos não encontrados: {contador_nao_encontrados}")
        
        return contador_atualizados, contador_nao_encontrados
    



# Função de compatibilidade para não quebrar código existente
def normalizar_nome_cidade(nome, rota=None):
    """Função de compatibilidade. Use LocalizacaoService.normalizar_nome_cidade_com_regras()"""
    return LocalizacaoService.normalizar_nome_cidade_com_regras(nome, rota)


def buscar_cidade_unificada(pedido=None, cidade=None, uf=None, rota=None):
    """Função de compatibilidade. Use LocalizacaoService.buscar_cidade_unificada()"""
    return LocalizacaoService.buscar_cidade_unificada(
        pedido=pedido,
        nome=cidade,
        uf=uf,
        rota=rota
    ) 