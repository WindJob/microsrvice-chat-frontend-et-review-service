# Messaging Service

This is a simple messaging microservice (FastAPI) used in the 015 workspace.

It exposes REST endpoints for conversations and messages and a native WebSocket endpoint for realtime delivery.

## Démarrage local simple

Si tu n'as pas PostgreSQL en local, utilise SQLite. Le service crée les tables automatiquement au démarrage.

```powershell
Set-Item -Path Env:DATABASE_URL -Value "sqlite:///./dev_messaging.db"
Set-Item -Path Env:JWT_SECRET_KEY -Value "dev-secret"
& .\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8011
```

Oui, dans ce cas tu peux lancer seulement `uvicorn main:app --reload --host 0.0.0.0 --port 8011` **après** avoir défini les variables d'environnement si tu veux contrôler le mode de stockage.

## PostgreSQL en option

Si tu veux le mode proche production, définis `DATABASE_URL` vers PostgreSQL :

```text
postgresql://postgres:postgres@localhost:5432/platform_db
```

Le code garde ce support, mais il n'est pas obligatoire en local.

## Variables d'environnement

- `DATABASE_URL` - URL de base de données (SQLite local ou PostgreSQL)
- `JWT_SECRET_KEY` - secret pour valider les JWT
- `JWT_ALGORITHM` - algorithme JWT, par défaut `HS256`

## Ce que fait le démarrage

- l'engine SQLAlchemy est créé à la demande
- les tables sont créées automatiquement via `create_db()` au startup FastAPI
- le WebSocket `/ws/notifications` diffuse les événements `message_created`

