"""Motifs regex deterministes pour l'extraction d'exigences CPS/CCTP (francais).

Perimetre volontairement restreint (a la demande du consultant) aux seules grandeurs
qui alimentent directement le calculateur et le moteur MAADEN : flux lumineux, CCT,
puissance, tension nominale, courant, protocole de commande, geometrie routiere.
Aucun LLM : uniquement des expressions regulieres et des dictionnaires de mots-cles.
Chaque motif reste volontairement etroit (mot-cle + valeur dans une fenetre courte)
pour limiter les faux positifs ; en cas de doute, plusieurs candidats sont produits
plutot qu'un seul choisi arbitrairement -- la decision finale reste humaine.
"""

import re

NUMBER = r"(\d[\d\s.,]*\d|\d)"

FLUX_LM = re.compile(rf"flux(?:\s+lumineux)?[^.\n]{{0,40}}?{NUMBER}\s*(?:lm|lumens?)\b", re.IGNORECASE)
POWER_W = re.compile(rf"(?:puissance|jusqu.{{0,2}})[^.\n]{{0,40}}?{NUMBER}\s*(?:w|watts?)\b", re.IGNORECASE)
CCT_K = re.compile(rf"(?:temp[eé]rature\s+de\s+couleur|\bcct\b)[^.\n]{{0,20}}?{NUMBER}\s*k\b", re.IGNORECASE)

# Courant : le CPS decrit generalement le courant du luminaire complet ("courant
# fonctionnant inferieur a 750 mA") -- utilise directement comme courant nominal cible
# de l'etude (simplification assumee : le consultant reste libre de le corriger).
CURRENT_MA = re.compile(rf"courant(?:\s+nominal)?[^.\n]{{0,40}}?{NUMBER}\s*m\s?a\b", re.IGNORECASE)

# Tension NOMINALE uniquement (motif etroit et explicite) : ne doit jamais capturer une
# tension d'alimentation secteur ("Voltage 220-240 VAC") qui n'a pas le meme sens qu'une
# tension nominale de module DC -- un CPS route/luminaire ne precise quasiment jamais
# cette donnee interne, la saisie manuelle reste la norme pour ce champ.
VOLTAGE_NOMINAL_V = re.compile(rf"tension\s+nominale[^.\n]{{0,30}}?{NUMBER}\s*v\b", re.IGNORECASE)

POLE_HEIGHT_M = re.compile(rf"hauteur(?:\s+d.installation)?[^.\n]{{0,40}}?{NUMBER}\s*m\b", re.IGNORECASE)
POLE_SPACING_M = re.compile(rf"(?:espacement|entraxe)[^.\n]{{0,40}}?{NUMBER}\s*m\b", re.IGNORECASE)
ROAD_WIDTH_M = re.compile(rf"largeur(?:\s+de\s+chauss[eé]e)?[^.\n]{{0,40}}?{NUMBER}\s*m\b", re.IGNORECASE)
ROAD_LENGTH_M = re.compile(
    rf"longueur(?:\s+(?:du\s+tron[cç]on|de\s+(?:la\s+)?route|totale))?[^.\n]{{0,40}}?{NUMBER}\s*m\b",
    re.IGNORECASE,
)

PROTOCOL_KEYWORDS = ["DALI-2", "DALI", "D4i", "0-10V", "1-10V", "PLC"]

LAYOUT_KEYWORDS = {
    "unilateral": ["unilateral", "unilaterale"],
    "opposite": ["vis-a-vis", "vis a vis", "bilateral", "bilaterale", "opposee"],
    "staggered": ["quinconce"],
    "central": ["mat central", "implantation centrale", "bi-face", "biface"],
}
