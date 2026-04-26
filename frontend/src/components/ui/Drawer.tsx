import { AnimatePresence, motion } from "framer-motion";
import { type ReactNode, useEffect } from "react";
import { createPortal } from "react-dom";
import { ease } from "../../lib/motion";
import styles from "./Drawer.module.css";

type Props = {
  open: boolean;
  onClose: () => void;
  side?: "right" | "bottom";
  title?: string;
  children: ReactNode;
};

export function Drawer({ open, onClose, side = "right", title, children }: Props) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  const drawer = (
    <AnimatePresence>
      {open && (
        <motion.div
          className={styles.overlay}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3, ease }}
          onClick={onClose}
        >
          <motion.aside
            className={`${styles.panel} ${styles[side]}`}
            initial={side === "right" ? { x: "100%" } : { y: "100%" }}
            animate={side === "right" ? { x: 0 } : { y: 0 }}
            exit={side === "right" ? { x: "100%" } : { y: "100%" }}
            transition={{ duration: 0.42, ease }}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal
            aria-label={title}
          >
            <header className={styles.header}>
              {title && <span className={styles.title}>{title}</span>}
              <button className={styles.close} onClick={onClose} aria-label="Close">×</button>
            </header>
            <div className={styles.body}>{children}</div>
          </motion.aside>
        </motion.div>
      )}
    </AnimatePresence>
  );

  if (typeof document === "undefined") return null;
  return createPortal(drawer, document.body);
}
