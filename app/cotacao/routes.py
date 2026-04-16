# ✅ IMPORTS REORGANIZADOS - Todos os imports necessários no topo
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime
from app.utils.timezone import agora_utc_naive

# Database
from app import db

# Models
from app.cotacao.forms import CotarFreteForm
from app.cotacao.models import Cotacao
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from app.transportadoras.models import Transportadora
from app.embarques.models import Embarque, EmbarqueItem
from app.tabelas.models import TabelaFrete
from app.localidades.models import Cidade
from app.veiculos.models import Veiculo
from app.vinculos.models import CidadeAtendida
from app.rastreamento.models import RastreamentoEmbarque  # 🚚 RASTREAMENTO GPS

# Utils
from app.utils.localizacao import LocalizacaoService
from app.utils.frete_simulador import calcular_frete_por_cnpj, buscar_cidade_unificada, calcular_fretes_possiveis
from app.utils.vehicle_utils import normalizar_nome_veiculo
from app.utils.calculadora_frete import CalculadoraFrete
from app.utils.embarque_numero import obter_proximo_numero_embarque
from app.utils.tabela_frete_manager import TabelaFreteManager  # ✅ NOVO: Gerenciador centralizado de campos
# Routes
# Função centralizada importada inline quando necessário

# Conditional imports (só quando necessário)
try:
    from dateutil import parser as date_parser
except ImportError:
    date_parser = None

cotacao_bp = Blueprint("cotacao", __name__, url_prefix="/cotacao")

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
        
        else:          
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
                    except Exception as e:
                        pass
        
        # Se for número (timestamp)
        if isinstance(data, (int, float)):
            try:
                data_obj = datetime.fromtimestamp(data)
                return data_obj.strftime('%d/%m/%Y')
            except Exception as e:
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
    pedidos_sem = [p for p in pedidos_atuais if p.separacao_lote_id != pedido.separacao_lote_id]
    peso_sem = sum(p.peso_total or 0 for p in pedidos_sem)
    peso_total = sum(p.peso_total or 0 for p in pedidos_atuais)
    
    # Só calcula se ainda sobrar pelo menos 1 pedido
    if not pedidos_sem:
        return None
    
    # Recalcula frete sem este pedido usando simulador
    try:
        
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


@cotacao_bp.route("/verificar_nf_cd", methods=["POST"])
@login_required
def verificar_nf_cd():
    """
    Verifica bidirecionalmente se existem pedidos pendentes dos mesmos CNPJs:
    - Selecionou normais (sincronizado_nf=False, nf_cd=False) → busca nf_cd=True não selecionados
    - Selecionou nf_cd=True → busca normais (sincronizado_nf=False, nf_cd=False) não selecionados
    """
    from sqlalchemy import and_, distinct

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Dados não recebidos"}), 400

    lotes_selecionados = data.get("separacao_lote_ids", [])

    if not lotes_selecionados:
        return jsonify({"success": False, "message": "Nenhum lote selecionado"}), 400

    # 1. Classificar os lotes selecionados em GRUPO A (normais) e GRUPO B (nf_cd)
    lotes_info = db.session.query(
        Separacao.separacao_lote_id,
        Separacao.cnpj_cpf,
        Separacao.nf_cd,
        Separacao.sincronizado_nf
    ).filter(
        Separacao.separacao_lote_id.in_(lotes_selecionados)
    ).distinct(Separacao.separacao_lote_id).all()

    cnpjs_grupo_a = set()  # CNPJs dos pedidos normais selecionados
    cnpjs_grupo_b = set()  # CNPJs dos pedidos nf_cd selecionados

    for info in lotes_info:
        if info.nf_cd:
            if info.cnpj_cpf:
                cnpjs_grupo_b.add(info.cnpj_cpf)
        elif not info.sincronizado_nf:
            if info.cnpj_cpf:
                cnpjs_grupo_a.add(info.cnpj_cpf)

    pendentes_nf_cd = []
    pendentes_normais = []

    # Campos para agrupamento e seleção
    campos_group = [
        Separacao.separacao_lote_id,
        Separacao.num_pedido,
        Separacao.cnpj_cpf,
        Separacao.raz_social_red,
        Separacao.nome_cidade,
        Separacao.cod_uf,
        Separacao.expedicao,
        Separacao.agendamento,
        Separacao.agendamento_confirmado,
        Separacao.protocolo,
        Separacao.numero_nf,
        Separacao.status
    ]

    campos_select = campos_group + [
        func.sum(Separacao.valor_saldo).label('valor_saldo'),
        func.sum(Separacao.peso).label('peso'),
        func.sum(Separacao.pallet).label('pallet')
    ]

    # 2. Direção 1: CNPJs do GRUPO A → buscar nf_cd=True não selecionados
    if cnpjs_grupo_a:
        resultado_nf_cd = db.session.query(*campos_select).filter(
            Separacao.cnpj_cpf.in_(list(cnpjs_grupo_a)),
            Separacao.nf_cd == True,
            Separacao.separacao_lote_id.notin_(lotes_selecionados)
        ).group_by(*campos_group).all()

        pendentes_nf_cd = [_serializar_pedido_verificacao(r) for r in resultado_nf_cd]

    # 3. Direção 2: CNPJs do GRUPO B → buscar normais não selecionados
    if cnpjs_grupo_b:
        resultado_normais = db.session.query(*campos_select).filter(
            Separacao.cnpj_cpf.in_(list(cnpjs_grupo_b)),
            Separacao.sincronizado_nf == False,
            Separacao.nf_cd == False,
            Separacao.separacao_lote_id.notin_(lotes_selecionados)
        ).group_by(*campos_group).all()

        pendentes_normais = [_serializar_pedido_verificacao(r) for r in resultado_normais]

    # 4. Se não há pendentes em nenhuma direção, sem modal
    if not pendentes_nf_cd and not pendentes_normais:
        return jsonify({"success": True, "tem_pendentes": False})

    # 5. Buscar dados dos selecionados para exibir no modal
    resultado_selecionados = db.session.query(*campos_select).filter(
        Separacao.separacao_lote_id.in_(lotes_selecionados)
    ).group_by(*campos_group).all()

    selecionados = [_serializar_pedido_verificacao(r) for r in resultado_selecionados]

    return jsonify({
        "success": True,
        "tem_pendentes": True,
        "selecionados": selecionados,
        "pendentes_nf_cd": pendentes_nf_cd,
        "pendentes_normais": pendentes_normais
    })


def _serializar_pedido_verificacao(row):
    """Serializa um registro de Separacao agrupado para a verificação NF CD."""
    return {
        "separacao_lote_id": row.separacao_lote_id,
        "num_pedido": row.num_pedido,
        "cnpj_cpf": row.cnpj_cpf,
        "raz_social_red": row.raz_social_red,
        "nome_cidade": row.nome_cidade,
        "cod_uf": row.cod_uf,
        "expedicao": row.expedicao.strftime("%d/%m/%Y") if row.expedicao else None,
        "agendamento": row.agendamento.strftime("%d/%m/%Y") if row.agendamento else None,
        "agendamento_confirmado": bool(row.agendamento_confirmado) if row.agendamento_confirmado else False,
        "protocolo": row.protocolo,
        "numero_nf": row.numero_nf,
        "status": row.status,
        "valor_saldo": float(row.valor_saldo or 0),
        "peso": float(row.peso or 0),
        "pallet": float(row.pallet or 0)
    }


@cotacao_bp.route("/iniciar", methods=["POST"])
@login_required
def iniciar_cotacao():
    """
    Recebe via POST a lista de pedidos selecionados.
    IMPORTANTE: Agora recebe separacao_lote_id ao invés de pedido_id
    """
    # Tenta primeiro por separacao_lote_ids (novo padrão)
    lista_lotes = request.form.getlist("separacao_lote_ids")
    
    # Fallback para pedido_ids (retrocompatibilidade)
    if not lista_lotes:
        lista_ids_str = request.form.getlist("pedido_ids")
        if lista_ids_str:
            # Se são IDs numéricos, buscar os lotes correspondentes
            from app.pedidos.models import Pedido
            pedidos = Pedido.query.filter(Pedido.num_pedido.in_(lista_ids_str)).all()
            lista_lotes = [p.separacao_lote_id for p in pedidos if p.separacao_lote_id]
    
    if not lista_lotes:
        flash("Nenhum pedido selecionado!", "warning")
        return redirect(url_for("pedidos.lista_pedidos"))

    # Armazena no session como lotes
    session["cotacao_lotes"] = lista_lotes
    session["cotacao_pedidos"] = lista_lotes  # Manter para retrocompatibilidade
    
    # CORREÇÃO: Limpa informações de alteração de embarque se houver
    # Isso evita que uma alteração anterior não finalizada interfira em nova cotação
    if 'alterando_embarque' in session:
        session.pop('alterando_embarque', None)
        print(f"[DEBUG] 🔄 Limpando alteração de embarque anterior não finalizada")

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
    
    # SOLUÇÃO ROBUSTA: Verifica se está alterando embarque pelo parâmetro da URL
    alterando_embarque_id = request.args.get('alterando_embarque')
    
    if alterando_embarque_id:
        # Está vindo da rota de alteração - mantém dados na sessão
        print(f"[DEBUG] 🔄 Alterando cotação do embarque #{alterando_embarque_id}")
        # Verifica se os dados na sessão correspondem ao embarque correto
        if 'alterando_embarque' not in session or session['alterando_embarque'].get('embarque_id') != int(alterando_embarque_id):
            flash('⚠️ Erro: dados de alteração inconsistentes. Tente novamente.', 'warning')
            return redirect(url_for('embarques.visualizar_embarque', id=alterando_embarque_id))
    else:
        # Não está alterando - limpa dados de alteração se existirem
        if 'alterando_embarque' in session:
            session.pop('alterando_embarque', None)
            print(f"[DEBUG] 🔄 Limpando dados de alteração - nova cotação iniciada")
    
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
    # Verifica primeiro se há dados completos de alteração de embarque
    pedidos_data_sessao = session.get("cotacao_pedidos_data", None)
    
    # Verifica se está alterando embarque (vindo da query string ou sessão)
    alterando_embarque = alterando_embarque_id is not None or 'alterando_embarque' in session
    
    # Inicializar lista_lotes para evitar UnboundLocalError
    lista_lotes = []
    
    if pedidos_data_sessao and alterando_embarque:
        # Está alterando embarque - usar dados da sessão diretamente
        from datetime import datetime
        
        pedidos = []
        for p_data in pedidos_data_sessao:
            # Criar objeto compatível com Pedido
            pedido_obj = type('PedidoTemp', (), {
                'id': p_data.get('separacao_lote_id'),
                'separacao_lote_id': p_data.get('separacao_lote_id'),
                'num_pedido': p_data.get('num_pedido', ''),
                'data_pedido': datetime.fromisoformat(p_data['data_pedido']) if p_data.get('data_pedido') else None,
                'cnpj_cpf': p_data.get('cnpj_cpf', ''),
                'raz_social_red': p_data.get('raz_social_red', ''),
                'nome_cidade': p_data.get('nome_cidade', ''),
                'cidade_normalizada': p_data.get('cidade_normalizada', p_data.get('nome_cidade', '')),
                'uf_normalizada': p_data.get('uf_normalizada', p_data.get('cod_uf', '')),
                'codigo_ibge': p_data.get('codigo_ibge', ''),
                'cod_uf': p_data.get('cod_uf', ''),
                'valor_saldo_total': p_data.get('valor_saldo_total', 0),
                'pallet_total': p_data.get('pallet_total', 0),
                'peso_total': p_data.get('peso_total', 0),
                'rota': p_data.get('rota', ''),
                'sub_rota': p_data.get('sub_rota', ''),
                'expedicao': datetime.fromisoformat(p_data['expedicao']) if p_data.get('expedicao') else None,
                'agendamento': datetime.fromisoformat(p_data['agendamento']) if p_data.get('agendamento') else None,
                'protocolo': p_data.get('protocolo'),
                'transportadora': None,
                'cotacao_id': None
            })()
            pedidos.append(pedido_obj)
            # Adicionar lote_id à lista para evitar erro
            if p_data.get('separacao_lote_id'):
                lista_lotes.append(p_data['separacao_lote_id'])
        print(f"[DEBUG] Pedidos carregados da sessão (alteração embarque): {len(pedidos)}")
    else:
        # Fluxo normal - buscar pedidos do banco
        # Tentar primeiro por lotes (novo padrão)
        lista_lotes = session.get("cotacao_lotes", [])
        
        # Fallback para IDs antigos
        if not lista_lotes:
            lista_lotes = session.get("cotacao_pedidos", [])
        
        if not lista_lotes:
            flash("Nenhum pedido na cotação!", "warning")
            return redirect(url_for("pedidos.lista_pedidos"))
        
        # Carrega os pedidos do banco usando separacao_lote_id
        # Pedido é uma VIEW agregada, então busca por lote
        pedidos = Pedido.query.filter(Pedido.separacao_lote_id.in_(lista_lotes)).all()
        print(f"[DEBUG] Pedidos carregados do banco por lote: {len(pedidos)}")
    
    if not pedidos:
        flash("Nenhum pedido encontrado!", "warning")
        return redirect(url_for("pedidos.lista_pedidos"))
    
    # Calcula totais
    peso_total = sum(p.peso_total or 0 for p in pedidos)
    print(f"[DEBUG] Peso total dos pedidos: {peso_total}kg")
    
    # Verifica se todos são do mesmo UF usando LocalizacaoService
    ufs_normalizados = set()
    for pedido in pedidos:
        # ✅ CORREÇÃO: Usa o LocalizacaoService para normalizar o UF diretamente
        uf_normalizado = LocalizacaoService.normalizar_uf_com_regras(
            uf=pedido.cod_uf,
            cidade=pedido.nome_cidade,
            rota=getattr(pedido, 'rota', None)
        )
        if uf_normalizado:
            ufs_normalizados.add(uf_normalizado)
    
    todos_mesmo_uf = len(ufs_normalizados) == 1
    print(f"[DEBUG] UFs encontrados: {ufs_normalizados}")
    print(f"[DEBUG] Todos mesmo UF? {todos_mesmo_uf}")
    
    # Organiza pedidos por CNPJ e cria versões JSON
    for pedido in pedidos:
        # Cria dicionário com dados do pedido
        # IMPORTANTE: Usar separacao_lote_id como identificador principal
        pedido_dict = {
            'id': pedido.separacao_lote_id,  # Usar lote como ID principal
            'separacao_lote_id': pedido.separacao_lote_id,
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
        # Usar lista_lotes ao invés de lista_ids
        pedidos_mesmo_estado = (Pedido.query
                               .filter(
                                   (Pedido.cod_uf == uf_busca))                                        
                               .filter(~Pedido.separacao_lote_id.in_(lista_lotes))
                               .filter(Pedido.status == 'ABERTO')  # ✅ Apenas pedidos abertos
                               .all())
        print(f"[DEBUG] Pedidos do mesmo estado encontrados: {len(pedidos_mesmo_estado)}")
        
        # Serializa pedidos_mesmo_estado
        for p in pedidos_mesmo_estado:
            pedidos_mesmo_estado_json.append({
                'id': p.separacao_lote_id,
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
                        # Usa TabelaFreteManager para preparar campos da tabela
                        dados_tabela_opcao = TabelaFreteManager.preparar_dados_tabela(melhor_opcao)
                        
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
                            **dados_tabela_opcao,  # Inclui todos os campos da tabela
                            'icms_destino': melhor_opcao.get('icms_destino', 0)  # icms_destino separado
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
                            # Usa TabelaFreteManager para preparar campos da tabela
                            dados_tabela_opcao = TabelaFreteManager.preparar_dados_tabela(opcao)
                            
                            opcao_completa = {
                                'cnpj': cnpj,
                                'transportadora_id': opcao.get('transportadora_id'),
                                'transportadora': opcao.get('transportadora'),
                                'valor_total': opcao.get('valor_total', 0),
                                'valor_liquido': opcao.get('valor_liquido', 0),
                                'frete_kg': opcao.get('valor_liquido', 0) / peso_grupo if peso_grupo > 0 else 0,
                                'peso_grupo': peso_grupo,
                                'valor_grupo': valor_grupo,
                                'pallets_grupo': pallets_grupo,
                                'cidade': opcao.get('cidade', ''),
                                'uf': opcao.get('uf', ''),
                                'razao_social': pedidos_cnpj[0].raz_social_red if pedidos_cnpj else '',
                                **dados_tabela_opcao,  # Inclui todos os campos da tabela
                                'icms_destino': opcao.get('icms_destino', 0)  # icms_destino separado
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


    # Debug final antes de enviar para o template
    print(f"[DEBUG] 🎯 ENVIANDO PARA TEMPLATE: opcoes_por_cnpj com {len(opcoes_por_cnpj)} CNPJs")
    for cnpj_final, opcoes_final in opcoes_por_cnpj.items():
        print(f"[DEBUG] 🎯 TEMPLATE - CNPJ {cnpj_final}: {len(opcoes_final)} opções")

    # ✅ BUSCAR EMBARQUES COMPATÍVEIS
    embarques_compativeis_direta = []
    embarques_compativeis_fracionada = []

    print(f"[DEBUG EMBARQUES] ============== INICIANDO BUSCA DE EMBARQUES ==============")
    print(f"[DEBUG EMBARQUES] todos_mesmo_uf: {todos_mesmo_uf}")
    print(f"[DEBUG EMBARQUES] ufs_normalizados: {ufs_normalizados}")
    print(f"[DEBUG EMBARQUES] opcoes_transporte.get('direta'): {opcoes_transporte.get('direta') is not None}")

    try:
        from app.embarques.models import Embarque
        from app.veiculos.models import Veiculo
        from sqlalchemy.orm import joinedload

        # ✅ OTIMIZAÇÃO: Para CARGA DIRETA - buscar embarques compatíveis com melhor performance
        if todos_mesmo_uf and len(ufs_normalizados) == 1 and opcoes_transporte.get('direta'):
            uf_destino = list(ufs_normalizados)[0]
            print(f"[DEBUG EMBARQUES] 🔍 Iniciando busca de embarques DIRETA - UF destino: {uf_destino}")

            # ✅ NOVA LÓGICA: Busca embarques da mesma transportadora/modalidade das cotações
            for opcao_direta in opcoes_transporte['direta']:
                transportadora_id = opcao_direta.get('transportadora_id')
                modalidade = opcao_direta.get('modalidade')
                print(f"[DEBUG EMBARQUES] 🚛 Buscando embarques - Transportadora ID: {transportadora_id}, Modalidade: {modalidade}")

                if transportadora_id and modalidade:
                    # Buscar embarques ativos da mesma transportadora, modalidade e sem data de embarque
                    # ⚠️ NOTA: Não usamos joinedload(Embarque._itens) porque lazy='dynamic' não suporta eager loading
                    # A propriedade embarque.itens já faz a query automaticamente
                    embarques_query = Embarque.query.options(
                        joinedload(Embarque.transportadora)
                    ).filter(
                        Embarque.status == 'ativo',
                        Embarque.tipo_carga == 'DIRETA',
                        Embarque.transportadora_id == transportadora_id,
                        Embarque.modalidade == modalidade,
                        Embarque.data_embarque.is_(None)  # ✅ Sem data de embarque
                    ).limit(200)  # ✅ Aumentado de 50 para 200 embarques

                    print(f"[DEBUG EMBARQUES] 📦 Embarques encontrados na query: {embarques_query.count()}")

                    for embarque in embarques_query:
                        print(f"[DEBUG EMBARQUES] 🔎 Processando embarque #{embarque.numero}")
                        print(f"[DEBUG EMBARQUES]   - Tipo _itens: {type(embarque._itens)}")
                        print(f"[DEBUG EMBARQUES]   - Tipo itens: {type(embarque.itens)}")
                        print(f"[DEBUG EMBARQUES]   - Quantidade itens: {len(embarque.itens)}")
                        print(f"[DEBUG EMBARQUES]   - Quantidade itens_ativos: {len(embarque.itens_ativos)}")
                        if embarque.itens_ativos:
                            print(f"[DEBUG EMBARQUES] ✅ Embarque #{embarque.numero} TEM itens ativos!")
                            # Verificar se é mesmo UF
                            uf_embarque = embarque.itens_ativos[0].uf_destino
                            print(f"[DEBUG EMBARQUES]   - UF embarque: {uf_embarque}, UF destino: {uf_destino}")
                            if uf_embarque == uf_destino:
                                print(f"[DEBUG EMBARQUES] ✅ UF compatível!")
                                # Verificar capacidade do veículo
                                veiculo = Veiculo.query.filter_by(nome=modalidade).first()
                                print(f"[DEBUG EMBARQUES]   - Veículo encontrado: {veiculo.nome if veiculo else 'None'}")
                                if veiculo and veiculo.peso_maximo:
                                    print(f"[DEBUG EMBARQUES]   - Peso máximo veículo: {veiculo.peso_maximo}kg")
                                    peso_atual = embarque.total_peso_pedidos()
                                    capacidade_restante = veiculo.peso_maximo - peso_atual
                                    
                                    # ✅ NOVA LÓGICA: Calcula acréscimo de valor (sempre positivo ou zero)
                                    # Extrai dados da tabela do embarque usando TabelaFreteManager
                                    dados_tabela_embarque = TabelaFreteManager.preparar_dados_tabela(embarque)
                                    valor_kg_embarque = dados_tabela_embarque.get('valor_kg', 0)
                                    
                                    valor_embarque_atual = valor_kg_embarque * peso_atual if valor_kg_embarque else 0
                                    valor_cotacao = opcao_direta.get('valor_liquido', 0)
                                    valor_embarque_com_cotacao = valor_kg_embarque * (peso_atual + peso_total) if valor_kg_embarque else 0
                                    
                                    # Acréscimo = diferença entre valor total com inclusão vs valor atual + valor da cotação separada
                                    acrescimo_valor = max(0, valor_embarque_com_cotacao - valor_embarque_atual - valor_cotacao)
                                    
                                    # ✅ CONTA CNPJs ÚNICOS NO EMBARQUE
                                    cnpjs_embarque = set(item.cnpj_cliente for item in embarque.itens_ativos if item.cnpj_cliente)
                                    
                                    if capacidade_restante >= peso_total:
                                        print(f"[DEBUG EMBARQUES] ✅ ADICIONANDO embarque #{embarque.numero} - TEM capacidade")
                                        embarques_compativeis_direta.append({
                                            'embarque': embarque,
                                            'capacidade_restante': capacidade_restante,
                                            'valor_sugerido': valor_cotacao,
                                            'acrescimo_valor': acrescimo_valor,
                                            'qtd_cnpjs': len(cnpjs_embarque),
                                            'tem_capacidade': True
                                        })
                                    else:
                                        # ✅ MOSTRA TAMBÉM OS SEM CAPACIDADE
                                        print(f"[DEBUG EMBARQUES] ⚠️ ADICIONANDO embarque #{embarque.numero} - SEM capacidade")
                                        embarques_compativeis_direta.append({
                                            'embarque': embarque,
                                            'capacidade_restante': capacidade_restante,
                                            'valor_sugerido': valor_cotacao,
                                            'acrescimo_valor': acrescimo_valor,
                                            'qtd_cnpjs': len(cnpjs_embarque),
                                            'tem_capacidade': False
                                        })
                                else:
                                    print(f"[DEBUG EMBARQUES] ❌ Embarque #{embarque.numero} - Veículo sem peso_maximo ou não encontrado")
                            else:
                                print(f"[DEBUG EMBARQUES] ❌ Embarque #{embarque.numero} - UF incompatível ({uf_embarque} != {uf_destino})")
                        else:
                            print(f"[DEBUG EMBARQUES] ❌ Embarque #{embarque.numero} - SEM itens ativos")
        
        # ✅ OTIMIZAÇÃO: Para CARGA FRACIONADA - buscar embarques compatíveis com melhor performance
        print(f"[DEBUG EMBARQUES] 🔍 Iniciando busca de embarques FRACIONADA")
        transportadoras_fracionada = set()
        for cnpj, pedidos_cnpj in pedidos_por_cnpj.items():
            if pedidos_cnpj and cnpj in opcoes_por_cnpj:
                for opcao in opcoes_por_cnpj[cnpj][:10]:  # ✅ Aumentado de 3 para 10 opções por CNPJ
                    transportadoras_fracionada.add(opcao.get('transportadora_id'))

        print(f"[DEBUG EMBARQUES] 🚛 Transportadoras fracionada: {transportadoras_fracionada}")

        if transportadoras_fracionada:
            # ⚠️ NOTA: Não usamos joinedload(Embarque._itens) porque lazy='dynamic' não suporta eager loading
            # A propriedade embarque.itens já faz a query automaticamente
            embarques_frac_query = Embarque.query.options(
                joinedload(Embarque.transportadora)
            ).filter(
                Embarque.status == 'ativo',
                Embarque.tipo_carga == 'FRACIONADA',
                Embarque.transportadora_id.in_(list(transportadoras_fracionada)),
                Embarque.data_embarque.is_(None)  # ✅ Sem data de embarque
            ).limit(100)  # ✅ Aumentado de 20 para 100 embarques

            print(f"[DEBUG EMBARQUES] 📦 Embarques FRACIONADA encontrados: {embarques_frac_query.count()}")

            for embarque in embarques_frac_query:
                print(f"[DEBUG EMBARQUES] 🔎 Processando embarque FRACIONADA #{embarque.numero}")
                print(f"[DEBUG EMBARQUES]   - Quantidade itens_ativos: {len(embarque.itens_ativos)}")
                if embarque.itens_ativos:
                    print(f"[DEBUG EMBARQUES] ✅ ADICIONANDO embarque FRACIONADA #{embarque.numero}")
                    # ✅ CONTA CNPJs ÚNICOS NO EMBARQUE
                    cnpjs_embarque = set(item.cnpj_cliente for item in embarque.itens_ativos if item.cnpj_cliente)
                    
                    embarques_compativeis_fracionada.append({
                        'embarque': embarque,
                        'qtd_cnpjs': len(cnpjs_embarque)
                    })
                else:
                    print(f"[DEBUG EMBARQUES] ❌ Embarque FRACIONADA #{embarque.numero} - SEM itens ativos")

        print(f"[DEBUG EMBARQUES] ============== RESULTADO FINAL ==============")
        print(f"[DEBUG EMBARQUES] 🚛 Embarques compatíveis DIRETA: {len(embarques_compativeis_direta)}")
        print(f"[DEBUG EMBARQUES] 🚛 Embarques compatíveis FRACIONADA: {len(embarques_compativeis_fracionada)}")

    except Exception as e:
        print(f"[DEBUG EMBARQUES] ❌ ERRO ao buscar embarques compatíveis: {str(e)}")
        import traceback
        traceback.print_exc()

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
        todos_mesmo_uf=todos_mesmo_uf,
        embarques_compativeis_direta=embarques_compativeis_direta,
        embarques_compativeis_fracionada=embarques_compativeis_fracionada,
        alterando_embarque_info=session.get('alterando_embarque'),
        transportadoras=Transportadora.query.filter(Transportadora.razao_social != 'FOB - COLETA').order_by(Transportadora.razao_social).all(),
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
    ✅ NOVO: Suporte para alterar cotação de embarques existentes
    """
    try:
        # ✅ CORREÇÃO: Aceita tanto JSON quanto form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
            # Converte strings para listas quando necessário
            if 'pedidos' in data and isinstance(data['pedidos'], str):
                import json
                try:
                    data['pedidos'] = json.loads(data['pedidos'])
                except Exception as e:
                    data['pedidos'] = []
        
        if not data:
            return jsonify({'success': False, 'message': 'Dados inválidos'}), 400

        tipo = data.get('tipo')
        transportadora_id = data.get('transportadora_id')
        pedidos_data = data.get('pedidos', [])
        indice_original = data.get('indice_original', 0)
        
        # ✅ NOVO: Verifica se estamos alterando cotação de embarque existente
        # Fonte 1: payload (mais confiável, sobrevive a perda de sessão)
        embarque_id_payload = data.get('embarque_id')
        if embarque_id_payload and str(embarque_id_payload).lower() in ('null', 'none', ''):
            embarque_id_payload = None
        # Fonte 2: session (backup)
        alterando_embarque_session = session.get('alterando_embarque')

        alterando_embarque = None
        embarque_existente = None

        if embarque_id_payload:
            embarque_existente = db.session.get(Embarque, int(embarque_id_payload))
            if embarque_existente:
                alterando_embarque = {'embarque_id': embarque_existente.id, 'numero_embarque': embarque_existente.numero}
                print(f"[DEBUG] 🔄 ALTERANDO COTAÇÃO do embarque #{embarque_existente.numero} (via payload)")
            else:
                return jsonify({'success': False, 'message': 'Embarque não encontrado para alteração'}), 404
        elif alterando_embarque_session:
            alterando_embarque = alterando_embarque_session
            embarque_id = alterando_embarque.get('embarque_id')
            embarque_existente = db.session.get(Embarque, embarque_id) if embarque_id else None

            if not embarque_existente:
                # Remove informação inválida da sessão
                session.pop('alterando_embarque', None)
                return jsonify({'success': False, 'message': 'Embarque não encontrado para alteração'}), 404

            print(f"[DEBUG] 🔄 ALTERANDO COTAÇÃO do embarque #{embarque_existente.numero} (via session)")

        if embarque_existente:
            # Verifica se ainda é possível alterar (data embarque não preenchida)
            if embarque_existente.data_embarque:
                session.pop('alterando_embarque', None)
                return jsonify({'success': False, 'message': 'Não é possível alterar cotação de embarque já embarcado'}), 400
        else:
            print(f"[DEBUG] ✅ CRIANDO NOVO EMBARQUE")

        print(f"[DEBUG] === FECHAR FRETE ===")
        print(f"[DEBUG] Tipo: {tipo}")
        print(f"[DEBUG] Transportadora: {transportadora_id}")
        print(f"[DEBUG] Índice original: {indice_original}")
        print(f"[DEBUG] Redespacho: {data.get('redespacho', False)}")
        print(f"[DEBUG] Alterando embarque: {embarque_existente.numero if embarque_existente else 'Não'}")
        
        if not tipo or not transportadora_id or not pedidos_data:
            return jsonify({'success': False, 'message': 'Dados incompletos'}), 400

        transportadora = db.session.get(Transportadora,transportadora_id) if transportadora_id else None
        if not transportadora:
            return jsonify({'success': False, 'message': 'Transportadora não encontrada'}), 404

        # ✅ NOVA LÓGICA: Recebe dados COMPLETOS da tabela do frontend (payload)
        tabela_selecionada = data.get('tabela_selecionada')

        print(f"[DEBUG] === RECEBENDO DADOS DA TABELA DO PAYLOAD ===")

        # ✅ VALIDAÇÃO CRÍTICA: Garante que tabela foi enviada
        if not tabela_selecionada:
            print(f"[DEBUG] ❌ ERRO: tabela_selecionada não foi enviada no payload!")
            return jsonify({
                'success': False,
                'message': 'Dados da tabela não foram enviados. Recarregue a página e tente novamente.'
            }), 400

        # ✅ VALIDAÇÃO: Verifica campos obrigatórios
        if not tabela_selecionada.get('nome_tabela'):
            print(f"[DEBUG] ❌ ERRO: nome_tabela está vazio!")
            return jsonify({
                'success': False,
                'message': 'Nome da tabela é obrigatório.'
            }), 400

        # ✅ USA DADOS DO PAYLOAD em vez da session
        opcao_escolhida = tabela_selecionada.copy()

        print(f"[DEBUG] ✅ Tabela recebida do PAYLOAD: {opcao_escolhida.get('nome_tabela')} - Modalidade: {opcao_escolhida.get('modalidade')}")
        print(f"[DEBUG] ✅ Valores do payload - Frete total: R${opcao_escolhida.get('valor_total', 0):.2f}, Líquido: R${opcao_escolhida.get('valor_liquido', 0):.2f}")

        # ✅ DEBUG: Compara com session para detectar divergências (opcional)
        resultados = session.get('resultados')
        if resultados and 'diretas' in resultados:
            opcao_session = None
            for opcao in resultados['diretas']:
                if isinstance(opcao, dict) and opcao.get('indice_original') == int(indice_original):
                    opcao_session = opcao
                    break

            if opcao_session:
                if opcao_session.get('nome_tabela') != opcao_escolhida.get('nome_tabela'):
                    print(f"[DEBUG] ⚠️ ALERTA: Tabela DIFERENTE entre payload e session!")
                    print(f"[DEBUG]   - Payload: {opcao_escolhida.get('nome_tabela')}")
                    print(f"[DEBUG]   - Session: {opcao_session.get('nome_tabela')}")
                else:
                    print(f"[DEBUG] ✅ Validação OK: Tabela no payload = tabela na session")

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
                # Usa separacao_lote_id em vez de id
                lote_id = pedido_data.get('id')  # Na verdade é o separacao_lote_id
                pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()
                if pedido:
                    uf_destino = pedido.cod_uf
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
            cidade_destino = Cidade.query.filter_by(nome='Guarulhos', uf='SP').first()
            if not cidade_destino:
                cidade_destino = Cidade.query.filter_by(nome='Guarulhos', uf='SP').first()
            if cidade_destino:
                icms_destino = cidade_destino.icms or 0
                print(f"[DEBUG] ✅ ICMS Guarulhos/SP: {icms_destino}%")
        else:
            # Para cotação normal, busca ICMS da cidade original do primeiro pedido
            for pedido_data in pedidos_data:
                # Usa separacao_lote_id em vez de id
                lote_id = pedido_data.get('id')  # Na verdade é o separacao_lote_id
                pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()
                if pedido:
                    # ✅ ESTRATÉGIA CODIGO IBGE: Usa código IBGE se disponível para buscar ICMS
                    cidade_destino = None
                    if pedido.codigo_ibge:
                        cidade_destino = Cidade.query.filter_by(codigo_ibge=pedido.codigo_ibge).first()
                        if cidade_destino:
                            print(f"[DEBUG] ✅ ICMS encontrado via IBGE {pedido.codigo_ibge}: {cidade_destino.nome}")
                    
                    if not cidade_destino:
                        # Fallback: busca por nome normalizado
                        cidade_destino = Cidade.query.filter_by(
                            nome=pedido.cidade_normalizada,
                            uf=uf_destino
                        ).first()
                        if cidade_destino:
                            print(f"[DEBUG] 🔄 ICMS encontrado via nome: {cidade_destino.nome}")
                    
                    if cidade_destino:
                        icms_destino = cidade_destino.icms or 0
                        print(f"[DEBUG] ✅ ICMS {cidade_destino.nome}/{uf_destino}: {icms_destino}%")
                        break

        # ✅ REFATORADO: Usa TabelaFreteManager
        dados_tabela = TabelaFreteManager.preparar_dados_tabela(opcao_escolhida)
        dados_tabela['icms_destino'] = icms_destino
        
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
            # Usa TabelaFreteManager para extrair dados da TabelaFrete do banco
            dados_banco = TabelaFreteManager.preparar_dados_tabela(tabela)
            
            # Atualiza apenas com valores não-zero do banco
            for campo, valor in dados_banco.items():
                if valor and (not dados_tabela.get(campo) or dados_tabela.get(campo) == 0):
                    dados_tabela[campo] = valor
            
            print(f"[DEBUG] ✅ Dados complementados com tabela do banco")

        print(f"[DEBUG] Dados da tabela finais: {dados_tabela}")

        # ✅ CORREÇÃO: Buscar dados corretos do banco para calcular totais
        # Em vez de usar pedidos_data do frontend, buscar do banco
        pedidos_db = []
        lote_ids_processados = set()  # Para evitar duplicação

        for pedido_data in pedidos_data:
            # Tenta pegar o separacao_lote_id de várias formas
            lote_id = pedido_data.get('separacao_lote_id') or pedido_data.get('id')

            if lote_id and lote_id not in lote_ids_processados:
                pedido_db = Pedido.query.filter_by(separacao_lote_id=lote_id).first()
                if pedido_db:
                    pedidos_db.append(pedido_db)
                    lote_ids_processados.add(lote_id)

        # Calcula totais das mercadorias usando dados do banco
        if pedidos_db:
            valor_mercadorias = sum(p.valor_saldo_total or 0 for p in pedidos_db)
            peso_total = sum(p.peso_total or 0 for p in pedidos_db)
            pallets_total = sum(p.pallet_total or 0 for p in pedidos_db)

            print(f"[DEBUG] ✅ Totais calculados do BANCO DE DADOS:")
            print(f"[DEBUG]   - {len(pedidos_db)} pedidos encontrados")
            print(f"[DEBUG]   - Valor total: R$ {valor_mercadorias:.2f}")
            print(f"[DEBUG]   - Peso total: {peso_total:.2f} kg")
            print(f"[DEBUG]   - Pallets total: {pallets_total:.2f}")

            # Debug detalhado de pallets por pedido
            for p in pedidos_db:
                print(f"[DEBUG]     Pedido {p.num_pedido}: {p.pallet_total or 0:.2f} pallets")

            # ✅ Validação adicional de sanidade
            if pallets_total < 0:
                print(f"[DEBUG] ⚠️ ERRO: Pallets negativos detectados! Ajustando para 0")
                pallets_total = 0
            elif peso_total > 0 and pallets_total > peso_total:
                print(f"[DEBUG] ⚠️ AVISO: Pallets ({pallets_total}) maior que peso ({peso_total}), possível erro de cálculo")
        else:
            # Fallback para dados do frontend se não encontrar no banco
            print(f"[DEBUG] ⚠️ AVISO: Usando dados do frontend (não encontrou no banco)")
            valor_mercadorias = sum(safe_float(p.get('valor')) for p in pedidos_data)
            peso_total = sum(safe_float(p.get('peso')) for p in pedidos_data)
            pallets_total = sum(safe_float(p.get('pallets')) for p in pedidos_data)

        # ✅ USA VALORES CORRETOS DA SESSÃO
        valor_frete_bruto = safe_float(opcao_escolhida.get('valor_total', 0))
        valor_frete_liquido = safe_float(opcao_escolhida.get('valor_liquido', 0))
        frete_por_kg = valor_frete_liquido / peso_total if peso_total > 0 else 0
        
        print(f"[DEBUG] ✅ Valores do frete (da sessão):")
        print(f"[DEBUG]   - Frete bruto: R${valor_frete_bruto:.2f}")
        print(f"[DEBUG]   - Frete líquido: R${valor_frete_liquido:.2f}")
        print(f"[DEBUG]   - Frete/kg: R${frete_por_kg:.2f}")

        # ✅ NOVO: Lógica diferente para alteração vs criação
        if embarque_existente:
            # ✅ ALTERAÇÃO DE COTAÇÃO: Atualiza embarque existente
            print(f"[DEBUG] 🔄 ALTERANDO cotação do embarque #{embarque_existente.numero}")

            # ✅ CORREÇÃO: Remove fretes sem CTe ANTES de atualizar a cotação
            # (mesma lógica do botão "Salvar Embarque" em embarques/routes.py)
            from app.embarques.routes import apagar_fretes_sem_cte_embarque
            try:
                sucesso_limpeza, resultado_limpeza = apagar_fretes_sem_cte_embarque(embarque_existente.id)
                if sucesso_limpeza:
                    print(f"[DEBUG] 🗑️ Limpeza de fretes: {resultado_limpeza}")
                else:
                    print(f"[DEBUG] ⚠️ Limpeza de fretes: {resultado_limpeza}")
            except Exception as e:
                print(f"[DEBUG] ⚠️ Erro na limpeza de fretes: {str(e)}")

            # Limpa dados antigos de cotação (conforme solicitado)
            cotacao_antiga = None
            if embarque_existente.cotacao_id:
                cotacao_antiga = db.session.get(Cotacao,embarque_existente.cotacao_id) if embarque_existente.cotacao_id else None
            
            # Atualiza dados básicos do embarque
            embarque_existente.transportadora_id = transportadora_id
            embarque_existente.tipo_carga = tipo
            embarque_existente.tipo_cotacao = data.get('tipo_cotacao', embarque_existente.tipo_cotacao)
            embarque_existente.valor_total = valor_mercadorias
            embarque_existente.peso_total = peso_total
            embarque_existente.pallet_total = pallets_total
            embarque_existente.transportadora_optante = transportadora.optante
            
            # Cria nova cotação
            cotacao = Cotacao(
                usuario_id=current_user.id,
                transportadora_id=transportadora_id,
                data_fechamento=agora_utc_naive(),
                status='Fechada',
                tipo_carga=tipo,
                valor_total=valor_mercadorias,
                peso_total=peso_total
            )
            db.session.add(cotacao)
            db.session.flush()  # Força geração do ID da cotação

            # Atualiza embarque com nova cotação
            embarque_existente.cotacao_id = cotacao.id
            
            # ✅ LIMPA E ATUALIZA DADOS DA TABELA NO LOCAL CORRETO
            if tipo == 'DIRETA':
                # ✅ CARGA DIRETA: Limpa dados antigos e atualiza no EMBARQUE
                # Usa TabelaFreteManager para atribuir campos da tabela de frete
                TabelaFreteManager.atribuir_campos_objeto(embarque_existente, dados_tabela)
                # icms_destino é atribuído separadamente (vem de localidades)
                embarque_existente.icms_destino = dados_tabela.get('icms_destino')
                
                print(f"[DEBUG] 🔄 CARGA DIRETA: Dados da tabela atualizados no EMBARQUE")
            
            # ✅ ATUALIZA DADOS DA TABELA NOS ITENS (para carga fracionada)
            if tipo == 'FRACIONADA':
                for item in embarque_existente.itens:
                    if item.status == 'ativo':  # Só atualiza itens ativos
                        # Usa TabelaFreteManager para atribuir campos da tabela de frete
                        TabelaFreteManager.atribuir_campos_objeto(item, dados_tabela)
                        # icms_destino é atribuído separadamente (vem de localidades)
                        item.icms_destino = dados_tabela.get('icms_destino')
                        
                        print(f"[DEBUG] 🔄 CARGA FRACIONADA: Dados da tabela atualizados no ITEM {item.pedido}")
            
            # Atualiza Separacao — apenas Nacom (CarVia nao tem Separacao)
            for pedido_data in pedidos_data:
                lote_id = pedido_data.get('id')
                if lote_id and str(lote_id).startswith('CARVIA-'):
                    continue  # Skip itens CarVia
                pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()
                if pedido and pedido.separacao_lote_id:
                    Separacao.atualizar_cotacao(
                        separacao_lote_id=pedido.separacao_lote_id,
                        cotacao_id=cotacao.id,
                        nf_cd=False
                    )

            # Remove cotação antiga se existir
            if cotacao_antiga:
                db.session.delete(cotacao_antiga)
                print(f"[DEBUG] 🗑️ Cotação antiga removida: ID {cotacao_antiga.id}")

            # ✅ CORREÇÃO: Recria fretes automaticamente se todas as NFs estiverem validadas
            # (mesma lógica do botão "Salvar Embarque")
            try:
                from app.fretes.routes import lancar_frete_automatico, verificar_requisitos_para_lancamento_frete
                # EmbarqueItem já importado no topo do arquivo

                # Flush para garantir que as alterações estejam visíveis
                db.session.flush()

                # Coleta CNPJs únicos dos itens ativos Nacom (exclui CarVia)
                itens_ativos = EmbarqueItem.query.filter(
                    EmbarqueItem.embarque_id == embarque_existente.id,
                    EmbarqueItem.status == 'ativo',
                    EmbarqueItem.carvia_cotacao_id.is_(None),
                    db.or_(
                        EmbarqueItem.separacao_lote_id.is_(None),
                        ~EmbarqueItem.separacao_lote_id.ilike('CARVIA-%'),
                    ),
                ).all()

                cnpjs_unicos = set()
                for item in itens_ativos:
                    if item.cnpj_cliente:
                        cnpjs_unicos.add(item.cnpj_cliente)

                fretes_criados = 0
                fretes_pendentes = 0

                for cnpj in cnpjs_unicos:
                    # Verifica se pode lançar frete para este CNPJ
                    pode_lancar, motivo = verificar_requisitos_para_lancamento_frete(
                        embarque_existente.id,
                        cnpj
                    )

                    if pode_lancar:
                        # Todas as NFs validadas - recria o frete
                        sucesso, msg = lancar_frete_automatico(
                            embarque_existente.id,
                            cnpj,
                            usuario=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
                        )
                        if sucesso:
                            fretes_criados += 1
                            print(f"[DEBUG] ✅ Frete recriado para CNPJ {cnpj}: {msg}")
                        else:
                            print(f"[DEBUG] ⚠️ Erro ao recriar frete para CNPJ {cnpj}: {msg}")
                    else:
                        fretes_pendentes += 1
                        print(f"[DEBUG] ⏳ Frete pendente para CNPJ {cnpj}: {motivo}")

                if fretes_criados > 0:
                    print(f"[DEBUG] 🎉 {fretes_criados} frete(s) recriado(s) automaticamente")
                if fretes_pendentes > 0:
                    print(f"[DEBUG] ⏳ {fretes_pendentes} frete(s) aguardando validação de NFs")

            except Exception as e:
                print(f"[DEBUG] ⚠️ Erro ao recriar fretes: {str(e)}")
                # Não falha a operação principal se a recriação de fretes falhar

            # Sinalizar que embarque precisa reimprimir (se ja foi impresso)
            embarque_existente.marcar_alterado_apos_impressao()

            embarque = embarque_existente  # Para usar nas próximas etapas

        else:
            # ✅ CRIAÇÃO NORMAL: Cria novo embarque
            print(f"[DEBUG] ✅ CRIANDO novo embarque")
            
            # ✅ CRIA COTAÇÃO
            cotacao = Cotacao(
                usuario_id=current_user.id,
                transportadora_id=transportadora_id,
                data_fechamento=agora_utc_naive(),
                status='Fechada',
                tipo_carga=tipo,
                valor_total=valor_mercadorias,
                peso_total=peso_total
            )
            db.session.add(cotacao)
            db.session.flush()  # ✅ CORREÇÃO CRÍTICA: Força geração do ID da cotação

            # Atualiza Separacao — apenas Nacom (CarVia nao tem Separacao)
            for pedido_data in pedidos_data:
                lote_id = pedido_data.get('id')
                if lote_id and str(lote_id).startswith('CARVIA-'):
                    continue  # Skip itens CarVia
                pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()
                if pedido and pedido.separacao_lote_id:
                    Separacao.atualizar_cotacao(
                        separacao_lote_id=pedido.separacao_lote_id,
                        cotacao_id=cotacao.id,
                        nf_cd=False
                    )

            # ✅ CRIA EMBARQUE
            # CORREÇÃO: Garante número único de embarque
            novo_numero = obter_proximo_numero_embarque()
            print(f"[DEBUG] 🔢 Novo número de embarque gerado: {novo_numero}")
            
            embarque = Embarque(
                transportadora_id=transportadora_id,
                status='ativo',
                numero=novo_numero,
                tipo_cotacao=data.get('tipo_cotacao', 'Automatica'),
                tipo_carga=tipo,
                valor_total=valor_mercadorias,
                peso_total=peso_total,
                pallet_total=pallets_total,
                criado_em=agora_utc_naive(),
                criado_por=current_user.nome,
                cotacao_id=cotacao.id,
                transportadora_optante=transportadora.optante
            )

            # ✅ CORREÇÃO PRINCIPAL: SALVA DADOS DA TABELA NO LOCAL CORRETO
            if tipo == 'DIRETA':
                # ✅ CARGA DIRETA: Dados da tabela vão para o EMBARQUE
                # Usa TabelaFreteManager para atribuir campos da tabela de frete
                TabelaFreteManager.atribuir_campos_objeto(embarque, dados_tabela)
                # icms_destino é atribuído separadamente (vem de localidades)
                embarque.icms_destino = dados_tabela.get('icms_destino')
                
                print(f"[DEBUG] ✅ CARGA DIRETA: Dados da tabela salvos no EMBARQUE")
            
            db.session.add(embarque)
            db.session.flush()  # Para obter o ID do embarque

            # 🚚 RASTREAMENTO GPS: Cria rastreamento APENAS para carga DIRETA
            if tipo == 'DIRETA':
                try:
                    rastreamento = RastreamentoEmbarque(
                        embarque_id=embarque.id,
                        criado_por=current_user.nome
                    )
                    db.session.add(rastreamento)
                    db.session.flush()  # Gera ID do rastreamento

                    # Criar EntregaRastreada para cada item (após criar EmbarqueItems)
                    # Será executado depois do loop de criação de itens
                    print(f"[DEBUG] 🚚 Rastreamento GPS criado para embarque DIRETA #{embarque.numero}")
                except Exception as e:
                    print(f"[DEBUG] ⚠️ Erro ao criar rastreamento GPS: {str(e)}")
                    db.session.rollback()
                    # Não falha a criação do embarque se rastreamento falhar
            else:
                print(f"[DEBUG] ⚠️ Rastreamento GPS NÃO criado - embarque é FRACIONADA")

            # Cria EmbarqueItems — separando Nacom de CarVia
            for pedido_data in pedidos_data:
                lote_id = pedido_data.get('id')
                pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()
                if not pedido:
                    continue

                eh_carvia = str(lote_id or '').startswith('CARVIA-')

                if eh_carvia:
                    # --- CarVia: EmbarqueItem PROVISORIO ---
                    uf_cv = (pedido.cod_uf or '').strip()
                    cidade_cv = (pedido.nome_cidade or '').strip()

                    carvia_cot_id = None
                    try:
                        if str(lote_id).startswith('CARVIA-PED-'):
                            ped_id = int(str(lote_id).replace('CARVIA-PED-', ''))
                            from app.carvia.models import CarviaPedido as _CP
                            _ped = db.session.get(_CP, ped_id)
                            carvia_cot_id = _ped.cotacao_id if _ped else None
                        elif str(lote_id).startswith('CARVIA-'):
                            carvia_cot_id = int(str(lote_id).replace('CARVIA-', ''))
                    except (ValueError, TypeError):
                        pass

                    # Calcular volumes e peso cubado das motos da cotacao
                    carvia_volumes = None
                    carvia_peso_cubado = None
                    if carvia_cot_id:
                        try:
                            from app.carvia.models import CarviaCotacaoMoto
                            agg = db.session.query(
                                db.func.coalesce(db.func.sum(CarviaCotacaoMoto.quantidade), 0),
                                db.func.coalesce(db.func.sum(CarviaCotacaoMoto.peso_cubado_total), 0),
                            ).filter_by(cotacao_id=carvia_cot_id).first()
                            carvia_volumes = int(agg[0]) or None
                            carvia_peso_cubado = float(agg[1]) or None
                        except Exception:
                            pass

                    # FIX CR3: Detectar multi-NF vinda de string_agg (Parte 2B).
                    # View usa string_agg(DISTINCT pi.numero_nf, ', ') — pedidos com
                    # 2+ NFs retornam "NF1, NF2". Tratamos como provisorio e deixamos
                    # o FIX CR2 (auto-expand apos commit) criar um EmbarqueItem real
                    # por NF individual via expandir_provisorio.
                    _nf_raw = (pedido.nf or '').strip()
                    _eh_multi_nf = ',' in _nf_raw
                    _nota_fiscal_unica = _nf_raw if _nf_raw and not _eh_multi_nf else None

                    item = EmbarqueItem(
                        embarque_id=embarque.id,
                        separacao_lote_id=pedido.separacao_lote_id,
                        cnpj_cliente=pedido.cnpj_cpf,
                        cliente=pedido.raz_social_red,
                        pedido=pedido.num_pedido,
                        nota_fiscal=_nota_fiscal_unica,
                        peso=pedido.peso_total or 0,
                        peso_cubado=carvia_peso_cubado,
                        valor=pedido.valor_saldo_total or 0,
                        pallets=0,
                        uf_destino=uf_cv,
                        cidade_destino=cidade_cv,
                        volumes=carvia_volumes,
                        provisorio=(_nota_fiscal_unica is None),
                        carvia_cotacao_id=carvia_cot_id,
                    )
                    if tipo == 'FRACIONADA':
                        TabelaFreteManager.atribuir_campos_objeto(item, dados_tabela)
                        item.icms_destino = dados_tabela.get('icms_destino')
                    db.session.add(item)
                    if _eh_multi_nf:
                        print(f"[DEBUG] ✅ CarVia MULTI-NF (provisorio): {pedido.num_pedido} → {_nf_raw} ({cidade_cv}/{uf_cv})")
                    elif _nota_fiscal_unica:
                        print(f"[DEBUG] ✅ CarVia REAL: {pedido.num_pedido} NF={_nota_fiscal_unica} → {cidade_cv}/{uf_cv}")
                    else:
                        print(f"[DEBUG] ✅ CarVia PROVISORIO: {pedido.num_pedido} → {cidade_cv}/{uf_cv}")

                else:
                    # --- Nacom: fluxo existente ---
                    cidade_formatada, uf_correto = LocalizacaoService.obter_cidade_destino_embarque(pedido)

                    protocolo_formatado = formatar_protocolo(pedido.protocolo)
                    data_formatada = formatar_data_brasileira(pedido.agendamento)

                    nota_fiscal = None
                    if pedido.separacao_lote_id and pedido.num_pedido:
                        separacao_com_nf = Separacao.query.filter_by(
                            separacao_lote_id=pedido.separacao_lote_id,
                            num_pedido=pedido.num_pedido
                        ).filter(Separacao.numero_nf.isnot(None)).first()
                        if separacao_com_nf:
                            nota_fiscal = separacao_com_nf.numero_nf
                            print(f"[DEBUG] 📄 NF encontrada para pedido {pedido.num_pedido}: {nota_fiscal}")

                    item = EmbarqueItem(
                        embarque_id=embarque.id,
                        separacao_lote_id=pedido.separacao_lote_id,
                        cnpj_cliente=pedido.cnpj_cpf,
                        cliente=pedido.raz_social_red,
                        pedido=pedido.num_pedido,
                        nota_fiscal=nota_fiscal,
                        peso=pedido.peso_total,
                        valor=pedido.valor_saldo_total,
                        pallets=pedido.pallet_total,
                        uf_destino=uf_correto,
                        cidade_destino=cidade_formatada,
                        volumes=None,
                        protocolo_agendamento=protocolo_formatado,
                        data_agenda=data_formatada
                    )
                    if tipo == 'FRACIONADA':
                        TabelaFreteManager.atribuir_campos_objeto(item, dados_tabela)
                        item.icms_destino = dados_tabela.get('icms_destino')
                        print(f"[DEBUG] ✅ CARGA FRACIONADA: tabela salvos no EMBARQUE_ITEM {pedido.num_pedido}")
                    db.session.add(item)

        db.session.commit()

        # FIX CR2: Auto-expandir provisorios CarVia cuja cotacao ja tem NFs anexadas.
        # Metodo extraido em EmbarqueCarViaService.auto_expandir_provisorios().
        try:
            from app.carvia.services.documentos.embarque_carvia_service import (
                EmbarqueCarViaService,
            )
            EmbarqueCarViaService.auto_expandir_provisorios(embarque)
        except Exception as e_cr2:
            print(f"[DEBUG] ⚠️ CR2 auto-expand: {e_cr2}")

        # Propagar cotacao_id para Separacao — apenas Nacom (CarVia nao tem Separacao)
        for item in embarque.itens:
            if item.separacao_lote_id and item.status == 'ativo':
                if str(item.separacao_lote_id).startswith('CARVIA-'):
                    continue  # Skip itens CarVia provisorios
                Separacao.atualizar_cotacao(
                    separacao_lote_id=item.separacao_lote_id,
                    cotacao_id=cotacao.id,
                    nf_cd=False
                )
                print(f"[DEBUG] ✅ Separacao lote {item.separacao_lote_id} atualizado com cotacao_id={cotacao.id}")

        db.session.commit()

        # 🚚 CRIAR ENTREGAS RASTREADAS (após commit dos EmbarqueItems)
        if tipo == 'DIRETA' and embarque.rastreamento:
            try:
                from app.rastreamento.services.entrega_rastreada_service import EntregaRastreadaService
                entregas_criadas = EntregaRastreadaService.criar_entregas_para_embarque(
                    embarque.rastreamento.id,
                    embarque.id
                )
                db.session.commit()
                print(f"[DEBUG] ✅ {len(entregas_criadas)} entregas rastreadas criadas para embarque #{embarque.numero}")
            except Exception as e:
                print(f"[DEBUG] ⚠️ Erro ao criar entregas rastreadas: {str(e)}")
                # Não falha a criação do embarque

        # ✅ LIMPA DADOS DA SESSÃO APÓS SUCESSO
        if alterando_embarque:
            session.pop('alterando_embarque', None)
            mensagem = f'Cotação do embarque #{embarque.numero} alterada com sucesso'
            print(f"[DEBUG] ✅ {mensagem}")
        else:
            mensagem = 'Cotação e embarque criados com sucesso'
            print(f"[DEBUG] ✅ {mensagem}")

        return jsonify({
            'success': True,
            'message': mensagem,
            'redirect_url': url_for('cotacao.resumo_frete', cotacao_id=cotacao.id)
        })

    except Exception as e:
        db.session.rollback()
        from flask import current_app
        current_app.logger.error(f"Erro em fechar_frete: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Erro ao criar/alterar embarque: {str(e)}'
        }), 500

@cotacao_bp.route("/fechar_frete_grupo", methods=["POST"])
@login_required
def fechar_frete_grupo():
    """
    Fechar fretes por grupo - versão corrigida com dados da tabela nos locais corretos
    """
    try:
        # ✅ PROTEÇÃO CONTRA DUPLICAÇÃO: Advisory lock PostgreSQL
        from sqlalchemy import text
        
        # ✅ CORREÇÃO: Aceita tanto JSON quanto form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
            # Converte strings para listas quando necessário
            if 'cnpjs' in data and isinstance(data['cnpjs'], str):
                import json
                try:
                    data['cnpjs'] = json.loads(data['cnpjs'])
                except Exception as e:
                    data['cnpjs'] = [data['cnpjs']]
        
        if not data:
            return jsonify({'success': False, 'message': 'Dados inválidos'}), 400
        
        # ✅ NOVO: Cria hash único para o conjunto de CNPJs para lock
        cnpjs = data.get('cnpjs', [])
        if cnpjs:
            # Cria uma string única ordenada com os CNPJs
            lock_key = '_'.join(sorted(cnpjs))
            # Usa advisory lock para evitar processamento simultâneo do mesmo conjunto
            db.session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {'key': f'fechar_frete_{lock_key}'})
            print(f"[DEBUG] 🔒 Advisory lock obtido para CNPJs: {lock_key[:50]}...")
        
        tipo = data.get('tipo', 'FRACIONADA')
        transportadora_id = data.get('transportadora_id')
        cnpjs = data.get('cnpjs', [])
        
        if not cnpjs and 'pedidos' in data:
            pedidos_data = data.get('pedidos', [])
            cnpjs = list(set(p.get('cnpj') for p in pedidos_data if p.get('cnpj')))

        if not cnpjs:
            lista_ids = session.get("cotacao_pedidos", [])
            if lista_ids:
                # Usar separacao_lote_id em vez de id (Pedido agora é VIEW)
                pedidos_sessao = Pedido.query.filter(Pedido.separacao_lote_id.in_(lista_ids)).all()
                cnpjs = list(set(p.cnpj_cpf for p in pedidos_sessao))

        if not transportadora_id or not cnpjs:
            return jsonify({'success': False, 'message': 'Dados incompletos'}), 400

        transportadora = db.session.get(Transportadora,transportadora_id) if transportadora_id else None
        if not transportadora:
            return jsonify({'success': False, 'message': 'Transportadora não encontrada'}), 404

        # Busca todos os pedidos dos CNPJs
        todos_pedidos = []
        for cnpj in cnpjs:
            lista_ids = session.get("cotacao_pedidos", [])
            pedidos_cnpj = Pedido.query.filter(
                Pedido.cnpj_cpf == cnpj,
                Pedido.separacao_lote_id.in_(lista_ids)
            ).all()
            todos_pedidos.extend(pedidos_cnpj)

        if not todos_pedidos:
            return jsonify({'success': False, 'message': 'Nenhum pedido encontrado'}), 400

        # Calcula totais
        valor_total = sum(p.valor_saldo_total or 0 for p in todos_pedidos)
        peso_total = sum(p.peso_total or 0 for p in todos_pedidos)
        pallets_total = sum(p.pallet_total or 0 for p in todos_pedidos)

        print(f"[DEBUG] ✅ FECHAR_FRETE_GRUPO - Totais calculados do BANCO:")
        print(f"[DEBUG]   - {len(todos_pedidos)} pedidos processados")
        print(f"[DEBUG]   - Valor total: R$ {valor_total:.2f}")
        print(f"[DEBUG]   - Peso total: {peso_total:.2f} kg")
        print(f"[DEBUG]   - Pallets total: {pallets_total:.2f}")

        # Debug detalhado de pallets por pedido
        for p in todos_pedidos:
            print(f"[DEBUG]     Pedido {p.num_pedido}: {p.pallet_total or 0:.2f} pallets")

        # ✅ Validação adicional de sanidade
        if pallets_total < 0:
            print(f"[DEBUG] ⚠️ ERRO: Pallets negativos detectados! Ajustando para 0")
            pallets_total = 0
        elif peso_total > 0 and pallets_total > peso_total:
            print(f"[DEBUG] ⚠️ AVISO: Pallets ({pallets_total}) maior que peso ({peso_total}), possível erro de cálculo")
        # ✅ NOVO: Verifica se já existe embarque recente (últimos 10 segundos) com os mesmos pedidos
        from datetime import timedelta
        tempo_limite = agora_utc_naive() - timedelta(seconds=10)
        
        # Busca os números de pedidos
        numeros_pedidos = sorted([p.num_pedido for p in todos_pedidos])
        
        # Verifica embarques recentes
        embarques_recentes = Embarque.query.filter(
            Embarque.transportadora_id == transportadora_id,
            Embarque.criado_em >= tempo_limite,
            Embarque.status == 'ativo'
        ).all()
        
        for emb_rec in embarques_recentes:
            # Busca os pedidos deste embarque
            itens_emb = EmbarqueItem.query.filter_by(embarque_id=emb_rec.id).all()
            pedidos_emb = sorted([item.pedido for item in itens_emb])
            
            # Se tem os mesmos pedidos, é duplicação
            if pedidos_emb == numeros_pedidos:
                print(f"[DEBUG] ⚠️ Embarque duplicado detectado! ID: {emb_rec.id}, Número: {emb_rec.numero}")
                return jsonify({
                    'success': True,  # Retorna sucesso para não mostrar erro ao usuário
                    'message': 'Embarque já foi criado',
                    'redirect_url': url_for('cotacao.resumo_frete', cotacao_id=emb_rec.cotacao_id)
                })

        # Cria cotação
        cotacao = Cotacao(
            usuario_id=current_user.id,
            transportadora_id=transportadora_id,
            data_fechamento=agora_utc_naive(),
            status='Fechada',
            tipo_carga=tipo,
            valor_total=valor_total,
            peso_total=peso_total
        )
        db.session.add(cotacao)
        db.session.flush()  # ✅ CORREÇÃO CRÍTICA: Força geração do ID da cotação

        # Atualiza Separacao — apenas Nacom (CarVia nao tem Separacao)
        for pedido in todos_pedidos:
            if pedido.separacao_lote_id and not str(pedido.separacao_lote_id).startswith('CARVIA-'):
                Separacao.query.filter_by(
                    separacao_lote_id=pedido.separacao_lote_id
                ).update({
                    'cotacao_id': cotacao.id,
                    'nf_cd': False
                })

        # ✅ NOVA LÓGICA: Recebe dados COMPLETOS das tabelas do frontend (payload)
        tabelas_por_cnpj = data.get('tabelas_por_cnpj', {})

        print(f"[DEBUG] === RECEBENDO DADOS DAS TABELAS POR CNPJ DO PAYLOAD ===")

        # ✅ VALIDAÇÃO CRÍTICA: Garante que tabelas foram enviadas
        if not tabelas_por_cnpj:
            print(f"[DEBUG] ❌ ERRO: tabelas_por_cnpj não foi enviado no payload!")
            return jsonify({
                'success': False,
                'message': 'Dados das tabelas por CNPJ não foram enviados. Recarregue a página e tente novamente.'
            }), 400

        # ✅ VALIDAÇÃO: Verifica se TODOS os CNPJs têm tabela
        cnpjs_sem_tabela = []
        for cnpj in cnpjs:
            if cnpj not in tabelas_por_cnpj:
                cnpjs_sem_tabela.append(cnpj)

        if cnpjs_sem_tabela:
            print(f"[DEBUG] ❌ ERRO: CNPJs sem tabela: {cnpjs_sem_tabela}")
            return jsonify({
                'success': False,
                'message': f'Dados da tabela não encontrados para os CNPJs: {", ".join(cnpjs_sem_tabela)}'
            }), 400

        # ✅ USA DADOS DO PAYLOAD em vez da session
        dados_tabela_por_cnpj = {}
        for cnpj in cnpjs:
            dados_tabela_por_cnpj[cnpj] = tabelas_por_cnpj[cnpj].copy()
            print(f"[DEBUG] ✅ Tabela recebida do PAYLOAD para CNPJ {cnpj}: {dados_tabela_por_cnpj[cnpj].get('nome_tabela')}")

        # ✅ DEBUG: Compara com session para detectar divergências (opcional)
        resultados = session.get('resultados', {})
        if 'fracionadas' in resultados:
            for cnpj in cnpjs:
                if cnpj in resultados['fracionadas']:
                    opcoes_cnpj = resultados['fracionadas'][cnpj]
                    if opcoes_cnpj and len(opcoes_cnpj) > 0:
                        melhor_opcao_session = None
                        for opcao in opcoes_cnpj:
                            if opcao.get('transportadora_id') == transportadora_id:
                                melhor_opcao_session = opcao
                                break

                        if melhor_opcao_session:
                            nome_tabela_session = melhor_opcao_session.get('nome_tabela')
                            nome_tabela_payload = dados_tabela_por_cnpj[cnpj].get('nome_tabela')

                            if nome_tabela_session != nome_tabela_payload:
                                print(f"[DEBUG] ⚠️ ALERTA: Tabela DIFERENTE para CNPJ {cnpj}")
                                print(f"[DEBUG]   - Payload: {nome_tabela_payload}")
                                print(f"[DEBUG]   - Session: {nome_tabela_session}")
                            else:
                                print(f"[DEBUG] ✅ Validação OK para CNPJ {cnpj}: Tabela no payload = session")
        
        # Cria embarque
        embarque = Embarque(
            transportadora_id=transportadora_id,
            status='ativo',
            numero=obter_proximo_numero_embarque(),
            tipo_cotacao='Automatica',
            tipo_carga=tipo,
            valor_total=valor_total,
            peso_total=peso_total,
            pallet_total=pallets_total,
            criado_em=agora_utc_naive(),
            criado_por=current_user.nome,
            cotacao_id=cotacao.id,
            transportadora_optante=transportadora.optante
        )

        # ✅ CORREÇÃO: NÃO SALVA DADOS DA TABELA NO EMBARQUE PARA CARGAS FRACIONADAS
        print(f"[DEBUG] ✅ CARGA FRACIONADA GRUPO: Dados da tabela irão para os EMBARQUE_ITENS")
        
        db.session.add(embarque)
        db.session.flush()

        # 🚚 RASTREAMENTO GPS: Cria rastreamento automaticamente
        try:
            rastreamento = RastreamentoEmbarque(
                embarque_id=embarque.id,
                criado_por=current_user.nome
            )
            db.session.add(rastreamento)
            print(f"[DEBUG] 🚚 Rastreamento GPS criado para embarque #{embarque.numero}")
        except Exception as e:
            print(f"[DEBUG] ⚠️ Erro ao criar rastreamento GPS: {str(e)}")
            # Não falha a criação do embarque se rastreamento falhar

        # Cria EmbarqueItems — separando Nacom de CarVia
        for pedido in todos_pedidos:
            eh_carvia = str(pedido.separacao_lote_id or '').startswith('CARVIA-')

            if eh_carvia:
                # --- CarVia: EmbarqueItem PROVISORIO ---
                uf_cv = (pedido.cod_uf or '').strip()
                cidade_cv = (pedido.nome_cidade or '').strip()

                carvia_cot_id = None
                try:
                    lote_id = str(pedido.separacao_lote_id)
                    if lote_id.startswith('CARVIA-PED-'):
                        ped_id = int(lote_id.replace('CARVIA-PED-', ''))
                        from app.carvia.models import CarviaPedido as _CP
                        _ped = db.session.get(_CP, ped_id)
                        carvia_cot_id = _ped.cotacao_id if _ped else None
                    elif lote_id.startswith('CARVIA-'):
                        carvia_cot_id = int(lote_id.replace('CARVIA-', ''))
                except (ValueError, TypeError):
                    pass

                # FIX CR3: Detectar multi-NF vinda de string_agg (Parte 2B).
                # View usa string_agg(DISTINCT pi.numero_nf, ', ') — pedidos com
                # 2+ NFs retornam "NF1, NF2". Tratamos como provisorio e deixamos
                # o FIX CR2 (auto-expand apos commit) criar um EmbarqueItem real
                # por NF individual via expandir_provisorio.
                _nf_raw = (pedido.nf or '').strip()
                _eh_multi_nf = ',' in _nf_raw
                _nota_fiscal_unica = _nf_raw if _nf_raw and not _eh_multi_nf else None

                item = EmbarqueItem(
                    embarque_id=embarque.id,
                    separacao_lote_id=pedido.separacao_lote_id,
                    cnpj_cliente=pedido.cnpj_cpf,
                    cliente=pedido.raz_social_red,
                    pedido=pedido.num_pedido,
                    nota_fiscal=_nota_fiscal_unica,
                    peso=pedido.peso_total or 0,
                    valor=pedido.valor_saldo_total or 0,
                    pallets=0,
                    uf_destino=uf_cv,
                    cidade_destino=cidade_cv,
                    volumes=None,
                    provisorio=(_nota_fiscal_unica is None),
                    carvia_cotacao_id=carvia_cot_id,
                )
                if tipo == 'FRACIONADA' and pedido.cnpj_cpf in dados_tabela_por_cnpj:
                    dados_tabela = dados_tabela_por_cnpj[pedido.cnpj_cpf]
                    TabelaFreteManager.atribuir_campos_objeto(item, dados_tabela)
                    item.icms_destino = dados_tabela.get('icms_destino', 0)
                db.session.add(item)
                if _eh_multi_nf:
                    print(f"[DEBUG] CarVia MULTI-NF grupo (provisorio): {pedido.num_pedido} → {_nf_raw} ({cidade_cv}/{uf_cv})")
                elif _nota_fiscal_unica:
                    print(f"[DEBUG] CarVia REAL (grupo): {pedido.num_pedido} NF={_nota_fiscal_unica} → {cidade_cv}/{uf_cv}")
                else:
                    print(f"[DEBUG] CarVia PROVISORIO (grupo): {pedido.num_pedido} → {cidade_cv}/{uf_cv}")

            else:
                # --- Nacom: fluxo existente ---
                cidade_formatada, uf_correto = LocalizacaoService.obter_cidade_destino_embarque(pedido)

                nota_fiscal = None
                if pedido.separacao_lote_id and pedido.num_pedido:
                    separacao_com_nf = Separacao.query.filter_by(
                        separacao_lote_id=pedido.separacao_lote_id,
                        num_pedido=pedido.num_pedido
                    ).filter(Separacao.numero_nf.isnot(None)).first()
                    if separacao_com_nf:
                        nota_fiscal = separacao_com_nf.numero_nf

                item = EmbarqueItem(
                    embarque_id=embarque.id,
                    separacao_lote_id=pedido.separacao_lote_id,
                    cnpj_cliente=pedido.cnpj_cpf,
                    cliente=pedido.raz_social_red,
                    pedido=pedido.num_pedido,
                    nota_fiscal=nota_fiscal,
                    peso=pedido.peso_total,
                    valor=pedido.valor_saldo_total,
                    pallets=pedido.pallet_total,
                    uf_destino=uf_correto,
                    cidade_destino=cidade_formatada,
                    volumes=None,
                    protocolo_agendamento=formatar_protocolo(pedido.protocolo),
                    data_agenda=formatar_data_brasileira(pedido.agendamento)
                )
                if tipo == 'FRACIONADA' and pedido.cnpj_cpf in dados_tabela_por_cnpj:
                    dados_tabela = dados_tabela_por_cnpj[pedido.cnpj_cpf]
                    TabelaFreteManager.atribuir_campos_objeto(item, dados_tabela)
                    item.icms_destino = dados_tabela.get('icms_destino', 0)
                db.session.add(item)

        db.session.commit()

        # FIX CR2: Auto-expandir provisorios CarVia cuja cotacao ja tem NFs anexadas.
        # Metodo extraido em EmbarqueCarViaService.auto_expandir_provisorios().
        try:
            from app.carvia.services.documentos.embarque_carvia_service import (
                EmbarqueCarViaService,
            )
            EmbarqueCarViaService.auto_expandir_provisorios(embarque)
        except Exception as e_cr2:
            print(f"[DEBUG] ⚠️ CR2 auto-expand: {e_cr2}")

        # Propagar cotacao_id para Separacao — apenas Nacom (CarVia nao tem Separacao)
        for item in embarque.itens:
            if item.separacao_lote_id and item.status == 'ativo':
                if str(item.separacao_lote_id).startswith('CARVIA-'):
                    continue  # Skip itens CarVia provisorios
                Separacao.atualizar_cotacao(
                    separacao_lote_id=item.separacao_lote_id,
                    cotacao_id=cotacao.id,
                    nf_cd=False
                )
                print(f"[DEBUG] ✅ Separacao lote {item.separacao_lote_id} atualizado com cotacao_id={cotacao.id}")

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Cotação e embarque criados com sucesso',
            'redirect_url': url_for('cotacao.resumo_frete', cotacao_id=cotacao.id)
        })

    except Exception as e:
        db.session.rollback()
        from flask import current_app
        current_app.logger.error(f"Erro em fechar_frete_grupo: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Erro ao criar embarque: {str(e)}'
        }), 500

# Importa função centralizada thread-safe

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
        pedidos = Pedido.query.filter(Pedido.separacao_lote_id.in_(lista_ids)).all()
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
                (Pedido.cod_uf == 'SP') 
            ).filter(~Pedido.separacao_lote_id.in_(lista_ids)).filter(
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
                uf_efetivo = pedido.cod_uf
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
                    (Pedido.cod_uf == uf_principal)
                ).filter(~Pedido.separacao_lote_id.in_(lista_ids)).filter(
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
        pallets_total = sum(p.pallet_total or 0 for p in pedidos)
        valor_liquido = opcao_atual.get('valor_liquido', 0)
        frete_atual_kg = valor_liquido / peso_total if peso_total > 0 else 0
        
        print(f"[OTIMIZADOR] 📊 Dados atuais: {transportadora} | {modalidade} | {peso_total}kg | R$/kg: {frete_atual_kg:.2f}")
        print(f"[OTIMIZADOR] 📦 Pedidos atuais: {len(pedidos)} | Pedidos disponíveis: {len(pedidos_mesmo_uf)}")

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
                        except Exception as e:
                            pass
                
                # ✅ ALTERAÇÃO PRINCIPAL: Força UF=SP e cidade=Guarulhos
                pedido_copia.cod_uf = 'SP'
                pedido_copia.nome_cidade = 'Guarulhos'
                pedido_copia.rota = 'CIF'  # Força para não ser RED
                
                pedidos_para_calculo.append(pedido_copia)
                print(f"[DEBUG] 📍 Convertido: {pedido_original.num_pedido} → Guarulhos/SP")
        
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
                    otimizacoes['remover'][pedido.separacao_lote_id] = resultado
                    pass  # Otimização encontrada
                else:
                    pass  # Nenhuma otimização encontrada
                    # Cria uma otimização básica para mostrar dados atuais
                    otimizacoes['remover'][pedido.separacao_lote_id] = {
                        'frete_kg_atual': frete_atual_kg,
                        'peso_pedido': pedido.peso_total or 0,
                        'sem_otimizacao': True,
                        'transportadora_atual': transportadora,
                        'modalidade_atual': modalidade,
                        'valor_liquido_atual': valor_liquido
                    }
            except Exception as e:
                print(f"[DEBUG] ❌ Erro ao calcular otimização para pedido {pedido.num_pedido}: {str(e)}")
                # Cria uma otimização básica mesmo com erro
                otimizacoes['remover'][pedido.separacao_lote_id] = {
                    'frete_kg_atual': frete_atual_kg,
                    'peso_pedido': pedido.peso_total or 0,
                    'erro': str(e),
                    'transportadora_atual': transportadora,
                    'modalidade_atual': modalidade,
                    'valor_liquido_atual': valor_liquido
                }

        # Calcula otimizações para pedidos que podem ser adicionados
        # ✅ CORREÇÃO: Remove limitação artificial e otimiza para performance
        max_otimizacoes = min(len(pedidos_mesmo_uf), 100)  # Limite dinâmico mais realista
        print(f"[OTIMIZADOR] 🔄 Processando {max_otimizacoes} de {len(pedidos_mesmo_uf)} pedidos para adicionar")
        
        for pedido in pedidos_mesmo_uf[:max_otimizacoes]:
            try:
                resultado = calcular_otimizacoes_pedido_adicional(pedido, pedidos_para_calculo, transportadora, modalidade, peso_total, veiculos, frete_atual_kg)
                if resultado:
                    otimizacoes['adicionar'][pedido.separacao_lote_id] = resultado
                    pass  # Otimização encontrada  
                else:
                    pass  # Nenhuma otimização encontrada
                    # Cria uma otimização básica para mostrar dados atuais
                    otimizacoes['adicionar'][pedido.separacao_lote_id] = {
                        'frete_kg_atual': frete_atual_kg,
                        'peso_pedido': pedido.peso_total or 0,
                        'sem_otimizacao': True,
                        'transportadora_atual': transportadora,
                        'modalidade_atual': modalidade,
                        'valor_liquido_atual': valor_liquido
                    }
            except Exception as e:
                print(f"[DEBUG] ❌ Erro ao calcular otimização para adicionar pedido {pedido.num_pedido}: {str(e)}")
                # Cria uma otimização básica mesmo com erro
                otimizacoes['adicionar'][pedido.separacao_lote_id] = {
                    'frete_kg_atual': frete_atual_kg,
                    'peso_pedido': pedido.peso_total or 0,
                    'erro': str(e),
                    'transportadora_atual': transportadora,
                    'modalidade_atual': modalidade,
                    'valor_liquido_atual': valor_liquido
                }
        
        print(f"[OTIMIZADOR] ✅ Finalizado: {len(otimizacoes['remover'])} otimizações de remoção | {len(otimizacoes['adicionar'])} otimizações de adição")

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
            
            # ✅ REFATORADO: Usa TabelaFreteManager
            dados_tabela = TabelaFreteManager.preparar_dados_tabela(embarque)
            
            # Calcula frete para toda a carga
            resultado_frete = CalculadoraFrete.calcular_frete_unificado(
                peso=peso_total,
                valor_mercadoria=valor_mercadorias,
                tabela_dados=dados_tabela,
                transportadora_optante=embarque.transportadora_optante or False
            )
            
            valor_frete_bruto = float(resultado_frete['valor_bruto'])
            valor_frete_liquido = float(resultado_frete['valor_liquido'])
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
                    # Usa TabelaFreteManager para extrair dados do item
                    itens_por_cnpj_calculo[cnpj]['dados_tabela'] = TabelaFreteManager.preparar_dados_tabela(item)
                    # Adiciona icms_destino separadamente
                    itens_por_cnpj_calculo[cnpj]['dados_tabela']['icms_destino'] = getattr(item, 'icms_destino', 0)
            
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
                    
                    valor_frete_bruto += float(resultado_frete_cnpj['valor_com_icms'])  # ✅ CORREÇÃO: Usar valor COM ICMS
                    valor_frete_liquido += float(resultado_frete_cnpj['valor_bruto'])   # ✅ CORREÇÃO: Usar valor SEM ICMS
                    cnpjs_calculados += 1
                    
                    print(f"[DEBUG]   ✅ CNPJ {cnpj} (Peso: {peso_cnpj}kg, Valor: R${valor_cnpj:.2f}): R${resultado_frete_cnpj['valor_bruto']:.2f} (SEM ICMS), R${resultado_frete_cnpj['valor_com_icms']:.2f} (COM ICMS)")
                    
                else:
                    # Fallback: Dados do embarque ou cálculo básico
                    if embarque and hasattr(embarque, 'tabela_nome_tabela') and embarque.tabela_nome_tabela:
                        # Usa TabelaFreteManager para extrair dados do embarque
                        dados_tabela_fallback = TabelaFreteManager.preparar_dados_tabela(embarque)
                        # Adiciona icms_destino separadamente
                        dados_tabela_fallback['icms_destino'] = getattr(embarque, 'icms_destino', 0)
                        
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
                dados_tabela_temp = TabelaFreteManager.preparar_dados_tabela(embarque)
                item.nome_tabela = dados_tabela_temp.get('nome_tabela', 'N/A')
                item.modalidade = dados_tabela_temp.get('modalidade', 'FRETE PESO')
                item.valor_kg = dados_tabela_temp.get('valor_kg', 0)
                item.icms_destino = getattr(embarque, 'icms_destino', 0)
            else:
                # Para carga fracionada, usa dados do próprio item
                if not hasattr(item, 'nome_tabela') or not item.nome_tabela:
                    dados_tabela_temp = TabelaFreteManager.preparar_dados_tabela(item)
                    item.nome_tabela = dados_tabela_temp.get('nome_tabela', 'N/A')
                    item.modalidade = dados_tabela_temp.get('modalidade', 'FRETE PESO')
                    item.valor_kg = dados_tabela_temp.get('valor_kg', 0)
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
                # Usa dados da tabela salvos no item - extrai com TabelaFreteManager
                dados_tabela_cnpj = TabelaFreteManager.preparar_dados_tabela(grupo['itens'][0])
                # Adiciona icms_destino separadamente
                dados_tabela_cnpj['icms_destino'] = getattr(grupo['itens'][0], 'icms_destino', 0)
                
                resultado_cnpj = CalculadoraFrete.calcular_frete_unificado(
                    peso=grupo['peso_total'],
                    valor_mercadoria=grupo['valor_total'],
                    tabela_dados=dados_tabela_cnpj,
                    transportadora_optante=(embarque and embarque.transportadora_optante) or False
                )
                
                grupo['frete_calculado']['valor_total'] = float(resultado_cnpj['valor_com_icms'])  # ✅ CORREÇÃO: COM ICMS
                grupo['frete_calculado']['valor_liquido'] = float(resultado_cnpj['valor_bruto'])   # ✅ CORREÇÃO: SEM ICMS
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
        
        # Verifica se todos são do mesmo UF
        ufs_encontrados = set(pedido.cod_uf for pedido in pedidos)
        
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
            # Busca cidade do pedido
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
        # Agrupa vínculos por transportadora + UF + modalidade
        combinacoes_transporte = {}  # (transportadora_id, uf_destino, modalidade) -> [tabelas]
        
        for vinculo in vinculos:
            tabelas = TabelaFrete.query.filter(
                TabelaFrete.transportadora_id == vinculo.transportadora_id,
                TabelaFrete.nome_tabela == vinculo.nome_tabela,
                TabelaFrete.tipo_carga == 'DIRETA'  # ✅ FILTRO: Apenas tabelas DIRETA
            ).all()
            
            for tabela in tabelas:
                modalidade = tabela.modalidade or 'FRETE PESO'
                # ✅ NOVA CHAVE: Inclui UF de destino
                chave = (tabela.transportadora_id, tabela.uf_destino, modalidade)
                
                if chave not in combinacoes_transporte:
                    combinacoes_transporte[chave] = []
                combinacoes_transporte[chave].append({
                    'tabela': tabela,
                    'cidade_id': vinculo.cidade_id
                })
        
        print(f"[DEBUG] ✅ Combinações transportadora/modalidade: {len(combinacoes_transporte)}")
        
        # REGRA 11: Descarta opções que não atendem TODAS as cidades
        combinacoes_validas = {}
        
        for (transportadora_id, uf_destino, modalidade), dados in combinacoes_transporte.items():
            # Verifica se esta combinação atende TODAS as cidades cotadas
            cidades_atendidas = set(item['cidade_id'] for item in dados)
            
            if cidades_atendidas.issuperset(cidades_cotadas):
                combinacoes_validas[(transportadora_id, uf_destino, modalidade)] = dados
                print(f"[DEBUG] ✅ Combinação válida: Transp {transportadora_id}, UF {uf_destino}, Modal {modalidade}")
            else:
                print(f"[DEBUG] ❌ Combinação descartada: Transp {transportadora_id}, UF {uf_destino}, Modal {modalidade} - não atende todas as cidades")
        
        if not combinacoes_validas:
            print("[DEBUG] ❌ Nenhuma combinação atende todas as cidades")
            return {'diretas': [], 'fracionadas': {}}
        
        # REGRA 12: Descarta modalidades que excedem peso máximo
        veiculos = {v.nome: v.peso_maximo for v in Veiculo.query.all()}
        combinacoes_com_peso_ok = {}
        
        for (transportadora_id, uf_destino, modalidade), dados in combinacoes_validas.items():
            peso_maximo = veiculos.get(modalidade, 0)
            
            if peso_maximo >= peso_total:
                combinacoes_com_peso_ok[(transportadora_id, uf_destino, modalidade)] = dados
                print(f"[DEBUG] ✅ Peso OK: Modal {modalidade} para {uf_destino} suporta {peso_maximo}kg >= {peso_total}kg")
            else:
                print(f"[DEBUG] ❌ Peso excedido: Modal {modalidade} para {uf_destino} suporta {peso_maximo}kg < {peso_total}kg")
        
        if not combinacoes_com_peso_ok:
            print("[DEBUG] ❌ Nenhuma modalidade suporta o peso total")
            return {'diretas': [], 'fracionadas': {}}
        
        # REGRA 13: Calcula fretes e pega a opção MAIS CARA
        opcoes_calculadas = []
        
        for (transportadora_id, uf_destino, modalidade), dados in combinacoes_com_peso_ok.items():
            # Para cada combinação válida, pega a tabela MAIS CARA entre as que atendem as cidades
            tabelas_da_combinacao = []
            
            for item in dados:
                tabela = item['tabela']
                cidade_id = item['cidade_id']
                cidade = db.session.get(Cidade,cidade_id) if cidade_id else None
                
                if not cidade:
                    continue
                
                # ✅ CARREGA DADOS DA CIDADE IMEDIATAMENTE PARA EVITAR PROBLEMAS DE SESSÃO
                try:
                    cidade_icms = cidade.icms or 0
                    cidade_nome = cidade.nome
                    cidade_uf = cidade.uf
                except Exception as e:
                    print(f"[DEBUG] ⚠️ Erro ao acessar dados da cidade {cidade_id}: {e}")
                    cidade_icms = 0
                    cidade_nome = "N/A"
                    cidade_uf = "N/A"
                
                # Calcula frete com esta tabela
                try:
                    # Usa TabelaFreteManager para extrair dados da tabela
                    dados_tabela = TabelaFreteManager.preparar_dados_tabela(tabela)
                    dados_tabela['modalidade'] = modalidade  # Sobrescreve com a modalidade específica
                    dados_tabela['icms_destino'] = cidade_icms  # ICMS vem da cidade
                    
                    resultado = CalculadoraFrete.calcular_frete_unificado(
                        peso=peso_total,
                        valor_mercadoria=valor_total,
                        tabela_dados=dados_tabela,
                        transportadora_optante=tabela.transportadora.optante if tabela.transportadora else False
                    )
                    
                    tabelas_da_combinacao.append({
                        'tabela': tabela,
                        'cidade_icms': cidade_icms,
                        'cidade_nome': cidade_nome,
                        'cidade_uf': cidade_uf,
                        'valor_liquido': float(resultado['valor_liquido']),
                        'valor_total': float(resultado['valor_com_icms']),
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
                    'icms': tabela_mais_cara['cidade_icms'],
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
        pedidos_originais = Pedido.query.filter(Pedido.separacao_lote_id.in_(lista_ids)).all()
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
                    except Exception as e:
                        pass
            
            # ✅ ALTERAÇÃO PRINCIPAL: Força UF=SP e cidade=Guarulhos
            pedido_copia.cod_uf = 'SP'
            pedido_copia.nome_cidade = 'Guarulhos'
            pedido_copia.rota = 'CIF'  # Força para não ser RED (que vai para Guarulhos)
            # ✅ CORREÇÃO: Define atributos normalizados para busca de cidade
            pedido_copia.cidade_normalizada = 'GUARULHOS'
            pedido_copia.uf_normalizada = 'SP'

            print(f"[DEBUG] 📍 Pedido {pedido_original.num_pedido}: {pedido_original.nome_cidade}/{pedido_original.cod_uf} → Guarulhos/SP")
            
            pedidos_redespacho.append(pedido_copia)

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
                'id': pedidos_originais[i].separacao_lote_id,  # Usar lote_id
                'separacao_lote_id': pedidos_originais[i].separacao_lote_id,
                'num_pedido': pedido.num_pedido,
                'data_pedido': pedido.data_pedido.strftime('%Y-%m-%d') if pedido.data_pedido else None,
                'cnpj_cpf': pedido.cnpj_cpf,
                'raz_social_red': pedido.raz_social_red,
                'nome_cidade': 'Guarulhos',  # Mostra cidade alterada
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
                    'cidade': 'Guarulhos',  # Cidade alterada
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
                        'cidade': 'Guarulhos',  # Cidade alterada
                        'uf': 'SP',  # UF alterada
                        'razao_social': pedidos_cnpj[0].raz_social_red if pedidos_cnpj else ''
                    }
                    opcoes_por_cnpj[cnpj].append(opcao_completa)

        # ✅ BUSCA PEDIDOS DO MESMO UF (SP) PARA OTIMIZADOR
        pedidos_mesmo_uf = (Pedido.query
                           .filter(Pedido.cod_uf == 'SP')
                           .filter(~Pedido.separacao_lote_id.in_(lista_ids))
                           .filter(Pedido.status == 'ABERTO')  # ✅ Apenas pedidos abertos
                           .limit(200)  # ✅ Aumenta limite para mais otimizações
                           .all())

        # Serializa pedidos_mesmo_uf
        pedidos_mesmo_estado_json = []
        for p in pedidos_mesmo_uf:
            pedidos_mesmo_estado_json.append({
                'id': p.separacao_lote_id,
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


@cotacao_bp.route("/redespachar_sao_paulo")
@login_required
def redespachar_sao_paulo():
    """
    Rota do Redespachar para São Paulo - Cota pedidos considerando UF=SP e cidade=São Paulo
    """
    try:
        # Recupera pedidos da sessão
        lista_ids = session.get("cotacao_pedidos", [])
        if not lista_ids:
            flash("Nenhum pedido na cotação!", "warning")
            return redirect(url_for("pedidos.lista_pedidos"))

        # Carrega os pedidos originais do banco
        pedidos_originais = Pedido.query.filter(Pedido.separacao_lote_id.in_(lista_ids)).all()
        if not pedidos_originais:
            flash("Nenhum pedido encontrado!", "warning")
            return redirect(url_for("pedidos.lista_pedidos"))

        print(f"[DEBUG] 📦 REDESPACHAR SÃO PAULO: Iniciando para {len(pedidos_originais)} pedidos")
        
        # ✅ CRIA CÓPIAS DOS PEDIDOS COM ALTERAÇÕES TEMPORÁRIAS
        pedidos_redespacho = []
        for pedido_original in pedidos_originais:
            # Cria uma cópia do pedido com os dados alterados para SP/São Paulo
            pedido_copia = Pedido()
            
            # Copia todos os atributos do pedido original
            for attr in dir(pedido_original):
                if not attr.startswith('_') and hasattr(Pedido, attr):
                    try:
                        valor = getattr(pedido_original, attr)
                        if not callable(valor):
                            setattr(pedido_copia, attr, valor)
                    except Exception as e:
                        pass
            
            # ✅ ALTERAÇÃO PRINCIPAL: Força UF=SP e cidade=São Paulo
            pedido_copia.cod_uf = 'SP'
            pedido_copia.nome_cidade = 'São Paulo'
            pedido_copia.rota = 'CIF'  # Força para não ser RED
            # ✅ CORREÇÃO: Define atributos normalizados para busca de cidade
            pedido_copia.cidade_normalizada = 'SAO PAULO'
            pedido_copia.uf_normalizada = 'SP'

            print(f"[DEBUG] 📍 Pedido {pedido_original.num_pedido}: {pedido_original.nome_cidade}/{pedido_original.cod_uf} → SÃO PAULO/SP")
            
            pedidos_redespacho.append(pedido_copia)

        # ✅ CALCULA FRETES COM OS DADOS ALTERADOS
        print("[DEBUG] 🚛 Calculando fretes para redespacho (SP/São Paulo)...")
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
                'id': pedidos_originais[i].separacao_lote_id,  # Usar lote_id
                'separacao_lote_id': pedidos_originais[i].separacao_lote_id,
                'num_pedido': pedido.num_pedido,
                'data_pedido': pedido.data_pedido.strftime('%Y-%m-%d') if pedido.data_pedido else None,
                'cnpj_cpf': pedido.cnpj_cpf,
                'raz_social_red': pedido.raz_social_red,
                'nome_cidade': 'São Paulo',  # Mostra cidade alterada
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
        
        # Todos são SP/São Paulo agora, então permite carga direta
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
            print("[DEBUG] 🎯 IMPLEMENTANDO MELHOR OPÇÃO PARA REDESPACHO SÃO PAULO")
            
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
                    'cidade': 'SAO PAULO',  # Cidade alterada
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
                        'cidade': 'SAO PAULO',  # Cidade alterada
                        'uf': 'SP',  # UF alterada
                        'razao_social': pedidos_cnpj[0].raz_social_red if pedidos_cnpj else ''
                    }
                    opcoes_por_cnpj[cnpj].append(opcao_completa)

        # ✅ BUSCA PEDIDOS DO MESMO UF (SP) PARA OTIMIZADOR
        pedidos_mesmo_uf = (Pedido.query
                           .filter(Pedido.cod_uf == 'SP')
                           .filter(~Pedido.separacao_lote_id.in_(lista_ids))
                           .filter(Pedido.status == 'ABERTO')  # ✅ Apenas pedidos abertos
                           .limit(200)  # ✅ Aumenta limite para mais otimizações
                           .all())

        # Serializa pedidos_mesmo_uf
        pedidos_mesmo_estado_json = []
        for p in pedidos_mesmo_uf:
            pedidos_mesmo_estado_json.append({
                'id': p.separacao_lote_id,
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
        session['redespacho_tipo'] = 'SAO_PAULO'  # Flag específica para São Paulo

        print(f"[DEBUG] ✅ REDESPACHAR SÃO PAULO: {len(opcoes_transporte['direta'])} opções diretas, {len(opcoes_transporte['fracionada'])} transportadoras fracionadas")

        # ✅ RENDERIZA O TEMPLATE COM DADOS ALTERADOS
        return render_template(
            "cotacao/redespachar_sao_paulo.html",  # Template específico para redespacho São Paulo
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
            redespacho=True,  # Flag para o template saber que é redespacho
            cidade_redespacho='São Paulo'  # Flag específica da cidade
        )

    except Exception as e:
        print(f"[DEBUG] ❌ Erro no redespacho São Paulo: {str(e)}")
        flash(f"Erro ao calcular redespacho para São Paulo: {str(e)}", "error")
        return redirect(url_for("cotacao.tela_cotacao"))


@cotacao_bp.route("/redespachar_sao_bernardo")
@login_required
def redespachar_sao_bernardo():
    """
    Rota do Redespachar para São Bernardo do Campo - Cota pedidos considerando UF=SP e cidade=São Bernardo do Campo
    """
    try:
        # Recupera pedidos da sessão
        lista_ids = session.get("cotacao_pedidos", [])
        if not lista_ids:
            flash("Nenhum pedido na cotação!", "warning")
            return redirect(url_for("pedidos.lista_pedidos"))

        # Carrega os pedidos originais do banco
        pedidos_originais = Pedido.query.filter(Pedido.separacao_lote_id.in_(lista_ids)).all()
        if not pedidos_originais:
            flash("Nenhum pedido encontrado!", "warning")
            return redirect(url_for("pedidos.lista_pedidos"))

        print(f"[DEBUG] REDESPACHAR SÃO BERNARDO: Iniciando para {len(pedidos_originais)} pedidos")

        # Cria cópias dos pedidos com alterações temporárias
        pedidos_redespacho = []
        for pedido_original in pedidos_originais:
            pedido_copia = Pedido()

            for attr in dir(pedido_original):
                if not attr.startswith('_') and hasattr(Pedido, attr):
                    try:
                        valor = getattr(pedido_original, attr)
                        if not callable(valor):
                            setattr(pedido_copia, attr, valor)
                    except Exception as e:
                        pass

            # Força UF=SP e cidade=São Bernardo do Campo
            pedido_copia.cod_uf = 'SP'
            pedido_copia.nome_cidade = 'São Bernardo do Campo'
            pedido_copia.rota = 'CIF'
            pedido_copia.cidade_normalizada = 'SAO BERNARDO DO CAMPO'
            pedido_copia.uf_normalizada = 'SP'

            print(f"[DEBUG] Pedido {pedido_original.num_pedido}: {pedido_original.nome_cidade}/{pedido_original.cod_uf} -> São Bernardo do Campo/SP")

            pedidos_redespacho.append(pedido_copia)

        # Calcula fretes com os dados alterados
        print("[DEBUG] Calculando fretes para redespacho (SP/São Bernardo do Campo)...")
        resultados = calcular_frete_por_cnpj(pedidos_redespacho)

        if not resultados:
            flash("Não foi possível calcular fretes para redespacho", "warning")
            return redirect(url_for("cotacao.tela_cotacao"))

        # Organiza dados para o template
        pedidos_json = []
        pedidos_por_cnpj = {}
        pedidos_por_cnpj_json = {}
        opcoes_por_cnpj = {}

        peso_total = sum(p.peso_total or 0 for p in pedidos_redespacho)
        valor_total = sum(p.valor_saldo_total or 0 for p in pedidos_redespacho)

        for i, pedido in enumerate(pedidos_redespacho):
            pedido_dict = {
                'id': pedidos_originais[i].separacao_lote_id,
                'separacao_lote_id': pedidos_originais[i].separacao_lote_id,
                'num_pedido': pedido.num_pedido,
                'data_pedido': pedido.data_pedido.strftime('%Y-%m-%d') if pedido.data_pedido else None,
                'cnpj_cpf': pedido.cnpj_cpf,
                'raz_social_red': pedido.raz_social_red,
                'nome_cidade': 'São Bernardo do Campo',
                'cod_uf': 'SP',
                'valor_saldo_total': float(pedido.valor_saldo_total) if pedido.valor_saldo_total else 0,
                'pallet_total': float(pedido.pallet_total) if pedido.pallet_total else 0,
                'peso_total': float(pedido.peso_total) if pedido.peso_total else 0,
                'rota': 'CIF',
                'sub_rota': getattr(pedido, 'sub_rota', '')
            }

            pedidos_json.append(pedido_dict)

            cnpj = pedido.cnpj_cpf
            if cnpj not in pedidos_por_cnpj:
                pedidos_por_cnpj[cnpj] = []
                pedidos_por_cnpj_json[cnpj] = []
            pedidos_por_cnpj[cnpj].append(pedidos_originais[i])
            pedidos_por_cnpj_json[cnpj].append(pedido_dict)

        # Processa resultados
        opcoes_transporte = {
            'direta': [],
            'fracionada': {}
        }

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
            print("[DEBUG] IMPLEMENTANDO MELHOR OPÇÃO PARA REDESPACHO SÃO BERNARDO DO CAMPO")

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
                    'cidade': 'SAO BERNARDO DO CAMPO',
                    'uf': 'SP',
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
                        'cidade': 'SAO BERNARDO DO CAMPO',
                        'uf': 'SP',
                        'razao_social': pedidos_cnpj[0].raz_social_red if pedidos_cnpj else ''
                    }
                    opcoes_por_cnpj[cnpj].append(opcao_completa)

        # Busca pedidos do mesmo UF (SP) para otimizador
        pedidos_mesmo_uf = (Pedido.query
                           .filter(Pedido.cod_uf == 'SP')
                           .filter(~Pedido.separacao_lote_id.in_(lista_ids))
                           .filter(Pedido.status == 'ABERTO')
                           .limit(200)
                           .all())

        # Serializa pedidos_mesmo_uf
        pedidos_mesmo_estado_json = []
        for p in pedidos_mesmo_uf:
            pedidos_mesmo_estado_json.append({
                'id': p.separacao_lote_id,
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

        # Armazena resultados alterados na sessão
        session['resultados'] = resultados
        session['redespacho_ativo'] = True
        session['redespacho_tipo'] = 'SAO_BERNARDO'

        print(f"[DEBUG] REDESPACHAR SÃO BERNARDO: {len(opcoes_transporte['direta'])} opções diretas, {len(opcoes_transporte['fracionada'])} transportadoras fracionadas")

        return render_template(
            "cotacao/redespachar_sao_bernardo.html",
            pedidos=pedidos_originais,
            pedidos_selecionados=pedidos_json,
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
            redespacho=True,
            cidade_redespacho='São Bernardo do Campo'
        )

    except Exception as e:
        print(f"[DEBUG] Erro no redespacho São Bernardo do Campo: {str(e)}")
        flash(f"Erro ao calcular redespacho para São Bernardo do Campo: {str(e)}", "error")
        return redirect(url_for("cotacao.tela_cotacao"))


@cotacao_bp.route("/incluir_em_embarque", methods=["POST"])
@login_required
def incluir_em_embarque():
    """
    Inclui os pedidos da cotação atual em um embarque existente
    """
    
    embarque_id = request.form.get('embarque_id')
    tipo_carga = request.form.get('tipo_carga')
    
    if not embarque_id:
        flash('❌ Embarque não informado.', 'danger')
        return redirect(url_for('cotacao.tela_cotacao'))
    
    # Recuperar pedidos da sessão
    lista_ids = session.get("cotacao_pedidos", [])
    if not lista_ids:
        flash("❌ Nenhum pedido na cotação!", "warning")
        return redirect(url_for("pedidos.lista_pedidos"))
    
    try:
        embarque = Embarque.query.get_or_404(embarque_id)
        pedidos = Pedido.query.filter(Pedido.separacao_lote_id.in_(lista_ids)).all()
        
        if not pedidos:
            flash("❌ Nenhum pedido encontrado!", "warning")
            return redirect(url_for("pedidos.lista_pedidos"))
        
        # Verificar se o embarque está ativo
        if embarque.status != 'ativo':
            flash('❌ Só é possível incluir pedidos em embarques ativos.', 'danger')
            return redirect(url_for('cotacao.tela_cotacao'))
        
        # Verificar compatibilidade por tipo de carga
        if tipo_carga == 'DIRETA':
            # Para carga direta, verificar capacidade do veículo
            from app.veiculos.models import Veiculo
            
            if embarque.modalidade:
                veiculo = Veiculo.query.filter_by(nome=embarque.modalidade).first()
                if veiculo and veiculo.peso_maximo:
                    peso_atual = embarque.total_peso_pedidos()
                    peso_novos_pedidos = sum(p.peso_total or 0 for p in pedidos)
                    
                    if (peso_atual + peso_novos_pedidos) > veiculo.peso_maximo:
                        flash(f'❌ Capacidade do veículo excedida. Capacidade: {veiculo.peso_maximo}kg, Atual: {peso_atual}kg, Tentando adicionar: {peso_novos_pedidos}kg', 'danger')
                        return redirect(url_for('cotacao.tela_cotacao'))
        
        # Adicionar pedidos ao embarque
        pedidos_adicionados = 0
        pedidos_nao_incluidos = []
        
        for pedido in pedidos:
            # ✅ Resolve cidade/UF real de entrega (corrige RED que gravava Guarulhos)
            cidade_formatada, uf_correto = LocalizacaoService.obter_cidade_destino_embarque(pedido)
            
            # ✅ CORREÇÃO: Formatar protocolo e data corretamente
            protocolo_formatado = formatar_protocolo(getattr(pedido, 'protocolo', None))
            data_formatada = formatar_data_brasileira(getattr(pedido, 'agendamento', None))

            # ✅ BUSCAR numero_nf da Separacao correspondente
            nota_fiscal = ''
            if pedido.separacao_lote_id and pedido.num_pedido:
                separacao_com_nf = Separacao.query.filter_by(
                    separacao_lote_id=pedido.separacao_lote_id,
                    num_pedido=pedido.num_pedido
                ).filter(Separacao.numero_nf.isnot(None)).first()

                if separacao_com_nf:
                    nota_fiscal = separacao_com_nf.numero_nf
                    print(f"[DEBUG] 📄 NF encontrada para pedido {pedido.num_pedido}: {nota_fiscal}")

            # Criar novo item do embarque
            novo_item = EmbarqueItem(
                embarque_id=embarque.id,
                separacao_lote_id=pedido.separacao_lote_id,  # ✅ CORREÇÃO: Usa o lote real do pedido
                cnpj_cliente=pedido.cnpj_cpf,
                cliente=pedido.raz_social_red,
                pedido=pedido.num_pedido,
                protocolo_agendamento=protocolo_formatado,
                data_agenda=data_formatada,
                nota_fiscal=nota_fiscal,  # ✅ PREENCHE com numero_nf da Separacao se houver
                volumes=getattr(pedido, 'volumes', 0),
                peso=pedido.peso_total,
                valor=pedido.valor_saldo_total,
                pallets=pedido.pallet_total,  # ✅ NOVO: Adiciona pallets reais do pedido
                status='ativo',
                uf_destino=uf_correto,
                cidade_destino=cidade_formatada
            )
            
            # ✅ CORREÇÃO: Para carga fracionada, OBRIGATÓRIO usar dados da tabela DA COTAÇÃO da mesma transportadora
            dados_tabela_encontrados = False
            
            if tipo_carga == 'FRACIONADA':
                # Busca os dados da tabela calculados na cotação para o CNPJ ESPECÍFICO deste pedido
                resultados = session.get('resultados', {})
                
                if 'fracionadas' in resultados and pedido.cnpj_cpf in resultados['fracionadas']:
                    opcoes_cnpj = resultados['fracionadas'][pedido.cnpj_cpf]
                    
                    # ✅ CORREÇÃO: Busca a MELHOR OPÇÃO DA COTAÇÃO para este CNPJ específico da mesma transportadora
                    melhor_opcao_cnpj = None
                    melhor_valor_kg = float('inf')
                    
                    # Encontra a melhor opção (mais barata) deste CNPJ para a transportadora do embarque
                    for opcao in opcoes_cnpj:
                        if opcao.get('transportadora_id') == embarque.transportadora_id:
                            # Calcula valor por kg para comparação
                            peso_total_cnpj = sum(p.peso_total or 0 for p in pedidos if p.cnpj_cpf == pedido.cnpj_cpf)
                            valor_kg = opcao.get('valor_liquido', 0) / peso_total_cnpj if peso_total_cnpj > 0 else float('inf')
                            
                            if valor_kg < melhor_valor_kg:
                                melhor_valor_kg = valor_kg
                                melhor_opcao_cnpj = opcao
                    
                    # Se encontrou a melhor opção deste CNPJ para a transportadora
                    if melhor_opcao_cnpj:
                        # Usa os dados da tabela específica da cotação deste CNPJ
                        # Prepara dados e atribui usando TabelaFreteManager
                        dados_tabela_temp = TabelaFreteManager.preparar_dados_tabela(melhor_opcao_cnpj)
                        TabelaFreteManager.atribuir_campos_objeto(novo_item, dados_tabela_temp)
                        # icms_destino é atribuído separadamente (vem de localidades)
                        novo_item.icms_destino = melhor_opcao_cnpj.get('icms_destino', 0)
                        
                        dados_tabela_encontrados = True
                        print(f"[DEBUG] ✅ Usando tabela ESPECÍFICA da cotação para CNPJ {pedido.cnpj_cpf} (Pedido {pedido.num_pedido}): {melhor_opcao_cnpj.get('nome_tabela')} - R${melhor_valor_kg:.2f}/kg")
                
                # ❌ SE NÃO ENCONTROU DADOS DA COTAÇÃO PARA A MESMA TRANSPORTADORA, NÃO INCLUI O PEDIDO
                if not dados_tabela_encontrados:
                    motivo = f"Sem dados de cotação para transportadora {embarque.transportadora.razao_social}"
                    pedidos_nao_incluidos.append({
                        'num_pedido': pedido.num_pedido,
                        'cnpj': pedido.cnpj_cpf,
                        'cliente': pedido.raz_social_red,
                        'motivo': motivo
                    })
                    print(f"[DEBUG] ❌ PEDIDO NÃO INCLUÍDO: {pedido.num_pedido} - {motivo}")
                    continue  # Pula para o próximo pedido
            else:
                # Para carga direta, sempre considera como encontrado (usa dados do embarque)
                dados_tabela_encontrados = True
            
            db.session.add(novo_item)
            
            # Atualizar Separacao — apenas Nacom (CarVia nao tem Separacao)
            if pedido.separacao_lote_id and not str(pedido.separacao_lote_id).startswith('CARVIA-'):
                if embarque.cotacao_id:
                    Separacao.atualizar_cotacao(
                        separacao_lote_id=pedido.separacao_lote_id,
                        cotacao_id=embarque.cotacao_id,
                        nf_cd=False
                    )
                else:
                    Separacao.atualizar_nf_cd(
                        separacao_lote_id=pedido.separacao_lote_id,
                        nf_cd=False
                    )
                
                # O status será calculado automaticamente como COTADO pelo trigger
            
            pedidos_adicionados += 1

        # Sinalizar que embarque precisa reimprimir (se ja foi impresso)
        if pedidos_adicionados > 0:
            embarque.marcar_alterado_apos_impressao()

        db.session.commit()

        # ✅ RECÁLCULO DA TABELA PARA CARGA DIRETA — "cidade mais cara"
        # Após incluir novos itens, verifica se alguma cidade nova é mais cara
        # que a cidade da tabela atual e atualiza os campos tabela_* do embarque
        if tipo_carga == 'DIRETA' and pedidos_adicionados > 0:
            try:
                # Invalida cache de itens para incluir os recém-adicionados
                embarque.invalidar_cache_itens()
                itens_ativos = [i for i in embarque.itens if i.status == 'ativo']

                # Calcula novos totais do embarque (peso/valor/pallets)
                novo_peso_total = sum(i.peso or 0 for i in itens_ativos)
                novo_valor_total = sum(i.valor or 0 for i in itens_ativos)
                novo_pallet_total = sum(i.pallets or 0 for i in itens_ativos)

                # Coleta cidades únicas de TODOS os itens ativos
                cidades_unicas = set()
                for item in itens_ativos:
                    if item.cidade_destino and item.uf_destino:
                        cidade_obj = buscar_cidade_unificada(
                            cidade=item.cidade_destino,
                            uf=item.uf_destino
                        )
                        if cidade_obj:
                            cidades_unicas.add(cidade_obj.id)

                if cidades_unicas and novo_peso_total > 0:
                    print(f"[DEBUG] 🔄 RECÁLCULO DIRETA: {len(cidades_unicas)} cidades, peso total {novo_peso_total:.2f}kg")

                    # Busca fretes para TODAS as cidades, filtra pela transportadora do embarque
                    grupos_recalculo = {}  # (transportadora_id, modalidade) -> [opcoes]

                    for cidade_id in cidades_unicas:
                        fretes_cidade = calcular_fretes_possiveis(
                            cidade_destino_id=cidade_id,
                            peso_utilizado=novo_peso_total,
                            valor_carga=novo_valor_total,
                            veiculo_forcado=embarque.modalidade,
                            tipo_carga="DIRETA"
                        )

                        for opcao in fretes_cidade:
                            # Filtra apenas pela transportadora do embarque
                            if opcao['transportadora_id'] == embarque.transportadora_id:
                                chave = (opcao['transportadora_id'], opcao['modalidade'])
                                if chave not in grupos_recalculo:
                                    grupos_recalculo[chave] = []
                                grupos_recalculo[chave].append(opcao)

                    # Seleciona a tabela mais cara entre todas as cidades
                    tabela_atualizada = False
                    for (_transp_id, modal), opcoes_todas in grupos_recalculo.items():
                        # Filtra pela modalidade do embarque (se tiver)
                        if embarque.modalidade and modal != embarque.modalidade:
                            continue

                        if opcoes_todas:
                            opcao_mais_cara = max(opcoes_todas, key=lambda x: x['valor_liquido'])

                            print(f"[DEBUG] 📊 Tabela mais cara: {opcao_mais_cara['nome_tabela']} "
                                  f"({opcao_mais_cara.get('cidade', 'N/A')}) "
                                  f"R${opcao_mais_cara['valor_liquido']:.2f}")

                            # Atualiza campos tabela_* do embarque
                            dados_tabela_nova = TabelaFreteManager.preparar_dados_tabela(opcao_mais_cara)
                            TabelaFreteManager.atribuir_campos_objeto(embarque, dados_tabela_nova)
                            embarque.icms_destino = opcao_mais_cara.get('icms_destino', 0)
                            tabela_atualizada = True
                            break  # Apenas uma combinação transportadora/modalidade por embarque DIRETA

                    # Atualiza totais do embarque
                    embarque.peso_total = novo_peso_total
                    embarque.valor_total = novo_valor_total
                    embarque.pallet_total = novo_pallet_total

                    db.session.commit()

                    if tabela_atualizada:
                        print(f"[DEBUG] ✅ Tabela do embarque #{embarque.numero} RECALCULADA com sucesso")
                    else:
                        print(f"[DEBUG] ⚠️ Nenhuma tabela encontrada para recalcular embarque #{embarque.numero}")

            except Exception as e:
                print(f"[DEBUG] ⚠️ Erro ao recalcular tabela DIRETA: {str(e)}")
                # Não falha a inclusão — o embarque foi criado, tabela pode ser ajustada via "Alterar Cotação"

        # ✅ FEEDBACK DETALHADO SOBRE PEDIDOS INCLUÍDOS E NÃO INCLUÍDOS
        if pedidos_adicionados > 0:
            flash(f'✅ {pedidos_adicionados} pedido(s) adicionado(s) ao embarque #{embarque.numero} com sucesso!', 'success')
            
            # Mostrar pedidos que NÃO foram incluídos (se houver)
            if pedidos_nao_incluidos:
                flash(f'⚠️ {len(pedidos_nao_incluidos)} pedido(s) NÃO foram incluídos:', 'warning')
                for pedido_nao_incluido in pedidos_nao_incluidos:
                    flash(f'❌ Pedido {pedido_nao_incluido["num_pedido"]} ({pedido_nao_incluido["cliente"][:30]}): {pedido_nao_incluido["motivo"]}', 'danger')
            
            # Limpar sessão da cotação apenas se todos foram incluídos
            if not pedidos_nao_incluidos and 'cotacao_pedidos' in session:
                del session['cotacao_pedidos']
            
            return redirect(url_for('embarques.visualizar_embarque', id=embarque.id))
        else:
            flash('❌ Nenhum pedido foi adicionado ao embarque.', 'warning')
            
            # Explicar por que nenhum pedido foi incluído
            if pedidos_nao_incluidos:
                flash('💡 Motivos pelos quais os pedidos não foram incluídos:', 'info')
                for pedido_nao_incluido in pedidos_nao_incluidos:
                    flash(f'❌ Pedido {pedido_nao_incluido["num_pedido"]}: {pedido_nao_incluido["motivo"]}', 'danger')
            
            return redirect(url_for('cotacao.tela_cotacao'))
            
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro ao incluir pedidos no embarque: {str(e)}', 'danger')
        return redirect(url_for('cotacao.tela_cotacao'))
