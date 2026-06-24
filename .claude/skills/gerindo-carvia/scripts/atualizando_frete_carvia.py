#!/usr/bin/env python3
"""
Atualiza valores de UM frete CarVia (carvia_fretes) — WRITE
============================================================

Origem: D8 IMP-2026-06-24-001/-002/-003. A skill gerindo-carvia era 100%
read-only; quando um frete CarVia nascia com tabela errada ("0") e
valor_cotado=0, o agente calculava o valor correto mas nao tinha como
persistir — encerrava a sessao entregando SQL manual para um dev rodar.
A tela /carvia/fretes/lancar-cte exibe V.Cotado vindo de
carvia_fretes.valor_cotado mas o campo NAO e editavel na UI sem CTe
vinculado (IMP-2026-06-24-004). Este script fecha o gap.

ESCOPO: persiste valores JA CALCULADOS. NAO calcula frete (peso cubado x
tabela) — isso e responsabilidade de `cotando_subcontrato_carvia.py`
(constituicao das skills: um atomo nunca embute outro fluxo). Combine:
  1) `cotando_subcontrato_carvia.py --operacao N --transportadora X`  (calcula)
  2) `atualizando_frete_carvia.py --frete-id N --valor-cotado <calc>`  (persiste)

SEGURANCA:
  - dry-run e o DEFAULT. Sem --confirmar, NADA e gravado (so mostra antes/depois).
  - So efetiva com --confirmar.
  - Recalcula requer_aprovacao via CarviaFrete.requer_aprovacao_por_valor()
    (paridade Frete Nacom: |considerado - cotado| > R$5 ou |considerado -
    pago| > R$5) e reporta os motivos — NAO auto-aprova nem dispara solicitacao.
  - Avisa (mas permite com --confirmar) se o frete ja tem valor_cte lancado.

Uso:
  --frete-id N           (obrigatorio) id do carvia_fretes
  --valor-cotado X       novo valor_cotado (custo de tabela)
  --valor-considerado Y  novo valor_considerado (default: espelha valor_cotado
                         quando este e informado E o frete nao tem valor_cte)
  --valor-pago W         novo valor_pago
  --valor-venda V        novo valor_venda (lado receita)
  --tabela-nome "9-"     novo tabela_nome_tabela (snapshot da tabela aplicada)
  --tabela-valor-kg Z    novo tabela_valor_kg
  --user-id N            usuario que solicitou (auditoria em observacoes)
  --confirmar            executa de verdade (sem isto = dry-run)

Exemplos:
  # preview (dry-run) — frete 810 com tabela "9-" sobre peso cubado, R$226,33
  python atualizando_frete_carvia.py --frete-id 810 --valor-cotado 226.33 \
      --tabela-nome "9-"
  # efetiva
  python atualizando_frete_carvia.py --frete-id 810 --valor-cotado 226.33 \
      --tabela-nome "9-" --user-id 87 --confirmar
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

EXIT_OK = 0
EXIT_FALHA = 1
EXIT_USO = 2
EXIT_DRYRUN = 4

# Campos de carvia_fretes que este script pode alterar.
# (chave CLI normalizada -> atributo do model)
CAMPOS_EDITAVEIS = {
    'valor_cotado': 'valor_cotado',
    'valor_considerado': 'valor_considerado',
    'valor_pago': 'valor_pago',
    'valor_venda': 'valor_venda',
    'tabela_nome': 'tabela_nome_tabela',
    'tabela_valor_kg': 'tabela_valor_kg',
}


def _snapshot(frete):
    """Captura os campos relevantes de um CarviaFrete para antes/depois."""
    return {
        'valor_cotado': _f(frete.valor_cotado),
        'valor_considerado': _f(frete.valor_considerado),
        'valor_cte': _f(frete.valor_cte),
        'valor_pago': _f(frete.valor_pago),
        'valor_venda': _f(frete.valor_venda),
        'tabela_nome_tabela': frete.tabela_nome_tabela,
        'tabela_valor_kg': _f(frete.tabela_valor_kg),
        'status_conferencia': frete.status_conferencia,
        'requer_aprovacao': bool(frete.requer_aprovacao),
    }


def _f(v):
    """float seguro (None preservado)."""
    return float(v) if v is not None else None


def atualizar_frete(frete_id, novos, user_id=None, confirmar=False):
    """Aplica os valores informados ao frete. dry-run por padrao."""
    from app import db
    from app.carvia.models import CarviaFrete

    frete = db.session.get(CarviaFrete, frete_id)
    if not frete:
        return EXIT_FALHA, {
            'sucesso': False,
            'erro': f'Frete CarVia {frete_id} nao encontrado',
        }

    avisos = []
    antes = _snapshot(frete)

    # Espelhamento default: valor_considerado segue valor_cotado quando este e
    # informado, --valor-considerado nao foi passado e nao ha CTe lancado.
    # Replica o comportamento da criacao (valor_considerado = valor_custo).
    if (
        'valor_cotado' in novos
        and 'valor_considerado' not in novos
        and frete.valor_cte is None
    ):
        novos['valor_considerado'] = novos['valor_cotado']
        avisos.append(
            'valor_considerado espelhado de valor_cotado '
            '(nao informado e sem CTe lancado)'
        )

    # Aviso: alterar valor_cotado com CTe ja lancado (a UI usa editar_frete p/
    # isso). Permitido (valor_cotado e o custo teorico de tabela), mas sinaliza.
    if 'valor_cotado' in novos and frete.valor_cte is not None:
        avisos.append(
            f'frete ja tem valor_cte={_f(frete.valor_cte)} lancado — alterar '
            'valor_cotado muda apenas o custo teorico de tabela, nao o CTe'
        )

    # Aplicar
    alteracoes = []
    for chave, valor in novos.items():
        attr = CAMPOS_EDITAVEIS[chave]
        atual = getattr(frete, attr)
        setattr(frete, attr, valor)
        alteracoes.append({
            'campo': attr,
            'de': _f(atual) if isinstance(atual, (int, float)) else atual,
            'para': _f(valor) if isinstance(valor, (int, float)) else valor,
        })

    # Auditoria em observacoes (frete nao tem atualizado_por/_em).
    if confirmar:
        _anotar_observacao(frete, alteracoes, user_id)

    # Recalcular flag de aprovacao (NAO auto-aprova; so reporta).
    requer, motivos = frete.requer_aprovacao_por_valor()
    frete.requer_aprovacao = requer

    depois = _snapshot(frete)

    resultado = {
        'sucesso': True,
        'frete_id': frete_id,
        'dry_run': not confirmar,
        'alteracoes': alteracoes,
        'antes': antes,
        'depois': depois,
        'requer_aprovacao': {'requer': requer, 'motivos': motivos},
        'avisos': avisos,
    }

    if confirmar:
        db.session.commit()
        resultado['gravado'] = True
        return EXIT_OK, resultado

    db.session.rollback()
    resultado['gravado'] = False
    resultado['mensagem'] = 'DRY-RUN: nada gravado. Rode com --confirmar para efetivar.'
    return EXIT_DRYRUN, resultado


def _anotar_observacao(frete, alteracoes, user_id):
    """Append em observacoes registrando a alteracao (auditoria leve)."""
    from app.utils.timezone import agora_brasil_naive

    autor = _nome_usuario(user_id) if user_id else 'desconhecido'
    quando = agora_brasil_naive().strftime('%Y-%m-%d %H:%M')
    resumo = '; '.join(
        f"{a['campo']}: {a['de']}->{a['para']}" for a in alteracoes
    )
    linha = f'[atualizando_frete_carvia {quando} por {autor}] {resumo}'
    frete.observacoes = (
        f'{frete.observacoes}\n{linha}' if frete.observacoes else linha
    )


def _nome_usuario(user_id):
    from app import db
    try:
        from app.auth.models import Usuario
    except Exception:
        return f'id {user_id}'
    u = db.session.get(Usuario, user_id)
    return f'{u.nome} (id {user_id})' if u and getattr(u, 'nome', None) else f'id {user_id}'


def main():
    parser = argparse.ArgumentParser(
        description='Atualiza valores de UM frete CarVia (WRITE, dry-run default)',
    )
    parser.add_argument('--frete-id', type=int, required=True, help='id do carvia_fretes')
    parser.add_argument('--valor-cotado', type=float, help='novo valor_cotado (custo tabela)')
    parser.add_argument('--valor-considerado', type=float, help='novo valor_considerado')
    parser.add_argument('--valor-pago', type=float, help='novo valor_pago')
    parser.add_argument('--valor-venda', type=float, help='novo valor_venda (receita)')
    parser.add_argument('--tabela-nome', type=str, help='novo tabela_nome_tabela')
    parser.add_argument('--tabela-valor-kg', type=float, help='novo tabela_valor_kg')
    parser.add_argument('--user-id', type=int, help='usuario solicitante (auditoria)')
    parser.add_argument('--confirmar', action='store_true',
                        help='executa de verdade (sem isto = dry-run)')
    args = parser.parse_args()

    # Coletar valores informados (so os que vieram na linha de comando).
    novos = {}
    if args.valor_cotado is not None:
        novos['valor_cotado'] = args.valor_cotado
    if args.valor_considerado is not None:
        novos['valor_considerado'] = args.valor_considerado
    if args.valor_pago is not None:
        novos['valor_pago'] = args.valor_pago
    if args.valor_venda is not None:
        novos['valor_venda'] = args.valor_venda
    if args.tabela_nome is not None:
        novos['tabela_nome'] = args.tabela_nome
    if args.tabela_valor_kg is not None:
        novos['tabela_valor_kg'] = args.tabela_valor_kg

    if not novos:
        print(json.dumps({
            'sucesso': False,
            'erro': 'Nenhum valor para atualizar. Informe ao menos um: '
                    '--valor-cotado, --valor-considerado, --valor-pago, '
                    '--valor-venda, --tabela-nome, --tabela-valor-kg',
        }, ensure_ascii=False, indent=2))
        sys.exit(EXIT_USO)

    # Validacao: valores monetarios nao-negativos.
    for chave in ('valor_cotado', 'valor_considerado', 'valor_pago',
                  'valor_venda', 'tabela_valor_kg'):
        if chave in novos and novos[chave] < 0:
            print(json.dumps({
                'sucesso': False,
                'erro': f'{chave} nao pode ser negativo ({novos[chave]})',
            }, ensure_ascii=False, indent=2))
            sys.exit(EXIT_USO)

    from app import create_app
    app = create_app()

    with app.app_context():
        try:
            exit_code, resultado = atualizar_frete(
                args.frete_id, novos, user_id=args.user_id,
                confirmar=args.confirmar,
            )
        except Exception as e:
            from app import db
            db.session.rollback()
            print(json.dumps({
                'sucesso': False,
                'erro': f'{type(e).__name__}: {e}',
            }, ensure_ascii=False, indent=2))
            sys.exit(EXIT_FALHA)

        print(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))
        sys.exit(exit_code)


if __name__ == '__main__':
    main()
