export const theme = {
  brand: {
    name: "VOOGLII",
    tagline: "Платформа управления бизнесом на Wildberries"
  },
  colors: {
    ink: "#1F2937",
    inkSoft: "#6B7280",
    surface: "#F7F3EC",
    surfaceMuted: "#EFE7DB",
    panel: "#FFFDFC",
    panelStrong: "#FBF6EF",
    line: "#E8E0D5",
    accent: "#D97745",
    accentStrong: "#BA6438",
    mint: "#8CA996",
    gold: "#D9A441",
    sky: "#C8D6DF",
    danger: "#C75C5C",
    success: "#4E8C66",
    warning: "#D9A441"
  },
  radii: {
    xs: "10px",
    sm: "16px",
    md: "24px",
    lg: "32px",
    pill: "999px"
  },
  shadows: {
    soft: "0 18px 48px rgba(31, 41, 55, 0.08)",
    raised: "0 24px 72px rgba(31, 41, 55, 0.12)"
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
