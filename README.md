# Multi-User Journal App

A serverless journal application supporting up to 10 public users with individual accounts. Users can register with username/password, create journal entries via text input, and search their own entries.

## Architecture

The application is built on AWS serverless services:

- **API Gateway** (REST API) - HTTP endpoint with CORS support
- **AWS Lambda** (Python 3.11) - Three handler functions for authentication, entries, and search
- **Amazon DynamoDB** - Two tables for users and journal entries (on-demand billing)
- **AWS SSM Parameter Store** - Stores the JWT signing secret
- **Frontend** - Single-page HTML/JS application (static hosting)

### Components

```
frontend/index.html    -> Static SPA (login, register, write, list, search)
src/handlers/auth.py   -> POST /auth/register, POST /auth/login
src/handlers/entries.py -> POST /entries, GET /entries
src/handlers/search.py -> GET /entries/search
infra/                 -> AWS CDK v2 infrastructure code
```

## API Endpoints

All endpoints return JSON. Protected endpoints require an `Authorization: Bearer <token>` header.

### Authentication

| Method | Path             | Description              | Auth Required |
|--------|------------------|--------------------------|---------------|
| POST   | /auth/register   | Register a new user      | No            |
| POST   | /auth/login      | Login and receive JWT    | No            |

**POST /auth/register**
```json
Request:  { "username": "myuser", "password": "mypassword" }
Response: { "message": "User registered successfully" }
```

**POST /auth/login**
```json
Request:  { "username": "myuser", "password": "mypassword" }
Response: { "token": "eyJhbGciOiJIUzI1NiIs..." }
```

### Journal Entries

| Method | Path             | Description                        | Auth Required |
|--------|------------------|------------------------------------|---------------|
| POST   | /entries         | Create a new journal entry         | Yes           |
| GET    | /entries         | List all entries (newest first)    | Yes           |
| GET    | /entries/search  | Search entries by content          | Yes           |

**POST /entries**
```json
Request:  { "content": "Today I learned about serverless..." }
Response: { "entry_id": "01H...", "content": "...", "created_at": 1234567890 }
```

**GET /entries**
```json
Response: { "entries": [{ "entry_id": "...", "content": "...", "created_at": ... }] }
```

**GET /entries/search?q=serverless**
```json
Response: { "entries": [{ "entry_id": "...", "content": "...", "created_at": ... }] }
```

## Deployment

### Prerequisites

- AWS CLI configured with appropriate credentials
- Node.js (for AWS CDK CLI)
- Python 3.11

### Steps

1. Install CDK dependencies:
   ```bash
   cd infra
   pip install -r requirements.txt
   ```

2. Install Lambda dependencies (for bundling):
   ```bash
   pip install -r src/requirements.txt -t src/
   ```

3. Bootstrap CDK (first time only):
   ```bash
   cd infra
   npx cdk bootstrap
   ```

4. Deploy the stack:
   ```bash
   cd infra
   npx cdk deploy
   ```

5. After deployment, the API URL will be output. Update `frontend/index.html` by setting the API URL in localStorage or modifying the `API_BASE_URL` constant.

6. Host the `frontend/index.html` file (e.g., via S3 static website hosting, CloudFront, or open locally).

### Configuration

- **JWT Secret**: Automatically generated and stored in SSM Parameter Store at `/journal-app/jwt-secret`
- **Max Users**: Hard-coded limit of 10 users enforced in the registration handler
- **Token Expiry**: JWT tokens expire after 24 hours

## Design Decisions

- **Custom JWT Auth**: Uses custom JWT authentication instead of Cognito for simplicity and cost efficiency
- **bcrypt**: Password hashing with 12 salt rounds
- **ULID**: Entry IDs use ULIDs for time-sortable unique identifiers
- **On-demand DynamoDB**: Pay-per-request billing to minimize costs for low-traffic usage
- **Single code asset**: All Lambda functions share the same code bundle from `src/` with different handler entry points

## Local Development

Run CDK synth to validate infrastructure changes:
```bash
cd infra
pip install -r requirements.txt
npx cdk synth
```

Run unit tests:
```bash
python -m pytest tests/ -v
```
