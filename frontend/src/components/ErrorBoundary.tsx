import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // eslint-disable-next-line no-console
    console.error("ErrorBoundary caught", error, info);
  }

  reset = () => this.setState({ error: null });

  render() {
    if (this.state.error) {
      if (this.props.fallback)
        return this.props.fallback(this.state.error, this.reset);
      return (
        <div className="card">
          <h2>Something went wrong</h2>
          <p className="muted">
            The page hit an error. You can refresh or go back to the dashboard.
          </p>
          <pre className="mono" style={{ background: "var(--color-panel-light)", padding: "8px", borderRadius: "6px" }}>
            {this.state.error.message}
          </pre>
          <button className="btn" onClick={this.reset}>
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
