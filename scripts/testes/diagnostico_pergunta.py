"""
Diagnóstico: Por que a pergunta não está sendo respondida corretamente?

Testa o fluxo completo de uma pergunta complexa para identificar
onde o sistema está falhando.

Execute: python scripts/testes/diagnostico_pergunta.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app

app = create_app()

PERGUNTA = "Quando dá pra enviar 28 pallets pro atacadao 183 que não esteja separado?"

with app.app_context():
    print("=" * 70)
    print("DIAGNÓSTICO: Fluxo da pergunta complexa")
    print("=" * 70)
    print(f"\n📝 PERGUNTA: {PERGUNTA}\n")

    # ETAPA 1: O que o EXTRATOR retorna?
    print("=" * 70)
    print("ETAPA 1: EXTRAÇÃO INTELIGENTE (o que o Claude entende?)")
    print("=" * 70)
    try:
        from app.claude_ai_lite.core.intelligent_extractor import extrair_inteligente

        extracao = extrair_inteligente(PERGUNTA)
        print(f"\n📤 Extração bruta do Claude:")
        print(json.dumps(extracao, indent=2, ensure_ascii=False, default=str))

        intencao_extraida = extracao.get('intencao', '')
        tipo_extraido = extracao.get('tipo', '')
        entidades_extraidas = extracao.get('entidades', {})

        print(f"\n🎯 Resumo:")
        print(f"   Intenção: {intencao_extraida}")
        print(f"   Tipo: {tipo_extraido}")
        print(f"   Entidades: {list(entidades_extraidas.keys())}")

    except Exception as e:
        print(f"❌ ERRO na extração: {e}")
        import traceback
        traceback.print_exc()
        extracao = {}

    # ETAPA 2: O que o ENTITY_MAPPER faz com isso?
    print("\n" + "=" * 70)
    print("ETAPA 2: MAPEAMENTO (como o sistema interpreta?)")
    print("=" * 70)
    try:
        from app.claude_ai_lite.core.entity_mapper import mapear_extracao

        mapeado = mapear_extracao(extracao)
        print(f"\n📤 Após mapeamento:")
        print(json.dumps(mapeado, indent=2, ensure_ascii=False, default=str))

        dominio = mapeado.get('dominio', '')
        intencao_final = mapeado.get('intencao', '')
        entidades_final = mapeado.get('entidades', {})

        print(f"\n🎯 Resumo:")
        print(f"   Domínio: {dominio}")
        print(f"   Intenção: {intencao_final}")
        print(f"   Entidades: {list(entidades_final.keys())}")

    except Exception as e:
        print(f"❌ ERRO no mapeamento: {e}")
        import traceback
        traceback.print_exc()
        mapeado = {}

    # ETAPA 3: Qual CAPABILITY é encontrada?
    print("\n" + "=" * 70)
    print("ETAPA 3: CAPABILITY (quem vai processar?)")
    print("=" * 70)
    try:
        from app.claude_ai_lite.capabilities import find_capability, get_all_capabilities

        intencao_final = mapeado.get('intencao', '')
        entidades_final = mapeado.get('entidades', {})

        cap = find_capability(intencao_final, entidades_final)

        if cap:
            print(f"\n✅ Capability encontrada: {cap.NOME}")
            print(f"   Domínio: {cap.DOMINIO}")
            print(f"   Tipo: {cap.TIPO}")
            print(f"   Campos de busca aceitos: {cap.CAMPOS_BUSCA}")
            print(f"   Intenções aceitas: {cap.INTENCOES}")

            # Verifica se as entidades extraídas são compatíveis
            campo, valor = cap.extrair_valor_busca(entidades_final)
            print(f"\n🔍 Tentativa de extrair critério de busca:")
            print(f"   Campo: {campo}")
            print(f"   Valor: {valor}")

            if not campo or not valor:
                print(f"\n⚠️ PROBLEMA: Capability encontrada mas NÃO consegue extrair critério!")
                print(f"   A capability espera: {cap.CAMPOS_BUSCA}")
                print(f"   Entidades disponíveis: {list(entidades_final.keys())}")
        else:
            print(f"\n❌ NENHUMA capability encontrada!")
            print(f"   Isso ativaria o auto_loader como fallback")

    except Exception as e:
        print(f"❌ ERRO ao buscar capability: {e}")
        import traceback
        traceback.print_exc()

    # ETAPA 4: O que a capability RETORNARIA?
    print("\n" + "=" * 70)
    print("ETAPA 4: EXECUÇÃO (o que seria retornado?)")
    print("=" * 70)
    try:
        if cap:
            resultado = cap.executar(entidades_final, {'usuario_id': 1})
            print(f"\n📤 Resultado da execução:")
            print(f"   Sucesso: {resultado.get('sucesso')}")
            print(f"   Total encontrado: {resultado.get('total_encontrado', resultado.get('total', 0))}")

            if resultado.get('erro'):
                print(f"   ❌ Erro: {resultado.get('erro')}")

            if resultado.get('dados'):
                print(f"\n   Primeiros dados:")
                for i, item in enumerate(resultado.get('dados', [])[:3], 1):
                    if isinstance(item, dict):
                        resumo = {k: v for k, v in list(item.items())[:4]}
                        print(f"   {i}. {resumo}")
                    else:
                        print(f"   {i}. {item}")

            # MOSTRA CARGA SUGERIDA SE EXISTIR
            if resultado.get('carga_sugerida', {}).get('pode_montar'):
                carga = resultado['carga_sugerida']
                print(f"\n" + "=" * 50)
                print(f"📋 CARGA SUGERIDA MONTADA:")
                print(f"=" * 50)
                print(f"   Total: {carga['total_pallets']:.1f} pallets")
                print(f"   Peso: {carga['total_peso']:,.0f} kg")
                print(f"   Valor: R$ {carga['total_valor']:,.2f}")
                print(f"   Itens: {len(carga['itens'])}")
                if carga['todos_disponiveis_hoje']:
                    print(f"   Status: ✅ TODOS DISPONÍVEIS HOJE")
                else:
                    print(f"   Status: ⏳ {carga['itens_aguardar']} item(ns) aguardando estoque")
                print(f"\n   --- ITENS DA CARGA ---")
                for i, item in enumerate(carga['itens'], 1):
                    status = "✅" if item.get('disponivel_hoje') else "⏳"
                    fracionado = item.get('fracionado', False)
                    if fracionado:
                        print(f"   {i}. [{status}] {item['nome_produto'][:50]} ✂️ PARCIAL")
                        print(f"      Pedido: {item['num_pedido']} | {item['quantidade']:.0f} de {item.get('quantidade_original', 0):.0f} un ({item.get('percentual_usado', 0):.0f}%) = {item['pallets']:.2f} pallets")
                    else:
                        print(f"   {i}. [{status}] {item['nome_produto'][:50]}")
                        print(f"      Pedido: {item['num_pedido']} | {item['quantidade']:.0f} un = {item['pallets']:.2f} pallets")
                print(f"\n   💬 Usuário pode responder 'CONFIRMAR CARGA' para criar separação")
        else:
            print("\n⏭️ Sem capability, testando auto_loader...")
            from app.claude_ai_lite.ia_trainer.services.auto_loader import tentar_responder_automaticamente

            resultado_auto = tentar_responder_automaticamente(
                consulta=PERGUNTA,
                intencao=mapeado,
                usuario_id=1,
                usuario="teste"
            )
            print(f"\n📤 Resultado do auto_loader:")
            print(f"   Sucesso: {resultado_auto.get('sucesso')}")
            print(f"   Loader ID: {resultado_auto.get('loader_id')}")
            if resultado_auto.get('resposta'):
                print(f"   Resposta: {resultado_auto.get('resposta')[:300]}...") # type: ignore
            if resultado_auto.get('erro'):
                print(f"   ❌ Erro: {resultado_auto.get('erro')}")

    except Exception as e:
        print(f"❌ ERRO na execução: {e}")
        import traceback
        traceback.print_exc()

    # RESUMO DO DIAGNÓSTICO
    print("\n" + "=" * 70)
    print("📊 RESUMO DO DIAGNÓSTICO")
    print("=" * 70)

    problemas = []
    sucessos = []

    # Verifica problemas
    if not extracao.get('entidades'):
        problemas.append("❌ Extrator não extraiu entidades")
    else:
        sucessos.append("✅ Entidades extraídas com sucesso")

    if 'cliente' in entidades_extraidas or 'raz_social_red' in entidades_final:
        sucessos.append(f"✅ Cliente extraído: {entidades_extraidas.get('cliente') or entidades_final.get('raz_social_red')}")
    else:
        problemas.append("❌ Cliente não foi extraído")

    if 'quantidade' in entidades_extraidas or 'qtd_saldo' in entidades_final:
        sucessos.append(f"✅ Quantidade extraída: {entidades_extraidas.get('quantidade') or entidades_final.get('qtd_saldo')}")
    else:
        problemas.append("❌ Quantidade não foi extraída")

    if cap and campo:
        sucessos.append(f"✅ Capability encontrada: {cap.NOME}")
        sucessos.append(f"✅ Campo de busca: {campo} = {valor}")
    elif cap and not campo:
        problemas.append(f"❌ Capability {cap.NOME} não aceita as entidades extraídas")

    # Verifica se tem pallets no resultado
    if 'resultado' in dir() and resultado.get('total_pallets'):
        sucessos.append(f"✅ Total de pallets calculado: {resultado.get('total_pallets')}")
    if 'resultado' in dir() and resultado.get('analise', {}).get('mensagem'):
        sucessos.append(f"✅ Mensagem: {resultado['analise']['mensagem']}")

    # Verifica carga sugerida
    if 'resultado' in dir() and resultado.get('carga_sugerida', {}).get('pode_montar'):
        carga = resultado['carga_sugerida']
        sucessos.append(f"✅ CARGA MONTADA: {carga['total_pallets']:.1f} pallets, {len(carga['itens'])} itens")

    if sucessos:
        print("\n🟢 SUCESSOS:")
        for s in sucessos:
            print(f"   {s}")

    if problemas:
        print("\n🔴 PROBLEMAS:")
        for p in problemas:
            print(f"   {p}")

    print("\n" + "=" * 70)
    print("FIM DO DIAGNÓSTICO")
    print("=" * 70)
