# IAM Watcher

This tool watch iam users and their credentials, alert about expiry and build reporting statistics.

This tool is based on a central AWS IAM model, with a single account acting as an IAM entry point and cross account assume roles.

This way, it will scan for all IAM users in a single account.

## Prerequisite

IAM users should have an email in a specific tag with "email" key and the email as value.

All users prefixed with "\_atm" will be considered as service account (not human) and therefore should not have console access.

## Features

### Credential Expiration

AWS IAM users credentials (Password and AK/SK) is deleted once the expiration duration has been passed.

An optional grace period can be configured.

User is notified upon deletion.

### User deletion

AWS IAM user is be deleted after a period of inactivity.

Their group membership configuration is saved upon deletion to ease restore if required.

### Alerting

Before credential deletion, user is notified by email to make credential rotation.

### Reporting

A report can be generated with statistics (over a duration) such as:

- Average age of credentials
- Number of alerts sent
- Number of users with no credentials
