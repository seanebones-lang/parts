"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { JP_BRAND, JP_NAV } from "@/lib/demo-vertical";
import { cn } from "@/lib/utils";

function PilotBadge() {
  return (
    <details className="group relative">
      <summary
        className="cursor-pointer list-none rounded border border-slate-300 bg-slate-100 px-2 py-0.5 text-[10px] font-semibold tracking-wide text-slate-700 marker:content-none [&::-webkit-details-marker]:hidden"
        title={JP_BRAND.pilotDetail}
      >
        {JP_BRAND.pilotLabel}
      </summary>
      <div className="absolute right-0 z-40 mt-2 w-72 rounded-md border border-slate-200 bg-white p-3 text-xs leading-relaxed text-slate-600 shadow-lg">
        {JP_BRAND.pilotDetail}
      </div>
    </details>
  );
}

export function JpShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "/";

  return (
    <div className="flex min-h-screen bg-slate-100 text-slate-900">
      <aside className="sticky top-0 flex h-screen w-56 shrink-0 flex-col border-r border-slate-200 bg-slate-950 text-slate-100">
        <div className="border-b border-slate-800 px-4 py-5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded bg-white text-xs font-bold text-slate-950">
              {JP_BRAND.mark}
            </div>
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold leading-tight">
                {JP_BRAND.title}
              </div>
              <div className="truncate text-[11px] text-slate-400">
                {JP_BRAND.productLine}
              </div>
            </div>
          </div>
        </div>
        <nav className="flex-1 space-y-0.5 p-2">
          {JP_NAV.map((item) => {
            const active =
              item.match != null
                ? new RegExp(item.match).test(pathname)
                : pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "block rounded px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-slate-800 text-white"
                    : "text-slate-300 hover:bg-slate-900 hover:text-white"
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-slate-800 px-4 py-3 text-[11px] text-slate-500">
          {JP_BRAND.subtitle}
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-12 items-center justify-between border-b border-slate-200 bg-white/95 px-6 backdrop-blur">
          <div className="text-sm font-medium text-slate-700">
            {JP_NAV.find((n) =>
              n.match ? new RegExp(n.match).test(pathname) : pathname === n.href
            )?.label || "JP Transmission"}
          </div>
          <div className="flex items-center gap-3">
            <PilotBadge />
            <span className="hidden text-[11px] text-slate-400 sm:inline">
              {JP_BRAND.subtitle}
            </span>
          </div>
        </header>
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
