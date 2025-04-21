from benchmark_helpers import *

def main():
    # Use benchmark_helpers to crawl bench mark
    year='2020'
    venue='acl'
    titles=return_paper_titles(year=year, venue=venue)
    #titles=['ABEX: Data Augmentation for Low-Resource NLU via Expanding Abstract Descriptions']
    # titles=['Unsupervised Multimodal Clustering for Semantics Discovery in Multimodal Utterances',
    #         'Detoxifying Large Language Models via Knowledge Editing',
    #         'Synergetic Event Understanding: A Collaborative Approach to Cross-Document Event Coreference Resolution with Large Language Models',
    #         'Ex3: Automatic Novel Writing by Extracting, Excelsior and Expanding',
    #         'Enhancing EEG-to-Text Decoding through Transferable Representations from Pre-trained Contrastive EEG-Text Masked Autoencoder',
    #         'Towards Real-world Scenario: Imbalanced New Intent Discovery',
    #         'Picturing Ambiguity: A Visual Twist on the Winograd Schema Challenge',
    #         'SportsMetrics: Blending Text and Numerical Data to Understand Information Fusion in LLMs',
    #         'Token-wise Influential Training Data Retrieval for Large Language Models']
    paper_id_dict, not_found_titles = get_arxiv_id_dict(titles=titles, max_results=10)
    paper_id_dict=download_latex_files(paper_id_dict=paper_id_dict, save_dir_path='./arxiv_source/')
    success_extractions=extract_to_csv(paper_id_dict=paper_id_dict, latex_files_path='./arxiv_source', csv_path='./benchmark/fig1_bench.csv')
    print("🎉",len(success_extractions),"out of", len(titles),"papers are successfully extracted")

if __name__ == "__main__":
    main()
    