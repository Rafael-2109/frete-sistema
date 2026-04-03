/**
 * BinPacker — Algoritmo 3D Guillotine para empacotamento de motos em bau de veiculo.
 *
 * Entrada: dimensoes do bau + lista de motos (modelo, dimensoes, quantidade).
 * Saida: posicoes 3D de cada moto colocada + lista de rejeitadas.
 *
 * Regras de orientacao:
 * - Comprimento da moto SEMPRE horizontal (eixos X ou Z do bau, nunca Y)
 * - Largura e altura intercambiaveis (moto pode ser deitada)
 * - Resultado: ate 4 orientacoes validas por moto
 *
 * Algoritmo: First Fit Decreasing (FFD) com subdivisao Guillotine.
 * Heuristica de posicionamento: Bottom-Left-Front (minimiza Y, depois Z, depois X).
 */
;(function () {
  'use strict';

  var MAX_ITEMS = 200;

  /**
   * Empacota motos dentro do bau.
   * @param {{w: number, d: number, h: number}} bay - Dimensoes do bau (comprimento, largura, altura) em cm
   * @param {Array<{id: number, nome: string, comprimento: number, largura: number, altura: number, qty: number, color: string}>} motoList
   * @returns {{placed: Array, rejected: Array, bay: Object, stats: Object}}
   */
  function pack(bay, motoList) {
    var items = expandAndSort(motoList);

    if (items.length > MAX_ITEMS) {
      items = items.slice(0, MAX_ITEMS);
    }

    // Lista de espacos livres — inicia com o bau inteiro
    var freeSpaces = [{ x: 0, y: 0, z: 0, w: bay.w, d: bay.d, h: bay.h }];
    var placed = [];
    var rejected = [];

    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      var orientations = getOrientations(item);
      var best = findBestFit(orientations, freeSpaces, bay);

      if (best) {
        placed.push({
          moto: item,
          x: best.space.x,
          y: best.space.y,
          z: best.space.z,
          w: best.ow,
          d: best.od,
          h: best.oh,
          orientacao: best.orientIdx,
        });
        freeSpaces = splitAndMerge(freeSpaces, best);
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
   * Expande a lista de motos (qty → itens individuais) e ordena por volume decrescente (FFD).
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
    // Ordenar por volume decrescente (maiores primeiro)
    items.sort(function (a, b) {
      return b.volume - a.volume;
    });
    return items;
  }

  /**
   * Gera orientacoes validas para um item.
   * Regra: comprimento da moto deve ficar horizontal (eixo X ou Z do bau).
   *
   * Convencao do bau:
   *   X = comprimento_bau (width)
   *   Z = largura_bau (depth)
   *   Y = altura_bau (height, vertical)
   *
   * As 4 orientacoes validas (C nunca no eixo Y):
   *   O1: C→X, L→Z, A→Y  (em pe, alinhada ao comprimento do bau)
   *   O2: C→X, A→Z, L→Y  (deitada, alinhada)
   *   O3: L→X, C→Z, A→Y  (em pe, rotacionada 90)
   *   O4: A→X, C→Z, L→Y  (deitada e rotacionada)
   */
  function getOrientations(item) {
    var C = item.comprimento;
    var L = item.largura;
    var A = item.altura;

    return [
      { ow: C, od: L, oh: A, idx: 0 }, // O1: em pe, alinhada
      { ow: C, od: A, oh: L, idx: 1 }, // O2: deitada, alinhada
      { ow: L, od: C, oh: A, idx: 2 }, // O3: em pe, rotacionada 90
      { ow: A, od: C, oh: L, idx: 3 }, // O4: deitada e rotacionada
    ];
  }

  /**
   * Encontra o melhor espaco livre para colocar o item.
   * Heuristica Bottom-Left-Front: minimiza Y (chao), depois Z, depois X.
   */
  function findBestFit(orientations, freeSpaces, bay) {
    var best = null;
    var bestScore = Infinity;

    for (var s = 0; s < freeSpaces.length; s++) {
      var space = freeSpaces[s];

      for (var o = 0; o < orientations.length; o++) {
        var orient = orientations[o];

        // Verifica se cabe no espaco livre
        if (
          orient.ow <= space.w + 0.01 &&
          orient.od <= space.d + 0.01 &&
          orient.oh <= space.h + 0.01
        ) {
          // Verifica se nao excede o bau
          if (
            space.x + orient.ow <= bay.w + 0.01 &&
            space.z + orient.od <= bay.d + 0.01 &&
            space.y + orient.oh <= bay.h + 0.01
          ) {
            // Score: prioriza chao (Y baixo), depois fundo (Z baixo), depois esquerda (X baixo)
            var score = space.y * 1000000 + space.z * 1000 + space.x;

            if (score < bestScore) {
              bestScore = score;
              best = {
                space: space,
                spaceIdx: s,
                ow: orient.ow,
                od: orient.od,
                oh: orient.oh,
                orientIdx: orient.idx,
              };
            }
          }
        }
      }
    }
    return best;
  }

  /**
   * Apos colocar um item, subdivide o espaco e faz merge de espacos adjacentes.
   *
   * Subdivisao Guillotine: divide o espaco ocupado em ate 3 sub-espacos
   * (direita, frente, cima) e remove o espaco original.
   */
  function splitAndMerge(freeSpaces, placement) {
    var sp = placement.space;
    var pw = placement.ow;
    var pd = placement.od;
    var ph = placement.oh;

    // Remover o espaco usado
    var newSpaces = [];
    for (var i = 0; i < freeSpaces.length; i++) {
      if (freeSpaces[i] !== sp) {
        newSpaces.push(freeSpaces[i]);
      }
    }

    // Sub-espaco 1: a DIREITA do item (mesmo Y e Z)
    var restW = sp.w - pw;
    if (restW > 1) {
      newSpaces.push({
        x: sp.x + pw,
        y: sp.y,
        z: sp.z,
        w: restW,
        d: sp.d,
        h: sp.h,
      });
    }

    // Sub-espaco 2: a FRENTE do item (mesmo X e Y, profundidade restante)
    var restD = sp.d - pd;
    if (restD > 1) {
      newSpaces.push({
        x: sp.x,
        y: sp.y,
        z: sp.z + pd,
        w: pw, // apenas a largura do item (nao toda a largura do espaco)
        d: restD,
        h: sp.h,
      });
    }

    // Sub-espaco 3: ACIMA do item (empilhamento)
    var restH = sp.h - ph;
    if (restH > 1) {
      newSpaces.push({
        x: sp.x,
        y: sp.y + ph,
        z: sp.z,
        w: pw, // apenas sobre o item
        d: pd,
        h: restH,
      });
    }

    return newSpaces;
  }

  // Exportar
  window.BinPacker = {
    pack: pack,
  };
})();
