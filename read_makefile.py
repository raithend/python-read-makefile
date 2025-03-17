import re
import os
import glob

def analyze_makefile(makefile_path):
    with open(makefile_path, 'r') as file:
        content = file.read()
    
    # 解析結果を格納する辞書
    analysis = {
        'source_directories': set(),
        'language': None,  # 'C' or 'C++' or 'Both'
        'include_directories': set(),
        'has_multithreading': False
    }
    
    # 変数の抽出（Makefileで定義されている変数を取得）
    variables = {}
    var_pattern = re.compile(r'^\s*([A-Za-z0-9_]+)\s*[:\+]?=\s*(.+?)(?:\s*#.*)?$', re.MULTILINE)
    for match in var_pattern.finditer(content):
        key, value = match.groups()
        variables[key] = value.strip()
    
    # ソースディレクトリの検出
    # SRCDIRなどの一般的な変数名を確認
    for key in ['SRCDIR', 'SRC_DIR', 'SOURCE_DIR', 'SOURCES_DIR']:
        if key in variables:
            analysis['source_directories'].add(variables[key])
    
    # ソースファイルのパターンから推測
    src_patterns = [
        r'^\s*\w+\s*=\s*(.+\/)*\*\.[ch]pp', # C++ファイルを含むパターン
        r'^\s*\w+\s*=\s*(.+\/)*\*\.[ch]',   # Cファイルを含むパターン
        r'^\s*[A-Za-z0-9_]+\s*:\s*(.+\/)*[\w\.]+\.[ch]pp', # 依存関係からC++を検出
        r'^\s*[A-Za-z0-9_]+\s*:\s*(.+\/)*[\w\.]+\.[ch]'    # 依存関係からCを検出
    ]
    
    for pattern in src_patterns:
        for match in re.finditer(pattern, content, re.MULTILINE):
            line = match.group(0)
            # ディレクトリパスを抽出
            dir_match = re.search(r'([^\s:=]+\/)[^\/]*\.[ch]', line)
            if dir_match:
                analysis['source_directories'].add(dir_match.group(1))
    
    # 言語の検出
    cpp_files = re.search(r'\.(cpp|cxx|cc|hpp|hxx)(?:\s|$)', content) is not None
    c_files = re.search(r'(?<!\.)\.c(?:\s|$)', content) is not None
    
    if cpp_files and c_files:
        analysis['language'] = 'Both'
    elif cpp_files:
        analysis['language'] = 'C++'
    elif c_files:
        analysis['language'] = 'C'
    
    # インクルードディレクトリの検出
    include_patterns = [
        r'-I\s*([^\s]+)',
        r'INCLUDE\w*\s*[:\+]?=\s*([^\s#]+)'
    ]
    
    for pattern in include_patterns:
        for match in re.finditer(pattern, content):
            path = match.group(1).strip()
            analysis['include_directories'].add(path)
    
    # マルチスレッド関連の検出
    thread_indicators = [
        r'-lpthread',
        r'-pthread',
        r'thread',
        r'pthread',
        r'std::thread',
        r'boost::thread',
        r'#include\s*[<"]thread[">]'
    ]
    
    for indicator in thread_indicators:
        if re.search(indicator, content, re.IGNORECASE):
            analysis['has_multithreading'] = True
            break
    
    return analysis

# 使用例
if __name__ == "__main__":
    result = analyze_makefile("./Makefile")
    print("ソースディレクトリ:", result['source_directories'])
    print("プログラミング言語:", result['language'])
    print("インクルードディレクトリ:", result['include_directories'])
    print("マルチスレッド使用:", "はい" if result['has_multithreading'] else "いいえ")