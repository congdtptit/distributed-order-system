import { AlertTriangle, CheckCircle2, Info, X } from "lucide-react";
import { type ReactNode, useEffect, useState } from "react";
import { cn } from "./cn";

export type ToastColor = "green" | "blue" | "yellow" | "red";

export interface ToastInput {
  color?: ToastColor;
  title?: string;
  message: ReactNode;
  autoClose?: number | false;
}

interface ToastItem extends ToastInput {
  id: number;
}

type Listener = (items: ToastItem[]) => void;

let nextId = 1;
let items: ToastItem[] = [];
const listeners = new Set<Listener>();
const timers = new Map<number, ReturnType<typeof setTimeout>>();

function emit() {
  for (const listener of listeners) {
    listener(items);
  }
}

function dismiss(id: number) {
  const timer = timers.get(id);
  if (timer) {
    clearTimeout(timer);
    timers.delete(id);
  }
  items = items.filter((item) => item.id !== id);
  emit();
}

export const toast = {
  show(input: ToastInput): number {
    const id = nextId++;
    items = [...items, { ...input, id }];
    emit();
    const delay = input.autoClose === undefined ? 4000 : input.autoClose;
    if (delay !== false && delay > 0) {
      timers.set(
        id,
        setTimeout(() => dismiss(id), delay),
      );
    }
    return id;
  },
  dismiss,
  clean() {
    for (const timer of timers.values()) {
      clearTimeout(timer);
    }
    timers.clear();
    items = [];
    emit();
  },
};

const TONE_MAP: Record<ToastColor, { accent: string; icon: typeof Info }> = {
  green: { accent: "border-emerald-200 text-emerald-700", icon: CheckCircle2 },
  blue: { accent: "border-blue-200 text-blue-700", icon: Info },
  yellow: { accent: "border-amber-200 text-amber-700", icon: AlertTriangle },
  red: { accent: "border-rose-200 text-rose-700", icon: AlertTriangle },
};

export function ToastViewport() {
  const [list, setList] = useState<ToastItem[]>(items);

  useEffect(() => {
    listeners.add(setList);
    setList(items);
    return () => {
      listeners.delete(setList);
    };
  }, []);

  if (!list.length) return null;

  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed right-4 top-4 z-50 flex w-full max-w-sm flex-col gap-2"
    >
      {list.map((item) => {
        const tone = TONE_MAP[item.color ?? "blue"];
        const Icon = tone.icon;
        return (
          <div
            key={item.id}
            role="status"
            className={cn(
              "pointer-events-auto flex items-start gap-2.5 rounded-xl border bg-surface p-3.5 text-sm shadow-lg",
              tone.accent,
            )}
          >
            <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <div className="min-w-0 flex-1 text-ink">
              {item.title && <p className="font-semibold leading-5">{item.title}</p>}
              <div className="text-sm leading-snug text-ink-secondary">{item.message}</div>
            </div>
            <button
              type="button"
              onClick={() => dismiss(item.id)}
              aria-label="Đóng thông báo"
              className="shrink-0 rounded-md p-1 text-ink-muted hover:bg-subtle hover:text-ink"
            >
              <X className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
