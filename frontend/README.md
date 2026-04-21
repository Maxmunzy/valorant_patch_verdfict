# Frontend

Next.js frontend for the Valorant Patch Verdict site.

## Commands

```bash
npm install
npm run typecheck
npm run build
npm run dev
```

## Environment

- `BACKEND_URL`: server-side API base, defaults to `http://localhost:8000`
- `NEXT_PUBLIC_API_BASE`: browser-side API base, defaults to `/api`

## Notes

- The layout avoids remote font fetching so builds work in restricted environments.
- This app uses ISR for the landing page and server-side fetches for prediction data.
