export const theme = {
  brand: {
    name: "VOOGLII",
    tagline: "Business Operating System for Marketplace Sellers"
  },
  colors: {
    ink: "#0F172A",
    inkSoft: "#334155",
    surface: "#F4EFE7",
    surfaceMuted: "#EAE3D6",
    panel: "#FFFDF8",
    panelStrong: "#F7F2E8",
    line: "#D6CCBC",
    accent: "#D0683F",
    accentStrong: "#A94822",
    mint: "#5E8F7A",
    gold: "#CC9C2C",
    sky: "#7EA4B8",
    danger: "#B84545",
    success: "#2F7D63",
    warning: "#B07A18"
  },
  radii: {
    xs: "10px",
    sm: "16px",
    md: "24px",
    lg: "32px",
    pill: "999px"
  },
  shadows: {
    soft: "0 20px 50px rgba(15, 23, 42, 0.08)",
    raised: "0 28px 90px rgba(15, 23, 42, 0.14)"
  },
  spacing: {
    section: "32px",
    card: "20px",
    widget: "24px"
  },
  transitions: {
    fast: "150ms",
    normal: "220ms"
  },
  typography: {
    eyebrowSpacing: "0.18em",
    titleTracking: "-0.04em"
  }
} as const;

export type ThemeTokens = typeof theme;
