# === Importações e Setup === #
import os  # manipulação de caminhos e arquivos
import re  # expressões regulares para parsing de HTML
import requests  # requisições HTTP para download
import zipfile  # extração de arquivos ZIP
from tqdm import tqdm  # barra de progresso
import pandas as pd  # manipulação de dataframes
from glob import glob  # busca de arquivos por padrões
from pathlib import Path  # para determinar diretórios dinamicamente

# === Determina diretório base dinamicamente === #
# SCRIPT_DIR: pasta onde este script está localizado
# PROJECT_DIR: pasta-pai do projeto 
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR

# === Função para criar diretórios === #
def criar_diretorios(root_dir):
    """
    Cria duas subpastas dentro de root_dir:
      - Dados
      - Documentacao
    Retorna as paths para estas pastas.
    """
    base = str(root_dir)
    dados_dir = os.path.join(base, "Dados")
    doc_dir  = os.path.join(base, "Documentacao")
    os.makedirs(dados_dir, exist_ok=True)
    os.makedirs(doc_dir,  exist_ok=True)
    return dados_dir, doc_dir

# === Função para tentar download com padrões e fallback FTP === #
def tentar_download(url_base, padroes_nomes, tipo):
    # 1) Tentativa com nomes fixos
    for nome in padroes_nomes:
        url = url_base + nome
        try:
            r = requests.head(url, timeout=10)
            if r.status_code == 200:
                print(f"✔ Padrão encontrado: {nome}")
                return url, nome
        except requests.RequestException:
            continue
    # 2) Fallback: lista diretório FTP e filtra por prefixo
    print("🔍 Padrões fixos falharam, listando FTP…")
    try:
        r = requests.get(url_base, timeout=10)
        r.raise_for_status()
        ext_map = {'microdados':'zip', 'input':'txt', 'dicionario':'xls', 'deflator':'xls'}
        ext = ext_map.get(tipo)
        links = re.findall(rf'href="([^"]+\.{ext})"', r.text)
        prefixo = os.path.splitext(padroes_nomes[0])[0]
        candidatos = [f for f in links if f.startswith(prefixo)]
        if candidatos:
            candidatos.sort()
            nome = candidatos[-1]
            print(f"✔ Arquivo dinâmico encontrado: {nome}")
            return url_base + nome, nome
    except Exception as e:
        print(f"⚠ Erro ao listar FTP: {e}")
    print(f"⚠ Não achou nenhum dos padrões: {padroes_nomes}")
    return None, None

# === Função para download com barra de progresso === #
def baixar_arquivo(url, destino, descricao):
    total = None
    try:
        head = requests.head(url, timeout=10)
        cl = head.headers.get('content-length')
        if cl and int(cl) > 0:
            total = int(cl)
    except Exception:
        pass
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            if total is None:
                cl2 = r.headers.get('content-length')
                total = int(cl2) if cl2 and int(cl2) > 0 else None
            with open(destino, 'wb') as f, tqdm(
                total=total, unit='B', unit_scale=True, desc=descricao
            ) as bar:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))
        return True
    except Exception as e:
        print(f"❌ Erro ao baixar {descricao}: {e}")
        return False

# === Função para aplicar o dicionário e mesclar deflator === #
def aplicar_dicionario(dados_dir, doc_dir, ano, visita, deflator_ano):
    # Localiza o arquivo de dicionário (.xls)
    prefixo = f"dicionario_PNADC_microdados_{ano}_visita{visita}"
    dict_files = glob(os.path.join(doc_dir, prefixo + '*.xls'))
    if not dict_files:
        print(f"⚠ Dicionário não encontrado em {doc_dir}")
        return
    dict_path = sorted(dict_files)[-1]
    dic = pd.read_excel(dict_path, engine='xlrd', skiprows=1)
    if 'Tamanho' not in dic.columns:
        print("⚠ Coluna 'Tamanho' não encontrada em:", dic.columns.tolist())
        return
    widths = dic['Tamanho'].dropna().astype(int).tolist()
    names  = dic.iloc[:, 2].dropna().astype(str).tolist()
    txt_file = next((f for f in os.listdir(dados_dir) if f.endswith('.txt')), None)
    if not txt_file:
        print(f"⚠ Nenhum .txt em {dados_dir}")
        return
    txt_path = os.path.join(dados_dir, txt_file)
    print(f"🔍 Carregando {txt_file} em chunks…")
    chunks = pd.read_fwf(txt_path, widths=widths, header=None, dtype=str, chunksize=50000)
    df = pd.concat([c for c in tqdm(chunks, desc='Lendo microdados')], ignore_index=True)
    if df.shape[1] != len(names):
        print(f"⚠ Nº de colunas ({df.shape[1]}) != nomes ({len(names)})")
    df.columns = names
    def_files = glob(os.path.join(doc_dir, f"deflator_PNADC_{deflator_ano}*.xls"))
    if def_files:
        df_def = pd.read_excel(def_files[0], engine='xlrd')
        df_def.rename(columns={'ano':'Ano','trim':'Trimestre','uf':'UF'}, inplace=True)
        for col in ['Ano','Trimestre']:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
            df_def[col] = pd.to_numeric(df_def[col], errors='coerce').astype('Int64')
        df['UF'] = df['UF'].astype(str)
        df_def['UF'] = df_def['UF'].astype(str)
        df = df.merge(
            df_def[['Ano','Trimestre','UF','CO1','CO1e','CO2','CO2e','CO3']],
            on=['Ano','Trimestre','UF'], how='left'
        )
        print("✅ Deflator mesclado")
    out_csv = os.path.join(dados_dir, f"PNADC_{ano}_visita{visita}_final.csv")
    df.to_csv(out_csv, index=False, sep=';')
    print("✅ CSV salvo em", out_csv)
    for ext in ('.txt','.zip'):
        for f in glob(os.path.join(dados_dir, f"*{ext}")):
            os.remove(f)

# === Função principal === #
def main():
    ano = input("Ano PNADC (ex: 2024): ").strip()
    if ano in ('2020','2021'):
        print(f"⚠️ Para o ano {ano}, apenas Visita 5 está disponível.")
        visita = '5'
    else:
        visita = input("Visita (1 ou 5): ").strip()
    deflator_ano = input("Ano do deflator (ex: 2024): ").strip()

    # Pasta específica de download para esta execução
    run_folder = PROJECT_DIR / f"PNADC_{ano}_visita{visita}_def_{deflator_ano}"
    dados_dir, doc_dir = criar_diretorios(run_folder)

    PAD = {
        'microdados': [f"PNADC_{ano}_visita{visita}.zip"],
        'input':      [f"input_PNADC_{ano}_visita{visita}.txt"],
        'dicionario': [f"dicionario_PNADC_microdados_{ano}_visita{visita}.xls"],
        'deflator':   [f"deflator_PNADC_{deflator_ano}.xls"],
    }
    URLS = {
        'microdados': (
            "https://ftp.ibge.gov.br/Trabalho_e_Rendimento/"
            "Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Anual/"
            f"Microdados/Visita/Visita_{visita}/Dados/"
        ),
        'documentacao': (
            "https://ftp.ibge.gov.br/Trabalho_e_Rendimento/"
            "Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Anual/"
            f"Microdados/Visita/Visita_{visita}/Documentacao/"
        ),
        'deflator': (
            "https://ftp.ibge.gov.br/Trabalho_e_Rendimento/"
            "Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Anual/"
            "Microdados/Visita/Documentacao_Geral/"
        ),
    }

    print(f"\n🔍 Iniciando PNADC {ano} — Visita {visita}")

    url_md, nome_md = tentar_download(URLS['microdados'], PAD['microdados'], 'microdados')
    if url_md and baixar_arquivo(url_md, os.path.join(dados_dir, nome_md), 'Microdados'):
        with zipfile.ZipFile(os.path.join(dados_dir, nome_md), 'r') as z:
            z.extractall(dados_dir)
        print("✅ Microdados extraídos")

    for tp, desc in (('input', 'Input'), ('dicionario', 'Dicionário')):
        url_doc, nome_doc = tentar_download(URLS['documentacao'], PAD[tp], tp)
        if url_doc and baixar_arquivo(url_doc, os.path.join(doc_dir, nome_doc), desc):
            print(f"✅ {desc} salvo")

    url_def, nome_def = tentar_download(URLS['deflator'], PAD['deflator'], 'deflator')
    if url_def and baixar_arquivo(url_def, os.path.join(doc_dir, nome_def), 'Deflator'):
        print("✅ Deflator salvo")

    aplicar_dicionario(dados_dir, doc_dir, ano, visita, deflator_ano)
    print("\n✅ Processo concluído!")

if __name__ == '__main__':
    main()
