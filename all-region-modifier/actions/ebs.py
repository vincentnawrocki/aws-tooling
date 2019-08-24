"""This module regroups actions relative to EBS resource."""
import boto3
from botocore.exceptions import ClientError
from logger.logger import LOG

def enable_ebs_default_encryption(session: boto3.Session)->[]:
    """Enable default EBS encryption.

    Arguments:
        session {boto3.Session} -- [description]

    Returns:
        [str] -- The list of error string encountered during action to be displayed at the end of overall process. Empty if no error.

    """
    local_failure_list = []
    account = session.get_caller_identity()["Account"]
    region = session.region_name

    try:
        ec2_client = session.client('ec2')
        encryption_result = ec2_client.enable_ebs_encryption_by_default()
        if encryption_result is False:
            local_failure_list.append(f"{account}/{region}")
        else:
            LOG.info(f"EBS default encryption enabled on {account}/{region}")
    except ClientError as error:
        LOG.error(f"Error during EBS default encryption setting activation: {error}")

    return local_failure_list
