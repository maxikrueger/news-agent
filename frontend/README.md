# News Agent – Frontend

Next.js 16 dashboard (App Router, React 19, Tailwind CSS 4, NextAuth). See the
[project README](../README.md) for the full setup.

```bash
npm ci
cp .env.example .env.local    # NEXTAUTH_SECRET, NEXT_PUBLIC_API_URL
npm run dev                   # http://localhost:3000

npm run lint && npx tsc --noEmit && npm run build
```
