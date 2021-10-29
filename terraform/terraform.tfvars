// Copyright (c) 2020, Oracle and/or its affiliates. All rights reserved.
// Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.

compartment_ids = {
    sandbox = "ocid1.compartmen"
}

subnet_ids = {
  hur1pub  = "ocid1.subnet."
}

app_params = {
  thunder_app99 = {
    compartment_name = "sandbox"
    subnet_name      = ["hur1pub"]
    display_name     = "thunder_app99"
    config = {
      "MY_FUNCTION_CONFIG" : "ConfVal"
    }
    freeform_tags = {
    }
  }
}

bucket_params = {
  hur-buck-99 = {
    compartment_name = "sandbox"
    name             = "hur-buck-99"
    access_type      = "NoPublicAccess"
    storage_tier     = "Standard"
    events_enabled   = true
    kms_key_name     = ""
  }
}

kms_key_ids = {}

objectlifecycle_params = {
  lifecycle99 = {
    bucket_name = "hur-buck-99"
    rules       = [
      {
        rule_name   = "lifecycle99"
        is_enabled  = true
        action      = "DELETE"
        time_amount = 7
        time_unit   = "DAYS"
      }
    ]    
  }
}

topic_params = {
    topic99 = {
        comp_name   = "sandbox"
        topic_name  = "topic99"
        description = "test topic"
    }
}

subscription_params = {
    subscription99 = {
        comp_name  = "sandbox"
        endpoint   = "flavius.dinu@oracle.com"
        protocol   = "EMAIL"
        topic_name = "topic99"
    }
}
