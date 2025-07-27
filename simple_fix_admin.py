#!/usr/bin/env python
"""
Script simples para dar permissões ao admin
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print("🔧 Dando permissões totais ao admin...")
    
    # 1. Buscar ID do usuário admin
    cur.execute("SELECT id FROM usuarios WHERE email = 'rafael6250@gmail.com'")
    usuario = cur.fetchone()
    
    if not usuario:
        print("❌ Usuário não encontrado!")
        exit(1)
    
    usuario_id = usuario[0]
    print(f"✅ Usuário encontrado: ID {usuario_id}")
    
    # 2. Criar módulo permissions se não existir
    cur.execute("SELECT id FROM modulo_sistema WHERE nome = 'permissions'")
    modulo = cur.fetchone()
    
    if not modulo:
        cur.execute("""
            INSERT INTO modulo_sistema (nome, nome_exibicao, descricao, icone, ativo, ordem, criado_em)
            VALUES ('permissions', 'Gerenciar Permissões', 'Sistema de permissões', 
                    'fas fa-shield-alt', true, 1, CURRENT_TIMESTAMP)
            RETURNING id
        """)
        modulo_id = cur.fetchone()[0]
        print(f"✅ Módulo permissions criado: ID {modulo_id}")
    else:
        modulo_id = modulo[0]
        print(f"ℹ️ Módulo permissions já existe: ID {modulo_id}")
    
    # 3. Dar permissão total em TODOS os módulos
    cur.execute("SELECT id FROM modulo_sistema")
    todos_modulos = cur.fetchall()
    
    for (mod_id,) in todos_modulos:
        # Verificar se já existe permissão
        cur.execute("""
            SELECT id FROM permissao_usuario 
            WHERE usuario_id = %s AND funcao_id = %s
        """, (usuario_id, mod_id))
        
        if not cur.fetchone():
            # Criar permissão
            cur.execute("""
                INSERT INTO permissao_usuario 
                (usuario_id, funcao_id, pode_visualizar, pode_editar, ativo, concedida_em)
                VALUES (%s, %s, true, true, true, CURRENT_TIMESTAMP)
            """, (usuario_id, mod_id))
        else:
            # Atualizar permissão
            cur.execute("""
                UPDATE permissao_usuario 
                SET pode_visualizar = true, pode_editar = true, ativo = true
                WHERE usuario_id = %s AND funcao_id = %s
            """, (usuario_id, mod_id))
    
    print(f"✅ Permissões configuradas para {len(todos_modulos)} módulos")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("\n🎉 Sucesso! Admin agora tem acesso total!")
    print("   Tente acessar /permissions/hierarchical novamente")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()