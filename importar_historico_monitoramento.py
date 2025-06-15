#!/usr/bin/env python3
"""
🎯 IMPORTAÇÃO INTELIGENTE DE HISTÓRICO DE MONITORAMENTO

Este script permite importar dados históricos do monitoramento preservando
informações que podem ter sido atualizadas por outras funcionalidades do sistema.

ESTRATÉGIA:
- Se NF não existe: Cria nova entrada
- Se NF já existe: Atualiza apenas campos seguros, preserva campos críticos

CAMPOS SEGUROS (sempre atualizar):
- numero_nf, cliente, valor_nf, data_faturamento
- cnpj_cliente, municipio, uf, vendedor

CAMPOS CRÍTICOS (preservar se existem):
- transportadora, data_embarque, data_entrega_prevista
- data_agenda, entregue, reagendar, status_finalizacao

⚠️ VALORES CONSIDERADOS VAZIOS:
- None, "", "nan", "NaT", "-"
"""

import pandas as pd
from datetime import datetime, date
import sys
import os

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.monitoramento.models import EntregaMonitorada

def valor_eh_vazio(valor):
    """Verifica se um valor deve ser considerado vazio para fins de importação"""
    if valor is None:
        return True
    if pd.isna(valor):
        return True
    
    valor_str = str(valor).strip().lower()
    valores_vazios = ['', 'nan', 'nat', '-', 'none', 'null']
    
    return valor_str in valores_vazios

def converter_data_segura(data_str):
    """Converte string de data para objeto date de forma segura"""
    if valor_eh_vazio(data_str):
        return None
    
    # Tenta diferentes formatos
    formatos = ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']
    
    for formato in formatos:
        try:
            return datetime.strptime(str(data_str), formato).date()
        except ValueError:
            continue
    
    print(f"⚠️ Data inválida ignorada: {data_str}")
    return None

def converter_valor_seguro(valor_str):
    """Converte string de valor para float de forma segura"""
    if valor_eh_vazio(valor_str):
        return None
    
    try:
        # Remove caracteres não numéricos exceto vírgula e ponto
        valor_limpo = str(valor_str).replace(',', '.').strip()
        return float(valor_limpo)
    except (ValueError, TypeError):
        print(f"⚠️ Valor inválido ignorado: {valor_str}")
        return None

def detectar_colunas_automaticamente(df):
    """Detecta automaticamente as colunas do DataFrame baseado em padrões comuns"""
    
    mapeamento = {}
    colunas_lower = {col.lower().strip(): col for col in df.columns}
    
    # Mapeamento de padrões para campos
    padroes = {
        'numero_nf': ['nf', 'nota', 'numero_nf', 'nota_fiscal', 'nf_numero', 'numero'],
        'cliente': ['cliente', 'razao_social', 'empresa', 'nome_cliente'],
        'cnpj_cliente': ['cnpj', 'cnpj_cliente', 'documento', 'cnpj_cpf'],
        'municipio': ['municipio', 'cidade', 'destino', 'cidade_destino'],
        'uf': ['uf', 'estado', 'uf_destino'],
        'vendedor': ['vendedor', 'representante', 'consultor'],
        'valor_nf': ['valor', 'valor_nf', 'valor_nota', 'valor_total'],
        'data_faturamento': ['data_faturamento', 'data_fatura', 'faturamento', 'emissao'],
        'transportadora': ['transportadora', 'transp', 'transportador'],
        'data_embarque': ['data_embarque', 'embarque', 'data_expedicao', 'expedicao'],
        'data_entrega_prevista': ['data_entrega_prevista', 'previsao', 'entrega_prevista', 'prev_entrega'],
        'data_agenda': ['data_agenda', 'agendamento', 'agenda', 'data_agendamento']
    }
    
    # Busca por padrões
    for campo, palavras_chave in padroes.items():
        for palavra in palavras_chave:
            for col_lower, col_original in colunas_lower.items():
                if palavra in col_lower:
                    mapeamento[campo] = col_original
                    break
            if campo in mapeamento:
                break
    
    return mapeamento

def importar_historico_monitoramento(arquivo_excel, sheet_name='Sheet1', modo='visualizar'):
    """
    Importa histórico de monitoramento de forma inteligente
    
    Args:
        arquivo_excel: Caminho para o arquivo Excel
        sheet_name: Nome da planilha (padrão: 'Sheet1')
        modo: 'visualizar' ou 'executar'
    """
    
    print("🎯 IMPORTAÇÃO INTELIGENTE DE HISTÓRICO")
    print("=" * 50)
    
    # Carrega o arquivo
    try:
        df = pd.read_excel(arquivo_excel, sheet_name=sheet_name)
        print(f"✅ Arquivo carregado: {len(df)} linhas encontradas")
    except Exception as e:
        print(f"❌ Erro ao carregar arquivo: {e}")
        return
    
    # Remove linhas completamente vazias
    df = df.dropna(how='all')
    print(f"📋 Linhas após limpeza: {len(df)}")
    
    # Detecta mapeamento automaticamente
    mapeamento = detectar_colunas_automaticamente(df)
    
    print("\n🔍 MAPEAMENTO DETECTADO:")
    for campo, coluna in mapeamento.items():
        print(f"   {campo:20} → {coluna}")
    
    if 'numero_nf' not in mapeamento:
        print("❌ ERRO: Coluna de número da NF não encontrada!")
        print("Colunas disponíveis:", list(df.columns))
        return
    
    # Estatísticas
    stats = {
        'total_linhas': len(df),
        'nfs_novas': 0,
        'nfs_atualizadas': 0,
        'nfs_preservadas': 0,
        'campos_preservados_total': 0,
        'erros': 0
    }
    
    if modo == 'visualizar':
        print(f"\n📊 MODO VISUALIZAÇÃO - Nenhuma alteração será feita")
        print(f"Total de registros para processar: {len(df)}")
        
        # Amostra das primeiras 5 linhas
        print(f"\n📋 AMOSTRA DOS DADOS:")
        for i, (_, row) in enumerate(df.head(5).iterrows()):
            print(f"Linha {i+1}:")
            for campo, coluna in mapeamento.items():
                valor = row.get(coluna, 'N/A')
                print(f"  {campo:20}: {valor}")
            print()
        
        return
    
    # Modo executar
    app = create_app()
    with app.app_context():
        print(f"\n⚡ MODO EXECUÇÃO - Aplicando alterações...")
        
        for index, row in df.iterrows():
            try:
                numero_nf = str(row[mapeamento['numero_nf']]).strip()
                
                if not numero_nf or numero_nf.lower() in ['nan', '']:
                    stats['erros'] += 1
                    continue
                
                # Verifica se a entrega já existe
                entrega_existente = EntregaMonitorada.query.filter_by(numero_nf=numero_nf).first()
                campos_preservados = []
                
                if entrega_existente:
                    print(f"🔄 Atualizando NF {numero_nf}")
                    
                    # Campos seguros - sempre atualizar
                    if 'cliente' in mapeamento and not valor_eh_vazio(row[mapeamento['cliente']]):
                        entrega_existente.cliente = str(row[mapeamento['cliente']]).strip()
                    
                    if 'cnpj_cliente' in mapeamento and not valor_eh_vazio(row[mapeamento['cnpj_cliente']]):
                        entrega_existente.cnpj_cliente = str(row[mapeamento['cnpj_cliente']]).strip()
                    
                    if 'municipio' in mapeamento and not valor_eh_vazio(row[mapeamento['municipio']]):
                        entrega_existente.municipio = str(row[mapeamento['municipio']]).strip()
                    
                    if 'uf' in mapeamento and not valor_eh_vazio(row[mapeamento['uf']]):
                        entrega_existente.uf = str(row[mapeamento['uf']]).strip()
                    
                    if 'vendedor' in mapeamento and not valor_eh_vazio(row[mapeamento['vendedor']]):
                        entrega_existente.vendedor = str(row[mapeamento['vendedor']]).strip()
                    
                    if 'valor_nf' in mapeamento:
                        valor = converter_valor_seguro(row[mapeamento['valor_nf']])
                        if valor:
                            entrega_existente.valor_nf = valor
                    
                    if 'data_faturamento' in mapeamento:
                        data = converter_data_segura(row[mapeamento['data_faturamento']])
                        if data:
                            entrega_existente.data_faturamento = data
                    
                    # ✅ CAMPOS CRÍTICOS - só atualizar se estiverem vazios (incluindo "-")
                    if valor_eh_vazio(entrega_existente.transportadora) and 'transportadora' in mapeamento:
                        if not valor_eh_vazio(row[mapeamento['transportadora']]):
                            entrega_existente.transportadora = str(row[mapeamento['transportadora']]).strip()
                        else:
                            entrega_existente.transportadora = "-"  # Valor padrão
                    else:
                        campos_preservados.append('transportadora')
                    
                    if not entrega_existente.data_embarque and 'data_embarque' in mapeamento:
                        data = converter_data_segura(row[mapeamento['data_embarque']])
                        if data:
                            entrega_existente.data_embarque = data
                    else:
                        campos_preservados.append('data_embarque')
                    
                    if not entrega_existente.data_entrega_prevista and 'data_entrega_prevista' in mapeamento:
                        data = converter_data_segura(row[mapeamento['data_entrega_prevista']])
                        if data:
                            entrega_existente.data_entrega_prevista = data
                    else:
                        campos_preservados.append('data_entrega_prevista')
                    
                    if not entrega_existente.data_agenda and 'data_agenda' in mapeamento:
                        data = converter_data_segura(row[mapeamento['data_agenda']])
                        if data:
                            entrega_existente.data_agenda = data
                    else:
                        campos_preservados.append('data_agenda')
                    
                    stats['nfs_atualizadas'] += 1
                    stats['campos_preservados_total'] += len(campos_preservados)
                    
                    if campos_preservados:
                        stats['nfs_preservadas'] += 1
                        print(f"   📌 Campos preservados: {', '.join(campos_preservados)}")
                
                else:
                    # Nova entrada
                    print(f"🆕 Criando NF {numero_nf}")
                    
                    nova_entrega = EntregaMonitorada(numero_nf=numero_nf)
                    
                    # Preenche todos os campos disponíveis
                    if 'cliente' in mapeamento and not valor_eh_vazio(row[mapeamento['cliente']]):
                        nova_entrega.cliente = str(row[mapeamento['cliente']]).strip()
                    
                    if 'cnpj_cliente' in mapeamento and not valor_eh_vazio(row[mapeamento['cnpj_cliente']]):
                        nova_entrega.cnpj_cliente = str(row[mapeamento['cnpj_cliente']]).strip()
                    
                    if 'municipio' in mapeamento and not valor_eh_vazio(row[mapeamento['municipio']]):
                        nova_entrega.municipio = str(row[mapeamento['municipio']]).strip()
                    
                    if 'uf' in mapeamento and not valor_eh_vazio(row[mapeamento['uf']]):
                        nova_entrega.uf = str(row[mapeamento['uf']]).strip()
                    
                    if 'vendedor' in mapeamento and not valor_eh_vazio(row[mapeamento['vendedor']]):
                        nova_entrega.vendedor = str(row[mapeamento['vendedor']]).strip()
                    
                    if 'valor_nf' in mapeamento:
                        valor = converter_valor_seguro(row[mapeamento['valor_nf']])
                        if valor:
                            nova_entrega.valor_nf = valor
                    
                    if 'data_faturamento' in mapeamento:
                        data = converter_data_segura(row[mapeamento['data_faturamento']])
                        if data:
                            nova_entrega.data_faturamento = data
                    
                    if 'transportadora' in mapeamento and not valor_eh_vazio(row[mapeamento['transportadora']]):
                        nova_entrega.transportadora = str(row[mapeamento['transportadora']]).strip()
                    else:
                        nova_entrega.transportadora = "-"
                    
                    if 'data_embarque' in mapeamento:
                        data = converter_data_segura(row[mapeamento['data_embarque']])
                        if data:
                            nova_entrega.data_embarque = data
                    
                    if 'data_entrega_prevista' in mapeamento:
                        data = converter_data_segura(row[mapeamento['data_entrega_prevista']])
                        if data:
                            nova_entrega.data_entrega_prevista = data
                    
                    if 'data_agenda' in mapeamento:
                        data = converter_data_segura(row[mapeamento['data_agenda']])
                        if data:
                            nova_entrega.data_agenda = data
                    
                    # Valores padrão
                    nova_entrega.entregue = False
                    nova_entrega.reagendar = False
                    nova_entrega.criado_por = "Importação Histórico"
                    nova_entrega.criado_em = datetime.utcnow()
                    
                    db.session.add(nova_entrega)
                    stats['nfs_novas'] += 1
                
            except Exception as e:
                print(f"❌ Erro na linha {index + 1}: {e}")
                stats['erros'] += 1
        
        # Commit das alterações
        try:
            db.session.commit()
            print(f"\n✅ IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO AO SALVAR: {e}")
            return
    
    # Relatório final
    print(f"\n📊 RELATÓRIO FINAL:")
    print(f"   Total de linhas processadas: {stats['total_linhas']}")
    print(f"   ✅ Novas NFs criadas: {stats['nfs_novas']}")
    print(f"   🔄 NFs atualizadas: {stats['nfs_atualizadas']}")
    print(f"   📌 NFs com campos preservados: {stats['nfs_preservadas']}")
    print(f"   🔒 Total de campos preservados: {stats['campos_preservados_total']}")
    print(f"   ❌ Erros: {stats['erros']}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Importa histórico de monitoramento')
    parser.add_argument('arquivo', help='Caminho para o arquivo Excel')
    parser.add_argument('--planilha', default='Sheet1', help='Nome da planilha')
    parser.add_argument('--executar', action='store_true', help='Executa a importação (padrão: apenas visualiza)')
    
    args = parser.parse_args()
    
    modo = 'executar' if args.executar else 'visualizar'
    importar_historico_monitoramento(args.arquivo, args.planilha, modo) 