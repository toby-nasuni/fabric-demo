from fabric import task
from os.path import basename, isfile
import tempfile
import os
import typing as t
from fabric import Connection

TEMP_DIR = "/tmp"
DEFAULT_REGION = "us-west-1"
DEFAULT_USER = "ubuntu"


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


def _get_ips(region_name: str) -> t.List:

    return [i.public_ip_address for i in _get_instances(region_name)]


def _get_instances(region_name: str) -> t.List:
    import boto3

    ec2 = boto3.resource('ec2', region_name=region_name)
    instances = ec2.instances.filter(Filters=[{
        'Name': 'instance-state-name',
        'Values': ['running']}]
    )

    return instances
