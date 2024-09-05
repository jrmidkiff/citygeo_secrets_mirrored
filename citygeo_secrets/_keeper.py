import os
import keeper_secrets_manager_core as ksm

# This module is meant to be imported by AbstractWorker
# Using this module directly will fail. 

# These global variables and all functions will be referenced by `self.` 
# because this module is imported into AbstractWorker
KEEPER_TOKEN_FILENAME = 'config-secret'
KEEPER_FILENAME = 'client-config.json'


def _get_keeper_secret_manager(self) -> ksm.core.SecretsManager: 
    '''Set up the Keeper Secret Manager
    
    If the Keeper secret token file name does not exist, then the application presumes 
    that there is a text file with a one-time secret token to be used. Otherwise 
    it presumes that set-up has already been completed'''
    
    os.environ["KSM_CONFIG_SKIP_MODE"] = 'TRUE'
    
    config_json_filename = os.path.expanduser(os.path.join(
            self._config['keeper_dir'], self.KEEPER_FILENAME))
    
    # First time connecting to keeper
    if not os.path.isfile(config_json_filename):
        token_filename = os.path.expanduser(os.path.join(
            self._config['keeper_dir'], self.KEEPER_TOKEN_FILENAME))
        with open(token_filename, 'r') as f: 
            secret_token = f.readline()
        # Token only needed for first-time set-up
        secrets_manager = ksm.SecretsManager(
            token=secret_token, 
            config=ksm.storage.FileKeyValueStorage(config_json_filename), 
            verify_ssl_certs=self._config.get('verify_ssl_certs', True))
        os.remove(token_filename) # One-time secret token should be removed
        self.logger.info('Keeper Secrets Manager initialized - one-time token deleted\n')
    else: # Going forwards
        secrets_manager = ksm.SecretsManager(
            config=ksm.storage.FileKeyValueStorage(config_json_filename), 
            verify_ssl_certs=self._config.get('verify_ssl_certs', True))
    
    return secrets_manager


def _parse_keeper_record(self, record: ksm.dto.dtos.Record) -> dict: 
    '''Parse the fields and custom fields of a secret
    
    Raise `AssertionError` if any field has multiple values'''
    secret_dict = {}
    for section in ['fields', 'custom']: 
        for field in record.dict[section]: 
            try: 
                field_name = field['label']
            except KeyError: 
                field_name = field['type']
            field_value = field['value']

            if field_value != []: 
                assert len(field_value) == 1, f'Multiple values appear for secret record"{record.title}" {section} {field_name}.\nParse manually with citygeo_secrets.keeper.get_record(secret_name)'
                secret_dict[field_name] = field_value[0]
                
    return secret_dict


def get_keeper_record(self, secret_name: str) -> ksm.dto.dtos.Record: 
    '''Return the record with this name from a Keeper Secrets Manager
    
    Raise an exception if 0 or more than 1 records match that title'''
    secrets_manager = self._get_keeper_secret_manager()
    record = secrets_manager.get_secrets_by_title(secret_name)
    assert len(record) != 0, f'Secret record "{secret_name}" was not found by this application.'
    assert len(record) == 1, f'"{secret_name}" belongs to {len(record)} records. Change record names.'
    self.logger.info(f'Successfully retrieved secret record "{secret_name}" from keeper')
    return record[0]


def update_keeper_secret(self, secret_name: str, secret: dict): 
    '''Update a secret in keeper by overwriting fields where possible otherwise 
    adding new custom fields'''
    secrets_manager = self._get_keeper_secret_manager()
    record = self.get_keeper_record(secret_name)
    
    for new_key, new_val in secret.items(): 
        try: 
            if new_key in ('host', 'port'): # Because of bad implementation in Keeper SDK
                keeper_host_value = record.get_standard_field_value('host')[0]
                if new_key == 'host': 
                    keeper_host_value['hostName'] = new_val
                elif new_key == 'port': 
                    keeper_host_value['port'] = new_val
                record.field('host', keeper_host_value)
            else: 
                record.field(new_key, new_val)
        except ValueError: 
            try: 
                record.custom_field(new_key, new_val)
            except ValueError: 
                record.add_custom_field(
                    field_type='text', label=new_key, value=new_val)

    rv = self._parse_keeper_record(record)
    secrets_manager.save(record)
    self.logger.info(f'Successfully updated secret record {secret_name} in Keeper')
    return rv
