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
          "inline-flex items-center rounded px-2.5 py-1 text-xs font-semibold tracking-wide bg-red-100 text-red-800",
          className
        )}
      >
        Out of Stock
      </span>
    );
  }
  if (level === "low") {
    return (
      <span
        className={cn(
          "inline-flex items-center rounded px-2.5 py-1 text-xs font-semibold tracking-wide bg-amber-100 text-amber-900",
          className
        )}
      >
        Low Stock · {qty}
      </span>
    );
  }
  return (
    <span
      className={cn(
        "inline-flex items-center rounded px-2.5 py-1 text-xs font-semibold tracking-wide bg-emerald-100 text-emerald-900",
        className
      )}
    >
      In Stock · {qty}
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
      <span className="inline-flex items-center rounded-md bg-amber-100 px-3 py-1.5 text-sm font-semibold text-amber-950">
        Needs Review
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-md bg-emerald-100 px-3 py-1.5 text-sm font-semibold text-emerald-950">
      Matched
    </span>
  );
}

export function StatusPill({
  children,
  tone = "neutral",
  className,
}: {
  children: React.ReactNode;
  tone?: "neutral" | "success" | "warn" | "danger" | "info";
  className?: string;
}) {
  const tones: Record<string, string> = {
    neutral: "bg-slate-100 text-slate-700 border-slate-200",
    success: "bg-emerald-50 text-emerald-900 border-emerald-200",
    warn: "bg-amber-50 text-amber-950 border-amber-200",
    danger: "bg-red-50 text-red-900 border-red-200",
    info: "bg-slate-800 text-white border-slate-800",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold capitalize",
        tones[tone] || tones.neutral,
        className
      )}
    >
      {children}
    </span>
  );
}

export function JpPage({
  title,
  description,
  actions,
  children,
  dense,
  fullBleed,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  dense?: boolean;
  /** Nearly full remaining viewport; default for ops screens */
  fullBleed?: boolean;
}) {
  return (
    <div
      className={cn(
        "mx-auto w-full px-5 py-5 sm:px-6 lg:px-8",
        fullBleed || dense
          ? "max-w-[1600px]"
          : "max-w-[1400px]"
      )}
    >
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-[26px]">
            {title}
          </h1>
          {description ? (
            <p className="mt-1.5 max-w-3xl text-[15px] leading-relaxed text-slate-500">
              {description}
            </p>
          ) : null}
        </div>
        {actions ? (
          <div className="flex flex-wrap items-center gap-2">{actions}</div>
        ) : null}
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
  bodyClassName,
  flush,
}: {
  children: React.ReactNode;
  className?: string;
  title?: string;
  right?: React.ReactNode;
  bodyClassName?: string;
  flush?: boolean;
}) {
  return (
    <section
      className={cn(
        "rounded-lg border border-slate-200 bg-white shadow-sm",
        className
      )}
    >
      {(title || right) && (
        <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3 sm:px-5">
          {title ? (
            <h2 className="text-[13px] font-semibold uppercase tracking-wide text-slate-700">
              {title}
            </h2>
          ) : (
            <span />
          )}
          {right}
        </div>
      )}
      <div className={cn(flush ? "" : "p-4 sm:p-5", bodyClassName)}>
        {children}
      </div>
    </section>
  );
}

export function StatTile({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "default" | "success" | "warn" | "danger" | "neutral";
}) {
  const accent =
    tone === "success"
      ? "border-l-emerald-500"
      : tone === "warn"
        ? "border-l-amber-400"
        : tone === "danger"
          ? "border-l-red-500"
          : tone === "neutral"
            ? "border-l-slate-400"
            : "border-l-slate-900";
  const valueColor =
    tone === "success"
      ? "text-emerald-800"
      : tone === "warn"
        ? "text-amber-900"
        : tone === "danger"
          ? "text-red-800"
          : "text-slate-900";
  return (
    <div
      className={cn(
        "rounded-lg border border-slate-200 border-l-4 bg-white px-4 py-3.5 shadow-sm",
        accent
      )}
    >
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div
        className={cn(
          "mt-1.5 text-[28px] font-semibold leading-none tabular-nums tracking-tight",
          valueColor
        )}
      >
        {value}
      </div>
      {hint ? (
        <div className="mt-1.5 text-xs text-slate-500">{hint}</div>
      ) : null}
    </div>
  );
}

export function MetricGroup({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-5">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{children}</div>
    </div>
  );
}

export function EmptyState({
  title,
  body,
  children,
  className,
}: {
  title: string;
  body?: string;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border border-dashed border-slate-300 bg-slate-50/80 px-6 py-10 text-center",
        className
      )}
    >
      <div className="text-base font-semibold text-slate-800">{title}</div>
      {body ? (
        <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-slate-500">
          {body}
        </p>
      ) : null}
      {children ? <div className="mt-4">{children}</div> : null}
    </div>
  );
}

export function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
      {children}
    </div>
  );
}

export function PrimaryButton({
  children,
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      className={cn(
        "inline-flex h-10 items-center justify-center rounded-md bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function SecondaryButton({
  children,
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      className={cn(
        "inline-flex h-10 items-center justify-center rounded-md border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-800 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function DangerButton({
  children,
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      className={cn(
        "inline-flex h-10 items-center justify-center rounded-md border border-red-300 bg-white px-4 text-sm font-semibold text-red-800 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
