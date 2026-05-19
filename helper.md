# docker compose

## reset
podman compose down -v

## hard reset
podman system prune -a -f

## start pgsql
podman compose up -d db

## liquibase
podman compose run --rm liquibase

## connect to db
podman exec -it dodobu-db-1 psql -U postgres -d dodobu

## start everything (production build)
podman compose up --build web

# Dev workflow (3 terminals)

## Terminal 1 — database
podman compose up -d db
podman compose run --rm liquibase

## Terminal 2 — Flask API (hot-reload)
cd backend && DB_HOST=localhost flask --app backend.app run --debug -p 5000

## Terminal 3 — React dev server (HMR)
cd frontend && npm run dev

Then visit http://localhost:5173 (not port 5000).
The Vite dev server proxies /api/* to Flask on port 5000.

# start over sequence
podman compose down -v
podman compose up -d db
podman compose run --rm liquibase
podman compose up --build web

# increment sequence
podman compose up -d db
podman compose run --rm liquibase
podman compose up --build web

# Worker (process pending reminders)
podman compose up --build -d web && podman compose exec web python worker.py



## Railway cron (prod)
# Railway dashboard → Cron Jobs → Add:
#   command: python worker.py
#   schedule: */5 * * * *

# Railway production deploy

railway login

1. Run migration if DB changed

railway_liquibase.sh

2. Deploy to Railway
railway up -s dodobu

3. Quick sanity check
  curl -sS --connect-timeout 5 --max-time 10 https://memobud.com/api/version


# Railway recipes

## deploy service
railway up -s worker-cron

## service vars
railway vars -s worker-cron

## add new var
railway variable set DATABASE_URL='${{Postgres.DATABASE_URL}}' -s worker-cron
railway variable set SERVICE_ROLE=worker -s worker-cron

## service logs
railway logs -s worker-cron --previous --tail 50