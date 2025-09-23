'''
Dependencies for porting the macronizer to use 
the (UD-style converted) conllu from OGA.

The goal is to enable minimal edits to 
class_text.py and class_macronizer.py.
'''

import pickle
from grc_utils import vowel

# -------------------------
# Morph class
# -------------------------
class Morph:
    def __init__(self, feature_str):
        """
        feature_str: e.g., "Mood=Inf|Tense=Pres|Voice=Act"
        """
        self.features = {}
        for feat in feature_str.split("|"):
            if "=" in feat:
                k, v = feat.split("=")
                self.features[k] = v

    def get(self, key):
        """
        Return the value of a feature, e.g., get('Mood') -> 'Inf'
        """
        return self.features.get(key, None)

# -------------------------
# Token class
# -------------------------
class Token:
    def __init__(self, text, lemma_, pos_, morph_str, token_id):
        self._text = text
        self._lemma = lemma_
        self._pos = pos_
        self._morph = Morph(morph_str)
        self._id = token_id  # store original token ID

    def text(self):
        return self._text

    def lemma_(self):
        return self._lemma

    def pos_(self):
        return self._pos

    def morph(self):
        return self._morph

    def token_id(self):
        return self._id

# -------------------------
# Main function
# -------------------------
def prepare_sentence_list_from_conllu_ud(input_tsv, output_pkl="oga_sentences.pkl"):
    """
    input_tsv: path to concatenated UD tsv
    output_pkl: path to write pickle file
    Returns: list of sentences, each sentence is a list of Token objects
    Skips words that contain no vowel according to grc_utils.vowel()
    """
    sentences = []
    current_sentence = []

    with open(input_tsv, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue

            fields = line.strip().split("\t")
            if len(fields) < 10:
                continue

            token_id = fields[0]
            if "-" in token_id or "." in token_id:
                # skip multi-word tokens and empty nodes
                continue

            token_id_int = int(token_id)
            text = fields[1]
            lemma_ = fields[2]
            pos_ = fields[3]
            morph_str = fields[5]

            # check for sentence boundary (id resets to 1)
            if token_id_int == 1 and current_sentence:
                sentences.append(current_sentence)
                current_sentence = []

            # skip words without vowels
            if not any(vowel(char) for char in text):
                continue

            tok = Token(text, lemma_, pos_, morph_str, token_id_int)
            current_sentence.append(tok)

    if current_sentence:
        sentences.append(current_sentence)

    # write to binary pickle file
    with open(output_pkl, "wb") as f:
        pickle.dump(sentences, f)

    print(f"Saved {len(sentences)} sentences to '{output_pkl}'")
    return sentences

sentences = prepare_sentence_list_from_conllu_ud("oga_conllu_ud.tsv", "oga_sentences.pkl")

# inspect first sentence
for tok in sentences[0]:
    print(tok.token_id(), tok.text(), tok.lemma_(), tok.pos_(), tok.morph().get("Mood"))

# load later
with open("oga_sentences.pkl", "rb") as f:
    loaded_sentences = pickle.load(f)