import { motion, useReducedMotion } from "framer-motion";
import { cn } from "../../lib/cn";
import { ease } from "../../lib/motion";
import styles from "./DisplayHeading.module.css";

type Tag = "h1" | "h2" | "h3";
type Props = {
  as?: Tag;
  children: string;
  className?: string;
  delay?: number;
  italicWords?: string[];
  align?: "left" | "center";
};

export function DisplayHeading({
  as = "h1", children, className, delay = 0, italicWords = [], align = "left",
}: Props) {
  const reduce = useReducedMotion();
  const Tag = as as "h1";
  const lines = children.split("\n");
  let wordIndex = 0;
  return (
    <Tag className={cn(styles.h, styles[align], className)}>
      {lines.map((line, li) => {
        const words = line.split(/(\s+)/);
        return (
          <span key={li} className={styles.line}>
            {words.map((w, wi) => {
              if (/^\s+$/.test(w)) return <span key={wi}>{w}</span>;
              const i = wordIndex++;
              const isItalic = italicWords.includes(w.replace(/[.,—,]/g, ""));
              return (
                <span key={wi} className={styles.wordWrap}>
                  <motion.span
                    className={cn(styles.word, isItalic && styles.italic)}
                    initial={reduce ? false : { y: "108%" }}
                    animate={{ y: 0 }}
                    transition={{ duration: 0.95, ease, delay: delay + i * 0.05 }}
                  >
                    {w}
                  </motion.span>
                </span>
              );
            })}
          </span>
        );
      })}
    </Tag>
  );
}
