import { cn } from "@/lib/utils";

export function stockLevel(qty: number): "in" | "low" | "out" {
  if (qty <= 0) return "out";
  if (qty === 1) return "low";
  return "in";
}

export function StockBadge({
  qty,
  className,
}: {
  qty: number;
  className?: string;
}) {
  const level = stockLevel(qty);
  if (level === "out") {
    return (
      <span
        className={cn(
          "inline-flex items-center rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide bg-red-100 text-red-800",
          className
        )}
      >
        Out of stock
      </span>
    );
  }
  if (level === "low") {
    return (
      <span
        className={cn(
          "inline-flex items-center rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide bg-amber-100 text-amber-900",
          className
        )}
      >
        Low stock · {qty}
      </span>
    );
  }
  return (
    <span
      className={cn(
        "inline-flex items-center rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide bg-emerald-100 text-emerald-900",
        className
      )}
    >
      In stock · {qty}
    </span>
  );
}

export function OutcomeBadge({
  outcome,
}: {
  outcome: "RESOLVED" | "NEEDS_HUMAN" | string;
}) {
  if (outcome === "NEEDS_HUMAN") {
    return (
      <span className="inline-flex items-center rounded bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-950">
        Needs Review
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-950">
      Matched
    </span>
  );
}

export function JpPage({
  title,
  description,
  actions,
  children,
  dense,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  dense?: boolean;
}) {
  return (
    <div className={cn("mx-auto w-full max-w-6xl px-6 py-5", dense && "max-w-7xl")}>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-900">
            {title}
          </h1>
          {description ? (
            <p className="mt-1 max-w-2xl text-sm text-slate-500">{description}</p>
          ) : null}
        </div>
        {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
      </div>
      {children}
    </div>
  );
}

export function Panel({
  children,
  className,
  title,
  right,
}: {
  children: React.ReactNode;
  className?: string;
  title?: string;
  right?: React.ReactNode;
}) {
  return (
    <section
      className={cn(
        "rounded-lg border border-slate-200 bg-white shadow-sm",
        className
      )}
    >
      {(title || right) && (
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2.5">
          {title ? (
            <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
          ) : (
            <span />
          )}
          {right}
        </div>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function StatTile({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">
        {value}
      </div>
      {hint ? <div className="mt-0.5 text-xs text-slate-400">{hint}</div> : null}
    </div>
  );
}

export function EmptyState({ title, body }: { title: string; body?: string }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center">
      <div className="text-sm font-medium text-slate-700">{title}</div>
      {body ? <p className="mt-1 text-xs text-slate-500">{body}</p> : null}
    </div>
  );
}
