"""Task generators supplied as replaceable implementations of core contracts."""

from math_game.generators.addition import AdditionTaskGenerator
from math_game.generators.subtraction import SubtractionTaskGenerator

__all__ = ["AdditionTaskGenerator", "SubtractionTaskGenerator"]
