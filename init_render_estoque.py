#!/usr/bin/env python3
"""
Script de Inicialização do Sistema de Estoque em Tempo Real para o Render
Cria tabelas e popula dados iniciais de forma segura e idempotente
"""

import os
import sys
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def criar_tabelas_estoque():
    """Cria as tabelas de estoque tempo real usando SQL direto"""
    from app import create_app, db
    from sqlalchemy import text, inspect
    
    app = create_app()
    
    with app.app_context():
        logger.info("🔍 Verificando e criando tabelas de estoque tempo real...")
        
        inspector = inspect(db.engine)
        tabelas_criadas = []
        
        try:
            # SQL para criar tabela estoque_tempo_real
            if not inspector.has_table('estoque_tempo_real'):
                logger.info("📦 Criando tabela estoque_tempo_real...")
                sql_estoque = text("""
                    CREATE TABLE IF NOT EXISTS estoque_tempo_real (
                        cod_produto VARCHAR(50) PRIMARY KEY,
                        nome_produto VARCHAR(200) NOT NULL,
                        saldo_atual NUMERIC(15,3) NOT NULL DEFAULT 0,
                        atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        menor_estoque_d7 NUMERIC(15,3),
                        dia_ruptura DATE
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_estoque_tempo_real_atualizado 
                    ON estoque_tempo_real(atualizado_em);
                """)
                db.session.execute(sql_estoque)
                db.session.commit()
                tabelas_criadas.append('estoque_tempo_real')
                logger.info("✅ Tabela estoque_tempo_real criada")
            else:
                logger.info("✅ Tabela estoque_tempo_real já existe")
                tabelas_criadas.append('estoque_tempo_real')
            
            # SQL para criar tabela movimentacao_prevista
            if not inspector.has_table('movimentacao_prevista'):
                logger.info("📅 Criando tabela movimentacao_prevista...")
                sql_mov = text("""
                    CREATE TABLE IF NOT EXISTS movimentacao_prevista (
                        id SERIAL PRIMARY KEY,
                        cod_produto VARCHAR(50) NOT NULL,
                        data_prevista DATE NOT NULL,
                        entrada_prevista NUMERIC(15,3) NOT NULL DEFAULT 0,
                        saida_prevista NUMERIC(15,3) NOT NULL DEFAULT 0,
                        UNIQUE(cod_produto, data_prevista)
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_mov_prevista_produto_data 
                    ON movimentacao_prevista(cod_produto, data_prevista);
                """)
                db.session.execute(sql_mov)
                db.session.commit()
                tabelas_criadas.append('movimentacao_prevista')
                logger.info("✅ Tabela movimentacao_prevista criada")
            else:
                logger.info("✅ Tabela movimentacao_prevista já existe")
                tabelas_criadas.append('movimentacao_prevista')
            
            # SQL para criar tabela programacao_producao se não existir
            if not inspector.has_table('programacao_producao'):
                logger.info("🏭 Criando tabela programacao_producao...")
                sql_prod = text("""
                    CREATE TABLE IF NOT EXISTS programacao_producao (
                        id SERIAL PRIMARY KEY,
                        data_programacao DATE NOT NULL,
                        cod_produto VARCHAR(50) NOT NULL,
                        nome_produto VARCHAR(200) NOT NULL,
                        qtd_programada FLOAT NOT NULL,
                        linha_producao VARCHAR(50),
                        cliente_produto VARCHAR(100),
                        observacao_pcp TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by VARCHAR(100),
                        updated_by VARCHAR(100)
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_programacao_data_linha 
                    ON programacao_producao(data_programacao, linha_producao);
                    
                    CREATE INDEX IF NOT EXISTS idx_programacao_produto_data 
                    ON programacao_producao(cod_produto, data_programacao);
                """)
                db.session.execute(sql_prod)
                db.session.commit()
                tabelas_criadas.append('programacao_producao')
                logger.info("✅ Tabela programacao_producao criada")
            else:
                logger.info("✅ Tabela programacao_producao já existe")
                tabelas_criadas.append('programacao_producao')
            
            return tabelas_criadas
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar tabelas: {e}")
            db.session.rollback()
            raise


def popular_dados_iniciais():
    """Popula dados iniciais do sistema de estoque"""
    from app import create_app, db
    from app.estoque.models import MovimentacaoEstoque, UnificacaoCodigos
    from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
    from app.carteira.models import PreSeparacaoItem
    from app.separacao.models import Separacao
    from sqlalchemy import text
    
    app = create_app()
    
    with app.app_context():
        logger.info("\n🔄 Populando dados iniciais...")
        
        try:
            # Verificar se já tem dados
            count = EstoqueTempoReal.query.count()
            if count > 0:
                logger.info(f"ℹ️  Sistema já tem {count} produtos. Pulando população inicial.")
                return {'status': 'skipped', 'message': f'Já existem {count} produtos'}
            
            # 1. Migrar saldos atuais de MovimentacaoEstoque
            logger.info("📦 Calculando saldos atuais dos produtos...")
            
            # Buscar produtos únicos
            produtos = db.session.query(
                MovimentacaoEstoque.cod_produto,
                MovimentacaoEstoque.nome_produto
            ).filter(
                MovimentacaoEstoque.ativo == True
            ).distinct().all()
            
            logger.info(f"📊 {len(produtos)} produtos encontrados para processar")
            
            produtos_processados = 0
            erros = []
            
            for cod_produto, nome_produto in produtos:
                try:
                    # Calcular saldo atual considerando unificação
                    saldo = Decimal('0')
                    
                    # Obter códigos relacionados
                    codigos_relacionados = [cod_produto]  # Iniciar com o próprio código
                    try:
                        codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)
                    except:
                        pass  # Se não houver unificação, usar só o código principal
                    
                    # Somar movimentações de todos os códigos relacionados
                    for codigo in codigos_relacionados:
                        movs = MovimentacaoEstoque.query.filter_by(
                            cod_produto=codigo,
                            ativo=True
                        ).all()
                        
                        for mov in movs:
                            # qtd_movimentacao já vem com sinal correto
                            saldo += Decimal(str(mov.qtd_movimentacao))
                    
                    # Inserir ou atualizar EstoqueTempoReal
                    estoque_existente = EstoqueTempoReal.query.filter_by(
                        cod_produto=cod_produto
                    ).first()
                    
                    if not estoque_existente:
                        novo_estoque = EstoqueTempoReal(
                            cod_produto=cod_produto,
                            nome_produto=nome_produto or f"Produto {cod_produto}",
                            saldo_atual=saldo
                        )
                        db.session.add(novo_estoque)
                    else:
                        estoque_existente.saldo_atual = saldo
                        estoque_existente.atualizado_em = datetime.utcnow()
                    
                    produtos_processados += 1
                    
                    # Commit parcial a cada 50 produtos
                    if produtos_processados % 50 == 0:
                        db.session.commit()
                        logger.info(f"  ✓ {produtos_processados} produtos processados...")
                        
                except Exception as e:
                    erros.append({'produto': cod_produto, 'erro': str(e)})
                    logger.warning(f"  ⚠️ Erro no produto {cod_produto}: {e}")
            
            # Commit final
            db.session.commit()
            logger.info(f"✅ Saldos migrados: {produtos_processados} produtos")
            
            # 2. Migrar movimentações previstas
            logger.info("\n📅 Migrando movimentações previstas...")
            hoje = date.today()
            movs_previstas = 0
            
            # PreSeparacaoItem
            try:
                preseps = PreSeparacaoItem.query.filter(
                    PreSeparacaoItem.recomposto == False,
                    PreSeparacaoItem.data_expedicao_editada >= hoje
                ).limit(1000).all()  # Limitar para não sobrecarregar
                
                for item in preseps:
                    if item.qtd_selecionada_usuario and item.qtd_selecionada_usuario > 0:
                        # Usar SQL direto para evitar problemas com triggers
                        sql = text("""
                            INSERT INTO movimentacao_prevista 
                            (cod_produto, data_prevista, entrada_prevista, saida_prevista)
                            VALUES (:cod, :data, 0, :qtd)
                            ON CONFLICT (cod_produto, data_prevista) 
                            DO UPDATE SET saida_prevista = movimentacao_prevista.saida_prevista + :qtd
                        """)
                        db.session.execute(sql, {
                            'cod': item.cod_produto,
                            'data': item.data_expedicao_editada,
                            'qtd': float(item.qtd_selecionada_usuario)
                        })
                        movs_previstas += 1
                
                db.session.commit()
                logger.info(f"  ✅ {len(preseps)} pré-separações processadas")
            except Exception as e:
                logger.warning(f"  ⚠️ Erro em pré-separações: {e}")
                db.session.rollback()
            
            # Separacao
            try:
                seps = Separacao.query.filter(
                    Separacao.expedicao >= hoje,
                    Separacao.qtd_saldo > 0
                ).limit(1000).all()
                
                for sep in seps:
                    sql = text("""
                        INSERT INTO movimentacao_prevista 
                        (cod_produto, data_prevista, entrada_prevista, saida_prevista)
                        VALUES (:cod, :data, 0, :qtd)
                        ON CONFLICT (cod_produto, data_prevista) 
                        DO UPDATE SET saida_prevista = movimentacao_prevista.saida_prevista + :qtd
                    """)
                    db.session.execute(sql, {
                        'cod': sep.cod_produto,
                        'data': sep.expedicao,
                        'qtd': float(sep.qtd_saldo)
                    })
                    movs_previstas += 1
                
                db.session.commit()
                logger.info(f"  ✅ {len(seps)} separações processadas")
            except Exception as e:
                logger.warning(f"  ⚠️ Erro em separações: {e}")
                db.session.rollback()
            
            # 3. Calcular rupturas D+7
            logger.info("\n🔮 Calculando projeções de ruptura...")
            produtos_tempo_real = EstoqueTempoReal.query.limit(500).all()  # Processar em lotes
            
            for produto in produtos_tempo_real:
                try:
                    calcular_ruptura_simples(produto.cod_produto)
                except Exception as e:
                    logger.warning(f"  ⚠️ Erro ao calcular ruptura para {produto.cod_produto}: {e}")
            
            db.session.commit()
            
            # Estatísticas finais
            total_produtos = EstoqueTempoReal.query.count()
            total_movs = MovimentacaoPrevista.query.count()
            produtos_negativos = EstoqueTempoReal.query.filter(
                EstoqueTempoReal.saldo_atual < 0
            ).count()
            produtos_ruptura = EstoqueTempoReal.query.filter(
                EstoqueTempoReal.dia_ruptura.isnot(None)
            ).count()
            
            resultado = {
                'status': 'success',
                'produtos_processados': produtos_processados,
                'erros': len(erros),
                'total_produtos': total_produtos,
                'total_movimentacoes': total_movs,
                'produtos_negativos': produtos_negativos,
                'produtos_ruptura': produtos_ruptura
            }
            
            logger.info(f"""
✅ POPULAÇÃO CONCLUÍDA:
─────────────────────────
• Produtos: {total_produtos}
• Movimentações: {total_movs}
• Estoque Negativo: {produtos_negativos}
• Rupturas Previstas: {produtos_ruptura}
• Erros: {len(erros)}
─────────────────────────
            """)
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro geral na população: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            raise


def calcular_ruptura_simples(cod_produto):
    """Calcula ruptura de forma simplificada para evitar dependências circulares"""
    from app import db
    from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
    from datetime import date, timedelta
    from decimal import Decimal
    
    estoque = EstoqueTempoReal.query.filter_by(cod_produto=cod_produto).first()
    if not estoque:
        return
    
    saldo = float(estoque.saldo_atual)
    menor_saldo = saldo
    dia_ruptura = None
    hoje = date.today()
    
    # Buscar movimentações dos próximos 7 dias
    for i in range(8):  # D0 até D7
        data_atual = hoje + timedelta(days=i)
        
        mov = MovimentacaoPrevista.query.filter_by(
            cod_produto=cod_produto,
            data_prevista=data_atual
        ).first()
        
        if mov:
            saldo = saldo + float(mov.entrada_prevista) - float(mov.saida_prevista)
        
        if saldo < menor_saldo:
            menor_saldo = saldo
        
        if saldo < 0 and not dia_ruptura:
            dia_ruptura = data_atual
    
    # Atualizar projeção
    estoque.menor_estoque_d7 = Decimal(str(menor_saldo))
    estoque.dia_ruptura = dia_ruptura
    db.session.add(estoque)


def registrar_triggers_seguros():
    """Registra triggers de forma segura, verificando se existem os modelos"""
    try:
        from app import create_app
        app = create_app()
        
        with app.app_context():
            logger.info("🔧 Registrando triggers do sistema...")
            
            # Tentar importar triggers apenas se os modelos existirem
            try:
                from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
                # Se conseguiu importar, os modelos existem
                
                # Agora tentar registrar triggers
                try:
                    from app.estoque.triggers_tempo_real import registrar_triggers
                    triggers = registrar_triggers()
                    logger.info(f"✅ Triggers registrados: {list(triggers.keys())}")
                except ImportError:
                    logger.warning("⚠️ Módulo de triggers não encontrado, continuando sem triggers")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao registrar triggers: {e}")
                    
            except ImportError:
                logger.warning("⚠️ Modelos de tempo real não encontrados, pulando triggers")
                
    except Exception as e:
        logger.error(f"❌ Erro ao configurar triggers: {e}")


def verificar_integridade():
    """Verifica e corrige problemas de integridade"""
    from app import create_app, db
    from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
    from sqlalchemy import text
    
    app = create_app()
    
    with app.app_context():
        logger.info("\n🔍 Verificando integridade do sistema...")
        
        try:
            # 1. Remover movimentações previstas órfãs (sem produto correspondente)
            sql_orfas = text("""
                DELETE FROM movimentacao_prevista mp
                WHERE NOT EXISTS (
                    SELECT 1 FROM estoque_tempo_real et 
                    WHERE et.cod_produto = mp.cod_produto
                )
            """)
            result = db.session.execute(sql_orfas)
            if result.rowcount > 0:
                logger.info(f"  ✅ {result.rowcount} movimentações órfãs removidas")
            
            # 2. Limpar movimentações zeradas
            sql_zeradas = text("""
                DELETE FROM movimentacao_prevista 
                WHERE entrada_prevista <= 0 AND saida_prevista <= 0
            """)
            result = db.session.execute(sql_zeradas)
            if result.rowcount > 0:
                logger.info(f"  ✅ {result.rowcount} movimentações zeradas removidas")
            
            # 3. Atualizar timestamps
            sql_update = text("""
                UPDATE estoque_tempo_real 
                SET atualizado_em = CURRENT_TIMESTAMP 
                WHERE atualizado_em IS NULL
            """)
            db.session.execute(sql_update)
            
            db.session.commit()
            logger.info("✅ Verificação de integridade concluída")
            
        except Exception as e:
            logger.error(f"❌ Erro na verificação: {e}")
            db.session.rollback()


def main():
    """Função principal de inicialização"""
    logger.info("""
╔══════════════════════════════════════════════════════╗
║   INICIALIZAÇÃO DO SISTEMA DE ESTOQUE - RENDER      ║
╚══════════════════════════════════════════════════════╝
    """)
    
    try:
        # 1. Criar tabelas
        tabelas = criar_tabelas_estoque()
        logger.info(f"✅ {len(tabelas)} tabelas verificadas/criadas")
        
        # 2. Popular dados iniciais
        resultado = popular_dados_iniciais()
        
        # 3. Registrar triggers
        registrar_triggers_seguros()
        
        # 4. Verificar integridade
        verificar_integridade()
        
        logger.info("""
╔══════════════════════════════════════════════════════╗
║         SISTEMA INICIALIZADO COM SUCESSO!           ║
╚══════════════════════════════════════════════════════╝
        """)
        
        return 0
        
    except Exception as e:
        logger.error(f"""
╔══════════════════════════════════════════════════════╗
║              ERRO NA INICIALIZAÇÃO                   ║
╚══════════════════════════════════════════════════════╝
Erro: {e}
        """)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())