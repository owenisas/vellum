import { cn } from "../../lib/cn";
import styles from "./StageIndicator.module.css";

type Stage = { id: string; label: string };
type Props = {
  stages: Stage[];
  current: string;
  onJump?: (id: string) => void;
  className?: string;
};

export function StageIndicator({ stages, current, onJump, className }: Props) {
  const idx = stages.findIndex((s) => s.id === current);
  return (
    <ol className={cn(styles.list, className)}>
      {stages.map((s, i) => {
        const state = i < idx ? "done" : i === idx ? "current" : "pending";
        return (
          <li key={s.id} className={cn(styles.item, styles[state])}>
            <button
              type="button"
              className={styles.btn}
              onClick={() => onJump?.(s.id)}
              disabled={!onJump}
            >
              <span className={styles.dot} aria-hidden />
              <span className={styles.num}>{String(i + 1).padStart(2, "0")}</span>
              <span className={styles.label}>{s.label}</span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
