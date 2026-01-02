# Integrated LLM
### Introduction
This app helps to use local or cloud LLM from Ollama to diretly read from your computer

### Preparations
1. You need to install Ollama from official site ```curl -fsSL https://ollama.ai/install.sh | sh```

2. If you want use local LLM, you can install from official ```ollama pull <model>```
3. Launch ollama server ```ollama serve```
4. Activate virtual environment ```source .venv/bin/activate```
5. run app ```main.py```

### Using
📁 **Файловые операции:**

!read <file> [file2]     - read file(s)

!read folder <path>      - read all files in directory

!analyze <file>          - analyze code from file

!info <file>             - info about file

!search <pattern>        - file search

**🚀 Управление LLM:**

!provider <name>         - change provider for LLM

!model <name>            - change LLM modwel

!models [provider]       - показать доступные модели

!set <provider> <key>   - установить API ключ

!test [provider]         - проверить соединение


### Example
!read main.py

!analyze utils.py

!provider openai
