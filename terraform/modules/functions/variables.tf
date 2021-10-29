// Copyright (c) 2020, Oracle and/or its affiliates. All rights reserved.
// Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.
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
