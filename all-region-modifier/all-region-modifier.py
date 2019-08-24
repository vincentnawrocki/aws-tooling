"""Module to apply a change on multiple regions for multiple AWS accounts."""

import json
import boto3
from botocore.exceptions import ClientError
import tqdm
from actions.ebs import enable_ebs_default_encryption
from logger.logger import LOG

def all_region_modifier(role: str, account_file: str, action):
    """all_region_modifier [summary]

    Arguments:
        role {str} -- [description]
        account_file {str} -- [description]
        action {[type]} -- [description]

    Returns:
        [type] -- [description]

    """
    sts_client = boto3.client('sts')
    failure_list = []

    with open(account_file) as file:
        account_list = json.load(file)

    LOG.info(
        f"Default ebs encryption will be activated on all regions for the list of account(s): {account_list['accounts']}")

    for account in tqdm.tqdm(account_list['accounts'], desc="Accounts"):
        role_arn = f"arn:aws:iam::{account}:role/{role}"

        try:
            assume_role = sts_client.assume_role(
                RoleArn=role_arn, RoleSessionName="get_all_regions", DurationSeconds=3600)
            session = boto3.Session(
                aws_access_key_id=assume_role['Credentials']['AccessKeyId'],
                aws_secret_access_key=assume_role['Credentials']['SecretAccessKey'],
                aws_session_token=assume_role['Credentials']['SessionToken'],
                region_name="us-east-1"
            )
        except ClientError as error:
            LOG.error(
                f"Failed to assume role during regions retrieval {role_arn} : {error}")

        try:
            ec2_client = session.client('ec2', region_name='us-east-1')
            aws_regions = [region['RegionName']
                           for region in ec2_client.describe_regions()['Regions']]
            LOG.info(f"Regions retrived using role {role_arn} : {aws_regions}")
        except ClientError as error:
            LOG.error(f"Failed to get regions : {error}")

        for region in tqdm.tqdm(aws_regions, desc="Regions"):
            try:
                assume_role = sts_client.assume_role(
                    RoleArn=role_arn, RoleSessionName=f"enable_ebs_encryption_{region}")
                session = boto3.Session(
                    aws_access_key_id=assume_role['Credentials']['AccessKeyId'],
                    aws_secret_access_key=assume_role['Credentials']['SecretAccessKey'],
                    aws_session_token=assume_role['Credentials']['SessionToken'],
                    region_name='us-east-1'
                )
            except ClientError as error:
                LOG.error(f"Failed to assume role {role_arn} : {error}")

            failure_list += action(session=session)

    # Print error list
    if failure_list:
        LOG.error(f"Failures encountered applying change on account/region: {failure_list}")
    else:
        LOG.info("No error during the process")


all_region_modifier(role="ebs_default_encryptioner", account_file="accounts.json", action=enable_ebs_default_encryption)
