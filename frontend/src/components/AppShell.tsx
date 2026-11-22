import { Menu, PanelLeftClose, PanelLeftOpen, UtensilsCrossed, X } from "lucide-react";
import { type ReactNode, useState } from "react";
import { NavLink, useLocation } from "react-router";
import { SCREENS } from "../screens";
import { cn } from "../ui";

const GROUPS = [...new Set(SCREENS.map((s) => s.group))];

export function AppShell({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { pathname } = useLocation();

  const currentScreen = SCREENS.find((s) => pathname.startsWith(`/${s.link.split("/")[1] ?? ""}`));

  return (
    <div className="min-h-screen bg-canvas text-ink">
      {/* Mobile drawer backdrop */}
      {mobileOpen && (
        <div
          aria-hidden="true"
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 z-30 bg-slate-950/45 backdrop-blur-[1px] md:hidden"
        />
      )}

      {/* Left Sidebar Rail — Deep Slate-Navy Anchor */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex flex-col border-r border-slate-800 bg-[#0f172a] text-slate-200 transition-[width,transform] duration-200 md:translate-x-0",
          collapsed ? "md:w-16" : "md:w-56",
          mobileOpen ? "w-60 translate-x-0" : "-translate-x-full md:translate-x-0",
        )}
      >
        <div
          className={cn(
            "flex h-13 shrink-0 items-center border-b border-slate-800 px-3",
            collapsed ? "justify-center" : "justify-between gap-2.5",
          )}
        >
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white shadow-sm shadow-blue-950/50">
              <UtensilsCrossed className="h-4 w-4" aria-hidden="true" />
            </span>
            {!collapsed && (
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold tracking-[-0.01em] text-white">
                  Đặt món
                </p>
                <p className="truncate text-[11px] text-slate-400">Chuỗi nhà hàng</p>
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            aria-label="Đóng menu"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white md:hidden"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <nav aria-label="Các màn hình" className="flex-1 space-y-5 overflow-y-auto px-2.5 py-4">
          {GROUPS.map((group) => (
            <div key={group} className="space-y-1">
              {!collapsed && (
                <p className="px-2.5 pb-1 text-[11px] font-semibold uppercase tracking-[0.06em] text-slate-400">
                  {group}
                </p>
              )}
              {SCREENS.filter((s) => s.group === group).map((screen) => {
                const Icon = screen.icon;
                const section = screen.link.split("/")[1] ?? "";
                const active = pathname.startsWith(`/${section}`);
                return (
                  <NavLink
                    key={screen.name}
                    to={screen.link}
                    data-active={active ? "true" : undefined}
                    title={collapsed ? screen.label : undefined}
                    onClick={() => setMobileOpen(false)}
                    className={cn(
                      "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors",
                      collapsed && "justify-center px-0",
                      active
                        ? "bg-blue-600 font-semibold text-white shadow-sm shadow-blue-950/40"
                        : "font-medium text-slate-300 hover:bg-slate-800/80 hover:text-white",
                    )}
                  >
                    <Icon
                      className={cn("h-4 w-4 shrink-0", active ? "text-white" : "text-slate-400")}
                      aria-hidden
                    />
                    <span className={cn(collapsed && "sr-only")}>{screen.label}</span>
                  </NavLink>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="hidden border-t border-slate-800 p-2.5 md:flex md:justify-end">
          <button
            type="button"
            onClick={() => setCollapsed((c) => !c)}
            aria-label={collapsed ? "Mở rộng thanh điều hướng" : "Thu gọn thanh điều hướng"}
            title={collapsed ? "Mở rộng" : "Thu gọn"}
            className={cn(
              "flex h-8 items-center gap-2 rounded-lg px-2 text-xs font-medium text-slate-400 transition-colors hover:bg-slate-800 hover:text-white",
              collapsed && "w-full justify-center px-0",
            )}
          >
            {collapsed ? (
              <PanelLeftOpen className="h-4 w-4" aria-hidden="true" />
            ) : (
              <>
                <PanelLeftClose className="h-4 w-4" aria-hidden="true" />
                <span>Thu gọn</span>
              </>
            )}
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div
        className={cn(
          "flex min-h-screen flex-col transition-[padding-left] duration-200",
          collapsed ? "md:pl-16" : "md:pl-56",
        )}
      >
        <header className="sticky top-0 z-20 flex h-13 items-center justify-between border-b border-line bg-[#eaeff5]/90 px-4 backdrop-blur-md sm:px-6">
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              aria-label="Mở menu"
              className="rounded-lg p-1.5 text-ink-secondary hover:bg-white/70 hover:text-ink md:hidden"
            >
              <Menu className="h-5 w-5" aria-hidden="true" />
            </button>
            <div className="flex items-center gap-2 text-xs text-ink-muted">
              <span className="font-medium text-ink-secondary">
                {currentScreen?.group ?? "Hệ thống"}
              </span>
              <span aria-hidden="true">/</span>
              <span className="font-semibold text-ink">{currentScreen?.label ?? "Đặt món"}</span>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-ink-secondary">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-2.5 py-1 font-medium text-ink-secondary shadow-2xs">
              <span className="h-2 w-2 rounded-full bg-emerald-500" aria-hidden="true" />
              Làm mới 2s
            </span>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1600px] flex-1 px-4 py-5 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}
