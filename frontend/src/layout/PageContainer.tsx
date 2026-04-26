import type { ReactNode } from "react";

export function PageContainer({
  title,
  subtitle,
  children,
}: {
  title?: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <main className="page-container">
      {title && <h1>{title}</h1>}
      {subtitle && <p className="muted">{subtitle}</p>}
      {children}
    </main>
  );
}
