# Telecom API

This project provides a FastAPI-based API for routing and number management, with CI/CD configured for GitLab and Docker-based deployment.

## Features

- FastAPI backend
- PostgreSQL database support
- JWT-based authentication
- Prometheus metrics
- Docker Compose for local development
- GitLab CI/CD for automated build, test, and deploy

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.10+
- PostgreSQL
- Redis

### Local Development

1. **Clone the repository:**
   ```sh
   git clone <your-repo-url>
   cd RouteAPI
   ```

2. **Configure environment variables:**
   - Copy `.env.example` to `.env` and edit as needed, or set variables in your environment.

3. **Start services with Docker Compose:**
   ```sh
   docker compose -f docker/postgres-docker-compose.yml up -d
   ```

4. **Run the API:**
   ```sh
   uvicorn main:app --reload
   ```

### Running Tests

```sh
docker run --rm routeapi-image pytest -s -v
```

### Prometheus Metrics

- The `/metrics` endpoint is protected and only accessible from allowed networks (see `src/utils/observability.py`).

## CI/CD

- The `.gitlab-ci.yml` file defines separate jobs for `dev` and `main` branches, using different runners and environment variables.
- Secrets and sensitive variables should be stored in GitLab CI/CD variables, not in the repository.

## Branching

- `main`: Production-ready code.
- `dev`: Development and testing.

## Useful Commands

- **Restart PostgreSQL in Docker:**
  ```sh
  docker compose restart postgres
  ```
- **Delete a branch in GitLab via terminal:**
  ```sh
  git push origin --delete branch-name
  ```

## License

MIT License

---

**Note:**  
Do not commit sensitive information (like real passwords or secret keys) to the repository. Use environment variables or GitLab CI/CD variables for secrets.
