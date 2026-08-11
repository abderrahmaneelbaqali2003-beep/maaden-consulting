"""Base documentaire normative (V2) : extraction PDF, chunking, embeddings, recherche.

Cette couche ne prend jamais de decision de compatibilite. Elle est consultee
uniquement APRES le calcul des meilleures configurations par le moteur
deterministe (`app.services.recommendation_engine`), via `EvidenceEnrichmentService`.
"""
