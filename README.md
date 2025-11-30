# Building a User Registration API

## Architecture

This project follows a **Layered Architecture (Domain Centric Develoment)** to ensure a clear separation of concerns, which makes the code
robust, testable and maintenable:

* **API/Presentation:** Handles HTTP requests and responses (FastAPI).
* **Service/Application:** Contains the orchestration logic.
* **Core/Domain:** Contains oure business rules (code expiration, user entities).
* **Infrastructure:** Handles technical details (PotsgreSQL Connection Pool, Email Mock).

## Prerequisites

* Docker and Docker Compose (v2.x)

## Getting started

### 1. Setup Var envs

Create a file named **`.env`** at the project root to securely store database credentials. **Do not omit this file.**

```bash
# .env file content example
DB_NAME=registration_db
DB_USER=myuser
DB_PAWWSORD=password
```

### 2. Launch the Application

the database (PgSQL) and the API service will be started automatically. The database schema will also created upon the first launch.

```bash
docker compose up --build -d
```

The API will be available at `http://localhost:8000``

### 3. Stop the containers

```bash
docker compose down
```

## Testing

To run the entire test suite inside the application containter : 

```bash
docker compose exec app pytest
```

