"""Task generators supplied as replaceable implementations of core contracts."""

from math_game.generators.addition import AdditionTaskGenerator
from math_game.generators.defined import DefinedGameTaskGenerator
from math_game.generators.mixed import MixedTaskGenerator
from math_game.generators.multiplication import MultiplicationTaskGenerator
from math_game.generators.subtraction import SubtractionTaskGenerator

__all__ = [
    "AdditionTaskGenerator",
    "DefinedGameTaskGenerator",
    "MixedTaskGenerator",
    "MultiplicationTaskGenerator",
    "SubtractionTaskGenerator",
]
