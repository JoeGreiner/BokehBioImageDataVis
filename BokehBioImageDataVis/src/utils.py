from pandas.api.types import is_numeric_dtype

def identify_numerical_variables(df):
    numeric_options = []
    for key in list(df.keys()):
        if is_numeric_dtype(df[key]):
            numeric_options.append(key)
        # there is an problem sometimes with identifying numeric dtypes.
        # saving and reloading a dataframe fixes this, but this also should deal with most cases
        elif isinstance(df[key][0], float):
            numeric_options.append(key)

    return numeric_options