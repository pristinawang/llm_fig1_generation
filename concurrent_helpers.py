import concurrent.futures
from benchmark_helpers import *

def subprocess_extract_helper(input_items):
    return subprocess_extract(input_items[0], input_items[1], input_items[2], input_items[3], input_items[4])
def subprocess_extract(tex_files, title, id, folder_path, folder):
    row_dict=None
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
            # # ✅ Save to CSV
            # with open(csv_path, mode='a', newline='', encoding='utf-8') as f:
            #     writer = csv.DictWriter(f, fieldnames=fieldnames)                        
            #     writer.writerow(row_dict)
            # success_extractions.append(title)
            break
    return row_dict

def parallel_extract_to_csv(paper_id_dict, latex_files_path, csv_path, max_workers, fig1_path_separater=';'):
    folder=os.path.dirname(csv_path)
    img_folder=os.path.join(folder, 'img')
    total_extractions, paper_id_dict = ensure_safe_resume(paper_id_dict, csv_path, folder, img_folder)
    fieldnames = ["paper_title", "arxiv_id", "fig1_file_path", "fig1_caption", "abstract", "introduction"]
    if not(os.path.isfile(csv_path)):
        with open(csv_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
    
    input_items = []
    for title, id in paper_id_dict.items():
        folder_path=latex_files_path+'/'+id
        tex_files = list_top_level_tex_files(folder_path=folder_path)
        if len(tex_files)==0:
            print(f" ❌ {id} Failed to find tex file.")
        else:
            input_items.append((tex_files, title, id, folder_path, folder))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    #with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(subprocess_extract_helper, input_items))
    success_extractions=[]
    for row_dict in results:
        if not(row_dict is None):
            # ✅ Save to CSV
            with open(csv_path, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)                        
                writer.writerow(row_dict)
            success_extractions.append(row_dict['paper_title'])
            
    total_extractions = total_extractions + success_extractions
    print('✅',len(success_extractions),'out of',len(paper_id_dict),'were extracted and saved to CSV', csv_path)
    return total_extractions