"""Standard-library random source adapter for production use."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass(slots=True)
class PythonRandomSource:
    """Adapter around an independently seedable ``random.Random`` instance."""

    random: random.Random = field(default_factory=random.Random)

    def randint(self, minimum: int, maximum: int) -> int:
        return self.random.randint(minimum, maximum)
