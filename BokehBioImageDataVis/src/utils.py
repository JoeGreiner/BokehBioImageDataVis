from pandas.api.types import is_numeric_dtype

def identify_numerical_variables(df):
    numeric_options = []
    for key in list(df.keys()):
        if is_numeric_dtype(df[key]):
            numeric_options.append(key)
    return numeric_options