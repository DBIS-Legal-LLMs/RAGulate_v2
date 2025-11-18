# Initialization of Anaconda and LIGHTRAGENV (Python)

### 1. Start conda
```bash
source ~/anaconda3/bin/activate
```

### 2. Update conda
```bash
conda update -n base -c defaults conda
```

### 3. Create conda environment
```bash
conda create -n LIGHTRAGENV
```

### 4. Install pip in LIGHTRAGENV
```bash
conda install pip
```

### 5. Install project requirements
```bash
pip install -r requirements.txt
```