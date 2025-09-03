#!/usr/bin/env python3
"""
Criar VIEW pedidos imediatamente
"""

from app import create_app, db
app = create_app()
from sqlalchemy import text

def criar_view():
    with app.app_context():
        print("=" * 80)
        print("CRIANDO VIEW PEDIDOS COM FILTRO DE STATUS")
        print("=" * 80)
        
        try:
            # 1. Renomear tabela pedidos se existir
            print("\n1. Verificando se pedidos é tabela ou VIEW...")
            
            # Verificar se é tabela
            result = db.session.execute(text("""
                SELECT table_type 
                FROM information_schema.tables 
                WHERE table_name = 'pedidos' 
                AND table_schema = 'public'
            """))
            
            tipo = result.first()
            if tipo and tipo.table_type == 'BASE TABLE':
                print("  pedidos é uma TABELA. Renomeando para pedidos_backup...")
                db.session.execute(text("ALTER TABLE pedidos RENAME TO pedidos_backup_20250903"))
                db.session.commit()
                print("  ✅ Tabela renomeada para pedidos_backup_20250903")
            elif tipo and tipo.table_type == 'VIEW':
                print("  pedidos é uma VIEW. Removendo...")
                db.session.execute(text("DROP VIEW IF EXISTS pedidos CASCADE"))
                db.session.commit()
                print("  ✅ VIEW antiga removida")
            else:
                print("  pedidos não existe. Continuando...")
            
            # 2. Criar nova VIEW com filtro
            print("\n2. Criando nova VIEW com filtro (excluindo PREVISAO)...")
            
            create_view_sql = """
            CREATE VIEW pedidos AS
            SELECT 
                -- ID determinístico baseado em hash do separacao_lote_id
                ABS(('x' || substr(md5(s.separacao_lote_id), 1, 8))::bit(32)::int) as id,
                
                -- Identificador único
                s.separacao_lote_id,
                MIN(s.num_pedido) as num_pedido,
                MIN(s.data_pedido) as data_pedido,
                
                -- Cliente (primeiro registro do grupo)
                MIN(s.cnpj_cpf) as cnpj_cpf,
                MIN(s.raz_social_red) as raz_social_red,
                MIN(s.nome_cidade) as nome_cidade,
                MIN(s.cod_uf) as cod_uf,
                
                -- Campos normalizados
                MIN(s.cidade_normalizada) as cidade_normalizada,
                MIN(s.uf_normalizada) as uf_normalizada,
                MIN(s.codigo_ibge) as codigo_ibge,
                
                -- Agregações de valores (SOMA dos produtos)
                COALESCE(SUM(s.valor_saldo), 0) as valor_saldo_total,
                COALESCE(SUM(s.pallet), 0) as pallet_total,
                COALESCE(SUM(s.peso), 0) as peso_total,
                
                -- Rota e observações
                MIN(s.rota) as rota,
                MIN(s.sub_rota) as sub_rota,
                MIN(s.observ_ped_1) as observ_ped_1,
                MIN(s.roteirizacao) as roteirizacao,
                
                -- Datas importantes
                MIN(s.expedicao) as expedicao,
                MIN(s.agendamento) as agendamento,
                MIN(s.protocolo) as protocolo,
                BOOL_OR(s.agendamento_confirmado) as agendamento_confirmado,
                
                -- Campos de transporte (NULL - virão de JOIN com cotacao quando necessário)
                NULL::varchar(100) as transportadora,
                NULL::float as valor_frete,
                NULL::float as valor_por_kg,
                NULL::varchar(100) as nome_tabela,
                NULL::varchar(50) as modalidade,
                NULL::varchar(100) as melhor_opcao,
                NULL::float as valor_melhor_opcao,
                NULL::integer as lead_time,
                
                -- Status e controles
                MIN(s.data_embarque) as data_embarque,
                MIN(s.numero_nf) as nf,
                MIN(s.status) as status,
                BOOL_OR(s.nf_cd) as nf_cd,
                MIN(s.pedido_cliente) as pedido_cliente,
                
                -- Controle de impressão
                BOOL_OR(s.separacao_impressa) as separacao_impressa,
                MIN(s.separacao_impressa_em) as separacao_impressa_em,
                MIN(s.separacao_impressa_por) as separacao_impressa_por,
                
                -- Relacionamentos
                MIN(s.cotacao_id) as cotacao_id,
                NULL::integer as usuario_id,
                
                -- Timestamps
                MIN(s.criado_em) as criado_em

            FROM separacao s
            WHERE s.separacao_lote_id IS NOT NULL
              AND s.status != 'PREVISAO'  -- EXCLUIR REGISTROS COM STATUS PREVISAO
            GROUP BY s.separacao_lote_id
            """
            
            db.session.execute(text(create_view_sql))
            db.session.commit()
            print("✅ VIEW criada com sucesso!")
            
            # 3. Verificar resultado
            print("\n3. Verificando resultado...")
            
            result = db.session.execute(text("""
                SELECT COUNT(*) as total, 
                       COUNT(DISTINCT status) as status_distintos,
                       STRING_AGG(DISTINCT status, ', ' ORDER BY status) as lista_status
                FROM pedidos
            """))
            
            row = result.first()
            print(f"✅ Total de pedidos na VIEW: {row.total}")
            print(f"✅ Status distintos: {row.status_distintos}")
            print(f"✅ Lista de status: {row.lista_status}")
            
            # 4. Verificar se novos ABERTO aparecem
            print("\n4. Verificando registros ABERTO recentes...")
            
            result = db.session.execute(text("""
                SELECT p.separacao_lote_id, p.num_pedido, p.status, p.criado_em
                FROM pedidos p
                WHERE p.status = 'ABERTO'
                ORDER BY p.criado_em DESC
                LIMIT 5
            """))
            
            count = 0
            for row in result:
                count += 1
                print(f"  - Lote: {row.separacao_lote_id}")
                print(f"    Pedido: {row.num_pedido}")
                print(f"    Status: {row.status}")
                print(f"    Criado: {row.criado_em}")
            
            if count == 0:
                print("  ⚠️ Nenhum registro ABERTO encontrado na VIEW")
            else:
                print(f"  ✅ {count} registros ABERTO encontrados")
                
            # 5. Testar um lote específico que deveria aparecer
            print("\n5. Testando lote específico ABERTO...")
            
            # Buscar um lote ABERTO na tabela separacao
            result = db.session.execute(text("""
                SELECT DISTINCT separacao_lote_id, num_pedido, status
                FROM separacao
                WHERE status = 'ABERTO'
                  AND separacao_lote_id IS NOT NULL
                ORDER BY criado_em DESC
                LIMIT 1
            """))
            
            teste = result.first()
            if teste:
                print(f"Testando lote: {teste.separacao_lote_id}")
                print(f"  Status na separacao: {teste.status}")
                
                # Verificar na VIEW
                result = db.session.execute(text("""
                    SELECT separacao_lote_id, status
                    FROM pedidos
                    WHERE separacao_lote_id = :lote
                """), {"lote": teste.separacao_lote_id})
                
                pedido = result.first()
                if pedido:
                    print(f"  ✅ APARECE na VIEW com status: {pedido.status}")
                else:
                    print(f"  ❌ NÃO APARECE na VIEW!")
                    
        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()

if __name__ == "__main__":
    criar_view()