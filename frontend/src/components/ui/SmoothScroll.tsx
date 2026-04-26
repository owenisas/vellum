import { useEffect } from "react";
import Lenis from "lenis";
import { prefersReducedMotion } from "../../lib/motion";

export function SmoothScroll() {
  useEffect(() => {
    if (prefersReducedMotion()) return;
    // Lenis fights native touch/momentum scroll on phones; use browser scrolling there.
    if (typeof window !== "undefined" && window.matchMedia("(hover: none)").matches) return;
    const lenis = new Lenis({
      duration: 0.95,
      easing: (t: number) => 1 - Math.pow(1 - t, 3),
      smoothWheel: true,
    });
    let raf = 0;
    const tick = (time: number) => { lenis.raf(time); raf = requestAnimationFrame(tick); };
    raf = requestAnimationFrame(tick);
    return () => { cancelAnimationFrame(raf); lenis.destroy(); };
  }, []);
  return null;
}
