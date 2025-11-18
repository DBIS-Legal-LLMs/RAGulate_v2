# Setup of Anaconda (Python)

### 1. Download Anaconda (Linux)
```bash
curl -O https://repo.anaconda.com/archive/Anaconda3-2025.06-0-Linux-x86_64.sh
```

### 2. Install Anaconda (Linux)
```bash
bash ~/Anaconda3-2025.06-0-Linux-x86_64.sh
```
- Press return to continue
- Enter yes to agree to the TOS
- Press return to continue
- Enter no (you have to activate conda manually every time, but rather do this than screwing your system)

### 3. Refresh terminal (Linux)
```bash
source ~/.bashrc
```

### 4. Activate conda manually
```bash
source ~/anaconda3/bin/activate
```

### Optional: 
Activate conda to run automatically
```bash
conda config --set auto_activate_base True
```

Deactivate conda to run manually
```bash
conda config --set auto_activate_base False
```