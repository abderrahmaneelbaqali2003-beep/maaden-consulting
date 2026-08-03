# Mapping des données sources → base PostgreSQL

## Origine des données

Les 3 fichiers Excel sources (`data/raw/`) contiennent chacun plusieurs feuilles. Seule la feuille `*_cleaned` est utilisée comme source d'import (colonnes déjà nettoyées et normalisées par un traitement antérieur, documenté dans la feuille `cleaning_log` de chaque fichier).

| Fichier | Feuille source | Lignes | Table PostgreSQL |
|---|---|---|---|
| `LED_Drivers_Database_Cleaned.xlsx` | `drivers_cleaned` | 108 | `catalog.drivers` |
| `LED_Modules_Database_Cleaned.xlsx` | `led_modules_cleaned` | 209 | `catalog.led_modules` |
| `LED_Lenses_Database_Cleaned.xlsx` | `lenses_cleaned` | 53 (52 importées, 1 sans référence) | `catalog.lenses` |

Les feuilles `driver_compatibility_rules`, `module_compatibility_rules` et `lens_compatibility_rules` de ces mêmes fichiers sont chargées dans `catalog.compatibility_rules` (35 règles au total) et servent de référence documentaire au moteur de compatibilité (`app/services/driver_module_matcher.py` et `module_lens_matcher.py`), qui les implémente en code déterministe.

## Principe de sélection des colonnes

Sur les 129 (drivers), 203 (modules) et 228 (lentilles) colonnes disponibles dans les feuilles sources, seules ont été conservées dans les modèles SQLAlchemy (`backend/app/database/models/`) :

1. Les colonnes réellement renseignées dans la source (non 100% vides).
2. Les colonnes indispensables au moteur de compatibilité, même partiellement vides (ex: `ies_file_available` sur les lentilles, à 100% vide dans la source actuelle mais nécessaire pour détecter l'absence de validation photométrique).
3. Les colonnes de traçabilité (`source_name`, `data_quality_score`, `data_quality_level`, `needs_manual_validation`, `is_active`, `created_at`, `updated_at`).

Les colonnes 100% vides et non utilisées par le moteur (prix, disponibilité fournisseur, fichiers CAO, capteurs IoT, etc.) n'ont pas été créées en base — elles pourront être ajoutées lors d'une prochaine évolution si des données réelles deviennent disponibles (voir section "Extension future" du cahier des charges).

## Colonnes source → champ modèle (différences de nom)

Quelques colonnes ont été renommées lors du mapping (`backend/app/services/import_service.py`, dictionnaires `DRIVER_FIELD_MAP` / `MODULE_FIELD_MAP` / `LENS_FIELD_MAP`) :

| Entité | Colonne source | Champ modèle |
|---|---|---|
| Driver | `benchmark_final_score` | `benchmark_score` |
| Driver | `overall_data_quality_score` | `data_quality_score` |
| Module | `overall_data_quality_score` | `data_quality_score` |
| Lentille | `overall_data_quality_score` | `data_quality_score` |
| Tous | `manual_review_required` | `needs_manual_validation` |

## Limitation connue : qualité des données lentilles

La base de lentilles a un score de qualité moyen de 31,9/100 (contre 94,1 pour les drivers et 85,9 pour les modules) : **aucune des 52 lentilles importées ne possède de fichier IES ou LDT**. Le moteur de recommandation en tient compte explicitement — toute configuration incluant une lentille reçoit un avertissement "validation photométrique non effectuée" et le statut global passe à `manual_validation_required` ou `compatible_with_warning` (jamais `compatible` sans réserve). Voir section 4 du cahier des charges initial.

## Champs de compatibilité non implémentés en V1 (faute de données)

Certaines règles présentes dans les feuilles `*_compatibility_rules` sources ne sont pas vérifiables avec les données actuelles et ne sont donc **pas implémentées** dans le moteur (plutôt que d'inventer une valeur) :

- Entraxes LED module ↔ lentille (`led_pitch_x_mm`/`led_pitch_y_mm` absents à 100% côté modules).
- Dimensions disponibles du luminaire (non collectées par le formulaire V1).
- Indice IP requis, classe électrique autorisée, tenue au foudre (non collectés par le formulaire V1).
- Matériaux autorisés selon exposition UV (non collectés par le formulaire V1).

Ces critères sont documentés comme extensions futures (section 22 du cahier des charges).
