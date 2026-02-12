"""
Script para atualizar campo crossdocking nos clientes
Data: 14/10/2025

REGRA DE NEGÓCIO:
Marcar crossdocking=True para clientes que atendam TODAS as condições abaixo:
1. NÃO seja do vendedor "DANI" (case insensitive)
2. NÃO seja do estado de São Paulo (estado_cliente != 'SP')
3. NÃO seja o CNPJ 62009696000174

MODOS DE EXECUÇÃO:
1. --rapido: Apenas aplica regra de CrossDocking (SEM consultar Receita) - INSTANTÂNEO
2. --sem-delay: Consulta Receita SEM delay entre requisições - RISCO DE BLOQUEIO
3. --delay=N: Define delay customizado entre requisições (padrão: 5 segundos)
4. Normal: Consulta Receita com delay de 5s e pula clientes com dados completos

EXEMPLOS:
python migrations/atualizar_crossdocking_clientes.py --rapido
python migrations/atualizar_crossdocking_clientes.py --delay=3
python migrations/atualizar_crossdocking_clientes.py --sem-delay
"""
import sys
import os
import time
import requests
import re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.motochefe.models import ClienteMoto, VendedorMoto
from app.utils.timezone import agora_utc_naive


def limpar_cnpj(cnpj):
    """Remove caracteres especiais do CNPJ"""
    if not cnpj:
        return None
    return re.sub(r'\D', '', str(cnpj))


def cliente_tem_dados_completos(cliente):
    """
    Verifica se cliente já tem dados mínimos preenchidos
    (não precisa consultar Receita)
    """
    return (
        cliente.cliente and
        not cliente.cliente.startswith('CLIENTE_') and
        cliente.cidade_cliente and
        cliente.estado_cliente
    )


def consultar_receita_federal(cnpj_limpo, mostrar_progresso=True):
    """
    Consulta dados do CNPJ na API ReceitaWS
    Retorna: dict com dados ou None se houver erro
    """
    try:
        url = f'https://www.receitaws.com.br/v1/cnpj/{cnpj_limpo}'
        if mostrar_progresso:
            print(f'   🔍 Consultando API ReceitaWS...', end=' ')

        response = requests.get(url, timeout=15)

        if response.status_code != 200:
            if mostrar_progresso:
                print(f'❌ Status {response.status_code}')
            return None

        dados = response.json()

        if dados.get('status') == 'ERROR':
            if mostrar_progresso:
                print(f'❌ {dados.get("message", "Erro desconhecido")}')
            return None

        if mostrar_progresso:
            print('✅ OK')
        return dados

    except requests.exceptions.Timeout:
        if mostrar_progresso:
            print('❌ Timeout')
        return None
    except requests.exceptions.RequestException as e:
        if mostrar_progresso:
            print(f'❌ Erro: {str(e)}')
        return None


def atualizar_crossdocking_clientes(modo='normal', delay_segundos=5):
    """
    Atualiza campo crossdocking nos clientes conforme regra de negócio

    Args:
        modo: 'normal', 'rapido' ou 'sem-delay'
        delay_segundos: segundos entre requisições (padrão: 5)
    """
    app = create_app()

    with app.app_context():
        print('='*80)
        print('SCRIPT: Atualizar CrossDocking em Clientes')
        print('='*80)
        print(f'MODO: {modo.upper()}')
        if modo != 'rapido':
            print(f'DELAY: {delay_segundos} segundos entre requisições')
        print('='*80)
        print()

        # 1. Buscar vendedor DANI
        print('1. Buscando vendedor DANI...')
        vendedor_dani = VendedorMoto.query.filter(
            VendedorMoto.vendedor.ilike('%DANI%'),
            VendedorMoto.ativo == True
        ).first()

        if vendedor_dani:
            print(f'   ✅ Vendedor DANI encontrado: ID={vendedor_dani.id}, Nome={vendedor_dani.vendedor}')
            vendedor_dani_id = vendedor_dani.id
        else:
            print('   ⚠️  Vendedor DANI não encontrado! Continuando sem filtro de vendedor...')
            vendedor_dani_id = None
        print()

        # 2. Buscar todos os clientes ativos
        print('2. Buscando clientes ativos...')
        clientes = ClienteMoto.query.filter_by(ativo=True).order_by(ClienteMoto.id).all()
        total_clientes = len(clientes)
        print(f'   ✅ {total_clientes} clientes encontrados')
        print()

        # 3. Estatísticas
        total_processados = 0
        total_atualizados = 0
        total_crossdocking_marcado = 0
        total_receita_consultada = 0
        total_receita_sucesso = 0
        total_pulados = 0
        erros = []

        print('3. Processando clientes...')
        print('-'*80)
        print('💡 DICA: Pressione Ctrl+C a qualquer momento para parar e salvar o progresso!')
        print()

        try:
            for idx, cliente in enumerate(clientes, 1):
                cnpj_limpo = limpar_cnpj(cliente.cnpj_cliente)

                # Barra de progresso
                percentual = int((idx / total_clientes) * 100)
                print(f'\n[{idx}/{total_clientes}] ({percentual}%) Cliente: {cliente.cliente[:40]}...')
                print(f'   CNPJ: {cnpj_limpo}')

                # Consultar Receita Federal (exceto modo rápido)
                dados_receita = None
                if modo != 'rapido':
                    # Verificar se cliente já tem dados completos
                    if cliente_tem_dados_completos(cliente):
                        print(f'   ⏩ Cliente já tem dados completos - pulando consulta Receita')
                        total_pulados += 1
                    elif cnpj_limpo and len(cnpj_limpo) == 14:
                        total_receita_consultada += 1
                        dados_receita = consultar_receita_federal(cnpj_limpo)

                        if dados_receita:
                            total_receita_sucesso += 1
                            # Atualizar dados do cliente
                            cliente.cliente = dados_receita.get('nome', cliente.cliente)
                            cliente.endereco_cliente = dados_receita.get('logradouro', cliente.endereco_cliente)
                            cliente.numero_cliente = dados_receita.get('numero', cliente.numero_cliente)
                            cliente.complemento_cliente = dados_receita.get('complemento', cliente.complemento_cliente)
                            cliente.bairro_cliente = dados_receita.get('bairro', cliente.bairro_cliente)
                            cliente.cidade_cliente = dados_receita.get('municipio', cliente.cidade_cliente)
                            cliente.estado_cliente = dados_receita.get('uf', cliente.estado_cliente)
                            cliente.cep_cliente = dados_receita.get('cep', cliente.cep_cliente)
                            cliente.telefone_cliente = dados_receita.get('telefone', cliente.telefone_cliente)
                            cliente.email_cliente = dados_receita.get('email', cliente.email_cliente)

                            print(f'   📝 Dados atualizados pela Receita Federal')

                        # Delay entre requisições (exceto modo sem-delay)
                        if modo != 'sem-delay' and idx < total_clientes:
                            print(f'   ⏳ Aguardando {delay_segundos}s...', end='', flush=True)
                            time.sleep(delay_segundos)
                            print(' ✅')

                # Aplicar regra de CrossDocking
                crossdocking_anterior = cliente.crossdocking
                deve_marcar_crossdocking = True

                # Condição 1: É do vendedor DANI?
                if vendedor_dani_id and cliente.vendedor_id == vendedor_dani_id:
                    deve_marcar_crossdocking = False
                    print(f'   ❌ É do vendedor DANI - NÃO marcar crossdocking')

                # Condição 2: É de São Paulo?
                elif cliente.estado_cliente and cliente.estado_cliente.upper() == 'SP':
                    deve_marcar_crossdocking = False
                    print(f'   ❌ É de São Paulo - NÃO marcar crossdocking')

                # Condição 3: É o CNPJ exceção?
                elif cnpj_limpo == '62009696000174':
                    deve_marcar_crossdocking = False
                    print(f'   ❌ É o CNPJ exceção 62.009.696/0001-74 - NÃO marcar crossdocking')

                # Aplicar CrossDocking
                if deve_marcar_crossdocking:
                    cliente.crossdocking = True
                    total_crossdocking_marcado += 1
                    print(f'   ✅ MARCADO como CrossDocking=True')
                else:
                    cliente.crossdocking = False
                    print(f'   ℹ️  Mantido como CrossDocking=False')

                # Marcar como atualizado
                cliente.atualizado_em = agora_utc_naive()
                cliente.atualizado_por = 'Script Migração CrossDocking'

                if crossdocking_anterior != cliente.crossdocking:
                    total_atualizados += 1
                    print(f'   📊 Status alterado: {crossdocking_anterior} → {cliente.crossdocking}')

                total_processados += 1

                # ✅ COMMIT INCREMENTAL A CADA CLIENTE
                try:
                    db.session.commit()
                    print(f'   💾 Salvo no banco')
                except Exception as e:
                    db.session.rollback()
                    erro_msg = f'Cliente {cliente.cliente} (CNPJ: {cnpj_limpo}): {str(e)}'
                    erros.append(erro_msg)
                    print(f'   ❌ ERRO ao salvar: {str(e)}')

        except KeyboardInterrupt:
            # ✅ USUÁRIO APERTOU CTRL+C - SALVAR O QUE JÁ FOI FEITO
            print('\n\n🛑 INTERROMPIDO PELO USUÁRIO (Ctrl+C)')
            print('📦 Salvando progresso até aqui...')
            try:
                db.session.commit()
                print('✅ Progresso salvo com sucesso!')
            except Exception as e:
                print(f'❌ Erro ao salvar progresso: {str(e)}')
                db.session.rollback()

        # Relatório final
        print()
        print('='*80)
        print('RELATÓRIO FINAL')
        print('='*80)
        print(f'Total de clientes processados:        {total_processados}')
        print(f'Total com status alterado:            {total_atualizados}')
        print(f'Total marcado como CrossDocking:      {total_crossdocking_marcado}')

        if modo != 'rapido':
            print(f'Clientes com dados completos (pulados): {total_pulados}')
            print(f'Consultas à Receita Federal:          {total_receita_consultada}')
            print(f'Consultas bem-sucedidas:              {total_receita_sucesso}')

        if erros:
            print()
            print('ERROS ENCONTRADOS:')
            for erro in erros:
                print(f'  - {erro}')

        # Tempo estimado economizado
        if modo != 'rapido' and total_pulados > 0:
            tempo_economizado = total_pulados * delay_segundos
            minutos = tempo_economizado // 60
            segundos = tempo_economizado % 60
            print()
            print(f'⚡ TEMPO ECONOMIZADO: {minutos}min {segundos}s (pulando {total_pulados} clientes com dados completos)')

        print('='*80)
        print('✅ Script finalizado!')
        print('='*80)


if __name__ == '__main__':
    # Parse argumentos
    modo = 'normal'
    delay = 5

    for arg in sys.argv[1:]:
        if arg == '--rapido':
            modo = 'rapido'
        elif arg == '--sem-delay':
            modo = 'sem-delay'
        elif arg.startswith('--delay='):
            try:
                delay = int(arg.split('=')[1])
            except ValueError:
                print(f'❌ Valor inválido para delay: {arg}')
                sys.exit(1)

    try:
        atualizar_crossdocking_clientes(modo=modo, delay_segundos=delay)
    except Exception as e:
        print(f'\n\n❌ ERRO FATAL: {str(e)}')
        import traceback
        traceback.print_exc()
