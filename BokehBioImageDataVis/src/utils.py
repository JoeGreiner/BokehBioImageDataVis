from pandas.api.types import is_numeric_dtype, is_float_dtype

def detect_if_key_is_float(df, key):
    if is_float_dtype(df[key]):
        return True


def detect_if_key_is_numeric(df, key):
    if is_numeric_dtype(df[key]):
        return True
    # there is an problem sometimes with identifying numeric dtypes.
    # saving and reloading a dataframe fixes this, but this also should deal with most cases
    elif isinstance(df[key][0], float):
        # nan can also be dealt as float
        # check if there is a nan in the column, if so, trust the original numeric dtype detection
        if not df[key].isnull().values.any():
            return True
    return False

def identify_numerical_variables(df):
    numeric_options = []
    for key in list(df.keys()):
        if detect_if_key_is_numeric(df, key):
            numeric_options.append(key)
    print(numeric_options)
    return numeric_options