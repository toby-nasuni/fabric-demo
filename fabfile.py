from fabric import task
from os.path import basename, isfile
import tempfile
import os
import typing as t
from fabric import Connection

TEMP_DIR = "/tmp"
DEFAULT_ENV = "test"
DEFAULT_REGION = "us-west-1"
DEFAULT_USER = "ubuntu"
DEFAULT_STACK = "tmodel1"
DEFAULT_PREFIX = "nasuni-noc-source"
S3_BUCKET_PATH = f"{DEFAULT_PREFIX}-{DEFAULT_ENV}-{DEFAULT_REGION}"


@task(name="build")
def build_git_artifact(context, path=None):
    """
    Build a git artifact from the git repo in the specified location
    """

    cwd = path if path else os.path.dirname(os.path.realpath(__file__))
    if not os.path.isdir(cwd):
        print(f"The path {cwd} does not appear to be a directory")
        return 1
    
    with context.cd(cwd):
        try:
            repo_name = basename(context.run('git rev-parse --show-toplevel', hide=True).stdout.strip())
            current_branch = context.run('git rev-parse --abbrev-ref HEAD', hide=True).stdout.strip()
            list_all_files = context.run('git ls-files', hide=True)
        except:
            print(f"The directory {cwd} does not appear to have a git repository")
            return 1


        tarball_filename_format = "{repo}-{branch}.tgz"
        tar_file_name = TEMP_DIR + '/' + tarball_filename_format.format(
            repo=repo_name, branch=current_branch
        ).replace('/', '-')


        exclude_args = '--exclude "*/.git*" '
        if isfile(f"{cwd}/.gitignore"):
            exclude_args += f'  --exclude-from={cwd}/.gitignore'

        with tempfile.NamedTemporaryFile(dir=TEMP_DIR) as fh:
            fh.write(list_all_files.stdout.encode())
            fh.flush()

            tar_cmd = f'tar -czf {tar_file_name} {exclude_args} -T {fh.name}'
            # print(tar_cmd)
            context.run(tar_cmd)

        print(f"Created the artifact {tar_file_name}")


@task(name="deploy")
def deploy_artifact(context, region=DEFAULT_REGION, artifact="python-test-development.tgz", ip=None):
    """
    Deploy the latest version of the artifact
    """

    s3_path = _gen_artifact_s3_key(artifact)
    for ip_address in _get_ips(region_name=region):
        if ip and ip_address != ip:
            continue
        cnx = Connection(ip_address, user=DEFAULT_USER)
        print(f"\033[95mDeploying to {ip_address} \033[0m")
        cnx.put("deploy.sh")
        cnx.run(f"./deploy.sh 's3://{S3_BUCKET_PATH}/{s3_path}'")


@task(name="instances")
def show_instances(context, region=DEFAULT_REGION, show_uptime=False):
    """
    Show information about EC2 Instances
    """

    instances = _get_instances(region_name=region)

    tmpl = "{id:>20}  {ip:16}  {lt:<16}"
    if show_uptime:
        tmpl += "  {uptime}"
    print(tmpl.format(id="Instance ID", ip="Public IP", lt="Launch Time", uptime="Uptime"))
    uptime = None
    for instance in instances:
        ip_address = instance.public_ip_address
        if show_uptime:
            try:
                cnx = Connection(ip_address, user=DEFAULT_USER)
                uptime = cnx.run("uptime", hide=True).stdout.strip()
            except:
                pass
        print(tmpl.format(id=instance.id, ip=ip_address, lt=str(instance.launch_time)[:16], uptime=uptime))

@task(name="ips")
def show_ips(context, region=DEFAULT_REGION):
    """
    Show just IP information about EC2 Instances
    """

    print(' '.join(_get_ips(region_name=region)))


@task(name="restart", aliases=['restart-flask'])
def restart_apache(context, region=DEFAULT_REGION, ip=None):
    """
    Restart the application on the servers
    """
    for ip_address in _get_ips(region_name=region):
        if ip and ip_address != ip:
            continue
        cnx = Connection(ip_address, user=DEFAULT_USER)
        print(f"Restart on {ip_address}")
        cnx.sudo(f"systemctl restart flask.service")


@task(name="upload")
def upload_git_artifact(context, file):
    """
    Upload an artifact to S3 for later deployment
    """
    s3 = _aws_session().resource('s3')

    file_path = os.path.abspath(file)
    if not os.path.exists(file_path):
        print(f"Path {file_path} does not exist")
        return

    s3_key = _gen_artifact_s3_key(file_path)
    s3.meta.client.upload_file(file_path, S3_BUCKET_PATH, s3_key)
    print(f"Uploaded artifact to s3://{S3_BUCKET_PATH}/{s3_key}")


def _aws_session(region_name=DEFAULT_REGION):
    import boto3

    session = boto3.session.Session(region_name=region_name)

    return session


def _gen_artifact_s3_key(file_name: str) -> str:
    file_name = os.path.basename(file_name)
    return f"{DEFAULT_STACK}-{DEFAULT_REGION}/{file_name}"


def _get_ips(region_name: str) -> t.List:

    return [i.public_ip_address for i in _get_instances(region_name)]


def _get_instances(region_name: str) -> t.List:


    ec2 = _aws_session().resource('ec2', region_name=region_name)
    instances = ec2.instances.filter(Filters=[{
        'Name': 'instance-state-name',
        'Values': ['running']}]
    )

    return instances
