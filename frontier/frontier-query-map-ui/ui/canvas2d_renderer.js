/**
 * Canvas 2D Renderer for LexMachina Query Map
 * Fallback renderer when WebGL is not available or disabled.
 * Provides the same visual output as WebGL renderer using Canvas 2D API.
 */

class Canvas2DRenderer {
    constructor(canvas, model) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.model = model;
        this.useWebGL = false;
        
        // Rendering state
        this.panX = 0;
        this.panY = 0;
        this.scale = 1;
        this.isDragging = false;
        this.dragStartX = 0;
        this.dragStartY = 0;
        this.dragStartPanX = 0;
        this.dragStartPanY = 0;
        
        // Cluster colors (matching WebGL/index.html)
        this.CLUSTER_COLORS = [
            '#7c8aff', '#ff6b6b', '#51cf66', '#ffd43b', '#cc5de8',
            '#20c997', '#ff922b', '#4dabf7', '#e599f7', '#69db7c',
            '#fcc419', '#ff8787', '#748ffc', '#63e6be', '#da77f2',
            '#a9e34b', '#ffa94d', '#74c0fc', '#b2f2bb', '#f783ac',
        ];
        
        this.LANG_COLORS = {
            'de': '#4dabf7',
            'fr': '#ffd43b',
            'it': '#51cf66',
            'unknown': '#666'
        };
        
        this.COUNTER_STATUS_COLORS = {
            'cited': '#ffd43b',
            'candidate-limiting': '#c00',
            'candidate-distinguishing': '#ff922b',
            'candidate-contrary': '#c00',
            'candidate-exception': '#ff6b6b',
            'none': '#7c8aff',
            'supporting-candidate': '#7c8aff',
            'context': '#7c8aff',
        };
        
        this._setupEventListeners();
        this._resize();
        window.addEventListener('resize', () => this._resize());
    }

    _setupEventListeners() {
        // Mouse events for pan/zoom
        this.canvas.addEventListener('mousedown', (e) => this._onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this._onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this._onMouseUp(e));
        this.canvas.addEventListener('mouseleave', (e) => this._onMouseUp(e));
        this.canvas.addEventListener('wheel', (e) => this._onWheel(e), { passive: false });
        this.canvas.addEventListener('click', (e) => this._onClick(e));
        this.canvas.addEventListener('dblclick', (e) => this._onDoubleClick(e));
        
        // Touch events for mobile
        this.canvas.addEventListener('touchstart', (e) => this._onTouchStart(e), { passive: false });
        this.canvas.addEventListener('touchmove', (e) => this._onTouchMove(e), { passive: false });
        this.canvas.addEventListener('touchend', (e) => this._onTouchEnd(e));
    }

    _resize() {
        const rect = this.canvas.parentElement.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        
        this.canvas.width = Math.max(300, rect.width) * dpr;
        this.canvas.height = Math.max(300, rect.height) * dpr;
        this.canvas.style.width = `${Math.max(300, rect.width)}px`;
        this.canvas.style.height = `${Math.max(300, rect.height)}px`;
        
        this.ctx.scale(dpr, dpr);
        this.viewportWidth = Math.max(300, rect.width);
        this.viewportHeight = Math.max(300, rect.height);
        
        // Update model viewport size
        this.model.setViewport({
            width: this.viewportWidth,
            height: this.viewportHeight
        });
        
        this.draw();
    }

    // Coordinate transformation: data space -> screen space
    _dataToScreen(x, y) {
        const bounds = this.model.getBounds();
        const dataWidth = bounds.x_max - bounds.x_min;
        const dataHeight = bounds.y_max - bounds.y_min;
        
        // Normalize to 0-1
        const nx = (x - bounds.x_min) / dataWidth;
        const ny = (y - bounds.y_min) / dataHeight;
        
        // Apply viewport transform
        const screenX = this.panX + nx * this.viewportWidth * this.scale;
        const screenY = this.panY + (1 - ny) * this.viewportHeight * this.scale;
        
        return { x: screenX, y: screenY };
    }

    // Coordinate transformation: screen space -> data space
    _screenToData(screenX, screenY) {
        const bounds = this.model.getBounds();
        const dataWidth = bounds.x_max - bounds.x_min;
        const dataHeight = bounds.y_max - bounds.y_min;
        
        const nx = (screenX - this.panX) / (this.viewportWidth * this.scale);
        const ny = 1 - (screenY - this.panY) / (this.viewportHeight * this.scale);
        
        const x = bounds.x_min + nx * dataWidth;
        const y = bounds.y_min + ny * dataHeight;
        
        return { x, y };
    }

    // Fit view to data bounds
    fitToData() {
        const bounds = this.model.getBounds();
        const dataWidth = bounds.x_max - bounds.x_min;
        const dataHeight = bounds.y_max - bounds.y_min;
        
        const scaleX = this.viewportWidth / (dataWidth * 1.1);
        const scaleY = this.viewportHeight / (dataHeight * 1.1);
        this.scale = Math.min(scaleX, scaleY);
        
        // Center
        this.panX = -bounds.x_min * this.scale * this.viewportWidth / dataWidth + (this.viewportWidth * (1 - this.scale * this.viewportWidth / dataWidth)) / 2;
        this.panY = this.viewportHeight - (-bounds.y_min * this.scale * this.viewportHeight / dataHeight + (this.viewportHeight * (1 - this.scale * this.viewportHeight / dataHeight)) / 2);
        
        this.model.setViewport({ scale: this.scale, x: this.panX, y: this.panY });
        this.draw();
    }

    // Reset view
    resetView() {
        this.scale = 1;
        this.panX = 0;
        this.panY = 0;
        this.fitToData();
    }

    zoomIn() {
        this._zoomAt(1.5, this.viewportWidth / 2, this.viewportHeight / 2);
    }

    zoomOut() {
        this._zoomAt(1 / 1.5, this.viewportWidth / 2, this.viewportHeight / 2);
    }

    _zoomAt(factor, screenX, screenY) {
        const dataBefore = this._screenToData(screenX, screenY);
        this.scale *= factor;
        this.scale = Math.max(0.1, Math.min(10, this.scale));
        const dataAfter = this._screenToData(screenX, screenY);
        
        this.panX += (dataBefore.x - dataAfter.x) * this.scale * this.viewportWidth / (this.model.getBounds().x_max - this.model.getBounds().x_min);
        this.panY += (dataBefore.y - dataAfter.y) * this.scale * this.viewportHeight / (this.model.getBounds().y_max - this.model.getBounds().y_min);
        
        this.model.setViewport({ scale: this.scale, x: this.panX, y: this.panY });
        this.draw();
    }

    // Event handlers
    _onMouseDown(e) {
        if (e.button !== 0) return;
        this.isDragging = true;
        this.dragStartX = e.clientX;
        this.dragStartY = e.clientY;
        this.dragStartPanX = this.panX;
        this.dragStartPanY = this.panY;
        this.canvas.style.cursor = 'grabbing';
    }

    _onMouseMove(e) {
        if (!this.isDragging) {
            // Check hover
            this._updateHover(e);
            return;
        }
        
        const dx = e.clientX - this.dragStartX;
        const dy = e.clientY - this.dragStartY;
        
        this.panX = this.dragStartPanX + dx;
        this.panY = this.dragStartPanY + dy;
        
        this.model.setViewport({ x: this.panX, y: this.panY });
        this.draw();
    }

    _onMouseUp(e) {
        this.isDragging = false;
        this.canvas.style.cursor = 'crosshair';
    }

    _onWheel(e) {
        e.preventDefault();
        const factor = e.deltaY > 0 ? 1 / 1.2 : 1.2;
        const rect = this.canvas.getBoundingClientRect();
        const screenX = e.clientX - rect.left;
        const screenY = e.clientY - rect.top;
        this._zoomAt(factor, screenX, screenY);
    }

    _onClick(e) {
        if (this.isDragging && (Math.abs(e.clientX - this.dragStartX) > 5 || Math.abs(e.clientY - this.dragStartY) > 5)) {
            return; // Was a drag, not a click
        }
        
        const rect = this.canvas.getBoundingClientRect();
        const screenX = e.clientX - rect.left;
        const screenY = e.clientY - rect.top;
        this._hitTest(screenX, screenY);
    }

    _onDoubleClick(e) {
        const rect = this.canvas.getBoundingClientRect();
        const screenX = e.clientX - rect.left;
        const screenY = e.clientY - rect.top;
        const dataPos = this._screenToData(screenX, screenY);
        
        // Find nearest cluster and zoom to it
        const decisions = this.model.getDecisions();
        let bestCluster = null;
        let bestDist = Infinity;
        
        decisions.forEach(d => {
            const dist = Math.hypot(d.x - dataPos.x, d.y - dataPos.y);
            if (dist < bestDist) {
                bestDist = dist;
                bestCluster = d.cluster_id;
            }
        });
        
        if (bestCluster !== null) {
            this._zoomToCluster(bestCluster);
        }
    }

    // Touch handlers
    _onTouchStart(e) {
        if (e.touches.length === 1) {
            this.isDragging = true;
            this.dragStartX = e.touches[0].clientX;
            this.dragStartY = e.touches[0].clientY;
            this.dragStartPanX = this.panX;
            this.dragStartPanY = this.panY;
        }
    }

    _onTouchMove(e) {
        if (!this.isDragging || e.touches.length !== 1) return;
        e.preventDefault();
        
        const dx = e.touches[0].clientX - this.dragStartX;
        const dy = e.touches[0].clientY - this.dragStartY;
        
        this.panX = this.dragStartPanX + dx;
        this.panY = this.dragStartPanY + dy;
        
        this.model.setViewport({ x: this.panX, y: this.panY });
        this.draw();
    }

    _onTouchEnd(e) {
        this.isDragging = false;
    }

    _updateHover(e) {
        const rect = this.canvas.getBoundingClientRect();
        const screenX = e.clientX - rect.left;
        const screenY = e.clientY - rect.top;
        
        const hovered = this._findNearestDecision(screenX, screenY);
        if (hovered && hovered.distance < 20) {
            this.model.highlightDecision(hovered.decision.decision_id);
        } else {
            this.model.clearHighlight();
        }
    }

    _hitTest(screenX, screenY) {
        const hit = this._findNearestDecision(screenX, screenY);
        if (hit && hit.distance < 20) {
            this.model.selectDecision(hit.decision.decision_id);
        } else {
            this.model.clearSelection();
        }
    }

    _findNearestDecision(screenX, screenY) {
        const decisions = this.model.getDecisions();
        let best = null;
        let bestDist = Infinity;
        
        for (const d of decisions) {
            const pos = this._dataToScreen(d.x, d.y);
            const dist = Math.hypot(pos.x - screenX, pos.y - screenY);
            const radius = (d.radius || 5) * this.scale + 5;
            
            if (dist < radius && dist < bestDist) {
                bestDist = dist;
                best = { decision: d, distance: dist };
            }
        }
        
        return best;
    }

    _zoomToCluster(clusterId) {
        const decisions = this.model.getDecisions().filter(d => d.cluster_id === clusterId);
        if (decisions.length === 0) return;
        
        const xs = decisions.map(d => d.x);
        const ys = decisions.map(d => d.y);
        const minX = Math.min(...xs);
        const maxX = Math.max(...xs);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);
        
        const centerX = (minX + maxX) / 2;
        const centerY = (minY + maxY) / 2;
        const width = maxX - minX;
        const height = maxY - minY;
        
        const bounds = this.model.getBounds();
        const dataWidth = bounds.x_max - bounds.x_min;
        const dataHeight = bounds.y_max - bounds.y_min;
        
        const scaleX = this.viewportWidth / (width * 1.5);
        const scaleY = this.viewportHeight / (height * 1.5);
        this.scale = Math.min(scaleX, scaleY, 5); // Cap zoom
        
        const nx = (centerX - bounds.x_min) / dataWidth;
        const ny = (centerY - bounds.y_min) / dataHeight;
        
        this.panX = this.viewportWidth / 2 - nx * this.viewportWidth * this.scale;
        this.panY = this.viewportHeight / 2 - (1 - ny) * this.viewportHeight * this.scale;
        
        this.model.setViewport({ scale: this.scale, x: this.panX, y: this.panY });
        this.draw();
    }

    // Main draw function
    draw() {
        if (!this.ctx) return;
        
        const ctx = this.ctx;
        const decisions = this.model.getDecisions();
        const clusters = this.model.getClusters();
        const selectedId = this.model.selectedDecisionId;
        const highlightedId = this.model.highlightedDecisionId;
        const relations = this.model.getRelationsForDecision(selectedId);
        
        // Clear
        ctx.clearRect(0, 0, this.viewportWidth, this.viewportHeight);
        ctx.fillStyle = '#0d0d14';
        ctx.fillRect(0, 0, this.viewportWidth, this.viewportHeight);
        
        if (decisions.length === 0) {
            ctx.fillStyle = '#666';
            ctx.font = '14px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('No decisions to display', this.viewportWidth / 2, this.viewportHeight / 2);
            return;
        }
        
        // Draw cluster hulls (background)
        this._drawClusterHulls(ctx, decisions, clusters);
        
        // Draw relation edges (for selected decision)
        if (selectedId && relations.length > 0) {
            this._drawRelations(ctx, selectedId, relations);
        }
        
        // Draw decision points
        this._drawDecisions(ctx, decisions, selectedId, highlightedId);
        
        // Draw legend/info
        this._drawInfo(ctx, decisions);
    }

    _drawClusterHulls(ctx, decisions, clusters) {
        // Group decisions by cluster
        const clusterPoints = {};
        decisions.forEach(d => {
            if (!clusterPoints[d.cluster_id]) clusterPoints[d.cluster_id] = [];
            clusterPoints[d.cluster_id].push(d);
        });
        
        clusters.forEach((cluster, i) => {
            const pts = clusterPoints[cluster.cluster_id];
            if (!pts || pts.length < 3) return;
            
            const color = this.CLUSTER_COLORS[i % this.CLUSTER_COLORS.length];
            
            ctx.beginPath();
            const first = this._dataToScreen(pts[0].x, pts[0].y);
            ctx.moveTo(first.x, first.y);
            
            // Draw convex hull approximation (bounding box for simplicity)
            const xs = pts.map(p => p.x);
            const ys = pts.map(p => p.y);
            const minX = Math.min(...xs);
            const maxX = Math.max(...xs);
            const minY = Math.min(...ys);
            const maxY = Math.max(...ys);
            
            const corners = [
                this._dataToScreen(minX, minY),
                this._dataToScreen(maxX, minY),
                this._dataToScreen(maxX, maxY),
                this._dataToScreen(minX, maxY)
            ];
            
            ctx.moveTo(corners[0].x, corners[0].y);
            for (let j = 1; j < corners.length; j++) {
                ctx.lineTo(corners[j].x, corners[j].y);
            }
            ctx.closePath();
            
            // Fill with low opacity
            const r = parseInt(color.slice(1, 3), 16);
            const g = parseInt(color.slice(3, 5), 16);
            const b = parseInt(color.slice(5, 7), 16);
            ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.08)`;
            ctx.fill();
            
            // Stroke
            ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.3)`;
            ctx.lineWidth = 1;
            ctx.stroke();
        });
    }

    _drawRelations(ctx, sourceId, relations) {
        const sourceDecision = this.model.getDecision(sourceId);
        if (!sourceDecision) return;
        
        const sourcePos = this._dataToScreen(sourceDecision.x, sourceDecision.y);
        
        relations.forEach(rel => {
            const targetDecision = this.model.getDecision(rel.target_id);
            if (!targetDecision) return;
            
            const targetPos = this._dataToScreen(targetDecision.x, targetDecision.y);
            
            // Draw line
            ctx.beginPath();
            ctx.moveTo(sourcePos.x, sourcePos.y);
            ctx.lineTo(targetPos.x, targetPos.y);
            
            // Color by relation kind
            let color = '#7c8aff';
            switch (rel.kind) {
                case 'cites': color = '#ff6b6b'; break;
                case 'cited_by': color = '#51cf66'; break;
                case 'shared_citation': color = '#ffd43b'; break;
                case 'shared_law': color = '#cc5de8'; break;
            }
            
            ctx.strokeStyle = color;
            ctx.lineWidth = 1.5;
            ctx.setLineDash([5, 5]);
            ctx.stroke();
            ctx.setLineDash([]);
            
            // Draw arrowhead
            const angle = Math.atan2(targetPos.y - sourcePos.y, targetPos.x - sourcePos.x);
            const arrowSize = 8;
            ctx.beginPath();
            ctx.moveTo(targetPos.x, targetPos.y);
            ctx.lineTo(
                targetPos.x - arrowSize * Math.cos(angle - Math.PI / 6),
                targetPos.y - arrowSize * Math.sin(angle - Math.PI / 6)
            );
            ctx.moveTo(targetPos.x, targetPos.y);
            ctx.lineTo(
                targetPos.x - arrowSize * Math.cos(angle + Math.PI / 6),
                targetPos.y - arrowSize * Math.sin(angle + Math.PI / 6)
            );
            ctx.strokeStyle = color;
            ctx.lineWidth = 1.5;
            ctx.stroke();
        });
    }

    _drawDecisions(ctx, decisions, selectedId, highlightedId) {
        // Sort: normal first, then highlighted, then selected on top
        const sorted = [...decisions].sort((a, b) => {
            const aSel = a.decision_id === selectedId ? 2 : (a.decision_id === highlightedId ? 1 : 0);
            const bSel = b.decision_id === selectedId ? 2 : (b.decision_id === highlightedId ? 1 : 0);
            return aSel - bSel;
        });
        
        sorted.forEach(d => {
            const isSelected = d.decision_id === selectedId;
            const isHighlighted = d.decision_id === highlightedId;
            const pos = this._dataToScreen(d.x, d.y);
            
            // Skip if off-screen (with margin)
            const margin = 50;
            if (pos.x < -margin || pos.x > this.viewportWidth + margin ||
                pos.y < -margin || pos.y > this.viewportHeight + margin) {
                return;
            }
            
            const radius = (d.radius || 5) * this.scale;
            const isOutlier = d.is_outlier === true;
            const isCited = d.counter_status === 'cited';
            const isCounter = d.counter_status && 
                d.counter_status !== 'none' && 
                d.counter_status !== 'cited' &&
                d.counter_status !== 'supporting-candidate' &&
                d.counter_status !== 'context';
            
            // Draw point
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, Math.max(2, radius), 0, Math.PI * 2);
            
            // Fill color
            let fillColor = d.cluster_color || this.CLUSTER_COLORS[d.cluster_id % this.CLUSTER_COLORS.length];
            if (isOutlier) {
                // Keep cluster color but reduce alpha
                const r = parseInt(fillColor.slice(1, 3), 16);
                const g = parseInt(fillColor.slice(3, 5), 16);
                const b = parseInt(fillColor.slice(5, 7), 16);
                fillColor = `rgba(${r}, ${g}, ${b}, 0.55)`;
            }
            ctx.fillStyle = fillColor;
            ctx.globalAlpha = isOutlier ? 0.55 : (isSelected || isHighlighted ? 1 : 0.9);
            ctx.fill();
            ctx.globalAlpha = 1;
            
            // Stroke for counter/cited/outlier
            let strokeColor = null;
            let strokeWidth = 0;
            
            if (isCounter) {
                strokeColor = this.COUNTER_STATUS_COLORS[d.counter_status] || '#c00';
                strokeWidth = 2.5;
            } else if (isCited) {
                strokeColor = '#ffd43b';
                strokeWidth = 2;
            } else if (isOutlier) {
                strokeColor = '#333';
                strokeWidth = 1;
                ctx.setLineDash([4, 4]);
            } else if (isSelected || isHighlighted) {
                strokeColor = '#fff';
                strokeWidth = 2;
            }
            
            if (strokeColor) {
                ctx.strokeStyle = strokeColor;
                ctx.lineWidth = strokeWidth;
                ctx.stroke();
                ctx.setLineDash([]);
            }
        });
    }

    _drawInfo(ctx, decisions) {
        // Draw stats in corner
        const summary = this.model.getSummary();
        ctx.fillStyle = 'rgba(18, 18, 26, 0.9)';
        ctx.fillRect(10, 10, 280, 80);
        ctx.strokeStyle = '#2a2a3a';
        ctx.strokeRect(10, 10, 280, 80);
        
        ctx.fillStyle = '#7c8aff';
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText(`Decisions: ${summary.n_decisions || decisions.length}`, 20, 30);
        ctx.fillText(`Clusters: ${summary.n_clusters || 0}`, 20, 46);
        ctx.fillText(`Counter: ${summary.n_counter || 0} · Cited: ${summary.n_cited || 0} · Outliers: ${summary.n_outliers || 0}`, 20, 62);
        
        // Legend
        ctx.fillStyle = '#888';
        ctx.font = '10px sans-serif';
        ctx.fillText('● Cluster  ○ Red=Counter  ○ Gold=Cited  ┄ Outlier', 20, 78);
    }

    // Public API
    setUseWebGL(use) {
        this.useWebGL = use;
    }

    getUseWebGL() {
        return this.useWebGL;
    }
}

// Export for both Node and browser
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Canvas2DRenderer;
} else if (typeof window !== 'undefined') {
    window.Canvas2DRenderer = Canvas2DRenderer;
}