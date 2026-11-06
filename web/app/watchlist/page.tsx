import { Watchlist } from "./watchlist";

export const metadata = { title: "Your watchlist — Tremor" };

export default function WatchlistPage() {
  return (
    <div>
      <h1 className="text-3xl font-black tracking-tight">Your watchlist</h1>
      <p className="mt-2 text-muted">Only you can see this list.</p>
      <div className="mt-6">
        <Watchlist />
      </div>
    </div>
  );
}
