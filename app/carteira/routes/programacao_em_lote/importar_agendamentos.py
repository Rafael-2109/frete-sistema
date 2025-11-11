"""
Módulo para importação de agendamentos do Assai via Excel
Implementação conforme especificação em import_agenda.md

Colunas esperadas no Excel:
- ID (números) -> Separacao.protocolo
- Status ("Aprovada" ou "Pendente") -> Separacao.agendamento_confirmado
- CNPJ Terminal (números sem formatação) -> Separacao.cnpj_cpf
- Data Efetiva (DD/MM/YYYY HH:MM:SS) -> Separacao.agendamento (quando Status=Aprovada)
- Data/Hora Sugerida: (DD/MM/YYYY HH:MM:SS) -> Separacao.agendamento (quando Status=Pendente e não tem Data Efetiva)
- Unidade Destino (nome da filial) -> para relatório de não encontrados

Regras de processamento:
1. Se Status=Aprovada e tem Data Efetiva: usa Data Efetiva com agendamento_confirmado=True
2. Se Status=Pendente e tem Data/Hora Sugerida: usa Data/Hora Sugerida com agendamento_confirmado=False
3. Se já existe protocolo+data+confirmado=True, ignora para não sobrescrever
4. Sempre calcula expedicao = agendamento - 1 dia útil (para SP)
"""

from flask import request, jsonify
from flask_login import login_required
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO
import logging
import traceback

from app import db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.carteira.utils.separacao_utils import calcular_peso_pallet_produto
from app.utils.lote_utils import gerar_lote_id
from app.utils.text_utils import truncar_observacao
from . import programacao_em_lote_bp

logger = logging.getLogger(__name__)


@programacao_em_lote_bp.route('/api/importar-agendamentos-assai', methods=['POST'])
@login_required
def importar_agendamentos_assai():
    """
    Importa agendamentos do Assai via Excel
    
    Busca registros em:
    1. Separacao com sincronizado_nf=False
    2. Separacao com nf_cd=True
    3. CarteiraPrincipal (saldo) - cria nova Separacao se necessário
    """
    try:
        # Verificar se arquivo foi enviado
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Arquivo vazio'}), 400
        
        # Verificar extensão
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Arquivo deve ser Excel (.xlsx ou .xls)'}), 400
        
        # Ler arquivo Excel
        try:
            df = pd.read_excel(BytesIO(file.read()))
            logger.info(f"Excel lido com {len(df)} linhas e colunas: {list(df.columns)}")
        except Exception as e:
            logger.error(f"Erro ao ler Excel: {str(e)}")
            return jsonify({'error': f'Erro ao ler arquivo Excel: {str(e)}'}), 400
        
        # Verificar colunas obrigatórias
        colunas_esperadas = ['ID', 'Status', 'CNPJ Terminal']
        colunas_faltantes = [col for col in colunas_esperadas if col not in df.columns]
        
        if colunas_faltantes:
            return jsonify({
                'error': f'Colunas obrigatórias faltando: {", ".join(colunas_faltantes)}'
            }), 400
        
        # Processar dados
        registros_processados = []
        registros_criados = []
        registros_atualizados = []
        registros_nao_encontrados = []
        erros = []
        
        for idx, row in df.iterrows():
            try:
                # Extrair dados da linha
                protocolo = str(row['ID']).strip() if pd.notna(row['ID']) else None
                status = str(row['Status']).strip().lower() if pd.notna(row['Status']) else ''
                cnpj_terminal = str(row['CNPJ Terminal']).strip() if pd.notna(row['CNPJ Terminal']) else ''
                data_efetiva = row.get('Data Efetiva')
                data_hora_sugerida = row.get('Data/Hora Sugerida:')  # Nova coluna para agendamentos pendentes
                unidade_destino = str(row.get('Unidade Destino', '')).strip() if 'Unidade Destino' in row else ''
                
                # Validações básicas
                if not protocolo:
                    erros.append(f"Linha {idx+2}: ID vazio") # type: ignore
                    continue
                
                if not cnpj_terminal:
                    erros.append(f"Linha {idx+2}: CNPJ Terminal vazio") # type: ignore
                    continue
                
                # Formatar CNPJ
                cnpj_formatado = _formatar_cnpj_assai(cnpj_terminal)
                if not cnpj_formatado:
                    erros.append(f"Linha {idx+2}: CNPJ inválido: {cnpj_terminal}") # type: ignore
                    continue
                
                # Determinar agendamento_confirmado baseado no Status
                # Status contém "Aprovada" (case insensitive) -> True
                # Caso contrário -> False
                agendamento_confirmado = 'aprovada' in status
                
                # Processar datas de agendamento
                data_agendamento = None
                data_expedicao = None
                
                # Lógica de processamento de data:
                # 1. Se Status = Aprovada e tem Data Efetiva -> usar Data Efetiva com confirmado=True
                # 2. Se Status = Pendente (ou não tem Data Efetiva) e tem Data/Hora Sugerida -> usar Data/Hora Sugerida com confirmado=False
                
                if agendamento_confirmado and pd.notna(data_efetiva):
                    # Caso 1: Agendamento aprovado com Data Efetiva
                    try:
                        # Converter para datetime e extrair apenas a data
                        if isinstance(data_efetiva, str):
                            # Formato esperado: "16/09/2025 07:00:00"
                            # Pegar apenas a parte da data
                            data_parte = data_efetiva.split()[0] if ' ' in data_efetiva else data_efetiva
                            data_agendamento = datetime.strptime(data_parte, '%d/%m/%Y').date()
                        else:
                            # Se já for datetime do pandas
                            data_agendamento = pd.to_datetime(data_efetiva).date()
                        
                        # Para SP: expedicao = agendamento - 1 dia útil
                        data_expedicao = _subtrair_dia_util(data_agendamento)
                        
                    except Exception as e:
                        erros.append(f"Linha {idx+2}: Data Efetiva inválida: {data_efetiva} - {str(e)}") # type: ignore
                        continue
                        
                elif not agendamento_confirmado and pd.notna(data_hora_sugerida):
                    # Caso 2: Agendamento pendente com Data/Hora Sugerida
                    try:
                        # Converter para datetime e extrair apenas a data
                        if isinstance(data_hora_sugerida, str):
                            # Formato esperado: "16/09/2025 07:00:00" ou "16/09/2025"
                            # Pegar apenas a parte da data
                            data_parte = data_hora_sugerida.split()[0] if ' ' in data_hora_sugerida else data_hora_sugerida
                            data_agendamento = datetime.strptime(data_parte, '%d/%m/%Y').date()
                        else:
                            # Se já for datetime do pandas
                            data_agendamento = pd.to_datetime(data_hora_sugerida).date()
                        
                        # Para SP: expedicao = agendamento - 1 dia útil (mesma regra)
                        data_expedicao = _subtrair_dia_util(data_agendamento)
                        
                        # IMPORTANTE: Manter agendamento_confirmado = False
                        agendamento_confirmado = False
                        
                    except Exception as e:
                        erros.append(f"Linha {idx+2}: Data/Hora Sugerida inválida: {data_hora_sugerida} - {str(e)}") # type: ignore
                        continue
                
                # Processar registro
                resultado = _processar_registro_agendamento(
                    cnpj_formatado,
                    protocolo,
                    agendamento_confirmado,
                    data_agendamento,
                    data_expedicao
                )
                
                if resultado['encontrado']:
                    if resultado['criado']:
                        registros_criados.append({
                            'cnpj': cnpj_formatado,
                            'protocolo': protocolo,
                            'status': 'Aprovada' if agendamento_confirmado else 'Pendente',
                            'data': data_agendamento.strftime('%d/%m/%Y') if data_agendamento else '-'
                        })
                    else:
                        registros_atualizados.append({
                            'cnpj': cnpj_formatado,
                            'protocolo': protocolo,
                            'status': 'Aprovada' if agendamento_confirmado else 'Pendente',
                            'data': data_agendamento.strftime('%d/%m/%Y') if data_agendamento else '-',
                            'qtd_registros': resultado['atualizados']
                        })
                else:
                    # Não encontrado no sistema
                    registros_nao_encontrados.append({
                        'cnpj': cnpj_formatado,
                        'protocolo': protocolo,
                        'unidade': unidade_destino,
                        'status': 'Aprovada' if agendamento_confirmado else 'Pendente',
                        'data': data_agendamento.strftime('%d/%m/%Y') if data_agendamento else '-'
                    })
                
                registros_processados.append(protocolo)
                
            except Exception as e:
                erros.append(f"Linha {idx+2}: Erro ao processar: {str(e)}") # type: ignore
                logger.error(f"Erro na linha {idx+2}: {str(e)}\n{traceback.format_exc()}") # type: ignore   
        
        # Commit das alterações
        try:
            db.session.commit()
            
            # Preparar resposta detalhada
            resposta = {
                'success': True,
                'resumo': {
                    'total_linhas': len(df),
                    'total_processados': len(registros_processados),
                    'criados': len(registros_criados),
                    'atualizados': len(registros_atualizados),
                    'nao_encontrados': len(registros_nao_encontrados),
                    'erros': len(erros)
                },
                'detalhes': {
                    'criados': registros_criados[:20],  # Primeiros 20
                    'atualizados': registros_atualizados[:20],  # Primeiros 20
                    'nao_encontrados': registros_nao_encontrados,  # Todos (importante para o usuário)
                    'erros': erros[:20]  # Primeiros 20 erros
                }
            }
            
            logger.info(f"Importação Assai concluída: {resposta['resumo']}")
            return jsonify(resposta)
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao salvar no banco: {str(e)}")
            return jsonify({'error': f'Erro ao salvar alterações: {str(e)}'}), 500
        
    except Exception as e:
        logger.error(f"Erro geral na importação Assai: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Erro ao processar importação: {str(e)}'}), 500


def _formatar_cnpj_assai(cnpj_numerico):
    """
    Formata CNPJ numérico (sem pontuação) para o padrão XX.XXX.XXX/XXXX-XX
    
    Args:
        cnpj_numerico: String com apenas números do CNPJ
        
    Returns:
        String formatada ou None se inválido
    """
    try:
        # Remover qualquer caractere não numérico
        cnpj_limpo = ''.join(filter(str.isdigit, str(cnpj_numerico)))
        
        # Se CNPJ tem 13 dígitos, adicionar zero à esquerda (Excel remove zeros iniciais)
        if len(cnpj_limpo) == 13:
            logger.info(f"CNPJ com 13 dígitos detectado: {cnpj_limpo}, adicionando zero inicial")
            cnpj_limpo = '0' + cnpj_limpo
        
        # CNPJ deve ter exatamente 14 dígitos
        if len(cnpj_limpo) != 14:
            logger.warning(f"CNPJ com tamanho inválido: {cnpj_limpo} ({len(cnpj_limpo)} dígitos)")
            return None
        
        # Formatar: XX.XXX.XXX/XXXX-XX
        cnpj_formatado = f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}"
        
        return cnpj_formatado
        
    except Exception as e:
        logger.error(f"Erro ao formatar CNPJ {cnpj_numerico}: {str(e)}")
        return None


def _subtrair_dia_util(data):
    """
    Subtrai 1 dia útil de uma data
    
    Args:
        data: date object
        
    Returns:
        date object com 1 dia útil subtraído
    """
    # Subtrair 1 dia
    data_resultado = data - timedelta(days=1)
    
    # Se cair no fim de semana, voltar para sexta
    # weekday(): 0=segunda, 1=terça, ..., 4=sexta, 5=sábado, 6=domingo
    while data_resultado.weekday() >= 5:
        data_resultado -= timedelta(days=1)
    
    return data_resultado


def _processar_registro_agendamento(cnpj, protocolo, confirmado, data_agendamento, data_expedicao):
    """
    Processa um registro de agendamento, atualizando existentes ou criando novos
    
    Ordem de busca:
    1. Separacao com sincronizado_nf=False (separações em aberto)
    2. Separacao com nf_cd=True (NFs voltadas ao CD)  
    3. CarteiraPrincipal (saldo) - cria nova Separacao se encontrar
    
    Args:
        cnpj: CNPJ formatado do cliente
        protocolo: ID do agendamento
        confirmado: Boolean indicando se está aprovado
        data_agendamento: Date do agendamento (None se pendente)
        data_expedicao: Date da expedição (None se pendente)
        
    Returns:
        dict com informações do processamento
    """
    encontrado = False
    criado = False
    registros_atualizados = 0
    
    # 1. Buscar e atualizar em Separacao (sincronizado_nf=False)
    # Estas são separações em aberto que ainda não foram faturadas
    separacoes_abertas = Separacao.query.filter_by(
        cnpj_cpf=cnpj,
        cod_uf='SP',
        sincronizado_nf=False
    ).all()
    
    for sep in separacoes_abertas:
        # NOVA REGRA: Se já existe um protocolo confirmado com a mesma data, não sobrescrever
        if (sep.protocolo == protocolo and 
            sep.agendamento_confirmado == True and 
            sep.agendamento == data_agendamento and
            sep.agendamento is not None): # type: ignore
            logger.info(f"Ignorando Separacao ID {sep.id}: já tem protocolo {protocolo} confirmado com data {data_agendamento}")
            encontrado = True
            continue
        
        # Atualizar protocolo
        sep.protocolo = protocolo
        sep.agendamento_confirmado = confirmado
        
        # IMPORTANTE: Se status é PREVISAO, mudar para ABERTO
        if sep.status == 'PREVISAO':
            sep.status = 'ABERTO'
            logger.info(f"Status alterado de PREVISAO para ABERTO no ID {sep.id}")
        
        if confirmado and data_agendamento:
            # Status Aprovada: preencher datas
            sep.agendamento = data_agendamento
            sep.expedicao = data_expedicao
        else:
            # Status Pendente: limpar agendamento
            sep.agendamento = None
            # Manter expedição existente ou limpar também?
            # Por segurança, vamos manter a expedição
        
        registros_atualizados += 1
        encontrado = True
        
        logger.info(f"Atualizado Separacao ID {sep.id}: protocolo={protocolo}, confirmado={confirmado}")
    
    # 2. Buscar e atualizar em Separacao (nf_cd=True)
    # Estas são NFs que voltaram para o CD
    nfs_cd = Separacao.query.filter_by(
        cnpj_cpf=cnpj,
        cod_uf='SP',
        nf_cd=True,
        sincronizado_nf=True
    ).all()
    
    for nf in nfs_cd:
        # NOVA REGRA: Se já existe um protocolo confirmado com a mesma data, não sobrescrever
        if (nf.protocolo == protocolo and 
            nf.agendamento_confirmado == True and 
            nf.agendamento == data_agendamento and
            nf.agendamento is not None): # type: ignore
            logger.info(f"Ignorando NF no CD ID {nf.id}: já tem protocolo {protocolo} confirmado com data {data_agendamento}")
            encontrado = True
            continue
        
        # Atualizar protocolo
        nf.protocolo = protocolo
        nf.agendamento_confirmado = confirmado
        
        if confirmado and data_agendamento:
            # Status Aprovada: preencher datas
            nf.agendamento = data_agendamento
            nf.expedicao = data_expedicao
        else:
            # Status Pendente: limpar agendamento
            nf.agendamento = None
        
        registros_atualizados += 1
        encontrado = True
        
        logger.info(f"Atualizado NF no CD ID {nf.id}: protocolo={protocolo}, confirmado={confirmado}")
    
    # 3. Se não encontrou em Separacao, buscar na CarteiraPrincipal
    if not encontrado:
        # Buscar itens ativos na carteira para este CNPJ/SP
        itens_carteira = CarteiraPrincipal.query.filter_by(
            cnpj_cpf=cnpj,
            cod_uf='SP',
            ativo=True
        ).all()
        
        if itens_carteira:
            logger.info(f"Encontrados {len(itens_carteira)} itens na CarteiraPrincipal para CNPJ {cnpj}")
            
            # Agrupar por num_pedido
            pedidos_dict = {}
            for item in itens_carteira:
                if item.num_pedido not in pedidos_dict:
                    pedidos_dict[item.num_pedido] = []
                pedidos_dict[item.num_pedido].append(item)
            
            logger.info(f"Agrupados em {len(pedidos_dict)} pedidos distintos")
            
            # Criar Separacoes para cada pedido
            for num_pedido, itens in pedidos_dict.items():
                # Usar o primeiro item para dados gerais
                primeiro_item = itens[0]

                # Gerar um único lote_id para todos os produtos deste pedido
                lote_id = gerar_lote_id()

                # Lista para armazenar produtos com saldo disponível
                produtos_com_saldo = []

                for item in itens:
                    qtd_carteira = float(item.qtd_saldo_produto_pedido or 0)

                    # IMPORTANTE: Abater o que já foi separado (sincronizado_nf=False)
                    qtd_ja_separada = db.session.query(
                        db.func.coalesce(db.func.sum(Separacao.qtd_saldo), 0)
                    ).filter(
                        Separacao.num_pedido == item.num_pedido,
                        Separacao.cod_produto == item.cod_produto,
                        Separacao.sincronizado_nf == False
                    ).scalar()

                    qtd = qtd_carteira - float(qtd_ja_separada)

                    # Se não há saldo disponível, pular este item
                    if qtd <= 0:
                        logger.info(f"Produto {item.cod_produto} do pedido {num_pedido} não tem saldo disponível")
                        continue

                    preco = float(item.preco_produto_pedido or 0)
                    valor = qtd * preco

                    # Calcular peso e pallet
                    peso_calculado = 0
                    pallet_calculado = 0
                    try:
                        # calcular_peso_pallet_produto retorna tupla (peso, pallet)
                        peso_calculado, pallet_calculado = calcular_peso_pallet_produto(item.cod_produto, qtd)
                    except Exception as e:
                        logger.warning(f"Erro ao calcular peso/pallet para produto {item.cod_produto}: {e}")

                    produtos_com_saldo.append({
                        'item': item,
                        'qtd': qtd,
                        'valor': valor,
                        'peso': peso_calculado,
                        'pallet': pallet_calculado
                    })

                # Só criar Separacoes se houver produtos com saldo
                if not produtos_com_saldo:
                    logger.info(f"Pedido {num_pedido} não tem produtos com saldo disponível")
                    continue

                # 🔧 DETERMINAR tipo_envio CORRETAMENTE
                from app.carteira.utils.separacao_utils import determinar_tipo_envio

                # Preparar lista de produtos no formato esperado
                produtos_lote = [{'cod_produto': p['item'].cod_produto, 'quantidade': p['qtd']} for p in produtos_com_saldo]

                # Buscar produtos na carteira
                produtos_carteira = {}
                for item in CarteiraPrincipal.query.filter_by(num_pedido=num_pedido, ativo=True).all():
                    produtos_carteira[item.cod_produto] = item

                tipo_envio_correto = determinar_tipo_envio(num_pedido, produtos_lote, produtos_carteira)
                logger.info(f"✅ tipo_envio determinado: {tipo_envio_correto} para pedido {num_pedido} (importação)")

                # Criar uma Separacao para cada produto com saldo
                for produto_info in produtos_com_saldo:
                    item = produto_info['item']

                    nova_separacao = Separacao(
                        separacao_lote_id=lote_id,  # Mesmo lote_id para todos os produtos do pedido
                        num_pedido=num_pedido,
                        data_pedido=item.data_pedido,
                        cnpj_cpf=cnpj,
                        raz_social_red=item.raz_social_red,
                        nome_cidade=item.nome_cidade,
                        cod_uf='SP',
                        cod_produto=item.cod_produto,  # Código real do produto
                        nome_produto=item.nome_produto,  # Nome real do produto
                        qtd_saldo=produto_info['qtd'],
                        valor_saldo=produto_info['valor'],
                        peso=produto_info['peso'],
                        pallet=produto_info['pallet'],
                        pedido_cliente=item.pedido_cliente,
                        protocolo=protocolo,
                        agendamento_confirmado=confirmado,
                        agendamento=data_agendamento if confirmado else None,
                        expedicao=data_expedicao if confirmado else None,
                        tipo_envio=tipo_envio_correto,  # 🔧 CORRIGIDO: Usa determinar_tipo_envio()
                        status='ABERTO',  # Status para agendamentos importados
                        sincronizado_nf=False,
                        nf_cd=False,
                        observ_ped_1=truncar_observacao(item.observ_ped_1)
                    )

                    db.session.add(nova_separacao)
                    logger.info(f"Criada Separacao para produto {item.cod_produto} do pedido {num_pedido}")

                criado = True
                encontrado = True

                logger.info(f"Criadas {len(produtos_com_saldo)} Separacoes para pedido {num_pedido} com lote {lote_id}")
    
    return {
        'encontrado': encontrado,
        'criado': criado,
        'atualizados': registros_atualizados
    }