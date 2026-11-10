"""Beyond-accuracy metrics for the held-out rankings (proposal 3.2.4, NFR-12, #199).

Computed over each ranking's top k for the held-out children. None of them
needs labels:

- intra-list diversity: mean pairwise semantic distance (1 - cosine) between
  the SBERT vectors of a child's top k; 0 = identical, higher = more varied;
- area diversity: distinct developmental areas in a child's top k, divided
  by k (1.0 = every slot a different area, capped by the five areas);
- catalogue coverage: share of the eligible activities that appear in at
  least one child's top k;
- personalisation: 1 - mean overlap of the top k between pairs of children;
- novelty: mean self-information, -log2(share of children whose top k
  contains the activity), over every recommended slot. With no usage data,
  "popular" means recommended to many of the held-out children, so higher
  novelty = less repetition of the same activities across children.
"""

import math
from collections import Counter
from itertools import combinations

import numpy as np


def intra_list_diversity(ids, vectors):
    """Mean pairwise 1 - cosine of the L2-normalised vectors of ids."""
    pairs = list(combinations(ids, 2))
    if not pairs:
        return None
    return float(np.mean([1.0 - float(vectors[a] @ vectors[b]) for a, b in pairs]))


def area_diversity(ids, areas):
    """Distinct areas among ids, divided by len(ids)."""
    if not ids:
        return None
    return len({areas[a] for a in ids}) / len(ids)


def catalogue_coverage(lists, catalogue_size):
    """Share of the catalogue appearing in at least one list."""
    if not catalogue_size:
        return None
    return len({a for ids in lists for a in ids}) / catalogue_size


def novelty(lists):
    """Mean -log2(p) over every slot, p = share of lists containing it."""
    lists = [ids for ids in lists if ids]
    if not lists:
        return None
    counts = Counter(a for ids in lists for a in set(ids))
    n = len(lists)
    slots = [-math.log2(counts[a] / n) for ids in lists for a in ids]
    return float(np.mean(slots))


def overlap(a, b):
    """Share of a's slots also in b (top-k lists of equal length)."""
    if not a:
        return None
    return len(set(a) & set(b)) / len(a)


def personalisation(lists):
    """1 - mean pairwise overlap of the lists; 1.0 = no two lists share."""
    pairs = list(combinations([ids for ids in lists if ids], 2))
    if not pairs:
        return None
    return 1.0 - float(np.mean([overlap(a, b) for a, b in pairs]))
