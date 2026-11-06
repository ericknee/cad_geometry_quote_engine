import Button from "@/components/Button";

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
      <p className="text-sm text-fg-muted">
        Showing {first}-{last} of {total}
      </p>
      <div className="flex gap-2">
        <Button variant="secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          Previous
        </Button>
        <Button variant="secondary" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          Next
        </Button>
      </div>
    </div>
  );
}
