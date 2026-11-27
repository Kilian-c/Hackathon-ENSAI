"""Source d'aléatoire unique du moteur (R1) : un flux indépendant par nom.

Un flux par variable du générateur (`x`, `eps`...) et `method:<id>` pour une méthode : changer une
hypothèse ne décale donc jamais les tirages des autres variables (même graine = mêmes tirages).
"""

import zlib

import numpy as np


def rng_for(seed: int, name: str) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, zlib.crc32(name.encode())])))
