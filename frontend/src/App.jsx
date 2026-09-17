import { useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import LandingPage from "./pages/LandingPage";
import Dashboard from "./pages/Dashboard";
import UnprocessedQueue from "./pages/UnprocessedQueue";
import AwaitingReview from "./pages/AwaitingReview";
import NeedsAttention from "./pages/NeedsAttention";
import CustomerComplaint from "./pages/CustomerComplaint";
import DashboardLayout from "./components/dashboard/DashboardLayout";
import Resolved from "./pages/Resolved";
import "./index.css";

function App() {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const isLoggedIn = !!token;

  function handleLogout() {
    localStorage.removeItem("token");
    setToken(null);
  }

  if (!isLoggedIn) {
    return (
      <Routes>
        <Route path="/login" element={<Login onLoginSuccess={setToken} />} />
        <Route path="/customerComplaint" element={<CustomerComplaint />} />
        <Route path="*" element={<LandingPage />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route path="/dashboard" element={<DashboardLayout onLogout={handleLogout} />}>
        <Route index element={<Dashboard />} />
        <Route path="unprocessed" element={<UnprocessedQueue />} />
        <Route path="awaiting-review" element={<AwaitingReview />} />
        <Route path="needs-attention" element={<NeedsAttention />} />
        <Route path="resolved" element={<Resolved />}/>
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default App;