**_THIS IS A MIRORED VERSION OF AN INTERNAL PRODUCTION REPOSITORY LAST UPDATED 2024-07-25_**

# CityGeo Secrets
_Authors: James Midkiff and Roland MacDavid_

Securely obtain, cache, and update secrets from Keeper

When retrieving secrets, `citygeo_secrets` will search in the following order and return a secret when found: 
1. Internal memory cache (if the secret has already been retrieved in the same python process)
1. Drive on Windows or Linux (if available and the user has permission)
1. Keeper API (the source of "truth")

When a secret is retrieved or updated, it will write the secret out in the reverse order: First to Keeper (if the user updates the secret), then to the "mounted" drive (if available and the user has permission), and then to the memory cache. 

## Pre-Setup
### Keeper Initialization
First, ensure your secrets are in Keeper in one (or more) shared folders and that they are type "login" or "database". **For unknown reasons, this package is unable to locate "general" type records.** Secret names **_must_** be globally unique.

Then, either
1. Use an existing `client-config.json` file, passing its file location to the module via:  
`cgs.set_config(keeper_dir="<relative or absolute filepath>")`  
    See **Configuration** section for more information. 
    Or, 
1. Initialize a new Keeper application. Follow [these directions](https://docs.keeper.io/secrets-manager/secrets-manager/about/one-time-token#using-the-keeper-vault-to-generate-a-token).

    Notes:
    - Name the application for the script and the server that will be using it, e.g. "Election Results - linux-scripts-aws"
    - The application should generally only need read-access; if a secret needs automated updating, then write-access can be granted, but the preference is to manually update secrets with the Keeper GUI. 
    - Lock the application to the first IP that uses the inital request
    - Be sure to give the application access to all the folders where your various secrets may be located

    Next, copy the one-time token into a file named `config-secret` located _wherever you are running your application from_. The application upon first use will consume the token and generate a new file `client-config.json`. 

__Do not add any of these files to your github repository; add the following to `.gitignore`:__
```
*client-config.json
*config-secret
*env_vars.bash
```



## Installation
Requires python >= 3.7  

_https_: 
```bash
pip install git+https://github.com/CityOfPhiladelphia/citygeo_secrets.git
```

_ssh_:
```bash
pip install git+ssh://git@github.com/CityOfPhiladelphia/citygeo_secrets.git
```

## Usage
```python
import citygeo_secrets as cgs
```

### Automatically connect using most up-to-date credentials
**cgs.connect_with_secrets**(_func_, *_secret_names_, _**kwargs_)

Use secret names to connect to host, automatically retrieving newest secrets and retrying once if an exception is raised.

Parameters:
- *_func_*: (dict) -> Any
    - A user-created function that accepts a dictionary, extracts the desired credentials, and returns the desired connection. This function should fail if the credentials are invalid so that `cgs.connect_with_secrets` can grab the latest credentials from Keeper and retry once.
        - Pass the function name itself, do not call the function with `()` 
    - Certain modules use lazy-initialization of connections (specifically [sqlalchemy.create_engine()](https://docs.sqlalchemy.org/en/20/core/engines.html#sqlalchemy.create_engine)), so ensure that the code actually verifies if the credentials are correct  by forcing a new connection to be made if necessary
    - For the structure of the dictionary that the function must accept, see `cgs.get_secrets()` 
- _*secret_names_: str
    - Names of one or more secrets exactly as they appear in Keeper
        - `'<secret_name1>', '<secret_name2>', ...`
- _**kwargs_: Any
    - Any keyword-arguments you need to pass to _func_
        - `kwarg1 = 'val1', kwarg2 = 'val2', ...`

Returns: 
- Return value of _func_, e.g. a database connection, API connection, SFTP connection, boto3 client, etc.

```python
import citygeo_secrets as cgs

def connect_db(creds: dict): 
    db_creds = creds['Test CityGeo_Secrets DB']
    db_creds_part2 = creds['Test CityGeo_Secrets DB - Part 2']
    ... # Connect to database
    return connection

def connect_other(creds: dict, extra: str): 
    other_creds = creds['Test CityGeo_Secrets']
    print(f'extra: {extra}')
    ... # Connect to other service
    return connection


conn_db = cgs.connect_with_secrets(
    connect_db, "Test CityGeo_Secrets DB", "Test CityGeo_Secrets DB - Part 2")
conn_other = cgs.connect_with_secrets(
    connect_other, "Test CityGeo_Secrets", extra='EXTRA')
```

### Generate environment variables as part of a bash script
**cgs.generate_env_file**(_method_='keeper', _**kwargs_)

Generate a file to source environment variables for a shell script, ignoring string interpolation.

While this method only creates the file itself (and does not actually source the variables), it will print the lines of code necessary to run in shell. The method can be run interactively, but is also designed to be run directly by a shell script - see the example below. 

**Warning**: Choose the names of environment variables carefully. It is not recommended to overwrite existing system environment variables such as  
- ORACLE_HOME  
- SSH_CLIENT  
- SHELL
- PWD

There are currently no checks for this. Overwriting an environment variable related to `citygeo_secrets` is fine. 


Parameters: 
- _method_: str = 'keeper'
    - Must be one of 
        - "keeper" (preferred), or
        - "mount", "mounted", or "tmpfs"
    - Determines whether secrets are sourced from keeper or from mounted drive
    - "keeper" is preferred as secrets sourced from mounted drive as environment variables will not auto-update upon connection failure. "mount" can be used for scripts that run _very_ frequently but whose secrets need to be changed manually only infrequently. 
- **_kwargs_: tuple[str, str | list[str] ]
    - Format: `<ENV_VAR_NAME> = ('<secret_name>', subset_path)`
    - Information: 
        1. `<ENV_VAR_NAME>` is the name of the environment variable to create
        1. `'<secret_name>'` is name of one  secret exactly as it appears in Keeper
        1. `subset_path` is a list of parsing levels in a secret's dictionary: `["<index1>", "<index2>", ...]`
            - If only one level is needed then a string can be passed instead.
            - To see a secret's dictionary, use: 
    
                ```
                cgs.get_secrets('<secret_name>', build=False)['<secret_name>']
                ```

Returns: 
- _None_ (writes out a file)

```bash 
#!/bin/bash

##### 
# This is a bash script
# Run `source <this_bash_script>` to have environment variables for all subprocesses
# Copy this file into your dbt project and modify as needed
#####
source venv/bin/activate # wherever citygeo_secrets & python are installed

# Writes out a file of environment variables 
# Note that 'databridge-oracle/hostname' requires two levels to access the host value
python -c "
import citygeo_secrets as cgs 
cgs.generate_env_file('keeper', 
    DATABRIDGE_USER = (
        'SDE', 
        'login'), 
    DATABRIDGE_PASSWORD = (
        'SDE', 
        'password'), 
    DATABRIDGE_HOST = (
        'databridge-oracle/hostname', 
        ['host', 'hostName']), 
    DATABRIDGE_DBNAME = (
        'databridge-oracle/hostname', 
        'database'), 
    AWS_ACCESS_KEY_ID = (
        'CityGeo AWS script access key', 
        'login'), 
    AWS_SECRET_ACCESS_KEY = (
        'CityGeo AWS script access key', 
        'password')
    )
"
###### 
# Include the following lines in your bash script to automatically source and delete the correct file, which is produced in the same location as this bash script. 
# If you do not copy the below lines, `citygeo_secrets` will output bash code that you SHOULD include instead. 

# Get dirname of this script
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd) 
ENV_VARS_FILE=""$SCRIPT_DIR"/citygeo_secrets_env_vars.bash"

source $ENV_VARS_FILE
rm $ENV_VARS_FILE
######

# Add additional variables to export here
export SCHEMA=$USER

# Rest of bash script and any subprocesses now have access to the above environment variables
...
```
Note this feature is currently implemented on Linux only, not on Windows.

### Manually use a secret or view its structure

**cgs.get_secrets**(_*secret_names_, _build_=True, _search_cache_=True)

Obtain secrets from mounted drive (tmpfs) and/or Keeper

While developing and debugging, it may be easier to use this manual method first. This method will not auto-update an existing secret on the mounted drive if the secret is out-dated, but it will create the mounted drive and write any new secrets there if either do not exist.

Parameters: 
- _*secret_names_: str
    - Names of one or more secrets exactly as they appear in Keeper
        - `'<secret_name1>', '<secret_name2>', ...`
- _build_: bool = True 
    - If True, attempt to build mounted drive, otherwise just get secrets from Keeper or memory cache
- _search_cache_: bool = True
    - If True, search for secret in cache. Regardless of this value, the returned secret will be written to cache

Returns: 
- _dict_ of credentials


```python
import citygeo_secrets as cgs

# Retrieve a dictionary of credentials
# Secret names must exactly match entries in Keeper (case-sensitive)
credentials = cgs.get_secrets(
    "db1", "db2", "db3")

# Returns a dictionary: 
# credentials = {
#     "db1": {
#         "login": "login1", 
#         "password": "password1"
#     }, 
#     "db2": {
#         "host": {
#             "hostName": "host2", 
#             "port": "5432"
#         }, 
#         "password": "password2"
#     }, 
#     ...
# }

# User creates function to extract credentials and connect
postgres_conn = create_postgres_conn(credentials)
oracle_conn = create_oracle_conn(credentials)
```

### Configuration
You may set various configuration parameters for how `citygeo_secrets` runs. These remain in place as long as the parent python process is active
```python
import citygeo_secrets as cgs

cgs.set_config(
    keeper_dir="~/citygeo_secrets/venv_3.10", 
    log_level='debug', 
    verify_ssl_certs=False)

cgs.get_config() # Print out currently configuration

db_conn = cgs.connect_with_secrets(func, 'my_secret')
```
* _keeper_dir_ - Directory where either `client-config.json` or `config-secret` are located. This means you can place one file in your user directory on the server and use that for each new script without making a new Keeper application each time. Defaults to the current directory otherwise
* _log_level_ - One of "debug", "info", "warn", "error". Default is "info"
* _verify_ssl_certs_ - True | False, used by `keeper_secrets_manager`. Default is True. 


### Additional Functionality
- **cgs.update_secret**(_secret_name_, _secret_)
    - Update a secret in Keeper and mounted drive (if possible), overwriting fields where possible otherwise adding new custom fields
    - Recommended only for secrets that require automated updating; manually updating secrets is preferred. Raises _AssertionError_ if secret does not exist
    - Parameters: 
        - _secret_name_: str
            - Name of secret to update
        - _secret_: dict
            - `{'field1': 'new_value1', 'field2': 'new_value2', ...}`
    - Returns: 
        - _None_ 
- **cgs.get_keeper_record**(_secret_name_)
    - Obtain a secret from keeper; only meant to be used if automated parsing fails
    - Parameters: 
        - _secret_name_: str
            - Name of secret to update
    - Returns: 
        * _keeper_secrets_manager_core.dto.dtos.Record_
- **cgs.worker.reset_mount_attributes()**
    - Redetermine existence and accessibility of "mounted" drive. 
    - Values will then be written to `cgs.worker.mount_exists` and `cgs.worker.mount_access`


#### Global variables
- `cgs.worker` - The object whose methods are utilized, depending on the operating system. Inheriting from `cgs.AbstractWorker`, it is a singleton object (never created more than once). It should not be accessed by most users, but it does provide information about current global variables 

## Notes
* The memory cache is only available within the same python process; it has not been tested in multiprocessing or multithread environments. 

### Linux
* **WARNING: This mounted drive will only be accessible by the first sudo user who ran the application.** If it is necessary to undo a mistake, then discuss with the systems engineer, but the general approach will be to unmount and (carefully) remove the added entry in /etc/fstab, and then re-run the application. 
* If a user _does not_ have sudo access, then the application will only retrieve secrets from Keeper. 

### Windows
* Every user will be able to create their own hidden drive locaton of secrets, regardless of their administrative privileges
