#!/usr/bin/env python3
"""
SCRIPT PARA CONVERTER PEDIDOS EM VIEW - EXECUTAR NO RENDER
"""
from app import create_app, db

app = create_app()

with app.app_context():
    print("="*60)
    print("INICIANDO CONVERSÃO DE PEDIDOS PARA VIEW")
    print("="*60)
    
    try:
        # 1. Dropar view dependente
        print("1. Removendo v_demanda_ativa...")
        db.session.execute(db.text("DROP VIEW IF EXISTS v_demanda_ativa CASCADE"))
        db.session.commit()
        print("   ✓ v_demanda_ativa removida")
        
        # 2. Remover foreign key
        print("2. Removendo foreign key de cotacao_itens...")
        try:
            db.session.execute(db.text("ALTER TABLE cotacao_itens DROP CONSTRAINT IF EXISTS cotacao_itens_pedido_id_fkey"))
            db.session.commit()
            print("   ✓ Foreign key removida")
        except:
            print("   ! Foreign key já não existia")
            db.session.rollback()
        
        # 3. Fazer backup
        print("3. Fazendo backup da tabela pedidos...")
        db.session.execute(db.text("ALTER TABLE pedidos RENAME TO pedidos_backup_30012025"))
        db.session.commit()
        print("   ✓ Backup criado: pedidos_backup_30012025")
        
        # 4. Criar VIEW
        print("4. Criando VIEW pedidos...")
        sql_view = """
        CREATE VIEW pedidos AS
        SELECT 
            ROW_NUMBER() OVER (ORDER BY s.separacao_lote_id)::integer as id,
            s.separacao_lote_id,
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
        
        # 5. Recriar v_demanda_ativa
        print("5. Recriando v_demanda_ativa...")
        sql_demanda = """
        CREATE OR REPLACE VIEW v_demanda_ativa AS
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
        """
        db.session.execute(db.text(sql_demanda))
        db.session.commit()
        print("   ✓ v_demanda_ativa recriada")
        
        # 6. Verificação
        print("\n" + "="*60)
        print("VERIFICAÇÃO FINAL:")
        print("="*60)
        
        count_view = db.session.execute(db.text("SELECT COUNT(*) FROM pedidos")).fetchone()[0]
        count_backup = db.session.execute(db.text("SELECT COUNT(*) FROM pedidos_backup_30012025")).fetchone()[0]
        
        print(f"✓ VIEW pedidos: {count_view} registros")
        print(f"✓ Backup pedidos_backup_30012025: {count_backup} registros")
        print(f"✓ Diferença: {count_backup - count_view} registros removidos")
        
        print("\n✅ CONVERSÃO CONCLUÍDA COM SUCESSO!")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        print("\nPARA REVERTER, EXECUTE:")
        print("DROP VIEW IF EXISTS pedidos CASCADE;")
        print("ALTER TABLE pedidos_backup_30012025 RENAME TO pedidos;")
        db.session.rollback()