'''
Here I generate baseline where I let every open syllable be marked as short
before comparing with Norma Syllaborum Graecorum.
'''

from datetime import datetime
from difflib import SequenceMatcher
import os
import re

from grc_utils import vowel, syllabifier
from move_text_into_brackets import move_text_into_brackets

nr_of_tosses = 0

greek_punctuation_and_editorial_signs = r'[\u0387\u037e\u00b7\.,!?;:\"()<>\-—…«»†]'
apostrophes = r"[''\u02bc]" 

# ---------- Configuration ----------

coin_toss = True
base_dir = "/Users/albin/git/norma-syllabarum-graecarum/final"
log_path = "scripts/norma_log.tsv"
output_path = "scripts/norma_output.tsv"
stoplist_file = "/Users/albin/git/norma-syllabarum-graecarum/stoplist.txt"

# Hardcoded file stoplist (filenames)
file_stoplist = {
    "norma_aristophanis_canticorum.txt",
}

# ANSI colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

# ---------- Load stoplist of wordforms ----------
if os.path.exists(stoplist_file):
    with open(stoplist_file, "r", encoding="utf-8") as f:
        wordform_stoplist = set(line.strip() for line in f if line.strip())
else:
    wordform_stoplist = set()

files = sorted([
    f for f in os.listdir(base_dir)
    if f.endswith(".txt") and f not in file_stoplist
])

total_files = len(files)
total_correct = 0
total_expected = 0
total_mismatches = 0
total_skipped = 0

# ---------- Helper: Progress bar ----------
def print_progress(current, total, filename, width=40):
    percent = current / total
    filled = int(width * percent)
    bar = "#" * filled + "-" * (width - filled)
    print(f"\r[{bar}] {current}/{total} - {filename}", end='', flush=True)

# ---------- Helper: Remove ^/_ from closed syllables ----------
def clean_closed_syllables(syllables):
    cleaned = []
    for syll in syllables:
        core = syll.replace("^", "").replace("_", "").replace("€", "").replace("#", "").replace(".", "").replace(",", "").replace("'", "").replace(";", "").rstrip()
        core = re.sub(greek_punctuation_and_editorial_signs, "", core)
        last_char = core[-1] if core else ''
        if not vowel(last_char):
            #print(f"{syll} is closed!")
            syll = syll.replace("^", "").replace("_", "")
        cleaned.append(syll)
    return cleaned

def coin_toss_open_syllables(syllables):
    global nr_of_tosses

    randomized = []
    for syll in syllables:
        core = syll.replace("^", "").replace("_", "").replace("€", "").replace("#", "").rstrip()
        core = re.sub(greek_punctuation_and_editorial_signs, "", core)
        last_char = core[-1] if core else ''
        if vowel(last_char):
            syll = syll + "^"
            nr_of_tosses += 1
        randomized.append(syll)
    
    return randomized

# ---------- Helper: Strip ^/_ from gold words in stoplist ----------
def strip_marks_from_stopwords(gold):
    def remove_if_in_stoplist(word):
        word_no_marks = word.replace("^", "").replace("_", "")
        if word_no_marks in wordform_stoplist:
            return word.replace("^", "").replace("_", "")
        return word
    return " ".join(remove_if_in_stoplist(w) for w in gold.split())

# ---------- Main Loop ----------
with open(log_path, "w", encoding="utf-8") as log_file, \
     open(output_path, "w", encoding="utf-8") as out_file:

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file.write(f"RUN STARTED: {timestamp}\n")
    log_file.write("Expected\tOutput\n")

    out_file.write(f"RUN STARTED: {timestamp}\n")
    out_file.write("Expected\tOutput\n")

    for idx, filename in enumerate(files, start=1):
        print_progress(idx, total_files, filename)
        filepath = os.path.join(base_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        correct = 0
        expected = 0
        mismatches = 0
        skipped = 0

        for line in lines:
            line = move_text_into_brackets(line)
            if not line:
                continue

            # Get plain input
            plain_input = re.sub(r"[\[\]\{\}#€_\^]", "", line)
            if not plain_input.strip():
                skipped += 1
                continue

            # Get bracketed syllables from gold line
            gold_sylls = re.findall(r"[\{\[]([^\}\]]+)[\}\]]", line)
            gold_sylls_cleaned = clean_closed_syllables(gold_sylls)
            gold = "".join(gold_sylls_cleaned)
            gold = strip_marks_from_stopwords(gold)
            gold = re.sub(greek_punctuation_and_editorial_signs, "", gold)
            gold = re.sub(apostrophes, "'", gold)

            # # Run model and syllabify
            # try:
            #     model_output = macronizer.macronize(plain_input)
            # except Exception:
            #     skipped += 1
            #     continue

            output_sylls = syllabifier(plain_input)
            output_sylls = clean_closed_syllables(output_sylls)

            if coin_toss == True:
                output_sylls = coin_toss_open_syllables(output_sylls)

            output = "".join(output_sylls)
            output = re.sub(greek_punctuation_and_editorial_signs, "", output)

            expected_line = gold.count("^") + gold.count("_")
            
            # Use difflib for robust alignment-based comparison
            matcher = SequenceMatcher(None, output, gold)
            correct_line = 0
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == 'equal':
                    segment = output[i1:i2]
                    correct_line += segment.count("^") + segment.count("_")

            expected += expected_line
            correct += correct_line

            out_file.write(f"{gold}\t{output}\n")

            if output != gold:
                log_file.write(f"{gold}\t{output}\n")
                mismatches += 1

        total_correct += correct
        total_expected += expected
        total_mismatches += mismatches
        total_skipped += skipped

        ratio = correct / expected if expected else 1.0
        color = GREEN if ratio > 0.95 else YELLOW if ratio > 0.85 else RED
        print(f"\n{filename:<30} {color}{ratio:.2%}{RESET} ({mismatches} mismatches, {skipped} skipped lines)")

# ---------- Final Summary ----------
print(f"\nNumber of open syllables: {nr_of_tosses}\n")

global_ratio = total_correct / total_expected if total_expected else 1.0
color = GREEN if ratio > 0.95 else YELLOW if ratio > 0.85 else RED

print(f"\nTotal lines with differences: {RED}{total_mismatches}{RESET}")
print(f"Total lines skipped due to empty or error: {YELLOW}{total_skipped}{RESET}")
print(f"Overall accuracy: {color}{global_ratio:.2%}{RESET}")
print(f"Log saved to {log_path}")
print(f"Full output saved to {output_path}")