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
                results = find_first_figure_abstract_caption(tex_file_path=tex)
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

def remove_commented_lines(text):
    """
    Removes lines that start with '%' (i.e., fully commented lines).
    Returns the cleaned text. Does NOT remove inline comments (e.g. text % comment).
    """
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        striped = line.lstrip()
        if striped.startswith('%'):
            # Entire line commented out, skip it
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

def extract_brace_block(tex, start_pattern=r'\\caption\s*\{'):
    """
    Finds the first occurrence of something matching start_pattern (by default '\\caption{'),
    and returns everything up to the matching '}' (handling nested braces).
    
    Returns:
       (content, end_index):
         content = string inside the { ... }
         end_index = position in the string right after the matching }
       or (None, None) if not found / not matched properly.
    """
    start_match = re.search(start_pattern, tex)
    if not start_match:
        return None, None  # no '\\caption{' found
    
    start_idx = start_match.end()  # index right after the '{'
    brace_count = 1
    i = start_idx
    n = len(tex)

    while i < n and brace_count > 0:
        if tex[i] == '{':
            brace_count += 1
        elif tex[i] == '}':
            brace_count -= 1
        i += 1

    if brace_count != 0:
        # Did not find matching '}'
        return None, None
    
    # content is everything between the first '{' and its matching '}'
    content = tex[start_idx : i-1]
    return content, i

def find_first_figure_abstract_caption(main_tex_path):
    """
    Reads a LaTeX file, removes fully commented lines, then searches for:
      1) The FIRST figure environment (either \begin{figure} or \begin{figure*}, with optional [ht!] etc.):
         - All \includegraphics commands within it (returned as a list of paths).
         - The \caption{...} text (including nested braces).
      2) The \begin{abstract}...\end{abstract} block (simple regex).
      
    Returns: (image_paths, first_fig_caption, abstract_str)
      - image_paths: list of str or None if no figure is found
      - first_fig_caption: str or None
      - abstract_str: str or None
    """

    if not os.path.exists(main_tex_path):
        print(f"[ERROR] main.tex doesn't exist: {main_tex_path}")
        return None, None, None

    # 1) Read the file content
    with open(main_tex_path, 'r', encoding='utf-8') as f:
        original_tex = f.read()

    # 2) Remove lines that are fully commented
    tex_content = remove_commented_lines(original_tex)

    # ============== (A) Match the FIRST figure environment ==============
    # We allow \begin{figure*} or \begin{figure}, plus any arguments like [t!], etc.
    # Same for \end{figure*} or \end{figure}.
    figure_env_pattern = re.compile(
        r'\\begin\{figure\*?[^}]*\}(.*?)\\end\{figure\*?[^}]*\}',
        re.DOTALL
    )
    figure_env_match = re.search(figure_env_pattern, tex_content)

    image_paths = []
    first_fig_caption = None

    if figure_env_match:
        figure_env = figure_env_match.group(1)  # content inside the figure block

        # (A1) Find ALL \includegraphics{...} calls
        incl_pattern = r'\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}'
        raw_image_paths = re.findall(incl_pattern, figure_env)
        if raw_image_paths:
            image_paths = [path.strip() for path in raw_image_paths]
            print("[INFO] Found image paths in the figure environment:", image_paths)
        else:
            print("[INFO] No \\includegraphics{...} found.")
            image_paths = None

        # (A2) Extract the caption via nested-brace parsing
        caption_content, _ = extract_brace_block(figure_env, start_pattern=r'\\caption\s*\{')
        if caption_content is not None:
            # If you want to remove or transform certain LaTeX commands inside the caption, do it here:
            # e.g. remove \small, \label, \textbf, but keep references:
            clean_cap = re.sub(r'\\(small|label|textbf|textit|mathrm|emph)\b(\[[^\]]*\])?', '', caption_content)
            # Remove extra whitespace
            clean_cap = re.sub(r'\s+', ' ', clean_cap).strip()
            first_fig_caption = clean_cap
            print(f"[INFO] Found figure caption: {first_fig_caption}")
        else:
            first_fig_caption = None
            print("[INFO] No \\caption{...} found in this figure block.")
    else:
        image_paths = None
        first_fig_caption = None
        print("[WARNING] No figure environment found in main.tex")

    # ============== (B) Match the abstract environment ==============
    abstract_str = None
    abstract_pattern = r'\\begin\{abstract\}(.*?)\\end\{abstract\}'
    abstract_match = re.search(abstract_pattern, tex_content, flags=re.DOTALL)
    if abstract_match:
        raw_abs = abstract_match.group(1)
        # Optionally remove some LaTeX commands from the abstract:
        raw_abs = re.sub(r'\\(small|label|textbf|textit|mathrm|emph)\b(\[[^\]]*\])?', '', raw_abs)

        raw_abs = re.sub(r'\\[A-Za-z]+\{.*?\}', '', raw_abs)
        raw_abs = re.sub(r'\\[A-Za-z]+', '', raw_abs)
        raw_abs = re.sub(r'\s+', ' ', raw_abs).strip()
        abstract_str = raw_abs
        print("[INFO] Found abstract:", abstract_str)
    else:
        print("[WARNING] No abstract found in main.tex")

    return image_paths, abstract_str, first_fig_caption
