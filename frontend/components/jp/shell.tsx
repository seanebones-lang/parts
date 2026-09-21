"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { JP_BRAND, JP_NAV } from "@/lib/demo-vertical";
import { cn } from "@/lib/utils";

function PilotBadge() {
  return (
    <details className="group relative">
      <summary
        className="cursor-pointer list-none rounded border border-amber-300/80 bg-amber-50 px-2.5 py-1 text-[11px] font-semibold tracking-wide text-amber-950 marker:content-none [&::-webkit-details-marker]:hidden"
        title={JP_BRAND.pilotDetail}
      >
        {JP_BRAND.pilotLabel}
      </summary>
      <div className="absolute right-0 z-40 mt-2 w-80 rounded-md border border-slate-200 bg-white p-3 text-xs leading-relaxed text-slate-600 shadow-lg">
        {JP_BRAND.pilotDetail}
      </div>
    </details>
  );
}

export function JpShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "/";

  return (
    <div className="flex min-h-screen bg-slate-100 text-slate-900">
      <aside className="sticky top-0 flex h-screen w-[200px] shrink-0 flex-col border-r border-slate-800 bg-slate-950 text-slate-100 lg:w-[212px]">
        <div className="border-b border-slate-800 px-4 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-white text-sm font-bold text-slate-950">
              {JP_BRAND.mark}
            </div>
            <div className="min-w-0">
              <div className="truncate text-[15px] font-semibold leading-tight tracking-tight">
                {JP_BRAND.title}
              </div>
              <div className="truncate text-xs text-slate-400">
                {JP_BRAND.productLine}
              </div>
            </div>
          </div>
        </div>
        <nav className="flex-1 space-y-0.5 p-2.5">
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
                  "block rounded-md px-3 py-2.5 text-[13.5px] font-medium transition-colors",
                  active
                    ? "bg-slate-800 text-white shadow-sm"
                    : "text-slate-300 hover:bg-slate-900 hover:text-white"
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-slate-800 px-4 py-3 text-[11px] leading-snug text-slate-500">
          {JP_BRAND.subtitle}
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-slate-200 bg-white/95 px-5 backdrop-blur sm:px-6 lg:px-8">
          <div>
            <div className="text-[15px] font-semibold text-slate-900">
              {JP_NAV.find((n) =>
                n.match ? new RegExp(n.match).test(pathname) : pathname === n.href
              )?.label || "JP Transmission"}
            </div>
            <div className="hidden text-xs text-slate-500 sm:block">
              {JP_BRAND.title} · {JP_BRAND.productLine}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <PilotBadge />
            <span className="hidden text-[11px] text-slate-400 xl:inline">
              {JP_BRAND.subtitle}
            </span>
          </div>
        </header>
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
