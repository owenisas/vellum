import { useEffect, useRef, useState } from "react";
import { prefersReducedMotion } from "../../lib/motion";
import styles from "./Cursor.module.css";

export function Cursor() {
  const dotRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    const isTouch = window.matchMedia("(hover: none)").matches;
    if (isTouch || prefersReducedMotion()) return;
    setEnabled(true);

    let mx = window.innerWidth / 2, my = window.innerHeight / 2;
    let dx = mx, dy = my, rx = mx, ry = my;
    let raf = 0;

    const onMove = (e: PointerEvent) => { mx = e.clientX; my = e.clientY; };
    const onDown = () => ringRef.current?.setAttribute("data-down", "true");
    const onUp = () => ringRef.current?.removeAttribute("data-down");
    const onOver = (e: PointerEvent) => {
      const t = e.target as HTMLElement | null;
      if (!t) return;
      const interactive = t.closest("a, button, [data-magnetic], [data-cursor='hover']");
      if (interactive) ringRef.current?.setAttribute("data-hover", "true");
      else ringRef.current?.removeAttribute("data-hover");
    };
    const tick = () => {
      dx += (mx - dx) * 0.55;
      dy += (my - dy) * 0.55;
      rx += (mx - rx) * 0.18;
      ry += (my - ry) * 0.18;
      if (dotRef.current) dotRef.current.style.transform = `translate3d(${dx}px, ${dy}px, 0)`;
      if (ringRef.current) ringRef.current.style.transform = `translate3d(${rx}px, ${ry}px, 0)`;
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerdown", onDown);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointerover", onOver, { passive: true });
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerdown", onDown);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointerover", onOver);
    };
  }, []);

  if (!enabled) return null;
  return (
    <>
      <div ref={ringRef} className={styles.ring} aria-hidden />
      <div ref={dotRef} className={styles.dot} aria-hidden />
    </>
  );
}
