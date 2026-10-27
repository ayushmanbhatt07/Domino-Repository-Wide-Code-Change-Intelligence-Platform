from tree_sitter import Language, Parser

_parser = None

def get_python_parser() -> Parser:
    global _parser
    if _parser is not None:
        return _parser
        
    try:
        import tree_sitter_python as tspython
        lang = Language(tspython.language())
        _parser = Parser(lang)
        return _parser
    except Exception:
        pass

    try:
        from tree_sitter_language_pack import get_parser
        _parser = get_parser("python")
        return _parser
    except Exception as e:
        raise RuntimeError(f"Could not initialize Tree-sitter Python parser: {e}")
