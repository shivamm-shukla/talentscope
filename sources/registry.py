"""Source selection at the application composition boundary."""

from collections.abc import Callable

from core.interfaces import JobSource
from sources.internshala import InternshalaSource
from sources.remotive import RemotiveSource

SOURCE_FACTORIES: dict[str, Callable[[], JobSource]] = {
    "internshala": InternshalaSource,
    "remotive": RemotiveSource,
}


def create_source(name: str) -> JobSource:
    """Create a configured source by its stable configuration name."""
    try:
        return SOURCE_FACTORIES[name]()
    except KeyError as error:
        supported = ", ".join(sorted(SOURCE_FACTORIES))
        raise ValueError(
            f"Unsupported job source {name!r}; choose one of: {supported}"
        ) from error
