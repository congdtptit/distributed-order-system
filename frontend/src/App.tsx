import { Navigate, Route, Routes } from "react-router";
import { AppShell } from "./components/AppShell";
import { SCREENS, type Screen } from "./screens";
import { BranchScreen } from "./screens/branch/BranchScreen";
import { InventoryScreen } from "./screens/inventory/InventoryScreen";
import { KitchenScreen } from "./screens/kitchen/KitchenScreen";
import { MonitorScreen } from "./screens/monitor/MonitorScreen";
import { ReportsScreen } from "./screens/reports/ReportsScreen";

const BUILT: Record<string, () => React.JSX.Element> = {
  branch: BranchScreen,
  kitchen: KitchenScreen,
  inventory: InventoryScreen,
  monitor: MonitorScreen,
  reports: ReportsScreen,
};

function Placeholder({ screen }: { screen: Screen }) {
  return (
    <div className="space-y-1">
      <h1 className="text-xl font-semibold text-ink">{screen.label}</h1>
      <p className="text-sm text-ink-secondary">Màn hình này được làm ở bước {screen.builtIn}.</p>
    </div>
  );
}

export function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/branch/POS01" replace />} />
        {SCREENS.map((screen) => {
          const Built = BUILT[screen.name];
          return (
            <Route
              key={screen.name}
              path={screen.path}
              element={Built ? <Built /> : <Placeholder screen={screen} />}
            />
          );
        })}
        <Route
          path="*"
          element={<p className="text-sm text-ink-secondary">Không có màn hình này.</p>}
        />
      </Routes>
    </AppShell>
  );
}
