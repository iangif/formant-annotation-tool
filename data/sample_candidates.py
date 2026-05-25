"""
Example of using fasttrack.
"""

from fasttrackpy import process_audio_textgrid
from fasttrackpy.processors.outputs import pickle_candidates, unpickle_candidates

all_vowels = process_audio_textgrid(
    audio_path="app/static/audio/00000_AA_27_male_27-123349-0036_2.1.wav",
    textgrid_path="app/static/audio/00000_AA_27_male_27-123349-0036_2.1.TextGrid",
    entry_classes=["words", "phones", "vowel"],
    target_tier="vowel",
    target_labels=r"\*",
    min_max_formant=4500,       # corpus-specific
    max_max_formant=6500,       # corpus-specific
    n_formants=4, # corpus-specific
    nstep=20
)

for candidates in all_vowels:
    #candidates.spectrograms(
        #formants=4, # should match n_formants
        #file_name=f"data/images/{candidates.id}.png",
    #)
    #pickle_candidates(candidates, f"data/pickles/{candidates.id}.pkl")
    print(candidates.min_max_formant)