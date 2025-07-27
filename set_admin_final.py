#!/usr/bin/env python
"""
Script final para definir usuário como admin
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Primeiro, verificar se o perfil admin existe
    cur.execute("SELECT id FROM perfil_usuario WHERE nome = 'admin'")
    result = cur.fetchone()
    
    if not result:
        # Criar perfil admin
        cur.execute("""
            INSERT INTO perfil_usuario (nome, descricao, nivel_hierarquico, ativo, criado_em)
            VALUES ('admin', 'Acesso total ao sistema', 10, true, CURRENT_TIMESTAMP)
            RETURNING id
        """)
        perfil_id = cur.fetchone()[0]
        print(f"✅ Perfil admin criado com ID: {perfil_id}")
    else:
        perfil_id = result[0]
        print(f"ℹ️ Perfil admin já existe com ID: {perfil_id}")
    
    # Verificar se a coluna perfil_id existe na tabela usuarios
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'usuarios' AND column_name = 'perfil_id'
        )
    """)
    
    if not cur.fetchone()[0]:
        # Adicionar a coluna se não existir
        print("⚠️ Adicionando coluna perfil_id na tabela usuarios...")
        cur.execute("ALTER TABLE usuarios ADD COLUMN perfil_id INTEGER REFERENCES perfil_usuario(id)")
        cur.execute("ALTER TABLE usuarios ADD COLUMN perfil_nome VARCHAR(50)")
    
    # Atualizar o usuário
    cur.execute("""
        UPDATE usuarios 
        SET perfil_id = %s, perfil_nome = 'admin'
        WHERE email = 'rafael6250@gmail.com'
        RETURNING id, nome
    """, (perfil_id,))
    
    result = cur.fetchone()
    if result:
        user_id, user_name = result
        print(f"✅ Usuário {user_name} (ID: {user_id}) agora é ADMINISTRADOR!")
        print("\n🎉 Sucesso! Você agora pode:")
        print("   - Acessar /permissions/admin para gerenciar permissões")
        print("   - Acessar /permissions/hierarchical para a nova interface")
        print("   - Gerenciar todos os módulos do sistema")
    else:
        print("❌ Usuário rafael6250@gmail.com não encontrado!")
    
    conn.commit()
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()