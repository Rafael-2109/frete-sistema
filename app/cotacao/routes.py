# ✅ IMPORTS REORGANIZADOS - Todos os imports necessários no topo
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime

# Database
from app import db

# Models
from app.cotacao.forms import CotarFreteForm
from app.cotacao.models import Cotacao
from app.pedidos.models import Pedido
from app.transportadoras.models import Transportadora
from app.embarques.models import Embarque, EmbarqueItem
from app.tabelas.models import TabelaFrete
from app.localidades.models import Cidade
from app.veiculos.models import Veiculo
from app.vinculos.models import CidadeAtendida

# Utils
from app.utils.localizacao import LocalizacaoService
from app.utils.frete_simulador import calcular_frete_por_cnpj, buscar_cidade_unificada
from app.utils.vehicle_utils import normalizar_nome_veiculo
from app.utils.calculadora_frete import CalculadoraFrete

# Routes
from app.embarques.routes import obter_proximo_numero_embarque

# Conditional imports (só quando necessário)
try:
    from dateutil import parser as date_parser
except ImportError:
    date_parser = None

cotacao_bp = Blueprint("cotacao", __name__, url_prefix="/cotacao")

# LocalizacaoService usa métodos estáticos, não precisa ser instanciado

def obter_nome_cidade_correto(pedido):
    """
    Função de compatibilidade - usa LocalizacaoService
    """
    return LocalizacaoService.buscar_cidade_unificada(
        nome=pedido.nome_cidade,
        uf=pedido.cod_uf,
        rota=getattr(pedido, 'rota', None)
    )

def formatar_protocolo(protocolo):
    """
    Formata protocolo removendo .0 se for número
    """
    if protocolo is None:
        return ''
    
    # Se for string, verifica se termina com .0 e remove
    if isinstance(protocolo, str):
        if protocolo.endswith('.0'):
            return protocolo[:-2]
        return protocolo
    
    # Se for número, converte para string e remove .0 se existir
    try:
        # Converte para string primeiro para evitar problemas com números grandes
        protocolo_str = str(protocolo)
        
        # Se termina com .0, remove
        if protocolo_str.endswith('.0'):
            return protocolo_str[:-2]
        
        # Se é um float que representa um inteiro, converte para int
        if isinstance(protocolo, float) and protocolo.is_integer():
            return str(int(protocolo))
        
        return protocolo_str
        
    except (ValueError, TypeError):
        return str(protocolo) if protocolo else ''

def formatar_data_brasileira(data):
    """
    Formatar data para dd/mm/aaaa - VERSÃO CORRIGIDA para evitar erro 'None' has no attribute 'strftime'
    """
    # 🔧 CORREÇÃO: Verificação mais rigorosa para None/vazio
    if data is None or data == '' or str(data).lower() in ['none', 'null']:
        return ''
    
    try:
        # 🔧 CORREÇÃO: Verificação adicional antes de usar strftime
        # Se já for datetime.date ou datetime.datetime e não for None
        if data is not None and hasattr(data, 'strftime'):
            return data.strftime('%d/%m/%Y')
        
                    # Se for string, tenta converter
            if isinstance(data, str):
                data = data.strip()
                if not data or data.lower() in ['none', 'null', '']:
                    return ''
                    
                # Tenta vários formatos comuns
                formatos = [
                    '%Y-%m-%d',      # 2025-05-29
                    '%d/%m/%Y',      # 2025/05/29
                    '%Y-%m-%d %H:%M:%S',  # 2025-05-29 10:30:00
                    '%d/%m/%Y %H:%M:%S',  # 2025/05/29 10:30:00
                    '%d-%m-%Y',      # 29-05-2025
                    '%m/%d/%Y',      # 05/29/2025 (formato americano)
                ]
                for formato in formatos:
                    try:
                        data_obj = datetime.strptime(data, formato)
                        return data_obj.strftime('%d/%m/%Y')
                    except ValueError:
                        continue
                        
                # Se não conseguiu converter com formatos conhecidos, tenta parsing mais flexível
                if date_parser:
                    try:
                        data_obj = date_parser.parse(data)
                        return data_obj.strftime('%d/%m/%Y')
                    except:
                        pass
        
        # Se for número (timestamp)
        if isinstance(data, (int, float)):
            try:
                data_obj = datetime.fromtimestamp(data)
                return data_obj.strftime('%d/%m/%Y')
            except:
                pass
        
        # 🔧 CORREÇÃO: Retorna string vazia para valores inválidos
        return ''
        
    except Exception as e:
        print(f"[DEBUG] Erro ao formatar data '{data}': {str(e)}")
        return ''  # 🔧 CORREÇÃO: Sempre retorna string vazia em caso de erro

def calcular_otimizacoes_pedido_adicional(pedido, pedidos_atuais, transportadora, modalidade, peso_total, veiculos, frete_atual_kg):
    """
    Calcula as otimizações possíveis para um pedido que pode ser adicionado
    ✅ NOVO: Usa TABELA MAIS CARA para cenário conservador
    """
    otimizacoes = {}
    
    # 1. Calcula frete COM este pedido adicionado
    pedidos_com = pedidos_atuais + [pedido]
    peso_com = peso_total + (pedido.peso_total or 0)
    
    # Recalcula frete com este pedido usando simulador
    try:
        # Normaliza dados dos pedidos
        for p in pedidos_com:
            LocalizacaoService.normalizar_dados_pedido(p)
        
        # ✅ LÓGICA TABELA MAIS CARA: Calcula com pior cenário
        resultados = calcular_frete_otimizacao_conservadora(pedidos_com)
        
        # Se tem resultados diretos, pega a PIOR opção (mais cara)
        if resultados and resultados.get('diretas'):
            # ✅ MUDANÇA: Ordena do MAIOR para MENOR valor/kg (pior cenário)
            opcoes_ordenadas = sorted(
                resultados['diretas'], 
                key=lambda x: x['valor_liquido'] / peso_com if peso_com > 0 else 0,
                reverse=True  # Pior primeiro (mais caro)
            )
            
            pior_opcao = opcoes_ordenadas[0]  # Tabela mais cara
            novo_frete_kg = pior_opcao['valor_liquido'] / peso_com if peso_com > 0 else float('inf')
            reducao_rota = frete_atual_kg - novo_frete_kg
            
            # ✅ CRITÉRIO CONSERVADOR: Se mesmo com tabela mais cara houve redução
            if reducao_rota > 0.01:
                otimizacoes['nova_rota_diff'] = reducao_rota
                otimizacoes['reducao_por_kg_rota'] = reducao_rota
                otimizacoes['nova_tabela'] = pior_opcao['nome_tabela']
                otimizacoes['frete_bruto_novo'] = pior_opcao['valor_total']
                otimizacoes['frete_liquido_novo'] = pior_opcao['valor_liquido']
                otimizacoes['frete_kg_novo'] = novo_frete_kg
                otimizacoes['frete_kg_atual'] = frete_atual_kg
                otimizacoes['peso_atual'] = peso_total
                otimizacoes['peso_novo'] = peso_com
                otimizacoes['reducao_total'] = reducao_rota * peso_com
                otimizacoes['nova_transportadora'] = pior_opcao['transportadora']
                otimizacoes['nova_modalidade'] = pior_opcao['modalidade']
                
                print(f"[DEBUG] 💡 OTIMIZAÇÃO CONSERVADORA para adicionar {pedido.num_pedido}:")
                print(f"[DEBUG]   - Frete atual: R${frete_atual_kg:.3f}/kg")
                print(f"[DEBUG]   - Novo frete (PIOR): R${novo_frete_kg:.3f}/kg")
                print(f"[DEBUG]   - Redução: R${reducao_rota:.3f}/kg")
                print(f"[DEBUG]   - Tabela mais cara: {pior_opcao['nome_tabela']}")
                
    except Exception as e:
        print(f"[DEBUG] Erro ao calcular otimização para adicionar {pedido.num_pedido}: {str(e)}")
    
    return otimizacoes if otimizacoes else None

def calcular_otimizacoes_pedido(pedido, pedidos_atuais, modalidade, veiculos, frete_atual_kg):
    """
    Calcula as otimizações possíveis removendo um pedido específico
    ✅ NOVO: Usa TABELA MAIS CARA para cenário conservador
    """
    otimizacoes = {}
    
    # 1. Calcula frete SEM este pedido
    pedidos_sem = [p for p in pedidos_atuais if p.id != pedido.id]
    peso_sem = sum(p.peso_total or 0 for p in pedidos_sem)
    peso_total = sum(p.peso_total or 0 for p in pedidos_atuais)
    
    # Só calcula se ainda sobrar pelo menos 1 pedido
    if not pedidos_sem:
        return None
    
    # Recalcula frete sem este pedido usando simulador
    try:
        # Normaliza dados dos pedidos
        for p in pedidos_sem:
            LocalizacaoService.normalizar_dados_pedido(p)
        
        # ✅ LÓGICA TABELA MAIS CARA: Calcula com pior cenário
        resultados = calcular_frete_otimizacao_conservadora(pedidos_sem)
        
        # Se tem resultados diretos, pega a PIOR opção (mais cara)
        if resultados and resultados.get('diretas'):
            # ✅ MUDANÇA: Ordena do MAIOR para MENOR valor/kg (pior cenário)
            opcoes_ordenadas = sorted(
                resultados['diretas'], 
                key=lambda x: x['valor_liquido'] / peso_sem if peso_sem > 0 else 0,
                reverse=True  # Pior primeiro (mais caro)
            )
            
            pior_opcao = opcoes_ordenadas[0]  # Tabela mais cara
            novo_frete_kg = pior_opcao['valor_liquido'] / peso_sem if peso_sem > 0 else float('inf')
            reducao_rota = frete_atual_kg - novo_frete_kg
            
            # ✅ CRITÉRIO CONSERVADOR: Se mesmo com tabela mais cara houve redução
            if reducao_rota > 0.01:
                otimizacoes['nova_rota_diff'] = reducao_rota
                otimizacoes['reducao_por_kg_rota'] = reducao_rota
                otimizacoes['nova_tabela'] = pior_opcao['nome_tabela']
                otimizacoes['frete_bruto_novo'] = pior_opcao['valor_total']
                otimizacoes['frete_liquido_novo'] = pior_opcao['valor_liquido']
                otimizacoes['frete_kg_novo'] = novo_frete_kg
                otimizacoes['frete_kg_atual'] = frete_atual_kg
                otimizacoes['peso_atual'] = peso_total
                otimizacoes['peso_novo'] = peso_sem
                otimizacoes['reducao_total'] = reducao_rota * peso_sem
                otimizacoes['nova_transportadora'] = pior_opcao['transportadora']
                otimizacoes['nova_modalidade'] = pior_opcao['modalidade']
                
                print(f"[DEBUG] 💡 OTIMIZAÇÃO CONSERVADORA removendo {pedido.num_pedido}:")
                print(f"[DEBUG]   - Frete atual: R${frete_atual_kg:.3f}/kg")
                print(f"[DEBUG]   - Novo frete (PIOR): R${novo_frete_kg:.3f}/kg")
                print(f"[DEBUG]   - Redução: R${reducao_rota:.3f}/kg")
                print(f"[DEBUG]   - Tabela mais cara: {pior_opcao['nome_tabela']}")
                
    except Exception as e:
        print(f"[DEBUG] Erro ao calcular otimização para remover {pedido.num_pedido}: {str(e)}")
    
    return otimizacoes if otimizacoes else None

@cotacao_bp.route("/iniciar", methods=["POST"])
@login_required
def iniciar_cotacao():
    """
    Recebe via POST a lista de pedidos selecionados (pedido_ids).
    Redireciona para a tela de cotação, guardando no 'session' 
    ou em outro local a lista de IDs.
    """
    lista_ids_str = request.form.getlist("pedido_ids")
    if not lista_ids_str:
        flash("Nenhum pedido selecionado!", "warning")
        return redirect(url_for("pedidos.lista_pedidos"))

    lista_ids = [int(x) for x in lista_ids_str]

    # Armazena no session para usar nas rotas subsequentes:
    session["cotacao_pedidos"] = lista_ids

    return redirect(url_for("cotacao.tela_cotacao"))

@cotacao_bp.route("/tela", methods=["GET", "POST"])
@login_required
def tela_cotacao():
    """
    Renderiza a tela principal da cotação
    """
    form = CotarFreteForm()
    
    # ✅ LIMPA MODO REDESPACHO quando volta para cotação normal
    if 'redespacho_ativo' in session:
        del session['redespacho_ativo']
        print(f"[DEBUG] 🔄 Modo redespacho desativado - voltou para cotação normal")
    
    # Inicializa as variáveis que serão usadas no template
    pedidos = []
    pedidos_json = []
    pedidos_por_cnpj = {}
    pedidos_por_cnpj_json = {}
    pedidos_mesmo_estado = []
    pedidos_mesmo_estado_json = []
    opcoes_por_cnpj = {}
    resultados = None
    opcoes_transporte = {
        'direta': [],
        'fracionada': {}
    }
    peso_total = 0  # Variável necessária para cálculos no template
    todos_mesmo_uf = False  # Flag para controle no template
    
    # Recupera pedidos da sessão
    lista_ids = session.get("cotacao_pedidos", [])
    if not lista_ids:
        flash("Nenhum pedido na cotação!", "warning")
        return redirect(url_for("pedidos.lista_pedidos"))

    # Carrega os pedidos do banco
    pedidos = Pedido.query.filter(Pedido.id.in_(lista_ids)).all()
    print(f"[DEBUG] Pedidos carregados: {len(pedidos)}")
    
    if not pedidos:
        flash("Nenhum pedido encontrado!", "warning")
        return redirect(url_for("pedidos.lista_pedidos"))
    
    # Calcula totais
    peso_total = sum(p.peso_total or 0 for p in pedidos)
    print(f"[DEBUG] Peso total dos pedidos: {peso_total}kg")
    
    # Verifica se todos são do mesmo UF usando LocalizacaoService
    ufs_normalizados = set()
    for pedido in pedidos:
        # Normaliza localização usando LocalizacaoService
        cidade = LocalizacaoService.buscar_cidade_unificada(
            nome=pedido.nome_cidade,
            uf=pedido.cod_uf,
            rota=getattr(pedido, 'rota', None)
        )
        if cidade:
            ufs_normalizados.add(cidade.uf)
    
    todos_mesmo_uf = len(ufs_normalizados) == 1
    print(f"[DEBUG] UFs encontrados: {ufs_normalizados}")
    print(f"[DEBUG] Todos mesmo UF? {todos_mesmo_uf}")
    
    # Organiza pedidos por CNPJ e cria versões JSON
    for pedido in pedidos:
        # Cria dicionário com dados do pedido
        pedido_dict = {
            'id': pedido.id,
            'num_pedido': pedido.num_pedido,
            'data_pedido': pedido.data_pedido.strftime('%Y-%m-%d') if pedido.data_pedido else None,
            'cnpj_cpf': pedido.cnpj_cpf,
            'raz_social_red': pedido.raz_social_red,
            'nome_cidade': pedido.nome_cidade,
            'cod_uf': pedido.cod_uf,
            'valor_saldo_total': float(pedido.valor_saldo_total) if pedido.valor_saldo_total else 0,
            'pallet_total': float(pedido.pallet_total) if pedido.pallet_total else 0,
            'peso_total': float(pedido.peso_total) if pedido.peso_total else 0,
            'rota': getattr(pedido, 'rota', ''),
            'sub_rota': getattr(pedido, 'sub_rota', '')
        }
        
        # Adiciona ao pedidos_json
        pedidos_json.append(pedido_dict)
        
        # Organiza por CNPJ
        cnpj = pedido.cnpj_cpf
        if cnpj not in pedidos_por_cnpj:
            pedidos_por_cnpj[cnpj] = []
            pedidos_por_cnpj_json[cnpj] = []
        pedidos_por_cnpj[cnpj].append(pedido)  # Mantém o objeto original para cálculos
        pedidos_por_cnpj_json[cnpj].append(pedido_dict)  # Versão serializada para o template

    # Busca outros pedidos do mesmo estado se todos forem do mesmo UF
    if pedidos and todos_mesmo_uf:
        # Pega o UF do primeiro grupo normalizado
        uf_busca = list(ufs_normalizados)[0]
                
        print(f"[DEBUG] Buscando pedidos com UF={uf_busca}")
        pedidos_mesmo_estado = (Pedido.query
                               .filter(
                                   (Pedido.cod_uf == uf_busca) |
                                   ((Pedido.rota == 'RED') & (uf_busca == 'SP'))
                               )
                               .filter(~Pedido.id.in_(lista_ids))
                               .filter(Pedido.status == 'ABERTO')  # ✅ Apenas pedidos abertos
                               .all())
        print(f"[DEBUG] Pedidos do mesmo estado encontrados: {len(pedidos_mesmo_estado)}")
        
        # Serializa pedidos_mesmo_estado
        for p in pedidos_mesmo_estado:
            pedidos_mesmo_estado_json.append({
                'id': p.id,
                'num_pedido': p.num_pedido,
                'data_pedido': p.data_pedido.strftime('%Y-%m-%d') if p.data_pedido else None,
                'cnpj_cpf': p.cnpj_cpf,
                'raz_social_red': p.raz_social_red,
                'nome_cidade': p.nome_cidade,
                'cod_uf': p.cod_uf,
                'valor_saldo_total': float(p.valor_saldo_total) if p.valor_saldo_total else 0,
                'pallet_total': float(p.pallet_total) if p.pallet_total else 0,
                'peso_total': float(p.peso_total) if p.peso_total else 0,
                'rota': getattr(p, 'rota', ''),
                'sub_rota': getattr(p, 'sub_rota', '')
            })

    # Calcula fretes usando o simulador integrado com LocalizacaoService
    if pedidos:
        try:
            print("[DEBUG] Iniciando cálculo de fretes...")
            
            # Normaliza dados dos pedidos usando LocalizacaoService
            for pedido in pedidos:
                LocalizacaoService.normalizar_dados_pedido(pedido)
            
            # Usa a função existente do simulador
            resultados = calcular_frete_por_cnpj(pedidos)
            
            if resultados:
                # Armazena os resultados completos na sessão
                session['resultados'] = resultados
                
                # Inicializa estrutura de opções de transporte
                opcoes_transporte = {
                    'direta': [],
                    'fracionada': {}
                }
                
                # Processa cargas diretas apenas se todos forem do mesmo UF
                if todos_mesmo_uf and 'diretas' in resultados:
                    # Adiciona índice original antes da ordenação
                    for i, opcao in enumerate(resultados['diretas']):
                        if isinstance(opcao, dict):
                            opcao['indice_original'] = i
                            # Calcula valor por kg para ordenação
                            peso_total_calc = sum(p.peso_total or 0 for p in pedidos)
                            opcao['valor_por_kg'] = opcao['valor_liquido'] / peso_total_calc if peso_total_calc > 0 else float('inf')
                    
                    # Ordena por valor/kg mantendo o índice original
                    resultados['diretas'].sort(key=lambda x: x['valor_por_kg'] if isinstance(x, dict) else float('inf'))
                    
                    # Atualiza índice após ordenação
                    for i, opcao in enumerate(resultados['diretas']):
                        if isinstance(opcao, dict):
                            opcao['indice'] = i
                    
                    opcoes_transporte['direta'] = resultados['diretas']

                # Processa cargas fracionadas - IMPLEMENTAÇÃO DA "MELHOR OPÇÃO" (item 2-a)
                if 'fracionadas' in resultados:
                    print("[DEBUG] 🎯 IMPLEMENTANDO MELHOR OPÇÃO PARA CADA CNPJ")
                    
                    # ETAPA 1: Identifica a melhor opção (mais barata) para cada CNPJ
                    melhores_opcoes_por_cnpj = {}
                    
                    for cnpj, opcoes_cnpj in resultados['fracionadas'].items():
                        print(f"[DEBUG] 📊 CNPJ {cnpj}: {len(opcoes_cnpj)} opções disponíveis")
                        
                        melhor_opcao = None
                        melhor_valor_kg = float('inf')
                        
                        # Calcula dados do grupo deste CNPJ
                        pedidos_cnpj = [p for p in pedidos if p.cnpj_cpf == cnpj]
                        peso_grupo = sum(p.peso_total or 0 for p in pedidos_cnpj)
                        
                        # Encontra a opção com menor valor por kg
                        for opcao in opcoes_cnpj:
                            valor_kg = opcao['valor_liquido'] / peso_grupo if peso_grupo > 0 else float('inf')
                            print(f"[DEBUG]   - {opcao['transportadora']}: R${opcao['valor_liquido']:.2f} = R${valor_kg:.2f}/kg")
                            
                            if valor_kg < melhor_valor_kg:
                                melhor_valor_kg = valor_kg
                                melhor_opcao = opcao
                        
                        if melhor_opcao:
                            melhores_opcoes_por_cnpj[cnpj] = melhor_opcao
                            print(f"[DEBUG] ✅ MELHOR OPÇÃO CNPJ {cnpj}: {melhor_opcao['transportadora']} - R${melhor_valor_kg:.2f}/kg")
                    
                    # ETAPA 2: Agrupa as melhores opções por transportadora
                    opcoes_transporte['fracionada'] = {}
                    
                    for cnpj, melhor_opcao in melhores_opcoes_por_cnpj.items():
                        transportadora_id = melhor_opcao['transportadora_id']
                        
                        # Inicializa estrutura da transportadora se não existir
                        if transportadora_id not in opcoes_transporte['fracionada']:
                            opcoes_transporte['fracionada'][transportadora_id] = {
                                'razao_social': melhor_opcao['transportadora'],
                                'cnpjs': []
                            }
                        
                        # Calcula dados do grupo deste CNPJ
                        pedidos_cnpj = [p for p in pedidos if p.cnpj_cpf == cnpj]
                        peso_grupo = sum(p.peso_total or 0 for p in pedidos_cnpj)
                        valor_grupo = sum(p.valor_saldo_total or 0 for p in pedidos_cnpj)
                        pallets_grupo = sum(p.pallet_total or 0 for p in pedidos_cnpj)
                        
                        # Adiciona apenas a melhor opção à lista da transportadora
                        opcao_completa = {
                            'cnpj': cnpj,
                            'razao_social': pedidos_cnpj[0].raz_social_red if pedidos_cnpj else '',
                            'cidade': melhor_opcao.get('cidade', ''),
                            'uf': melhor_opcao.get('uf', ''),
                            'peso_grupo': peso_grupo,
                            'valor_grupo': valor_grupo,
                            'pallets_grupo': pallets_grupo,
                            'valor_total': melhor_opcao['valor_total'],
                            'valor_liquido': melhor_opcao['valor_liquido'],
                            'frete_kg': melhor_opcao['valor_liquido'] / peso_grupo if peso_grupo > 0 else float('inf'),
                            'nome_tabela': melhor_opcao.get('nome_tabela', ''),
                            'modalidade': melhor_opcao.get('modalidade', 'FRETE PESO'),
                            'valor_kg': melhor_opcao.get('valor_kg', 0),
                            'icms': melhor_opcao.get('icms', 0),
                            'percentual_gris': melhor_opcao.get('percentual_gris', 0),
                            'pedagio_por_100kg': melhor_opcao.get('pedagio_por_100kg', 0),
                            'valor_tas': melhor_opcao.get('valor_tas', 0),
                            'percentual_adv': melhor_opcao.get('percentual_adv', 0),
                            'percentual_rca': melhor_opcao.get('percentual_rca', 0),
                            'valor_despacho': melhor_opcao.get('valor_despacho', 0),
                            'valor_cte': melhor_opcao.get('valor_cte', 0),
                            'icms_incluso': melhor_opcao.get('icms_incluso', False),
                            'icms_destino': melhor_opcao.get('icms_destino', 0)
                        }
                        opcoes_transporte['fracionada'][transportadora_id]['cnpjs'].append(opcao_completa)
                    
                    print(f"[DEBUG] 🎯 RESULTADO FINAL: {len(opcoes_transporte['fracionada'])} transportadoras com melhores opções")
                    for transp_id, dados in opcoes_transporte['fracionada'].items():
                        print(f"[DEBUG]   - {dados['razao_social']}: {len(dados['cnpjs'])} CNPJs")
                
                # Prepara TODAS as opções por CNPJ para o modal (item 2-b)
                print("[DEBUG] 🎯 PREPARANDO TODAS AS OPÇÕES PARA O MODAL (ITEM 2-b)")
                opcoes_por_cnpj = {}
                
                if 'fracionadas' in resultados:
                    for cnpj, todas_opcoes in resultados['fracionadas'].items():
                        opcoes_por_cnpj[cnpj] = []
                        
                        # Calcula dados do grupo deste CNPJ
                        pedidos_cnpj = [p for p in pedidos if p.cnpj_cpf == cnpj]
                        peso_grupo = sum(p.peso_total or 0 for p in pedidos_cnpj)
                        valor_grupo = sum(p.valor_saldo_total or 0 for p in pedidos_cnpj)
                        pallets_grupo = sum(p.pallet_total or 0 for p in pedidos_cnpj)
                        
                        print(f"[DEBUG] CNPJ {cnpj}: {len(todas_opcoes)} opções para o modal")
                        
                        # Adiciona TODAS as opções para este CNPJ
                        for opcao in todas_opcoes:
                            opcao_completa = {
                                'cnpj': cnpj,
                                'transportadora_id': opcao.get('transportadora_id'),
                                'transportadora': opcao.get('transportadora'),
                                'nome_tabela': opcao.get('nome_tabela', ''),
                                'modalidade': opcao.get('modalidade', 'FRETE PESO'),
                                'valor_total': opcao.get('valor_total', 0),
                                'valor_liquido': opcao.get('valor_liquido', 0),
                                'frete_kg': opcao.get('valor_liquido', 0) / peso_grupo if peso_grupo > 0 else 0,
                                'peso_grupo': peso_grupo,
                                'valor_grupo': valor_grupo,
                                'pallets_grupo': pallets_grupo,
                                'cidade': opcao.get('cidade', ''),
                                'uf': opcao.get('uf', ''),
                                'razao_social': pedidos_cnpj[0].raz_social_red if pedidos_cnpj else '',
                                'valor_kg': opcao.get('valor_kg', 0),
                                'icms': opcao.get('icms', 0),
                                'percentual_gris': opcao.get('percentual_gris', 0),
                                'pedagio_por_100kg': opcao.get('pedagio_por_100kg', 0),
                                'valor_tas': opcao.get('valor_tas', 0),
                                'percentual_adv': opcao.get('percentual_adv', 0),
                                'percentual_rca': opcao.get('percentual_rca', 0),
                                'valor_despacho': opcao.get('valor_despacho', 0),
                                'valor_cte': opcao.get('valor_cte', 0),
                                'icms_incluso': opcao.get('icms_incluso', False),
                                'icms_destino': opcao.get('icms_destino', 0)
                            }
                            opcoes_por_cnpj[cnpj].append(opcao_completa)
                            print(f"[DEBUG]   - {opcao.get('transportadora')}: R${opcao.get('valor_liquido', 0):.2f}")
                
                print(f"[DEBUG] ✅ MODAL: {len(opcoes_por_cnpj)} CNPJs com todas as opções preparadas")
                for cnpj_debug, opcoes_debug in opcoes_por_cnpj.items():
                    print(f"[DEBUG] FINAL MODAL - CNPJ {cnpj_debug}: {len(opcoes_debug)} opções")
                    for opcao_debug in opcoes_debug:
                        print(f"[DEBUG]   → {opcao_debug.get('transportadora')}: R${opcao_debug.get('valor_liquido', 0):.2f}")
            
        except Exception as e:
            print(f"[DEBUG] Erro ao calcular fretes: {str(e)}")
            flash(f"Erro ao calcular fretes: {str(e)}", "error")
            opcoes_transporte = {
                'direta': [],
                'fracionada': {}
            }

    # 🔧 CORREÇÃO GARANTIDA: Força preparação do opcoes_por_cnpj para o modal
    print(f"[DEBUG] 🔧 VERIFICANDO opcoes_por_cnpj: {len(opcoes_por_cnpj)} CNPJs")
    if not opcoes_por_cnpj and resultados and 'fracionadas' in resultados:
        print("[DEBUG] 🔧 opcoes_por_cnpj estava vazio, criando agora...")
        opcoes_por_cnpj = {}
        
        for cnpj, todas_opcoes in resultados['fracionadas'].items():
            if isinstance(todas_opcoes, list) and todas_opcoes:
                opcoes_por_cnpj[cnpj] = []
                
                # Calcula dados do grupo deste CNPJ
                pedidos_cnpj = [p for p in pedidos if p.cnpj_cpf == cnpj]
                peso_grupo = sum(p.peso_total or 0 for p in pedidos_cnpj)
                valor_grupo = sum(p.valor_saldo_total or 0 for p in pedidos_cnpj)
                
                print(f"[DEBUG] 🔧 CORREÇÃO - CNPJ {cnpj}: {len(todas_opcoes)} opções")
                
                for opcao in todas_opcoes:
                    opcao_completa = {
                        'cnpj': cnpj,
                        'transportadora_id': opcao.get('transportadora_id'),
                        'transportadora': opcao.get('transportadora'),
                        'nome_tabela': opcao.get('nome_tabela', ''),
                        'modalidade': opcao.get('modalidade', 'FRETE PESO'),
                        'valor_total': opcao.get('valor_total', 0),
                        'valor_liquido': opcao.get('valor_liquido', 0),
                        'frete_kg': opcao.get('valor_liquido', 0) / peso_grupo if peso_grupo > 0 else 0,
                        'peso_grupo': peso_grupo,
                        'valor_grupo': valor_grupo,
                        'pallets_grupo': sum(p.pallet_total or 0 for p in pedidos_cnpj),
                        'cidade': opcao.get('cidade', ''),
                        'uf': opcao.get('uf', ''),
                        'razao_social': pedidos_cnpj[0].raz_social_red if pedidos_cnpj else ''
                    }
                    opcoes_por_cnpj[cnpj].append(opcao_completa)
                    print(f"[DEBUG] 🔧 → {opcao.get('transportadora')}: R${opcao.get('valor_liquido', 0):.2f}")
        
        print(f"[DEBUG] 🔧 CORREÇÃO FINAL: {len(opcoes_por_cnpj)} CNPJs preparados")

    # Debug final antes de enviar para o template
    print(f"[DEBUG] 🎯 ENVIANDO PARA TEMPLATE: opcoes_por_cnpj com {len(opcoes_por_cnpj)} CNPJs")
    for cnpj_final, opcoes_final in opcoes_por_cnpj.items():
        print(f"[DEBUG] 🎯 TEMPLATE - CNPJ {cnpj_final}: {len(opcoes_final)} opções")

    return render_template(
        "cotacao/cotacao.html",
        form=form,
        pedidos=pedidos,
        pedidos_selecionados=pedidos_json,  # Usa a versão JSON dos pedidos
        pedidos_json=pedidos_json,
        pedidos_mesmo_estado=pedidos_mesmo_estado,
        pedidos_mesmo_estado_json=pedidos_mesmo_estado_json,
        resultados=resultados,
        opcoes_transporte=opcoes_transporte,
        pedidos_por_cnpj=pedidos_por_cnpj_json,
        pedidos_por_cnpj_json=pedidos_por_cnpj_json,
        opcoes_por_cnpj=opcoes_por_cnpj,
        peso_total=peso_total,
        todos_mesmo_uf=todos_mesmo_uf
    )

@cotacao_bp.route("/excluir_pedido", methods=["POST"])
@login_required
def excluir_pedido():
    """
    Exemplo: remove o pedido da lista de IDs no 'session' e redireciona
    """
    pedido_id = request.form.get("pedido_id")
    if not pedido_id:
        flash("Pedido não informado", "warning")
        return redirect(url_for("cotacao.tela_cotacao"))

    lista_ids = session.get("cotacao_pedidos", [])
    try:
        pedido_id = int(pedido_id)
        if pedido_id in lista_ids:
            lista_ids.remove(pedido_id)
            session["cotacao_pedidos"] = lista_ids
    except ValueError:
        pass

    return redirect(url_for("cotacao.tela_cotacao"))

@cotacao_bp.route("/incluir_pedido", methods=["POST"])
@login_required
def incluir_pedido():
    """
    Exemplo: adiciona pedido na lista de IDs e redireciona
    """
    pedido_id = request.form.get("pedido_id")
    if not pedido_id:
        flash("Pedido não informado", "warning")
        return redirect(url_for("cotacao.tela_cotacao"))

    lista_ids = session.get("cotacao_pedidos", [])
    try:
        pedido_id_int = int(pedido_id)
        if pedido_id_int not in lista_ids:
            lista_ids.append(pedido_id_int)
            session["cotacao_pedidos"] = lista_ids
    except ValueError:
        pass

    return redirect(url_for("cotacao.tela_cotacao"))

def safe_float(value, default=0.0):
    """
    Converte um valor para float de forma segura.
    Se o valor for None ou não puder ser convertido, retorna o valor padrão.
    """
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

@cotacao_bp.route("/fechar_frete", methods=["POST"])
@login_required
def fechar_frete():
    """
    Fechar frete - versão corrigida com dados da tabela nos locais corretos
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Dados inválidos'}), 400

        tipo = data.get('tipo')
        transportadora_id = data.get('transportadora_id')
        pedidos_data = data.get('pedidos', [])
        indice_original = data.get('indice_original', 0)
        
        print(f"[DEBUG] === CORREÇÃO FECHAR FRETE ===")
        print(f"[DEBUG] Tipo: {tipo}")
        print(f"[DEBUG] Transportadora: {transportadora_id}")
        print(f"[DEBUG] Índice original: {indice_original}")
        print(f"[DEBUG] Redespacho: {data.get('redespacho', False)}")
        
        if not tipo or not transportadora_id or not pedidos_data:
            return jsonify({'success': False, 'message': 'Dados incompletos'}), 400

        transportadora = Transportadora.query.get(transportadora_id)
        if not transportadora:
            return jsonify({'success': False, 'message': 'Transportadora não encontrada'}), 404

        # Recupera dados da tabela dos resultados da sessão
        resultados = session.get('resultados')
        dados_tabela = None
        opcao_escolhida = None
        
        print(f"[DEBUG] === BUSCANDO OPÇÃO PELOS DADOS DA SESSÃO ===")
        
        if resultados and 'diretas' in resultados:
            # Busca pelo indice_original
            for opcao in resultados['diretas']:
                if isinstance(opcao, dict) and opcao.get('indice_original') == int(indice_original):
                    opcao_escolhida = opcao
                    break
        
        if not opcao_escolhida:
            return jsonify({'success': False, 'message': f'Opção com índice {indice_original} não encontrada'}), 400

        print(f"[DEBUG] ✅ Opção encontrada: {opcao_escolhida.get('transportadora')} - {opcao_escolhida.get('nome_tabela')}")

        # ✅ CORREÇÃO REDESPACHO: Determina UF de destino corretamente
        redespacho_ativo = data.get('redespacho', False)
        if redespacho_ativo:
            # Para redespacho, sempre SP/Guarulhos
            uf_destino = 'SP'
            print(f"[DEBUG] 🔄 REDESPACHO: UF destino = SP (Guarulhos)")
        else:
            # Para cotação normal, usa UF original dos pedidos
            uf_destino = None
            for pedido_data in pedidos_data:
                pedido = Pedido.query.get(pedido_data.get('id'))
                if pedido:
                    uf_destino = 'SP' if pedido.rota and pedido.rota.upper().strip() == 'RED' else pedido.cod_uf
                    break
            print(f"[DEBUG] 📍 COTAÇÃO NORMAL: UF destino = {uf_destino}")

        # Busca a tabela original no banco (opcional - para validação)
        nome_tabela = opcao_escolhida.get('nome_tabela')
        modalidade_escolhida = opcao_escolhida.get('modalidade')
        
        # Imports já estão no topo do arquivo
        
        tabela = TabelaFrete.query.filter(
            TabelaFrete.transportadora_id == transportadora_id,
            func.upper(func.trim(TabelaFrete.nome_tabela)) == func.upper(func.trim(nome_tabela)),
            TabelaFrete.uf_origem == 'SP',
            TabelaFrete.uf_destino == uf_destino,
            TabelaFrete.tipo_carga == tipo,
            TabelaFrete.modalidade == modalidade_escolhida
        ).first()
        
        print(f"[DEBUG] Tabela no banco: {'✅ Encontrada' if tabela else '❌ Não encontrada'}")

        # ✅ BUSCA ICMS CORRETO
        # Import já está no topo do arquivo
        icms_destino = 0
        
        if redespacho_ativo:
            # Para redespacho, sempre busca ICMS de Guarulhos/SP
            cidade_destino = Cidade.query.filter_by(nome='GUARULHOS', uf='SP').first()
            if not cidade_destino:
                cidade_destino = Cidade.query.filter_by(nome='Guarulhos', uf='SP').first()
            if cidade_destino:
                icms_destino = cidade_destino.icms or 0
                print(f"[DEBUG] ✅ ICMS Guarulhos/SP: {icms_destino}%")
        else:
            # Para cotação normal, busca ICMS da cidade original do primeiro pedido
            for pedido_data in pedidos_data:
                pedido = Pedido.query.get(pedido_data.get('id'))
                if pedido:
                    if hasattr(pedido, 'codigo_ibge') and pedido.codigo_ibge:
                        cidade_destino = Cidade.query.filter_by(codigo_ibge=pedido.codigo_ibge).first()
                    else:
                        cidade_destino = Cidade.query.filter_by(
                            nome=pedido.cidade_normalizada,
                            uf=uf_destino
                        ).first()
                    if cidade_destino:
                        icms_destino = cidade_destino.icms or 0
                        print(f"[DEBUG] ✅ ICMS {cidade_destino.nome}/{uf_destino}: {icms_destino}%")
                        break

        # Prepara dados da tabela usando sempre os dados da sessão (COM TODOS OS VALORES)
        dados_tabela = {
            'modalidade': opcao_escolhida.get('modalidade'),
            'nome_tabela': opcao_escolhida.get('nome_tabela'),
            'valor_kg': opcao_escolhida.get('valor_kg', 0),
            'percentual_valor': opcao_escolhida.get('percentual_valor', 0),
            'frete_minimo_valor': opcao_escolhida.get('frete_minimo_valor', 0),
            'frete_minimo_peso': opcao_escolhida.get('frete_minimo_peso', 0),
            'icms': icms_destino,
            'percentual_gris': opcao_escolhida.get('percentual_gris', 0),
            'pedagio_por_100kg': opcao_escolhida.get('pedagio_por_100kg', 0),
            'valor_tas': opcao_escolhida.get('valor_tas', 0),
            'percentual_adv': opcao_escolhida.get('percentual_adv', 0),
            'percentual_rca': opcao_escolhida.get('percentual_rca', 0),
            'valor_despacho': opcao_escolhida.get('valor_despacho', 0),
            'valor_cte': opcao_escolhida.get('valor_cte', 0),
            'icms_incluso': opcao_escolhida.get('icms_incluso', False),
            'icms_destino': icms_destino
        }
        
        print(f"[DEBUG] ✅ DADOS DA TABELA COMPLETOS PREPARADOS:")
        print(f"[DEBUG]   - Nome tabela: {dados_tabela.get('nome_tabela')}")
        print(f"[DEBUG]   - Modalidade: {dados_tabela.get('modalidade')}")
        print(f"[DEBUG]   - Valor/kg: {dados_tabela.get('valor_kg')}")
        print(f"[DEBUG]   - Percentual valor: {dados_tabela.get('percentual_valor')}")
        print(f"[DEBUG]   - Frete mín peso: {dados_tabela.get('frete_minimo_peso')}")
        print(f"[DEBUG]   - Frete mín valor: {dados_tabela.get('frete_minimo_valor')}")
        print(f"[DEBUG]   - ICMS destino: {dados_tabela.get('icms_destino')}%")
        
        # Se encontrou tabela no banco, usa alguns dados dela
        if tabela:
            dados_tabela.update({
                'valor_kg': tabela.valor_kg or dados_tabela['valor_kg'],
                'percentual_valor': tabela.percentual_valor or dados_tabela['percentual_valor'],
                'frete_minimo_valor': tabela.frete_minimo_valor or dados_tabela['frete_minimo_valor'],
                'frete_minimo_peso': tabela.frete_minimo_peso or dados_tabela['frete_minimo_peso'],
                'percentual_gris': tabela.percentual_gris or dados_tabela['percentual_gris'],
                'pedagio_por_100kg': tabela.pedagio_por_100kg or dados_tabela['pedagio_por_100kg'],
                'valor_tas': tabela.valor_tas or dados_tabela['valor_tas'],
                'percentual_adv': tabela.percentual_adv or dados_tabela['percentual_adv'],
                'percentual_rca': tabela.percentual_rca or dados_tabela['percentual_rca'],
                'valor_despacho': tabela.valor_despacho or dados_tabela['valor_despacho'],
                'valor_cte': tabela.valor_cte or dados_tabela['valor_cte'],
                'icms_incluso': tabela.icms_incluso
            })
            print(f"[DEBUG] ✅ Dados complementados com tabela do banco")

        print(f"[DEBUG] Dados da tabela finais: {dados_tabela}")

        # Calcula totais das mercadorias
        valor_mercadorias = sum(safe_float(p.get('valor')) for p in pedidos_data)
        peso_total = sum(safe_float(p.get('peso')) for p in pedidos_data)

        # ✅ USA VALORES CORRETOS DA SESSÃO
        valor_frete_bruto = safe_float(opcao_escolhida.get('valor_total', 0))
        valor_frete_liquido = safe_float(opcao_escolhida.get('valor_liquido', 0))
        frete_por_kg = valor_frete_liquido / peso_total if peso_total > 0 else 0
        
        print(f"[DEBUG] ✅ Valores do frete (da sessão):")
        print(f"[DEBUG]   - Frete bruto: R${valor_frete_bruto:.2f}")
        print(f"[DEBUG]   - Frete líquido: R${valor_frete_liquido:.2f}")
        print(f"[DEBUG]   - Frete/kg: R${frete_por_kg:.2f}")

        # ✅ CRIA COTAÇÃO
        cotacao = Cotacao(
            usuario_id=current_user.id,
            transportadora_id=transportadora_id,
            data_fechamento=datetime.now(),
            status='Fechada',
            tipo_carga=tipo,
            valor_total=valor_mercadorias,
            peso_total=peso_total
        )
        db.session.add(cotacao)
        db.session.flush()  # ✅ CORREÇÃO CRÍTICA: Força geração do ID da cotação

        # Atualiza pedidos COM ID DA COTAÇÃO VÁLIDO
        for pedido_data in pedidos_data:
            pedido = Pedido.query.get(pedido_data.get('id'))
            if pedido:
                pedido.cotacao_id = cotacao.id
                pedido.transportadora = transportadora.razao_social
                pedido.nf_cd = False  # ✅ NOVO: Reseta flag NF no CD ao criar nova cotação
                # ✅ Status será atualizado automaticamente pela property status_calculado

        # ✅ CRIA EMBARQUE
        embarque = Embarque(
            transportadora_id=transportadora_id,
            status='ativo',
            numero=obter_proximo_numero_embarque(),
            tipo_cotacao='Automatica',
            tipo_carga=tipo,
            valor_total=valor_mercadorias,
            peso_total=peso_total,
            criado_em=datetime.now(),
            criado_por=current_user.nome,
            cotacao_id=cotacao.id,
            transportadora_optante=transportadora.optante
        )
        
        # ✅ CORREÇÃO PRINCIPAL: SALVA DADOS DA TABELA NO LOCAL CORRETO
        if tipo == 'DIRETA':
            # ✅ CARGA DIRETA: Dados da tabela vão para o EMBARQUE
            embarque.modalidade = dados_tabela.get('modalidade')
            embarque.tabela_nome_tabela = dados_tabela.get('nome_tabela')
            embarque.tabela_valor_kg = dados_tabela.get('valor_kg')
            embarque.tabela_percentual_valor = dados_tabela.get('percentual_valor')
            embarque.tabela_frete_minimo_valor = dados_tabela.get('frete_minimo_valor')
            embarque.tabela_frete_minimo_peso = dados_tabela.get('frete_minimo_peso')
            embarque.tabela_icms = dados_tabela.get('icms')
            embarque.tabela_percentual_gris = dados_tabela.get('percentual_gris')
            embarque.tabela_pedagio_por_100kg = dados_tabela.get('pedagio_por_100kg')
            embarque.tabela_valor_tas = dados_tabela.get('valor_tas')
            embarque.tabela_percentual_adv = dados_tabela.get('percentual_adv')
            embarque.tabela_percentual_rca = dados_tabela.get('percentual_rca')
            embarque.tabela_valor_despacho = dados_tabela.get('valor_despacho')
            embarque.tabela_valor_cte = dados_tabela.get('valor_cte')
            embarque.tabela_icms_incluso = dados_tabela.get('icms_incluso', False)
            embarque.icms_destino = dados_tabela.get('icms_destino')
            
            print(f"[DEBUG] ✅ CARGA DIRETA: Dados da tabela salvos no EMBARQUE")
        
        db.session.add(embarque)
        db.session.flush()  # Para obter o ID do embarque

        # Cria EmbarqueItems
        for pedido_data in pedidos_data:
            pedido = Pedido.query.get(pedido_data.get('id'))
            if not pedido:
                continue

            uf_correto = 'SP' if pedido.rota and pedido.rota.upper().strip() == 'RED' else pedido.cod_uf
            
            cidade_obj = LocalizacaoService.buscar_cidade_unificada(
                nome=pedido.nome_cidade,
                uf=pedido.cod_uf,
                rota=getattr(pedido, 'rota', None)
            )
            cidade_formatada = cidade_obj.nome if cidade_obj else pedido.nome_cidade
            protocolo_formatado = formatar_protocolo(pedido.protocolo)
            data_formatada = formatar_data_brasileira(pedido.agendamento)
            
            item = EmbarqueItem(
                embarque_id=embarque.id,
                separacao_lote_id=pedido.separacao_lote_id,  # ✅ CORRIGE: copia separacao_lote_id do pedido
                cnpj_cliente=pedido_data.get('cnpj'),
                cliente=pedido.raz_social_red,
                pedido=pedido.num_pedido,
                peso=pedido.peso_total,
                valor=pedido.valor_saldo_total,
                uf_destino=uf_correto,
                cidade_destino=cidade_formatada,
                volumes=None,  # ✅ ALTERADO: Deixa volumes em branco também na cotação normal
                protocolo_agendamento=protocolo_formatado,
                data_agenda=data_formatada
            )
            
            
            # ✅ CORREÇÃO: CARGA FRACIONADA - Dados da tabela vão para os EMBARQUE_ITENS
            if tipo == 'FRACIONADA':
                item.modalidade = dados_tabela.get('modalidade')
                item.tabela_nome_tabela = dados_tabela.get('nome_tabela')
                item.tabela_valor_kg = dados_tabela.get('valor_kg')
                item.tabela_percentual_valor = dados_tabela.get('percentual_valor')
                item.tabela_frete_minimo_valor = dados_tabela.get('frete_minimo_valor')
                item.tabela_frete_minimo_peso = dados_tabela.get('frete_minimo_peso')
                item.tabela_icms = dados_tabela.get('icms')
                item.tabela_percentual_gris = dados_tabela.get('percentual_gris')
                item.tabela_pedagio_por_100kg = dados_tabela.get('pedagio_por_100kg')
                item.tabela_valor_tas = dados_tabela.get('valor_tas')
                item.tabela_percentual_adv = dados_tabela.get('percentual_adv')
                item.tabela_percentual_rca = dados_tabela.get('percentual_rca')
                item.tabela_valor_despacho = dados_tabela.get('valor_despacho')
                item.tabela_valor_cte = dados_tabela.get('valor_cte')
                item.tabela_icms_incluso = dados_tabela.get('icms_incluso', False)
                item.icms_destino = dados_tabela.get('icms_destino')
                
                print(f"[DEBUG] ✅ CARGA FRACIONADA: Dados da tabela salvos no EMBARQUE_ITEM {pedido.num_pedido}")
                print(f"[DEBUG]   📋 Nome tabela: {item.tabela_nome_tabela}")
                print(f"[DEBUG]   📋 Modalidade: {item.modalidade}")
                print(f"[DEBUG]   📋 Valor/kg: R${item.tabela_valor_kg}")
                print(f"[DEBUG]   📋 ICMS destino: {item.icms_destino}%")
            
            db.session.add(item)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Cotação e embarque criados com sucesso',
            'redirect_url': url_for('cotacao.resumo_frete', cotacao_id=cotacao.id)
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro ao criar embarque: {str(e)}'
        }), 500

@cotacao_bp.route("/fechar_frete_grupo", methods=["POST"])
@login_required
def fechar_frete_grupo():
    """
    Fechar fretes por grupo - versão corrigida com dados da tabela nos locais corretos
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Dados inválidos'}), 400
        
        tipo = data.get('tipo', 'FRACIONADA')
        transportadora_id = data.get('transportadora_id')
        cnpjs = data.get('cnpjs', [])
        
        if not cnpjs and 'pedidos' in data:
            pedidos_data = data.get('pedidos', [])
            cnpjs = list(set(p.get('cnpj') for p in pedidos_data if p.get('cnpj')))

        if not cnpjs:
            lista_ids = session.get("cotacao_pedidos", [])
            if lista_ids:
                pedidos_sessao = Pedido.query.filter(Pedido.id.in_(lista_ids)).all()
                cnpjs = list(set(p.cnpj_cpf for p in pedidos_sessao))

        if not transportadora_id or not cnpjs:
            return jsonify({'success': False, 'message': 'Dados incompletos'}), 400

        transportadora = Transportadora.query.get(transportadora_id)
        if not transportadora:
            return jsonify({'success': False, 'message': 'Transportadora não encontrada'}), 404

        # Busca todos os pedidos dos CNPJs
        todos_pedidos = []
        for cnpj in cnpjs:
            lista_ids = session.get("cotacao_pedidos", [])
            pedidos_cnpj = Pedido.query.filter(
                Pedido.cnpj_cpf == cnpj,
                Pedido.id.in_(lista_ids)
            ).all()
            todos_pedidos.extend(pedidos_cnpj)

        if not todos_pedidos:
            return jsonify({'success': False, 'message': 'Nenhum pedido encontrado'}), 400

        # Calcula totais
        valor_total = sum(p.valor_saldo_total or 0 for p in todos_pedidos)
        peso_total = sum(p.peso_total or 0 for p in todos_pedidos)

        # Cria cotação
        cotacao = Cotacao(
            usuario_id=current_user.id,
            transportadora_id=transportadora_id,
            data_fechamento=datetime.now(),
            status='Fechada',
            tipo_carga=tipo,
            valor_total=valor_total,
            peso_total=peso_total
        )
        db.session.add(cotacao)
        db.session.flush()  # ✅ CORREÇÃO CRÍTICA: Força geração do ID da cotação

        # Atualiza todos os pedidos com a cotação
        for pedido in todos_pedidos:
            pedido.cotacao_id = cotacao.id
            pedido.transportadora = transportadora.razao_social
            pedido.nf_cd = False  # ✅ NOVO: Reseta flag NF no CD ao criar nova cotação
            # Status será atualizado automaticamente pelo trigger

        # ✅ BUSCA DADOS DA TABELA PARA GRUPO
        resultados = session.get('resultados', {})
        dados_tabela_por_cnpj = {}
        
        # Para cada CNPJ, busca os dados da melhor opção
        if 'fracionadas' in resultados:
            for cnpj in cnpjs:
                if cnpj in resultados['fracionadas']:
                    opcoes_cnpj = resultados['fracionadas'][cnpj]
                    if opcoes_cnpj and len(opcoes_cnpj) > 0:
                        # Busca a opção da transportadora escolhida
                        melhor_opcao = None
                        for opcao in opcoes_cnpj:
                            if opcao.get('transportadora_id') == transportadora_id:
                                melhor_opcao = opcao
                                break
                        
                        # Se não encontrou, usa a primeira opção
                        if not melhor_opcao and opcoes_cnpj:
                            melhor_opcao = opcoes_cnpj[0]
                        
                        if melhor_opcao:
                            dados_tabela_por_cnpj[cnpj] = {
                                'modalidade': melhor_opcao.get('modalidade', 'FRETE PESO'),
                                'nome_tabela': melhor_opcao.get('nome_tabela', ''),
                                'valor_kg': melhor_opcao.get('valor_kg', 0),
                                'percentual_valor': melhor_opcao.get('percentual_valor', 0),
                                'frete_minimo_valor': melhor_opcao.get('frete_minimo_valor', 0),
                                'frete_minimo_peso': melhor_opcao.get('frete_minimo_peso', 0),
                                'percentual_gris': melhor_opcao.get('percentual_gris', 0),
                                'pedagio_por_100kg': melhor_opcao.get('pedagio_por_100kg', 0),
                                'valor_tas': melhor_opcao.get('valor_tas', 0),
                                'percentual_adv': melhor_opcao.get('percentual_adv', 0),
                                'percentual_rca': melhor_opcao.get('percentual_rca', 0),
                                'valor_despacho': melhor_opcao.get('valor_despacho', 0),
                                'valor_cte': melhor_opcao.get('valor_cte', 0),
                                'icms_destino': melhor_opcao.get('icms_destino', 0),
                                'icms_incluso': melhor_opcao.get('icms_incluso', False)
                            }
                            print(f"[DEBUG] Dados da tabela para CNPJ {cnpj}: {dados_tabela_por_cnpj[cnpj]}")
        
        # Cria embarque
        embarque = Embarque(
            transportadora_id=transportadora_id,
            status='ativo',
            numero=obter_proximo_numero_embarque(),
            tipo_cotacao='Automatica',
            tipo_carga=tipo,
            valor_total=valor_total,
            peso_total=peso_total,
            criado_em=datetime.now(),
            criado_por=current_user.nome,
            cotacao_id=cotacao.id,
            transportadora_optante=transportadora.optante
        )
        
        # ✅ CORREÇÃO: NÃO SALVA DADOS DA TABELA NO EMBARQUE PARA CARGAS FRACIONADAS
        print(f"[DEBUG] ✅ CARGA FRACIONADA GRUPO: Dados da tabela irão para os EMBARQUE_ITENS")
        
        db.session.add(embarque)
        db.session.flush()

        # Cria EmbarqueItems
        for pedido in todos_pedidos:
            uf_correto = 'SP' if pedido.rota and pedido.rota.upper().strip() == 'RED' else pedido.cod_uf
            
            cidade_obj = LocalizacaoService.buscar_cidade_unificada(
                nome=pedido.nome_cidade,
                uf=pedido.cod_uf,
                rota=getattr(pedido, 'rota', None)
            )
            cidade_formatada = cidade_obj.nome if cidade_obj else pedido.nome_cidade
            
            item = EmbarqueItem(
                embarque_id=embarque.id,
                separacao_lote_id=pedido.separacao_lote_id,  # ✅ CORRIGE: copia separacao_lote_id do pedido
                cnpj_cliente=pedido.cnpj_cpf,
                cliente=pedido.raz_social_red,
                pedido=pedido.num_pedido,
                peso=pedido.peso_total,
                valor=pedido.valor_saldo_total,
                uf_destino=uf_correto,
                cidade_destino=cidade_formatada,
                volumes=None,  # ✅ ALTERADO: Deixa volumes em branco também na cotação por grupo
                protocolo_agendamento=formatar_protocolo(pedido.protocolo),
                data_agenda=formatar_data_brasileira(pedido.agendamento)
            )
            
            # ✅ CORREÇÃO: PARA CARGAS FRACIONADAS, SALVA DADOS DA TABELA NO EMBARQUE_ITEM
            if tipo == 'FRACIONADA' and pedido.cnpj_cpf in dados_tabela_por_cnpj:
                dados_tabela = dados_tabela_por_cnpj[pedido.cnpj_cpf]
                
                item.modalidade = dados_tabela.get('modalidade')
                item.tabela_nome_tabela = dados_tabela.get('nome_tabela')
                item.tabela_valor_kg = dados_tabela.get('valor_kg')
                item.tabela_percentual_valor = dados_tabela.get('percentual_valor')
                item.tabela_frete_minimo_valor = dados_tabela.get('frete_minimo_valor')
                item.tabela_frete_minimo_peso = dados_tabela.get('frete_minimo_peso')
                item.tabela_percentual_gris = dados_tabela.get('percentual_gris')
                item.tabela_pedagio_por_100kg = dados_tabela.get('pedagio_por_100kg')
                item.tabela_valor_tas = dados_tabela.get('valor_tas')
                item.tabela_percentual_adv = dados_tabela.get('percentual_adv')
                item.tabela_percentual_rca = dados_tabela.get('percentual_rca')
                item.tabela_valor_despacho = dados_tabela.get('valor_despacho')
                item.tabela_valor_cte = dados_tabela.get('valor_cte')
                item.icms_destino = dados_tabela.get('icms_destino')
                item.tabela_icms_incluso = dados_tabela.get('icms_incluso', False)
                
                print(f"[DEBUG] ✅ CARGA FRACIONADA: Dados COMPLETOS da tabela salvos no EMBARQUE_ITEM {pedido.num_pedido} (CNPJ: {pedido.cnpj_cpf})")
            
            db.session.add(item)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Cotação e embarque criados com sucesso',
            'redirect_url': url_for('cotacao.resumo_frete', cotacao_id=cotacao.id)
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro ao criar embarque: {str(e)}'
        }), 500

def obter_proximo_numero_embarque():
    """Obtém o próximo número de embarque"""
    try:
        ultimo_embarque = Embarque.query.order_by(Embarque.id.desc()).first()
        if ultimo_embarque:
            return ultimo_embarque.numero + 1
        return 1
    except:
        return 1

@cotacao_bp.route("/otimizar")
@login_required
def otimizar():
    """
    Tela do otimizador de fretes - analisa opções de otimização real
    """
    try:
        # Recupera parâmetros da URL
        opcao_id = request.args.get('opcao_id', type=int)
        tipo = request.args.get('tipo', 'direta')
        indice = request.args.get('indice', type=int)
        
        # Recupera pedidos da sessão
        lista_ids = session.get("cotacao_pedidos", [])
        if not lista_ids:
            flash("Nenhum pedido na cotação!", "warning")
            return redirect(url_for("cotacao.tela_cotacao"))

        # Carrega os pedidos do banco
        pedidos = Pedido.query.filter(Pedido.id.in_(lista_ids)).all()
        if not pedidos:
            flash("Nenhum pedido encontrado!", "warning")
            return redirect(url_for("cotacao.tela_cotacao"))

        # Recupera resultados da sessão
        resultados = session.get('resultados')
        if not resultados:
            flash("Dados de cotação não encontrados. Refaça a cotação.", "warning")
            return redirect(url_for("cotacao.tela_cotacao"))

        # Busca a opção específica selecionada baseado no índice
        opcao_atual = None
        
        # ✅ CORREÇÃO: Procura nos resultados usando o índice fornecido
        if 'diretas' in resultados:
            for opcao in resultados['diretas']:
                if opcao.get('indice_original') == indice:
                    opcao_atual = opcao
                    break
        
        # Se não encontrou por índice, tenta por opcao_id (fallback)
        if not opcao_atual and tipo == 'direta' and 'diretas' in resultados:
            if opcao_id is not None and 0 <= opcao_id < len(resultados['diretas']):
                opcao_atual = resultados['diretas'][opcao_id]
        
        if not opcao_atual:
            flash("Opção de frete não encontrada!", "warning")
            return redirect(url_for("cotacao.tela_cotacao"))

        print(f"[DEBUG] Opção atual encontrada: {opcao_atual.get('transportadora', 'N/A')}")

        # ✅ LÓGICA REDESPACHO: Verifica se está em modo redespacho
        redespacho_ativo = session.get('redespacho_ativo', False)
        
        # ✅ CORREÇÃO: Se veio da cotação normal (não do redespacho), limpa a flag
        referer = request.headers.get('Referer', '')
        if '/redespachar' not in referer and redespacho_ativo:
            # Usuário acessou otimizador da cotação normal, não do redespacho
            session.pop('redespacho_ativo', None)
            redespacho_ativo = False
            print(f"[DEBUG] 🔄 Modo redespacho desativado - otimizador acessado da cotação normal")
        
        if redespacho_ativo:
            # 🔄 MODO REDESPACHO: Busca pedidos de SP (pois a carga estará em Guarulhos)
            uf_principal = 'SP'
            print(f"[DEBUG] 🔄 MODO REDESPACHO ATIVO: Buscando pedidos de SP para otimização")
            
            # ✅ NOVO: Verifica sub_rotas dos pedidos atuais
            sub_rotas_atuais = set()
            for p in pedidos:
                if p.sub_rota:
                    sub_rotas_atuais.add(p.sub_rota)
            
            query_redespacho = Pedido.query.filter(
                (Pedido.cod_uf == 'SP') |
                (Pedido.rota == 'RED')  # RED também vai para SP/Guarulhos
            ).filter(~Pedido.id.in_(lista_ids)).filter(
                Pedido.status == 'ABERTO'
            ).filter(
                Pedido.rota != 'FOB'  # ✅ NOVO: Exclui FOB
            )
            
            # ✅ NOVO: Filtra por sub_rota se todos os pedidos atuais têm a mesma
            if len(sub_rotas_atuais) == 1:
                sub_rota_filtro = list(sub_rotas_atuais)[0]
                query_redespacho = query_redespacho.filter(Pedido.sub_rota == sub_rota_filtro)
                print(f"[DEBUG] ✅ Filtro por sub_rota: {sub_rota_filtro}")
            
            pedidos_mesmo_uf = query_redespacho.limit(200).all()
        else:
            # 📍 MODO NORMAL: Busca pedidos do mesmo UF original
            uf_principal = None
            pedidos_ufs = set()
            
            # ✅ NOVO: Verifica sub_rotas dos pedidos atuais
            sub_rotas_atuais = set()
            for pedido in pedidos:
                # Aplica regras de UF e cidade
                uf_efetivo = 'SP' if pedido.rota and pedido.rota.upper().strip() == 'RED' else pedido.cod_uf
                pedidos_ufs.add(uf_efetivo)
                
                # Coleta sub_rotas
                if pedido.sub_rota:
                    sub_rotas_atuais.add(pedido.sub_rota)
            
            # Usa o UF mais comum ou o primeiro encontrado
            uf_principal = pedidos_ufs.pop() if pedidos_ufs else 'SP'
            print(f"[DEBUG] 📍 MODO NORMAL: UF principal identificado: {uf_principal}")

            pedidos_mesmo_uf = []
            if uf_principal:
                query_normal = Pedido.query.filter(
                    (Pedido.cod_uf == uf_principal) |
                    ((Pedido.rota == 'RED') & (uf_principal == 'SP'))
                ).filter(~Pedido.id.in_(lista_ids)).filter(
                    Pedido.status == 'ABERTO'
                ).filter(
                    Pedido.rota != 'FOB'  # ✅ NOVO: Exclui FOB
                )
                
                # ✅ NOVO: Filtra por sub_rota se todos os pedidos atuais têm a mesma
                if len(sub_rotas_atuais) == 1:
                    sub_rota_filtro = list(sub_rotas_atuais)[0]
                    query_normal = query_normal.filter(Pedido.sub_rota == sub_rota_filtro)
                    print(f"[DEBUG] ✅ Filtro por sub_rota: {sub_rota_filtro}")
                
                pedidos_mesmo_uf = query_normal.limit(200).all()

        # ✅ PREPARAÇÃO DE DADOS CORRETOS
        transportadora = opcao_atual.get('transportadora', 'N/A')
        modalidade = opcao_atual.get('modalidade', 'N/A')
        peso_total = sum(p.peso_total or 0 for p in pedidos)
        valor_liquido = opcao_atual.get('valor_liquido', 0)
        frete_atual_kg = valor_liquido / peso_total if peso_total > 0 else 0
        
        print(f"[DEBUG] Dados básicos:")
        print(f"[DEBUG] - Transportadora: {transportadora}")
        print(f"[DEBUG] - Modalidade: {modalidade}")
        print(f"[DEBUG] - Peso total: {peso_total}kg")
        print(f"[DEBUG] - Valor líquido: R${valor_liquido}")
        print(f"[DEBUG] - Frete atual/kg: R${frete_atual_kg:.2f}")

        # ✅ CARREGA VEÍCULOS DISPONÍVEIS
        # Import já está no topo do arquivo
        veiculos_query = Veiculo.query.all()
        veiculos = {normalizar_nome_veiculo(v.nome): v.peso_maximo for v in veiculos_query}
        
        # ✅ CONVERTE PEDIDOS PARA REDESPACHO SE NECESSÁRIO
        pedidos_para_calculo = pedidos
        if redespacho_ativo:
            print(f"[DEBUG] 🔄 CONVERTENDO PEDIDOS PARA GUARULHOS/SP NOS CÁLCULOS DE OTIMIZAÇÃO")
            pedidos_para_calculo = []
            
            for pedido_original in pedidos:
                # Cria uma cópia do pedido com dados alterados para SP/Guarulhos
                pedido_copia = Pedido()
                
                # Copia todos os atributos do pedido original
                for attr in dir(pedido_original):
                    if not attr.startswith('_') and hasattr(Pedido, attr):
                        try:
                            valor = getattr(pedido_original, attr)
                            if not callable(valor):
                                setattr(pedido_copia, attr, valor)
                        except:
                            pass
                
                # ✅ ALTERAÇÃO PRINCIPAL: Força UF=SP e cidade=Guarulhos
                pedido_copia.cod_uf = 'SP'
                pedido_copia.nome_cidade = 'GUARULHOS'
                pedido_copia.rota = 'CIF'  # Força para não ser RED
                
                # Normaliza dados do pedido convertido
                LocalizacaoService.normalizar_dados_pedido(pedido_copia)
                
                pedidos_para_calculo.append(pedido_copia)
                print(f"[DEBUG] 📍 Convertido: {pedido_original.num_pedido} → GUARULHOS/SP")
        
        # ✅ CÁLCULO CORRETO DAS OTIMIZAÇÕES
        otimizacoes = {
            'remover': {},
            'adicionar': {}
        }

        print(f"[DEBUG] Calculando otimizações com pedidos {'convertidos' if redespacho_ativo else 'originais'}...")
        
        # Calcula otimizações para pedidos atuais (remoção)
        for i, pedido in enumerate(pedidos):
            try:
                pedido_calculo = pedidos_para_calculo[i]  # Usa pedido convertido se redespacho
                resultado = calcular_otimizacoes_pedido(pedido_calculo, pedidos_para_calculo, modalidade, veiculos, frete_atual_kg)
                if resultado:
                    otimizacoes['remover'][pedido.id] = resultado
                    print(f"[DEBUG] ✅ Otimização calculada para pedido {pedido.num_pedido}: {list(resultado.keys())}")
                else:
                    print(f"[DEBUG] ⚠️ Nenhuma otimização encontrada para pedido {pedido.num_pedido}")
                    # Cria uma otimização básica para mostrar dados atuais
                    otimizacoes['remover'][pedido.id] = {
                        'frete_kg_atual': frete_atual_kg,
                        'peso_pedido': pedido.peso_total or 0,
                        'sem_otimizacao': True
                    }
            except Exception as e:
                print(f"[DEBUG] ❌ Erro ao calcular otimização para pedido {pedido.num_pedido}: {str(e)}")
                # Cria uma otimização básica mesmo com erro
                otimizacoes['remover'][pedido.id] = {
                    'frete_kg_atual': frete_atual_kg,
                    'peso_pedido': pedido.peso_total or 0,
                    'erro': str(e)
                }

        # Calcula otimizações para pedidos que podem ser adicionados
        # ✅ CORREÇÃO: Remove limitação artificial e otimiza para performance
        max_otimizacoes = min(len(pedidos_mesmo_uf), 100)  # Limite dinâmico mais realista
        print(f"[DEBUG] 📊 Processando {max_otimizacoes} de {len(pedidos_mesmo_uf)} pedidos disponíveis para otimização")
        
        for pedido in pedidos_mesmo_uf[:max_otimizacoes]:
            try:
                resultado = calcular_otimizacoes_pedido_adicional(pedido, pedidos_para_calculo, transportadora, modalidade, peso_total, veiculos, frete_atual_kg)
                if resultado:
                    otimizacoes['adicionar'][pedido.id] = resultado
                    print(f"[DEBUG] ✅ Otimização calculada para adicionar pedido {pedido.num_pedido}: {list(resultado.keys())}")
                else:
                    print(f"[DEBUG] ⚠️ Nenhuma otimização encontrada para adicionar pedido {pedido.num_pedido}")
                    # Cria uma otimização básica para mostrar dados atuais
                    otimizacoes['adicionar'][pedido.id] = {
                        'frete_kg_atual': frete_atual_kg,
                        'peso_pedido': pedido.peso_total or 0,
                        'sem_otimizacao': True
                    }
            except Exception as e:
                print(f"[DEBUG] ❌ Erro ao calcular otimização para adicionar pedido {pedido.num_pedido}: {str(e)}")
                # Cria uma otimização básica mesmo com erro
                otimizacoes['adicionar'][pedido.id] = {
                    'frete_kg_atual': frete_atual_kg,
                    'peso_pedido': pedido.peso_total or 0,
                    'erro': str(e)
                }
        
        print(f"[DEBUG] Otimizações calculadas:")
        print(f"[DEBUG] - Remoção: {len(otimizacoes['remover'])} opções")
        print(f"[DEBUG] - Adição: {len(otimizacoes['adicionar'])} opções")

        return render_template(
            'cotacao/otimizador.html',
            opcao_atual=opcao_atual,
            pedidos=pedidos,
            pedidos_mesmo_uf=pedidos_mesmo_uf,
            otimizacoes=otimizacoes,
            tipo=tipo
        )

    except Exception as e:
        print(f"[DEBUG] Erro no otimizador: {str(e)}")
        flash(f"Erro ao carregar otimizador: {str(e)}", "error")
        return redirect(url_for("cotacao.tela_cotacao"))

@cotacao_bp.route("/resumo/<int:cotacao_id>")
@login_required
def resumo_frete(cotacao_id):
    """Exibe resumo da cotação fechada"""
    cotacao = Cotacao.query.get_or_404(cotacao_id)
    
    embarque = Embarque.query.filter_by(cotacao_id=cotacao_id).first()
    itens = []
    if embarque:
        itens = EmbarqueItem.query.filter_by(embarque_id=embarque.id).all()
    
    # ✅ CORREÇÃO: CALCULA DADOS DO FRETE BASEADO NO TIPO DE CARGA
    print(f"[DEBUG] === RESUMO FRETE - CALCULANDO VALORES ===")
    print(f"[DEBUG] Cotação ID: {cotacao_id}")
    print(f"[DEBUG] Tipo de carga: {cotacao.tipo_carga if hasattr(cotacao, 'tipo_carga') else 'N/A'}")
    
    # Valor das mercadorias (sempre da cotação)
    valor_mercadorias = cotacao.valor_total if hasattr(cotacao, 'valor_total') and cotacao.valor_total else 0
    peso_total = cotacao.peso_total if hasattr(cotacao, 'peso_total') and cotacao.peso_total else 0
    
    print(f"[DEBUG] Valor mercadorias: R${valor_mercadorias}")
    print(f"[DEBUG] Peso total: {peso_total}kg")
    
    # ✅ CORREÇÃO: CALCULA FRETE BASEADO NO LOCAL CORRETO DOS DADOS DA TABELA
    valor_frete_bruto = 0
    valor_frete_liquido = 0
    frete_por_kg = 0
    
    if embarque and peso_total > 0:
        tipo_carga = getattr(embarque, 'tipo_carga', 'FRACIONADA')
        print(f"[DEBUG] Tipo de carga do embarque: {tipo_carga}")
        
        if tipo_carga == 'DIRETA':
            # ✅ CARGA DIRETA: Dados da tabela estão no EMBARQUE
            print(f"[DEBUG] 📦 CARGA DIRETA: Buscando dados da tabela no embarque")
            
            dados_tabela = {
                'modalidade': getattr(embarque, 'modalidade', 'FRETE PESO'),
                'valor_kg': getattr(embarque, 'tabela_valor_kg', 0),
                'percentual_valor': getattr(embarque, 'tabela_percentual_valor', 0),
                'frete_minimo_valor': getattr(embarque, 'tabela_frete_minimo_valor', 0),
                'frete_minimo_peso': getattr(embarque, 'tabela_frete_minimo_peso', 0),
                'percentual_gris': getattr(embarque, 'tabela_percentual_gris', 0),
                'pedagio_por_100kg': getattr(embarque, 'tabela_pedagio_por_100kg', 0),
                'valor_tas': getattr(embarque, 'tabela_valor_tas', 0),
                'percentual_adv': getattr(embarque, 'tabela_percentual_adv', 0),
                'percentual_rca': getattr(embarque, 'tabela_percentual_rca', 0),
                'valor_despacho': getattr(embarque, 'tabela_valor_despacho', 0),
                'valor_cte': getattr(embarque, 'tabela_valor_cte', 0),
                'icms_destino': getattr(embarque, 'icms_destino', 0),
                'icms_incluso': getattr(embarque, 'tabela_icms_incluso', False)
            }
            
            # Calcula frete para toda a carga
            resultado_frete = CalculadoraFrete.calcular_frete_unificado(
                peso=peso_total,
                valor_mercadoria=valor_mercadorias,
                tabela_dados=dados_tabela,
                transportadora_optante=embarque.transportadora_optante or False
            )
            
            valor_frete_bruto = resultado_frete['valor_bruto']
            valor_frete_liquido = resultado_frete['valor_liquido']
            frete_por_kg = valor_frete_liquido / peso_total if peso_total > 0 else 0
            
            print(f"[DEBUG] ✅ CARGA DIRETA calculada:")
            print(f"[DEBUG]   - Tabela: {getattr(embarque, 'tabela_nome_tabela', 'N/A')}")
            print(f"[DEBUG]   - Modalidade: {dados_tabela['modalidade']}")
            print(f"[DEBUG]   - Valor/kg: R${dados_tabela['valor_kg']}")
            
        else:
            # ✅ CARGA FRACIONADA: Calcula POR CNPJ (não por item individual)
            print(f"[DEBUG] 📦 CARGA FRACIONADA: Calculando por CNPJ (CORREÇÃO)")
            
            # Organiza itens por CNPJ
            itens_por_cnpj_calculo = {}
            
            for item in itens:
                cnpj = getattr(item, 'cnpj_cliente', None)
                if not cnpj:
                    continue
                    
                if cnpj not in itens_por_cnpj_calculo:
                    itens_por_cnpj_calculo[cnpj] = {
                        'itens': [],
                        'peso_total': 0,
                        'valor_total': 0,
                        'dados_tabela': None
                    }
                
                itens_por_cnpj_calculo[cnpj]['itens'].append(item)
                itens_por_cnpj_calculo[cnpj]['peso_total'] += getattr(item, 'peso', 0)
                itens_por_cnpj_calculo[cnpj]['valor_total'] += getattr(item, 'valor', 0)
                
                # Pega dados da tabela (são iguais para o mesmo CNPJ)
                if not itens_por_cnpj_calculo[cnpj]['dados_tabela'] and hasattr(item, 'tabela_nome_tabela') and item.tabela_nome_tabela:
                    itens_por_cnpj_calculo[cnpj]['dados_tabela'] = {
                        'modalidade': getattr(item, 'modalidade', 'FRETE PESO'),
                        'valor_kg': getattr(item, 'tabela_valor_kg', 0),
                        'percentual_valor': getattr(item, 'tabela_percentual_valor', 0),
                        'frete_minimo_valor': getattr(item, 'tabela_frete_minimo_valor', 0),
                        'frete_minimo_peso': getattr(item, 'tabela_frete_minimo_peso', 0),
                        'percentual_gris': getattr(item, 'tabela_percentual_gris', 0),
                        'pedagio_por_100kg': getattr(item, 'tabela_pedagio_por_100kg', 0),
                        'valor_tas': getattr(item, 'tabela_valor_tas', 0),
                        'percentual_adv': getattr(item, 'tabela_percentual_adv', 0),
                        'percentual_rca': getattr(item, 'tabela_percentual_rca', 0),
                        'valor_despacho': getattr(item, 'tabela_valor_despacho', 0),
                        'valor_cte': getattr(item, 'tabela_valor_cte', 0),
                        'icms_destino': getattr(item, 'icms_destino', 0),
                        'icms_incluso': getattr(item, 'tabela_icms_incluso', False)
                    }
            
            # Calcula frete para cada CNPJ usando totais do CNPJ
            valor_frete_bruto = 0
            valor_frete_liquido = 0
            cnpjs_calculados = 0
            cnpjs_sem_tabela = 0
            
            for cnpj, dados_cnpj in itens_por_cnpj_calculo.items():
                peso_cnpj = dados_cnpj['peso_total']
                valor_cnpj = dados_cnpj['valor_total']
                
                if dados_cnpj['dados_tabela']:
                    # ✅ CORREÇÃO: Calcula UMA VEZ com totais do CNPJ
                    resultado_frete_cnpj = CalculadoraFrete.calcular_frete_unificado(
                        peso=peso_cnpj,
                        valor_mercadoria=valor_cnpj,
                        tabela_dados=dados_cnpj['dados_tabela'],
                        transportadora_optante=(embarque and embarque.transportadora_optante) or False
                    )
                    
                    valor_frete_bruto += resultado_frete_cnpj['valor_com_icms']  # ✅ CORREÇÃO: Usar valor COM ICMS
                    valor_frete_liquido += resultado_frete_cnpj['valor_bruto']   # ✅ CORREÇÃO: Usar valor SEM ICMS
                    cnpjs_calculados += 1
                    
                    print(f"[DEBUG]   ✅ CNPJ {cnpj} (Peso: {peso_cnpj}kg, Valor: R${valor_cnpj:.2f}): R${resultado_frete_cnpj['valor_bruto']:.2f} (SEM ICMS), R${resultado_frete_cnpj['valor_com_icms']:.2f} (COM ICMS)")
                    
                else:
                    # Fallback: Dados do embarque ou cálculo básico
                    if embarque and hasattr(embarque, 'tabela_nome_tabela') and embarque.tabela_nome_tabela:
                        dados_tabela_fallback = {
                            'modalidade': getattr(embarque, 'modalidade', 'FRETE PESO'),
                            'valor_kg': getattr(embarque, 'tabela_valor_kg', 0),
                            'percentual_valor': getattr(embarque, 'tabela_percentual_valor', 0),
                            'frete_minimo_valor': getattr(embarque, 'tabela_frete_minimo_valor', 0),
                            'frete_minimo_peso': getattr(embarque, 'tabela_frete_minimo_peso', 0),
                            'percentual_gris': getattr(embarque, 'tabela_percentual_gris', 0),
                            'pedagio_por_100kg': getattr(embarque, 'tabela_pedagio_por_100kg', 0),
                            'valor_tas': getattr(embarque, 'tabela_valor_tas', 0),
                            'percentual_adv': getattr(embarque, 'tabela_percentual_adv', 0),
                            'percentual_rca': getattr(embarque, 'tabela_percentual_rca', 0),
                            'valor_despacho': getattr(embarque, 'tabela_valor_despacho', 0),
                            'valor_cte': getattr(embarque, 'tabela_valor_cte', 0),
                            'icms_destino': getattr(embarque, 'icms_destino', 0),
                            'icms_incluso': getattr(embarque, 'tabela_icms_incluso', False)
                        }
                        
                        resultado_frete_cnpj = CalculadoraFrete.calcular_frete_unificado(
                            peso=peso_cnpj,
                            valor_mercadoria=valor_cnpj,
                            tabela_dados=dados_tabela_fallback,
                            transportadora_optante=embarque.transportadora_optante or False
                        )
                        
                        valor_frete_bruto += resultado_frete_cnpj['valor_com_icms']  # ✅ CORREÇÃO: Usar valor COM ICMS
                        valor_frete_liquido += resultado_frete_cnpj['valor_bruto']   # ✅ CORREÇÃO: Usar valor SEM ICMS
                        
                        print(f"[DEBUG]   🔄 CNPJ {cnpj} (usando dados embarque): R${resultado_frete_cnpj['valor_bruto']:.2f} (SEM ICMS), R${resultado_frete_cnpj['valor_com_icms']:.2f} (COM ICMS)")
                    else:
                        # Último fallback: R$ 1.00/kg
                        frete_basico = peso_cnpj * 1.0
                        valor_frete_liquido += frete_basico
                        valor_frete_bruto += frete_basico * 1.1
                        
                        print(f"[DEBUG]   🆘 CNPJ {cnpj} (frete básico R$1.00/kg): R${frete_basico:.2f}")
                    
                    cnpjs_sem_tabela += 1
            
            frete_por_kg = valor_frete_liquido / peso_total if peso_total > 0 else 0
            
            print(f"[DEBUG] ✅ CARGA FRACIONADA total: R${valor_frete_liquido:.2f}")
            print(f"[DEBUG] 📊 CNPJs com dados tabela: {cnpjs_calculados}")
            print(f"[DEBUG] 📊 CNPJs sem dados tabela: {cnpjs_sem_tabela}")
        
        print(f"[DEBUG] ✅ Frete final calculado:")
        print(f"[DEBUG]   - Frete bruto: R${valor_frete_bruto:.2f}")
        print(f"[DEBUG]   - Frete líquido: R${valor_frete_liquido:.2f}")
        print(f"[DEBUG]   - Frete/kg: R${frete_por_kg:.2f}")
    
    # Se ainda não conseguiu calcular, usa valores zerados
    if not valor_frete_bruto:
        print(f"[DEBUG] ⚠️ Não foi possível calcular o frete - valores zerados")
        valor_frete_bruto = 0
        valor_frete_liquido = 0
        frete_por_kg = 0
    
    frete_calculado = {
        'valor_mercadorias': valor_mercadorias,
        'valor_total': valor_frete_bruto,  # ✅ CORREÇÃO: Frete COM ICMS (bruto)
        'valor_liquido': valor_frete_liquido,  # ✅ CORREÇÃO: Frete SEM ICMS (líquido)
        'frete_por_kg': frete_por_kg,
        'peso_total': peso_total
    }
    
    # ✅ ORGANIZA ITENS POR CNPJ E PREENCHE DADOS DE TABELAS
    itens_por_cnpj = {}
    for item in itens:
        try:
            # ✅ CORREÇÃO: CNPJ está sempre em item.cnpj_cliente para cargas fracionadas
            cnpj = getattr(item, 'cnpj_cliente', None)
            razao_social = getattr(item, 'cliente', 'N/A')
            peso_item = getattr(item, 'peso', 0)
            valor_item = getattr(item, 'valor', 0)
            
            # Se não tem CNPJ no item, tenta buscar do pedido relacionado
            if not cnpj and hasattr(item, 'pedido'):
                pedido_obj = Pedido.query.filter_by(num_pedido=item.pedido).first()
                if pedido_obj:
                    cnpj = pedido_obj.cnpj_cpf
                    if not razao_social or razao_social == 'N/A':
                        razao_social = pedido_obj.raz_social_red
                    if not peso_item:
                        peso_item = pedido_obj.peso_total or 0
                    if not valor_item:
                        valor_item = pedido_obj.valor_saldo_total or 0
            
            # Se ainda não tem CNPJ, usa um valor padrão mas informa o erro
            if not cnpj:
                cnpj = f'SEM_CNPJ_{item.pedido or "N/A"}'
                print(f"[DEBUG] ⚠️ Item sem CNPJ: Pedido {item.pedido}, usando: {cnpj}")
            
            print(f"[DEBUG] 🔍 Item processado: Pedido {item.pedido} → CNPJ {cnpj} (Peso: {peso_item}kg, Valor: R${valor_item})")
            
            # ✅ PREENCHE DADOS DA TABELA DO LOCAL CORRETO
            if embarque and embarque.tipo_carga == 'DIRETA':
                # Para carga direta, usa dados do embarque
                item.nome_tabela = getattr(embarque, 'tabela_nome_tabela', 'N/A')
                item.modalidade = getattr(embarque, 'modalidade', 'FRETE PESO')
                item.valor_kg = getattr(embarque, 'tabela_valor_kg', 0)
                item.icms_destino = getattr(embarque, 'icms_destino', 0)
            else:
                # Para carga fracionada, usa dados do próprio item
                if not hasattr(item, 'nome_tabela') or not item.nome_tabela:
                    item.nome_tabela = getattr(item, 'tabela_nome_tabela', 'N/A')
                    item.modalidade = getattr(item, 'modalidade', 'FRETE PESO')
                    item.valor_kg = getattr(item, 'tabela_valor_kg', 0)
                    item.icms_destino = getattr(item, 'icms_destino', 0)
            
            if cnpj not in itens_por_cnpj:
                itens_por_cnpj[cnpj] = {
                    'cnpj': cnpj,
                    'cliente': razao_social,
                    'razao_social': razao_social,
                    'itens': [],
                    'peso_total': 0,
                    'valor_total': 0,
                    'frete_total': 0,
                    'frete_calculado': {
                        'valor_total': 0,
                        'valor_liquido': 0
                    }
                }
            
            itens_por_cnpj[cnpj]['itens'].append(item)
            itens_por_cnpj[cnpj]['peso_total'] += peso_item
            itens_por_cnpj[cnpj]['valor_total'] += valor_item
            
            # ✅ CORREÇÃO: Não calcula aqui por item, os valores por CNPJ serão calculados depois
                
        except Exception as e:
            print(f"[DEBUG] ❌ Erro ao processar item: {str(e)}")
            # ✅ FALLBACK: Cria entrada genérica com dados seguros
            item.nome_tabela = 'N/A'
            item.modalidade = 'FRETE PESO'
            item.valor_kg = 0
            item.icms_destino = 0
            item.valor_total = 0
            item.valor_liquido = 0
            
            cnpj_fallback = 'ERRO_PROCESSAMENTO'
            if cnpj_fallback not in itens_por_cnpj:
                itens_por_cnpj[cnpj_fallback] = {
                    'cnpj': cnpj_fallback,
                    'cliente': 'Erro no processamento',
                    'razao_social': 'Erro no processamento',
                    'itens': [],
                    'peso_total': 0,
                    'valor_total': 0,
                    'frete_total': 0,
                    'frete_calculado': {
                        'valor_total': 0,
                        'valor_liquido': 0
                    }
                }
            itens_por_cnpj[cnpj_fallback]['itens'].append(item)
    
    # ✅ NOVA SEÇÃO: Calcula valores corretos para cada CNPJ
    for cnpj, grupo in itens_por_cnpj.items():
        if embarque and embarque.tipo_carga == 'DIRETA':
            # Para carga direta: rateia o frete total pelo peso do CNPJ
            peso_embarque = sum(getattr(i, 'peso', 0) for i in itens)
            if peso_embarque > 0:
                proporcao_peso = grupo['peso_total'] / peso_embarque
                grupo['frete_calculado']['valor_total'] = frete_calculado['valor_total'] * proporcao_peso    # COM ICMS
                grupo['frete_calculado']['valor_liquido'] = frete_calculado['valor_liquido'] * proporcao_peso # SEM ICMS
        else:
            # Para carga fracionada: recalcula o frete específico para este CNPJ
            if grupo['itens'] and hasattr(grupo['itens'][0], 'tabela_nome_tabela') and grupo['itens'][0].tabela_nome_tabela:
                # Usa dados da tabela salvos no item
                dados_tabela_cnpj = {
                    'modalidade': getattr(grupo['itens'][0], 'modalidade', 'FRETE PESO'),
                    'valor_kg': getattr(grupo['itens'][0], 'tabela_valor_kg', 0),
                    'percentual_valor': getattr(grupo['itens'][0], 'tabela_percentual_valor', 0),
                    'frete_minimo_valor': getattr(grupo['itens'][0], 'tabela_frete_minimo_valor', 0),
                    'frete_minimo_peso': getattr(grupo['itens'][0], 'tabela_frete_minimo_peso', 0),
                    'percentual_gris': getattr(grupo['itens'][0], 'tabela_percentual_gris', 0),
                    'pedagio_por_100kg': getattr(grupo['itens'][0], 'tabela_pedagio_por_100kg', 0),
                    'valor_tas': getattr(grupo['itens'][0], 'tabela_valor_tas', 0),
                    'percentual_adv': getattr(grupo['itens'][0], 'tabela_percentual_adv', 0),
                    'percentual_rca': getattr(grupo['itens'][0], 'tabela_percentual_rca', 0),
                    'valor_despacho': getattr(grupo['itens'][0], 'tabela_valor_despacho', 0),
                    'valor_cte': getattr(grupo['itens'][0], 'tabela_valor_cte', 0),
                    'icms_destino': getattr(grupo['itens'][0], 'icms_destino', 0),
                    'icms_incluso': getattr(grupo['itens'][0], 'tabela_icms_incluso', False)
                }
                
                resultado_cnpj = CalculadoraFrete.calcular_frete_unificado(
                    peso=grupo['peso_total'],
                    valor_mercadoria=grupo['valor_total'],
                    tabela_dados=dados_tabela_cnpj,
                    transportadora_optante=(embarque and embarque.transportadora_optante) or False
                )
                
                grupo['frete_calculado']['valor_total'] = resultado_cnpj['valor_com_icms']  # ✅ CORREÇÃO: COM ICMS
                grupo['frete_calculado']['valor_liquido'] = resultado_cnpj['valor_bruto']   # ✅ CORREÇÃO: SEM ICMS
            else:
                # Fallback: rateia proporcionalmente
                proporcao = grupo['peso_total'] / peso_total if peso_total > 0 else 0
                grupo['frete_calculado']['valor_total'] = frete_calculado['valor_total'] * proporcao
                grupo['frete_calculado']['valor_liquido'] = frete_calculado['valor_liquido'] * proporcao

    print(f"[DEBUG] Frete calculado para resumo: {frete_calculado}")
    print(f"[DEBUG] Itens por CNPJ: {len(itens_por_cnpj)} grupos")
    
    return render_template(
        'cotacao/resumo_frete.html',
        cotacao=cotacao,
        embarque=embarque,
        itens=itens,
        frete_calculado=frete_calculado,
        itens_por_cnpj=itens_por_cnpj
    )

# ❌ FUNÇÃO REMOVIDA - Usar CalculadoraFrete.calcular_frete_unificado() de app/utils/calculadora_frete.py

def calcular_frete_otimizacao_conservadora(pedidos):
    """
    ✅ FUNÇÃO REFORMULADA: Implementa EXATAMENTE as regras especificadas para otimizações conservadoras
    
    REGRAS IMPLEMENTADAS:
    1- Considera os pedidos com rota "RED" como se fosse UF = "SP" e cidade = "Guarulhos"
    2- Verifica se todos os pedidos tem o mesmo UF (considere a conversão de rota "RED" para UF = SP e cidade = Guarulhos)
    3- Verifica se todos os pedidos da cotação tem a mesma subrota
    4- Traz todos os pedidos do mesmo UF (Considere a conversão de subrota = "RED") e mesma subrota
    5- Se tiver na seção de remover pedidos, considere sem o pedido da linha, se tiver na seção de adicionar considere com o pedido da linha
    6- Soma todos os pesos
    7- Soma todos os valores
    8- Lista todas as cidades dos pedidos cotados (Considere a conversão de subrota = "RED")
    9- Busca nos vinculos todas os nome_tabela / transportadora / UF que atenda as cidades cotadas
    10- Busca nas tabelas as modalidades que atendam aos resultados dos vinculos (transportadora / nome_tabela / uf_destino ).
    11- Descarta as opções de transportadora / modalidade que atendam a apenas uma parte dos pedidos. (caso de transportadora / modalidade que não atenda a todas as cidades dos pedidos)
    12 - Descarta as modalidades que o peso_maximo (link entre veiculos.nome e tabelas.modalidade) não atenda ao total de peso dos pedidos cotados.
    13- Considera a opção mais cara
    """
    # ✅ Todos os imports já estão no topo do arquivo
    
    # Fallback para resultados normais em caso de erro
    try:
        # REGRA 1 e 2: Normalização e validação de UF
        print("[DEBUG] 🎯 OTIMIZAÇÃO CONSERVADORA: Iniciando...")
        
        for pedido in pedidos:
            LocalizacaoService.normalizar_dados_pedido(pedido)
        
        # Verifica se todos são do mesmo UF (considerando RED -> SP)
        ufs_encontrados = set()
        for pedido in pedidos:
            if hasattr(pedido, 'rota') and pedido.rota and pedido.rota.upper().strip() == 'RED':
                ufs_encontrados.add('SP')
            else:
                ufs_encontrados.add(pedido.cod_uf)
        
        if len(ufs_encontrados) > 1:
            print(f"[DEBUG] ❌ Pedidos de UFs diferentes: {ufs_encontrados}")
            return {'diretas': [], 'fracionadas': {}}
        
        uf_comum = list(ufs_encontrados)[0]
        print(f"[DEBUG] ✅ Todos pedidos do UF: {uf_comum}")
        
        # REGRA 3: Verifica se todos têm a mesma sub_rota
        sub_rotas_encontradas = set()
        for pedido in pedidos:
            if hasattr(pedido, 'sub_rota') and pedido.sub_rota:
                sub_rotas_encontradas.add(pedido.sub_rota)
            else:
                sub_rotas_encontradas.add(None)  # Pedidos sem sub_rota
        
        if len(sub_rotas_encontradas) > 1:
            print(f"[DEBUG] ❌ Pedidos de sub_rotas diferentes: {sub_rotas_encontradas}")
            return {'diretas': [], 'fracionadas': {}}
        
        sub_rota_comum = list(sub_rotas_encontradas)[0]
        print(f"[DEBUG] ✅ Todos pedidos da sub_rota: {sub_rota_comum}")
        
        # REGRA 6 e 7: Soma todos os pesos e valores
        peso_total = sum(p.peso_total or 0 for p in pedidos)
        valor_total = sum(p.valor_saldo_total or 0 for p in pedidos)
        
        print(f"[DEBUG] ✅ Peso total: {peso_total}kg, Valor total: R${valor_total:.2f}")
        
        if peso_total <= 0 or valor_total <= 0:
            print("[DEBUG] ❌ Peso ou valor inválido")
            return {'diretas': [], 'fracionadas': {}}
        
        # REGRA 8: Lista todas as cidades dos pedidos cotados
        cidades_cotadas = set()
        for pedido in pedidos:
            # Considera conversão RED -> Guarulhos/SP
            if hasattr(pedido, 'rota') and pedido.rota and pedido.rota.upper().strip() == 'RED':
                cidade = buscar_cidade_unificada(cidade='GUARULHOS', uf='SP', rota='RED')
            else:
                cidade = buscar_cidade_unificada(pedido=pedido)
            
            if cidade:
                cidades_cotadas.add(cidade.id)
        
        if not cidades_cotadas:
            print("[DEBUG] ❌ Nenhuma cidade encontrada")
            return {'diretas': [], 'fracionadas': {}}
        
        print(f"[DEBUG] ✅ Cidades cotadas: {len(cidades_cotadas)} cidades")
        
        # REGRA 9: Busca nos vínculos todas as opções que atendem as cidades cotadas
        vinculos = CidadeAtendida.query.filter(
            CidadeAtendida.cidade_id.in_(cidades_cotadas)
        ).all()
        
        if not vinculos:
            print("[DEBUG] ❌ Nenhum vínculo encontrado")
            return {'diretas': [], 'fracionadas': {}}
        
        print(f"[DEBUG] ✅ Vínculos encontrados: {len(vinculos)}")
        
        # REGRA 10: Busca nas tabelas as modalidades que atendam aos vínculos
        # ✅ NOVO: Filtro por tipo_carga = "DIRETA"
        # Agrupa vínculos por transportadora + modalidade
        combinacoes_transporte = {}  # (transportadora_id, modalidade) -> [tabelas]
        
        for vinculo in vinculos:
            tabelas = TabelaFrete.query.filter(
                TabelaFrete.transportadora_id == vinculo.transportadora_id,
                TabelaFrete.nome_tabela == vinculo.nome_tabela,
                TabelaFrete.tipo_carga == 'DIRETA'  # ✅ FILTRO: Apenas tabelas DIRETA
            ).all()
            
            for tabela in tabelas:
                modalidade = tabela.modalidade or 'FRETE PESO'
                chave = (tabela.transportadora_id, modalidade)
                
                if chave not in combinacoes_transporte:
                    combinacoes_transporte[chave] = []
                combinacoes_transporte[chave].append({
                    'tabela': tabela,
                    'cidade_id': vinculo.cidade_id
                })
        
        print(f"[DEBUG] ✅ Combinações transportadora/modalidade: {len(combinacoes_transporte)}")
        
        # REGRA 11: Descarta opções que não atendem TODAS as cidades
        combinacoes_validas = {}
        
        for (transportadora_id, modalidade), dados in combinacoes_transporte.items():
            # Verifica se esta combinação atende TODAS as cidades cotadas
            cidades_atendidas = set(item['cidade_id'] for item in dados)
            
            if cidades_atendidas.issuperset(cidades_cotadas):
                combinacoes_validas[(transportadora_id, modalidade)] = dados
                print(f"[DEBUG] ✅ Combinação válida: Transp {transportadora_id}, Modal {modalidade}")
            else:
                print(f"[DEBUG] ❌ Combinação descartada: Transp {transportadora_id}, Modal {modalidade} - não atende todas as cidades")
        
        if not combinacoes_validas:
            print("[DEBUG] ❌ Nenhuma combinação atende todas as cidades")
            return {'diretas': [], 'fracionadas': {}}
        
        # REGRA 12: Descarta modalidades que excedem peso máximo
        veiculos = {v.nome: v.peso_maximo for v in Veiculo.query.all()}
        combinacoes_com_peso_ok = {}
        
        for (transportadora_id, modalidade), dados in combinacoes_validas.items():
            peso_maximo = veiculos.get(modalidade, 0)
            
            if peso_maximo >= peso_total:
                combinacoes_com_peso_ok[(transportadora_id, modalidade)] = dados
                print(f"[DEBUG] ✅ Peso OK: Modal {modalidade} suporta {peso_maximo}kg >= {peso_total}kg")
            else:
                print(f"[DEBUG] ❌ Peso excedido: Modal {modalidade} suporta {peso_maximo}kg < {peso_total}kg")
        
        if not combinacoes_com_peso_ok:
            print("[DEBUG] ❌ Nenhuma modalidade suporta o peso total")
            return {'diretas': [], 'fracionadas': {}}
        
        # REGRA 13: Calcula fretes e pega a opção MAIS CARA
        opcoes_calculadas = []
        
        for (transportadora_id, modalidade), dados in combinacoes_com_peso_ok.items():
            # Para cada combinação válida, pega a tabela MAIS CARA entre as que atendem as cidades
            tabelas_da_combinacao = []
            
            for item in dados:
                tabela = item['tabela']
                cidade_id = item['cidade_id']
                cidade = Cidade.query.get(cidade_id)
                
                if not cidade:
                    continue
                
                # Calcula frete com esta tabela
                try:
                    dados_tabela = {
                        'modalidade': modalidade,
                        'valor_kg': tabela.valor_kg or 0,
                        'percentual_valor': tabela.percentual_valor or 0,
                        'frete_minimo_valor': tabela.frete_minimo_valor or 0,
                        'frete_minimo_peso': tabela.frete_minimo_peso or 0,
                        'percentual_gris': tabela.percentual_gris or 0,
                        'pedagio_por_100kg': tabela.pedagio_por_100kg or 0,
                        'valor_tas': tabela.valor_tas or 0,
                        'percentual_adv': tabela.percentual_adv or 0,
                        'percentual_rca': tabela.percentual_rca or 0,
                        'valor_despacho': tabela.valor_despacho or 0,
                        'valor_cte': tabela.valor_cte or 0,
                        'icms_destino': cidade.icms or 0,
                        'icms_incluso': tabela.icms_incluso or False
                    }
                    
                    resultado = CalculadoraFrete.calcular_frete_unificado(
                        peso=peso_total,
                        valor_mercadoria=valor_total,
                        tabela_dados=dados_tabela,
                        transportadora_optante=tabela.transportadora.optante if tabela.transportadora else False
                    )
                    
                    tabelas_da_combinacao.append({
                        'tabela': tabela,
                        'cidade': cidade,
                        'valor_liquido': resultado['valor_liquido'],
                        'valor_total': resultado['valor_com_icms'],
                        'resultado': resultado
                    })
                    
                except Exception as e:
                    print(f"[DEBUG] Erro ao calcular tabela {tabela.nome_tabela}: {str(e)}")
                    continue
            
            # Pega a tabela MAIS CARA desta combinação
            if tabelas_da_combinacao:
                tabela_mais_cara = max(tabelas_da_combinacao, key=lambda x: x['valor_liquido'])
                
                opcao_final = {
                    'transportadora_id': transportadora_id,
                    'transportadora': tabela_mais_cara['tabela'].transportadora.razao_social if tabela_mais_cara['tabela'].transportadora else 'N/A',
                    'modalidade': modalidade,
                    'tipo_carga': 'DIRETA',
                    'valor_total': tabela_mais_cara['valor_total'],
                    'valor_liquido': tabela_mais_cara['valor_liquido'],
                    'nome_tabela': f"{tabela_mais_cara['tabela'].nome_tabela} (CONSERVADOR)",
                    'valor_kg': tabela_mais_cara['tabela'].valor_kg or 0,
                    'percentual_valor': tabela_mais_cara['tabela'].percentual_valor or 0,
                    'icms': tabela_mais_cara['cidade'].icms or 0,
                    'frete_por_kg': tabela_mais_cara['valor_liquido'] / peso_total
                }
                
                opcoes_calculadas.append(opcao_final)
                print(f"[DEBUG] ✅ Opção calculada: {opcao_final['transportadora']} {modalidade} - R${opcao_final['valor_liquido']:.2f}")
        
        if not opcoes_calculadas:
            print("[DEBUG] ❌ Nenhuma opção foi calculada com sucesso")
            return {'diretas': [], 'fracionadas': {}}
        
        # ✅ LÓGICA FINAL: Entre todas as "tabelas mais caras", pega a opção MAIS BARATA
        print(f"[DEBUG] 🎯 COMPARANDO {len(opcoes_calculadas)} OPÇÕES CONSERVADORAS:")
        for opcao in opcoes_calculadas:
            print(f"[DEBUG]   → {opcao['transportadora']} {opcao['modalidade']} - R${opcao['valor_liquido']:.2f} (tabela mais cara)")
        
        # Ordena por valor líquido e pega a MAIS BARATA entre as tabelas mais caras
        opcao_final = min(opcoes_calculadas, key=lambda x: x['valor_liquido'])
        
        print(f"[DEBUG] 🏆 OPÇÃO FINAL CONSERVADORA: {opcao_final['transportadora']} {opcao_final['modalidade']} - R${opcao_final['valor_liquido']:.2f}")
        print(f"[DEBUG]     → Tabela: {opcao_final['nome_tabela']}")
        print(f"[DEBUG]     → Tipo: {opcao_final['tipo_carga']}")
        
        return {
            'diretas': [opcao_final],  # ✅ Apenas a opção mais barata entre as tabelas mais caras
            'fracionadas': {}
        }
        
    except Exception as e:
        print(f"[DEBUG] ❌ Erro na otimização conservadora: {str(e)}")
        return {'diretas': [], 'fracionadas': {}}


@cotacao_bp.route("/redespachar")
@login_required
def redespachar():
    """
    Rota do Redespachar - Cota pedidos considerando UF=SP e cidade=Guarulhos
    """
    try:
        # Recupera pedidos da sessão
        lista_ids = session.get("cotacao_pedidos", [])
        if not lista_ids:
            flash("Nenhum pedido na cotação!", "warning")
            return redirect(url_for("pedidos.lista_pedidos"))

        # Carrega os pedidos originais do banco
        pedidos_originais = Pedido.query.filter(Pedido.id.in_(lista_ids)).all()
        if not pedidos_originais:
            flash("Nenhum pedido encontrado!", "warning")
            return redirect(url_for("pedidos.lista_pedidos"))

        print(f"[DEBUG] 📦 REDESPACHAR: Iniciando para {len(pedidos_originais)} pedidos")
        
        # ✅ CRIA CÓPIAS DOS PEDIDOS COM ALTERAÇÕES TEMPORÁRIAS
        pedidos_redespacho = []
        for pedido_original in pedidos_originais:
            # Cria uma cópia do pedido com os dados alterados para SP/Guarulhos
            pedido_copia = Pedido()
            
            # Copia todos os atributos do pedido original
            for attr in dir(pedido_original):
                if not attr.startswith('_') and hasattr(Pedido, attr):
                    try:
                        valor = getattr(pedido_original, attr)
                        if not callable(valor):
                            setattr(pedido_copia, attr, valor)
                    except:
                        pass
            
            # ✅ ALTERAÇÃO PRINCIPAL: Força UF=SP e cidade=Guarulhos
            pedido_copia.cod_uf = 'SP'
            pedido_copia.nome_cidade = 'GUARULHOS'
            pedido_copia.rota = 'CIF'  # Força para não ser RED (que vai para Guarulhos)
            
            print(f"[DEBUG] 📍 Pedido {pedido_original.num_pedido}: {pedido_original.nome_cidade}/{pedido_original.cod_uf} → GUARULHOS/SP")
            
            pedidos_redespacho.append(pedido_copia)

        # ✅ NORMALIZA OS DADOS DOS PEDIDOS ALTERADOS
        for pedido in pedidos_redespacho:
            LocalizacaoService.normalizar_dados_pedido(pedido)

        # ✅ CALCULA FRETES COM OS DADOS ALTERADOS
        print("[DEBUG] 🚛 Calculando fretes para redespacho (SP/Guarulhos)...")
        resultados = calcular_frete_por_cnpj(pedidos_redespacho)
        
        if not resultados:
            flash("Não foi possível calcular fretes para redespacho", "warning")
            return redirect(url_for("cotacao.tela_cotacao"))

        # ✅ ORGANIZA DADOS PARA O TEMPLATE (mesmo formato da cotação normal)
        pedidos_json = []
        pedidos_por_cnpj = {}
        pedidos_por_cnpj_json = {}
        opcoes_por_cnpj = {}
        
        # Calcula totais
        peso_total = sum(p.peso_total or 0 for p in pedidos_redespacho)
        valor_total = sum(p.valor_saldo_total or 0 for p in pedidos_redespacho)
        
        # Organiza pedidos por CNPJ
        for i, pedido in enumerate(pedidos_redespacho):
            pedido_dict = {
                'id': pedidos_originais[i].id,  # Mantém ID original para referências
                'num_pedido': pedido.num_pedido,
                'data_pedido': pedido.data_pedido.strftime('%Y-%m-%d') if pedido.data_pedido else None,
                'cnpj_cpf': pedido.cnpj_cpf,
                'raz_social_red': pedido.raz_social_red,
                'nome_cidade': 'GUARULHOS',  # Mostra cidade alterada
                'cod_uf': 'SP',  # Mostra UF alterada
                'valor_saldo_total': float(pedido.valor_saldo_total) if pedido.valor_saldo_total else 0,
                'pallet_total': float(pedido.pallet_total) if pedido.pallet_total else 0,
                'peso_total': float(pedido.peso_total) if pedido.peso_total else 0,
                'rota': 'CIF',  # Mostra rota alterada
                'sub_rota': getattr(pedido, 'sub_rota', '')
            }
            
            pedidos_json.append(pedido_dict)
            
            # Organiza por CNPJ
            cnpj = pedido.cnpj_cpf
            if cnpj not in pedidos_por_cnpj:
                pedidos_por_cnpj[cnpj] = []
                pedidos_por_cnpj_json[cnpj] = []
            pedidos_por_cnpj[cnpj].append(pedidos_originais[i])  # Objetos originais para cálculos
            pedidos_por_cnpj_json[cnpj].append(pedido_dict)  # Dados alterados para display

        # ✅ PROCESSA RESULTADOS (mesmo formato da cotação normal)
        opcoes_transporte = {
            'direta': [],
            'fracionada': {}
        }
        
        # Todos são SP/Guarulhos agora, então permite carga direta
        todos_mesmo_uf = True
        
        # Processa cargas diretas
        if 'diretas' in resultados:
            for i, opcao in enumerate(resultados['diretas']):
                if isinstance(opcao, dict):
                    opcao['indice_original'] = i
                    opcao['valor_por_kg'] = opcao['valor_liquido'] / peso_total if peso_total > 0 else float('inf')
            
            resultados['diretas'].sort(key=lambda x: x['valor_por_kg'] if isinstance(x, dict) else float('inf'))
            
            for i, opcao in enumerate(resultados['diretas']):
                if isinstance(opcao, dict):
                    opcao['indice'] = i
            
            opcoes_transporte['direta'] = resultados['diretas']

        # Processa cargas fracionadas (melhor opção por CNPJ)
        if 'fracionadas' in resultados:
            print("[DEBUG] 🎯 IMPLEMENTANDO MELHOR OPÇÃO PARA REDESPACHO")
            
            melhores_opcoes_por_cnpj = {}
            
            for cnpj, opcoes_cnpj in resultados['fracionadas'].items():
                pedidos_cnpj = [p for p in pedidos_redespacho if p.cnpj_cpf == cnpj]
                peso_grupo = sum(p.peso_total or 0 for p in pedidos_cnpj)
                
                melhor_opcao = None
                melhor_valor_kg = float('inf')
                
                for opcao in opcoes_cnpj:
                    valor_kg = opcao['valor_liquido'] / peso_grupo if peso_grupo > 0 else float('inf')
                    if valor_kg < melhor_valor_kg:
                        melhor_valor_kg = valor_kg
                        melhor_opcao = opcao
                
                if melhor_opcao:
                    melhores_opcoes_por_cnpj[cnpj] = melhor_opcao
            
            # Agrupa por transportadora
            for cnpj, melhor_opcao in melhores_opcoes_por_cnpj.items():
                transportadora_id = melhor_opcao['transportadora_id']
                
                if transportadora_id not in opcoes_transporte['fracionada']:
                    opcoes_transporte['fracionada'][transportadora_id] = {
                        'razao_social': melhor_opcao['transportadora'],
                        'cnpjs': []
                    }
                
                pedidos_cnpj = [p for p in pedidos_redespacho if p.cnpj_cpf == cnpj]
                peso_grupo = sum(p.peso_total or 0 for p in pedidos_cnpj)
                valor_grupo = sum(p.valor_saldo_total or 0 for p in pedidos_cnpj)
                pallets_grupo = sum(p.pallet_total or 0 for p in pedidos_cnpj)
                
                opcao_completa = {
                    'cnpj': cnpj,
                    'razao_social': pedidos_cnpj[0].raz_social_red if pedidos_cnpj else '',
                    'cidade': 'GUARULHOS',  # Cidade alterada
                    'uf': 'SP',  # UF alterada
                    'peso_grupo': peso_grupo,
                    'valor_grupo': valor_grupo,
                    'pallets_grupo': pallets_grupo,
                    'valor_total': melhor_opcao['valor_total'],
                    'valor_liquido': melhor_opcao['valor_liquido'],
                    'frete_kg': melhor_opcao['valor_liquido'] / peso_grupo if peso_grupo > 0 else float('inf'),
                    'nome_tabela': melhor_opcao.get('nome_tabela', ''),
                    'modalidade': melhor_opcao.get('modalidade', 'FRETE PESO')
                }
                opcoes_transporte['fracionada'][transportadora_id]['cnpjs'].append(opcao_completa)
            
            # Prepara todas as opções para o modal
            for cnpj, todas_opcoes in resultados['fracionadas'].items():
                opcoes_por_cnpj[cnpj] = []
                
                pedidos_cnpj = [p for p in pedidos_redespacho if p.cnpj_cpf == cnpj]
                peso_grupo = sum(p.peso_total or 0 for p in pedidos_cnpj)
                
                for opcao in todas_opcoes:
                    opcao_completa = {
                        'cnpj': cnpj,
                        'transportadora_id': opcao.get('transportadora_id'),
                        'transportadora': opcao.get('transportadora'),
                        'nome_tabela': opcao.get('nome_tabela', ''),
                        'modalidade': opcao.get('modalidade', 'FRETE PESO'),
                        'valor_total': opcao.get('valor_total', 0),
                        'valor_liquido': opcao.get('valor_liquido', 0),
                        'frete_kg': opcao.get('valor_liquido', 0) / peso_grupo if peso_grupo > 0 else 0,
                        'peso_grupo': peso_grupo,
                        'cidade': 'GUARULHOS',  # Cidade alterada
                        'uf': 'SP',  # UF alterada
                        'razao_social': pedidos_cnpj[0].raz_social_red if pedidos_cnpj else ''
                    }
                    opcoes_por_cnpj[cnpj].append(opcao_completa)

        # ✅ BUSCA PEDIDOS DO MESMO UF (SP) PARA OTIMIZADOR
        pedidos_mesmo_uf = (Pedido.query
                           .filter(Pedido.cod_uf == 'SP')
                           .filter(~Pedido.id.in_(lista_ids))
                           .filter(Pedido.status == 'ABERTO')  # ✅ Apenas pedidos abertos
                           .limit(200)  # ✅ Aumenta limite para mais otimizações
                           .all())

        # Serializa pedidos_mesmo_uf
        pedidos_mesmo_estado_json = []
        for p in pedidos_mesmo_uf:
            pedidos_mesmo_estado_json.append({
                'id': p.id,
                'num_pedido': p.num_pedido,
                'data_pedido': p.data_pedido.strftime('%Y-%m-%d') if p.data_pedido else None,
                'cnpj_cpf': p.cnpj_cpf,
                'raz_social_red': p.raz_social_red,
                'nome_cidade': p.nome_cidade,
                'cod_uf': p.cod_uf,
                'valor_saldo_total': float(p.valor_saldo_total) if p.valor_saldo_total else 0,
                'pallet_total': float(p.pallet_total) if p.pallet_total else 0,
                'peso_total': float(p.peso_total) if p.peso_total else 0,
                'rota': getattr(p, 'rota', ''),
                'sub_rota': getattr(p, 'sub_rota', '')
            })

        # ✅ ARMAZENA RESULTADOS ALTERADOS NA SESSÃO
        session['resultados'] = resultados
        session['redespacho_ativo'] = True  # Flag para indicar que está em modo redespacho

        print(f"[DEBUG] ✅ REDESPACHAR: {len(opcoes_transporte['direta'])} opções diretas, {len(opcoes_transporte['fracionada'])} transportadoras fracionadas")

        # ✅ RENDERIZA O TEMPLATE COM DADOS ALTERADOS
        return render_template(
            "cotacao/redespachar.html",  # Template específico para redespacho
            pedidos=pedidos_originais,  # Objetos originais para compatibilidade
            pedidos_selecionados=pedidos_json,  # Dados alterados para exibição
            pedidos_json=pedidos_json,
            pedidos_mesmo_estado=pedidos_mesmo_uf,
            pedidos_mesmo_estado_json=pedidos_mesmo_estado_json,
            resultados=resultados,
            opcoes_transporte=opcoes_transporte,
            pedidos_por_cnpj=pedidos_por_cnpj_json,
            pedidos_por_cnpj_json=pedidos_por_cnpj_json,
            opcoes_por_cnpj=opcoes_por_cnpj,
            peso_total=peso_total,
            todos_mesmo_uf=todos_mesmo_uf,
            redespacho=True  # Flag para o template saber que é redespacho
        )

    except Exception as e:
        print(f"[DEBUG] ❌ Erro no redespachar: {str(e)}")
        flash(f"Erro ao calcular redespacho: {str(e)}", "error")
        return redirect(url_for("cotacao.tela_cotacao"))
