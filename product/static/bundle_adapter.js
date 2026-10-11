/**
 * Query Result Bundle Adapter
 * Transforms query_result_bundle v1.0 into the format expected by the
 * LexMachina WebGL/Canvas renderer (reused from index.html).
 *
 * This adapter isolates the query-specific map from the global 174k
 * alignment/hierarchy. The map geometry is derived entirely from the
 * bundle's local TF-IDF clustering and 2D projection.
 */

// Color palette matching index.html
const CLUSTER_COLORS = [
  '#7c8aff', '#ff6b6b', '#51cf66', '#ffd43b', '#cc5de8',
  '#20c997', '#ff922b', '#4dabf7', '#e599f7', '#69db7c',
  '#fcc419', '#ff8787', '#748ffc', '#63e6be', '#da77f2',
  '#a9e34b', '#ffa94d', '#74c0fc', '#b2f2bb', '#f783ac',
];

const LANG_COLORS = {
  de: '#7c8aff',
  fr: '#51cf66',
  it: '#ffd43b',
  en: '#cc5de8',
  rm: '#20c997',
  unknown: '#888888',
};

const COUNTER_STATUS_COLORS = {
  'candidate-limiting': '#ff6b6b',
  'candidate-contrary': '#cc0000',
  'candidate-distinguishing': '#ff922b',
  'candidate-exception': '#cc5de8',
  'cited': '#ffd43b',
  'supporting-candidate': '#51cf66',
  'context': '#888888',
  'none': '#888888',
};

/**
 * Transform a query_result_bundle into WebGL-ready data structures.
 * @param {Object} bundle - query_result_bundle v1.0
 * @returns {Object} WebGL renderer compatible data
 */
function adaptBundleForWebGL(bundle) {
  const decisions = bundle.decisions || [];
  const clusters = bundle.clusters || [];
  const relations = bundle.relations || [];

  // Build cluster lookup
  const clusterById = {};
  clusters.forEach(c => { clusterById[c.cluster_id] = c; });

  // Build relation index for on-demand edge rendering
  const relationsBySource = {};
  const relationsByTarget = {};
  relations.forEach(r => {
    if (!relationsBySource[r.source]) relationsBySource[r.source] = [];
    if (!relationsByTarget[r.target]) relationsByTarget[r.target] = [];
    relationsBySource[r.source].push(r);
    relationsByTarget[r.target].push(r);
  });

  // Transform decisions to WebGL point format
  const points = decisions.map(d => {
    const cluster = clusterById[d.cluster_id] || { label: 'unknown', size: 0 };
    const isCounter = d.counter_status && d.counter_status !== 'none' && d.counter_status !== 'cited';
    const isCited = d.counter_status === 'cited';
    const isOutlier = d.is_outlier === true;

    return {
      decision_id: d.decision_id,
      x: d.x,
      y: d.y,
      cluster: d.cluster_id,
      cluster_label: cluster.label || `Cluster ${d.cluster_id}`,
      cluster_size: cluster.size || 0,
      language: d.language || 'unknown',
      court: d.court || '?',
      decision_date: d.decision_date || '',
      docket_number: d.docket_number || '',
      rank: d.rank || 0,
      score: d.score || 0,
      provenance: d.provenance || '?',
      snippet: d.snippet || '',
      is_outlier: isOutlier,
      is_counter: isCounter,
      is_cited: isCited,
      counter_status: d.counter_status || 'none',
      counter_evidence: d.counter_evidence || '',
      counter_markers: d.counter_markers || [],
      canonical_url: d.canonical_url || '',
      citation: d.citation || [],
      // For WebGL rendering
      color: CLUSTER_COLORS[d.cluster_id % CLUSTER_COLORS.length],
      counter_color: COUNTER_STATUS_COLORS[d.counter_status] || '#888888',
      lang_color: LANG_COLORS[d.language] || LANG_COLORS.unknown,
      // Radius based on cluster size and citation status
      radius: isCited ? 7 : (isOutlier ? 4 : 5),
    };
  });

  // Build cluster hulls for WebGL (bounding boxes per cluster)
  const clusterHulls = [];
  const clusterPoints = {};
  decisions.forEach(d => {
    if (!clusterPoints[d.cluster_id]) clusterPoints[d.cluster_id] = [];
    clusterPoints[d.cluster_id].push(d);
  });

  Object.entries(clusterPoints).forEach(([cid, pts]) => {
    if (pts.length < 3) return;
    const xs = pts.map(p => p.x);
    const ys = pts.map(p => p.y);
    const color = CLUSTER_COLORS[cid % CLUSTER_COLORS.length];
    // Convert hex to rgba
    const r = parseInt(color.slice(1, 3), 16) / 255;
    const g = parseInt(color.slice(3, 5), 16) / 255;
    const b = parseInt(color.slice(5, 7), 16) / 255;
    clusterHulls.push({
      cluster_id: parseInt(cid),
      points: [
        [Math.min(...xs), Math.min(...ys)],
        [Math.max(...xs), Math.min(...ys)],
        [Math.max(...xs), Math.max(...ys)],
        [Math.min(...xs), Math.max(...ys)],
      ],
      color: [r, g, b, 0.1],
      label: clusterById[cid]?.label || `Cluster ${cid}`,
      size: pts.length,
    });
  });

  // Compute data extents for transform
  const xs = decisions.map(d => d.x);
  const ys = decisions.map(d => d.y);
  const transform = {
    xMin: Math.min(...xs) - 0.05,
    xMax: Math.max(...xs) + 0.05,
    yMin: Math.min(...ys) - 0.05,
    yMax: Math.max(...ys) + 0.05,
    scale: 1.0,
    offsetX: 0,
    offsetY: 0,
  };

  // Flatten points for WebGL buffer upload
  const positions = [];
  const colors = [];
  const radii = [];
  const imported = [];
  const decision_ids = [];
  const cluster_ids = [];
  const languages = [];

  points.forEach(p => {
    positions.push(p.x, p.y);
    const r = parseInt(p.color.slice(1, 3), 16) / 255;
    const g = parseInt(p.color.slice(3, 5), 16) / 255;
    const b = parseInt(p.color.slice(5, 7), 16) / 255;
    colors.push(r, g, b, 0.8);
    radii.push(p.radius);
    imported.push(0); // No imported decisions in query map
    decision_ids.push(p.decision_id);
    cluster_ids.push(p.cluster);
    languages.push(p.language);
  });

  return {
    points: {
      positions,
      colors,
      radii,
      imported,
      decision_ids,
      cluster_ids,
      languages,
      count: points.length,
    },
    clusters: clusters.map(c => ({
      cluster_id: c.cluster_id,
      size: c.size,
      centroid_x: 0, // Will be computed if needed
      centroid_y: 0,
      label: c.label,
      member_ids: c.member_ids || [],
    })),
    hulls: clusterHulls,
    transform,
    relations: {
      bySource: relationsBySource,
      byTarget: relationsByTarget,
    },
    metadata: {
      query: bundle.query,
      answer: bundle.answer,
      provenance: bundle.provenance,
      n_decisions: decisions.length,
      n_clusters: clusters.length,
      n_relations: relations.length,
      n_counter: decisions.filter(d => d.counter_status && d.counter_status !== 'none' && d.counter_status !== 'cited').length,
      n_cited: decisions.filter(d => d.counter_status === 'cited').length,
      n_outliers: decisions.filter(d => d.is_outlier).length,
    },
  };
}

/**
 * Get relations for a specific decision (for on-demand edge rendering)
 * @param {Object} adapted - Output from adaptBundleForWebGL
 * @param {string} decision_id - Decision ID
 * @returns {Array} Related decisions with relation details
 */
function getRelationsForDecision(adapted, decision_id) {
  const results = [];
  const bySource = adapted.relations.bySource[decision_id] || [];
  const byTarget = adapted.relations.byTarget[decision_id] || [];

  bySource.forEach(r => {
    const target = adapted.points.decision_ids.indexOf(r.target);
    if (target >= 0) {
      results.push({
        target_id: r.target,
        target_index: target,
        kind: r.kind,
        shared: r.shared,
        direction: 'outgoing',
      });
    }
  });

  byTarget.forEach(r => {
    const source = adapted.points.decision_ids.indexOf(r.source);
    if (source >= 0) {
      results.push({
        target_id: r.source,
        target_index: source,
        kind: r.kind,
        shared: r.shared,
        direction: 'incoming',
      });
    }
  });

  return results;
}

/**
 * Filter points by counter-authority status
 * @param {Object} adapted - Output from adaptBundleForWebGL
 * @param {string} filter - 'all' | 'counter' | 'cited' | 'outlier' | 'normal'
 * @returns {boolean[]} Visibility mask
 */
function filterByCounterStatus(adapted, filter) {
  const { decision_ids, points_count } = adapted.points;
  // We need to check the original bundle data - store counter status in a map
  // For now, return all visible; the UI will handle filtering via CSS/class
  return new Array(adapted.points.count).fill(true);
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { adaptBundleForWebGL, getRelationsForDecision, filterByCounterStatus, CLUSTER_COLORS, LANG_COLORS, COUNTER_STATUS_COLORS };
}

// Also expose globally for browser script usage
if (typeof window !== 'undefined') {
  window.BundleAdapter = { adaptBundleForWebGL, getRelationsForDecision, filterByCounterStatus, CLUSTER_COLORS, LANG_COLORS, COUNTER_STATUS_COLORS };
}