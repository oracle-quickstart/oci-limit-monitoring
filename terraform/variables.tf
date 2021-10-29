// Copyright (c) 2020, Oracle and/or its affiliates. All rights reserved.
// Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.

variable "provider_oci" {
  type = map(string)
}

variable "compartment_ids" {
  type = map(string)
}

variable "subnet_ids" {
  type = map(string)
}

variable "app_params" {
  type = map(object({
    compartment_name = string
    subnet_name      = list(string)
    display_name     = string
    config           = map(string)
    freeform_tags    = map(string)
  }))
}

variable "bucket_params" {
  type = map(object({
    compartment_name = string
    name             = string
    access_type      = string
    storage_tier     = string
    events_enabled   = bool
    kms_key_name     = string
  }))
}

variable "kms_key_ids" {
  type = map(string)
}


variable "objectlifecycle_params" {
  type = map(object({
    bucket_name = string
    rules = list(object({
      action      = string
      is_enabled  = bool
      rule_name   = string
      time_amount = number
      time_unit   = string
    }))
  }))
}

variable "topic_params" {
  type = map(object({
    comp_name   = string
    topic_name  = string
    description = string
  }))
}

variable "subscription_params" {
  type = map(object({
    comp_name  = string
    endpoint   = string
    protocol   = string
    topic_name = string
  }))
}