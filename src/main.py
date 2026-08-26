# pyright: basic, reportMissingImports=false
"""Entry point for Flet Android and Desktop application."""

from __future__ import annotations

import flet as ft

from math_game.app.flet_app import main

if __name__ == "__main__":
    ft.app(target=main)
