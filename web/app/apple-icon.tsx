// Home-screen icon for phones ("Add to Home Screen"): the three rising Tremor bars on white.
import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  // Same three rising bars as the site header, in the score colors
  const bar = (color: string, height: number) => ({ width: 30, height, borderRadius: 15, background: color });
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", background: "#ffffff", display: "flex", alignItems: "flex-end", justifyContent: "center", gap: 14, paddingBottom: 38 }}>
        <div style={bar("#18794e", 76)} />
        <div style={bar("#d4900a", 98)} />
        <div style={bar("#b4232c", 120)} />
      </div>
    ),
    size,
  );
}
