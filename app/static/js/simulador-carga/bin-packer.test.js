/**
 * Testes do BinPacker (simulador 3D de carga de motos).
 *
 * Sem framework — Node puro. Rodar:
 *   node app/static/js/simulador-carga/bin-packer.test.js
 * Exit 0 = tudo verde; exit 1 = alguma falha.
 *
 * Carrega o fonte real (IIFE que seta window.BinPacker) num escopo com `window`.
 *
 * Dados canonicos = caso real reportado (bau override 630x240x230, sliders 10%/60/150).
 * O algoritmo original (Best Short Side Fit) entregava 47% de ocupacao com 29 motos
 * rejeitadas no Caso 1 e era instavel (1 moto a menos na entrada -> 20 a mais cabendo).
 */
'use strict';
const fs = require('fs');
const path = require('path');

function loadPacker() {
  const code = fs.readFileSync(path.join(__dirname, 'bin-packer.js'), 'utf8');
  const window = {};
  eval(code); // seta window.BinPacker
  return window.BinPacker;
}

const BinPacker = loadPacker();
const BAY = { w: 630, d: 240, h: 230 };
const OPT = { minSupport: 0.10, maxOverhang: 60, maxGap: 150 };

function modelos(bigTriQty) {
  return [
    { id: 1, nome: 'FANTON',   comprimento: 160, largura: 38, altura: 75, peso_medio: 136.8,   qty: 9 },
    { id: 2, nome: 'X11 MINI', comprimento: 141, largura: 39, altura: 65, peso_medio: 107.2,   qty: 22 },
    { id: 3, nome: 'X12',      comprimento: 148, largura: 37, altura: 64, peso_medio: 105.1,   qty: 18 },
    { id: 4, nome: 'JET',      comprimento: 168, largura: 42, altura: 84, peso_medio: 177.811, qty: 6 },
    { id: 5, nome: 'BOB',      comprimento: 142, largura: 32, altura: 75, peso_medio: 102.24,  qty: 3 },
    { id: 6, nome: 'BIG TRI',  comprimento: 137, largura: 76, altura: 61, peso_medio: 190.5,   qty: bigTriQty },
  ];
}

// ---- mini runner ----
let failures = 0;
function test(name, fn) {
  try { fn(); console.log('  ✓ ' + name); }
  catch (e) { failures++; console.log('  ✗ ' + name + '\n      ' + e.message); }
}
function assert(cond, msg) { if (!cond) throw new Error(msg); }

// ---- contrato de qualidade do empacotamento ----

test('CASO 1 (BIG TRI 6x): ocupa >=70% e rejeita no maximo 3', () => {
  const s = BinPacker.pack(BAY, modelos(6), OPT).stats;
  assert(s.percentualOcupacao >= 70, `ocupacao ${s.percentualOcupacao}% < 70%`);
  assert(s.rejeitadas <= 3, `rejeitadas ${s.rejeitadas} > 3`);
});

test('CASO 2 (BIG TRI 5x): ocupa >=70% e rejeita no maximo 3', () => {
  const s = BinPacker.pack(BAY, modelos(5), OPT).stats;
  assert(s.percentualOcupacao >= 70, `ocupacao ${s.percentualOcupacao}% < 70%`);
  assert(s.rejeitadas <= 3, `rejeitadas ${s.rejeitadas} > 3`);
});

test('estabilidade: adicionar 1 BIG TRI nunca reduz o total posicionado (monotonia)', () => {
  let prev = -1, prevBt = -1;
  for (let bt = 2; bt <= 8; bt++) {
    const pos = BinPacker.pack(BAY, modelos(bt), OPT).stats.posicionadas;
    if (prev >= 0) {
      assert(pos >= prev, `BIG TRI ${bt}: posic=${pos} caiu vs ${prevBt}: posic=${prev}`);
    }
    prev = pos; prevBt = bt;
  }
});

// ---- invariantes fisicos (devem valer SEMPRE) ----

function place(bt) { return BinPacker.pack(BAY, modelos(bt), OPT).placed; }

test('invariante: nenhuma caixa se interpenetra com outra', () => {
  const p = place(6); const E = 0.1;
  for (let i = 0; i < p.length; i++) for (let j = i + 1; j < p.length; j++) {
    const a = p[i], b = p[j];
    const overlap = a.x < b.x + b.w - E && a.x + a.w > b.x + E &&
                    a.y < b.y + b.h - E && a.y + a.h > b.y + E &&
                    a.z < b.z + b.d - E && a.z + a.d > b.z + E;
    assert(!overlap, `sobreposicao entre ${a.moto.nome}@(${a.x},${a.y},${a.z}) e ${b.moto.nome}@(${b.x},${b.y},${b.z})`);
  }
});

test('invariante: toda caixa cabe dentro do bau', () => {
  const p = place(6); const E = 0.1;
  p.forEach(b => {
    assert(b.x >= -E && b.x + b.w <= BAY.w + E, `${b.moto.nome} estoura X`);
    assert(b.y >= -E && b.y + b.h <= BAY.h + E, `${b.moto.nome} estoura Y`);
    assert(b.z >= -E && b.z + b.d <= BAY.d + E, `${b.moto.nome} estoura Z`);
  });
});

test('invariante: horizontalidade — comprimento nunca na vertical (altura = largura ou altura da moto)', () => {
  const p = place(6); const E = 0.5;
  p.forEach(b => {
    const m = b.moto;
    const ok = Math.abs(b.h - m.largura) < E || Math.abs(b.h - m.altura) < E;
    assert(ok, `${m.nome}: altura empilhada ${b.h} == comprimento ${m.comprimento} (de pe!)`);
  });
});

test('invariante: caixa empilhada (y>0) nao flutua — ha caixa logo abaixo com apoio', () => {
  const p = place(6); const E = 2, F = 0.1;
  p.filter(b => b.y > 0.1).forEach(b => {
    const apoiada = p.some(o => o !== b &&
      Math.abs((o.y + o.h) - b.y) <= E &&
      Math.min(b.x + b.w, o.x + o.w) - Math.max(b.x, o.x) > F &&
      Math.min(b.z + b.d, o.z + o.d) - Math.max(b.z, o.z) > F);
    assert(apoiada, `${b.moto.nome}@y=${b.y} flutua (sem caixa abaixo)`);
  });
});

test('degenerado: 1 moto fica no chao (y=0)', () => {
  const r = BinPacker.pack(BAY, [{ id: 1, nome: 'FANTON', comprimento: 160, largura: 38, altura: 75, peso_medio: 136.8, qty: 1 }], OPT);
  assert(r.stats.posicionadas === 1, 'deveria posicionar 1');
  assert(Math.abs(r.placed[0].y) < 0.1, `y=${r.placed[0].y} (esperado 0)`);
});

// ---- empacotamento OTIMIZADO (metaheuristica Simulated Annealing sobre a ordem) ----

test('packOptimized CASO 1: acomoda todas as 64 motos (cabe tudo)', () => {
  const s = BinPacker.packOptimized(BAY, modelos(6), OPT).stats;
  assert(s.posicionadas === s.total, `posicionou ${s.posicionadas}/${s.total}`);
});

test('packOptimized CASO 2: acomoda todas as 63 motos', () => {
  const s = BinPacker.packOptimized(BAY, modelos(5), OPT).stats;
  assert(s.posicionadas === s.total, `posicionou ${s.posicionadas}/${s.total}`);
});

test('packOptimized e deterministico (mesmos inputs -> mesmo resultado)', () => {
  const a = BinPacker.packOptimized(BAY, modelos(6), OPT).stats;
  const b = BinPacker.packOptimized(BAY, modelos(6), OPT).stats;
  assert(a.posicionadas === b.posicionadas && a.volumeOcupado === b.volumeOcupado,
    `divergiu: ${a.posicionadas}/${a.volumeOcupado} vs ${b.posicionadas}/${b.volumeOcupado}`);
});

test('packOptimized nunca posiciona menos que pack() (passada unica)', () => {
  const base = BinPacker.pack(BAY, modelos(6), OPT).stats.posicionadas;
  const opt = BinPacker.packOptimized(BAY, modelos(6), OPT).stats.posicionadas;
  assert(opt >= base, `otimizado ${opt} < base ${base}`);
});

test('packOptimized mantem invariantes fisicos (sem sobreposicao, dentro do bau)', () => {
  const p = BinPacker.packOptimized(BAY, modelos(6), OPT).placed; const E = 0.1;
  for (let i = 0; i < p.length; i++) for (let j = i + 1; j < p.length; j++) {
    const a = p[i], b = p[j];
    const overlap = a.x < b.x + b.w - E && a.x + a.w > b.x + E &&
                    a.y < b.y + b.h - E && a.y + a.h > b.y + E &&
                    a.z < b.z + b.d - E && a.z + a.d > b.z + E;
    assert(!overlap, `sobreposicao ${a.moto.nome} x ${b.moto.nome}`);
  }
  p.forEach(b => { assert(b.x + b.w <= BAY.w + E && b.y + b.h <= BAY.h + E && b.z + b.d <= BAY.d + E, `${b.moto.nome} fora do bau`); });
});

// ---- Conservas Nacom: multi-slab + pallets ----

test('multi-slab: moto posicionada expoe slabs absolutos coerentes', () => {
  const r = BinPacker.pack({ w: 200, d: 200, h: 200 },
    [{ id: 1, nome: 'M', comprimento: 100, largura: 40, altura: 50, peso_medio: 100, qty: 1 }]);
  assert(r.stats.posicionadas === 1, 'deveria posicionar 1');
  const p = r.placed[0];
  assert(Array.isArray(p.slabs) && p.slabs.length === 1, 'moto tem 1 slab');
  const s = p.slabs[0];
  assert(s.w === p.w && s.d === p.d && s.h === p.h, 'slab = footprint da moto');
  assert(s.x === p.x && s.y === p.y && s.z === p.z, 'slab na posicao da moto');
});

function pallet(mx, my, altMerc, id) {
  return { tipo: 'pallet', id: id, nome: id,
           base_x: 100, base_y: 120, altura_estrado: 15,
           merc_x: mx, merc_y: my, altura_merc: altMerc,
           altura_total: 15 + altMerc, comprimento: 100, largura: 120, altura: 15 + altMerc,
           peso_medio: 100, qty: 1 };
}

test('caminho critico: pallets 104 e 90 cabem encostados (media 97 < 100)', () => {
  const r = BinPacker.pack({ w: 200, d: 130, h: 250 },
    [pallet(104, 104, 100, 'A'), pallet(90, 90, 100, 'B')]);
  assert(r.stats.posicionadas === 2, `esperava 2, veio ${r.stats.posicionadas}`);
});

test('caminho critico: dois pallets 104 NAO cabem lado a lado em bau de 200 (baixo)', () => {
  // bau baixo (h=200) nao comporta empilhar 2 pallets (115+115=230) -> isola o
  // efeito horizontal: 104+104 nao interdigitam (media 104 > 100) -> so 1 cabe.
  const r = BinPacker.pack({ w: 200, d: 130, h: 200 },
    [pallet(104, 104, 100, 'A'), pallet(104, 104, 100, 'B')]);
  assert(r.stats.posicionadas === 1, `esperava 1, veio ${r.stats.posicionadas}`);
});

test('pallet tem orientacao unica (estrado no chao) e 2 slabs', () => {
  const r = BinPacker.pack({ w: 200, d: 200, h: 250 }, [pallet(104, 104, 100, 'A')]);
  const p = r.placed[0];
  assert(p.slabs.length === 2, '2 slabs (estrado + coluna)');
  assert(p.slabs[0].y === 0 && p.slabs[0].h === 15, 'estrado em Y 0..15');
  assert(p.slabs[1].y === 15, 'coluna comeca em Y=15');
});

test('Nacom embaixo: nenhuma moto fica sob um pallet', () => {
  const bay = { w: 300, d: 130, h: 250 };
  const items = [
    pallet(90, 110, 120, 'P1'),
    { id: 2, nome: 'M', tipo: 'moto', comprimento: 80, largura: 40, altura: 50, peso_medio: 150, qty: 4 },
  ];
  const r = BinPacker.pack(bay, items);
  const pallets = r.placed.filter(p => p.moto.tipo === 'pallet');
  const motos = r.placed.filter(p => p.moto.tipo !== 'pallet');
  motos.forEach(m => {
    pallets.forEach(p => {
      const sobrepoeXZ = (p.x < m.x + m.w && p.x + p.w > m.x &&
                          p.z < m.z + m.d && p.z + p.d > m.z);
      assert(!(sobrepoeXZ && p.y >= m.y + m.h - 0.1),
        'pallet nao pode estar acima de uma moto');
    });
  });
});

test('pallet sobre pallet: OFF mantem todos no chao', () => {
  const bay = { w: 110, d: 130, h: 400 };
  const r = BinPacker.pack(bay, [pallet(90, 110, 120, 'A'), pallet(90, 110, 120, 'B')]);
  // base 100x120 so cabe 1 no chao desse bau estreito; sem empilhar -> 1
  assert(r.stats.posicionadas === 1, `OFF esperava 1, veio ${r.stats.posicionadas}`);
});

test('pallet sobre pallet: ON empilha (+15cm estrado)', () => {
  const bay = { w: 110, d: 130, h: 400 };
  const r = BinPacker.pack(bay, [pallet(90, 110, 120, 'A'), pallet(90, 110, 120, 'B')],
    { palletSobrePallet: true, minSupport: 0.5, maxOverhang: 20, maxGap: 60 });
  assert(r.stats.posicionadas === 2, `ON esperava 2, veio ${r.stats.posicionadas}`);
  const ys = r.placed.map(p => p.y).sort((a, b) => a - b);
  assert(ys[0] === 0, 'um no chao');
  assert(ys[1] >= 135 - 0.1, 'outro empilhado acima do topo (15+120)');
});

console.log(failures === 0 ? '\nTODOS OS TESTES PASSARAM' : `\n${failures} TESTE(S) FALHARAM`);
process.exit(failures === 0 ? 0 : 1);
