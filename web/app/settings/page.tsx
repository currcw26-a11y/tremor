import { Settings } from "./settings";

export const metadata = { title: "Alert settings", robots: { index: false } };

export default function SettingsPage() {
  return (
    <div>
      <h1 className="mb-6 text-3xl font-black tracking-tight">Alert settings</h1>
      <Settings />
    </div>
  );
}
