import requests
from bs4 import BeautifulSoup
import arxiv, os
import shutil
import tarfile, os, csv
import re, json
from plasTeX.TeX import TeX
from pylatexenc.latex2text import LatexNodes2Text

from plasTeX.Packages.xcolor import ColorError

from textacy import preprocessing
import spacy

from pylatexenc.latexwalker import LatexWalker
import os
from plasTeX.TeX import TeX
from plasTeX.Base import LaTeX
from pylatexenc.latex2text import LatexNodes2Text
import openreview

from pylatexenc.latex2text import LatexNodes2Text, MacroTextSpec
from pylatexenc import latexwalker, latex2text, macrospec
from pylatexenc.latex2text import get_default_latex_context_db

def return_paper_titles(year: str, venue: str):
    if venue == 'acl':
        return return_acl_paper_titles(year=year)
    elif venue == 'naacl':
        return return_naacl_paper_titles(year=year)
    elif venue == 'emnlp':
        return return_emnlp_paper_titles(year=year)
    elif venue == 'neurips':
        return return_neurips_paper_titles(year=year)
    elif venue == 'iclr':
        return return_iclr_paper_titles(year=year)
    elif venue == 'cvpr':
        return return_cvpr_paper_titles(year=year)
    else:
        raise ValueError(f"This venue is not supported yet: {venue}")

def return_iclr_paper_titles(year: str):
    """
    Fetches the titles of papers accepted as 'oral' at ICLR for a given year.

    Args:
        year (str): Year of the ICLR conference, e.g., "2024"

    Returns:
        List[str]: A list of accepted oral paper titles
    """
    year_int=int(year)
    if year_int<2020: raise ValueError(f"This year is not supported yet: {year}")
    # check api version
    venue_id = f'ICLR.cc/{year}/Conference'
    
    client = openreview.api.OpenReviewClient(
        baseurl='https://api2.openreview.net',
        username='pwang71@jh.edu',
        password='Openrev1234'
    )
    api2_venue_group = client.get_group(venue_id)
    api2_venue_domain = api2_venue_group.domain
    if api2_venue_domain is None:
        api_version='v1'
    else:
        api_version='v2'
    
    if api_version=='v2':
        venue_group_settings = client.get_group(venue_id).content
        submission_invitation = venue_group_settings['submission_id']['value']
        submissions = client.get_all_notes(
            invitation=submission_invitation,
            details='directReplies'
        )
        titles = []
        # API V2
        venue_group_settings = client.get_group(venue_id).content
        decision_invitation_name = venue_group_settings['decision_name']['value']
        for submission in submissions:
            paper_decision=''
            for reply in submission.details['directReplies']:
                if any(invitation.endswith(f'/-/{decision_invitation_name}') for invitation in reply['invitations']):
                    paper_decision = reply['content']['decision']['value']
                    break  # found decision for this submission, exit loop
            if paper_decision.lower() in ["accept (oral)", "accept (poster)", "accept (spotlight)"]:
                titles.append(submission.content['title']['value'])

        return titles
    elif api_version=='v1':
        client = openreview.Client(
            baseurl='https://api.openreview.net',
            username='pwang71@jh.edu',
            password='Openrev1234'
        )
        submissions = client.get_all_notes(
            invitation=venue_id+"/-/Blind_Submission",
            details='directReplies'
        )
        titles=[]
        for submission in submissions:
            paper_decision=''
            for reply in submission.details["directReplies"]:
                if reply["invitation"].endswith("Decision"):
                    if 'decision' in reply['content']:
                        paper_decision=reply['content']['decision']
                        break
                    elif 'recommendation' in reply['content']:
                        paper_decision=reply['content']['recommendation']
                        break

            if paper_decision[:6].lower()=='accept' or paper_decision.lower() in ["accept (oral)", "accept (poster)", "accept (spotlight)", "accept: oral", "accept: poster", "accept: spotlight"]:
                titles.append(submission.content['title'])
        return titles
    else:
        raise ValueError(f"This api version doesn't exist.")

def return_cvpr_paper_titles(year: str):
    url = "https://cvpr.thecvf.com/Conferences/"+year+"/AcceptedPapers"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Error while accessing the URL: {url}. The requested year probably doesn't exist ({year}).")
    soup = BeautifulSoup(response.text, 'html.parser')

    paper_titles = []

    # Go through all rows
    for tr in soup.find_all('tr'):
        tds = tr.find_all('td')
        if not tds:
            continue

        first_td = tds[0]
        title = None

        # Case 1: <strong> tag title
        strong = first_td.find('strong')
        if strong:
            title = strong.get_text(strip=True)

        # Case 2: <a> tag title (e.g., GitHub/website link used as title)
        elif first_td.find('a'):
            a_tag = first_td.find('a')
            title = a_tag.get_text(strip=True)

        if title:
            paper_titles.append(title)

    return paper_titles

def return_neurips_paper_titles(year: str):
    url = "https://papers.nips.cc/paper_files/paper/"+year
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Error while accessing the URL: {url}. The requested year probably doesn't exist ({year}).")
    soup = BeautifulSoup(response.text, 'html.parser')
    
    paper_list = soup.find('ul', class_='paper-list')
    if not paper_list:
        raise Exception("Could not find the paper list on the page.")

    titles = []
    for li in paper_list.find_all('li', class_='conference'):
        a_tag = li.find('a')
        if a_tag:
            title = a_tag.get_text(strip=True)
            titles.append(title)

    return titles

def return_emnlp_paper_titles(year: str):
    '''
    input:
    year of acl main track papers to extract, str; Ex: '2024'
    
    output:
    list of titles of papers, list of str
    '''
    url = "https://aclanthology.org/volumes/"+year+".emnlp-main/"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Error while accessing the URL: {url}. The requested year probably doesn't exist ({year}).")
    soup = BeautifulSoup(response.content, "html.parser")

    # This finds all paper titles
    titles = []
    for strong in soup.find_all("strong"):
        a_tag = strong.find("a", class_="align-middle")
        if a_tag:
            titles.append(a_tag.text.strip())
    print('✅ Extracted', len(titles[1:]), 'paper titles from', year)
    return titles[1:]
    
def return_naacl_paper_titles(year: str):
    '''
    input:
    year of acl main track papers to extract, str; Ex: '2024'
    
    output:
    list of titles of papers, list of str
    '''
    url = "https://aclanthology.org/volumes/"+year+".naacl-long/"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Error while accessing the URL: {url}. The requested year probably doesn't exist ({year}).")
    soup = BeautifulSoup(response.content, "html.parser")

    # This finds all paper titles
    titles = []
    for strong in soup.find_all("strong"):
        a_tag = strong.find("a", class_="align-middle")
        if a_tag:
            titles.append(a_tag.text.strip())
    print('✅ Extracted', len(titles[1:]), 'paper titles from', year)
    return titles[1:]

def return_acl_paper_titles(year: str):
    '''
    input:
    year of acl main track papers to extract, str; Ex: '2024'
    
    output:
    list of titles of papers, list of str
    '''
    url = "https://aclanthology.org/volumes/"+year+".acl-long/"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Error while accessing the URL: {url}. The requested year probably doesn't exist ({year}).")
    soup = BeautifulSoup(response.content, "html.parser")

    # This finds all paper titles
    titles = []
    for strong in soup.find_all("strong"):
        a_tag = strong.find("a", class_="align-middle")
        if a_tag:
            titles.append(a_tag.text.strip())
    print('✅ Extracted', len(titles[1:]), 'paper titles from', year)
    return titles[1:]

def get_arxiv_id_dict(titles, max_results=10, arxiv_id_db_path="./arxiv_id_db.json"):
    '''
    input:
    list of titles, list of str
    max_results: int, the max result for 1 title search using arxic search package
    
    output:
    paper_dict: dict, key is paper title, value is arxiv paper id
    not_found_titles: list of not found paper titles, list of str
    '''
    if os.path.exists(arxiv_id_db_path):
        with open(arxiv_id_db_path, "r") as f:
            paper_dict = json.load(f)
    else:
        paper_dict = {}
    
    not_in_db_titles=[]
    for title in titles:
        if not(title in paper_dict): not_in_db_titles.append(title)
    print("🔍 Found", len(titles)-len(not_in_db_titles),"out of",len(titles), "ids in database", arxiv_id_db_path)
    if len(not_in_db_titles)>0: print('Start searching for the remaining', len(not_in_db_titles), "ids")
    #titles=not_in_db_titles
    
    not_found_titles=[]
    client = arxiv.Client()
    for i,title in enumerate(not_in_db_titles):
        print(f"Searching for paper {i+1} of {len(not_in_db_titles)}")
        search = arxiv.Search(
            query=title,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )

        results = list(client.results(search))
        
        for result in results:
            if result.title == title:
                paper_dict[title]=result.get_short_id()
                break
        if title not in paper_dict.keys():
            not_found_titles.append(title)
    if len(not_found_titles) > 0:
        print('❌ Failed to find', len(not_found_titles),'paper ids')
    elif len(not_in_db_titles)>0:
        print("✅ Found all", len(not_in_db_titles),'papers')
    with open(arxiv_id_db_path, "w") as f:
        json.dump(paper_dict, f)
    extracting_paper_dict={}
    for title in titles:
        if title in paper_dict:
            extracting_paper_dict[title]=paper_dict[title]
    return extracting_paper_dict, not_found_titles

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
        return False

def list_top_level_tex_files(folder_path):
    tex_files = []
    for file in os.listdir(folder_path):
        full_path = os.path.join(folder_path, file)
        if os.path.isfile(full_path) and file.endswith('.tex'):
            tex_files.append(full_path)
    return tex_files

def download_latex_files(paper_id_dict, save_dir_path):
    subdirs=[]
    if os.path.exists(save_dir_path):
        subdirs = [d for d in os.listdir(save_dir_path) if os.path.isdir(os.path.join(save_dir_path, d))]
    else: ensure_empty_dir(dir_path=save_dir_path)
    # print(subdirs)
    # print(list(paper_id_dict.keys()))
    overlap = set(subdirs) & set(list(paper_id_dict.values()))
    if len(overlap)>0: 
        print("🔍 Found tex source of", len(overlap),"out of",len(paper_id_dict),"papers")
        download_paper_id_dict={}
        for title, id in paper_id_dict.items():
            if not(id in subdirs):
                download_paper_id_dict[title]=id
    else:
        download_paper_id_dict=paper_id_dict
    if len(download_paper_id_dict)>0: print("Start downloading and extracting the remaining", len(download_paper_id_dict), "papers")
    
    failed_extract_download=set()
    for paper, id in download_paper_id_dict.items():
        tar_path=save_dir_path+id+'.tar'
        if download_arxiv_source(arxiv_id=id, save_path=tar_path):
            try:
                with tarfile.open(tar_path, "r:gz") as tar:
                    tar.extractall(path=save_dir_path+id)
                os.remove(tar_path)
                print(f"{id} Downloaded and extracted source to {tar_path}")
            except Exception as e:
                failed_extract_download.add(paper)
                print(f"❌ Failed to extract {tar_path}: {e}")
        else:
            failed_extract_download.add(paper)
            print(f" ❌ {id} Failed to download source.")
    if len(download_paper_id_dict)-len(failed_extract_download)>0: print('✅', len(download_paper_id_dict)-len(failed_extract_download),"out of", len(download_paper_id_dict), "have been downloaded and extracted to", save_dir_path)
    for paper in list(failed_extract_download):
        del paper_id_dict[paper]
    return paper_id_dict

def ensure_empty_dir(dir_path):
    # If it exists, remove it entirely
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
        print('Deleted directory', dir_path)
    # Then create a fresh empty version
    os.makedirs(dir_path)
    print('Created directory', dir_path)

def extract_to_csv(paper_id_dict, latex_files_path, csv_path, fig1_path_separater=';'):
    success_extractions=[]
    folder='/'.join(csv_path.split('/')[:-1])
    ensure_empty_dir(dir_path=folder)
    ensure_empty_dir(dir_path=folder+'/img')
    rows = []
    for title, id in paper_id_dict.items():
        folder_path=latex_files_path+'/'+id
        tex_files = list_top_level_tex_files(folder_path=folder_path)
        if len(tex_files)==0:
            print(f" ❌ {id} Failed to find tex file.")
        else:

            for tex in tex_files:
                try:
                    results = extract_latex_info(latex_path=tex)#find_first_figure_abstract_caption(main_tex_path=tex)
                except Exception as e:
                    results=None
                    print("❌ [extract tex ERROR]",e)
                if results is not None:

                    fig1_file_path=os.path.join(folder_path, results['image_path'] )
                    introduction_str=results['introduction']
                    abstract_str=results['abstract']
                    fig1_caption_str=results['figure_caption']
                    

                    # Copy img to new path
                    new_filename=id + os.path.splitext(fig1_file_path)[1] 
                    destination_path = os.path.join(folder+'/img', new_filename)
                    shutil.copy2(fig1_file_path, destination_path)
                    fig1_file_path=destination_path
                    
                    rows.append({
                        "paper_title": title,
                        "arxiv_id": id,
                        "abstract": abstract_str,
                        "fig1_file_path": fig1_file_path,
                        "fig1_caption": fig1_caption_str,
                        "introduction": introduction_str
                    })
                    success_extractions.append(title)
                    break

    # ✅ Save to CSV
    fieldnames = ["paper_title", "arxiv_id", "fig1_file_path", "fig1_caption", "abstract", "introduction"]
    with open(csv_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print('✅',len(success_extractions),'out of',len(paper_id_dict),'were extracted and saved to CSV', csv_path)
    return success_extractions

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

# def extract_latex_content(latex_path):
#     results={}
#     try:
#         with open(latex_path, 'r', encoding='utf-8') as f:
#             str_tex = f.read()
#     except Exception as e:
#         print(f"Error reading file: {latex_path}\n{e}")
#         return None
#     print('------------------------------------------------')
#     pattern = re.compile(r'\\newcommand\{(\\\w+)\}\[0\]\{(.+?)\}', re.DOTALL)

#     for match in pattern.findall(str_tex):
#         macro, definition = match
#         print(macro, definition)
#     print('----------------------------------')
#     # 1. Extract \begin{abstract}...\end{abstract}
#     abstract_match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", str_tex, re.DOTALL)
#     if abstract_match:
#         abstract_tex = abstract_match.group(1).strip()
#     else: return None


#     # 2. Extract content of \section{Introduction} up to next \section{
#     intro_match = re.search(r"\\section\{[ ]*Introduction[ ]*\}(.*?)(?=\\section\{)", str_tex, re.DOTALL | re.IGNORECASE)
#     if intro_match: intro_tex = intro_match.group(1).strip()
#     else: return None
    

#     # 3. Extract \begin{figure}...\end{figure}
#     figure_match = re.search(r"\\begin\{figure\}(.*?)\\end\{figure\}", str_tex, re.DOTALL)
#     if figure_match: figure_tex = figure_match.group(1).strip()
#     else: return None
    
#     return results



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
        return None#[None, None, None]

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
    full_image_paths = []
    first_fig_caption = None
    dirname = os.path.dirname(main_tex_path)

    if figure_env_match:
        figure_env = figure_env_match.group(1)  # content inside the figure block

        # (A1) Find ALL \includegraphics{...} calls
        incl_pattern = r'\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}'
        raw_image_paths = re.findall(incl_pattern, figure_env)
        if raw_image_paths:
            image_paths = [path.strip() for path in raw_image_paths]
            full_image_paths = [
            os.path.join(dirname, img_path)  # 组合完整路径
            for img_path in image_paths
            ]
            if len(full_image_paths)>1: 
                print("[INFO] More than one fig in fig1", image_paths)
                return None   
            fig1_full_image_path = full_image_paths[0]
            print("[INFO] Found image path in the figure environment:", fig1_full_image_path)
        else:
            print("[INFO] No \\includegraphics{...} found.")
            return None
            full_image_paths = None

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
            return None
            first_fig_caption = None
            print("[INFO] No \\caption{...} found in this figure block.")
    else:
        return None
        image_paths = None
        first_fig_caption = None
        print("[WARNING] No figure environment found in main.tex")

    # ============== (B) Match the abstract environment ==============
    abstract_str = None
    abstract_pattern = r'\\begin\{abstract\}(.*?)\\end\{abstract\}'
    abstract_match = re.search(abstract_pattern, tex_content, flags=re.DOTALL)
    if abstract_match:
        raw_abs = abstract_match.group(1)
        abstract_str = clean_latex_to_text(raw_abs) # needs try block
        
        # raw_abs = abstract_match.group(1)
        # # Optionally remove some LaTeX commands from the abstract:
        # raw_abs = re.sub(r'\\(small|label|textbf|textit|mathrm|emph)\b(\[[^\]]*\])?', '', raw_abs)

        # raw_abs = re.sub(r'\\[A-Za-z]+\{.*?\}', '', raw_abs)
        # raw_abs = re.sub(r'\\[A-Za-z]+', '', raw_abs)
        # raw_abs = re.sub(r'\s+', ' ', raw_abs).strip()
        # abstract_str = raw_abs
        # print("[INFO] Found abstract:", abstract_str)
    else:
        return None
        print("[WARNING] No abstract found in main.tex")
    return {
        "fig1_path": fig1_full_image_path,
        "abstract": abstract_str,
        "fig1_caption": first_fig_caption
    }
    return [full_image_paths, abstract_str, first_fig_caption]

def has_extension(path):
    return os.path.splitext(path)[1] != ''  # e.g. returns '.png' → True


def resolve_image_path(base_path, search_dir):
    image_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.eps']

    subdir = os.path.dirname(base_path)
    base_name, requested_ext = os.path.splitext(os.path.basename(base_path))

    search_path = os.path.join(search_dir, subdir)

    if not os.path.isdir(search_path):
        return None

    # Look for exact match (case-insensitive, even with extension)
    for filename in os.listdir(search_path):
        name_no_ext, ext = os.path.splitext(filename)
        if (
            name_no_ext.lower() == base_name.lower() and
            ext.lower() in image_extensions
        ):
            return os.path.join(subdir, filename)

    return None

# def resolve_image_path(base_path, search_dir):
#     image_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.eps']
    
#     subdir = os.path.dirname(base_path)
#     base_name = os.path.basename(base_path)

#     search_path = os.path.join(search_dir, subdir)

#     if not os.path.isdir(search_path):
#         return None

#     # List files in the directory and look for case-insensitive match
#     for filename in os.listdir(search_path):
#         name_no_ext, ext = os.path.splitext(filename)
#         if name_no_ext.lower() == base_name.lower() and ext.lower() in image_extensions:
#             print('--FILE NAME', os.path.join(subdir, filename))
#             return os.path.join(subdir, filename)

#     return None

def extract_latex_info(latex_path):

    # Read LaTeX content
    with open(latex_path, 'r', encoding='utf-8') as f:
        tex_str = f.read()

    ## Remove tables
    tex_str = re.sub(r'\\begin\{table\*?\}.*?\\end\{table\*?\}', '', tex_str, flags=re.DOTALL)
    
    # Replace figure* environments with figure
    tex_str = re.sub(r'\\begin\{figure\*\}', r'\\begin{figure}', tex_str)
    tex_str = re.sub(r'\\end\{figure\*\}', r'\\end{figure}', tex_str)
    
    # Deal with \textcircled and \raisebox
    tex_str = re.sub(r'\\raisebox\{[^\}]*\}(?:\[[^\]]*\]){0,2}\{([^\}]*)\}', r'\1', tex_str)
    tex_str = re.sub(r'\\textcircled\{(.*?)\}', lambda m: '*' if not m.group(1).strip() else f'({m.group(1).strip()})', tex_str)
    
    # print('---------DEBUG tex str')
    
    # print(tex_str)
    # print('----------')
    # Parse using plasTeX
    
    tex = TeX()
    try:
        tex.input(tex_str)
        doc = tex.parse()
    except ColorError as ce:
        tex_str = re.sub(r'\\definecolor\{.*?\}\{HTML\}\{.*?\}', '', tex_str)
        tex.input(tex_str)
        doc = tex.parse()
    except Exception as e:
        
        print("❌ [Parse tex ERROR]",e)
        return None

    result = {}
    # --- Extract abstract node ---
    abstract_node = None
    for node in doc.getElementsByTagName("abstract"):
        abstract_node = node
        break
    if abstract_node:
        # print('----Child source----------')
        # for i,child in enumerate(abstract_node.allChildNodes):
        #     if hasattr(child, 'source'): 
        #         print(i)
        #         print(child.source)
        # print('----Child source----------')

        # print('----')
        # print('Prev')
        # print(abstract_node.source)
        # print('----')
        latex=extract_latex_text_without_figures(abstract_node)
        # print('Raw abstract')
        # print(latex)
        # print('----')
        raw_text = custom_latex_to_text(latex)
        norm_text = enforce_spacing(raw_text)
        result["abstract"] = norm_text

        
    else: return None # No abstract node found
    # print(result)
    # print('-----HERE??')
    
    # --- Extract first figure node ---    
    figure_node = None
    for fig in doc.getElementsByTagName("figure"):
        figure_node = fig
        break
    if figure_node:
        includes = figure_node.getElementsByTagName("includegraphics")
        image_paths = [img.attributes.get("file", "") for img in includes if img.attributes.get("file", "")]
        if len(image_paths) != 1:
            return None  # Must have exactly one image

        raw_image_path = image_paths[0]

        resolved_path = resolve_image_path(raw_image_path, search_dir=os.path.dirname(latex_path))
        if not resolved_path:
            return None
        result["image_path"] = resolved_path
        



        captions = figure_node.getElementsByTagName("caption")
        if captions:
            
            raw_caption = captions[0].source #''.join([child.source for child in captions[0].allChildNodes if hasattr(child, 'source')])
            raw_text = custom_latex_to_text(raw_caption)
            norm_text = enforce_spacing(raw_text)
            result["figure_caption"] = norm_text
            #result["figure_caption"] = LatexNodes2Text().latex_to_text(raw_caption).strip()
        else:
            return None # Must have caption
    else: return None # No figure node found
    # print(result)
    
    # --- Extract \section{Introduction} ---
    intro_node = None
    for sec in doc.getElementsByTagName("section"):
        title = getattr(sec, 'title', None)
        title_str = getattr(title, 'textContent', '') if title else ''
        if 'introduction' in title_str.lower():
            intro_node = sec
            break
    if intro_node:
        # test=[]
        # test.append(intro_node.source)
        # print('-------INTRO-------------------')
        # print(test)

        # print('-------INTRO DEBUG-------------------')
        # test=[]
        
        latex=extract_latex_text_without_figures(intro_node)
        # test.append(latex)
        # print('----')
        # print('Raw')
        # print(test)
        # print('----')
        # list_macros_and_args(latex)
        raw_text = custom_latex_to_text(latex)
        # test=[]
        # test.append(raw_text)
        # print('----')
        # print('Raw text')
        # print(test)
        # print('----')
        norm_text = enforce_spacing(raw_text)
        # test=[]
        # test.append(norm_text)
        # print('----')
        # print('Norm Text')
        # print(test)
        # print('----')
        result["introduction"] = norm_text
    else: return None # No introduction node extraced

    return result

def custom_latex_to_text(latex):
    specs_db = get_default_latex_context_db()
    custom_specs = {
        'macros': [
            MacroTextSpec('texttt', discard=False),  # keep contents
            MacroTextSpec('footnote', discard=True),
            MacroTextSpec('ref', discard=True),
            MacroTextSpec('autoref', discard=True),
            MacroTextSpec('cref', discard=True),
            MacroTextSpec('Cref', discard=True),
            MacroTextSpec('eqref', discard=True),
            MacroTextSpec('cite', discard=True),
            MacroTextSpec('citet', discard=True),
            MacroTextSpec('citep', discard=True),
        ]
    }

    specs_db.add_context_category('custom_specs',prepend=True, macros=custom_specs['macros'])
    return LatexNodes2Text(latex_context=specs_db).latex_to_text(latex).strip()




def contains_figure(node):
        # Recursively check if node or any of its children is a figure or figure*
        tag = getattr(node, 'tagName', '')
        if tag in {'figure', 'figure*'}:
            return True
        return any(contains_figure(child) for child in getattr(node, 'childNodes', []))
    

def extract_latex_text_without_figures(node, delimiter=''):
    latex_parts = []

    for child in getattr(node, 'childNodes', []):
        if contains_figure(child):
            continue
        latex_parts.append(child.source)

    # Combine LaTeX source and convert to plain text
    full_latex = delimiter.join(latex_parts)
    return full_latex
        


def list_macros_and_args(latex_str):
    walker = LatexWalker(latex_str)
    nodes, parsing_errors, _ = walker.get_latex_nodes()

    def walk(nodes):
        for n in nodes:
            if hasattr(n, 'macroname'):
                args = getattr(n.nodeargd, 'argnlist', [])
                print(f"Macro: \\{n.macroname}  | Args: {len(args)}")
            if hasattr(n, 'nodelist'):
                walk(n.nodelist)
            if hasattr(n, 'nodeargd'):
                for arg in getattr(n.nodeargd, 'argnlist', []):
                    if hasattr(arg, 'nodelist'):
                        walk(arg.nodelist)

    walk(nodes)

nlp = spacy.load("en_core_web_sm")

def enforce_spacing(text):
    doc = nlp(text)
    text = preprocessing.normalize.whitespace(doc.text)
    text = preprocessing.normalize.quotation_marks(text)
    text = preprocessing.normalize.hyphenated_words(text)

    # Normalize quotation marks (basic double/single quote spacing)
    text = re.sub(r'\s*"\s*([^"]*?)\s*"\s*', r' "\1" ', text)  # Space around quoted text
    text = re.sub(r"\s*'\s*([^']*?)\s*'\s*", r" '\1' ", text)  # Same for single quotes

    # Fix spacing around brackets and parentheses, including angle brackets
    text = re.sub(r'\s*([(\[\{<])\s*', r' \1', text)  # Space before opening brackets
    text = re.sub(r'\s*([)\]\}>])\s*', r'\1 ', text)  # Space after closing brackets

    # --- Math-aware punctuation handling ---

    # Preserve commas/periods between digits (e.g., 12.34, 1,000)
    text = re.sub(r'(?<=\d)\s*([.,])\s*(?=\d)', r'\1', text)

    # Preserve factorial, percent, and exponentiation notation (e.g., 5!, 20%, 2^3)
    text = re.sub(r'(?<=\d)\s*([!%^])\s*', r'\1', text)

    # Remove space before general punctuation (only outside math cases)
    text = re.sub(r'\s+([,.!?;:])', r'\1', text)

    # Add space after punctuation, only if NOT followed by whitespace or digit (to avoid 12.34 → 12. 34)
    text = re.sub(r'([,.!?;:])(?=[^\s\d])', r'\1 ', text)
    
    # Normalize Latin abbreviations like e. g. , → e.g., or E. G. , → E.G.,
    text = re.sub(r'\b([eE])\s*\.\s*([gG])\s*\.\s*,?', r'\1.\2.,', text)
    text = re.sub(r'\b([iI])\s*\.\s*([eE])\s*\.\s*,?', r'\1.\2.,', text)


    return text