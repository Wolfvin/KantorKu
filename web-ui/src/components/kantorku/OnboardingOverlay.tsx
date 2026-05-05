'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { MessageSquare, Briefcase, BarChart3, ChevronRight, X } from 'lucide-react';

const ONBOARDING_KEY = 'kantorku_onboarding_dismissed';

const STEPS = [
  {
    icon: MessageSquare,
    title: 'Selamat Datang di KantorKu!',
    description: 'Chat dengan Manager di Lobby untuk memulai proyek. Manager akan memahami kebutuhan Anda dan menyusun kontrak kerja.',
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/10',
  },
  {
    icon: Briefcase,
    title: 'Pantau Tim di Workspace',
    description: 'Lihat workers yang bekerja, briefing room, diskusi channel, dan DAG visualisasi untuk memantau progress.',
    color: 'text-teal-400',
    bg: 'bg-teal-500/10',
  },
  {
    icon: BarChart3,
    title: 'Dashboard & Observability',
    description: 'Track biaya, latency, health status, dan observability metrics. Semua yang Anda butuhkan untuk mengawasi kantor digital.',
    color: 'text-green-400',
    bg: 'bg-green-500/10',
  },
];

export function OnboardingOverlay() {
  const [visible, setVisible] = useState(() => {
    if (typeof window === 'undefined') return false;
    return !localStorage.getItem(ONBOARDING_KEY);
  });
  const [step, setStep] = useState(0);
  const [dontShowAgain, setDontShowAgain] = useState(false);

  const handleDismiss = useCallback(() => {
    if (dontShowAgain) {
      localStorage.setItem(ONBOARDING_KEY, 'true');
    }
    setVisible(false);
  }, [dontShowAgain]);

  const handleNext = useCallback(() => {
    if (step < STEPS.length - 1) {
      setStep(step + 1);
    } else {
      handleDismiss();
    }
  }, [step, handleDismiss]);

  if (!visible) return null;

  const currentStep = STEPS[step];
  const Icon = currentStep.icon;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm" role="dialog" aria-label="Welcome to KantorKu">
      <div className="relative max-w-md w-full mx-4 p-6 rounded-xl bg-slate-900 border border-cyan-500/20 shadow-[0_0_40px_rgba(6,182,212,0.1)]">
        {/* Skip button */}
        <button
          onClick={handleDismiss}
          className="absolute top-3 right-3 text-slate-500 hover:text-slate-300 transition-colors"
          aria-label="Skip onboarding"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-5">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                i === step ? 'w-8 bg-cyan-400' : i < step ? 'w-4 bg-cyan-400/40' : 'w-4 bg-slate-700'
              }`}
            />
          ))}
        </div>

        {/* Icon */}
        <div className={`w-14 h-14 rounded-xl ${currentStep.bg} flex items-center justify-center mx-auto mb-4`}>
          <Icon className={`h-7 w-7 ${currentStep.color}`} />
        </div>

        {/* Content */}
        <h3 className="text-lg font-bold text-white text-center mb-2">
          {currentStep.title}
        </h3>
        <p className="text-[12px] text-slate-400 text-center leading-relaxed mb-5">
          {currentStep.description}
        </p>

        {/* Actions */}
        <div className="flex items-center justify-between">
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={dontShowAgain}
              onChange={(e) => setDontShowAgain(e.target.checked)}
              className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 text-cyan-400 focus:ring-cyan-400"
            />
            <span className="text-[10px] text-slate-500">Jangan tampilkan lagi</span>
          </label>

          <Button
            onClick={handleNext}
            size="sm"
            className="bg-cyan-600 hover:bg-cyan-500 text-white text-xs px-4"
            aria-label={step < STEPS.length - 1 ? 'Next step' : 'Get started'}
          >
            {step < STEPS.length - 1 ? (
              <>
                Lanjut
                <ChevronRight className="h-3.5 w-3.5 ml-1" />
              </>
            ) : (
              'Mulai! 🚀'
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
