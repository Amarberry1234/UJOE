from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from langgraph.graph import StateGraph, END

from .config import settings
from .model_client import ModelClient
from .tools import AuditLogger, LocalFileTool, SandboxTool, ToolResult
from .vector import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class AgentState:
    goal: str
    history: list[dict[str, str]] = field(default_factory=list)
    iterations: int = 0
    max_iters: int = 3
    last_result: ToolResult | None = None
    plan: list[str] = field(default_factory=list)
    completed: bool = False


class AgentOrchestrator:
    def __init__(self) -> None:
        self.model = ModelClient()
        self.sandbox = SandboxTool()
        self.files = LocalFileTool()
        self.vector = VectorStore()
        self.audit = AuditLogger()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)
        graph.add_node("plan", self._plan)
        graph.add_node("act", self._act)
        graph.add_node("reflect", self._reflect)

        graph.set_entry_point("plan")
        graph.add_edge("plan", "act")
        graph.add_edge("act", "reflect")
        graph.add_edge("reflect", END)
        graph.add_edge("reflect", "act", condition=lambda s: not s.completed and s.iterations < s.max_iters)
        return graph

    def run(self, goal: str, max_iters: int = 3) -> AgentState:
        state = AgentState(goal=goal, max_iters=max_iters)
        app = self.graph.compile()
        result: AgentState = app.invoke(state)
        return result

    def _plan(self, state: AgentState) -> AgentState:
        prompt = [
            {"role": "system", "content": "Plan up to 4 steps to achieve the goal."},
            {"role": "user", "content": state.goal},
        ]
        plan_text = self.model.chat(prompt)
        state.plan = [line.strip("- ") for line in plan_text.split("\n") if line.strip()]
        state.history.append({"role": "assistant", "content": plan_text})
        self.audit.log("plan", {"goal": state.goal, "plan": state.plan})
        return state

    def _act(self, state: AgentState) -> AgentState:
        if state.iterations >= state.max_iters:
            state.completed = True
            return state

        context_docs = self.vector.query(state.goal, k=2)
        tool_prompt = [
            {"role": "system", "content": "Use the tools to progress. Tools: sandbox, file_read, retrieval."},
            {"role": "user", "content": f"Goal: {state.goal}. Context: {context_docs}. Plan: {state.plan}"},
        ]
        action_text = self.model.chat(tool_prompt)
        result = self._dispatch_tool(action_text)
        state.last_result = result
        state.history.append({"role": "assistant", "content": action_text})
        state.iterations += 1
        self.audit.log("act", {"action": action_text, "result": result.output, "ok": result.ok})
        return state

    def _reflect(self, state: AgentState) -> AgentState:
        reflection_prompt = [
            {
                "role": "system",
                "content": "Reflect on the last result. Mark success if goal reached. Keep responses short.",
            },
            {"role": "assistant", "content": state.history[-1]["content"] if state.history else ""},
            {"role": "user", "content": f"Result: {state.last_result.output if state.last_result else ''}"},
        ]
        reflection = self.model.chat(reflection_prompt)
        state.history.append({"role": "assistant", "content": reflection})
        if "success" in reflection.lower() or "done" in reflection.lower():
            state.completed = True
        return state

    def _dispatch_tool(self, action: str) -> ToolResult:
        action_lower = action.lower()
        if "sandbox" in action_lower:
            cmd = action.split(":", 1)[-1].strip()
            return self.sandbox.run(cmd)
        if "read" in action_lower:
            target = action.split(":", 1)[-1].strip()
            return self.files.read(target)
        if "retrieve" in action_lower or "vector" in action_lower:
            query = action.split(":", 1)[-1].strip()
            docs = self.vector.query(query)
            return ToolResult(output=str(docs), metadata={"hits": len(docs)})
        return ToolResult(output=f"Unknown action: {action}", ok=False)
