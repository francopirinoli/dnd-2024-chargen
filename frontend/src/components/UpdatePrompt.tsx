/**
 * UpdatePrompt — surfaces PWA service-worker update + offline-ready
 * toasts using `vite-plugin-pwa`'s `useRegisterSW` hook.
 *
 * - Auto-checks for updates every hour.
 * - When a new SW is waiting, shows a "Reload" prompt.
 * - On first install, briefly shows "Ready to work offline".
 */
import { useEffect, useState } from "react";
import { useRegisterSW } from "virtual:pwa-register/react";

const UPDATE_INTERVAL_MS = 60 * 60 * 1000; // 1 hour

export function UpdatePrompt() {
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    offlineReady: [offlineReady, setOfflineReady],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW(_swUrl, registration) {
      if (!registration) return;
      // Periodically check for updates while the app is open.
      setInterval(() => {
        registration.update().catch(() => {
          /* ignore — likely offline */
        });
      }, UPDATE_INTERVAL_MS);
    },
  });

  const [hideOfflineReady, setHideOfflineReady] = useState(false);
  useEffect(() => {
    if (!offlineReady) return;
    const t = window.setTimeout(() => setHideOfflineReady(true), 5000);
    return () => window.clearTimeout(t);
  }, [offlineReady]);

  if (!needRefresh && (!offlineReady || hideOfflineReady)) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-4 right-4 z-[1000] max-w-sm rounded-md border border-border bg-card text-card-foreground shadow-lg p-4"
    >
      {needRefresh ? (
        <>
          <p className="text-sm font-semibold text-primary">
            New version available
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Reload to apply the latest update.
          </p>
          <div className="mt-3 flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => setNeedRefresh(false)}
              className="rounded border border-border px-3 py-1 text-xs hover:bg-secondary"
            >
              Later
            </button>
            <button
              type="button"
              onClick={() => updateServiceWorker(true)}
              className="rounded bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground hover:opacity-90"
            >
              Reload
            </button>
          </div>
        </>
      ) : (
        <div className="flex items-start justify-between gap-3">
          <p className="text-sm">
            <span className="font-semibold text-primary">Offline ready.</span>{" "}
            <span className="text-muted-foreground">
              The app will keep working without a connection.
            </span>
          </p>
          <button
            type="button"
            aria-label="Dismiss"
            onClick={() => {
              setOfflineReady(false);
              setHideOfflineReady(true);
            }}
            className="text-muted-foreground hover:text-foreground"
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
}
