#!/usr/bin/env python3
"""
SCRIPT DE LIMPEZA: Remove classes obsoletas do carteira/models.py
Remove 9 classes identificadas como obsoletas de forma segura
"""

import os
import re
from datetime import datetime

def remover_classes_obsoletas():
    """Remove classes obsoletas do arquivo models.py"""
    
    arquivo_models = "app/carteira/models.py"
    
    if not os.path.exists(arquivo_models):
        print(f"Arquivo nao encontrado: {arquivo_models}")
        return False
    
    # Backup do arquivo original
    backup_name = f"app/carteira/models.py.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"Criando backup: {backup_name}")
    with open(arquivo_models, 'r', encoding='utf-8') as f:
        conteudo_original = f.read()
    
    with open(backup_name, 'w', encoding='utf-8') as f:
        f.write(conteudo_original)
    
    # Classes a serem removidas (9 classes obsoletas)
    classes_obsoletas = [
        'HistoricoFaturamento',
        'LogAtualizacaoCarteira',
        'VinculacaoCarteiraSeparacao', 
        'EventoCarteira',
        'AprovacaoMudancaCarteira',
        'ControleAlteracaoCarga',
        'ControleDescasamentoNF',
        'SnapshotCarteira',
        'TipoEnvio'
    ]
    
    conteudo_modificado = conteudo_original
    
    print("Removendo classes obsoletas:")
    
    for classe in classes_obsoletas:
        # Padrão regex para encontrar e remover a classe completa
        # Inclui desde "class NomeClasse" até antes da próxima "class" ou fim do arquivo
        padrao = rf'class {classe}\(db\.Model\):.*?(?=\nclass|\n\n# [A-Z]|$)'
        
        # Buscar a classe no conteúdo
        match = re.search(padrao, conteudo_modificado, re.DOTALL)
        
        if match:
            # Substituir pela mensagem de remoção
            comentario_remocao = f'# {classe} - CLASSE REMOVIDA (obsoleta)\n# Funcionalidade não utilizada no sistema atual\n'
            
            conteudo_modificado = re.sub(
                padrao, 
                comentario_remocao,
                conteudo_modificado,
                flags=re.DOTALL
            )
            
            print(f"  {classe} removida")
        else:
            print(f"  {classe} nao encontrada")
    
    # Limpar linhas duplas e triplas em branco
    conteudo_modificado = re.sub(r'\n\n\n+', '\n\n', conteudo_modificado)
    
    # Escrever arquivo modificado
    with open(arquivo_models, 'w', encoding='utf-8') as f:
        f.write(conteudo_modificado)
    
    # Calcular estatísticas
    linhas_original = len(conteudo_original.split('\n'))
    linhas_modificado = len(conteudo_modificado.split('\n'))
    linhas_removidas = linhas_original - linhas_modificado
    
    print(f"\nESTATISTICAS:")
    print(f"  Linhas originais: {linhas_original}")
    print(f"  Linhas finais: {linhas_modificado}")
    print(f"  Linhas removidas: {linhas_removidas}")
    print(f"  Reducao: {(linhas_removidas/linhas_original)*100:.1f}%")
    
    print(f"\nLIMPEZA CONCLUIDA!")
    print(f"  Backup criado: {backup_name}")
    print(f"  Arquivo limpo: {arquivo_models}")
    
    return True

def verificar_imports_removidos():
    """Verifica se não há imports quebrados após a remoção"""
    
    try:
        # Tentar importar as classes essenciais
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        from app.carteira.models import (
            CarteiraPrincipal, 
            PreSeparacaoItem,
            InconsistenciaFaturamento, 
            FaturamentoParcialJustificativa
        )
        
        print("Imports das classes essenciais funcionando")
        return True
        
    except Exception as e:
        print(f"Erro nos imports: {e}")
        return False

def main():
    """Executa limpeza completa"""
    
    print("LIMPEZA DE CLASSES OBSOLETAS")
    print("=" * 50)
    print("Este script remove 9 classes obsoletas do carteira/models.py")
    print("mantendo apenas as 4 classes essenciais + 5 em avaliação.")
    print()
    
    # Executar automaticamente (usuário já solicitou remoção)
    print("Executando limpeza automaticamente...")
    print("Continuando com a limpeza...")
    
    print("\nIniciando limpeza...")
    
    try:
        # Remover classes obsoletas
        if remover_classes_obsoletas():
            print("\nVerificando imports...")
            
            # Verificar se imports ainda funcionam
            if verificar_imports_removidos():
                print("\nLIMPEZA CONCLUIDA COM SUCESSO!")
                print("\nProximos passos recomendados:")
                print("1. Testar o sistema completamente")
                print("2. Executar migrations se necessario")
                print("3. Remover tabelas vazias do banco de dados")
                print("4. Atualizar documentacao")
                
            else:
                print("\nLimpeza concluida mas ha problemas de import.")
                print("Verifique o arquivo manualmente.")
        else:
            print("\nFalha na limpeza.")
            
    except Exception as e:
        print(f"\nERRO INESPERADO: {e}")
        print("Restaure o backup se necessario.")

if __name__ == "__main__":
    main()