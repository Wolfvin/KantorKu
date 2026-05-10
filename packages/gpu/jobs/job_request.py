"""
kantorku.gpu.jobs.job_request — re-export dari core.request untuk backward compat.
"""
from kantorku.gpu.core.request import JobRequest, JobRequestResult, FailureReason, GPU_PROFILES

__all__ = ["JobRequest", "JobRequestResult", "FailureReason", "GPU_PROFILES"]
