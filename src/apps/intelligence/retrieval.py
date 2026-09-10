"""Tenant-isolated, encrypted knowledge chunking and bounded retrieval."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from django.db import transaction

from apps.intelligence.models import KnowledgeChunk, KnowledgeSource
from apps.knowledge.models import SharedKnowledgeChunk, SharedKnowledgeSource
from apps.organizations.models import Organization

CHUNK_CHARS = 900
CHUNK_OVERLAP_CHARS = 120


@dataclass(frozen=True)
class ChunkRefreshResult:
    created: int
    removed: int
    unchanged: int


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def query_words(value: str) -> list[str]:
    """Normalise natural-language punctuation before bounded lexical retrieval."""
    return [word.casefold() for word in re.findall(r"[\wÀ-ÿ]+", value) if len(word) > 2][:5]


def split_knowledge(value: str) -> list[str]:
    """Create a few readable chunks without losing a sentence at each boundary."""
    text = _normalise(value)
    if not text:
        return []
    chunks: list[str] = []
    cursor = 0
    while cursor < len(text):
        end = min(cursor + CHUNK_CHARS, len(text))
        if end < len(text):
            boundary = max(text.rfind(". ", cursor, end), text.rfind("; ", cursor, end))
            if boundary > cursor + CHUNK_CHARS // 2:
                end = boundary + 1
        chunk = text[cursor:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        cursor = max(end - CHUNK_OVERLAP_CHARS, cursor + 1)
    return chunks


def refresh_knowledge_chunks(*, organization: Organization) -> ChunkRefreshResult:
    """Idempotently rebuild only approved sources in one office."""
    created = removed = unchanged = 0
    approved = KnowledgeSource.objects.filter(
        organization=organization, status=KnowledgeSource.Status.APPROVED
    )
    with transaction.atomic():
        KnowledgeChunk.objects.filter(organization=organization).exclude(
            source__in=approved
        ).delete()
        for source in approved:
            desired = [
                (
                    ordinal,
                    text,
                    hashlib.sha256(f"{ordinal}\x1f{text}".encode()).hexdigest(),
                )
                for ordinal, text in enumerate(split_knowledge(source.content))
            ]
            existing = {
                chunk.content_hash: chunk
                for chunk in KnowledgeChunk.objects.filter(organization=organization, source=source)
            }
            desired_hashes = {content_hash for _, _, content_hash in desired}
            stale = [
                chunk.id
                for content_hash, chunk in existing.items()
                if content_hash not in desired_hashes
            ]
            if stale:
                removed += len(stale)
                KnowledgeChunk.objects.filter(id__in=stale).delete()
            for ordinal, content, content_hash in desired:
                chunk = existing.get(content_hash)
                if chunk is None:
                    KnowledgeChunk.objects.create(
                        organization=organization,
                        source=source,
                        ordinal=ordinal,
                        content=content,
                        content_hash=content_hash,
                    )
                    created += 1
                elif chunk.ordinal != ordinal:
                    chunk.ordinal = ordinal
                    chunk.save(update_fields=["ordinal", "updated_at"])
                    unchanged += 1
                else:
                    unchanged += 1
    return ChunkRefreshResult(created=created, removed=removed, unchanged=unchanged)


def retrieve_chunks(
    *, organization: Organization, query: str, limit: int = 4
) -> list[KnowledgeChunk]:
    words = query_words(query)
    if not words:
        return []
    matches: list[KnowledgeChunk] = []
    chunks = KnowledgeChunk.objects.filter(
        organization=organization, source__status=KnowledgeSource.Status.APPROVED
    ).select_related("source")
    for chunk in chunks:
        searchable = chunk.content.casefold()
        if any(word in searchable for word in words):
            matches.append(chunk)
            if len(matches) >= limit:
                break
    return matches


def refresh_shared_knowledge_chunks() -> ChunkRefreshResult:
    """Rebuild the global corpus in the ``knowledge`` database only."""
    created = removed = unchanged = 0
    approved = SharedKnowledgeSource.objects.using("knowledge").filter(
        status=SharedKnowledgeSource.Status.APPROVED
    )
    with transaction.atomic(using="knowledge"):
        SharedKnowledgeChunk.objects.using("knowledge").exclude(source__in=approved).delete()
        for source in approved:
            desired = [
                (ordinal, text, hashlib.sha256(f"{ordinal}\x1f{text}".encode()).hexdigest())
                for ordinal, text in enumerate(split_knowledge(source.content))
            ]
            existing = {
                chunk.content_hash: chunk
                for chunk in SharedKnowledgeChunk.objects.using("knowledge").filter(source=source)
            }
            desired_hashes = {content_hash for _, _, content_hash in desired}
            stale = [
                chunk.id
                for content_hash, chunk in existing.items()
                if content_hash not in desired_hashes
            ]
            if stale:
                removed += len(stale)
                SharedKnowledgeChunk.objects.using("knowledge").filter(id__in=stale).delete()
            for ordinal, content, content_hash in desired:
                chunk = existing.get(content_hash)
                if chunk is None:
                    SharedKnowledgeChunk.objects.using("knowledge").create(
                        source=source,
                        ordinal=ordinal,
                        content=content,
                        content_hash=content_hash,
                    )
                    created += 1
                elif chunk.ordinal != ordinal:
                    chunk.ordinal = ordinal
                    chunk.save(using="knowledge", update_fields=["ordinal", "updated_at"])
                    unchanged += 1
                else:
                    unchanged += 1
    return ChunkRefreshResult(created=created, removed=removed, unchanged=unchanged)


def retrieve_shared_chunks(*, query: str, limit: int = 2) -> list[SharedKnowledgeChunk]:
    """Bounded global retrieval; models here carry no tenant key or tenant FK."""
    words = query_words(query)
    if not words:
        return []
    matches: list[SharedKnowledgeChunk] = []
    chunks = (
        SharedKnowledgeChunk.objects.using("knowledge")
        .filter(source__status=SharedKnowledgeSource.Status.APPROVED)
        .select_related("source")
    )
    for chunk in chunks:
        if any(word in chunk.content.casefold() for word in words):
            matches.append(chunk)
            if len(matches) >= limit:
                break
    return matches
