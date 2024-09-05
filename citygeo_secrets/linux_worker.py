from .abstract_worker import AbstractWorker
import re, os, subprocess, functools
from typing import Sequence


class LinuxWorker(AbstractWorker): 
    '''Worker designed for Linux OS
    - Linux uses a mounted drive only accessible by the first ROOT user to create it. 
    All other users will use Keeper only
    '''
   
    def __init__(self): 
        self.MOUNT_LOCATION = '/tmpfs-secure' # Must be the same as assigned in SCRIPT_NAME
        self.SCRIPT_NAME = 'tmpfs-mount.sh'
        
        super().__init__()

    def determine_mount_exists(self) -> bool:
        '''Determine if tmpfs exists'''
        return os.path.ismount(self.MOUNT_LOCATION)

    def generate_env_file(self, method: str = 'keeper', **kwargs: 'tuple[str, str | list[str]]'):
        strings = []
        for env_name, secret_info in kwargs.items():
            assert isinstance(secret_info, Sequence)
            assert len(secret_info) == 2

            secret_name, subset_path = secret_info
            assert isinstance(secret_name, str)
            if isinstance(subset_path, str):
                subset_path = [subset_path]
            assert isinstance(subset_path, Sequence)

            if method.lower() == 'keeper':
                secret_dict = self._generate_secrets_dict(
                    secret_name, drive_access=False, search_cache=True)
            elif method.lower() in ('mount', 'mounted', 'tmpfs'):
                secret_dict = self.get_secrets(secret_name)
            else:
                raise AttributeError(
                    f'Method "{method}" not one of "keeper", "mount"')
            secret = secret_dict[secret_name]
            env_value = functools.reduce(dict.get, subset_path, secret)
            strings.append(f"export {env_name}='{env_value}'\n")
        with open(self.ENV_VARS_FILENAME, 'w') as f:
            f.writelines(strings)
            self.logger.info(f'Successfully created env_file')
            self.logger.info(f'''After running this python script in bash file, include these lines:
            ENV_VARS_FILE="{os.path.realpath(f.name)}"
            source $ENV_VARS_FILE
            rm $ENV_VARS_FILE''')
            self.logger.warning(
                f'DO NOT GIT COMMIT {os.path.realpath(f.name)} - ADD TO .gitignore')
            if method.lower() in ('mount', 'mounted', 'tmpfs'):
                self.logger.warning('Secrets sourced from mounted drive as environment variables will not auto-update upon connection failure')

    def _generate_secret_path(self, secret_name: str) -> str:
        storage_name = secret_name.replace('/', '_')
        return os.path.join(self.MOUNT_LOCATION, f'{storage_name}.json')

    def _build_mount(self):
        '''Build tmpfs. If bash returns a permission error, then return None to 
        allow sourcing secrets from Keeper. Raise any other bash error.'''
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, self.SCRIPT_NAME)

        completed_process = subprocess.run(
            [script_path],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.logger.info(completed_process.stdout)
        if completed_process.returncode != 0 and re.search('Permission denied', completed_process.stdout, flags=re.IGNORECASE):
            return None
        completed_process.check_returncode()
