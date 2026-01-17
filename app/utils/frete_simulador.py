from collections import defaultdict

from sqlalchemy import func

from app.localidades.models import Cidade
from app.tabelas.models import TabelaFrete
from app.vinculos.models import CidadeAtendida
from app.veiculos.models import Veiculo
from app.utils.string_utils import normalizar_nome_cidade, remover_acentos
from app.utils.vehicle_utils import normalizar_nome_veiculo
from app.utils.grupo_empresarial import grupo_service
from app.utils.calculadora_frete import CalculadoraFrete  # Nova importação
from app.utils.tabela_frete_manager import TabelaFreteManager  # Usar o manager centralizado
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
    
    ✅ NOVA LÓGICA: Para carga DIRETA, aplica "tabela mais cara" por transportadora/modalidade
    Para outras cargas, mantém comportamento original
    
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
        cidade = db.session.get(Cidade,cidade_destino_id) if cidade_destino_id else None
        if not cidade:
            return []
        # ✅ CARREGA DADOS DA CIDADE IMEDIATAMENTE PARA EVITAR PROBLEMAS DE SESSÃO
        try:
            cidade_nome = cidade.nome
            cidade_uf = cidade.uf
            cidade_icms = cidade.icms or 0
            cidade_codigo_ibge = cidade.codigo_ibge
        except Exception as e:
            print(f"[DEBUG] ⚠️ Erro ao acessar dados da cidade {cidade_destino_id}: {e}")
            return []
        
        # Se não foi passado uf_destino, usa o da cidade
        if not uf_destino:
            uf_destino = cidade_uf
    else:
        cidade = buscar_cidade_unificada(
            cidade=cidade_destino,
            uf=uf_destino,
            rota=rota
        )
        if not cidade:
            return []
        
        # ✅ CARREGA DADOS DA CIDADE IMEDIATAMENTE PARA EVITAR PROBLEMAS DE SESSÃO
        try:
            cidade_nome = cidade.nome
            cidade_uf = cidade.uf
            cidade_icms = cidade.icms or 0
            cidade_codigo_ibge = cidade.codigo_ibge
        except Exception as e:
            print(f"[DEBUG] ⚠️ Erro ao acessar dados da cidade: {e}")
            return []

    # Se for FOB, retorna vazio
    if cidade_nome.upper() == 'FOB':
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
        CidadeAtendida.codigo_ibge == cidade_codigo_ibge
    ).all()
    
    if not atendimentos:
        return []
    
    # ✅ NOVA LÓGICA: Para carga DIRETA, agrupa por transportadora/uf_destino/modalidade para aplicar "tabela mais cara"
    if tipo_carga == "DIRETA":
        grupos_direta = {}  # (transportadora_id, uf_destino, modalidade) -> [opcoes_calculadas]
        
        print(f"[DEBUG] 🎯 CARGA DIRETA: Aplicando lógica de tabela mais cara por transportadora/UF/modalidade")
        
    # Processa todas as transportadoras
    for at in atendimentos:
        # ✅ NOVO: Verificar se transportadora está ativa
        if hasattr(at, 'transportadora') and hasattr(at.transportadora, 'ativo'):
            if not at.transportadora.ativo:
                continue  # Pula transportadoras inativas
        
        # 🏢 GRUPO EMPRESARIAL: Busca tabelas em todas as transportadoras do grupo
        grupo_ids = grupo_service.obter_transportadoras_grupo(at.transportadora_id)
        
        # Busca final com todos os filtros - INCLUINDO GRUPO EMPRESARIAL
        tabelas = TabelaFrete.query.filter(
            TabelaFrete.transportadora_id.in_(grupo_ids),  # ✅ MUDANÇA: Busca em todo o grupo!
            TabelaFrete.uf_origem == (uf_origem or "SP"),
            TabelaFrete.uf_destino == (uf_destino or cidade_uf),
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

            # ✅ INTEGRAÇÃO COM CALCULADORA CENTRALIZADA
            
            # Usar TabelaFreteManager para preparar dados (já inclui novos campos!)
            dados_tabela = TabelaFreteManager.preparar_dados_tabela(tf)
            
            # Adicionar informação da transportadora para cálculo do líquido
            dados_tabela['transportadora_optante'] = at.transportadora.optante
            
            # Configuração da transportadora (novos campos de quando aplicar componentes)
            transportadora_config = None
            if hasattr(at.transportadora, 'aplica_gris_pos_minimo'):
                transportadora_config = {
                    'aplica_gris_pos_minimo': at.transportadora.aplica_gris_pos_minimo or False,
                    'aplica_adv_pos_minimo': at.transportadora.aplica_adv_pos_minimo or False,
                    'aplica_rca_pos_minimo': at.transportadora.aplica_rca_pos_minimo or False,
                    'aplica_pedagio_pos_minimo': at.transportadora.aplica_pedagio_pos_minimo or False,
                    'aplica_tas_pos_minimo': at.transportadora.aplica_tas_pos_minimo or False,
                    'aplica_despacho_pos_minimo': at.transportadora.aplica_despacho_pos_minimo or False,
                    'aplica_cte_pos_minimo': at.transportadora.aplica_cte_pos_minimo or False,
                    'pedagio_por_fracao': at.transportadora.pedagio_por_fracao if hasattr(at.transportadora, 'pedagio_por_fracao') else True
                }
            
            # Chamar calculadora centralizada
            resultado_calculo = CalculadoraFrete.calcular_frete_unificado(
                peso=peso_final,
                valor_mercadoria=valor_final,
                tabela_dados=dados_tabela,  # CORREÇÃO: dados_tabela -> tabela_dados
                transportadora_optante=at.transportadora.optante,
                transportadora_config=transportadora_config,
                cidade={'icms': cidade_icms} if cidade_icms else None,
                codigo_ibge=cidade_codigo_ibge
            )
            
            # Extrair valores do resultado
            frete_com_icms = resultado_calculo['valor_com_icms']
            valor_liquido = resultado_calculo['valor_liquido']

            # Só inclui se tiver algum valor
            if frete_com_icms > 0:
                
                # Cria opção calculada com todos os dados necessários
                opcao_calculada = {
                    "transportadora": at.transportadora.razao_social,
                    "transportadora_id": at.transportadora.id,
                    "modalidade": tf.modalidade,
                    "tipo_carga": tf.tipo_carga,
                    "valor_total": round(frete_com_icms, 2),
                    "valor_liquido": round(valor_liquido, 2),
                    "nome_tabela": at.nome_tabela,
                    "icms_destino": cidade_icms,
                    "cidade": cidade_nome,
                    "uf": cidade_uf,
                    # Detalhes do cálculo (útil para debug)
                    "detalhes_calculo": resultado_calculo.get('detalhes', {})
                }
                
                # Adicionar todos os campos da tabela usando o que já foi preparado
                # Isso garante que TODOS os campos (incluindo novos) estejam presentes
                opcao_calculada.update(dados_tabela)
                
                # ✅ APLICA LÓGICA ESPECÍFICA POR TIPO DE CARGA
                if tipo_carga == "DIRETA":
                    # 🎯 CARGA DIRETA: Agrupa por (transportadora_id, uf_destino, modalidade)
                    chave_grupo = (at.transportadora_id, cidade_uf, tf.modalidade)
                    
                    if chave_grupo not in grupos_direta:
                        grupos_direta[chave_grupo] = []
                    grupos_direta[chave_grupo].append(opcao_calculada)
                else:
                    # ✅ OUTRAS CARGAS: Adiciona diretamente
                    resultados.append(opcao_calculada)

    # ✅ APLICA LÓGICA "TABELA MAIS CARA" apenas para carga DIRETA
    if tipo_carga == "DIRETA":
        print(f"[DEBUG] 🎯 CARGA DIRETA: Processando {len(grupos_direta)} grupos (transportadora/UF/modalidade)")
        
        for (transportadora_id, uf_destino, modalidade), opcoes in grupos_direta.items():
            if len(opcoes) > 1:
                # Tem mais de uma tabela para esta combinação -> escolhe a MAIS CARA
                opcao_mais_cara = max(opcoes, key=lambda x: x['valor_liquido'])
                print(f"[DEBUG] 📊 Transp {transportadora_id} {uf_destino} {modalidade}: {len(opcoes)} tabelas → escolhida mais cara: {opcao_mais_cara['nome_tabela']} (R${opcao_mais_cara['valor_liquido']:.2f})")
                
                # ✅ MELHORIA: Adiciona informação sobre o critério de seleção
                opcao_mais_cara['nome_tabela'] = f"{opcao_mais_cara['nome_tabela']} (MAIS CARA p/ {uf_destino})"
                opcao_mais_cara['criterio_selecao'] = f"Tabela mais cara entre {len(opcoes)} opções para {uf_destino}"
                resultados.append(opcao_mais_cara)
            else:
                # Apenas uma tabela para esta combinação
                print(f"[DEBUG] 📋 Transp {transportadora_id} {uf_destino} {modalidade}: 1 tabela única: {opcoes[0]['nome_tabela']} (R${opcoes[0]['valor_liquido']:.2f})")
                opcoes[0]['criterio_selecao'] = f"Tabela única para {uf_destino}"
                resultados.append(opcoes[0])

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
    1. Se rota FOB -> Ignora
    2. Outros casos -> Usa UF normalizado
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
        ufs.add(pedido.uf_normalizada)

    # Se tem mais de um UF, não permite
    if len(ufs) > 1:
        return False

    return True

def normalizar_dados_pedido(pedido):
    """
    Normaliza os dados de cidade e UF do pedido.
    Regras:
    1. Se rota FOB -> Mantém cidade/UF original
    2. Se cidade SP -> SAO PAULO/SP
    3. Se cidade RJ -> RIO DE JANEIRO/RJ
    4. Outros casos -> Remove acentos e converte para maiúsculo
    ✅ CORRIGIDO: Atualiza Separacao em vez de Pedido (que é VIEW)
    """
    
    if not pedido:
        return
    
    # Determina valores normalizados
    uf_normalizada = None
    cidade_normalizada = None
    
    # Normaliza UF
    if pedido.cod_uf:
        uf_normalizada = pedido.cod_uf.strip().upper()
    
    # Se for FOB, mantém os dados originais
    if hasattr(pedido, 'rota') and pedido.rota and pedido.rota.upper().strip() == 'FOB':
        cidade_normalizada = pedido.nome_cidade
    else:
        # Normaliza cidade usando a função unificada
        if pedido.nome_cidade:
            cidade_normalizada = normalizar_nome_cidade(
                pedido.nome_cidade,
                getattr(pedido, 'rota', None)
            )
    
    # ✅ CORRIGIDO: Atualiza diretamente na tabela Separacao se tiver separacao_lote_id
    if hasattr(pedido, 'separacao_lote_id') and pedido.separacao_lote_id:
        from app.separacao.models import Separacao
        from app import db
        
        update_data = {}
        if uf_normalizada is not None:
            update_data['uf_normalizada'] = uf_normalizada
        if cidade_normalizada is not None:
            update_data['cidade_normalizada'] = cidade_normalizada
        
        if update_data:
            Separacao.query.filter_by(
                separacao_lote_id=pedido.separacao_lote_id
            ).update(update_data)
            db.session.commit()
    
    # ✅ IMPORTANTE: NÃO atribuir diretamente ao pedido para evitar UPDATE na VIEW
    # Os valores já foram salvos na tabela Separacao acima
    # Se precisar usar os valores normalizados, leia direto dos atributos ou use getattr


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
        
        # ✅ CORREÇÃO CRÍTICA: Para CARGA DIRETA, precisa buscar tabelas de TODAS as cidades
        print(f"[DEBUG] 🎯 CARGA DIRETA: Iniciando busca para múltiplas cidades do mesmo UF")
        
        # Identifica todas as cidades únicas dos pedidos
        cidades_unicas = set()
        uf_comum = None
        
        for pedido in pedidos:
            cidade = buscar_cidade_unificada(
                cidade=pedido.cidade_normalizada,
                uf=pedido.uf_normalizada,
                rota=pedido.rota
            )
            if cidade:
                cidades_unicas.add(cidade.id)
                uf_comum = cidade.uf
        
        if not cidades_unicas:
            return resultados
        
        print(f"[DEBUG] 📍 Encontradas {len(cidades_unicas)} cidades únicas para UF {uf_comum}")
        
        # ✅ NOVA LÓGICA: Busca tabelas para TODAS as cidades e compara
        grupos_direta_multiplas_cidades = {}  # (transportadora_id, modalidade) -> [opcoes_todas_cidades]
        
        for cidade_id in cidades_unicas:
            print(f"[DEBUG] 🔍 Buscando tabelas para cidade_id {cidade_id}")
            
            # Busca fretes para esta cidade específica
            fretes_cidade = calcular_fretes_possiveis(
                cidade_destino_id=cidade_id,
                peso_utilizado=peso_total_geral,
                valor_carga=valor_total_geral,
                veiculo_forcado=veiculo_forcado,
                rota=pedidos[0].rota if pedidos else None,
                tipo_carga="DIRETA"
            )
            
            # Adiciona ao grupo geral para comparação
            for opcao in fretes_cidade:
                chave = (opcao['transportadora_id'], opcao['modalidade'])
                
                if chave not in grupos_direta_multiplas_cidades:
                    grupos_direta_multiplas_cidades[chave] = []
                
                # Adiciona informação da cidade de origem da tabela
                opcao['cidade_origem_tabela'] = opcao.get('cidade', 'N/A')
                grupos_direta_multiplas_cidades[chave].append(opcao)
        
        # ✅ APLICA LÓGICA "TABELA MAIS CARA" considerando TODAS as cidades
        print(f"[DEBUG] 🎯 Aplicando lógica tabela mais cara para {len(grupos_direta_multiplas_cidades)} grupos")
        
        for (transportadora_id, modalidade), opcoes_todas_cidades in grupos_direta_multiplas_cidades.items():
            if len(opcoes_todas_cidades) > 1:
                # ✅ CORREÇÃO: Escolhe a MAIS CARA entre todas as cidades
                opcao_mais_cara = max(opcoes_todas_cidades, key=lambda x: x['valor_liquido'])
                
                cidades_consideradas = [opt['cidade_origem_tabela'] for opt in opcoes_todas_cidades]
                print(f"[DEBUG] 📊 Transp {transportadora_id} {modalidade}: {len(opcoes_todas_cidades)} tabelas de {len(set(cidades_consideradas))} cidades → mais cara: {opcao_mais_cara['nome_tabela']} de {opcao_mais_cara['cidade_origem_tabela']} (R${opcao_mais_cara['valor_liquido']:.2f})")
                
                # Atualiza informações da seleção
                opcao_mais_cara['nome_tabela'] = f"{opcao_mais_cara['nome_tabela']} (MAIS CARA - {opcao_mais_cara['cidade_origem_tabela']})"
                opcao_mais_cara['criterio_selecao'] = f"Tabela mais cara entre {len(opcoes_todas_cidades)} opções de {len(set(cidades_consideradas))} cidades"
                opcao_mais_cara['cidades_comparadas'] = list(set(cidades_consideradas))
                
                resultados['diretas'].append(opcao_mais_cara)
            else:
                # Apenas uma tabela encontrada
                opcao_unica = opcoes_todas_cidades[0]
                print(f"[DEBUG] 📋 Transp {transportadora_id} {modalidade}: tabela única de {opcao_unica['cidade_origem_tabela']}: {opcao_unica['nome_tabela']} (R${opcao_unica['valor_liquido']:.2f})")
                
                opcao_unica['criterio_selecao'] = f"Tabela única encontrada de {opcao_unica['cidade_origem_tabela']}"
                resultados['diretas'].append(opcao_unica)
    
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

def buscar_cidade_unificada(pedido=None, cidade=None, uf=None, rota=None):
    """
    Função unificada para busca de cidades que implementa todas as regras:
    1. Se rota FOB -> Busca apenas por FOB
    2. Se cidade SP -> Considera como SAO PAULO
    3. Se cidade RJ -> Considera como RIO DE JANEIRO
    4. Normaliza nomes para comparação (maiúsculo, sem acentos)
    
    Pode receber:
    - Um objeto pedido
    - OU cidade e UF (e opcionalmente rota)
    """
    
    # Se recebeu pedido, extrai os dados dele
    if pedido:
        # ✅ CORRIGIDO: Busca valores normalizados da Separacao se necessário
        if not hasattr(pedido, 'cidade_normalizada') or not pedido.cidade_normalizada:
            # Normaliza dados salvando na Separacao (sem commit extra)
            normalizar_dados_pedido(pedido)
            
            # Busca os valores recém-salvos da Separacao
            if hasattr(pedido, 'separacao_lote_id') and pedido.separacao_lote_id:
                from app.separacao.models import Separacao
                sep = Separacao.query.filter_by(
                    separacao_lote_id=pedido.separacao_lote_id
                ).first()
                if sep:
                    cidade = sep.cidade_normalizada
                    uf = sep.uf_normalizada
                else:
                    # Fallback para valores originais
                    cidade = pedido.nome_cidade
                    uf = pedido.cod_uf
            else:
                # Fallback para valores originais
                cidade = pedido.nome_cidade
                uf = pedido.cod_uf
        else:
            cidade = pedido.cidade_normalizada
            uf = pedido.uf_normalizada
        
        rota = pedido.rota if hasattr(pedido, 'rota') else None
    
    # Valida parâmetros
    if not cidade or not uf:
        return None
    
    # Normaliza a cidade considerando a rota
    cidade_normalizada = normalizar_nome_cidade(cidade, rota)
    if not cidade_normalizada:
        # Se rota FOB, busca direto por FOB
        if rota and rota.upper() == 'FOB':
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
