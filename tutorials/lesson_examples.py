"""Locate the course's shared application sources once, independently of cwd.

This is teaching support, not a second SDK API. All executions use the installed
agentic_systems package; only reference-application modules are added here.
"""
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "examples"))
sys.path.insert(0, str(PROJECT / "examples/agentic_systems_studio/src"))

from tool_contracts.example import increment as validated_increment  # noqa: E402
from episode_memory.example import build as build_episode  # noqa: E402
from model_serving.example import run as serving_example  # noqa: E402
from agent_contracts.example import run as contracts_example  # noqa: E402
from evaluation_checks.example import run as evaluation_example  # noqa: E402
from order_fulfillment import build_system as build_order_system, verify as verify_orders  # noqa: E402

__all__ = ["validated_increment", "build_episode", "serving_example", "contracts_example",
           "evaluation_example", "build_order_system", "verify_orders"]
