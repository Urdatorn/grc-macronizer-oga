# -------------------------
# Morph class
# -------------------------
class Morph:
    """
    Stores a UD-style feature string (e.g. 'Mood=Inf|Tense=Pres|Voice=Act')
    and provides feature-level access via .get(). Safe for '_' and empty strings.
    """
    def __init__(self, morph_str):
        # Store features in a dict for fast access
        self._features = {}
        if morph_str and morph_str.strip() != "_":
            for feat in morph_str.split("|"):
                if "=" in feat:
                    k, v = feat.split("=", 1)
                    self._features[k] = v

    def get(self, feature_name):
        """Return the value of a feature, or None if absent."""
        return self._features.get(feature_name, None)

    def __repr__(self):
        return "|".join(f"{k}={v}" for k, v in self._features.items()) or "_"

    # Optional: make object pickle-friendly (not strictly necessary here)
    def __getstate__(self):
        return {"_features": self._features}

    def __setstate__(self, state):
        self._features = state.get("_features", {})


# -------------------------
# Token class
# -------------------------
class Token:
    """
    Drop-in replacement for spaCy Token objects with the attributes:
      - text           (property)
      - lemma_         (property)
      - pos_           (property)
      - morph          (Morph object, property)
      - token_id       (property)  <-- newly supported
    Robust to extra args/kwargs for backward compatibility.
    """
    def __init__(self, text, lemma, pos, morph_str="_", token_id=None, *args, **kwargs):
        """
        text, lemma, pos are required.
        morph_str: UD-style feature string (default "_")
        token_id: optional original token id (int or str)
        *args, **kwargs: accepted and ignored for backward compatibility
        """
        self._text = text
        self._lemma = lemma
        self._pos = pos
        self._morph = Morph(morph_str)
        # store token id (may be None)
        self._id = token_id

        # store any extra kwargs for debugging / compatibility if you want
        # (not used by default)
        if kwargs:
            self._extra = kwargs
        else:
            self._extra = None

    @property
    def text(self):
        return self._text

    @property
    def lemma_(self):
        return self._lemma

    @property
    def pos_(self):
        return self._pos

    @property
    def morph(self):
        return self._morph

    @property
    def token_id(self):
        """Return the stored original token id (or None)."""
        return self._id

    def __repr__(self):
        return (
            f"Token(text={self._text!r}, lemma={self._lemma!r}, pos={self._pos!r}, "
            f"morph={self._morph!r}, token_id={self._id!r})"
        )

    # Optional: pickle helpers to be resilient across code changes
    def __getstate__(self):
        return {
            "_text": self._text,
            "_lemma": self._lemma,
            "_pos": self._pos,
            "_morph": self._morph._features if isinstance(self._morph, Morph) else self._morph,
            "_id": self._id,
            "_extra": self._extra,
        }

    def __setstate__(self, state):
        self._text = state.get("_text")
        self._lemma = state.get("_lemma")
        self._pos = state.get("_pos")
        morph_features = state.get("_morph", {})
        # if _morph was saved as dict of features, restore Morph
        if isinstance(morph_features, dict):
            m = Morph("_")
            m._features = morph_features
            self._morph = m
        else:
            # fallback: try to reconstruct from string
            self._morph = Morph(morph_features or "_")
        self._id = state.get("_id")
        self._extra = state.get("_extra", None)