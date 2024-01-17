import boto3
from botocore.exceptions import ClientError
import json
from datetime import datetime, timedelta, date
from dateutil import parser as dateParser
import typing
import time
import pprint

# boto3 clients used
iam_client = boto3.client("iam")
dynamo_client = boto3.client("dynamodb")
ses_client = boto3.client("ses")

# custom log stream
logs = boto3.client("logs")
try:
    logs.create_log_group(logGroupName="disable-inactive-unused-iam")
    logs.create_log_stream(logGroupName="disable-inactive-unused-iam", logStreamName="user")
    logs.create_log_stream(logGroupName="disable-inactive-unused-iam", logStreamName="key")
except Exception as e:
    print(f"Ignoring the exception: {e}")

# limits' settings - duration in days
MAX_AKSK_AGE: int = 90
MAX_PASSWORD_AGE: int = 90
GRACE_PERIOD: int = 7
REMINDER_SCHEDULE: list[int] = [28, 21, 14, 7, 6, 5, 4, 3, 2, 1, 0]

# Various variables
SENDER_EMAIL = "iam.watcher@nawrocki.cc"


class User(typing.NamedTuple):
    """Represents an AWS IAM user with its attributes from credential report
    """
    user: str
    arn: str
    user_creation_time: str
    password_enabled: str
    password_last_used: str
    password_last_changed: str
    password_next_rotation: str
    mfa_active: str
    access_key_1_active: str
    access_key_1_last_rotated: str
    access_key_1_last_used_date: str
    access_key_1_last_used_region: str
    access_key_1_last_used_service: str
    access_key_2_active: str
    access_key_2_last_rotated: str
    access_key_2_last_used_date: str
    access_key_2_last_used_region: str
    access_key_2_last_used_service: str
    cert_1_active: str
    cert_1_last_rotated: str
    cert_2_active: str
    cert_2_last_rotated: str


def get_users_credential_report() -> list:
    generate_report_response = iam_client.generate_credential_report()

    while generate_report_response["State"] != "COMPLETE":
        time.sleep(2)

    # format report to readable
    response: typing.Dict[str, typing.Any] = iam_client.get_credential_report()
    body: str = response["Content"].decode("utf-8")
    lines = body.split("\n")
    users = [User(*line.split(",")) for line in lines[1:]]

    return users


# def lambda_handler(event: typing.Dict[str, typing.Any], context):
def lambda_handler():
    users = get_users_credential_report()

    today = datetime.now()

    # console user
    never_logged_in_user: list[typing.Dict[str, str]] = []
    inactive_past_90_days_user: list[typing.Dict[str, str | int]] = []
    # access key user
    never_used_key: list[typing.Dict[str, str]] = []
    inactive_past_90_days_key: list[typing.Dict[str, str | int]] = []

    for user in users:
        # user has access privilege to web aws console
        if user.password_enabled == "true":

            # user used their password at least one time
            if (user.password_last_used != "N/A" and user.password_last_used != "no_information"):

                # convert string to datetime
                temp_user_password_last_used = dateParser.parse(user.password_last_used)
                delta: int = (today - temp_user_password_last_used.replace(tzinfo=None)).days

                # check if user dont logged in for the past 90 days
                if delta >= 90:
                    inactive_past_90_days_user.append({"username": user.user, "inactivity_time": delta})

            # user never used password (never made login)
            else:
                never_logged_in_user.append({"username": user.user})

        #########################
        # user has only api keys
        else:
            # check if access key 1 is active
            if user.access_key_1_active == "true":

                # user used this key at least one time
                try:
                    # convert string to datetime
                    temp_user_password_last_used = dateParser.parse(user.access_key_1_last_used_date)
                    delta = (today - temp_user_password_last_used.replace(tzinfo=None)).days

                    # check if user dont logged in for the past 90 days
                    if delta >= 90:
                        inactive_past_90_days_key.append(
                            {
                                "username": user.user,
                                "key": "1",
                                "inactivity_time": delta,
                            }
                        )

                except:
                    never_used_key.append({"username": user.user, "key": "1"})

            # check if access key 1 is active
            if user.access_key_2_active == "true":

                # user used this key at least one time
                try:
                    # convert string to datetime
                    temp_user_password_last_used = dateParser.parse(user.access_key_2_last_used_date)
                    delta = (today - temp_user_password_last_used.replace(tzinfo=None)).days

                    # check if user dont logged in for the past 90 days
                    if delta >= 90:
                        inactive_past_90_days_key.append(
                            {
                                "username": user.user,
                                "key": "2",
                                "inactivity_time": delta,
                            }
                        )

                except:
                    never_used_key.append({"username": user.user, "key": "2"})

    # Log to lambda cloudwatch operational info
    pprint.pprint(f"inactive_past_90_days_user\n{inactive_past_90_days_user}")
    pprint.pprint(f"never_logged_in_user\n{never_logged_in_user}")
    pprint.pprint(f"inactive_past_90_days_key\n{inactive_past_90_days_key}")
    pprint.pprint(f"never_used_key\n{never_used_key}")

    # for user in inactive_past_90_days_user:
    #     str_aux = str(user["username"]) + "\t" + "disable_console_access"
    #     str_aux += "\t" + str(user["inactivity_time"]) + "\tdays_inactive"
    #     try:
    #         # remove the login_profile/password/ability to use the Console
    #         iam_client.delete_login_profile(UserName=user["username"])
    #         str_aux = "SUCCESS\t" + str_aux
    #         create_log_cloudwatch(str_aux, "user")
    #     except ClientError as e:
    #         # error to remove ability to use console
    #         str_aux = "ERROR\t" + str_aux
    #         create_log_cloudwatch(str_aux, "user")
    #         print(e)

    # for user in never_logged_in_user:
    #     str_aux = str(user["username"]) + "\t" + "disable_console_access"
    #     try:
    #         # remove the login_profile/password/ability to use the Console
    #         iam_client.delete_login_profile(UserName=user["username"])
    #         str_aux = "SUCCESS\t" + str_aux
    #         create_log_cloudwatch(str_aux, "user")
    #     except Exception as e:
    #         # error to remove ability to use console
    #         str_aux = "ERROR\t" + str_aux
    #         create_log_cloudwatch(str_aux, "user")
    #         print(e)

    # # Delete unused access keys
    # timeLimit = datetime.now() - timedelta(days=int(90))
    # concat_list_key = inactive_past_90_days_key + never_used_key
    # for user in concat_list_key:
    #     try:
    #         accessKeys = iam_client.list_access_keys(UserName=user["username"])

    #         for key in accessKeys["AccessKeyMetadata"]:
    #             if key["CreateDate"].date() <= timeLimit.date():

    #                 str_aux = (
    #                     str(user["username"])
    #                     + "\tdisable_access_key\t"
    #                     + str(key["AccessKeyId"])
    #                     + "\t"
    #                     + str((date.today() - key["CreateDate"].date()).days)
    #                     + "\t"
    #                     + str("key_age")
    #                 )
    #                 if "inactivity_time" in user:
    #                     str_aux += (
    #                         "\t" + str(user["inactivity_time"]
    #                                    ) + "\tdays_inactive"
    #                     )

    #                 try:
    #                     response = iam_client.delete_access_key(
    #                         AccessKeyId=key["AccessKeyId"],
    #                         UserName=user["username"],
    #                     )
    #                     str_aux = "SUCCESS\t" + str_aux
    #                     create_log_cloudwatch(str_aux, "key")
    #                 except Exception as e:
    #                     str_aux = "ERROR\t" + str(e) + "\t" + str_aux
    #                     create_log_cloudwatch(str_aux, "key")
    #                     print(e)
    #     except:
    #         pass

    # # delete users without login and at least one key
    # for user in users:
    #     if user.password_enabled == "false" or user.password_enabled == "N/A":
    #         if user.access_key_1_active == "false" or user.access_key_1_active == "N/A":
    #             if (
    #                 user.access_key_2_active == "false"
    #                 or user.access_key_2_active == "N/A"
    #             ):

    #                 # detach attached policies
    #                 try:
    #                     policies = iam_client.list_attached_user_policies(UserName=user.user)
    #                     for policy in policies["AttachedPolicies"]:
    #                         try:
    #                             response = iam_client.detach_user_policy(
    #                                 UserName=user.user, PolicyArn=policy["PolicyArn"])
    #                             str_aux = (
    #                                 "INFO\t"
    #                                 + str(user.user)
    #                                 + "\tdetach_policy"
    #                                 + str(policy["PolicyArn"])
    #                             )
    #                             create_log_cloudwatch(str_aux, "user")
    #                             print(str_aux)
    #                         except Exception as e:
    #                             str_aux = (
    #                                 "ERROR\t"
    #                                 + str(e)
    #                                 + "\t"
    #                                 + str(user.user)
    #                                 + "\tdetach_policy\t"
    #                                 + str(policy["PolicyArn"])
    #                             )
    #                             print(str_aux)
    #                 except Exception as e:
    #                     str_aux = ("ERROR\t" + str(e) + "\t" + str(user.user) + "\tlist_policy")
    #                     print(str_aux)

    #                 # detach user groups
    #                 try:
    #                     groups = iam_client.list_groups_for_user(UserName=user.user)
    #                     for group in groups["Groups"]:
    #                         try:
    #                             response = iam_client.remove_user_from_group(
    #                                 GroupName=group["GroupName"], UserName=user.user)
    #                             str_aux = (
    #                                 "INFO\t"
    #                                 + str(user.user)
    #                                 + "\tremove_user_from_group\t"
    #                                 + str(group["GroupName"])
    #                             )
    #                             create_log_cloudwatch(str_aux, "user")
    #                             print(str_aux)
    #                         except Exception as e:
    #                             str_aux = (
    #                                 "ERROR\t"
    #                                 + str(e)
    #                                 + "\t"
    #                                 + str(user.user)
    #                                 + "\tremove_user_from_group\t"
    #                                 + str(group["GroupName"])
    #                             )
    #                             print(str_aux)
    #                 except Exception as e:
    #                     str_aux = ("ERROR\t" + str(e) + "\t" + str(user.user) + "\tlist_groups")
    #                     print(str_aux)

    #                 # remove user policies
    #                 try:
    #                     policies = iam_client.list_user_policies(UserName=user.user)
    #                     for policy in policies["PolicyNames"]:
    #                         try:
    #                             response = iam_client.delete_user_policy(UserName=user.user, PolicyName=policy)
    #                             str_aux = (
    #                                 "INFO\t"
    #                                 + str(user.user)
    #                                 + "\tdetach_policy_user"
    #                                 + str(policy)
    #                             )
    #                             create_log_cloudwatch(str_aux, "user")
    #                             print(str_aux)
    #                         except Exception as e:
    #                             str_aux = (
    #                                 "ERROR\t"
    #                                 + str(e)
    #                                 + "\t"
    #                                 + str(user.user)
    #                                 + "\tdetach_policy_user\t"
    #                                 + str(policy)
    #                             )
    #                             print(str_aux)
    #                 except Exception as e:
    #                     str_aux = (
    #                         "ERROR\t"
    #                         + str(e)
    #                         + "\t"
    #                         + str(user.user)
    #                         + "\tlist_policy_user"
    #                     )
    #                     print(str_aux)

    #                 str_aux = str(user.user) + "\tusername_deleted"
    #                 try:
    #                     response = iam_client.delete_user(UserName=user.user)
    #                     str_aux = "SUCCESS\t" + str_aux
    #                 except Exception as e:
    #                     str_aux = "ERROR\t" + str(e) + "\t" + str_aux
    #                     print(f"ERROR\tEXCEPTION during user deletion -> {e}")
    #                 finally:
    #                     create_log_cloudwatch(str_aux, "user")
    #                     print(str_aux)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "AWS IAM Watcher function executed successfully",
            }
        ),
    }


def update_statistics_database(reminder_age: int):
    pass


def delete_aksk(username: str, inactivity_time: int = 0):
    time_limit = datetime.now() - timedelta(days=int(90))

    try:
        access_keys = iam_client.list_access_keys(UserName=username)

        for key in access_keys["AccessKeyMetadata"]:
            if key["CreateDate"].date() <= time_limit.date():

                str_aux = (
                    str(username)
                    + "\tdisable_access_key\t"
                    + str(key["AccessKeyId"])
                    + "\t"
                    + str((date.today() - key["CreateDate"].date()).days)
                    + "\t"
                    + str("key_age")
                )
                if inactivity_time != 0:
                    str_aux += (f"\t{str(inactivity_time)}\tdays_inactive")

                try:
                    iam_client.delete_access_key(
                        AccessKeyId=key["AccessKeyId"],
                        UserName=username,
                    )
                    str_aux = "SUCCESS\t" + str_aux
                    create_log_cloudwatch(str_aux, "key")
                except Exception as e:
                    str_aux = "ERROR\t" + str(e) + "\t" + str_aux
                    create_log_cloudwatch(str_aux, "key")
                    print(e)
    except ClientError as err:
        print(f"ERROR\t{username}\tSomething went wrong during AK/SK deletion -> {err}")


def delete_password(username: str):
    pass


def delete_user(username: str):
    pass


def get_username_email(username: str):
    pass


def send_email_warning_email(dest_email: str, password_age: int, aksk_age: int):
    pass


def create_log_cloudwatch(message: str, log_stream_name):
    logs = boto3.client("logs")

    response: typing.Dict[str, typing.Any] = logs.describe_log_streams(
        logGroupName="disable-inactive-unused-iam", logStreamNamePrefix=log_stream_name
    )

    event_log: typing.Dict[str, typing.Any] = {
        "logGroupName": "disable-inactive-unused-iam",
        "logStreamName": log_stream_name,
        "logEvents": [
            {"timestamp": int(round(time.time() * 1000)), "message": message}
        ],
    }

    if "uploadSequenceToken" in response["logStreams"][0]:
        event_log.update({"sequenceToken": response["logStreams"][0]["uploadSequenceToken"]})

    response = logs.put_log_events(**event_log)


if __name__ == "__main__":
    print("starting")
    pprint.pprint(lambda_handler())
    print("finished")
