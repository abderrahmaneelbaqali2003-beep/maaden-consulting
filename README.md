# Smart Lighting Decision Tool

Outil intelligent d'aide à la décision pour le consulting en éclairage public.
Le système recommande une configuration technique (driver LED + module LED + lentille optique) à partir des besoins d'un projet, en s'appuyant sur un moteur de règles déterministe (aucune décision électrique/mécanique n'est prise par une IA générative).

> Statut du projet : **MVP fonctionnel complet** — backend, base de données, moteur de recommandation et frontend opérationnels et testés sur les 3 bases de données réelles fournies.

## Sommaire

- [Architecture](#architecture)
- [Installation et lancement](#installation-et-lancement)
- [Structure du projet](#structure-du-projet)
- [Données sources](#données-sources)
- [Moteur de recommandation](#moteur-de-recommandation)
- [Tests](#tests)
- [Documentation complémentaire](#documentation-complémentaire)
- [Limitations connues et extensions futures](#limitations-connues-et-extensions-futures)

## Architecture

- **Backend** : Python 3.12 / FastAPI / Pydantic 2 / SQLAlchemy 2 / Alembic / Psycopg 3 / Pandas / OpenPyXL
- **Frontend** : React 19 / TypeScript / Vite / Tailwind CSS 4 / React Hook Form / Zod / Axios / Recharts / React Router
- **Base de données** : PostgreSQL 18, schémas `staging`, `catalog`, `consulting`, `audit`
- **Moteur de recommandation** : règles déterministes + scoring documenté sur 100 points + génération d'explications par templates (pas de LLM en V1 — architecture prête pour un `LLMExplanationProvider` futur)

## Installation et lancement

Voir **[docs/INSTALLATION_WINDOWS.md](docs/INSTALLATION_WINDOWS.md)** pour le guide détaillé étape par étape (première installation et lancement quotidien).

Résumé du lancement quotidien (2 terminaux PowerShell) :

```powershell
# Terminal 1 — backend
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
```

Puis ouvrir **http://localhost:5173**. Documentation API interactive (Swagger) : **http://127.0.0.1:8000/docs**.

## Structure du projet

```
smart-lighting-decision-tool/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # Endpoints REST (drivers, modules, lenses, recommendations, imports, dashboard)
│   │   ├── core/               # Configuration (.env), logging
│   │   ├── database/models/    # Modeles SQLAlchemy (catalog, consulting, audit)
│   │   ├── schemas/            # Schemas Pydantic (validation entree/sortie API)
│   │   ├── repositories/       # Requetes base de donnees (filtres, pagination)
│   │   ├── services/           # Import, moteur de compatibilite, scoring, explications
│   │   ├── rules/               # Structures de regles et correspondance protocoles
│   │   └── main.py
│   ├── migrations/             # Migrations Alembic
│   ├── scripts/                # Script d'import initial
│   └── tests/                  # Tests pytest (29 tests)
├── frontend/
│   └── src/
│       ├── api/                 # Client axios + endpoints typés
│       ├── components/          # Composants UI reutilisables (style shadcn/ui)
│       ├── features/catalog/    # Tableaux catalogue par entite
│       ├── pages/                # 7 pages de l'application
│       └── schemas/              # Validation Zod des formulaires
├── data/
│   ├── raw/            # Fichiers Excel sources (jamais modifiés)
│   ├── processed/      # Reserve pour exports intermediaires futurs
│   └── samples/
├── docs/                # Installation Windows, mapping de donnees
└── scripts/
```

## Données sources

Trois bases nettoyées fournies au format Excel (voir **[docs/DATA_MAPPING.md](docs/DATA_MAPPING.md)** pour le détail complet des colonnes retenues et des choix de mapping) :

| Fichier | Références importées | Fabricants |
|---|---|---|
| `data/raw/LED_Drivers_Database_Cleaned.xlsx` | 108 drivers | 5 (Mean Well, TCI, Philips, OSRAM, Tridonic) |
| `data/raw/LED_Modules_Database_Cleaned.xlsx` | 209 modules LED | 6 (TCI, Signify, Tridonic, Samsung, Lumileds, Seoul Semiconductor) |
| `data/raw/LED_Lenses_Database_Cleaned.xlsx` | 52 lentilles (1 rejetée, sans référence) | 4 (LEDiL, Khatod, Darkoo, LEDLINK) |

Ces fichiers contiennent déjà des règles de compatibilité formalisées (feuilles `*_compatibility_rules`), chargées dans `catalog.compatibility_rules` (35 règles) et servant de référence documentaire au moteur de compatibilité codé dans `backend/app/services/`.

Pour réimporter (ou importer de nouvelles références via l'interface **Imports** ou l'API) :

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\run_initial_import.py
```

## Moteur de recommandation

Pipeline en 7 étapes (`backend/app/services/recommendation_engine.py`), conforme au cahier des charges :

1. **Validation des entrées** — schémas Pydantic (`schemas/recommendation.py`), rejette valeurs négatives/manquantes.
2. **Sélection des modules candidats** — flux (tolérance ±configurable), puissance, CCT, package LED.
3. **Filtrage driver ↔ module** — tension, courant (tolérance driver à courant fixe), marge de puissance (`safety_factor` configurable), protocole, température ambiante.
4. **Filtrage module ↔ lentille** — package LED déclaré, nombre de cellules optiques, fichier photométrique, température.
5. **Élimination** — toute règle `blocking` élimine la configuration ; le reste génère un avertissement.
6. **Scoring sur 100 points** — électrique (35) + flux/CCT (25) + mécanique/optique (20) + thermique (10) + qualité des données (10). Formules documentées dans `services/scoring_engine.py`.
7. **Classement** — les 3 meilleures configurations (configurable via `MAX_RESULTS`), avec explication générée automatiquement par `TemplateExplanationProvider`.

Statuts possibles : `compatible`, `compatible_with_warning`, `data_incomplete`, `manual_validation_required`, `not_compatible`, `impossible` — jamais de configuration inventée quand les données sont insuffisantes.

Paramètres configurables dans `backend/.env` : `SAFETY_FACTOR`, `FLUX_TOLERANCE_MIN/MAX`, `CURRENT_FIXED_TOLERANCE_MA`, `MODULE_VOLTAGE_TOLERANCE_PERCENT`, `MODULE_CURRENT_TOLERANCE_PERCENT`, `MAX_RESULTS`.

### Sélection manuelle assistée et semi-automatique

En plus du mode automatique, la page **Nouveau calcul** propose deux autres modes (`selection_mode` : `automatic` / `manual` / `hybrid`) :

- **Manuel assisté** — le consultant choisit lui-même le module, le driver et la lentille (dans cet ordre, avec statut de compatibilité affiché à chaque étape) ; le système exécute les mêmes règles de compatibilité et retourne une matrice de validation complète (tension, courant, puissance, protocole, thermique, compatibilité mécanique, IES/LDT), un score, des alternatives.
- **Semi-automatique** — le consultant impose 1 ou 2 composants ; le système recherche le(s) reste(s) parmi les références compatibles.

Toute la logique de compatibilité est centralisée dans **`ConfigurationValidationService`** (`backend/app/services/configuration_validation_service.py`), réutilisé à l'identique par `recommendation_engine.py` (automatique), `manual_configuration_service.py` (manuel) et `hybrid_configuration_service.py` (semi-automatique) — aucune règle n'est dupliquée entre les trois modes. Endpoints dédiés : `GET /api/configurator/options|modules|drivers|lenses`, `POST /api/configurator/validate|recommend-missing|save`. Les configurations validées peuvent être enregistrées dans `consulting.saved_configurations`.

## Tests

```powershell
# Backend (45 tests : import, CRUD API, 15 scenarios du moteur automatique, 16 scenarios du configurateur)
cd backend
.\.venv\Scripts\python.exe -m pytest tests\ -v

# Frontend (16 tests : composants, formulaire, configurateur)
cd frontend
npm run test
```

## Documentation complémentaire

- **[docs/INSTALLATION_WINDOWS.md](docs/INSTALLATION_WINDOWS.md)** — guide d'installation et de lancement pas à pas.
- **[docs/DATA_MAPPING.md](docs/DATA_MAPPING.md)** — mapping détaillé colonnes source → base de données, limitations de qualité des données.
- Swagger / OpenAPI généré automatiquement par FastAPI : http://127.0.0.1:8000/docs

## Limitations connues et extensions futures

- **Aucune lentille de la base n'a de fichier IES/LDT** : toute recommandation impliquant une lentille reçoit un avertissement et le statut `manual_validation_required` ou `compatible_with_warning`. La simulation photométrique réelle est une extension future (section 22 du cahier des charges).
- Certaines règles de compatibilité présentes dans les fichiers sources (entraxes LED, indice IP requis, tenue au foudre, matériaux vs exposition UV) ne sont pas implémentées en V1 faute de données ou de champs de formulaire correspondants — voir `docs/DATA_MAPPING.md`.
- La page Catalogue permet recherche, filtrage, consultation et désactivation (suppression logique) ; l'ajout se fait via l'import Excel/CSV ou l'API (`POST /api/drivers|modules|lenses`, documentée dans Swagger). Un formulaire de création/édition dédié dans l'interface est une extension naturelle future.
- Composants UI stylés manuellement à la manière de shadcn/ui (sans dépendance Radix UI) pour rester légers ; migrable vers de vrais composants shadcn/ui si des interactions plus riches (menus, dialogues accessibles) sont nécessaires.
- Machine learning, RAG sur fiches techniques, génération PDF, authentification, déploiement cloud : non développés en V1, architecture conçue pour les accueillir (voir section 22 du cahier des charges initial).
#   m a a d e n - c o n s u l t i n g  
 #   m a a d e n - c o n s u l t i n g  
 