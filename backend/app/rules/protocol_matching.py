"""Correspondance protocole demande -> capacite reelle du driver.

Principe (section 3 du cahier des charges) : ne jamais assumer qu'un protocole en
implique un autre plus avance. DALI-2 et D4i sont traites via leurs propres drapeaux
fiables de la base nettoyee. Pour une demande "DALI" generique (non "DALI-2"), la
seule information fiable disponible dans la base est le drapeau dali_2 (DALI-2 est
un sur-ensemble compatible de DALI) : ce choix est documente ici et rappele dans
l'explication generee, jamais presente comme une certitude absolue.
"""

PROTOCOL_ALIASES = {
    "dali": "dali_2",
    "dali-2": "dali_2",
    "dali2": "dali_2",
    "d4i": "d4i",
    "0-10v": "dimming_0_10v",
    "0-10 v": "dimming_0_10v",
    "1-10v": "dimming_1_10v",
    "1-10 v": "dimming_1_10v",
}


def resolve_protocol_column(protocol: str) -> str | None:
    return PROTOCOL_ALIASES.get(protocol.strip().lower())
