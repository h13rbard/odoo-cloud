variable "resource_group_name" {
  description = "Nombre del Grupo de Recursos en Azure"
  type        = string
  default     = "rg-odoo-production"
}

variable "location" {
  description = "Región de Azure donde se desplegarán los recursos"
  type        = string
  default     = "eastus2" # Puedes cambiarlo a 'southcentralus' o la región más cercana a ti
}

variable "vm_size" {
  description = "Tamaño de la instancia para soportar la carga analítica de las 45k ventas"
  type        = string
  default     = "Standard_B2s" # 2 vCPUs, 4 GB RAM. Ideal para Odoo 17 + Postgres en producción.
}

variable "admin_username" {
  description = "Usuario administrador para el Hardening de la VM"
  type        = string
  default     = "azureuser"
}
