import { Settings } from "./settings";

export const metadata = { title: "Alert settings", robots: { index: false } };

export default function SettingsPage() {
  return (
    <div>
      <h1 className="mb-8 font-serif text-4xl font-medium tracking-tight sm:text-5xl">Alert settings</h1>
      <Settings />
    </div>
  );
}
