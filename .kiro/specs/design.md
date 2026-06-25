## Architecture Overview

This is a serverless REST API backend built on AWS Lambda, API Gateway, and DynamoDB. The application uses a token-based authentication system where users register and login to receive JWT tokens. All subsequent API calls include this token for authorization.

### Components
1. **API Gateway (HTTP API)**: Provides external-facing HTTPS endpoint
2. **Lambda Functions**: Handle business logic for auth, entries, and search
3. **DynamoDB Tables**: 
   - `users` table: Stores user credentials (hashed passwords) and metadata
   - `journal_entries` table: Stores journal entries with user ownership
4. **Cognito (not used)**: Using custom JWT-based auth to keep solution simple

## AWS Services Used

### Amazon API Gateway (HTTP API)
- Provides RESTful API endpoints
- Routes requests to appropriate Lambda functions
- Handles CORS for browser access
- Returns public URL for external access

### AWS Lambda (Python 3.11)
- **auth_handler**: Manages user registration, login, token generation
- **entries_handler**: Creates and retrieves journal entries for authenticated users
- **search_handler**: Searches journal entries with text queries

### Amazon DynamoDB
- **users table**:
  - Partition Key: `username` (String)
  - Attributes: `password_hash`, `created_at`, `user_count`
  - Provisioned capacity: On-demand
  
- **journal_entries table**:
  - Partition Key: `username` (String)
  - Sort Key: `entry_id` (String, ULID format for time-ordered IDs)
  - Attributes: `content`, `created_at`
  - GSI: Not required for basic query patterns
  - Provisioned capacity: On-demand

### AWS Systems Manager Parameter Store
- Stores JWT secret for token signing/verification
- Accessed by Lambda functions at runtime

## Data Flow

### User Registration Flow
1. Client POST `/auth/register` with `{username, password}`
2. API Gateway routes to `auth_handler` Lambda
3. Lambda checks current user count in DynamoDB
4. If count < 10, hash password with bcrypt, store in `users` table
5. Increment user count tracker
6. Return success response

### User Login Flow
1. Client POST `/auth/login` with `{username, password}`
2. API Gateway routes to `auth_handler` Lambda
3. Lambda retrieves user from `users` table
4. Verify password hash with bcrypt
5. Generate JWT token with username claim, sign with secret from Parameter Store
6. Return `{token}` to client

### Create Entry Flow
1. Client POST `/entries` with `{content}` and Authorization header with JWT token
2. API Gateway routes to `entries_handler` Lambda
3. Lambda verifies JWT token and extracts username
4. Generate ULID for entry_id (time-sortable)
5. Store entry in `journal_entries` table with partition key=username
6. Return created entry with timestamp

### List Entries Flow
1. Client GET `/entries` with Authorization header
2. Lambda verifies token, extracts username
3. Query `journal_entries` table by partition key (username)
4. Return list of entries sorted by timestamp (descending)

### Search Entries Flow
1. Client GET `/entries/search?q=query` with Authorization header
2. Lambda verifies token, extracts username
3. Scan `journal_entries` table filtered by username
4. Apply text search filter on content attribute (case-insensitive substring match)
5. Return matching entries

## Security

### Authentication & Authorization
- Custom JWT-based authentication (HS256 algorithm)
- JWT secret stored in AWS Systems Manager Parameter Store (SecureString)
- All entry and search endpoints require valid JWT token
- Token includes username claim for user identification
- Token expiration set to 24 hours

### Password Security
- Passwords hashed using bcrypt with salt rounds=12
- Plain-text passwords never stored
- Password hashing performed in Lambda layer with bcrypt library

### Data Isolation
- DynamoDB queries filtered by username (partition key)
- Lambda functions validate token before any data access
- No cross-user data leakage possible through API

### Network Security
- API Gateway uses HTTPS only
- CORS configured to allow browser access (with appropriate origins)
- Lambda functions run in AWS managed VPC (no custom VPC required for this scale)

### IAM Permissions
- Lambda execution role has least-privilege permissions:
  - Read/Write access only to specific DynamoDB tables
  - Read access to JWT secret in Parameter Store
  - CloudWatch Logs write permissions

### Input Validation
- Username: 3-20 characters, alphanumeric only
- Password: Minimum 8 characters
- Entry content: Maximum 10,000 characters
- Search query: Maximum 100 characters
- All inputs sanitized to prevent injection attacks