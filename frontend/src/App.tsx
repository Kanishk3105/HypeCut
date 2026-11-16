import { BrowserRouter } from "react-router-dom";
import { NavLayout } from "./app/NavLayout";
import { AppRoutes } from "./app/AppRoutes";

export function App() {
  return (
    <BrowserRouter>
      <NavLayout>
        <AppRoutes />
      </NavLayout>
    </BrowserRouter>
  );
}
