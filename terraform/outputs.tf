output "buckets" {
  value = module.object-storage.buckets
}

output "topic" {
  value = module.notifications.topic
}

output "apps" {
  value = module.functions.apps
}