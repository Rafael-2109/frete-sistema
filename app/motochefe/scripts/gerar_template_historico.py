"""
Script para Gerar Template Excel de Importação Histórica
Sistema MotoCHEFE - Fases 5, 6 e 7

USO:
    python app/motochefe/scripts/gerar_template_historico.py

SAÍDA:
    Cria arquivo: /tmp/template_historico_motochefe.xlsx
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import pandas as pd
from datetime import date


def gerar_template_historico():
    """Gera arquivo Excel template para importação histórica"""

    arquivo_saida = '/tmp/template_historico_motochefe.xlsx'

    print("=" * 80)
    print("GERADOR DE TEMPLATE - IMPORTAÇÃO HISTÓRICA MOTOCHEFE")
    print("=" * 80)
    print()

    with pd.ExcelWriter(arquivo_saida, engine='openpyxl') as writer:
        # ========================================
        # ABA 1: COMISSÕES
        # ========================================
        df_comissoes = pd.DataFrame(columns=[
            'numero_pedido',
            'numero_chassi',
            'vendedor',
            'valor_comissao',
            'status_pagamento',
            'data_pagamento',
            'empresa_pagadora'
        ])

        # Linha de exemplo
        df_comissoes.loc[0] = [
            'MC-001',           # numero_pedido
            'ABC123XYZ456',     # numero_chassi
            'João Silva',       # vendedor (obrigatório)
            300.00,             # valor_comissao
            'PAGO',             # status_pagamento (PAGO ou PENDENTE)
            '2024-01-15',       # data_pagamento (obrigatório se PAGO)
            'Sogima LTDA'       # empresa_pagadora (obrigatório se PAGO)
        ]

        df_comissoes.loc[1] = [
            'MC-001',
            'ABC123XYZ456',
            'Maria Santos',     # Mesmo chassi, vendedor diferente (permitido)
            150.00,
            'PAGO',
            '2024-01-15',
            'Sogima LTDA'
        ]

        df_comissoes.loc[2] = [
            'MC-002',
            'DEF789GHI012',
            'João Silva',
            250.00,
            'PENDENTE',
            None,               # data_pagamento (NULL se PENDENTE)
            None                # empresa_pagadora (NULL se PENDENTE)
        ]

        df_comissoes.to_excel(writer, sheet_name='Comissoes', index=False)

        # ========================================
        # ABA 2: MONTAGENS
        # ========================================
        df_montagens = pd.DataFrame(columns=[
            'numero_pedido',
            'numero_chassi',
            'fornecedor_montagem',
            'valor_cliente',
            'valor_custo',
            'status_recebimento',
            'data_recebimento',
            'empresa_recebedora',
            'status_pagamento',
            'data_pagamento',
            'empresa_pagadora'
        ])

        # Linha de exemplo
        df_montagens.loc[0] = [
            'MC-001',           # numero_pedido
            'ABC123XYZ456',     # numero_chassi
            'Equipe Montagem X',  # fornecedor_montagem
            100.00,             # valor_cliente (quanto cliente pagou)
            80.00,              # valor_custo (quanto empresa pagou)
            'PAGO',             # status_recebimento (PAGO ou PENDENTE)
            '2024-01-10',       # data_recebimento (obrigatório se status_recebimento=PAGO)
            'Sogima LTDA',      # empresa_recebedora (obrigatório se status_recebimento=PAGO)
            'PAGO',             # status_pagamento (PAGO ou PENDENTE)
            '2024-01-15',       # data_pagamento (obrigatório se status_pagamento=PAGO)
            'Sogima LTDA'       # empresa_pagadora (obrigatório se status_pagamento=PAGO)
        ]

        df_montagens.loc[1] = [
            'MC-002',
            'DEF789GHI012',
            'Equipe Montagem Y',
            150.00,
            120.00,
            'PAGO',
            '2024-01-12',
            'Sogima LTDA',
            'PENDENTE',         # Recebeu do cliente mas ainda não pagou fornecedor
            None,
            None
        ]

        df_montagens.to_excel(writer, sheet_name='Montagens', index=False)

        # ========================================
        # ABA 3: MOVIMENTAÇÕES
        # ========================================
        df_movimentacoes = pd.DataFrame(columns=[
            'numero_pedido',
            'numero_chassi',
            'valor_cliente',
            'valor_custo',
            'status_recebimento',
            'data_recebimento',
            'empresa_recebedora',
            'status_pagamento',
            'data_pagamento',
            'empresa_pagadora'
        ])

        # Linha de exemplo
        df_movimentacoes.loc[0] = [
            'MC-001',           # numero_pedido
            'ABC123XYZ456',     # numero_chassi
            50.00,              # valor_cliente (quanto cliente pagou)
            50.00,              # valor_custo (quanto empresa pagou MargemSogima)
            'PAGO',             # status_recebimento (PAGO ou PENDENTE)
            '2024-01-10',       # data_recebimento (obrigatório se status_recebimento=PAGO)
            'Sogima LTDA',      # empresa_recebedora (obrigatório se status_recebimento=PAGO)
            'PAGO',             # status_pagamento (PAGO ou PENDENTE)
            '2024-01-15',       # data_pagamento (obrigatório se status_pagamento=PAGO)
            'Sogima LTDA'       # empresa_pagadora (obrigatório se status_pagamento=PAGO)
        ]

        df_movimentacoes.loc[1] = [
            'MC-002',
            'DEF789GHI012',
            0.00,               # Cliente não pagou movimentação (empresa absorveu custo)
            50.00,              # Mas empresa pagou MargemSogima
            'PAGO',             # Título R$ 0 fica PAGO automaticamente
            '2024-01-12',
            'Sogima LTDA',
            'PAGO',
            '2024-01-15',
            'Sogima LTDA'
        ]

        df_movimentacoes.to_excel(writer, sheet_name='Movimentacoes', index=False)

        # ========================================
        # ABA 4: INSTRUÇÕES
        # ========================================
        df_instrucoes = pd.DataFrame({
            'INSTRUÇÕES DE USO': [
                '',
                '1. PREPARAÇÃO:',
                '   - Certifique-se de que os pedidos já foram importados (Fase 4)',
                '   - Certifique-se de que as empresas existem no sistema',
                '',
                '2. PREENCHIMENTO:',
                '   - numero_pedido: DEVE existir no sistema',
                '   - numero_chassi: DEVE existir no pedido',
                '   - vendedor (comissões): Nome EXATO do vendedor cadastrado',
                '   - Datas: Formato DD/MM/YYYY ou YYYY-MM-DD',
                '   - Valores: Números com 2 casas decimais (use . ou ,)',
                '   - status_pagamento/status_recebimento: Apenas "PAGO" ou "PENDENTE"',
                '',
                '3. CAMPOS CONDICIONAIS:',
                '   - Se status = "PAGO": data e empresa são OBRIGATÓRIOS',
                '   - Se status = "PENDENTE": data e empresa devem ficar VAZIOS (NULL)',
                '',
                '4. IMPORTANTE:',
                '   - FASE 5 (Comissões): Pode haver MÚLTIPLAS comissões por chassi',
                '   - FASE 5: Apenas 1 comissão por vendedor+chassi (valida duplicidade)',
                '   - FASE 6 (Montagens): valor_cliente pode ser R$ 0 (sem montagem)',
                '   - FASE 7 (Movimentações): valor_cliente pode ser R$ 0 (empresa absorveu)',
                '   - Valor deduzido de VENDA = valor_cliente (montagem + movimentação)',
                '   - Em caso de ERRO em qualquer fase: ROLLBACK TOTAL',
                '',
                '5. ORDEM DE EXECUÇÃO:',
                '   - O script executa: Fase 5 → Fase 6 → Fase 7',
                '   - Se qualquer fase falhar, NADA é importado',
                '',
                '6. VALIDAÇÕES:',
                '   - Após importação, valide:',
                '     * Saldos de empresas estão corretos',
                '     * Títulos VENDA foram deduzidos corretamente',
                '     * MovimentacaoFinanceira PAI/FILHOS criadas para lotes',
                '',
                '7. EXECUÇÃO:',
                '   python app/motochefe/scripts/importar_historico_completo.py',
                '',
                '8. ARQUIVO DE SAÍDA:',
                '   - Altere o caminho no script se necessário',
                '   - Padrão: /tmp/historico_motochefe.xlsx'
            ]
        })

        df_instrucoes.to_excel(writer, sheet_name='LEIA_ME', index=False)

    print(f"✅ Template criado com sucesso!")
    print(f"📄 Arquivo: {arquivo_saida}\n")
    print("📋 ABAS CRIADAS:")
    print("   1. Comissoes - Fase 5")
    print("   2. Montagens - Fase 6")
    print("   3. Movimentacoes - Fase 7")
    print("   4. LEIA_ME - Instruções de uso\n")
    print("📝 PRÓXIMOS PASSOS:")
    print("   1. Abra o arquivo Excel")
    print("   2. Preencha os dados históricos nas abas 1, 2 e 3")
    print("   3. Salve como: /tmp/historico_motochefe.xlsx")
    print("   4. Execute: python app/motochefe/scripts/importar_historico_completo.py\n")


if __name__ == '__main__':
    gerar_template_historico()
