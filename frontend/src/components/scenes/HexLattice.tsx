import { useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import type { ChainBlock } from "../../api/types";
import styles from "./HexLattice.module.css";

type Props = {
  blocks: ChainBlock[];
  onHover?: (block: ChainBlock | null) => void;
};

export function HexLattice({ blocks, onHover }: Props) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const ref = useRef<SVGSVGElement>(null);

  const cells = useMemo(() => {
    const cols = 9, rows = 7, r = 18;
    const w = Math.sqrt(3) * r;
    const h = 1.5 * r;
    const xs: { x: number; y: number; idx: number }[] = [];
    let n = 0;
    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        const x = col * w + (row % 2 ? w / 2 : 0) + r;
        const y = row * h + r;
        xs.push({ x, y, idx: n++ });
      }
    }
    return xs;
  }, []);

  const filled = blocks.length;
  const handleEnter = (idx: number) => {
    setHoverIdx(idx);
    if (onHover && idx < filled) onHover(blocks[idx]);
  };
  const handleLeave = () => { setHoverIdx(null); onHover?.(null); };

  return (
    <svg
      ref={ref}
      viewBox={`0 0 ${9 * Math.sqrt(3) * 18 + 18} ${7 * 1.5 * 18 + 18}`}
      className={styles.svg}
      role="img"
      aria-label="Lattice of anchored blocks"
    >
      {cells.map(({ x, y, idx }) => {
        const isFilled = idx < filled;
        const isHover = hoverIdx === idx;
        const r = 18;
        const points = Array.from({ length: 6 }).map((_, i) => {
          const a = (Math.PI / 3) * i - Math.PI / 6;
          return `${x + r * Math.cos(a)},${y + r * Math.sin(a)}`;
        }).join(" ");
        return (
          <motion.polygon
            key={idx}
            points={points}
            fill={isFilled ? "var(--signal)" : "transparent"}
            fillOpacity={isFilled ? (isHover ? 1 : 0.85) : 0}
            stroke="currentColor"
            strokeOpacity={isFilled ? 0 : 0.18}
            strokeWidth={1}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.45, delay: 0.005 * idx, ease: [0.22, 1, 0.36, 1] }}
            onMouseEnter={() => handleEnter(idx)}
            onMouseLeave={handleLeave}
            whileHover={{ scale: 1.08 }}
            style={{ cursor: isFilled ? "none" : "default", transformOrigin: `${x}px ${y}px` }}
          />
        );
      })}
    </svg>
  );
}
