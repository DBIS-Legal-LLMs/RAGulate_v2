# Setup GPU support for docker

### 1. NVIDIA Treiber installieren
Auf dem Host (außerhalb von Docker) normalen NVIDIA Treiber installieren
Test:
```bash
nvidia-smi
```
Wenn du eine schöne Tabelle mit deiner GPU siehst, dann passt es!

### 2. NVIDIA Container Toolkit installieren
Damit Docker auf die GPU zugreifen kann, brauchst du das NVIDIA Container Toolkit.

Repo einrichten:
```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
```

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
```

```bash
sudo apt update
```

```bash
sudo apt install -y nvidia-container-toolkit
```

```bash
sudo nvidia-ctk runtime configure --runtime=docker
```

```bash
sudo systemctl restart docker
```

Du kannst testen, ob ein einfacher Docker Container die GPU sieht:
```bash
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

Wenn das klappt, und der Docker Container deine GPU sieht (selbe Tabelle wie bei $ nvidia-smi), kann Docker die GPU verwenden!