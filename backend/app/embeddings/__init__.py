"""Text embedding behind a provider abstraction (Phase 6).

The semantic-search service depends only on :class:`EmbeddingProvider`. The
vector dimension is fixed by configuration + migration ``0002`` and must match
the active provider's output.
"""
