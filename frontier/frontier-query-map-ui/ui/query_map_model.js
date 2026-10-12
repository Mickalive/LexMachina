/**
 * Query Map Model
 * Handles data loading, state management, and provides an API for the UI controller.
 */

class QueryMapModel {
    constructor() {
        this.vizData = null;
        this.bundleData = null;
        this.relationsIndex = null;
        this.filteredDecisionIds = new Set();
        this.selectedDecisionId = null;
        this.highlightedDecisionId = null;
        this.counterFilter = 'all'; // all, counter, cited, outlier, normal
        this.activeLanguages = new Set(['de', 'fr', 'it']);
        this.searchQuery = '';
        this.searchLang = '';
        
        // Viewport state
        this.viewport = {
            x: 0,
            y: 0,
            scale: 1,
            width: 0,
            height: 0
        };
        
        // Callbacks
        this.onDataLoaded = null;
        this.onSelectionChange = null;
        this.onHighlightChange = null;
        this.onFilterChange = null;
        this.onViewportChange = null;
    }

    /**
     * Load visualization data from the server
     */
    async loadData() {
        try {
            const [vizRes, bundleRes] = await Promise.all([
                fetch('/data/visualization.json'),
                fetch('/data/bundle.json')
            ]);
            
            if (!vizRes.ok) throw new Error(`Failed to load visualization: ${vizRes.status}`);
            if (!bundleRes.ok) throw new Error(`Failed to load bundle: ${bundleRes.status}`);
            
            this.vizData = await vizRes.json();
            this.bundleData = await bundleRes.json();
            
            // Build relations index for fast lookup
            this._buildRelationsIndex();
            
            // Initialize filtered set to all decisions
            this.filteredDecisionIds = new Set(this.vizData.decisions.map(d => d.decision_id));
            
            // Notify listeners
            if (this.onDataLoaded) {
                this.onDataLoaded(this.vizData);
            }
            
            return this.vizData;
        } catch (error) {
            console.error('Failed to load map data:', error);
            throw error;
        }
    }

    /**
     * Build relations index for on-demand edge rendering
     */
    _buildRelationsIndex() {
        if (!this.vizData || !this.vizData.relations) return;
        
        this.relationsIndex = {
            bySource: {},
            byTarget: {}
        };
        
        this.vizData.relations.forEach(r => {
            if (!this.relationsIndex.bySource[r.source]) {
                this.relationsIndex.bySource[r.source] = [];
            }
            if (!this.relationsIndex.byTarget[r.target]) {
                this.relationsIndex.byTarget[r.target] = [];
            }
            this.relationsIndex.bySource[r.source].push(r);
            this.relationsIndex.byTarget[r.target].push(r);
        });
    }

    /**
     * Get all decisions (for rendering)
     */
    getDecisions() {
        if (!this.vizData) return [];
        return this.vizData.decisions.filter(d => this.filteredDecisionIds.has(d.decision_id));
    }

    /**
     * Get clusters
     */
    getClusters() {
        if (!this.vizData) return [];
        return this.vizData.clusters;
    }

    /**
     * Get relations for a specific decision
     */
    getRelationsForDecision(decisionId) {
        if (!this.relationsIndex) return [];
        
        const results = [];
        
        const bySource = this.relationsIndex.bySource[decisionId] || [];
        const byTarget = this.relationsIndex.byTarget[decisionId] || [];
        
        // Create a map of decision_id to index for fast lookup
        const decisionIndex = new Map();
        this.vizData.decisions.forEach((d, i) => {
            decisionIndex.set(d.decision_id, i);
        });
        
        bySource.forEach(r => {
            const targetIdx = decisionIndex.get(r.target);
            if (targetIdx !== undefined) {
                results.push({
                    target_id: r.target,
                    target_index: targetIdx,
                    kind: r.kind,
                    shared: r.shared || [],
                    direction: 'outgoing'
                });
            }
        });
        
        byTarget.forEach(r => {
            const sourceIdx = decisionIndex.get(r.source);
            if (sourceIdx !== undefined) {
                results.push({
                    target_id: r.source,
                    target_index: sourceIdx,
                    kind: r.kind,
                    shared: r.shared || [],
                    direction: 'incoming'
                });
            }
        });
        
        return results;
    }

    /**
     * Get a decision by ID
     */
    getDecision(decisionId) {
        if (!this.vizData) return null;
        return this.vizData.decisions.find(d => d.decision_id === decisionId) || null;
    }

    /**
     * Get the bundle data (for answer, provenance, etc.)
     */
    getBundle() {
        return this.bundleData;
    }

    /**
     * Get answer information
     */
    getAnswer() {
        return this.vizData?.answer || this.bundleData?.answer || { prose: '', statements: [], cited_decision_ids: [] };
    }

    /**
     * Get provenance information
     */
    getProvenance() {
        return this.vizData?.provenance || this.bundleData?.provenance || {};
    }

    /**
     * Get summary statistics
     */
    getSummary() {
        if (!this.vizData) return {};
        return this.vizData.summary || {
            n_decisions: this.vizData.n_decisions || 0,
            n_clusters: this.vizData.n_clusters || 0,
            n_relations: this.vizData.n_relations || 0,
            n_counter: this.vizData.n_counter || 0,
            n_cited: this.vizData.n_cited || 0,
            n_outliers: this.vizData.n_outliers || 0,
            languages: this.vizData.languages || []
        };
    }

    /**
     * Get bounds for fit-to-data
     */
    getBounds() {
        return this.vizData?.bounds || { x_min: -1, x_max: 1, y_min: -1, y_max: 1 };
    }

    /**
     * Set counter filter
     */
    setCounterFilter(filter) {
        this.counterFilter = filter;
        this._applyFilters();
        
        if (this.onFilterChange) {
            this.onFilterChange(this.counterFilter, this.activeLanguages, this.searchQuery);
        }
    }

    /**
     * Set active languages
     */
    setActiveLanguages(languages) {
        this.activeLanguages = new Set(languages);
        this._applyFilters();
        
        if (this.onFilterChange) {
            this.onFilterChange(this.counterFilter, this.activeLanguages, this.searchQuery);
        }
    }

    /**
     * Set search query
     */
    setSearchQuery(query, lang = '') {
        this.searchQuery = query.toLowerCase().trim();
        this.searchLang = lang;
        this._applyFilters();
        
        if (this.onFilterChange) {
            this.onFilterChange(this.counterFilter, this.activeLanguages, this.searchQuery);
        }
    }

    /**
     * Apply all filters to the decision set
     */
    _applyFilters() {
        if (!this.vizData) return;
        
        const newFiltered = new Set();
        
        this.vizData.decisions.forEach(d => {
            // Counter filter
            let passesCounter = true;
            switch (this.counterFilter) {
                case 'counter':
                    passesCounter = d.counter_status && 
                        d.counter_status !== 'none' && 
                        d.counter_status !== 'cited' &&
                        d.counter_status !== 'supporting-candidate' &&
                        d.counter_status !== 'context';
                    break;
                case 'cited':
                    passesCounter = d.counter_status === 'cited';
                    break;
                case 'outlier':
                    passesCounter = d.is_outlier === true;
                    break;
                case 'normal':
                    passesCounter = d.counter_status === 'none' || 
                        d.counter_status === 'supporting-candidate' || 
                        d.counter_status === 'context';
                    break;
                case 'all':
                default:
                    passesCounter = true;
            }
            
            // Language filter
            const passesLanguage = this.activeLanguages.has(d.language);
            
            // Search filter
            let passesSearch = true;
            if (this.searchQuery) {
                const searchable = [
                    d.decision_id,
                    d.cluster_label,
                    d.snippet,
                    d.court,
                    d.docket_number,
                    d.citation?.join(' ') || ''
                ].join(' ').toLowerCase();
                passesSearch = searchable.includes(this.searchQuery);
                
                if (this.searchLang && d.language !== this.searchLang) {
                    passesSearch = false;
                }
            }
            
            if (passesCounter && passesLanguage && passesSearch) {
                newFiltered.add(d.decision_id);
            }
        });
        
        this.filteredDecisionIds = newFiltered;
    }

    /**
     * Select a decision
     */
    selectDecision(decisionId) {
        const wasSelected = this.selectedDecisionId === decisionId;
        this.selectedDecisionId = decisionId;
        
        if (this.onSelectionChange) {
            this.onSelectionChange(decisionId, wasSelected);
        }
    }

    /**
     * Clear selection
     */
    clearSelection() {
        this.selectedDecisionId = null;
        if (this.onSelectionChange) {
            this.onSelectionChange(null, false);
        }
    }

    /**
     * Highlight a decision (hover)
     */
    highlightDecision(decisionId) {
        this.highlightedDecisionId = decisionId;
        if (this.onHighlightChange) {
            this.onHighlightChange(decisionId);
        }
    }

    /**
     * Clear highlight
     */
    clearHighlight() {
        this.highlightedDecisionId = null;
        if (this.onHighlightChange) {
            this.onHighlightChange(null);
        }
    }

    /**
     * Check if a decision is selected
     */
    isSelected(decisionId) {
        return this.selectedDecisionId === decisionId;
    }

    /**
     * Check if a decision is highlighted
     */
    isHighlighted(decisionId) {
        return this.highlightedDecisionId === decisionId;
    }

    /**
     * Check if a decision is filtered (visible)
     */
    isVisible(decisionId) {
        return this.filteredDecisionIds.has(decisionId);
    }

    /**
     * Update viewport
     */
    setViewport(viewport) {
        this.viewport = { ...this.viewport, ...viewport };
        if (this.onViewportChange) {
            this.onViewportChange(this.viewport);
        }
    }

    /**
     * Get current viewport
     */
    getViewport() {
        return { ...this.viewport };
    }

    /**
     * Get filtered decision count
     */
    getFilteredCount() {
        return this.filteredDecisionIds.size;
    }

    /**
     * Get all data for renderer
     */
    getRenderData() {
        return {
            decisions: this.getDecisions(),
            clusters: this.getClusters(),
            relations: this.vizData?.relations || [],
            bounds: this.getBounds(),
            viewport: this.getViewport(),
            selectedId: this.selectedDecisionId,
            highlightedId: this.highlightedDecisionId,
            filteredIds: this.filteredDecisionIds
        };
    }
}

// Export for both Node and browser
if (typeof module !== 'undefined' && module.exports) {
    module.exports = QueryMapModel;
} else if (typeof window !== 'undefined') {
    window.QueryMapModel = QueryMapModel;
}