"""Adapters that normalize external job-board data into core domain models."""

from sources.internshala import InternshalaSource
from sources.remotive import RemotiveSource

__all__ = ["InternshalaSource", "RemotiveSource"]
