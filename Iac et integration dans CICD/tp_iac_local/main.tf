terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "4.6.0"
    }
  }
}

provider "docker" {

}

#configure the database
resource "docker_image" "postgres_image"{
    name= "postgres:latest"
    keep_locally = true
}

resource "docker_container" "db_container"{
    name="tp_db_postgres"
    image = docker_image.postgres_image.image_id


    ports{
        internal = 5432
        external = 5432
    }

    # Configuration de la DB via les variables d'environnement

    env = [
    "POSTGRES_USER=${var.utilisateur}",

    "POSTGRES_PASSWORD=${var.password}",
    "POSTGRES_DB=${var.name_db}",
    ]
}


# Resource 2: Web APP 
# Construit l'image de l'application à partir du Dockerfile_app local
resource "docker_image" "app_image" {
    name = "tp-web-app:latest"

    build {

    context ="."

    dockerfile = "Dockerfile_app"
    }
}


# Crée le conteneur de l'application web
resource "docker_container" "app_container" {
    name = "tp-app-web"
    image = docker_image.app_image.image_id

    # Dépendance explicite : la DB doit être prête avant l'Application
    depends_on = [
    docker_container.db_container

    ]

    # Mappage du port 80 interne au port externe défini dans variables.tf (par défaut 8080)
    ports {

    internal = 80

    external = var.app_port_external
    }
}

