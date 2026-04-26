import { motion } from "framer-motion";
import { useMemo } from "react";
import styles from "./MerkleTreeScene.module.css";

type Props = {
  leafCount?: number;
  highlightLeaf?: number;
  sealed?: boolean;
  className?: string;
};

type Node = { x: number; y: number; depth: number; idx: number };

export function MerkleTreeScene({
  leafCount = 8, highlightLeaf = 2, sealed = false, className,
}: Props) {
  const { nodes, edges, pathSet, leafSet } = useMemo(() => {
    const depth = Math.ceil(Math.log2(leafCount));
    const nodes: Node[][] = [];
    const W = 600, H = 320;
    for (let d = depth; d >= 0; d--) {
      const count = 2 ** d;
      const row: Node[] = [];
      for (let i = 0; i < count; i++) {
        const x = ((i + 0.5) / count) * W;
        const y = ((depth - d) / depth) * (H - 60) + 30;
        row.push({ x, y, depth: d, idx: i });
      }
      nodes.push(row);
    }
    const edges: { x1: number; y1: number; x2: number; y2: number; key: string }[] = [];
    for (let level = 0; level < nodes.length - 1; level++) {
      const cur = nodes[level];
      const parent = nodes[level + 1];
      for (let i = 0; i < cur.length; i++) {
        const p = parent[Math.floor(i / 2)];
        edges.push({ x1: cur[i].x, y1: cur[i].y, x2: p.x, y2: p.y, key: `${level}-${i}` });
      }
    }
    const pathSet = new Set<string>();
    const leafSet = new Set<string>([`0-${highlightLeaf}`]);
    let idx = highlightLeaf;
    for (let level = 0; level < nodes.length - 1; level++) {
      pathSet.add(`${level}-${idx}`);
      idx = Math.floor(idx / 2);
    }
    pathSet.add(`${nodes.length - 1}-0`);
    return { nodes, edges, pathSet, leafSet };
  }, [leafCount, highlightLeaf]);

  return (
    <svg viewBox="0 0 600 320" className={`${styles.svg} ${className ?? ""}`} role="img" aria-label="Merkle tree">
      <defs>
        <linearGradient id="path-grad" x1="0" x2="0" y1="1" y2="0">
          <stop offset="0%" stopColor="#00D26A" stopOpacity="0.2" />
          <stop offset="100%" stopColor="#00D26A" stopOpacity="1" />
        </linearGradient>
      </defs>
      {edges.map((e) => {
        const child = `${parseInt(e.key.split("-")[0])}-${e.key.split("-")[1]}`;
        const onPath = pathSet.has(child);
        return (
          <motion.line
            key={e.key}
            x1={e.x1} y1={e.y1} x2={e.x2} y2={e.y2}
            stroke={onPath ? "url(#path-grad)" : "currentColor"}
            strokeWidth={onPath ? 2 : 1}
            strokeOpacity={onPath ? 1 : 0.18}
            initial={{ pathLength: 0 }}
            animate={{ pathLength: sealed ? 1 : 0.3 }}
            transition={{ duration: 1, ease: [0.65, 0, 0.35, 1], delay: parseInt(e.key.split("-")[0]) * 0.15 }}
          />
        );
      })}
      {nodes.flatMap((row) =>
        row.map((n) => {
          const level = nodes.length - 1 - n.depth;
          const key = `${level}-${n.idx}`;
          const isLeaf = level === 0;
          const isRoot = level === nodes.length - 1;
          const onPath = pathSet.has(key);
          const isHighlight = leafSet.has(key);
          const r = isRoot ? 11 : isHighlight ? 8 : isLeaf ? 5 : 4;
          return (
            <g key={`n-${key}`}>
              {(onPath || isHighlight) && (
                <motion.circle
                  cx={n.x} cy={n.y} r={r + 6}
                  fill="#00D26A" fillOpacity={0.18}
                  initial={{ scale: 0 }}
                  animate={{ scale: sealed ? 1 : 0 }}
                  transition={{ duration: 0.5, delay: 0.2 + level * 0.15 }}
                />
              )}
              <motion.circle
                cx={n.x} cy={n.y} r={r}
                fill={onPath || isHighlight ? "#00D26A" : "currentColor"}
                fillOpacity={onPath || isHighlight ? 1 : 0.4}
                stroke="currentColor"
                strokeWidth={isRoot ? 1.5 : 0}
                strokeOpacity={0.4}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ duration: 0.4, delay: level * 0.1, ease: [0.22, 1, 0.36, 1] }}
              />
              {isRoot && (
                <text x={n.x} y={n.y - 18} textAnchor="middle" fill="currentColor" fillOpacity={0.85}
                      fontSize="9" fontFamily="var(--font-mono)" letterSpacing="0.18em">ROOT</text>
              )}
              {isHighlight && (
                <text x={n.x} y={n.y + 22} textAnchor="middle" fill="#00D26A"
                      fontSize="9" fontFamily="var(--font-mono)" letterSpacing="0.18em">YOURS</text>
              )}
            </g>
          );
        }),
      )}
    </svg>
  );
}
