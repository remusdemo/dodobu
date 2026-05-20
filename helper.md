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


# Droplet recipes

## Connect to DB

# reset pwd
docker exec -it fb70ca33d7ec psql -U postgres -d postgres
ALTER USER postgres WITH PASSWORD 'new_password';
docker restart fb70ca33d7ec

Test withing db-container : PGPASSWORD="new_password" psql -h 127.0.0.1 -U postgres -d postgres -c "select 1;"
## liquibase

liquibase --url="$DATABASE_URL" --changeLogFile=db/changelog/master.xml update

## verify container hosts
docker exec -it 1887b24308b2 sh -c "getent hosts postgres"
fd51:73bc:2441::2 postgres