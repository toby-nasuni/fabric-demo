from fabric import task
from os.path import basename, isfile
import tempfile
import os
import typing as t

TEMP_DIR = "/tmp"

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
def show_instances(context, region="us-west-1"):
    """
    Show information about EC2 Instances
    """

    instances = _get_instances(region_name=region)

    tmpl = "{:>20}  {:16}  {}"
    print(tmpl.format("Instance ID", "Public IP", "Launch Time"))
    for instance in instances:
        print(tmpl.format(instance.id, instance.public_ip_address, str(instance.launch_time)[:16]))

@task(name="ips")
def show_ips(context, region="us-west-1"):
    """
    Show just IP information about EC2 Instances
    """

    print(' '.join(_get_ips(region_name=region)))


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
