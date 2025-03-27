from benchmark_helpers import *

def main():
    # Use benchmark_helpers to crawl bench mark
    year='2024'
    titles=return_acl_paper_titles(year=year)
    titles_small=titles[:10]
    paper_id_dict, not_found_titles = get_arxiv_id_dict(titles=titles_small, max_results=10)
    download_latex_files(paper_id_dict=paper_id_dict, save_dir_path='./arxiv_source/')
    extract_to_csv(paper_id_dict=paper_id_dict, latex_files_path='./arxiv_source', csv_path='./benchmark/fig1_bench.csv')

if __name__ == "__main__":
    main()