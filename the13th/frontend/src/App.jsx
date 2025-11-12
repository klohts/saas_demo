import { useNavigate, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";

function LandingPage() {
  const navigate = useNavigate();
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-orange-400">
      <h1 className="text-4xl font-bold mb-8 text-black">
        The 13th Intelligence Dashboard
      </h1>

      <button
        onClick={() => navigate("/dashboard")}
        className="px-6 py-3 bg-purple-700 text-white rounded-lg shadow-lg hover:bg-purple-800"
      >
        Dashboard
      </button>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/dashboard" element={<Dashboard />} />
    </Routes>
  );
}
