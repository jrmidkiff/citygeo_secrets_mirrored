from .abstract_worker import AbstractWorker
import os, subprocess


class WindowsWorker(AbstractWorker): 
    '''Worker designed for Windows OS
    - Windows uses a folder of json files in the USERPROFILE directory. No special privileges required. 
    '''
    def __init__(self): 
        # $env:USERPROFILE is powershell automagic var that refers to your home directory
        # e.g. C:/Users/john.smith/
        self._HOME_DIR = os.getenv('USERPROFILE')
        self.MOUNT_LOCATION = os.path.join(self._HOME_DIR, '.citygeo_secrets') # '.' keeps the folder more hidden
        
        super().__init__()

    def determine_mount_exists(self) -> bool:
        '''Determine if "mounted" drive exists'''
        return os.path.isdir(self.MOUNT_LOCATION)

    def generate_env_file(self, method: str = 'keeper', **kwargs: 'tuple[str, str | list[str]]'):
        raise NotImplementedError

    def _generate_secret_path(self, secret_name: str) -> str:
        '''Generate the file path for where secret will be stored'''
        storage_name = secret_name.replace('/', '_').replace('\\', '_')
        return os.path.join(self.MOUNT_LOCATION, f'{storage_name}.json')

    def _build_mount(self):
        '''Build mount'''
        if not os.path.exists(self.MOUNT_LOCATION):
            os.makedirs(self.MOUNT_LOCATION)
            cmd = ['attrib', '+h', self.MOUNT_LOCATION]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode != 0: 
                self.logger.error(process.stderr)
            if process.stdout != '': 
                self.logger.info(process.stdout)
            process.check_returncode()
            self.logger.info(f'Hidden secrets directory successfully built at {self.MOUNT_LOCATION}')
