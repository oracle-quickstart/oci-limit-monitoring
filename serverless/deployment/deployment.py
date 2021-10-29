import io
import os
import json
import oci
from datetime import datetime, timezone
from oci import events
from oci.config import from_file
from subprocess import Popen, PIPE
from jinja2 import Template
import argparse
import json


from oci.identity.models import compartment

identity_client = None
fn_mgmt_client = None
os_client = None
events_client = None
search_client = None


def initialize(region=None):
    """Creates OCI python sdk clients

    Parameters:
    region - the region in which you want to spawn the config

    Returns:

    identity_client - Client used for making IAM requests
    fn_mgmt_client - Client used for fn
    os_client - Client used for object storage
    event_client - Client used for events
    search_client - Client used for search
    """

    config = from_file()

    global identity_client
    global fn_mgmt_client
    global os_client
    global events_client
    global search_client

    identity_client = oci.identity.IdentityClient(config)
    response = identity_client.list_region_subscriptions(config["tenancy"])
    for reg in response.data:
        if reg.is_home_region:
            config["region"] = reg.region_name
            identity_client = oci.identity.IdentityClient(config)
            fn_mgmt_client = oci.functions.FunctionsManagementClient(config)
            os_client = oci.object_storage.ObjectStorageClient(
                config)
            events_client = oci.events.EventsClient(config)
            search_client = oci.resource_search.ResourceSearchClient(config)

    return config, identity_client, fn_mgmt_client, os_client, events_client, search_client


def create_rule(comp_id, fn_prefix, fn_id, bucket_name):
    """Creates an event rule for the oci function

    Parameters:

    Returns:
    -
    """

    event_json = json.dumps(
        {
            "eventType": "com.oraclecloud.objectstorage.deleteobject",
            "data": {
                "additionalDetails": {
                    "bucketName": bucket_name
                }
            }
        }
    )
    events_client.create_rule((oci.events.models.CreateRuleDetails(
        compartment_id=comp_id,
        actions=oci.events.models.ActionDetailsList(
            actions=[oci.events.models.CreateFaaSActionDetails(
                action_type="FAAS",
                is_enabled=True,
                function_id=fn_id,
            )]
        ),
        condition=event_json,
        display_name="{}-event".format(fn_prefix),
        is_enabled=True
    )))


def get_function(fn_name):
    """ Gets the main functions

    Parameters:
    fn_name - The name of the main_function

    Returns:
    The function and its details
    """

    structured_search = oci.resource_search.models.StructuredSearchDetails(query="query functionsfunction resources where displayName='{}'".format(fn_name),
                                                                           type='Structured',
                                                                           matching_context_type=oci.resource_search.models.SearchDetails.MATCHING_CONTEXT_TYPE_NONE)
    fns = search_client.search_resources(structured_search).data
    return fns


def put_object(namespace_name, bucket_name, object_name, put_object_body):
    """ Adds an object to object storage

    Parameters:
    namespace_name: The name of the namespace
    bucket_name: The name of the bucket
    object_name: The name of the object
    put_object_body: Body of the object

    Returns:
    None
    """
    print("[INFO] Adding object to a bucket.")
    os_client.put_object(namespace_name, bucket_name,
                         object_name, put_object_body)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description="Creates the limits functions for all of the regions")

    parser.add_argument("-user", dest="user", type=str, required=True,
                        help="The user used for connecting to the docker registry. tenancy_namespace\\user_email or tenancy_namespace\\federation_client\\user_email \n")

    parser.add_argument("-password", dest="password", type=str, required=True,
                        help="The auth token value used for logging in to the docker registry\n")

    parser.add_argument("-compartment_id", dest="compartment_id", type=str, required=True,
                        help="The comp id in which the functions will be created\n")

    parser.add_argument("-app_name", dest="app_name", type=str, required=True,
                        help="The name of the app in which the functions will be created\n")

    parser.add_argument("-topic_id", dest="topic_id", type=str, required=True,
                        help="The id of the topic used for publishing limit messages \n")

    parser.add_argument("-percentage", dest="percentage", type=str, required=True,
                        help="The threshold percentage \n")

    parser.add_argument("-bucket_name", dest="bucket_name", type=str, required=True,
                        help="The name of the bucket used by the main function \n")

    parser.add_argument("-fn_prefix", dest="fn_prefix", type=str, required=True,
                        help="The prefix name of the fn \n")

    args = parser.parse_args()

    config, identity_client, fn_mgmt_client, os_client, events_client, search_client = initialize()

    tenancy_namespace = os_client.get_namespace().data

    regions = identity_client.list_region_subscriptions(config["tenancy"])

    get_context = Popen('fn list contexts | grep limit_context',
                        stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = get_context.communicate()
    if len(stdout) == 0:
        create_context = Popen('fn create context limit_context --provider oracle',
                               stdout=PIPE, stderr=PIPE, shell=True)
        stdout, stderr = create_context.communicate()
        print(stdout)
    else:
        print("Context already exists")

    use_context = Popen('fn use context limit_context',
                        stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = use_context.communicate()

    update_context_with_comp = Popen('fn update context oracle.compartment-id {}'.format(
        args.compartment_id), stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = update_context_with_comp.communicate()

    home_region = [i for i in regions.data if i.is_home_region == True]
    home_region_name = home_region[0].region_name
    home_region_key = str(home_region[0].region_key).lower()

    docker_login = Popen("docker login -u {} -p '{}' {}".format(args.user,
                                                                args.password, "{}.ocir.io".format(home_region_key)), stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = docker_login.communicate()

    update_api_url = Popen(
        'fn update context api-url https://functions.{}.oci.oraclecloud.com'.format(home_region_name), stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = update_api_url.communicate()

    update_context_registry = Popen(
        'fn update context registry {}.ocir.io/{}/limits'.format(home_region_key, tenancy_namespace), stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = update_context_registry.communicate()

    main_config = '''
schema_version: 20180708
name: main_{{ fn_prefix }}
version: 0.0.1
runtime: python
entrypoint: /python/bin/fdk /function/func.py handler
memory: 256
timeout: 300
config:
  bucket_name: {{ bucket_name }}
  fn_prefix: {{ fn_prefix }}_'''

    main_tm = Template(main_config)
    msg = main_tm.render(fn_prefix=args.fn_prefix,
                         bucket_name=args.bucket_name)
    os.chdir("../main")
    with open('./func.yaml', "w") as myfile:
        myfile.write(msg)

    print("Publishing main function")
    add_main_to_app = Popen(
        'fn deploy --app {}'.format(args.app_name), stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = add_main_to_app.communicate()

    fn_config = '''
schema_version: 20180708
name: {{ fn_prefix }}_{{ region_key }}
version: 0.0.1
runtime: python
entrypoint: /python/bin/fdk /function/func.py handler
memory: 1024
timeout: 300
config:
  regions: {{ region_name }}
  percentage: {{ percentage }}
  topic_id: {{ topic_id }}'''

    os.chdir("../fn")
    tm = Template(fn_config)

    for reg in regions.data:
        msg = tm.render(fn_prefix=args.fn_prefix, region_key=str(reg.region_key).lower(
        ), region_name=reg.region_name, percentage=args.percentage, topic_id=args.topic_id)
        with open('./func.yaml', "w") as myfile:
            myfile.write(msg)
        print("Publishing function for region {}".format(reg.region_name))
        add_func_to_app = Popen(
            'fn deploy --app {}'.format(args.app_name), stdout=PIPE, stderr=PIPE, shell=True)
        stdout, stderr = add_func_to_app.communicate()

    fn_details = get_function("main_{}".format(args.fn_prefix))
    create_rule(comp_id=args.compartment_id, fn_prefix=args.fn_prefix, fn_id=fn_details.items[0].identifier,
                bucket_name=args.bucket_name)

    try:
        put_object(tenancy_namespace, args.bucket_name,
                   "main.txt", "Limit scheduler")
    except Exception as e:
        print(e)
        if e.status == 429:
            raise
