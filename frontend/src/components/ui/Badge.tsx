import type { ReactNode } from "react";

type Tone = "neutral" | "success" | "warning" | "danger" | "info";

const map: Record<Tone, string> = {
  neutral: "badge",
  success: "badge badge-success",
  warning: "badge badge-warning",
  danger: "badge badge-danger",
  info: "badge badge-info",
};

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: Tone }) {
  return <span className={map[tone]}>{children}</span>;
}
