"""GPU Scheduler for FamilyGPU Orchestrator.

The scheduler is the core decision-making component. It accepts job
requests, selects the best available account, creates leases, and
manages the job lifecycle including failover.

Components:
  - request.py: Job request model and validation
  - selector.py: Account selection algorithm with scoring
  - leases.py: Lease lifecycle management
  - quota.py: Quota enforcement and checking
  - failover.py: Failover logic when jobs fail
  - scoring.py: Account scoring algorithm
  - autoloop.py: Background daemon for continuous auto-scheduling
"""

from kantorku.gpu.core.request import JobRequest, JobRequestResult, FailureReason
from kantorku.gpu.core.selector import AccountSelector
from kantorku.gpu.core.leases import LeaseManager
from kantorku.gpu.core.quota import QuotaEnforcer
from kantorku.gpu.core.failover import FailoverManager
from kantorku.gpu.core.autoloop import AutoLoop, AutoLoopConfig, AutoLoopStats

__all__ = [
    "JobRequest",
    "JobRequestResult",
    "FailureReason",
    "AccountSelector",
    "LeaseManager",
    "QuotaEnforcer",
    "FailoverManager",
    "AutoLoop",
    "AutoLoopConfig",
    "AutoLoopStats",
]
