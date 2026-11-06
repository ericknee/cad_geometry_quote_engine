import Card from "@/components/Card";
import DataList from "@/components/DataList";
import { formatNumber } from "@/format";
import type { Features } from "@/types";

export default function ComplexityPanel({ features }: { features: Features }) {
  return (
    <Card title="Complexity">
      <DataList
        rows={[
          [
            "Complexity score",
            features.complexity_score === null ? "N/A" : formatNumber(features.complexity_score),
          ],
          ["Holes detected", features.holes_detected],
          ["Faces", features.face_count.toLocaleString("en-US")],
          ["Edges", features.edge_count.toLocaleString("en-US")],
          ["Surface area to volume", `${formatNumber(features.sa_to_volume_ratio)} cm⁻¹`],
        ]}
      />
    </Card>
  );
}
