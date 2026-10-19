import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "bg.carmarket.app",
  appName: "Bulgaria Auto CarMarket",
  webDir: "dist",
  backgroundColor: "#07111f",
  android: {
    path: "../android",
    allowMixedContent: true,
  },
  ios: {
    path: "../ios",
    contentInset: "automatic",
  },
  server: {
    androidScheme: "https",
  },
};

export default config;
