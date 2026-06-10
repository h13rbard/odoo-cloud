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


variable "ssh_public_key" {
  description = "Llave pública SSH"
  type        = string
  default     = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC07D5lYSXXdqZeoG5qPakd/JUjNEHRORIwpdvv3RFeWi1KBcHE7LQqXLUlRCgGsMnEM984S4UcxRInxzYIQU6AIk6CVH0RerM7zPmnMcGHFdgHZ11vmDWdkrOkUjrA6sNORS7kox7spV7SEWkLOj13A4Z5hA9glwhCijSIECNqqQX9umSHkFcrE4diinx9TUScR0LXpbqNGnvWNVgIM4LKvcYIsa8GGdbH40l5Ud2YZmKqUJaBn4szQKxMkNG4CdB1/RXaEb8AqbnIiempXAWZRYcEwd8EQmCCKBA4u1rO2jUtHPTnDaN/uU8TEDDu2Cvdm/usrO8cTK7zEKIE3F8k2Jq+3d6XaBhhBZu0HWfSPhOfk46FEPjIB7llPloYPScCWW62kvCgj87SWnsi7QPql1q3t7M8bfSLiRsvn8fzexn0NeTrqEVcv1n5J5ilNySi41hjN7uSAr5ju4JmJWvLsgf5nIEAuq7GjcK5qrcptF7QwtuRv0eAsmLsuitk6+t6acVeqvnvS2rNKlIp8PDh52u6HoWBqe86mHJmWZ7fzIs7FT8guYPBn0/d+HWmdIuNS1sPcpkMxAhOgo2s9nKJcV5PxzF1MDkFs+SWBymts25BWzCuE+wsIAEVQbD7TSGB0s91WgwzaGpjq/3kz8s9USoK0FCwZzJv4CzQ8MRH7Q== azureuser@odoo-prod" 
}
