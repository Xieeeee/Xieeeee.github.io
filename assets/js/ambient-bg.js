// Ambient hero background: a slow WebGL2 "warp" shader plus a faint node grid.
// Ported from the deepseek.com landing hero. Colors come from CSS variables
// (--ambient-shader-colors, --ambient-grid-rgb, --ambient-grid-alpha) so the
// light and dark themes each get their own greys.
(function () {
  var layer = document.querySelector(".ambient-layer");
  if (!layer) return;
  var shaderCanvas = layer.querySelector(".ambient-shader");
  var gridCanvas = layer.querySelector(".ambient-grid");

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Shader settings (deepseek.com uses the same values with a blue first color)
  var SETTINGS = {
    speed: 14,
    distortion: 20,
    swirl: 12,
    swirlIterations: 8,
    scale: 0.35,
    rotation: -5,
    proportion: 50,
    softness: 100,
    shapeScale: 10,
    offsetX: 0,
    offsetY: 65,
  };
  var RENDER_SCALE = 1; // the image is soft, so render at CSS resolution
  var FRAME_MS = 1000 / 30;

  var GRID_SPACING = 90;
  var GRID_GAP = 10;
  var GRID_DOT_RADIUS = 1.8;

  var colors = [];
  var gridRgb = "45, 45, 45";
  var gridAlpha = 0.08;

  function readThemeColors() {
    var style = getComputedStyle(document.documentElement);
    colors = style
      .getPropertyValue("--ambient-shader-colors")
      .split(",")
      .map(function (c) {
        return c.trim();
      })
      .filter(Boolean)
      .slice(0, 3)
      .map(hexToRgb);
    gridRgb = style.getPropertyValue("--ambient-grid-rgb").trim() || gridRgb;
    gridAlpha = parseFloat(style.getPropertyValue("--ambient-grid-alpha")) || gridAlpha;
  }

  function hexToRgb(hex) {
    var h = hex.replace("#", "");
    return [parseInt(h.slice(0, 2), 16) / 255, parseInt(h.slice(2, 4), 16) / 255, parseInt(h.slice(4, 6), 16) / 255];
  }

  // ---------------------------------------------------------------------------
  // Grid of short line segments with a dot at each node
  // ---------------------------------------------------------------------------
  function drawGrid() {
    if (!gridCanvas) return;
    var ctx = gridCanvas.getContext("2d");
    if (!ctx) return;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var w = gridCanvas.clientWidth;
    var h = gridCanvas.clientHeight;
    gridCanvas.width = Math.round(w * dpr);
    gridCanvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    var cols = Math.ceil(w / GRID_SPACING) + 1;
    var rows = Math.ceil(h / GRID_SPACING) + 1;
    var x0 = (w - (cols - 1) * GRID_SPACING) / 2;
    var y0 = (h - (rows - 1) * GRID_SPACING) / 2;

    ctx.strokeStyle = "rgba(" + gridRgb + ", " + gridAlpha + ")";
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        var x = x0 + c * GRID_SPACING;
        var y = y0 + r * GRID_SPACING;
        if (c < cols - 1) {
          ctx.moveTo(x + GRID_GAP, y);
          ctx.lineTo(x + GRID_SPACING - GRID_GAP, y);
        }
        if (r < rows - 1) {
          ctx.moveTo(x, y + GRID_GAP);
          ctx.lineTo(x, y + GRID_SPACING - GRID_GAP);
        }
      }
    }
    ctx.stroke();

    ctx.fillStyle = "rgba(" + gridRgb + ", " + gridAlpha * 0.4 + ")";
    for (var rr = 0; rr < rows; rr++) {
      for (var cc = 0; cc < cols; cc++) {
        ctx.beginPath();
        ctx.arc(x0 + cc * GRID_SPACING, y0 + rr * GRID_SPACING, GRID_DOT_RADIUS, 0, 2 * Math.PI);
        ctx.fill();
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Warp shader
  // ---------------------------------------------------------------------------
  var VERTEX_SRC = "#version 300 es\nin vec4 a_position;\nvoid main() { gl_Position = a_position; }\n";

  var FRAGMENT_SRC = [
    "#version 300 es",
    "precision mediump float;",
    "uniform float u_time;",
    "uniform float u_pixelRatio;",
    "uniform vec2 u_resolution;",
    "uniform float u_scale;",
    "uniform float u_rotation;",
    "uniform vec3 u_color1;",
    "uniform vec3 u_color2;",
    "uniform vec3 u_color3;",
    "uniform float u_proportion;",
    "uniform float u_softness;",
    "uniform float u_shapeScale;",
    "uniform float u_distortion;",
    "uniform float u_swirl;",
    "uniform float u_swirlIterations;",
    "uniform vec2 u_offset;",
    "out vec4 fragColor;",
    "#define TWO_PI 6.28318530718",
    "#define PI 3.14159265358979323846",
    "vec2 rotate(vec2 uv, float th) { return mat2(cos(th), sin(th), -sin(th), cos(th)) * uv; }",
    "float random(vec2 st) { return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123); }",
    "float noise(vec2 st) {",
    "  vec2 i = floor(st);",
    "  vec2 f = fract(st);",
    "  float a = random(i);",
    "  float b = random(i + vec2(1.0, 0.0));",
    "  float c = random(i + vec2(0.0, 1.0));",
    "  float d = random(i + vec2(1.0, 1.0));",
    "  vec2 u = f * f * (3.0 - 2.0 * f);",
    "  return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);",
    "}",
    "vec3 blend(float mixer, float softness) {",
    "  float edge = 1.0 - softness;",
    "  vec3 col = mix(u_color1, u_color2, smoothstep(0.0 + 0.35 * edge, 0.7 - 0.35 * edge, mixer));",
    "  return mix(col, u_color3, smoothstep(0.3 + 0.35 * edge, 1.0 - 0.35 * edge, mixer));",
    "}",
    "void main() {",
    "  vec2 uv = gl_FragCoord.xy / u_resolution.xy;",
    "  float t = 0.5 * u_time;",
    "  float noise_scale = 0.0005 + 0.006 * u_scale;",
    "  uv -= 0.5;",
    "  uv *= (noise_scale * u_resolution);",
    "  uv = rotate(uv, u_rotation * 0.5 * PI);",
    "  uv /= u_pixelRatio;",
    "  uv += 0.5;",
    "  uv += u_offset;",
    "  float n1 = noise(uv + t);",
    "  float n2 = noise(uv * 2.0 - t);",
    "  float angle = n1 * TWO_PI;",
    "  uv.x += 4.0 * u_distortion * n2 * cos(angle);",
    "  uv.y += 4.0 * u_distortion * n2 * sin(angle);",
    "  float iterations = ceil(clamp(u_swirlIterations, 1.0, 30.0));",
    "  for (float i = 1.0; i <= 30.0; i++) {",
    "    if (i > iterations) break;",
    "    uv.x += clamp(u_swirl, 0.0, 2.0) / i * cos(t + i * 1.5 * uv.y);",
    "    uv.y += clamp(u_swirl, 0.0, 2.0) / i * cos(t + i * 1.0 * uv.x);",
    "  }",
    "  float proportion = clamp(u_proportion, 0.0, 1.0);",
    "  vec2 checks_uv = uv * (0.5 + 3.5 * u_shapeScale);",
    "  float shape = 0.5 + 0.5 * sin(checks_uv.x) * cos(checks_uv.y);",
    "  float mixer = shape + 0.48 * sign(proportion - 0.5) * pow(abs(proportion - 0.5), 0.5);",
    "  fragColor = vec4(blend(mixer, clamp(u_softness, 0.0, 1.0)), 1.0);",
    "}",
  ].join("\n");

  function initShader() {
    if (!shaderCanvas) return null;
    var gl = shaderCanvas.getContext("webgl2", {
      alpha: true,
      premultipliedAlpha: false,
      powerPreference: "low-power",
      preserveDrawingBuffer: reduceMotion,
    });
    if (!gl) return null;

    function compile(type, src) {
      var s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
        console.error("Ambient shader compile error:", gl.getShaderInfoLog(s));
        return null;
      }
      return s;
    }
    var vs = compile(gl.VERTEX_SHADER, VERTEX_SRC);
    var fs = compile(gl.FRAGMENT_SHADER, FRAGMENT_SRC);
    if (!vs || !fs) return null;
    var program = gl.createProgram();
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return null;
    gl.useProgram(program);

    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    var pos = gl.getAttribLocation(program, "a_position");
    gl.enableVertexAttribArray(pos);
    gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 0, 0);

    var u = {};
    [
      "u_time",
      "u_pixelRatio",
      "u_resolution",
      "u_scale",
      "u_rotation",
      "u_color1",
      "u_color2",
      "u_color3",
      "u_proportion",
      "u_softness",
      "u_shapeScale",
      "u_distortion",
      "u_swirl",
      "u_swirlIterations",
      "u_offset",
    ].forEach(function (name) {
      u[name] = gl.getUniformLocation(program, name);
    });

    gl.uniform1f(u.u_pixelRatio, RENDER_SCALE);
    gl.uniform1f(u.u_scale, SETTINGS.scale);
    gl.uniform1f(u.u_rotation, SETTINGS.rotation / 90);
    gl.uniform1f(u.u_proportion, SETTINGS.proportion / 100);
    gl.uniform1f(u.u_softness, SETTINGS.softness / 100);
    gl.uniform1f(u.u_shapeScale, SETTINGS.shapeScale / 100);
    gl.uniform1f(u.u_distortion, SETTINGS.distortion / 100);
    gl.uniform1f(u.u_swirl, SETTINGS.swirl / 50);
    gl.uniform1f(u.u_swirlIterations, SETTINGS.swirlIterations);
    gl.uniform2f(u.u_offset, SETTINGS.offsetX / 100, SETTINGS.offsetY / 100);

    function resize() {
      shaderCanvas.width = Math.round(shaderCanvas.clientWidth * RENDER_SCALE);
      shaderCanvas.height = Math.round(shaderCanvas.clientHeight * RENDER_SCALE);
      gl.viewport(0, 0, shaderCanvas.width, shaderCanvas.height);
    }

    function render(timeSec) {
      var c1 = colors[0] || [0.65, 0.65, 0.65];
      var c2 = colors[1] || [1, 1, 1];
      var c3 = colors[2] || c2;
      gl.uniform3f(u.u_color1, c1[0], c1[1], c1[2]);
      gl.uniform3f(u.u_color2, c2[0], c2[1], c2[2]);
      gl.uniform3f(u.u_color3, c3[0], c3[1], c3[2]);
      gl.uniform1f(u.u_time, timeSec * (SETTINGS.speed / 100));
      gl.uniform2f(u.u_resolution, shaderCanvas.width, shaderCanvas.height);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }

    return { resize: resize, render: render };
  }

  // ---------------------------------------------------------------------------
  // Animation loop: ~30 fps, paused when the tab is hidden or the hero is off screen
  // ---------------------------------------------------------------------------
  readThemeColors();
  drawGrid();
  var shader = initShader();
  if (!shader) {
    if (shaderCanvas) shaderCanvas.style.display = "none";
  } else {
    layer.classList.add("has-shader");
    shader.resize();
  }

  var start = performance.now();
  var last = 0;
  var rafId = 0;
  var onScreen = true;

  function frame(now) {
    rafId = 0;
    if (now - last >= FRAME_MS) {
      last = now;
      shader.render((now - start) / 1000);
    }
    schedule();
  }

  function schedule() {
    if (!shader || reduceMotion || rafId || !onScreen || document.hidden) return;
    rafId = requestAnimationFrame(frame);
  }

  function redrawStill() {
    if (shader) shader.render(reduceMotion ? 0 : (performance.now() - start) / 1000);
  }

  redrawStill();
  schedule();

  document.addEventListener("visibilitychange", schedule);

  if (window.IntersectionObserver) {
    new IntersectionObserver(function (entries) {
      onScreen = entries[0].isIntersecting;
      schedule();
    }).observe(layer);
  }

  var resizeTimer = 0;
  window.addEventListener("resize", function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      if (shader) shader.resize();
      drawGrid();
      redrawStill();
    }, 100);
  });

  // Re-read colors when the light/dark toggle changes data-theme on <html>
  new MutationObserver(function () {
    readThemeColors();
    drawGrid();
    redrawStill();
  }).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
})();
