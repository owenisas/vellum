import { useMemo } from "react";
import styles from "./VisualizedText.module.css";

const INVISIBLE = /[\u200B\u200C\u2063\u2064]/;

export function VisualizedText({ text }: { text: string }) {
  const parts = useMemo(() => {
    const out: { kind: "text" | "tag"; value: string }[] = [];
    let buf = "", tag = "", inTag = false;
    for (const c of text) {
      if (INVISIBLE.test(c)) {
        if (!inTag) {
          if (buf) out.push({ kind: "text", value: buf });
          buf = "";
          inTag = true;
        }
        tag += c;
      } else {
        if (inTag) {
          out.push({ kind: "tag", value: tag });
          tag = "";
          inTag = false;
        }
        buf += c;
      }
    }
    if (buf) out.push({ kind: "text", value: buf });
    if (tag) out.push({ kind: "tag", value: tag });
    return out;
  }, [text]);

  return (
    <div className={styles.body}>
      {parts.map((p, i) =>
        p.kind === "text" ? (
          <span key={i}>{p.value}</span>
        ) : (
          <span key={i} className={styles.tag} title={`${p.value.length} invisible characters`} aria-label="invisible provenance tag">
            <span className={styles.tagInner} />
          </span>
        ),
      )}
    </div>
  );
}
