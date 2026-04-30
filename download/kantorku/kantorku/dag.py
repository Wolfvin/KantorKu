"""
DAG — Dependency resolution for parallel task execution.

Resolves task dependencies into parallel execution groups
using topological sort. Ensures tasks with dependencies
are executed in the correct order while maximizing parallelism.

Usage:
    from kantorku.dag import DAGResolver, TaskNode

    nodes = [
        TaskNode(id="a", depends_on=[]),
        TaskNode(id="b", depends_on=["a"]),
        TaskNode(id="c", depends_on=["a"]),
        TaskNode(id="d", depends_on=["b", "c"]),
    ]

    resolver = DAGResolver(nodes)
    groups = resolver.resolve()  # [["a"], ["b", "c"], ["d"]]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskNode:
    """
    A task node in a DAG.

    Attributes:
        id: Unique task identifier
        depends_on: List of task IDs this task depends on
        data: Optional arbitrary data attached to the node
    """
    id: str
    depends_on: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)


class DAGCycleError(Exception):
    """Raised when a cycle is detected in the DAG."""
    pass


class DAGResolver:
    """
    Resolve a DAG of task dependencies into parallel execution groups.

    Uses Kahn's algorithm for topological sorting, producing groups
    of tasks that can be executed in parallel. Each group contains
    tasks whose dependencies are all satisfied by previous groups.

    Usage:
        nodes = [
            TaskNode(id="setup", depends_on=[]),
            TaskNode(id="frontend", depends_on=["setup"]),
            TaskNode(id="backend", depends_on=["setup"]),
            TaskNode(id="wiring", depends_on=["frontend", "backend"]),
            TaskNode(id="verify", depends_on=["wiring"]),
        ]

        resolver = DAGResolver(nodes)
        groups = resolver.resolve()
        # Result: [["setup"], ["frontend", "backend"], ["wiring"], ["verify"]]

        # Execute groups sequentially, tasks within each group in parallel
        for group in groups:
            results = await asyncio.gather(*[execute(task) for task in group])
    """

    def __init__(self, nodes: list[TaskNode]) -> None:
        self.nodes = nodes
        self._adjacency: dict[str, list[str]] = {}  # id -> list of dependents
        self._in_degree: dict[str, int] = {}  # id -> number of unresolved deps
        self._node_map: dict[str, TaskNode] = {}

        # Build graph
        for node in nodes:
            self._node_map[node.id] = node
            self._in_degree[node.id] = len(node.depends_on)
            if node.id not in self._adjacency:
                self._adjacency[node.id] = []

        for node in nodes:
            for dep in node.depends_on:
                if dep not in self._adjacency:
                    self._adjacency[dep] = []
                self._adjacency[dep].append(node.id)

    def resolve(self) -> list[list[TaskNode]]:
        """
        Resolve the DAG into parallel execution groups.

        Returns:
            List of groups, where each group is a list of TaskNodes
            that can be executed in parallel.

        Raises:
            DAGCycleError: If a dependency cycle is detected
        """
        in_degree = dict(self._in_degree)
        queue: list[str] = [nid for nid, deg in in_degree.items() if deg == 0]
        groups: list[list[TaskNode]] = []
        processed = 0

        while queue:
            # All nodes in current queue can run in parallel
            group = [self._node_map[nid] for nid in queue if nid in self._node_map]
            if group:
                groups.append(group)

            next_queue: list[str] = []
            for nid in queue:
                processed += 1
                for dependent in self._adjacency.get(nid, []):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_queue.append(dependent)

            queue = next_queue

        # Check for cycles
        if processed != len(self.nodes):
            remaining = [nid for nid, deg in in_degree.items() if deg > 0]
            raise DAGCycleError(
                f"Dependency cycle detected involving nodes: {remaining}"
            )

        return groups

    def get_critical_path(self) -> list[str]:
        """
        Find the critical path (longest dependency chain) in the DAG.

        Returns:
            List of task IDs forming the critical path
        """
        # Compute longest path to each node
        dist: dict[str, int] = {}
        parent: dict[str, str | None] = {}

        # Process in topological order
        groups = self.resolve()
        for group in groups:
            for node in group:
                if not node.depends_on:
                    dist[node.id] = 1
                    parent[node.id] = None
                else:
                    max_dep_dist = 0
                    max_dep_id = node.depends_on[0]
                    for dep_id in node.depends_on:
                        if dist.get(dep_id, 0) > max_dep_dist:
                            max_dep_dist = dist[dep_id]
                            max_dep_id = dep_id
                    dist[node.id] = max_dep_dist + 1
                    parent[node.id] = max_dep_id

        if not dist:
            return []

        # Find node with maximum distance
        end_node = max(dist, key=lambda k: dist[k])

        # Trace back
        path: list[str] = []
        current: str | None = end_node
        while current is not None:
            path.append(current)
            current = parent.get(current)

        path.reverse()
        return path

    def get_dependents(self, task_id: str) -> list[str]:
        """Get all tasks that depend on the given task (directly or transitively)."""
        result: list[str] = []
        visited: set[str] = set()

        def _dfs(nid: str) -> None:
            for dep in self._adjacency.get(nid, []):
                if dep not in visited:
                    visited.add(dep)
                    result.append(dep)
                    _dfs(dep)

        _dfs(task_id)
        return result

    def get_dependencies(self, task_id: str) -> list[str]:
        """Get all tasks that the given task depends on (directly or transitively)."""
        result: list[str] = []
        visited: set[str] = set()

        def _dfs(nid: str) -> None:
            node = self._node_map.get(nid)
            if not node:
                return
            for dep in node.depends_on:
                if dep not in visited:
                    visited.add(dep)
                    result.append(dep)
                    _dfs(dep)

        _dfs(task_id)
        return result
