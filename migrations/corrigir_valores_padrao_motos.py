"""
Script para corrigir valores padrão das motos no banco
Data: 14/10/2025

OBJETIVO:
Garantir que todas as motos no sistema tenham valores padrão corretos para:
- status
- status_pagamento_custo
- reservado
- empresa_pagadora_id

REGRA:
Motos que ainda não foram vendidas/reservadas devem ter:
- status = 'DISPONIVEL'
- status_pagamento_custo = 'PENDENTE' (se não foi pago)
- reservado = False (se status = 'DISPONIVEL')
- empresa_pagadora_id = NULL (se não foi pago)
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.motochefe.models.produto import Moto
from app.utils.timezone import agora_utc_naive
from sqlalchemy import text


def corrigir_valores_padrao_motos():
    """
    Corrige valores padrão de motos que possam estar inconsistentes
    """
    app = create_app()

    with app.app_context():
        print('='*80)
        print('SCRIPT: Corrigir Valores Padrão de Motos')
        print('='*80)
        print()

        # 1. Estatísticas iniciais
        print('1. Verificando estado atual...')
        total_motos = Moto.query.filter_by(ativo=True).count()
        print(f'   Total de motos ativas: {total_motos}')

        motos_disponiveis = Moto.query.filter_by(status='DISPONIVEL', ativo=True).count()
        motos_reservadas = Moto.query.filter_by(status='RESERVADA', ativo=True).count()
        motos_vendidas = Moto.query.filter_by(status='VENDIDA', ativo=True).count()
        motos_avariadas = Moto.query.filter_by(status='AVARIADO', ativo=True).count()
        motos_devolvidas = Moto.query.filter_by(status='DEVOLVIDO', ativo=True).count()

        print(f'   - DISPONIVEL: {motos_disponiveis}')
        print(f'   - RESERVADA: {motos_reservadas}')
        print(f'   - VENDIDA: {motos_vendidas}')
        print(f'   - AVARIADO: {motos_avariadas}')
        print(f'   - DEVOLVIDO: {motos_devolvidas}')
        print()

        # 2. Corrigir inconsistências
        print('2. Corrigindo inconsistências...')
        print('-'*80)

        total_corrigidas = 0
        erros = []

        # 2.1. Motos DISPONÍVEIS devem ter reservado=False
        print('\n[2.1] Corrigindo campo "reservado" de motos DISPONÍVEIS...')
        motos_disponiveis_reservadas = Moto.query.filter_by(
            status='DISPONIVEL',
            reservado=True,
            ativo=True
        ).all()

        if motos_disponiveis_reservadas:
            print(f'   Encontradas {len(motos_disponiveis_reservadas)} motos DISPONÍVEIS marcadas como reservadas')
            for moto in motos_disponiveis_reservadas:
                moto.reservado = False
                moto.atualizado_em = agora_utc_naive()
                moto.atualizado_por = 'Script Correção Padrões'
                total_corrigidas += 1
            print(f'   ✅ {len(motos_disponiveis_reservadas)} motos corrigidas')
        else:
            print('   ✅ Nenhuma inconsistência encontrada')

        # 2.2. Motos RESERVADAS/VENDIDAS devem ter reservado=True
        print('\n[2.2] Corrigindo campo "reservado" de motos RESERVADAS/VENDIDAS...')
        motos_reservadas_nao_marcadas = Moto.query.filter(
            Moto.status.in_(['RESERVADA', 'VENDIDA']),
            Moto.reservado == False,
            Moto.ativo == True
        ).all()

        if motos_reservadas_nao_marcadas:
            print(f'   Encontradas {len(motos_reservadas_nao_marcadas)} motos RESERVADAS/VENDIDAS sem flag reservado')
            for moto in motos_reservadas_nao_marcadas:
                moto.reservado = True
                moto.atualizado_em = agora_utc_naive()
                moto.atualizado_por = 'Script Correção Padrões'
                total_corrigidas += 1
            print(f'   ✅ {len(motos_reservadas_nao_marcadas)} motos corrigidas')
        else:
            print('   ✅ Nenhuma inconsistência encontrada')

        # 2.3. Verificar status_pagamento_custo vs custo_pago
        print('\n[2.3] Verificando status_pagamento_custo vs custo_pago...')
        motos_todas = Moto.query.filter_by(ativo=True).all()

        inconsistencias_pagamento = 0
        for moto in motos_todas:
            custo_pago = moto.custo_pago or 0
            custo_aquisicao = moto.custo_aquisicao

            # Determinar status correto
            if custo_pago == 0:
                status_correto = 'PENDENTE'
            elif custo_pago >= custo_aquisicao:
                status_correto = 'PAGO'
            else:
                status_correto = 'PARCIAL'

            # Corrigir se necessário
            if moto.status_pagamento_custo != status_correto:
                print(f'   Moto {moto.numero_chassi}: {moto.status_pagamento_custo} → {status_correto}')
                moto.status_pagamento_custo = status_correto
                moto.atualizado_em = agora_utc_naive()
                moto.atualizado_por = 'Script Correção Padrões'
                inconsistencias_pagamento += 1
                total_corrigidas += 1

        if inconsistencias_pagamento > 0:
            print(f'   ✅ {inconsistencias_pagamento} motos com status_pagamento_custo corrigido')
        else:
            print('   ✅ Nenhuma inconsistência encontrada')

        # 2.4. Remover empresa_pagadora_id de motos não pagas
        print('\n[2.4] Corrigindo empresa_pagadora_id de motos PENDENTES...')
        motos_pendentes_com_empresa = Moto.query.filter_by(
            status_pagamento_custo='PENDENTE',
            ativo=True
        ).filter(
            Moto.empresa_pagadora_id.isnot(None)
        ).all()

        if motos_pendentes_com_empresa:
            print(f'   Encontradas {len(motos_pendentes_com_empresa)} motos PENDENTES com empresa_pagadora_id preenchido')
            for moto in motos_pendentes_com_empresa:
                print(f'   Moto {moto.numero_chassi}: removendo empresa_pagadora_id={moto.empresa_pagadora_id}')
                moto.empresa_pagadora_id = None
                moto.atualizado_em = agora_utc_naive()
                moto.atualizado_por = 'Script Correção Padrões'
                total_corrigidas += 1
            print(f'   ✅ {len(motos_pendentes_com_empresa)} motos corrigidas')
        else:
            print('   ✅ Nenhuma inconsistência encontrada')

        # 3. Commit
        print()
        print('-'*80)
        print('3. Salvando alterações...')
        try:
            db.session.commit()
            print('   ✅ Alterações salvas com sucesso!')
        except Exception as e:
            db.session.rollback()
            print(f'   ❌ ERRO ao salvar: {str(e)}')
            erros.append(f'Erro ao salvar: {str(e)}')

        # 4. Estatísticas finais
        print()
        print('='*80)
        print('RELATÓRIO FINAL')
        print('='*80)
        print(f'Total de motos ativas:           {total_motos}')
        print(f'Total de correções realizadas:   {total_corrigidas}')

        if erros:
            print()
            print('ERROS ENCONTRADOS:')
            for erro in erros:
                print(f'  - {erro}')

        # 5. Estado final
        print()
        print('ESTADO FINAL:')
        motos_disponiveis = Moto.query.filter_by(status='DISPONIVEL', ativo=True).count()
        motos_reservadas = Moto.query.filter_by(status='RESERVADA', ativo=True).count()
        motos_vendidas = Moto.query.filter_by(status='VENDIDA', ativo=True).count()
        motos_avariadas = Moto.query.filter_by(status='AVARIADO', ativo=True).count()
        motos_devolvidas = Moto.query.filter_by(status='DEVOLVIDO', ativo=True).count()

        print(f'   - DISPONIVEL: {motos_disponiveis}')
        print(f'   - RESERVADA: {motos_reservadas}')
        print(f'   - VENDIDA: {motos_vendidas}')
        print(f'   - AVARIADO: {motos_avariadas}')
        print(f'   - DEVOLVIDO: {motos_devolvidas}')

        print()
        print('='*80)
        print('✅ Script finalizado!')
        print('='*80)


if __name__ == '__main__':
    try:
        corrigir_valores_padrao_motos()
    except KeyboardInterrupt:
        print('\n\n⚠️  Script interrompido pelo usuário!')
    except Exception as e:
        print(f'\n\n❌ ERRO FATAL: {str(e)}')
        import traceback
        traceback.print_exc()
