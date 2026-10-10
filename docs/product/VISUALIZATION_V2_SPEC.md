# LexMachina — Product Visualization V2 Specification

Status: CANONICAL PRODUCT SPEC
Owner: Product lane
Scope: visualization, navigation, relational geometry, fractal interaction
Date: 2026-10-10

## 1. Product thesis

LexMachina is not a 3D scatterplot and not a free-flight data visualization.

The canonical experience is a **navigable legal territory**: a Google-Maps-like map of case law whose geography is generated from legally meaningful relations between decisions, whose regions refine as the user zooms, and whose relief exposes an interpretable structural property of the legal graph.

The product must feel like navigating a meaningful legal structure, not merely admiring a 3D point cloud.

A true 3D rendering engine is required. Free orbit / camera rotation is allowed and may be the default if it remains usable. Camera freedom is not itself a product criterion. The decisive criterion is whether the spatial representation makes legally meaningful relations between decisions and regions easier to see, inspect and understand.

## 2. Non-negotiable distinction: legal geometry vs visual geometry

Every spatial dimension or visual feature must have an explicit semantic status.

### 2.1 Legal geometry

The X/Y neighborhood geometry must come from an ACCEPTED or explicitly labelled EXPLORATORY legal representation. For v1.x, the accepted full-scale production geometry remains:

`cited_outcome_hybrid_0.5_174k`

until a better representation passes the frozen evaluation gates.

### 2.2 Relational terrain

The default height field must not be arbitrary decoration. It must be derived from the relation graph active in the current map mode.

Default height semantics:

> **relational cohesion** — areas rise when nearby decisions are densely and strongly connected under the active legal relation graph; valleys appear where connectivity between neighboring regions weakens.

This produces mountains, plateaus, valleys, passes and separate landmasses from the graph itself.

Alternative height overlays may exist, but each must be explicitly named and explained:

- `relational_cohesion` — default;
- `precedent_centrality` — height = citation / lineage centrality;
- `bridge_score` — height or ridge emphasis = decisions linking otherwise distinct communities;
- `novelty` — elevation = structural deviation from established neighborhood;
- `density_visual_only` — permitted only as a clearly marked visual aid, never presented as legal meaning.

No unnamed or unexplained Z-axis is allowed.

## 3. Multiplex relational model

A map mode is defined by a weighted relation graph over decisions.

For decisions i and j:

`W_view(i,j) = Σ_k α_k(view) * R_k(i,j)`

where the available relation layers may include:

- accepted legal-distance / neighborhood affinity;
- precedent citation relation;
- citation role (following / distinguishing / criticizing where supported);
- norms genuinely at issue;
- legal issue / doctrinal similarity;
- reasoning similarity;
- legally relevant fact similarity;
- outcome / holding relation;
- doctrine citations;
- metadata only when intentionally used as context, never as hidden label leakage.

Each view must expose its relation recipe and evidence tier.

No product mode may silently combine layers merely because the resulting map looks better.

## 4. Terrain construction

The rendered territory should emerge in four stages.

### 4.1 Neighborhood graph

From the active representation, construct a sparse weighted k-nearest-neighbor graph. Preserve the strongest meaningful local relations rather than rendering all O(n²) links.

### 4.2 Nested communities

Use the accepted hierarchical / multiresolution clustering pipeline to create nested communities:

corpus → domain → subdomain → issue cluster → microcluster → decisions.

Children must be nested within parents. Zooming reveals children; it must not merely enlarge points.

### 4.3 Region geometry

Each community becomes a geographic region.

The renderer should derive region boundaries from member coordinates and graph structure using a stable polygonal envelope such as alpha-shapes / density contours / graph-aware hulls.

Boundaries must:

- remain stable between nearby zoom levels;
- avoid arbitrary Voronoi-like ownership where evidence is weak;
- allow fuzzy / permeable borders where inter-cluster connectivity is high;
- preserve holes or separated components where the graph genuinely supports them.

### 4.4 Relational height field

At the current zoom level, define node cohesion approximately from weighted same-community relations:

`c_i = Σ_j W(i,j) * 1[community(i)=community(j)]`

and local inter-community coupling:

`b_i = Σ_j W(i,j) * 1[community(i)≠community(j)]`

Generate a continuous terrain field by smoothing these node values spatially.

Default terrain intuition:

- high c, low b → mountain / plateau: internally coherent doctrinal region;
- low c between communities → valley / boundary;
- meaningful high b between communities → pass / corridor;
- high bridge centrality → saddle / ridge marker connecting territories.

The exact formula is an implementation hypothesis and must be tested. The invariant is semantic: **terrain must be generated from relation strength and hierarchical structure, not arbitrary extrusion.**

## 5. Connection geometry — PRIMARY PRODUCT REQUIREMENT

The graph must be visually legible. A user should be able to answer not only “what is near this decision?” but also “what is it connected to, by what kind of relation, and what does it connect across?”

The scene therefore needs explicit relation rendering, without degenerating into edge spaghetti.

### 5.1 At corpus / domain scale

Do not render millions of individual edges.

Aggregate node-level relations into **inter-region corridors**. Corridor width / intensity should encode aggregate relation weight between regions under the active relation layer.

The result should expose:

- strongly isolated legal territories;
- strongly coupled neighboring regions;
- surprising long-range links;
- bridge regions connecting otherwise separated communities.

### 5.2 At cluster scale

Selecting or hovering a cluster reveals its strongest neighboring clusters and the dominant relation types responsible for each connection.

The user should be able to switch relation layers, e.g.:

- legal-neighborhood affinity;
- precedent citations;
- following / distinguishing / criticizing where validated;
- shared norms at issue;
- reasoning similarity;
- fact similarity.

### 5.3 At decision scale

Selecting a decision reveals only a bounded, ranked relation ego-network:

- strongest outgoing citations;
- strongest incoming citations;
- strongest legal-neighborhood edges;
- strongest cross-cluster / bridge relations;
- relation type, direction and strength.

Use different visual encodings for different relation types and directions. Do not draw every available edge.

### 5.4 Lineages and paths

Where citation direction is meaningful, a jurisprudential lineage may be rendered as a directed route through the landscape.

The user should be able to choose a target decision and inspect a relation path or shortest / strongest path through the graph.

### 5.5 Relation-first test

A visualization fails if the user sees a beautiful 3D terrain but cannot inspect the graph relationships that generated or explain it.

## 6. Canonical map modes

### 6.1 Legal / doctrinal map — default

Purpose: answer “what decisions belong to the same legal problem / doctrinal neighborhood?”

Base geometry: current accepted legal-distance representation.

Terrain: relational cohesion.

Status: production only when representation is ACCEPTED.

### 6.2 Precedent / lineage map

Purpose: answer “which decisions belong to the same jurisprudential lineage and how does the line evolve?”

Primary relation: citation graph + citation role where validated.

Terrain: precedent centrality or lineage cohesion.

Until the corpus-scale citation graph passes acceptance, this view must be marked EXPERIMENTAL or unavailable.

### 6.3 Facts map

Purpose: answer “which decisions arise from materially similar factual configurations?”

Primary relation: legally relevant facts.

Terrain: fact-pattern density / cohesion.

Do not ship as production default until evaluated.

### 6.4 Reasoning map

Purpose: answer “which decisions reason in similar ways, even if facts or cited norms differ?”

Primary relation: reasoning / argument representation.

Do not ship as production default until evaluated.

### 6.5 Optional overlays

Overlays may change the visual encoding without changing the underlying map:

- time;
- language;
- chamber;
- court;
- outcome;
- centrality;
- novelty;
- citation direction.

Overlays must not silently change X/Y geometry.

## 7. Interaction model

Camera freedom is allowed. The product may use free orbit if users can control it comfortably. The interaction model must optimize comprehension of relations, not enforce a particular camera ideology.

### 7.1 Core controls

- drag / orbit controls = move the camera naturally;
- wheel / trackpad = zoom;
- pan control = translate focus;
- double-click region = focus / enter the region;
- single click = select;
- Escape / breadcrumb = go back;
- search = drop a pin and fly smoothly to the target;
- hover = lightweight tooltip;
- selected decision = highlight + nearest legal neighbors + strongest typed relations.

### 7.2 Camera

Required:

- perspective camera;
- orbit / tilt / pan / zoom;
- reset and top-down views;
- smooth focus transitions;
- selected-object focus;
- no interaction mode should obscure the selected relation network.

A constrained map mode may be offered if it proves easier to use, but free orbit is not a failure condition and may remain the canonical camera.

The usability criterion is empirical: users must be able to navigate and inspect relations without fighting the camera.

### 7.3 Fractal zoom semantics

Each zoom threshold changes what the user sees:

- Z0: major legal continents / domains;
- Z1: subdomains;
- Z2: doctrinal families;
- Z3: legal issues / currents;
- Z4+: microclusters and decisions.

Transitions should morph parent geometry into child geometry rather than replacing the scene abruptly.

A zoom action must reveal additional legal structure, not merely scale the same set of points.

## 8. Labels and cartographic language

Labels are first-class product output.

At coarse zoom:

- display only region names;
- use stable, short labels;
- avoid covering the terrain.

At finer zoom:

- introduce subregion labels;
- show representative / anchor decisions;
- show decision identifiers only near individual-decision scale.

Labels must be derived from supported metadata / cluster characterization. LLM-generated labels may be used only if provenance is stored and they are clearly treated as generated summaries, not ground truth.

## 9. Selection behavior

Selecting a region should show:

- region label;
- size;
- legal-area distribution;
- languages;
- representative decisions;
- internal cohesion;
- strongest neighboring regions;
- strongest cross-region corridors;
- child regions.

Selecting a decision should show:

- identifier and metadata;
- full text or source link where available;
- its current region path;
- nearest legal neighbors;
- strongest relation types explaining proximity;
- cited / citing decisions;
- “why is this here?” explanation;
- ability to switch map mode while keeping the decision selected.

## 10. Search behavior

Search is spatial.

A successful query should:

1. identify matching decisions;
2. drop pins into the existing map;
3. fly the camera to the relevant area;
4. optionally outline the region containing the best hit;
5. allow “show neighborhood” around a selected result.

Search results must not replace the map with a conventional list-only experience.

## 11. Imported corpora

A user-imported corpus must produce its own persisted territory.

The same decision may occupy a different position in a different corpus because geometry is corpus-relative.

The UI must show which map is active and must never imply that coordinates are globally absolute.

## 12. Rendering architecture

The production renderer must be a genuine 3D scene:

- world-space `vec3` positions;
- perspective projection;
- view matrix / camera transform;
- depth testing;
- GPU point/region rendering;
- LOD;
- viewport / frustum culling;
- picking;
- stable region meshes or terrain tiles.

The current z=0 WebGL renderer is a deprecated performance renderer, not the target visualization.

Recommended architecture:

- GPU-rendered terrain / region meshes;
- GPU instancing for decision points;
- coarse region meshes at distant zoom;
- decision-level points only near appropriate zoom;
- server-side or precomputed hierarchy and region artifacts;
- no recomputation of accepted geometry on ordinary client navigation.

## 13. Performance requirements

At the full 173,963-decision corpus:

- camera interactions must remain responsive;
- ordinary pan/zoom should target >=30 FPS on a normal desktop;
- input-to-camera response should feel immediate (<100–150 ms);
- LOD must prevent all 174k detailed decision objects from being drawn at country zoom;
- coarse scene startup should not wait for all fine-grained artifacts;
- fine detail streams / loads progressively by zoom.

Performance must not be achieved by flattening the map back to 2D.

## 14. Evidence and honesty rules

The visualization must distinguish:

- ACCEPTED legal geometry;
- EXPLORATORY legal geometry;
- visual-only terrain;
- metadata overlays.

A prettier terrain is not evidence of a better legal map.

No visual encoding may imply:

- doctrinal importance;
- precedential authority;
- novelty;
- similarity;
- hierarchy;

unless the underlying metric actually supports that meaning.

## 15. Acceptance criteria for Product Visualization V2

The feature is not accepted merely because it uses WebGL or a 3D camera.

It passes only if all of the following hold:

1. **Relation-readable usability** — navigation may include free orbit, but selecting decisions/regions and inspecting typed relations must be easy and must not require fighting the camera.
2. **True 3D** — world geometry uses nonconstant Z, perspective projection, camera/view transforms and depth testing.
3. **Relational terrain** — default terrain height is generated from an explicitly defined relation/hierarchy field, not random extrusion or cosmetic noise.
4. **Emergent regions** — visible regions / landmasses derive from nested communities and graph relations.
5. **Fractal zoom** — zoom reveals child legal structure and preserves parent-child continuity.
6. **Meaningful corridors** — important inter-region graph relations can be visualized as passes/corridors without edge spaghetti.
7. **Explanation** — a user can inspect why a decision/region is located where it is.
8. **Evidence gating** — unvalidated map modes are visibly experimental and cannot silently replace the accepted production default.
9. **Full-scale viability** — the 173,963-decision production corpus remains navigable through LOD/culling.
10. **Regression tests** — automated tests fail if the renderer regresses to a flat z=0 scatterplot, if typed relation rendering disappears, or if selection cannot reveal a bounded relation ego-network.

## 16. Immediate implementation order

Do not attempt every view simultaneously.

### Milestone A — usable relational terrain on accepted geometry

- keep `cited_outcome_hybrid_0.5_174k` X/Y;
- compute hierarchical region meshes;
- compute relational-cohesion height field from the accepted neighborhood graph;
- usable perspective/orbit camera with reset + top-down;
- zoom / select / focus hierarchy;
- region labels;
- decision and region picking;
- selected decision immediately reveals a bounded typed ego-network.

### Milestone B — relation corridors and explanations

- aggregated cross-region connections visible at coarse scale;
- selected-decision strongest typed relations and directions;
- cluster-to-cluster relation summaries;
- lineage / relation path inspection;
- “why here?” panel;
- breadcrumb / path through hierarchy.

### Milestone C — alternate evidence-backed terrain overlays

- precedent centrality;
- bridge score;
- novelty;
- visual density fallback.

### Milestone D — additional legal map modes

Enable precedent, facts and reasoning maps only as their underlying representations reach the required evidence tier.

## 17. Product test

The key qualitative test is:

> A jurist should be able to open LexMachina, recognize coherent legal territories, select a decision, immediately see its most important typed relations, trace a jurisprudential lineage or bridge into another region, and understand both its neighborhood and the relations that shaped the surrounding geography.

If the user experiences the system as a 3D point cloud with no readable relational structure, the product has failed even if the renderer is technically correct.
