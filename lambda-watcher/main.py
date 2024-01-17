import boto3
from boto_session_manager import BotoSesManager

# function to scan lambda runtime in all region of an account


def scan_lambda_runtime():
    bsm = BotoSesManager()
    lambda_client = bsm.lambda_client
    response = lambda_client.list_functions()
    for function in response["Functions"]:
        print(function["Runtime"])
        print(function["FunctionArn"])
        print(function["FunctionName"])


scan_lambda_runtime()
