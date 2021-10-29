import io
import json
import logging
import oci
from datetime import datetime, timezone

from oci.identity.models import region
import logging
import os
from oci.config import from_file

identity_client = None
fn_mgmt_client = None
os_client = None
search_client = None
invoke_client = None


def initialize(region=None):
    """Creates OCI python sdk clients

    Parameters:
    region - the region in which you want to spawn the config

    Returns:
    limits_client - Client used for making limit requests

    quotas_client - Client used for making quotas requests

    identity_client - Client used for making IAM requests

    search_client - Client used for making search requests

    notifications_client - Client used for making notifications requests

    os_client - Client used for making object storage requests
    """

    config = from_file()

    global limits_client
    global quotas_client
    global search_client
    global identity_client
    global notifications_client
    global os_client
    identity_client = oci.identity.IdentityClient(config)
    regions = identity_client.list_region_subscriptions(config["tenancy"])

    home_region = [i for i in regions.data if i.is_home_region == True]
    home_region_name = home_region[0].region_name

    limits_client = oci.limits.LimitsClient(
        config)
    search_client = oci.resource_search.ResourceSearchClient(
        config)
    identity_client = oci.identity.IdentityClient(
        config)

    return config, limits_client, quotas_client, search_client, identity_client, notifications_client, os_client


def initialize(region=None):
    """Creates OCI python sdk clients

    Parameters:
    region - the region in which you want to spawn the config

    Returns:

    identity_client - Client used for making IAM requests
    """

    global identity_client
    global fn_mgmt_client
    global os_client
    global search_client
    global invoke_client

    config = from_file()
    identity_client = oci.identity.IdentityClient()
    regions = identity_client.list_region_subscriptions(signer.tenancy_id)

    home_region = [i for i in regions.data if i.is_home_region == True]
    home_region_name = home_region[0].region_name

    search_client = oci.resource_search.ResourceSearchClient(
        config)
    identity_client = oci.identity.IdentityClient(
        config)

    fn_mgmt_client = oci.functions.FunctionsManagementClient(config)

    os_client = oci.object_storage.ObjectStorageClient(config)

    return config, identity_client, fn_mgmt_client, os_client, search_client


def get_app(app_name):
    """ Gets app

    Parameters:
    app_name - The name of the application

    Returns:
    The application and its details
    """

    structured_search = oci.resource_search.models.StructuredSearchDetails(query="query functionsapplication resources where displayName='{}'".format(app_name),
                                                                           type='Structured',
                                                                           matching_context_type=oci.resource_search.models.SearchDetails.MATCHING_CONTEXT_TYPE_NONE)
    apps = search_client.search_resources(structured_search).data
    return apps


def get_functions(fn_name):
    """ Gets functions

    Parameters:
    fn_name - The name prefix of the function

    Returns:
    The functions and their details
    """

    structured_search = oci.resource_search.models.StructuredSearchDetails(query="query functionsfunction resources where displayName=~'{}'".format(fn_name),
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
    config, identity_client, fn_mgmt_client, os_client, search_client = initialize()
    namespace = os_client.get_namespace().data

    fn_config = {
        "bucket_name": "hur-buck-9",
        "fn_prefix": "lim_"
    }
    bucket_name = fn_config["bucket_name"]
    fn_prefix = fn_config["fn_prefix"]
    fn = get_functions(str(fn_prefix))

    required_fn = [{fn.display_name: fn.identifier}
                   for fn in fn.items]

    print(required_fn)
    # for fn in required_fn:
    #     for key, value in fn.items():
    #         fn_details = fn_mgmt_client.get_function(value).data
    #         invoke_client = oci.functions.FunctionsInvokeClient(
    #             {}, service_endpoint=fn_details.invoke_endpoint, signer=signer)
    #         print("Invoking fn {} with id {}".format(key, value))
    #         invoke_client.invoke_function(value, fn_invoke_type="detached")

    # try:
    #     put_object(namespace, bucket_name, "main.txt", "Limit scheduler")
    # except Exception as e:
    #     print(e)
    #     if e.status == 429:
    #         raise
