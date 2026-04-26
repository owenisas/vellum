import { useState } from "react";
import { motion } from "framer-motion";
import { useSearchParams } from "react-router-dom";

import { useChainBlocks, useChainStatus } from "../api/chain";
import { DisplayHeading } from "../components/ui/DisplayHeading";
import { EditorialCaption } from "../components/ui/EditorialCaption";
import { Button } from "../components/ui/Button";
import { HexLattice } from "../components/scenes/HexLattice";
import { BlockTable } from "./ledger/BlockTable";
import { IssuerList } from "./ledger/IssuerList";
import { AdminDrawer } from "./ledger/AdminDrawer";
import { ease } from "../lib/motion";
import type { ChainBlock } from "../api/chain";
import styles from "./Ledger.module.css";

export function Ledger() {
  const [params, setParams] = useSearchParams();
  const [limit, setLimit] = useState(50);
  const [hover, setHover] = useState<number | null>(null);
  const [adminOpen, setAdminOpen] = useState(params.get("tab") === "issuers");
  const { data: status } = useChainStatus();
  const { data: blocks, isLoading } = useChainBlocks(limit);

  const list = blocks ?? [];
  const chain = status?.chain_type ?? "—";
  const lastBlockTime = list[0]?.timestamp;

  const onLatticeHover = (b: ChainBlock | null) => {
    if (!b) return setHover(null);
    const idx = list.findIndex((x) => x.tx_hash === b.tx_hash);
    setHover(idx >= 0 ? idx : null);
  };

  return (
    <motion.section
      key="ledger"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4, ease }}
      className={`container ${styles.shell}`}
    >
      <header className={styles.head}>
        <EditorialCaption number="N°03" rule>THE PUBLIC LEDGER</EditorialCaption>
        <DisplayHeading as="h1" italicWords={["public"]}>
          {"A record kept\nin public —\nfor anyone\nto read."}
        </DisplayHeading>
        <p className={styles.lede}>
          {status
            ? `${(status.block_count ?? 0).toLocaleString()} sentences anchored on ${chain}${
                lastBlockTime ? `, most recently ${timeAgo(lastBlockTime)}` : ""
              }.`
            : "Loading the ledger…"}
        </p>
      </header>

      <div className={styles.grid}>
        <div className={styles.left}>
          <div className={styles.tableHead}>
            <span className={styles.tableLabel}>Recent anchors</span>
            <span className={styles.tableMeta}>
              {isLoading ? "Loading…" : `${list.length} of ${(status?.block_count ?? 0).toLocaleString()}`}
            </span>
          </div>
          <BlockTable
            blocks={list}
            chainType={chain}
            hoverIndex={hover}
            setHoverIndex={setHover}
          />
          {list.length >= limit && (
            <div className={styles.more}>
              <Button variant="outline" onClick={() => setLimit(limit + 50)}>Load more</Button>
            </div>
          )}
        </div>

        <aside className={styles.right}>
          <div className={styles.lattice}>
            <span className={styles.latticeCap}>LATTICE</span>
            <HexLattice blocks={list} onHover={onLatticeHover} />
            <p className={styles.latticeNote}>
              Each cell is one anchored block. Hover to highlight in the table.
            </p>
          </div>
          <IssuerList
            onAdmin={() => {
              setAdminOpen(true);
              setParams({ tab: "issuers" }, { replace: true });
            }}
          />
        </aside>
      </div>

      <AdminDrawer
        open={adminOpen}
        onClose={() => {
          setAdminOpen(false);
          setParams({}, { replace: true });
        }}
      />
    </motion.section>
  );
}

function timeAgo(iso: string): string {
  const t = Date.parse(iso);
  if (isNaN(t)) return iso;
  const d = Math.max(0, Math.round((Date.now() - t) / 1000));
  if (d < 60) return `${d} seconds ago`;
  if (d < 3600) return `${Math.floor(d / 60)} minutes ago`;
  if (d < 86400) return `${Math.floor(d / 3600)} hours ago`;
  return `${Math.floor(d / 86400)} days ago`;
}
