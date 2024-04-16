from pandas.api.types import is_numeric_dtype, is_float_dtype
import logging
def detect_if_key_is_float(df, key):
    if is_float_dtype(df[key]):
        return True


def detect_if_key_is_numeric(df, key):
    if is_numeric_dtype(df[key]):
        return True
    # there is an problem sometimes with identifying numeric dtypes.
    # saving and reloading a dataframe fixes this, but this also should deal with most cases
    elif isinstance(df[key].iloc[0], float):
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

def download_files_simple_example_1():
    # download files needed to run simple example 1
    # https://github.com/JoeGreiner/BokehBioImageDataVis/tree/main/examples/simple_1/data/pictures/cat1.jpg
    # https://github.com/JoeGreiner/BokehBioImageDataVis/tree/main/examples/simple_1/data/pictures/dog1.jpg
    # https://github.com/JoeGreiner/BokehBioImageDataVis/tree/main/examples/simple_1/data/pictures/dog2.jpg
    # https://github.com/JoeGreiner/BokehBioImageDataVis/tree/main/examples/simple_1/data/videos/cat1.mp4
    # https://github.com/JoeGreiner/BokehBioImageDataVis/tree/main/examples/simple_1/data/videos/dog1.mp4
    # https://github.com/JoeGreiner/BokehBioImageDataVis/tree/main/examples/simple_1/data/videos/dog2.mp4
    import os
    import requests

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

    logging.info('downloading files for simple example 1')

    # save them to data/videos and data/pictures
    os.makedirs('data/videos', exist_ok=True)
    os.makedirs('data/pictures', exist_ok=True)
    picture_files = ['cat1.jpg', 'dog1.jpg', 'dog2.jpg']
    video_files = ['cat1.mp4', 'dog1.mp4', 'dog2.mp4']
    for file in picture_files:
        if not os.path.exists(f'data/pictures/{file}'):
            logging.info(f'downloading {file}')
            url = f'https://raw.githubusercontent.com/JoeGreiner/BokehBioImageDataVis/main/examples/simple_1/data/pictures/{file}'
            r = requests.get(url, allow_redirects=True)
            open(f'data/pictures/{file}', 'wb').write(r.content)
    for file in video_files:
        if not os.path.exists(f'data/videos/{file}'):
            logging.info(f'downloading {file}')
            url = f'https://raw.githubusercontent.com/JoeGreiner/BokehBioImageDataVis/main/examples/simple_1/data/videos/{file}'
            r = requests.get(url, allow_redirects=True)
            open(f'data/videos/{file}', 'wb').write(r.content)
    logging.info('downloads for simple example 1 done')




