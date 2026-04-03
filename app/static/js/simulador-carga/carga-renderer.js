/**
 * CargaRenderer — Renderiza cena Three.js com bau de veiculo e motos empacotadas.
 *
 * Responsabilidades:
 * - Criar e gerenciar scene, camera, renderer, OrbitControls
 * - Renderizar bau (wireframe) + motos (caixas coloridas)
 * - Vistas preset: Frontal, Lateral, Topo, 3D
 * - Adaptacao dark/light mode via themechange event
 * - Cleanup de memoria via dispose()
 */
;(function () {
  'use strict';

  // Paleta de cores para diferenciar modelos de moto
  var PALETTE = [
    0x4a90d9, // azul
    0xe8854c, // laranja
    0x67c26a, // verde
    0xb06fc4, // roxo
    0xe8cc4c, // amarelo
    0x4cc4c4, // ciano
    0xe85c6e, // rosa
    0x8a9bb0, // cinza-azulado
  ];

  // Escala para converter cm → unidades 3D (1cm = 0.01 unidades, mas usamos 1:1 e ajustamos camera)
  var SCALE = 0.01; // 1cm = 0.01 unidades Three.js

  /**
   * @param {HTMLElement} container - Elemento container para o canvas
   * @param {string} theme - 'dark' ou 'light'
   */
  function CargaRenderer(container, theme) {
    this.container = container;
    this.theme = theme || 'dark';
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.controls = null;
    this.animationId = null;
    this.bayGroup = null;
    this.motosGroup = null;
    this._disposed = false;

    this._init();
  }

  CargaRenderer.prototype._init = function () {
    var width = this.container.clientWidth || 800;
    var height = this.container.clientHeight || 500;

    // Scene
    this.scene = new THREE.Scene();

    // Camera — posicao inicial conservadora, sera ajustada no render()
    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.01, 500);
    this.camera.position.set(5, 4, 8);
    this.camera.lookAt(0, 0, 0);

    // Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this._updateClearColor();
    this.container.appendChild(this.renderer.domElement);

    // OrbitControls
    if (THREE.OrbitControls) {
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.1;
      this.controls.minDistance = 0.5;
      this.controls.maxDistance = 200;
      this.controls.target.set(0, 0, 0);
      this.controls.update();
    }

    // Luzes
    var ambientLight = new THREE.AmbientLight(0xffffff, 0.65);
    this.scene.add(ambientLight);

    var dirLight = new THREE.DirectionalLight(0xffffff, 0.7);
    dirLight.position.set(5, 10, 7);
    this.scene.add(dirLight);

    var fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
    fillLight.position.set(-5, 3, -5);
    this.scene.add(fillLight);

    // Grupos
    this.bayGroup = new THREE.Group();
    this.scene.add(this.bayGroup);
    this.motosGroup = new THREE.Group();
    this.scene.add(this.motosGroup);

    // Grid — sera recriado no render() para acompanhar o tamanho do bau
    this._gridHelper = null;

    // Events
    this._onResize = this._handleResize.bind(this);
    this._onThemeChange = this._handleThemeChange.bind(this);
    window.addEventListener('resize', this._onResize);
    document.addEventListener('themechange', this._onThemeChange);

    // Animation loop
    this._animate();
  };

  CargaRenderer.prototype._animate = function () {
    if (this._disposed) return;
    this.animationId = requestAnimationFrame(this._animate.bind(this));
    if (this.controls) this.controls.update();
    this.renderer.render(this.scene, this.camera);
  };

  CargaRenderer.prototype._handleResize = function () {
    if (this._disposed) return;
    var width = this.container.clientWidth;
    var height = this.container.clientHeight || 500;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  };

  CargaRenderer.prototype._handleThemeChange = function (e) {
    if (this._disposed) return;
    this.theme = (e.detail && e.detail.theme) || 'dark';
    this._updateClearColor();
    this._updateWireframeColors();
  };

  CargaRenderer.prototype._updateClearColor = function () {
    if (this.theme === 'dark') {
      this.renderer.setClearColor(0x0d1117, 1);
    } else {
      this.renderer.setClearColor(0xf0f2f5, 1);
    }
  };

  CargaRenderer.prototype._updateWireframeColors = function () {
    if (!this._bayEdges) return;
    var color = this.theme === 'dark' ? 0x58a6ff : 0x333333;
    this._bayEdges.material.color.setHex(color);
  };

  /**
   * Renderiza o resultado do bin-packing.
   * @param {Object} result - Saida de BinPacker.pack()
   * @param {Object} bay - {w, d, h} dimensoes do bau em cm
   * @param {Object} colorMap - {modelo_id: '#hex'} mapa de cores por modelo
   */
  CargaRenderer.prototype.render = function (result, bay, colorMap) {
    // Limpar cena anterior
    this._clearGroup(this.bayGroup);
    this._clearGroup(this.motosGroup);
    this._bayEdges = null;

    // Remover grid antigo
    if (this._gridHelper) {
      this.scene.remove(this._gridHelper);
      this._gridHelper.geometry.dispose();
      this._gridHelper.material.dispose();
      this._gridHelper = null;
    }

    if (!bay || !bay.w || !bay.d || !bay.h) return;

    var bw = bay.w * SCALE;
    var bd = bay.d * SCALE;
    var bh = bay.h * SCALE;

    // Centro do bau — usamos offset para centralizar a cena na origem
    var cx = bw / 2;
    var cy = bh / 2;
    var cz = bd / 2;

    // Salvar centro para uso em setView
    this._bayCenter = { x: cx, y: cy, z: cz };
    this._baySize = { w: bw, d: bd, h: bh };

    // --- Grid (proporcional ao bau, centrado) ---
    var gridSize = Math.max(bw, bd) * 1.3;
    var gridDiv = Math.max(10, Math.round(gridSize / 0.5));
    var gridHelper = new THREE.GridHelper(gridSize, gridDiv, 0x444444, 0x282828);
    gridHelper.position.set(cx, -0.001, cz);
    this.scene.add(gridHelper);
    this._gridHelper = gridHelper;

    // --- Bau (wireframe) ---
    var bayGeom = new THREE.BoxGeometry(bw, bh, bd);
    var edgesGeom = new THREE.EdgesGeometry(bayGeom);
    var edgeColor = this.theme === 'dark' ? 0x58a6ff : 0x333333;
    var edgesMat = new THREE.LineBasicMaterial({ color: edgeColor, linewidth: 2 });
    var bayEdges = new THREE.LineSegments(edgesGeom, edgesMat);
    bayEdges.position.set(cx, cy, cz);
    this.bayGroup.add(bayEdges);
    this._bayEdges = bayEdges;

    // Chao do bau (semi-transparente)
    var floorGeom = new THREE.PlaneGeometry(bw, bd);
    var floorMat = new THREE.MeshBasicMaterial({
      color: this.theme === 'dark' ? 0x1a2332 : 0xdde1e6,
      transparent: true,
      opacity: 0.25,
      side: THREE.DoubleSide,
    });
    var floor = new THREE.Mesh(floorGeom, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(cx, 0.002, cz);
    this.bayGroup.add(floor);

    // --- Motos (caixas coloridas) ---
    if (result && result.placed) {
      for (var i = 0; i < result.placed.length; i++) {
        var p = result.placed[i];
        var mw = p.w * SCALE;
        var mh = p.h * SCALE;
        var md = p.d * SCALE;

        var colorHex = this._resolveColor(p.moto, colorMap, i);

        var boxGeom = new THREE.BoxGeometry(mw, mh, md);
        var boxMat = new THREE.MeshPhongMaterial({
          color: colorHex,
          transparent: true,
          opacity: 0.82,
          shininess: 30,
        });
        var mesh = new THREE.Mesh(boxGeom, boxMat);
        mesh.position.set(
          p.x * SCALE + mw / 2,
          p.y * SCALE + mh / 2,
          p.z * SCALE + md / 2
        );
        this.motosGroup.add(mesh);

        // Wireframe da moto para melhor visibilidade
        var wireGeom = new THREE.EdgesGeometry(boxGeom);
        var wireMat = new THREE.LineBasicMaterial({
          color: 0x000000,
          transparent: true,
          opacity: 0.15,
        });
        var wire = new THREE.LineSegments(wireGeom, wireMat);
        wire.position.copy(mesh.position);
        this.motosGroup.add(wire);
      }
    }

    // Ajustar camera para enquadrar o bau inteiro
    this._fitCamera(bw, bh, bd, cx, cy, cz);
  };

  CargaRenderer.prototype._resolveColor = function (moto, colorMap, index) {
    if (colorMap && moto.id && colorMap[moto.id]) {
      var hex = colorMap[moto.id];
      if (typeof hex === 'string') {
        return parseInt(hex.replace('#', ''), 16);
      }
      return hex;
    }
    // Fallback: paleta por modelo_id
    var paletteIdx = (moto.id || index) % PALETTE.length;
    return PALETTE[paletteIdx];
  };

  /**
   * Posiciona a camera para enquadrar o bau completo.
   * Usa a diagonal do bau + FOV para calcular a distancia minima.
   */
  CargaRenderer.prototype._fitCamera = function (bw, bh, bd, cx, cy, cz) {
    // Distancia para enquadrar toda a diagonal do bau
    var diagonal = Math.sqrt(bw * bw + bh * bh + bd * bd);
    var fovRad = this.camera.fov * Math.PI / 180;
    var dist = (diagonal / 2) / Math.tan(fovRad / 2) * 1.1;

    // Posicao 3D isometrica (frente-direita-acima)
    this.camera.position.set(
      cx + dist * 0.6,
      cy + dist * 0.45,
      cz + dist * 0.7
    );

    if (this.controls) {
      this.controls.target.set(cx, cy * 0.5, cz);
      this.controls.update();
    } else {
      this.camera.lookAt(cx, cy * 0.5, cz);
    }
  };

  /**
   * Muda para uma vista preset.
   * @param {'3d'|'front'|'side'|'top'} preset
   * @param {{w: number, d: number, h: number}} bay - Dimensoes do bau em cm
   */
  CargaRenderer.prototype.setView = function (preset, bay) {
    if (!this._bayCenter || !this._baySize) return;

    var cx = this._bayCenter.x;
    var cy = this._bayCenter.y;
    var cz = this._bayCenter.z;
    var bw = this._baySize.w;
    var bd = this._baySize.d;
    var bh = this._baySize.h;

    var diagonal = Math.sqrt(bw * bw + bh * bh + bd * bd);
    var fovRad = this.camera.fov * Math.PI / 180;
    var dist = (diagonal / 2) / Math.tan(fovRad / 2) * 1.1;

    var pos;
    var lookAt = { x: cx, y: cy * 0.5, z: cz };

    switch (preset) {
      case 'front':
        pos = { x: cx, y: cy, z: cz + dist };
        lookAt = { x: cx, y: cy, z: cz };
        break;
      case 'side':
        pos = { x: cx + dist, y: cy, z: cz };
        lookAt = { x: cx, y: cy, z: cz };
        break;
      case 'top':
        pos = { x: cx, y: dist, z: cz + 0.01 };
        lookAt = { x: cx, y: 0, z: cz };
        break;
      case '3d':
      default:
        pos = { x: cx + dist * 0.6, y: cy + dist * 0.45, z: cz + dist * 0.7 };
        lookAt = { x: cx, y: cy * 0.5, z: cz };
        break;
    }

    this._animateCamera(pos, lookAt);
  };

  CargaRenderer.prototype._animateCamera = function (targetPos, targetLook) {
    var self = this;
    var startPos = {
      x: this.camera.position.x,
      y: this.camera.position.y,
      z: this.camera.position.z,
    };
    var startTarget = this.controls
      ? {
          x: this.controls.target.x,
          y: this.controls.target.y,
          z: this.controls.target.z,
        }
      : targetLook;

    var start = performance.now();
    var duration = 600; // ms

    function easeInOutCubic(t) {
      return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    function step(now) {
      if (self._disposed) return;
      var elapsed = now - start;
      var t = Math.min(elapsed / duration, 1);
      var e = easeInOutCubic(t);

      self.camera.position.set(
        startPos.x + (targetPos.x - startPos.x) * e,
        startPos.y + (targetPos.y - startPos.y) * e,
        startPos.z + (targetPos.z - startPos.z) * e
      );

      if (self.controls) {
        self.controls.target.set(
          startTarget.x + (targetLook.x - startTarget.x) * e,
          startTarget.y + (targetLook.y - startTarget.y) * e,
          startTarget.z + (targetLook.z - startTarget.z) * e
        );
        self.controls.update();
      }

      if (t < 1) {
        requestAnimationFrame(step);
      }
    }

    requestAnimationFrame(step);
  };

  CargaRenderer.prototype._clearGroup = function (group) {
    while (group.children.length > 0) {
      var child = group.children[0];
      if (child.geometry) child.geometry.dispose();
      if (child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach(function (m) { m.dispose(); });
        } else {
          child.material.dispose();
        }
      }
      group.remove(child);
    }
  };

  /**
   * Libera todos os recursos (chamar ao sair da pagina).
   */
  CargaRenderer.prototype.dispose = function () {
    this._disposed = true;
    if (this.animationId) cancelAnimationFrame(this.animationId);
    window.removeEventListener('resize', this._onResize);
    document.removeEventListener('themechange', this._onThemeChange);

    this._clearGroup(this.bayGroup);
    this._clearGroup(this.motosGroup);

    if (this.controls) this.controls.dispose();
    if (this.renderer) {
      this.renderer.dispose();
      if (this.renderer.domElement && this.renderer.domElement.parentNode) {
        this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
      }
    }
    this.scene = null;
    this.camera = null;
    this.renderer = null;
  };

  // Exportar
  window.CargaRenderer = CargaRenderer;
})();
