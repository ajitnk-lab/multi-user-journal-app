## Tasks

1. Customize infra/stack.py to match requirements
   - Update DynamoDB table definitions:
     - Create `users` table with partition key `username` (String)
     - Create `journal_entries` table with partition key `username` (String) and sort key `entry_id` (String)
   - Update Lambda function environment variables:
     - Set `USERS_TABLE_NAME` to reference users table name
     - Set `ENTRIES_TABLE_NAME` to reference journal_entries table name
     - Set `JWT_SECRET_PARAMETER` to SSM parameter name for JWT secret
   - Update API Gateway route definitions:
     - POST /auth/register → auth_handler
     - POST /auth/login → auth_handler
     - POST /entries → entries_handler
     - GET /entries → entries_handler
     - GET /entries/search → search_handler
   - Add SSM Parameter for JWT secret (SecureString)
   - Run `cdk synth` to verify changes compile

2. Implement auth_handler Lambda function (src/handlers/auth.py)
   - Install dependencies: `boto3`, `bcrypt`, `pyjwt`
   - Implement `/auth/register` endpoint:
     - Parse request body for username and password
     - Validate username format (3-20 chars, alphanumeric)
     - Validate password strength (min 8 chars)
     - Query users table to check if user count < 10
     - Check if username already exists
     - Hash password with bcrypt (12 salt rounds)
     - Store user record in DynamoDB with timestamp
     - Return success response or appropriate error
   - Implement `/auth/login` endpoint:
     - Parse request body for username and password
     - Query users table by username
     - Verify password hash with bcrypt
     - Retrieve JWT secret from SSM Parameter Store
     - Generate JWT token with username claim and 24h expiration
     - Return token in response
   - Add error handling for DynamoDB exceptions
   - Add input sanitization

3. Implement entries_handler Lambda function (src/handlers/entries.py)
   - Install dependencies: `boto3`, `pyjwt`, `ulid-py`
   - Create token verification helper function:
     - Extract token from Authorization header
     - Retrieve JWT secret from SSM Parameter Store
     - Verify token signature and expiration
     - Extract username from token claims
     - Return username or raise authentication error
   - Implement POST /entries endpoint:
     - Verify JWT token and get username
     - Parse request body for content
     - Validate content length (max 10,000 chars)
     - Generate ULID for entry_id
     - Create entry record with username, entry_id, content, timestamp
     - Store in journal_entries table
     - Return created entry
   - Implement GET /entries endpoint:
     - Verify JWT token and get username
     - Query journal_entries table by partition key (username)
     - Sort results by entry_id descending (ULID is time-sortable)
     - Return list of entries
   - Add error handling and input validation

4. Implement search_handler Lambda function (src/handlers/search.py)
   - Install dependencies: `boto3`, `pyjwt`
   - Reuse token verification helper (extract to shared utility)
   - Implement GET /entries/search endpoint:
     - Verify JWT token and get username
     - Extract query parameter 'q' from request
     - Validate query length (max 100 chars)
     - Query journal_entries table by partition key (username)
     - Filter results where content contains query string (case-insensitive)
     - Return matching entries sorted by timestamp
   - Optimize for small dataset (< 1000 entries per user)
   - Add error handling

5. Create shared utility module (src/utils/auth.py)
   - Implement `verify_token(token, secret)` function
   - Implement `get_jwt_secret()` function to retrieve from SSM
   - Implement error classes for authentication failures
   - Add unit tests for token verification logic

6. Update CDK stack to generate JWT secret on first deploy
   - Use CustomResource or AWS Lambda to generate random secret
   - Store in SSM Parameter Store as SecureString
   - Ensure secret is only generated once (check if exists first)
   - Grant Lambda functions read access to parameter

7. Add Lambda Layer for shared dependencies
   - Create requirements.txt with: bcrypt, pyjwt, ulid-py
   - Build Lambda layer with dependencies
   - Attach layer to all Lambda functions in CDK stack
   - Test layer compatibility with Python 3.11 runtime

8. Configure API Gateway CORS settings
   - Enable CORS on all routes
   - Set allowed origins (initially wildcard for testing)
   - Set allowed methods: GET, POST, OPTIONS
   - Set allowed headers: Content-Type, Authorization
   - Test preflight OPTIONS requests

9. Add input validation and error handling
   - Create validation functions for all inputs
   - Implement consistent error response format: `{"error": "message"}`
   - Add HTTP status codes: 200, 201, 400, 401, 403, 500
   - Log errors to CloudWatch with context
   - Sanitize error messages (no sensitive data leakage)

10. Implement user count tracking in registration
    - Create atomic counter in DynamoDB using conditional updates
    - Use separate item in users table with special key like `__metadata__`
    - Increment counter on successful registration
    - Return error if count >= 10 before creating new user
    - Add integration test to verify 10-user limit

11. Deploy and test authentication flow
    - Run `cdk deploy` to deploy stack
    - Capture API Gateway URL from outputs
    - Test user registration with curl/Postman:
      - Register user 1-10 successfully
      - Verify 11th registration fails
    - Test login with valid credentials
    - Test login with invalid credentials
    - Verify JWT token structure and expiration

12. Deploy and test journal entry operations
    - Test POST /entries with valid token:
      - Create multiple entries with different content
      - Verify entries stored in DynamoDB
    - Test POST /entries without token (expect 401)
    - Test GET /entries with valid token:
      - Verify only user's own entries returned
      - Verify entries sorted by time (newest first)
    - Test GET /entries for different users (verify isolation)

13. Deploy and test search functionality
    - Test GET /entries/search?q=keyword with valid token:
      - Create entries with known keywords
      - Search for keyword, verify matches returned
      - Search for non-existent keyword, verify empty results
    - Test case-insensitive search
    - Test search with special characters
    - Test search without token (expect 401)
    - Verify search only returns current user's entries

14. Performance and load testing
    - Test API response times with single user
    - Test concurrent requests from multiple users
    - Verify DynamoDB read/write capacity handling
    - Test with maximum content size (10,000 chars)
    - Monitor Lambda execution duration and memory usage
    - Verify cold start performance is acceptable

15. Security audit and hardening
    - Review IAM policies for least privilege
    - Verify JWT secret strength and storage
    - Test password hashing (attempt to crack with common tools)
    - Verify no cross-user data access possible
    - Test for SQL injection in search (should not affect DynamoDB)
    - Test for XSS in stored content (API responsibility vs frontend)
    - Scan dependencies for vulnerabilities

16. Create API documentation
    - Document all endpoints with request/response examples
    - Include authentication flow diagram
    - Provide curl examples for each endpoint
    - Document error codes and messages
    - Create Postman collection for testing
    - Add README with deployment instructions

17. Final deployment and URL delivery
    - Run final `cdk deploy` to production
    - Capture API Gateway public URL from CloudFormation outputs
    - Test all endpoints from external network
    - Verify HTTPS certificate
    - Create sample frontend HTML page (optional) to demonstrate usage
    - Deliver API URL and documentation to user