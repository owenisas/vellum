import { Component, ErrorInfo, ReactNode } from "react";

interface State {
  err: Error | null;
  errorId: string | null;
}

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { err: null, errorId: null };

  static getDerivedStateFromError(error: Error): State {
    const id = Math.random().toString(16).slice(2, 10);
    return { err: error, errorId: id };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[veritext]", this.state.errorId, error, info.componentStack);
  }

  render() {
    if (this.state.err) {
      return (
        <div className="card">
          <h3>Something went wrong</h3>
          <p className="mono">Error ID: {this.state.errorId}</p>
          <pre>{this.state.err.message}</pre>
          <button onClick={() => location.reload()}>Reload</button>
        </div>
      );
    }
    return this.props.children;
  }
}
