# Setup of Docker for the project (Linux Ubuntu)
[Installation based on dockerdocs](https://docs.docker.com/engine/install/ubuntu/)

### 1. Uninstall all conflicting Docker packages
```bash
sudo apt remove $(dpkg --get-selections docker.io docker-compose docker-compose-v2 docker-doc podman-docker containerd runc | cut -f1)
```

### 2. Install using apt repository
Add dockers official GPG key:
```bash
sudo apt update
```

```bash
sudo apt install ca-certificates curl
```

```bash
sudo install -m 0755 -d /etc/apt/keyrings
```

```bash
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
```

```bash
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

Add repository to apt sources:
```bash
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF
```

```bash
sudo apt update
```

Install latest version:
```bash
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### Optional

Verify if docker is running:
```bash
sudo systemctl status docker
```

If docker is not running, start it manually:
```bash
sudo systemctl start docker
```

### 3. Verify the installation is successful
```bash
sudo docker run hello-world
```