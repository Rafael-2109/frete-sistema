from collections import defaultdict

from sqlalchemy import func

from app.localidades.models import Cidade
from app.tabelas.models import TabelaFrete
from app.vinculos.models import CidadeAtendida
from app.veiculos.models import Veiculo
from app.utils.string_utils import normalizar_nome_cidade
from app.utils.vehicle_utils import normalizar_nome_veiculo
from app.utils.grupo_empresarial import grupo_service
from app import db


def calcular_fretes_possiveis(
    cidade_destino_id=None,
    peso_utilizado=None,
    valor_carga=None,
    uf_origem=None,
    uf_destino=None,
    cidade_destino=None,
    peso=None,
    valor=None,
    veiculo_forcado=None,
    rota=None,
    tipo_carga=None,
):
    """
    Calcula fretes possíveis (por transportadora / tabela) para UM conjunto de peso + valor.
    
    LÓGICA CORRETA:
    1. frete_minimo_peso = peso mínimo para cálculo (não é valor)
    2. Calcular frete líquido SEM ICMS
    3. frete_minimo_valor = valor mínimo do frete líquido
    4. Aplicar ICMS no valor final

    Aceita tanto os parâmetros antigos (cidade_destino_id, peso_utilizado, valor_carga)
    quanto os novos (uf_origem, cidade_origem, uf_destino, cidade_destino, peso, valor)
    
    Se veiculo_forcado for informado, retorna apenas as opções com este veículo
    Se tipo_carga for informado, retorna apenas as opções deste tipo
    """
    resultados = []

    # Validação inicial de peso e valor
    peso_final = peso_utilizado if peso_utilizado is not None else peso
    valor_final = valor_carga if valor_carga is not None else valor

    if peso_final is None or peso_final <= 0:
        return []
        
    if valor_final is None or valor_final <= 0:
        return []

    # Busca cidade usando a função unificada
    if cidade_destino_id:
        cidade = Cidade.query.get(cidade_destino_id)
        if not cidade:
            return []
        # Se não foi passado uf_destino, usa o da cidade
        if not uf_destino:
            uf_destino = cidade.uf
    else:
        cidade = buscar_cidade_unificada(
            cidade=cidade_destino,
            uf=uf_destino,
            rota=rota
        )
        if not cidade:
            return []

    # Se for FOB, retorna vazio
    if cidade.nome.upper() == 'FOB':
        return []

    # Carrega capacidades dos veículos uma única vez
    veiculos = {v.nome: v.peso_maximo for v in Veiculo.query.all()}
    
    # Se tem veículo forçado, valida se ele comporta o peso
    if veiculo_forcado:
        modalidade = normalizar_nome_veiculo(veiculo_forcado)
        capacidade = veiculos.get(modalidade)
        if not capacidade:
            return []
        if capacidade < peso_final:
            return []

    # Pega todas as transportadoras/tabelas que atendem a cidade destino
    # CORREÇÃO CRÍTICA: Busca por código IBGE ao invés de cidade_id
    atendimentos = CidadeAtendida.query.filter(
        CidadeAtendida.codigo_ibge == cidade.codigo_ibge
    ).all()
    
    if not atendimentos:
        return []
    
    for at in atendimentos:        
        # 🏢 GRUPO EMPRESARIAL: Busca tabelas em todas as transportadoras do grupo
        grupo_ids = grupo_service.obter_transportadoras_grupo(at.transportadora_id)
        
        # Busca final com todos os filtros - INCLUINDO GRUPO EMPRESARIAL
        tabelas = TabelaFrete.query.filter(
            TabelaFrete.transportadora_id.in_(grupo_ids),  # ✅ MUDANÇA: Busca em todo o grupo!
            TabelaFrete.uf_origem == (uf_origem or "SP"),
            TabelaFrete.uf_destino == (uf_destino or cidade.uf),
            func.upper(func.trim(TabelaFrete.nome_tabela)) == func.upper(func.trim(at.nome_tabela))
        ).all()

        # Se tiver tipo_carga especificado, filtra
        if tipo_carga:
            tabelas = [t for t in tabelas if t.tipo_carga == tipo_carga]
        
        # Se tiver veículo forçado, filtra apenas as tabelas com este veículo
        if veiculo_forcado:
            tabelas = [t for t in tabelas if t.tipo_carga == "DIRETA" and t.modalidade == veiculo_forcado]

        for tf in tabelas:
            # Se for carga direta, validar se o veículo suporta o peso
            if tf.tipo_carga == "DIRETA":
                modalidade = normalizar_nome_veiculo(tf.modalidade)
                capacidade = veiculos.get(modalidade)

                if capacidade and peso_final > capacidade:
                    continue

            # ✅ CORREÇÃO COMPLETA: Aplicar lógica correta do cálculo
            
            # 1. CORREÇÃO: Determinar peso para cálculo (peso real vs peso mínimo)
            peso_para_calculo = max(peso_final, tf.frete_minimo_peso or 0)
            
            # 2. CORREÇÃO: Calcular frete base SOMANDO peso + valor
            frete_peso = (tf.valor_kg or 0) * peso_para_calculo
            frete_valor = (tf.percentual_valor or 0) * valor_final / 100
            frete_base = frete_peso + frete_valor  # SOMA peso + valor
            
            # 3. Calcular adicionais sobre valor da mercadoria
            gris = (tf.percentual_gris or 0) * valor_final / 100
            adv = (tf.percentual_adv or 0) * valor_final / 100
            rca = (tf.percentual_rca or 0) * valor_final / 100
            
            # 4. Calcular pedágio sobre peso para cálculo (por frações de 100kg)
            if tf.pedagio_por_100kg and peso_para_calculo > 0:
                fracoes_100kg = int((peso_para_calculo - 1) // 100) + 1  # Arredonda para cima
                pedagio = fracoes_100kg * tf.pedagio_por_100kg
            else:
                pedagio = 0
            
            # 5. Somar valores fixos
            fixos = (tf.valor_despacho or 0) + (tf.valor_cte or 0) + (tf.valor_tas or 0)
            
            # 6. Total líquido SEM ICMS
            frete_liquido = frete_base + gris + adv + rca + pedagio + fixos
            
            # 7. CORREÇÃO: Aplicar frete mínimo VALOR no frete líquido
            frete_final_liquido = max(frete_liquido, tf.frete_minimo_valor or 0)
            
            # 8. CORREÇÃO: Aplicar ICMS apenas no final (se não estiver incluso)
            frete_com_icms = frete_final_liquido
            if not tf.icms_incluso:
                icms_decimal = cidade.icms or 0
                if icms_decimal < 1 and icms_decimal > 0:
                    frete_com_icms = frete_final_liquido / (1 - icms_decimal)

            # Só inclui se tiver algum valor
            if frete_com_icms > 0:
                # 9. Calcular valor líquido - se não for optante, desconta ICMS
                valor_liquido = frete_com_icms
                if not at.transportadora.optante:
                    icms_decimal = cidade.icms or 0
                    if icms_decimal < 1 and icms_decimal > 0:
                        valor_liquido = frete_com_icms * (1 - icms_decimal)
                
                resultados.append(
                    {
                        "transportadora": at.transportadora.razao_social,
                        "transportadora_id": at.transportadora.id,
                        "modalidade": tf.modalidade,
                        "tipo_carga": tf.tipo_carga,
                        "valor_total": round(frete_com_icms, 2),
                        "valor_liquido": round(valor_liquido, 2),
                        "nome_tabela": at.nome_tabela,
                        # ✅ CORREÇÃO: Adiciona TODOS os dados da tabela
                        "valor_kg": tf.valor_kg or 0,
                        "percentual_valor": tf.percentual_valor or 0,
                        "frete_minimo_valor": tf.frete_minimo_valor or 0,
                        "frete_minimo_peso": tf.frete_minimo_peso or 0,
                        "percentual_gris": tf.percentual_gris or 0,
                        "pedagio_por_100kg": tf.pedagio_por_100kg or 0,
                        "valor_tas": tf.valor_tas or 0,
                        "percentual_adv": tf.percentual_adv or 0,
                        "percentual_rca": tf.percentual_rca or 0,
                        "valor_despacho": tf.valor_despacho or 0,
                        "valor_cte": tf.valor_cte or 0,
                        "icms_incluso": tf.icms_incluso or False,
                        "icms_destino": cidade.icms or 0,
                        "cidade": cidade.nome,
                        "uf": cidade.uf
                    }
                )

    return resultados


def agrupar_por_cnpj(pedidos):
    """
    Dado uma lista de 'pedidos' (com .cnpj_cpf e .nome_cidade, .peso_total, .valor_saldo_total),
    agrupa em dict: { cnpj_cpf: [lista_de_pedidos] }
    """
    grupos = defaultdict(list)
    for ped in pedidos:
        grupos[ped.cnpj_cpf].append(ped)
    return grupos


def deve_calcular_frete(pedido):
    """
    Verifica se o pedido deve ter frete calculado.
    Regras:
    1. Se rota FOB -> Não calcula
    2. Outros casos -> Calcula
    """
    if not pedido:
        return False
    
    # Se for FOB, não calcula frete
    if hasattr(pedido, 'rota') and pedido.rota and pedido.rota.upper().strip() == 'FOB':
        return False
    
    return True


def pedidos_mesmo_uf(pedidos):
    """
    Verifica se todos os pedidos são do mesmo UF.
    Regras:
    1. Se rota RED -> Considera SP
    2. Se rota FOB -> Ignora
    3. Outros casos -> Usa UF normalizado
    """
    if not pedidos:
        return True

    # Primeiro normaliza todos os UFs que ainda não foram normalizados
    for pedido in pedidos:
        if not pedido.uf_normalizada:
            normalizar_dados_pedido(pedido)

    # Pega o conjunto de UFs normalizados
    ufs = set()
    for pedido in pedidos:
        if (
            hasattr(pedido, "rota")
            and pedido.rota
            and pedido.rota.upper().strip() == "RED"
        ):
            ufs.add("SP")  # RED sempre é SP
        else:
            ufs.add(pedido.uf_normalizada)

    # Se tem mais de um UF, não permite
    if len(ufs) > 1:
        return False

    return True


def normalizar_uf_pedido(pedido):
    """
    Normaliza o UF do pedido considerando regras especiais:
    1. Se rota for RED, sempre retorna SP independente de cidade/UF
    2. Se cidade for SP, retorna SP
    3. Se cidade for RJ, retorna RJ
    4. Caso contrário, usa o UF do pedido
    """
    if not pedido:
        return None

    # Se for RED, é SP e pronto - nem olha cidade/UF
    if hasattr(pedido, "rota") and pedido.rota and pedido.rota.upper().strip() == "RED":
        return "SP"

    # Se cidade for SP, considera SP
    if pedido.nome_cidade and pedido.nome_cidade.upper().strip() == "SP":
        return "SP"

    # Se cidade for RJ, considera RJ
    if pedido.nome_cidade and pedido.nome_cidade.upper().strip() == "RJ":
        return "RJ"

    # Para outros casos, usa o UF do pedido
    if hasattr(pedido, "cod_uf") and pedido.cod_uf:
        uf = pedido.cod_uf.upper().strip()
        return uf

    return None


def normalizar_dados_pedido(pedido):
    """
    Normaliza os dados de cidade e UF do pedido.
    Regras:
    1. Se rota FOB -> Mantém cidade/UF original
    2. Se rota RED -> GUARULHOS/SP
    3. Se cidade SP -> SAO PAULO/SP
    4. Se cidade RJ -> RIO DE JANEIRO/RJ
    5. Outros casos -> Remove acentos e converte para maiúsculo
    """
    
    if not pedido:
        return
    
    # Normaliza UF
    if pedido.cod_uf:
        pedido.uf_normalizada = pedido.cod_uf.strip().upper()
    
    # Se for FOB, mantém os dados originais
    if hasattr(pedido, 'rota') and pedido.rota and pedido.rota.upper().strip() == 'FOB':
        pedido.cidade_normalizada = pedido.nome_cidade
        return
    
    # Se for RED, força GUARULHOS/SP
    if hasattr(pedido, 'rota') and pedido.rota and pedido.rota.upper().strip() == 'RED':
        pedido.cidade_normalizada = 'GUARULHOS'
        pedido.uf_normalizada = 'SP'
        return
    
    # Normaliza cidade usando a função unificada
    if pedido.nome_cidade:
        pedido.cidade_normalizada = normalizar_nome_cidade(
            pedido.nome_cidade,
            getattr(pedido, 'rota', None)
        )


def calcular_frete_por_cnpj(pedidos, veiculo_forcado=None):
    """
    Calcula fretes agrupando pedidos por CNPJ.
    
    Para carga DIRETA:
    - Uma única cotação para todos os CNPJs
    - Valor total único
    - Não tem rateio nenhum
    
    Para carga FRACIONADA:
    - Uma cotação por CNPJ
    - Valor total por CNPJ
    - Não tem rateio nenhum
    """
    resultados = {
        'diretas': [],
        'fracionadas': {}
    }
    
    # Agrupa pedidos por CNPJ
    grupos = agrupar_por_cnpj(pedidos)
    
    # Calcula totais gerais (para carga DIRETA)
    peso_total_geral = sum(p.peso_total or 0 for p in pedidos)
    valor_total_geral = sum(p.valor_saldo_total or 0 for p in pedidos)
    
    # Normaliza dados dos pedidos
    for pedido in pedidos:
        normalizar_dados_pedido(pedido)
    
    # Verifica se todos são do mesmo UF
    todos_mesmo_uf = pedidos_mesmo_uf(pedidos)
    
    if todos_mesmo_uf:
        # Se são do mesmo UF, pode ser DIRETA ou FRACIONADA
        
        # Pega primeiro pedido como referência
        pedido = pedidos[0]
        
        # Busca cidade destino
        cidade = buscar_cidade_unificada(
            cidade=pedido.cidade_normalizada,
            uf=pedido.uf_normalizada,
            rota=pedido.rota
        )
        if not cidade:
            return resultados
        
        # Para carga DIRETA, usa peso/valor total de TODOS os pedidos
        fretes_diretos = calcular_fretes_possiveis(
            cidade_destino_id=cidade.id,
            peso_utilizado=peso_total_geral,  # Usa peso total GERAL
            valor_carga=valor_total_geral,    # Usa valor total GERAL
            veiculo_forcado=veiculo_forcado,
            rota=pedido.rota,
            tipo_carga="DIRETA"
        )
        
        # Para cada opção de frete DIRETA
        resultados['diretas'].extend(fretes_diretos)
    
    # Para cada grupo de pedidos do mesmo CNPJ
    for cnpj, pedidos_grupo in grupos.items():
        # Calcula totais do grupo
        peso_total = sum(p.peso_total or 0 for p in pedidos_grupo)
        valor_total = sum(p.valor_saldo_total or 0 for p in pedidos_grupo)
        
        # Pega primeiro pedido como referência
        pedido = pedidos_grupo[0]
        
        # Busca cidade destino
        cidade = buscar_cidade_unificada(
            cidade=pedido.cidade_normalizada,
            uf=pedido.uf_normalizada,
            rota=pedido.rota
        )
        if not cidade:
            continue
        
        # Para carga FRACIONADA, calcula com peso/valor do grupo
        fretes_fracionados = calcular_fretes_possiveis(
            cidade_destino_id=cidade.id,
            peso_utilizado=peso_total,
            valor_carga=valor_total,
            veiculo_forcado=veiculo_forcado,
            rota=pedido.rota,
            tipo_carga="FRACIONADA"
        )
        
        # Para cada opção de frete FRACIONADA
        for frete in fretes_fracionados:
            transportadora_id = frete['transportadora_id']
            
            # ✅ CORREÇÃO: Copia TODOS os dados do frete + adiciona dados específicos do CNPJ
            opcao_cnpj = frete.copy()  # Copia todos os dados da tabela
            opcao_cnpj.update({
                'cnpj': cnpj,
                'cidade': cidade.nome,
                'uf': cidade.uf,
                'peso_grupo': peso_total,
                'valor_grupo': valor_total,
                'frete_kg': frete['valor_liquido'] / peso_total if peso_total > 0 else float('inf')
            })
            
            # Inicializa lista de opções do CNPJ se não existir
            if cnpj not in resultados['fracionadas']:
                resultados['fracionadas'][cnpj] = []
            
            # Adiciona opção na lista do CNPJ
            resultados['fracionadas'][cnpj].append(opcao_cnpj)
    
    return resultados


# ❌ FUNÇÕES REMOVIDAS - As otimizações agora são feitas em app/cotacao/routes.py
# - calcular_otimizacoes() - REMOVIDA (substituída pela lógica conservadora)
# - calcular_otimizacoes_pedido() - REMOVIDA (implementada em cotacao/routes.py)
# - calcular_fretes_diretos() - REMOVIDA (usava lógica antiga)


def buscar_cidade_unificada(pedido=None, cidade=None, uf=None, rota=None):
    """
    Função unificada para busca de cidades que implementa todas as regras:
    1. Se rota FOB -> Busca apenas por FOB
    2. Se rota RED -> Considera como GUARULHOS/SP
    3. Se cidade SP -> Considera como SAO PAULO
    4. Se cidade RJ -> Considera como RIO DE JANEIRO
    5. Normaliza nomes para comparação (maiúsculo, sem acentos)
    
    Pode receber:
    - Um objeto pedido
    - OU cidade e UF (e opcionalmente rota)
    """
    from app.utils.string_utils import normalizar_nome_cidade, remover_acentos
    
    # Se recebeu pedido, extrai os dados dele
    if pedido:
        if not hasattr(pedido, 'cidade_normalizada') or not pedido.cidade_normalizada:
            normalizar_dados_pedido(pedido)
            db.session.commit()
        
        cidade = pedido.cidade_normalizada
        uf = pedido.uf_normalizada
        rota = pedido.rota if hasattr(pedido, 'rota') else None
    
    # Valida parâmetros
    if not cidade or not uf:
        return None
    
    # Normaliza a cidade considerando a rota
    cidade_normalizada = normalizar_nome_cidade(cidade, rota)
    if not cidade_normalizada:
        if rota and rota.upper() == 'FOB':
            # Para FOB, busca direto por FOB
            return Cidade.query.filter(
                func.upper(Cidade.nome) == 'FOB'
            ).first()
        return None
    
    # Busca todas as cidades com o mesmo UF
    cidades = Cidade.query.filter(
        func.upper(Cidade.uf) == uf.upper()
    ).all()
    
    # Compara os nomes normalizados em Python
    for cidade_obj in cidades:
        if remover_acentos(cidade_obj.nome.upper()) == cidade_normalizada:
            return cidade_obj
    
    return None


def buscar_cidade(pedido):
    """
    Função de compatibilidade que usa buscar_cidade_unificada.
    Mantida para não quebrar código existente.
    """
    return buscar_cidade_unificada(pedido=pedido)

