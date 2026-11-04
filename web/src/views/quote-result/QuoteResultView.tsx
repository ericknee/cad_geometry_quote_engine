export default function QuoteResultView({ id }: { id: string }) {
  return (
    <main className="p-8">
      <h1 className="text-2xl font-semibold">Quote</h1>
      <p className="text-neutral-600">Quote {id}</p>
    </main>
  );
}
