"""Couche "domaine" neutre : concepts partages par plusieurs modes de saisie du besoin
(CPS/CCTP, saisie manuelle, assistant IA) sans qu'aucun de ces modes ne depende des
autres. `app/cps/` et `app/ai/` dependent tous les deux de `app/domain/` ; l'inverse
n'est jamais vrai, et `app/cps/` et `app/ai/` ne s'importent jamais l'un l'autre."""
