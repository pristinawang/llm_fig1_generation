import re

class LatexBlock:
    def __init__(self, result_tuple):
        self.result_tuple=result_tuple
    def get_index(self):
        
        return self.result_tuple[0]
    def get_tex(self):
        return self.result_tuple[1]
    def is_none(self):
        if self.result_tuple is None: return True
        else: return False    
        
def find_figure_block(text):

    # 2. \begin{figure} ... \end{figure}
    match2 = re.search(r'\\begin\{figure\}.*?\\end\{figure\}', text, re.DOTALL)
    if match2:
        return (match2.start(), match2.group())
    else: return None

def find_include_graphic_block(text):

    # 1. \includegraphics[...]{...}
    match1 = re.search(r'\\includegraphics\s*\[.*?\]\s*\{.*?\}', text, re.DOTALL)
    if match1:
        return (match1.start(), match1.group())
    else: return None
    
def find_twocolumn_block(text):
    pattern = r'\\twocolumn\s*\['
    match = re.search(pattern, text)
    if not match:
        return None

    start_idx = match.start()
    idx = match.end()  # Position after the opening [

    depth = 1
    while idx < len(text):
        char = text[idx]
        if char == '[':
            depth += 1
        elif char == ']':
            depth -= 1
            if depth == 0:
                return start_idx, text[start_idx:idx + 1]
        idx += 1

    return None  # No matching closing bracket found

def count_includegraphics(text):
    matches = re.findall(r'\\includegraphics\b', text)
    return len(matches)

def remove_latex_comments(text):
    lines = text.splitlines()
    new_lines = []
    for line in lines:
        # Remove everything after a non-escaped '%'
        uncommented = re.split(r'(?<!\\)%', line)[0]
        new_lines.append(uncommented.rstrip())  # strip trailing spaces
    return '\n'.join(new_lines)

def simple_ext(latex_str, debug=False):
    latex_str=remove_latex_comments(latex_str)
    two_col_block=LatexBlock(find_twocolumn_block(latex_str))
    graph_block=LatexBlock(find_include_graphic_block(latex_str))
    fig_block=LatexBlock(find_figure_block(latex_str))
    if graph_block.is_none(): 
        print('No graphic in this latex doc')
        return None
    if not(fig_block.is_none()) and not(two_col_block.is_none()):
        if fig_block.get_index()<two_col_block.get_index():
            figone_block = fig_block
            print('Using figure block')
        elif fig_block.get_index()>two_col_block.get_index():
            figone_block = two_col_block
            print('Using two column block')
        else:
            return None
    elif fig_block.is_none():
        figone_block = two_col_block
    elif two_col_block.is_none():
        figone_block = fig_block
    else:
        print('Figure extraction failed: regular expression cannot find neither twocolumn block or figure block')
        return None
    if count_includegraphics(figone_block.get_tex())!=1:
        print('The fig1 block has more than 1 pic. Count:', count_includegraphics(figone_block.get_tex()))
        return None
    figone_graph_block=LatexBlock(find_include_graphic_block(figone_block.get_tex()))
    if figone_graph_block.is_none():
        print('No graphic in figure1 block')
        return None
    if graph_block.get_index()==figone_graph_block.get_index()+figone_block.get_index():
        print('First pic in doc is in fig1 block with index', graph_block.get_index())
        if debug: print('----------⚠️ fig1 raw tex-----------\n',figone_block.get_tex(), '\n---------------------------')
    else:
        if debug: print('----------⚠️ fig1 block raw tex-----------\n',figone_block.get_tex(), '\n---------------------------')
        if debug: print('----------⚠️ first pic raw tex-----------\n',graph_block.get_tex(), '\n---------------------------')
    
        print('First pic is not in fig1 block')
        return None
    results = extract_latex_figures(figone_block.get_tex())
    if len(results['includegraphics']) > 1 or len(results['captions'])>1:
        if debug: print('----------⚠️ fig extraction result-----------\n',results, '\n---------------------------')
        print('More than one pic or more than one caption is found in figure 1 block. Pic#:', len(results['includegraphics']), 'Cap#:', len(results['captions']))
        return None
    else:
        path = results['includegraphics'][0][1]
        caption = results['captions'][0]
        return {'path': path, 'cap_tex': caption}





def extract_brace_content(text, start_idx):
    assert text[start_idx] == '{'
    idx = start_idx + 1
    depth = 1
    content = []

    while idx < len(text):
        char = text[idx]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return ''.join(content), idx  # content, end_index
        content.append(char)
        idx += 1

    raise ValueError("Unbalanced braces in LaTeX content.")



def extract_latex_figures(text):
    results = {
        'includegraphics': [],  # list of (options, path)
        'captions': []          # list of caption texts
    }

    # 1. Find all \includegraphics[options]{path}
    pattern_includegraphics = re.compile(
        r'\\includegraphics\s*\[(.*?)\]\s*\{(.*?)\}',
        re.DOTALL
    )
    for match in pattern_includegraphics.finditer(text):
        options = match.group(1).strip()
        path = match.group(2).strip()
        results['includegraphics'].append((options, path))

    # 2. Find all \caption{...}
    pattern_caption = re.compile(r'\\caption\s*\{', re.DOTALL)
    for match in pattern_caption.finditer(text):
        start = match.end() - 1  # point at {
        content, _ = extract_brace_content(text, start)
        results['captions'].append(content.strip())

    # 3. Find all \captionof{...}{...}
    pattern_captionof = re.compile(r'\\captionof\s*\{(.*?)\}\s*\{', re.DOTALL)
    for match in pattern_captionof.finditer(text):
        after_type = match.end() - 1  # point at second {
        content, _ = extract_brace_content(text, after_type)
        results['captions'].append(content.strip())

    return results
