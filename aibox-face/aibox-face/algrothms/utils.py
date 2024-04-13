def get_import_meta(model_type: str):
    if model_type == "rt":
        import metart as meta
    elif model_type == "rknn":
        import metarknn as meta
    else:
        raise ValueError(f"未知的模型类型: {model_type}")
    return meta
