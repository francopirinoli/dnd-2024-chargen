/**
 * OfflineIndicator — small pill that appears in the corner only when
 * the browser reports `navigator.onLine === false`.
 */
import { useEffect, useState } from "react";

export function OfflineIndicator() {
  const [online, setOnline] = useState(
    typeof navigator === "undefined" ? true : navigator.onLine,
  );
  useEffect(() => {
    const handleOnline = () => setOnline(true);
    const handleOffline = () => setOnline(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  if (online) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-4 left-4 z-[1000] rounded-full border border-border bg-card px-3 py-1 text-xs font-semibold text-muted-foreground shadow"
    >
      <span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-amber-500 align-middle" />
      Offline
    </div>
  );
}
