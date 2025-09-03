#!/usr/bin/env python3
"""
Script de Migração Direta: PreSeparacaoItem → Separacao
Data: 2025-01-29

Este script ajuda a migrar o código de PreSeparacaoItem para usar 
Separacao com status='PREVISAO' diretamente, sem adapter.
"""

import os
import re
from pathlib import Path

def criar_mapeamento_campos():
    """Mapeamento de campos PreSeparacaoItem → Separacao"""
    return {
        # Campos idênticos
        'separacao_lote_id': 'separacao_lote_id',
        'num_pedido': 'num_pedido', 
        'cod_produto': 'cod_produto',
        'nome_produto': 'nome_produto',
        
        # Campos com nome diferente
        'cnpj_cliente': 'cnpj_cpf',
        'qtd_selecionada_usuario': 'qtd_saldo',
        'valor_original_item': 'valor_saldo',
        'peso_original_item': 'peso',
        'data_expedicao_editada': 'expedicao',
        'data_agendamento_editada': 'agendamento',
        'protocolo_editado': 'protocolo',
        'observacoes_usuario': 'observ_ped_1',
        'data_criacao': 'criado_em',
        
        # Campos que não existem em Separacao (ignorar)
        'qtd_original_carteira': None,
        'qtd_restante_calculada': None,
        'recomposto': None,
        'criado_por': None,
        'hash_item_original': None,
        'data_recomposicao': None,
        'recomposto_por': None,
        'versao_carteira_original': None,
        'versao_carteira_recomposta': None,
    }

def gerar_codigo_migrado(arquivo_path):
    """Gera versão migrada de um arquivo Python"""
    
    with open(arquivo_path, 'r', encoding='utf-8') as f:
        codigo = f.read()
    
    # Substituições básicas
    migracoes = [
        # Import
        (r'from app\.carteira\.models import (.*?)PreSeparacaoItem',
         r'from app.separacao.models import Separacao  # Migrado de PreSeparacaoItem'),
        
        # Queries simples
        (r'PreSeparacaoItem\.query\.filter_by\(',
         r'Separacao.query.filter_by(status="PREVISAO", '),
        
        (r'PreSeparacaoItem\.query\.filter\(',
         r'Separacao.query.filter(Separacao.status == "PREVISAO", '),
         
        # Status in
        (r'PreSeparacaoItem\.status\.in_\(\["CRIADO", "RECOMPOSTO"\]\)',
         r'Separacao.status == "PREVISAO"'),
         
        # Criar novo
        (r'PreSeparacaoItem\(',
         r'Separacao(status="PREVISAO", '),
         
        # Campos
        (r'\.cnpj_cliente',
         r'.cnpj_cpf'),
        (r'\.qtd_selecionada_usuario',
         r'.qtd_saldo'),
        (r'\.valor_original_item',
         r'.valor_saldo'),
        (r'\.data_expedicao_editada',
         r'.expedicao'),
        (r'\.data_agendamento_editada', 
         r'.agendamento'),
        (r'\.protocolo_editado',
         r'.protocolo'),
        (r'\.observacoes_usuario',
         r'.observ_ped_1'),
    ]
    
    codigo_migrado = codigo
    for pattern, replacement in migracoes:
        codigo_migrado = re.sub(pattern, replacement, codigo_migrado)
    
    return codigo_migrado

def migrar_arquivo_critico(arquivo_path):
    """Migra um arquivo crítico específico"""
    print(f"\n🔄 Migrando: {arquivo_path}")
    
    # Backup
    backup_path = f"{arquivo_path}.backup_presep"
    if not os.path.exists(backup_path):
        with open(arquivo_path, 'r', encoding='utf-8') as f:
            conteudo_original = f.read()
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(conteudo_original)
        print(f"  ✅ Backup criado: {backup_path}")
    
    # Gerar código migrado
    codigo_migrado = gerar_codigo_migrado(arquivo_path)
    
    # Salvar versão migrada
    migrado_path = f"{arquivo_path}.migrado"
    with open(migrado_path, 'w', encoding='utf-8') as f:
        f.write(codigo_migrado)
    
    print(f"  ✅ Versão migrada: {migrado_path}")
    print(f"  📝 Revise o arquivo e renomeie quando estiver OK")
    
    return migrado_path

def exemplo_query_migrada():
    """Exemplos de queries migradas"""
    
    print("\n" + "="*60)
    print("EXEMPLOS DE MIGRAÇÃO DE QUERIES")
    print("="*60)
    
    exemplos = [
        ("Buscar pré-separações",
         "# ANTES:\nPreSeparacaoItem.query.filter_by(num_pedido=num_pedido)",
         "# DEPOIS:\nSeparacao.query.filter_by(num_pedido=num_pedido, status='PREVISAO')"),
        
        ("Criar pré-separação",
         "# ANTES:\npre_sep = PreSeparacaoItem(\n    num_pedido=num_pedido,\n    cnpj_cliente=cnpj)",
         "# DEPOIS:\npre_sep = Separacao(\n    num_pedido=num_pedido,\n    cnpj_cpf=cnpj,\n    status='PREVISAO')"),
        
        ("Verificar status",
         "# ANTES:\nif item.status in ['CRIADO', 'RECOMPOSTO']:",
         "# DEPOIS:\nif item.status == 'PREVISAO':"),
        
        ("Transformar em separação",
         "# ANTES:\nitem.status = 'ENVIADO_SEPARACAO'",
         "# DEPOIS:\nitem.status = 'ABERTO'"),
    ]
    
    for titulo, antes, depois in exemplos:
        print(f"\n### {titulo}")
        print(antes)
        print(depois)

def main():
    """Executa migração"""
    
    print("🚀 MIGRAÇÃO DIRETA: PreSeparacaoItem → Separacao")
    print("="*60)
    
    # Arquivos críticos para migrar primeiro
    arquivos_criticos = [
        'app/carteira/routes/pre_separacao_api.py',
        'app/carteira/routes/separacao_api.py',
        'app/carteira/routes/workspace_api.py',
        'app/carteira/services/agrupamento_service.py',
    ]
    
    print("\n📋 Arquivos críticos identificados:")
    for arquivo in arquivos_criticos:
        if os.path.exists(arquivo):
            print(f"  ✅ {arquivo}")
        else:
            print(f"  ❌ {arquivo} (não encontrado)")
    
    # Mostrar exemplos
    exemplo_query_migrada()
    
    print("\n" + "="*60)
    print("PRÓXIMOS PASSOS:")
    print("="*60)
    print("1. Execute este script para criar versões migradas")
    print("2. Revise os arquivos .migrado gerados")
    print("3. Teste as funcionalidades")
    print("4. Substitua os arquivos originais quando OK")
    print("5. Delete os backups após validação completa")
    
    resposta = input("\n🔧 Deseja migrar os arquivos críticos agora? (s/n): ")
    if resposta.lower() == 's':
        for arquivo in arquivos_criticos:
            if os.path.exists(arquivo):
                migrar_arquivo_critico(arquivo)
    
    print("\n✅ Processo de migração concluído!")

if __name__ == "__main__":
    main()