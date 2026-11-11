// Home-screen icon for phones ("Add to Home Screen"): the three Tremor bars on white.
import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  const bar = (color: string) => ({ width: 30, height: 104, borderRadius: 15, background: color });
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", background: "#ffffff", display: "flex", alignItems: "center", justifyContent: "center", gap: 12 }}>
        <div style={bar("#166534")} />
        <div style={bar("#d97706")} />
        <div style={bar("#b91c1c")} />
      </div>
    ),
    size,
  );
}
