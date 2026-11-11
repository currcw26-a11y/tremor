import { Suspense } from "react";
import { UnsubscribeButton } from "./unsubscribe-button";

export const metadata = { title: "Unsubscribe", robots: { index: false } };

async function Content({ searchParams }: { searchParams: PageProps<"/unsubscribe">["searchParams"] }) {
  const token = (await searchParams).token;
  if (typeof token !== "string") return <p className="text-muted">This unsubscribe link is missing its code. Use the link in a Tremor email.</p>;
  return <UnsubscribeButton token={token} />;
}

export default function Unsubscribe(props: PageProps<"/unsubscribe">) {
  return (
    <div>
      <h1 className="mb-8 font-serif text-4xl font-medium tracking-tight sm:text-5xl">Unsubscribe</h1>
      <Suspense fallback={<div className="h-32 animate-pulse rounded-lg bg-line" />}>
        <Content searchParams={props.searchParams} />
      </Suspense>
    </div>
  );
}
