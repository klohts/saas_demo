import { useState } from "react";

export default function Dashboard() {
  const [count, setCount] = useState(0);

  return (
    <div className="min-h-screen bg-gray-100 p-10">
      <h1 className="text-3xl font-bold mb-6 text-black">Dashboard</h1>

      <div className="bg-white p-6 rounded-xl shadow-lg">
        <p className="text-gray-800 mb-4">
          ✅ Routing works — this is the dashboard page.
        </p>

        <button
          onClick={() => setCount(count + 1)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-800"
        >
          Test Counter: {count}
        </button>
      </div>
    </div>
  );
}
