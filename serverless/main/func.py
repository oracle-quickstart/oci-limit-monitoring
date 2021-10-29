import io
import json
import logging
import oci
from datetime import datetime, timezone

from oci.identity.models import region
import logging
import os
from fdk import response

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

    identity_client - Client used for making IAM requests
    """

    signer = oci.auth.signers.get_resource_principals_signer()

    global identity_client
    global fn_mgmt_client
    global os_client
    global search_client
    global invoke_client
    identity_client = oci.identity.IdentityClient({}, signer=signer)
    regions = identity_client.list_region_subscriptions(signer.tenancy_id)

    home_region = [i for i in regions.data if i.is_home_region == True]
    home_region_name = home_region[0].region_name

    identity_client = oci.identity.IdentityClient(
        config={"region": home_region_name}, signer=signer)
    fn_mgmt_client = oci.functions.FunctionsManagementClient(
        config={"region": home_region_name}, signer=signer)
    os_client = oci.object_storage.ObjectStorageClient(
        config={"region": home_region_name}, signer=signer)
    search_client = oci.resource_search.ResourceSearchClient(
        config={"region": home_region_name}, signer=signer)
    return signer, identity_client, fn_mgmt_client, os_client, search_client


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


def handler(ctx, data: io.BytesIO = None):
    signer, identity_client, fn_mgmt_client, os_client, search_client = initialize()
    namespace = os_client.get_namespace().data

    fn_config = ctx.Config()
    bucket_name = fn_config["bucket_name"]
    fn_prefix = fn_config["fn_prefix"]
    fn = get_functions(str(fn_prefix))

    required_fn = [{fn.display_name: fn.identifier}
                   for fn in fn.items]

    for fn in required_fn:
        for key, value in fn.items():
            fn_details = fn_mgmt_client.get_function(value).data
            invoke_client = oci.functions.FunctionsInvokeClient(
                {}, service_endpoint=fn_details.invoke_endpoint, signer=signer)
            print("Invoking fn {} with id {}".format(key, value))
            invoke_client.invoke_function(value, fn_invoke_type="detached")

    try:
        put_object(namespace, bucket_name, "main.txt", "Limit scheduler")
    except Exception as e:
        print(e)
        if e.status == 429:
            raise

    return response.Response(
        ctx, response_data=json.dumps({"Success": "200"}),
        headers={"Content-Type": "application/json"}
    )
