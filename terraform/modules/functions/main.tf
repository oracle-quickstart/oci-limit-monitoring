// Copyright (c) 2020, Oracle and/or its affiliates. All rights reserved.
// Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.

terraform {
  required_providers {
    oci = {
      configuration_aliases = []
    }
  }
}

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_ids[var.app_params[keys(var.app_params)[0]].compartment_name]
}

resource "oci_functions_application" "this" {
  for_each       = var.app_params
  compartment_id = var.compartment_ids[each.value.compartment_name]
  subnet_ids     = [for i in each.value.subnet_name : var.subnet_ids[i]]
  display_name   = each.value.display_name
  config         = each.value.config
  freeform_tags  = each.value.freeform_tags
}
