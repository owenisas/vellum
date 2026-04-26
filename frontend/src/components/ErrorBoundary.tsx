import { Component, type ErrorInfo, type ReactNode } from "react";

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
    // eslint-disable-next-line no-console
    console.error("[veritext]", this.state.errorId, error, info.componentStack);
  }

  render() {
    if (!this.state.err) return this.props.children;
    return (
      <div style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: "var(--s-7)",
        background: "var(--bg)",
        color: "var(--fg)",
      }}>
        <div style={{ maxWidth: "560px", textAlign: "left" }}>
          <span style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.6875rem",
            letterSpacing: "0.22em",
            textTransform: "uppercase",
            color: "var(--alarm)",
          }}>err-{this.state.errorId}</span>
          <h2 style={{
            fontFamily: "var(--font-display)",
            fontSize: "var(--t-49)",
            margin: "var(--s-3) 0 var(--s-4)",
            lineHeight: 0.95,
          }}>
            Something interrupted the rendering.
          </h2>
          <p style={{ color: "var(--fg-mute)", marginBottom: "var(--s-5)" }}>
            {this.state.err.message}
          </p>
          <button
            onClick={() => location.reload()}
            style={{
              padding: "0.85rem 1.45rem",
              border: 0,
              borderRadius: "999px",
              background: "var(--fg)",
              color: "var(--bg)",
              fontFamily: "var(--font-sans)",
              fontSize: "var(--t-14)",
              fontWeight: 500,
              letterSpacing: "0.04em",
              cursor: "pointer",
            }}
          >
            Reload the page
          </button>
        </div>
      </div>
    );
  }
}
