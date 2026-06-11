# 1. DEFINICIÓN DE PROVEEDORES Y BACKEND
terraform {
  required_version = ">= 1.0.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# 2. GRUPO DE RECURSOS
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
}

# 3. RED VIRTUAL (VNet) Y SUBRED
resource "azurerm_virtual_network" "vnet" {
  name                = "vnet-odoo-prod"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_subnet" "subnet" {
  name                 = "snet-odoo-backend"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

# 4. IP PÚBLICA ESTÁTICA (Para amarrar tu dominio jgerardogm.lat)
resource "azurerm_public_ip" "public_ip" {
  name                = "pip-odoo-prod"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

# 5. FIREWALL / NETWORK SECURITY GROUP (NSG)
resource "azurerm_network_security_group" "nsg" {
  name                = "nsg-odoo-prod"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  # Regla SSH (Gestión y CI/CD)
  security_rule {
    name                       = "allow-ssh"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Regla HTTP (Nginx / Certbot validation)
  security_rule {
    name                       = "allow-http"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Regla HTTPS (Tráfico Seguro de Producción)
  security_rule {
    name                       = "allow-https"
    priority                   = 1003
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# 6. INTERFAZ DE RED (NIC) Y ASOCIACIÓN DEL NSG
resource "azurerm_network_interface" "nic" {
  name                = "nic-odoo-prod"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.public_ip.id
  }
}

resource "azurerm_network_interface_security_group_association" "nic_nsg_assoc" {
  network_interface_id      = azurerm_network_interface.nic.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}


# 7. MÁQUINA VIRTUAL DE PRODUCCIÓN (Rocky Linux 9.0)
resource "azurerm_linux_virtual_machine" "vm" {
  name                = "vm-odoo-rockylinux9"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  size                = var.vm_size
  admin_username      = var.admin_username

  # ✨ PROPIEDADES OBLIGATORIAS PARA LA SERIE DCas_v6 (Confidential Computing)
  secure_boot_enabled = true
  vtpm_enabled        = true
  security_type       = "TrustedLaunch" # 👈 Esto elimina el error de <NULL>
  
  network_interface_ids = [
    azurerm_network_interface.nic.id,
  ]

  # Autenticación segura por Llave Pública SSH
  admin_ssh_key {
    username   = var.admin_username
    public_key = var.ssh_public_key # 👈 Cambiamos a una variable
  }
  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS" # SSD Premium para evitar cuellos de botella con Postgres
    disk_size_gb         = 30            # Espacio óptimo para Odoo, filestore y logs
  }

  # 🚀 ESTRUCTURA PERFECTA PARA ROCKY LINUX 9 CON LVM
  source_image_reference {
    publisher = "resf"
    offer     = "rockylinux-x86_64"
    sku       = "9-lvm"               # Cambiamos a '9-lvm' para heredar la estructura de volúmenes compatible
    version   = "latest"
  }
}
