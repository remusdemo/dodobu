  podman compose down -v
  podman compose up -d db
  podman compose run --rm liquibase
  podman compose up --build web
  