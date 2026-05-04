'use client';

import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import type { Locale } from './config';
import { defaultLocale, locales } from './config';
import en from './en.json';
import id from './id.json';

// ── Message map type ────────────────────────────────────────────────
type Messages = typeof en;

const messages: Record<Locale, Messages> = { en, id };

// ── Deep path type for dot-notation access ──────────────────────────
// Simplified recursive type that generates all possible dot-notation paths
// through the translation object structure (up to 3 levels deep which covers
// our JSON structure like "common.loading", "lobby.newSession", etc.)
type PathImpl<T, Prefix extends string = ''> = T extends string
  ? Prefix
  : T extends object
    ? {
        [K in keyof T & string]: PathImpl<T[K], Prefix extends '' ? K : `${Prefix}.${K}`>;
      }[keyof T & string]
    : never;

export type TranslationKey = PathImpl<Messages>;

// ── i18n Context ────────────────────────────────────────────────────
interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
  locales: readonly Locale[];
}

const I18nContext = createContext<I18nContextValue | null>(null);

// ── Translation function (pure, no hooks) ───────────────────────────
function resolveValue(obj: unknown, keys: string[]): unknown {
  let current = obj;
  for (const k of keys) {
    if (current && typeof current === 'object') {
      current = (current as Record<string, unknown>)[k];
    } else {
      return undefined;
    }
  }
  return current;
}

function interpolate(value: string, params?: Record<string, string | number>): string {
  if (!params) return value;
  return value.replace(/\{(\w+)\}/g, (_, p) =>
    String(params[p] ?? `{${p}}`)
  );
}

function translate(
  locale: Locale,
  key: string,
  params?: Record<string, string | number>
): string {
  const keys = key.split('.');

  // Try current locale first
  const value = resolveValue(messages[locale], keys);
  if (typeof value === 'string') {
    return interpolate(value, params);
  }

  // Fallback to English
  const fallback = resolveValue(messages[defaultLocale], keys);
  if (typeof fallback === 'string') {
    return interpolate(fallback, params);
  }

  // Key not found, return the key itself
  return key;
}

// ── Provider Component ──────────────────────────────────────────────
const LOCALE_STORAGE_KEY = 'kantorku_locale';

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    if (typeof window === 'undefined') return defaultLocale;
    const stored = localStorage.getItem(LOCALE_STORAGE_KEY);
    if (stored && locales.includes(stored as Locale)) {
      return stored as Locale;
    }
    return defaultLocale;
  });

  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale);
    if (typeof window !== 'undefined') {
      localStorage.setItem(LOCALE_STORAGE_KEY, newLocale);
    }
  }, []);

  // Sync across tabs
  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === LOCALE_STORAGE_KEY && e.newValue && locales.includes(e.newValue as Locale)) {
        setLocaleState(e.newValue as Locale);
      }
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);

  const t = useCallback(
    (key: string, params?: Record<string, string | number>): string => {
      return translate(locale, key, params);
    },
    [locale]
  );

  const contextValue: I18nContextValue = {
    locale,
    setLocale,
    t,
    locales,
  };

  return (
    <I18nContext.Provider value={contextValue}>
      {children}
    </I18nContext.Provider>
  );
}

// ── useTranslations hook ────────────────────────────────────────────
export function useTranslations() {
  const context = useContext(I18nContext);
  if (!context) {
    // Fallback for usage outside of provider (e.g. during SSR or testing)
    const t = (key: string, params?: Record<string, string | number>): string => {
      return translate(defaultLocale, key, params);
    };
    return {
      t,
      locale: defaultLocale,
      setLocale: () => {},
      locales,
    } as I18nContextValue;
  }
  return context;
}

// ── Standalone translate function (for use outside React) ───────────
export function getTranslation(
  key: string,
  locale: Locale = defaultLocale,
  params?: Record<string, string | number>
): string {
  return translate(locale, key, params);
}

// Re-export config
export { locales, defaultLocale } from './config';
export type { Locale } from './config';
