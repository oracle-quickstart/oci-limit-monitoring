// Copyright (c) 2020, Oracle and/or its affiliates. All rights reserved.
// Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.
// Copyright (c) 2017, 2020, Oracle and/or its affiliates. All rights reserved.

output "apps" {
  value = {
    for app in oci_functions_application.this:
    app.display_name => app.id
  }
}