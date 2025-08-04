"""
Serviço para processamento de importação de faturamento TagPlus via Excel
Centraliza a lógica de importação para evitar duplicação
"""
import openpyxl
from datetime import datetime
from decimal import Decimal
from app import db
from app.carteira.models import CadastroCliente
from app.producao.models import CadastroPalletizacao
from app.faturamento.models import FaturamentoProduto
from app.integracoes.tagplus.processador_faturamento_tagplus import ProcessadorFaturamentoTagPlus
import logging
import os

logger = logging.getLogger(__name__)

def limpar_cnpj(cnpj):
    """Remove formatação do CNPJ"""
    if not cnpj:
        return None
    return ''.join(filter(str.isdigit, cnpj))

def extrair_codigo_produto(codigo_str):
    """Extrai código do produto removendo aspas"""
    if not codigo_str:
        return None
    return str(codigo_str).strip("'")

def converter_data(data_str):
    """Converte string de data para objeto date"""
    if not data_str:
        # Se não tem data, usa data atual
        logger.warning(f"Data vazia, usando data atual")
        return datetime.now().date()
    try:
        data_parte = str(data_str)[:10]
        return datetime.strptime(data_parte, '%d/%m/%Y').date()
    except Exception as e:
        # Se falha na conversão, usa data atual
        logger.warning(f"Erro ao converter data '{data_str}': {e}. Usando data atual.")
        return datetime.now().date()

def converter_quantidade(qtd_str):
    """Converte string de quantidade para Decimal"""
    if not qtd_str:
        return Decimal('0')
    try:
        qtd_limpa = str(qtd_str).strip().replace(',', '.')
        return Decimal(qtd_limpa)
    except Exception:
        return Decimal('0')

def converter_valor(valor_str):
    """Converte string de valor monetário para Decimal"""
    if not valor_str:
        return Decimal('0')
    try:
        valor_limpo = str(valor_str).strip().replace('.', '').replace(',', '.')
        return Decimal(valor_limpo)
    except Exception:
        return Decimal('0')

def processar_arquivo_tagplus_web(arquivo_excel, processar_completo=True):
    """
    Processa arquivo Excel do TagPlus e retorna resultado para a web
    
    Args:
        arquivo_excel: Caminho do arquivo Excel
        processar_completo: Se deve executar todas as sincronizações
        
    Returns:
        dict: Resultado do processamento
    """
    try:
        # Detecta a extensão do arquivo
        _, ext = os.path.splitext(arquivo_excel.lower())
        
        if ext == '.xls':
            # ÚLTIMA TENTATIVA: tenta com diferentes engines
            logger.info(f"Tentando processar arquivo .xls...")
            
            # Lista de engines para tentar
            engines = ['xlrd', 'openpyxl', None]
            
            for engine in engines:
                try:
                    import pandas as pd
                    logger.info(f"Tentando engine: {engine}")
                    
                    if engine == 'openpyxl':
                        # Força como se fosse xlsx
                        df = pd.read_excel(arquivo_excel, engine='openpyxl', header=None)
                    else:
                        df = pd.read_excel(arquivo_excel, engine=engine, header=None)
                    
                    rows_data = [tuple(row) for row in df.values]
                    wb = None
                    logger.info(f"✅ Sucesso com engine: {engine}")
                    break
                    
                except Exception as e:
                    logger.info(f"❌ Falhou com engine {engine}: {str(e)}")
                    continue
            else:
                # Se chegou aqui, todos os engines falharam
                return {
                    'success': False,
                    'message': (
                        '❌ **Arquivo .xls corrompido ou incompatível**\n\n'
                        '💡 **Solução simples**:\n'
                        '1. Abra o arquivo no Excel\n'
                        '2. Clique em "Salvar Como"\n'
                        '3. Escolha formato ".xlsx"\n'
                        '4. Tente importar novamente\n\n'
                        '⚠️ O arquivo parece ter corrupção interna que impede a leitura.'
                    ),
                    'detalhes_erro': 'Todos os engines falharam'
                }
        else:
            # Para arquivos .xlsx, usa openpyxl
            wb = openpyxl.load_workbook(arquivo_excel, read_only=True)
            ws = wb.active
            rows_data = list(ws.iter_rows(min_row=1, values_only=True))
        
        # Variáveis de controle
        nf_atual = None
        razao_social_atual = None
        cnpj_atual = None
        itens_nf = []
        total_nfs = 0
        nfs_importadas = 0
        nfs_com_erro = 0
        nfs_processadas = []
        erros = []
        pular_proxima_linha = False  # Flag para pular cabeçalho após NF-e
        
        # Lista para armazenar todos os FaturamentoProduto criados
        todos_faturamento_produtos = []
        
        # Processa linha por linha
        for row in rows_data:
            # Se deve pular esta linha (cabeçalho após NF-e)
            if pular_proxima_linha:
                logger.info(f"Pulando linha de cabeçalho: {row[0] if row and row[0] else 'vazia'}")
                pular_proxima_linha = False
                continue
            
            # Verifica se é uma linha de cabeçalho de NF
            if row[0] and str(row[0]).startswith('NF-e'):
                # Se já tinha uma NF sendo processada, salva ela
                if nf_atual and itens_nf:
                    resultado_nf = criar_registros_faturamento(
                        nf_atual, razao_social_atual, cnpj_atual, itens_nf
                    )
                    if resultado_nf['success']:
                        nfs_importadas += 1
                        nfs_processadas.append(nf_atual)
                        todos_faturamento_produtos.extend(resultado_nf['faturamento_produtos'])
                    else:
                        nfs_com_erro += 1
                        erros.append(resultado_nf['erro'])
                
                # Extrai informações da NF
                linha_nf = str(row[0])
                nf_atual = linha_nf[7:11].strip()
                razao_social_atual = linha_nf[14:].strip()
                
                # Busca CNPJ do cliente
                cliente = CadastroCliente.query.filter_by(raz_social=razao_social_atual).first()
                if not cliente:
                    cliente = CadastroCliente.query.filter_by(raz_social_red=razao_social_atual).first()
                
                cnpj_atual = cliente.cnpj_cpf if cliente else None
                
                if not cnpj_atual:
                    erros.append(f"Cliente não encontrado: {razao_social_atual}")
                
                itens_nf = []
                total_nfs += 1
                
                # Marca para pular a próxima linha (cabeçalho das colunas)
                pular_proxima_linha = True
                
            # Verifica se é linha de total (fim dos itens)
            elif row[0] and str(row[0]).startswith('Total'):
                # Processa a NF atual
                if nf_atual and itens_nf:
                    resultado_nf = criar_registros_faturamento(
                        nf_atual, razao_social_atual, cnpj_atual, itens_nf
                    )
                    if resultado_nf['success']:
                        nfs_importadas += 1
                        nfs_processadas.append(nf_atual)
                        todos_faturamento_produtos.extend(resultado_nf['faturamento_produtos'])
                    else:
                        nfs_com_erro += 1
                        erros.append(resultado_nf['erro'])
                
                # Reseta variáveis
                nf_atual = None
                razao_social_atual = None
                cnpj_atual = None
                itens_nf = []
                
            # Se estamos dentro de uma NF, é uma linha de item
            elif nf_atual and row[0]:
                try:
                    # Log para debug dos dados (baseado na estrutura real)
                    logger.info(f"Processando item: cod={row[0]}, desc={row[1] if len(row) > 1 else ''}, data={row[3] if len(row) > 3 else ''}, qtd={row[4] if len(row) > 4 else ''}, valor={row[5] if len(row) > 5 else ''}")
                    
                    # Estrutura baseada no exemplo fornecido:
                    # [0] = Código Interno, [1] = Descrição, [2] = Categoria, [3] = Data de Criação, [4] = Quantidade, [5] = Subtotal
                    item = {
                        'cod_produto': extrair_codigo_produto(row[0]),
                        'data_fatura': converter_data(row[3] if len(row) > 3 else None),
                        'qtd_produto_faturado': converter_quantidade(row[4] if len(row) > 4 else None),
                        'valor_produto_faturado': converter_valor(row[5] if len(row) > 5 else None)
                    }
                    
                    # Busca informações do produto
                    produto = CadastroPalletizacao.query.filter_by(
                        cod_produto=item['cod_produto']
                    ).first()
                    
                    if produto:
                        item['nome_produto'] = produto.nome_produto
                        item['peso_bruto'] = Decimal(str(produto.peso_bruto or 0))
                    else:
                        # Usa a descrição do Excel se produto não encontrado no cadastro
                        item['nome_produto'] = str(row[1]) if len(row) > 1 and row[1] else f"Produto {item['cod_produto']}"
                        item['peso_bruto'] = Decimal('0')
                    
                    # Calcula preço unitário
                    if item['qtd_produto_faturado'] > 0:
                        item['preco_produto_faturado'] = item['valor_produto_faturado'] / item['qtd_produto_faturado']
                    else:
                        item['preco_produto_faturado'] = Decimal('0')
                    
                    itens_nf.append(item)
                    
                except Exception as e:
                    erros.append(f"Erro ao processar item da NF {nf_atual}: {str(e)}")
        
        # Processa última NF se houver
        if nf_atual and itens_nf:
            resultado_nf = criar_registros_faturamento(
                nf_atual, razao_social_atual, cnpj_atual, itens_nf
            )
            if resultado_nf['success']:
                nfs_importadas += 1
                nfs_processadas.append(nf_atual)
                todos_faturamento_produtos.extend(resultado_nf['faturamento_produtos'])
            else:
                nfs_com_erro += 1
                erros.append(resultado_nf['erro'])
        
        # Fecha o workbook se foi usado (apenas para .xlsx)
        if wb:
            wb.close()
        
        # Se processar_completo, usa o ProcessadorFaturamentoTagPlus
        if processar_completo and todos_faturamento_produtos:
            try:
                processador = ProcessadorFaturamentoTagPlus()
                resultado_processamento = processador.processar_lote_completo(todos_faturamento_produtos)
                
                return {
                    'success': True,
                    'message': f'Importação concluída! {nfs_importadas} NFs importadas com processamento completo.',
                    'total_nfs': total_nfs,
                    'nfs_importadas': nfs_importadas,
                    'nfs_com_erro': nfs_com_erro,
                    'nfs_processadas': nfs_processadas,
                    'erros': erros,
                    'processamento_completo': True,
                    'detalhes_processamento': resultado_processamento
                }
            except Exception as e:
                return {
                    'success': True,
                    'message': f'Importação concluída! {nfs_importadas} NFs importadas (processamento completo falhou).',
                    'total_nfs': total_nfs,
                    'nfs_importadas': nfs_importadas,
                    'nfs_com_erro': nfs_com_erro,
                    'nfs_processadas': nfs_processadas,
                    'erros': erros + [f'Erro no processamento completo: {str(e)}'],
                    'processamento_completo': False
                }
        
        return {
            'success': True,
            'message': f'Importação concluída! {nfs_importadas} NFs importadas.',
            'total_nfs': total_nfs,
            'nfs_importadas': nfs_importadas,
            'nfs_com_erro': nfs_com_erro,
            'nfs_processadas': nfs_processadas,
            'erros': erros,
            'processamento_completo': False
        }
        
    except Exception as e:
        import traceback
        return {
            'success': False,
            'message': f'Erro ao processar arquivo: {str(e)}',
            'detalhes_erro': traceback.format_exc()
        }

def criar_registros_faturamento(numero_nf, razao_social, cnpj, itens):
    """
    Cria registros de FaturamentoProduto para uma NF
    
    Args:
        numero_nf: Número da nota fiscal
        razao_social: Razão social do cliente
        cnpj: CNPJ do cliente
        itens: Lista de itens da NF
        
    Returns:
        dict: Resultado da criação dos registros
    """
    try:
        # Se não tem CNPJ, não pode processar
        if not cnpj:
            return {
                'success': False,
                'erro': f'NF {numero_nf} sem CNPJ do cliente'
            }
        
        # Busca dados completos do cliente
        cliente = CadastroCliente.query.filter_by(cnpj_cpf=cnpj).first()
        
        # Cria ou atualiza registros em FaturamentoProduto
        faturamento_produtos = []
        for item in itens:
            # Verifica se já existe o item
            faturamento_existente = FaturamentoProduto.query.filter_by(
                numero_nf=numero_nf,
                cod_produto=item['cod_produto']
            ).first()
            
            if faturamento_existente:
                # Atualiza registro existente
                faturamento_existente.data_fatura = item['data_fatura']
                faturamento_existente.qtd_produto_faturado = item['qtd_produto_faturado']
                faturamento_existente.preco_produto_faturado = item['preco_produto_faturado']
                faturamento_existente.valor_produto_faturado = item['valor_produto_faturado']
                faturamento_existente.peso_unitario_produto = item['peso_bruto']
                faturamento_existente.peso_total = item['qtd_produto_faturado'] * item['peso_bruto']
                # Mantém origem se já existir
                faturamento = faturamento_existente
            else:
                # Cria novo registro
                faturamento = FaturamentoProduto(
                    numero_nf=numero_nf,
                    data_fatura=item['data_fatura'],
                    cnpj_cliente=cnpj,
                    nome_cliente=razao_social,
                    municipio=cliente.municipio if cliente else None,
                    estado=cliente.estado if cliente else None,
                    vendedor=cliente.vendedor if cliente else None,
                    equipe_vendas=cliente.equipe_vendas if cliente else None,
                    cod_produto=item['cod_produto'],
                    nome_produto=item['nome_produto'],
                    qtd_produto_faturado=item['qtd_produto_faturado'],
                    preco_produto_faturado=item['preco_produto_faturado'],
                    valor_produto_faturado=item['valor_produto_faturado'],
                    peso_unitario_produto=item['peso_bruto'],
                    peso_total=item['qtd_produto_faturado'] * item['peso_bruto'],
                    origem=None,
                    status_nf='Lançado',
                    created_by='ImportTagPlus'
                )
                db.session.add(faturamento)
            
            faturamento_produtos.append(faturamento)
        
        # Commit para criar os registros
        db.session.commit()
        
        return {
            'success': True,
            'faturamento_produtos': faturamento_produtos
        }
        
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'erro': f'Erro ao processar NF {numero_nf}: {str(e)}'
        }