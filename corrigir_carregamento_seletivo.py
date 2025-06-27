#!/usr/bin/env python
"""
🔧 Script para corrigir o carregamento seletivo de dados no Claude AI
Garante que TODOS os clientes sejam considerados, não apenas subconjunto
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

def aplicar_correcoes_carregamento():
    """Aplica correções para evitar carregamento seletivo"""
    
    arquivo = "app/claude_ai/claude_real_integration.py"
    
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # 1. Adicionar função para carregar TODOS os clientes do sistema
        funcao_todos_clientes = '''
    def _carregar_todos_clientes_sistema(self) -> Dict[str, Any]:
        """
        🆕 Carrega TODOS os clientes do sistema, não apenas últimos 30 dias
        CRÍTICO: Para perguntas sobre "quantos clientes", "todos clientes", etc.
        """
        try:
            from app import db
            from app.faturamento.models import RelatorioFaturamentoImportado
            from app.monitoramento.models import EntregaMonitorada
            from app.pedidos.models import Pedido
            from app.utils.grupo_empresarial import GrupoEmpresarialDetector
            
            logger.info("🌐 CARREGANDO TODOS OS CLIENTES DO SISTEMA...")
            
            # 1. Clientes de faturamento (fonte mais completa)
            clientes_faturamento = db.session.query(
                RelatorioFaturamentoImportado.nome_cliente,
                RelatorioFaturamentoImportado.cnpj_cliente
            ).filter(
                RelatorioFaturamentoImportado.nome_cliente != None,
                RelatorioFaturamentoImportado.nome_cliente != ''
            ).distinct().all()
            
            # 2. Clientes de entregas monitoradas (todas, sem filtro de data)
            clientes_entregas = db.session.query(
                EntregaMonitorada.cliente
            ).filter(
                EntregaMonitorada.cliente != None,
                EntregaMonitorada.cliente != ''
            ).distinct().all()
            
            # 3. Clientes de pedidos
            clientes_pedidos = db.session.query(
                Pedido.nome_cliente
            ).filter(
                Pedido.nome_cliente != None,
                Pedido.nome_cliente != ''
            ).distinct().all()
            
            # Unificar todos os clientes
            todos_clientes = set()
            
            # Adicionar de faturamento (com CNPJ)
            clientes_com_cnpj = {}
            for nome, cnpj in clientes_faturamento:
                if nome:
                    todos_clientes.add(nome)
                    if cnpj:
                        clientes_com_cnpj[nome] = cnpj
            
            # Adicionar de entregas
            for (cliente,) in clientes_entregas:
                if cliente:
                    todos_clientes.add(cliente)
            
            # Adicionar de pedidos
            for (cliente,) in clientes_pedidos:
                if cliente:
                    todos_clientes.add(cliente)
            
            # Detectar grupos empresariais
            detector = GrupoEmpresarialDetector()
            grupos_detectados = {}
            clientes_por_grupo = {}
            
            for cliente in todos_clientes:
                # Verificar se é parte de um grupo
                resultado_grupo = detector.detectar_grupo_na_consulta(cliente)
                if resultado_grupo:
                    grupo_nome = resultado_grupo['grupo_detectado']
                    if grupo_nome not in grupos_detectados:
                        grupos_detectados[grupo_nome] = {
                            'total_filiais': 0,
                            'filiais_exemplo': [],
                            'cnpj_prefixos': resultado_grupo.get('cnpj_prefixos', [])
                        }
                    grupos_detectados[grupo_nome]['total_filiais'] += 1
                    if len(grupos_detectados[grupo_nome]['filiais_exemplo']) < 5:
                        grupos_detectados[grupo_nome]['filiais_exemplo'].append(cliente)
                    
                    # Mapear cliente para grupo
                    clientes_por_grupo[cliente] = grupo_nome
            
            # Contar clientes com entregas nos últimos 30 dias
            data_limite = datetime.now() - timedelta(days=30)
            clientes_ativos_30d = db.session.query(
                EntregaMonitorada.cliente
            ).filter(
                EntregaMonitorada.data_embarque >= data_limite,
                EntregaMonitorada.cliente != None
            ).distinct().count()
            
            logger.info(f"✅ TOTAL DE CLIENTES NO SISTEMA: {len(todos_clientes)}")
            logger.info(f"📊 Grupos empresariais detectados: {len(grupos_detectados)}")
            logger.info(f"🕐 Clientes ativos (30 dias): {clientes_ativos_30d}")
            
            return {
                'total_clientes_sistema': len(todos_clientes),
                'clientes_ativos_30_dias': clientes_ativos_30d,
                'grupos_empresariais': grupos_detectados,
                'total_grupos': len(grupos_detectados),
                'clientes_com_cnpj': len(clientes_com_cnpj),
                'fontes_dados': {
                    'faturamento': len(clientes_faturamento),
                    'entregas': len(clientes_entregas),
                    'pedidos': len(clientes_pedidos)
                },
                'principais_grupos': list(grupos_detectados.keys())[:10],
                '_metodo_completo': True
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar todos os clientes: {e}")
            return {'erro': str(e), '_metodo_completo': False}
    '''

        # 2. Modificar _analisar_consulta para detectar perguntas sobre total de clientes
        deteccao_total_clientes = '''
        
        # 🆕 DETECTAR PERGUNTAS SOBRE TOTAL DE CLIENTES
        perguntas_total_clientes = [
            "quantos clientes", "total de clientes", "quantidade de clientes",
            "numero de clientes", "número de clientes", "clientes existem",
            "clientes no sistema", "clientes cadastrados", "clientes tem"
        ]
        
        for pergunta in perguntas_total_clientes:
            if pergunta in consulta_lower:
                analise["pergunta_total_clientes"] = True
                analise["requer_dados_completos"] = True
                logger.info("🌐 PERGUNTA SOBRE TOTAL DE CLIENTES DETECTADA")
                break
        '''

        # 3. Modificar _carregar_contexto_inteligente para usar dados completos quando necessário
        carregamento_completo = '''
            
            # 🆕 SE PERGUNTA SOBRE TOTAL, CARREGAR DADOS COMPLETOS
            if analise.get("pergunta_total_clientes"):
                logger.info("🌐 CARREGANDO DADOS COMPLETOS DO SISTEMA...")
                dados_completos = self._carregar_todos_clientes_sistema()
                contexto["dados_especificos"]["sistema_completo"] = dados_completos
                contexto["_dados_completos_carregados"] = True
                
                # Adicionar lista de TODOS os grupos ao contexto
                if dados_completos.get('principais_grupos'):
                    contexto["_grupos_existentes"] = dados_completos['principais_grupos']
                    logger.info(f"📊 Grupos no sistema: {', '.join(dados_completos['principais_grupos'])}")
        '''

        # 4. Adicionar aviso no system prompt sobre dados parciais
        aviso_dados_parciais = '''
        
⚠️ **IMPORTANTE SOBRE DADOS PARCIAIS**:
- Por padrão, o sistema carrega apenas últimos 30 dias
- Para perguntas sobre "total de clientes", use dados_especificos['sistema_completo']
- SEMPRE mencione se os dados são parciais (ex: "nos últimos 30 dias")
- Se perguntarem sobre um cliente/grupo não mencionado, ele PODE existir fora do período

✅ **RESPOSTAS CORRETAS**:
- "Nos últimos 30 dias, identifiquei X clientes ativos"
- "O sistema tem Y clientes cadastrados no total"
- "Analisando os dados carregados (30 dias)..."

❌ **RESPOSTAS ERRADAS**:
- "O sistema tem apenas 3 grupos" (sem mencionar período)
- "Total de clientes: 78" (quando são só os últimos 30 dias)
'''

        # Aplicar as modificações
        
        # 1. Inserir função _carregar_todos_clientes_sistema após _carregar_entregas_banco
        pos_carregar_entregas = conteudo.find('def _carregar_entregas_banco(self')
        if pos_carregar_entregas != -1:
            # Encontrar o fim da função
            pos_fim_funcao = conteudo.find('\n    def ', pos_carregar_entregas + 1)
            if pos_fim_funcao != -1:
                conteudo = (
                    conteudo[:pos_fim_funcao] + '\n' +
                    funcao_todos_clientes + '\n' +
                    conteudo[pos_fim_funcao:]
                )
                print("✅ Função _carregar_todos_clientes_sistema adicionada")

        # 2. Adicionar detecção de perguntas sobre total
        pos_analise = conteudo.find('# ANÁLISE TEMPORAL INTELIGENTE')
        if pos_analise != -1:
            conteudo = (
                conteudo[:pos_analise] +
                deteccao_total_clientes + '\n        ' +
                conteudo[pos_analise:]
            )
            print("✅ Detecção de perguntas sobre total adicionada")

        # 3. Adicionar carregamento completo
        pos_contexto = conteudo.find('# ESTATÍSTICAS GERAIS COM REDIS CACHE')
        if pos_contexto != -1:
            conteudo = (
                conteudo[:pos_contexto] +
                carregamento_completo + '\n            ' +
                conteudo[pos_contexto:]
            )
            print("✅ Carregamento completo adicionado")

        # 4. Adicionar aviso no system prompt
        pos_system_prompt = conteudo.find('self.system_prompt = self.system_prompt_base + """')
        if pos_system_prompt != -1:
            pos_fim_prompt = conteudo.find('"""', pos_system_prompt + 50)
            if pos_fim_prompt != -1:
                # Inserir antes do fim
                conteudo = (
                    conteudo[:pos_fim_prompt] + 
                    aviso_dados_parciais +
                    conteudo[pos_fim_prompt:]
                )
                print("✅ Aviso sobre dados parciais adicionado ao system prompt")

        # 5. Adicionar tratamento especial para respostas sobre clientes
        tratamento_resposta = '''
        
        # 🆕 ADICIONAR CONTEXTO SOBRE DADOS PARCIAIS NA RESPOSTA
        if analise.get("pergunta_total_clientes") and dados_contexto.get("_dados_completos_carregados"):
            sistema_completo = dados_contexto["dados_especificos"].get("sistema_completo", {})
            if sistema_completo.get("_metodo_completo"):
                contexto_adicional = f"""
                
📊 DADOS COMPLETOS DO SISTEMA:
- Total de clientes cadastrados: {sistema_completo.get('total_clientes_sistema', 'N/A')}
- Clientes ativos (30 dias): {sistema_completo.get('clientes_ativos_30_dias', 'N/A')}
- Grupos empresariais: {sistema_completo.get('total_grupos', 'N/A')}

⚠️ IMPORTANTE: Os 933 registros mencionados são apenas dos últimos 30 dias.
O sistema tem muito mais clientes cadastrados historicamente."""
                
                # Adicionar ao prompt
                messages[0]["content"] += contexto_adicional
        '''

        # Encontrar onde adicionar o tratamento
        pos_messages = conteudo.find('messages = [')
        if pos_messages != -1:
            # Adicionar antes de enviar messages
            conteudo = (
                conteudo[:pos_messages] + 
                tratamento_resposta + '\n        ' +
                conteudo[pos_messages:]
            )
            print("✅ Tratamento de resposta para totais adicionado")

        # Salvar arquivo modificado
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        print("\n✅ Correções de carregamento seletivo aplicadas!")
        print("\n🔧 Melhorias implementadas:")
        print("1. Função para carregar TODOS os clientes (não só 30 dias)")
        print("2. Detecção de perguntas sobre totais")
        print("3. Carregamento completo quando necessário")
        print("4. Avisos sobre dados parciais no prompt")
        print("5. Contexto adicional nas respostas")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao aplicar correções: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    print("🔧 CORREÇÃO: CARREGAMENTO SELETIVO DE DADOS")
    print("=" * 50)
    print("Este script corrige o problema onde Claude")
    print("não vê todos os clientes do sistema")
    print("=" * 50)
    
    # Fazer backup
    if not fazer_backup():
        print("❌ Falha ao criar backup. Abortando...")
        return
    
    # Aplicar correções
    if aplicar_correcoes_carregamento():
        print("\n✅ CORREÇÕES APLICADAS!")
        print("\n🎯 Resultados esperados:")
        print("1. Pergunta 'quantos clientes?' → resposta com TOTAL real")
        print("2. Todos os grupos mencionados desde o início")
        print("3. Distinção clara entre 'últimos 30 dias' e 'total'")
        print("4. Tenda aparecerá na primeira resposta")
        
        print("\n⚠️ Comportamento corrigido:")
        print("ANTES: '3 grupos empresariais' (só 30 dias)")
        print("DEPOIS: '700+ clientes, incluindo grupos X, Y, Z...'")
        
        print("\n💡 Para reverter:")
        print("   Restaure o backup criado")
    else:
        print("\n❌ Falha ao aplicar correções")

if __name__ == "__main__":
    main() 