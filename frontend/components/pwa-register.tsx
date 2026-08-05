"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
};

export function PwaRegister() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [swReady, setSwReady] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker
        .register("/sw.js")
        .then(() => setSwReady(true))
        .catch(() => setSwReady(false));
    }
    const onBip = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", onBip);
    return () => window.removeEventListener("beforeinstallprompt", onBip);
  }, []);

  if (!deferred && !swReady) return null;
  if (!deferred) return null;

  return (
    <div className="border-b border-slate-200 bg-slate-50">
      <div className="container mx-auto flex flex-wrap items-center gap-2 px-6 py-2 text-xs sm:text-sm">
        <span className="text-slate-800">
          Install <strong>Parts</strong> on this device for counter tablet use (shell cache only).
        </span>
        <Button
          type="button"
          size="sm"
          className="ml-auto h-7 text-xs"
          onClick={() => {
            void (async () => {
              await deferred.prompt();
              await deferred.userChoice;
              setDeferred(null);
            })();
          }}
        >
          <Download className="mr-1 h-3 w-3" />
          Install app
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="h-7 text-xs"
          onClick={() => setDeferred(null)}
        >
          Dismiss
        </Button>
      </div>
    </div>
  );
}
