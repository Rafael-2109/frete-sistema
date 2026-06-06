#!/usr/bin/env python3
"""KIT DE VERIFICACAO (nao e teste pytest — nome sem prefixo test_).

Compara o WRAPPER NOVO (worktree) vs o CLI ANTIGO (repo principal, ainda intacto), ambos via
subprocess, no MESMO banco local. Prova que o contrato CLI (flags + JSON) nao regrediu.
Divergencia esperada: cidade (accent — novo casa, antigo nao).

Uso:
    cd /home/rafaelnascimento/projetos/frete_sistema_resolvedores
    source .venv/bin/activate
    python tests/resolvedores/comparar_antigo_vs_novo.py
"""
import json
import subprocess
import sys
import os

PRINC = '/home/rafaelnascimento/projetos/frete_sistema'
WT = '/home/rafaelnascimento/projetos/frete_sistema_resolvedores'
S_ANT = os.path.join(PRINC, '.claude/skills/resolvendo-entidades/scripts')
S_NOV = os.path.join(WT, '.claude/skills/resolvendo-entidades/scripts')
PY = sys.executable

os.chdir(WT)
sys.path.insert(0, WT)
from app import create_app  # noqa: E402
app = create_app()


def run(scriptdir, cwd, script, args):
    p = subprocess.run([PY, os.path.join(scriptdir, script)] + args,
                       capture_output=True, text=True, cwd=cwd)
    out = p.stdout
    i = out.find('{')
    if i < 0:
        return {'__err__': p.stderr[-200:]}
    try:
        return json.loads(out[i:])
    except Exception as e:
        return {'__err__': str(e)}


def ids(obj, key, idk):
    out = set()
    for it in (obj.get(key) or []):
        out.add(tuple(it.get(k) for k in idk) if isinstance(it, dict) else it)
    return out


def cmp(nome, script, args, lista, idk, esperado_difere=False):
    ant = run(S_ANT, PRINC, script, args)
    nov = run(S_NOV, WT, script, args)
    ka, kn = set(ant.keys()), set(nov.keys())
    ia, ino = ids(ant, lista, idk), ids(nov, lista, idk)
    suc_ok = ant.get('sucesso') == nov.get('sucesso')
    key_ok = ka == kn
    ids_ok = ia == ino
    tag = 'OK' if (suc_ok and key_ok and ids_ok) else ('DIFERE-ESPERADO' if esperado_difere else '*** REGRESSAO ***')
    print(f"  [{tag}] {nome}: sucesso {ant.get('sucesso')}->{nov.get('sucesso')} "
          f"| chaves {'iguais' if key_ok else f'DIFF ant-only={sorted(ka-kn)} nov-only={sorted(kn-ka)}'} "
          f"| {lista} ant={len(ia)} nov={len(ino)} comum={len(ia & ino)}")


with app.app_context():
    from sqlalchemy import text
    from app import db
    num = db.session.execute(text("SELECT num_pedido FROM carteira_principal WHERE qtd_saldo_produto_pedido>0 LIMIT 1")).scalar()
    nome = db.session.execute(text("SELECT raz_social_red FROM carteira_principal WHERE qtd_saldo_produto_pedido>0 AND raz_social_red IS NOT NULL LIMIT 1")).scalar()
    tr = db.session.execute(text("SELECT razao_social FROM transportadoras WHERE razao_social IS NOT NULL AND length(razao_social)>=5 LIMIT 1")).scalar()

print("## PRODUTO (hibrida default + texto)")
for t in ['palmito', 'azeitona', 'AZ VF', 'mezzani', 'palmito campo belo']:
    cmp(f"produto '{t}'", 'resolver_produto.py', ['--termo', t], 'produtos', ('cod_produto',))
for t in ['palmito', 'azeitona', 'AZ VF']:
    cmp(f"produto '{t}' [texto]", 'resolver_produto.py', ['--termo', t, '--modo', 'texto'], 'produtos', ('cod_produto',))
print("## CIDADE (accent — divergencia esperada)")
for t in ['itanhaem', 'sao paulo']:
    cmp(f"cidade '{t}' carteira", 'resolver_cidade.py', ['--cidade', t, '--fonte', 'carteira'], 'cidades_encontradas', ('cidade', 'uf'), esperado_difere=True)
print("## PEDIDO")
cmp(f"pedido '{num}'", 'resolver_pedido.py', ['--termo', str(num), '--fonte', 'carteira'], 'pedidos', ('num_pedido',))
cmp("pedido 'atacadao 183'", 'resolver_pedido.py', ['--termo', 'atacadao 183', '--fonte', 'carteira'], 'pedidos', ('num_pedido',))
print("## GRUPO / UF / CLIENTE / TRANSPORTADORA")
cmp("grupo atacadao entregas", 'resolver_grupo.py', ['--grupo', 'atacadao'], 'clientes', ('cnpj', 'nome'))
cmp("uf SP carteira", 'resolver_uf.py', ['--uf', 'SP', '--fonte', 'carteira'], 'clientes', ('cnpj', 'nome'))
cmp(f"cliente '{nome}' carteira", 'resolver_cliente.py', ['--termo', str(nome), '--fonte', 'carteira'], 'clientes', ('cnpj', 'nome'))
cmp(f"transp '{str(tr)[:5]}'", 'resolver_transportadora.py', ['--termo', str(tr)[:5]], 'transportadoras', ('id', 'razao_social'))
print("# FIM — se tudo [OK] exceto cidade [DIFERE-ESPERADO], ZERO regressao.")
