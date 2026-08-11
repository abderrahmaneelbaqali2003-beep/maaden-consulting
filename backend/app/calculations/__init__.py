"""Calculateur technique (V1) : grandeurs electriques, geometriques, thermiques,
energetiques et photometriques estimatives.

Couche de calcul pure et independante : ne decide jamais de compatibilite
(role des matchers dans `app.services`) et ne modifie jamais le score
technique existant (`app.services.scoring_engine`). Aucune donnee manquante
n'est jamais convertie silencieusement en zero : voir `CalculationValue` dans
`models.py`.
"""
