// Copyright (c) 2020, Oracle and/or its affiliates. All rights reserved.
// Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.
output "topic" {
  value = {
    for topic in oci_ons_notification_topic.this :
    topic.name => topic.id
  }
}
