import requests
from bs4 import BeautifulSoup
import arxiv, os
import shutil
import tarfile, os, csv
import re, json
from plasTeX.TeX import TeX
from pylatexenc.latex2text import LatexNodes2Text
import time
from plasTeX.Packages.xcolor import ColorError
import plasTeX
from textacy import preprocessing
import spacy
import pandas as pd
from pylatexenc.latexwalker import LatexWalker
import os
from plasTeX.TeX import TeX
from plasTeX.Base import LaTeX
from pylatexenc.latex2text import LatexNodes2Text
import openreview
from datetime import datetime
from pylatexenc.latex2text import LatexNodes2Text, MacroTextSpec
from pylatexenc import latexwalker, latex2text, macrospec
from pylatexenc.latex2text import get_default_latex_context_db
from arxiv import UnexpectedEmptyPageError

from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import requests
import random

arxiv_retry = retry(
    wait=wait_exponential(multiplier=1, min=4, max=60), 
    stop=stop_after_attempt(5),  
    retry=(
        retry_if_exception_type(UnexpectedEmptyPageError) |
        retry_if_exception_type(requests.exceptions.RequestException) |
        retry_if_exception_type(ConnectionResetError)
    ),
    before_sleep=lambda _: print("arXiv API request failed, watiting for retrying...")
)


def return_paper_titles(year: str, venue: str):
    if venue == 'acl':
        titles = return_acl_paper_titles(year=year)
    elif venue == 'naacl':
        titles = return_naacl_paper_titles(year=year)
    elif venue == 'emnlp':
        titles = return_emnlp_paper_titles(year=year)
    elif venue == 'neurips':
        titles = return_neurips_paper_titles(year=year)
    elif venue == 'iclr':
        titles = return_iclr_paper_titles(year=year)
    elif venue == 'cvpr':
        titles=return_cvpr_paper_titles(year=year)
    else:
        raise ValueError(f"This venue is not supported yet: {venue}")
    print('✅ Extracted', len(titles), 'paper titles from', year, 'from', venue)
    return titles

def return_iclr_paper_titles(year: str):
    """
    Fetches the titles of papers accepted as 'oral' at ICLR for a given year.

    Args:
        year (str): Year of the ICLR conference, e.g., "2024"

    Returns:
        List[str]: A list of accepted oral paper titles
    """
    time.sleep(60)
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
    
    if int(year)<=2021:
        # Find all <a> tags inside <li> elements with class 'none'
        title_tags = soup.select("li.none a[title='paper title']")
        titles = [tag.text.strip() for tag in title_tags]    
    else:
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
    return titles[1:]
    
def return_naacl_paper_titles(year: str):
    '''
    input:
    year of acl main track papers to extract, str; Ex: '2024'
    
    output:
    list of titles of papers, list of str
    '''
    try:
        url = "https://aclanthology.org/volumes/"+year+".naacl-long/"
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        try:
            url = "https://aclanthology.org/volumes/"+year+".naacl-main/"
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
    return titles[1:]

def return_acl_paper_titles(year: str):
    '''
    input:
    year of acl main track papers to extract, str; Ex: '2024'
    
    output:
    list of titles of papers, list of str
    '''
    year_int=int(year)
    if year_int==2020:
        url='https://aclanthology.org/volumes/'+year+'.acl-main/'
    elif year_int<2020:
        raise ValueError(f"This year is not supported yet({year}).")
    else:
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
    return titles[1:]

def load_csv_db(csv_path):
    db_dict={}
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)  # Reads rows into dictionaries
        for row in reader:
            title=row['title']
            p_id=row['id']
            if p_id=='': p_id=None
            db_dict[title] = p_id
    return db_dict

def write_csv_db(csv_path, row):
    fieldnames = ["title", "id"]
    if not(os.path.isfile(csv_path)):
        with open(csv_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
    with open(csv_path, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)                        
        writer.writerow(row)

def get_arxiv_id_dict(titles, max_results=10, arxiv_id_db_path="./arxiv_id_db.csv", backup_db_path=None):
    '''
    input:
    list of titles, list of str
    max_results: int, the max result for 1 title search using arxic search package
    
    output:
    paper_dict: dict, key is paper title, value is arxiv paper id
    not_found_titles: list of not found paper titles, list of str
    '''
    if os.path.exists(arxiv_id_db_path):
        paper_dict = load_csv_db(arxiv_id_db_path)
        # with open(arxiv_id_db_path, "r") as f:
        #     paper_dict = json.load(f)
    else:
        paper_dict = {}
    
    not_in_db_titles=[]
    none_id_titles=[]
    for title in titles:
        if not(title in paper_dict): not_in_db_titles.append(title)
        elif paper_dict[title] is None: none_id_titles.append(title)
    print("🔍 Found", len(titles)-len(not_in_db_titles),"out of",len(titles), "ids in database", arxiv_id_db_path,'and',len(none_id_titles),'out of',len(titles)-len(not_in_db_titles),'have None type arxiv id')
    if len(not_in_db_titles)>0: print('Start searching for the remaining', len(not_in_db_titles), "ids")
    #titles=not_in_db_titles
    
    not_found_titles=[]
    client = arxiv.Client(
        page_size=100,  
        delay_seconds=5, 
        num_retries=5    
    )
    for i,title in enumerate(not_in_db_titles):
        print(f"Searching for paper {i+1} of {len(not_in_db_titles)}")
        
        @arxiv_retry
        def search_and_get_results():
            search = arxiv.Search(
                query=title,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance
            )
            try:
                return list(client.results(search))
            except (UnexpectedEmptyPageError, 
                    requests.exceptions.RequestException,
                    ConnectionResetError) as e:
                print(f"arXiv API错误: {str(e)}")
                raise 

        try:
            results = search_and_get_results()
        except Exception as e:
            print(f"❌ Cannot get the paper [{title}] arxiv info: {str(e)}")
            not_found_titles.append(title)
            paper_dict[title] = None
            continue  
        
        for result in results:
            if result.title == title:
                paper_dict[title]=result.get_short_id()
                break
        if title not in paper_dict.keys():
            not_found_titles.append(title)
            paper_dict[title]=None
            
        row={'title':title,'id':paper_dict[title]}
        write_csv_db(arxiv_id_db_path, row)
        if backup_db_path: write_csv_db(backup_db_path, row)
        # with open(arxiv_id_db_path, "w") as f:
        #     json.dump(paper_dict, f)
        #time.sleep(5 + random.uniform(0, 2))
    if len(not_found_titles) > 0:
        print('❌ Failed to find', len(not_found_titles),'paper ids')
    elif len(not_in_db_titles)>0:
        print("✅ Found all", len(not_in_db_titles),'papers')
    extracting_paper_dict={}
    for title in titles:
        if not(paper_dict[title] is None):
            extracting_paper_dict[title]=paper_dict[title]
    return extracting_paper_dict, not_found_titles

def merge_json_dbs_to_single_csv_db(db_paths, new_db_path):
    dicts=[]
    for db_path in db_paths:
        with open(db_path, "r") as f:
            dicts.append(json.load(f))
        print('Old DB path:', db_path, 'has', len(dicts[-1]),'data items')
    big_dict={}
    for db_dict in dicts:
        for title, p_id in db_dict.items():
            data = {'title': title, 'id':p_id}
            big_dict[title] = data
    print('Merged db has', len(big_dict), 'data items')
    data_ls=[]
    for title, data in big_dict.items():
        data_ls.append(data)
    with open(new_db_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=data_ls[0].keys())
        writer.writeheader()
        writer.writerows(data_ls)
    print('✅ New db saved to', new_db_path)

def download_arxiv_source(arxiv_id, save_path):
    '''
    return True if download was successful
    return False if download was unsuccessful
    '''
    url1 = f"https://arxiv.org/src/{arxiv_id}"
    url2 = f"https://export.arxiv.org/src/{arxiv_id}"
    response = requests.get(url1)
    
    if response.status_code == 200:
        with open(save_path, "wb") as f:
            f.write(response.content)
        return True
    else:
        response = requests.get(url2)
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(response.content)
            return True
        else:
            print(response.status_code)
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
                with tarfile.open(tar_path, "r:*") as tar: #with tarfile.open(tar_path, "r:gz") as tar:
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
    
def ensure_safe_resume(paper_id_dict, csv_path, folder, img_folder):
    '''
    This function ensure img_folder and csv_path have the same values
    
    p.s.
    if we want the folder to only contains data that's in paper_id_dict, add "& set(paper_id_dict.values())" to overlapping_ids
    '''
    overlapping_ids = set()
    if os.path.isdir(img_folder) and  os.path.isfile(csv_path):
        df = pd.read_csv(csv_path)
        csv_ids=df["arxiv_id"].dropna().tolist()
        
        filenames = os.listdir(img_folder)
        id_filename_dict = {os.path.splitext(f)[0]:f for f in filenames}
        img_ids = list(id_filename_dict.keys())
        overlapping_ids = set(csv_ids) & set(img_ids)
        if len(set(img_ids) - overlapping_ids)>0:
            to_be_deleted = list(set(img_ids) - overlapping_ids)
            for id_ in to_be_deleted:
                os.remove(os.path.join(img_folder, id_filename_dict[id_]))

        rows=[]
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Access columns by name
                title = row.get('paper_title')
                abstract = row.get('abstract')
                id_ = row.get('arxiv_id')
                fig1_path = row.get('fig1_file_path')
                caption = row.get('fig1_caption')
                introduction = row.get('introduction')
                if id_ in overlapping_ids:
                    rows.append({
                        "paper_title": title,
                        "arxiv_id": id_,
                        "abstract": abstract,
                        "fig1_file_path": fig1_path,
                        "fig1_caption": caption,
                        "introduction": introduction
                    })
        # Write to temporary file first
        temp_csv_path = csv_path + ".tmp"
        # ✅ Save to CSV
        fieldnames = ["paper_title", "arxiv_id", "fig1_file_path", "fig1_caption", "abstract", "introduction"]
        with open(temp_csv_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        # Safely replace original file with the temporary file
        os.replace(temp_csv_path, csv_path)
    else:
        ensure_empty_dir(folder)
        ensure_empty_dir(img_folder)
    remaining_paper_id_dict = {}
    checkpoint_titles = []
    for title, id_ in paper_id_dict.items():
        if not(id_ in overlapping_ids):
            remaining_paper_id_dict[title]=id_
        else:
            checkpoint_titles.append(title)
    if len(overlapping_ids - set(paper_id_dict.values()))>0:
        print('🫶 Found', len(overlapping_ids - set(paper_id_dict.values())),'data items that are not in requested list in benchmark directory and safely kept all.')
    if len(overlapping_ids & set(paper_id_dict.values()))>0: 
        print('➡️ Resume from previous checkpoint where', len(overlapping_ids & set(paper_id_dict.values())),'out of',len(paper_id_dict),'data items exist')     
    if len(remaining_paper_id_dict)>0:
        print('Start extracting the remaining', len(remaining_paper_id_dict),'out of', len(paper_id_dict), 'to csv')
    return checkpoint_titles, remaining_paper_id_dict
        


def extract_to_csv(paper_id_dict, latex_files_path, csv_path, fig1_path_separater=';'):
    folder=os.path.dirname(csv_path)
    img_folder=os.path.join(folder, 'img')
    total_extractions, paper_id_dict = ensure_safe_resume(paper_id_dict, csv_path, folder, img_folder)
    fieldnames = ["paper_title", "arxiv_id", "fig1_file_path", "fig1_caption", "abstract", "introduction"]
    if not(os.path.isfile(csv_path)):
        with open(csv_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
    success_extractions=[]
    for title, id in paper_id_dict.items():
        print('✅ Working on extracting title:', title, 'id:',id)
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
                    if not(os.path.isfile(fig1_file_path)):
                        break
                    shutil.copy2(fig1_file_path, destination_path)
                    fig1_file_path=destination_path
                    
                    row_dict={
                        "paper_title": title,
                        "arxiv_id": id,
                        "abstract": abstract_str,
                        "fig1_file_path": fig1_file_path,
                        "fig1_caption": fig1_caption_str,
                        "introduction": introduction_str
                    }
                    # ✅ Save to CSV
                    with open(csv_path, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)                        
                        writer.writerow(row_dict)
                    success_extractions.append(title)
                    break
    total_extractions = total_extractions + success_extractions
    print('✅',len(success_extractions),'out of',len(paper_id_dict),'were extracted and saved to CSV', csv_path)
    return total_extractions

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