import { Badge } from "./ui";
import type { WatermarkInfo } from "../api/types";

export function WatermarkBadge({ info }: { info: WatermarkInfo | undefined }) {
  if (!info) return <Badge>—</Badge>;
  if (!info.watermarked) return <Badge tone="warning">No watermark</Badge>;
  if (info.invalid_count > 0)
    return (
      <Badge tone="danger">
        {info.valid_count}/{info.tag_count} tags valid
      </Badge>
    );
  return (
    <Badge tone="success">
      {info.valid_count} watermark tag{info.valid_count === 1 ? "" : "s"}
    </Badge>
  );
}
