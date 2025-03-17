import re
import os
import glob

def parse_include_files(makefile_path, parsed_files=None):
    """
    Makefileとincludeされている.mkファイルを再帰的に解析する
    
    Args:
        makefile_path: 解析するMakefileのパス
        parsed_files: 既に解析したファイルのセット（循環参照防止用）
    
    Returns:
        全てのファイルの内容を結合したテキスト
    """
    if parsed_files is None:
        parsed_files = set()
    
    # 既に解析済みのファイルは再度解析しない（循環参照防止）
    if makefile_path in parsed_files:
        return ""
    
    # 解析済みファイルとして記録
    parsed_files.add(makefile_path)
    
    if not os.path.exists(makefile_path):
        print(f"警告: ファイル {makefile_path} が見つかりません")
        return ""
    
    # ファイルを読み込む
    with open(makefile_path, 'r', errors='ignore') as file:
        content = file.read()
    
    # includeディレクティブを検索
    include_pattern = re.compile(r'^\s*include\s+(.+)$', re.MULTILINE)
    
    # 現在のディレクトリをベースディレクトリとする
    base_dir = os.path.dirname(makefile_path)
    
    # 全てのincludeファイルの内容を取得
    for match in include_pattern.finditer(content):
        include_path = match.group(1).strip()
        
        # 変数展開を簡易的に処理
        # $(VAR)や${VAR}形式の変数展開を処理
        var_pattern = re.compile(r'\$[\({]([A-Za-z0-9_]+)[\)}]')
        
        # 簡易的な変数展開（完全な処理は複雑なため、基本的なケースのみ対応）
        def expand_var(match):
            var_name = match.group(1)
            # 変数の値を探す（簡易的な実装）
            var_pattern = re.compile(r'^\s*' + re.escape(var_name) + r'\s*[:\+]?=\s*(.+?)(?:\s*#.*)?$', re.MULTILINE)
            var_match = var_pattern.search(content)
            if var_match:
                return var_match.group(1).strip()
            return match.group(0)  # 変数が見つからない場合は置換しない
        
        include_path = var_pattern.sub(expand_var, include_path)
        
        # 相対パスを絶対パスに変換
        if not os.path.isabs(include_path):
            include_path = os.path.normpath(os.path.join(base_dir, include_path))
        
        # ワイルドカードを処理
        if '*' in include_path:
            include_files = glob.glob(include_path)
            for include_file in include_files:
                content += parse_include_files(include_file, parsed_files)
        else:
            content += parse_include_files(include_path, parsed_files)
    
    return content

def analyze_makefile(makefile_path):
    """
    Makefileとincludeされている全ての.mkファイルを解析する
    """
    # 全てのファイルの内容を結合
    content = parse_include_files(makefile_path)
    
    # 解析結果を格納する辞書
    analysis = {
        'source_directories': set(),
        'language': None,  # 'C' or 'C++' or 'Both'
        'include_directories': set(),
        'has_multithreading': False,
        'included_files': set()  # includeされたファイルのリスト
    }
    
    # このあとは前回同様の解析コードを続ける
    # 変数の抽出
    variables = {}
    var_pattern = re.compile(r'^\s*([A-Za-z0-9_]+)\s*[:\+]?=\s*(.+?)(?:\s*#.*)?$', re.MULTILINE)
    for match in var_pattern.finditer(content):
        key, value = match.groups()
        variables[key] = value.strip()
    
    # ソースディレクトリの検出
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
    
    # includeファイルの記録
    include_pattern = re.compile(r'^\s*include\s+(.+)$', re.MULTILINE)
    for match in include_pattern.finditer(content):
        include_path = match.group(1).strip()
        analysis['included_files'].add(include_path)
    
    return analysis

# 使用例
if __name__ == "__main__":
    result = analyze_makefile("./Makefile")
    print("ソースディレクトリ:", result['source_directories'])
    print("プログラミング言語:", result['language'])
    print("インクルードディレクトリ:", result['include_directories'])
    print("マルチスレッド使用:", "はい" if result['has_multithreading'] else "いいえ")
    print("含まれるファイル:", result['included_files'])