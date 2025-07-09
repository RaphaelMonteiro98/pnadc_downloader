# PNADC Anual Microdados Downloader

Script Python para automatizar o download e extração dos microdados anuais da **PNADC** (Pesquisa Nacional por Amostra de Domicílios Contínua) do IBGE, incluindo aplicação de dicionário de variáveis e merge com deflator.

---

## ⚙️ Pré-requisitos

- **Python 3.8+**  
- Git instalado (opcional, para clonar o repositório).
- Instalar dependências:
  ```bash
  pip install -r requirements.txt
  ```

Conteúdo mínimo de `requirements.txt`:
```text
pandas==2.2.3
requests==2.32.3
tqdm==4.67.1
xlrd==2.0.1
```

---

## 📁 Estrutura do Repositório

```
pnadc_downloader/
├── download_pnadc.py                  # Script principal
├── requirements.txt                   # Dependências Python
├── README.md                          # Instruções de uso
└── PNADC_<ano>_visita<visita>_def_<deflator>/  # Após uso
    ├── Dados/                         # Microdados extraídos + CSV final
    └── Documentacao/                  # input (.txt), dicionário (.xls) e deflator (.xls)

```

---

## Instruções

1. **Instale as dependências**  
   ```bash
   pip install -r requirements.txt
   ```

2. **Execute o script**  
   ```bash
   python download_pnadc.py
   ```
   Você irá informar:
   - **Ano da pesquisa PNADC** (ex: `2024`)  
     - *Para 2020 e 2021*: aviso de que só existe a Visita 5.  
   - **Visita** (`1` ou `5`)  
   - **Ano do deflator** (ex: `2024`)

3. **O que o script faz**  
   - Cria as pastas `Dados/` e `Documentacao/` dentro de `PNADC<ano>/`.  
   - Baixa e extrai o arquivo ZIP de microdados em `Dados/`.  
   - Baixa arquivos de **input** (`.txt`) e **dicionário** (`.xls`) em `Documentacao/`.  
   - Baixa o **deflator** (`.xls`) em `Documentacao/`.  
   - Aplica o dicionário para nomear colunas do `.txt`, carrega em chunks com barra de progresso.  
   - Faz merge com as colunas de deflator (`CO1`, `CO1e`, `CO2`, `CO2e`, `CO3`) via `Ano`, `Trimestre` e `UF`.  
   - Gera `PNADC_<ano>_visita<visita>_final.csv` em `Dados/`.  
   - Remove automaticamente arquivos `.zip` e `.txt` brutos para economizar espaço.


## 📝 Licença

Dados obtidos via FTP do IBGE, conforme condições de uso do IBGE.

---

> **Autor:** Raphael Lopes Monteiro 
> **Contato:** raphaellmonteiro2@gmail.com  
> **Data:** Julho de 2025  
