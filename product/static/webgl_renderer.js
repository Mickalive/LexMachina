/**
 * WebGL Renderer for LexMachina Query Map
 * Extracted and adapted from index.html for bundle-driven query maps.
 * Renders points, cluster hulls, and on-demand relation edges.
 */

class WebGLRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.gl = canvas.getContext('webgl2', { antialias: true, alpha: true });
    if (!this.gl) {
      console.warn('WebGL2 not available, falling back to Canvas 2D');
      return null;
    }

    this.gl.enable(this.gl.BLEND);
    this.gl.blendFunc(this.gl.SRC_ALPHA, this.gl.ONE_MINUS_SRC_ALPHA);
    this.gl.disable(this.gl.DEPTH_TEST);

    this._initShaders();
    this._initBuffers();

    this.pointCount = 0;
    this.hullCount = 0;
    this.edgeCount = 0;
    this.currentTransform = null;
    this.frustumPlanes = null;
  }

  _initShaders() {
    const gl = this.gl;

    // Point shader (instanced rendering for points)
    const pointVS = `#version 300 es
      precision highp float;
      in vec2 a_position;
      in vec4 a_color;
      in float a_radius;
      in float a_imported;
      uniform mat3 u_transform;
      uniform vec2 u_viewport;
      out vec4 v_color;
      out float v_radius;
      out float v_imported;
      void main() {
        vec3 pos = u_transform * vec3(a_position, 1.0);
        gl_Position = vec4(pos.xy / u_viewport * 2.0 - 1.0, 0.0, 1.0);
        gl_PointSize = a_radius * u_transform[0][0] * 2.0;
        v_color = a_color;
        v_radius = a_radius;
        v_imported = a_imported;
      }
    `;

    const pointFS = `#version 300 es
      precision highp float;
      in vec4 v_color;
      in float v_radius;
      in float v_imported;
      out vec4 fragColor;
      void main() {
        vec2 center = gl_PointCoord - 0.5;
        float dist = length(center) * 2.0;
        float alpha = smoothstep(1.0, 0.0, dist);
        if (alpha < 0.05) discard;
        vec4 color = v_color;
        if (v_imported > 0.5) {
          color = vec4(1.0, 0.5, 1.0, color.a);
        }
        fragColor = vec4(color.rgb, color.a * alpha);
      }
    `;

    // Hull shader (line strips for cluster bounding boxes)
    const hullVS = `#version 300 es
      precision highp float;
      in vec2 a_position;
      in vec4 a_color;
      uniform mat3 u_transform;
      uniform vec2 u_viewport;
      out vec4 v_color;
      void main() {
        vec3 pos = u_transform * vec3(a_position, 1.0);
        gl_Position = vec4(pos.xy / u_viewport * 2.0 - 1.0, 0.0, 1.0);
        v_color = a_color;
      }
    `;

    const hullFS = `#version 300 es
      precision highp float;
      in vec4 v_color;
      out vec4 fragColor;
      void main() {
        fragColor = v_color;
      }
    `;

    // Edge shader (lines for citation relations)
    const edgeVS = `#version 300 es
      precision highp float;
      in vec2 a_start;
      in vec2 a_end;
      in vec4 a_color;
      uniform mat3 u_transform;
      uniform vec2 u_viewport;
      out vec4 v_color;
      void main() {
        vec3 start = u_transform * vec3(a_start, 1.0);
        vec3 end = u_transform * vec3(a_end, 1.0);
        // Emit two vertices for the line
        gl_Position = vec4(gl_VertexID == 0 ? start.xy : end.xy) / u_viewport * 2.0 - 1.0, 0.0, 1.0);
        v_color = a_color;
      }
    `;

    const edgeFS = `#version 300 es
      precision highp float;
      in vec4 v_color;
      out vec4 fragColor;
      void main() {
        fragColor = v_color;
      }
    `;

    this.pointProgram = this._createProgram(gl, pointVS, pointFS);
    this.hullProgram = this._createProgram(gl, hullVS, hullFS);
    this.edgeProgram = this._createProgram(gl, edgeVS, edgeFS);

    // Get attribute/uniform locations
    this.pointAttrs = {
      position: gl.getAttribLocation(this.pointProgram, 'a_position'),
      color: gl.getAttribLocation(this.pointProgram, 'a_color'),
      radius: gl.getAttribLocation(this.pointProgram, 'a_radius'),
      imported: gl.getAttribLocation(this.pointProgram, 'a_imported'),
    };
    this.pointUniforms = {
      transform: gl.getUniformLocation(this.pointProgram, 'u_transform'),
      viewport: gl.getUniformLocation(this.pointProgram, 'u_viewport'),
    };

    this.hullAttrs = {
      position: gl.getAttribLocation(this.hullProgram, 'a_position'),
      color: gl.getAttribLocation(this.hullProgram, 'a_color'),
    };
    this.hullUniforms = {
      transform: gl.getUniformLocation(this.hullProgram, 'u_transform'),
      viewport: gl.getUniformLocation(this.hullProgram, 'u_viewport'),
    };

    this.edgeAttrs = {
      start: gl.getAttribLocation(this.edgeProgram, 'a_start'),
      end: gl.getAttribLocation(this.edgeProgram, 'a_end'),
      color: gl.getAttribLocation(this.edgeProgram, 'a_color'),
    };
    this.edgeUniforms = {
      transform: gl.getUniformLocation(this.edgeProgram, 'u_transform'),
      viewport: gl.getUniformLocation(this.edgeProgram, 'u_viewport'),
    };
  }

  _createProgram(gl, vsSource, fsSource) {
    const vs = gl.createShader(gl.VERTEX_SHADER);
    gl.shaderSource(vs, vsSource);
    gl.compileShader(vs);
    if (!gl.getShaderParameter(vs, gl.COMPILE_STATUS)) {
      console.error('Vertex shader error:', gl.getShaderInfoLog(vs));
      return null;
    }

    const fs = gl.createShader(gl.FRAGMENT_SHADER);
    gl.shaderSource(fs, fsSource);
    gl.compileShader(fs);
    if (!gl.getShaderParameter(fs, gl.COMPILE_STATUS)) {
      console.error('Fragment shader error:', gl.getShaderInfoLog(fs));
      return null;
    }

    const program = gl.createProgram();
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error('Program link error:', gl.getProgramInfoLog(program));
      return null;
    }
    return program;
  }

  _initBuffers() {
    const gl = this.gl;

    // Point buffers
    this.pointPositionBuffer = gl.createBuffer();
    this.pointColorBuffer = gl.createBuffer();
    this.pointRadiusBuffer = gl.createBuffer();
    this.pointImportedBuffer = gl.createBuffer();

    // Hull buffers
    this.hullPositionBuffer = gl.createBuffer();
    this.hullColorBuffer = gl.createBuffer();

    // Edge buffers
    this.edgeStartBuffer = gl.createBuffer();
    this.edgeEndBuffer = gl.createBuffer();
    this.edgeColorBuffer = gl.createBuffer();
  }

  /**
   * Upload point data to GPU buffers
   * @param {Float32Array|Array} positions - Flat array [x0, y0, x1, y1, ...]
   * @param {Float32Array|Array} colors - Flat array [r0, g0, b0, a0, ...]
   * @param {Float32Array|Array} radii - Array of point radii
   * @param {Float32Array|Array} imported - Array of imported flags (0/1)
   */
  uploadPointData(positions, colors, radii, imported) {
    const gl = this.gl;
    this.pointCount = positions.length / 2;

    gl.bindBuffer(gl.ARRAY_BUFFER, this.pointPositionBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(positions), gl.DYNAMIC_DRAW);

    gl.bindBuffer(gl.ARRAY_BUFFER, this.pointColorBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(colors), gl.DYNAMIC_DRAW);

    gl.bindBuffer(gl.ARRAY_BUFFER, this.pointRadiusBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(radii), gl.DYNAMIC_DRAW);

    gl.bindBuffer(gl.ARRAY_BUFFER, this.pointImportedBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(imported), gl.DYNAMIC_DRAW);
  }

  /**
   * Upload cluster hull data
   * @param {Array} hulls - Array of {points: [[x,y],...], color: [r,g,b,a]}
   */
  uploadHullData(hulls) {
    const gl = this.gl;
    const positions = [];
    const colors = [];

    hulls.forEach(hull => {
      // Close the polygon (5 points for 4 corners)
      const pts = hull.points;
      for (let i = 0; i < pts.length; i++) {
        positions.push(pts[i][0], pts[i][1]);
        colors.push(...hull.color);
      }
      // Close
      positions.push(pts[0][0], pts[0][1]);
      colors.push(...hull.color);
    });

    this.hullCount = positions.length / 2;

    gl.bindBuffer(gl.ARRAY_BUFFER, this.hullPositionBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(positions), gl.DYNAMIC_DRAW);

    gl.bindBuffer(gl.ARRAY_BUFFER, this.hullColorBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(colors), gl.DYNAMIC_DRAW);
  }

  /**
   * Upload relation edge data for on-demand rendering
   * @param {Array} edges - Array of {start: [x,y], end: [x,y], color: [r,g,b,a]}
   */
  uploadEdgeData(edges) {
    const gl = this.gl;
    const starts = [];
    const ends = [];
    const colors = [];

    edges.forEach(edge => {
      starts.push(edge.start[0], edge.start[1]);
      ends.push(edge.end[0], edge.end[1]);
      colors.push(...edge.color, ...edge.color); // Two vertices per edge
    });

    this.edgeCount = edges.length * 2; // Two vertices per edge

    gl.bindBuffer(gl.ARRAY_BUFFER, this.edgeStartBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(starts), gl.DYNAMIC_DRAW);

    gl.bindBuffer(gl.ARRAY_BUFFER, this.edgeEndBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(ends), gl.DYNAMIC_DRAW);

    gl.bindBuffer(gl.ARRAY_BUFFER, this.edgeColorBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(colors), gl.DYNAMIC_DRAW);
  }

  /**
   * Render the scene
   * @param {Object} transform - {xMin, xMax, yMin, yMax, scale, offsetX, offsetY}
   * @param {number} frustumCulling - Frustum culling parameter (unused in WebGL, done server-side)
   * @param {Array} frustumPlanes - Frustum planes for GPU culling
   */
  render(transform, frustumCulling = 1.0, frustumPlanes = null) {
    if (!this.gl) return;
    const gl = this.gl;

    this.currentTransform = transform;
    this.frustumPlanes = frustumPlanes;

    // Clear
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.clearColor(0.05, 0.05, 0.08, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT);

    // Build transform matrix (column-major for mat3)
    // Maps data coordinates -> clip space [-1, 1]
    const sx = 2.0 / (transform.xMax - transform.xMin);
    const sy = 2.0 / (transform.yMax - transform.yMin);
    const tx = - (transform.xMax + transform.xMin) / (transform.xMax - transform.xMin);
    const ty = - (transform.yMax + transform.yMin) / (transform.yMax - transform.yMin);

    const transformMatrix = new Float32Array([
      sx * transform.scale, 0, 0,
      0, sy * transform.scale, 0,
      tx + transform.offsetX * sx * transform.scale,
      ty + transform.offsetY * sy * transform.scale,
      1 // unused (mat3)
    ]);

    const viewport = new Float32Array([this.canvas.width, this.canvas.height]);

    // Render cluster hulls first (background)
    if (this.hullCount > 0) {
      gl.useProgram(this.hullProgram);
      gl.uniformMatrix3fv(this.hullUniforms.transform, false, transformMatrix);
      gl.uniform2fv(this.hullUniforms.viewport, viewport);

      gl.enableVertexAttribArray(this.hullAttrs.position);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.hullPositionBuffer);
      gl.vertexAttribPointer(this.hullAttrs.position, 2, gl.FLOAT, false, 0, 0);

      gl.enableVertexAttribArray(this.hullAttrs.color);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.hullColorBuffer);
      gl.vertexAttribPointer(this.hullAttrs.color, 4, gl.FLOAT, false, 0, 0);

      gl.drawArrays(gl.LINE_STRIP, 0, this.hullCount);
    }

    // Render points
    if (this.pointCount > 0) {
      gl.useProgram(this.pointProgram);
      gl.uniformMatrix3fv(this.pointUniforms.transform, false, transformMatrix);
      gl.uniform2fv(this.pointUniforms.viewport, viewport);

      gl.enableVertexAttribArray(this.pointAttrs.position);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.pointPositionBuffer);
      gl.vertexAttribPointer(this.pointAttrs.position, 2, gl.FLOAT, false, 0, 0);

      gl.enableVertexAttribArray(this.pointAttrs.color);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.pointColorBuffer);
      gl.vertexAttribPointer(this.pointAttrs.color, 4, gl.FLOAT, false, 0, 0);

      gl.enableVertexAttribArray(this.pointAttrs.radius);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.pointRadiusBuffer);
      gl.vertexAttribPointer(this.pointAttrs.radius, 1, gl.FLOAT, false, 0, 0);

      gl.enableVertexAttribArray(this.pointAttrs.imported);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.pointImportedBuffer);
      gl.vertexAttribPointer(this.pointAttrs.imported, 1, gl.FLOAT, false, 0, 0);

      gl.drawArrays(gl.POINTS, 0, this.pointCount);
    }

    // Render relation edges (on top)
    if (this.edgeCount > 0) {
      gl.useProgram(this.edgeProgram);
      gl.uniformMatrix3fv(this.edgeUniforms.transform, false, transformMatrix);
      gl.uniform2fv(this.edgeUniforms.viewport, viewport);

      gl.enableVertexAttribArray(this.edgeAttrs.start);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.edgeStartBuffer);
      gl.vertexAttribPointer(this.edgeAttrs.start, 2, gl.FLOAT, false, 0, 0);

      gl.enableVertexAttribArray(this.edgeAttrs.end);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.edgeEndBuffer);
      gl.vertexAttribPointer(this.edgeAttrs.end, 2, gl.FLOAT, false, 0, 0);

      gl.enableVertexAttribArray(this.edgeAttrs.color);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.edgeColorBuffer);
      gl.vertexAttribPointer(this.edgeAttrs.color, 4, gl.FLOAT, false, 0, 0);

      gl.drawArrays(gl.LINES, 0, this.edgeCount);
    }
  }

  /**
   * Hit-test a screen coordinate against rendered points
   * @param {number} clientX - Mouse client X
   * @param {number} clientY - Mouse client Y
   * @param {Array} decision_ids - Array of decision IDs matching point order
   * @param {Array} positions - Flat array of positions [x0, y0, ...]
   * @param {Object} transform - Current transform
   * @returns {Object|null} Hit result {decision_id, index, distance}
   */
  hitTest(clientX, clientY, decision_ids, positions, transform) {
    if (!this.gl || !this.currentTransform) return null;

    const rect = this.canvas.getBoundingClientRect();
    const mx = clientX - rect.left;
    const my = clientY - rect.top;

    // Convert screen to data coordinates
    const sx = 2.0 / (transform.xMax - transform.xMin);
    const sy = 2.0 / (transform.yMax - transform.yMin);
    const tx = - (transform.xMax + transform.xMin) / (transform.xMax - transform.xMin);
    const ty = - (transform.yMax + transform.yMin) / (transform.yMax - transform.yMin);

    // Inverse transform: clip -> data
    const clipX = (mx / this.canvas.width) * 2.0 - 1.0;
    const clipY = 1.0 - (my / this.canvas.height) * 2.0; // Flip Y

    const dataX = (clipX - tx) / sx;
    const dataY = (clipY - ty) / sy;

    // Find nearest point (brute force for now - could use spatial index)
    let bestIdx = -1;
    let bestDist = Infinity;
    const threshold = 0.02; // Data coordinate threshold

    for (let i = 0; i < decision_ids.length; i++) {
      const px = positions[i * 2];
      const py = positions[i * 2 + 1];
      const dx = px - dataX;
      const dy = py - dataY;
      const dist = dx * dx + dy * dy;
      if (dist < bestDist && dist < threshold * threshold) {
        bestDist = dist;
        bestIdx = i;
      }
    }

    if (bestIdx >= 0) {
      return {
        decision_id: decision_ids[bestIdx],
        index: bestIdx,
        distance: Math.sqrt(bestDist),
      };
    }
    return null;
  }

  destroy() {
    if (!this.gl) return;
    const gl = this.gl;
    [this.pointPositionBuffer, this.pointColorBuffer, this.pointRadiusBuffer, this.pointImportedBuffer,
     this.hullPositionBuffer, this.hullColorBuffer,
     this.edgeStartBuffer, this.edgeEndBuffer, this.edgeColorBuffer].forEach(buf => {
      if (buf) gl.deleteBuffer(buf);
    });
    [this.pointProgram, this.hullProgram, this.edgeProgram].forEach(prog => {
      if (prog) gl.deleteProgram(prog);
    });
  }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { WebGLRenderer };
}

// Also expose globally for browser script usage
if (typeof window !== 'undefined') {
  window.WebGLRenderer = WebGLRenderer;
}