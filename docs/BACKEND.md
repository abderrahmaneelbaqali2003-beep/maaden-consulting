# Documentation backend — Smart Lighting Decision Tool

Référence complète du backend FastAPI : architecture, base de données, API, moteur de recommandation, configuration.

## Sommaire

- [Stack technique](#stack-technique)
- [Arborescence](#arborescence)
- [Configuration (.env)](#configuration-env)
- [Base de données](#base-de-données)
- [API — liste complète des endpoints](#api--liste-complète-des-endpoints)
- [Service d'import](#service-dimport)
- [Moteur de recommandation](#moteur-de-recommandation)
- [Configurateur (sélection manuelle / semi-automatique)](#configurateur-sélection-manuelle--semi-automatique)
- [Tests](#tests)
- [Scripts](#scripts)

## Stack technique

| Composant | Technologie |
|---|---|
| Langage | Python 3.12 |
| Framework API | FastAPI 0.115 |
| Validation | Pydantic 2 / pydantic-settings |
| ORM | SQLAlchemy 2 (mapping déclaratif `Mapped[...]`) |
| Migrations | Alembic |
| Driver PostgreSQL | Psycopg 3 (`postgresql+psycopg://`) |
| Traitement fichiers | Pandas + OpenPyXL |
| Serveur ASGI | Uvicorn |
| Tests | Pytest + httpx (via `TestClient`) |

## Arborescence

```
backend/
├── app/
│   ├── main.py                     # Point d'entree FastAPI, montage des routers, CORS
│   ├── core/
│   │   ├── config.py                # Settings (lit backend/.env via pydantic-settings)
│   │   └── logging.py               # Configuration du logging
│   ├── database/
│   │   ├── base.py                  # Base declarative + TimestampMixin + TraceabilityMixin
│   │   ├── session.py               # engine, SessionLocal, dependance get_db()
│   │   └── models/                  # Un fichier par entite (voir section Base de donnees)
│   ├── schemas/                     # Schemas Pydantic request/response par entite
│   ├── repositories/                # Requetes SQLAlchemy (filtres, pagination, tri)
│   ├── services/
│   │   ├── import_service.py        # Import Excel/CSV -> catalogue
│   │   ├── candidate_selection.py   # Etape B : selection des modules candidats
│   │   ├── driver_module_matcher.py # Etape C : compatibilite driver <-> module
│   │   ├── module_lens_matcher.py   # Etape D : compatibilite module <-> lentille
│   │   ├── scoring_engine.py        # Etape F : scoring sur 100 points
│   │   ├── explanation_engine.py    # Etape G : generation de l'explication texte
│   │   └── recommendation_engine.py # Orchestration complete (etapes B a G)
│   ├── rules/
│   │   ├── protocol_matching.py     # Correspondance protocole demande -> colonne driver
│   │   └── results.py               # Dataclasses MatchEvaluation / RuleOutcome
│   ├── api/
│   │   ├── dependencies.py          # Re-export de get_db
│   │   └── routes/                  # Un fichier par groupe d'endpoints
│   └── utils/
│       ├── file_readers.py          # Lecture Excel/CSV, detection feuille/separateur
│       └── value_cleaning.py        # clean_str/clean_int/clean_float/clean_bool
├── migrations/                      # Alembic (env.py + versions/)
├── scripts/
│   └── run_initial_import.py        # Import initial des 3 bases + regles de compatibilite
├── tests/                           # 29 tests pytest
├── requirements.txt
├── alembic.ini
├── .env                             # Non versionne (secrets)
└── .env.example                     # Modele versionne
```

## Configuration (.env)

Chargé par `app/core/config.py` (classe `Settings`, pydantic-settings). Toutes les valeurs ont un défaut sauf `DATABASE_URL`.

| Variable | Défaut | Rôle |
|---|---|---|
| `DATABASE_URL` | *(obligatoire)* | Chaîne de connexion `postgresql+psycopg://user:pass@host:port/db` |
| `CORS_ORIGINS` | `http://localhost:5173` | Origines autorisées (séparées par virgule) |
| `SAFETY_FACTOR` | `1.10` | Marge de sécurité puissance driver/module (règle R-005) |
| `FLUX_TOLERANCE_MIN` | `0.95` | Borne basse de tolérance flux (95% du flux demandé) |
| `FLUX_TOLERANCE_MAX` | `1.15` | Borne haute de tolérance flux (115%) |
| `CURRENT_FIXED_TOLERANCE_MA` | `0` | Tolérance courant pour un driver à courant fixe |
| `MODULE_VOLTAGE_TOLERANCE_PERCENT` | `10` | Tolérance tension module vs besoin saisi |
| `MODULE_CURRENT_TOLERANCE_PERCENT` | `10` | Tolérance courant module vs besoin saisi |
| `LENS_PITCH_TOLERANCE_MM` | `0.2` | Tolérance entraxe module/lentille (réservée, non utilisée en V1 faute de données) |
| `MAX_RESULTS` | `3` | Nombre de configurations renvoyées par le moteur |
| `MAX_IMPORT_FILE_SIZE_MB` | `20` | Taille max acceptée pour un import |
| `LOG_LEVEL` | `INFO` | Niveau de log |
| `ENVIRONMENT` | `development` | Environnement courant |

## Base de données

PostgreSQL 18, 4 schémas. Toutes les tables de catalogue héritent de `TimestampMixin` (`created_at`, `updated_at`) et `TraceabilityMixin` (`source_name`, `notes`, `data_quality_score`, `data_quality_level`, `needs_manual_validation`, `is_active`).

### Schéma `catalog`

| Table | Modèle | Rôle |
|---|---|---|
| `manufacturers` | `Manufacturer` | Fabricants (dédupliqués par nom, créés à la volée) |
| `drivers` | `Driver` | Drivers LED — tension/courant/puissance de sortie, protocoles (`dali_2`, `d4i`, `dimming_0_10v`, `dimming_1_10v`), thermique, certifications |
| `led_modules` | `LedModule` | Modules LED — flux, CCT, package LED, électrique, mécanique |
| `lenses` | `Lens` | Lentilles — compatibilité LED déclarée, layout optique, photométrie, IES/LDT |
| `technical_documents` | `TechnicalDocument` | Fiches techniques/fichiers liés à un produit (extension future) |
| `compatibility_rules` | `CompatibilityRule` | Règles chargées depuis les feuilles `*_compatibility_rules` des fichiers sources (35 lignes) |
| `driver_module_compatibility` | `DriverModuleCompatibility` | Cache optionnel de compatibilité driver↔module (non peuplé automatiquement en V1) |
| `module_lens_compatibility` | `ModuleLensCompatibility` | Cache optionnel de compatibilité module↔lentille |

### Schéma `consulting`

| Table | Modèle | Rôle |
|---|---|---|
| `projects` | `Project` | Projet client (optionnel, un calcul peut être fait sans projet rattaché) |
| `project_requirements` | `ProjectRequirement` | Un jeu de besoins saisi via le formulaire "Nouveau calcul" |
| `recommendation_runs` | `RecommendationRun` | Une exécution du moteur automatique (statut, message, compteurs de rejet) |
| `recommendation_results` | `RecommendationResult` | Une configuration classée (driver+module+lentille, scores, explication) |
| `saved_configurations` | `SavedConfiguration` | Configuration enregistrée explicitement par un consultant (tous modes confondus), colonnes `validated_rules`/`blocking_reasons`/`warnings` en JSONB |

### Schéma `audit`

| Table | Modèle | Rôle |
|---|---|---|
| `import_history` | `ImportHistory` | Historique de chaque import de fichier |
| `data_issues` | `DataIssue` | Anomalies détectées ligne par ligne (import ou nettoyage source) |
| `expert_validations` | `ExpertValidation` | Décision (validé/rejeté) d'un consultant sur une configuration |
| `decision_history` | `DecisionHistory` | Trace de toute action sur une exécution (created/validated/rejected) |

### Schéma `staging`

Créé par la migration (`CREATE SCHEMA IF NOT EXISTS`) mais sans table fixe : réservé aux futurs imports par étapes (table temporaire par import avant contrôle qualité), non utilisé activement en V1 (l'import actuel écrit directement dans `catalog.*` après validation ligne par ligne, cf. section suivante).

### Migrations

Une seule migration (`d811b3f62d69_initial_schema.py`). Pour en générer une nouvelle après modification des modèles :

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "description"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

⚠️ Toujours relire le fichier généré avant d'appliquer — Alembic peut inclure de faux positifs (ex: suppression de sa propre table `alembic_version`, déjà rencontré et corrigé lors de la Phase 2).

## API — liste complète des endpoints

Base URL locale : `http://127.0.0.1:8000`. Documentation interactive : `/docs` (Swagger) et `/redoc`.

### Santé

| Méthode | Route |
|---|---|
| GET | `/api/health` |

### Drivers (`app/api/routes/drivers.py`)

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/drivers` | Liste paginée, filtres : `manufacturer`, `power_min_w`, `power_max_w`, `voltage_min_v`, `voltage_max_v`, `protocol`, `search`, `include_inactive`, tri, pagination |
| GET | `/api/drivers/{driver_id}` | Détail |
| POST | `/api/drivers` | Création (409 si `external_ref` déjà existant) |
| PUT | `/api/drivers/{driver_id}` | Mise à jour partielle (`exclude_unset`) |
| DELETE | `/api/drivers/{driver_id}` | Suppression logique (`is_active = False`) |

### Modules LED (`modules.py`)

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/modules` | Filtres : `manufacturer`, `flux_min_lm`, `flux_max_lm`, `power_min_w`, `power_max_w`, `cct_k`, `voltage_min_v`, `voltage_max_v`, `current_min_ma`, `current_max_ma`, `led_package`, `search` |
| GET | `/api/modules/{module_id}` | Détail |
| POST | `/api/modules` | Création |
| PUT | `/api/modules/{module_id}` | Mise à jour partielle |
| DELETE | `/api/modules/{module_id}` | Suppression logique |

### Lentilles (`lenses.py`)

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/lenses` | Filtres : `manufacturer`, `led_package`, `optical_cells_quantity`, `distribution`, `search` |
| GET | `/api/lenses/{lens_id}` | Détail |
| POST | `/api/lenses` | Création |
| PUT | `/api/lenses/{lens_id}` | Mise à jour partielle |
| DELETE | `/api/lenses/{lens_id}` | Suppression logique |

### Recommandations (`recommendations.py`)

| Méthode | Route | Description |
|---|---|---|
| POST | `/api/recommendations` | Crée un `ProjectRequirement` puis exécute le moteur (`run_recommendation`) — retourne le format complet (statut, configurations, rejets) |
| GET | `/api/recommendations/history` | Historique paginé de toutes les exécutions |
| GET | `/api/recommendations/{run_id}` | Détail d'une exécution |
| POST | `/api/recommendations/{run_id}/validate` | Valide la configuration n°1 (crée `ExpertValidation` + `DecisionHistory`) |
| POST | `/api/recommendations/{run_id}/reject` | Rejette la configuration n°1 |

### Imports (`imports.py`)

| Méthode | Route | Description |
|---|---|---|
| POST | `/api/imports/analyze` | Analyse un fichier uploadé sans écrire en base (colonnes, types, % manquants, aperçu 10 lignes) |
| POST | `/api/imports/drivers` | Importe un fichier de drivers |
| POST | `/api/imports/modules` | Importe un fichier de modules |
| POST | `/api/imports/lenses` | Importe un fichier de lentilles |
| GET | `/api/imports/history` | Historique paginé des imports |
| GET | `/api/imports/{import_id}/issues` | Anomalies détectées pour un import donné |

### Tableau de bord (`dashboard.py`)

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/dashboard/summary` | Compteurs catalogue, taux de compatibilité, 5 derniers imports, 5 dernières recommandations |

### Configurateur (`configurator.py`)

7 endpoints pour la sélection manuelle assistée et semi-automatique — détaillés dans la section
[Configurateur](#configurateur-sélection-manuelle--semi-automatique) plus bas (`/api/configurator/options`,
`/modules`, `/drivers`, `/lenses`, `/validate`, `/recommend-missing`, `/save`).

## Service d'import

`app/services/import_service.py` — logique partagée par le script initial et les endpoints `/api/imports/*`.

**Principe** : chaque colonne de la feuille `*_cleaned` du fichier source est mappée vers un champ du modèle via un dictionnaire `{champ_modele: (colonne_source, fonction_nettoyage)}` (`DRIVER_FIELD_MAP`, `MODULE_FIELD_MAP`, `LENS_FIELD_MAP`). Une valeur absente reste `None` en base — jamais convertie en 0 ou chaîne vide (`app/utils/value_cleaning.py`).

**Étapes par ligne** :
1. Vérifie l'identifiant externe (`driver_id`/`module_id`/`lens_id`) — sinon ligne rejetée.
2. Détecte les doublons d'identifiant **dans le fichier** — 2ᵉ occurrence rejetée.
3. Résout ou crée le fabricant (`get_or_create_manufacturer`).
4. Vérifie les champs strictement indispensables au moteur (ex: `output_voltage_min_v`/`max_v`/`output_power_max_w` pour un driver) — absents → ligne rejetée et anomalie journalisée dans `audit.data_issues`.
5. Upsert : si l'`external_ref` existe déjà en base, met à jour ; sinon crée. **Idempotent** — relancer un import ne duplique jamais.
6. Un `audit.import_history` est créé par appel (compteurs importés/mis à jour/rejetés, statut `success`/`partial`).

**Détection de fichier** (`app/utils/file_readers.py`) :
- Extensions autorisées : `.xlsx`, `.xls`, `.csv`.
- Feuille Excel choisie automatiquement (contient `cleaned` dans le nom, sinon la première feuille).
- Séparateur CSV auto-détecté (`csv.Sniffer`, teste `;`, `,`, tabulation).
- Nombres à virgule décimale convertis automatiquement pour les CSV.

**Règles de compatibilité** : `import_compatibility_rules()` charge les feuilles `driver_compatibility_rules` / `module_compatibility_rules` / `lens_compatibility_rules` dans `catalog.compatibility_rules` (upsert par `entity_type` + `external_rule_id`).

## Moteur de recommandation

Orchestré par `app/services/recommendation_engine.py::run_recommendation()`. Appelé par `POST /api/recommendations`.

### Étape A — Validation des entrées
Gérée par `app/schemas/recommendation.py::RecommendationRequest` (Pydantic) avant même d'atteindre le moteur : 5 champs obligatoires strictement positifs (`required_flux_lm`, `max_power_w`, `required_cct_k`, `voltage_nominal_v`, `current_nominal_ma`), 6 champs optionnels.

### Étape B — Sélection des modules candidats
`app/services/candidate_selection.py::select_candidate_modules()`. Filtre **strict** (élimine directement, hors moteur de règles) :
- Flux dans `[FLUX_TOLERANCE_MIN, FLUX_TOLERANCE_MAX] × required_flux_lm`.
- `power_nominal_w <= max_power_w` (si renseigné).
- CCT exacte, ou présente dans `cct_options` (référence multi-CCT).
- `led_package` si demandé.
- Tension/courant nominal module vs besoin, tolérance `MODULE_VOLTAGE_TOLERANCE_PERCENT`/`MODULE_CURRENT_TOLERANCE_PERCENT` — **champ absent = non éliminé** (donnée non vérifiable ≠ incompatible).

### Étape C — Compatibilité driver ↔ module
`app/services/driver_module_matcher.py::evaluate_driver_for_module()`, pour chaque driver actif × chaque module candidat :

| Vérification | Type | Détail |
|---|---|---|
| Tension | Bloquant | `output_voltage_min_v <= module.input_voltage_nominal_v <= output_voltage_max_v` |
| Courant | Bloquant | Plage driver, tolérance `CURRENT_FIXED_TOLERANCE_MA` si driver à courant fixe |
| Marge de puissance | Bloquant | `output_power_max_w >= power_nominal_w × SAFETY_FACTOR` |
| Protocole | Bloquant (si demandé) | Résolution via `app/rules/protocol_matching.py` (DALI→`dali_2`, D4i→`d4i`, 0-10V→`dimming_0_10v`, 1-10V→`dimming_1_10v`) |
| Température ambiante | Bloquant (si fournie) | `ambient_temperature_max_c >= ambient_temperature_c` demandée |

Toute donnée manquante empêchant une vérification génère un **avertissement**, jamais un blocage.

### Étape D — Compatibilité module ↔ lentille
`app/services/module_lens_matcher.py::evaluate_lens_for_module()`, pour chaque lentille active :

| Vérification | Type |
|---|---|
| Package LED déclaré compatible | Bloquant si déclaré et non couvert ; avertissement si non déclaré |
| Nombre de cellules optiques = nombre de LED | Bloquant si les deux renseignés |
| Fichier IES/LDT disponible | Avertissement seul (jamais bloquant — cf. limitation données) |
| Distribution photométrique vs type de voie | Avertissement informatif |
| Température ambiante vs limite lentille | Bloquant si les deux renseignés |

### Étape E — Élimination
Toute règle `blocking` non respectée élimine la paire/triplet. Compteurs `drivers_rejected`, `modules_rejected`, `lenses_rejected` alimentés en conséquence.

### Étape F — Scoring (100 points)
`app/services/scoring_engine.py::compute_scores()`, calculé uniquement pour les configurations ayant passé l'étape E :

| Sous-score | Points | Formule résumée |
|---|---|---|
| Électrique | 35 | 20 pts marge de puissance (linéaire entre le seuil `SAFETY_FACTOR` et 30% de marge) + 15 pts centrage de la tension module dans la plage driver |
| Flux / CCT | 25 | 15 pts précision du flux (distance à 1.0 normalisée par la tolérance) + 10 pts CCT exacte (6 pts si via `cct_options`) |
| Mécanique / optique | 20 | 20 − 3×(nb avertissements lentille) ; 0 si aucune lentille trouvée |
| Thermique | 10 | Neutre (5) si température non fournie ; sinon marge à la limite la plus contraignante (10 pts si marge ≥ 15 °C) |
| Qualité des données | 10 | Moyenne des `data_quality_score` (0-100) des composants, ramenée sur 10 ; neutre (5) si absent |

### Étape G — Classement et explication
Tri par `overall_score` décroissant, les `MAX_RESULTS` (3 par défaut) meilleures configurations sont conservées. `app/services/explanation_engine.py::TemplateExplanationProvider` génère le texte d'explication par templates Python (pas d'IA générative — voir `docs/DATA_MAPPING.md` et README pour le détail).

### Détermination du statut global

```
si aucune configuration               -> impossible
sinon, en regardant la 1re configuration (meilleur score) :
  si aucune regle validee (validated_rules vide) -> data_incomplete
  sinon si validation manuelle necessaire         -> manual_validation_required
  sinon si des avertissements existent            -> compatible_with_warning
  sinon                                            -> compatible
```

`needs_manual_validation` est vrai si le driver, le module ou la lentille a `needs_manual_validation=True` en base, si aucune lentille n'a été trouvée, ou si la lentille retenue n'a ni fichier IES ni LDT.

### Persistance

Chaque appel crée un `consulting.recommendation_runs` (statut, message, compteurs, `blocking_reasons`, `suggestions`) et un `consulting.recommendation_results` par configuration retenue (scores détaillés, règles validées, avertissements, explication, `validation_status`).

## Configurateur (sélection manuelle / semi-automatique)

En plus du mode automatique (`recommendation_engine.py`), trois autres briques permettent à un consultant
de choisir lui-même tout ou partie de la configuration :

### `ConfigurationValidationService` (`app/services/configuration_validation_service.py`)

Point d'entrée **unique** pour évaluer une combinaison (driver, module, lentille) — quel que soit le mode
qui l'appelle. Orchestre `evaluate_driver_for_module` et `evaluate_lens_for_module` (les matchers, seule source
de vérité des règles), agrège leurs `validated_rules`/`warnings`/`blocking_reasons`/`criteria`, calcule les
scores via `scoring_engine.compute_scores`, détermine un statut unique et produit l'explication. `driver` et
`lens` peuvent être `None` (sélection partielle) ; `module` est toujours requis.

Statut retourné (`ConfigurationEvaluation.status`) :

```
si des regles bloquantes existent          -> not_compatible
sinon si aucune regle n'a pu etre validee   -> data_incomplete
sinon si validation manuelle necessaire      -> manual_validation_required
sinon si des avertissements existent         -> compatible_with_warning
sinon                                        -> compatible
```

`recommendation_engine.py` (mode automatique) délègue chaque évaluation driver↔module / module↔lentille /
combinaison finale à ce même service (avec `skip_explanation=True` pendant le filtrage, pour l'efficacité,
puis une réévaluation complète pour les configurations finalement classées) — **aucune règle n'est dupliquée**
entre les trois modes.

### `ManualConfigurationService` (`app/services/manual_configuration_service.py`)

- `validate(driver, module, lens, requirement, settings)` → délègue directement à `ConfigurationValidationService.evaluate`.
- `find_alternatives(db, module, requirement, settings, exclude_driver_id, exclude_lens_id, limit=3)` → cherche
  jusqu'à `limit` combinaisons compatibles alternatives pour le **même module**, classées par score.

### `HybridConfigurationService` (`app/services/hybrid_configuration_service.py`)

`recommend_missing(db, requirement, settings, fixed_driver, fixed_module, fixed_lens)` — les composants
imposés (non `None`) deviennent des contraintes obligatoires : ils sont toujours évalués et retournés, même
si le résultat final est incompatible (pour expliquer pourquoi). Le(s) composant(s) non imposé(s) sont
recherchés parmi tout le catalogue actif. Si le module n'est pas imposé, `required_flux_lm` et
`required_cct_k` doivent être fournis (sinon `MissingRequirementFieldsError` → HTTP 422) car ils servent à
`select_candidate_modules` (même fonction que le mode automatique).

### Endpoints (`app/api/routes/configurator.py`)

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/configurator/options` | Modes disponibles, fabricants par entité, compteurs catalogue |
| GET | `/api/configurator/modules` | Liste paginée de modules ; `status` par item calculé si `required_flux_lm`+`required_cct_k` fournis en query |
| GET | `/api/configurator/drivers?module_id=` | Liste paginée de drivers avec `status` réel (via `ConfigurationValidationService`) vis-à-vis du module |
| GET | `/api/configurator/lenses?module_id=` | Idem pour les lentilles |
| POST | `/api/configurator/validate` | `{selection_mode, driver_id?, module_id, lens_id?, project_requirements}` → matrice de critères, scores, statut, alternatives |
| POST | `/api/configurator/recommend-missing` | `{driver_id?, module_id?, lens_id?, project_requirements}` (au moins un id) → meilleure configuration complétant les composants imposés |
| POST | `/api/configurator/save` | Enregistre une configuration dans `consulting.saved_configurations` |

`PartialRequirements` (`app/schemas/configurator.py`) reprend les mêmes champs que `RecommendationRequest`
mais **tous optionnels** : un consultant peut valider une combinaison sans ressaisir l'intégralité du besoin
projet (`project_requirements: {}` est un appel valide) ; les champs absents dégradent les critères/scores
correspondants en "non vérifiable" plutôt que de bloquer l'appel (`candidate_selection.py` et
`scoring_engine._score_photometric` ont été rendus tolérants à ces champs `None`).

## Tests

45 tests (`backend/tests/`), base réelle avec rollback automatique par test (`tests/conftest.py::db_session` — chaque test s'exécute dans une transaction annulée à la fin, aucune pollution des données réelles).

| Fichier | Contenu |
|---|---|
| `test_import_service.py` | 6 tests : nouvelle référence, doublon, champ requis manquant, valeur numérique invalide, réimport idempotent, fabricant manquant |
| `test_drivers_api.py` | 8 tests : CRUD complet, 409 doublon, 404, pagination, filtres, suppression logique, validation 422 |
| `test_recommendation_engine.py` | 15 tests : tension/courant/puissance/protocole/CCT compatibles et incompatibles, package LED, nombre de LED, fichier IES absent, données incomplètes, aucune configuration, classement multiple |
| `test_configurator.py` | 16 tests : validation manuelle compatible/incompatible (driver/lentille), données manquantes, sélection partielle, mode semi-automatique (module/driver imposé, erreurs 422), enregistrement, alternatives, statuts dans les listes, réutilisation prouvée du même service de validation |
| `factories.py` | Fabriques `make_driver`/`make_module`/`make_lens`/`make_requirement` pour données de test synthétiques et isolées des vraies données importées |

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\ -v
```

## Scripts

| Script | Rôle |
|---|---|
| `scripts/run_initial_import.py` | Importe les 3 fichiers `data/raw/*.xlsx` + charge les 35 règles de compatibilité. Idempotent (relançable sans dupliquer). |
