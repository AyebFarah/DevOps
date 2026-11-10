variable "utilisateur" {
    type = string
    default = "usr1"
}

variable "name_db"{
    type = string
    default = "DB_tp3"
}

variable "password"{
    type = string
    default = "NewPassword225"
}

variable "app_port_external" { 
    description = "Port externe pour accéder à l'application web (mappé au 80 interne)." 
    type  = number 
    default = 8080
} 



