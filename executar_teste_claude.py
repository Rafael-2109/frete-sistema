#!/usr/bin/env python
"""
🧪 Script para Executar Testes do Claude AI
Facilita o envio de perguntas e registro de respostas
"""

import json
import datetime
import os
from typing import List, Dict, Tuple

# Lista de perguntas para teste
PERGUNTAS_TESTE = [
    # Consultas Básicas
    ("1.1", "Qual o status do sistema?"),
    ("1.2", "Quantos clientes existem no sistema?"),
    ("1.3", "Quais são as transportadoras ativas?"),
    
    # Faturamento
    ("2.1", "Quanto faturou hoje?"),
    ("2.2", "Qual o faturamento de ontem?"),
    ("2.3", "Quanto faturou essa semana?"),
    ("2.4", "Qual o faturamento do mês de junho de 2024?"),
    
    # Clientes Específicos
    ("3.1", "Mostre as entregas do Assai"),
    ("3.2", "Qual o faturamento do Atacadão este mês?"),
    ("3.3", "Quantas entregas pendentes tem o Carrefour?"),
    ("3.4", "Mostre os pedidos do Fort Atacadista"),
    
    # Filtros Geográficos
    ("4.1", "Quais entregas estão pendentes em SP?"),
    ("4.2", "Mostre o faturamento do RJ esta semana"),
    ("4.3", "Quantas entregas foram feitas em MG hoje?"),
    
    # Status e Problemas
    ("5.1", "Quais entregas estão atrasadas?"),
    ("5.2", "Mostre os pedidos pendentes de cotação"),
    ("5.3", "Quais embarques estão ativos?"),
    ("5.4", "Tem alguma entrega com problema?"),
    
    # Consultas Complexas
    ("6.1", "Qual o faturamento do Assai em SP nos últimos 30 dias?"),
    ("6.2", "Quantas entregas o Atacadão tem pendentes em São Paulo?"),
    ("6.3", "Mostre os fretes aprovados mas não pagos"),
    ("6.4", "Quais transportadoras são freteiros?"),
    
    # Validação e Erros
    ("7.1", "Mostre dados da Magazine Luiza"),
    ("7.2", "Qual o faturamento de 2030?"),
    ("7.3", "asai"),  # Com erro de digitação
    ("7.4", "Mostre entregas de São Paulo do cliente Renner"),
    
    # Agregações
    ("8.1", "Qual o ticket médio de hoje?"),
    ("8.2", "Quantos pedidos foram criados esta semana?"),
    ("8.3", "Qual transportadora tem mais fretes este mês?"),
    ("8.4", "Qual o prazo médio de entrega?"),
    
    # Operacional
    ("9.1", "Tem algum embarque na portaria?"),
    ("9.2", "Quantos veículos estão no pátio?"),
    ("9.3", "Quais entregas tem agendamento para hoje?"),
    ("9.4", "Mostre as despesas extras pendentes"),
]

# Perguntas de contexto (devem ser feitas em sequência)
PERGUNTAS_CONTEXTO = [
    ("10.1", "Mostre dados do Assai"),
    ("10.2", "E de SP?"),  # Deve entender Assai + SP
    ("10.3", "Qual o faturamento de junho?"),
    ("10.4", "E de julho?"),  # Deve manter contexto
]

def gerar_relatorio_html(resultados: List[Dict]) -> str:
    """Gera relatório HTML dos resultados"""
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Relatório de Teste - Claude AI</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .pergunta {{ background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px; }}
        .resposta {{ background: #e8f4f8; padding: 10px; margin: 5px 0 15px 20px; border-left: 3px solid #2196F3; }}
        .correto {{ border-color: #4CAF50; background: #e8f5e9; }}
        .incorreto {{ border-color: #f44336; background: #ffebee; }}
        .parcial {{ border-color: #ff9800; background: #fff3e0; }}
        .stats {{ background: #333; color: white; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #2196F3; color: white; }}
        .badge {{ padding: 2px 8px; border-radius: 12px; font-size: 12px; }}
        .badge-success {{ background: #4CAF50; color: white; }}
        .badge-error {{ background: #f44336; color: white; }}
        .badge-warning {{ background: #ff9800; color: white; }}
    </style>
</head>
<body>
    <h1>📊 Relatório de Teste - Claude AI Sistema de Fretes</h1>
    <p><strong>Data do Teste:</strong> {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
    
    <div class="stats">
        <h2>📈 Estatísticas Gerais</h2>
        <p>Total de perguntas: {len(resultados)}</p>
        <p>✅ Corretas: <span id="corretas">0</span></p>
        <p>❌ Incorretas: <span id="incorretas">0</span></p>
        <p>⚠️ Parcialmente corretas: <span id="parciais">0</span></p>
    </div>
    
    <h2>🔍 Resultados Detalhados</h2>
"""
    
    for resultado in resultados:
        status_class = ""
        if resultado.get('status') == 'correto':
            status_class = "correto"
        elif resultado.get('status') == 'incorreto':
            status_class = "incorreto"
        elif resultado.get('status') == 'parcial':
            status_class = "parcial"
            
        html += f"""
    <div class="pergunta">
        <strong>{resultado['id']}) {resultado['pergunta']}</strong>
        {' <span class="badge badge-success">✅</span>' if resultado.get('status') == 'correto' else ''}
        {' <span class="badge badge-error">❌</span>' if resultado.get('status') == 'incorreto' else ''}
        {' <span class="badge badge-warning">⚠️</span>' if resultado.get('status') == 'parcial' else ''}
    </div>
    <div class="resposta {status_class}">
        <strong>Resposta:</strong><br>
        {resultado.get('resposta', 'Sem resposta')}
        {f'<br><br><strong>Observações:</strong> {resultado.get("observacao")}' if resultado.get('observacao') else ''}
    </div>
"""
    
    html += """
    <h2>📝 Tabela Resumo</h2>
    <table>
        <tr>
            <th>ID</th>
            <th>Pergunta</th>
            <th>Status</th>
            <th>Observações</th>
        </tr>
"""
    
    for resultado in resultados:
        status_emoji = ""
        if resultado.get('status') == 'correto':
            status_emoji = "✅"
        elif resultado.get('status') == 'incorreto':
            status_emoji = "❌"
        elif resultado.get('status') == 'parcial':
            status_emoji = "⚠️"
        else:
            status_emoji = "❓"
            
        html += f"""
        <tr>
            <td>{resultado['id']}</td>
            <td>{resultado['pergunta']}</td>
            <td style="text-align: center;">{status_emoji}</td>
            <td>{resultado.get('observacao', '')}</td>
        </tr>
"""
    
    html += """
    </table>
    
    <script>
        // Contar estatísticas
        const corretas = document.querySelectorAll('.correto').length;
        const incorretas = document.querySelectorAll('.incorreto').length;
        const parciais = document.querySelectorAll('.parcial').length;
        
        document.getElementById('corretas').textContent = corretas;
        document.getElementById('incorretas').textContent = incorretas;
        document.getElementById('parciais').textContent = parciais;
    </script>
</body>
</html>
"""
    
    return html

def salvar_resultados(resultados: List[Dict]):
    """Salva os resultados em JSON e HTML"""
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Salvar JSON
    json_file = f'teste_claude_{timestamp}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"✅ Resultados salvos em: {json_file}")
    
    # Salvar HTML
    html_file = f'teste_claude_{timestamp}.html'
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(gerar_relatorio_html(resultados))
    print(f"✅ Relatório HTML salvo em: {html_file}")

def main():
    """Função principal para executar os testes"""
    print("🧪 TESTE DO CLAUDE AI - SISTEMA DE FRETES")
    print("=" * 50)
    print("Este script ajuda a organizar o teste do Claude AI")
    print("Para cada pergunta, você deve:")
    print("1. Copiar e enviar a pergunta ao Claude")
    print("2. Colar a resposta quando solicitado")
    print("3. Avaliar se está correta")
    print("=" * 50)
    
    resultados = []
    
    # Testar perguntas normais
    print("\n📋 INICIANDO TESTES PRINCIPAIS...")
    for id_pergunta, pergunta in PERGUNTAS_TESTE:
        print(f"\n{'='*50}")
        print(f"🔍 Pergunta {id_pergunta}: {pergunta}")
        print(f"{'='*50}")
        print("📝 Copie e envie esta pergunta ao Claude AI")
        
        input("\n⏸️  Pressione ENTER quando tiver enviado a pergunta...")
        
        print("\n📥 Cole a resposta do Claude (termine com uma linha vazia):")
        resposta_linhas = []
        while True:
            linha = input()
            if linha == "":
                break
            resposta_linhas.append(linha)
        resposta = "\n".join(resposta_linhas)
        
        print("\n📊 Avalie a resposta:")
        print("1 - ✅ Correto")
        print("2 - ❌ Incorreto")
        print("3 - ⚠️  Parcialmente correto")
        print("4 - ❓ Pular")
        
        avaliacao = input("\nEscolha (1-4): ")
        
        status = ""
        if avaliacao == "1":
            status = "correto"
        elif avaliacao == "2":
            status = "incorreto"
        elif avaliacao == "3":
            status = "parcial"
        else:
            status = "pulado"
        
        observacao = ""
        if status in ["incorreto", "parcial"]:
            observacao = input("💭 Observações (opcional): ")
        
        resultados.append({
            "id": id_pergunta,
            "pergunta": pergunta,
            "resposta": resposta,
            "status": status,
            "observacao": observacao,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        print(f"\n✅ Pergunta {id_pergunta} registrada!")
    
    # Testar contexto
    print("\n\n🧠 TESTE DE CONTEXTO")
    print("=" * 50)
    print("⚠️  IMPORTANTE: As próximas perguntas devem ser feitas em SEQUÊNCIA")
    print("Não limpe o contexto entre elas!")
    input("\nPressione ENTER para continuar...")
    
    for id_pergunta, pergunta in PERGUNTAS_CONTEXTO:
        print(f"\n{'='*50}")
        print(f"🔍 Pergunta {id_pergunta}: {pergunta}")
        if "E de" in pergunta or "E de" in pergunta:
            print("⚠️  Esta pergunta depende do contexto da anterior!")
        print(f"{'='*50}")
        
        input("\n⏸️  Pressione ENTER quando tiver enviado a pergunta...")
        
        print("\n📥 Cole a resposta do Claude:")
        resposta_linhas = []
        while True:
            linha = input()
            if linha == "":
                break
            resposta_linhas.append(linha)
        resposta = "\n".join(resposta_linhas)
        
        print("\n❓ O Claude entendeu o contexto corretamente? (S/N): ")
        contexto_ok = input().upper() == "S"
        
        resultados.append({
            "id": id_pergunta,
            "pergunta": pergunta,
            "resposta": resposta,
            "status": "correto" if contexto_ok else "incorreto",
            "observacao": "Teste de contexto" + (" - OK" if contexto_ok else " - Falhou"),
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    # Salvar resultados
    print("\n\n💾 SALVANDO RESULTADOS...")
    salvar_resultados(resultados)
    
    # Resumo final
    corretas = len([r for r in resultados if r['status'] == 'correto'])
    incorretas = len([r for r in resultados if r['status'] == 'incorreto'])
    parciais = len([r for r in resultados if r['status'] == 'parcial'])
    total = len(resultados)
    
    print("\n\n📊 RESUMO FINAL")
    print("=" * 50)
    print(f"Total de perguntas: {total}")
    print(f"✅ Corretas: {corretas} ({corretas/total*100:.1f}%)")
    print(f"❌ Incorretas: {incorretas} ({incorretas/total*100:.1f}%)")
    print(f"⚠️  Parciais: {parciais} ({parciais/total*100:.1f}%)")
    print("=" * 50)
    
    print("\n✨ Teste concluído! Verifique os arquivos gerados.")

if __name__ == "__main__":
    main() 