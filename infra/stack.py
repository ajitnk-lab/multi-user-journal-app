"""CDK Stack for the Multi-User Journal Application."""

import secrets
import os

from aws_cdk import (
    Stack,
    CfnOutput,
    RemovalPolicy,
    Duration,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_ssm as ssm,
    aws_apigateway as apigw,
)
from constructs import Construct


class JournalAppStack(Stack):
    """Main stack defining all resources for the journal application."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # DynamoDB Tables
        users_table = dynamodb.Table(
            self,
            "UsersTable",
            table_name="journal_users",
            partition_key=dynamodb.Attribute(
                name="username", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        entries_table = dynamodb.Table(
            self,
            "EntriesTable",
            table_name="journal_entries",
            partition_key=dynamodb.Attribute(
                name="username", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="entry_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # SSM Parameter for JWT Secret
        jwt_secret_parameter = ssm.StringParameter(
            self,
            "JwtSecretParameter",
            parameter_name="/journal-app/jwt-secret",
            string_value=secrets.token_hex(32),
            description="JWT signing secret for the journal application",
        )

        # Lambda code path (relative to infra/)
        lambda_code_path = os.path.join(os.path.dirname(__file__), "..", "src")

        # Common environment variables for all Lambda functions
        common_env = {
            "USERS_TABLE_NAME": users_table.table_name,
            "ENTRIES_TABLE_NAME": entries_table.table_name,
            "JWT_SECRET_PARAMETER": jwt_secret_parameter.parameter_name,
        }

        # Lambda Functions
        auth_handler = _lambda.Function(
            self,
            "AuthHandler",
            function_name="journal-auth-handler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handlers.auth.handler",
            code=_lambda.Code.from_asset(lambda_code_path),
            environment=common_env,
            timeout=Duration.seconds(30),
            memory_size=256,
        )

        entries_handler = _lambda.Function(
            self,
            "EntriesHandler",
            function_name="journal-entries-handler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handlers.entries.handler",
            code=_lambda.Code.from_asset(lambda_code_path),
            environment=common_env,
            timeout=Duration.seconds(30),
            memory_size=256,
        )

        search_handler = _lambda.Function(
            self,
            "SearchHandler",
            function_name="journal-search-handler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handlers.search.handler",
            code=_lambda.Code.from_asset(lambda_code_path),
            environment=common_env,
            timeout=Duration.seconds(30),
            memory_size=256,
        )

        # IAM Permissions - DynamoDB
        users_table.grant_read_write_data(auth_handler)
        entries_table.grant_read_write_data(entries_handler)
        entries_table.grant_read_data(search_handler)

        # IAM Permissions - SSM Parameter (all functions need JWT secret)
        jwt_secret_parameter.grant_read(auth_handler)
        jwt_secret_parameter.grant_read(entries_handler)
        jwt_secret_parameter.grant_read(search_handler)

        # API Gateway REST API with CORS
        api = apigw.RestApi(
            self,
            "JournalApi",
            rest_api_name="Journal API",
            description="Multi-user journal application API",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "POST", "OPTIONS"],
                allow_headers=["Content-Type", "Authorization"],
            ),
        )

        # Lambda integrations
        auth_integration = apigw.LambdaIntegration(auth_handler)
        entries_integration = apigw.LambdaIntegration(entries_handler)
        search_integration = apigw.LambdaIntegration(search_handler)

        # API Routes
        # /auth
        auth_resource = api.root.add_resource("auth")
        # /auth/register
        register_resource = auth_resource.add_resource("register")
        register_resource.add_method("POST", auth_integration)
        # /auth/login
        login_resource = auth_resource.add_resource("login")
        login_resource.add_method("POST", auth_integration)

        # /entries
        entries_resource = api.root.add_resource("entries")
        entries_resource.add_method("POST", entries_integration)
        entries_resource.add_method("GET", entries_integration)

        # /entries/search
        search_resource = entries_resource.add_resource("search")
        search_resource.add_method("GET", search_integration)

        # Output the API URL
        CfnOutput(
            self,
            "ApiUrl",
            value=api.url,
            description="URL of the Journal API",
        )
