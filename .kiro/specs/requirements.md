## Functional Requirements

### User Authentication
- Users must be able to register with a unique username and password
- Users must be able to login with their credentials
- Maximum 10 users can register
- Each user can only access their own journal entries

### Journal Entry Management
- Authenticated users can create new journal entries via text input
- Journal entries are stored with timestamp and user association
- Users can view their own journal entries

### Search Functionality
- Users can search their own journal entries using text-based queries
- Search should match against entry content
- Search results display only entries belonging to the authenticated user

## Non-Functional Requirements

### Performance
- API response time should be under 2 seconds for typical operations
- Search operations should complete within 3 seconds

### Security
- Passwords must be securely hashed before storage
- User sessions must be authenticated via tokens
- Users cannot access other users' data
- API endpoints must validate authentication tokens

### Scalability
- System designed to support exactly 10 concurrent users
- DynamoDB tables configured for low-cost, small-scale usage

### Availability
- Serverless architecture for high availability
- No single point of failure

## Constraints

### Technical Constraints
- Must be deployed on AWS using serverless services
- Must provide an external-facing URL for API access
- Must use AWS CDK for infrastructure as code
- Maximum 10 user accounts enforced at registration

### Budget Constraints
- Optimize for AWS Free Tier where possible
- Use on-demand DynamoDB billing
- Minimize Lambda execution time and memory

### Time Constraints
- Solution must be deployable in a single CDK stack
- No complex migration or multi-stage deployment required