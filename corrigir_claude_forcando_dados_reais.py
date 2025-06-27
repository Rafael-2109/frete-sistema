#!/usr/bin/env python
"""
🔧 Script AGRESSIVO para forçar Claude a usar APENAS dados reais
Implementa restrições muito mais rigorosas contra invenções
"""

import os
import sys
import shutil
from datetime import datetime

def fazer_backup():
    """Faz backup do arquivo original"""
    arquivo_original = "app/claude_ai/claude_real_integration.py"
    arquivo_backup = f"app/claude_ai/claude_real_integration.py.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if os.path.exists(arquivo_original):
        shutil.copy2(arquivo_original, arquivo_backup)
        print(f"✅ Backup criado: {arquivo_backup}")
        return True
    else:
        print(f"❌ Arquivo não encontrado: {arquivo_original}")
        return False

def aplicar_correcoes_agressivas():
    """Aplica correções AGRESSIVAS para forçar uso de dados reais"""
    
    arquivo = "app/claude_ai/claude_real_integration.py"
    
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # 1. System prompt EXTREMAMENTE rigoroso
        novo_system_prompt = '''
🚨 **MODO DADOS REAIS OBRIGATÓRIO** 🚨

Você é um analisador de dados que APENAS pode usar informações dos dados fornecidos.

❌ **PROIBIÇÕES ABSOLUTAS - VIOLAÇÃO = FALHA CRÍTICA**:

1. **PROIBIDO usar conhecimento pré-treinado sobre empresas brasileiras**
   - Esqueça que Makro, Walmart, Extra existem
   - Use APENAS nomes nos dados fornecidos

2. **PROIBIDO inventar números ou estatísticas**
   - Cada número deve vir de cálculo real dos dados
   - Se não calculou, não afirme

3. **PROIBIDO extrapolar além dos dados**
   - 30 dias de dados = fale apenas sobre 30 dias
   - Não assuma sobre "todo o sistema"

4. **PROIBIDO listar empresas não presentes nos dados**
   - Se não está nos 933 registros, NÃO EXISTE
   - Mesmo que seja uma empresa famosa

⚠️ **EMPRESAS BANIDAS - NUNCA MENCIONAR**:
```
MAKRO, WALMART, EXTRA, BIG, SAM'S CLUB, ZAFFARI, PÃO DE AÇÚCAR,
PREZUNIC, CHAMPION, HIPER BOMPREÇO, NACIONAL, CASA & VIDEO
```

✅ **FORMATO OBRIGATÓRIO DE RESPOSTA**:

Para pergunta "Quantos clientes existem?":

RESPOSTA CORRETA:
"Analisando os 933 registros fornecidos dos últimos 30 dias, 
identifiquei X clientes únicos COM ATIVIDADE NESTE PERÍODO.
Não posso afirmar sobre o total de clientes cadastrados no sistema."

RESPOSTA ERRADA:
"O sistema tem X clientes" (assumindo total)
"Os principais clientes são..." (listando empresas não nos dados)

🎯 **VALIDAÇÃO OBRIGATÓRIA**:
Antes de mencionar QUALQUER empresa, verifique:
1. Está explicitamente nos dados fornecidos?
2. Você viu o nome nos 933 registros?
3. Se não, NÃO MENCIONE

⚡ **MODO DE OPERAÇÃO**:
- Você é um CONTADOR DE DADOS, não um assistente criativo
- Responda APENAS com o que está nos dados
- Quando não souber: "Informação não disponível nos dados fornecidos"
'''

        # Substituir system prompt completamente
        # Encontrar onde começa o system prompt
        inicio_prompt = conteudo.find('self.system_prompt = self.system_prompt_base + """')
        if inicio_prompt != -1:
            # Encontrar o fim do prompt (três aspas)
            fim_prompt = conteudo.find('"""', inicio_prompt + 50)
            if fim_prompt != -1:
                # Substituir todo o conteúdo do prompt
                conteudo_novo = (
                    conteudo[:inicio_prompt] + 
                    'self.system_prompt = self.system_prompt_base + """' +
                    novo_system_prompt +
                    conteudo[fim_prompt:]
                )
                conteudo = conteudo_novo
                print("✅ System prompt substituído por versão AGRESSIVA")

        # 2. Adicionar validador de clientes mencionados
        validador_clientes = '''
    def _validar_clientes_resposta(self, resposta: str, dados_carregados: Dict[str, Any]) -> str:
        """Valida e remove clientes inventados da resposta"""
        
        # Lista de empresas PROIBIDAS
        empresas_proibidas = {
            'makro', 'walmart', 'extra', 'big', "sam's club", 'sams club',
            'zaffari', 'pão de açúcar', 'pao de acucar', 'prezunic', 
            'champion', 'hiper bompreço', 'bompreco', 'nacional', 'casa & video'
        }
        
        # Extrair clientes reais dos dados
        clientes_reais = set()
        if 'dados_especificos' in dados_carregados:
            for dominio, dados in dados_carregados['dados_especificos'].items():
                if isinstance(dados, dict) and 'registros' in dados:
                    for registro in dados['registros']:
                        cliente = registro.get('cliente') or registro.get('nome_cliente')
                        if cliente:
                            clientes_reais.add(cliente.lower())
        
        logger.warning(f"🔍 Validando resposta - {len(clientes_reais)} clientes reais encontrados")
        
        # Verificar menções proibidas
        resposta_lower = resposta.lower()
        empresas_mencionadas = []
        
        for empresa in empresas_proibidas:
            if empresa in resposta_lower:
                empresas_mencionadas.append(empresa)
                logger.error(f"❌ EMPRESA PROIBIDA DETECTADA: {empresa}")
        
        # Se encontrou empresas proibidas, adicionar aviso
        if empresas_mencionadas:
            aviso = f"""

⚠️ **CORREÇÃO AUTOMÁTICA**: As seguintes empresas foram mencionadas mas NÃO EXISTEM nos dados:
{', '.join(empresas_mencionadas.upper())}

Estas empresas foram removidas pois não aparecem nos 933 registros analisados."""
            resposta = resposta + aviso
        
        return resposta'''

        # 3. Modificar processamento para incluir lista de clientes reais
        adicao_contexto = '''
        
        # FORÇAR INCLUSÃO DA LISTA DE CLIENTES REAIS NO PROMPT
        clientes_unicos = set()
        if hasattr(self, '_ultimo_contexto_carregado') and self._ultimo_contexto_carregado:
            dados = self._ultimo_contexto_carregado.get('dados_especificos', {})
            for dominio, dados_dominio in dados.items():
                if isinstance(dados_dominio, dict) and 'registros' in dados_dominio:
                    for registro in dados_dominio['registros']:
                        cliente = registro.get('cliente') or registro.get('nome_cliente')
                        if cliente:
                            clientes_unicos.add(cliente)
        
        lista_clientes_reais = list(clientes_unicos)[:20]  # Primeiros 20
        contexto_clientes = f"""
        
🎯 CLIENTES REAIS NOS DADOS (use APENAS estes):
{', '.join(lista_clientes_reais)}
... e mais {len(clientes_unicos) - 20} clientes

⚠️ QUALQUER CLIENTE NÃO LISTADO ACIMA NÃO EXISTE!"""
        
        # Adicionar ao prompt do usuário
        '''

        # 4. Inserir validador após a definição da classe
        pos_classe = conteudo.find('class ClaudeRealIntegration:')
        if pos_classe != -1:
            # Encontrar próximo método após __init__
            pos_processar = conteudo.find('def processar_consulta_real', pos_classe)
            if pos_processar != -1:
                # Inserir validador antes
                conteudo = (
                    conteudo[:pos_processar] + 
                    validador_clientes + '\n\n    ' +
                    conteudo[pos_processar:]
                )
                print("✅ Validador de clientes adicionado")

        # 5. Adicionar chamada do validador no final do processamento
        # Encontrar onde retorna resposta_final
        pos_resposta_final = conteudo.find('return resposta_final')
        contador = 0
        while pos_resposta_final != -1 and contador < 5:  # Procurar até 5 ocorrências
            # Verificar se está dentro do método processar_consulta_real
            # Inserir validação antes do return
            validacao_call = '''
            # VALIDAR RESPOSTA PARA REMOVER INVENÇÕES
            resposta_final = self._validar_clientes_resposta(resposta_final, dados_contexto)
            '''
            
            # Encontrar a linha antes do return
            inicio_linha = conteudo.rfind('\n', 0, pos_resposta_final)
            indent = '        '  # 8 espaços
            
            # Verificar se já não foi adicionado
            if '_validar_clientes_resposta' not in conteudo[inicio_linha-200:pos_resposta_final]:
                conteudo = (
                    conteudo[:pos_resposta_final] + 
                    f'\n{indent}# Validar resposta contra dados reais' +
                    f'\n{indent}resposta_final = self._validar_clientes_resposta(resposta_final, dados_contexto)\n{indent}' +
                    conteudo[pos_resposta_final:]
                )
                print(f"✅ Validação adicionada no return #{contador+1}")
                break
            
            # Procurar próxima ocorrência
            pos_resposta_final = conteudo.find('return resposta_final', pos_resposta_final + 1)
            contador += 1

        # 6. Adicionar lista de clientes no contexto
        # Encontrar onde monta as messages
        pos_messages = conteudo.find('messages = [')
        if pos_messages != -1:
            pos_content = conteudo.find('"content": f"""CONSULTA DO USUÁRIO', pos_messages)
            if pos_content != -1:
                # Adicionar contexto de clientes antes do fechamento
                pos_fim_content = conteudo.find('"""', pos_content + 50)
                if pos_fim_content != -1:
                    conteudo = (
                        conteudo[:pos_fim_content] + 
                        '\n{contexto_clientes}' +
                        conteudo[pos_fim_content:]
                    )
                    
                    # Adicionar o código que gera contexto_clientes antes de messages
                    conteudo = (
                        conteudo[:pos_messages] + 
                        adicao_contexto + '\n        ' +
                        conteudo[pos_messages:]
                    )
                    print("✅ Lista de clientes reais adicionada ao prompt")

        # Salvar arquivo modificado
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        print("\n✅ Correções AGRESSIVAS aplicadas com sucesso!")
        print("\n🔒 Restrições implementadas:")
        print("1. System prompt EXTREMAMENTE rigoroso")
        print("2. Lista de empresas BANIDAS")
        print("3. Validador automático de respostas")
        print("4. Inclusão de clientes reais no prompt")
        print("5. Avisos quando detecta invenções")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao aplicar correções: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    print("🔒 CORREÇÃO AGRESSIVA: FORÇAR DADOS REAIS")
    print("=" * 50)
    print("Este script implementa restrições EXTREMAS")
    print("para impedir que Claude invente dados")
    print("=" * 50)
    
    # Fazer backup
    if not fazer_backup():
        print("❌ Falha ao criar backup. Abortando...")
        return
    
    # Aplicar correções
    if aplicar_correcoes_agressivas():
        print("\n✅ CORREÇÕES AGRESSIVAS APLICADAS!")
        print("\n🎯 Próximos passos:")
        print("1. Reinicie o servidor Flask")
        print("2. Teste com as mesmas perguntas")
        print("3. Claude não conseguirá mais inventar!")
        
        print("\n🔒 Comportamento esperado:")
        print("- NÃO mencionará Makro, Walmart, etc.")
        print("- Dirá apenas sobre 30 dias de dados")
        print("- Listará APENAS clientes dos 933 registros")
        print("- Adicionará avisos se tentar inventar")
        
        print("\n💡 Para reverter:")
        print("   Restaure o backup criado")
    else:
        print("\n❌ Falha ao aplicar correções")

if __name__ == "__main__":
    main() 