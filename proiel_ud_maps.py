"""
Maps to convert from PROIEL shorthand (used by OGA) to Universal Dependencies (UD) format (used by spaCy).
"""

# POS mapping
pos_map = {
    "n": "NOUN",
    "v": "VERB",
    "a": "ADJ",
    "d": "ADV",
    "c": "SCONJ",   # sometimes CCONJ
    "l": "DET",     # article
    "p": "PRON",
    "r": "ADP",
    "m": "NUM",
    "u": "PUNCT",
    "g": "PART",
    "i": "INTJ",
    "e": "INTJ",    # EXCLAMATION in PROIEL -> INTJ in UD
    "-": "X",
    "x": "X"
}

# feature maps
case_map = {"n": "Nom", "g": "Gen", "d": "Dat", "a": "Acc", "v": "Voc"}
gender_map = {"m": "Masc", "f": "Fem", "n": "Neut", "c": "Com"}   # Common gender
number_map = {"s": "Sing", "p": "Plur", "d": "Dual"}

# note: Future perfect ("t") -> Tense=Fut + Aspect=Perf
tense_map = {
    "p": "Pres",
    "i": "Imp",
    "f": "Fut",
    "a": "Aor",
    "r": "Perf",
    "l": "Pqp",
    "t": "Fut|Aspect=Perf"
}

# note: Gerundive ("g") -> VerbForm=Ger
mood_map = {
    "i": "Ind",
    "s": "Sub",
    "o": "Opt",
    "m": "Imp",
    "n": "Inf",
    "p": "Part",
    "g": "VerbForm=Ger"
}

voice_map = {"a": "Act", "m": "Mid", "p": "Pass", "e": "MedPass"}
degree_map = {"c": "Comp", "s": "Sup", "p": "Pos"}
prontype_map = {"d": "Dem", "i": "Ind", "x": "Int", "r": "Rel", "p": "Prs"}
person_map = {"1": "1", "2": "2", "3": "3"}

feature_dispatch = {
    "Case": case_map,
    "Gender": gender_map,
    "Number": number_map,
    "Tense": tense_map,
    "Mood": mood_map,
    "Voice": voice_map,
    "Degree": degree_map,
    "PronType": prontype_map,
    "Person": person_map
}


def translate_morph(morph_str, unknown_feats):
    if morph_str.strip() == "_" or not morph_str:
        return "_"
    features = []
    for feat in morph_str.split("|"):
        if "=" not in feat:
            continue
        k, v = feat.split("=")
        if k in feature_dispatch:
            mapped = feature_dispatch[k].get(v)
            if mapped:
                # handle multi-feature expansions like "Fut|Aspect=Perf"
                if "|" in mapped:
                    for m in mapped.split("|"):
                        if "=" in m:
                            features.append(m)
                        else:
                            features.append(f"{k}={m}")
                elif "=" in mapped:  # e.g. VerbForm=Ger
                    features.append(mapped)
                else:
                    features.append(f"{k}={mapped}")
            else:
                unknown_feats[f"{k}={v}"] += 1
                features.append(f"{k}={v}")
        else:
            unknown_feats[f"{k}={v}"] += 1
            features.append(f"{k}={v}")
    return "|".join(features)