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
    """
    
    # Cache em memória para melhor performance
    _cache_cidades_ibge = {}
    _cache_cidades_nome = {}
    
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
                return 'GUARULHOS'
        
        # Casos especiais de cidade
        if nome in ['SP', 'SAO PAULO', 'SÃO PAULO', 'S PAULO', 'S. PAULO']:
            return 'SAO PAULO'
        if nome in ['RJ', 'RIO DE JANEIRO', 'R JANEIRO', 'R. JANEIRO']:
            return 'RIO DE JANEIRO'
        
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
        Usa cache em memória para melhor performance.
        """
        if not codigo_ibge:
            return None
            
        codigo_ibge = str(codigo_ibge).strip()
        
        # Verifica cache primeiro
        if codigo_ibge in LocalizacaoService._cache_cidades_ibge:
            return LocalizacaoService._cache_cidades_ibge[codigo_ibge]
        
        # Busca no banco
        cidade = Cidade.query.filter_by(codigo_ibge=codigo_ibge).first()
        
        # Salva no cache
        LocalizacaoService._cache_cidades_ibge[codigo_ibge] = cidade
        
        return cidade
    
    @staticmethod
    def buscar_cidade_por_nome(nome, uf):
        """
        Busca cidade por nome e UF (fallback quando não tem código IBGE).
        Usa normalização para comparação.
        """
        if not nome or not uf:
            return None
            
        # Normaliza parâmetros
        nome_normalizado = remover_acentos(nome.strip()).upper()
        uf_normalizado = uf.strip().upper()
        
        # Verifica cache
        cache_key = f"{nome_normalizado}_{uf_normalizado}"
        if cache_key in LocalizacaoService._cache_cidades_nome:
            return LocalizacaoService._cache_cidades_nome[cache_key]
        
        # Busca todas as cidades do UF
        cidades_uf = Cidade.query.filter(
            func.upper(Cidade.uf) == uf_normalizado
        ).all()
        
        # Compara nomes normalizados
        cidade_encontrada = None
        for cidade in cidades_uf:
            cidade_nome_normalizado = remover_acentos(cidade.nome.strip()).upper()
            if cidade_nome_normalizado == nome_normalizado:
                cidade_encontrada = cidade
                break
        
        # Salva no cache
        LocalizacaoService._cache_cidades_nome[cache_key] = cidade_encontrada
        
        return cidade_encontrada
    
    @staticmethod
    def buscar_cidade_especial_fob():
        """
        Busca cidade especial FOB.
        """
        return Cidade.query.filter(func.upper(Cidade.nome) == 'FOB').first()
    
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
                logger.debug(f"✅ Cidade encontrada por IBGE: {cidade.nome}")
                return cidade
        
        # ESTRATÉGIA 2: Casos especiais
        if rota and rota.upper() == 'FOB':
            cidade = LocalizacaoService.buscar_cidade_especial_fob()
            if cidade:
                logger.debug(f"✅ Cidade FOB encontrada: {cidade.nome}")
                return cidade
        
        # ESTRATÉGIA 3: Normaliza cidade e UF com regras de negócio
        if nome and uf:
            nome_normalizado = LocalizacaoService.normalizar_nome_cidade_com_regras(nome, rota)
            uf_normalizado = LocalizacaoService.normalizar_uf_com_regras(uf, nome, rota)
            
            if nome_normalizado and uf_normalizado:
                cidade = LocalizacaoService.buscar_cidade_por_nome(nome_normalizado, uf_normalizado)
                if cidade:
                    logger.debug(f"✅ Cidade encontrada por nome: {cidade.nome}")
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
                pedido.cidade_normalizada = 'GUARULHOS'
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
                
                if cidade and cidade.codigo_ibge:
                    pedido.codigo_ibge = cidade.codigo_ibge
                    logger.debug(f"✅ Código IBGE {cidade.codigo_ibge} salvo no pedido")
            
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
            return cidade.icms or 0
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
    
    @staticmethod
    def limpar_cache():
        """
        Limpa o cache em memória.
        Útil quando há atualizações na tabela de cidades.
        """
        LocalizacaoService._cache_cidades_ibge.clear()
        LocalizacaoService._cache_cidades_nome.clear()
        logger.info("Cache de localização limpo")


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