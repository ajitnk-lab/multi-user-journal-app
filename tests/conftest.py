import os
import sys

import boto3
import pytest
from moto import mock_aws

# Ensure src/ is on the path for handler imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Set environment variables before importing any handler code
os.environ["USERS_TABLE_NAME"] = "users"
os.environ["ENTRIES_TABLE_NAME"] = "journal_entries"
os.environ["JWT_SECRET_PARAMETER"] = "/journal/jwt-secret"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"

from tests.helpers import JWT_SECRET  # noqa: E402


@pytest.fixture(autouse=True)
def reset_jwt_cache():
    """Reset the JWT secret cache between tests."""
    import utils.auth as auth_utils
    auth_utils._jwt_secret_cache = None
    yield
    auth_utils._jwt_secret_cache = None


@pytest.fixture
def aws_mock():
    """Create a mocked AWS environment with DynamoDB tables and SSM parameter."""
    with mock_aws():
        # Create DynamoDB tables
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # Users table
        dynamodb.create_table(
            TableName="users",
            KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Journal entries table
        dynamodb.create_table(
            TableName="journal_entries",
            KeySchema=[
                {"AttributeName": "username", "KeyType": "HASH"},
                {"AttributeName": "entry_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "username", "AttributeType": "S"},
                {"AttributeName": "entry_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Create SSM parameter for JWT secret
        ssm = boto3.client("ssm", region_name="us-east-1")
        ssm.put_parameter(
            Name="/journal/jwt-secret",
            Value=JWT_SECRET,
            Type="SecureString",
        )

        yield {
            "dynamodb": dynamodb,
            "ssm": ssm,
            "users_table": dynamodb.Table("users"),
            "entries_table": dynamodb.Table("journal_entries"),
        }
