import Navbar from "./components/Navbar.tsx";
import { Outlet } from "react-router-dom";
import { UserProvider } from "./hooks/userProvider.tsx";

function App() {
  return (
    // TODO: heights are wack - debate.tsx too long
    <UserProvider>
      <div className="h-screen">
        <Navbar />
        <Outlet />
      </div>
    </UserProvider>
  );
}

export default App;
