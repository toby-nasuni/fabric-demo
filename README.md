# Fabric Presentation

## Initial Commit

Use `pipenv install 'fabric<3'` to install the fabric library.

## Fabric Tasks

A "fabfile" can be used to define tasks executable by the `fab` command.  

Build a task that looks for a git repository in the current or designated directory, and builds an archive of committed files.

## AWS Integration

Use the `boto3` library to query AWS and fetch information about our S3 instances.  
Note, for these calls to work you're ~/.aws/credentials must be correct, 
or you must set AWS_SESSION variables in your environment.

## SSH Integration

Add some tasks that will use fabric's remote shell features.

```
fab instances --show-uptime
fab restart-flask
```
