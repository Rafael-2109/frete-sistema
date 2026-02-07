"""
Utilitários para separação e workspace
"""

from datetime import datetime
from app import db
from app.carteira.models import CarteiraPrincipal
from app.producao.models import CadastroPalletizacao
from app.localidades.models import CadastroRota, CadastroSubRota
from app.utils.text_utils import truncar_observacao
import logging
import re

logger = logging.getLogger(__name__)


def determinar_tipo_envio(num_pedido, produtos_lote, produtos_carteira):
    """
    Determina se o envio é 'total' ou 'parcial' baseado nas quantidades
    
    Se estiver enviando TODOS os produtos do pedido com as quantidades COMPLETAS,
    então é 'total', senão é 'parcial'.
    """
    try:
        # Buscar todos os produtos do pedido na carteira
        todos_produtos_pedido = db.session.query(CarteiraPrincipal).filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True
        ).all()

        if not todos_produtos_pedido:
            return 'parcial'

        # Criar mapa de quantidades do pedido
        qtd_pedido_total = {}
        for item in todos_produtos_pedido:
            cod = item.cod_produto
            qtd_pedido_total[cod] = qtd_pedido_total.get(cod, 0) + float(item.qtd_saldo_produto_pedido or 0)

        # Criar mapa de quantidades sendo separadas
        qtd_separando = {}
        for produto in produtos_lote:
            cod = produto.get('cod_produto')
            qtd = produto.get('quantidade', 0)
            qtd_separando[cod] = qtd_separando.get(cod, 0) + float(qtd)

        # Verificar se está separando tudo
        produtos_pedido_set = set(qtd_pedido_total.keys())
        produtos_separando_set = set(qtd_separando.keys())

        # Se não está separando todos os produtos, é parcial
        if produtos_separando_set != produtos_pedido_set:
            return 'parcial'

        # Se está separando todos os produtos, verificar quantidades
        for cod_produto in produtos_pedido_set:
            qtd_total = qtd_pedido_total[cod_produto]
            qtd_sep = qtd_separando.get(cod_produto, 0)
            
            # Se a quantidade separada é menor que a total (com margem de 0.01), é parcial
            if qtd_sep < (qtd_total - 0.01):
                return 'parcial'

        # Se chegou até aqui, está separando tudo = total
        return 'total'

    except Exception as e:
        logger.error(f"Erro ao determinar tipo de envio: {e}")
        return 'parcial'  # Default para parcial em caso de erro


def calcular_peso_pallet_produto(cod_produto, quantidade):
    """
    Calcula peso e pallet usando CadastroPalletizacao
    
    Args:
        cod_produto (str): Código do produto
        quantidade (float): Quantidade a calcular
        
    Returns:
        tuple: (peso_total, pallet_total)
    """
    try:
        palletizacao = db.session.query(CadastroPalletizacao).filter(
            CadastroPalletizacao.cod_produto == cod_produto,
            CadastroPalletizacao.ativo == True
        ).first()
        
        if palletizacao:
            peso_bruto = float(palletizacao.peso_bruto or 0)
            qtd_pallet = float(palletizacao.palletizacao or 1)
            
            # Peso = quantidade * peso_bruto
            peso_total = quantidade * peso_bruto
            
            # Pallet = quantidade / palletizacao
            pallet_total = quantidade / qtd_pallet if qtd_pallet > 0 else 0
            
            return peso_total, pallet_total
        else:
            # Valores padrão se não encontrar palletização
            return quantidade * 1.0, quantidade / 100.0
            
    except Exception as e:
        logger.error(f"Erro ao calcular peso/pallet para {cod_produto}: {e}")
        return quantidade * 1.0, quantidade / 100.0


def buscar_rota_por_uf(cod_uf):
    """Busca rota principal baseada no cod_uf"""
    if not cod_uf:
        return None
    try:
        rota = CadastroRota.query.filter_by(cod_uf=cod_uf, ativa=True).first()
        return rota.rota if rota else None  # Corrigido: usar .rota em vez de .nome
    except Exception as e:
        logger.debug(f"Erro ao buscar rota para UF {cod_uf}: {e}")
        return None


def buscar_sub_rota_por_uf_cidade(cod_uf, nome_cidade):
    """
    Busca sub-rota baseada no cod_uf + nome_cidade
    Usa ILIKE para busca com acentos
    """
    if not cod_uf or not nome_cidade:
        return None
    try:
        # Normalizar nome da cidade (remover acentos e espaços extras)
        nome_normalizado = re.sub(r'[^\w\s]', '', nome_cidade.strip().upper())
        
        sub_rota = CadastroSubRota.query.filter(
            CadastroSubRota.cod_uf == cod_uf,
            CadastroSubRota.nome_cidade.ilike(f'%{nome_normalizado}%'),
            CadastroSubRota.ativa == True
        ).first()
        
        return sub_rota.sub_rota if sub_rota else None  # Corrigido: usar .sub_rota em vez de .nome
    except Exception as e:
        logger.debug(f"Erro ao buscar sub-rota para {nome_cidade}/{cod_uf}: {e}")
        return None


# Função gerar_novo_lote_id movida para app.utils.lote_utils para padronização
# Importada no topo do arquivo como alias para manter compatibilidade


def gerar_separacao_workspace_interno(num_pedido, lote_id, produtos, expedicao, agendamento=None, protocolo=None):
    """
    Função interna para gerar separação (usado por pre_separacao_api.py)
    """
    try:
        from app.separacao.models import Separacao
        from app.utils.timezone import agora_utc_naive
        
        # Buscar informações dos produtos na carteira
        produtos_carteira = {}
        for produto in produtos:
            cod_produto = produto.get('cod_produto')
            item_carteira = db.session.query(CarteiraPrincipal).filter(
                CarteiraPrincipal.num_pedido == num_pedido,
                CarteiraPrincipal.cod_produto == cod_produto,
                CarteiraPrincipal.ativo == True
            ).first()
            
            if item_carteira:
                produtos_carteira[cod_produto] = item_carteira

        # Determinar tipo de envio
        tipo_envio = determinar_tipo_envio(num_pedido, produtos, produtos_carteira)

        # Converter datas
        try:
            expedicao_obj = datetime.strptime(expedicao, '%Y-%m-%d').date() if expedicao else None
        except ValueError:
            expedicao_obj = None
            
        try:
            agendamento_obj = datetime.strptime(agendamento, '%Y-%m-%d').date() if agendamento else None
        except ValueError:
            agendamento_obj = None

        # Criar separações
        separacoes_criadas = []
        for produto in produtos:
            cod_produto = produto.get('cod_produto')
            quantidade = float(produto.get('quantidade', 0))
            
            if quantidade <= 0:
                continue
                
            item_carteira = produtos_carteira.get(cod_produto)
            if not item_carteira:
                continue

            # Calcular valores
            preco_unitario = float(item_carteira.preco_produto_pedido or 0)
            valor_separacao = quantidade * preco_unitario
            
            # Calcular peso e pallet
            peso_calculado, pallet_calculado = calcular_peso_pallet_produto(cod_produto, quantidade)
            
            # Buscar rota
            # Se incoterm for RED ou FOB, usar ele como rota
            if hasattr(item_carteira, 'incoterm') and item_carteira.incoterm in ["RED", "FOB"]:
                rota_calculada = item_carteira.incoterm
            else:
                rota_calculada = buscar_rota_por_uf(item_carteira.cod_uf or 'SP')
            sub_rota_calculada = buscar_sub_rota_por_uf_cidade(
                item_carteira.cod_uf or '', 
                item_carteira.nome_cidade or ''
            )

            # Criar separação
            separacao = Separacao(
                separacao_lote_id=lote_id,
                num_pedido=num_pedido,
                data_pedido=item_carteira.data_pedido,
                cnpj_cpf=item_carteira.cnpj_cpf,
                raz_social_red=item_carteira.raz_social_red,
                nome_cidade=item_carteira.nome_cidade,
                cod_uf=item_carteira.cod_uf,
                cod_produto=cod_produto,
                nome_produto=item_carteira.nome_produto,
                qtd_saldo=quantidade,
                valor_saldo=valor_separacao,
                peso=peso_calculado,
                pallet=pallet_calculado,
                rota=rota_calculada,
                sub_rota=sub_rota_calculada,
                observ_ped_1=truncar_observacao(item_carteira.observ_ped_1),
                tags_pedido=item_carteira.tags_pedido,
                roteirizacao=None,
                expedicao=expedicao_obj,
                agendamento=agendamento_obj,
                protocolo=protocolo,
                tipo_envio=tipo_envio,
                sincronizado_nf=False,  # IMPORTANTE: Sempre criar com False (não NULL)
                criado_em=agora_utc_naive()
            )
            
            db.session.add(separacao)
            separacoes_criadas.append(separacao)

        if not separacoes_criadas:
            return {
                'success': False,
                'error': 'Nenhuma separação foi criada'
            }


        db.session.commit()

        return {
            'success': True,
            'message': f'Separação gerada com sucesso! {len(separacoes_criadas)} itens criados.',
            'separacoes_criadas': len(separacoes_criadas)
        }

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro na função interna de separação: {e}")
        return {
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }