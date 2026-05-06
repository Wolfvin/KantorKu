"""
Losion Training — Modul pelatihan untuk framework Losion.

Mengimplementasikan training 4-fase dengan dukungan:
- LosionTrainer: Trainer utama dengan 4 fase curriculum
- GRPOTrainer: Group Relative Policy Optimization (dari DeepSeek-R1)
- DAPOTrainer: Decoupled Clip & Dynamic Sampling Policy Optimization (Yu et al., 2025)
- AdvancedGRPOTrainer: GRPO + Self-Play + Value Head (DeepMind)
- CurriculumScheduler: Penjadwal transisi antar fase
- Advanced RLHF: Self-Play Preference, Value Head, Self-Consistency
- Advanced Backprop: Chinchilla Scaling, Soft Capping, Scheduled Sampling
- Advanced Memory/Data: Progressive KV, Attention Sinks, Modality-Aware Loss
- ETR Entropy Trend Reward: Reduces thinking tokens up to 40%
- LLM-JEPA: Joint-Embedding Predictive Architecture for LLMs

Penggunaan:
    >>> from kantorku.losion.training import LosionTrainer, GRPOTrainer, CurriculumScheduler
    >>> from kantorku.losion.training import AdvancedGRPOTrainer
    >>> from kantorku.losion.training import DAPOTrainer, DAPOConfig
    >>> from kantorku.losion.training import ETRTrainer, ETRRewardFunction, ETRConfig
    >>> from kantorku.losion.config import LosionConfig
    >>> config = LosionConfig()
    >>> trainer = LosionTrainer(config)
    >>> trainer.train()
"""

from __future__ import annotations

from kantorku.losion.training.trainer import LosionTrainer
from kantorku.losion.training.grpo import GRPOTrainer
from kantorku.losion.training.curriculum import CurriculumScheduler
from kantorku.losion.training.advanced_rlhf import (
    AdvancedGRPOTrainer,
    AdvancedGRPOConfig,
    JalurValueHead,
    SelfPlayPreferenceGenerator,
    SelfConsistencyVerifier,
    DirichletNoiseInjector,
)
from kantorku.losion.training.advanced_backprop import (
    ChinchillaScaler,
    ChinchillaScalingResult,
    PerJalurLRScheduler,
    LogitSoftCapper,
    ScheduledSampler,
    ConfidenceHeads,
    ParallelAttentionFFN,
    GradientOverlapScheduler,
    MemoryEfficientBackprop,
)
from kantorku.losion.training.advanced_memory_data import (
    ProgressiveKVCompressor,
    AttentionSinkManager,
    DynamicExpertBufferAllocator,
    ModalityAwareLossWeighter,
    ChinchillaDataSizer,
    SampleFilterPipeline,
    TemplateConditionalRouter,
)
from kantorku.losion.training.gen_distillation import (
    GenerationDistillationConfig,
    GenerationDistiller,
)
from kantorku.losion.training.compute_aligned import (
    ComputeAlignedConfig,
    ComputeAlignedTrainer,
    ComputeTracker,
)
from kantorku.losion.training.etr_reward import (
    EntropyTrendTracker,
    ETRConfig,
    ETRRewardFunction,
    ETRTrainer,
)
from kantorku.losion.training.llm_jepa import (
    JEPAConfig,
    LatentPredictor,
    TargetEncoder,
    VICRegLoss,
    LLMJEPA,
)
from kantorku.losion.training.dapo import (
    DAPOConfig,
    DAPOResult,
    DAPORewardFunction,
    DAPOTrainer,
)
from kantorku.losion.training.losion_recipe import (
    WSDLRScheduler,
    WSDConfig,
    LosionTrainingRecipe,
    PhaseRecipe,
    LosionTrainingState,
    GradientStats,
    ActivationStats,
    ScalingRecipe,
    ModelScaleConfig,
)

__all__ = [
    "LosionTrainer",
    "GRPOTrainer",
    "CurriculumScheduler",
    # Advanced RLHF
    "AdvancedGRPOTrainer",
    "AdvancedGRPOConfig",
    "JalurValueHead",
    "SelfPlayPreferenceGenerator",
    "SelfConsistencyVerifier",
    "DirichletNoiseInjector",
    # Advanced Backprop
    "ChinchillaScaler",
    "ChinchillaScalingResult",
    "PerJalurLRScheduler",
    "LogitSoftCapper",
    "ScheduledSampler",
    "ConfidenceHeads",
    "ParallelAttentionFFN",
    "GradientOverlapScheduler",
    "MemoryEfficientBackprop",
    # Advanced Memory & Data
    "ProgressiveKVCompressor",
    "AttentionSinkManager",
    "DynamicExpertBufferAllocator",
    "ModalityAwareLossWeighter",
    "ChinchillaDataSizer",
    "SampleFilterPipeline",
    "TemplateConditionalRouter",
    # Generation-Focused Distillation
    "GenerationDistillationConfig",
    "GenerationDistiller",
    # Compute-Aligned Training (TACO)
    "ComputeAlignedConfig",
    "ComputeAlignedTrainer",
    "ComputeTracker",
    # ETR Entropy Trend Reward
    "EntropyTrendTracker",
    "ETRConfig",
    "ETRRewardFunction",
    "ETRTrainer",
    # LLM-JEPA
    "JEPAConfig",
    "LatentPredictor",
    "TargetEncoder",
    "VICRegLoss",
    "LLMJEPA",
    # DAPO
    "DAPOConfig",
    "DAPOResult",
    "DAPORewardFunction",
    "DAPOTrainer",
    # Losion Training Recipe
    "WSDLRScheduler",
    "WSDConfig",
    "LosionTrainingRecipe",
    "PhaseRecipe",
    "LosionTrainingState",
    "GradientStats",
    "ActivationStats",
    "ScalingRecipe",
    "ModelScaleConfig",
]
