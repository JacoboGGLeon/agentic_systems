"""Skill primitives and filesystem skill-loader compatibility exports.

This package preserves the historical ``agentic_systems._engine.skills`` import surface
while making room for the runtime ``Skill`` API in ``agentic_systems._engine.skills.skill``.
"""

from __future__ import annotations

import importlib

from .loader import LoadedSkill, SkillManifest, load_skill
from .loader import load_skill_definition
from .skill import Skill

__all__ = [
    "Skill",
    "SkillManifest",
    "LoadedSkill",
    "load_skill",
    "load_skill_definition",
    "importlib",
]
