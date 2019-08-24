def enable_ebs_default_encryption(role: str, session: boto3.Session, account: str, region: str):
    """Enable default EBS encryption on all regions for all accounts found in input file.

    Arguments:
        role {str} -- [description]
        account_file {str} -- [description]

    """

    local_failure_list = []

    try:
        ec2_client = session.client('ec2')
        encryption_result = ec2_client.enable_ebs_encryption_by_default()
        if encryption_result is False:
            local_failure_list.append(f"{account}/{region}")
        else:
            LOG.info(
                f"EBS default encryption enabled on {account}/{region}")
    except ClientError as error:
        LOG.error(
            f"Error during EBS default encryption setting activation: {error}")

    return local_failure_list
