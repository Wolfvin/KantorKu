'use client';

import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { logger } from '@/lib/kantorku/logger';
import { Button } from '@/components/ui/button';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallbackTitle?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    logger.error('error-boundary', `${this.props.fallbackTitle || 'Zone'} crashed`, error, errorInfo);
    this.setState({ errorInfo });
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full p-6">
          <div className="max-w-sm w-full p-6 rounded-xl bg-slate-900/90 border border-red-500/30 backdrop-blur-sm text-center">
            <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 mx-auto mb-4">
              <AlertTriangle className="h-6 w-6 text-red-400" />
            </div>
            <h3 className="text-sm font-semibold text-red-300 mb-1">
              {this.props.fallbackTitle || 'Zone Error'}
            </h3>
            <p className="text-[11px] text-slate-400 mb-4 leading-relaxed">
              Something went wrong rendering this section. The error has been logged.
            </p>
            {this.state.error && (
              <pre className="text-[10px] text-red-300/70 bg-slate-950/60 p-2 rounded-md mb-4 max-h-24 overflow-y-auto custom-scrollbar text-left font-mono break-all">
                {this.state.error.message}
              </pre>
            )}
            <Button
              onClick={this.handleRetry}
              size="sm"
              className="bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500 text-white text-xs"
            >
              <RefreshCw className="h-3 w-3 mr-1.5" />
              Retry
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
