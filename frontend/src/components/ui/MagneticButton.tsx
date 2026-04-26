import { useRef, useEffect, type ReactNode, type MouseEvent } from "react";
import { Link } from "react-router-dom";
import { cn } from "../../lib/cn";
import { prefersReducedMotion } from "../../lib/motion";
import styles from "./MagneticButton.module.css";

type Props = {
  to?: string;
  href?: string;
  onClick?: (e: MouseEvent<HTMLElement>) => void;
  children: ReactNode;
  className?: string;
  variant?: "filled" | "outline";
  arrow?: boolean;
  disabled?: boolean;
  strength?: number;
};

export function MagneticButton({
  to, href, onClick, children, className, variant = "filled", arrow = true, disabled, strength = 0.35,
}: Props) {
  const wrapRef = useRef<HTMLSpanElement>(null);
  const innerRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (prefersReducedMotion()) return;
    const wrap = wrapRef.current, inner = innerRef.current;
    if (!wrap || !inner) return;
    let raf = 0, tx = 0, ty = 0, cx = 0, cy = 0;
    const onMove = (e: PointerEvent) => {
      const rect = wrap.getBoundingClientRect();
      const mx = e.clientX - rect.left - rect.width / 2;
      const my = e.clientY - rect.top - rect.height / 2;
      tx = mx * strength; ty = my * strength;
    };
    const onLeave = () => { tx = 0; ty = 0; };
    const tick = () => {
      cx += (tx - cx) * 0.18;
      cy += (ty - cy) * 0.18;
      inner.style.transform = `translate3d(${cx}px, ${cy}px, 0)`;
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    wrap.addEventListener("pointermove", onMove);
    wrap.addEventListener("pointerleave", onLeave);
    return () => {
      cancelAnimationFrame(raf);
      wrap.removeEventListener("pointermove", onMove);
      wrap.removeEventListener("pointerleave", onLeave);
    };
  }, [strength]);

  const content = (
    <span ref={innerRef} className={styles.inner}>
      <span className={styles.label}>{children}</span>
      {arrow && <span className={styles.arrow} aria-hidden>→</span>}
    </span>
  );
  const cls = cn(styles.btn, styles[variant], disabled && styles.disabled, className);

  if (to && !disabled) {
    return (
      <span ref={wrapRef} data-magnetic className={styles.wrap}>
        <Link to={to} className={cls} onClick={onClick}>{content}</Link>
      </span>
    );
  }
  if (href && !disabled) {
    return (
      <span ref={wrapRef} data-magnetic className={styles.wrap}>
        <a href={href} className={cls} onClick={onClick}>{content}</a>
      </span>
    );
  }
  return (
    <span ref={wrapRef} data-magnetic className={styles.wrap}>
      <button type="button" className={cls} disabled={disabled} onClick={onClick}>
        {content}
      </button>
    </span>
  );
}
