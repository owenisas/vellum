interface Props {
  detected: boolean;
  tagCount?: number;
  validCount?: number;
}

export function WatermarkBadge({ detected, tagCount, validCount }: Props) {
  return (
    <span className={"badge " + (detected ? "ok" : "warn")} title={`tags=${tagCount ?? "?"}, valid=${validCount ?? "?"}`}>
      {detected ? "✓ Provenance tag" : "✗ No tag"}
    </span>
  );
}
