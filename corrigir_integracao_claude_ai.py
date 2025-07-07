#!/usr/bin/env python3
"""
🔧 CORRIGIR INTEGRAÇÃO CLAUDE AI
Script para corrigir os problemas de integração identificados no diagnóstico
"""

import os
import shutil
from datetime import datetime

def fazer_backup_arquivo(arquivo):
    """Faz backup de um arquivo antes da modificação"""
    if os.path.exists(arquivo):
        backup = f"{arquivo}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(arquivo, backup)
        print(f"✅ Backup criado: {backup}")
        return backup
    return None

def corrigir_contexto_conversacional():
    """Corrige o uso do contexto conversacional no prompt final"""
    arquivo = "app/claude_ai/claude_real_integration.py"
    
    print("🧠 CORRIGINDO CONTEXTO CONVERSACIONAL...")
    
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não encontrado: {arquivo}")
        return False
    
    # Fazer backup
    fazer_backup_arquivo(arquivo)
    
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # Localizar e corrigir o problema do contexto
        conteudo_original = '''messages = [
                {
                    "role": "user", 
                    "content": consulta
                }
            ]'''
        
        conteudo_corrigido = '''messages = [
                {
                    "role": "user", 
                    "content": consulta_com_contexto  # ✅ CORRIGIDO: Usar contexto conversacional
                }
            ]'''
        
        if conteudo_original in conteudo:
            conteudo = conteudo.replace(conteudo_original, conteudo_corrigido)
            print("✅ Corrigido: Contexto conversacional agora é usado no prompt final")
        else:
            print("⚠️ Padrão não encontrado - pode já estar corrigido")
        
        # Corrigir confiança mínima para lifelong learning
        conteudo_original_confianca = "if conhecimento_previo['confianca_geral'] > 0.7:"
        conteudo_corrigido_confianca = "if conhecimento_previo['confianca_geral'] > 0.4:  # ✅ CORRIGIDO: Confiança mais flexível"
        
        if conteudo_original_confianca in conteudo:
            conteudo = conteudo.replace(conteudo_original_confianca, conteudo_corrigido_confianca)
            print("✅ Corrigido: Confiança mínima reduzida para 0.4 (mais flexível)")
        
        # Salvar arquivo corrigido
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        print("✅ Arquivo corrigido com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao corrigir arquivo: {e}")
        return False

def adicionar_botoes_feedback():
    """Adiciona botões de feedback real nas respostas do Claude"""
    arquivo = "app/templates/claude_ai/claude_real.html"
    
    print("👥 ADICIONANDO BOTÕES DE FEEDBACK REAL...")
    
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não encontrado: {arquivo}")
        return False
    
    # Fazer backup
    fazer_backup_arquivo(arquivo)
    
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # JavaScript para adicionar botões de feedback
        javascript_feedback = '''
// 👥 SISTEMA DE FEEDBACK REAL (CORRIGIDO)
function adicionarBotoesFeedback(messageElement, consulta, resposta) {
    if (messageElement.querySelector('.feedback-buttons')) {
        return; // Já tem botões
    }
    
    const feedbackDiv = document.createElement('div');
    feedbackDiv.className = 'feedback-buttons mt-2';
    feedbackDiv.innerHTML = `
        <div class="feedback-section">
            <small class="text-muted">Esta resposta foi útil?</small><br>
            <button class="btn btn-sm btn-success me-1" onclick="enviarFeedback('positive', this, '${consulta.substring(0, 100)}', '${resposta.substring(0, 200)}')">
                👍 Sim
            </button>
            <button class="btn btn-sm btn-warning me-1" onclick="enviarFeedback('improvement', this, '${consulta.substring(0, 100)}', '${resposta.substring(0, 200)}')">
                📝 Pode melhorar
            </button>
            <button class="btn btn-sm btn-danger me-1" onclick="enviarFeedback('negative', this, '${consulta.substring(0, 100)}', '${resposta.substring(0, 200)}')">
                👎 Não
            </button>
            <div class="feedback-details mt-2" style="display: none;">
                <textarea class="form-control" placeholder="Opcional: Como posso melhorar?" rows="2"></textarea>
                <button class="btn btn-sm btn-primary mt-1" onclick="enviarFeedbackDetalhado(this)">
                    Enviar Feedback
                </button>
            </div>
        </div>
    `;
    
    messageElement.appendChild(feedbackDiv);
}

function enviarFeedback(tipo, botao, consulta, resposta) {
    const feedbackSection = botao.closest('.feedback-section');
    const detailsDiv = feedbackSection.querySelector('.feedback-details');
    
    if (tipo === 'improvement' || tipo === 'negative') {
        detailsDiv.style.display = 'block';
        detailsDiv.dataset.feedbackType = tipo;
    } else {
        // Feedback positivo direto
        enviarFeedbackParaServidor(tipo, '', consulta, resposta);
        feedbackSection.innerHTML = '<small class="text-success">✅ Obrigado pelo feedback!</small>';
    }
}

function enviarFeedbackDetalhado(botao) {
    const detailsDiv = botao.closest('.feedback-details');
    const feedbackSection = botao.closest('.feedback-section');
    const tipo = detailsDiv.dataset.feedbackType;
    const detalhes = detailsDiv.querySelector('textarea').value;
    const consulta = feedbackSection.closest('.message').dataset.consulta || '';
    const resposta = feedbackSection.closest('.message').dataset.resposta || '';
    
    enviarFeedbackParaServidor(tipo, detalhes, consulta, resposta);
    feedbackSection.innerHTML = '<small class="text-success">✅ Obrigado pelo feedback detalhado!</small>';
}

function enviarFeedbackParaServidor(tipo, detalhes, consulta, resposta) {
    fetch('/claude-ai/api/advanced-feedback', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({
            query: consulta,
            response: resposta,
            feedback_text: detalhes || `Feedback ${tipo}`,
            feedback_type: tipo,
            session_id: Date.now().toString()
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('✅ Feedback enviado com sucesso:', data);
        } else {
            console.error('❌ Erro ao enviar feedback:', data);
        }
    })
    .catch(error => {
        console.error('❌ Erro na requisição de feedback:', error);
    });
}'''
        
        # Encontrar onde inserir o JavaScript
        if 'function formatMessage(' in conteudo:
            # Inserir após a função formatMessage
            posicao = conteudo.find('function formatMessage(')
            fim_funcao = conteudo.find('}', conteudo.find('}', posicao) + 1) + 1
            
            # Encontrar local para adicionar chamada dos botões
            if 'messageDiv.innerHTML = formattedMessage;' in conteudo:
                conteudo = conteudo.replace(
                    'messageDiv.innerHTML = formattedMessage;',
                    '''messageDiv.innerHTML = formattedMessage;
                    
                    // 👥 ADICIONAR BOTÕES DE FEEDBACK REAL
                    if (role === 'assistant' && message.length > 10) {
                        messageDiv.dataset.consulta = lastUserMessage || '';
                        messageDiv.dataset.resposta = message;
                        setTimeout(() => adicionarBotoesFeedback(messageDiv, lastUserMessage || '', message), 500);
                    }'''
                )
                print("✅ Botões de feedback adicionados à função formatMessage")
            
            # Inserir JavaScript antes do final do arquivo
            conteudo = conteudo.replace(
                '</script>',
                javascript_feedback + '\n\n// Variável para armazenar última mensagem do usuário\nlet lastUserMessage = "";\n\n</script>'
            )
            
            # Adicionar tracking da mensagem do usuário
            if 'addMessage("user", message);' in conteudo:
                conteudo = conteudo.replace(
                    'addMessage("user", message);',
                    '''lastUserMessage = message;  // Armazenar para feedback
                    addMessage("user", message);'''
                )
                print("✅ Tracking de mensagem do usuário adicionado")
        
        # Salvar arquivo corrigido
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        print("✅ Botões de feedback real adicionados!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao adicionar botões de feedback: {e}")
        return False

def gerar_script_popular_grupos():
    """Gera instruções para popular grupos empresariais"""
    print("🏢 INSTRUÇÕES PARA POPULAR GRUPOS EMPRESARIAIS...")
    
    instrucoes = """
🏢 EXECUTAR NO RENDER - POPULAR GRUPOS EMPRESARIAIS:

1. Acesse o console do Render:
   - Vá para seu projeto no Render
   - Clique em "Shell" ou "Console"

2. Execute os comandos:
   ```bash
   cd /opt/render/project/src
   python popular_grupos_empresariais.py
   ```

3. Verifique se os grupos foram criados:
   ```bash
   python verificar_knowledge_base_render.py
   ```

4. O resultado esperado:
   ✅ ai_grupos_empresariais: 8 registros (ao invés de 0)

Isso ativará o sistema de detecção inteligente de grupos empresariais.
"""
    
    with open("INSTRUCOES_POPULAR_GRUPOS.md", "w", encoding="utf-8") as f:
        f.write(instrucoes)
    
    print("✅ Instruções salvas em INSTRUCOES_POPULAR_GRUPOS.md")

def remover_feedback_automatico():
    """Remove o feedback automático falso e deixa apenas o real"""
    arquivo = "app/claude_ai/claude_real_integration.py"
    
    print("🔄 REMOVENDO FEEDBACK AUTOMÁTICO FALSO...")
    
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # Localizar e comentar o feedback automático
        feedback_falso = '''# 🧑‍🤝‍🧑 HUMAN-IN-THE-LOOP LEARNING (ÓRFÃO INTEGRADO!)
            if self.human_learning:
                try:
                    # Capturar interação automaticamente para análise de padrões
                    feedback_automatic = self.human_learning.capture_feedback(
                        query=consulta,
                        response=resposta_final,
                        user_feedback="Interação processada automaticamente",
                        feedback_type="positive",  # Assumir positivo se não há erro
                        severity="low",
                        context={
                            'user_id': user_context.get('user_id') if user_context else None,
                            'automatic': True,
                            'processing_source': 'claude_real_integration',
                            'interpretation': contexto_analisado,
                            'timestamp': datetime.now().isoformat()
                        }
                    )
                    logger.info(f"🧑‍🤝‍🧑 Interação capturada para Human Learning: {feedback_automatic}")
                except Exception as e:
                    logger.warning(f"⚠️ Human Learning falhou na captura automática: {e}")'''
        
        feedback_real = '''# 🧑‍🤝‍🧑 HUMAN-IN-THE-LOOP LEARNING (AGUARDANDO FEEDBACK REAL)
            # Feedback real será capturado pelos botões na interface
            # Removido feedback automático falso que assumia sempre positivo
            logger.info("🧑‍🤝‍🧑 Aguardando feedback real do usuário via interface")'''
        
        if 'user_feedback="Interação processada automaticamente"' in conteudo:
            conteudo = conteudo.replace(feedback_falso, feedback_real)
            print("✅ Feedback automático falso removido")
        else:
            print("⚠️ Feedback automático não encontrado - pode já estar corrigido")
        
        # Salvar arquivo corrigido
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        print("✅ Sistema de feedback corrigido!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao corrigir feedback: {e}")
        return False

def main():
    """Executa todas as correções"""
    print("🔧 INICIANDO CORREÇÕES DO CLAUDE AI...")
    print("=" * 60)
    
    sucessos = 0
    total = 4
    
    # 1. Corrigir contexto conversacional
    if corrigir_contexto_conversacional():
        sucessos += 1
    
    print("-" * 60)
    
    # 2. Adicionar botões de feedback real
    if adicionar_botoes_feedback():
        sucessos += 1
    
    print("-" * 60)
    
    # 3. Remover feedback automático falso
    if remover_feedback_automatico():
        sucessos += 1
    
    print("-" * 60)
    
    # 4. Gerar instruções para grupos empresariais
    gerar_script_popular_grupos()
    sucessos += 1
    
    print("=" * 60)
    print(f"🎯 RESULTADO: {sucessos}/{total} correções aplicadas")
    
    if sucessos == total:
        print("✅ TODAS AS CORREÇÕES APLICADAS COM SUCESSO!")
        print("\n📋 PRÓXIMOS PASSOS:")
        print("1. Execute no Render: python popular_grupos_empresariais.py")
        print("2. Teste o contexto conversacional fazendo perguntas sequenciais")
        print("3. Teste os botões de feedback nas respostas do Claude")
        print("4. Monitore os logs para verificar o aprendizado funcionando")
        print("\n🚀 Após isso, o Claude AI será verdadeiramente inteligente!")
    else:
        print("⚠️ Algumas correções falharam. Verifique os logs acima.")

if __name__ == "__main__":
    main() 