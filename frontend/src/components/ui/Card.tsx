import type { ReactNode } from "react";

export function Card({
  title,
  actions,
  children,
}: {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="card">
      {(title || actions) && (
        <div className="flex-between" style={{ marginBottom: "12px" }}>
          {title && <h3 style={{ margin: 0 }}>{title}</h3>}
          {actions && <div className="flex gap-sm">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}
