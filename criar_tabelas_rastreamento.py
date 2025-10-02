#!/usr/bin/env python3
"""
🚚 SCRIPT DE CRIAÇÃO DAS TABELAS DE RASTREAMENTO GPS
Para rodar LOCALMENTE no ambiente de desenvolvimento

Uso:
    python criar_tabelas_rastreamento.py

Requisitos:
    - Flask app configurado
    - Conexão com banco de dados ativa
"""

import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text


def criar_tabelas_rastreamento():
    """
    Cria as tabelas de rastreamento GPS no banco de dados local
    IMPORTANTE: Deve ser chamado DENTRO de app.app_context()
    """
    print("=" * 80)
    print("🚚 CRIAÇÃO DAS TABELAS DE RASTREAMENTO GPS")
    print("=" * 80)
    print()

    # Verificar se estamos dentro do contexto Flask
    try:
        print(f"🔗 Conectado ao banco: {db.engine.url}")
        print()

        # Script SQL (mesmo do arquivo manual)
        sql_script = """
        BEGIN;

        -- ================================================================
        -- 1. TABELA: rastreamento_embarques
        -- ================================================================
        CREATE TABLE IF NOT EXISTS rastreamento_embarques (
            id SERIAL PRIMARY KEY,
            embarque_id INTEGER NOT NULL UNIQUE,

            -- Token de acesso
            token_acesso VARCHAR(64) NOT NULL UNIQUE,
            token_expiracao TIMESTAMP,

            -- Status do rastreamento
            status VARCHAR(20) NOT NULL DEFAULT 'AGUARDANDO_ACEITE',

            -- Aceite LGPD
            aceite_lgpd BOOLEAN NOT NULL DEFAULT FALSE,
            aceite_lgpd_em TIMESTAMP,
            aceite_lgpd_ip VARCHAR(45),
            aceite_lgpd_user_agent VARCHAR(500),

            -- Controle de rastreamento
            rastreamento_iniciado_em TIMESTAMP,
            rastreamento_finalizado_em TIMESTAMP,
            ultimo_ping_em TIMESTAMP,

            -- Chegada ao destino
            chegou_destino_em TIMESTAMP,
            distancia_minima_atingida FLOAT,

            -- Comprovante de entrega
            canhoto_arquivo VARCHAR(500),
            canhoto_enviado_em TIMESTAMP,
            canhoto_latitude FLOAT,
            canhoto_longitude FLOAT,

            -- Auditoria e LGPD
            criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            criado_por VARCHAR(100) NOT NULL DEFAULT 'Sistema',
            data_expurgo_lgpd TIMESTAMP NOT NULL,

            -- Foreign key
            CONSTRAINT fk_rastreamento_embarque FOREIGN KEY (embarque_id)
                REFERENCES embarques(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_rastreamento_embarques_embarque_id
            ON rastreamento_embarques(embarque_id);
        CREATE INDEX IF NOT EXISTS idx_rastreamento_embarques_token
            ON rastreamento_embarques(token_acesso);
        CREATE INDEX IF NOT EXISTS idx_rastreamento_embarques_status
            ON rastreamento_embarques(status);
        CREATE INDEX IF NOT EXISTS idx_rastreamento_embarques_data_expurgo
            ON rastreamento_embarques(data_expurgo_lgpd);

        -- ================================================================
        -- 2. TABELA: pings_gps
        -- ================================================================
        CREATE TABLE IF NOT EXISTS pings_gps (
            id SERIAL PRIMARY KEY,
            rastreamento_id INTEGER NOT NULL,

            -- Dados GPS
            latitude FLOAT NOT NULL,
            longitude FLOAT NOT NULL,
            precisao FLOAT,
            altitude FLOAT,
            velocidade FLOAT,
            direcao FLOAT,

            -- Distância calculada
            distancia_destino FLOAT,

            -- Bateria
            bateria_nivel INTEGER,
            bateria_carregando BOOLEAN DEFAULT FALSE,

            -- Timestamps
            criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            timestamp_dispositivo TIMESTAMP,

            -- Foreign key
            CONSTRAINT fk_ping_rastreamento FOREIGN KEY (rastreamento_id)
                REFERENCES rastreamento_embarques(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_pings_gps_rastreamento_id
            ON pings_gps(rastreamento_id);
        CREATE INDEX IF NOT EXISTS idx_pings_gps_criado_em
            ON pings_gps(criado_em DESC);

        -- ================================================================
        -- 3. TABELA: logs_rastreamento
        -- ================================================================
        CREATE TABLE IF NOT EXISTS logs_rastreamento (
            id SERIAL PRIMARY KEY,
            rastreamento_id INTEGER NOT NULL,

            -- Dados do evento
            evento VARCHAR(50) NOT NULL,
            detalhes TEXT,

            -- Timestamp
            criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

            -- Foreign key
            CONSTRAINT fk_log_rastreamento FOREIGN KEY (rastreamento_id)
                REFERENCES rastreamento_embarques(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_logs_rastreamento_rastreamento_id
            ON logs_rastreamento(rastreamento_id);
        CREATE INDEX IF NOT EXISTS idx_logs_rastreamento_criado_em
            ON logs_rastreamento(criado_em DESC);
        CREATE INDEX IF NOT EXISTS idx_logs_rastreamento_evento
            ON logs_rastreamento(evento);

        -- ================================================================
        -- 4. TABELA: configuracao_rastreamento
        -- ================================================================
        CREATE TABLE IF NOT EXISTS configuracao_rastreamento (
            id SERIAL PRIMARY KEY,

            -- Configurações de ping
            intervalo_ping_segundos INTEGER NOT NULL DEFAULT 120,
            intervalo_ping_parado_segundos INTEGER NOT NULL DEFAULT 300,
            velocidade_considerada_parado FLOAT NOT NULL DEFAULT 5.0,

            -- Configurações de proximidade
            distancia_chegada_metros FLOAT NOT NULL DEFAULT 200.0,

            -- Configurações LGPD
            dias_retencao_dados INTEGER NOT NULL DEFAULT 90,
            versao_termo_lgpd VARCHAR(20) NOT NULL DEFAULT '1.0',

            -- Configurações de notificação
            notificar_chegada_destino BOOLEAN NOT NULL DEFAULT TRUE,
            notificar_inatividade_minutos INTEGER,

            -- Controle
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_por VARCHAR(100)
        );

        INSERT INTO configuracao_rastreamento (
            intervalo_ping_segundos,
            intervalo_ping_parado_segundos,
            velocidade_considerada_parado,
            distancia_chegada_metros,
            dias_retencao_dados,
            versao_termo_lgpd,
            notificar_chegada_destino
        ) VALUES (
            120, 300, 5.0, 200.0, 90, '1.0', TRUE
        )
        ON CONFLICT DO NOTHING;

        COMMIT;
        """

        try:
            print("🔨 Executando SQL para criar tabelas...")
            print()

            # Executar script SQL
            with db.engine.connect() as connection:
                # Dividir em statements individuais (sem BEGIN/COMMIT)
                statements = [
                    stmt.strip()
                    for stmt in sql_script.split(';')
                    if stmt.strip() and stmt.strip().upper() not in ['BEGIN', 'COMMIT']
                ]

                for i, statement in enumerate(statements, 1):
                    if statement:
                        try:
                            connection.execute(text(statement))
                            connection.commit()

                            # Identificar tipo de operação
                            if 'CREATE TABLE' in statement.upper():
                                table_name = statement.split('CREATE TABLE')[1].split('(')[0].strip().split()[2]
                                print(f"  ✅ Tabela criada: {table_name}")
                            elif 'CREATE INDEX' in statement.upper():
                                index_name = statement.split('CREATE INDEX')[1].split('ON')[0].strip().split()[2]
                                print(f"  ✅ Índice criado: {index_name}")
                            elif 'INSERT INTO' in statement.upper():
                                print(f"  ✅ Configuração padrão inserida")
                            else:
                                print(f"  ✅ Statement {i} executado")

                        except Exception as e:
                            # Ignora erros de "já existe"
                            if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                                print(f"  ⚠️  Statement {i} já existia (ignorado)")
                            else:
                                print(f"  ❌ Erro no statement {i}: {str(e)}")
                                raise

            print()
            print("=" * 80)
            print("✅ TABELAS CRIADAS COM SUCESSO!")
            print("=" * 80)
            print()

        # Verificar tabelas criadas
        verificar_tabelas()

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ ERRO AO CRIAR TABELAS")
        print("=" * 80)
        print(f"Erro: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)


def verificar_tabelas():
    """
    Verifica se as tabelas foram criadas corretamente
    """
    print("🔍 VERIFICANDO TABELAS CRIADAS:")
    print()

    from sqlalchemy import inspect

    inspector = inspect(db.engine)
    tabelas_esperadas = [
        'rastreamento_embarques',
        'pings_gps',
        'logs_rastreamento',
        'configuracao_rastreamento'
    ]

    tabelas_existentes = inspector.get_table_names()

    for tabela in tabelas_esperadas:
        if tabela in tabelas_existentes:
            # Contar colunas
            colunas = inspector.get_columns(tabela)
            print(f"  ✅ {tabela}: {len(colunas)} colunas")

            # Verificar índices
            indices = inspector.get_indexes(tabela)
            if indices:
                print(f"     └─ {len(indices)} índices criados")
        else:
            print(f"  ❌ {tabela}: NÃO ENCONTRADA")

    print()

    # Contar registros
    print("📊 CONTAGEM DE REGISTROS:")
    print()

    for tabela in tabelas_esperadas:
        if tabela in tabelas_existentes:
            try:
                with db.engine.connect() as connection:
                    result = connection.execute(text(f"SELECT COUNT(*) FROM {tabela}"))
                    count = result.scalar()
                    print(f"  📋 {tabela}: {count} registro(s)")
            except Exception as e:
                print(f"  ❌ Erro ao contar {tabela}: {str(e)}")

    print()

    # Mostrar configuração
    print("⚙️  CONFIGURAÇÃO PADRÃO:")
    print()

    try:
        with db.engine.connect() as connection:
            result = connection.execute(text("SELECT * FROM configuracao_rastreamento LIMIT 1"))
            config = result.fetchone()

            if config:
                print(f"  Intervalo de ping: {config.intervalo_ping_segundos}s (2 minutos)")
                print(f"  Distância de chegada: {config.distancia_chegada_metros}m")
                print(f"  Retenção LGPD: {config.dias_retencao_dados} dias")
                print(f"  Versão termo LGPD: {config.versao_termo_lgpd}")
            else:
                print("  ⚠️  Nenhuma configuração encontrada")
    except Exception as e:
        print(f"  ❌ Erro ao buscar configuração: {str(e)}")

    print()


def testar_criacao_rastreamento(app):
    """
    Teste opcional: cria um rastreamento de teste
    IMPORTANTE: Precisa do contexto Flask ativo
    """
    print("=" * 80)
    print("🧪 TESTE OPCIONAL: Criar rastreamento de teste?")
    print("=" * 80)
    print()

    resposta = input("Digite 'S' para criar um rastreamento de teste: ").strip().upper()

    if resposta == 'S':
        # 🔧 CORREÇÃO: Usar contexto Flask aqui também
        with app.app_context():
            from app.rastreamento.models import RastreamentoEmbarque
            from app.embarques.models import Embarque

            try:
                # Buscar primeiro embarque
                embarque = Embarque.query.first()

                if embarque:
                    # Verificar se já tem rastreamento
                    if hasattr(embarque, 'rastreamento') and embarque.rastreamento:
                        print(f"  ⚠️  Embarque #{embarque.numero} já tem rastreamento")
                        print(f"  Token: {embarque.rastreamento.token_acesso[:20]}...")
                        print(f"  URL: {embarque.rastreamento.url_rastreamento}")
                    else:
                        # Criar rastreamento
                        rastreamento = RastreamentoEmbarque(
                            embarque_id=embarque.id,
                            criado_por='Script Teste'
                        )
                        db.session.add(rastreamento)
                        db.session.commit()

                        print(f"  ✅ Rastreamento criado para embarque #{embarque.numero}")
                        print(f"  Token: {rastreamento.token_acesso[:20]}...")
                        print(f"  URL: {rastreamento.url_rastreamento}")
                        print()
                        print("  🔗 Escaneie o QR Code ao imprimir o embarque!")
                else:
                    print("  ⚠️  Nenhum embarque encontrado no banco")

            except Exception as e:
                print(f"  ❌ Erro ao criar rastreamento de teste: {str(e)}")
                import traceback
                traceback.print_exc()

    print()


if __name__ == '__main__':
    try:
        # Criar app Flask uma vez
        print("📦 Criando contexto Flask...")
        app = create_app()

        # Executar criação de tabelas
        with app.app_context():
            criar_tabelas_rastreamento()

        # Testar criação de rastreamento (passa o app como parâmetro)
        testar_criacao_rastreamento(app)

        print("=" * 80)
        print("🎉 SCRIPT CONCLUÍDO COM SUCESSO!")
        print("=" * 80)
        print()
        print("Próximos passos:")
        print("  1. Reinicie a aplicação: flask run")
        print("  2. Crie um embarque pela interface")
        print("  3. Imprima o embarque e verifique o QR Code")
        print("  4. Escaneie o QR Code com o celular")
        print()

    except KeyboardInterrupt:
        print()
        print("❌ Script cancelado pelo usuário")
        sys.exit(1)
    except Exception as e:
        print()
        print("❌ Erro inesperado:")
        print(str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)
