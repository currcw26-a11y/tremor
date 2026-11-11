// The preview card shown when someone shares a Tremor link (texts, social apps, chats).
import { ImageResponse } from "next/og";

export const alt = "Tremor: early warnings for cancer drug trials";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  const bar = (color: string) => ({ width: 34, height: 120, borderRadius: 17, background: color });
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", background: "#fafaf9", display: "flex", flexDirection: "column", justifyContent: "center", padding: "0 90px", color: "#0c0a09" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 36 }}>
          <div style={{ display: "flex", gap: 12 }}>
            <div style={bar("#166534")} />
            <div style={bar("#d97706")} />
            <div style={bar("#b91c1c")} />
          </div>
          <div style={{ fontSize: 120, fontWeight: 900, letterSpacing: -4 }}>Tremor</div>
        </div>
        <div style={{ marginTop: 40, fontSize: 52, fontWeight: 700, lineHeight: 1.2 }}>
          Early warnings for cancer drug trials, in plain English.
        </div>
        <div style={{ marginTop: 28, fontSize: 30, color: "#57534e" }}>Free · Every trial gets a 0-100 worry score · Not investment advice</div>
      </div>
    ),
    size,
  );
}
