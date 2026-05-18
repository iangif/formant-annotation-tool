"""
Example of using fasttrack.
"""

from fasttrackpy import process_audio_textgrid
from fasttrackpy.processors.outputs import pickle_candidates, unpickle_candidates

all_vowels = process_audio_textgrid(
    audio_path="data/sample_swedish/SW001_62.wav",
    textgrid_path="data/sample_swedish/SW001_62.TextGrid",
    entry_classes=["words", "phones"],
    target_tier="phones",
    target_labels="[aɛɔuɪe]",
    min_max_formant=4500,       # corpus-specific
    max_max_formant=6500,       # corpus-specific
    n_formants=4, # corpus-specific
    nstep=20
)

for candidates in all_vowels:
    candidates.spectrograms(file_name=f"data/images/{candidates.id}.png")
    pickle_candidates(candidates, f"data/pickles/{candidates.id}.pkl")