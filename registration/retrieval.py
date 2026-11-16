from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class RetrievalCandidate:
    candidate_id: str
    score: float
    rank: int


class ReferenceRetriever:
    """Interface placeholder for observer-view to reference-view retrieval."""

    def retrieve(self, observer_sample, top_k: int) -> List[RetrievalCandidate]:
        raise NotImplementedError("Use AnyVisLoc baseline wrapper first; custom retrieval comes later.")

