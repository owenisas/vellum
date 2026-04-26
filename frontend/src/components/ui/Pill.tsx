import { type ReactNode } from "react";
import { cn } from "../../lib/cn";
import styles from "./Pill.module.css";

type Props = {
  children: ReactNode;
  tone?: "default" | "signal" | "alarm";
  active?: boolean;
  onClick?: () => void;
  className?: string;
};

export function Pill({ children, tone = "default", active, onClick, className }: Props) {
  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={cn(styles.pill, styles[tone], active && styles.active, styles.button, className)}
      >
        {children}
      </button>
    );
  }
  return (
    <span className={cn(styles.pill, styles[tone], active && styles.active, className)}>
      {children}
    </span>
  );
}
