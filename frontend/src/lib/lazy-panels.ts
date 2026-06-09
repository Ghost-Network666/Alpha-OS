import dynamic from "next/dynamic";

export const LazySettingsDrawer = dynamic(
  () =>
    import("@/components/SettingsDrawer").then((m) => ({
      default: m.SettingsDrawer,
    })),
  { ssr: false, loading: () => null }
);

export const LazyViewCustomizer = dynamic(
  () =>
    import("@/components/ViewCustomizer").then((m) => ({
      default: m.ViewCustomizer,
    })),
  { ssr: false, loading: () => null }
);

export const LazySidePanels = dynamic(
  () =>
    import("@/components/SidePanels").then((m) => ({
      default: m.SidePanels,
    })),
  { ssr: false, loading: () => null }
);

export const LazyTelemetryPanel = dynamic(
  () =>
    import("@/components/TelemetryPanel").then((m) => ({
      default: m.TelemetryPanel,
    })),
  { ssr: false, loading: () => null }
);

export const LazyConnectScreen = dynamic(
  () =>
    import("@/components/ConnectScreen").then((m) => ({
      default: m.ConnectScreen,
    })),
  { ssr: false, loading: () => null }
);

export const LazyCapabilitiesPanel = dynamic(
  () =>
    import("@/components/CapabilitiesPanel").then((m) => ({
      default: m.CapabilitiesPanel,
    })),
  { ssr: false, loading: () => null }
);

export const LazyMetricsBar = dynamic(
  () =>
    import("@/components/MetricsBar").then((m) => ({
      default: m.MetricsBar,
    })),
  { ssr: false, loading: () => null }
);

export const LazyProfileAgentsRow = dynamic(
  () =>
    import("@/components/ProfileAgentsRow").then((m) => ({
      default: m.ProfileAgentsRow,
    })),
  { ssr: false, loading: () => null }
);