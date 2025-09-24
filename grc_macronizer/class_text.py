'''
New version made to use lemma, pos and morph from the OGA conllu instead of odyCy.
'''

import logging
import re
from tqdm import tqdm
import warnings

from grc_utils import (
    ACCENTS,
    ACUTES,
    count_dichrona_in_open_syllables,
    GRAVES,
    is_greek_numeral,
    lower_grc,
    normalize_word,
    ROUGHS,
)

from .stop_list import stop_list
from .stop_list_epic import epic_stop_words

warnings.filterwarnings("ignore", category=FutureWarning)

greek_ano_teleia = "\u0387"
greek_question_mark = "\u037e"
middle_dot = "\u00b7"
apostrophes = "'’‘´΄\u02bc᾿͵"  # the last one is for thousands


def word_list(text):
    to_clean = (
        r"[\u0387\u037e\u00b7\.,!?;:\"()\[\]{}<>«»\-—…|⏑⏓†×]"  # NOTE hyphens must be escaped
    )
    cleaned_text = re.sub(to_clean, " ", text)
    word_list = [word for word in cleaned_text.split() if word]
    logging.debug(f"Diagnostic word list: {word_list}")
    return word_list


class Text:
    """
    Container for text and metadata during macronization.

    Minimally modified to work with custom pickled Token/Morph objects 
    with info from the OGA conllu, instead of spaCy docs from OdyCy.

    """

    def __init__(self, sentences, genre="prose", debug=False, lowercase=False):
        """
        sentences: list[list[Token]] — list of sentences, each sentence is a list of Token objects
        """
        #
        # -- Prepare diagnostic word list (flatten text from tokens) --
        #

        all_text = " ".join(token.text for sent in sentences for token in sent)

        ### Clean non-Greek characters and punctuation

        chars_to_clean = r'[\^_()\[\]{}<>⟨⟩⎡⎤\"«»\-—…|⏑⏓†×]'
        oga = r'[#$%&*+/=@~£¦§¨ª¬¯°±²³¶¸¹½¿ÁÄÆÈÉÌÍÒÓÖÚÜßàáâäæçèéëìíïòóôö÷ùúüýÿĀāćĎďĹŒœŕźƑǁȳɛʰʳ˘˙˝ˡˢˣ̠̣͎̀́̄̅̆̇̈̊̔͂͞ͅ΅ЗСҀҁҏӄӔӕֹלݲតហឲាិេᵃᵅᵇᵈᵉᵊᵍᵏᵐᵒᵖᵗᵘᵛᵝᶜᶠᶦᶹḍḿṃẂẃẉạụỳ‐‒–―‖✶❮❯⟦⟧⥼⥽⦵⨆⩚⩹⫯⸕⸢⸣⸤⸥⸨〈〉ﬀﬁ＊－｢�𐅵𝒢𝒮𝔮𝕷‹›※‾⁄⁎⁑⁰ⁱ⁴⁵⁶⁷⁸⁹ⁿ€™ℵ∗√∠∴∼∾⊏⊔⊙⊢⊣⊤⊻⋃⋆⋇⋖⌈⌉⌊⌋⌞⌟⏒⏔⏕─═║△○◻★☼☾☿♀♂♃♄]' # OCR errors in OGA; rarely found in edited digital edition

        all_text = re.sub(chars_to_clean, '', all_text)
        all_text = re.sub(oga, '', all_text)

        # normalize + lowercase if requested
        all_text = normalize_word(all_text)
        if lowercase:
            all_text = lower_grc(all_text)

        diagnostic_word_list = word_list(all_text)

        if debug:
            logging.debug(f"Text after normalization: {all_text}")

        logging.debug(f"Loaded {len(sentences)} sentences.")
        for i, sentence in enumerate(sentences):
            logging.debug(f"{i}: {' '.join(tok.text for tok in sentence)}")

        #
        # -- Preparing the master list of words to be macronized (and handling ἄν) --
        #
        an_list = []
        fail_counter = 0
        buggy_words_in_input = 0
        token_lemma_pos_morph = []

        for sentence in sentences:
            for token in sentence:
                logging.debug(
                    f"Considering token: {token.text}\tLemma: {token.lemma_}\tPOS: {token.pos_}\tMorph: {token.morph}"
                )

                if token.text in ("ἂν", "ἄν"):
                    an = token.text
                    subjunctive_verb = False
                    no_ei = True
                    logging.debug(f"\t\tPROCESSING ἂν/ἄν: {token.text}")

                    # Look at the *current sentence* instead of spaCy doc
                    for inner_token in sentence:
                        if "Sub" in (inner_token.morph.get("Mood") or ""): # NOTE fallback to avoid TypeError if get() returns None
                            subjunctive_verb = True
                        if inner_token.text in ("εἰ", "εἴ"):
                            no_ei = False
                            logging.debug(f"\t\tEi found: {inner_token.text}")

                    if subjunctive_verb and no_ei:
                        an_list.append(an[0] + "_" + an[1])
                        logging.debug(f"\t\tLong ἂν macronized")
                    else:
                        an_list.append(an[0] + "^" + an[1])
                        logging.debug(f"\t\tShort ἂν macronized")

                if token.text and token.pos_:
                    orth = token.text.replace("\u0387", "").replace(
                        "\u037e", ""
                    )  # remove ano teleia + Greek question mark
                    logging.debug(f"\tToken text: {orth}")

                    # === FILTERS ===

                    # 1 Numerals
                    if is_greek_numeral(orth):
                        logging.debug(
                            f"Word '{orth}' is a Greek numeral. Skipping with 'continue'."
                        )
                        continue

                    # 2 Stop words
                    if orth in stop_list:
                        logging.info(
                            f"General stop word '{orth}' found. Skipping with 'continue'."
                        )
                        continue
                    if genre == "epic" and orth in epic_stop_words:
                        logging.info(
                            f"Epic stop word '{orth}' found. Skipping with 'continue'."
                        )
                        continue

                    # 3 Formatting/OCR errors
                    if "ς" in list(orth[:-1]):
                        logging.debug(
                            f"Word '{orth}' contains a final sigma mid-word. Skipping with 'continue'."
                        )
                        buggy_words_in_input += 1
                        continue
                    if (
                        sum(char in GRAVES for char in orth) > 1
                        or (
                            any(char in GRAVES for char in orth)
                            and any(char in ACUTES for char in orth)
                        )
                        or sum(char in ACCENTS for char in orth) > 2
                        or sum(char in ROUGHS for char in orth) > 2
                    ):
                        logging.debug(
                            f"Pathological word '{orth}' has invalid diacritics. Skipping."
                        )
                        buggy_words_in_input += 1
                        continue

                    if (
                        orth not in diagnostic_word_list
                        and orth not in ("ἂν", "ἄν")
                    ):
                        fail_counter += 1
                        logging.debug(
                            f"Word '{orth}' not in diagnostic word list. Skipping."
                        )
                        continue

                    # Skip words without dichrona
                    if count_dichrona_in_open_syllables(orth) == 0 and orth not in [
                        "ἂν_",
                        "ἂν^",
                        "ἄν_",
                        "ἄν^",
                    ]:
                        logging.debug(
                            f"Word '{orth}' has no dichrona. Skipping with 'continue'."
                        )
                        continue

                    # Special case: ἂν/ἄν macronization
                    if token.text in ("ἂν", "ἄν"):
                        macronized_an = an_list.pop(0)
                        token_lemma_pos_morph.append(
                            [macronized_an, token.lemma_, token.pos_, token.morph]
                        )
                        logging.debug(
                            f"Popping an {macronized_an}! {len(an_list)} left to pop"
                        )
                    else:
                        token_lemma_pos_morph.append(
                            [orth, token.lemma_, token.pos_, token.morph]
                        )

                    logging.debug(
                        f"\tAppended: Token: {token.text}\tLemma: {token.lemma_}\tPOS: {token.pos_}\tMorph: {token.morph}"
                    )

        # Sanity checks and final logging
        assert an_list == [], f"An list is not empty: {an_list}. This means that the ἂν macronization step failed. Please check the code."
        logging.debug(f'Len of token_lemma_pos_morph: {len(token_lemma_pos_morph)}')
        if len(token_lemma_pos_morph) == 1:
            logging.debug(f'Only element of token_lemma_pos_morph: {token_lemma_pos_morph[0]}')
        if len(token_lemma_pos_morph) > 1:
            logging.debug(f'First elements of token_lemma_pos_morph: {token_lemma_pos_morph[0]}, {token_lemma_pos_morph[1]}...')
        logging.info(f'odyCy fail count: {fail_counter}')

        self.text = all_text
        self.genre = genre
        self.token_lemma_pos_morph = token_lemma_pos_morph
        self.macronized_words = [] # populated by class_macronizer
        self.macronized_text = ''
        self.debug = debug

        self.fail_counter = fail_counter
        self.buggy_words_in_input = buggy_words_in_input

    def integrate(self):
        """
        Integrates the macronized words back into the original text.
        """
        result_text = self.text # making a working copy
        macronized_words = [word for word in self.macronized_words if word is not None and any(macron in word for macron in ['_', '^'])]
        
        word_counts = {}
        
        replacements = [] # going to be a list of triples: (starting position, ending position, macronized word)
        
        for macronized_word in tqdm(macronized_words, desc="Finding replacements", leave=False):
            normalized_word = normalize_word(macronized_word.replace('_', '').replace('^', ''))
            
            if not normalized_word:
                continue
            
            current_count = word_counts.get(normalized_word, 0)  # how many times have we seen the present word before? default to 0
            
            if self.debug:
                logging.debug(f"Processing: {macronized_word} (Current count: {current_count})")
            
            '''
            NOTE re the regex: \b does not work for strings containing apostrophe!
            Hence we use negative lookbehind (?<!) and lookahead groups (?!) with explicit w to match word boundaries instead.
            '''
            matches = list(re.finditer(fr"(?<!\w){normalized_word}(?!\w)", self.text))
            matches = [m for m in matches if (m.group() != "ἂν" or m.group() != "ἄν" or m.group() != "ἀν")] # remove ἂν and ἄν from the list of matches, since they are already macronized

            if current_count >= len(matches):
                logging.debug(f"Current count: {current_count}, Matches: {matches}")
                print(f"Could not find occurrence {current_count + 1} of word '{normalized_word}'")
                continue
                #raise ValueError(f"Could not find occurrence {current_count + 1} of word '{normalized_word}'")
            
            target_match = matches[current_count]
            # .start() and .end() are methods of a regex Match object, giving the start and end indices of the match
            # NOTE TO SELF TO REMEMBER: .start() is inclusive, while .end() is *exclusive*, meaning .end() returns the index of the first character *just after* the match
            start_pos = target_match.start()
            end_pos = target_match.end()
            
            replacements.append((start_pos, end_pos, macronized_word))
            
            word_counts[normalized_word] = current_count + 1
        
        # NOTE USEFUL NLP TRICK: Reversing the replacements list. This is because when a ^ or _ is added to a word, the positions of all subsequent words change, but those of all previous words remain the same.
        replacements.sort(reverse=True, key=lambda x: x[0]) # the lambda means sorting by start_pos *only*: ties are left in their original order. I don't think this is necessary, because there shouldn't be two words with the identical start_pos.
        
        for start_pos, end_pos, replacement in tqdm(replacements, desc="Applying replacements", leave=False):
            result_text = result_text[:start_pos] + replacement + result_text[end_pos:] # remember, slicing (:) means "from and including" the start index and "up to but not including" the end index, so this line only works because .end() is exclusive, as noted above!
        
        self.macronized_text = result_text
        
        # Verify that only macrons have been changed
        original_no_macrons = self.text.replace('_', '').replace('^', '')
        result_no_macrons = self.macronized_text.replace('_', '').replace('^', '')
        
        if original_no_macrons != result_no_macrons:
            print("Original (no macrons):", repr(original_no_macrons[:100]), "...")
            print("Result (no macrons):", repr(result_no_macrons[:100]), "...")
            
            # Find the first difference
            for i, (orig_char, result_char) in enumerate(zip(original_no_macrons, result_no_macrons)):
                if orig_char != result_char:
                    print(f"First difference at position {i}: '{orig_char}' vs '{result_char}'")
                    print(f"Context: '{original_no_macrons[max(0, i-10):i+10]}' vs '{result_no_macrons[max(0, i-10):i+10]}'")
                    break
            
            if len(original_no_macrons) != len(result_no_macrons):
                print(f"Length difference: original={len(original_no_macrons)}, result={len(result_no_macrons)}")
            
            print("Integration corrupted the text: changes other than macrons were made.")
            logging.debug("Integration corrupted the text: changes other than macrons were made.")
        
        return self.macronized_text
