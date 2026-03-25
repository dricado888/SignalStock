# SignalStock Database Migrations

## Strategy

This project uses **sequential numbered SQL files** for migrations. Each file is a standalone SQL script that can be applied in order.

### Naming Convention

```
NNN_description.sql
```

- `NNN` - Zero-padded sequence number (001, 002, ...)
- `description` - Short snake_case description of the change

### Applying Migrations

Migrations run against the database in order:

```bash
# Apply a specific migration
docker exec -i signalstock-db psql -U signalstock -d signalstock < db/migrations/001_initial_schema.sql

# Apply all migrations in order (bash)
for f in db/migrations/*.sql; do
  echo "Applying $f..."
  docker exec -i signalstock-db psql -U signalstock -d signalstock < "$f"
done
```

### Creating a New Migration

1. Copy the next sequence number
2. Write idempotent SQL where possible (use `IF NOT EXISTS`, `IF EXISTS`)
3. Wrap in a transaction (`BEGIN; ... COMMIT;`)
4. Test against a fresh database and against one with existing data

### Notes

- `001_initial_schema.sql` matches `db/init.sql` — the init script runs automatically via docker-compose on first start
- For production, consider a migration tool like [golang-migrate](https://github.com/golang-migrate/migrate) or [Flyway](https://flywaydb.org/)
