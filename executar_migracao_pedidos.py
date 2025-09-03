#!/usr/bin/env python3
"""
SCRIPT DE MIGRAÇÃO COMPLETA - PEDIDOS PARA VIEW
Execute no Render para migrar pedidos para VIEW usando separacao_lote_id
"""
from app import create_app, db
from datetime import datetime

app = create_app()

def executar_migracao():
    with app.app_context():
        print("="*70)
        print(f"MIGRAÇÃO PEDIDOS → VIEW - {datetime.now()}")
        print("="*70)
        
        try:
            # PASSO 1: Adicionar coluna separacao_lote_id em cotacao_itens
            print("\n1. Adicionando coluna separacao_lote_id em cotacao_itens...")
            try:
                db.session.execute(db.text(
                    "ALTER TABLE cotacao_itens ADD COLUMN separacao_lote_id VARCHAR(50)"
                ))
                db.session.commit()
                print("   ✓ Coluna adicionada")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("   ! Coluna já existe")
                    db.session.rollback()
                else:
                    raise
            
            # PASSO 2: Migrar dados
            print("\n2. Migrando dados de pedido_id para separacao_lote_id...")
            result = db.session.execute(db.text("""
                UPDATE cotacao_itens ci
                SET separacao_lote_id = p.separacao_lote_id
                FROM pedidos p
                WHERE ci.pedido_id = p.id
                  AND ci.pedido_id IS NOT NULL
                  AND ci.separacao_lote_id IS NULL
            """))
            rows = result.rowcount
            db.session.commit()
            print(f"   ✓ {rows} registros migrados")
            
            # Verificar migração
            count = db.session.execute(db.text(
                "SELECT COUNT(*) FROM cotacao_itens WHERE separacao_lote_id IS NOT NULL"
            )).scalar()
            print(f"   ✓ Total com separacao_lote_id: {count}")
            
            # PASSO 3: Remover FK antiga
            print("\n3. Removendo foreign key antiga...")
            try:
                db.session.execute(db.text(
                    "ALTER TABLE cotacao_itens DROP CONSTRAINT cotacao_itens_pedido_id_fkey"
                ))
                db.session.commit()
                print("   ✓ Foreign key removida")
            except:
                print("   ! FK já não existia")
                db.session.rollback()
            
            # Renomear coluna antiga
            try:
                db.session.execute(db.text(
                    "ALTER TABLE cotacao_itens RENAME COLUMN pedido_id TO pedido_id_old"
                ))
                db.session.commit()
                print("   ✓ Coluna pedido_id renomeada para pedido_id_old")
            except:
                print("   ! Coluna já foi renomeada")
                db.session.rollback()
            
            # PASSO 4: Backup da tabela pedidos
            print("\n4. Fazendo backup da tabela pedidos...")
            backup_name = f"pedidos_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            db.session.execute(db.text(f"ALTER TABLE pedidos RENAME TO {backup_name}"))
            db.session.commit()
            print(f"   ✓ Backup criado: {backup_name}")
            
            # PASSO 5: Criar VIEW pedidos
            print("\n5. Criando VIEW pedidos...")
            sql_view = """
            CREATE VIEW pedidos AS
            SELECT 
                -- ID numérico derivado do separacao_lote_id
                ABS(hashtext(s.separacao_lote_id)) as id,
                
                -- Chave principal
                s.separacao_lote_id,
                
                -- Dados agregados
                MIN(s.num_pedido) as num_pedido,
                MIN(s.data_pedido) as data_pedido,
                MIN(s.cnpj_cpf) as cnpj_cpf,
                MIN(s.raz_social_red) as raz_social_red,
                MIN(s.nome_cidade) as nome_cidade,
                MIN(s.cod_uf) as cod_uf,
                MIN(s.cidade_normalizada) as cidade_normalizada,
                MIN(s.uf_normalizada) as uf_normalizada,
                MIN(s.codigo_ibge) as codigo_ibge,
                COALESCE(SUM(s.valor_saldo), 0) as valor_saldo_total,
                COALESCE(SUM(s.pallet), 0) as pallet_total,
                COALESCE(SUM(s.peso), 0) as peso_total,
                MIN(s.rota) as rota,
                MIN(s.sub_rota) as sub_rota,
                MIN(s.observ_ped_1) as observ_ped_1,
                MIN(s.roteirizacao) as roteirizacao,
                MIN(s.expedicao) as expedicao,
                MIN(s.agendamento) as agendamento,
                MIN(s.protocolo) as protocolo,
                BOOL_OR(s.agendamento_confirmado) as agendamento_confirmado,
                NULL::varchar(100) as transportadora,
                NULL::float as valor_frete,
                NULL::float as valor_por_kg,
                NULL::varchar(100) as nome_tabela,
                NULL::varchar(50) as modalidade,
                NULL::varchar(100) as melhor_opcao,
                NULL::float as valor_melhor_opcao,
                NULL::integer as lead_time,
                MIN(s.data_embarque) as data_embarque,
                MIN(s.numero_nf) as nf,
                MIN(s.status) as status,
                BOOL_OR(s.nf_cd) as nf_cd,
                MIN(s.pedido_cliente) as pedido_cliente,
                BOOL_OR(s.separacao_impressa) as separacao_impressa,
                MIN(s.separacao_impressa_em) as separacao_impressa_em,
                MIN(s.separacao_impressa_por) as separacao_impressa_por,
                MIN(s.cotacao_id) as cotacao_id,
                NULL::integer as usuario_id,
                MIN(s.criado_em) as criado_em
            FROM separacao s
            WHERE s.separacao_lote_id IS NOT NULL
              AND s.status != 'PREVISAO'
            GROUP BY s.separacao_lote_id
            """
            db.session.execute(db.text(sql_view))
            db.session.commit()
            print("   ✓ VIEW pedidos criada")
            
            # PASSO 6: Recriar v_demanda_ativa
            print("\n6. Recriando v_demanda_ativa...")
            db.session.execute(db.text("DROP VIEW IF EXISTS v_demanda_ativa"))
            db.session.execute(db.text("""
                CREATE VIEW v_demanda_ativa AS
                SELECT 
                    s.cod_produto,
                    s.nome_produto,
                    EXTRACT(MONTH FROM s.expedicao) as mes,
                    EXTRACT(YEAR FROM s.expedicao) as ano,
                    SUM(s.qtd_saldo) as qtd_demanda
                FROM separacao s
                WHERE s.status NOT IN ('FATURADO', 'PREVISAO')
                  AND s.separacao_lote_id IS NOT NULL
                GROUP BY s.cod_produto, s.nome_produto, mes, ano
            """))
            db.session.commit()
            print("   ✓ v_demanda_ativa recriada")
            
            # PASSO 7: Criar índice para performance
            print("\n7. Criando índice em cotacao_itens...")
            try:
                db.session.execute(db.text(
                    "CREATE INDEX idx_cotacao_itens_separacao_lote ON cotacao_itens(separacao_lote_id)"
                ))
                db.session.commit()
                print("   ✓ Índice criado")
            except:
                print("   ! Índice já existe")
                db.session.rollback()
            
            # VERIFICAÇÃO FINAL
            print("\n" + "="*70)
            print("VERIFICAÇÃO FINAL:")
            print("="*70)
            
            # Contar registros
            view_count = db.session.execute(
                db.text("SELECT COUNT(*) FROM pedidos")
            ).scalar()
            
            cotacao_count = db.session.execute(
                db.text("SELECT COUNT(*) FROM cotacao_itens WHERE separacao_lote_id IS NOT NULL")
            ).scalar()
            
            # Testar alguns registros
            sample = db.session.execute(db.text("""
                SELECT p.id, p.separacao_lote_id, p.num_pedido
                FROM pedidos p
                LIMIT 3
            """)).fetchall()
            
            print(f"✓ VIEW pedidos: {view_count} registros")
            print(f"✓ cotacao_itens migrados: {cotacao_count} registros")
            print(f"✓ Backup salvo como: {backup_name}")
            print("\nExemplos de IDs na VIEW:")
            for row in sample:
                print(f"  ID: {row[0]}, Lote: {row[1]}, Pedido: {row[2]}")
            
            print("\n" + "="*70)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("="*70)
            print("\nPara reverter se necessário:")
            print(f"  DROP VIEW pedidos CASCADE;")
            print(f"  ALTER TABLE {backup_name} RENAME TO pedidos;")
            print(f"  ALTER TABLE cotacao_itens RENAME COLUMN pedido_id_old TO pedido_id;")
            
        except Exception as e:
            print(f"\n❌ ERRO NA MIGRAÇÃO: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False
        
        return True

if __name__ == "__main__":
    executar_migracao()