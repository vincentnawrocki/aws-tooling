"""Module to apply a change on multiple regions for multiple AWS accounts."""

import json
import logging
import boto3
from botocore.exceptions import ClientError
import tqdm

class TqdmLoggingHandler(logging.Handler):
    """Special class to handle logging using tqdm progress bar.

    Arguments:
        logging {[type]} -- [description]

    """

    def emit(self, record):
        """Actually manages logs.

        Arguments:
            record {str} -- Record to print

        """
        try:
            msg = self.format(record)
            tqdm.tqdm.write(msg)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


def enable_ebs_default_encryption(role: str, account_file: str):
    """Enable default EBS encryption on all regions for all accounts found in input file.

    Arguments:
        role {str} -- [description]
        account_file {str} -- [description]

    """
    log = logging.getLogger(__name__)
    log.setLevel(logging.INFO)
    log.addHandler(TqdmLoggingHandler())

    sts_client = boto3.client('sts')
    failure_list = []

    with open(account_file) as file:
        account_list = json.load(file)

    log.info(
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
            log.error(
                f"Failed to assume role during regions retrieval {role_arn} : {error}")

        try:
            ec2_client = session.client('ec2', region_name='us-east-1')
            aws_regions = [region['RegionName']
                           for region in ec2_client.describe_regions()['Regions']]
            log.info(f"Regions retrived using role {role_arn} : {aws_regions}")
        except ClientError as error:
            log.error(f"Failed to get regions : {error}")

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
                log.error(f"Failed to assume role {role_arn} : {error}")

            try:
                ec2_client = session.client('ec2')
                encryption_result = ec2_client.enable_ebs_encryption_by_default()
                if encryption_result is False:
                    failure_list.append(f"{account}/{region}")
                else:
                    log.info(
                        f"EBS default encryption enabled on {account}/{region}")
            except ClientError as error:
                log.error(
                    f"Error during EBS default encryption setting activation: {error}")

    # Print error list
    if failure_list:
        log.error(
            f"Activation of EBS default encryption failed on account/region: {failure_list}")
    else:
        log.info("No error during the process")


enable_ebs_default_encryption(
    role="ebs_default_encryptioner", account_file="accounts.json")
