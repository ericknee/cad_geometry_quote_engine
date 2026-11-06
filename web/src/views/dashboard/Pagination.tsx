const BUTTON =
  "rounded-md border border-neutral-300 bg-white px-3 py-1.5 text-sm hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40";

export default function Pagination({
  total,
  limit,
  skip,
  onPage,
}: {
  total: number;
  limit: number;
  skip: number;
  onPage: (page: number) => void;
}) {
  const page = Math.floor(skip / limit) + 1;
  const pages = Math.max(1, Math.ceil(total / limit));
  const first = total === 0 ? 0 : skip + 1;
  const last = Math.min(skip + limit, total);

  return (
    <div className="flex items-center justify-between gap-3">
      <p className="text-sm text-neutral-600">
        Showing {first}-{last} of {total}
      </p>
      <div className="flex gap-2">
        <button className={BUTTON} disabled={page <= 1} onClick={() => onPage(page - 1)}>
          Previous
        </button>
        <button className={BUTTON} disabled={page >= pages} onClick={() => onPage(page + 1)}>
          Next
        </button>
      </div>
    </div>
  );
}
