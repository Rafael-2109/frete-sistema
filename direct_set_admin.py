#!/usr/bin/env python
"""
Script direto para definir usuário como admin via SQL
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
            INSERT INTO perfil_usuario (nome, nome_exibicao, descricao, nivel, ativo)
            VALUES ('admin', 'Administrador', 'Acesso total ao sistema', 10, true)
            RETURNING id
        """)
        perfil_id = cur.fetchone()[0]
        print(f"✅ Perfil admin criado com ID: {perfil_id}")
    else:
        perfil_id = result[0]
        print(f"ℹ️ Perfil admin já existe com ID: {perfil_id}")
    
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
        print("\n🎉 Sucesso! Acesse /permissions/admin para gerenciar permissões.")
    else:
        print("❌ Usuário rafael6250@gmail.com não encontrado!")
    
    conn.commit()
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Erro: {e}")