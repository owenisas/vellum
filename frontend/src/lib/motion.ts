export const ease = [0.65, 0, 0.35, 1] as const;
export const easeOut = [0.22, 1, 0.36, 1] as const;

export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
}
