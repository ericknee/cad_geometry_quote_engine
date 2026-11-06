import Link from "next/link";
import { routes } from "@/routes";

export default function NavBar() {
  return (
    <header className="border-b border-neutral-200 bg-white">
      <nav className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
        <Link href={routes.newQuote} className="text-lg font-semibold">
          Vendra
        </Link>
        <div className="flex gap-6 text-sm">
          <Link href={routes.newQuote} className="hover:underline">
            New quote
          </Link>
          <Link href={routes.dashboard} className="hover:underline">
            Dashboard
          </Link>
        </div>
      </nav>
    </header>
  );
}
