#!/bin/bash
# === THE13TH Grey & Purple Theme Updater ===
# Applies minimalist grey + purple theme to the frontend

set -e
echo "🎨 Applying THE13TH grey–purple theme..."

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

# 2️⃣ Create or update index.css with color scheme
cat > frontend/src/index.css <<'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --color-bg: #1a1a1d; /* deep grey */
  --color-surface: #242429; /* slightly lighter grey */
  --color-accent: #8b5cf6; /* purple 500 */
  --color-accent-light: #a78bfa; /* purple 400 */
  --color-text: #e4e4e7; /* light grey text */
}

body {
  background-color: var(--color-bg);
  color: var(--color-text);
}

.sidebar {
  background-color: var(--color-surface);
  border-right: 1px solid var(--color-accent-light);
}

button,
a,
.sidebar a.active {
  background-color: var(--color-accent);
  color: white;
  border-radius: 0.5rem;
  transition: background-color 0.3s ease;
}

button:hover,
a:hover,
.sidebar a:hover {
  background-color: var(--color-accent-light);
}
EOF
echo "✅ index.css theme applied."

# 3️⃣ Clear Tailwind cache to ensure full rebuild
echo "🧹 Clearing Tailwind cache..."
rm -rf frontend/.vite frontend/node_modules/.vite

# 4️⃣ Done
echo "✨ Grey–Purple theme applied successfully!"
echo "Now run: cd frontend && npm run dev"
