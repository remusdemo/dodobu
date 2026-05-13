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

## Setup (one time)
# 1. Push repo to GitHub
# 2. Create Railway project from GitHub repo
# 3. Add PostgreSQL service in Railway UI
# 4. Railway injects DATABASE_URL automatically
# 5. Set env vars in Railway:
#    - APP_BASE_URL (your Railway domain)
#    - RESEND_API_KEY

## Run migrations against production
# Liquibase connects through Railway's tunnel — no public DB needed.
# It reads databasechangelog on prod and only runs pending changesets.
railway run -- \
  docker run --rm \
    -v ./db/changelog:/liquibase/changelog \
    -v ./db/liquibase-lib:/liquibase/lib \
    liquibase/liquibase \
    --driver=org.postgresql.Driver \
    --classpath=/liquibase/lib/postgresql.jar \
    --url="jdbc:postgresql://${PGHOST}:${PGPORT:-5432}/${PGDATABASE}" \
    --searchPath=/liquibase/changelog \
    --changeLogFile=master.xml \
    --username="${PGUSER}" \
    --password="${PGPASSWORD}" \
    update
