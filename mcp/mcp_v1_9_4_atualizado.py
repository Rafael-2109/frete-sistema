#!/usr/bin/env python3
"""
MCP FRETES - VERSÃO 1.9.4 ATUALIZADA
Servidor MCP com API mais recente para melhor compatibilidade
"""

import asyncio
import sys
import os
import sqlite3
from typing import List
from datetime import datetime

# Debug inicial
print("🔍 MCP v1.9.4 INICIANDO...", file=sys.stderr)

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    print("✅ MCP v1.9.4 imports OK", file=sys.stderr)
except ImportError as e:
    print(f"❌ Erro import: {e}", file=sys.stderr)
    sys.exit(1)

# Servidor
server = Server("fretes-v1.9.4")
print("✅ Servidor v1.9.4 criado", file=sys.stderr)

def conectar_db():
    """Conecta ao banco de dados"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'sistema_fretes.db')
        
        if not os.path.exists(db_path):
            return None, f"Banco não encontrado: {db_path}"
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn, None
    except Exception as e:
        return None, str(e)

@server.list_tools()
async def list_tools() -> List[Tool]:
    """Lista ferramentas disponíveis"""
    print("📋 Listando ferramentas v1.9.4...", file=sys.stderr)
    return [
        Tool(
            name="status_sistema",
            description="Verifica status geral do sistema de fretes",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="consultar_fretes",
            description="Lista fretes cadastrados no sistema",
            inputSchema={
                "type": "object",
                "properties": {
                    "cliente": {
                        "type": "string",
                        "description": "Nome do cliente para filtrar (opcional)"
                    }
                }
            }
        ),
        Tool(
            name="consultar_transportadoras",
            description="Lista transportadoras cadastradas",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="consultar_embarques",
            description="Lista embarques ativos",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Executa ferramentas"""
    print(f"🔧 Executando {name} - args: {arguments}", file=sys.stderr)
    
    if name == "status_sistema":
        conn, erro = conectar_db()
        if erro:
            resultado = f"❌ Sistema OFFLINE: {erro}"
        else:
            try:
                cursor = conn.cursor()
                
                # Estatísticas básicas
                cursor.execute("SELECT COUNT(*) FROM fretes")
                total_fretes = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM transportadoras")
                total_transportadoras = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM embarques WHERE status='ativo'")
                embarques_ativos = cursor.fetchone()[0]
                
                resultado = "🟢 SISTEMA DE FRETES ONLINE\n\n"
                resultado += "📊 ESTATÍSTICAS:\n"
                resultado += f"- Fretes: {total_fretes}\n"
                resultado += f"- Transportadoras: {total_transportadoras}\n"
                resultado += f"- Embarques ativos: {embarques_ativos}\n\n"
                resultado += f"⏰ Verificado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                resultado += "🔗 MCP v1.9.4 conectado com sucesso!"
                
                conn.close()
            except Exception as e:
                resultado = f"❌ Erro nas estatísticas: {str(e)}"
        
        return [TextContent(type="text", text=resultado)]
    
    elif name == "consultar_fretes":
        conn, erro = conectar_db()
        if erro:
            return [TextContent(type="text", text=f"❌ Erro conexão: {erro}")]
        
        try:
            cursor = conn.cursor()
            cliente_filtro = arguments.get("cliente")
            
            if cliente_filtro:
                query = """
                    SELECT id, nome_cliente, cidade_destino, uf_destino,
                           valor_cotado, status, numero_cte
                    FROM fretes 
                    WHERE nome_cliente LIKE ?
                    ORDER BY id DESC LIMIT 10
                """
                cursor.execute(query, (f'%{cliente_filtro}%',))
            else:
                query = """
                    SELECT id, nome_cliente, cidade_destino, uf_destino,
                           valor_cotado, status, numero_cte
                    FROM fretes 
                    ORDER BY id DESC LIMIT 10
                """
                cursor.execute(query)
            
            fretes = cursor.fetchall()
            
            if not fretes:
                resultado = "📋 Nenhum frete encontrado"
            else:
                resultado = f"📦 FRETES ENCONTRADOS ({len(fretes)}):\n\n"
                for frete in fretes:
                    resultado += f"🔹 ID: {frete['id']}\n"
                    resultado += f"   Cliente: {frete['nome_cliente']}\n"
                    resultado += f"   Destino: {frete['cidade_destino']}/{frete['uf_destino']}\n"
                    resultado += f"   Valor: R$ {frete['valor_cotado'] or 0:,.2f}\n"
                    resultado += f"   Status: {frete['status'] or 'N/A'}\n"
                    resultado += f"   CTe: {frete['numero_cte'] or 'Não emitido'}\n\n"
            
            conn.close()
            return [TextContent(type="text", text=resultado)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Erro consulta fretes: {str(e)}")]
    
    elif name == "consultar_transportadoras":
        conn, erro = conectar_db()
        if erro:
            return [TextContent(type="text", text=f"❌ Erro conexão: {erro}")]
        
        try:
            cursor = conn.cursor()
            query = """
                SELECT razao_social, cnpj, cidade, uf, freteiro
                FROM transportadoras
                ORDER BY razao_social
            """
            cursor.execute(query)
            transportadoras = cursor.fetchall()
            
            if not transportadoras:
                resultado = "📋 Nenhuma transportadora cadastrada"
            else:
                resultado = f"🚛 TRANSPORTADORAS ({len(transportadoras)}):\n\n"
                for t in transportadoras:
                    resultado += f"🔹 {t['razao_social']}\n"
                    resultado += f"   CNPJ: {t['cnpj'] or 'N/A'}\n"
                    resultado += f"   Local: {t['cidade'] or 'N/A'}/{t['uf'] or 'N/A'}\n"
                    resultado += f"   Freteiro: {'✅ Sim' if t['freteiro'] else '❌ Não'}\n\n"
            
            conn.close()
            return [TextContent(type="text", text=resultado)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Erro consulta transportadoras: {str(e)}")]
    
    elif name == "consultar_embarques":
        conn, erro = conectar_db()
        if erro:
            return [TextContent(type="text", text=f"❌ Erro conexão: {erro}")]
        
        try:
            cursor = conn.cursor()
            query = """
                SELECT e.numero, e.data_embarque, e.status, 
                       e.peso_total, e.valor_total, e.placa_veiculo,
                       t.razao_social as transportadora
                FROM embarques e
                LEFT JOIN transportadoras t ON e.transportadora_id = t.id
                WHERE e.status = 'ativo'
                ORDER BY e.numero DESC
                LIMIT 10
            """
            cursor.execute(query)
            embarques = cursor.fetchall()
            
            if not embarques:
                resultado = "📋 Nenhum embarque ativo"
            else:
                resultado = f"📋 EMBARQUES ATIVOS ({len(embarques)}):\n\n"
                for e in embarques:
                    resultado += f"🔹 Nº {e['numero']}\n"
                    resultado += f"   Transportadora: {e['transportadora'] or 'N/A'}\n"
                    resultado += f"   Placa: {e['placa_veiculo'] or 'N/A'}\n"
                    resultado += f"   Data: {e['data_embarque'] or 'Pendente'}\n"
                    resultado += f"   Peso: {e['peso_total'] or 0:.2f} kg\n"
                    resultado += f"   Valor: R$ {e['valor_total'] or 0:,.2f}\n\n"
            
            conn.close()
            return [TextContent(type="text", text=resultado)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Erro consulta embarques: {str(e)}")]
    
    return [TextContent(type="text", text="❌ Ferramenta não encontrada")]

async def main():
    """Função principal otimizada para v1.9.4"""
    print("🚀 Iniciando servidor MCP v1.9.4...", file=sys.stderr)
    
    try:
        async with stdio_server() as streams:
            print("✅ STDIO server v1.9.4 criado", file=sys.stderr)
            await server.run(
                streams[0], streams[1], 
                server.create_initialization_options()
            )
    except Exception as e:
        print(f"❌ Erro servidor: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise

if __name__ == "__main__":
    try:
        print("🔥 EXECUTANDO MCP v1.9.4...", file=sys.stderr)
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 MCP interrompido", file=sys.stderr)
    except Exception as e:
        print(f"❌ ERRO FATAL: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1) 