import { useState } from "react";

export default function Dashboard() {
  const [count, setCount] = useState(0);

  return (
    <div className="min-h-screen bg-brand-grayBg p-10">
      <h1 className="text-3xl font-bold mb-6 text-brand-purple">
        Dashboard
      </h1>

      <div className="card">
        <p className="text-gray-800 mb-4">
          ✅ Routing works — this is the dashboard page.
        </p>

        <button onClick={() => setCount(count + 1)}>
          Test Counter: {count}
        </button>
      </div>
    </div>
  );
}
