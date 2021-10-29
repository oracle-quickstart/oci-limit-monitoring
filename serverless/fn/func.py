import io
import json
import logging
import oci
from datetime import datetime, timezone

from oci.identity.models import region
import backoff
import logging
import os

from fdk import response

limits_client = None
quotas_client = None
search_client = None
logger = None
identity_client = None
notifications_client = None
os_client = None


def create_log():
    """ Creates logging file

    Parameters: None

    Returns: A logger instance
    """
    global logger
    if not os.path.exists("/tmp/limits"):
        os.makedirs("/tmp/limits")
    now = datetime.now(timezone.utc)
    LOG_FILENAME = '/tmp/limits/limits'
    filename = LOG_FILENAME + now.strftime('_%Y%m%dT%H%M.log')
    try:
        logging.basicConfig(filename=filename, level=logging.INFO,
                            filemode='w', datefmt='%m/%d/%Y %I:%M:%S%p',
                            format='%(asctime)s %(message)s')
        logger = logging.getLogger("limits")
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S%p')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    except Exception as e:
        logger.info("There is a problem on creating logger: {}".format(e))
    return logger


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

    signer = oci.auth.signers.get_resource_principals_signer()

    global limits_client
    global quotas_client
    global search_client
    global identity_client
    global notifications_client
    global os_client
    identity_client = oci.identity.IdentityClient({}, signer=signer)
    response = identity_client.list_region_subscriptions(signer.tenancy_id)
    for reg in response.data:
        if reg.is_home_region:
            quotas_client = oci.limits.QuotasClient(
                config={"region": reg.region_name}, signer=signer)
            notifications_client = oci.ons.NotificationDataPlaneClient(
                config={"region": reg.region_name}, signer=signer)
            os_client = oci.object_storage.ObjectStorageClient(
                config={"region": reg.region_name}, signer=signer)
            break

    if region != None:
        limits_client = oci.limits.LimitsClient(
            config={"region": region}, signer=signer)
        search_client = oci.resource_search.ResourceSearchClient(
            config={"region": region}, signer=signer)
        identity_client = oci.identity.IdentityClient(
            config={"region": region}, signer=signer)
    else:
        limits_client = oci.limits.LimitsClient({}, signer=signer)
        search_client = oci.resource_search.ResourceSearchClient(
            {}, signer=signer)
        identity_client = oci.identity.IdentityClient({}, signer=signer)
    return signer, limits_client, quotas_client, search_client, identity_client, notifications_client, os_client


def is_throttling_error(err):
    """ Returns a bool depending if the status of the error is 429 or not

    Parameters:
    err - Error received from a request

    Returns:
    True or False
    """

    if err.status == 429:
        return False
    return True


@backoff.on_exception(backoff.expo, exception=oci.exceptions.ServiceError, max_time=300, giveup=is_throttling_error)
def get_compartment(comp_name):
    """ Gets compartment

    Parameters:
    comp_name - The name of the compartment

    Returns:
    The compartment and its details
    """

    structured_search = oci.resource_search.models.StructuredSearchDetails(query="query compartment resources where displayName='{}'".format(comp_name),
                                                                           type='Structured',
                                                                           matching_context_type=oci.resource_search.models.SearchDetails.MATCHING_CONTEXT_TYPE_NONE)
    comps = search_client.search_resources(structured_search).data
    return comps


@backoff.on_exception(backoff.expo, exception=oci.exceptions.ServiceError, max_time=300, giveup=is_throttling_error)
def get_topic(topic_name):
    """ Gets topic

    Parameters:
    topic_name - The name of the compartment

    Returns:
    The topic and its details
    """

    structured_search = oci.resource_search.models.StructuredSearchDetails(query="query onstopic resources where displayName='{}'".format(topic_name),
                                                                           type='Structured',
                                                                           matching_context_type=oci.resource_search.models.SearchDetails.MATCHING_CONTEXT_TYPE_NONE)
    topics = search_client.search_resources(structured_search).data
    return topics


@backoff.on_exception(backoff.expo, exception=oci.exceptions.ServiceError, max_time=300, giveup=is_throttling_error)
def list_quotas(compartment_id):
    """ Lists quotas

    Parameters:
    compartment_id: The id of the compartment that should be used for listing quotas

    Returns:
    Quotas for the tenancy
    """
    logger.info(
        "[INFO] Getting quotas for compartment: {}".format(compartment_id))
    return quotas_client.list_quotas(compartment_id=compartment_id).data


@backoff.on_exception(backoff.expo, exception=oci.exceptions.ServiceError, max_time=300, giveup=is_throttling_error)
def list_services(tenancy_id):
    """ Lists Services

    Parameters:
    tenancy_id: The id of the tenancy

    Returns:
    Services for a specific compartment
    """
    logger.info("[INFO] Getting services for tenancy: {}".format(tenancy_id))
    return limits_client.list_services(compartment_id=tenancy_id).data


@backoff.on_exception(backoff.expo, exception=oci.exceptions.ServiceError, max_time=300, giveup=is_throttling_error)
def list_limit_values(tenancy_id, service_name):
    """ Lists limit values

    Parameters:
    tenancy_id: The id of the tenancy that should be used for listing quotas
    service_name: The name of the service

    Returns:
    Limits for a specific service
    """
    logger.info("[INFO] Getting limits for tenancy: {}".format(tenancy_id))
    return oci.pagination.list_call_get_all_results(limits_client.list_limit_values, compartment_id=tenancy_id, service_name=service_name).data


@backoff.on_exception(backoff.expo, exception=oci.exceptions.ServiceError, max_time=300, giveup=is_throttling_error)
def get_resource_availability(tenancy_id, service_name, limit_name, ad=None):
    """ Lists quotas

    Parameters:
    tenancy_id: The id of the tenancy that should be used for listing quotas

    Returns:
    Limits for a specific service
    """
    # logger.info("[INFO] Getting percentage for tenancy: {}".format(tenancy_id))
    if ad != None:
        return limits_client.get_resource_availability(compartment_id=tenancy_id, service_name=service_name, limit_name=limit_name, availability_domain=ad).data
    else:
        return limits_client.get_resource_availability(compartment_id=tenancy_id, service_name=service_name, limit_name=limit_name).data


@backoff.on_exception(backoff.expo, exception=oci.exceptions.ServiceError, max_time=300, giveup=is_throttling_error)
def list_limit_definition(tenancy_id):
    """ Lists Limit definitions

    Parameters:
    tenancy_id: The id of the tenancy

    Returns:
    Limit definitions for a specific compartment
    """
    logger.info(
        "[INFO] Getting limit definitions for tenancy: {}".format(tenancy_id))
    return oci.pagination.list_call_get_all_results(limits_client.list_limit_definitions, compartment_id=tenancy_id).data


@backoff.on_exception(backoff.expo, exception=oci.exceptions.ServiceError, max_time=300, giveup=is_throttling_error)
def publish_message(topic_id, body, title):
    """ Publishes message to a topic

    Parameters:
    topic_id: The id of the topic
    body: The body of the message that should be published
    title: The title of the message that should be published

    Returns:
    None
    """
    logger.info("[INFO] Publishing alert to topic.")
    notifications_client.publish_message(topic_id, oci.ons.models.MessageDetails(
        body=body,
        title=title
    ))


def check_limits(tenancy, topic_id, region, percentage, services):
    limit_values = {}
    body_email = []
    try:
        limits = list_limit_definition(tenancy)
    except Exception as e:
        logger.info(e)
        if e.status_code == "429":
            raise
    if len(services) > 0:
        limits = [limit for limit in limits if limit.service_name in services]

    for limit in limits:
        if limit.scope_type == "AD":
            try:
                ads = identity_client.list_availability_domains(tenancy)
            except Exception as e:
                logger.info(e)

            for ad in ads.data:
                try:
                    resource_availability = get_resource_availability(
                        tenancy, limit.service_name, limit.name, ad.name)
                except Exception as e:
                    logger.info(e)
                    if e.status_code == "429":
                        raise
                if resource_availability.used != None and resource_availability.available != None:
                    if int(resource_availability.used) + int(resource_availability.available) > 0:
                        total_available = int(resource_availability.available)*100/(
                            int(resource_availability.used)+int(resource_availability.available))
                        logger.info("Service {}       Ad {}              Limit_Name {}              Available {}        Used {}       Total {}{}".format(
                            limit.service_name, ad.name, limit.name, resource_availability.available, resource_availability.used, total_available, '%'))
                        limit_values[limit.name + "_" + region] = "Available Resources: {}{}".format(
                            total_available, '%')
                        if int(total_available) < percentage:
                            body = "Limit reached for {}. Info: Service {}, Scope {}, AD {}, Limit_Name {}, Available {}, Used {}, Total {}{}".format(
                                limit.name, limit.service_name, limit.scope_type, ad.name, limit.name, resource_availability.available, resource_availability.used, total_available, '%')
                            body_email.append(body)

        else:
            try:
                resource_availability = get_resource_availability(
                    tenancy, limit.service_name, limit.name)
            except Exception as e:
                logger.info(e)
                if e.status_code == "429":
                    raise
            if resource_availability.used != None and resource_availability.available != None:
                if int(resource_availability.used) + int(resource_availability.available) > 0:
                    total_available = int(resource_availability.available)*100/(
                        int(resource_availability.used)+int(resource_availability.available))
                    logger.info("Service {}       Scope {}       Limit_Name {}       Available {}        Used {}       Total {}{}".format(
                        limit.service_name, limit.scope_type, limit.name, resource_availability.available, resource_availability.used, total_available, '%'))
                    limit_values[limit.name + "_" + region] = "Available Resources: {}{}".format(
                        total_available, '%')
                    if int(total_available) < percentage:
                        body = "Limit reached for {}. Info: Service {}, Scope {}, Limit_Name {}, Available {}, Used {}, Total {}{}".format(
                            limit.name, limit.service_name, limit.scope_type, limit.name, resource_availability.available, resource_availability.used, total_available, '%')
                        body_email.append(body)

    title = "Region {} Limit exceeds for {} {} treshold".format(
        region, percentage, '%')
    message_body = "\n\n".join(str(body) for body in body_email)
    if len(message_body) > 0:
        publish_message(topic_id, message_body, title)
    return limit_values


def main(regions, topic_id, percentage, services):
    signer, limits_client, quotas_client, search_client, identity_client, notifications_client, os_client = initialize()
    tenancy = signer.tenancy_id
    region_data = identity_client.list_region_subscriptions(tenancy)
    namespace = os_client.get_namespace().data
    limits = []
    for reg in region_data.data:
        signer, limits_client, quotas_client, search_client, identity_client, notifications_client, os_client = initialize(
            region=reg.region_name)
        if len(regions) == 0:
            limit_values = check_limits(
                tenancy, topic_id, reg.region_name, percentage, services)
            limits.append(limit_values)
        else:
            if ',' not in regions:
                region_list = regions
            else:
                region_list = regions.split(',')
            if reg.region_name in region_list:
                limit_values = check_limits(
                    tenancy, topic_id, reg.region_name, percentage, services)
                limits.append(limit_values)
    return limits, namespace


def handler(ctx, data: io.BytesIO = None):
    config = ctx.Config()
    percentage = config["percentage"]
    if "regions" in config:
        regions = config["regions"]
    else:
        regions = []
    if "topic_id" not in config:
        exit(1)
    else:
        topic_id = config["topic_id"]

    if "services" in config:
        if ',' not in config["services"]:
            services = config["services"]
        else:
            services = config["services"].split(',')
    else:
        services = []

    create_log()

    limits, namespace = main(regions, topic_id, int(percentage), services)

    return response.Response(
        ctx, response_data=json.dumps(limits),
        headers={"Content-Type": "application/json"}
    )
