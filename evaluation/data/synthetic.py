"""
Synthetic Data Generator for Evaluation Testing

Generates synthetic legal decisions with known structure for testing
evaluation framework without requiring real corpus data.
"""

import numpy as np
import random
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib


@dataclass
class SyntheticDecision:
    """A synthetic legal decision with known properties."""
    decision_id: str
    docket_number: str
    date: str
    language: str
    court: str = "bger"
    chamber: Optional[str] = None
    legal_area: Optional[str] = None
    jurivoc_descriptors: List[str] = field(default_factory=list)
    cited_decisions: List[str] = field(default_factory=list)
    citing_decisions: List[str] = field(default_factory=list)
    outcome: Optional[str] = None
    full_text: str = ""
    embedding: Optional[np.ndarray] = None


@dataclass
class SyntheticCorpusConfig:
    """Configuration for synthetic corpus generation."""
    num_decisions: int = 500
    num_legal_areas: int = 10
    num_jurivoc_concepts: int = 50
    num_languages: int = 3
    citation_density: float = 0.02
    multilingual_fraction: float = 0.1
    embedding_dim: int = 384
    cluster_separation: float = 2.0
    noise_level: float = 0.1
    random_seed: int = 42


class SyntheticCorpusGenerator:
    """
    Generates a synthetic corpus of legal decisions with known ground truth structure.
    
    The corpus has:
    - Legal areas (domains) that form top-level clusters
    - Jurivoc descriptors that form sub-clusters within legal areas
    - Citation graph that follows legal area / Jurivoc structure
    - Multilingual parallel versions of some decisions
    - Known embeddings that respect the legal structure
    """

    def __init__(self, config: Optional[SyntheticCorpusConfig] = None):
        self.config = config or SyntheticCorpusConfig()
        random.seed(self.config.random_seed)
        np.random.seed(self.config.random_seed)

        self.decisions: Dict[str, SyntheticDecision] = {}
        self.legal_areas = [f"Area_{i:02d}" for i in range(self.config.num_legal_areas)]
        self.jurivoc_concepts = [f"JV_{i:04d}" for i in range(self.config.num_jurivoc_concepts)]
        self.languages = ["de", "fr", "it"][:self.config.num_languages]

        # Map legal areas to Jurivoc concepts (each area has ~5 concepts)
        self.area_to_jurivoc = {}
        concepts_per_area = max(1, self.config.num_jurivoc_concepts // self.config.num_legal_areas)
        for i, area in enumerate(self.legal_areas):
            start = i * concepts_per_area
            end = min(start + concepts_per_area, self.config.num_jurivoc_concepts)
            self.area_to_jurivoc[area] = self.jurivoc_concepts[start:end]

        # Generate cluster centers in embedding space
        self.area_centers = self._generate_area_centers()
        self.jurivoc_centers = self._generate_jurivoc_centers()

    def _generate_area_centers(self) -> Dict[str, np.ndarray]:
        """Generate well-separated cluster centers for legal areas."""
        centers = {}
        dim = self.config.embedding_dim
        
        # Use spherical distribution for good separation
        for i, area in enumerate(self.legal_areas):
            # Generate random direction
            vec = np.random.randn(dim)
            vec = vec / np.linalg.norm(vec)
            # Scale by separation factor
            centers[area] = vec * self.config.cluster_separation
        
        return centers

    def _generate_jurivoc_centers(self) -> Dict[str, np.ndarray]:
        """Generate Jurivoc centers near their legal area centers."""
        centers = {}
        dim = self.config.embedding_dim
        
        for area, concepts in self.area_to_jurivoc.items():
            area_center = self.area_centers[area]
            for concept in concepts:
                # Small perturbation from area center
                perturbation = np.random.randn(dim) * 0.3
                vec = area_center + perturbation
                vec = vec / np.linalg.norm(vec) * self.config.cluster_separation
                centers[concept] = vec
        
        return centers

    def generate(self) -> Dict[str, SyntheticDecision]:
        """Generate the full synthetic corpus."""
        self.decisions = {}

        # Step 1: Generate base decisions (one per Jurivoc concept, plus extras)
        base_decisions = []
        for concept in self.jurivoc_concepts:
            area = self._get_area_for_jurivoc(concept)
            decision = self._create_decision(
                legal_area=area,
                jurivoc_descriptors=[concept],
                language=random.choice(self.languages),
            )
            base_decisions.append(decision)
            self.decisions[decision.decision_id] = decision

        # Step 2: Generate additional decisions to reach target count
        while len(self.decisions) < self.config.num_decisions:
            area = random.choice(self.legal_areas)
            concepts = random.sample(self.area_to_jurivoc[area], k=random.randint(1, 3))
            decision = self._create_decision(
                legal_area=area,
                jurivoc_descriptors=concepts,
                language=random.choice(self.languages),
            )
            self.decisions[decision.decision_id] = decision

        # Step 3: Add multilingual parallel versions
        self._add_multilingual_versions()

        # Step 4: Generate citation graph
        self._generate_citations()

        # Step 5: Generate embeddings
        self._generate_embeddings()

        # Step 6: Generate boilerplate-heavy texts
        self._generate_texts()

        return self.decisions

    def _get_area_for_jurivoc(self, concept: str) -> str:
        """Find legal area for a Jurivoc concept."""
        for area, concepts in self.area_to_jurivoc.items():
            if concept in concepts:
                return area
        return random.choice(self.legal_areas)

    def _create_decision(
        self,
        legal_area: str,
        jurivoc_descriptors: List[str],
        language: str,
    ) -> SyntheticDecision:
        """Create a single synthetic decision."""
        # Generate unique ID
        counter = len(self.decisions)
        decision_id = f"syn_{legal_area}_{counter:05d}"
        docket_number = f"{legal_area}_{counter:05d}/2024"
        
        # Random date in 2020-2024
        year = random.randint(2020, 2024)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        date = f"{year}-{month:02d}-{day:02d}"

        # Chamber based on legal area
        chamber = f"Chamber_{self.legal_areas.index(legal_area) % 5 + 1}"

        # Outcome
        outcomes = ["approved", "dismissed", "partially_approved", "referred_back"]
        outcome = random.choice(outcomes)

        return SyntheticDecision(
            decision_id=decision_id,
            docket_number=docket_number,
            date=date,
            language=language,
            court="bger",
            chamber=chamber,
            legal_area=legal_area,
            jurivoc_descriptors=jurivoc_descriptors,
            outcome=outcome,
        )

    def _add_multilingual_versions(self):
        """Add parallel language versions for some decisions."""
        base_decisions = list(self.decisions.values())
        num_multilingual = int(len(base_decisions) * self.config.multilingual_fraction)
        
        for decision in random.sample(base_decisions, num_multilingual):
            for lang in self.languages:
                if lang != decision.language:
                    # Create parallel version
                    parallel_id = f"{decision.decision_id}_{lang}"
                    parallel = SyntheticDecision(
                        decision_id=parallel_id,
                        docket_number=decision.docket_number,
                        date=decision.date,
                        language=lang,
                        court=decision.court,
                        chamber=decision.chamber,
                        legal_area=decision.legal_area,
                        jurivoc_descriptors=decision.jurivoc_descriptors.copy(),
                        outcome=decision.outcome,
                    )
                    self.decisions[parallel_id] = parallel

    def _generate_citations(self):
        """Generate citation graph following legal structure."""
        decision_ids = list(self.decisions.keys())
        
        for citing_id in decision_ids:
            citing = self.decisions[citing_id]
            # Each decision cites ~5% of earlier decisions in same/related area
            num_citations = max(1, int(len(decision_ids) * self.config.citation_density))
            
            # Prefer citations within same legal area
            same_area = [
                d for d in decision_ids 
                if d != citing_id and self.decisions[d].legal_area == citing.legal_area
            ]
            other_area = [
                d for d in decision_ids 
                if d != citing_id and self.decisions[d].legal_area != citing.legal_area
            ]
            
            # 70% same area, 30% other
            same_count = int(num_citations * 0.7)
            other_count = num_citations - same_count
            
            cited = []
            if same_area:
                cited.extend(random.sample(same_area, min(same_count, len(same_area))))
            if other_area:
                cited.extend(random.sample(other_area, min(other_count, len(other_area))))
            
            citing.cited_decisions = cited
            for cited_id in cited:
                self.decisions[cited_id].citing_decisions.append(citing_id)

    def _generate_embeddings(self):
        """Generate embeddings that respect the legal structure."""
        for decision in self.decisions.values():
            # Base embedding from Jurivoc concepts
            if decision.jurivoc_descriptors:
                concept_vecs = [self.jurivoc_centers[c] for c in decision.jurivoc_descriptors if c in self.jurivoc_centers]
                if concept_vecs:
                    base_emb = np.mean(concept_vecs, axis=0)
                else:
                    area = decision.legal_area
                    base_emb = self.area_centers.get(area, np.zeros(self.config.embedding_dim))
            else:
                area = decision.legal_area
                base_emb = self.area_centers.get(area, np.zeros(self.config.embedding_dim))

            # Add noise
            noise = np.random.randn(self.config.embedding_dim) * self.config.noise_level
            embedding = base_emb + noise
            
            # Normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            decision.embedding = embedding.astype(np.float32)

    def _generate_texts(self):
        """Generate synthetic full texts with boilerplate and legal content."""
        boilerplate_de = [
            "Das Bundesgericht zieht in Erwägung:",
            "Gemäss Art. 29 BV hat jede Person Anspruch auf rechtliches Gehör.",
            "Die Beschwerde ist fristgerecht eingereicht worden.",
            "Die Parteien haben keine Kosten zu erstatten.",
            "Dieses Urteil wird den Parteien mitgeteilt.",
        ]
        boilerplate_fr = [
            "Le Tribunal fédéral considère:",
            "Selon l'art. 29 Cst., toute personne a droit à une procédure judiciaire équitable.",
            "Le recours a été déposé dans les délais.",
            "Les parties n'ont pas de frais à rembourser.",
            "Cet arrêt est communiqué aux parties.",
        ]
        boilerplate_it = [
            "Il Tribunale federale considera:",
            "Secondo l'art. 29 Cost., ogni persona ha diritto a un giusto processo.",
            "Il ricorso è stato presentato tempestivamente.",
            "Le parti non hanno spese da rimborsare.",
            "Questa sentenza è comunicata alle parti.",
        ]

        boilerplate_by_lang = {"de": boilerplate_de, "fr": boilerplate_fr, "it": boilerplate_it}

        legal_content_templates = {
            "Area_00": "Vertragsrecht - {concept} - Prüfung der Vertragsgültigkeit",
            "Area_01": "Arbeitsrecht - {concept} - Kündigungsschutz",
            "Area_02": "Strafrecht - {concept} - Strafzumessung",
            "Area_03": "Verwaltungsrecht - {concept} - Verfügungsrechtmässigkeit",
            "Area_04": "Zivilprozessrecht - {concept} - Zuständigkeit",
            "Area_05": "Sozialversicherungsrecht - {concept} - Leistungsanspruch",
            "Area_06": "Steuerrecht - {concept} - Steuerpflicht",
            "Area_07": "Immaterialgüterrecht - {concept} - Schutzrechtverletzung",
            "Area_08": "Mietrecht - {concept} - Kündigungsfristen",
            "Area_09": "Erbrecht - {concept} - Erbteilungsanspruch",
        }

        for decision in self.decisions.values():
            lang = decision.language
            bp = boilerplate_by_lang.get(lang, boilerplate_de)
            
            # Legal content based on Jurivoc
            legal_parts = []
            for concept in decision.jurivoc_descriptors:
                template = legal_content_templates.get(decision.legal_area, "{area} - {concept}")
                legal_parts.append(template.format(area=decision.legal_area, concept=concept))
            
            legal_text = " ".join(legal_parts)
            
            # Mix boilerplate and legal content (70% boilerplate, 30% legal)
            num_bp = random.randint(3, 5)
            selected_bp = random.sample(bp, min(num_bp, len(bp)))
            
            text_parts = selected_bp + [legal_text] * 2
            random.shuffle(text_parts)
            
            decision.full_text = " ".join(text_parts)

    def get_representation_fn(self) -> callable:
        """Get a representation function for the synthetic corpus."""
        def representation_fn(decision_id: str, corpus_subset: Optional[List[str]] = None) -> Optional[np.ndarray]:
            if decision_id in self.decisions:
                return self.decisions[decision_id].embedding
            return None
        return representation_fn

    def get_corpus_object(self) -> Any:
        """Get a corpus-like object for testing."""
        class CorpusWrapper:
            def __init__(self, decisions):
                self.decisions = decisions
            
            def get_decisions(self, limit=None):
                decisions = list(self.decisions.values())
                if limit:
                    decisions = decisions[:limit]
                return [d.__dict__ for d in decisions]

        return CorpusWrapper(self.decisions)

    def get_ground_truth(self) -> Dict[str, Any]:
        """Get ground truth information for evaluation."""
        return {
            "legal_areas": self.legal_areas,
            "jurivoc_concepts": self.jurivoc_concepts,
            "area_to_jurivoc": self.area_to_jurivoc,
            "area_centers": {k: v.tolist() for k, v in self.area_centers.items()},
            "jurivoc_centers": {k: v.tolist() for k, v in self.jurivoc_centers.items()},
            "decision_metadata": {
                did: {
                    "legal_area": d.legal_area,
                    "jurivoc_descriptors": d.jurivoc_descriptors,
                    "language": d.language,
                    "chamber": d.chamber,
                    "outcome": d.outcome,
                }
                for did, d in self.decisions.items()
            },
        }


def create_synthetic_corpus(config: Optional[SyntheticCorpusConfig] = None) -> Tuple[Dict[str, SyntheticDecision], callable, Any, Dict[str, Any]]:
    """Convenience function to create synthetic corpus and all needed components."""
    generator = SyntheticCorpusGenerator(config)
    decisions = generator.generate()
    representation_fn = generator.get_representation_fn()
    corpus = generator.get_corpus_object()
    ground_truth = generator.get_ground_truth()
    return decisions, representation_fn, corpus, ground_truth