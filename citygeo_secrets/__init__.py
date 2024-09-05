import platform
from .linux_worker import LinuxWorker
from .windows_worker import WindowsWorker
from typing import Callable, Any
import keeper_secrets_manager_core as ksm


this_platform = platform.system()
if this_platform == 'Linux': 
    worker = LinuxWorker()
elif this_platform == 'Windows': 
    worker = WindowsWorker()
else: 
    raise NotImplementedError(f"Platform {this_platform} not currently accepted")


def set_config(**kwargs): 
    '''Set basic configuration options for the module'''
    worker.set_config(**kwargs)


def get_config(): 
    '''Print current configuration options for the module'''
    worker.get_config()


def get_secrets(*secret_names: str, build: bool = True, search_cache: bool = True) -> 'dict':
    '''Obtain secrets from mounted drive (tmpfs) and/or Keeper  
        - `secret_names`: Names of secrets 
        - `build`: If True, attempt to build mounted drive, otherwise get secrets 
        from Keeper
    
    The keys of the returned dictionary will be the `secret_names`, and the values
    will be the parsed secrets

    The mounted drive will only be built if `build=True`, the mounted drive does 
    not exist, and if on Linux the user has sudo privileges but is not a root user.

    Raises: 
    * `subprocess.CalledProcessError` if the subprocess used to generate the mounted 
    drive raises an error not due to user permissions
    '''
    return worker.get_secrets(*secret_names, build=build, search_cache=search_cache)


def connect_with_secrets(func: Callable[[dict], Any], *secret_names: str, **kwargs) -> Any:
    ''' Use secret names to connect to host, automatically retrieving newest secrets 
    and retrying once if an exception is raised.

    - `func`: User function that accepts a dictionary input and returns a 
    database/server/API/etc. connection
    - `secret_names`: Names of secrets to gather
    - `**kwargs`: keyword-arguments to pass to func

    Usage: 
        ```
        citygeo_secrets.connect_with_secrets(
            create_my_conn, 
            'secret1', 'secret2', ... , 
            kwarg1='val1', kwarg2='val2', ...)
        ```
    
    If a retry occurs, this function will update the mounted drive if the user has 
    access for each secret_name.

    Assume that: 
    1. An error in connection function is because of old credentials, and
    2. That if 1st assumption is wrong, then no harm will arise'''
    return worker.connect_with_secrets(func, *secret_names, **kwargs)


def update_secret(secret_name: str, secret: 'dict[str: str]'):
    '''Update a secret in Keeper and mounted drive (if possible) 
        - `secret_name`: Name of secret to update
        - `secret`: Dictionary of `{'field1': 'new_value1', 'field2': 'new_value2', ...}`
    
    Overwrites fields where possible otherwise adds new custom fields
    
    Raises AssertionError if secret does not exist'''
    worker.update_secret(secret_name, secret)


def generate_env_file(method: str = 'keeper', **kwargs: 'tuple[str, str | list[str]]'):
    '''Generate a file to source environment variables for a shell script, ignoring
    string interpolation
        - `method`: One of "keeper", "mount"/"tmpfs"
        - `kwargs`: Tuple of: 
            - `secret_name`: Name of secret as it appears in Keeper
            - `subset_path`: List of parsing levels in a secret's dictionary. 
            To see a secret's dictionary, use: 
    
                ```
                cgs.get_secrets('<secret_name>', build=False)['<secret_name>']
                ```
    
    As part of a shell script, run this function to generate the file of env vars, 
    source the file, then delete it. 
    
    The file created MUST NOT be committed to a git repository

    Raises: 
    * `AttributeError`: if `method` not recognized
    * `AssertionError`: if 0 kwargs provided
    '''
    assert len(kwargs) >= 1, "At least one environment variable required"
    worker.generate_env_file(method, **kwargs)


def get_keeper_record(secret_name: str) -> ksm.dto.dtos.Record: 
    '''Obtain a record from keeper; only meant to be used if automated parsing fails

    Raise an exception if 0 or more than 1 records match that title'''
    return worker.get_keeper_record(secret_name)
