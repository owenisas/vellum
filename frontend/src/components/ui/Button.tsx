import { forwardRef, type ButtonHTMLAttributes, type AnchorHTMLAttributes, type ReactNode } from "react";
import { cn } from "../../lib/cn";
import styles from "./Button.module.css";

type Variant = "primary" | "ghost" | "outline" | "link";
type Size = "sm" | "md" | "lg";

type CommonProps = {
  variant?: Variant;
  size?: Size;
  children: ReactNode;
  className?: string;
};

type ButtonProps = CommonProps & ButtonHTMLAttributes<HTMLButtonElement>;
type LinkProps = CommonProps & AnchorHTMLAttributes<HTMLAnchorElement> & { href: string };

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", className, children, ...rest }, ref,
) {
  return (
    <button ref={ref} className={cn(styles.btn, styles[variant], styles[size], className)} {...rest}>
      <span className={styles.label}>{children}</span>
      {variant === "primary" && <span className={styles.arrow} aria-hidden>→</span>}
    </button>
  );
});

export function ButtonLink({ variant = "primary", size = "md", className, children, ...rest }: LinkProps) {
  return (
    <a className={cn(styles.btn, styles[variant], styles[size], className)} {...rest}>
      <span className={styles.label}>{children}</span>
      {variant === "primary" && <span className={styles.arrow} aria-hidden>→</span>}
    </a>
  );
}
