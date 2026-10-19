import { useEffect, useRef } from "react";
import { App as CapacitorApp } from "@capacitor/app";
import { Capacitor } from "@capacitor/core";

/**
 * Routes the Android hardware back button through the SPA before exiting.
 * The handler returns true when it consumed the event.
 */
export function useAndroidBackButton(handler: (canGoBack: boolean) => boolean) {
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  useEffect(() => {
    if (Capacitor.getPlatform() !== "android") return;

    let remove: (() => void) | undefined;
    CapacitorApp.addListener("backButton", ({ canGoBack }) => {
      if (handlerRef.current(canGoBack)) return;
      if (canGoBack) {
        window.history.back();
        return;
      }
      void CapacitorApp.exitApp();
    })
      .then((handle) => {
        remove = () => void handle.remove();
      })
      .catch(() => undefined);

    return () => remove?.();
  }, []);
}
