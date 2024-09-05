from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Callable, Any
import os, json, pprint, logging, getpass, platform

class AbstractWorker(ABC): 
    '''Abstract base class to ensure worker classes are properly implemented
    
    See https://www.geeksforgeeks.org/factory-method-python-design-patterns/'''
    from ._keeper import (
        get_keeper_record, update_keeper_secret, _get_keeper_secret_manager,
        _parse_keeper_record, KEEPER_TOKEN_FILENAME, KEEPER_FILENAME)
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    sh = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    logger.propagate = False

    ENV_VARS_FILENAME = 'citygeo_secrets_env_vars.bash'

    def __init__(self): 
        self._config = {}
        self._config['keeper_dir'] = os.getcwd()
        self._config['log_level'] = "INFO"
        self._cache = {}
        self.platform = platform.system()
        self.reset_mount_attributes()

    def set_config(self, **kwargs): 
        '''Set the configuration options regardless of worker subclass'''
        for k,v in kwargs.items(): 
            if k == 'log_level': 
                v = v.upper()
                self.logger.setLevel(v)

            self._config[k] = v

    def get_config(self): 
        '''Print the configuration options regardless of worker subclass'''
        print('CityGeo Secrets Config:')
        pprint.pprint(self._config)
    
    def reset_mount_attributes(self): 
        '''Set or reset attributes for the worker related to mount existence and access'''
        self.mount_exists = self.determine_mount_exists()
        if self.mount_exists:
            self.logger.info(f'Mounted drive located at {self.MOUNT_LOCATION}')
            self.mount_access = self.determine_mount_access()
            if self.mount_access: 
                self.logger.info(f'User "{getpass.getuser()}" has permission to access mounted drive')
            else: 
                self.logger.info(f'User "{getpass.getuser()}" does not have permission to access mounted drive')
        else:
            self.mount_access = False
            self.logger.info(f'Mounted drive does not exist')
    
    def determine_write(self, secret_name: str, secret: dict, write_cache: bool, write_mount: bool):
        '''Determine how to write to cache and/or mounted drive'''
        if write_cache:
            self._cache[secret_name] = secret # Write to cache regardless
            self.logger.debug(f'Successfully wrote secret "{secret_name}" to cache')
        if write_mount:
            secret_path = self._generate_secret_path(secret_name)
            self._write_secret_to_mount(secret_path, secret)
    
    def _generate_secrets_dict(self, *secret_names: str, drive_access: bool, search_cache: bool) -> 'dict':
        secrets_dict = {}
        for secret_name in secret_names:
            if search_cache:
                secret = self._cache.get(secret_name, None)
                if secret != None:  # Secret found in cache
                    secrets_dict[secret_name] = self._cache[secret_name]
                    self.logger.info(
                        f'Successfully retrieved secret "{secret_name}" from cache')
                    continue
            if drive_access:
                secret_path = self._generate_secret_path(secret_name)
                secret = self._get_secret_from_mount(secret_path)
                if secret != None:  # Secret found in mount
                    secrets_dict[secret_name] = secret
                    self.logger.info(
                        f'Successfully retrieved secret "{secret_name}" from mounted drive')
                    self.determine_write(secret_name, secret,
                                         write_cache=True, write_mount=False)
                    continue

            # If not found or not searching in cache & mount, use Keeper
            record = self.get_keeper_record(secret_name)
            secret = self._parse_keeper_record(record)
            secrets_dict[secret_name] = secret
            self.determine_write(secret_name, secret,
                                 write_cache=True, write_mount=drive_access)

        return secrets_dict

    def get_secrets(self, *secret_names: str, build: bool = True,
                    search_cache: bool = True) -> 'dict':
        if build:
            if self.mount_exists:
                return self._generate_secrets_dict(
                    *secret_names, drive_access=self.mount_access, search_cache=search_cache)
            else:
                self._build_mount()
                self.reset_mount_attributes()
                if self.mount_exists and self.mount_access: 
                    return self._generate_secrets_dict(
                        *secret_names, drive_access=True, search_cache=search_cache)
            
        return self._generate_secrets_dict(
            *secret_names, drive_access=False, search_cache=search_cache)

    def connect_with_secrets(self, func: Callable[[dict], Any], *secret_names: str, **kwargs):
        secrets = self.get_secrets(*secret_names)
        try:
            return func(secrets, **kwargs)
        except Exception as e:
            if self.mount_exists and self.mount_access:
                secrets_dict = {}
                for secret_name in secret_names:
                    record = self.get_keeper_record(secret_name)
                    secret = self._parse_keeper_record(record)
                    secrets_dict[secret_name] = secret
                conn = func(secrets_dict, **kwargs)
                for secret_name, secret in secrets_dict.items():  # Only write if 2nd attempt doesn't raise an exception
                    self.determine_write(secret_name, secret, write_cache=True, write_mount=True)
                return conn
            else:
                raise e
    
    def update_secret(self, secret_name: str, secret: 'dict[str: str]'):
        secret_to_write = self.update_keeper_secret(secret_name, secret)
        write_mount = self.mount_exists and self.mount_access
        self.determine_write(secret_name, secret_to_write, write_cache=True, write_mount=write_mount)
    
    @abstractmethod
    def determine_mount_exists(): 
        ''''''
        raise NotImplementedError

    def determine_mount_access(self) -> bool:
        '''Determine if user has permission to access mount'''
        try:
            os.listdir(self.MOUNT_LOCATION)
            return True
        except PermissionError:
            return False

    def _write_secret_to_mount(self, secret_path: str, secret: dict):
        with open(secret_path, 'w') as f:
            json.dump(secret, f)
            f.write('\n')
            self.logger.debug(f'Successfully wrote secret to "{secret_path}"')
    
    def _get_secret_from_mount(self, secret_path: str) -> 'dict | None':
        '''Return secret (if present) from mounted drive'''
        if os.path.isfile(secret_path):
            with open(secret_path, 'r') as f:
                try: 
                    secret = json.load(f)
                except json.decoder.JSONDecodeError: 
                    if self.platform == 'Windows': 
                        print('\nJSON Decode Error')
                        print('If running citygeo_secrets in a Windows environment that previously used encryption, consider running the following powershell command:')
                        print('Remove-Item $env:USERPROFILE/.citygeo_secrets -Recurse')
                    raise
                return secret
        else:
            return None
    
    @abstractmethod
    def generate_env_file(method: str = 'keeper', **kwargs: 'tuple[str, str | list[str]]'):
        raise NotImplementedError

    @abstractmethod
    def _generate_secret_path(self, secret_name: str) -> str:
        '''Generate the file path for where secret will be stored'''
        raise NotImplementedError
    
    @abstractmethod
    def _build_mount(self):
        '''Build mount'''
        raise NotImplementedError
