/**
 * Query Map Controller
 * Main entry point that coordinates model, view, and user interactions.
 */

class QueryMapController {
    constructor() {
        this.model = null;
        this.renderer = null;
        this.useWebGL = false;
        this.webglRenderer = null;
        this.canvas = null;
        this.detailPanel = null;
        this.relationLegend = null;
        this.tooltip = null;
        this.initialized = false;
    }

    async init() {
        // Get DOM elements
        this.canvas = document.getElementById('map-canvas');
        this.detailPanel = document.getElementById('detail-panel');
        this.relationLegend = document.getElementById('relation-legend');
        this.tooltip = document.getElementById('tooltip');
        
        // Initialize model
        this.model = new window.QueryMapModel();
        
        // Set up model callbacks
        this.model.onDataLoaded = (vizData) => this._onDataLoaded(vizData);
        this.model.onSelectionChange = (decisionId, wasSelected) => this._onSelectionChange(decisionId, wasSelected);
        this.model.onHighlightChange = (decisionId) => this._onHighlightChange(decisionId);
        this.model.onFilterChange = () => this._onFilterChange();
        this.model.onViewportChange = (viewport) => this._onViewportChange(viewport);
        
        // Initialize renderer (start with Canvas 2D)
        this.renderer = new window.Canvas2DRenderer(this.canvas, this.model);
        
        // Try to initialize WebGL renderer if available
        this._tryInitWebGL();
        
        // Set up UI event listeners
        this._setupUI();
        
        // Load data
        await this.model.loadData();
        
        this.initialized = true;
    }

    _tryInitWebGL() {
        try {
            if (window.WebGLRenderer) {
                this.webglRenderer = new window.WebGLRenderer(this.canvas);
                if (this.webglRenderer && this.webglRenderer.gl) {
                    console.log('WebGL renderer available');
                    // We'll switch to it when user toggles
                } else {
                    this.webglRenderer = null;
                }
            }
        } catch (e) {
            console.warn('WebGL initialization failed:', e);
            this.webglRenderer = null;
        }
    }

    _setupUI() {
        // Counter filter
        const counterFilter = document.getElementById('counter-filter');
        counterFilter.addEventListener('change', (e) => {
            this.model.setCounterFilter(e.target.value);
        });

        // Language toggles - will be populated after data load
        this._setupLanguageToggles();

        // Search
        const searchInput = document.getElementById('search-input');
        const searchLang = document.getElementById('search-lang');
        
        let searchDebounce = null;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchDebounce);
            searchDebounce = setTimeout(() => {
                this.model.setSearchQuery(e.target.value, searchLang.value);
            }, 150);
        });
        
        searchLang.addEventListener('change', (e) => {
            this.model.setSearchQuery(searchInput.value, e.target.value);
        });

        // Zoom controls
        document.querySelectorAll('#zoom-controls .zoom-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                switch (action) {
                    case 'fit': this.renderer.fitToData(); break;
                    case 'reset': this.renderer.resetView(); break;
                    case 'zoom-in': this.renderer.zoomIn(); break;
                    case 'zoom-out': this.renderer.zoomOut(); break;
                }
            });
        });

        // Renderer toggle
        const rendererToggle = document.getElementById('renderer-toggle');
        rendererToggle.addEventListener('click', () => {
            this._toggleRenderer();
        });

        // Detail panel close
        document.getElementById('detail-close').addEventListener('click', () => {
            this.model.clearSelection();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
            
            switch (e.key) {
                case 'Escape':
                    this.model.clearSelection();
                    break;
                case '0':
                    this.renderer.fitToData();
                    break;
                case '1':
                case '2':
                case '3':
                case '4':
                    // Zoom levels could be implemented
                    break;
                case '+':
                case '=':
                    this.renderer.zoomIn();
                    break;
                case '-':
                    this.renderer.zoomOut();
                    break;
            }
        });

        // Click outside detail panel to close
        document.addEventListener('click', (e) => {
            if (this.detailPanel.classList.contains('visible') &&
                !this.detailPanel.contains(e.target) &&
                !this.canvas.contains(e.target)) {
                this.model.clearSelection();
            }
        });
    }

    _setupLanguageToggles() {
        const container = document.getElementById('lang-toggles');
        if (!container) return;
        
        const languages = this.model.getSummary().languages || ['de', 'fr', 'it'];
        const langLabels = { de: 'DE', fr: 'FR', it: 'IT' };
        const langColors = { de: '#4dabf7', fr: '#ffd43b', it: '#51cf66' };
        
        container.innerHTML = '';
        languages.forEach(lang => {
            const btn = document.createElement('button');
            btn.className = 'lang-btn active';
            btn.dataset.lang = lang;
            btn.innerHTML = `<span class="lang-dot" style="background:${langColors[lang]}"></span>${langLabels[lang]}`;
            btn.addEventListener('click', () => {
                btn.classList.toggle('active');
                const active = Array.from(container.querySelectorAll('.lang-btn.active')).map(b => b.dataset.lang);
                this.model.setActiveLanguages(active);
            });
            container.appendChild(btn);
        });
    }

    _onDataLoaded(vizData) {
        console.log('Data loaded:', vizData.n_decisions, 'decisions,', vizData.n_clusters, 'clusters');
        
        // Update stats
        this._updateStats(vizData);
        
        // Populate cluster list
        this._renderClusterList(vizData.clusters);
        
        // Set up language toggles now that we have data
        this._setupLanguageToggles();
        
        // Fit to data
        this.renderer.fitToData();
        
        // Initial draw
        this.renderer.draw();
    }

    _updateStats(vizData) {
        document.getElementById('stat-total').textContent = vizData.n_decisions || 0;
        document.getElementById('stat-clusters').textContent = vizData.n_clusters || 0;
        document.getElementById('stat-counter').textContent = vizData.n_counter || 0;
        document.getElementById('stat-cited').textContent = vizData.n_cited || 0;
    }

    _renderClusterList(clusters) {
        const container = document.getElementById('cluster-list');
        if (!container) return;
        
        if (!clusters || clusters.length === 0) {
            container.innerHTML = '<div id="empty-state">No clusters</div>';
            return;
        }
        
        container.innerHTML = clusters.map((cluster, i) => {
            const color = this.renderer.CLUSTER_COLORS[i % this.renderer.CLUSTER_COLORS.length];
            const counterCount = cluster.counter_count || 0;
            const outlierCount = cluster.outlier_count || 0;
            const citedCount = cluster.cited_count || 0;
            
            return `
                <div class="cluster-card" data-cluster-id="${cluster.cluster_id}">
                    <div class="cluster-header">
                        <span class="cluster-id" style="color: ${color}">Cluster ${cluster.cluster_id}</span>
                        <span class="cluster-size">${cluster.size} decisions</span>
                    </div>
                    <div class="cluster-samples">${cluster.label}</div>
                    <div class="cluster-stats">
                        ${counterCount > 0 ? `<span class="cluster-stat"><span class="cluster-stat-dot" style="background:#ff6b6b"></span>${counterCount} counter</span>` : ''}
                        ${citedCount > 0 ? `<span class="cluster-stat"><span class="cluster-stat-dot" style="background:#ffd43b"></span>${citedCount} cited</span>` : ''}
                        ${outlierCount > 0 ? `<span class="cluster-stat"><span class="cluster-stat-dot" style="background:#888"></span>${outlierCount} outliers</span>` : ''}
                    </div>
                </div>
            `;
        }).join('');
        
        // Add click handlers
        container.querySelectorAll('.cluster-card').forEach(card => {
            card.addEventListener('click', () => {
                const clusterId = parseInt(card.dataset.clusterId);
                this._zoomToCluster(clusterId);
                
                // Highlight card
                container.querySelectorAll('.cluster-card').forEach(c => c.classList.remove('active'));
                card.classList.add('active');
            });
        });
    }

    _onSelectionChange(decisionId, wasSelected) {
        if (decisionId) {
            this._showDetail(decisionId);
            this._showRelations(decisionId);
        } else {
            this._hideDetail();
            this._hideRelations();
        }
        
        // Re-render to show selection highlight
        this.renderer.draw();
    }

    _onHighlightChange(decisionId) {
        // Update tooltip
        if (decisionId) {
            const decision = this.model.getDecision(decisionId);
            if (decision) {
                this._showTooltip(decision);
            }
        } else {
            this._hideTooltip();
        }
        
        // Re-render to show highlight
        this.renderer.draw();
    }

    _onFilterChange() {
        // Update cluster list counts
        this._renderClusterList(this.model.getClusters());
        
        // Update stats
        const summary = this.model.getSummary();
        this._updateStats({
            n_decisions: this.model.getFilteredCount(),
            n_clusters: summary.n_clusters,
            n_counter: summary.n_counter,
            n_cited: summary.n_cited
        });
        
        // Re-render
        this.renderer.draw();
    }

    _onViewportChange(viewport) {
        // Could update minimap or other viewport-dependent UI
    }

    _showDetail(decisionId) {
        const decision = this.model.getDecision(decisionId);
        if (!decision) return;
        
        const cluster = this.model.getClusters().find(c => c.cluster_id === decision.cluster_id);
        const bundle = this.model.getBundle();
        const answer = this.model.getAnswer();
        
        let html = `
            <div class="detail-field">
                <div class="detail-label">Decision ID</div>
                <div class="detail-value">${decision.decision_id}</div>
            </div>
            <div class="detail-field">
                <div class="detail-label">Court / Language / Date</div>
                <div class="detail-value">${decision.court} · ${decision.language} · ${decision.decision_date}</div>
            </div>
            <div class="detail-field">
                <div class="detail-label">Docket</div>
                <div class="detail-value">${decision.docket_number}</div>
            </div>
            <div class="detail-field">
                <div class="detail-label">Rank / Score</div>
                <div class="detail-value">Rank ${decision.rank} · Score ${decision.score?.toFixed(5) || 'N/A'}</div>
            </div>
            <div class="detail-field">
                <div class="detail-label">Cluster</div>
                <div class="detail-value">C${decision.cluster_id} - ${cluster?.label || 'Unknown'}</div>
            </div>
        `;
        
        // Status badges
        const badges = [];
        if (decision.counter_status === 'cited') {
            badges.push('<span class="detail-badge cited">Cited in Answer</span>');
        } else if (decision.counter_status && decision.counter_status !== 'none') {
            badges.push(`<span class="detail-badge counter">${decision.counter_label || decision.counter_status}</span>`);
        }
        if (decision.is_outlier) {
            badges.push('<span class="detail-badge outlier">Outlier</span>');
        }
        if (badges.length > 0) {
            html += `<div class="detail-field"><div class="detail-label">Status</div><div class="detail-value">${badges.join(' ')}</div></div>`;
        }
        
        // Snippet
        if (decision.snippet) {
            html += `
                <div class="detail-field">
                    <div class="detail-label">Snippet</div>
                    <div class="detail-value" style="white-space: pre-wrap; font-size: 11px; line-height: 1.5;">${this._escapeHtml(decision.snippet.slice(0, 500))}…</div>
                </div>
            `;
        }
        
        // Counter evidence
        if (decision.counter_evidence) {
            html += `
                <div class="detail-field">
                    <div class="detail-label">Counter Evidence</div>
                    <div class="detail-value" style="font-style: italic; color: #ff6b6b;">${this._escapeHtml(decision.counter_evidence)}</div>
                </div>
            `;
        }
        
        // Citations
        if (decision.citation && decision.citation.length > 0) {
            html += `
                <div class="detail-section">
                    <div class="detail-section-title">Citations</div>
                    <div class="detail-value">${decision.citation.map(c => this._escapeHtml(c)).join('<br>')}</div>
                </div>
            `;
        }
        
        // Source link
        if (decision.canonical_url) {
            html += `
                <div class="detail-field" style="margin-top: 16px; padding-top: 12px; border-top: 1px solid #2a2a3a;">
                    <a href="${decision.canonical_url}" target="_blank" rel="noopener">Open Source ↗</a>
                </div>
            `;
        }
        
        document.getElementById('detail-title').textContent = decision.decision_id;
        document.getElementById('detail-body').innerHTML = html;
        this.detailPanel.classList.add('visible');
    }

    _hideDetail() {
        this.detailPanel.classList.remove('visible');
    }

    _showRelations(decisionId) {
        const relations = this.model.getRelationsForDecision(decisionId);
        if (!relations || relations.length === 0) {
            this._hideRelations();
            return;
        }
        
        const list = document.getElementById('relation-list');
        list.innerHTML = relations.map(rel => {
            const target = this.model.getDecision(rel.target_id);
            if (!target) return '';
            
            const kindLabels = {
                'cites': 'Cites',
                'cited_by': 'Cited by',
                'shared_citation': 'Shared Citation',
                'shared_law': 'Shared Law'
            };
            
            return `
                <div class="relation-item" data-target-id="${rel.target_id}">
                    <div>
                        <div class="relation-target">${target.decision_id}</div>
                        <div class="relation-kind">${kindLabels[rel.kind] || rel.kind}</div>
                        ${rel.shared && rel.shared.length > 0 ? `<div class="relation-shared">Shared: ${rel.shared.slice(0, 3).join(', ')}${rel.shared.length > 3 ? '…' : ''}</div>` : ''}
                    </div>
                </div>
            `;
        }).join('');
        
        // Add click handlers for relation items
        list.querySelectorAll('.relation-item').forEach(item => {
            item.addEventListener('click', () => {
                const targetId = item.dataset.targetId;
                this.model.selectDecision(targetId);
            });
        });
        
        this.relationLegend.classList.remove('hidden');
    }

    _hideRelations() {
        this.relationLegend.classList.add('hidden');
    }

    _showTooltip(decision) {
        const pos = this.renderer._dataToScreen(decision.x, decision.y);
        this.tooltip.style.left = `${pos.x + 15}px`;
        this.tooltip.style.top = `${pos.y - 10}px`;
        
        let html = `<div class="tooltip-id">${decision.decision_id}</div>`;
        html += `<div class="tooltip-info">${decision.court} · ${decision.language} · ${decision.decision_date}</div>`;
        
        if (decision.counter_status && decision.counter_status !== 'none') {
            const label = decision.counter_label || decision.counter_status;
            html += `<div class="tooltip-counter">${label}</div>`;
        }
        if (decision.is_outlier) {
            html += `<div class="tooltip-outlier">Outlier</div>`;
        }
        
        this.tooltip.innerHTML = html;
        this.tooltip.classList.remove('hidden');
    }

    _hideTooltip() {
        this.tooltip.classList.add('hidden');
    }

    _zoomToCluster(clusterId) {
        this.renderer._zoomToCluster(clusterId);
    }

    _toggleRenderer() {
        const toggleBtn = document.getElementById('renderer-toggle');
        
        if (!this.useWebGL && this.webglRenderer) {
            // Switch to WebGL
            this.useWebGL = true;
            toggleBtn.textContent = 'Canvas2D';
            toggleBtn.classList.add('active');
            // Note: Full WebGL integration would require more work
            // For now, we just show the toggle works
            console.log('WebGL toggle: would switch to WebGL renderer');
        } else {
            // Switch to Canvas 2D
            this.useWebGL = false;
            toggleBtn.textContent = 'WebGL';
            toggleBtn.classList.remove('active');
            this.renderer.draw();
        }
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.queryMapController = new QueryMapController();
    window.queryMapController.init().catch(err => {
        console.error('Failed to initialize query map:', err);
        document.getElementById('cluster-list').innerHTML = 
            `<div id="empty-state" style="color: #ff6b6b;">Failed to load map data: ${err.message}</div>`;
    });
});

// Expose for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = QueryMapController;
} else if (typeof window !== 'undefined') {
    window.QueryMapController = QueryMapController;
}