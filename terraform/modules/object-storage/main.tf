// Copyright (c) 2020, Oracle and/or its affiliates. All rights reserved.
// Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.

terraform {
  required_providers {
    oci = {
      configuration_aliases = []
    }
  }
}

data "oci_objectstorage_namespace" "this" {
  compartment_id = var.oci_provider["tenancy"]
}

resource "oci_objectstorage_bucket" "this" {
  for_each              = var.bucket_params
  compartment_id        = var.compartment_ids[each.value.compartment_name]
  name                  = each.value.name
  namespace             = data.oci_objectstorage_namespace.this.namespace
  access_type           = each.value.access_type
  storage_tier          = each.value.storage_tier
  object_events_enabled = each.value.events_enabled
  kms_key_id            = length(var.kms_key_ids) == 0 || each.value.kms_key_name == "" ? "" : var.kms_key_ids[each.value.kms_key_name]
}

resource "oci_objectstorage_object_lifecycle_policy" "this" {
  for_each  = var.objectlifecycle_params
  bucket    = oci_objectstorage_bucket.this[each.value.bucket_name].name
  namespace = data.oci_objectstorage_namespace.this.namespace

  dynamic "rules" {
    iterator = rule
    for_each = each.value.rules
    content {
      action      = rule.value.action
      is_enabled  = rule.value.is_enabled
      name        = rule.value.rule_name
      time_amount = rule.value.time_amount
      time_unit   = rule.value.time_unit
    }
  }
}
