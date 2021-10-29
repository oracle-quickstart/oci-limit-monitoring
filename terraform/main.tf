// Copyright (c) 2020, Oracle and/or its affiliates. All rights reserved.
// Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.
data "oci_identity_regions" "this" {
}

data "oci_identity_tenancy" "this" {
  tenancy_id = var.provider_oci.tenancy
}

locals {
  region_map = { for region in data.oci_identity_regions.this.regions : region.key => region.name }
}

provider "oci" {
  tenancy_ocid     = var.provider_oci.tenancy
  user_ocid        = var.provider_oci.user_id
  fingerprint      = var.provider_oci.fingerprint
  private_key_path = var.provider_oci.key_file_path
  region           = var.provider_oci.region
}

provider "oci" {
  alias            = "home"
  tenancy_ocid     = var.provider_oci.tenancy
  user_ocid        = var.provider_oci.user_id
  fingerprint      = var.provider_oci.fingerprint
  private_key_path = var.provider_oci.key_file_path
  region           = lookup(local.region_map, data.oci_identity_tenancy.this.home_region_key)
}

module "object-storage" {
  providers              = { oci = oci.home }
  source                 = "./modules/object-storage"
  compartment_ids        = var.compartment_ids
  bucket_params          = var.bucket_params
  objectlifecycle_params = var.objectlifecycle_params
  oci_provider           = var.provider_oci
  kms_key_ids            = var.kms_key_ids
}

module "notifications" {
  providers           = { oci = oci.home }
  source              = "./modules/notifications"
  topic_params        = var.topic_params
  subscription_params = var.subscription_params
  compartment_ids     = var.compartment_ids
}

module "functions" {
  providers       = { oci = oci.home }
  source          = "./modules/functions"
  compartment_ids = var.compartment_ids
  subnet_ids      = var.subnet_ids
  app_params      = var.app_params
}
