#!/usr/bin/env python3
"""
Cross-lingual legal_area normalization for the lex_machina evaluation harness.

MOTIVATION
----------
Evaluation v16 (run 33366069802) reported that the hierarchy_coherence,
zoom_coherence and legal_area_clustering benchmarks FAIL for all representations
and attributed this to "105 unique legal_area labels in 1200 decisions
= avg 11.4 decisions per area, making cluster purity mathematically unlikely".

Inspection of the raw metadata shows the label count is inflated by
UN-NORMALIZED CROSS-LINGUAL DUPLICATION: the same Swiss legal-area topic is
entered as separate German / French / Italian strings (e.g. Strafprozess /
Procédure pénale / Procedura penale). This makes a single legal area count as
three labels and deflates every label-purity metric for reasons unrelated to
embedding quality.

This module maps equivalent de/fr/it legal_area strings to a single canonical
(Jurivoc-style) concept. It is CONSERVATIVE: it merges only clearly-equivalent
labels across languages and never merges genuinely distinct legal areas, so it
cannot inflate purity by over-collapsing distinct topics.

USAGE
-----
    from legal_area_normalize import LEGAL_AREA_CANONICAL, normalize_legal_area
    canon = {did: normalize_legal_area(m.get('legal_area')) for did, m in metadata}

The coarse umbrella labels (public, civil, tax, social_insurance, administrative,
criminal, NONE, economy) are kept as identity: they are already umbrella-level
and are not part of the cross-lingual duplication artifact this module targets.
"""

# de -> canonical  ...  fr -> canonical  ...  it -> canonical
CROSS_LINGUAL_MAP = {
    # criminal procedure
    "Strafprozess": "criminal_procedure",
    "Procédure pénale": "criminal_procedure",
    "Procedura penale": "criminal_procedure",
    # contract law
    "Vertragsrecht": "contract_law",
    "Droit des contrats": "contract_law",
    "Diritto contrattuale": "contract_law",
    # invalidity insurance
    "Invalidenversicherung": "invalidity_insurance",
    "Assurance-invalidité": "invalidity_insurance",
    "Assicurazione per l'invalidità": "invalidity_insurance",
    # family law
    "Familienrecht": "family_law",
    "Droit de la famille": "family_law",
    "Diritto di famiglia": "family_law",
    # debt enforcement / bankruptcy
    "Schuldbetreibungs- und Konkursrecht": "debt_enforcement_bankruptcy",
    "Droit des poursuites et faillites": "debt_enforcement_bankruptcy",
    "Diritto delle esecuzioni e del fallimento": "debt_enforcement_bankruptcy",
    # accident insurance
    "Unfallversicherung": "accident_insurance",
    "Assurance-accidents": "accident_insurance",
    "Assicurazione contro gli infortuni": "accident_insurance",
    # land use / public construction
    "Raumplanung und öffentliches Baurecht": "land_use_public_construction",
    "Aménagement du territoire et droit public des constructions": "land_use_public_construction",
    "Pianificazione territoriale e diritto pubblico edilizio": "land_use_public_construction",
    # public finance / taxation
    "Öffentliche Finanzen & Abgaberecht": "public_finance_taxation",
    "Finances publiques & droit fiscal": "public_finance_taxation",
    "Finanze pubbliche & diritto tributario": "public_finance_taxation",
    # unemployment insurance
    "Arbeitslosenversicherung": "unemployment_insurance",
    "Assurance-chômage": "unemployment_insurance",
    "Assicurazione contro la disoccupazione": "unemployment_insurance",
    # law of obligations (general)
    "Obligationenrecht (allgemein)": "law_of_obligations_general",
    "Droit des obligations (en général)": "law_of_obligations_general",
    # jurisdiction questions
    "Zuständigkeitsfragen, Garantie des Wohnsitzrichters und des verfassungsmässigen Richters": "jurisdiction_questions",
    "Questions de compétences, garantie du juge du domicile et du juge constitutionnel": "jurisdiction_questions",
    # health & social security (overarching)
    "Gesundheitswesen & soziale Sicherheit": "health_social_security",
    "Santé & sécurité sociale": "health_social_security",
    # old-age & survivors insurance
    "Alters- und Hinterlassenenversicherung": "old_age_survivors_insurance",
    "Assurance-vieillesse et survivants": "old_age_survivors_insurance",
    "Assicurazione per la vecchiaia e per i superstiti": "old_age_survivors_insurance",
    # supplementary benefits
    "Ergänzungsleistung": "supplementary_benefits",
    "Prestations complémentaires à l'AVS/AI": "supplementary_benefits",
    "Prestazione complementari": "supplementary_benefits",
    # citizenship & foreigners
    "Bürgerrecht und Ausländerrecht": "citizenship_foreigners",
    "Droit de cité et droit des étrangers": "citizenship_foreigners",
    "Cittadinanza e diritto degli stranieri": "citizenship_foreigners",
    # fundamental rights
    "Grundrecht": "fundamental_rights",
    "Droit fondamental": "fundamental_rights",
    # health insurance
    "Krankenversicherung": "health_insurance",
    "Assurance-maladie": "health_insurance",
    "Assicurazione contro le malattie": "health_insurance",
    # road building & traffic
    "Strassenbau und Strassenverkehr": "road_building_traffic",
    "Construction des routes et circulation routière": "road_building_traffic",
    "Costruzioni stradali e circolazione stradale": "road_building_traffic",
    # IP / competition / cartel
    "Immaterialgüter-, Wettbewerbs- und Kartellrecht": "ip_competition_cartel",
    "Propriété intellectuelle, concurrence et cartels": "ip_competition_cartel",
    # real rights / property
    "Sachenrecht": "real_rights_property",
    "Droits réels": "real_rights_property",
    # state liability
    "Staatshaftung": "state_liability",
    "Responsabilité de l'État": "state_liability",
    # penal & measures execution
    "Straf- und Massnahmenvollzug": "penal_measures_execution",
    "Exécution des peines et des mesures": "penal_measures_execution",
    # general criminal law
    "Strafrecht (allgemein)": "criminal_law_general",
    "Droit pénal (en général)": "criminal_law_general",
    # criminal offenses
    "Straftaten": "criminal_offenses",
    "Infractions": "criminal_offenses",
    "Infrazione": "criminal_offenses",
    # ecological balance
    "Ökologisches Gleichgewicht": "ecological_balance",
    "Équilibre écologique": "ecological_balance",
    # education & vocational training
    "Unterrichtswesen und Berufsausbildung": "education_vocational_training",
    "Instruction et formation professionnelle": "education_vocational_training",
    "Istruzione e formazione professionale": "education_vocational_training",
    # arbitration
    "Schiedsgerichtsbarkeit": "arbitration",
    "Juridiction arbitrale": "arbitration",
    # succession
    "Erbrecht": "succession_law",
    "Droit des successions": "succession_law",
    # company law
    "Gesellschaftsrecht": "company_law",
    "Droit des sociétés": "company_law",
    # economy (umbrella, cross-lingual identical concept)
    "Wirtschaft": "economy",
    "Économie": "economy",
    # mutual assistance & extradition
    "Rechtshilfe und Auslieferung": "mutual_assistance_extradition",
    "Entraide et extradition": "mutual_assistance_extradition",
    "Assistenza giudiziaria e estradizione": "mutual_assistance_extradition",
    # civil service / public employment
    "Öffentliches Dienstverhältnis": "civil_service",
    "Fonction publique": "civil_service",
    # administrative procedure
    "Verwaltungsverfahren": "administrative_procedure",
    "Procédure administrative": "administrative_procedure",
    # occupational pension
    "Berufliche Vorsorge": "occupational_pension",
    "Prévoyance professionnelle": "occupational_pension",
    # political rights
    "Droits politiques": "political_rights",
    # rights of persons
    "Droit des personnes": "rights_of_persons",
    # energy
    "Energia": "energy",
    # family / social allowance
    "Allocation familiale et assurance sociale cantonale": "family_allowance_social",
    # file/record consultation
    "consultation de dossier": "file_access",
    # mass / media
    "Mass media": "mass_media",
}


def normalize_legal_area(label):
    """Return canonical legal-area concept for a raw label.

    Coarse umbrella labels and singletons not in CROSS_LINGUAL_MAP pass through
    unchanged (identity), so this normalization does not merge distinct topics.
    """
    if label is None:
        return None
    return CROSS_LINGUAL_MAP.get(label, label)
