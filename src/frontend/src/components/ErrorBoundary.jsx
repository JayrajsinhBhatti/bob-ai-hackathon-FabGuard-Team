import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Cleanroom ErrorBoundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="glass-panel rounded-xl p-8 max-w-xl mx-auto my-12 text-center font-mono border-red-500/40 shadow-glass">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-500/20 text-red-400 mx-auto mb-4 border border-red-500/40">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <h2 className="text-base font-bold text-white uppercase tracking-tight mb-2">
            Metrology Telemetry Render Notice
          </h2>
          <p className="text-xs text-slate-300 mb-6 font-sans">
            A temporary component initialization occurred. Click below to recover cleanroom telemetry.
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            className="inline-flex items-center gap-2 rounded-lg bg-cyan px-4 py-2 text-xs font-mono font-bold text-canvas hover:bg-cyan-bright transition-colors shadow-cyan-glow"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Reload Console</span>
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
