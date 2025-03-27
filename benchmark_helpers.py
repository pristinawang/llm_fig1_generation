import requests
from bs4 import BeautifulSoup
import arxiv, os
import shutil
import tarfile, os, csv

def return_acl_paper_titles(year: str):
    '''
    input:
    year of acl main track papers to extract, str; Ex: '2024'
    
    output:
    list of titles of papers, list of str
    '''
    url = "https://aclanthology.org/volumes/"+year+".acl-long/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    # This finds all paper titles
    titles = []
    for strong in soup.find_all("strong"):
        a_tag = strong.find("a", class_="align-middle")
        if a_tag:
            titles.append(a_tag.text.strip())
    print('Extracted', len(titles[1:]), 'paper titles from', year)
    return titles[1:]

def get_arxiv_id_dict(titles, max_results=10):
    '''
    input:
    list of titles, list of str
    max_results: int, the max result for 1 title search using arxic search package
    
    output:
    paper_dict: dict, key is paper title, value is arxiv paper id
    not_found_titles: list of not found paper titles, list of str
    '''
    paper_dict={}
    not_found_titles=[]
    client = arxiv.Client()
    for i,title in enumerate(titles):
        print(f"Searching for paper {i+1} of {len(titles)}")
        search = arxiv.Search(
            query=title,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )

        results = list(client.results(search))
        # print(f"🔍 Found {len(results)} result(s):")

        for result in results:
            # print("=" * 50)
            # print("Title:", result.title)
            # print("arXiv ID:", result.get_short_id())
            # print("URL:", result.entry_id)
            # print("Published:", result.published.date())
            if result.title == title:
                paper_dict[title]=result.get_short_id()
                break
        if title not in paper_dict.keys():
            not_found_titles.append(title)
    print('❌ Failed to find', len(not_found_titles),'paper ids')
    return paper_dict, not_found_titles

def download_arxiv_source(arxiv_id, save_path):
    '''
    return True if download was successful
    return False if download was unsuccessful
    '''
    url = f"https://arxiv.org/src/{arxiv_id}"
    response = requests.get(url)

    if response.status_code == 200:
        with open(save_path, "wb") as f:
            f.write(response.content)
        return True
    else:
        #print(f" ❌ {id} Failed to download source. Status code: {response.status_code}")
        return False

def list_top_level_tex_files(folder_path):
    tex_files = []
    for file in os.listdir(folder_path):
        full_path = os.path.join(folder_path, file)
        if os.path.isfile(full_path) and file.endswith('.tex'):
            tex_files.append(full_path)
    return tex_files

def download_latex_files(paper_id_dict, save_dir_path):
    ensure_empty_dir(dir_path=save_dir_path)
    
    for paper, id in paper_id_dict.items():
        tar_path=save_dir_path+id+'.tar'
        if download_arxiv_source(arxiv_id=id, save_path=tar_path):
            try:
                with tarfile.open(tar_path, "r:gz") as tar:
                    tar.extractall(path=save_dir_path+id)
                os.remove(tar_path)
                print(f"✅ {id} Downloaded source to {tar_path}")
            except Exception as e:
                print(f"❌ Failed to extract {tar_path}: {e}")
        else:
            print(f" ❌ {id} Failed to download source.")

def ensure_empty_dir(dir_path):
    # If it exists, remove it entirely
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
        print('Deleted directory', dir_path)
    # Then create a fresh empty version
    os.makedirs(dir_path)
    print('Created directory', dir_path)

def extract_to_csv(paper_id_dict, latex_files_path, csv_path):
    
    folder='/'.join(csv_path.split('/')[:-1])
    ensure_empty_dir(dir_path=folder)
    rows = []
    for title, id in paper_id_dict.items():
        folder_path=latex_files_path+'/'+id
        tex_files = list_top_level_tex_files(folder_path=folder_path)
        if len(tex_files)==0:
            print(f" ❌ {id} Failed to find tex file.")
        else:
            for tex in tex_files:
                results = return_fig1_abstract(tex_file_path=tex)
                if results is not None:
                    
                    fig1_file_path=results[0]
                    abstract_str=results[1]
                    fig1_caption_str=results[2]
                    
                    rows.append({
                        "paper_title": title,
                        "arxiv_id": id,
                        "fig1_file_path": fig1_file_path,
                        "abstract": abstract_str,
                        "fig1_caption": fig1_caption_str
                    })
                    break

    # ✅ Save to CSV
    fieldnames = ["paper_title", "arxiv_id", "fig1_file_path", "abstract", "fig1_caption"]
    with open(csv_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print('✅ Save to CSV', csv_path)

def return_fig1_abstract(tex_file_path='/home/2401.07159v1/acl_latex.tex'):
    '''
    tex_file_path: absolute file path (str)
    fig1_file_path: absolute file path(str)
    abstract_str: string
    fig1_caption_str: string 
    '''
    
    # if fig1 exists in this file:
    #     return [fig1_file_path, abstract_str, fig1_caption_str]
    # else:
    #     return None 
    
    return [tex_file_path, 'abs', 'cap']