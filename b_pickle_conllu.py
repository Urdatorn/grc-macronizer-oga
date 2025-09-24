"""
Updated pickling script that is compatible with the new Token/Morph classes.

Key fixes:
- Token.__init__ now accepts token_id and extra args/kwargs for backward compatibility.
- Token exposes token_id as a @property so downstream code can use token.token_id.
- Everything else left as in your chunked pickling script.
"""

import pickle
from grc_utils import vowel
from tqdm import tqdm
import os

from class_token import Token


# -------------------------
# Main function with streaming and chunked pickling
# -------------------------
def prepare_sentence_list_from_conllu_ud(input_tsv, output_pkl="oga_sentences.pkl", chunk_size=10000):
    """
    Reads a UD .tsv file and processes sentences into Token objects.
    Skips words without vowels. Writes pickle in chunks to avoid memory issues.

    Minimal changes from your previous version: the Token signature now supports token_id.
    """
    sentence_count = 0
    batch = []

    # ensure output folder exists
    out_dir = os.path.dirname(output_pkl)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # Temporary storage for chunks
    temp_files = []

    current_sentence = []

    # Count total lines for tqdm
    with open(input_tsv, "r", encoding="utf-8") as f:
        total_lines = sum(1 for _ in f)

    with open(input_tsv, "r", encoding="utf-8") as f:
        for line in tqdm(f, total=total_lines, desc="Processing lines"):
            if not line.strip() or line.startswith("#"):
                continue

            fields = line.strip().split("\t")
            if len(fields) < 10:
                continue

            token_id = fields[0]
            if "-" in token_id or "." in token_id:
                continue  # skip multi-word tokens and empty nodes

            # safe token_id int conversion; keep as int if possible
            try:
                token_id_int = int(token_id)
            except ValueError:
                token_id_int = token_id

            text = fields[1]
            lemma_ = fields[2]
            pos_ = fields[3]
            morph_str = fields[5]

            # sentence boundary: token ID resets to 1
            if token_id_int == 1 and current_sentence:
                batch.append(current_sentence)
                sentence_count += 1
                current_sentence = []

                # flush batch to temporary pickle if large
                if len(batch) >= chunk_size:
                    temp_file = f"{output_pkl}_chunk_{len(temp_files)}.pkl"
                    with open(temp_file, "wb") as f_chunk:
                        pickle.dump(batch, f_chunk, protocol=pickle.HIGHEST_PROTOCOL)
                    temp_files.append(temp_file)
                    batch = []

            # skip words without vowels
            if not any(vowel(char) for char in text):
                continue

            # instantiate Token with token_id (works with older and newer constructors)
            tok = Token(text, lemma_, pos_, morph_str, token_id_int)
            current_sentence.append(tok)

    # append last sentence
    if current_sentence:
        batch.append(current_sentence)
        sentence_count += 1

    # flush remaining batch
    if batch:
        temp_file = f"{output_pkl}_chunk_{len(temp_files)}.pkl"
        with open(temp_file, "wb") as f_chunk:
            pickle.dump(batch, f_chunk, protocol=pickle.HIGHEST_PROTOCOL)
        temp_files.append(temp_file)
        batch = []

    # Merge all chunk files into the final pickle
    all_sentences = []
    for temp_file in tqdm(temp_files, desc="Merging chunks"):
        with open(temp_file, "rb") as f_chunk:
            all_sentences.extend(pickle.load(f_chunk))
        os.remove(temp_file)  # clean up temporary file

    # write final merged pickle
    with open(output_pkl, "wb") as f_final:
        pickle.dump(all_sentences, f_final, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"Processed {sentence_count} sentences. Final pickle saved to '{output_pkl}'")
    return all_sentences


if __name__ == "__main__":
    sentences = prepare_sentence_list_from_conllu_ud("example_ud.tsv", "example_ud.pkl", chunk_size=10000)

    # quick verification: load back and print a short sample
    with open("oga_sentences.pkl", "rb") as f:
        loaded_sentences = pickle.load(f)
    print(f"Loaded {len(loaded_sentences)} sentences from final pickle.")
    if loaded_sentences and len(loaded_sentences[0]) > 0:
        tok0 = loaded_sentences[0][0]
        print("Sample token:", tok0)