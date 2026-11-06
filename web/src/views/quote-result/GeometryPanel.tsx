"use client";

import { useState } from "react";
import Card from "@/components/Card";
import DataList from "@/components/DataList";
import { formatLength, formatNumber } from "@/format";
import type { GeometryResult } from "@/types";

export default function GeometryPanel({ geometry }: { geometry: GeometryResult }) {
  const [unit, setUnit] = useState<"mm" | "in">("mm");
  const { length, width, height } = geometry.bounding_box_mm;

  const toggle = (
    <div className="flex overflow-hidden rounded-md border border-neutral-300 text-xs">
      {(["mm", "in"] as const).map((u) => (
        <button
          key={u}
          type="button"
          aria-pressed={unit === u}
          onClick={() => setUnit(u)}
          className={`px-2.5 py-1 ${unit === u ? "bg-neutral-900 text-white" : "bg-white hover:bg-neutral-50"}`}
        >
          {u}
        </button>
      ))}
    </div>
  );

  return (
    <Card title="Geometry" action={toggle}>
      <DataList
        rows={[
          [
            "Bounding box (L × W × H)",
            `${[length, width, height].map((mm) => formatLength(mm, unit, false)).join(" × ")} ${unit}`,
          ],
          ["Part volume", `${formatNumber(geometry.volume_cm3)} cm³`],
          ["Surface area", `${formatNumber(geometry.surface_area_cm2)} cm²`],
          ["Stock volume", `${formatNumber(geometry.stock_volume_cm3)} cm³`],
        ]}
      />
      {geometry.warnings.length > 0 && (
        <ul className="mt-4 space-y-1 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">
          {geometry.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}
    </Card>
  );
}
