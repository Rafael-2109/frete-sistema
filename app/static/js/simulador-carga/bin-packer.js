/**
 * BinPacker — Algoritmo 3D Maximal Rectangles para empacotamento de motos.
 *
 * Entrada: dimensoes do bau + lista de motos (modelo, dimensoes, quantidade).
 * Saida: posicoes 3D de cada moto colocada + lista de rejeitadas.
 *
 * Regras de orientacao:
 * - Comprimento da moto SEMPRE horizontal (eixos X ou Z do bau, nunca Y)
 * - Largura e altura intercambiaveis (moto pode ser deitada)
 * - Resultado: 4 orientacoes validas por moto
 *
 * Algoritmo: Maximal Rectangles com First Fit Decreasing (FFD).
 * Mantém espacos livres sobrepostos para maximizar aproveitamento.
 * Heuristica: Bottom-Left-Front (minimiza Y, depois Z, depois X).
 */
;(function () {
  'use strict';

  var MAX_ITEMS = 200;
  var EPS = 0.5; // tolerancia em cm para comparacoes de fit

  /**
   * Empacota motos dentro do bau.
   * @param {{w: number, d: number, h: number}} bay - Dimensoes do bau (comprimento, largura, altura) cm
   * @param {Array} motoList - [{id, nome, comprimento, largura, altura, qty, color, peso_medio}]
   * @returns {{placed: Array, rejected: Array, bay: Object, stats: Object}}
   */
  function pack(bay, motoList) {
    var items = expandAndSort(motoList);

    if (items.length > MAX_ITEMS) {
      items = items.slice(0, MAX_ITEMS);
    }

    // Lista de espacos livres maximos (podem se sobrepor)
    var freeSpaces = [{ x: 0, y: 0, z: 0, w: bay.w, d: bay.d, h: bay.h }];
    var placed = [];
    var rejected = [];

    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      var orientations = getOrientations(item);
      var best = findBestFit(orientations, freeSpaces, bay);

      if (best) {
        var placement = {
          moto: item,
          x: best.x,
          y: best.y,
          z: best.z,
          w: best.ow,
          d: best.od,
          h: best.oh,
          orientacao: best.orientIdx,
        };
        placed.push(placement);

        // Atualizar espacos livres: remover volume ocupado de todos os espacos
        freeSpaces = subtractBox(freeSpaces, placement);
      } else {
        rejected.push(item);
      }
    }

    // Estatisticas
    var bayVolume = bay.w * bay.d * bay.h;
    var usedVolume = 0;
    var totalPeso = 0;
    for (var j = 0; j < placed.length; j++) {
      usedVolume += placed[j].w * placed[j].d * placed[j].h;
      totalPeso += placed[j].moto.peso_medio || 0;
    }

    return {
      placed: placed,
      rejected: rejected,
      bay: bay,
      stats: {
        total: items.length,
        posicionadas: placed.length,
        rejeitadas: rejected.length,
        volumeOcupado: usedVolume,
        volumeTotal: bayVolume,
        percentualOcupacao: bayVolume > 0 ? Math.round((usedVolume / bayVolume) * 100) : 0,
        pesoTotal: Math.round(totalPeso * 100) / 100,
      },
    };
  }

  /**
   * Expande qty em itens individuais e ordena por volume decrescente (FFD).
   */
  function expandAndSort(motoList) {
    var items = [];
    for (var i = 0; i < motoList.length; i++) {
      var m = motoList[i];
      var qty = m.qty || 1;
      for (var q = 0; q < qty; q++) {
        items.push({
          id: m.id,
          nome: m.nome,
          comprimento: m.comprimento,
          largura: m.largura,
          altura: m.altura,
          peso_medio: m.peso_medio || 0,
          color: m.color || '#4a90d9',
          volume: m.comprimento * m.largura * m.altura,
        });
      }
    }
    items.sort(function (a, b) {
      return b.volume - a.volume;
    });
    return items;
  }

  /**
   * Gera 4 orientacoes validas (comprimento nunca no eixo Y/vertical).
   *
   * Convencao: ow→eixo X(largura bau), od→eixo Z(profundidade bau), oh→eixo Y(altura bau)
   */
  function getOrientations(item) {
    var C = item.comprimento;
    var L = item.largura;
    var A = item.altura;

    return [
      { ow: C, od: L, oh: A, idx: 0 }, // O1: em pe, C ao longo de X
      { ow: C, od: A, oh: L, idx: 1 }, // O2: deitada, C ao longo de X
      { ow: L, od: C, oh: A, idx: 2 }, // O3: em pe, C ao longo de Z
      { ow: A, od: C, oh: L, idx: 3 }, // O4: deitada, C ao longo de Z
    ];
  }

  /**
   * Encontra o melhor espaco para colocar o item.
   * Heuristica: Bottom-Left-Front — minimiza Y, depois Z, depois X.
   * Testa todas orientacoes em todos espacos livres.
   */
  function findBestFit(orientations, freeSpaces, bay) {
    var best = null;
    var bestScore = Infinity;

    for (var s = 0; s < freeSpaces.length; s++) {
      var sp = freeSpaces[s];

      for (var o = 0; o < orientations.length; o++) {
        var ori = orientations[o];

        // Cabe neste espaco?
        if (ori.ow > sp.w + EPS || ori.od > sp.d + EPS || ori.oh > sp.h + EPS) {
          continue;
        }

        // Cabe dentro do bau?
        if (sp.x + ori.ow > bay.w + EPS || sp.z + ori.od > bay.d + EPS || sp.y + ori.oh > bay.h + EPS) {
          continue;
        }

        // Score: prioriza chao (Y baixo), profundidade (Z baixo), esquerda (X baixo)
        var score = sp.y * 1e8 + sp.z * 1e4 + sp.x;

        if (score < bestScore) {
          bestScore = score;
          best = {
            x: sp.x,
            y: sp.y,
            z: sp.z,
            ow: ori.ow,
            od: ori.od,
            oh: ori.oh,
            orientIdx: ori.idx,
          };
        }
      }
    }
    return best;
  }

  /**
   * Maximal Rectangles: subtrai uma caixa de todos os espacos livres.
   *
   * Para cada espaco livre que intersecta a caixa colocada:
   *   - Remove o espaco original
   *   - Gera ate 6 novos espacos (um por face da intersecao)
   *   - Mantem apenas espacos que nao estao contidos em outros
   */
  function subtractBox(freeSpaces, box) {
    var bx1 = box.x, by1 = box.y, bz1 = box.z;
    var bx2 = box.x + box.w, by2 = box.y + box.h, bz2 = box.z + box.d;

    var newSpaces = [];

    for (var i = 0; i < freeSpaces.length; i++) {
      var sp = freeSpaces[i];
      var sx1 = sp.x, sy1 = sp.y, sz1 = sp.z;
      var sx2 = sp.x + sp.w, sy2 = sp.y + sp.h, sz2 = sp.z + sp.d;

      // Se nao intersecta, manter intacto
      if (bx1 >= sx2 - EPS || bx2 <= sx1 + EPS ||
          by1 >= sy2 - EPS || by2 <= sy1 + EPS ||
          bz1 >= sz2 - EPS || bz2 <= sz1 + EPS) {
        newSpaces.push(sp);
        continue;
      }

      // Intersecta — gerar ate 6 sub-espacos (faces livres)

      // Espaco a ESQUERDA da caixa (X < box.x)
      if (bx1 > sx1 + EPS) {
        newSpaces.push({ x: sx1, y: sy1, z: sz1, w: bx1 - sx1, d: sp.d, h: sp.h });
      }

      // Espaco a DIREITA da caixa (X > box.x + box.w)
      if (bx2 < sx2 - EPS) {
        newSpaces.push({ x: bx2, y: sy1, z: sz1, w: sx2 - bx2, d: sp.d, h: sp.h });
      }

      // Espaco ATRAS da caixa (Z < box.z)
      if (bz1 > sz1 + EPS) {
        newSpaces.push({ x: sx1, y: sy1, z: sz1, w: sp.w, d: bz1 - sz1, h: sp.h });
      }

      // Espaco na FRENTE da caixa (Z > box.z + box.d)
      if (bz2 < sz2 - EPS) {
        newSpaces.push({ x: sx1, y: sy1, z: bz2, w: sp.w, d: sz2 - bz2, h: sp.h });
      }

      // Espaco ABAIXO da caixa (Y < box.y) — raro, mas possivel com empilhamento
      if (by1 > sy1 + EPS) {
        newSpaces.push({ x: sx1, y: sy1, z: sz1, w: sp.w, d: sp.d, h: by1 - sy1 });
      }

      // Espaco ACIMA da caixa (Y > box.y + box.h) — empilhamento
      if (by2 < sy2 - EPS) {
        newSpaces.push({ x: sx1, y: by2, z: sz1, w: sp.w, d: sp.d, h: sy2 - by2 });
      }
    }

    // Remover espacos muito pequenos (< 10cm em qualquer dimensao)
    var filtered = [];
    for (var f = 0; f < newSpaces.length; f++) {
      var ns = newSpaces[f];
      if (ns.w >= 10 && ns.d >= 10 && ns.h >= 10) {
        filtered.push(ns);
      }
    }

    // Remover espacos contidos em outros (manter apenas maximos)
    return removeContained(filtered);
  }

  /**
   * Remove espacos que estao totalmente contidos dentro de outro espaco.
   * Garante que so mantemos "maximal rectangles".
   */
  function removeContained(spaces) {
    if (spaces.length <= 1) return spaces;

    var keep = [];
    for (var i = 0; i < spaces.length; i++) {
      var contained = false;
      var a = spaces[i];

      for (var j = 0; j < spaces.length; j++) {
        if (i === j) continue;
        var b = spaces[j];

        // a esta contido em b?
        if (a.x >= b.x - EPS && a.y >= b.y - EPS && a.z >= b.z - EPS &&
            a.x + a.w <= b.x + b.w + EPS &&
            a.y + a.h <= b.y + b.h + EPS &&
            a.z + a.d <= b.z + b.d + EPS) {
          contained = true;
          break;
        }
      }

      if (!contained) {
        keep.push(a);
      }
    }
    return keep;
  }

  // Exportar
  window.BinPacker = {
    pack: pack,
  };
})();
