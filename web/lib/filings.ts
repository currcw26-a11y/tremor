// Plain-English names for SEC forms and 8-K item numbers.

export const FORM_NAMES: Record<string, string> = {
  "8-K": "News report",
  "8-K/A": "Correction to a news report",
  "10-Q": "Quarterly report",
  "10-K": "Yearly report",
  "S-3": "Permission to sell new shares",
  "S-1": "Permission to sell new shares",
  "424B5": "New shares being sold",
};

export const FORM_HELP: Record<string, string> = {
  "8-K": "Companies must file an 8-K within 4 business days when something important happens.",
  "10-Q": "Includes the company's cash and spending for the last 3 months.",
  "10-K": "The company's full yearly report, including its finances and risks.",
  "S-3": "Lets the company sell new shares later. Selling new shares usually makes each existing share worth a bit less.",
  "424B5": "The company is selling new shares now, often to raise cash.",
};

export function filingSummary(f: { form: string; description: string | null; key_exec_departure: boolean | null }) {
  if (f.key_exec_departure) return "A key executive is leaving";
  return f.description ?? FORM_NAMES[f.form] ?? f.form;
}
