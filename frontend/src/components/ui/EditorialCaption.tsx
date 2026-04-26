import { type ReactNode } from "react";
import { cn } from "../../lib/cn";
import styles from "./EditorialCaption.module.css";

type Props = {
  children: ReactNode;
  className?: string;
  size?: "xs" | "sm";
  rule?: boolean;
  number?: string;
};

export function EditorialCaption({ children, className, size = "sm", rule, number }: Props) {
  return (
    <span className={cn(styles.cap, styles[size], rule && styles.rule, className)}>
      {number && <span className={styles.num}>{number}</span>}
      <span>{children}</span>
    </span>
  );
}
