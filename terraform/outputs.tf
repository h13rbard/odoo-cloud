output "resource_group_name" {
  value = azurerm_resource_group.rg.name
}

output "public_ip_address" {
  description = "IP pública de la VM de Azure asignada a jgerardogm.lat"
  value       = azurerm_public_ip.public_ip.ip_address
}
