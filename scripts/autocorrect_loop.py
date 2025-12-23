from __future__ import annotations

import argparse
import logging
import subprocess
from pathlib import Path

from uj0e.orchestrator import AgentOrchestrator
from uj0e.tools import ToolResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_tests() -> ToolResult:
    proc = subprocess.run(
        ["python", "-m", "pytest", "-q"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    output = proc.stdout + proc.stderr
    return ToolResult(output=output, ok=proc.returncode == 0)


def auto_correct(goal: str, max_iters: int = 3) -> None:
    orchestrator = AgentOrchestrator()
    for i in range(max_iters):
        logger.info("iteration %s", i + 1)
        state = orchestrator.run(goal=goal, max_iters=2)
        test_result = run_tests()
        logger.info("tests ok? %s", test_result.ok)
        if test_result.ok and state.completed:
            logger.info("goal achieved with passing tests")
            break
        logger.info("retrying with new context")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("goal")
    parser.add_argument("--max-iters", type=int, default=3)
    args = parser.parse_args()
    auto_correct(goal=args.goal, max_iters=args.max_iters)


if __name__ == "__main__":
    main()
