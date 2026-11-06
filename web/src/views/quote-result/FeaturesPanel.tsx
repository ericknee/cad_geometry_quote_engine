import Card from "@/components/Card";
import DataList from "@/components/DataList";
import { formatNumber } from "@/format";
import type { Features } from "@/types";

export default function FeaturesPanel({ features }: { features: Features }) {
  return (
    <Card title="Features">
      <DataList
        rows={[
          ["Holes detected", features.holes_detected],
          ["Faces", features.face_count.toLocaleString("en-US")],
          ["Edges", features.edge_count.toLocaleString("en-US")],
          ["Thin walls (under 3 mm)", features.thin_wall_count],
          ["Surface area to volume", `${formatNumber(features.sa_to_volume_ratio)} cm⁻¹`],
        ]}
      />
    </Card>
  );
}
