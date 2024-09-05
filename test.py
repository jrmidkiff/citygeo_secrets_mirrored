'''
A series of tests for this package. Somebody with several days 
time can turn this into a better set of tests suitable for `pytest`. 
'''

import citygeo_secrets as cgs
import sqlalchemy as sa
import random, logging

def create_engine(creds: dict, host_secret: str, schema_secret: str) -> sa.Engine:
    '''Compose the URL object, create engine, and test connection'''
    db_creds = creds[host_secret]
    creds_schema = creds[schema_secret]
    url_object = sa.URL.create(
        drivername='postgresql+psycopg',
        username=creds_schema['login'],
        password=creds_schema['password'],
        host=db_creds['host'],
        port=db_creds['port'],
        database=db_creds['database']
    )
    engine = sa.create_engine(url_object)
    engine.connect()
    return engine

counter = 0
def print_test(): 
    global counter
    counter += 1
    print(f'Test {counter}')

# Test
print_test() 
cgs.get_config()
cgs.set_config(keeper_dir="./venv_3.10", log_level='debug')
cgs.set_config(keeper_dir="~", log_level='debug'
               , verify_ssl_certs=False
               )
cgs.get_config()
print()

# Test
print_test()
cgs.get_secrets('CITY\gisscripts') # This should log only once and include debug

logging.basicConfig(format='%(levelname)s: %(message)s')
this_log = 'info'
log_level = getattr(logging, this_log.upper(), None)
global logger
logger = logging.getLogger(__name__)
logger.setLevel(level=log_level)

logger.warning('This should also print')
logger.info('This should also print')
logger.debug('This should NOT print')

logging.root.warning('This should print')
logging.root.info('This should NOT print')
logging.root.debug('This should NOT print')

cgs.get_secrets('CITY\gisscripts') # This should log only once
print()

# Test
print_test()
cgs.get_secrets('CITY\gisscripts', search_cache=False)
cgs.get_secrets('CITY\gisscripts', build=False, search_cache=False)
print()

# Test
print_test()
print(f"\t{cgs.get_secrets('Test CityGeo_Secrets')}")
cgs.update_secret('Test CityGeo_Secrets', {'password': f'password{random.randint(1,100)}'})
print(f"\t{cgs.get_secrets('Test CityGeo_Secrets')}")
print()

# Test
print_test()
print(f"\t{cgs.get_secrets('Test CityGeo_Secrets')}")
def test_conn(creds): 
    assert creds['Test CityGeo_Secrets']['password'] != 'password64'

# To properly run this test: 
# Once the debugger gets here, change the assert statement 
# to match whatever keeper has for the password. 
cgs.connect_with_secrets(test_conn, 'Test CityGeo_Secrets')
print()

# Test
print_test()
example = cgs.get_keeper_record('databridge-v2/rds-hostname-testing')
print(f"\t{example}")
print()

# Test
print_test()
cgs.connect_with_secrets(create_engine, 
    'databridge-v2/rds-hostname-testing', 'databridge-v2/postgres', 
    host_secret='databridge-v2/rds-hostname-testing', schema_secret='databridge-v2/postgres')
cgs.connect_with_secrets(create_engine, 
    'databridge-v2/rds-hostname-testing', 'databridge-v2/postgres', 
    host_secret='databridge-v2/rds-hostname-testing', schema_secret='databridge-v2/postgres')
print()

# Test
print_test()
cgs.set_config(log_level='info')
cgs.get_secrets("databridge-v2/hostname", build=False)
cgs.get_secrets("databridge-v2/hostname",
                "databridge-v2/hostname", "databridge-v2/hostname")
print()

# Test
print_test()
try: 
    cgs.get_secrets('Non-existent secret')
except AssertionError: 
    print('Assertion error successfully raised')
print()

# Test
print_test()
# Currently not implemented on Windows
try: 
    cgs.generate_env_file('keeper',
                        USER=(
                            'databridge-v2/citygeo',
                            'login'),
                        PASSWORD=(
                            'databridge-v2/citygeo',
                            'password'),
                        HOST=(
                            'databridge-v2/hostname-testing',
                            'host'),
                        DBNAME=(
                            'databridge-v2/hostname-testing',
                            'database'),
                        PORT=(
                            'databridge-v2/hostname-testing',
                            'port'))

    cgs.generate_env_file('keeper',
                        USER=(
                            'databridge-v2/citygeo',
                            'login'),
                        PASSWORD=(
                            'databridge-v2/citygeo',
                            'password'),
                        HOST=(
                            'databridge-v2/hostname-testing',
                            'host'),
                        DBNAME=(
                            'databridge-v2/hostname-testing',
                            'database'),
                        PORT=(
                            'databridge-v2/hostname-testing',
                            'port'))
except NotImplementedError: 
    print('NotImplementedError successfully raised')
