"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CloudOff, RefreshCw, Wifi } from "lucide-react";
import { API_BASE_URL } from "@/lib/api";
import {
  clearOfflineQueue,
  flushOfflineQueue,
  loadOfflineQueue,
  type OfflineMutation,
} from "@/lib/offline-queue";

export function OfflineQueueBanner() {
  const [items, setItems] = useState<OfflineMutation[]>([]);
  const [online, setOnline] = useState(true);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const refresh = useCallback(() => {
    setItems(loadOfflineQueue());
    if (typeof navigator !== "undefined") setOnline(navigator.onLine);
  }, []);

  useEffect(() => {
    refresh();
    const onOnline = () => {
      setOnline(true);
      void (async () => {
        setBusy(true);
        const r = await flushOfflineQueue(API_BASE_URL);
        setMsg(
          r.flushed
            ? `Flushed ${r.flushed} offline mutation(s)${r.remaining ? ` · ${r.remaining} left` : ""}`
            : r.remaining
              ? `${r.remaining} still queued`
              : null
        );
        refresh();
        setBusy(false);
      })();
    };
    const onOffline = () => {
      setOnline(false);
      refresh();
    };
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    const t = window.setInterval(refresh, 8000);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
      window.clearInterval(t);
    };
  }, [refresh]);

  const onFlush = async () => {
    setBusy(true);
    setMsg(null);
    const r = await flushOfflineQueue(API_BASE_URL);
    setMsg(
      r.ok
        ? r.flushed
          ? `Flushed ${r.flushed}`
          : "Queue empty"
        : `Flushed ${r.flushed}, remaining ${r.remaining}`
    );
    refresh();
    setBusy(false);
  };

  if (!items.length && online) return null;

  return (
    <div className="border-b border-amber-200 bg-amber-50 text-amber-950">
      <div className="container mx-auto flex flex-wrap items-center gap-2 px-6 py-2 text-xs sm:text-sm">
        {!online ? (
          <Badge variant="outline" className="gap-1 border-amber-400 bg-white">
            <CloudOff className="h-3 w-3" /> Offline
          </Badge>
        ) : (
          <Badge variant="outline" className="gap-1 border-emerald-400 bg-white">
            <Wifi className="h-3 w-3" /> Online
          </Badge>
        )}
        <span>
          Offline queue: <strong>{items.length}</strong> mutation
          {items.length === 1 ? "" : "s"} (orders/customers only — no fake stock)
        </span>
        <div className="ml-auto flex flex-wrap gap-1">
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-7 text-xs"
            disabled={busy || !items.length || !online}
            onClick={() => void onFlush()}
          >
            <RefreshCw className={`mr-1 h-3 w-3 ${busy ? "animate-spin" : ""}`} />
            Retry now
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-7 text-xs"
            disabled={!items.length}
            onClick={() => {
              clearOfflineQueue();
              refresh();
              setMsg("Queue cleared");
            }}
          >
            Clear
          </Button>
        </div>
        {msg ? <span className="w-full text-muted-foreground sm:w-auto">{msg}</span> : null}
      </div>
    </div>
  );
}
