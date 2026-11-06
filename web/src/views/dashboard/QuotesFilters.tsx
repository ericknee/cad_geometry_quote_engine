import Select from "@/components/Select";
import { ALL_STATUSES, type QuoteStatus } from "@/types";
import type { Filters, SortOrder } from "./filters";

export default function QuotesFilters({
  filters,
  onChange,
}: {
  filters: Filters;
  onChange: (next: Partial<Filters>) => void;
}) {
  // Picking a status shows exactly that status, so the archived toggle has no effect then.
  const statusPicked = filters.status !== null;

  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
      <label className="flex items-center gap-2 text-sm">
        Status
        <Select
          value={filters.status ?? ""}
          onChange={(e) => onChange({ status: (e.target.value || null) as QuoteStatus | null })}
        >
          <option value="">All</option>
          {ALL_STATUSES.map((status) => (
            <option key={status} value={status} className="capitalize">
              {status}
            </option>
          ))}
        </Select>
      </label>

      <label className="flex items-center gap-2 text-sm">
        Sort
        <Select value={filters.sort} onChange={(e) => onChange({ sort: e.target.value as SortOrder })}>
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
        </Select>
      </label>

      <label
        className={`flex items-center gap-2 text-sm ${statusPicked ? "text-fg-subtle" : ""}`}
        title={statusPicked ? "Not used while a status is selected" : undefined}
      >
        <input
          type="checkbox"
          checked={filters.showArchived}
          disabled={statusPicked}
          onChange={(e) => onChange({ showArchived: e.target.checked })}
        />
        Show archived
      </label>
    </div>
  );
}
