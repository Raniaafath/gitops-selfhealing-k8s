variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
  default     = "gitops-demo-rg"
}

variable "location" {
  description = "Azure region for the resource group and AKS cluster"
  type        = string
  default     = "francecentral"
}

variable "cluster_name" {
  description = "Name of the AKS cluster"
  type        = string
  default     = "gitops-demo-aks"
}

variable "node_count" {
  description = "Number of nodes in the default node pool"
  type        = number
  default     = 2
}

variable "node_vm_size" {
  description = "VM size for the default node pool (Standard_B2s is a low-cost burstable size, suitable for a demo)"
  type        = string
  default     = "Standard_B2s"
}
