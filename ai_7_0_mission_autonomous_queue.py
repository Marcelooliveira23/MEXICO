#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 7.0 - Mission Autonomous Queue

Módulo de fila autônoma para coordenação de tarefas de manutenção.
Implementa priorização, dependências, detecção de deadlock, balanceamento,
escalation e analytics operacionais.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import uuid


class TaskType(str, Enum):
    MAINTENANCE = "maintenance"
    INSPECTION = "inspection"
    REPAIR = "repair"
    REMOVAL = "removal"


class TaskPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    DEFERRED = "DEFERRED"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff_minutes: int = 30


@dataclass
class Task:
    title: str
    description: str
    aircraft_id: str
    ata_chapter: str
    priority: TaskPriority = TaskPriority.MEDIUM
    task_type: TaskType = TaskType.MAINTENANCE
    estimated_hours: float = 1.0
    required_parts: Dict[str, int] = field(default_factory=dict)
    required_tools: List[str] = field(default_factory=list)
    assigned_to: Optional[str] = None
    dependencies: Set[str] = field(default_factory=set)
    blocked_by: Set[str] = field(default_factory=set)
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    sla_due_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "aircraft_id": self.aircraft_id,
            "ata_chapter": self.ata_chapter,
            "priority": self.priority.value,
            "task_type": self.task_type.value,
            "estimated_hours": self.estimated_hours,
            "required_parts": dict(self.required_parts),
            "required_tools": list(self.required_tools),
            "assigned_to": self.assigned_to,
            "dependencies": sorted(list(self.dependencies)),
            "blocked_by": sorted(list(self.blocked_by)),
            "status": self.status.value,
            "sla_due_at": self.sla_due_at.isoformat() if self.sla_due_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count,
            "metadata": dict(self.metadata),
        }


class AutonomousTaskQueue:
    """
    Fila autônoma com foco em operações de manutenção aeronáutica.

    Melhorias incluídas:
    - Priorização dinâmica
    - Dependências e bloqueios
    - Detecção/resolução de deadlock
    - Auto-assign por skill/load
    - Escalação por SLA
    - Retry com backoff
    - Analytics operacionais
    """

    PRIORITY_WEIGHT = {
        TaskPriority.CRITICAL: 100,
        TaskPriority.HIGH: 80,
        TaskPriority.MEDIUM: 50,
        TaskPriority.LOW: 20,
        TaskPriority.DEFERRED: 5,
    }

    def __init__(self) -> None:
        self.tasks: Dict[str, Task] = {}
        self.queue: List[str] = []
        self.assignment: Dict[str, Set[str]] = {}
        self.technician_skills: Dict[str, List[str]] = {}

    # ============================
    # Priorização (5)
    # ============================
    def add_task(self, task: Task) -> str:
        if task.sla_due_at is None:
            task.sla_due_at = self._default_sla(task.priority)
        task.status = TaskStatus.QUEUED
        task.updated_at = datetime.utcnow()
        self.tasks[task.task_id] = task
        self._enqueue_task(task.task_id)
        self._update_queue_order()
        return task.task_id

    def _enqueue_task(self, task_id: str) -> None:
        if task_id not in self.queue:
            self.queue.append(task_id)

    def reorder_queue(self) -> List[str]:
        self._update_queue_order()
        return list(self.queue)

    def _update_queue_order(self) -> None:
        def score(task: Task) -> float:
            base = float(self.PRIORITY_WEIGHT.get(task.priority, 0))
            urgency = 0.0
            if task.sla_due_at:
                minutes_left = (task.sla_due_at - datetime.utcnow()).total_seconds() / 60.0
                if minutes_left <= 0:
                    urgency = 200.0
                elif minutes_left <= 60:
                    urgency = 120.0
                elif minutes_left <= 240:
                    urgency = 70.0
                else:
                    urgency = max(0.0, 30.0 - (minutes_left / 120.0))
            dep_penalty = 30.0 if task.dependencies else 0.0
            return base + urgency - dep_penalty

        existing = [tid for tid in self.queue if tid in self.tasks]
        existing.sort(key=lambda tid: score(self.tasks[tid]), reverse=True)
        self.queue = existing

    def resolve_dependencies(self, task_id: str) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False
        unresolved = [dep for dep in task.dependencies if self.tasks.get(dep, Task("x", "x", "x", "x")).status != TaskStatus.COMPLETED]
        task.blocked_by = set(unresolved)
        if unresolved:
            task.status = TaskStatus.BLOCKED
            task.updated_at = datetime.utcnow()
            return False
        if task.status == TaskStatus.BLOCKED:
            task.status = TaskStatus.QUEUED
            task.updated_at = datetime.utcnow()
            self._enqueue_task(task_id)
            self._update_queue_order()
        return True

    # ============================
    # Deadlock handling (5)
    # ============================
    def detect_deadlocks(self) -> List[List[str]]:
        graph = {tid: set(self.tasks[tid].dependencies) for tid in self.tasks}
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        stack: Set[str] = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            stack.add(node)
            path.append(node)
            for nxt in graph.get(node, set()):
                if nxt not in graph:
                    continue
                if nxt not in visited:
                    dfs(nxt, path)
                elif nxt in stack:
                    idx = path.index(nxt) if nxt in path else 0
                    cycles.append(path[idx:] + [nxt])
            stack.discard(node)
            path.pop()

        for node in graph:
            if node not in visited:
                dfs(node, [])
        return cycles

    def _has_cycle(self) -> bool:
        return len(self.detect_deadlocks()) > 0

    def _resolve_deadlock(self, cycle: List[str]) -> Optional[str]:
        if not cycle:
            return None
        candidate = None
        best = 10**9
        for tid in cycle:
            task = self.tasks.get(tid)
            if not task:
                continue
            weight = self.PRIORITY_WEIGHT.get(task.priority, 0)
            if weight < best:
                best = weight
                candidate = tid
        if candidate and candidate in self.tasks:
            self.tasks[candidate].dependencies.clear()
            self.tasks[candidate].blocked_by.clear()
            self.tasks[candidate].status = TaskStatus.QUEUED
            self._enqueue_task(candidate)
            self._update_queue_order()
        return candidate

    def check_blocking_relationships(self) -> Dict[str, List[str]]:
        return {tid: sorted(list(task.blocked_by)) for tid, task in self.tasks.items() if task.blocked_by}

    def unblock_tasks(self, completed_task_id: str) -> int:
        changed = 0
        for tid, task in self.tasks.items():
            if completed_task_id in task.blocked_by:
                task.blocked_by.discard(completed_task_id)
                if not task.blocked_by and task.status == TaskStatus.BLOCKED:
                    task.status = TaskStatus.QUEUED
                    self._enqueue_task(tid)
                    changed += 1
        if changed:
            self._update_queue_order()
        return changed

    # ============================
    # Load balancing (5)
    # ============================
    def assign_task_optimal(self, task_id: str) -> Optional[str]:
        task = self.tasks.get(task_id)
        if not task:
            return None
        if not self.resolve_dependencies(task_id):
            return None

        best_tech = None
        best_score = -10**9
        for tech_id, skills in self.technician_skills.items():
            skill_score = self._skill_fit(task, skills)
            load_penalty = len(self.assignment.get(tech_id, set())) * 5
            score = skill_score - load_penalty
            if score > best_score:
                best_score = score
                best_tech = tech_id

        if not best_tech:
            return None

        self._assign_task(task_id, best_tech)
        return best_tech

    def _assign_task(self, task_id: str, technician_id: str) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False
        task.assigned_to = technician_id
        task.status = TaskStatus.ASSIGNED
        task.updated_at = datetime.utcnow()
        self.assignment.setdefault(technician_id, set()).add(task_id)
        if task_id in self.queue:
            self.queue.remove(task_id)
        return True

    def suggest_reassignment(self) -> List[Tuple[str, str, str]]:
        suggestions: List[Tuple[str, str, str]] = []
        loads = {tech: len(tasks) for tech, tasks in self.assignment.items()}
        if not loads:
            return suggestions
        max_load = max(loads.values())
        min_load = min(loads.values())
        if max_load - min_load < 2:
            return suggestions

        heavy = max(loads, key=loads.get)
        light = min(loads, key=loads.get)
        for tid in list(self.assignment.get(heavy, set())):
            task = self.tasks.get(tid)
            if not task:
                continue
            if self._skill_fit(task, self.technician_skills.get(light, [])) > 0:
                suggestions.append((tid, heavy, light))
                break
        return suggestions

    def predict_bottlenecks(self) -> Dict[str, object]:
        blocked = [t.task_id for t in self.tasks.values() if t.status == TaskStatus.BLOCKED]
        overdue = [t.task_id for t in self.tasks.values() if t.sla_due_at and t.sla_due_at < datetime.utcnow()]
        queued_long = [
            t.task_id
            for t in self.tasks.values()
            if t.status in {TaskStatus.QUEUED, TaskStatus.PENDING} and (datetime.utcnow() - t.created_at).total_seconds() > 6 * 3600
        ]
        return {
            "blocked_count": len(blocked),
            "overdue_count": len(overdue),
            "queued_long_count": len(queued_long),
            "blocked_tasks": blocked[:15],
            "overdue_tasks": overdue[:15],
            "queued_long_tasks": queued_long[:15],
        }

    def balance_workload(self) -> int:
        moved = 0
        for tid, src, dst in self.suggest_reassignment():
            self.assignment.get(src, set()).discard(tid)
            self.assignment.setdefault(dst, set()).add(tid)
            task = self.tasks.get(tid)
            if task:
                task.assigned_to = dst
                task.updated_at = datetime.utcnow()
                moved += 1
        return moved

    # ============================
    # Escalation (5)
    # ============================
    def check_sla_compliance(self) -> List[str]:
        breached: List[str] = []
        now = datetime.utcnow()
        for task in self.tasks.values():
            if task.status in {TaskStatus.COMPLETED, TaskStatus.CANCELLED}:
                continue
            if task.sla_due_at and task.sla_due_at < now:
                breached.append(task.task_id)
                self._escalate_task(task.task_id, "SLA breach")
        return breached

    def _escalate_task(self, task_id: str, reason: str) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False
        task.status = TaskStatus.ESCALATED
        task.metadata["escalation_reason"] = reason
        task.metadata["escalated_at"] = datetime.utcnow().isoformat()
        task.updated_at = datetime.utcnow()
        return True

    def auto_request_parts(self, task_id: str) -> Dict[str, int]:
        task = self.tasks.get(task_id)
        if not task:
            return {}
        return {part: qty for part, qty in task.required_parts.items() if qty > 0}

    def auto_retry_failed(self) -> int:
        retried = 0
        now = datetime.utcnow()
        for task in self.tasks.values():
            if task.status != TaskStatus.FAILED:
                continue
            if task.retry_count >= task.retry_policy.max_attempts:
                continue
            wait_until = task.updated_at + timedelta(minutes=task.retry_policy.backoff_minutes)
            if now >= wait_until:
                task.retry_count += 1
                task.status = TaskStatus.QUEUED
                task.updated_at = now
                self._enqueue_task(task.task_id)
                retried += 1
        if retried:
            self._update_queue_order()
        return retried

    def split_large_task(self, task_id: str) -> List[str]:
        task = self.tasks.get(task_id)
        if not task or task.estimated_hours <= 8:
            return []

        chunks = max(2, int(round(task.estimated_hours / 4.0)))
        new_ids: List[str] = []
        for idx in range(chunks):
            sub = Task(
                title=f"{task.title} - Part {idx+1}/{chunks}",
                description=f"Subtask of {task.task_id}",
                aircraft_id=task.aircraft_id,
                ata_chapter=task.ata_chapter,
                priority=task.priority,
                task_type=task.task_type,
                estimated_hours=round(task.estimated_hours / chunks, 2),
                required_parts=dict(task.required_parts),
                required_tools=list(task.required_tools),
            )
            sub.dependencies = set(task.dependencies)
            sub.metadata["parent_task"] = task.task_id
            new_ids.append(self.add_task(sub))

        task.status = TaskStatus.CANCELLED
        task.metadata["split_into"] = ",".join(new_ids)
        task.updated_at = datetime.utcnow()
        return new_ids

    # ============================
    # Analytics (3)
    # ============================
    def get_queue_status(self) -> Dict[str, object]:
        status_count: Dict[str, int] = {}
        for task in self.tasks.values():
            status_count[task.status.value] = status_count.get(task.status.value, 0) + 1

        return {
            "total_tasks": len(self.tasks),
            "queued": len(self.queue),
            "status_breakdown": status_count,
            "technicians": len(self.technician_skills),
            "assignments": {k: len(v) for k, v in self.assignment.items()},
        }

    def get_queue_analytics(self) -> Dict[str, object]:
        now = datetime.utcnow()
        completed = [t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED and t.completed_at]
        lead_times = [(t.completed_at - t.created_at).total_seconds() / 3600.0 for t in completed if t.completed_at]

        overdue = [
            t.task_id for t in self.tasks.values()
            if t.sla_due_at and t.sla_due_at < now and t.status not in {TaskStatus.COMPLETED, TaskStatus.CANCELLED}
        ]

        return {
            "throughput_completed": len(completed),
            "avg_lead_time_hours": round(sum(lead_times) / len(lead_times), 2) if lead_times else None,
            "overdue_tasks": overdue,
            "bottlenecks": self.predict_bottlenecks(),
            "deadlocks_detected": self.detect_deadlocks(),
        }

    def recommend_optimizations(self) -> List[str]:
        recs: List[str] = []
        bottlenecks = self.predict_bottlenecks()
        if bottlenecks["blocked_count"] > 0:
            recs.append("Resolver dependências bloqueadas e revisar cadeia de tarefas críticas.")
        if bottlenecks["overdue_count"] > 0:
            recs.append("Aumentar capacidade para tarefas em breach de SLA e priorizar CRITICAL/HIGH.")
        if bottlenecks["queued_long_count"] > 0:
            recs.append("Executar balance_workload e avaliar auto-assignment por especialidade ATA.")
        if not recs:
            recs.append("Fila saudável. Manter monitoramento de SLA e rebalanceamento periódico.")
        return recs

    # ============================
    # Utilitários
    # ============================
    def complete_task(self, task_id: str) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()
        if task.assigned_to and task.assigned_to in self.assignment:
            self.assignment[task.assigned_to].discard(task_id)
        self.unblock_tasks(task_id)
        return True

    def fail_task(self, task_id: str, reason: str) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False
        task.status = TaskStatus.FAILED
        task.metadata["failure_reason"] = reason
        task.updated_at = datetime.utcnow()
        return True

    def _skill_fit(self, task: Task, skills: List[str]) -> int:
        ata_skill = task.ata_chapter.upper().replace(" ", "")
        normalized = [s.upper().replace(" ", "") for s in skills]
        if ata_skill in normalized:
            return 100
        if "GENERAL" in normalized:
            return 40
        return 0

    def _default_sla(self, priority: TaskPriority) -> datetime:
        now = datetime.utcnow()
        if priority == TaskPriority.CRITICAL:
            return now + timedelta(hours=6)
        if priority == TaskPriority.HIGH:
            return now + timedelta(hours=24)
        if priority == TaskPriority.MEDIUM:
            return now + timedelta(hours=72)
        if priority == TaskPriority.LOW:
            return now + timedelta(hours=168)
        return now + timedelta(days=14)


__all__ = [
    "Task",
    "TaskType",
    "TaskPriority",
    "TaskStatus",
    "RetryPolicy",
    "AutonomousTaskQueue",
]
