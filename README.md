# aws-tooling

This repo contains few tools inpired by problem I faced, and tried to automate to ease my life.

## all-region-modifier

### What is it?

This tool aims at applying a change on multiple accounts, on all regions.

It was originally built to activate EBS encryption on all regions for many accounts (based on a real-life requirement).

### Usage

```shell
$ python3 all_region_modifier.py -h
usage: all_region_modifier.py [-h] role account_file

Apply change on all regions for all accounts listed in provided input.

positional arguments:
  role          The role to execute describe_regions and the action
  account_file  The relative path to json file with accounts

optional arguments:
  -h, --help    show this help message and exit
```

### Add an action

All action functions prototype should be like:

```python
def action_name(session: boto3.Session, account: str)->[]:
""" Perform an action on AWS account for the specified region.

Arguments:
    session {boto3.Session} -- a generic boto3 session opened with required privileges to perform action.
    account {str} -- account number currently processed, for logging and perf purpose as session is already opened.

Returns:
    [str] -- The list of error string encountered during action to be displayed at the end of overall process. Empty if no error.

"""
```

