#!/bin/bash
# === THE13TH Light Grey + Purple Theme (Patched Version) ===
# Fully replaces any cached dark theme build and enforces the new light grey + purple palette

set -e
echo "🎨 Applying THE13TH Light Grey + Purple Theme (patched rebuild)..."

# 1️⃣ Update Tailwind config
cat > frontend/tailwind.config.js <<'EOF'
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--color-bg)',
        surface: 'var(--color-surface)',
        surfaceAlt: 'var(--color-surface-alt)',
        accent: 'var(--color-accent)',
        accentLight: 'var(--color-accent-light)',
        text: 'var(--color-text)',
      },
    },
  },
  plugins: [],
}
EOF
echo "✅ Tailwind config updated."

# 2️⃣ Apply new color theme with global overrides
cat > frontend/src/index.css <<'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;

/* === THE13TH Light Grey + Purple Theme === */
:root {
  --color-bg: #f4f4f7;            /* soft light grey background */
  --color-surface: #ffffff;       /* white surface for cards/panels */
  --color-surface-alt: #ececf0;   /* subtle contrast for sidebar */
  --color-accent: #7c3aed;        /* vibrant purple 600 */
  --color-accent-light: #a78bfa;  /* soft purple 400 */
  --color-text: #1f1f23;          /* dark text */
}

html, body {
  background-color: var(--color-bg) !important;
  color: var(--color-text) !important;
  font-family: 'Inter', sans-serif;
}

/* Sidebar styling */
.sidebar {
  background-color: var(--color-surface-alt);
  border-right: 1px solid var(--color-accent-light);
}

/* Buttons and active nav */
button,
a,
.sidebar a.active {
  background-color: var(--color-accent);
  color: white;
  border-radius: 0.5rem;
  transition: background-color 0.25s ease;
}

button:hover,
a:hover,
.sidebar a:hover {
  background-color: var(--color-accent-light);
}

/* Card component styling */
.card {
  background-color: var(--color-surface);
  border: 1px solid #d8d8df;
  border-radius: 0.75rem;
  padding: 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
EOF
echo "✅ index.css theme applied with enforced light background."

# 3️⃣ Clean all Vite, Tailwind, and PostCSS caches
echo "🧹 Purging build caches..."
rm -rf frontend/node_modules/.vite frontend/.vite frontend/dist frontend/.cache 2>/dev/null || true
rm -rf frontend/postcss-cache frontend/.parcel-cache 2>/dev/null || true
echo "✅ All caches cleared."

# 4️⃣ Reinstall dependencies (optional safety)
if [ ! -d "frontend/node_modules" ]; then
  echo "📦 node_modules not found, reinstalling..."
  cd frontend
  npm install
  cd ..
  echo "✅ Dependencies reinstalled."
fi

# 5️⃣ Rebuild development server
echo "⚙️  Restarting development build..."
cd frontend
npm run dev &

echo "✨ THE13TH Light Grey + Purple Theme successfully applied!"
echo "🌐 Open your browser at http://localhost:5173 or http://localhost:5174"
echo "If it still appears dark, force-refresh (Ctrl+Shift+R) to flush browser cache."
