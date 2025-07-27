#!/usr/bin/env python
"""
Script simples para corrigir permissões do admin
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print("🔧 Corrigindo permissões do admin...")
    
    # 1. Buscar ID do usuário admin
    cur.execute("SELECT id FROM usuarios WHERE email = 'rafael6250@gmail.com'")
    usuario = cur.fetchone()
    
    if not usuario:
        print("❌ Usuário não encontrado!")
        exit(1)
    
    usuario_id = usuario[0]
    print(f"✅ Usuário encontrado: ID {usuario_id}")
    
    # 2. Verificar se categoria administrador existe
    cur.execute("SELECT id FROM permission_category WHERE nome = 'administrador'")
    categoria = cur.fetchone()
    
    if not categoria:
        # Criar categoria
        cur.execute("""
            INSERT INTO permission_category (nome, nome_exibicao, descricao, icone, ordem)
            VALUES ('administrador', 'Administração', 'Módulos administrativos', 'fas fa-cog', 1)
            RETURNING id
        """)
        categoria_id = cur.fetchone()[0]
        print(f"✅ Categoria administrador criada: ID {categoria_id}")
    else:
        categoria_id = categoria[0]
        print(f"ℹ️ Categoria administrador já existe: ID {categoria_id}")
    
    # 3. Verificar se módulo permissions existe
    cur.execute("SELECT id FROM modulo_sistema WHERE nome = 'permissions'")
    modulo = cur.fetchone()
    
    if not modulo:
        # Criar módulo
        cur.execute("""
            INSERT INTO modulo_sistema (nome, nome_exibicao, descricao, icone, categoria_id, ativo, ordem)
            VALUES ('permissions', 'Gerenciar Permissões', 'Sistema de permissões', 
                    'fas fa-shield-alt', %s, true, 1)
            RETURNING id
        """, (categoria_id,))
        modulo_id = cur.fetchone()[0]
        print(f"✅ Módulo permissions criado: ID {modulo_id}")
    else:
        modulo_id = modulo[0]
        print(f"ℹ️ Módulo permissions já existe: ID {modulo_id}")
    
    # 4. Garantir permissão total no módulo permissions
    cur.execute("""
        SELECT id FROM permissao_usuario 
        WHERE usuario_id = %s AND modulo_id = %s
    """, (usuario_id, modulo_id))
    
    permissao = cur.fetchone()
    
    if not permissao:
        # Criar permissão
        cur.execute("""
            INSERT INTO permissao_usuario 
            (usuario_id, modulo_id, visualizar, criar, editar, deletar, aprovar, exportar)
            VALUES (%s, %s, true, true, true, true, true, true)
        """, (usuario_id, modulo_id))
        print("✅ Permissão criada para módulo permissions")
    else:
        # Atualizar permissão
        cur.execute("""
            UPDATE permissao_usuario 
            SET visualizar = true, criar = true, editar = true, 
                deletar = true, aprovar = true, exportar = true
            WHERE usuario_id = %s AND modulo_id = %s
        """, (usuario_id, modulo_id))
        print("✅ Permissão atualizada para módulo permissions")
    
    # 5. Dar permissão em TODOS os módulos para admin
    cur.execute("""
        INSERT INTO permissao_usuario (usuario_id, modulo_id, visualizar, criar, editar, deletar, aprovar, exportar)
        SELECT %s, id, true, true, true, true, true, true
        FROM modulo_sistema
        WHERE id NOT IN (
            SELECT modulo_id FROM permissao_usuario WHERE usuario_id = %s
        )
    """, (usuario_id, usuario_id))
    
    rows_inserted = cur.rowcount
    if rows_inserted > 0:
        print(f"✅ {rows_inserted} novas permissões criadas")
    
    # 6. Atualizar todas as permissões existentes para garantir acesso total
    cur.execute("""
        UPDATE permissao_usuario 
        SET visualizar = true, criar = true, editar = true, 
            deletar = true, aprovar = true, exportar = true
        WHERE usuario_id = %s
    """, (usuario_id,))
    
    print(f"✅ Todas as permissões atualizadas para acesso total")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("\n🎉 Sucesso! Admin agora tem acesso total!")
    print("   Tente acessar /permissions/hierarchical novamente")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()